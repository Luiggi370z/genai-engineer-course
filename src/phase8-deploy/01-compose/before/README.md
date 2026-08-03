# 8.1 Compose

**Goal.** Turn a compose file that "boots on a good day" into one a stranger can
trust: write structural checks over the parsed YAML (pins, healthchecks, dependency
conditions, published ports), watch them fail on the shipped `docker-compose.yml`,
then fix its wiring until the whole suite is green. Then do it again for the
`docker-compose.secure.yml` overlay — the profile you'd run on a host that isn't
your laptop. Then write the preflight for the half of the system compose cannot
see: the model, which runs on your machine.
**Prerequisite.** The capstone service (workshops/assistant) — both app containers
build from its image; this lesson packages it, no new agent logic. Ollama installed
**on this machine** with `qwen3.5:9b` and `nomic-embed-text` pulled.
**Effort.** ~45 min to green on the fast tests · no integration tier · ~75 min realistic first pass.

## Do this

```bash
make setup && make test            # 27 failing tests — read them, they are the spec
$EDITOR src/health.py              # TODOs 1-6: the structural review
$EDITOR docker-compose.yml         # fix what your own checks catch
$EDITOR src/health.py              # TODOs 7-8: review the secure overlay too
$EDITOR docker-compose.secure.yml  # then fix that
$EDITOR src/preflight.py           # TODOs 1-9: the dependency compose cannot start
make check                         # green: ruff + pyright + pytest, all offline
```

## What the first failure means

`test_every_service_the_stack_needs_is_wired` fails because `missing_services`
isn't built. It hands you parsed YAML (via the given `load_services`) and wants the
names from `REQUIRED_SERVICES` that aren't there. That one passes quickly — the
teeth are in the next five: pinned image tags, a healthcheck on every service,
`depends_on` that waits for *health* rather than start, and only the assistant
publishing a port. The shipped compose file violates all of them, on purpose.

Then four failures about `docker-compose.secure.yml`, which is currently security
theatre: the JWT secret is committed, rate limiting and concurrency caps are
commented out, and the port is still on every interface. Same rule as the rest of
the lesson — a control that exists only as a comment does not exist, and a check
that passes on one is not a check.

## The dependency that is not in the file

`REQUIRED_SERVICES` has three entries, not four. The model is not one of them: it
runs on your machine, and the assistant reaches it at `host.docker.internal:11434`.
That is not a shortcut, it is where the GPU is — Docker Desktop passes none through,
and the same 9B measured **0.52 tokens/second** in a container against **81** on the
host. A container is a good place to pin a dependency and a bad place to run
inference on a laptop.

What it costs you is everything `depends_on` was doing. Compose cannot start Ollama,
cannot health-gate on it, and will happily bring the stack up against a daemon that
isn't running — after which every answer comes from the offline stitcher and every
probe stays green. `src/preflight.py` is what replaces it, and it is where the
lesson's sharpest idea now lives: **readiness is not presence**. `ollama list`
reports a file on disk. Loading a 9B takes longer than the composer's whole budget,
so a stack that treats "downloaded" as "ready" times out its own first question.
TODO 5 makes the model actually answer one token; nothing cheaper is evidence.

The preflight never pulls anything. A 5.6 GB download is the user's decision, and a
check that quietly starts one has stopped being a check. It prints the exact
`ollama pull` command instead — `test_every_failure_arrives_with_the_command_that_fixes_it`
holds you to that.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] Your checks catch the deliberately broken fixture in the test file — they
      review structure, not substrings.
- [ ] The fixed `docker-compose.yml` passes `compose_ok` — pinned images,
      healthchecks everywhere, `condition: service_healthy` dependencies, exactly
      one published port, and an assistant that can resolve `host.docker.internal`.
- [ ] The fixed `docker-compose.secure.yml` passes `secure_overlay_problems` — auth
      and load shedding actually set, the secret read from the environment, the
      published port bound to loopback.
- [ ] `python -m preflight` (from `src/`) reports every check against your own
      Ollama, and each failure names the command that fixes it.

## Stuck?

1. Parse once with `yaml.safe_load`, then walk dicts. A service pulls an image if
   it has an `image:` key; built services are exempt from the pin check — their
   pin is the Dockerfile. An image reference is `name[:tag][@digest]`, and two of
   its colons are not tag separators: the one inside `@sha256:…` and the one in a
   registry port like `localhost:5000/qdrant`. Split the digest off first.
2. `depends_on: [qdrant]` (list form) always waits for start only. The map form
   must carry `condition: service_healthy` — a started Qdrant is not a ready
   Qdrant. The reference wiring is in `../after/docker-compose.yml`.
3. An overlay only *replaces* the keys it names, so `merged_service` needs a
   shallow merge with `environment` combined key-by-key. `${VAR:?message}` is how
   compose reads a value from the environment and refuses to start without it —
   that indirection is the thing TODO 8 checks for.
4. `OLLAMA_HOST` means two different things and TODO 1 is about the collision. To
   the Ollama *server* it is a bind address (`0.0.0.0:11434` — where to listen); to
   every *client* it is a URL (`http://localhost:11434` — where to dial). A shell
   that exported the server's meaning will hand you `0.0.0.0`, and dialling that is
   a bug on some platforms and a silent wrong host on others. Normalise it before
   you use it, and never dial a wildcard.

No integration lane in `make check` — the tests review the YAML and drive the
preflight through fakes, so the suite stays offline. The real-world payoff is
`ollama serve` on your machine plus `docker compose up --build` from this folder:
capstone assistant + MCP server + pinned Qdrant, answering from your own GPU, zero
API keys.
