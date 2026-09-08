# BMI160 resource attribution

Follow-up, 2026-09-08. The [chip ID](BMI_IDENTITY.md) is established; this
investigation distinguishes the vendor's cached power metadata and attempted
interrupt registration from a usable physical board contract. It does not
repeat the consumed identity read or perform a sensor transaction.

## Power metadata does not identify a supply

On the same verified Gemian boot, both `cust_accel@1` and `cust_gyro@1` specify
bus 1, direction 7, `power_id = 0xffff` and `power_vol = 0`. Neither those
configuration nodes nor the two IMU I2C nodes has a `*-supply` property.
The selected public `sensor_dts.c` converts `0xffff` to signed `-1`; the
retained accelerometer parser corroborates that conversion. Zero in
`power_vol` is a cached configuration value, not a voltage measurement.

In the inspected accelerometer and gyroscope driver files, `power_id` and
`power_vol` occur only in status formatting. A bounded search of those files
and their `accel.c`/`gyroscope.c` frameworks found no regulator, `hwPower`,
GPIO or pinctrl resource acquisition. This is a file-scoped negative result,
not proof that firmware, another driver or a board-level circuit cannot
control the rails. The accelerometer's `set_power_mode` sends an internal
sensor command over I2C; it does not identify or own VDD/VDDIO.

Therefore no fixed regulator, PMIC supply phandle, voltage or always-on
claim follows from this metadata. Resolve the actual VDD/VDDIO net and its
lifetime owner using board electrical evidence or an attributable retained
power-setup path. Do not try voltage or regulator writes to discover it.

## The attempted IRQ is the ALS node

The public accelerometer probe invokes `bmi160_request_irq`, which looks up
`mediatek, ALS-eint`, maps interrupt zero and requests a rising-edge handler
named `bmi160_accint`. The retained binary inlines this sequence:

- the lookup uses the string at `0xffffffc000f7c448`;
- `request_threaded_irq` at `0xffffffc000490354` receives flags `1` and the
  name `bmi160_accint`;
- the following signed comparison only logs the nominal failure message
  for a positive return; normal negative errors bypass it; and
- probe returns its earlier result and marks initialization successful,
  without propagating the IRQ request result.

The live `als` node has compatible `mediatek, als-eint`, debounce `<88 0>`
and interrupt cells `<88 8>`. Capitalization does not prevent the lookup:
`__of_device_is_compatible` in the retained binary calls `strcasecmp` for
compatible strings. No physical BMI160 INT1/INT2 connection follows from
this lookup of an ALS-labelled node.

The filtered live interrupt inventory contains only
`395: 0 0 mt-eint 11 ALS-eint`; it contains no `bmi160_accint` action.
This shows no currently listed BMI action under the inspected names. It
neither captures the old request's exact error nor proves that either IMU
interrupt pin is unwired. An IRQ conflict is a plausible explanation, not
an observed return code. No IRQ request, rebind or trigger was attempted.

## Mainline decision

Do not copy GPIO88, EINT11, the ALS interrupt cells, or the vendor's rising
edge into the BMI160 node. The existing upstream BMI160 driver supports
non-triggered direct IIO reads without a host IRQ, as established by the
[driver audit](README.md#driver-and-binding-disposition). An initial direct
read test may deliberately omit the interrupt once its bus and power
contract is admitted; proving that no physical IRQ wire exists is not a
prerequisite for that limited test. Buffered IRQ and wake operation remain
separate work requiring the actual pin and electrical contract.

The direction-7 metadata still supplies only the recovered software matrix.
Validate package-to-chassis orientation with an attended, bounded physical
observation before claiming correctly oriented motion data. No new driver,
binding, sensor node, power action or mainline probe is admitted here.

## Evidence and validation

The [normalized receipt](results/bmi-resources-20260908.json) pins the six
public files and three retained-binary function envelopes. They use the same
primary-kernel provenance as the [identity audit](BMI_IDENTITY.md), and raw
disassembly remains private in the RE VM. Function envelopes end at the next
distinct symbol and may include alignment bytes.

Live access read only allowlisted immutable DT properties, boot/release/version
identity and a filtered interrupt listing. No sensor value, calibration,
regulator, GPIO or IRQ-control interface was accessed. The observation is one
snapshot, not a reliability or functionality test. Repository publication
checks apply; no kernel build, mainline test or physical orientation test was
performed.
