# AW9120 indicator LEDs

Scope: the AWINIC AW9120 20-channel LED controller on the Gemini PDA, the vendor
kernel interface, the Gemian `gemian-leds` daemon, and the mainline driver. This is
a source, data-sheet and retained-log study, plus the driver's first device test.

Evidence chronology is in the
[2026-10-31 AW9120 experiment](../../experiments/2026-10-31-gemian-aw9120-led/README.md)
and the [2026-11-04 driver record](../../experiments/2026-11-04-gemini-aw9120-leds/README.md);
live identity is in the
[Gemian hardware baseline](gemini-gemian-baseline.md#aw9120-indicator-leds).

## 1. Identity and wiring

| Item | Value |
| --- | --- |
| Controller | AWINIC AW9120, 20 current sinks, 8-bit PWM, 256x16-bit SRAM |
| Bus | I2C3, address `0x2c`, 400 kHz |
| Chip ID | `0x00` reads `0xb223` |
| Enable | GPIO245, active-high PDN (low = shutdown) |
| Interrupt | INTN exists but is not wired to an IRQ here |
| Current | 8 codes: `001` = 3.5 mA through `111` = 24.5 mA; `000` = off |

The public tree declares only the platform/pinctrl node
(`arch/arm64/boot/dts/mt6797.dtsi:4045`, `aeon6797_6m_n.dts:641-666`). The
shipped Gemian DTS adds `aw9120_led@2c` under `&i2c3`, which is why the live
kernel binds `3-002c` to `aw9120_led`. I2C3 also carries the sub-camera
(`0x36`), sub-camera AF (`0x0c`), and unbound HDMI/EDID clients (`0x39`,
`0x50`), so only `0x2c` is safe to address.

## 2. Vendor kernel driver

`drivers/misc/mediatek/aw9120/aw9120_led.c` registers a platform driver and an
I2C driver under the same `mediatek,aw9120_led` compatible:

- the platform probe resolves the PDN pinctrl states and registers the I2C
  driver;
- the I2C probe stores the client, pulses PDN low/high (5 ms each), polls
  register `0x00` for `0xb223`, and creates `/proc/aw9120_value`,
  `/proc/aw9120_reg`, and `/proc/aw9120_operation` with mode `0777`;
- there is no LED class, input device, PM ops, or INTN use.

Registers are accessed one at a time: 8-bit address plus big-endian 16-bit
value for writes, repeated-start read for reads. There is no auto-increment.

| `/proc` node | Write | Read |
| --- | --- | --- |
| `aw9120_value` | `0` off, `1` on (all channels, 3.5 mA), `2` fixed breath | none |
| `aw9120_reg` | text `0xADDR 0xDATA`, one register write | dump of `0x01`-`0x7e` |
| `aw9120_operation` | `LED R G B` hex, LED 1-7, per-channel current | none |

The write handlers copy an unbounded `count` into a 16-byte stack buffer and
pass user pointers to `sscanf` without `copy_from_user`. The ABI is unsafe and
must not be reproduced upstream.

## 3. Register and instruction model

Key registers:

| Addr | Meaning |
| --- | --- |
| `0x00` | ID `0xB223`; `0x55AA` resets the device |
| `0x01` | GCR: bit 0 enables the LED drivers |
| `0x50`/`0x51` | LER1/LER2: enable LEDs 1-12 / 13-20 |
| `0x52` | LCR: dimming curve, default natural log |
| `0x53` | PMD/PMR: `PROGMD` load/reload/run control |
| `0x54` | RMD/RMR: `RUNMD` hold/step/run/repeat |
| `0x55`/`0x56` | CTRSR1/2: per-channel source, 0 = SRAM, 1 = I2C |
| `0x57`-`0x5b` | IMAX1-5: four 3-bit current codes each |
| `0x5f` | SADDR: program start address |
| `0x61` | CMDR: immediate instruction for I2C-controlled channels |
| `0x7e`/`0x7f` | WADDR/WDATA: SRAM load address/data |

IMAX groups pack four channels per register at bits 14:12, 10:8, 6:4, 2:0.

The SRAM executes one 16-bit instruction per 32 kHz clock. The used formats:

| Encoding | Instruction |
| --- | --- |
| `0x00xx` | `JP addr`, immediate jump |
| `0x3800 \| Pre<<10 \| T` | `WAITI`, `T` x 0.5 ms or 16 ms |
| `0x8000 \| Ch<<8 \| Pre<<7 \| Im` | ramp step time (`Im`+1) x `Pre` |
| `0xA000 \| Ch<<8 \| Im` | set PWM 0-255 |
| `0xE000 \| Ch<<8 \| Im` | fade in over `Im` steps |
| `0xC000 \| Ch<<8 \| Im` | fade out over `Im` steps |

`Ch = 0x1f` broadcasts to all SRAM-controlled channels. A program ends with a
bare `JP` back to its loop start.

## 4. Channel map and Gemian daemon

`gemian-leds` 0.2 is a systemd D-Bus service
(`org.thinkglobally.Gemian.LEDs`, `/usr/sbin/gemian-leds`). It exposes
`SetCapsLock`, `SetLEDBlockStep`, `ClearLEDBlockAnimation`,
`PushLEDBlockAnimation`, `SetTorch`, and `SetCall`.

It writes two surfaces:

- `/proc/aw9120_reg` for the AW9120 array;
- `/sys/class/leds/red|green/brightness` for the MT6351 PMIC ISINK0/ISINK1
  pair (board DTS `led_mode = 3`, PMIC).

On every update it disables GCR, writes the five IMAX registers, enables all
20 channels with CTRS=0 (SRAM control), re-enables GCR, loads a program at
`WADDR=0`, then starts it with `SADDR=0`, `PMD=1`, `RMD=2`. The program starts
with a 2 ms ramp step and all-off, then the state, the animation steps, a
default wait/blink, and a `JP` loop.

| UI block | AW9120 outputs |
| --- | --- |
| 1 | 1 / 2 / 3 |
| 2 | 13 / 14 / 15 |
| 3 | 4 / 5 / 6 |
| 4 | 7 / 8 / 9 |
| 5 | 10 / 11 / 12 |

Outputs 16-18 are the extra RGB indicator. Caps lock uses output 19 red at PWM
`0xa0`; `powerState` would use output 20 blue, but nothing sets it. Call
indication uses output 16 or 17 plus the PMIC red/green pair.

Implemented behavior:

- **Caps lock:** `SetCapsLock` toggles output 19 red.
- **Connectivity:** ConnMan technology `Powered` flags drive extra-RGB red
  (cellular), green (WiFi), and blue (Bluetooth), blinking for 2.048 s per
  active colour.
- **Call:** `SetCall(earpiece,leftUp)` selects red or green on the extra RGB and
  the opposite PMIC class LED.
- **Torch:** all channels at 24.5 mA and PWM 255; the tail turns off only
  outputs 16-18, leaving 17 channels at maximum current. Duration is a
  daemon-side millisecond timer; zero means until the next call.
- **Block animation:** PWM steps, fade in/out over 2 ms steps, and frame delays
  of `value` x 16 ms.

Not implemented: battery, charging, or low-battery indication (`powerState` is
dead), link-level connectivity, suspend/resume handling, and per-channel
current control. The IMAX packing rotates each channel's code by one position
(`(led % 4) * 4`); the two uniform current maps hide it today but a per-channel
map would land on the wrong outputs.

The audited Android `lights.mt6797.so` HAL writes the standard LED-class paths
and never references the AW9120 `/proc` nodes, so the array is a Gemian-only
surface in the observed stack. Both Gemian and Android can write the PMIC
red/green pair, and the daemon clears it on every non-call update.

## 5. Firmware position

The AW9120 has no firmware image and no non-volatile program store. Its effect
program is the volatile 256x16-bit SRAM loaded over I2C; Gemian rebuilds it at
runtime, and the vendor driver embeds a fixed seven-instruction breath program.
Neither appears in `/etc/firmware` or the vendor firmware directory. A PDN
reset clears the program and returns the outputs to their default state.

## 6. Physical position

From the [device test](../../experiments/2026-11-04-gemini-aw9120-leds/README.md#observations),
device closed with the logo strip at the top:

| LED | AW9120 outputs | Position |
| --- | --- | --- |
| `rgb:indicator-5` to `-1` | 10-12, 7-9, 4-6, 13-15, 1-3 | Five spots around the middle of the cover, in this order from left to right |
| `rgb:indicator-6` | 16-18 | Cover, far right |
| `red:` and `blue:indicator-7` | 19, 20 | One LED inside, in the strip left of Q, above Tab and Caps; red and blue only |

The enumerators keep the daemon's block numbers, so they count from the right. Each
cover group showed one spot in a photo. Output colours other than 1 and 19 come from
the Gemian daemon, and whether each output lights alone awaits the owner's answer.

Reported, not observed here: the public
[Gemian wiki](https://github.com/gemian/gemian/wiki/LEDs) puts the power LED to the
left of the cover, not on this chip, and the MT6351 `red`/`green` pair beside it. The
[user guide](https://support.planetcom.co.uk/) gives the power LED red, orange and
green while charging.

So the PMIC pair isn't outputs 19/20: those are inside the device, and the pair is
reported outside with no blue. Whether the PMIC pair and the power LED are one package
is unresolved.

## 7. Mainline position

Linux 7.1.3 has no AW9120 driver. The project's `leds-aw9120` module
([0572](../../patches/proposals/0572-leds-rgb-add-a-driver-for-the-AWINIC-AW9120.patch))
probes and drives LEDs on the station at 3.5 mA:

- `awinic,aw9120` at I2C3 `0x2c`, active-high `enable-gpios` on GPIO245, chip ID check;
- each output set by a per-channel `SETPWMI` in `CMDR` with `CTRS=1`. The vendor stack
  only used the broadcast form;
- `GCR.LEDE` is set only while an output is lit: 0.55 mA active against 130 uA standby.
  Configuration survives clearing it;
- the SRAM engine and the `/proc` ABI aren't carried forward.

The station device tree names the LEDs by group without assigning a purpose:
`rgb:indicator-1` to `-5` follow the daemon's block numbers, `rgb:indicator-6` is the
extra RGB, and `red:indicator-7` and `blue:indicator-7` are outputs 19 and 20. By the
owner's choice, `red:indicator-7` defaults to `kbd-capslock`, from patch 0577; the
other LEDs have no default trigger. The default worked on the device, and `timer`
works from userspace. The station's `init` loads the module, from the image after that
check. `phy0rx` and its siblings are listed but unexercised; `hci0-power`
should appear with `CONFIG_BT_LEDS` once Bluetooth is up, and hasn't been seen.

Every output is limited to 3.5 mA, or 70 mA for the chip. From the data sheet's 45 C/W,
a 4.35 V battery and about 1.8 V across a red LED, that heats the chip about 8 C. The
same estimate for Gemian's torch, 17 outputs at 24.5 mA, is about 1 W and 48 C. These
are estimates. All twenty on for 60 s at 3.5 mA moved no thermal zone by more than
0.3 C, though none is near the LEDs and the owner felt it slightly warmer. Don't raise
a limit without a thermal check.

The MT6351 pair needs its own work: upstream's `leds-mt6323` doesn't cover the MT6351.

## 8. Open questions

1. Is the MT6351 red/green pair where the wiki says, separate from outputs 19/20 as
   [section 6](#6-physical-position) infers? The pair hasn't been driven here.
2. Which Gemian component calls `SetCapsLock`?
3. What are the measured currents and brightness, and the thermal rise at higher
   currents, especially for the torch state?
4. Does the array or SRAM program survive suspend, and does PDN glitch on
   resume?

## 9. Evidence index

- Vendor kernel `8cfe6596a503612e3332d9c26e292a19525a7f07`:
  `drivers/misc/mediatek/aw9120/`, `drivers/misc/mediatek/leds/`, and the board
  DTS touch/LED/pinctrl nodes.
- Public `gemian/gemian-leds` `02e05085e680d8be51722351a462bf3081e6aa03`.
- [AW9120 V1.4 data sheet](https://static.chipdip.ru/lib/858/DOC014858495.pdf).
- [Gemian hardware baseline](gemini-gemian-baseline.md#aw9120-indicator-leds),
  [vendor kernel ABI](vendor-kernel-abi.md),
  [Android lights HAL audit](../../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/android-thermal-lights-hal-audit-20260714.txt),
  [live I2C client list](../../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/i2c-mt6797-controller-reuse-20260714.txt).
