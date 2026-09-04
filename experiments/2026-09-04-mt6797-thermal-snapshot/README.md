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
selects the canonical series and only this focused suite. Exact clean revision
`846391b2` passes the Buildbox package gate and all seven no-network QEMU cases
with no failure or skip. See [build validation](results/build-validation.txt)
and the [strict KUnit result](results/kunit-pass.json). The initial remote QEMU
launch found no system emulator; the validated package ran unchanged on the
host emulator. This closes the pure collector gate, not production integration.

## Production observer integration under review

The prospective integration generator
[scripts/generate-observer-on-buildbox](scripts/generate-observer-on-buildbox)
adds a default-off MT6797-only interface and a separate mutex/budget owner.
Each admitted read consumes one of three attempts before two monotonic clock
callbacks and exactly one existing scan. Normal thermal-zone polling passes a
null collector and does not touch that owner, budget or clock. The EEM bank
reader also retains its null-collector wrapper. The existing bank lock remains
held around selection, conversion and capture of that bank's values; other
polling may interleave between banks, so this is a sequential scan, not an
atomic simultaneous sensor snapshot or a conversion-age measurement.

Two root-only, read-only platform attributes are proposed:
`mt6797_temperature_snapshot` emits the bounded record, including failed and
exhausted attempts as text; `mt6797_temperature_snapshot_status` reads only the
attempt count and limit. Registration occurs after successful thermal probe,
only for the exact MT6797 data table. Registration failure warns and leaves
normal thermal behavior intact; any eventual host gate must reject a missing
interface. Device-managed teardown removes the interface before driver state.
No new MMIO access, calibration export, policy, storage write, CPU action or
thermal emulation is introduced. An observer read directly uses the actual
converted hardware scan and bypasses the thermal core's emulated value.

Source review compares the exact parent and register/locking/conversion call
inventory. That structural check is not sufficient by itself to prove dynamic
return equivalence or read counts. The added KUnit owner fixtures check three
successful attempts, fourth refusal with no clock/scan callbacks, consumed scan
failure with sealed output, recovery on the next allowed attempt, invalid ops
and active-record refusal. Production source review, strict patch review,
Buildbox compilation, KUnit execution and a stronger scan-path oracle remain
required before selecting a production profile or device candidate. These
source templates are not yet a generated or tested kernel change. No additional
boot or workload is admitted by this work.
