# Experiment: Gemini sensor current-upstream architecture

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-07-gemini-sensors-upstream-architecture` |
| Status | review-ready exact stop; no implementation admitted |
| Subsystem | Gemini BMI160 IMU and STK3310-family light/proximity sensors |
| Device variant | Gemini PDA; physical sensor variant remains unresolved |
| Date | 2026-09-07 |
| Investigator | Sol Medium current-source review; Astra Medium hardware-boundary review remains required |

## Verdict

The current Linux BMI160 and STK3310-family IIO drivers remain the correct
reuse candidates, but neither Gemini board device is ready to describe or
probe. Local patch 0052 is a disabled evidence marker, not a usable consumer
and not an upstream-ready patch. It leaves both the BMI160 child and its
upstream-disabled `i2c1` parent disabled; current upstream and the inspected DT
development tree do not contain a Gemini board DTS at all.

The patch's `bosch,bmi160`, `reg` and `mount-matrix` properties fit the current
BMI160 binding shape. That syntactic match does not establish that a BMI160 is
physically populated at `0x69`, that the sensor rails are safely owned, or that
the recovered matrix matches the chassis coordinate system. Enabling the node
would cause power, reset and configuration writes, so the normal driver probe
is not a read-only identity test.

The STK3X1X record has strong register-protocol overlap with the upstream
STK3310 family, but the exact product and revision are unresolved. The current
binding offers only explicit `sensortek,stk3013`, `stk3310`, `stk3311` and
`stk3335` forms; it has no generic `sensortek,stk3x1x` compatible. No STK node
is present in patch 0052. The current driver deliberately logs and continues
for an unknown product ID, then enables ALS, proximity and the device's
proximity-interrupt mode. A successful probe therefore would neither prove
identity nor be a read-only discriminator.

Exact source revisions, hashes, tree comparisons and the normalized decision
are in [the source receipt](results/source-review.json). The assigned boundary
is in [the work item](WORK_ITEM.md).

## Patch 0052 disposition

Patch 0052 is at canonical `patches/series` line 55 in the frozen parent,
between patches 0051 and 0053. Its description is internally cautious: one
BMI160 candidate at `0x69`, a direction-7-derived matrix, no guessed supply or
interrupt, and `status = "disabled"`.

That makes it safe as inert local documentation, but not useful upstream:

- the `bmi160_candidate` label and commit message explicitly describe an
  unresolved candidate rather than board hardware;
- the frozen evidence shows two legacy logical clients whose probes both
  rewrite the address to `0x69`, not two independently identified devices or
  direct proof of the SDO strap;
- neither the parent bus nor child has a runtime consumer;
- no rail, interrupt pin, electrical mode or wake contract is supplied; and
- the Gemini base board DTS is not present in the current upstream DT tree.

Do not submit patch 0052 as-is, enable it, or treat its successful application
or compilation as sensor support. Retain it only as a disabled experiment
marker until the identity decision below either replaces it with a truthful
board node or disproves and retires it.

## Driver and binding disposition

| Candidate | Current public contract | Frozen Gemini evidence | Decision |
| --- | --- | --- | --- |
| BMI160 I2C | `bosch,bmi160`; standard addresses `0x68` or `0x69`; IDs `0xd1` (BMI160) and `0xd3` (BMI120); IIO accel/gyro, standard scale/timestamp and optional named INT1/INT2 trigger | Legacy software identifies BMI160 paths, but both logical clients are forced to `0x69`; no direct electrical ID or one-versus-two-device proof | Reuse only after one physical part and address are proved; do not add a driver or legacy input ABI |
| BMI160 supplies | Binding permits `vdd-supply` and `vddio-supply`; driver acquires and enables both named regulator consumers before reset | Patch omits supplies because controlled rail ownership is unknown | Omission is not rail evidence; resolve always-on versus controlled owners before enabling |
| BMI160 interrupt | Binding and driver support one named `INT1` or `INT2`, trigger polarity/type and optional open drain; no IRQ falls back to non-triggered direct IIO access | Patch intentionally supplies no interrupt | Do not claim buffered IRQ or wake behavior; add an IRQ only after pin, polarity, drive and ownership are proved |
| BMI160 mount matrix | Driver reads nine strings and exposes the matrix as shared IIO metadata for accel and angular velocity | Frozen direction 7 is `(-raw_y,-raw_x,-raw_z)`, exactly represented by patch 0052's matrix; the frozen HAL performs no later axis transform | Translation is internally consistent, but physical chassis orientation and userspace application remain unvalidated |
| STK3310 family | I2C address `0x48`; explicit compatibles and IDs; IIO light/proximity channels and threshold events; optional host IRQ | Register map overlaps strongly, but exact product/revision and GPIO88/EINT11 electrical contract are unresolved | Reuse the existing driver only after selecting the compatible from direct identity and resource evidence |
| Legacy input/misc ABI | No BMI160 or STK3310 entry in the reviewed current `drivers/input/misc` build surface | Frozen vendor HAL consumes legacy input and misc nodes and performs virtual fusion | Keep physical devices in IIO and compatibility/fusion in userspace |

Both current drivers continue after an unknown chip-ID result. For BMI160, the
driver enables regulators, issues a soft reset, reads the ID, then configures
accelerometer and gyroscope modes even after warning about an unknown value.
For STK3310, the driver reads `0x3e`, logs an unknown value, then writes normal
ALS/proximity and interrupt state. This behavior is present in both mainline
and the current IIO `togreg` branch. It is a reason to require an independent
identity observation, not a reason to select a broad driver-policy change for
unrelated boards.

## Exact stop and next discriminator

No kernel, binding, configuration or DTS topic is admitted now. The smallest
eventual upstream topic is one Gemini board-DTS BMI160 consumer using the
existing binding and driver, after the Gemini base DTS is accepted and all of
the following are attributable:

1. one physical BMI160/BMI120 identity and its responding `0x68` or `0x69`
   address;
2. VDD/VDDIO source, voltage and lifetime owner, including whether each rail is
   controlled or already-on;
3. INT1/INT2 connection, pinmux, polarity, edge/level and drive mode, or an
   explicit decision that no interrupt is wired; and
4. the matrix relating the physical package axes to the documented Gemini
   chassis axes.

The next discriminator is a source-pinned, independently redistributable
Gemini BMI160 population/electrical record covering those four points. If no
such public record exists, a later device custodian may propose a separately
reviewed, strictly read-only identity protocol; this experiment does not
select or authorize an I2C transaction. Missing or conflicting attribution
retains the stop and admits no node or probe.

STK3310 is a separate later board topic. It needs the exact product/revision
from ID register `0x3e`, a matching explicit upstream compatible, rail
lifetime, and the full GPIO88/EINT11 pin/polarity/drive/wake contract. Do not
combine the two sensors into one admission simply because they share I2C1.

## Dependency and validation story

| Dependency | Required evidence | Rejection condition |
| --- | --- | --- |
| Base board | Accepted Gemini DTS and enabled, validated I2C1 controller/pins | No upstream board consumer or unproved bus ownership |
| Physical identity | Direct, attributable chip/product ID at exactly one responding address | Legacy name, forced client address, generic family match or successful probe alone |
| Rails | Exact source, voltage, sequencing and kernel/firmware ownership | Missing supply silently treated as proof of always-on power |
| Interrupt | Exact sensor pin, SoC pin, trigger polarity/type, drive mode and wake policy | Inferring BMI160 wiring from the unrelated ALS EINT or from a zero counter |
| Orientation | Package-to-chassis axes and the corresponding IIO matrix | Only a legacy direction number without a physical-frame check |
| Userspace | Standard IIO channels, scale, timestamps and matrix-aware consumer | Recreating vendor misc/input nodes or kernel virtual-sensor classes |

Once the evidence gate passes, the future BMI160 board patch should be checked
with the relevant binding and DT checks, built through Buildbox, and tested on
the exact revision. Hardware validation must distinguish identity from normal
operation: verify the expected ID/address first under an admitted protocol,
then one IIO device with accel/gyro channels, standard scale/timestamps, static
gravity on each chassis axis after applying the matrix, optional interrupt
delivery only if described, rail behavior, suspend/resume and absence of a
duplicate logical device. STK3310 needs its own identity-first protocol and
light/proximity/threshold/IRQ tests. A compile or enumerated IIO device alone
does not satisfy either story.

## Upstream route and removal condition

The existing bindings and drivers are maintained through IIO and Devicetree.
A proved Gemini consumer belongs in the ARM64 MediaTek board DTS path with DT,
IIO and ARM/MediaTek reviewers. No binding extension is needed for a genuine
supported BMI160 or explicitly listed STK33xx part. A driver or binding change
is appropriate only if the observed identity and protocol fall outside those
contracts, and must name the actual variant rather than a generic vendor ABI.

Patch 0052 can be removed when an accepted upstream Gemini board change covers
the same proved BMI identity, address, orientation and resource contract. If
evidence disproves any of those fields, retire or replace it rather than wait
for an upstream equivalent. Its existing author and sign-off metadata are not
recertified here; the actual author must confirm any future DCO certification.
No `Tested-by`, submission readiness, maintainer agreement or upstream contact
is claimed.

## Validation and limits

This was an offline public-source audit. The four frozen inputs were verified
from parent `c8344011557b2369e8d15187a5969103108a2c18`; current source files were
hashed at the revisions in the receipt. Eight selected BMI160/STK3310 files are
byte-identical between mainline and IIO `togreg`, and `mt6797.dtsi` is
byte-identical between mainline and DT `for-next`. The inspected DT directory
contains MT6797 EVB and X20 board files but no Gemini board file. Bounded public
history confirms explicit BMI120 enablement and the intentional STK3310
unknown-ID informational behavior; it found no Gemini/MT6797 sensor series.
That last negative result is bounded, not proof of historical absence.

No build, VM, private source or capture, retained binary, device, I2C access,
rail or interrupt action, sample, upstream contact, shared-file edit or
hardware-support claim occurred. The source review validates architecture and
refusal boundaries only.

Review-ready UTC: `2026-09-07T20:49:17Z`.

Accepted UTC: `2026-09-07T20:52:42Z` on first specialist review. No node,
probe, driver or binding change was admitted.
