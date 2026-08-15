# Experiment: MT6797 handoff decoder linkage

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-15-mt6797-handoff-decoder-link` |
| Status | running |
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
- Patch base: canonical `patches/series` through patch `0276`.
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

## Analysis

Pending static and Buildbox validation.

## Conclusion

Pending.

## Follow-up

After both Buildbox configurations pass, return to the ordered native DA921x
read-only runtime-observation gate in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md). No device action follows from a
link repair alone.
