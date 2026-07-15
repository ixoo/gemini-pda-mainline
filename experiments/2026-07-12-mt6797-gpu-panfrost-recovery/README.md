# Experiment: MT6797 Mali-T88x and Panfrost recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-mt6797-gpu-panfrost-recovery` |
| Status | `inconclusive` for mainline runtime support; Panfrost core-model support and platform gaps captured |
| Subsystem | MT6797 MFG, Mali Midgard GPU, GPU DVFS, SCPSYS, and memory ownership |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant not independently established |
| Date(s) | 2026-07-12 through 2026-07-14 |
| Investigator(s) | Repository maintainer with Codex assistance |
| Tracking issue | None |

## Question or hypothesis

Does the Gemini expose a standard ARM Mali Midgard GPU that Linux 7.1.3's
Panfrost can drive, or does MT6797 require a new GPU silicon driver? The
working hypothesis is that Panfrost already understands the GPU register model,
but the MT6797 platform still needs a board/SoC integration for clocks,
regulator, power domains, reset, and safe OPPs.

## Provenance and environment

- Live kernel: Linux `3.18.41+`, AArch64, Gemian Debian 9 userspace.
- Live device: `gemini@192.168.1.50` over the owner's private LAN.
- Vendor source: Gemian MT6797 tree commit
  `d388d350cb2dda8f23b99be6fa5db9628896e87f`.
- Mainline comparison: Linux `7.1.3` in the development VM.
- Sanitized summary: [`results/runtime-summary.txt`](results/runtime-summary.txt).
- Vendor ELF/source contract: [`results/mali-vendor-analysis.txt`](results/mali-vendor-analysis.txt).
- Current 72-patch package boundary: [`results/mainline-panfrost-current-72-package-20260714.txt`](results/mainline-panfrost-current-72-package-20260714.txt).
- Reproducible static analyzer: [`scripts/analyze-mali-vendor-elf.sh`](scripts/analyze-mali-vendor-elf.sh).
- Private raw capture, if regenerated, belongs only under the Git-ignored
  `artifacts/device-inventory/20260712-live/` directory.

## Safety assessment

The collector is read-only. It reads device-tree metadata, interrupt counts,
GPU driver status, and vendor diagnostic files. It never writes a procfs or
sysfs control, changes a frequency/voltage/governor, binds or unbinds a driver,
or submits a GPU job. The collector deliberately does not read the vendor
debug help file because it contains write examples.

## Associated code

Run from the repository root:

```sh
mkdir -p artifacts/device-inventory/20260712-live
ssh -i artifacts/credentials/gemini_ed25519 \
  -o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes \
  gemini@192.168.1.50 'bash -s' \
  < experiments/2026-07-12-mt6797-gpu-panfrost-recovery/scripts/collect-live-gpu.sh \
  > artifacts/device-inventory/20260712-live/gpu-panfrost.txt
chmod 700 artifacts/device-inventory/20260712-live
```

The output must remain below the ignored `artifacts/` tree. Review it before
sharing: memory-usage counters and runtime policy values are device-specific.

## Procedure

1. Confirm the key-only, noninteractive SSH path with `BatchMode=yes`.
2. Run the collector while the GPU is idle; do not change GPU policy or OPP.
3. Compare the live DT and vendor `mt_gpufreq`/Mali contracts with Panfrost's
   Midgard binding and Linux 7.1.3 SCPSYS/clock providers.
4. Keep any new GPU node disabled until a fixed-clock, fixed-voltage test plan
   proves reset, power sequencing, MMU ownership, and recovery behavior.

## Observations

- The live platform binds a vendor `mali` driver at `0x13040000`, exposes
  `/dev/mali0`, and counts activity on the three job/MMU/GPU interrupts
  (vendor GIC lines 294--296, corresponding to SPI 264--262). The device-tree
  compatible is `arm,malit860`, `arm,mali-t86x`, `arm,malit8xx`,
  `arm,mali-midgard`.
- The driver's hardware identification reports `Mali-T88x MP4 r1p0 0x0880`,
  four shader cores (`0xf` masks), and zero utilization at capture. Thus the
  DT's T860 label is not a sufficient silicon identity; the runtime GPU ID is
  T880-family Midgard.
