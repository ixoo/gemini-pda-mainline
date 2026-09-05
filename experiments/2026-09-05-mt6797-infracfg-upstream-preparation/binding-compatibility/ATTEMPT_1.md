# Compatibility attempt 1: diagnostic guard refusal

The single admitted run at main
`1e2d7e05ea29dcb17573756837d89b44bd3b1ea3` stopped **REFUSED** after 28.597
seconds, with outer exit status 1. There was no retry or input change.
[Execution](results/attempt-1-1e2d7e05/execution.json) records the 1000-second
outer timeout and five-second forced-kill grace.

Fresh publication verification and full pre-run source integrity passed. Both
mandatory/optional bindings passed their meta-schema tools and were processed
successfully. Four simple DTS cases compiled cleanly. The fifth, `mt6797-two-cells`,
compiled with exit zero and these two diagnostic kinds:

- `resets_is_cell`: the fixture's `#reset-cells` is not a single cell;
- `resets_property`: its `resets_is_cell` prerequisite failed.

The [exact diagnostic](results/attempt-1-1e2d7e05/dtc-mt6797-two-cells.stderr)
identifies the expected fixture and node. The reviewed runner allowed one warning
named `reset_cells_is_cell`, so it refused this actual compiler output. This
is a protocol warning-name/count mismatch. It does not establish a binding or
compatibility failure. The 50-row schema comparison never ran; none of its
expected outcomes can be promoted to a result. All 11 commands returned zero,
with no timeout, truncation, TERM/KILL or surviving process group; the parent
classification then stopped the run.

The [original receipt](results/attempt-1-1e2d7e05/result.json) is preserved unchanged,
SHA-256 `96b4dbfb80bc218c2502b6061b57dd1a6401d0b89bf63f8fd00d46ca1bdc460d`.
[Fetch review](results/attempt-1-1e2d7e05/fetch-review.json) verifies the exact
23 original regular receipt/log files, 18,976 bytes total, and all command-log
hashes before/after transfer. Each file was below 256 KiB and their aggregate
below 1 MiB. No source, generated DTB or processed schema was fetched.

[Post-run checks](results/attempt-1-1e2d7e05/post-run.json) confirmed removed scratch,
retained exact ownership marker, clean exact managed project checkout and
independent normal-lock reacquisition/release. The failure-path checks confirmed
all 11 source and 9 build file pins, old processed-schema hash and retained tools
unchanged. The full *post*-run source-tree scan was not reached; this result must
not be described as complete before/after full-tree verification.

The original six-patch tree/results, kernel build and device were not changed.
The backend window is released. Root must review the diagnostic evidence and
any narrowly corrected guard/refusal fixtures before admitting another run.
The original protocol and this refusal receipt remain immutable historical
inputs; no automatic rerun or schema acceptance is implied.
