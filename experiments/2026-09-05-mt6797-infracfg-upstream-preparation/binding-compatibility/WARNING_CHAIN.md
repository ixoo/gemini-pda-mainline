# Narrow warning-chain correction after attempt 1

The [first refusal](ATTEMPT_1.md) remains unchanged. This correction changes only
the dtc diagnostic guard and its host fixtures/documentation. It does not change
DTS inputs, schemas, expected comparison outcomes, command budgets, process
containment, retained tools or preservation policy. No second execution is
admitted or performed.

The retained compiler's observed two-line stderr has SHA-256
`5b70bc81cdd4b35c69d2b72cb9930f67aa3d79a60b0869a3317d41b86092139d`.
The original guard incorrectly named the primary check `reset_cells_is_cell`
and omitted its dependent diagnostic. At the pinned upstream source,
[`scripts/dtc/checks.c`](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/scripts/dtc/checks.c)
SHA-256 `8e66cb4fb01f52e69b575290b9cc58dca621de55ab00ba19264b7379ed1b25de`,
`WARNING_PROPERTY_PHANDLE_CELLS(resets, ...)` creates `resets_is_cell` and
`resets_property`, with the former a prerequisite of the latter. `run_check`
emits the dependent check's failed-prerequisite diagnostic. The source was
reviewed through a bounded hash-verified public read, without backend execution
or persisted source.

The corrected guard requires exactly two complete lines for each of the four
malformed-cell fixtures. The primary line must identify the exact source file,
source-position syntax, `resets_is_cell`, `/infracfg@10001000`, `#reset-cells`
and the single-cell error. The second line must identify that same fixture's
output DTB, `resets_property` and failed prerequisite `resets_is_cell`. The
second line itself has no node text; attribution comes from its exact fixture
and prerequisite chain to the sole accepted primary node/property diagnostic.
It is not represented as independent node evidence. Both lines are required;
empty/missing warnings are refused for those malformed inputs. All other cases
must have no dtc diagnostics.

[The focused test](test-dtc-chain.py) replays the exact retained compiler output
through the actual guard. It also checks synthetic filename substitutions for
the other three malformed cases and a clean positive case. These substitutions
are guard tests, not observations of those cases on the backend.
[Seventeen unsafe variants](dtc-chain-refusals.json) reject missing lines,
duplicates, reordering, extra diagnostics, wrong file/node/property/check/
prerequisite, wrong fixture identity and incomplete framing. Existing 24
comparison/cleanup refusal cases still pass. No classifier rule or schema
outcome was relaxed to accommodate the compiler warning.

The coordinator must review this correction and assign a new exact published
revision/window before execution. The first result cannot be reclassified as
compatibility success, and later diagnostics may still produce a fresh refusal.

## Integration review

Project Planning reviewed the exact `36763b18` guard change against the retained
compiler stderr and independently reproduced the observed-chain replay, all
17 warning-chain refusals and all 24 existing comparison/process refusals.
The fixture/schema/comparison inputs and original attempt bytes remain unchanged.
The correction is accepted for one separately assigned bounded execution after
publication. It neither accepts the failed first attempt nor predicts the
remaining actual compiler/decoder outcomes.
