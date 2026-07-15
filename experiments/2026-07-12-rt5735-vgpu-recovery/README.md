# Experiment: RT5735 external GPU regulator recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-rt5735-vgpu-recovery` |
| Status | `inconclusive` for mainline runtime; register contract recovered from live DT and vendor source |
| Subsystem | External RT5735 VGPU buck on MT6797 I²C7 |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant not independently established |
| Date(s) | 2026-07-12 |
| Investigator(s) | Repository maintainer with Codex assistance |
| Tracking issue | None |

## Question or hypothesis

Is the Gemini GPU supply an existing Linux FAN53555-compatible regulator, or
does the board require a dedicated RT5735 regulator provider before Panfrost
can safely request `mali-supply`?

## Provenance and environment

- Live kernel: Linux `3.18.41+`, AArch64, Gemian Debian 9 userspace.
- Live device-tree capture: private, Git-ignored under
  `artifacts/device-inventory/20260711-live/device-tree-v5.txt`.
- Live regulator/config capture: private, Git-ignored under
  `artifacts/device-inventory/20260711-live/pmic-regulators.txt`.
- Vendor source: Gemian MT6797 tree commit
  `d388d350cb2dda8f23b99be6fa5db9628896e87f`.
- Mainline comparison: Linux `7.1.3` in the development VM.
- Sanitized source summary: [`results/source-summary.txt`](results/source-summary.txt).

## Safety assessment

This investigation is read-only. It inspects an already captured device tree,
regulator metadata, kernel configuration, and public vendor source. It does not
probe an I²C address, change a voltage, enable or disable a regulator, alter a
GPU clock, or attach a consumer. The proposed mainline provider must not copy
the vendor boot-time GPIO workaround or write default protection settings at
probe time.

## Associated code and evidence

No new device collector is required: the live DT and regulator captures were
collected by the hardware-inventory experiment. The source comparison is
reproducible in the VM with:

```sh
limactl shell --workdir=/mnt/gemini-pda-mainline gemini-pda-dev -- bash -lc \
  'cd /home/julien.guest/src/reference/gemian-linux-kernel-3.18 && \
   sed -n "1,180p" drivers/misc/mediatek/power/mt6797/rt5735.h && \
   sed -n "220,290p" drivers/misc/mediatek/power/mt6797/rt5735.c'
```

The raw captures remain private. This record contains only register addresses,
identities, and source-derived behavior needed to review a driver.

## Observations

- The live vendor DT contains `i2c@11010000/rt5735@1c` with compatible
  `rt,rt5735-regulator` and status `ok`. The same bus contains a separate
  `vgpu_buck@60` candidate, but the inventory marks that candidate unbound.
- The vendor kernel configuration enables `CONFIG_REGULATOR_RT5735`. The
  PMIC's internal `buck_vgpu` is also present and enabled, so its live status
  must not be mistaken for proof that it supplies the GPU.
- Vendor `mt_gpufreq.c` selects `VGPU_SET_BY_EXTIC`. It checks RT5735 product
  ID `0x10` at register `0x03`, uses VSEL0 register `0x11`, and treats bit 7 as
  the VSEL0 enable bit. The voltage field is bits 6:0 with 6.25 mV steps from
  600 mV through 1.39375 V, giving 128 linear selectors.
- The vendor implementation uses register `0x12` bit 4 for active discharge
  and register `0x14` bit 7 for VSEL0 forced-PWM mode. Its initialization writes
  protection/slew defaults to `0x12`--`0x14` and `0x16` from vendor-only DT
  properties; those writes are not required for a read-only mainline probe.
- The vendor RT5735 path configures I²C7's GPU-PM clock and has a separate
  SDA-low recovery GPIO workaround. Neither is evidence that a generic
  regulator driver should manipulate GPIOs implicitly.
- The focused Gemini DTB build also exposed an existing board-DTS label drift:
  the MT6351 node is labelled `pmic` in the SoC DTS while the board override
  referred to the nonexistent `mt6351regulator` label. Patch 51 corrects that
  reference as part of making the disabled-only board description buildable.

## Linux 7.1.3 comparison

Linux 7.1.3 has no RT5735 driver or binding. Its FAN53555 driver uses a
different identity and register contract; reusing it by name would hide the
RT5735 product-ID check and protection fields. The recovered VSEL0 path maps
cleanly to a standard single-output `regulator_desc` with linear voltage
selectors, regmap enable/disable, status, and active-discharge operations.

The GPU node remains disabled, so this provider should initially be added as a
disabled-only board resource. A future Panfrost consumer can request the
external rail only after the RT5735 identity, board wiring, and safe OPP table
are verified together.

## Conclusion

`inconclusive` for hardware runtime, but `confirmed` that the Gemini's external
GPU buck is a distinct RT5735 contract and warrants a dedicated mainline
regulator provider. No voltage transition or I²C write was attempted.

## Follow-up

Patch 51 now adds the minimal standard RT5735 regulator driver, YAML binding,
and disabled-only Gemini I²C7 node using the recovered product ID and VSEL0
register map. The focused provider compile, binding check, and Gemini DTB build
passed in the VM. The complete 51-patch build recorded at the time also passed
as package
`linux-7.1.3-gemini-a3270f43cdfa`; its patchset SHA-256 is
`a3270f43cdfa51e61cefa6ba5ebbb353fa1c766f959aa9f380914cd88a9ccb42`, its
merged configuration SHA-256 is
`34ecccb066354cf1644d3f4f0146f36b7a3f7085389599c13d997ed29eef48fa`, and its
Gemini DTB checksum is
`766c1855327b4d99ef531ae4b4b49f074d853b9ca5c25585325577b34de80899`.

Runtime probe and voltage changes still require a recovery path and explicit
hardware opt-in. The next gate is attaching the external rail to a Panfrost
node only after reset ownership, board wiring, and a safe OPP are established.
