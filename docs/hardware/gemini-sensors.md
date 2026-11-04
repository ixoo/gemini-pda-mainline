# Gemini I2C1 sensors

What is on the I2C1 sensor bus of one Gemini, and what mainline does with it.
Chronology and exact identities are in the
[I2C1 sensors experiment](../../experiments/2026-10-06-gemini-i2c1-sensors/README.md).

## Population

All results are from one unit, on one boot, at 400 kHz.

| Address | Vendor name | Result | Mainline |
| --- | --- | --- | --- |
| `0x69` | `gyro_bmi160`, `gsensor_bmi160` | Answers; register `0x00` reads `0xd1` | `bosch,bmi160`, working |
| `0x48` | `alsps` | Answers; `0x3e` reads `0x11`, `0x3f` reads `0xc2` | `sensortek,stk3311`, working |
| `0x68` | client name only | No ACK | None. The vendor's driver moves this client to `0x69` |
| `0x30` | `mmc3530` | No ACK | None |
| `0x77` | `barometer` | No ACK | None |
| `0x5f` | `humidity` | No ACK | None |
| `0x6a`, `0x6b` | `gsensor`, `gyro` | No ACK | None |

The six no-ACK results are one read each, with `0x69` and `0x48` answering on the
same bus. They are taken to mean the parts aren't fitted on this unit, which is an
inference: a part on an unpowered rail wouldn't answer either, and the vendor kernel
has no driver that would show otherwise. Other units may differ; public Gemian notes
describe LSM6DS3 builds. `0x25` and `0x3e` (a second FUSB301 and the panel bias) are
on this bus too and mainline leaves them alone.

## Bus

I2C1 at `0x11008000`, on GPIO55/56 in mode 1. No supplies are named: the vendor
manages none. Both parts answer with the rails as firmware leaves them.

Enabling it moves other buses in the dynamic numbering. I2C0 stays `i2c-0`, I2C1 is
`i2c-1`, and the others go up by one.

## IMU

A BMI160 at `0x69`, with no chip-ID warning from the upstream driver.

The chip moves with the lid, not the base. With the base held still, moving the lid
turns the gravity vector about X alone. So the matrix describes the screen, which is
the frame the kernel's mount-matrix document gives: X toward the screen's right edge,
Y toward its top, Z out of it. The matrix from the vendor's direction 7 is correct in
that frame:

```dts
mount-matrix = "0", "-1", "0", "-1", "0", "0", "0", "0", "-1";
```

It reads gravity on the expected axis with the right sign in three positions, and the
gyro's signs fit. Limits:

- It can't report the base's attitude without knowing the hinge angle.
- Nothing is calibrated. Gravity measured about 9.7 m/s^2 on X and Z and 10.7 on Y,
  and the gyro read within 0.5 deg/s of zero at rest. No offset is written to the chip.
- Direct reads only. No interrupt pin is known, so no data-ready trigger.

## Light and proximity

An STK3x1x-family part at `0x48`. The upstream driver logs
`new unknown chip id: 0x11` and works. The marketed part name isn't known, so
`sensortek,stk3311` is a working choice, not an identity, and no ID-table change
follows. Register semantics beyond the ones tested aren't checked.

| Condition | Light raw | Proximity raw |
| --- | --- | --- |
| Room | about 110 to 220 | about 200 to 205 |
| Fully covered | 0 to 2 | about 2740 |
| Hand at about 5 cm | about 13 | about 281 |
| Torch at 10 to 20 cm | about 2880 | about 205 |

Light is raw counts, not checked against a lux meter. The sensor's window is in the
screen's right bezel, as located by the owner. A finger to the right of the front
camera covers it only partly.

## Interrupts

The vendor's `Flags mismatch irq 395 (bmi160_accint) vs (ALS-eint)` is a driver bug,
not a shared wire: the IMU driver looks up the light sensor's node and asks for its
line with another trigger. EINT11 on GPIO88 is the light sensor's. It fires as
proximity crosses the set thresholds, including after a module reload, and it stayed
quiet with the IMU loaded and active.

No pin is known to be the IMU's. The vendor programs none of the chip's interrupt
outputs. GPIO65 and GPIO63 are untested candidates.

The vendor selects a pull-up on GPIO88. The MT6797 pin data has no pull registers, so
mainline leaves the pad as firmware set it. The line was quiet at rest and worked.

## Not shown

Suspend and resume, wake from proximity, long runs, buffered capture, step counting,
and any unit but this one. Nothing loads these modules at boot.
