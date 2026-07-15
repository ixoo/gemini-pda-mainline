# Experiment: MT6797 clock, MFG power, and reset-provider recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-mt6797-clock-power-reset-recovery` |
| Status | `inconclusive` for mainline runtime; provider contracts and a disabled-only implementation path recovered |
| Subsystem | MT6797 topckgen, infracfg, SPM/SCPSYS, MFG clock and GPU power hierarchy |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant not independently established |
| Date(s) | 2026-07-12 and 2026-07-13 |
| Investigator(s) | Repository maintainer with Codex assistance |
| Tracking issue | None |

## Question or hypothesis

Does the live MT6797 clock and power topology map directly to Linux 7.1.3's
common-clock and generic SCPSYS drivers, or does the MFG/GPU block require a
new platform-specific implementation? The preferred hypothesis is reuse of
the generic providers with narrowly scoped MT6797 data where the vendor
register contract is demonstrably different.

## Provenance and environment

- Live kernel: Linux `3.18.41+`, AArch64, Gemian Debian 9 userspace.
- Live device: `gemini@192.168.1.50` over the owner's private LAN.
- Vendor source: Gemian MT6797 tree commit
  `d388d350cb2dda8f23b99be6fa5db9628896e87f`.
- Mainline comparison: Linux `7.1.3` in the development VM.
- Sanitized summary: [`results/runtime-summary.txt`](results/runtime-summary.txt).
- Private raw capture, if regenerated, belongs only under the Git-ignored
  `artifacts/device-inventory/20260712-live/` directory.

## Safety assessment

The collector is read-only. It reads debugfs clock summaries, provider links,
SPM diagnostics, regulator topology, and selected device-tree metadata. It
does not write clock, power-domain, reset, regulator, debugfs, procfs, or
sysfs controls. Do not turn the captured register offsets into a write test
without a serial/recovery path and an explicit target.

## Associated code

Run from the repository root:

```sh
mkdir -p artifacts/device-inventory/20260712-live
ssh -i artifacts/credentials/gemini_ed25519 \
  -o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes \
  gemini@192.168.1.50 'bash -s' \
  < experiments/2026-07-12-mt6797-clock-power-reset-recovery/scripts/collect-live-clock-power-reset.sh \
  > artifacts/device-inventory/20260712-live/clock-power-reset.txt
chmod 700 artifacts/device-inventory/20260712-live
```

The output must remain below the ignored `artifacts/` tree. The SPM firmware
debugfs listing contains vendor image names and sizes; do not copy or publish
the blobs.

The CPU-clock comparison is source-only and runs in the development VM. The
current 72-patch rerun is recorded in
[`results/mt6797-cpu-clock-backend-current-72-20260714.txt`](results/mt6797-cpu-clock-backend-current-72-20260714.txt):

```sh
./scripts/dev-vm run bash -lc \
  'bash experiments/2026-07-12-mt6797-clock-power-reset-recovery/scripts/analyze-cpu-clock-backend.sh'
```

It reads the pinned vendor tree with `git show`, compares Linux 7.1.3 CCF
coverage, and emits source hashes plus the recovered ownership boundary.

## Procedure

1. Confirm the key-only, noninteractive SSH path with `BatchMode=yes`.
2. Run the collector while the device is idle; do not change a governor,
   frequency, voltage, power-domain state, or reset line.
3. Compare the live clock summary and flattened-tree resource tuples with the
   vendor `clk-mt6797.c`/`clk-mt6797-pg.c` source.
4. Compare the recovered register contract with Linux 7.1.3's generic
   `mtk-scpsys` and `mtk_clk_simple_probe` implementations.

## Observations

- The live system exposes `10001000.scpsys`, `10001000.infracfg_ao`,
  `13000000.g3d_config`, `13040000.mali`, `14000000.mmsys_config`, and both
  MSDC controllers as platform devices. The vendor flattened tree's SCPSYS
  node has three resources: infracfg `0x10001000`, SPM `0x10006000`, and
  infracfg `0x10201000`. The mainline driver intentionally maps the second
  SPM window as its resource and gets the first infracfg window through the
  `infracfg` syscon phandle; the address difference is therefore a binding
  shape difference, not evidence of a different chip.
- The live clock summary reports `mfgpll`/`mfgpll_ck`/`mfg_sel`/`mfg_bg3d` at
  500.5 MHz, `mfg_52m_sel` and `infra_mfg_vcg` at 156 MHz, and the MFG power
  gates with zero enable/prepare counts while the vendor GPU is idle. The
  display/MM, thermal, USB, and MSDC clocks show the expected active rates.
- Vendor MFG power control uses SPM status bits 8--13 and control offsets
  `0x334` (async), `0x338` (MFG), and `0x340`--`0x34c` (cores 0--3). The SRAM
  power-down control and acknowledgement bits for MFG and all four cores are
  in a separate register at `0x33c`; core acknowledgements are bits 20--23 and
  MFG acknowledgement is bits 16--17. This cannot be represented by the
  current generic driver, which assumes control and acknowledgement fields
  share one register.
