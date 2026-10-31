# AW9120 LED controller and Gemian usage inventory

Scope: the AWINIC AW9120 20-channel LED controller on the Gemini PDA, its
vendor kernel interface, the Gemian `gemian-leds` daemon, the Android-side LED
boundary, and the mainline gap. Vendor paths are relative to commit
`8cfe6596a503612e3332d9c26e292a19525a7f07`; daemon paths to
`gemian-leds` commit `02e05085e680d8be51722351a462bf3081e6aa03`.

## 1. Identity and wiring

| Item | Value |
| --- | --- |
| Controller | AWINIC AW9120, 20 constant-current channels with 256x16-bit SRAM |
| Bus | I2C3, 7-bit address `0x2c`, 400 kHz |
| Chip ID | Register `0x00` reads `0xb223` |
| Enable/reset | GPIO245, active-high PDN (low = shutdown) |
| Interrupt | INTN pin exists but is not wired to an IRQ in this design |
| Stack default current | code `1` = 3.5 mA per channel; maximum code `7` = 24.5 mA |
| SRAM | 256 instructions, 16 bit each, volatile; reloaded over I2C |

- The public `mt6797.dtsi` declares a platform node
  `aw9120@ { compatible = "mediatek,aw9120_led"; }` with no `reg`
  (`arch/arm64/boot/dts/mt6797.dtsi:4045-4047`). The board DTS attaches the
  PDN pinctrl states to it (`aeon6797_6m_n.dts:641-666`).
- The shipped Gemian DTS adds the actual I2C child under `&i2c3`:
  `aw9120_led@2c { compatible = "mediatek,aw9120_led"; reg = <0x2c>; }`.
  That child is absent from the public board source. The live client list
  confirms `3-002c:aw9120_led/aw9120_led`.
- I2C3 is shared with the sub-camera (`0x36`), sub-camera AF (`0x0c`), and the
  unbound HDMI/EDID clients (`0x39`, `0x50`). A probe must address only
  `0x2c`.
- The live boot log records platform probe at ~0.685 s, I2C probe at
  ~1.371 s, PDN pulse, and chip ID `0xb223` at ~1.403 s.

## 2. Vendor kernel driver structure

`drivers/misc/mediatek/aw9120/aw9120_led.c` is unusual: one source registers
both a platform driver and an I2C driver with the same compatible string.

- Platform probe (`aw9120_led_probe`, line 522) resolves the `aw9120_default`,
  `aw9120_pdn_high`, and `aw9120_pdn_low` pinctrl states, then calls
  `i2c_add_driver()`.
- I2C probe (`aw9120_i2c_probe`, line 445) stores the client, calls
  `aw9120_hw_on()` (PDN low 5 ms, high 5 ms), retries register `0x00` up to five
  times for `0xb223`, and creates three `/proc` entries with mode `0777`:
  `aw9120_value`, `aw9120_reg`, `aw9120_operation`.
- There is no LED-class or input device, no `dev_pm_ops`, and no use of the
  INTN pin. PDN is pulsed only at probe.
- Register access is one transaction per register: an 8-bit address followed
  by a big-endian 16-bit value for writes; a 1-byte address write followed by a
  2-byte read for reads (`i2c_write_reg` line 134, `i2c_read_reg` line 165).
  There is no auto-increment and no burst transfer.

### 2.1 `/proc` ABI

| Node | Write | Read |
| --- | --- | --- |
| `aw9120_value` | ASCII `0` off, `1` on, `2` breath; any other first byte off | none |
| `aw9120_reg` | ASCII `"0xADDR 0xDATA"`, one 16-bit register write | dumps registers `0x01`-`0x7e` |
| `aw9120_operation` | ASCII `"LED R G B"` hex, LED 1-7, sets three 3-bit IMAX codes | none |

The `aw9120_value` ON path uses IMAX `0x1111` on all five registers (3.5 mA per
channel), enables all 20 channels, selects I2C control (`CTRS1=0x0FFF`,
`CTRS2=0x00FF`), then writes `CMDR=0xBFFF` (broadcast PWM 255). The breath path
loads a fixed seven-instruction SRAM program.

