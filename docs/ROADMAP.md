# Roadmap

This roadmap describes the current decision path and milestone exits. Detailed
candidate history, build identities, runtime logs, and rejected branches belong
in the [experiment index](../experiments/README.md), not here.

## Immediate objective: a safe legacy DA921x provider boundary

### Visual reboot evidence caution

The owner reported on 2026-07-31 that some earlier white/grey-screen cycles
followed by an apparent automatic reboot may have been reboot-path or boot
selection issues rather than kernel failures. Preserve those observations and
their chronology, but do not use the visual state plus return to Gemian alone
to attribute a fault to the tested kernel or its changed subsystem. Without an
exact runtime identity, durable stage record, or attributable crash/reset
evidence, treat such cycles as inconclusive. Positive identity-gated runtime
results remain valid; causal boundaries previously inferred only by contrast
with an ambiguous visual/reboot cycle are correspondingly weaker.

The current critical path is the external regulator dependency for the MT6797
Cortex-A72 pair.

| Boundary | Current state | Consequence |
| --- | --- | --- |
| Recoverable development boot | Linux 7.1.3 candidates boot from non-primary `boot2`; console, keyboard, USB gadget shell, and native reboot are available. | Preserve this serviceability set as a mandatory gate. |
| Cortex-A53 cluster | CPU0–7 can be online together. | Keep this baseline fixed while regulator work proceeds. |
| I2C6 ownership | DVFSP handoff and shared AP-DMA ownership are understood well enough for the fixed native path. | Do not disturb the working I2C5/AP-DMA owner. |
| I2C6 transfer | Native packed/FIFO one-byte pointer plus one-byte read is proven for the fixed diagnostic shape. | Do not generalize this to arbitrary transfers or writes. |
| Legacy board contract | The fixed `0x68`/`0x69` tuple is stable and DA9213/DA9214/DA9215-compatible. | The read-only board-contract gate is closed; unique silicon identity remains open. |
| Linux regulator provider | The upstream DA9211/A-family probe is incompatible and no suitable legacy provider is active. | Implement a genuine legacy-family contract instead of emulating it in the A-family probe. |
| Cortex-A72 | CPU8 and CPU9 remain offline; rail ownership, rollback, resume, and the full power sequence are unproved. | Keep both CPUs disconnected until the provider gates below pass. |

The durable technical boundary is in
[DA921x, I2C6, and Cortex-A72](hardware/da921x-i2c6-a72.md). The exact
completed diagnostic is in its
[experiment record](../experiments/2026-07-28-da9214-gauss/README.md) and must
not be repeated unchanged.

## High-level path to the project goal

The project goal is a maintainable, upstream-derived Linux system for the
Gemini PDA, not merely a kernel that reaches userspace once. The critical path
is:

1. close the real-compatible DA921x event/serviceability regression without
   weakening the established console, keyboard, USB, CPU0--7, or recovery
   baseline;
2. prove the identification-only legacy DA921x driver can bind, perform its
   fixed read-only contract, and unbind cleanly;
3. finish the regulator, DVFSP, SPM, SRAM-LDO, clock, reset, suspend/resume,
   and rollback ownership audit;
4. register a passive regulator provider while all writable operations and
   consumers remain disconnected;
5. prove one reviewed, bounded write/readback/rollback operation with CPU8 and
   CPU9 still offline;
6. bring up CPU8 with checkpoints and fail-closed rollback, then validate CPU9
   and the complete cluster separately; and
7. complete the persistent-storage, native display/touch, keyboard/USB,
   battery/charging/thermal, suspend, peripheral, and distribution-integration
   milestones around that safe power foundation.

Reusable bindings and drivers move upstream continuously throughout this
sequence. Each local patch has a deletion condition tied to an accepted
upstream version; the end state must not require a permanent Gemini platform
fork.

Work on eMMC, logging, keyboard coverage, USB roles, display/touch, and other
independent subsystems may proceed in parallel only when it preserves the
fixed DA921x/A72 experiment baseline. The immediate critical chain is:

`event regression -> read-only DA921x bind -> passive provider -> bounded write -> CPU8 -> CPU9`

## Ordered gates

### 0. Repair the profile-series invariant — complete

The manifest debt recorded by the
[profile-series invariant audit](../experiments/2026-07-28-profile-series-invariant-audit/README.md)
was repaired on 2026-07-29. The superseded legacy-readonly and active-A72
profiles are no longer selectable, their historical experiment inputs remain
available as evidence, and the kernel wrapper now enforces the invariant
across every manifest profile before selecting one.

The default and fixed board-contract diagnostic profiles were preserved
unchanged. Rejected legacy/provider/A72 patches were not added to the canonical
series. Any useful part of that historical work still requires a new reviewed
logical patch.

Exit met: every selectable manifest profile satisfies the
canonical-subsequence policy and the invariant is enforced automatically.

### 1. Specify the legacy-family driver — complete

The [legacy-family driver and binding contract](../experiments/2026-07-29-da921x-legacy-driver-contract/README.md)
was completed on 2026-07-29.

It specifies a separate identification-only driver for the non-A
DA9213/DA9214/DA9215 programming model. The initial Gemini variant:

- claims only the fixed direct `0x68` and `0x69` addresses;
- accepts only the exact observed tuple through two fixed seven-read passes;
- has no DA9211/A-family fallback, paged regmap, `PAGE_CON`, device-ID,
  register-data write, provider, IRQ, consumer, or A72 path; and
- gives failed probe, unbind, shutdown, suspend, and resume zero hardware
  transactions.

The complete successful probe trace is a
[machine-readable 14-transfer contract](../experiments/2026-07-29-da921x-legacy-driver-contract/probe-contract.json);
every failure trace is a strict prefix. Ownership, constraints, error
handling, cleanup, unbind, and resume behavior are defined in the
[design review](../experiments/2026-07-29-da921x-legacy-driver-contract/DESIGN.md).

Exit met: the contract relies on the public manufacturer register model and
upstream subsystem interfaces rather than vendor policy code, and every
probe-time transaction is statically enumerable.

### 2. Implement and validate an isolated profile — complete

The [legacy identification-only integration](../experiments/2026-07-29-da921x-legacy-bind/README.md)
was completed offline on 2026-07-29. Canonical patches `0123`–`0125` add the
binding, driver, and board description as separate logical changes, selected
only by the `da921x-legacy-bind` profile.

The static validator proves the fixed `0x68`/`0x69` tuple and exact fourteen
reads, and rejects representative retrying, write-bearing, wrong-address, and
provider-bearing mutations. The binding and focused Gemini DT checks pass.
Checkpatch reports no code checks; the patches remain intentionally
non-submission-ready because author DCO certification and maintainer review are
still outstanding.

Exit met: two fresh out-of-tree Linux 7.1.3 assemblies produced byte-identical
`Image`, `Image.gz`, configuration, `System.map`, and Gemini DTB. Both packages
pass provenance, checksum, image-boundary, and experiment validation with the
same source, patchset, and configuration identities. No device was accessed.

### 3. Probe, bind, and unbind only — open after pre-serviceability failure

The first hardware candidate after the completed read-only diagnostic tested
only the isolated driver lifecycle, not a regulator action. Its first boot
failed before recoverable serviceability and automatically returned to Gemian
with watchdog-block-class reset tokens but no attributable pstore record. It
therefore produced no lifecycle evidence and must not be repeated unchanged.

Hypothesis:

> A dedicated legacy-family driver can match the fixed tuple, bind, and unbind
> without a register-data write or loss of the known-good serviceability
> baseline.

Unique attributable evidence:

- exact driver match and lifecycle log;
- fixed tuple read through the isolated driver path;
- I2C counters and a write oracle proving zero register-data writes;
- unchanged CPU0–7, CPU8/9-offline, I2C5/AP-DMA, DVFSP, console, keyboard, USB,
  and reboot state.

Decision:

- success permits the resource-only provider gate;
- a tuple mismatch stops at chip/board identification;
- a transfer or lifecycle failure stays an I2C/driver issue;
- any unexplained serviceability regression blocks provider work.

