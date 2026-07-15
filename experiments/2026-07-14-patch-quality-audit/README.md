# Experiment: kernel patch quality audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-14-patch-quality-audit` |
| Status | `completed` for static checkpatch review; upstream review remains required |
| Scope | all 77 Linux 7.1.3 format-patch files in `patches/series` |
| Date | 2026-07-14 |

## Question

Do the current MT6797/Gemini patches pass Linux's own review-oriented static
checks, and which diagnostics need to be resolved before upstream submission?

## Method and safety

The audit runs the pinned Linux 7.1.3 `scripts/checkpatch.pl` with
`--strict --terse --show-types` against every patch listed by
`patches/series`. It is read-only: no patch, source tree, build output, device,
or firmware is modified.

Run it in the VM with:

```sh
./scripts/dev-vm run experiments/2026-07-14-patch-quality-audit/scripts/audit-checkpatch.sh
```

The script prints aggregate counts, diagnostics by patch, and the first 160
diagnostics for review. Its own shell syntax and ShellCheck status are recorded
separately from checkpatch findings.

## Interpretation

`checkpatch.pl` is a review aid, not proof of functional correctness. In
particular, `FILE_PATH_CHANGES` warnings for new DT bindings or drivers may
require MAINTAINERS updates, while line-length and prose warnings still need
human review. A clean result would not replace binding validation, compilation,
or hardware evidence.

## Evidence

- [Historical 71-entry audit](results/checkpatch-20260714.txt)
- [Current 74-entry audit](results/checkpatch-current-74-20260714.txt), which reports 10 missing sign-offs, 60 warnings, and 11 checks; patches 0072–0073 add the two new sign-off blockers.
- [Current 74-patch review action plan](results/review-action-plan-current-74-20260714.md), which separates DCO/provenance blockers from binding, ownership, commit-message, and style cleanup.
- [Current 74-patch provenance audit](results/patch-provenance-current-74-20260714.txt), which detects placeholder authors, synthetic zero object IDs, and missing sign-offs without exposing email addresses.
- [Current 77-patch checkpatch audit](results/checkpatch-current-77-20260714.txt), which reports 10 errors, 64 warnings, and 18 checks; patch 0075 adds the new driver/binding review findings.
- [Current 77-patch provenance audit](results/patch-provenance-current-77-20260714.txt), which adds the 0075 placeholder object to the existing provenance blockers.
- [Current 74-patch W=1/sparse compile](results/series-static-compile-current-74-20260714.txt), which checks all 23 kernel subsystem directories touched by C sources in the series, including `drivers/spi` for patches 0072–0073.
- [Current 74-patch integration result](../2026-07-13-kernel-integration/results/mainline-74-patch-current-20260714.txt)
- [Gemini-only DT schema validation](../2026-07-14-first-boot-probe-audit/results/gemini-dtb-schema-validation-20260714.txt)
