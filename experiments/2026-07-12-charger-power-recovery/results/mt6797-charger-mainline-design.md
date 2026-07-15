# MT6797 charger and fuel-gauge mainline design

## Recovered device contract

| Resource | Live observation | Confidence | Mainline consequence |
| --- | --- | --- | --- |
| I2C0 `0x6b` | `sw_charger`, `mediatek,sw_charger`, bound `bq25890` | observed | Reuse the upstream BQ25890 core only after identity/IRQ/rail checks; translate the node to the upstream binding |
| I2C0 `0x70` | `buck_boost`, `mediatek,buck_boost`, bound `fan49101` | observed | New regulator driver/data unless an exact register-protocol match is proven |
| I2C0 `0x53` | `richtek,rt9466`, `primary_charger`, unbound | observed alternative | Keep disabled; DT limits are not populated-part evidence |
| I2C1 `0x6b` | `gyro`, unbound | observed | Do not infer a charger from the repeated address |
| `/sys/class/power_supply` | AC online; USB/wireless offline; battery full/good/100% | transient observation | Use only as telemetry baseline, not as charge safety validation |

## Upstream reuse boundary

### BQ25890

Linux 7.1.3's `drivers/power/supply/bq25890_charger.c` provides the desired
standard power-supply interface and charger controls. Its binding requires a
real interrupt and explicit battery/system/boost limits. The Gemini board DTS
should therefore use a TI-compatible node only after these values are sourced
from the schematic, a measured board limit, or an otherwise reviewable
calibration record. The vendor `mediatek,sw_charger` string and command table
are implementation evidence, not a Linux-compatible binding.

The same I2C address is present in an old `bq24261@6b` node. This is a stale or
alternative description: enabling both nodes would create address ownership
ambiguity. The mainline board DTS must select exactly one charger owner.

### FAN49101

The vendor driver identifies the part through `FAN49101_ID1`/`FAN49101_ID2`
registers (`0x40`/`0x41`) and accepts manufacturer ID `0x83`. Its bulk
probe-time VSEL initialization is disabled under `#if 0`, while a separate
`fan49101_vosel` helper writes register `0x01`: the source formula is a 603 mV
base with 12.826 mV steps, clamps the six-bit code to 63, and sets bit 7.
Register `0x00` is named soft reset and `0x02` control, but their operational
semantics are not recovered. The source comments document 0.7 V and 1.1 V
selections. Linux `fan53555` uses a different regmap, ID table, and enable
protocol. Similar voltage names do not establish protocol identity. See the
[bounded register audit](fan49101-register-contract.txt) for hashes and
bring-up gates.

The correct path is a small, reviewable `fan49101` regulator driver and DT
binding once the ID values, enable semantics, voltage ranges, ramp behavior,
and rail consumers are measured. Do not expose the vendor's writeable
`fan49101_access` sysfs ABI.

### RT9466 and fuel gauge

The vendor DT's RT9466 node contains charge limits, AICL/MIVR, interrupt names,
and compensation values, but the live client is unbound. Linux has an RT9467
driver, which is not enough to claim RT9466 compatibility. Keep this path
disabled until a controlled ID and IRQ test establishes that the part is
actually populated.

The vendor battery meter/HAL combines ADC, Coulomb counter, OCV, charger type,
temperature, and profile tables behind private commands. Mainline should
split those responsibilities into a standard charger power_supply, an IIO ADC
provider, and a fuel-gauge driver with explicit calibration. The profile tables
are not copied because their electrical calibration and redistribution rights
are unresolved.

## Bring-up gates

1. Build with all charger/regulator consumers disabled and confirm no duplicate
   I2C owner at `0x6b`.
2. Add only the BQ25890 node with a verified interrupt and conservative,
   reviewable limits; first validate probe, read-only status, and unplugged
   telemetry.
3. Add the battery gauge/ADC path independently and compare voltage, current,
   temperature, and capacity against an external instrument. A full/100%
   report alone is insufficient.
4. Author and review the FAN49101 regulator driver with read-only ID checks,
   then attach one known consumer at a time. Do not transition GPU/CPU rails
   until the rail owner and allowed voltage range are established.
5. Exercise charge enable, input-limit, termination, thermal cutoff, and
   suspend/wake only with an explicit hardware owner, a recovery image, a
   current/temperature monitor, and a cable removal stop condition.

## Source identities

The VM analyzer records exact Git blob IDs for the vendor files and SHA-256
values for the Linux files. At the audited revisions the key identities were:

- vendor BQ25890 source: `d66a43f88153ee0c03b66f4f8bcaf9e6e2b7633c`;
- vendor FAN49101 source: `bee84a67680c01724279b7d13ab37ca73c2dc00e`;
- vendor RT9466 source: `7654c61dfc4ab1cae36b2fbc7a2ae2073aa250e8`;
- Linux BQ25890 driver: `ef2cfbdd6e3c67abe1dbd5583f329d1a93539f48fb15ebd9a27e201b08ddbf90`;
- Linux BQ25890 binding: `05fc506c2d0bbf059fee6a3dbe8b4aa6e37c3eac5695f3ecffbdf10261cdf03c`;
- Linux FAN53555 driver: `85d81789a5fe438d544c13726d4b61c4cadb4131359d9d274a06531b47155af9`;
- Linux RT9467 driver: `abb15de8e2b355d5cc7cf2113499a078768ce7e45f3001505ec4547583b64ff5`.

These hashes identify the audited inputs; they do not grant redistribution
rights to vendor source or firmware.
