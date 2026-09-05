# Focused compatibility attempt 3: collected for integration review

One separately admitted execution used exact published main
`003e552ec598061cb711e321bb39a36fab846079` and `refs/heads/main`, after independent
review of the [decoder-attribution correction](DECODER_ATTRIBUTION.md).
The runner returned zero after 42.074 seconds and published
`COLLECTED_REVIEW_REQUIRED`. This is the completed worker handoff; integrator
acceptance remains separate. No further execution is admitted.

[Attempt 1](ATTEMPT_1.md) and [attempt 2](ATTEMPT_2.md), including their original
receipts and refusals, remain unchanged. This run adds actual per-case decoder
capture and raw-property attribution; it does not reclassify the earlier runs.

## Exact execution and observed comparison

[Original receipt](results/attempt-3-003e552e/result.json), SHA-256
`43f2fd0d1f12c06c898886f62b4471baaee2d3ddddf53fd4d48e4f21c158b582`.
[Original comparison](results/attempt-3-003e552e/compare.stdout), SHA-256
`a76eb9783e0d03adf231bcd04ec3f086b3269e13ea0a108f600e36e6e71b6c66`.
[Outer execution](results/attempt-3-003e552e/execution.json) records one invocation,
1000-second timeout and five-second kill grace.

All 33 guarded commands returned zero without timeout, signals or a remaining
process group: fresh publication check, two full source-integrity scans, four
schema commands, 25 DTC compilations and one comparison. The prescribed
128 MiB generated-file and separate 256 KiB log limits remained unchanged.
Both binding meta-schema checks and processing commands emitted no diagnostic.
The four malformed DTC cases emitted their exact reviewed warning chains.

The 50 unique comparison rows retain these observed outcomes:

| Case | Mandatory variant | Optional variant |
| --- | --- | --- |
| Old MT6797 without reset cells | required-property rejection | full validity passes |
| New MT6797 with one reset cell | passes | passes |
| Raw byte `01` | decoded-schema validity true, raw width false, exact size-1 decoder error, full validity false | same |
| Raw string `31 00` | raw width false, exact size-2 decoder error, const rejection | same |
| Unknown property with reset cells omitted | both additional-property and required-property errors | additional-property error |
| Other malformed MT6797 forms | rejected | rejected |
| Eight other listed compatibles | omission rejected; one reset cell accepted | same |

Only the old MT6797 omission changes full outcome: 9/25 mandatory rows and
10/25 optional rows pass. All four decoder diagnostics now belong to the exact
fixture/variant; the outer comparison stderr is empty. No schema error is
invented for the byte fallback. The installed decoder-module hashes match the
audited pins. Processed hashes are recorded in the comparison and verified by
the parent while scratch exists.

[Offline review](results/attempt-3-003e552e/offline-review.json) checks the complete
expected matrix, all 25 DTS/DTB identities across both variants, all command
log hashes and both source-integrity outputs. Every actual schema error and
decoded-schema validity value agrees with attempt 2; the new evidence is the
raw/capture attribution and successful guarded full comparison, not changed
schema outcomes.

## Preservation, cleanup and fetch

[Preflight](results/attempt-3-003e552e/preflight.json) independently acquired and
released the existing nonblocking lock and found 282390851584 bytes free at both
exact managed scratch/evidence parents. The revision's evidence directory did
not exist. Managed project preparation used Git fetch/clone only, with exact
origin and clean revision checks. No Linux source-tree copy or tool installation ran.

Both full retained-source scans returned
`90923e5fb4d9bf2db35049abb6011437bc334aeedc528f099591f6198e9fc7aa`.
The final source/build pins, tool identities and original processed schema were
preserved. A [separate post-run check](results/attempt-3-003e552e/post-run-review.json)
rechecked those files/tools, verified scratch `run` absent and its owned marker,
verified the exact project checkout clean, and reacquired/released the existing
lock. It did not claim an additional full-tree scan beyond the runner's two.

The bounded [fetch inventory](results/attempt-3-003e552e/fetch-review.json) contains
67 original files totaling 75720 bytes, each below 256 KiB. All transferred sizes
and hashes match; receipt and comparison hashes also match the independent
post-run inventory. These original logs/receipt are published byte-for-byte,
including empty logs. The five separate host review records identify preflight,
outer execution, post-check, fetch and offline review. No DTB, processed schema,
source, object, kernel image or private device evidence was fetched.

## Scope

This focused binding comparison executes schema/DTC tools, not a kernel or
hardware. No kernel build, QEMU, device, firmware, partition, radio, CONN or
CPU action occurred. No original six-patch topic, manifest, kernel source,
build output or earlier result was modified. Root may review the completed
compatibility evidence before any revised topic generation or other admission.

Publication checks passed for 74 scoped files: common repository checks (190
profiles; unchanged metadata debt 37), JSON/link review, diff checks and
file-by-file sensitive-data exclusions. No artifact path is staged. The common
checker adds no kernel build, checkpatch, DT execution or device result to the
separately recorded focused run above.

## Independent integration acceptance

Project Planning independently verified all 67 original file sizes/digests,
all 33 command outcomes, log digests and ceilings, both source-integrity outputs,
and the original result identity. It reparsed all 50 rows with the reviewed
classifier, checked every DTS and DTB identity, and compared every decoded-schema
error and validity result against the unchanged second attempt. The four
per-case decoder diagnostics and 9/10 full-validity counts match the contract.
The separate post-run record confirms preserved pins/tools, clean checkout,
removed scratch and released lock; root did not repeat backend access.

The focused DTB/schema comparison is accepted. Only old MT6797 reset-cell omission
changes outcome. This supports preparation of the optional-binding reset topic;
it does not promote hardware support or authorize another backend/device run.
The original `COLLECTED_REVIEW_REQUIRED` receipt and all previous failures remain
unchanged; this section is the separate integration decision.
