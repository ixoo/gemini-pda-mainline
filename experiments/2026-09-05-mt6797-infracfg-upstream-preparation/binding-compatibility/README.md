# Optional reset-cell compatibility correction

Preparation only: retain patch 3's two-ID header and omit its sole schema hunk.
No original patch, selected series, manifest or device candidate changes here.
The [input derivation](derive.py) consumes only exact original patch 3 SHA-256
`88e629b8a56aa892f43949bc052322efb38ba209df7b4d5c6a8d8df936c6fb03` and returns
its header Git diff byte-for-byte. It does not emit a replacement mail header,
claim a new Git commit identity, assign authorship or assert DCO certification.
A later admitted generation must produce an actual new format-patch and correct
its one-file/eight-insertion diffstat. Patches 1, 2, 4, 5 and 6 remain identical.

This is the minimal implementation of the accepted
[compatibility decision](../SUBMISSION_READINESS.md#smallest-binding-compatibility-correction).
The old input adds MT6797 to the conditional list that requires `#reset-cells`.
Omitting that change leaves the upstream binding byte-identical at
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c`, SHA-256
`0610f891e326d1e0a7ce9ffe3ef0513ab229bf37eee8177de0999cac17157c6f`.
The existing binding already accepts MT6797 and optionally permits reset cells
with value 1. Its other eight mandatory-compatible branches remain intact.
Do not remove MT6797 from the compatible enum or relax the property's value.

The two exported header IDs remain thermal 0 and PMIC-wrapper 1. Patch 6 still
adds `#reset-cells = <1>` to both in-tree MT6797 descriptions. It does not include
the new header, so there is no new compile-time DTS/header dependency. Old
schema validity is a compatibility claim, not proof of runtime behavior on every
old DTB or error path.

## Local derivation evidence

Run `python3 -B` on [test-derivation.py](test-derivation.py) from any directory.
[The recorded result](derivation-result.json) proves exact-input selection,
unchanged eight header lines and two IDs, absence of the schema diff, and three
changed-input refusals (extra bytes, renumbered ID and missing schema hunk).
It also checks the inventory of 25 prepared fixtures. It executes no schema
validator, DTS compiler, kernel, QEMU or backend command. No Linux source is
persisted or fetched by these checks.

## Focused schema plan, pending a separate admitted run

[Fixtures](fixtures.json) contain complete small DTS inputs and expected results:
old MT6797 without reset cells and new MT6797 with one cell pass; zero, two,
multiple cells, string, byte, boolean and unknown-property forms reject. Each
of the eight unrelated mandatory compatibles rejects omission and accepts one.
Malformed forms may trigger dtc warnings as well as schema diagnostics; retain
both and attribute the rejection instead of treating an arbitrary crash as a
successful negative test.

Use the existing pinned Linux source and dt-schema environment from the previous
schema attempt, after explicitly admitting the exact revised inputs. Do not
mutate the six-patch prepared tree. The corrected binding is the original pinned
upstream file, so a fresh full source extraction is unnecessary. Compare these
25 cases against both the currently proposed mandatory binding and the corrected
binding. Only `mt6797-old-absent` should change from rejection to acceptance;
all other expected outcomes must remain equal. This catches a missing correction
and accidental relaxation of values or unrelated required branches.

In that admitted window, validate the binding and build its processed schema
using the existing bounded `dt_binding_check` path. Compile each synthetic DTS
with the existing dtc, then use `dt-validate -s` with the exact processed schema
and binding filter `mediatek,infracfg`. Inspect complete bounded diagnostics:
zero exit status alone is not a pass because dt-schema may report validation
errors without a failing process status. Require attributed expected schema
rejections for negative cases and no selected-binding diagnostic for positives.
Retain tool versions, source/binding/processed-schema hashes, per-case DTS/DTB
hashes and exact stdout/stderr/exit outcomes. Missing output, decoding failure
without an attributed result, timeout, unexpected warnings or truncated output
is inconclusive/refusal, not expected rejection.

Reuse the reviewed 128 MiB generated-file ceiling and separate 16 MiB capture
limits of [schema attempt 2](../results/schema-attempt-2-f4ff1028/) where applicable;
set smaller explicit per-fixture caps in the eventual invocation. Full
`dtbs_check`, schema/QEMU repeats and device boots are not selected by this plan.
The two existing MT6797 DTBs must still be checked for one reset cell when a
revised topic is generated, and the five unaffected patch bytes compared to the
original topic. No new build or hardware support result is claimed here.

[The exact execution proposal](EXECUTION.md) now supplies the narrow runner,
structured comparison and refusal fixtures. It supersedes the prospective
make-based processing step above with direct retained schema tools on two small
copies. Backend execution still requires separate integrator review/admission.
