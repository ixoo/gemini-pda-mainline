# Experiment: the AW9120 indicator LEDs from a module on the station

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-04-gemini-aw9120-leds` |
| Status | `running`: T1 ran on boot `a41d3aa7`; the driver works on the device. Step 9 and two owner questions are open |
| Subsystem | AW9120 at I2C3 `0x2c`, GPIO245, LED class |
| Device variant | Planet Computers Gemini PDA, MT6797X, boot2 station |
| Date(s) | 2026-11-04 |
| Investigator(s) | project session, device custody with the custodian session |
| Tracking issue | M4 local interaction (indicator LEDs) |

## Question or hypothesis

Can a small module drive every AW9120 output directly over I2C, and where is
each output on the device?

Hypothesis: the chip answers `0xb223` with the camera off, a per-channel `SETPWMI`
written to `CMDR` lights only that output, and the outputs sit as the Gemian wiki
describes. The vendor stack only ever used the broadcast form of `CMDR`, so the
per-channel form is untested here.

Prior reports, not observed by this project:

| Output (1-based) | Gemian's use | Gemian wiki's position |
| --- | --- | --- |
| 1-3 | block 1 red, green, blue | block of five, middle of the cover |
| 13-15 | block 2 | same |
| 4-6 | block 3 | same |
| 7-9 | block 4 | same |
| 10-12 | block 5 | same |
| 16-18 | red cellular, green Wi-Fi, blue Bluetooth | cover, opposite end from the power LED |
| 19 | red caps lock | inside the device |
| 20 | blue, never set | same LED inside |

The wiki puts the PMIC `red`/`green` pair beside the power LED, on the outside.
Output 20 is blue and that pair has no blue, so the open question in the
[hardware document](../../docs/hardware/aw9120-led.md) looks answered: they are
different LEDs. Step 3 checks the inside half of that.

## Provenance and environment

- Linux 7.1.3 with `patches/series-a53-station` through
  [0573](../../patches/proposals/0573-arm64-dts-mediatek-gemini-station-describe-the-indic.patch).
- Driver [0572](../../patches/proposals/0572-leds-rgb-add-a-driver-for-the-AWINIC-AW9120.patch),
  binding [0571](../../patches/proposals/0571-dt-bindings-leds-add-AWINIC-AW9120.patch).
- Register and channel facts:
  [2026-10-31 study](../2026-10-31-gemian-aw9120-led/README.md), AW9120 V1.4 data
  sheet (public, not copied), public
  [Gemian wiki LEDs page](https://github.com/gemian/gemian/wiki/LEDs).

## Compile check

In the dev VM only, against the station series and the
`mt6797-a53-station-a72` fragments:

- `drivers/leds/rgb/leds-aw9120.ko` builds with `W=1` and no compiler warnings.
  `modpost` couldn't check its symbols because no `vmlinux` was built for that tree.
- `scripts/checkpatch.pl --strict -f` on the driver: no problems. On the patches,
  the only complaints are the absent `Signed-off-by` and `MAINTAINERS` entry; a
  sign-off is the owner's to give at upstream submission.
- `dt_binding_check` on the binding and `CHECK_DTBS` on
  `mt6797-gemini-pda-station-a72.dtb`: no AW9120 warnings. The node is in the DTB
  with all 20 outputs at `led-max-microamp = <3500>`.

This doesn't show that the chip responds. No LED has been driven.

## Safety assessment

Touches `0x2c` on I2C3 and GPIO245 only; no other I2C address, radio, regulator,
calibration or partition. The chip holds nothing across a PDN reset.

Current is the only stress. Each output is limited to 3.5 mA in the device tree
and the test doesn't change it, so all twenty draw 70 mA. Worst-case heating,
from the data sheet's 45 C/W, a 4.35 V battery and about 1.8 V across a red LED:
70 mA x 2.55 V = 0.18 W, about 8 C above ambient. The same sum for Gemian's torch,
17 outputs at 24.5 mA, gives about 1 W and 48 C, which is why that state stays out
until it has its own thermal check. Nothing in this test raises a limit.

I2C3 carries the front camera, so don't stream from it during the test. The adapter
serializes transfers, but a failure should have one possible cause.

Probe reset: the driver holds PDN low 5 ms, raises it and waits 5 ms, the data
sheet's minimum. `rmmod` turns the LEDs off and drops PDN.

## Associated code

- [`led-walk.sh`](led-walk.sh) lights each output alone, in output order. It only
  writes LED class files.

## Procedure

Needs an image with 0571-0573 and `CONFIG_BT_LEDS=y`, in the next batched boot, with
the module from the same package. Attended: the owner watches the outside and the
inside of the device. Load budget: two loads this boot. Any probe failure stops the
test with no retry.

The adapter number isn't fixed: `&i2c3` was `4-002c` on T1's image, so find the
device with `ls -d /sys/bus/i2c/devices/*-002c` and use that name below in place of
`N-002c`.

1. Note `dmesg | wc -l`. `insmod leds-aw9120.ko`, exit code, new `dmesg` lines,
   `ls /sys/class/leds`, `ls -l /sys/bus/i2c/devices/N-002c/driver`.

   Expect `rgb:indicator-1` to `-6`, `red:indicator-7` and `blue:indicator-7`, and
   nothing lit.
2. `grep -E '^(00|01|50|51|55|56|57|58|59|5a|5b):' /sys/kernel/debug/regmap/N-002c/registers`.

   Expect `00: b223`, `01: 0000`, `50: 0fff`, `51: 00ff`, `55: 0fff`, `56: 00ff`,
   and `1111` in all five IMAX registers.
3. **Owner step, about 90 s.** Tell the owner there are 20 steps, 4 s each, in order,
   and that each lights one colour in one place. Device open on the desk, so that
   the inside and the cover can both be seen; closing the lid partway is fine.
   `sh led-walk.sh 3`. The owner writes down each step's colour and position, left
   to right as seen from the cover, or "nothing". Also ask: is the inside LED
   where the keyboard's caps lock indicator would be, and is it a separate LED from
   the one beside the power LED?
4. Read `01:` again as in step 2. Expect `0000`: the chip stopped its oscillator.
5. Brightness and mixing on `rgb:indicator-1`, about 5 s each, owner reporting:
   `echo 255 255 255 > multi_intensity` with `brightness` 255, then 64, then 8; then
   `255 80 0` at 255. Then `brightness` 0. Expect three visibly different levels and
   a mixed colour. The PWM curve is the chip's default logarithmic one, as in Gemian.
6. Everything at once, for 60 s: `brightness` 255 on all eight LEDs, multicolor
   ones at `255 255 255`. Read `/sys/class/thermal/thermal_zone*/temp` before and
   after. Owner touches the area around the LEDs: warmer than the rest of the case?
   All off. Expect no visible heating, no I2C error.
7. Triggers from userspace. `cat /sys/class/leds/red:indicator-7/trigger` and send
   the list. Set `timer` on `rgb:indicator-1` for 10 s, then `none`. Set
   `kbd-capslock` on `red:indicator-7`; owner presses Fn+Caps twice on the console;
   then `none`. If Wi-Fi is up, `phy0rx` on `rgb:indicator-6` for 20 s under some
   traffic, then `none`. If `hci0-power` is listed and Bluetooth is up, note it but
   don't start Bluetooth for this.
8. Light `rgb:indicator-1`, then `rmmod leds_aw9120`, exit code. Owner: did it go
   dark? `grep -i 245 /sys/kernel/debug/pinctrl/*/pinmux-pins | head -2`. Load again,
   same checks as steps 1 and 2. Leave it loaded with nothing lit, and no trigger.
9. At the session's next ordinary `poweroff`, light `rgb:indicator-1` first and ask
   the owner whether it stays lit after power off. It's passive: no extra restart.

## Decision table

| Observed | Do |
| --- | --- |
| All steps as expected | Record the position map; correct the DT in the next batch if any group differs; ask the owner for the LED-to-function mapping |
| Chip ID read fails or is wrong | Send output; stop; no retry. Next hypothesis: I2C3's pull-ups or the chip's VIO need a rail that's off with the camera idle |
| Probe passes, registers wrong | Send step 2; stop. The register model is wrong somewhere |
| Registers right, nothing lights | Finish step 4; stop. Next driver: broadcast `CMDR` as the vendor did, and `GCR` held on, through a reload, no boot |
| One step lights the wrong colour or place | Finish; a DT fix |
| One step lights more than one output | Finish; send. The per-channel form doesn't work as read |
| LEDs fail to come back after going dark | The `GCR` gating loses state. Send; next driver keeps `GCR` set |
| Transfer timeout, oops or USB loss | `rmmod` if you can; no more I2C3 this boot; preserve logs |
| Case visibly warm in step 6 | All off; stop; lower the block's duty before anything else |

## Observations

T1: image `c894320e` built from `01bbd719`, boot `a41d3aa7`, module `568ec8ce`,
`led-walk.sh` `a3dcd8ef`. Camera idle, though that boot had used camera DMA earlier.
The custodian ran the test and kept the owner's photos, which stay private.

Deviations from the procedure: the bus was `4-002c`, not `3-002c`, and colour wasn't
judged by eye. The owner wasn't asked to name colours; photos are the only colour
evidence below.

| Step | Result |
| --- | --- |
| 1 | `insmod` rc 0, probe 15627 us, the 8 expected LED devices |
| 2 | `00: b223`, `01: 0000`, `50: 0fff`, `51: 00ff`, `55: 0fff`, `56: 00ff`, `57`-`5b: 1111` |
| 3 | Walk rc 0. Owner: outputs 19 and 20 are two colours on the caps lock LED; the others are a series of LEDs of different colours on the back of the screen |
| 4 | `01: 0000` |
| 5 | Levels 255, 64, 8, rc 0; owner says they looked different. Mix `255 80 0` rc 0, not judged |
| 6 | All on for 60 s. `soc-thermal` 28.9 to 28.7 C, `battery-thermal` 26.66 to 26.75 C, `battery` 26.4 to 26.7 C. Owner: feels slightly warmer. No I2C errors |
| 7 | Triggers listed: `none`, `kbd-capslock`, `timer`, `phy0rx`, `phy0tx`, `phy0assoc`, `phy0radio`. `kbd-capslock` on `red:indicator-7` followed Fn+Caps on and off. `timer` on `rgb:indicator-1` at 500/500 blinked. Wi-Fi wasn't up, so `phy0rx` didn't run. `hci0-power` wasn't listed |
| 8 | Lit `rgb:indicator-1`, `rmmod` rc 0, it went dark. Pin 245 read low and unclaimed. Second `insmod` rc 0, probe 15583 us, steps 1 and 2 the same. Left loaded, nothing lit, no trigger. Kernel not tainted |
| 9 | Pending the next ordinary power off |

Positions from angled phone photos, device closed, logo strip at the top, as a
fraction along the slit. The order is reliable and the spacing is rough; the logo's
centre is about 0.48.

| LED | Fraction |
| --- | --- |
| `rgb:indicator-5` | 0.40 |
| `rgb:indicator-4` | 0.45 |
| `rgb:indicator-3` | 0.47 |
| `rgb:indicator-2` | 0.51 |
| `rgb:indicator-1` | 0.54 |
| `rgb:indicator-6` | 0.88, far right |

Each group at `255 255 255` showed one spot in the photos. The owner first described
`rgb:indicator-1` at white as several positions and colours on one line, then, seeing
the photo, said it might be a single RGB LED.

Colour evidence: output 1 alone looked red in a photo, the only single cover output
photographed. Output 19 looked red, in the strip left of Q, above Tab and Caps. Outputs
19 and 20 together looked violet-blue with a washed-out core.

Asked and not yet answered: whether any walk step lit more than one spot, and whether
the caps lock LED is separate from the light beside the power LED.

## Analysis

The chip answers with the camera off, the register model is right, and writes reach
LEDs through `CMDR`. Clearing `GCR.LEDE` doesn't lose configuration: `01` reads `0000`
after the walk, and LEDs lit again in every later step, including the timer's repeated
on and off.

Output 1 alone looking red, and output 19 alone looking red, supports the per-channel
form of `CMDR`, but the hypothesis that each write lights only its own output needs
the owner's answer on the walk. The colour order of the other outputs still comes from
the Gemian daemon.

The block's physical order runs opposite to the daemon's numbers, 5 to 1 from left to
right, with block 2 in sequence despite its outputs being 13-15. So the DT's groups
hold, and `-1` to `-5` count from the right.

The 60 s all-on run moved no sensor by more than 0.3 C, but none of those sensors is
near the LEDs and 60 s is short. The owner's "slightly warmer" wasn't the predeclared
stop. It shows nothing above 3.5 mA.

`hci0-power` not being listed doesn't test `CONFIG_BT_LEDS`: nothing in this test
brought up Bluetooth, and that trigger appears with the `hci0` device.

## Conclusion

`confirmed`, for this image and boot: the module probes, reloads and turns its LEDs
off, and `timer` and `kbd-capslock` drive them, at 3.5 mA. Positions of the six cover
LEDs and of the caps lock LED are observed.

Not established: per-channel isolation on every output, the colour of each output, the
state through power off, Wi-Fi and Bluetooth triggers, suspend, and any higher current.

## Follow-up

- Finish step 9 and the two open questions with the custodian.
- The owner chose caps lock only (2026-11-05): `kbd-capslock` as the default on
  `red:indicator-7`, in [0577](../../patches/proposals/0577-arm64-dts-mediatek-gemini-station-show-caps-lock-on-.patch)
  for the next batched image. After that boot, load the module and check that the LED
  follows Fn+Caps with no trigger written. The other LEDs stay for userspace to set.
- Not attempted: the SRAM engine, suspend behaviour, currents above 3.5 mA, the PMIC
  `red`/`green` pair. MT6351 isn't in upstream's `leds-mt6323`, so the pair needs its
  own ISINK work.
