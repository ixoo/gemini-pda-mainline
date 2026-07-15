# Experiment: MT6797 charger and fuel-gauge recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-charger-power-recovery` |
| Status | `inconclusive` for mainline runtime; populated charger identity and source boundaries recovered |
| Subsystem | Charger, buck/boost regulator, battery power-supply and fuel-gauge ABI |
| Device variant | Gemini PDA running Gemian, `MT6797X` / `mediatek,MT6797` |
| Date(s) | 2026-07-12 — 2026-07-14 |
| Investigator(s) | Repository maintainer with Codex assistance |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Which charger and battery paths are actually populated on this Gemini, which
Linux 7.1.3 drivers can be reused, and where does a different register
protocol require a new driver rather than compatibility shims?

The working hypothesis was that the live `sw_charger` device is a BQ25890 and
that the `buck_boost` device is a distinct FAN49101 regulator. The RT9466 node
is treated as an alternative until population and IRQ wiring are demonstrated.

## Provenance and environment

- Live device: Gemian 3.18.41+ (`MT6797X`), read-only SSH capture.
- Vendor source evidence: Gemian reference commit
  `d388d350cb2dda8f23b99be6fa5db9628896e87f`.
- Mainline comparison: prepared Linux `7.1.3` tree in the development VM.
- Private capture: `artifacts/device-inventory/20260712-live/charger-power.txt`
  (Git-ignored; not a redistributable fixture).
- Fresh post-recovery capture: `artifacts/device-inventory/20260714T162500Z-battery-recovery-charger/charger-power.txt`
  (Git-ignored; mode 0600; indexed by
  [`results/live-charger-battery-recovery-20260714.txt`](results/live-charger-battery-recovery-20260714.txt)).
- Source analyzer output is reproducible in the VM and reads vendor Git
  objects without materializing proprietary source into this repository.

## Safety assessment

The collection and source comparison are read-only. The live collector reads
sysfs, the flattened device tree, `/proc/interrupts`, `/proc/config.gz`, and
filtered kernel messages. It does not use `i2cget`, `i2cdump`, an I2C scan,
debugfs writes, regulator writes, charger sysfs writes, cable insertion, or
charging-state changes. No sudo was needed.

The first mainline bring-up must keep all charger and regulator consumers
disabled. Do not infer charge voltage/current limits from a stale DT node or a
full-battery snapshot. Any later charge test needs a known-good recovery path,
an explicit cable/target owner, current and temperature limits, and a stop
condition for unexpected status, thermal rise, or battery swelling.

## Associated code

- [`scripts/analyze-mt6797-charger-contract.sh`](scripts/analyze-mt6797-charger-contract.sh)
  prints vendor blob IDs, Linux SHA-256 values, bounded source anchors, and the
  reuse/new-driver decision.
- [`scripts/analyze-fan49101-contract.sh`](scripts/analyze-fan49101-contract.sh)
  records the FAN49101 register, identity, and VSEL anchors needed for a
  dedicated regulator driver.
- [`scripts/collect-live-charger.sh`](scripts/collect-live-charger.sh) is the
  read-only device collector used over SSH.
- [`results/mt6797-charger-source-audit.txt`](results/mt6797-charger-source-audit.txt)
  is the bounded output from the pinned VM source comparison.
- [`results/mt6797-charger-mainline-design.md`](results/mt6797-charger-mainline-design.md)
  records the implementation boundary and bring-up gates.
- [`results/bq25890-reuse-audit-20260713.txt`](results/bq25890-reuse-audit-20260713.txt)
  records the exact vendor/mainline identity and register-contract comparison
  from the refreshed live metadata.
- [`results/fan49101-mainline-validation.txt`](results/fan49101-mainline-validation.txt)
  records the Linux 7.1.3 build, driver-object, binding, and focused DTB
  schema validation for patch 0055.
- [`results/mainline-charger-current-72-package-20260714.txt`](results/mainline-charger-current-72-package-20260714.txt)
  records the reproducible current 72-patch package, module, configuration,
  source-contract, and Gemini-DTB consumer audit.
- [`results/live-charger-battery-recovery-20260714.txt`](results/live-charger-battery-recovery-20260714.txt)
  records the fresh vendor identity and transient power-supply snapshot.

Run the source audit from the VM:

```sh
./experiments/2026-07-12-charger-power-recovery/scripts/analyze-mt6797-charger-contract.sh
```

