# 8.1 Compose — reference

`ollama serve` on your machine, then one `docker compose up --build`, and the real stack is online: the capstone assistant and its MCP server (both built from the SAME image — `workshops/assistant/after` and its Dockerfile), plus pinned Qdrant. Zero API keys.

What makes this deployable rather than a diagram:

- **Pinned images, by tag and digest.** `qdrant/qdrant:v1.18.3` and the rest each carry an `@sha256:…` after the tag. `:latest` means every reviewer runs a different stack, and a version tag only narrows that — a tag is a mutable pointer its publisher can repoint at a rebuild, so the digest is the part that actually names the bytes. The tag stays because a digest alone is unreadable.
- **Healthchecks everywhere, and dependencies wait on them.** `depends_on: condition: service_healthy` — a started Qdrant is not a ready Qdrant.
- **The model is on the host, on purpose.** `OLLAMA_HOST: http://host.docker.internal:11434` plus `extra_hosts: ["host.docker.internal:host-gateway"]`, which Docker Desktop provides by name and Linux needs mapped explicitly. See below for the number that decided this.
- **One published port.** Only the assistant reaches the host; MCP and Qdrant stay on the compose network.

`src/health.py` reviews the compose file structurally (parsed YAML — services, pins, healthchecks, dependency conditions, published ports), and the tests prove the checks catch a broken file, not just bless this one. `src/preflight.py` covers what YAML cannot: the daemon outside the stack.

## Secure profile

The base file is a **zero-key local demo** — no auth, port on every interface. That is the right default for a laptop and the wrong one for a host with a public IP. The overlay switches the controls on:

```bash
ASSISTANT_JWT_SECRET=$(openssl rand -base64 48) \
  docker compose -f docker-compose.yml -f docker-compose.secure.yml up --build
```

- **Auth on.** Every mutating endpoint demands a Bearer JWT carrying `exp`, `aud`, `sub` and the endpoint's scope. `ASSISTANT_JWT_LEEWAY=30` is the clock-skew policy: wide enough that two honest machines agree, narrow enough that a revoked token stops working promptly.
- **The secret comes from the environment.** `${ASSISTANT_JWT_SECRET:?...}` — compose refuses to start rather than fall back to a committed default, because a committed default is a published credential.
- **Load shedding on.** `RATE_LIMIT_RPS`, `RATE_LIMIT_BURST`, `MAX_CONCURRENCY` — reject politely rather than degrade for everyone.
- **Loopback only.** `127.0.0.1:8000:8000`. Put a TLS-terminating reverse proxy in front; the service speaks plain HTTP on purpose and does not pretend otherwise.
- **Reduced blast radius.** `read_only`, `cap_drop: ALL`, `no-new-privileges` on both Python services.

`secure_overlay_problems()` in `src/health.py` reviews this overlay the same way the base checks review the base file — merged environment, secret indirection, port binding — and `test_the_secure_checks_catch_an_overlay_that_only_pretends` proves the checks fail on an overlay whose controls are only comments.

## OAuth 2.1 + PKCE lane (optional)

The secure profile uses a shared HS256 secret, which is honest about what it is: fine for one operator, wrong for many. Add the OAuth overlay to swap it for real asymmetric verification against an identity provider's JWKS:

```bash
ASSISTANT_JWT_SECRET=unused \
  docker compose -f docker-compose.yml -f docker-compose.secure.yml \
                 -f docker-compose.oauth.yml up --build
python oauth/pkce_login.py     # browser opens; log in as alice/alice
curl -H "Authorization: Bearer $TOKEN" localhost:8000/ask -d '{"goal":"hello"}'
```

`docker-compose.oauth.yml` adds a pinned Keycloak importing `oauth/assistant-realm.json`: a **public** client (`assistant-cli`) with PKCE `S256` required, loopback redirect URI, an audience mapper stamping `aud: assistant`, and `assistant:ask` / `assistant:ingest` / `assistant:approve` as client scopes. The overlay points the assistant at `ASSISTANT_JWKS_URL` and `ASSISTANT_JWT_ISSUER` instead of a secret, so `auth.py` verifies RS256 against fetched keys and rejects anything issued elsewhere.

`oauth/pkce_login.py` runs the browser half of the flow using `assistant/oauth.py` — the same module the capstone's offline tests cover, so the tested code and the runnable script are not two different flows.

## Guard-model lane (optional)

The deterministic screen is the floor and stays the floor. `ASSISTANT_GUARD_MODEL` adds a local model as a second opinion on every untrusted string — question, retrieved document, tool output, ingested document:

```bash
ollama pull llama-guard3:8b        # on the host, like every other model
ASSISTANT_GUARD_MODEL=llama-guard3:8b docker compose up -d assistant
curl -s localhost:8000/health | python3 -m json.tool | grep guard
```

It is off by default because it costs a model round trip per untrusted string, and it is wired so it can only ever **add** a block — never clear one — and fails open to the deterministic verdict when Ollama is slow or down. `/health` reports `tier.guard` so an operator can tell from outside which screen is actually in front of the caller. See [ADR-0010](../../../workshops/assistant/adr/0010-the-screen-expands-squashes-and-may-ask-a-model.md).

## Observability overlay (optional)

```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml up --build
docker compose -f docker-compose.yml -f docker-compose.observability.yml logs collector
```

