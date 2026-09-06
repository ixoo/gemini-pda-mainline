# Independent producer-audit freeze

Declared after the two bounded retrieval batches and before verifier construction.
Canonical encoding: JSON sorted keys, ASCII escapes, comma/colon separators,
UTF-8 bytes, SHA-256; source tuple array sorted by `source_id`.

| Immutable value | Literal SHA-256 |
| --- | --- |
| All 19 complete source tuples | `0e4a8b43331146d936b3c3c16f06d28cf5e9331a01a76b3435a119e944a707d4` |
| All citation anchors | `934b2dfbb3783770e1f2acd181ca007ea501301a2300b1df4977bc755f6e13c0` |
| Complete search/request record | `f57631177704a9b2d9d511ff153c2b9598723c8737d13148217cecfb1aab8151` |
| Complete verdict record, including prose | `9f7adc450d74c7cc9f760fac536a1ab4b2bd089060ee92671556fb9d2847009f` |

These are independent literal expectations, never generated from mutable inputs
at verifier startup. The verifier also pins the eight inherited local-file
identities in [inputs.json](inputs.json) and compares all 13 inherited source
tuples field-for-field against their appropriate immutable predecessor.

The direct predecessor supplies ten tuples. Its builtin predecessor supplies
the additional connectivity/common Makefiles and `init.h`; both predecessor
four-file sets retain their previously accepted whole-file hashes. The new
request record includes every success, the empty failure/reread budgets,
predeclarations, four bounded no-hits and the stub-presentation limitation.
No source bodies or excerpts are part of this freeze.
