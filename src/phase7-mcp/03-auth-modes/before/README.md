# 7.3 Auth modes

**Goal.** Pick the right auth mode per deployment (none/bearer/OAuth 2.1+PKCE) and validate tokens correctly, twice: a policy tier in `src/auth.py` (which checks a resource server runs, and why) and a cryptography tier in `src/jwt_auth.py`, where PyJWT verifies actually-signed tokens (signature, expiry, audience, scope) behind a `BearerGate` guarding a lesson-5.2-style tool handler.
**Prerequisite.** 7.2 REST → MCP (the gate wraps the kind of tool handler you built there).
**Effort.** ~45 min to green on the fast tests · no integration tier · ~75 min realistic first pass.

## Do this

```bash
make setup && make test     # 13 failing tests — read them, they are the spec
$EDITOR src/auth.py         # recommend, validate, call_upstream_correctly (policy tier)
$EDITOR src/jwt_auth.py     # validate_jwt + BearerGate (real PyJWT crypto tier)
make check                  # green: ruff + pyright + pytest, all offline
```

## What the first failure means

`test_recommendations_map_to_trust_boundary` fails first: `recommend` raises `NotImplementedError`, so the deployment-to-auth-mode mapping (personal → none, team → bearer, public → oauth2.1+pkce) doesn't exist yet. That's the warm-up; the weight of the lesson is `validate`/`validate_jwt` — expiry, the wrong-audience trap (RFC 8707), and scope checks — and the confused-deputy rule in `call_upstream_correctly`: never forward the client's token upstream.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] `test_a_token_for_another_server_is_rejected` passes: a real signed JWT minted for a different audience is refused with a reason naming the audience — the check that makes token passthrough fail loudly.
- [ ] The three `BearerGate` tests pass: valid Bearer flows through to the tool, missing or bad tokens come back as `{"error": "unauthorized: <reason>"}` — data, not an exception, because an MCP client reads tool results.

## Stuck?

1. In `jwt_auth.py`, don't re-implement the checks PyJWT already does: `jwt.decode(token, key, algorithms=["HS256"], audience=audience)` verifies signature, expiry, and audience in one call. Your only hand-rolled check is scope.
2. Catch PyJWT's *specific* exceptions and translate them: `ExpiredSignatureError` → `"expired"`, `InvalidAudienceError` → an audience reason, anything else → `"invalid token"`. The `"scope"` claim is one space-separated string — split it and look for `required_scope`; missing → `"missing scope"`.

No integration lane: HS256 needs a shared secret, not a network — the fast tests already mint and verify real signed JWTs offline.
