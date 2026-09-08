# Bounded BMI identity observation

Completed, 2026-09-08. The one-read budget is consumed; do not repeat it.

Original admission: read exactly one byte from chip-ID register `0x00`
through the already bound Gemian accelerometer client. The root task is the
sole device custodian. Standing bounded read-only Gemian inspection covers
this hardware effect. Selecting the address and length modifies only the
audited driver's cached diagnostic fields, which are restored afterward.

## Discriminator and limits

The pinned upstream BMI160 driver identifies `0xd1` as BMI160 and `0xd3` as
BMI120. Either byte narrows driver selection; another value preserves the
identity gap. This does not prove physical device count, rails, interrupts,
orientation, mainline operation or general register compatibility. No kernel
probe or board-node enablement follows from this observation alone.

The [one-boot observer](scripts/observe-bmi-identity.py) defaults to metadata
preflight. It pins boot, release, version/configuration digests, bound driver
and initial selector `reg=0X00, len=0`. Only `--read-identity` selects register
zero with length one, verifies those cached fields, and performs one
`os.read()` from `reg_val`. It restores the original selector and verifies it
using metadata only. The zero-length value reader is never invoked.

Budget: one value-read call, no observer retry, no register-value write,
reset, reinitialization, sample, FIFO, gyro diagnostic, calibration, power
change or boot. The bus helper invokes the existing I2C transfer policy;
this is not a bound on electrical retries inside that controller policy.
Unexpected identity, driver or selector metadata stops the operation. A
failed transfer is not a chip ID. A competing selector change prevents an
automatic restore over another consumer's selection. Exclusive diagnostic
use is assumed: the legacy interface does not atomically lock selection
and the subsequent read. Ordinary sensor activity does not use this selector.

## Source and retained-image basis

The selected Planet source at
`c5b0be85017ad0c599725e8273842efdbecdd88a`, file
`drivers/misc/mediatek/accelerometer/bmi160_acc/bmi160_acc.c`, defines:

- `bmi160_store_reg_sel`: parses two integers into cached register and length
  fields; it performs no bus transaction.
- `bmi160_show_reg_val`: reads through the selected bus callback and returns
  negative errors before formatting. Its length-zero formatting is invalid,
  and larger lengths are unchecked, requiring the exact length-one gate.
- `bmi_i2c_read_wrapper` and `bma_i2c_read_block`: use the bound global
  accelerometer client for a one-byte address plus read transfer; success
  requires two completed I2C messages and failure returns a negative error.
- The probe forces the client address to `0x69` and installs that read
  callback. The observer never invokes probe or initialization.

Private disassembly in the RE VM corroborates these paths in the retained
primary kernel, including the callback assignment, error branch and selector
field offsets. The reconstructed ELF kernel section equals the retained
Image. The same boot's primary-partition checksum and version/configuration
digests were already matched in the [STK observation](STK_IDENTITY.md).
Live callback addresses are masked: this attributes the implementation by
provenance, without claiming a runtime instruction or electrical bus capture.

The comparison driver is Linux commit
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c`,
`drivers/iio/imu/bmi160/bmi160_core.c`. Its chip-ID constants distinguish
BMI160 `0xd1` from BMI120 `0xd3`.

Retain exact streams and execution metadata privately; publish only reviewed
identity and source receipts. Raw disassembly, firmware and unrelated device
data remain outside Git.

## Observation and next decision

The [execution receipt](results/bmi-identity-20260908.json) records one
successful value read: register `0x00` returned `0xd1`. The observer verified
that the original cached selector was restored. Its preceding default
preflight issued no value read. The [source receipt](results/bmi-identity-sources.json)
pins the inspected source and retained-binary spans.

This is direct ID-byte evidence consistent with BMI160. Address `0x69` is
attributed through the audited bound-client setup, not a physical bus trace
or direct live client-memory inspection. No second address was tested, so
physical device count and absence at `0x68` remain unproved. The existing
BMI160 IIO driver remains the reuse choice; no new driver or variant is
selected. Resolve VDD/VDDIO ownership and the board interrupt/orientation
contract before a normal mainline probe, which writes power and configuration.

Validation: Python 3.5 syntax, retained-source/binary path review, live
metadata preflight and the single successful ID read with selector restore.
No error injection, mainline build, sensor sample or functional test occurred.
The older July IMU probe record reverses the BMI160/BMI120 labels for `0xd1`
and `0xd3`; the pinned upstream constants above are the comparison used here.