Kernel-side defects worth recording before any reuse: `aw9120_value_proc_write`
copies an unbounded `count` into a 16-byte stack buffer, and the two write
handlers pass the user pointer directly to `sscanf` without
`copy_from_user`. This ABI is not a model for an upstream driver.

## 3. Register map (used subset)

| Addr | Name | Meaning |
| --- | --- | --- |
| `0x00` | IDRST | Chip ID `0xB223`; write `0x55AA` for software reset |
| `0x01` | GCR | Bit 0 `LEDE`, global LED-driver enable |
| `0x50` | LER1 | Enable bits for LEDs 1-12 |
| `0x51` | LER2 | Enable bits for LEDs 13-20 |
| `0x52` | LCR | Dimming curve; default `00` = natural log, `01` = log10, `1x` = linear |
| `0x53` | PMD (driver PMR) | Bits 1:0 `PROGMD`: `00` load via I2C, `01` reload+run, `10` run |
| `0x54` | RMD (driver RMR) | Bits 1:0 `RUNMD`: `00` hold, `01` step, `10` run, `11` repeat |
| `0x55` | CTRSR1 | LEDs 1-12 source: 0 = SRAM, 1 = I2C |
| `0x56` | CTRSR2 | LEDs 13-20 source: 0 = SRAM, 1 = I2C |
| `0x57`-`0x5b` | IMAX1-5 | Four 3-bit current codes per register |
| `0x5f` | SADDR | SRAM start address |
| `0x60` | PCR | SRAM program counter |
| `0x61` | CMDR | Immediate instruction applied to I2C-controlled channels |
| `0x62`-`0x65` | RA-RD | ALU registers, read-only |
| `0x66`-`0x6d` | R1-R8 | Temporary registers, read-only |
| `0x6e`-`0x6f` | GRPMSK | Global broadcast mask |
| `0x7d` | WP | SRAM write protection |
| `0x7e` | WADDR | SRAM load address |
| `0x7f` | WDATA | SRAM load data |

IMAX packing (one register): bits 14:12 = channel 4, 10:8 = channel 3,
6:4 = channel 2, 2:0 = channel 1 of that group. Current code: `000` 0 mA,
`001` 3.5 mA, `010` 7.0, `011` 10.5, `100` 14.0, `101` 17.5, `110` 21.0,
`111` 24.5 mA.

## 4. SRAM instruction set

The controller executes one instruction per 32 kHz clock (31.25 us). The
formats used by the vendor stack:

| Encoding | Instruction | Meaning |
| --- | --- | --- |
| `0x00xx` | `JP addr` | Immediate jump to PC = `addr` |
| `0x04xx` | `JPZ addr` | Jump if Rz = 0 |
| `0x3800 \| Pre<<10 \| T` | `WAITI` | Wait `T` x (0.5 ms if Pre=0, 16 ms if Pre=1), `T` 0-1023 |
| `0x8000 \| Ch<<8 \| Pre<<6 \| Im` | `SETSTEPTMRI` | Ramp step time = (`Im`+1) x `Pre`, `Im` 0-63 |
| `0xA000 \| Ch<<8 \| Im` | `SETPWMI` | Set channel PWM to `Im` 0-255 |
| `0xE000 \| Ch<<8 \| Im` | `RAMPI` fade-in | Fade in over `Im` steps |
| `0xC000 \| Ch<<8 \| Im` | `RAMPI` fade-out | Fade out over `Im` steps |

`Ch = 0x1f` is the broadcast channel: it applies to every channel whose
CTRSR bit is 0 (SRAM-controlled). `Ch = 0x1e` targets the GRPMSK-selected
subset. The last instruction of a program is normally a bare `JP` address.

The vendor driver's fixed breath program decodes as:

| PC | Word | Decode |
| --- | --- | --- |
| 0 | `0xBF00` | all channels PWM 0 |
| 1 | `0x9F05` | broadcast ramp step 3 ms |
| 2 | `0xFFFA` | broadcast fade in, 250 steps (750 ms) |
| 3 | `0x3C7D` | wait 125 x 16 ms = 2.0 s |
| 4 | `0xDFFA` | broadcast fade out, 250 steps (750 ms) |
| 5 | `0x3CBB` | wait 187 x 16 ms = 2.99 s |
| 6 | `0x0002` | jump to PC 2 |

## 5. The Gemian daemon

`gemian-leds` 0.2 is a systemd D-Bus service:

- unit `gemian-leds.service`: `Type=dbus`, bus name
  `org.thinkglobally.Gemian.LEDs`, `ExecStart=/usr/sbin/gemian-leds`,
  `Wants/After=lxc-android-config.service`, `Before=repowerd.service`.
- D-Bus object `/org/thinkglobally/Gemian/LEDs`, interface
  `org.thinkglobally.Gemian.LEDs`. Policy is installed in
  `/etc/dbus-1/system.d/`.
- Methods: `SetCapsLock(b)`, `SetLEDBlockStep(uuuu)`,
  `ClearLEDBlockAnimation()`, `PushLEDBlockAnimation()`, `SetTorch(bu)`,
  `SetCall(bb)`.
- Animation scripts are installed in `/usr/share/gemian-leds/scripts` and call
  those methods through Python D-Bus.

### 5.1 Hardware paths

`LightState` writes two independent hardware surfaces:

- `/proc/aw9120_reg`: text `"0xADDR 0xDATA"` per register. Every LED state
  change reloads the whole AW9120 configuration and SRAM program this way.
- `/sys/class/leds/red/brightness` and `/sys/class/leds/green/brightness`:
  values `0` or `1`. These are the MTK LED-class entries backed by MT6351
  PMIC ISINK0/ISINK1 (`led_mode = 3` = PMIC, `data = 1/2` in the board DTS),
  not AW9120 channels. They are used only for call indication.

The Android `lights.mt6797.so` HAL writes the same `/sys/class/leds/{red,green,
blue}/...` family (plus backlight entries) and never references the AW9120
`/proc` nodes. The AW9120 block is therefore a Gemian-only surface in the
observed stack; the PMIC red/green pair has two possible writers.

### 5.2 Update sequence

For every state change the daemon:

1. writes `GCR=0` (disable outputs);
2. computes the five IMAX registers from a 60-bit current map (default all
   `001` = 3.5 mA; torch all `111` = 24.5 mA);
3. writes `LER1=0x0FFF`, `LER2=0x00FF`, `CTRS1=0`, `CTRS2=0`
   (all channels enabled and SRAM-controlled);
4. writes `GCR=1`;
5. holds the SRAM (`PMD=0`, `RMD=0`), sets `WADDR=0`;
6. writes the program, starting with `0x9F03` (broadcast ramp step 2 ms) and
   `0xBF00` (all off);
7. appends state (caps, connectivity, call), then the queued animation steps,
   then either a frame delay or a default wait/blink sequence, then a `JP` to
   the loop start;
8. writes `SADDR=0`, `PMD=1` (reload and execute), `RMD=2` (run).

The SRAM program then runs autonomously; the host is not involved until the
next update. A power-down reset or `PDN` low clears it.

### 5.3 Channel mapping

The daemon's block numbering maps to AW9120 channels as follows:

| UI block | AW9120 outputs (1-based) | `SETPWMI` channel field |
| --- | --- | --- |
| 1 | 1 / 2 / 3 | `0x00` / `0x01` / `0x02` |
| 2 | 13 / 14 / 15 | `0x0c` / `0x0d` / `0x0e` |
| 3 | 4 / 5 / 6 | `0x03` / `0x04` / `0x05` |
| 4 | 7 / 8 / 9 | `0x06` / `0x07` / `0x08` |
| 5 | 10 / 11 / 12 | `0x09` / `0x0a` / `0x0b` |

