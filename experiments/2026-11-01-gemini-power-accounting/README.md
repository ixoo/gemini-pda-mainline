# Experiment: power accounting on the Gemini station

| Field | Value |
| --- | --- |
| ID | `2026-11-01-gemini-power-accounting` |
| Status | `planned`: design proposal only; no build, device access or measurement |
| Subsystem | MT6351 fuel gauge, MT6351 AUXADC, BQ25896 power path, Mali-T880/Panfrost, cgroup accounting |
| Device variant | named Gemini PDA (MT6797X), development station |
| Date(s) | 2026-11-01 |
| Investigator(s) | project custodian |
| Tracking issue | M5 power gate (battery telemetry) |

## Question

The station can read battery-side current, but only while the battery carries
the load. The owner wants per-domain power figures that stay valid with the
charger attached: the kernel floor, each enabled feature, the user-driven
state, and each application, including applications using the GPU.

**Question:** what measurement and model design produces those figures, and
what does each of them claim?

## What already exists

- The MT6351 fuel gauge publishes `current_now`, `charge_counter`,
  `voltage_now`, `temp` and `capacity` on the station
  ([fuel-gauge record](../2026-10-31-gemini-fuel-gauge/README.md)); capacity is
  an OCV lookup, current and counter are hardware reads.
- `power-status` reads the BQ25896's own ADC through plain SMBus reads and one
  admitted `CONV_START` write
  ([power-status record](../2026-10-31-gemini-power-status/README.md)).
- `charge-guard` already writes BQ25896 `REG03` (`CHG_CONFIG`, `WD_RST`) to
  hold charging off for a capacity limit
  ([station record](../2026-10-30-mainline-dev-station/README.md)).
- Cgroup v2 CPU accounting is enabled in the configurations this project
  composes (`CGROUP_SCHED`, `CGROUP_CPUACCT`, `FAIR_GROUP_SCHED`).
- The GPU has no runtime: the node is disabled and the bring-up is offline-only
  ([Mali-T880 record](../../docs/hardware/mali-t880.md)).

## The proposal

[DESIGN.md](DESIGN.md) records the design:

- four disjoint domains with a single ownership rule, so that kernel cost,
  feature cost, user-driven cost and application cost cannot absorb each other;
- the power-path identity that shows why system current is unobservable while
  plugged, and the two measurement regimes that restore observability;
- an interleaved paired-toggle calibration protocol with a held-out closure
  check, instead of one global fit;
- marginal, not proportional, application reporting, with an explicit
  unattributed bucket;
- GPU static and dynamic cost allocated to the client that holds or drives the
  device, and why that cost can only be modelled, never read.

## Safety assessment

This record is design only: no build, no device access, no register read and
no write.

One step in the design is state-changing when implemented: a bounded BQ25896
input-current clamp (`REG00`) with watchdog kicks and a restore guarantee. It
is the same register class as the `charge-guard` write, and the design states
that it needs its own review and a validity predicate before any device run.
The design deliberately keeps the calibration protocol battery-only, which
needs no charger write at all.

## Associated code

None yet. The design names three userspace programs (`power-sampler`,
`power-clamp`, `power-report`) and requires no kernel change for the first
three domains.

## Procedure

Not run. The calibration and closure protocol is predeclared in
[DESIGN.md](DESIGN.md) section 5 so that a later device session cannot choose
its conditions after seeing the numbers.

## Observations

None. No device was accessed.

## Analysis

The design's decisive constraint is that the board has no system-rail or
input-current sense anywhere: the gauge is on the battery branch, the BQ25896
has no input-current ADC, and the MT6351 auxiliary ADC has no rail-current
channels. Any plugged measurement therefore depends on forcing the input into
a known state, and any per-application figure depends on a model that is
calibrated once and reported with its residual.

## Conclusion

No conclusion. `confirmed`, `rejected` and `inconclusive` apply only to device
results, and this record has none.

## Follow-up

1. Recheck the exact composed configuration symbols named in the design
   against the candidate that would run the calibration.
2. Settle the gauge scale (the `CAR_TUNE` 115 against LK's 86, and the
   unapplied per-chip trim) with one independent reference, because every
   domain coefficient inherits it.
3. Build `power-sampler` and run the battery-only calibration matrix; do not
   report any domain figure before the closure test passes.
4. Review the input-current clamp separately before measuring while plugged.
5. Leave the GPU domain `unknown` until Panfrost has a runtime; do not assign
   it zero.
