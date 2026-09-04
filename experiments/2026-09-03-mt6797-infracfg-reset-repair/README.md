# Experiment: MT6797 infracfg reset repair

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-03-mt6797-infracfg-reset-repair` |
| Status | `in progress`; hardware-free implementation gate |
| Subsystem | MediaTek MT6797 infracfg reset controller |
| Device variant | Planet Computers Gemini PDA, MT6797 |
| Date(s) | 2026-09-03 to 2026-09-04 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Thermal/AUXADC transaction prerequisite |

## Question or hypothesis

Can the incorrect three-bank read/modify/write reset provider be replaced by a
fail-closed SET/CLEAR model that exposes only the two reset paths directly
proved by exact MT6797 sources?

The hypothesis is that the existing MediaTek reset-index map can preserve a
compact DT ABI while translating thermal and PMIC-wrap to separate proven
banks. The unsourced RST1 path and every historical unverified bit remain
unaddressable.

## Provenance and environment

- Repository parent: `77ece506cdce07042f74f4295e21077851b35abe`.
- Prepared Linux source state: `49084a29725089735de735e0b63543ef44261ef1533075fe9a815574d48fa9f0`.
- Prepared Linux source integrity: `d23fbc7533cfe264398e45620e216113259468afaf06154262bd709360752d07`.
- Parent source hashes are pinned by `scripts/generate-on-buildbox`.
- Source proof and vendor identities are retained by the preceding
  [transaction audit](../2026-09-03-mt6797-thermal-auxadc-transaction-audit/README.md).
- Build backend: Buildbox only.
- Boot path: none. This experiment creates no device candidate.

## Safety assessment

The generator edits bounded copies of Linux clock/reset sources on Buildbox.
The focused KUnit suite resolves descriptor entries into register offsets and
masks through the same pure helper used by the production reset write path. It
creates no platform device, maps no MMIO, writes no register or storage, and
does not contact the Gemini.

## Associated code

- `DESIGN.md`: accepted translation and quarantine model.
- `scripts/source_edits.py`: deterministic production and KUnit edits.
- `scripts/validate_source.py`: exact edited-source contract.
- `scripts/validate_patches.py`: generated patch boundary checks.
- `scripts/generate-on-buildbox`: pinned three-patch generator.
- `results/patch-generation-20260904.txt`: exact Buildbox generation receipt.

## Procedure

1. Correct the superseded July interpretation without rewriting its chronology.
2. Validate, commit, and publish the deterministic generator.
3. Generate three normal patches from the exact prepared source on Buildbox:
   binding correction, production repair, then focused KUnit coverage.
4. Admit the production repair and focused KUnit test in canonical order.
5. Build the exact pushed KUnit profile on Buildbox and run it in isolated
   arm64 QEMU.
6. Record source, patch, build, package, and KTAP identities.

## Expected observations

- External reset 0 resolves to internal bank 0 bit 0: assert `0x120`,
  deassert `0x124`.
- External reset 1 resolves to internal bank 1 bit 0: assert `0x140`,
  deassert `0x144`.
- External reset 2, the old linear ID 64, and an internal ID beyond the two
  declared banks are rejected without a register address.
- The descriptor uses `MTK_RST_SET_CLR`, contains two non-contiguous physical
  banks, and contains no RST1 base.

## Observations

- The first generated review correctly exposed two style issues: the binding
  correction was combined with driver code and KUnit formatting was not yet
  submission-clean. The generator was changed to emit three logical patches.
- Manual diff review then found that the initial binding slice also removed
  unrelated TOPRGU IDs added later in the canonical series. The edit and its
  validator were narrowed before admission; all TOPRGU definitions are now
  preserved.
- The corrected Buildbox run at repository commit `be8fa9ff7542...` reproduced
  the exact prepared source and emitted three normal patches. Patch replay,
  source-contract checks, full-package checksums, and strict checkpatch all
  pass; checkpatch reports zero errors, warnings, or checks for every patch.
- The canonical series and all 176 manifest profiles pass the repository
  subsequence invariant after admitting patches 0514 through 0516 and the
  isolated `mt6797-infracfg-reset-kunit` profile.
- No kernel build, KUnit execution, candidate, or device action has occurred
  yet. Those results must be recorded before this gate is complete.

## Non-scope

This gate does not enable thermal or standalone AUXADC DT nodes, add the
thermal reset phandle, sample temperature, request an IRQ, touch watchdog
protection, alter cpufreq/OPP or CPU load, create a boot image, or act on the
device. Correcting the already-live PMIC-wrap reset changes runtime behavior;
that requires its own later serviceability candidate.

## Follow-up

After the hardware-free source, build, and KUnit gates pass, construct one
isolated PMIC-wrapper serviceability candidate. Only after that consumer is
shown to survive a real reset may the thermal transaction implementation take
the repaired reset as a dependency.