This boot also provides independent-boot repeatability of the tuple without
repeating the completed diagnostic.

The next diagnostic preserved the exact Gate 3 kernel, oracle, initramfs, and
I2C6 controller description while disabling only the new DA921x DT child. Its
first boot was serviceable: USB, console, keyboard, CPU0--7, handoff, and fatal
log gates passed while no `0x68` client existed and every I2C6 transfer/oracle
counter remained zero. This implicates the enabled child’s automatic
creation/probe path but does not distinguish client creation, early probe
timing, or the fourteen-read logic.

The post-serviceability discriminator kept the child enabled, linked the
identification driver only as a manual-path module, and preserved the exact
Gate 3 DT. Attempt 1 grey-screened and rebooted before USB/netcat
serviceability, so the module was never loaded. Returned Gemian confirmed the
exact boot2 checksum; pstore was empty. The later owner caution about ambiguous
visual/reboot cycles means this attempt does not establish that the candidate
kernel reset. It rules out neither enabled-client creation nor a module-enabled
kernel/configuration effect and provides no fourteen-read probe result.

The exact-current-kernel child-disabled derivative was serviceable on attempt
1. USB, console, keyboard, CPU, handoff, and zero-counter gates passed. No
DA921x code was resident or loadable automatically. This rules out the
module-enabled kernel/configuration boundary only if the prior cycle was an
attributable kernel failure. Under the later owner caution, it positively
proves this child-disabled derivative serviceable but does not attribute the
earlier cycle to the enabled DT-client path.

The exact serviceable artifact was preserved and used to build the next
discriminator: the child is enabled with its resource contract unchanged, and
only its compatible is replaced by diagnostic non-matching value
`dlg,da9214-unbound`. The candidate passed all offline gates, was installed to
live-GPT-resolved `boot2`, passed an independent full-partition byte
comparison, and left the device powered off.

The first selected boot was serviceable. The enabled `1-0068` client existed
with the unmatched compatible, the unchanged resource contract, and no bound
driver. USB, console, keyboard, CPU, handoff, and fatal-log gates passed while
all I2C6 transfer/oracle counters remained zero and no DA921x code was
resident. This proves generic unmatched client creation and the unchanged
resource contract serviceable. It does not, by contrast with an ambiguous
earlier reboot, prove that the real-compatible/modalias path caused a failure.

The module-file discriminator restores `dlg,da9214-legacy` on the exact
module-profile kernel while using the exact Gate 3 initramfs with no module
file or loader path. It passed all offline gates, was installed to
live-GPT-resolved `boot2`, passed an independent full-partition byte
comparison, and left the device powered off.

The first selected boot white-screened and rebooted before console or
USB/netcat serviceability. Returned Gemian and the full boot2 checksum
confirmed the exact candidate; pstore was empty. Because the initramfs
contained no module or loader path, driver execution was unavailable. The
later owner caution nevertheless makes the visual/reboot cycle inconclusive
about whether this kernel failed, so it does not by itself place a causal
failure boundary before module availability.

Exact-source audit found no real-compatible string or match table in the
kernel Image. The DA921x driver is module-only, the uevent helper is disabled,
and the module-free initramfs has no listener. The early string-dependent
paths that remain are the compatible-derived I2C client name and the OF
modalias uevent.

The name-only discriminator preserves the exact kernel and module-free
initramfs while disabling the DT child. It passed all offline gates, was
installed to live-GPT-resolved `boot2`, passed an independent full-partition
byte comparison, and left the device powered off.

The first selected boot was serviceable and every pre-creation gate passed.
The one permitted `new_device` write was rejected because the inherited
initramfs mounts sysfs read-only. No client was created, no driver bound, and
all I2C/oracle counters remained zero. This is safely inconclusive about the
name/I2C-modalias path.

The second selected boot used the same exact artifact with the new bounded
RW-window observation path. The helper created one name-only
`da9214-legacy` client, restored sysfs read-only immediately, and verified that
the client had no OF node and no bound driver. USB/netcat and the complete
serviceability baseline survived while every I2C/oracle counter remained zero.
This proves the compatible-derived client name and I2C modalias serviceable in
that bounded path. The real-compatible OF node and uevent path remain useful
integration boundaries, but are not established as the cause of an ambiguous
earlier reboot.

The OF-modalias suppression candidate preserved the real-compatible OF child,
client name, resources, OF-node attachment, module-free initramfs, and
zero-activity baseline while replacing only the add-event OF modalias with the
already-exonerated I2C fallback. It was fully serviceable. The real-compatible
client remained unbound, all I2C/oracle counters remained zero, and native
reboot returned Gemian. This proves real-compatible OF-node instantiation
serviceable when the OF modalias is suppressed; it motivates testing the
modalias path but does not establish that path as the cause of an ambiguous
earlier reboot.

The private-insertion discriminator generated the exact 38-byte modalias,
inserted it as one terminated `MODALIAS=` entry in a bounded private
`kobj_uevent_env`, validated the complete layout and bytes, discarded it, and
emitted only the safe I2C fallback. Its first selected boot was fully
serviceable with the real client unbound and every I2C/oracle counter at zero;
native reboot returned Gemian. This proves the bounded private environment
insertion mechanics serviceable. The real OF entry's presence during event
emission remains unproved, but is not established as a prior failure cause.

The real-environment rollback discriminator inserted and validated the exact
OF `MODALIAS=` entry in the actual device event, restored the original pointer,
indices, and exact 48-byte target buffer range, then added only the safe I2C
fallback. Its first selected boot was fully serviceable with the real client
unbound, every I2C/oracle counter at zero, and native reboot back to Gemian.
This proves transient real-environment mutation serviceable. Because the
earlier unsuppressed visual/reboot cycle is now treated as ambiguous, it does
not isolate a failure to the OF entry remaining present during event emission.

The first pre-dispatch candidate remained fully serviceable with the real
client unbound and every I2C/oracle counter at zero, but its required success
marker was absent. It suppressed the target event through the fail-closed
validation error path, so it does not yet prove the asserted complete layout.
Source audit at that point introduced another assumption: that the normal I2C
uevent path appends `MODALIAS=i2c:da9214-legacy` after the exact OF modalias,
making ten entries with `SEQNUM`. Later read-only-state evidence showed that
an earlier, still-present `/soc` path assumption had actually failed first, so
the nine-entry runtime was safe but not attributable to its entry count. The
entry-classification experiment below later disproved the ten-entry
assumption: the OF success path returns before the I2C fallback is appended.

On that then-current ten-entry hypothesis, the selected next discriminator was
designed to validate both modalias entries, suppress only transport, and
convert the target event to a successful return before normal cleanup. This
changed the observed error-return behavior rather than merely adding marker
text. Serviceability with the exact success marker would isolate the reset to
broadcast or receiver handling; a reset would implicate complete assembly or
successful cleanup. It remained driver- and transfer-free.

That discriminator is now represented by the named
`da921x-dual-modalias-pre-dispatch-suppression` profile. Its exact runtime gate
requires the ordered OF and I2C modaliases, numeric sequence entry, successful
return, normal cleanup, zero hardware activity, and the complete established
serviceability baseline. It passed offline validation and exact boot2
deployment, but its first selected boot white-screened and rebooted before
console or USB/netcat serviceability. Returned Gemian confirmed the exact
boot2 checksum, a changed boot ID, a watchdog-class reset reason, and empty
pstore. No validation marker survived. Under the later owner caution, this is
an inconclusive pre-serviceability observation rather than proof that the
candidate kernel failed or that the intended checkpoint executed.

