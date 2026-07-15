# Experiment: Gemini sensor and IIO recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-sensor-iio-recovery` |
| Status | `completed` for static/live contract capture; mainline runtime remains untested |
| Subsystem | I2C sensors, IIO/input boundary, sensor fusion |
| Device variant | Gemini PDA running Gemian; live model reports `MT6797X` |
| Date(s) | 2026-07-12 through 2026-07-14 |
| Investigator(s) | Repository maintainer with Codex assistance |
| Tracking issue | None |

## Question or hypothesis

Which physical sensor candidates are actually present on the running Gemini, and
can Linux 7.1.3 reuse standard IIO drivers for them? The hypothesis is split by
part: a real BMI160 should reuse the upstream driver, while an LSM6DS3 variant
should use the upstream ST sensor family; BMP280 and HTS221 can reuse upstream
drivers only if the vendor candidates are confirmed; STK3X1X should first be
checked against Linux's existing STK3310-family driver because the register
protocol overlaps, while MMC3530 still needs a distinct protocol match.

Vendor logical sensors such as step, pickup, tilt, gravity, rotation vectors,
and fused events are treated as userspace/HAL policy, not as separate chip
drivers.

## Provenance and environment

- Live kernel: Linux `3.18.41+`, AArch64, Gemian Debian 9 userspace.
- Live model/properties: `MT6797X`, `ro.board.platform=mt6797`,
  `ro.mediatek.platform=MT6797`.
- Vendor source: Planet MT6797 tree
  `c5b0be85017ad0c599725e8273842efdbecdd88a`.
- Mainline comparison: Linux 7.1.3 in the development VM.
- Current 72-patch package boundary: [`results/mainline-sensors-current-72-package-20260714.txt`](results/mainline-sensors-current-72-package-20260714.txt).
- Raw capture: `artifacts/device-inventory/20260714-sensors-live/sensors.txt`
  (Git-ignored and access-restricted; it is not a repository artifact).

## Safety assessment

The collector is read-only. It reads sysfs, procfs, the flattened live
device-tree, and filtered kernel messages. It does not scan I2C addresses,
read sensor values or calibration blobs, enable IIO channels, change input
state, reset a part, or write a sysfs/debug interface. The capture is retained
only under the ignored `artifacts/` directory.

## Associated code

Run from the repository root:

```sh
mkdir -p artifacts/device-inventory/20260714-sensors-live
ssh -i artifacts/credentials/gemini_ed25519 \
  -o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes \
  gemini@192.168.1.50 'bash -s' \
  < experiments/2026-07-12-sensor-iio-recovery/scripts/collect-live-sensors.sh \
  > artifacts/device-inventory/20260714-sensors-live/sensors.txt
chmod 700 artifacts/device-inventory/20260714-sensors-live
chmod 600 artifacts/device-inventory/20260714-sensors-live/sensors.txt
```

The captured HAL can be summarized without executing it:

```sh
./experiments/2026-07-12-sensor-iio-recovery/scripts/analyze-sensor-hal.sh \
  artifacts/device-userspace/gemian-2019/system/vendor/lib64/hw/sensors.mt6797.so
```

The VM invocation and sanitized output are retained in
[`hal-binary-tool-output.txt`](results/hal-binary-tool-output.txt).

The vendor kernel image can be reconstructed into a guest-owned symbol-bearing
ELF without booting or executing it:

```sh
./experiments/2026-07-12-sensor-iio-recovery/scripts/analyze-vendor-kernel.sh \
  artifacts/device-inventory/20260712-live/vendor-Image.gz-dtb
```

The selected symbol/disassembly output is retained in
[`kernel-analysis-tool-output.txt`](results/kernel-analysis-tool-output.txt).
The probe/address interpretation is normalized in
[`vendor-imu-probe.txt`](results/vendor-imu-probe.txt).

The output must remain below the ignored `artifacts/` tree. Review it before
sharing because a topology capture can still reveal local hardware details.

## Procedure

1. Confirm the key-only, noninteractive SSH path with `BatchMode=yes`.
2. Run the collector once while the device is idle.
3. Compare bound I2C names, DT resources, interrupt evidence, and exposed
   vendor classes with the pinned vendor DTS.
4. Compare each candidate's exact upstream compatible and Kconfig symbol in
   Linux 7.1.3.
5. Do not enable a mainline sensor node until rails, interrupt polarity, and
   orientation are independently recovered.

## Observations

