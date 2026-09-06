# Independent v2 static-attribution freeze

Declared after both fresh analysis batches and before verifier construction.
Canonical encoding is JSON with sorted keys, ASCII escapes, comma/colon
separators and UTF-8 bytes; digest is SHA-256.

| Immutable value | Literal SHA-256 |
| --- | --- |
| Complete inputs metadata | `b66fb7e2934fa1965754ca52e9b40d9b377f16e058ace6003c111fded8744bc2` |
| Binary anchors and inherited source citations | `9cd60ff515c67e6d99d558810efcdfc9d5d91bdb828f2045a233a0f78aee5af2` |
| Complete analysis/predeclaration/receipt record | `e6c02cdf79fccb0b91297988843a28b804e5aeaa8496a3432c1bbbde942a7317` |
| Complete verdict/semantics record | `0df00cda55346a7e0c539e880494d92efe922b9130de91a54936f8a53c8cfb02` |

The anchor object has keys `binary` and `source`, containing respectively the
`anchors` and `inherited_source_citations` values from verdicts.json. Expectations
are literal constants, not recomputed from mutable evidence at verifier startup.
All four predecessor whole-file identities in [inputs.json](inputs.json) were
checked against the frozen parent commit before reuse. The verifier independently
pins them and compares inherited tuples/citations field-for-field.

No v1 partial output, raw bytes, instruction listing, private path or complete
function dump is included. Raw-output hashes in the receipts identify transient
tool responses; their contents are not retained. Control-flow accounting contains
addresses/counts only and normalized prose, not an executable implementation.
