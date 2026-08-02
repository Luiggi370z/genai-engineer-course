# 8.1 Compose

**Goal.** Turn a compose file that "boots on a good day" into one a stranger can
trust: write structural checks over the parsed YAML (pins, healthchecks, dependency
conditions, published ports), watch them fail on the shipped `docker-compose.yml`,
then fix its wiring until the whole suite is green. Then do it again for the
`docker-compose.secure.yml` overlay — the profile you'd run on a host that isn't
your laptop.
**Prerequisite.** The capstone service (workshops/assistant) — both app containers
build from its image; this lesson packages it, no new agent logic.
**Effort.** ~45 min · moderate.

## Do this

```bash
make setup && make test            # 11 failing tests — read them, they are the spec
$EDITOR src/health.py              # TODOs 1-6: the structural review
$EDITOR docker-compose.yml         # fix what your own checks catch
$EDITOR src/health.py              # TODOs 7-8: review the secure overlay too
$EDITOR docker-compose.secure.yml  # then fix that
make check                         # green: ruff + pyright + pytest, all offline
```

## What the first failure means

`test_all_four_services_are_wired` fails because `missing_services` isn't built.
It hands you parsed YAML (via the given `load_services`) and wants the names from
`REQUIRED_SERVICES` that aren't there. That one passes quickly — the teeth are in
the next five: pinned image tags, a healthcheck on every service, `depends_on`
that waits for *health* rather than start, and only the assistant publishing a
port. The shipped compose file violates all of them, on purpose.

The last four failures are about `docker-compose.secure.yml`, which is currently
security theatre: the JWT secret is committed, rate limiting and concurrency
caps are commented out, and the port is still on every interface. Same rule as
the rest of the lesson — a control that exists only as a comment does not exist,
and a check that passes on one is not a check.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] Your checks catch the deliberately broken fixture in the test file — they
      review structure, not substrings.
- [ ] The fixed `docker-compose.yml` passes `compose_ok` — pinned images,
      healthchecks everywhere, `condition: service_healthy` dependencies, a model
      bootstrap on the ollama service, and exactly one published port.
- [ ] The fixed `docker-compose.secure.yml` passes `secure_overlay_problems` — auth
      and load shedding actually set, the secret read from the environment, the
      published port bound to loopback.

## Stuck?

1. Parse once with `yaml.safe_load`, then walk dicts. A service pulls an image if
   it has an `image:` key; built services are exempt from the pin check — their
   pin is the Dockerfile.
2. `depends_on: [qdrant]` (list form) always waits for start only. The map form
   must carry `condition: service_healthy` — a started Qdrant is not a ready
   Qdrant. The reference wiring, including the ollama model bootstrap, is in
   `../after/docker-compose.yml`.
3. An overlay only *replaces* the keys it names, so `merged_service` needs a
   shallow merge with `environment` combined key-by-key. `${VAR:?message}` is how
   compose reads a value from the environment and refuses to start without it —
   that indirection is the thing TODO 8 checks for.

No integration lane in `make check` — the tests review the YAML without a daemon.
The real-world payoff is `docker compose up --build` from this folder: capstone
assistant + MCP server + pinned Qdrant + Ollama, zero API keys.