- The vendor GPU DVFS table is selected by efuse/function-code logic. The live
  table type is `12` and contains 900, 780, 610, 520, 442.5, 365, and 238 MHz
  entries with vendor voltage units. The current sample is 238 MHz, while the
  vendor diagnostic says GPU voltage control is disabled. These diagnostics are
  not safe generic OPP values.
- The board-level vendor DTS supplies an external `rt5735@1c` on I²C7 and a
  separate `vgpu_buck@60` candidate. The live inventory marks RT5735 as bound
  and the `vgpu_buck` candidate as unbound. The vendor `mt_gpufreq` build is
  compiled with `VGPU_SET_BY_EXTIC`; its RT5735 path uses product ID `0x10`,
  VSEL registers `0x10`/`0x11`, an enable bit at bit 7, and a 7-bit voltage
  code. This is a distinct regulator contract, not evidence that the MT6351
  `buck_vgpu` or Linux's FAN53555 driver can be used unchanged.
- The vendor DT lists one MFG clock, an infrastructure MFG gate, async/MFG and
  four MFG-core power handles, two 52 MHz/universal-PLL muxes, GPU DVFS/SPM,
  GPU-PM I2C, and AP-DMA clocks. It provides no regulator, reset, OPP, or M4U
  property on the Mali node.
- The captured vendor autoconf does not define `CONFIG_MTK_GPU_SPM_DVFS_SUPPORT`.
  The ELF consequently requests the ten base clocks but does not show the
  optional GPU-PM/AP-DMA requests; the checked-in SPM sources document an
  available vendor feature path, not an active path in this image.
- The vendor `mt_gpufreq` implementation directly programs MFGPLL, switches
  parking/universal PLL paths, couples VGPU and SRAM/PMIC behavior, applies
  efuse speed bins, and includes thermal/PBM/low-battery limits. This is a
  platform DVFS policy layer, not part of the Mali job/MMU register model.
- The pinned public tree contains generic Arm Mali Midgard/Kbase `mali-r12p0`
  plus the configured `mali-r12p1` tree. The exact MT6797 platform files are
  present under `platform/mt6797/`: `mtk_config_platform.c`, the SPM sources,
  and the matching Kbase core call to `mtk_platform_init()`. The vendor ELF
  correlates with these source-level hooks, including
  `mtk_debug_mfg_reset` and the `mtk_get_gpu_pmu_*` callback shims. Treat the
  source and ELF as ABI/sequencing evidence, not code to copy; absence of a
  reset property in the vendor Mali node still does not prove that no reset or
  firmware handshake exists.
- The vendor `gpufreq` node obtains a MFG mux, MFGPLL parent, and 26 MHz
  fallback clock, then performs a parking-PLL handoff before changing MFGPLL
  post-dividers. The external-buck init also maps `0x10001000` as a GPU-LDO
  window and configures the RT5735; this is a vendor sequencing ABI, not a
  standard Panfrost OPP implementation.

## Current package boundary

The exact current package is `linux-7.1.3-gemini-a9a7c5002038`. Its effective
configuration selects `CONFIG_DRM_PANFROST=m`, the MT6797 MFG clock and power
domain providers, and the RT5735 regulator backend. The package contains
`panfrost.ko`; the MFG clock provider, four MFG power domains, and RT5735
driver are built in. The generated Gemini DTB contains one `gpu@13040000`
consumer with the live-compatible `mediatek,mt6797-mali`/`arm,mali-t880`,
three interrupts, the `mfg_bg3d` clock, four named MFG core domains, and an
RT5735 `mali-supply`, but the GPU and MFG clock nodes are disabled. The RT5735
I2C7 parent and `regulator@1c` child are also disabled. The GPU node has no
OPP, reset, or IOMMU property.

This package audit is reproducible in the VM:

```sh
./scripts/dev-vm run bash -lc \
  'CURRENT_PACKAGE=/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-a9a7c5002038 \
   experiments/2026-07-12-mt6797-gpu-panfrost-recovery/scripts/audit-current-package-panfrost.sh'
```

The audit is read-only and repeated byte-identically. It confirms a platform
integration boundary, not runtime GPU support: Panfrost's Midgard/T880 model
is the reuse target, while MT6797 clock/power sequencing, external VGPU
ownership, reset ownership, and safe fixed OPPs remain unproven.

## Linux 7.1.3 comparison

