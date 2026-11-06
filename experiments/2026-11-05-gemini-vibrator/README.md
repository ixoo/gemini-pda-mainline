# Experiment: the vibration motor on the MT6351 VIBR LDO with regulator-haptic

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-05-gemini-vibrator` |
| Status | `planned`: patch 0585 and the module are built; V1 waits for the next batched image |
| Subsystem | MT6351 VIBR LDO, upstream `mt6351-regulator` and `regulator-haptic` |
| Device variant | Planet Computers Gemini PDA, MT6797X, boot2 station |
| Date(s) | 2026-11-05 |
| Investigator(s) | project session, device custody with the custodian session |
| Tracking issue | vibration motor, not yet listed in [hardware support](../../docs/HARDWARE_SUPPORT.md) |

## Question or hypothesis

Does the upstream `regulator-haptic` driver, on the MT6351 VIBR LDO held at
2.8 V, run the Gemini's vibration motor through the standard input
force-feedback interface, and stop it when the effect ends?

Hypothesis: the motor is wired straight to the VIBR LDO output. Switching the
LDO enable bit at 2.8 V is the whole protocol, as in the vendor driver, so the
owner feels each pulse and the LDO reads disabled afterwards.

## What the sources establish

All vendor references are to Gemian's GPL kernel,
[gemini-linux-kernel-3.18](https://github.com/gemian/gemini-linux-kernel-3.18)
at `8cfe6596a503`.

| Fact | Kind | Source |
| --- | --- | --- |
| The Gemini board DT has one `mediatek,vibrator` node, `vib_timer = <25>`, `vib_limit = <9>`, `vib_vol = <5>` | vendor DT | `arch/arm64/boot/dts/aeon6797_6m_n.dts` |
| The board DT is shared by the Gemini variants; there is no per-variant vibrator node | vendor DT | same file |
| Gemian's running config has `CONFIG_MTK_VIBRATOR=y` | owner's unit | [active Gemian config](../2026-07-23-gemian-a72-owner-observer/inputs/active-gemian.config) |
| `vib_vol = 5` selects 2.8 V: VIBR's table is 1.2, 1.3, 1.5, 1.8, 2.0, 2.8, 3.0, 3.3 V | vendor source | `drivers/misc/mediatek/power/mt6797/pmic.c` (`mt6351_VCAM_AF_voltages`, used for `vibr`) |
| Gemian's boot log on this unit reports `vibr: 1200 <--> 3300 mV at 2800 mV` | observed, retained private Gemian boot log | |
| At init the driver writes `RG_VIBR_VOSEL` once; on and off only write `RG_VIBR_EN` | vendor source | `drivers/misc/mediatek/vibrator/mt6797/vibrator.c`, `vibrator_drv.c` |
| `RG_VIBR_EN` is bit 1 of `LDO_VIBR_CON0` (`0x0a3a`); `RG_VIBR_VOSEL` is bits 10:8 of `VIBR_ANA_CON0` (`0x0ae6`) | vendor header | `drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/upmu_hw.h` |
| Status bits: `EN_STATUS_VIBR` is bit 15 of `EN_STATUS2` (`0x0210`), `OC_STATUS_VIBR` bit 0 of `OCSTATUS1` (`0x0212`) | vendor header | same |
| No PWM, GPIO, current limit or trim write is involved. `vib_timer` and `vib_limit` are timing: a request between 10 and 24 ms is stretched to 25 ms; any request is capped at 15 s | vendor source | `vibrator_drv.c` |
| LK pulses the motor for 200 ms at power-on, outside charging and alarm modes | LK source | [LK behaviour](../../docs/hardware/lk.md) |

The upstream `mt6351-regulator` driver's `ldo-vibr` uses the same enable bit
(`MT6351_LDO_EN`, bit 1 of `0x0a3a`), the same voltage field (bits 10:8 of
`0x0ae6`) and the same eight-entry table. `regulator-haptic` turns that
regulator on for a non-zero force-feedback magnitude and off for zero. With
`min-microvolt` equal to `max-microvolt` every magnitude asks for 2.8 V, which
is the vendor's single level. The protocol matches, so no new driver is needed.

Not established: the motor's rated voltage and current, and whether the PMIC
over-current status ever trips with it. The vendor sets no limit beyond the
LDO's own protection.

## Implementation

- [0585](../../patches/proposals/0585-arm64-dts-mediatek-gemini-station-describe-the-vibra.patch)
  describes `ldo-vibr` held at 2.8 V and a `regulator-haptic` node on it, in the
  station DT. This needs a new image; it is waiting to be batched.
- `CONFIG_INPUT_REGULATOR_HAPTIC=m` in the station fragment. `INPUT_FF_MEMLESS`
  is already built in. Nothing loads the module.
- [`rumble.c`](rumble.c) plays one full-strength `FF_RUMBLE` effect for 10 to
  300 ms on a device named `regulator-haptic`, waits for it to end, removes it
  and closes the device. Built static for aarch64 with
  `gcc -static -O2 -Wall -Wextra -o rumble rumble.c`.

At boot, with 0585 and without the module, the regulator core only sets VIBR's
voltage field to 2.8 V, the value Gemian also sets, and the LDO stays off.

## Checks before the device

- The station DTB builds with 0585 and `dt-validate` reports nothing for the
  new nodes; checkpatch reports only the missing sign-off.
- `rumble` builds without warnings and refuses a bad length or a non-input
  device.
- Buildbox package validated; see Provenance below.

## Provenance

- Patch revision: 0585 on top of the station series.
- Buildbox build `a1c0560e`, profile `mt6797-a53-station-a72`, `BUILD_MODULES=1`,
  756 patches, package `445e8b8d…`, patchset `e6ef244a…`, config `6b86c0b3…`,
  `Image.gz` `5229086f…`; validation passed. `regulator-haptic.ko` `2bc8d3af…`,
  station DTB `c017c972…` with both new nodes. `rumble` static aarch64 build
  `dd9feb5f…`. Built, not booted.

## Safety assessment

The only hardware effect is the VIBR LDO switched on at 2.8 V, the vendor's
voltage, in pulses of at most 300 ms, at most 1 s of motor time in all. No
radio, firmware, calibration, partition or other regulator action. Closing the
input device or removing the module turns the LDO off. The owner holds the
device and reports what they feel; nothing is judged by colour.

## V1 procedure

Needs the next batched image containing 0585 and its `regulator-haptic.ko`
(`kernel/drivers/input/misc/`), both from the same Buildbox package, plus
`rumble` at the hash in the request.

1. Identity: `uname -a`, boot id, the image's `station.json` match.
   Ask the owner whether the device buzzed at the boot2 power-on (LK's 200 ms
   pulse).
2. Before loading: `ls /proc/device-tree/haptic`; for the regulator whose
   `name` is `vibr` under `/sys/class/regulator/`, read `state`,
   `microvolts`, `num_users`. Expected: `disabled`, `2800000`, `0`.
3. `insmod regulator-haptic.ko`; new dmesg lines; find the
   `/sys/class/input/event*/device/name` that reads `regulator-haptic`.
4. Owner holds the device. `rumble /dev/input/eventN 100`. Owner: felt or not.
   Then read the regulator `state`: expected `disabled`.
5. `rumble /dev/input/eventN 300 & usleep 150000; cat .../state; wait` (`sleep 0.15` if busybox has no `usleep`).
   Expected `enabled` during the pulse, owner feels a longer pulse, then
   `disabled`.
6. Three pulses of 100 ms, 1 s apart. Owner counts them.
7. `rmmod regulator_haptic`; regulator `state` `disabled`. `insmod` once more,
   one 100 ms pulse, `rmmod`. Dmesg since step 3.

Motor time in all: 100 + 300 + 300 + 100 = 800 ms.

## Stop list

Stop, record and send back at once, with no retry, if:

- the motor keeps running after an effect ends: `rmmod regulator_haptic`; if it
  still runs, `poweroff`;
- the regulator reads `enabled` with no effect playing;
- dmesg shows a regulator, PMIC wrapper or over-current error;
- the device or the motor area gets warm;
- probe fails: no further pulses this boot.

## Decision table

| Result | Meaning | Next |
| --- | --- | --- |
| All pulses felt with the right lengths and count, `disabled` after each, reload works | The motor runs from VIBR at 2.8 V through `regulator-haptic` | Record it as supported; consider loading the module from init |
| Not felt, `enabled` during the pulse | The LDO switches but the motor does not run at this level or is not on VIBR | Owner's answer on the LK power-on buzz decides: buzz means the wiring holds, so read the PMIC registers through a reviewed path; no buzz means look for another motor path |
| Not felt, `disabled` during the pulse | The effect does not reach the regulator | Software fault; debug without further pulses |
| Probe fails or no `vibr` regulator | DT or regulator registration problem | Read dmesg; fix before another test |
| Motor does not stop | Unexpected; possible enable held elsewhere | Stop list; diagnose before any further pulse |

## Observations

None yet.