- The vendor hierarchy is async → MFG → core0..core3. The vendor MFG power
  routines do not execute the defined MFG bus-protection mask in the actual
  code path; no mainline bus-protection bit is inferred. The generic
  power-on/off sequencing otherwise matches the vendor ordering (power on,
  status poll, clock/iso/reset, SRAM handshake, and reverse shutdown).
- Every vendor MFG power-gate entry prepares the `mfg_52m_sel` clock before
  invoking its power sequence and unprepares it afterward. Patch 50 maps that
  requirement to the existing topckgen `CLK_TOP_MUX_MFG_52M` clock instead of
  relying on the unrelated `mfg_sel` gate.
- The vendor `g3d_config@13000000` clock provider exposes one `MFG_BG3D` gate
  at set/clear/status offsets `0x4`/`0x8`/`0x0`, with `mfg_sel` as parent.
  Base Linux 7.1.3 had no MT6797 MFG/G3D provider or binding, although the
  parent and infrastructure clock IDs already existed; local patch 48 adds
  the normal set/clear gate provider.
- The vendor CPU DVFS path is not a normal unprotected CCF mapping. LL, L, and
  CCI use ARMPLL windows and shared mux/divider fields behind an MCUMIXED
  hardware semaphore shared with SPM and ATF; the B cluster uses secure
  BigiDVFS calls for PLL and SRAM-LDO operations. The source-derived field map
  and staged mainline boundary are recorded in
  [`results/mt6797-cpu-clock-backend.md`](results/mt6797-cpu-clock-backend.md).
- The vendor SPM debugfs endpoint lists loaded PCM image names and sizes for
  suspend, SODI, deep-idle, and vcorefs. These are firmware evidence only;
  their contents are not redistributed and no generic mainline firmware
  contract is inferred.

## Linux 7.1.3 comparison

The generic MediaTek SCPSYS driver is the correct starting point. It already
implements the MT6797 status registers, power sequencing, regulator hooks,
clock hooks, and MM/VDEC/ISP/VENC/MJC subdomain relationships. A small generic
extension for separate SRAM control and acknowledgement offsets, plus the
evidence-backed MT6797 MFG/core data and hierarchy, is sufficient; a wholly
new power-domain driver is not indicated.

The clock gate is likewise a normal MediaTek set/clear gate. A small
`mt6797-mfg` provider using `MFG_BG3D` and a disabled `g3d_config` DTS node is
preferable to copying the vendor power-gate ABI. The GPU remains disabled
until the standard Panfrost binding, VGPU regulator, reset ownership, and a
conservative OPP are independently verified.

## Conclusion

`inconclusive`: the clock and power register contracts are sufficiently
understood to prepare disabled-only mainline provider/data patches. Runtime
power sequencing has not been attempted, so this experiment does not claim
GPU, display, or suspend support.

The evidence-backed implementation is now represented by patches 47–50:
generic SCPSYS MFG/core domains with separate SRAM offsets, the standard
MT6797 MFGSYS gate provider, its disabled-only DTS resource, and the
vendor-confirmed MFG 52 MHz preclock. The complete 50-patch Linux 7.1.3
series compiled successfully in the VM as package
`linux-7.1.3-gemini-a0d79855dcb8`. The patchset SHA-256 is
`a0d79855dcb8365e10ab64ad090bf67d80f58e1f78d1dfcdd3c6f6d298f66188`, the
merged configuration SHA-256 is
`b573886673370ced1d68cfaaea5a55647177e4bb4275cc8d0d0e432964e758da`, the
arm64 `Image` SHA-256 is
`9663aaaaa5d422c5cd85333c67d8bd0f052dabe1aa575eee7cac7413a1f80e56`, and the
Gemini DTB SHA-256 is
`70681c8a5a10f264d2431a5d31176efaa5b592ec75f15cfedc0b6d8700a0ce66`.
These are build results only; no image was flashed or booted.

The later RT5735 VGPU investigation extends the ordered series. The current
72-patch artifact is `linux-7.1.3-gemini-a9a7c5002038`; its package provenance
and validation are recorded in the integration audit, while the source-only
clock ownership result above remains independent of package hashes.

## Follow-up

1. Build the generic SCPSYS separate-SRAM-offset extension with the MT6797
   MFG/core hierarchy and check that the previously sparse domain table probes.
2. Build the disabled MT6797 MFG clock provider and DTS node; inspect CCF names
   and `clk_summary` on a mainline boot before enabling consumers.
3. Recover the reset and VGPU/OPP boundary from vendor probe paths, then run a
   bounded Panfrost power-on experiment with a recovery path.
4. Keep vendor SPM/PCM images private and treat suspend/deep-idle as a separate
   firmware investigation.