Run the device collector only through the authorized private SSH path:

```sh
ssh -i artifacts/credentials/gemini_ed25519 \
  -o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes \
  gemini@192.168.1.50 'bash -s' \
  < experiments/2026-07-12-charger-power-recovery/scripts/collect-live-charger.sh \
  > artifacts/device-inventory/20260712-live/charger-power.txt
```

## Procedure

1. Read the source paths and hashes from the pinned vendor commit and Linux
   7.1.3 tree.
2. Compare the vendor BQ25890, FAN49101, RT9466, charger-interface, and
   battery-meter contracts with standard Linux power-supply, regulator, and
   IIO interfaces.
3. Collect the live I2C modalias/driver/DT metadata and power-supply telemetry
   without probing unbound addresses.
4. Record conflicting DT alternatives and negative evidence separately from
   observed bindings.

## Current package boundary

The current reproducible package is
`linux-7.1.3-gemini-a9a7c5002038`. Its configuration selects the generic
`power_supply` core and packages `bq25890_charger.ko` and `fan49101.ko`; the
generic `bq27xxx` battery core is built in and `max17042_battery.ko` is also
present. The generated Gemini DTB has a disabled I2C0 charger controller at
`0x11007000` with SPI84, a disabled `onsemi,fan49101` child at `0x70`, and no
BQ25890 client, RT9466 client, battery/fuel-gauge consumer, cable-policy node,
or charge-control limit. Thus the package contains reusable provider code but
has no enabled charger or battery consumer.

The audit is read-only and byte-repeatable:

```sh
./scripts/dev-vm run bash -lc \
  'CURRENT_PACKAGE=/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-a9a7c5002038 \
   experiments/2026-07-12-charger-power-recovery/scripts/audit-current-package-charger.sh'
```

The complete hashes, module paths, DT status checks, and source identity gates
are in [`mainline-charger-current-72-package-20260714.txt`](results/mainline-charger-current-72-package-20260714.txt).
This is package evidence only: no charger probe, charge-control write, or
hardware write was attempted.

## Observations

- I2C0 `0x6b` is named `sw_charger`, has compatible
  `mediatek,sw_charger`, and is bound to the `bq25890` driver.
- I2C0 `0x70` is named `buck_boost`, has compatible `mediatek,buck_boost`,
  and is bound to `fan49101`.
- I2C0 `0x53` has compatible `richtek,rt9466` and a `primary_charger` label,
  but no driver is bound. Its DT charge properties therefore describe an
  inactive alternative, not the populated charger.
- A second I2C1 `0x6b` node is named `gyro` and is also unbound; the address
  alone is not charger evidence.
- The vendor power-supply class reports AC online, USB and wireless offline,
  and a Li-ion battery full/good at 100%. These are transient telemetry values.
- A fresh read-only post-recovery capture reports AC online, USB and wireless
  offline, a present/Good Li-ion battery at 91% and `Charging`. The private
  capture is indexed in [`results/live-charger-battery-recovery-20260714.txt`](results/live-charger-battery-recovery-20260714.txt);
  these values are still a time-dependent snapshot, not safe mainline charge
  limits.
- Vendor logs repeatedly report `chr_type=4` while the battery is full. The
  vendor enum maps 4 to `STANDARD_CHARGER`; this does not establish electrical
  limits or prove that the cable state is safe to reproduce under mainline.
- The vendor source uses a large charger command/HAL ABI: BQ25890 current,
  voltage, input-limit, VBUS and status helpers are called through the
  MediaTek battery/charger layer; the fuel-gauge side exposes ADC, Coulomb,
  OCV and battery-profile commands rather than a standard Linux power_supply.
- FAN49101 source reads dedicated ID registers during probe. Its bulk VSEL
  initialization is compiled out under `#if 0`, but a separate `fan49101_vosel`
  helper and the writeable legacy `fan49101_access` sysfs file can write the
  device. Neither vendor write path should be carried into mainline without
  explicit regulator semantics and safety constraints.
- The same post-recovery vendor probe log reports FAN49101 manufacturer ID
  `0x83` and die ID `0x06`, matching the vendor's manufacturer gate. It also
  reports that the RT9466 probe found no device. This confirms identity at the
  vendor read-only probe boundary, but does not validate mainline control/reset
  semantics or rail ownership.