Panfrost already has generic `arm,mali-t860` and `arm,mali-t880` Midgard
matches, discovers the GPU ID from the GPU register block, and includes model
handling for IDs `0x860` and `0x880`. A new GPU silicon driver is therefore not
indicated by the live `0x0880` identity alone. The mainline binding does not
accept the vendor's legacy `arm,malit860` spelling or thirteen-clock contract;
an MT6797 board-compatible integration/backend is still required.

The reusable Panfrost binding accepts one or two clocks, one optional
`mali-supply`, one to five power-domain phandles, optional resets, and a standard
OPP table. Linux 7.1.3 already has the MT6797 topckgen, infracfg, and SCPSYS
providers. The current local series adds the missing MFG hierarchy and clock
provider, and patch 0058 gives Panfrost explicit MT6797 platform data for the
four named `core0`--`core3` power domains. Patch 0059 adds the live register and
interrupt map plus the RT5735 supply reference, but leaves the node disabled.
The binding intentionally keeps generic power-domain cardinality permissive;
the four-domain contract is enforced by the MT6797 Panfrost data, not by
changing behavior for unrelated Midgard platforms. The local MT6797 clock IDs
for `MFG`, `MFG_52M`,
`MFGPLL_CK`, `I2C_GPUPM`, and `MFG_VCG` exist, but that does not prove their
combined sequencing is Panfrost-safe.

The MT6797 Mali node is therefore a disabled, minimal integration experiment
using the standard Panfrost model and only individually described platform
resources. It has no OPP table, reset property, M4U `iommus`, or runtime enable
request. The vendor `MFG_BG3D` clock is represented by the local `mfgsys`
provider, but its sequencing remains unverified.
Do not add a MediaTek M4U `iommus` property: the recovered
MT6797 M4U port table has no GPU client and the Mali block exposes its own MMU
interrupt.

## Analysis

The strongest reuse boundary is the GPU core driver: Panfrost's Midgard model
code covers the live T88x/T880-family ID. The new work is platform integration,
not a wholesale replacement of the GPU driver. The source and ELF add a
  concrete vendor contract: five compatible-node mappings, ten requested clocks,
  VGPU readiness gating, a G3D reset write at offset `0x0c`, and an eight-clock
  power-on/off sequence. The source also contains an optional SPM DVFS PCM path,
  but that feature is absent from the captured autoconf and optional clock
  requests are absent from the ELF. The mainline binding cannot express the
  base contract unchanged, so a small MT6797 backend or carefully layered
  platform integration is represented by patches 0058--0059; runtime ownership
  and sequencing still require hardware evidence.
The main unknowns remain the minimum safe clock set, whether generic SCPSYS
domains can replace the vendor handles, reset ownership, and a calibrated
OPP/RT5735 relationship. A 700 or 900 MHz target copied from vendor DT/procfs
is not an initial safe operating point.

## Conclusion

`inconclusive`: Panfrost reuse is technically plausible and preferred for the
observed `0x0880` core model; the evidence does not justify enabling the GPU or
creating a new Mali register driver yet. The follow-up clock/power investigation
adds disabled-only patches 47–51 for the reusable MFG clock, SCPSYS hierarchy,
MFG preclock, and external RT5735 VSEL0 provider. Patches 0058–0059 add the
MT6797 Panfrost platform data and disabled node without enabling clocks,
domains, reset, OPP, or jobs. The GPU consumer remains disabled because reset,
rail, and OPP behavior are unverified. If a future board reports a GPU
ID outside Panfrost's Midgard model table, use a new-driver boundary instead of
forcing a generic match.

## Follow-up

1. Validate the source contract recorded in
   `results/mainline-panfrost-mt6797-source-validation.txt` against each
   regenerated Linux tree and preserve the disabled status.
2. Reconcile the recovered ELF platform contract with a small MT6797 Panfrost
   backend: reset ownership, MFG/MFG-core sequencing, VGPU readiness, and the
   ten-clock vendor contract must be reduced to standard Linux resources
   without copying proprietary code.
3. Correlate efuse/PTP/EEM speed-bin selection with a board-safe fixed OPP;
   keep dynamic GPU DVFS off until voltage telemetry is independently verified.
4. Test Panfrost first with the vendor GPU held at an explicitly conservative
   clock and with the M4U relationship absent; stop on any display, memory, or
   watchdog regression.
