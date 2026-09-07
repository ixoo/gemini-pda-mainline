# Frozen fresh-run evidence

Execution HEAD: `f35c050cff62de6278e7788cad0ff775587fb0c9`.

Loader and method freeze: `2026-09-07T01:06:19Z`, before private content.
Single guarded run:
`2026-09-07T01:07:09.223614Z–2026-09-07T01:07:10.261116Z`.
Result JSON freeze: `2026-09-07T01:09:15Z`, before verifier creation.

| File | SHA-256 |
| --- | --- |
| [inputs.json](inputs.json) | `c5dffb7323e7eb25626704d3310565b1ca9252e0dd9f349eff66ed04fc3d4e31` |
| [loader.json](loader.json) | `54763f55f63b12fd47e32931c13f6fe7f617d807a161da9f77e223abc4f43557` |
| [method.json](method.json) | `9b4ce1dfe5773c2264ebe302ea17b62fb502793589e05dc6243ac753adbdc51c` |
| [analysis.json](analysis.json) | `e1ebec2e0080d70fd8e5e0d59801d20c874821f25f99c3a4e62d5effd35652ea` |
| [intervals.json](intervals.json) | `e44de0d978edbaaccc5f5d05afc5fc913bd691c2ab56e2e03c02edbc23ebef0c` |
| [verify.py](verify.py) | `e757e180b623290ee095f16e66bbccb605ea1ea372ee86375804bcc96d212204` |
| [WORK_ITEM.md](WORK_ITEM.md) | `3351a2b6222cf449a4111c0cd4e15cbd2d637f00abdd38698f63c971052eb4a4` |
| [AMENDMENT.md](AMENDMENT.md) | `104efd97a0d6eee2c41a0e897c852c6d95e40d7232152adc12cb39b291db6a27` |
| [PREFLIGHT.md](PREFLIGHT.md) | `971549ace77fbb58b04cd37c8884c2c4c73ceca686923b01c86d688366de03cc` |

The five JSON hashes are also pinned in the assert-free verifier. Its normal
and optimized modes verify the same evidence; mutation tests use in-memory
copies and never rerun the parser. Predecessor records are identity-checked
only. The original excluded attempt's tuples and raw output were not used.

The raw stdout/stderr/parser-log hashes are in [analysis.json](analysis.json).
Only bounded sanitized metadata is published; raw evidence remains private.
The process-scoped filesystem limitation and separate collector output writes
are explicit in the loader, analysis and [validation record](VALIDATION.md).

The source-only sentinel ruling narrows the documentation to the enumerated
read/use operations; unsupported mutations fail naturally and were not
separately counted or fault-injected. No frozen JSON or executable was changed.

Review-ready UTC: `2026-09-07T01:27:13Z`.
