# Experiment: MT6797 handoff decoder linkage

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-15-mt6797-handoff-decoder-link` |
| Status | completed |
| Subsystem | MT6797 DVFSP configuration and linkage |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date(s) | 2026-08-15 America/New_York |
| Investigator(s) | repository owner and Codex |
| Tracking issue | none |

## Question or hypothesis

Can every handoff profile link the pure MT6797 clock/CSPM decoder helpers
without enabling the optional protected-clock hardware transport?

## Provenance and environment

- Kernel release: Linux 7.1.3 from the manifest-selected prepared source.
- Patch base: canonical `patches/series` through patch `0277` at exact
  repository commit `ede1f47909ed582d6db0dcdd2fb672607da540f0`.
- Failed configuration: manifest profile `da921x-resource-only-provider`.
- Build backend: Buildbox only.
- Boot path: none.

## Safety assessment

This is a hardware-free configuration and link repair. Patch 0277 only changes
Kconfig and object selection for two existing pure decoders. It does not enable
the MMIO transport, add a hardware operation, build a boot candidate, access
the Gemini, or write a partition. No device backup is needed.

## Associated code

- [`DESIGN.md`](DESIGN.md): dependency and two-configuration contract.
- [`scripts/validate.py`](scripts/validate.py): patch, series, and no-effect
  validation.
- [Patch 0277](../../patches/v7.1.3/0277-soc-mediatek-build-MT6797-state-decoders-for-handoff.patch).

## Procedure

1. Retain the exact failed Buildbox result for commit `0b620c98396c...`.
2. Add the hidden pure-decoder gate as one logical patch.
3. Run static, manifest-series, patch-apply, and patch-format checks.
4. Commit and push the exact repository state.
5. Rebuild the same transport-free `da921x-resource-only-provider` profile on
   Buildbox.
6. Build the transport-enabled `dvfsp-owner-kunit` profile on Buildbox to prove
   that each decoder remains linked exactly once.

## Observations

The transport-free profile compiled both handoff callers but failed the final
link with undefined references to `mt6797_dvfsp_cspm_state_decode`,
`mt6797_dvfsp_clock_state_decode`, `mt6797_dvfsp_cspm_vproc_code_to_uv`, and
`mt6797_dvfsp_cspm_vsram_code_to_uv`. Its final configuration had
`CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=n`, matching the intended profile and
showing that the failure was an object-ownership error rather than a missing
hardware-transport selection.

See the [failed Buildbox receipt](results/transport-free-build-attempt-20260815.txt).

Patch 0277 adds a hidden pure-decoder object gate and leaves the protected
clock transport independently default-off. The exact failed profile then
passed the full Buildbox build and package-validation path with
`HANDOFF=y`, `STATE_DECODERS=y`, and `CLOCK_BACKEND=n`. Its `System.map`
contains exactly one copy of each of the four formerly unresolved helpers.
The paired `dvfsp-owner-kunit` profile also passed with `HANDOFF=y`,
`STATE_DECODERS=y`, and `CLOCK_BACKEND=y`, again with exactly one copy of each
helper. Both builds produced 119 DTBs from the same clean pushed commit and
patchset.

See the [transport-free receipt](results/transport-free-buildbox-20260815.txt)
and [transport-enabled receipt](results/transport-enabled-buildbox-20260815.txt).

## Analysis

The failure was a configuration ownership defect. Handoff state sources call
the pure decoders regardless of whether the optional MMIO transport is
selected, so the decoder objects belong to the union of those two features.
The paired build proves that moving ownership to the hidden union gate fixes
the missing-object case without creating duplicate objects in the existing
transport-enabled case.

This is link closure only. It creates no production caller for the experimental
owner-registration entry points and supplies no new live hardware observation.
Neither fetched package is a boot candidate.

## Conclusion

The two-configuration contract passes at exact pushed commit `ede1f47`.
Transport-free handoff profiles can now link their pure decoder dependencies,
and transport-enabled profiles still link each decoder once. No device action
was taken.

## Follow-up

After both Buildbox configurations pass, return to the ordered native DA921x
read-only runtime-observation gate in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md). No device action follows from a
link repair alone.
