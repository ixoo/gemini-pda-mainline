# Experiment: Linux 7.1.3 patched-tree integration build

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-13-kernel-integration` |
| Status | `completed` |
| Subsystem | stable-kernel patch integration and artifact packaging |
| Device variant | Gemini PDA, MT6797 keyboard variant (compile target only) |
| Date(s) | 2026-07-13 through 2026-07-14 |
| Investigator(s) | Codex with repository owner |
| Tracking issue | none |

## Question or hypothesis

Can the pinned Linux 7.1.3 source, the ordered current 74-patch series, and the reviewed
Gemini configuration merge and compile into a reproducible arm64 Image and
MediaTek DTB package without changing hardware state? This tests build
integration only; it does not claim that any driver has been validated on the
device.

## Provenance and environment

- Kernel release: Linux 7.1.3, source archive SHA-256
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`.
- Patch series: 72 entries, current patchset SHA-256
  `a9a7c5002038022c5df87ed48f61cd68778b422370f7d038d07e73a086490632`.
- Configuration: merged `configs/gemini.fragment`, resulting configuration
  SHA-256 `60a84aa5ac3b3aeb17d5357508ac123089d97d7d5ed9164458dee3ce6ded8159`.
- Toolchain: GCC 13.3.0 and GNU ld 2.42 in the ARM64 Ubuntu 24.04 VM.
- Build workflow: `./scripts/dev-vm build-kernel`.
- Artifact validator: `./scripts/dev-vm validate-kernel` using
  `scripts/validate-kernel-artifact`.
- Inputs are pinned by `kernel/manifest.json`; generated source, build, and
  artifact trees remain guest-owned and Git-ignored.

## Safety assessment

The procedure is read-only with respect to the Gemini PDA and does not access a
device, flash a partition, write preloader/NVRAM/GPT data, or generate a whole-
device image. It only downloads a public kernel archive, applies patches in the
VM, compiles, and verifies guest-owned files.

## Associated code

- `scripts/dev-vm` dispatches the host-to-VM workflow.
- `scripts/kernel` prepares, configures, builds, and packages the pinned tree.
- `scripts/validate-kernel-artifact` validates package checksums and provenance.
- `kernel/manifest.json`, `patches/series`, `patches/v7.1.3/`, and
  `configs/gemini.fragment` are the complete declared inputs.

## Procedure

1. From the repository root, run `./scripts/dev-vm kernel status` and confirm
   the pinned version and patch count.
2. Run `./scripts/dev-vm build-kernel` in the ARM64 development VM.
3. Run `./scripts/dev-vm validate-kernel` to select and verify the newest
   guest-owned package.
4. Retain the printed metadata with the experiment notes. Do not transfer the
   package to hardware without a separate, explicit flashing procedure.

## Current follow-up

This record preserves earlier 68-, 71-, and 72-patch integration milestones.
The authoritative current package and validation are in
[`mainline-74-patch-current-20260714.txt`](results/mainline-74-patch-current-20260714.txt).
The earlier module-enabled package revalidation is retained as historical
evidence in [`mainline-71-patch-modules-revalidation-20260714.txt`](results/mainline-71-patch-modules-revalidation-20260714.txt).

## Observations

The prepared source was already current. Configuration completed with the
expected `merge_config.sh` override warnings for values deliberately set by the
Gemini fragment. Compilation exited successfully and produced the uncompressed
`Image`, LK-compatible `Image.gz`, and all arm64 DTBs.

The earlier package was named `linux-7.1.3-gemini-a9a7c5002038`. The
current package is `linux-7.1.3-gemini-c2feb465d6c6`; its
[current package record](results/mainline-74-patch-current-20260714.txt)
is the authoritative hash/provenance record. The older
[LK-compatible rebuild](results/mainline-71-patch-lk-fdt-build-20260713.txt)
and module-enabled revalidation use superseded package hashes and remain
historical build evidence. The
current private LK candidate is recorded separately by the boot-contract
experiment. That historical LK-compatible rebuild
contains `Image.gz` as well as the raw `Image`, and its 48,547,848-byte
decompressed payload fits the MT6797 LK 50 MiB buffer. It contains 119
MediaTek DTBs, including `mt6797-gemini-pda.dtb`; that DTB contains the
disabled MT6797 USB3/T-PHY and USB11/MUSB topologies as well as the earlier
disabled display and peripheral candidates. Its complete `SHA256SUMS` manifest
passed, including `Image`, `Image.gz`, `kernel.config`, `System.map`, provenance
files, every DTB, and every patch copy. The retained LK FDT/reservation audit
also passes with no static post-LK mblock overlap; mainline runtime remains
untested.
The 2026-07-14 revalidation also passed the complete checksum manifest with
`BUILD_MODULES=1`; it contains 1,570 `.ko` objects (1,583 files including
module metadata) under the guest-owned `modules/` tree. Those modules are not
loaded or hardware-tested.
Patches 0066/0067 add explicit MT6797 compatible data to the existing T-PHY,
MTU3, and xHCI frameworks; patch 0067 also makes the MTU3 binding accept the
single `device` interrupt name observed on this board. The generated full
schema validates the Gemini DTB without the earlier short-tuple warning.
Patch 0068 describes the source-derived USB3 resources while patches 0069/0070
add the disabled USB11/MUSB shape. All USB nodes remain disabled and omit VBUS,
role, redriver, and PHY tuning. The
earlier 68-patch validator and schema records remain historical provenance.

## Analysis

The hypothesis is supported for source preparation, configuration, compilation,
packaging, file-integrity verification, the corrected Gemini DT hierarchy, and
the source-derived disabled USB3 topology. The SCPSYS, AFE, T-PHY, MTU3, and
xHCI changes reuse existing Linux frameworks with explicit MT6797 data;
runtime role/VBUS/PHY behavior remains untested. This result does not
distinguish runtime driver bugs, bootloader contract problems, unsupported
peripherals, or variant-specific wiring; compile success is therefore
deliberately not promoted to `docs/HARDWARE_SUPPORT.md`.

## Conclusion

`confirmed`, scoped to Linux 7.1.3, the 74 patches listed by the pinned series,
the recorded configuration, and the ARM64 VM toolchain. Hardware behavior is
untested.

## Follow-up

- Keep the artifact in the guest or an explicitly ignored export directory and
  use the validator after every patch/configuration change.
- Keep the MT6797 USB3/T-PHY nodes disabled until a named device boot and a
  reversible gadget-serial test establish clocks, PHY initialization, and
  connector/role ownership.
- For runtime work, boot a named Gemini variant through the separate reversible
  boot-artifact path and update the subsystem experiment and support matrix only
  from serial-console evidence.
- Keep the new SCPSYS/AFE schemas aligned with their existing drivers, and
  develop a separate DVFSP driver only from additional hardware evidence.
- If a chipset-specific block differs from the generic Linux driver contract,
  keep the reuse decision and the new-driver rationale in that subsystem's
  experiment rather than changing the default behavior speculatively.
