# Workshop · Harden the assistant  (ends Phase 6)

Armor the assistant against the attack catalog. The bar is **containment**: a
landed injection may produce junk text, but must never fire a gated tool or leak PII.

## Deliverables
- [ ] `screen()` runs on every input AND every fetched email/news page
- [ ] Untrusted content is `spotlight()`-ed as data, not instructions
- [ ] Encoded (base64) injections are caught after decoding
- [ ] PII is redacted on input and blocked on output (`output_ok`)
- [ ] An indirect injection in an email cannot fire a gated tool without approval

Implement `guardrails.py`. Tests: `tests/test_guardrails.py`.