The extra RGB indicator is outputs 16-18 (SRAM channels 15-17). Caps lock is
output 19 (SRAM channel 18) red at PWM `0xa0`; the `powerState` field would
drive output 20 (SRAM channel 19) blue at `0xff`, but nothing ever sets
`powerState`. Call indication combines output 16 or 17 (SRAM channel 15 or 16)
with the PMIC red/green pair.

### 5.4 Implemented behavior

- Caps lock: `SetCapsLock` toggles channel 18 red at `0xa0`.
- Connectivity: `ConnectionWatcher` reads ConnMan technology objects
  `/net/connman/technology/{wifi,bluetooth,cellular}` and watches `Powered`.
  Cellular drives extra-RGB red `0xa0`, WiFi green `0x50`, Bluetooth blue
  `0xc0` (or `0xff` without WiFi). With no explicit animation delay, the program
  blinks each active colour for 128 x 16 ms (2.048 s) per loop.
- Call: `SetCall(earpiece,leftUp)` lights extra-RGB red `0xa0` plus PMIC green,
  or extra-RGB green `0x50` plus PMIC red, depending on `leftUp`.
- Torch: `SetTorch(on,duration)` sets all IMAX codes to `111` (24.5 mA), clears
  queued steps, adds a broadcast `SETPWMI` at 255, and updates. The default
  tail then turns off outputs 16-18 only, leaving outputs 1-15 and 19-20 at
  full current. `duration` is milliseconds and is a daemon-side timer; zero
  means until the next call.
- Block animation: steps are accumulated with
  `SetLEDBlockStep(led 1-5, colour 0/1/2, type 0/1/2/3, value)`. Type 0 is
  PWM 0-255, types 1/2 fade in/out over `value` steps at the fixed 2 ms step
  time, type 3 is a frame delay of `value` x 16 ms (0-1023).

### 5.5 Not implemented

- No battery, charging, or low-battery handler exists. `powerState` is dead
  code despite the README's planned charging and low-battery indicators.
- The connectivity state is ConnMan's radio `Powered` flag, not link or
  traffic state.
- No suspend/resume handling; the SRAM program and PDN state are untouched
  across system suspend.
- The IMAX packing in `maxLED()` applies LED n's 3-bit code to the next
  channel's field (`(led % 4) * 4` instead of `((led - 1) % 4) * 4`). With the
  two uniform power maps used today (`001` everywhere or `111` everywhere)
  this rotation is invisible; a future per-channel current map would land on
  the wrong outputs.
- The daemon writes PMIC red/green `0` on every non-call update, so it can
  override an Android-side notification on the same class devices.

## 6. Firmware position

There is no AW9120 firmware image. The controller has no non-volatile program
store; its effect program is the volatile 256x16-bit SRAM loaded over I2C. The
only persistent software is the vendor kernel driver. Gemian rebuilds the SRAM
program at runtime from `gemian-leds`; the vendor driver embeds the fixed breath
program above. Neither is present in `/etc/firmware` or the vendor firmware
directory.

## 7. Mainline gap

Linux 7.1.3 has no AW9120 driver and no matching compatible. A mainline driver
would need a new I2C binding at `0x2c` with an active-high `enable-gpios`
(GPIO245), a regmap for the 8-bit-address/16-bit-big-endian register file, and
an LED-class or multicolor exposure. Direct PWM through `CTRS=1` plus `CMDR` is
sufficient for indicators; the SRAM animation engine is optional and should
not be the first target. The `/proc` ABI and its unchecked copies must not be
carried forward.

## 8. Limits

- Static source and data-sheet reading plus retained boot-log/sysfs evidence;
  no register was read or written in this study and no LED was observed.
- The installed `gemian-leds` binary was not disassembled; the reconstruction
  uses the public 0.2 source at the commit matching the installed version.
- The physical identity of the PMIC red/green pair versus AW9120 outputs 19/20
  is unresolved; the daemon drives both paths in different states.
- Actual current, brightness, thermal rise, and suspend behavior were not
  measured.
