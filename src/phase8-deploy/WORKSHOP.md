# Workshop · Deployed stack

Workshops 2–8 are one assistant. This phase is six folders, then the defect lab. Finish one folder before you open the next.

Read [How to work with workshops](../workshops/README.md) first. The map of the finished system is [`WORKSHOP-DEPLOYED-STACK.md`](../workshops/assistant/phases/WORKSHOP-DEPLOYED-STACK.md).

In each folder: `make setup`, then `make test`. Diff only the files that folder names, against its own `after/`.

1. `src/workshops/assistant/phases/08-trace/before` — edit `observe.py`, `cache.py`, `usage.py`. First failure: `test_wrapping_the_registry_traces_every_tool_without_editing_any_tool`.
2. `src/workshops/assistant/phases/08-corpus/before` — edit `adapters.py`. First failure: `test_reingesting_the_same_source_updates_instead_of_accumulating`.
3. `src/workshops/assistant/phases/08-reliability/before` — edit `deadline.py`, `resilience.py`, `idempotency.py`, `outbox.py`, `approvals.py`. First failure: `test_a_bug_is_not_retried_three_times`.
4. `src/workshops/assistant/phases/08-service/before` — edit `service.py`, `api.py`, `core.py`, `composers.py`, `connectors.py`, `output_gate.py`, `audit_log.py`. First failure: `test_health_reports_the_offline_tier`.
5. `src/workshops/assistant/phases/08-auth/before` — edit `auth.py`, `oauth.py`. First failure: `test_without_a_key_source_the_zero_key_demo_path_stays_open`.
6. `src/workshops/assistant/phases/08-evidence/before` — edit `report.py`. `release.py` and `evidence.py` are already finished. First failure: `test_build_portfolio_is_still_the_page`.
7. Defect lab, in `src/workshops/assistant/after`. Brief: [`WORKSHOP-DEFECT-LAB.md`](../workshops/assistant/phases/09-defect-lab/WORKSHOP-DEFECT-LAB.md). Copy `phases/09-defect-lab/test_regressions.py` over the reference tests, then run `make defect-lab`.
