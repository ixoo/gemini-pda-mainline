# Experiment: Mali-T880 GPU offline bring-up preparation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-31-mali-t880-offline-bringup` |
| Status | `offline only`: profile, composition helper and validator prepared; no build or device run |
| Subsystem | MT6797 MFG / Mali-T880 / Panfrost / RT5735 |
| Device variant | Planet Gemini PDA, MT6797X, Gemian 3.18 vendor baseline |
| Date(s) | 2026-10-31 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | GPU step in the roadmap |

## Review correction (2026-11-01)

The [source/ELF and validator review](../2026-11-01-mali-t880-research-review/README.md)
found unresolved sequencing and validation gaps. Legacy SCPSYS powers MFG
at provider probe even with the GPU node disabled; this profile must remain
compile-only. A validator PASS checks selected properties, not provider
availability or correct core-clock/domain references, and does not admit a boot.
The composition requests 520 MHz but has no runtime rate evidence.

## Question

What is the minimum offline change set that builds the MT6797 GPU platform
providers and produces a reviewable, enabled GPU DT composition for a later
fixed-point 520 MHz / 1.0 V Panfrost probe?

## Inputs

- [Mali-T880 hardware record](../../docs/hardware/mali-t880.md)
- [GPU RE record](../2026-10-04-gemini-gpu-re/README.md)
- [GPU/Panfrost recovery](../2026-07-12-mt6797-gpu-panfrost-recovery/README.md)
- Exact Gemian DTB and active vmlinux identities are in the hardware record.
- Local patches `0047`-`0051`, `0058`-`0059`, `0090`, `gpu/0001`.
- Public MT6797 register tables (96boards): `GPULDO_CTRL_0..10`,
  `CLK_MISC_CFG_0`, `CLK_CFG_1`, `TOPRGUWDT_SWSYSRST`, `MFG_ASYNC_CON`.
- Vendor userspace audit: `libGLES_mali.so`, `libged.so`, `ged_srv`,
  `libgpu_aux.so` contain no firmware path or load call; `libGLES_mali.so` is
  the shader compiler/command-stream runtime and opens `/dev/mali`.
- Active vendor vmlinux contains `dvfs_gpu_binary` and `mtk_kbase_spm_*`, but
  the SPM kick path is compiled out (`MTK_GPU_SPM` undefined).
- Planet LK `md1_boot()` pre-sets a modem-boot GPU LDO subset
  (`0x10001fc0/fc4 = 0x0d0d0d0d`, `0x10001fbc = 0xff`) and powers
  `MFG_ASYNC_PWR_CON`; LK `mt_pll_turn_off()` also disables MFGPLL in the
  battery/charging path.
- `vgpu_buck@60` is the FAN53555 driver (`mediatek,vgpu_buck`) at I2C7 `0x60`,
  not the active RT5735 at `0x1c`.
- Vendor Kbase defaults to `COHERENCY_NONE`; the exact DT has no
  `system-coherency` override, so no `dma-coherent` property should be added.
- Thermal trips/NTC parameters are userspace `.tp` data, already decoded in
  `2026-10-31-mt6797-thermal-management`; the GPU is cooled by a
  `mt_gpufreq_thermal_protect()` power budget, not a GPU thermal zone. Only
  per-unit devinfo/EEM calibration values remain device-only.

## Changes

| File | Purpose |
| --- | --- |
| `configs/gemini-a53-gpu-bringup.fragment` | DRM/Panfrost, SCPSYS, MFGSYS, RT5735 and I2C options |
| `patches/series-a53-gpu-bringup` | A53 service foundation plus `gpu/0001` bus protection |
| `kernel/manifest.json` profile `mt6797-a53-gpu-bringup` | A53 service chain plus the GPU fragment |
| `scripts/compose-gpu-dtb.py` | Enables MFGSYS, I2C7, RT5735 and GPU in a DTB copy; adds bus clock, fixed 1.0 V, 520 MHz core rate, `univpll2_d8` MFG 52 MHz parent and TOPRGU MFG reset |
| `scripts/validate-gpu-config.py` | Checks config symbols and the GPU DT contract |
| `scripts/test-validator.py` | Positive/negative fixture test |

The composition helper deliberately does not add an OPP table, devfreq
governor, IOMMU or thermal cooling. It does add a TOPRGU reset reference;
Panfrost initially deasserts that line, which does not reproduce the vendor's
init pulse. Reset sequencing remains unresolved.

## Procedure

1. Build the profile on a Buildbox from a clean pushed commit:

   ```sh
   KERNEL_PROFILE=mt6797-a53-gpu-bringup \
     ./scripts/build-kernel --backend buildbox
   ```

2. Validate the resulting `.config` and base DTB (GPU still disabled):

   ```sh
   ./scripts/dev-vm run bash -lc \
     'experiments/2026-10-31-mali-t880-offline-bringup/scripts/validate-gpu-config.py \
        --config <build>/.config --dtb <build>/board.dtb --expect disabled'
   ```

3. Compose an enabled bring-up DTB copy:

   ```sh
   ./scripts/dev-vm run bash -lc \
     'experiments/2026-10-31-mali-t880-offline-bringup/scripts/compose-gpu-dtb.py \
        --input <build>/board.dtb --output <build>/board-gpu.dtb'
   ```

4. Validate the enabled composition:

   ```sh
   ./scripts/dev-vm run bash -lc \
     'experiments/2026-10-31-mali-t880-offline-bringup/scripts/validate-gpu-config.py \
        --config <build>/.config --dtb <build>/board-gpu.dtb --expect enabled'
   ```

5. Build/DT checks alone do not admit a candidate. Resolve the provider-probe,
   LDO/rail/clock/protection ordering and validator gaps before designing a
   separate reviewed experiment for inactive `boot2`.

## Safety

No device, partition, regulator, clock, power domain or GPU register was
touched. The composition helper mutates a temporary DTB copy only. The
profile keeps the GPU node disabled until the composition step; no default
profile enables it. This describes the files, not the effects of booting them:
SCPSYS provider probe would still power the MFG domains.

## Limits

- The profile has not yet been built on a Buildbox in this record.
- The composed DTB has been exercised on the fixture and on a retained real
  `board.dtb`; it has not yet been applied to a freshly built candidate.
- The MFG SRAM LDO values and 52 MHz parent are now decoded from the public
  MT6797 register table, but the LDO writes are not implemented. Runtime
  readback and bus-protect status still need a bounded Gemian capture.
- No OPP/devfreq/thermal policy is included.

## Follow-up

1. Resolve rail/LDO/domain/protection ownership and rollback, including SCPSYS
   probe. MFG callbacks alone do not reproduce the vendor sequence. The vendor
   chooses `MFG_ASYNC_CON` from the table maximum: type 12 selects `0xa`,
   even at 520 MHz; do not select `0x5` just from the fixed frequency.
2. Build the profile on Buildbox.
3. Repair provider/reference validation and run the base-DTB and composed-DTB
   checks on that exact package.
4. Perform the read-only Gemian register capture from the hardware record.
5. Only then design the fixed-point boot candidate.
