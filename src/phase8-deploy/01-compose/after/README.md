# 8.1 Compose — reference

One `docker compose up --build` brings the real stack online: the capstone assistant and its MCP server (both built from the SAME image — `workshops/assistant/after` and its Dockerfile), plus pinned Qdrant and Ollama. Zero API keys.

What makes this deployable rather than a diagram:

- **Pinned images.** `qdrant/qdrant:v1.18.3`, `ollama/ollama:0.32.5`. `:latest` means every reviewer runs a different stack.
- **Healthchecks everywhere, and dependencies wait on them.** `depends_on: condition: service_healthy` — a started Qdrant is not a ready Qdrant.
- **Model bootstrap.** The ollama service pulls `qwen3.5:9b` and `nomic-embed-text` on first boot and only reports healthy once they're in, so the assistant never starts against an empty model store.
- **One published port.** Only the assistant reaches the host; MCP, Qdrant and Ollama stay on the compose network.

`src/health.py` reviews the compose file structurally (parsed YAML — services, pins, healthchecks, dependency conditions, published ports), and the tests prove the checks catch a broken file, not just bless this one.

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
docker compose exec ollama ollama pull llama-guard3:8b
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
