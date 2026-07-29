# Experiment: manifest profile-series invariant audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-28-profile-series-invariant-audit` |
| Status | `completed; violation confirmed; remediated 2026-07-29` |
| Subsystem | Repository patch/profile reproducibility |
| Device variant | Not applicable; repository-only audit |
| Date(s) | 2026-07-28 |
| Investigator(s) | Codex |
| Tracking issue | — |

## Question or hypothesis

Does every `patch_series` selected by `kernel/manifest.json` remain a
canonical-order subsequence of `patches/series`, as required by the repository
architecture?

## Provenance and environment

- Repository state: the worktree present on 2026-07-28; intentionally dirty
  ongoing experiment changes were inspected without modification.
- Inputs: `kernel/manifest.json`, `patches/series`, and every series referenced
  by a manifest profile.
- Tools: read-only `jq`, `awk`, `rg`, and ordered line comparison on macOS.
- Kernel, configuration, boot path, and device slot: not applicable.

## Safety assessment

The audit was repository-read-only. It did not build a kernel, access the
device, select a boot path, or write hardware. The resulting invalid-profile
classification must prevent selection; it does not authorize deleting
historical files or adding rejected patches to the canonical series.

## Audit method

No persistent script existed when the violation was discovered. The audit
used:

```sh
jq -r '.config.profiles | to_entries[] |
  select(.value.patch_series != null) |
  [.key, .value.patch_series] | @tsv' kernel/manifest.json

awk 'BEGIN { physical=selected=comments=0 }
  {
    physical++
    if ($0 ~ /^[[:space:]]*#/) comments++
    else if ($0 ~ /[^[:space:]]/) selected++
  }
  END {
    printf "physical=%d selected=%d comments=%d\n",
           physical, selected, comments
  }' patches/series
```

Each selected non-comment path in every referenced series was then compared
with the canonical path order. A profile passed only if every path occurred in
`patches/series` and its canonical position increased monotonically.

## Procedure

1. Parse `kernel/manifest.json` and enumerate every profile with an explicit
   `patch_series`.
2. Normalize `patches/series` by ignoring blank and comment lines.
3. Count the canonical physical, selected, and comment lines.
4. For each distinct referenced series, reject a missing canonical path or an
   out-of-order canonical position.
5. Map each rejected series back to every profile that selects it.
6. Independently inspect the default and fixed board-contract diagnostic
   selections.

## Observations

The canonical file has 114 physical lines: 111 selected patch paths and three
comments. After patch 0092, its selected paths are 0094–0095, 0097–0103, and
0114–0122; the numbering gaps are intentional.

Five manifest profile entries select four noncanonical historical series:

```text
observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve-da9214-legacy-readonly
observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve-da9214-legacy-readonly-emmc-development
observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-active-galileo
observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-active-nova
observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-active-pioneer
```

The first two profiles share
`patches/series-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve-da9214-legacy-readonly`,
which selects noncanonical patch 0096 and patches 0104–0110. The Galileo,
Nova, and Pioneer series retain that noncanonical base and extend it through
0111, 0112, and 0113 respectively.

The manifest default and the fixed board-contract diagnostic selection passed
the manual canonical-subsequence comparison. At the audited revision, the
build wrapper checked that a selected series and its patch files existed and
applied, but did not enforce the whole-manifest canonical-subsequence
invariant.

## Analysis

The hypothesis is rejected: not every selectable manifest entry satisfies the
documented invariant. This is repository reproducibility debt, not evidence
about kernel runtime or hardware support. The four rejected series are
historical experiment inputs and must not be selected for new work.

Adding their rejected provider/A72 patches to `patches/series` merely to make
the check pass would invert the safety decision and is not a valid repair.
Useful changes, if any, need new logical canonical patches after review.

## Conclusion

`confirmed` for one repository-policy violation affecting five manifest
entries and four historical series at the audited worktree state. The default
and fixed board-contract diagnostic paths were not affected by those four
series.

## Remediation

On 2026-07-29 the five rejected profiles were removed from the manifest
without deleting their historical series, fragments, patches, or experiment
records. The rejected patches were not added to `patches/series`.

`scripts/validate-manifest-series` now checks every effective profile series
against the canonical series before `scripts/kernel` selects a profile. Its
focused self-test rejects noncanonical, reordered, duplicated, missing, and
unsafe inputs and pins the unchanged default and Gauss board-contract profile
definitions.

[Roadmap gate 0](../../docs/ROADMAP.md#0-repair-the-profile-series-invariant)
records the completed gate and the next ordered work.
