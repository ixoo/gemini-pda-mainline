# Per-case decoder attribution after attempt 2

Prepared correction, not a third execution. Both refused attempts and all
original diagnostics remain immutable. The 25 DTS fixtures, two binding inputs,
expected full-validity outcomes, time/file/capture budgets and cleanup policy
remain unchanged. No malformed-byte expectation is changed to success.

## Why schema validity alone was insufficient

In the exact dtschema 2026.6 wheel, SHA-256
`95c29a26d875e8fb6c4d3f63152cd6ebb88ecb0cb731e937decc6f78290d0213`,
`dtb.py:prop_value` attempts unpacking as the selected type. On a uint32 unpack
error it prints a size diagnostic, then falls back to uint16/uint8 when the raw
property contains two/one bytes. A single decoded value is returned as a sized
integer. Thus the raw one-byte `01` can become the numeric value 1 despite the
uint32 diagnostic; the binding's const check reports no error for that decoded
value. This matches the [retained attempt](ATTEMPT_2.md); it is not proof that
the raw DT property is valid.

The corrected child requires exact installed source bytes for these reviewed
modules, before and after its operation:

| dtschema module | SHA-256 |
| --- | --- |
| `dtb.py` | `93f07555d95c3850f23faae8226512c30c1f896bc0e452766f3afa32d2814b54` |
| `validator.py` | `c18a2356934d4bd5c6018646dc4c83754e5ddfb0d110e84b7518ada82e23af56` |
| `__init__.py` | `c3dc9040f30f37e6da33b34c5498a2b23fc630ce36225cd451ed3b410244788b` |

These were reviewed from the hash-verified primary wheel in memory, with no
backend operation, package installation or persisted source. Existing pinned
schema Python, setup and libfdt checks remain required. A mismatch refuses.

## Three separately recorded observations

For each exact fixture/variant, [compare.py](compare.py) now records:

1. **Raw property:** libfdt locates `/infracfg@10001000` and reads `#reset-cells`
   before schema decoding. Presence, byte count and hexadecimal value must
   equal the pinned DTS input. Absence is not a raw-width error; the variant's
   schema decides whether absence is allowed. A present cell must be four bytes.
2. **Decoder diagnostics:** capture stderr only around that fixture's actual
   `decode_dtb` call, capped at 4096 characters. For the raw string (`31 00`)
   and raw byte (`01`) fixtures, require exactly their one size-2/size-1 uint32
   diagnostic, with property, node and raw size attached to that same row.
   Other fixtures require empty decoder stderr. Exceptions still fail the child;
   arbitrary runtime errors, missing/extra warnings or wrong sizes are refused.
3. **Decoded-schema validity:** retain actual `iter_errors` output, with its
   original messages, validators and schema/property paths. This field is true
   exactly when those decoded-schema errors are absent. It is never renamed
   into full DTB validity or forced false to manufacture a YAML rejection.

The row's full `valid` value requires correct raw width, no decoder diagnostics
and no decoded-schema errors. The parent independently recomputes these predicates
and compares the unchanged expected outcome matrix. The byte case therefore may
retain `decoded_schema_valid=true` while full validity remains false. The two-
cell and boolean forms likewise retain their distinct raw-width and schema
findings. Decoder messages outside the per-case capture still reach the outer
stderr guard and refuse the run. There is no general stderr whitelist.

The four former aggregate size messages cannot by themselves establish a
per-case runtime receipt. Only a newly admitted execution of these captures can
supply that evidence. The original refusal is not reclassified.

## Legitimate compound schema diagnostics

The unknown-property fixture deliberately omits reset cells. Its mandatory
schema must report both the `additionalProperties` error for `unreviewed-property`
and the exact `then/required` error for `#reset-cells`. Its optional schema must
report only the additional-property error. The classifier now requires those
complete sets, without dropping either error. Duplicate, missing, wrong-node,
wrong-property or other extra diagnostics remain refusals.

## Host review evidence and admission

[test-decoder-attribution.py](test-decoder-attribution.py) consumes the exact
retained 50 decoded-schema rows and their aggregate stderr, verified by hashes.
It preserves every schema error and original decoded-validity value, then uses
explicitly synthetic per-case raw/capture records derived from pinned DTS bytes
and audited fallback behavior. Their concatenation matches the retained stderr
exactly. This is a host classifier test, not a claim that the previously
unlabelled messages were individually captured on Buildbox.

[Twenty unsafe attribution cases](decoder-attribution-refusals.json) reject
missing/unlabelled captures, false full validity, changed raw bytes/width,
wrong property/node/size, extra messages/crashes, erased compound diagnostics
and capture overflow. The existing 24 comparison/process/scratch and 17 dtc-chain
refusal tests still pass. No DTS, decoder or schema tool was rerun for these
host tests. Root must independently review this correction and assign a new
exact published revision/window before any third backend run.
