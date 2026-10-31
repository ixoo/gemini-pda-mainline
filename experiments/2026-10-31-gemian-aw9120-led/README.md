# Experiment: AW9120 LED controller and Gemian usage

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-31-gemian-aw9120-led` |
| Status | `completed` for the static driver, userspace, register and instruction-set study; no hardware access |
| Subsystem | AW9120 20-channel LED controller, vendor kernel `/proc` driver, Gemian `gemian-leds`, Android lights HAL boundary |
| Device variant | Planet Computers Gemini PDA, MT6797X, vendor Android/Gemian 3.18 stack |
| Date(s) | 2026-10-31 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | M4 local interaction (indicator LEDs) |

## Question or hypothesis

How does the Gemini drive its AW9120 LED controller, what does the vendor kernel
expose, how does Gemian use it, and is there any firmware image involved?

The hypothesis was that the controller is programmed entirely through registers
and a volatile SRAM instruction program, with no downloadable firmware, and
that Gemian reaches it through a private `/proc` ABI rather than the LED class.

## Provenance and environment

- Vendor kernel commit `8cfe6596a503612e3332d9c26e292a19525a7f07`:
  `drivers/misc/mediatek/aw9120/aw9120_led.c`,
  `drivers/misc/mediatek/aw9120/aw9120_reg.h`,
  `drivers/misc/mediatek/leds/`, `arch/arm64/boot/dts/mt6797.dtsi`,
  `arch/arm64/boot/dts/aeon6797_6m_n.dts`.
- Public `gemian/gemian-leds` at commit
  `02e05085e680d8be51722351a462bf3081e6aa03` (version 0.2, also the installed
  package version per the userspace inventory).
- AW9120 data sheet V1.4 (Feb 2019), public copy at
  <https://static.chipdip.ru/lib/858/DOC014858495.pdf>. Read only; no text is
  copied here beyond register and instruction facts.
- Shipped Gemian device tree (private extraction) containing the `&i2c3`
  `aw9120_led@2c` child absent from the public board source.
- Retained Gemian boot logs and the live I2C client list:
  [i2c reuse audit](../2026-07-14-upstream-mt6797-coverage-audit/results/i2c-mt6797-controller-reuse-20260714.txt).
- Live baseline: [Gemian hardware baseline](../../docs/hardware/gemini-gemian-baseline.md#aw9120-indicator-leds).

## Safety assessment

Read-only. No I2C transfer, GPIO change, `/proc` write, LED activation, or
firmware access. The private data sheet and extracted DTS stayed outside Git;
only independently established register facts and public source references are
recorded.

## Procedure

1. Read the vendor platform/I2C driver, its `/proc` handlers, and the register
   header.
2. Reconcile the public and shipped device trees and the live I2C client list.
3. Decode the data-sheet register file and SRAM instruction formats used by the
   vendor programs.
4. Read `gemian-leds` service, D-Bus interface, `LightState` update path,
   `ConnectionWatcher`, and packaged scripts.
5. Compare the Android lights HAL boundary with the Gemian daemon paths.
6. Check the firmware inventory for an AW9120 image.

## Observations

- Full inventory:
  [AW9120 driver and userspace inventory](results/aw9120-driver-and-userspace.md).

Decisive observations:

1. The controller is I2C3 `0x2c`, chip ID `0xb223`, enabled by active-high
   GPIO245 PDN. The public DTS has only the platform/pinctrl node; the shipped
   DTS adds the I2C child, which is why the live kernel binds `3-002c`.
2. The vendor driver registers a platform driver and an I2C driver with the
   same compatible, creates three mode-`0777` `/proc` nodes, and exposes no LED
   class device. Register access is one big-endian 16-bit register per I2C
   transaction.
3. The AW9120 has no firmware store. Its 256x16-bit SRAM program is volatile;
   Gemian reloads it on every state change, and the vendor driver contains a
   fixed seven-instruction breath program.
4. `gemian-leds` is a systemd/D-Bus daemon that writes `/proc/aw9120_reg` for
   the 20-channel controller and `/sys/class/leds/{red,green}/brightness` for
   the MT6351 PMIC ISINK pair. It implements caps lock, the five-block
   animations, torch, call indication, and ConnMan `Powered` indicators.
5. The Android lights HAL writes the standard LED-class paths and never
   references the AW9120 `/proc` nodes. The AW9120 array is therefore a
   Gemian-only userspace surface in the observed stack.
6. Charging and low-battery indication are not implemented: `powerState` is
   never assigned, and there is no battery or charger watcher.
7. The daemon's IMAX packing rotates each channel's 3-bit current code by one
   position relative to the data sheet. The two uniform maps it uses today hide
   the error; a future per-channel map would not.
8. `SetTorch` sets all 20 channels to 24.5 mA and full PWM, then turns off only
   outputs 16-18. That is a high-current, all-array state, not a single
   illuminator.

## Analysis

The AW9120 is a register-and-SRAM device, not a firmware device. The vendor
kernel driver is a thin, unsafe private ABI over I2C; all policy, timing, and
animation logic lives in the Gemian daemon (or in the driver's fixed breath
program). This split explains why the controller has no `/sys/class/leds`
entry: the only generic userspace consumer is Android's lights HAL, and it
targets the PMIC red/green pair instead.

The SRAM program is the interesting part: it gives autonomous fades, waits, and
loops at 32 kHz without host involvement, which is why the daemon can reload a
whole animation once and then leave the bus idle. It also means the LED state
does not survive a PDN reset, and no persistent image exists to preserve.

The mainline path should not reproduce the `/proc` interface or its unbounded
copies. A small regmap LED-class/multicolor driver with an enable GPIO and
direct PWM is enough for the indicators; SRAM animations can remain a later
feature without blocking basic LED support.

## Conclusion

`confirmed`, scoped to the vendor source, public daemon source, shipped DTS,
retained boot logs and data sheet: the wiring, driver structure, `/proc` ABI,
register map, SRAM instruction formats, channel map, daemon behavior, Android
boundary, and the absence of AW9120 firmware.

Not established: physical mapping of PMIC red/green versus AW9120 outputs
19/20, actual currents and brightness, suspend behavior, runtime LED
appearance, and whether an external Gemian component calls `SetCapsLock`.

## Follow-up

- Durable summary: [AW9120 indicator LEDs](../../docs/hardware/aw9120-led.md).
- Next discriminating step: read the live `/proc/aw9120_reg` dump and the
  class LED `max_brightness` values without writing, then light one known
  channel (block 1 green, 3.5 mA, low PWM) in an attended session.
