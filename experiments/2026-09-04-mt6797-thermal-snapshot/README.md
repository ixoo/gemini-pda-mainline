# MT6797 thermal snapshot collector

## Record and question

Status: implementation in progress; disconnected hardware-free component.
Subsystem: thermal. Variant: named MT6797X Gemini PDA. Date: 2026-09-04.
Can a bounded collector preserve every normal scan's converted sensor value,
validity, winning sample and callback interval, rejecting incomplete or
inconsistent evidence without adding hardware access?

The [preceding source audit](../2026-09-04-mt6797-a72-frequency-observation/THERMAL_AUDIT.md)
shows why aggregate temperatures alone cannot resolve the cold/warm difference.
Neither rejected workload is reopened by this experiment.

## Provenance and safety

The exact parent is production source state
`a6cf8f228e8aecff0c71b81db28c07fe83a1909d454759262a4fb1082fa7ed13` and integrity
`2f7d22312c16db61b46c9db8300b89c1ff9b054f79cc0b800cf5e0c6e8b588ec`.
The first logical change is a pure internal collector header; the second adds
KUnit and build wiring. There is no call site in the thermal driver, no sysfs
interface, no production option, device-tree change, MMIO, calibration export,
clock operation, CPU request, background worker or device action.
Patches are experiment-only and not upstream-submission-ready. Synthetic
non-certifying author metadata has no DCO sign-off.

## Collector contract

A separately serialized observer owner has three attempts per boot. The budget
is consumed before a caller could start a scan; failures consume it too.
Ordinary polling must never call begin or spend that observer budget. The caller
must zero-initialize the per-invocation record and protect its entire lifetime.
A nested begin rejects an active invocation without resetting it.

Append accepts exactly the seven existing scan slots, in order: bank/sensor
0/0, 1/3, 2/1, 2/2, 3/1, 4/1, 5/1. It records converted temperatures and the
validity boolean supplied by the normal driver's validity predicate. It does
not read or convert sensor registers or infer a hardware freshness bit.
Invalid sensors are retained but excluded from the maximum; a complete success
requires every slot valid. First observed maximum wins ties. Wrong order,
extra slots and prior append failure latch a rejecting result.

Finish seals the invocation once, rejects reversed timestamps, missing slots,
a maximum inconsistent with the caller's normal aggregate and invalid sensors.
Failure records retain the count, validity and values collected so far.
Success concerns record completeness only; it does not declare temperatures
safe. Timestamp units are monotonic nanoseconds supplied by the eventual caller,
not conversion-age measurements.

## Generation and validation

The source templates live in [source](source). The Git-based Buildbox generator
[scripts/generate-on-buildbox](scripts/generate-on-buildbox) checks parent
identity/integrity, copies only the two small build files into a managed
scratch repository, adds the new source templates and exports two ordinary
format patches. It validates strict Checkpatch and independent tree replay,
then removes scratch state. It never copies a Linux tree between hosts or
modifies the prepared kernel source.

The KUnit suite covers complete capture, failure-consuming budget exhaustion,
order corruption, invalid/winning/all-invalid samples, aggregate disagreement,
reversed time, missing slots, nested begin, extra slots and double finish.
Kernel compilation and KUnit execution are still required; source fixtures alone
are not a kernel test result. Subsequent production wiring must preserve the
normal callback's register-read sites, shared bank lock and return behavior,
use a dedicated observer lock, and record timing only for observer requests.
No device candidate is selected until the actual evidence-producing integration
passes its separate source, KUnit, Buildbox and composition gates.

## Interpretation and ownership

This disconnected collector is one dependency of thermal attribution, not the
finished feature. Exact generation/build/test results belong here. Runtime
support stays unchanged. Ordered implementation is in the
[roadmap](../../docs/ROADMAP.md); the first eventual device gate must observe
without adding a workload.

## Patch review result

Published source revision `6fd0f7e9` generated canonical patches `0535` and
`0536` after correcting the initial strict-style review findings. Both patches
pass strict Checkpatch with zero errors, warnings or checks and reproduce the
same tree through independent patch replay. The pure collector has no normal
driver call site. The named `mt6797-thermal-snapshot-kunit` manifest profile
selects the canonical series and only this focused suite; its build and runtime
result remain pending.