Source inspection confirmed that `device_add()` ignores this uevent return
value. Under the then-current ten-entry assumption, the next discriminator was
therefore designed to preserve that validation and transport suppression while
removing the immediate printk and publishing the validation state through an
independent read-only observation path available only if the boot remained
serviceable. A surviving exact state would test the removed-printk hypothesis;
another unattributed visual/reboot cycle would remain inconclusive. The named
`da921x-dual-modalias-state` profile implemented that split. Its Buildbox
package and deterministic independent candidate
assembly passed, and exact boot2 deployment passed full-partition readback
before clean shutdown. The first selected boot was fully serviceable with exact
kernel identity, state `pending`, the real client unbound, and every
I2C/oracle counter at zero. Live sysfs proves the validator inserted a false
`/soc` component in both the client devpath and OF fullname; source
ordering proves the devpath comparison failed first and suppressed transport
before environment validation. This is not evidence about the removed printk.
One identity-gated native reboot returned to known-good Gemian. The named
`da921x-dual-modalias-path-state` profile implements the next
discriminator by correcting only those two expectations while retaining the
same no-printk read-only state, transport suppression, and zero-hardware
baseline. Its Buildbox package, deterministic candidate assembly, exact boot2
deployment, full readback, and clean shutdown passed. On the first selected
boot the console remained serviceable and the owner confirmed exact kernel
identity, but the state was still `pending`. USB did not enumerate before or
after a physical cable reconnect, so the automated verifier could not run.
This proves the two path corrections were insufficient and does not establish
the complete event or the full serviceability baseline.

The next discriminator must expose the ordered validator's last successful
comparison through a read-only state code, covering target identity, each
expected environment entry, final buffer layout, and numeric sequence. It must
retain transport suppression, no printk, no driver/provider/transfer path, and
must not repeat the path-state artifact. The named
`da921x-dual-modalias-stage-state` profile implements stages 0–17 for those
boundaries while preserving the existing one-bit state. Its Buildbox package,
deterministic candidate assembly, exact boot2 deployment, full readback, and
clean shutdown passed. On the first selected boot, exact USB/netcat evidence
reported state `pending` at stage `2`; the target identity and corrected
device path therefore matched, while the following compound envelope-shape
check did not. The unbound real client, CPU0--7 policy, module-free baseline,
USB serviceability, and zero-I2C-activity contract all passed. Local console
and keyboard usability were not separately assessed on this capture.

The next discriminator must retain the identical event and safety behavior
while exposing enough read-only envelope metadata to distinguish entry-count,
envp-capacity/terminator, and packed-buffer-length failures. It must not alter
an expectation merely to force progress, and it must not repeat this artifact.
The named `da921x-dual-modalias-envelope-state` profile implements that exact
read-only split. Its clean Buildbox build, deterministic candidate assembly,
exact boot2 deployment, full readback, and clean shutdown passed. The first
selected boot reported `envp_idx=9`, capacity 64, a valid null terminator,
`buflen=245`, and buffer capacity 2048. The entry count is therefore the sole
failing operand: the validator expects nine fixed entries plus `SEQNUM`, but
the live event contains nine total entries. USB serviceability, CPU0--7,
unbound-client, handoff, and zero-I2C-activity checks passed; local console and
keyboard were not separately assessed.

The named `da921x-dual-modalias-entry-classification` profile was the selected
next discriminator. It preserved the identical event and exposed a read-only
classification for the nine expected fixed entries, duplicates, their ordered
prefix, `SEQNUM` count and first index, and any unexpected bounded entry. It
did not print or transport the target event or copy arbitrary environment
text. Its 126-patch inputs passed the manifest, configuration, patch, and
static checks; exact clean commit `442910e` built successfully on Buildbox.
Two candidate assemblies were byte-identical and all 32 LK gates passed. The
exact candidate was deployed to live-GPT-resolved boot2 from known-good Gemian;
the predecessor, write, flush, and independent full-partition readback all
matched, no backup was created, and shutdown was confirmed. The first selected
boot matched exact identity and reported `present_mask=0xff`, no duplicates,
an eight-entry ordered prefix, one `SEQNUM` at index 8, and no unexpected
entry. Thus the eight OF-path fixed entries are present exactly once and in
order, `MODALIAS=i2c:da9214-legacy` is absent, and `SEQNUM` is the ninth and
final entry. Exact-source inspection confirms that a successful OF modalias
helper returns immediately from `i2c_device_uevent()`; the I2C modalias is a
fallback, not a second entry. USB/netcat serviceability, CPU0--7, the unbound
real client, handoff, and every zero-I2C-activity gate passed. No partition
read, storage write, or reboot occurred.

The next Gate 3 change must correct only the ordered validator to eight fixed
entries plus `SEQNUM`, while preserving the exact target event, transport
suppression, no-printk observation path, module-free unbound client, and
zero-hardware baseline. This is a decision-changing semantic correction, not
an identical retry. A native VM kernel build requires an explicit owner
request. Provider work remains blocked.

The named `da921x-of-event-layout-correction` profile now represents that
single correction. Its 127-patch inputs apply cleanly, its merged configuration
enables the correction only for the new profile, all 44 manifest profiles pass
the canonical-series invariant, and focused strict checkpatch is clean apart
from the intentionally absent experiment-only DCO. Exact clean commit
`0656017` built successfully on Buildbox. Two candidate assemblies were
byte-identical and all 32 LK gates passed; the retained exact candidate is
`candidate-Gate3-da921x-ofevent-461e90ef`. A native reboot returned the prior
runtime to known-good Gemian, then guarded deployment resolved live-GPT boot2,
matched the exact predecessor, wrote without a backup, passed flush and full
independent readback, and shut the device down cleanly. The first selected boot
matched the exact release, installed checksum, USB identity, and route. It
reported validated state, final stage 17, the exact nine-entry envelope and
classification, an unbound real client, and the established serviceability and
zero-I2C-activity baseline. The collector made no partition read, storage
write, or reboot request. This proves complete corrected event assembly,
successful suppression, return, and cleanup safe.

The named `da921x-netlink-skb-serialization` profile implements this exact
split. Its exact clean source built on Buildbox; two assemblies were
byte-identical and all 32 LK gates passed. Guarded deployment matched the exact
predecessor, wrote only live-GPT-resolved boot2 without a new backup, passed
flush and independent full readback, and shut the device down. The first
selected boot matched exact identity. After one recorded host-verifier
infrastructure failure, the corrected BusyBox-compatible helper reported final
stage 18, the unchanged nine-entry event, unbound client, zero I2C activity,
and full serviceability. Stage 18 proves the normal allocator produced the
exact 48-byte header plus 245-byte environment, length 293, root credentials,
destination group 1, and port ID 0; the skb was consumed before socket-list
traversal or multicast. No partition read, storage write, or reboot occurred.

The named `da921x-uevent-listener-discovery` profile retained that exact
stage-18 and zero-hardware baseline, traversed the normal mutex-protected uevent
socket list, and consumed the skb before multicast. Its first selected boot
reached stage 19, observed one socket entry and zero group-1 listeners, and
preserved the exact event, unbound client, zero I2C activity, and full
serviceability baseline. The bounded zero-listener result is specific to this
initramfs boot.

The named `da921x-uevent-no-listener-delivery` profile retained that exact
stage-19 and zero-hardware baseline and exercised the normal untagged delivery
loop only with the runtime-proven topology. Its first connected selected-boot
capture reached stage 20 with one socket, zero listeners, zero skb allocations,
zero broadcasts, and return value zero. The exact event, unbound client, zero
I2C activity, and full serviceability baseline remained unchanged. The
host-side attempt before USB address restoration contains no device evidence.

The named `da921x-uevent-bounded-listener` profile is the input-validated next
Gate 3 discriminator. It retains the exact target after stage 20, requires one
independently observable userspace group-1 listener, accepts one exact-token
replay, and advances to stage 21 only after observing the runtime-proven single
socket plus exactly one listener. The event remains consumed before multicast,
and the helper separately requires no receipt over a bounded 1.5-second wait.
Its exact clean Buildbox package and two byte-identical candidate assemblies
passed offline validation. Guarded live-GPT boot2 installation matched the
exact stage-20 predecessor, passed full readback, and shut the device down.
Two pre-trigger runtime attempts left the one-shot unconsumed; the preserved
second diagnostic isolated the failure to this initramfs's read-only sysfs
mount. A checksum-pinned retry temporarily remounted only virtual sysfs,
restored it read-only, and reached stage 21 with one socket, exactly one
listener, zero broadcasts, and bounded no-receipt. The exact event, unbound
client, zero-I2C activity, and full serviceability baseline remained unchanged.
An independent read-only follow-up confirmed stage 21 and restored read-only
sysfs. No partition read, storage write, or reboot occurred.