The bounded FAN49101 register audit is in
[`fan49101-register-contract.txt`](results/fan49101-register-contract.txt).
It confirms a five-register identity/control boundary distinct from the Linux
FAN53555 family; this is a new-driver task, not a new compatible string for
`fan53555`. Patch 0055 now carries a dedicated `onsemi,fan49101` regmap
regulator driver, binding, and disabled Gemini I2C0 node. Its probe reads the
manufacturer and die-ID registers and rejects a manufacturer value other than
`0x83`; it does not run the vendor initialization sequence or expose the
writeable vendor sysfs ABI.

## Analysis

The upstream Linux BQ25890 driver is a strong reuse candidate: it already
implements standard `power_supply` properties, IRQ handling, charger current
and voltage controls, and a binding with explicit charge-limit properties.
Reuse still requires an exact silicon ID, interrupt resource, battery/system
rail wiring, and conservative board values. The vendor compatible string
`mediatek,sw_charger` is not an upstream binding; the stale `bq24261` DT node
must not be enabled as a duplicate at the same address.

FAN49101 is not a FAN53555 by name. Linux's `fan53555` driver has a different
regmap, vendor-ID set, voltage table, and enable protocol. The recovered
FAN49101 ID/VSEL sequence is insufficient to prove equivalence, so patch 0055
adds a new regulator driver and binding. The candidate uses the recovered
VOUT selector/enable fields and standard regulator operations, while keeping
the board node disabled until control/reset semantics, rail ownership, die-ID
handling, and readback are verified on hardware. The driver object compiles,
the binding validates, and the generated Gemini DTB passes the focused schema
check; these are not runtime support evidence.

Linux 7.1.3 contains an RT9467 charger driver, not evidence that the unbound
RT9466 node is populated. The RT9466 node remains disabled until a controlled
identity and IRQ test proves it is the active board part.

The vendor battery meter and charger interface should be replaced by standard
power_supply plus IIO/ADC and a fuel-gauge implementation. Vendor battery
profiles and calibration tables are not copied: their electrical provenance,
temperature model, and redistribution rights are not established.

## Conclusion

`inconclusive` for mainline runtime support. The live device and vendor source
establish a BQ25890 charger candidate and a distinct FAN49101 buck/boost
candidate, while the RT9466 is an unbound alternative. Upstream BQ25890 and
generic power-supply infrastructure should be reused where the electrical
contract matches; the FAN49101 path is a new-driver task and now has a
disabled-only implementation candidate. No charge-control or regulator
consumer is enabled by this experiment. The earlier validation and checksums
are in [`fan49101-mainline-validation.txt`](results/fan49101-mainline-validation.txt).
The earlier 65-patch tree has a fresh object compile, focused binding check,
and regulator-core audit in
[`fan49101-current-validation.txt`](results/fan49101-current-validation.txt).
The refreshed 70-patch source/object and binding validation, including the
corrected new-file hunk and module metadata, is in
[`fan49101-current-70-module-validation-20260713.txt`](results/fan49101-current-70-module-validation-20260713.txt).
The older package validations are retained as historical evidence. The
authoritative current 72-patch package provenance is recorded in
[`mainline-72-patch-current-20260714.txt`](../2026-07-13-kernel-integration/results/mainline-72-patch-current-20260714.txt);
this experiment's charger-specific runtime validation remains untested.

## Follow-up

- [Mainline charger design result](results/mt6797-charger-mainline-design.md)
- [Hardware support matrix](../../docs/HARDWARE_SUPPORT.md)
- [Live resource map](../../docs/hardware/mt6797-live-resource-map.md)
- [Gemian baseline](../../docs/hardware/gemini-gemian-baseline.md)
- [FAN49101 mainline validation](results/fan49101-mainline-validation.txt)
- [FAN49101 current-tree validation](results/fan49101-current-validation.txt)
- [FAN49101 prior 70-patch module validation](results/fan49101-current-70-module-validation-20260713.txt)

The next discriminating tests are non-writing identity/resource checks on a
mainline image, followed by read-only telemetry only if a qualified hardware
owner approves the procedure. For FAN49101, first confirm die ID and VOUT
readback/control semantics with the board rail owner; do not enable the node or
exercise voltage transitions until a recovery path, thermal/current limits, and
rollback stop condition are documented. Charge-control testing is deferred
until the BQ25890 DT limits, battery gauge source, thermal cutoffs, and
recovery path are reviewed.