The live I2C1 controller is at `0x11008000` and exposes vendor sensor
children at addresses `0x30`, `0x48`, `0x5f`, `0x68`, `0x69`, `0x6a`,
`0x6b`, and `0x77`. The `0x68` and `0x69` clients are bound to vendor
drivers named `bmi160_acc` and `bmi160_gyro`; the
`0x48` child is bound to a vendor `stk3x1x` driver. The MMC3530, humidity,
barometer, and alternate `gsensor`/`gyro` children have no bound driver in
the capture. No `/sys/bus/iio/devices/iio:device*` entries exist, and the
vendor kernel reports `# CONFIG_IIO is not set`.

The vendor platform metadata adds bounded software identity evidence:
`/sys/bus/platform/drivers/gsensor/chipinfo` is `bmi160_acc`,
`.../gyroscope/chipinfo` is `bmi160_gyro`, and the gyroscope status reports
`i2c addr:0x69,ver:V1.0`. Both status files report the vendor CUST direction 7.
This confirms the active driver path, but it is not a direct chip-ID register
read and does not prove that the legacy `0x68`/`0x69` clients are two physical
devices. Raw, calibration, register, and factory-value attributes remain
excluded from the collector.

Static probe analysis adds an important address caveat: both vendor probe
functions overwrite the incoming `struct i2c_client.addr` with `0x69`, so the
logical accelerometer client initially described at `0x68` is rewritten before
the common BMI160 register accesses. The gyro init explicitly accepts ID bytes
`0xd0` through `0xd3`; the accelerometer path reads register `0x00` but has no
visible mismatch rejection in the recovered path. See
[`vendor-imu-probe.txt`](results/vendor-imu-probe.txt) for the disassembly
evidence and its limits.

The recovered diagnostic attributes do not provide a safe shortcut to the
electrical ID: `bmi160_bmi_value_show` reads 12 raw bytes from register `0x0c`,
and the register-selection helpers support arbitrary reads and writes. Those
interfaces are intentionally excluded from the live collector; the static
boundary is recorded in [`vendor-imu-probe.txt`](results/vendor-imu-probe.txt).

Patch 52 adds a disabled-only standard `bosch,bmi160` candidate at I2C1
address `0x69`, carries the recovered direction-7 mount matrix, and enables
the upstream IIO/BMI160 module in the reproducible config. It deliberately
does not guess supplies or an interrupt. Prepared-source application, config
merge, DTB compilation, and BMI160 object compilation are recorded in
[`mainline-bmi160-build.txt`](results/mainline-bmi160-build.txt).

The reproducible config also prepares `CONFIG_STK3310=m` for the upstream
STK3310-family driver. This is a build-time capability only: no Gemini DT
child is added and the module is not a runtime support claim. The focused
object compile and serialized full Image/DTB build are recorded in
[`stk3310-mainline-validation.txt`](results/stk3310-mainline-validation.txt).

The live DT names physical nodes with vendor compatibles
`mediatek,gsensor_bmi160`, `mediatek,gyro_bmi160`,
`mediatek,msensor_mmc3530`, `mediatek,alsps`,
`mediatek,humidity`, and `mediatek,barometer`. Separate vendor
configuration nodes describe BMI160, LSM6DS3, STK3X1X, MMC3530, BMP280, and
HTS221 candidates. These are configuration descriptions, not proof that every
candidate is populated. The vendor source selects GPIO88/EINT11 for the
ALS/proximity line and GPIO65 as a gyro GPIO; the live EINT sample shows ALS
line 11 at zero and the raw gyro pseudo-node interrupt tuple is retained in the
private capture without being promoted to a mainline mapping.

The STK3X1X evidence is more specific than the initial Linux coverage audit.
The pinned vendor register header and read-only kernel disassembly show the
standard STK3310-family map: state/control at `0x00`-`0x05`, thresholds at
`0x06`-`0x0d`, flags at `0x10`, PS/ALS data at `0x11`-`0x14`, and product ID at
`0x3e`. Linux 7.1.3 already has the `stk3310` IIO driver with the same map,
standard light/proximity channels, threshold events, optional IRQ, and
`stk33xx.yaml` binding. This is protocol evidence for reuse, not proof of the
exact Gemini product. The vendor ID path accepts product-ID high nibbles
`0x10`, `0x20`, or `0x30`, while the upstream driver lists explicit IDs only;
the live product/revision bytes have not been read safely. The complete
comparison and its identity gate are in
[`stk3310-reuse-audit.txt`](results/stk3310-reuse-audit.txt).

