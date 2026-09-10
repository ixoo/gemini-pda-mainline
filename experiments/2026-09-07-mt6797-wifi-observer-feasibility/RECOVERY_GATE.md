# Capture before recovery takeover

The unselected [patch](patches/recovery-gate/0001-watchdog-join-capture-and-recovery-takeover.patch)
adds `mtk_wdt_capture_begin()` to the native kicker driver. It joins attributable
capture to the twelve-second watchdog takeover before a future controller can
start connectivity. It has no automatic trigger, exported module symbol or
userspace interface. The [source receipt](results/recovery-gate-sources.json)
pins its complete edited parents and outputs. Prerequisites are historical
recovery patch 0002, the [ordinary setter correction](RECOVERY_SETTERS.md), and
the ten [pstore patches](PERSISTENT_CAPTURE.md); the historical delayed trigger,
profile and consumed candidate are not selected. The archive author is
synthetic and provides no DCO certification.

## Entry and failure behavior

The built-in caller must use sleepable process context and establish the
[remaining isolation requirements](RECOVERY_INTEGRATION.md). The function
rejects interrupt/IRQ-disabled callers and null arguments, consumes one atomic
attempt, checks the native cpuidle-disable value and zero panic timeout, then
begins capture. The cpuidle change only declares the existing function in its
public header; it does not change idle behavior. CPU_IDLE must be built in.
Parameter checks are observations, not locks against later writers. Candidate,
boot and input identities come from the trusted controller; this backend does
not authenticate those bytes.

After the identity and recovery-entry records, the function disables CPU
hotplug and takes the existing kicker lock with interrupts saved. It requires
the initialized, ready and enabled kicker, disables kicking, and invokes the
native arm helper. Only a failure before low-level ownership restores kicking;
CPU hotplug is released only if ownership was never claimed. Result recording
happens after releasing the kicker lock. Any subsequent failure attempts one
failed terminal record, preserving whatever prefix was committed. It never
rearms, reloads or disarms the owned watchdog. Failed terminal writes are not
repaired or treated as evidence of completion.

A zero return requires successful arm and successful result recording. An
error ends the controller's normal requests, including when `state.owned` is
true. Null/context/duplicate refusals leave the supplied state untouched;
callers must not infer absence of ownership from those refusals. No second
attempt is admitted after a software preflight or capture failure.

## Retained record

Kind 11, transaction zero, contains seven little-endian 32-bit fields: stage,
timeout seconds, ownership, prior MODE, resulting MODE, resulting LENGTH and
signed arm status. Stage 1 is entry with timeout 12 and all other fields zero.
Stage 2 preserves the actual arm return and its existing register snapshots;
the recorder adds no register reads. A result-record storage failure is separate
from that arm status and is returned to the caller.

The [decoder](capture-records.py) validates field sizes and discriminators.
Its explicit `check_recovery_prefix()` requires identity, entry and successful
result before other activity, rejects duplicate recovery records, and checks
the same MODE/LENGTH masks as the native helper. Failed and interrupted prefixes
remain decodable evidence but fail this prerequisite. Historical classifiers
are not silently changed; the future controller classifier must call this
check. A valid prefix proves recorded software observations, not timer timing,
physical reset, RAM retention or complete watchdog exclusivity.

## Verification and remaining work

The [focused fixture](test-recovery-gate.py) extracts the complete native entry
function and state declaration. Fifteen injected boundary cases cover context,
idle/panic preflight, capture acquisition, entry recording, kicker readiness,
pre-owner arm refusal, owned readback failure, result-record failure and success.
It checks ordering, lock exclusion around capture, ownership retention and
duplicate refusal. It uses injected arm/capture operations; the low-level arm
and setter tests remain separate. The slot-writer test roundtrips both recovery
records through the actual host writer and decoder. Framing tests reject bad
readback, ordering, transaction and status fields. These tests and strict
Checkpatch pass. The [native compilation receipt](results/recovery-gate-object-compile.json)
records six successful complete-object compilations and the same fifteen
boundary cases on Buildbox at `c421ee8f6ed34ecd0690dd8a1f758c3560d5d78a`.
All twenty-nine returned files match the remote inventory and twenty-eight-entry
checksum manifest, SHA-256
`56a1bff40dc8c282291336f01e932c972960b6b86ab1881cd863c772d01ef379`.
The changed native slot-writer header is byte-identical to the host-tested
header. Native compiler commands retain baseline `-w`; this is not
warning-clean evidence or a link of the complete Wi-Fi/recovery combination.

The [Buildbox object checker](check-recovery-setters.py) accepts the additional
`--gate` argument after the exact published commit. It reconstructs both sides
and compiles complete watchdog, kicker and ramoops units using the pinned
native commands. Complete linking, controller wiring, remaining reset/resource
isolation and an owner-approved radio/restart session remain open. No boot
image, deployment or device action results from this patch or its fixture.