`docker-compose.observability.yml` adds a pinned OpenTelemetry Collector (`otel-collector.yaml` config: OTLP-in over HTTP, debug exporter to stdout) and sets `OTEL_EXPORTER_OTLP_ENDPOINT` on the assistant. The assistant's instrumentation does not change — the same spans that back `spans_recorded` on `/health` also ship over OTLP, and `logs collector` shows the `agent.run` trees arriving **outside the process**. Swap the debug exporter for an `otlp` exporter at Phoenix, Langfuse or your APM and nothing upstream notices; that pluggability is why the course exports OTel instead of a vendor SDK. `verify-e2e.sh` boots with this overlay and asserts the collector saw the spans.

## Why the model is not in the compose file

Docker Desktop on macOS gives containers **no GPU access**. A containerised Ollama therefore runs the course's 9B on CPU inside a VM, measured at **0.52 tokens/second**. The same model, on the same laptop, through the host's Ollama with Metal: **81 tokens/second**. Identical code, identical model, 156× — the entire difference is which side of the VM boundary the accelerator is on.

That is why this stack keeps its infrastructure in compose and its model on the host. Three things follow, and only one of them is about speed:

- **`extra_hosts` is not optional.** Docker Desktop resolves `host.docker.internal` on its own; Linux does not, and without `host.docker.internal:host-gateway` the assistant resolves nothing, every composition fails, and the offline stitcher answers with the stack looking perfectly healthy. Mapping it explicitly costs one line and makes the file portable.
- **If your production plan is "containerised model on a VM without a GPU", 0.52 tokens/second is your latency budget**, not a laptop artifact. Either give the container the accelerator, call a model over the network, or design for the number you actually have.
- **Timeouts are part of that budget and belong next to the deployment.** `COMPOSE_TIMEOUT_SECONDS: "60"`. The library default of 60 seconds is a GPU's number, which is right here and was catastrophically wrong in a container: at half a token per second every composition blew through it, the offline stitcher answered, and the end-to-end run failed on a stack working exactly as configured. The value is declared in the compose file rather than inherited from a library, because a timeout is a statement about the hardware underneath.

What the split costs is `depends_on`. Compose cannot start the host's Ollama, cannot health-gate on it, and will bring the stack up cheerfully without it. `src/preflight.py` replaces that lost guarantee — and inherits the sharper half of the old model bootstrap's lesson.

## Preflight (the dependency compose cannot wait for)

```bash
../../preflight-ollama.sh            # human-readable
../../preflight-ollama.sh --json     # the record verify-e2e.sh attests
```

Six checks, each printing the exact command that fixes it: the daemon answers, `qwen3.5:9b` is present, `nomic-embed-text` is present, the chat model **answers a token**, the embedder **returns a vector**, and a throwaway container can reach the host through `host-gateway`.

The two warmups are the point. `ollama list` reports a file on disk, and loading a 9B takes longer than the composer's entire budget — so a stack that treats presence as readiness times out its own first question and answers it from the fallback with every probe green. This is the `cold_model_healthchecks` idea from the containerised era, which was always about the same confusion and is now enforced where the model actually lives.

It never pulls. A 5.6 GB download is the operator's decision; a check that starts one silently has stopped being a check.

One trap it handles explicitly: `OLLAMA_HOST` is a **bind address** to the Ollama server (`0.0.0.0:11434`) and a **client URL** to everything else (`http://localhost:11434`). A shell that exported the server's meaning must not have `0.0.0.0` dialled back at it, or leaked into the container's environment.

`--json` emits the Ollama version and both model digests, which `verify-e2e.sh` folds into its attestation — so a release claim names the bytes that produced it rather than just a model tag.

## CI overlay (what a hosted runner can honestly measure)

```bash
docker compose -f docker-compose.yml -f docker-compose.ci.yml up --build
../../../verify-e2e.sh --ci             # the nightly workflow's exact lane
../../../verify-e2e.sh --model TAG      # the same, with a tag you choose
```

`docker-compose.ci.yml` swaps the chat model for a 1.7B and gives the composer a longer deadline; everything else is unchanged. The reason is the number above with the sign flipped: a GitHub runner is four CPU cores with no GPU anywhere — host or container — so the 9B would miss the composer's budget on every request and the whole run would report the fallback tier's behaviour under the model's name. The workflow still installs Ollama on the runner rather than in a container, so CI exercises the same `host.docker.internal` path a learner does.

This is the part worth taking with you. A cheap lane is only worth having if it is **labelled by what it measures**, and the labelling has to survive being quoted out of context — a green check gets pasted into a pull request without its workflow name attached. So the model tag is registered in `app/src/data/reference.ts` as a `ci`-tier entry with the exact list of files allowed to name it, `check-claims` fails if it appears anywhere else, the workflow is called `e2e (wiring, small model)`, and the script prints its lane twice: once before check 1 and once under the final count.

What the small model still proves is most of the suite: the stack boots and passes its own healthchecks, the gate refuses unauthenticated and under-scoped calls, retrieval is hybrid over Qdrant with the real embedder (unchanged — `nomic-embed-text` is small and fast, and weakening it would gut check 4's semantic-recall assertion), injections are refused in four spellings, a gated tool pauses and runs once for the approver only, retries replay, discovered tools obey local policy, memory stays partitioned, spans reach the collector, state survives a restart. What it cannot prove is answer quality; that is the unqualified `./verify-e2e.sh`, and `workshops/assistant/after/docs/RELEASE-CHECKLIST.md` makes it a precondition for publishing.