The named `da921x-uevent-single-multicast` profile is the next Gate 3
discriminator. Its replacement exact clean Buildbox package and two
byte-identical candidate assemblies passed offline validation after the first
package was rejected for a frozen metadata-identity mismatch. The retained
candidate passed all 32 LK gates. Its frozen selected-boot check first
re-establishes stage 21 with the proven bounded-listener helper, then requires
one allocation, one group-1 broadcast, one exact 293-byte userspace receipt,
and no duplicate while preserving the zero-hardware and serviceability
baseline. Topology, receipt, counter, or baseline changes reject attribution.
Guarded live-GPT installation matched the exact predecessor, passed full
readback, and shut the device down. On the first selected boot, the frozen
predecessor transition re-established stage 21, then the separate multicast
helper reached stage 22 with one socket, one listener, one allocation, one
broadcast, return zero, one exact 293-byte kernel-group-1/root-credential
receipt, and no duplicate. The event, unbound client, CPU policy, zero-I2C
state, and serviceability baseline passed. A fresh read-only postcheck confirmed
persistent stage 22, exact counters, read-only sysfs, and helper removal. No
partition read, storage write, or reboot occurred.

The named `da921x-uevent-untagged-dispatch` profile is the next Gate 3
discriminator. It retains the exact topology, event, and zero-hardware baseline
while allowing one replay through the original untagged delivery function
rather than the experiment-local single-broadcast split. Its 133-patch series,
resolved configuration, manifest invariants, and strict patch checks passed
input validation. Pre-deployment review caught and corrected a stale 21-to-22
stage assertion in the listener; the superseded binary was removed and two
corrected 22-to-23 helper builds were byte-identical. The frozen
runtime decision requires exactly one function entry and return, socket,
listener, allocation, broadcast, exact receipt, and no duplicate. Exact clean
Buildbox compilation passed for the intended pushed commit and the fetched
package revalidated. Two independent candidate assemblies were byte-identical,
the retained copy passed its manifest and all 32 LK gates, and the regenerable
VM copies were removed. Guarded live-GPT deployment matched the exact stage-22
predecessor, passed full readback, and shut the device down without creating a
fresh backup. The first selected-boot runtime capture is next. Visual
white/grey-screen and reboot behavior alone remains inconclusive. On the first
selected boot, the predecessor helpers reconstructed stages 21 and 22, then
the original untagged delivery function reached stage 23 with exactly one
entry and return, one socket, listener, allocation, broadcast, return zero,
one exact 293-byte kernel/root receipt, and no duplicate. The client remained
unbound, CPU and zero-I2C state were unchanged, serviceability passed, and a
fresh read-only postcheck confirmed persistent stage 23, read-only sysfs, and
helper removal. No partition read, storage write, or reboot occurred. The next
Gate 3 discriminator is the named `da921x-uevent-net-broadcast` profile. It
moves exactly one boundary outward to the original
`kobject_uevent_net_broadcast()` wrapper and requires one namespace check, one
untagged route, zero tagged routes, and the same single exact receipt and
zero-hardware baseline. Its 134-patch series, resolved configuration, manifest
invariants, strict patch checks, and two byte-identical static listener builds
passed input validation. Exact clean Buildbox compilation passed for the frozen
pushed commit and the fetched package revalidated. Two independent candidate
assemblies were byte-identical, the retained copy passed its manifest and all
32 LK gates, and the regenerable VM copies were removed. The guarded installer
and four-listener runtime chain passed syntax and ShellCheck. Guarded deployment
resolved the live GPT, matched the exact stage-23 predecessor, passed stable
power, inactive-target, synchronized-write, flush, and full-readback gates, and
shut the device down without creating a fresh backup. One selected `boot2`
runtime capture through the corrected, complete stage-20-to-24 reconstruction
chain passed on the selected boot. The wrapper produced one namespace check,
selected the untagged route once and the tagged route zero times, retained the
single exact receipt, and preserved the unbound-client, CPU, zero-I2C, and
serviceability baseline. A fresh read-only postcheck confirmed persistent
stage 24, exact counters, read-only sysfs, and helper removal. The next Gate 3
boundary is now frozen as the named
`da921x-uevent-normal-fallthrough` profile. It moves exactly one boundary
outward from the proven direct wrapper call: the retained event must traverse
the original `kobject_uevent_env()` network-broadcast call site and return
through the public uevent function exactly once, with return zero, the same
single exact receipt, no duplicate, and the unchanged zero-hardware and
serviceability baseline. The 135-patch series, resolved configuration,
manifest invariants, strict patch checks, and two byte-identical static
listener builds passed input validation. The next action is an exact clean
Buildbox build from the frozen pushed commit. That build passed for exact
commit `6c74785`, the fetched package revalidated, and two independent
candidate assemblies were byte-identical. The retained candidate passed its
manifest and all 32 LK gates; the regenerable VM assemblies were removed. The
next action is guarded live-GPT `boot2` deployment against the exact stage-24
predecessor, full-partition readback, and clean shutdown. Deployment matched
that predecessor, resolved live `boot2`, passed stable-power, inactive-target,
synchronized-write, flush, device-side checksum, and independent full-readback
gates, then confirmed clean shutdown without creating a fresh backup. One
selected `boot2` runtime capture through the checksum-pinned, complete
stage-20-to-25 reconstruction chain passed. The ordinary fallthrough produced
one call-site entry, one call-site return, one public return, and return zero,
retained the single exact 293-byte receipt with no duplicate, and preserved the
unbound-client, CPU, zero-I2C, and serviceability baseline. A fresh read-only
postcheck confirmed persistent stage 25, exact counters, read-only sysfs, and
removal of all nine helpers. The next Gate 3 boundary is a separate natural
`device_add()` experiment with an independent observation path. This result
does not yet prove driver bind, provider behavior, or A72 power. That boundary
is now frozen as the named `da921x-natural-device-add` profile. Patch `0147`
observes the exact boot-time I2C `device_register()` call, its natural uevent
call site and wrapper, and their returns without adding a trigger, replay,
driver, transfer, or hardware write. Exact-source patch application, strict
patch review, manifest invariants, the static contract, and the read-only
runtime checker passed input validation. Exact clean Buildbox compilation
passed for pushed commit `a8a6efa`; the fetched package revalidated. Two
independent Linux candidate assemblies were byte-identical, and the retained
candidate passed its checksum manifest and all 32 LK gates with the unchanged
module-free initramfs and exact real-compatible Gemini DT. The guarded
installer and read-only USB/netcat collector pass syntax and managed-VM
ShellCheck. The next action is deployment to live-GPT-resolved `boot2` against
the exact stage-25 predecessor, full-partition readback, and clean shutdown.
That deployment matched the predecessor and all live-target and stable-power
gates, then passed synchronized write, flush, device-side checksum, independent
full-partition readback, temporary-readback removal, and clean shutdown without
creating a fresh backup. The next action is one selected `boot2` runtime
capture followed by a fresh read-only persistence snapshot. Attempt 1 passed:
the natural device-register entry and return, ordinary uevent call site and
return, public return, wrapper entry and return, namespace check, and untagged
route each occurred exactly once with return zero. The boot-time topology had
one socket, zero listeners, zero allocations, and zero broadcasts. The exact
real-compatible client remained unbound, every I2C/oracle counter stayed zero,
CPU and serviceability state were unchanged, and a separately constructed
direct snapshot confirmed the persistent state and helper removal on the same
boot. No partition read, storage write, or reboot occurred. This closes the
real-compatible event/serviceability regression. The next Gate 3 action is a
separately built identification-only driver-bind experiment using the already
specified fourteen-read contract; provider work remains blocked. No native VM
kernel build was run. That next action is now frozen as the named
`da921x-post-event-lifecycle` profile. It exactly extends the runtime-proven
Stage 26 stack and changes only the already reviewed legacy identification
driver from module-only to built-in, plus attributable release/USB identity.
The runtime decision requires initial `14/8/6` read counters, a
zero-transaction unbind, one exact rebind reaching `28/16/12`, zero
write/other counters throughout, sysfs restored read-only on every exit, and
the unchanged Stage 26/serviceability state. The unchanged fourteen-read
contract, new static validator, runtime classifier and five unsafe mutations,
all 54 manifest profiles, eight invariant mutations, syntax, and managed-VM
ShellCheck passed input validation. Exact clean commit `e0fc95f` built
successfully on Buildbox and the fetched package revalidated. Two independent
managed-Linux candidate assemblies were byte-identical; the retained candidate
passed its manifest and all 32 LK gates with the unchanged module-free
initramfs and exact real-compatible Gemini DT. The guarded installer and
USB/netcat lifecycle collector pass syntax and managed-VM ShellCheck. The next
action is guarded live-GPT `boot2` deployment against the exact Stage 26
predecessor, full-partition readback, and clean shutdown. That deployment
matched the predecessor and all live-target and stable-power gates, then passed
synchronized write, flush, device-side checksum, independent full-partition
readback, temporary-readback removal, and clean shutdown without creating a
fresh backup. Runtime attempt 1 booted the exact candidate and proved the
natural driver bind plus exact `14/8/6` read-only identification, but its
checker stopped before sysfs remount or lifecycle mutation: built-in binding
produced a measured two-wrapper event envelope ending at stage 20, and the
native transfer path correctly left DMA-start zero. The corrected runtime model
now pins those observations, retains `14 -> 14 -> 28` transfer/nonzero-start/IRQ
and oracle requirements, requires DMA-start and all write/other counters to
remain zero, and rejects six unsafe mutations. The next action is the first
actual unbind/rebind lifecycle measurement on the still-running selected boot.
Attempt 2 stopped at one final pre-mutation model mismatch: the page-2 dummy
client is correctly bound to the kernel's exact I2C `dummy` driver rather than
unbound. Its name, modalias, driver link, unchanged `14/8/6` counters,
read-only sysfs, and helper removal were captured. The corrected helper now
requires that exact driver before and after rebind and complete page-2 removal
during unbind; all pre-mutation gates match the live state and seven unsafe
classifier mutations are rejected. Attempt 3 then performed the only lifecycle
sequence. Initial bind passed at `14/8/6`; unbind removed both links with no
counter change; rebind reached `28/16/12`; DMA-start and every write/other
counter remained zero. The helper observed a transiently absent page-2 sysfs
client immediately after bind, while an independent read-only persistence
snapshot found it restored with the exact I2C `dummy` driver alongside the
primary driver, two identity logs, read-only sysfs, helper removal, and complete
serviceability. The combined phase record passes the runtime classifier, and
the helper now models the visibility delay with bounded read-only polling. The
identification lifecycle is closed without a repeated lifecycle action. The
next ordered action is the ownership and rollback audit in Gate 4; passive
provider design may proceed, but writes, consumers, and A72 requests remain
blocked.

