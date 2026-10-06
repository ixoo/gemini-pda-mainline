# Experiment: I2C1 sensors H1, BMI160 identity on the enabled bus

| Field | Value |
| --- | --- |
| ID | `2026-10-06-gemini-i2c1-sensors` |
| Status | Profile and DT derivation; protocol draft for review; not booted |
| Profile | `mt6797-a53-i2c1-sensors-compile` |
| Date | 2026-10-06 |
| Device action | None |

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
