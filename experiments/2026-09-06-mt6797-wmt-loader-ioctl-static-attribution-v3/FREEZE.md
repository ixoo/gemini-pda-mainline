# Independent fresh v3 freeze

Declared after the single fresh batch and before verifier construction.
Canonical encoding: JSON sorted keys, ASCII escapes, comma/colon separators,
UTF-8 bytes; SHA-256.

| Immutable record | Literal SHA-256 |
| --- | --- |
| Complete inputs | `1c94495b7e6fbc0faa3641d7e6c6f2c12806f8c2f920efd8dcdcbae9b4fbd8df` |
| Binary anchors plus inherited source citations | `850a5d0520ac9c8ccbd78dca9df872930c277c495c2d9966966daaa1592cb133` |
| Complete analysis/declaration/receipts | `1daad911f3b3527590d80ab110d98d40083eab07004ca5555d6bc5647a72df97` |
| Complete verdicts | `a85468a71102136da837cc27b2662016dc87b90059e28c236925f9ab6a2d1226` |

The anchor object has keys `binary` and `source`, populated respectively from
`anchors` and `inherited_source_citations` in verdicts.json. Expected digests
are literal constants; they are never derived from mutable evidence at startup.

All four accepted source-predecessor files were freshly compared against their
paths at the frozen parent commit. The verifier separately pins those file
hashes and compares the three inherited source tuples and four inherited
citations field-for-field. V1/v2 partial output is not an input.

The frozen analysis record includes the complete six child receipts, one
controller receipt, exact prospective intervals, fresh counts and two selected
literals. Raw responses are represented by hashes/lengths only, not retained
instruction listings, binary bytes or function dumps. The host-launcher warning
note is kept separate from the zero static-analysis-tool diagnostic count.