### 4. Finish the ownership and rollback audit

In parallel with driver work, use the working Gemian environment and recovered
binaries to capture one natural, synchronized CPU8 transition:

- external buck state before, during, and after the transition;
- voltage and enable operations, including page/address semantics;
- iDVFS/DVFSP, SPM, SRAM-LDO, clock, CCI, DCM, and TOPRGU ordering;
- error paths and inverse/rollback sequence;
- CPU9 differences;
- suspend/resume owner and firmware interaction.

The static Gate 4 audit now inventories 19 boundaries from the exact active
Gemian binary, verified source-equivalent hooks, secure-firmware analysis,
natural CPU8 trigger, and completed mainline DA921x lifecycle. Forward physical
writers are assigned except for the system suspend/resume boundary, but 16
transaction-local pre-states, 11 independent readbacks, three rollback classes,
and resume ownership remain open. Eleven rows require the same owner-local
synchronized Gemian observation; two dynamic-policy rows are deliberately
excluded from the first CPU8 experiment. The next action is to freeze that
read-only observer against the exact active boot contract and build it on an
exact clean pushed commit using a dedicated Buildbox lane. Buildbox reaches the
public source and immutable 2017 Debian snapshot, which resolves exact
cross-GCC `6.3.0-18cross1` and binutils `2.28-5`. The exact 39-package compiler
and interpreter closure is checksum-pinned, and the relocated compiler/linker
produced a valid AArch64 object. The dedicated Git-based compile-review lane is
implemented; its first exact submission
stopped before compilation because normalization exposed precisely the observer
absent-to-`y` delta and an inert public-source-only `CONFIG_ANBOX`
absent-to-explicit-`n` delta. That exact disabled serialization is now pinned;
every other delta remains rejected. No native VM kernel build, register write,
or CPU request is authorized by the audit. The replacement passed that gate
and then stopped before kernel-object compilation because the selected source's
tracked DCT generator requires Python 2. The exact Stretch Python 2.7 runtime
now reproduces `cust.dtsi`. The third exact submission proved generation but
rejected its time-varying checksum; two independent outputs differ only in the
line-3 wall-clock comment. The lane now requires that exact syntax, normalizes
only that comment, and pins the full normalized output. The next result is a
fourth clean pushed-commit vendor source build. That attempt passed all prior
gates and reached target preparation, then modern host GCC rejected the legacy
DTC's duplicate tentative `yylloc` definitions under its `-fno-common`
default. The replacement uses only the tree's `HOST_EXTRACFLAGS=-fcommon`,
matching GCC 6 host semantics without affecting target flags. The next result
was a fifth exact compile. It fixed DTC, but command-line Make precedence
blocked SELinux sub-Makefiles from appending the tracked `classmap.h` include
path. The same flag is now exported through the environment so local additions
survive. The sixth exact compile passed the full patched vendor tree and linked
`vmlinux` and `Image.gz-dtb`; its config delta is exact, expected observer
symbols are present, and its sole extracted diagnostic is the vendor summary
of 69 section mismatches. That attempt did not prove the warning is inherited
or retain compiler stack-use data. The next result is therefore an exact
unpatched-baseline comparison under identical Buildbox inputs, with
byte-identical diagnostic enforcement and retained `-fstack-usage` evidence,
followed by the owner-lock/timing review—not a device boot. That seventh exact
submission passed both full builds, proved byte-identical diagnostics, excluded
observer symbols from the baseline, and captured 2484 stack reports. Its host
fetch then failed closed because four uppercase/lowercase Linux netfilter
filename pairs collide on the case-insensitive destination filesystem. The
replacement nests the stack tree in a checksum-covered case-preserving archive;
the eighth exact submission then repeated both builds and all comparison gates,
source-compared all 2484 archived reports, and fetched cleanly to the host.
Compiler and stack gates pass, but the owner-timing review rejects this revision
for boot: eight broad snapshots per online/offline cycle can add up to 16 ms of
IRQ-disabled semaphore waiting, 104 secure calls, at least 24 I2C transactions,
and an oversized proc-copy critical section. A fifth logical patch is now
prepared: it reduces the ring to 256 records, eliminates the semaphore wait,
and retains only pre/post boundary snapshots. The ninth exact submission built
that five-patch revision and the unpatched baseline, passed byte-identical
diagnostics and case-safe stack retrieval, and proved the compiled 26624-byte
ring. Replacement lock/timing review passes for one bounded diagnostic capture:
there is no snapshot inside the 240-microsecond SRAM-LDO intervals and no
semaphore wait, although one complete cycle still adds 52 secure reads and 12
to 24 I2C transactions. The separate boot-image experiment now passes offline:
two raw assemblies and two 16 MiB padding methods are byte-identical, while the
active Gemian ramdisk, command line, addresses, and appended-DTB contract remain
exact. The raw image is `d3ec1e13123e…` and the padded image is
`33ace2c30a88…`. Its predeployment contract now pins one natural CPU8 cycle,
exact initial identity, stop conditions, observer ordering/retrieval, and a
result-to-next-action matrix. The guarded installer then resolved live logical
`boot2`, required the exact Stage27 predecessor, wrote padded image
`33ace2c30a88…`, passed synchronized/flushed remote and independent full
readbacks, and shut the device down without a fresh backup or automatic reboot.
The boot initially appeared to return to Gemian because the candidate
deliberately retains the exact Gemian ramdisk and root filesystem. A later
read-only check proved both the exact `boot2` partition checksum and the running
observer build identity, closing selection and serviceability. The no-load
collector then stopped correctly because USB power was absent; no pulse ran.
By the time an immutable ring copy was retrieved, it held 256 records with 3474
earlier records overwritten. Its retained tail contains five complete CPU8-up
and six complete CPU8-down transactions, no CPU9 record, successful DA9214 page
restoration and BUCKB transitions, stable secure snapshots, immediate clock
snapshots, complete SPM state, matching masked mutations, matching raw/mapped
PSCI success, and timestamp-valid lifecycle ordering. One 231 ns cross-CPU
append-order inversion proves that transaction review must use monotonic
timestamps rather than ring sequence alone. The last-A72-offline snapshots saw
VSEL `0x32` twice and `0x3a` four times before consistent `0x46` disable state.
These are durable owner constraints, but the full-partition checksum and
diagnostic work preceded capture and the initial ring content is lost, so the
predeclared clean-attribution result is inconclusive. The pulse is prohibited,
the exact image must not be repeated with the same late retrieval path, and the
device shut down cleanly. The retained values are reconciled into the
ownership/rollback audit. The first-complete-cycle latch then froze the state,
concurrency, ABI and owner-effect contract and passed its executable success
path, eight model boundaries, 17 source mutations, exact Buildbox
observer/baseline compile, byte-identical diagnostic attribution, 2484-report
stack gate, owner-lock review, and bounded timing review. Its exact Android-v0
container retained the Gemian ramdisk and passed two assembly and padding paths
plus independent parsing. Guarded boot2 deployment passed a full
write/readback and shutdown. The manually selected candidate then returned ABI
v2 `frozen-complete` with 46 records, no overflow, CPU8-up transaction 2 and
CPU8-down transaction 3. Two reads separated by two seconds were
byte-identical; the exact owner validator passed DA9214 page restoration and
BUCKB `0 -> 1 -> 0`, SPM and TOPRGU readbacks, stable secure sentinels,
immediate clock snapshots, DCM enable/disable, matching raw/mapped PSCI
identities, secondary-online and offline-final ordering. No load or diagnostic
write ran. Optional USB status later reported offline without losing the
already copied evidence, resolving the parent retrieval ambiguity. The
successful up and down paths took 6,008,000 ns and 5,193,154 ns respectively,
and no CPU9 record appeared.

