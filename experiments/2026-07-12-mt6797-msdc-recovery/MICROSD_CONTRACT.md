# microSD card-detect and power contract

Offline follow-up, 2026-09-09. This narrows the MSDC1 implementation contract;
it does not establish mainline card detection, enumeration, or rail behavior.
No device access, GPIO sampling, PMIC transaction, boot, or storage I/O was
performed for this follow-up. Retained binary analysis ran in the RE VM.

## Card detection

The retained board DTB's `/mtk-msdc.0/msdc1@11240000` has `cd_level` encoded
as the single byte `01`, and `cd-gpios` as cells `0x0c 0x43 0x00`.
The one-byte encoding matters: the compiled parser calls
`of_property_read_u8_array()` with count 1, not a 32-bit-cell reader.
It separately reads cell 1 of `cd-gpios` into a global GPIO number.

The compiled `msdc_ops_get_cd()` obtains the raw GPIO value through
`gpio_to_desc()` and `gpiod_get_raw_value()`. With the nonzero `cd_level`
byte, a high raw value means present and a low value means absent. The
bad-card suppression branch can subsequently force absence. This establishes
the retained driver's interpretation, not the physical switch's measured
polarity. The vendor GPIO flags alone do not establish that interpretation.

In pinned upstream MMC code, `mmc_of_parse()` requests card detection with
`override_active_level=false`; `mmc_gpio_get_cd()` returns the descriptor's
logical value. `cd-inverted` toggles descriptor polarity. Consequently,
GPIO67 with `GPIO_ACTIVE_HIGH` and **no** `cd-inverted` expresses the retained
high-means-present convention. Adding `cd-inverted` to that description would
reverse it. The existing MT6797 map places GPIO67 on EINT6; these numbers
must not be interchanged.

This is a candidate translation only. A future physical insertion/removal
observation must confirm both levels and event delivery after pin ownership
is established; the previous empty-slot snapshot cannot prove both states.

## Power ownership

The compiled host-1 power callback matches the public source's VMCH card
supply and VMC I/O supply requests at nominal 3.0 V. It programs pad drive,
TDSEL and RDSEL before those requests. The `MSDC_SD_NEED_POWER` flag can keep
the card-supply request on while the I/O-supply request follows the callback's
argument. Regulator requests are not measurements of output voltage.

The retained probe also contains PMIC trim adjustments for host 1:

| Field | Compiled operation on the five-bit value |
| --- | --- |
| VMCH, register `0xace`, bits 4:0 | Subtract 5 with wrap modulo 32 |
| VMC, register `0xae2`, bits 4:0 | Add 5 with wrap modulo 32; save the result as the default |
| VMC in the enabled 1.8 V switch path | Write saved default minus 2 before requesting 1.8 V |

These are code operations, not recovered device calibration values or an
approved sequence to reproduce. The probe does not check the return values
of these trim reads/writes. The public source's voltage commentary does not
prove the electrical effect on this board.

The rail names therefore identify prospective `vmmc` and `vqmmc` consumers,
but do not complete the ownership contract. Before enabling MSDC1, resolve
the initial pad state and whether the standard regulator path can preserve
the required trim state across the actual boot path. A conservative first
card test should exclude 1.8 V switching; that restriction alone does not
resolve the initial 3.0 V power/pad transition. No trim writes or new DT node
are introduced by this investigation.

## Reproduction and identities

Use the private retained primary Gemian boot extraction documented in the
[RTC binary receipt](../2026-07-11-mt6351-pmic-recovery/results/rtc-binary-receipt-20260908.json).
This follow-up rechecked that the reconstructed ELF `.kernel` section equals
the complete Image, whose SHA-256 is
`0570480c28bce1583636a240904df8da3af0b5e5b4bcc6254f5719b42bd723d0`.
The board DTB SHA-256 is
`9e26929563f7682d1f7545d6007f0092c7e085a4edbd6e7be0ac8eaa5159b2f9`.
Read the named properties with `fdtget -t bx` and `fdtget -t x`, respectively.
The parser's string references at `0xffffffc0010d4bf8` and
`0xffffffc0010d4c48` resolve to `cd_level` and `cd-gpios` in that Image.

Disassemble the following symbols with GNU AArch64 objdump. Ends are the next
distinct symbol, exclusive, including any trailing padding. Hash the Image
slice at virtual address minus `0xffffffc000080000`.

| Symbol | Start | End | SHA-256 |
| --- | --- | --- | --- |
| `msdc_ops_get_cd` | `0xffffffc000960578` | `0xffffffc000960698` | `91fd6d43ac577dd75d52506d3ebc55dbf43238b03ba14527cae4c805d0697ea7` |
| `msdc_of_parse` | `0xffffffc000976198` | `0xffffffc000976848` | `66750d819f500f6d20281192f47dbef7665de70f4d51770b5cb0da48ac2bcadd` |
| `msdc_sd_power` | `0xffffffc0009789c8` | `0xffffffc000978af8` | `e959326edd78d6439919f9bb2a325a11334c0bd1046f86759030eecb0655a51a` |
| `msdc_sd_power_switch` | `0xffffffc000978910` | `0xffffffc0009789c8` | `f48cd3ede2d67a14c6bae4f9ab800d7e1c27fcdacb43c8c984985283d7cc1827` |
| `msdc_drv_probe` | `0xffffffc0009622a0` | `0xffffffc000962d28` | `cc1504f5ac6b58b9747b7ed9a4f36bd611dbbd440714123b8fcb0389d0e9089c` |

Public vendor comparison is Planet's tree at
`c5b0be85017ad0c599725e8273842efdbecdd88a`, under
`drivers/mmc/host/mediatek/mt6797/`: `sd.c` SHA-256
`e8cc38b57f18b0a8c8e6476d3c11c333f999326297538d35e7f93585daf63cba`,
and `msdc_io.c` SHA-256
`b87966fb3bb7be7e9c7c273cc58e92e7c19ed6a3b09a503afbaedb529c890e07`.
Upstream comparison is Linux commit
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c`, files
`drivers/mmc/core/host.c`, `drivers/mmc/core/slot-gpio.c`,
`drivers/gpio/gpiolib-of.c`, and
`Documentation/devicetree/bindings/mmc/mmc-controller.yaml`.
Raw binaries and disassembly remain private; only independently described
facts and reproducibility hashes are published.