The public Gemian hardware inventory reports that early X25 units used BMI160
instead of LSM6DS3 and that downstream kernels carry both as interchangeable
alternatives. That matches the vendor `cust_*` alternatives (`direction 6`
LSM6DS3 and `direction 7` BMI160), but is not device-specific proof. Also,
BMI160 normally selects one I2C address with SDO; the two bound vendor clients
at `0x68`/`0x69` therefore do not prove two physical chips. Mainline should
probe the responding part and model one standard IMU instance per physical
chip. See the [Gemian hardware inventory](https://github.com/gemian/gemian/wiki/HardwareHacking)
for the public variant note.

The only sensor-named input devices are vendor virtual `m_gyro_input` and
`m_step_c_input`. Misc classes include `gsensor`, `gyroscope`,
`hwmsensor`, `m_gyro_misc`, and `m_step_c_misc`; these are legacy HAL
interfaces rather than IIO devices.

The captured `sensors.mt6797.so` makes the ABI boundary explicit: it maps
`m_alsps_misc` to input event 4, `m_acc_misc` to event 5, and `m_gyro_misc` to
event 6 through the corresponding `*devnum` attributes. Its `Hwmsen` base path
opens `/dev/hwmsensor`, then reads `/dev/input/eventN`; it does not expose a
userspace I2C protocol. The symbol table exposed by `/proc/kallsyms` contains
STK3X1X register/threshold/interrupt functions and BMI160 FIFO/calibration/
step-counter functions, but no MMC3530 symbols or magnetic input stream. The
normalized binary and ABI evidence is in
[`hal-binary-contract.txt`](results/hal-binary-contract.txt).
The disassembled axis/scaling/timestamp contract is normalized in
[`hal-axis-contract.txt`](results/hal-axis-contract.txt).

The 2026-07-14 repeat capture retains the same eight I2C1 sensor client
addresses and the same three vendor driver bindings. The software metadata is
unchanged (`bmi160_acc`, `bmi160_gyro`, direction 7, gyroscope `0x69`/`V1.0`),
and no IIO device appeared. The sanitized comparison and private-capture hash
are recorded in [`live-sensors-repeat-20260714.txt`](results/live-sensors-repeat-20260714.txt).

## Current package boundary

The exact current package is `linux-7.1.3-gemini-c2d9eea95daa`. It selects the
IIO core and packages the upstream BMI160, LSM6DSX, and STK3310-family drivers
as modules. The generated Gemini DTB contains only the disabled `i2c@11008000`
sensor controller and one disabled `bosch,bmi160` child at `0x69`. That
candidate carries the recovered direction-7 mount matrix but no interrupt or
supply property. There are no STK3X1X, LSM6DS3, MMC3530, BMP280, or HTS221 DT
consumers in the package, and this audit did not read any sensor identity.

Reproduce the package audit in the VM with:

```sh
./scripts/dev-vm run bash -lc \
  'CURRENT_PACKAGE=/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-c2d9eea95daa \
   experiments/2026-07-12-sensor-iio-recovery/scripts/audit-current-package-sensors.sh'
```

The audit is read-only and repeated byte-identically. It confirms that the
mainline user-facing IIO layer is available without promoting the vendor HAL
or virtual sensor classes into kernel hardware claims.

## Analysis

Linux 7.1.3 already contains:

- `BMI160_I2C` and `BMI160_SPI`, with the standard
  `bosch,bmi160` binding, optional INT1/INT2 interrupt, `vdd`/`vddio`
  supplies, and `mount-matrix`. The driver reads the Bosch chip ID and
  exposes accelerometer and gyroscope channels through IIO.
- `BMP280_I2C` with `bosch,bmp280`; the vendor string
  `mediatek,bmp280` is not an upstream compatible.
- `HTS221_I2C` with `st,hts221`; the vendor string
  `mediatek,hts221` is not an upstream compatible.
- `IIO_ST_LSM6DSX` for LSM6DS3-family parts, but the LSM6DS3 entries in the
  vendor configuration are alternate candidates and are not bound on this
  device.

The pinned 7.1.3 BMI160 core recognizes Bosch IDs `0xd1` and `0xd3`, supports
either legal I2C address, and exposes one IIO device containing both axes. Its
chip-init path currently warns on an unrecognized ID but continues, so a
successful probe alone is not a sufficient Gemini identity test.

The live `bmi160_acc`/`bmi160_gyro` names are strong software evidence for a
BMI160-compatible path, while the address-pair layout and the vendor's
alternate LSM6DS3 configuration keep the physical BOM classification
`observed, not yet electrically identified`. If a probe or later board
revision identifies LSM6DS3 (or another part), selecting its existing upstream
driver or adding a new chip-specific driver is preferable to changing BMI160
to emulate the legacy ABI.

A targeted search found no `stk3x1x`, `mmc3530`, or matching
`mediatek,*` sensor drivers/bindings in Linux 7.1.3. A public GPLv2 Android
STK3X1X implementation provides a useful register-map and family reference,
but the exact Gemini product/revision still needs a bounded identity capture.
The initial “no matching driver” result was incomplete: the existing upstream
STK3310-family driver is a plausible implementation match, but its OF table
does not contain a generic `sensortek,stk3x1x` compatible and it continues after
an unknown ID warning. Until the product ID is recorded, do not alias the
vendor name to STK3310 or claim runtime support.
The closest mainline magnetometer is MMC35240; the absence of a live MMC3530
symbol or magnetic input stream means compatibility is currently only a
hypothesis. If identity evidence confirms either part, a new IIO driver/binding
or a carefully justified extension of an actually compatible upstream driver is
appropriate; changing an unrelated generic driver to preserve the vendor HAL
would be the wrong boundary.

The mainline bring-up should therefore add IIO and the standard BMI160 driver
first, with a real Gemini I2C1 child only after the board's power rails,
interrupt mapping, and mount matrix are recovered. The vendor HAL's
`processEvent` methods divide raw ABS values by per-device `mdiv` values but
do not permute or sign-flip axes; the configured direction-7 mounting transform
therefore belongs to the vendor kernel sensor path. The recovered vendor
kernel table gives direction 7 as `sign={-1,-1,-1}`, `map={1,0,2}`:
`out=(-raw_y,-raw_x,-raw_z)`. Linux IIO's documented multiplication rule
therefore maps it directly to
`mount-matrix = "0", "-1", "0", "-1", "0", "0", "0", "0", "-1"`.
The recovered BMI160 data paths apply that sign/map before formatting the
input-event triplet, confirming it is not a userspace-only convention.

For the light/proximity part, enable the existing `STK3310` module as a
build-time candidate only. Add a Gemini DT child only after a safe read of
product/revision at `0x3e`, confirmation that it is one of the upstream
supported IDs, and recovery of the VDD/VIO and GPIO88/EINT11 contract. If the
ID or register behavior differs, select another existing family driver or add
a new chip-specific driver; do not bend the generic STK3310 driver around the
legacy vendor ABI.
BMP280/HTS221 should remain
unbound candidates until chip identity is proven. Virtual sensor fusion and
gesture policy should stay outside the kernel physical-driver layer.

## Conclusion

`confirmed` for the live vendor topology, the vendor BMI160 conversion path,
the existence of reusable upstream BMI160 and STK3310-family drivers, and the
buildability of a disabled standard BMI160 candidate node (patch 52).
`inconclusive` remains the correct state for the exact electrical IMU
identity/count, STK3X1X product/revision, and the humidity, barometer, and
magnetometer candidates. STK3X1X is now a strong upstream-reuse candidate,
not a proven new-driver gap; MMC3530 still has no established match.

## Follow-up

- Confirm whether this board's physical IMU is BMI160 or the alternate LSM6DS3
  by a safe chip-ID read during mainline bring-up; do not infer it solely from
  vendor client names or the paired 0x68/0x69 DT nodes. Account for the vendor
  probes rewriting both logical clients to 0x69.
- Recover a non-destructive chip-ID path for STK3X1X/MMC3530 and confirm
  BMP280/HTS221 identities before creating new bindings.
- For STK3X1X, capture the product/revision registers before choosing a
  family-compatible string; preserve the vendor GPIO88/EINT11 and separate
  VDD/VIO power contract in the eventual IIO binding. Prefer the existing
  STK3310-family driver when the ID and protocol match; add a new driver only
  for a genuinely different chipset or register contract.
- Treat MMC35240 reuse as unproven until the `0x30` device is shown to respond
  to the compatible register model; do not issue SET/RESET or measurement
  commands as an identity test.
- Recover BMI160 supply names and GPIO65 interrupt electrical mode. The
  vendor direction-7 transform is now known (`out=(-raw_y,-raw_x,-raw_z)`);
  express it as the standard DT `mount-matrix` shown in the axis contract. It
  is kernel-side in the legacy stack, not a HAL axis rewrite.
- Add a disabled-only mainline BMI160 node and IIO Kconfig fragment once those
  resources are sourced; patch 52 provides the safe candidate node now, but
  keep it disabled until the electrical ID, rails, and runtime recovery path
  are verified.
- Update the support matrix only from a named-device mainline boot and IIO
  enumeration/measurement protocol.
