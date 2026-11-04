# Experiment: I2C1 sensors H1, BMI160 identity on the enabled bus

| Field | Value |
| --- | --- |
| ID | `2026-10-06-gemini-i2c1-sensors` |
| Status | `completed`: IMU and light/proximity work from modules on the station; [results](#results-boot-ef1dc545). The 2026-10-06 candidate below was never booted |
| Profile | `mt6797-a53-station-a72`; originally `mt6797-a53-i2c1-sensors-compile` |
| Date | 2026-10-06, 2026-11-04 |
| Device action | One boot, `ef1dc545`, through the custodian |

## Purpose

The after-Wi-Fi order's I2C1 boot: enable I2C1 once and decide
[sensors H1](../2026-10-04-gemini-sensors-re/README.md). One BMI160 with SDO
high should answer at `0x69` and enumerate one IIO device with sane static
gravity. The same boot can make the single identity reads of H6 and H7
(`0x30`, `0x77`, `0x5f`) through i2c-dev.

## Pin pair answered offline (sensors H8)

The public board DWS (`drivers/misc/mediatek/dws/mt6797/aeon6797_6m_n.dws` at
`c5b0be85…`) sets these default pin modes:

| GPIO | DWS mode | Function in mainline `mt6797-pinfunc.h` |
| --- | --- | --- |
| 55, 56 | 1 | `SCL1_0`, `SDA1_0`: I2C1 |
| 53, 54 | 1 | `DPI_HSYNC`, `DPI_VSYNC`; I2C1's alternate here is mode 4 |
| 58, 60 | 0 | GPIO |
| 37, 38 | 1 | `SCL0_0`, `SDA0_0`: I2C0, the charger bus |

So the Gemini uses the `SCL1_0/SDA1_0` pair, as H8 predicted, and I2C0 is on
GPIO37/38. The loader applies DWS defaults, so the DT adds no pinctrl state
and relies on them; a later product DT can describe the same modes.

## Profile and candidate DT

- `mt6797-a53-i2c1-sensors-compile`: the board-services series unchanged
  (patch 0052 already carries the disabled `bosch,bmi160@69` node with the
  direction-7 mount matrix). The fragment keeps the board-services RTC scope
  and adds `I2C_CHARDEV`, `IIO` and `BMI160_I2C`, all built in.
- [i2c1-dt.sh](i2c1-dt.sh) runs the board-services DT derivation, then sets
  `/i2c@11008000` and its only child `bmi160@69` to okay. It checks that the
  bus has exactly that one child and that the difference is exactly the two
  status edits. The output is reproducible: SHA-256
  `93e0b5857c6de7628477202793a8e0d6514481f9df68b7d77dd789c54ba29b75`. There is
  no new schema diagnostic relative to the board-services DT.

## Protocol draft (for the custodian's review)

- **Admitted effects.**
  - I2C1 controller probe: its clocks and init.
  - BMI160 probe: chip-ID read, the soft-reset command the vendor issues at
    every init (sensors F7), and power-mode and range writes.
  - IIO reads.
  - Optional single-byte i2c-dev reads: `0x20` at `0x30`, `0xD0` at `0x77`,
    and `0x0F` at `0x5f`.
  - No other I2C1 address is touched, and no write goes anywhere but the
    BMI160.
- **Observations.**
  - The BMI160 probe line and the IIO device name.
  - `in_accel_{x,y,z}_raw`, scale and `in_accel_mount_matrix`, with the device
    flat and then on each edge.
  - `in_anglvel_*_raw` at rest.
  - The three identity bytes, or an `-ENXIO`/no-ACK for each.
- **Branches.**
  - IIO device present with gravity on the expected axis: H1 holds, and I2C1
    is validated for the display bias chip.
  - No ACK at `0x69`: record it. Do not probe `0x68` in this boot (sensors H1
    note).
  - Any I2C1 timeout or controller error: stop; no further I2C1 access in
    this boot.

## Build

| Item | Value |
| --- | --- |
| Input commit | `cbe66949c33a108f1115cf380b898c38acad1b2e` |
| Job | `cbe66949…-mt6797-a53-i2c1-sensors-compile-m0`, buildbox-1, 32 jobs |
| Package inventory | `7f605fb20893db2520005c08ea97433db10c269c6069cc76cfb0b162bd0de6f3` |
| Release | `7.1.3-gemini-a53-i2c1-sensors-compile` |

Compilation, remote validation, fetch and local checksums pass, with no
compiler warning. The resolved config has `I2C_CHARDEV`, `IIO`, `BMI160` and
`BMI160_I2C` built in.

## Station port, 2026-11-04

The profile above predates the current station series, so it is not booted.
[Patch 0542](../../patches/proposals/0542-arm64-dts-mediatek-gemini-station-enable-the-sensor-.patch)
carries the idea to the station DT, with `BMI160_I2C` and `STK3310` as modules
nothing loads. What it adds to a boot: the I2C1 controller's probe and its
clocks, the mode of GPIO55/56, and the bus's place in the dynamic I2C numbering.
It sends nothing on the bus.

Bus numbers are not stable across this change. I2C0 stays `i2c-0`, the only number
station code relies on, in [`charge-guard.c`](../2026-10-30-mainline-dev-station/charge-guard.c);
I2C1 takes `i2c-1` and the others move up.

### The interrupt conflict

[`mt6797-interrupts.md`](../../docs/hardware/mt6797-interrupts.md) recorded a
conflict between the STK3x1x and BMI160 in one vendor probe; its note now points here.

Observed:

- The retained vendor log has `genirq: Flags mismatch irq 395. ... (bmi160_accint) vs. ... (ALS-eint)`.
  This is the return path the [BMI resources review](../2026-09-07-gemini-sensors-upstream-architecture/BMI_RESOURCES.md)
  could only call plausible.
- The live DTB `9e269295…` gives the `als` node `interrupts = <88 8>`, GPIO88 and
  level low, and `/proc/interrupts` lists only `mt-eint 11 ALS-eint`.
- The same DTB gives `gyroscope@0` `<65 8>` and `gse_1` `<63 8>`. Its pin state for
  GPIO65 selects the GPIO function with a pull-down, not the EINT function.

Inference, confirmed for EINT11 in [T2b](#t2b-eint11): this is a vendor driver bug, not a shared wire. `bmi160_request_irq`
looks up the light sensor's node, asks for its line as rising against the
sensor's level low, and fails; the probe ignores the failure
([sensors F8](../2026-10-04-gemini-sensors-re/README.md)). That driver also never
programs the chip's interrupt outputs. So EINT11 belongs to the STK3x1x, and no
pin is known to be the BMI160's. The patch gives the STK3x1x the line and the IMU
none. GPIO65 and GPIO63 remain untested candidates.

### Station tests

[`sensors-t0.sh`](sensors-t0.sh) makes the identity reads with no module loaded.
[`sensors-imu.sh`](sensors-imu.sh) and [`sensors-als.sh`](sensors-als.sh) sample
through IIO, and [`decode-imu.py`](decode-imu.py) summarizes an IMU capture on the
laptop. Raw captures stay under `artifacts/`.

The device frame is the screen's, as the kernel's mount-matrix document describes
it: X toward the screen's right edge, Y toward its top, Z out of it toward the
user.

## Results, boot `ef1dc545`

Package `ff92b123…` from commit `1cdbea2a…`, composed into image `39be7121…` on the
usual station parent. The board DTB is `be83c638…`, since composing rederives it. Kernel
untainted, radio not started, no I2C timeout or oops through all of it. Raw captures
stay private under `artifacts/`.

### T0: identity, no module loaded

Observed. The bus probed in about 1.2 ms. Pads 55 and 56 are mode 1, claimed by the
controller. One read per register:

| Address | Register | Result |
| --- | --- | --- |
| `0x69` | `0x00` | `0xd1` |
| `0x48` | `0x3e`, `0x3f` | `0x11`, `0xc2` |
| `0x68` | `0x00` | No ACK |
| `0x30` | `0x20` | No ACK |
| `0x77` | `0xd0` | No ACK |
| `0x5f` | `0x0f` | No ACK |
| `0x6a` | `0x0f` | No ACK |
| `0x6b` | `0x0f` | No ACK |

Hypothesis held, including for `0x30`, which was open. H1, H6 (negative), H7 and H8
of the [sensors record](../2026-10-04-gemini-sensors-re/README.md) are settled.

Inference: those parts aren't fitted on this unit. An unpowered rail would look the
same, and this test doesn't exclude it. `0x68` also gave no ACK, so one IMU at
`0x69` is the simple reading.

### T1 and T1b: the IMU

Observed. Modules load and reload (`rmmod` and `insmod` once) with no chip-ID warning,
each probe about 88 ms, supplies as dummy regulators, IIO name `bmi160`, default 100 Hz.

**My prediction was wrong.** I expected the base's frame, with Z at +g when the base
lay flat. At rest with the base flat and the lid at about 140 degrees by the owner's
estimate, gravity read X -0.05, Y 6.78, Z 7.70 m/s^2 after the matrix, an angle of
41.5 degrees.

T1b tied this to single held positions, hand-held, and each prediction held
(means, m/s^2):

| Position | X | Y | Z |
| --- | --- | --- | --- |
| Right edge up | **9.66** | 1.11 | 0.16 |
| Screen upright, base flat | -0.04 | **10.67** | 0.11 |
| Screen facing the ceiling | -0.08 | 1.21 | **9.65** |

With the base pressed down and the lid moved to past upright and back, X stayed within
0.04 of zero while Y and Z swung, and rotation was about X (`gy`, `gz` within about
1 deg/s).

Inference: the chip moves with the lid, and the existing direction-7 matrix is correct
in the screen's frame. In T1, raising an edge of the whole device gave `gy` and `gz`
in the ratio the lid's tilt predicts, and a counterclockwise turn gave positive rates
along the vertical. So the gyro shares the matrix, on sign. No patch change.

Limits: at rest the gyro is within 0.5 deg/s of zero. The field reads about 9.7 on X
and Z but 10.7 on Y, about 1 m/s^2 high on Y, and I didn't separate gain from offset.
Nothing is calibrated and nothing was written to the chip's offsets or NVM. T1's step 8,
keyboard down, wasn't captured, since the recording ended first. The owner also added
a left-side position there, which is how that record's extra excursion reads.

### T2: light and proximity

Observed. `stk3310.ko` loads with `new unknown chip id: 0x11`, in about 2 ms, IIO name
`stk3310`. Pad 88 is claimed in mode 1 (EINT11). With the sensor's window found by
the owner, 8 s captures, raw:

| Condition | Light | Proximity |
| --- | --- | --- |
| Room, untouched | about 110 to 220 | about 200 to 205 |
| Window fully covered | 0 to 2 | 2733 to 2745 |
| Hand about 5 cm away | 12 to 13 | 276 to 285 |
| Lit torch at 10 to 20 cm | 2781 to 2919 | 204 to 206 |

Hypothesis held. A first pass with a finger to the right of the front camera gave a
partial cover (light 28, proximity 342) and a torch with no rise, which was the wrong
spot, not a limit of the part. One idle sample read light 2352, cause unknown. The
position is recorded only as found by the owner. The IMU kept reading normally with
both loaded.

### T2b: EINT11

Observed, with thresholds of 270 and 230 written through IIO:

- 10 s idle: 0 interrupts, with proximity near 200.
- 25 s of presses: the count went from 14 to 27, in step with proximity crossing between
  about 200 and 2700.
- After `rmmod` and `insmod`, with the same writes: 41 to 48 in step with presses, then
  0 over about 16 s with hands clear.

So EINT11 is the sensor's own line, and it survives a reload. Not exactly two per press,
and the count also moved between captures with nothing recorded; I didn't explain either.

## Limitations

One unit and one boot. No suspend or resume, wake, long run or buffered capture. No
calibration. Light is raw counts. `0x11` has no marketed name, so `sensortek,stk3311`
is a working choice. No interrupt for the IMU; GPIO65 and GPIO63 remain untested.
GPIO88's pull is firmware's, since the pin data has no pull registers. Modules are loaded
by hand, and nothing loads them at boot. The durable summary is in
[Gemini I2C1 sensors](../../docs/hardware/gemini-sensors.md).