Those exact transaction-local values are now reconciled into the 19-boundary
Gate 4 ownership matrix. All nine forward decisions remain closed; five
failure rollbacks, one CPU9-only observation, and suspend/resume ownership
remain open. The first independent failure/rollback discriminator is now
specified and machine-checked: it stops after CPU8 BUCKB enable and before
external-isolation clear, permits only attempt-owned BUCKB, SPM-reset, and
PWRAP-reset inverses, and rejects 17 pre-state, ownership, readback, and
forbidden-boundary mutations. Exact pinned-source review also proves that the
existing observer helpers cannot serve as safety gates and that an error return
from `cpu_power_on_buck` alone would be unsafe because the caller currently
continues into PSCI, DCM, and iDVFS.

The exact three-patch vendor series now passes reproducible Buildbox
generation, checksum verification, the static safety contract, all 13
generated-patch mutation tripwires, strict style review, and an exact
rollback-versus-parent Buildbox compile comparison. Both trees retain 2484
stack reports and the same sole vendor diagnostic; the rollback caller grows
from 96 to 128 bytes, its new owner helpers use at most 112 bytes, and the
unchanged whole-kernel maximum remains 1488 bytes. Required rollback symbols
are retained and absent from the parent. Owner-lock review finds no cross-owner
nesting, and timing review bounds the successful one-shot path to the inherited
1 ms settle, immediate clock probes, and fixed DA921x/SPM/TOPRGU/secure/DCM
operations without crossing external isolation or reaching PSCI, DCM enable,
iDVFS, SRAM-LDO, or CPU9. The patches remain experiment-only and deliberately
lack a synthetic DCO sign-off. The separate predeployment contract now freezes
the natural one-shot CPU8 trigger, exact compiled identity, expected 30-record
rollback and 14-record pre-state-rejection shapes, immutable two-read evidence,
known-good recovery, owner-visible expectations, and guarded logical-boot2
boundary before container assembly. Two exact Android-v0 assemblies and two
independent 16 MiB padding methods are now byte-identical; the active Gemian
ramdisk and container fields are unchanged, while the exact reviewed kernel is
the only payload delta. The raw image is `58e3efd5dca…` and the full boot2 image
is `6a180e5a62a0…`. The passive ABI-v3 collector now accepts the exact
30-record rollback, 14-record no-write pre-state rejection, and bounded
fault-retain paths while rejecting 18 identity, ordering, final-state,
forbidden-boundary, and stimulus mutations. It copies immutable evidence before
optional power reporting and never requests a CPU, reboot, or write. The
source-pinned guarded installer now also passes syntax, managed-VM ShellCheck,
exact token, candidate-manifest, predecessor, full-readback, cleanup, and
clean-shutdown review. After this complete offline evidence is pushed, the
immediate ordered action is one guarded deployment from known-good Gemian to
live-GPT-resolved inactive boot2, followed by shutdown and manual boot2
selection. Attempt 1 stopped before upload or write because the healthy battery
was at 76% with USB power offline, below the strict above-80% gate. The owner
then explicitly approved this write despite that threshold. A separate
source-pinned wrapper narrows only the capacity floor to 70%, requires an
explicit override flag, and retains Good health plus every identity, target,
predecessor, readback, cleanup, and shutdown gate. After the override evidence
is pushed, the next action is one exact guarded deployment; no boot selection
or runtime action resulted from the deferred attempt. That deployment then
passed from the exact first-cycle predecessor at an owner-authorized 75%: live
GPT resolved inactive boot2, synchronized write and flush completed, remote and
independent full readbacks matched `6a180e5a62a0…`, temporary copies were
removed, and clean shutdown was confirmed. Exact selected-boot identity and
immutable retrieval then passed, but the attributable HPS CPU8 transaction
froze after only begin/end lifecycle records with `-EALREADY`. Exact-source
analysis proves an earlier CPU8 request consumed the atomic one-shot before the
HPS latch opened; because owner records were gated outside that window, the
result cannot say whether that unobserved attempt rejected, rolled back, or
fault-retained. The device returned to verified 2019 Gemian. Unchanged retry is
prohibited. The replacement source now requires the exact HPS capture window
before consuming the one-shot or invoking an owner. Two Buildbox generations
are byte-identical; model/static/mutation gates pass; changed and parent kernels
compile with identical diagnostics; and disassembly proves the observer query
dominates both the atomic operation and first owner call. The new checksum-pinned
Android-v0 raw and 16 MiB padded containers reproduce byte-for-byte, independent
structure analysis passes, and the revised passive collector, normal installer,
and predeployment matrix pass offline review. After that exact evidence is
pushed, the first live attempt correctly deferred at 67% with USB power absent,
before upload or write; boot2 remained unchanged and no staging file remained.
The owner then explicitly approved one deployment despite that power state. A
second source-pinned wrapper narrows only the capacity floor to 60%, requires
an explicit one-use flag, and retains battery presence, Good health, exact
identity, target, predecessor, readback, cleanup, and shutdown gates. The next
action passed at a healthy owner-authorized 65%: live GPT resolved inactive
boot2, the exact predecessor matched, synchronized write and flush completed,
the post-write and independent full readbacks matched `4830a0d0e1a3…`, staging
was removed, and shutdown was confirmed. Identity-gated passive runtime
evidence now closes the pre-isolation BUCKB/reset rollback row: the bounded
forward subset completed, its owned inverse restored the frozen entry state,
no later boundary was crossed, and known-good recovery passed. CPU8/9 remained
offline. Offline owner review then rejected an isolation-only rollback: the
public Linux path has no isolation inverse, and the natural offline restore is
outside the instrumented Linux writer. The next ordered action is source-owner,
timing, watchdog, and pstore validation of one fail-closed CPU8 startup state
machine. It may roll back only before isolation; afterward it must retain power,
record the exact terminal stage, and recover by reset. Source review found that
the normal Gemian watchdog kicker continuously refreshes the hardware deadline,
so the immediate prerequisite is a recovery-only watchdog/pstore discriminator
with every A72 write and request forbidden.

