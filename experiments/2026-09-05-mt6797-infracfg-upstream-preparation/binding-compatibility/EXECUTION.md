# Exact focused compatibility execution proposal

Prepared for integrator review; **no backend window or schema execution has
occurred**. [run-fixtures.py](run-fixtures.py) defaults to a plan-only message.
It reuses the existing [schema collector](../scripts/schema-check.py) and its
process-group cleanup, stream ceilings, generated-file limit, interruption and
atomic receipt publication. It adds no generic validation or process framework.

## Admission and inputs

Root must assign one exclusive, bounded Git-based window after publishing the
exact clean project revision. Use its managed Buildbox checkout and full
published branch ref. The runner verifies checkout identity/cleanliness, exact
origin and a fresh advertised ref equality with no stale fallback; it takes the
existing nonblocking normal Buildbox lock. A busy lock or unavailable/moved ref
refuses. Root must first check host/backend space and create the explicit evidence
parent `/workspace/gemini-pda/artifacts/binding-compatibility`; no other worker
may mutate the backend during this window.

The inherited [source/tool contract](../schema-contract.json) and
[accepted retained tool receipt](../results/schema-attempt-2-f4ff1028/result.json)
remain exact. Require identical tool versions/hashes, the setup marker and
pylibfdt identity in the schema Python environment. Retained built dtc is
`1.7.2-g53373d13`, SHA-256
`918bd1e8ee0ac2f08210e16eedc6486f6daa4872a108c9a4cc8f1b78422301a5`.
The runner does not install or fetch tools. The actual dtschema 2026.6 Python
API was inspected from its primary distribution wheel, SHA-256
`95c29a26d875e8fb6c4d3f63152cd6ebb88ecb0cb731e937decc6f78290d0213`.
No wheel or Linux source was persisted by that host review.

Before and after, verify the inherited 11 source/9 build pins and full retained
source integrity `90923e5fb4d9bf2db35049abb6011437bc334aeedc528f099591f6198e9fc7aa`.
The original processed schema must keep SHA-256
`a3265d87a3617c19c3463fb3a728df2120b8932ee0be686dcd8c4f69fac82b38`.
Neither it nor the original six-patch tree/build/results is modified.

Copy only the exact mandatory binding into private scratch. Its SHA-256 is
`83e13fddec7a39f2f6cc95408e9f3c4389fe55c9d33dfd635105d36c52c2979a`.
Remove the one uniquely anchored conditional enum entry and require the optional
binding's complete SHA-256
`0610f891e326d1e0a7ce9ffe3ef0513ab229bf37eee8177de0999cac17157c6f`.
[The host input-derivation check](schema-input-derivation.json) confirmed exact
byte equality with pinned upstream; it did not execute a schema tool.

## Narrow execution and classification

Process only these two YAML copies with the retained `dt-doc-validate` and
`dt-mk-schema -j -o` tools. This supersedes the earlier prospective make-based
step: no `make`, full `dt_binding_check`, `dtbs_check`, new source extraction or
old processed-schema rewrite is required for this focused comparison. Standard
dtschema core dependencies come from the retained tool environment.

Compile the 25 pinned [DTS cases](fixtures.json) once with retained dtc. Only the
single, exactly attributed `reset_cells_is_cell` warning is allowed for the
four malformed-cell forms; unexpected diagnostics or nonzero compiler exit
refuse. Positive cases must compile without diagnostics. Retain each DTS/DTB
hash and every command's bounded stdout/stderr/status, including expected warnings.

[compare.py](compare.py) loads both processed schemas through actual
`dtschema.DTValidator`, decodes the same DTBs, requires the one expected node and
matching schema selection, and collects actual `iter_errors` results. It does
not reimplement JSON Schema rules. Each of the 50 rows records variant, fixture,
node, compatible, DTB digest, validity and structured schema/path/validator/message
attribution. The parent checks processed-file identities, fixture/DTB identities
and the complete comparison. Only old MT6797 omission may change outcome.
Unexpected schema/node/property, missing/duplicate rows, no attributed diagnostic,
crash, decoder warning, timeout or truncated output refuses. A process exit status
alone cannot establish rejection. All expected negative diagnostics are retained.

Successful collection ends at `COLLECTED_REVIEW_REQUIRED`; the integrator must
review all results before accepting compatibility or admitting downstream work.
A refusal preserves the receipt/logs and requires review before another attempt.
Nothing runs a kernel, QEMU, driver lifecycle or device transition.

## Resource limits and cleanup

Use one outer 1000-second timeout plus five-second forced-kill grace around the
pinned schema Python invocation. There are at most 33 guarded commands: one
publication read; two 180-second source-integrity scans; four 30-second schema
commands; 25 five-second dtc calls; one 60-second comparison. Inherited tool
version probes each have five-second timeouts. Each child group has five-second
cleanup grace, no core dumps, a 128 MiB generated-file ceiling, and separate
256 KiB stdout/stderr ceilings. Fixture DTBs must be at most 64 KiB. Require
512 MiB free at both managed scratch and evidence parents; two maximum processed
files plus logs/fixtures fit below that headroom.

The fixed private owned scratch directory is
`/workspace/gemini-pda/tmp/infracfg-binding-compatibility`. Under the shared
lock, validate its marker/uid/mode and reject symlink/unknown paths before
removing a recognized stale `run`. Cleanup is installed before source creation.
Success and handled failures remove `run`, retaining only root/marker. SIGKILL
leaves recognizable scratch for the next separately admitted run; it does not
permit overwriting the prior evidence. Evidence is exclusive-create beneath
its exact revision, never replaced or opportunistically deleted. Source/tool
preservation checks run even after failure; interrupted/unproven cleanup cannot
be accepted. Record independent post-run lock reacquisition before handoff.

After admission, wrap this invocation with the stated outer timeout, substituting
the exact published revision/ref in the exact managed checkout:

```sh
SCHEMA_PYTHON=/workspace/gemini-pda/cache/validation-tools/schema-2026.6/bin/python
timeout --kill-after=5 1000 "$SCHEMA_PYTHON" -B \
  experiments/2026-09-05-mt6797-infracfg-upstream-preparation/binding-compatibility/run-fixtures.py \
  --execute "$REVIEWED_REVISION" --published-ref "$REVIEWED_REF"
```

Fetch only reviewed bounded logs/receipts after preservation and cleanup review,
not a source/object/processed-schema tree. A later result should pin the runner's
published revision, all command argv/budgets, tool/input/output identities and
comparison outcomes, keeping hardware and original topic results separate.

## Host refusal evidence

[test-comparison.py](test-comparison.py) directly exercises the actual classifier,
diagnostic guard, inherited command-admission guard and scratch helper. Its
[24 refusal cases](comparison-refusals.json) cover identity reuse/omission,
reversed expected outcome, unattributed/wrong schema/node/property diagnostics,
wrong input bytes, command failure/overrun/live group and unsafe scratch. An
exact synthetic 50-row table and recognized stale cleanup pass. These are host
fixtures; they establish neither dtschema decoder outcomes nor a backend result.
