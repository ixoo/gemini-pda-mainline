# Corrected V4 runtime acceptance boundary

## Hypothesis and attributable evidence

[Patch 0541](V4_CORRECTION.md) corrects offset normalization and calibration
indexing. The isolated compile passed, but its package is not admitted for boot.
The first corrected-image question is whether this changed production conversion
still supplies complete, bounded, internally consistent observer records while
the CPU lifecycle and frequency budgets remain pristine on the named Gemini.
This is a regression test of changed code, not a repeat of the consumed
original no-workload protocol or a claim to explain the workload transient.

A pass establishes only the corrected candidate's bounded observation path.
Missing/invalid records, temperature refusal, changed identity/accounting or
interruption reject and preserve the spent capture. Neither result permits a
workload, a retry, thermal protection, cpufreq/OPP, broader hotplug, idle,
suspend or default integration. Conversion age and calibrated accuracy remain
unknown. The earlier thermal rejections remain unchanged even if this gate passes.

## Required candidate identity

Reserve release `7.1.3-gemini-thermal-v4-corrected` for the future runtime
profile. The compile profile's release and A41 record are explicitly rejected.
Before a candidate can be selected, its manifest must pin:

- the correction patch and exact tested production source hash;
- the named runtime profile, fragments, config-input digest and matching
  A41 configuration binding;
- clean pushed Buildbox revision, validated package manifest, resolved config,
  Image/DT identities and new runtime A41 record;
- the unchanged audited initramfs, exact DT composition, raw/padded container
  hashes and sizes, and independent LK/decompression and mutation checks.

The runtime profile and generated binding patch are now admitted for building
below, but no runtime candidate, installation command or executable device
runner is admitted yet. These are required inputs to a later frozen runner. The protocol object accepts explicit
candidate/record identities only for offline composition and fixtures; it is
not a substitute for proving those identities from a package and container.
No unknown identity may be learned from the device and accepted as expected.

## Frozen action budget and refusal rules

Use five USB shell sessions at most: preflight, one session per snapshot, and
postflight. Connection/idle/outer limits remain 5/15/20 seconds. Before snapshots
two and three, use one second of host spacing. No transport retry, fourth read,
exhaustion test or additional cleanup probe after failure. Host persistence must
seal and fsync each request before transport, and an exclusive capture cannot
be reopened after any partial or interrupted attempt.

Before the first snapshot, require the exact new release/record, a boot ID
unlike deployment or any consumed boot, unchanged full pristine lifecycle,
CPU0--7 online and CPU8/9 offline, zero frequency attempts and zero snapshot
attempts. Retain all inherited ready-profile, unique zone/device, attribute-mode
and read-only sysfs checks. Require initial temperature 0..58500 mC and a
multiple of 100. Do not inspect the consuming attribute during discovery.

Each read must independently recheck the frozen remote identity and pristine
state contract before its single consuming access. Require a complete ABI-1
record, exact seven-slot bank/sensor order, all-valid mask, correct aggregate
and first winning slot, expected attempt and matching before/after boot ID.
Every converted slot must be 0..58500 mC and 100-mC-quantized. Require strictly
ordered software scans and at most 5000 mC aggregate spread across snapshots.
These are experiment refusal bounds, not silicon safety limits or timestamps
of the underlying conversions. Stop before the next request on every failure.

Postflight requires the same boot/record, full pristine lifecycle, unchanged
late-profile frame, offline A72s, zero frequency attempts, exactly three snapshot
attempts and the same ordinary-temperature range/precision rule. Report all
records, two ordinary reads, zero CPU admission/off requests, zero retries,
no remote temporary files, exited transport shells and no device storage access.
The unchanged initramfs's normal background activity remains present; no claim
of an otherwise idle system follows.

## Offline implementation and validation

[v4_observation_protocol.py](scripts/v4_observation_protocol.py) pins the existing
state, receipt and record parsers. It privately adapts only the expected release
and candidate identity, adds consumed-boot and precision refusals, and preserves
the old module unchanged. It provides no transport or device CLI. The final
runner must pin this module and its dependencies, the package/candidate and
remote programs before its execute option exists.

[test-v4-observation-protocol.py](scripts/test-v4-observation-protocol.py) passes
30 scenarios and 13 constructor identity refusals. It asserts exact request
counts and a five-session ceiling, including preflight refusal, request-marker
interruption before transport, read timeout, host-spacing interruption, reused
boots, malformed/invalid snapshots, wrong order/winner, thermal/spread failures
and final identity/accounting/precision changes. The inherited 19 state and 11
receipt mutation cases also pass. These injected host fixtures do not validate
physical hardware or the exact candidate shell. New remote derivation, source
pins, durable-capture/restart fixtures and exact-shell validation remain required.

## Device cycle boundary

The current mainline recovery session is consumed and is not queried here.
Preparing an eventual new candidate requires the standing live-GPT inactive
boot2 gates, stable power, matching-image skip or verified write, full readback,
no fresh backup, evidence flush and clean shutdown. The deployment receipt
must be complete before a fresh pristine frame can admit this gate. Known-good
OS recovery and owner physical selection must have their own explicit cycle
provenance; do not invent continuity from an old receipt. Publish the fully
validated protocol and hypothesis before spending the owner's boot. Expected
USB service remains separate from the previously absent visible console.

No device operation, rebuild or candidate creation occurred while defining this
contract. The ordered implementation remains in the [roadmap](../../docs/ROADMAP.md).


## Runtime profile and pending binding generation

`gemini-thermal-v4-corrected` inherits the complete compile profile and appends
only [its release fragment](../../configs/gemini-thermal-v4-corrected.fragment).
The intended config-input SHA256 is
`f789e69598a86a9f2522b4fc5c408f7c972d88396da10b018156a66bc8337e22`.
No observer/workload/power policy is changed by that fragment. The functional
kernel change remains the tested V4 arithmetic/index correction; the new
identity ensures that the runtime cannot be confused with its predecessor.

The [binding editor](scripts/v4-profile-source-edits.py) pins the current PSCI
file and changes only the thermal selector's four identity words. It checks
all four frequency/thermal selector combinations, preserves other branches,
rejects four source mutations, and distinguishes reordered or missing fragments.
The [generation wrapper](scripts/generate-v4-profile-on-buildbox) requires a
clean published revision and full production-source integrity, then creates
one normal patch from a temporary single-file Git repository, style-checks and
replays it, and removes temporary work. The existing compile profile must be
frozen before this binding patch enters the canonical series. No build may
use the runtime profile until generation and selector checks pass and the
exact patch is admitted and pushed. The old runtime profile remains unchanged.


## Binding generation and build admission

Published tooling revision `f3641db2eb02c54a874714b37390f2aae227c043` generated
[patch 0542](../../patches/v7.1.3/0542-arm64-bind-corrected-Gemini-thermal-V4-configuration.patch).
The [selector tests](results/v4-profile-selector-tests.txt) pass four branches,
four source-mutation refusals and two profile-mutation checks. The
[generation receipt](results/v4-profile-generation.txt) records identical-tree
replay; the [sanitized style check](results/v4-profile-checkpatch.txt) passes.
The corrected PSCI file hash is
`ab37fc176ee2581c522201a0001c7f7458abc40bbac9a849a5907e273c4c5361`.

All 188 predecessor profiles retain their exact selected patch contents,
including the now-frozen compile profile. Only the corrected runtime profile
selects the new binding. This admits one explicit Buildbox build after this
patch/profile revision is committed and pushed cleanly. Compilation and package
validation do not admit installation or the consuming observer; candidate
composition, host persistence and exact-shell gates remain required.