That prerequisite now has a source-drift-checked three-patch generator: it
rejects CPU8/9 before platform action, transfers recovery ownership under the
normal kicker lock, arms a fixed reset-only TOPRGU deadline, and emits one exact
console-ramoops marker. Buildbox patch generation, mutation testing, and review
now pass after closing the CPU-hotplug no-lock reload race. The
changed-versus-unpatched full Buildbox compile, binary ordering review, and
kernel-only Android-v0 container reconstruction also pass. The guarded write
and its full readback passed. Runtime attempt 1 selected the exact image and
automatically returned on the designed time scale with a changed boot ID and a
watchdog-class Gemian reason; boot2 remained exact and CPU8/9 remained offline.
Pstore was empty, so the predeclared exact-marker oracle did not pass. Attempt
2 added a host-side USB/netcat observation path; the short cycle reset before
that interface appeared, but immediate post-return pstore collection recovered
the exact one-time armed marker. It also recorded every CPU8/9 request rejected
before A72 action and no recovery-owner failure. Another automatic changed-boot
ID watchdog-class return, offline CPU8/9, and an unchanged full boot2 checksum
close the recovery prerequisite. Unchanged retry is prohibited. The immediate
next action is Buildbox-only source generation, static/mutation review, and
changed-versus-unpatched compilation of the one-way CPU8 state machine.

That one-way state machine has now passed its complete offline gate and first
hardware attempt. The exact image was installed from the verified
recovery-only predecessor with two full-partition readbacks and clean shutdown.
Retained ramoops then recorded all nine ordered startup checkpoints and exactly
one `cpu8-online-held` terminal marker after generic secondary completion,
CPU8-online accounting, CPU9 absence, and DCM readback. Cluster 2 was reported
on at 845 MHz. This is the first attributable local CPU8-online checkpoint.
About 1.17 seconds later, HPS attempted CPU8 down; a generic hotplug notifier
entered `cpuhvfs_notify_cluster_off` and faulted before the platform
CPU-disable veto could run. Known-good Gemian returned with a changed boot ID,
`kpanic`/`wdt_by_pass_pwk` reasons, CPU8/9 offline, and unchanged boot2. The
unchanged candidate must not be repeated. The next ordered action is an exact
source/order audit and a fail-closed HPS CPU8-down veto before notifier
dispatch, followed by Buildbox compilation and a bounded CPU8
accounting/coherency hold test. Gate 7 is partially closed: startup feasibility
is proven; stability, repeatability, and safe offlining are not.

The two-layer held-online candidate then passed source, mutation, exact-parent
Buildbox comparison, binary, stack, container, deployment, and readback gates.
Its first runtime automatically returned through the fixed watchdog with an
unchanged boot2 and no retained fault. The 65,524-byte console tail begins at
9.166 seconds, however, after the expected substantive CPU8 IPI samples at
about 2.932 and 7.932 seconds; normal traffic overwrote the predeclared success
sequence. Fourteen later CPU9 rejections and no retained panic are consistent
with a held CPU8 but are not the required proof. The result is inconclusive and
the unchanged artifact must not be repeated. The next ordered action is a new
later synchronous CPU8 execution/accounting sample near the existing watchdog
deadline, so it both extends the bounded stability interval and remains in the
retained console window. Only an exact clean pushed commit may be compiled on
Buildbox; CPU9 startup, CPU_OFF, load, DVFS, thermal, and suspend remain blocked.

The later-sample child passed exact-parent generation, mutation testing,
Buildbox child/parent compilation, binary and stack review, reproducible
Android-v0 construction, guarded deployment, and full boot2 readback. Its first
runtime produced exactly one retained held-v2 terminal at 12.415481 seconds:
sample 3 executed on CPU8, CPU8 remained accounted online, CPU9 remained
offline, and the cumulative synchronous callback hit count was three. No held
fault, down veto, predecessor-v1 terminal, notifier fault, panic, Internal
error, or Call trace was retained. A changed boot ID, `wdt_by_pass_pwk`
recovery, offline CPU8/9 under Gemian, and the unchanged full boot2 checksum
close the bounded late-execution question. The next ordered action is one
explicit independent repeatability measurement of this exact artifact; this
is the declared repeatability hypothesis and adds a fresh changed-cycle and
late-execution observation. CPU9 design may begin only after that second pass.

The declared repeatability run then produced a second exact held-v2 terminal
at 12.265514 seconds in an independent changed watchdog cycle. Its terminal,
zero conflict/fault counts, CPU9 exclusion, recovery state, and unchanged
boot2 identity match attempt 1; the late-sample times differ by 0.149967
seconds. The bounded CPU8 execution/accounting diagnostic is therefore
repeatable across two exact runs. The next ordered action is CPU9-specific
source/order/ownership design from this exact CPU8 foundation, with CPU9 kept
disabled until its distinct checkpoints, failures, and recovery decisions pass
offline review. CPU_OFF, load/stress coherency, DVFS/OPP, thermal, and suspend
remain separate closed gates.

The CPU9 cluster-reuse child now passes exact-source generation, all 16 static
mutations, two full Buildbox builds against the exact late-CPU8 parent,
byte-identical inherited diagnostics, durable `cpu_psci_cpu_boot` and `__cpu_up`
binary review, and bounded stack review. Its only forward action is one
standard PSCI CPU_ON after verified CPU8/cluster state; CPU8's cluster
preparation is not replayed. The next ordered action is reproducible Android-v0
container construction and independent offline validation of the exact
accepted Image.gz-dtb. CPU9 remains disabled on the device until that container
and the deployment/runtime decision map pass their own gates.

That exact Android-v0 container now reproduces byte-for-byte across three
independent ignored output roots, retains the known-good Gemian ramdisk, passes
independent header/extent/image-ID parsing, and pads identically to exactly 16
MiB. Its full boot2 image SHA-256 is
`b32bca348efc0fcaffe2b5909c6246d66a4d0fec4102cee091103c42db604d69`.
The next ordered action is guarded-installer and runtime decision-map review
for this sole accepted checksum; no device write is authorized by this result
alone.

The guarded installer and runtime decision map now pass offline review. The
installer inherits live-GPT resolution, inactive/unmounted boot2, exact
predecessor, stable-power, full readback, cleanup, no-fresh-backup, and clean
shutdown gates; the optional netcat path remains read-only. The next ordered
action is one deployment from known-good Gemian followed by one manually
selected boot2 cycle with changed-cycle pstore as the primary observation.

That deployment is now complete: the exact late-CPU8 predecessor was replaced
only on live-GPT-resolved inactive boot2, both full readbacks match the accepted
CPU9 checksum, temporary staging was removed, no fresh backup was made, and the
device was cleanly powered off without reboot. The next ordered action is the
single manually selected boot2 cycle with both observation paths armed.

That cycle rejected the declared success predicate but advanced the CPU9
boundary. At 11.995489 seconds, retained pstore proves CPU8 and CPU9 both
Linux-accounted online and two synchronous callbacks completed on each CPU
with reconciled hit counts. No pair fault, panic, Internal error, or Call trace
was retained. HPS also requested CPU9 down 83 times; every request reached the
inherited veto, and the predeclared map classifies any such request as failure.
The third sample was scheduled beyond the inherited watchdog window, so this
artifact cannot produce its terminal before recovery and must not be repeated.
The next ordered action is a child that keeps standard PSCI-only CPU9 startup
and CPU_OFF prohibition, moves all three pair samples inside the fixed deadline,
and collapses repeated HPS down-pressure reporting into one bounded attributable
record while continuing to veto every request.

That retention-window child passed its complete offline and deployment gates.
Its changed-cycle runtime retained the exact pair-v2 sample-3 pass at
10.885355 seconds: CPU8 and CPU9 were both Linux-accounted online and each
completed all three synchronous callbacks with reconciled hit counts. No
pair/startup fault, generic down-veto leak, panic, Internal error, or Call trace
was retained; watchdog-class recovery and the unchanged boot2 checksum passed.
The 65,524-byte tail starts at 8.847920 seconds, however, after sample 1 and the
expected first HPS rejection, so it contains no required one-shot
`hps-down-held-first cpu=9 error=-1`. The predeclared overall gate is therefore
inconclusive and this exact image must not be repeated. The next ordered action
is a source-minimal child that leaves CPU startup, pair timing, the public-down
barrier, and power sequencing unchanged while snapshotting the accumulated HPS
first result/count/error into the durable sample-3 terminal. A clean terminal
then earns one exact repeatability run before any coherency/load experiment.

CPU9, suspend/resume, later power boundaries, a mainline provider write, and
any A72 consumer remain blocked until their separate ownership and rollback
gates close.

Exit: observations and inference are separated, every required writer has one
owner, and a failed step has a bounded rollback path.

### 5. Register a resource-only provider

Register the provider with all consumers disconnected and writable operations
disabled or unreachable.

Required evidence:

- provider registration performs no register-data write;
- current selector, enable, and constraint reporting is internally consistent;
- bind/unbind and failed-probe cleanup preserve the original state;
- console, keyboard, USB, I2C5/AP-DMA, CPU0–7, and native reboot remain intact.

Test resume in a separate experiment; a successful boot does not establish
resume ownership.

Exit: a provider can exist without changing hardware state.

### 6. Prove one bounded writable operation

Do not reach this gate until the register-write transport, constraints, and
rollback sequence have been reviewed.

The first writable test must:

- keep CPU8 and CPU9 disconnected;
- request one predeclared no-op or bounded state transition;
- read back the exact affected state;
- restore the starting state or execute the reviewed rollback;
- stop immediately on any mismatch;
- retain an independent reboot/recovery path.

Exit: one exact write/readback/rollback protocol passes. This is not yet A72
support.

### 7. Bring up CPU8

Request CPU8 only after the external provider, SPM/SRAM, clocks, CCI, PSCI,
error handling, and recovery sequence are all represented.

The candidate must have a single CPU8 request, strict checkpoints before and
after each power step, a bounded timeout, and a fail-closed rollback. CPU9
remains offline and is tested later as a separate hypothesis.

Exit: CPU8 reaches an attributable online checkpoint, executes a bounded
coherency/accounting test, and can be offlined or safely recovered.

### 8. Validate CPU9 and the complete cluster

After CPU8 is repeatable, test CPU9 separately, then validate:

- CPU topology and cache/CCI coherency under load;
- clock and reset ownership;
- OPP and cpufreq tables with conservative voltage bounds;
- idle states and hotplug;
- thermal protection and throttling;
- suspend/resume;
- scheduler behavior using upstream energy-aware and capacity mechanisms.

Do not transplant vendor HMP, HPS, or PPM policy as the mainline scheduler
design.

Exit: both A72 CPUs pass repeated boot, stress, hotplug, thermal, and suspend
protocols without regressing the A53 or serviceability baseline.

## Parallel work that does not block the A72 sequence

Work on these areas may proceed independently when it does not alter the fixed
A72 experiment baseline:

- harden eMMC access and a persistent development root filesystem;
- separate kernel logs from the interactive console;
- complete keyboard function-key, Page Up/Page Down, modifier, rollover, and
  wake testing;
- replace loader-retained display output with native DRM/panel/backlight
  ownership;
- validate USB role switching and both physical ports;
- upstream reusable MT6797 bindings and drivers as their evidence closes.

## Milestones

Milestones are not strictly serial. The project currently has useful pieces of
M0–M3 while working through an M5 dependency; none is complete merely because
one diagnostic candidate passed.

### M0 — Safe reproducible lab

Outcome: reversible experiments with traceable artifacts.

Exit criteria:

- recovery and protected partitions are documented and tested;
- build, configuration, DTB, initramfs, and packaging inputs are pinned;
- device-writing tools reject ambiguous or active targets;
- hardware facts record provenance and confidence;
- every local kernel patch has an upstream target and deletion condition.

### M1 — Current-mainline boot

Outcome: a current upstream-derived arm64 kernel repeatedly reaches an
observable initramfs from a named non-primary target.

Exit criteria:

- kernel and `/init` execution have attributable evidence;
- RAM, reserved memory, timer, interrupts, PSCI, watchdog, and CPU topology are
  checked;
- bootloader DT and command-line mutations are documented;
- at least ten consecutive cold boots complete without observed corruption;
- required generic and board changes are on a public upstream path.

### M2 — Persistent headless system

Outcome: an ordinary distribution can be administered without UART.

Exit criteria:

- PMIC, required regulators, RTC, restart, and power-off are safe;
- eMMC and partition constraints pass repeated I/O and recovery tests;
- USB gadget networking provides normal remote administration;
- charger and battery telemetry use conservative standard interfaces;
- clean restart and power-off preserve storage.

### M3 — Keyboard and USB serviceability

Outcome: built-in input and external ports provide a stable recovery and use
path.

Exit criteria:

- full keyboard map, modifiers, rollover, wake, LEDs/backlight, and lid/power
  buttons have named tests;
- microSD insertion, I/O, removal, and suspend behavior pass;
- both USB-C paths and supported roles are documented;
- repeated USB hotplug and role transitions pass.

### M4 — Native display and touch

Outcome: a locally interactive system using upstream DRM/KMS and evdev.

Exit criteria:

- MT6797 display dependencies and graph use reviewed bindings;
- the exact panel initializes through a DRM panel driver;
- backlight and power sequencing survive repeated cycles;
- framebuffer console or simple DRM output is reliable;
- calibrated multitouch input works.

### M5 — Mobile-grade power

Outcome: safe battery-powered operation.

Exit criteria:

- regulator and PMIC relationships are correct;
- CPU OPPs and voltage transitions are validated incrementally;
- thermal sensors and conservative trip points protect the SoC and battery;
- runtime PM, idle, suspend, and wake pass repeated tests;
- charging protection remains active during suspend;
- power baselines and limitations are published.

### M6 — Daily-driver peripherals

Outcome: major non-cellular peripherals use upstream subsystems.

Exit criteria:

- audio routing and jack behavior are documented;
- Mali works with Panfrost or has a precise upstream blocker;
- Wi-Fi, Bluetooth, and GNSS have a maintainable firmware boundary;
- supported sensors use standard IIO/input interfaces;
- runtime PM and suspend regressions are covered.

### M7 — Standard boot and distribution integration

Outcome: a distribution consumes the support without a Gemini platform fork.

Exit criteria:

- board DT and generic/MT6797 changes are merged or on an accepted path;
- standard Image, DTB, and initramfs artifacts use a maintained loader;
- boot and recovery choices are owner-controlled;
- one general-purpose distribution uses its normal arm64 packaging flow;
- remaining local patches are only time-bounded upstream backports;
- upgrade and rollback pass.

## Stretch work

Cellular, cameras, external display, and replacement of retained early firmware
do not block the main milestones. Cellular work must first establish shared
memory, crash isolation, firmware ownership, regulatory constraints, and a
maintainable standard userspace interface.

## Cross-cutting upstream workflow

Every milestone follows the same loop:

1. identify existing binding and driver support;
2. reproduce behavior with the least risky discriminator;
3. implement the smallest generic change;
4. validate on Gemini and, where possible, another MT6797 device;
5. submit to the appropriate upstream maintainers;
6. track review revisions and accepted commits;
7. remove the local patch after the containing upstream baseline is selected.
