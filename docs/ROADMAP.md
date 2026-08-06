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
| DVFSP/PCM firmware lease | The historical receiver is positively attributed to the embedded MT6797 hybrid PCM, but mainline has only a read-only stopped-state handoff. | The selected handoff maps CSPM only: no CSRAM mapping, firmware request, PCM residency, start/kick sequence, or callable `SEMA_I2C_DRV` path. Keep I2C6 provider writes blocked. |
| I2C6 transfer | Native packed/FIFO one-byte pointer plus one-byte read is proven for the fixed diagnostic shape. | Do not generalize this to arbitrary transfers or writes. |
| Legacy board contract | The fixed `0x68`/`0x69` tuple is stable and DA9213/DA9214/DA9215-compatible. | The read-only board-contract gate is closed; unique silicon identity remains open. |
| Linux regulator provider | The upstream DA9211/A-family probe is incompatible and no suitable legacy provider is active. | Implement a genuine legacy-family contract instead of emulating it in the A-family probe. |
| Cortex-A72 | CPU8 and CPU9 remain offline in the default profile. An experiment-only retained-cluster path now provides repeatable bounded execution and scheduler-context cleanup on both CPUs, but safe offlining, rail ownership, rollback, resume, and production integration remain unproved. | Keep both CPUs disconnected from the default profile until the provider and safe-off gates below pass. |

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

`safe-off/rollback ownership -> passive provider -> bounded write -> production CPU8 -> production CPU9`

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

That terminal-attribution child passed its offline, deployment, and first
runtime gates. Changed-cycle pstore retained exactly one pair-v3 pass at
10.816179 seconds: CPU8 and CPU9 were online, each completed all three
synchronous callbacks, and the terminal coherently reported the first HPS
CPU9 `-EPERM` result plus 91 matching requests. No pair/startup fault, generic
down-veto leak, panic, BUG, Internal error, or Call trace was retained. Gemian
returned with a changed boot ID and watchdog reason 4; CPU8/9 were offline and
the live-GPT-resolved unmounted boot2 checksum remained exact. The next ordered
action is one exact repeatability cycle from a new ordinary-Gemian baseline.
Only a second exact pass may unblock a separately designed bounded
coherency/load experiment; CPU_OFF and every later power boundary remain
prohibited.

The exact repeatability cycle also passed. Its unique pair-v3 terminal at
11.195671 seconds again showed CPU8/9 online with three reconciled callbacks
each and a complete CPU9 HPS `-EPERM` attribution, this time after 89 matching
requests. The candidate checksum was unchanged; fault exclusions, watchdog
reason 4, offline recovery CPUs 8/9, and unchanged unmounted boot2 all passed.
The prearmed helpers expired while the unit remained shut down awaiting owner
selection, but direct baseline/shutdown/recovery continuity proves a changed
boot ID and immediate pstore recovery for the selected cycle. The bounded
retained-execution gate is now repeatable across two exact runs. Do not run a
third unchanged cycle. The next ordered action is a changed, separately
predeclared coherency/load child that preserves startup, CPU_OFF prohibition,
power state, watchdog recovery, and the proven terminal.

That bounded-coherency child passed its compile, container, deployment, and
first runtime gates. Retained pstore contains one exact pair-v4 pass at
11.385671 seconds: CPUs 8/9 were online, completed all three inherited
callbacks, and then completed a 1,024-round barrier-ordered shared-memory
exchange on the exact target CPUs with zero errors and final sequences
1,024/1,024. The same terminal preserved HPS CPU9 `-EPERM` attribution after 79
matching requests. Declared faults were absent; watchdog reason 4, a changed
recovery boot ID, offline CPUs 8/9, and unchanged unmounted boot2 passed. The
next ordered action is the one exact repeatability cycle earned by the fixed
decision map. Do not extend load, enable CPU_OFF, or cross another power
boundary before that result.

The exact repeatability cycle also passed. Its pair-v4 terminal at 10.945550
seconds independently reproduced all three callbacks per CPU, HPS CPU9
`-EPERM` attribution after 91 matching requests, exactly 1,024 coherency
rounds, zero errors, and final sequences 1,024/1,024. Fault exclusions,
watchdog reason 4, changed recovery boot identity, offline CPUs 8/9, and
unchanged unmounted boot2 passed again. The bounded single-cacheline oracle is
now repeatable across two exact cycles; do not run a third unchanged cycle. The
next ordered action is a separately designed finite multi-cacheline
integrity/load child that preserves startup, HPS veto, CPU_OFF prohibition,
power state, and watchdog recovery. CPU_OFF and later power boundaries remain
blocked.

That changed multi-cacheline child has now passed its source, mutation,
Buildbox compile/binary/stack, reproducible container, guarded deployment, and
two runtime gates. Pair-v5 completed the inherited 1,024-round scalar exchange
and then 64 alternating rounds over 256 aligned cachelines in both exact
cycles: 262,144 exact cross-CPU word checks per cycle, zero errors or
mismatches, and identical cross-matching hashes. Both watchdog recoveries had
CPUs 8/9 offline and unchanged unmounted boot2. The bounded multi-cacheline
oracle is repeatable; do not run a third unchanged cycle. The next ordered
action is a separately designed finite parallel/disjoint-load child that adds a
decision-changing observation while preserving startup, prior scalar and
multiline gates, the HPS veto, CPU_OFF prohibition, power state, and watchdog
recovery. CPU_OFF and later power boundaries remain blocked.

The parallel/disjoint-load child has now passed its complete offline gate and
two attributable runtime cycles. After every inherited pair-v5 predicate, CPUs
8 and 9 concurrently wrote disjoint halves of one 64 KiB working set and
verified the peer half for 128 rounds. Each successful cycle completed 524,288
checks per CPU (1,048,576 total), reported exact 256/256/256 rendezvous counts,
zero errors and mismatches, and identical deterministic cross-matching hashes.
Both watchdog recoveries returned CPUs 8/9 offline with unchanged unmounted
boot2; the repeat used a prearmed changed-cycle pstore observer. The bounded
IPI-context concurrent-load gate is repeatable and must not run unchanged
again. The next ordered action is a separately designed finite scheduler-context
child: bind one kernel task to each retained A72, prove concurrent task-context
dispatch and bounded completion on CPUs 8/9, and preserve every inherited gate,
the HPS veto, CPU_OFF prohibition, power state, watchdog recovery, and
serviceability boundary. This is not yet CPU_OFF/hotplug, OPP/cpufreq, thermal,
or suspend validation.

The scheduler-context child has now passed exact-source generation, 25
negative mutations, Buildbox child-versus-exact-parent compilation, binary and
terminal boundaries, identical diagnostics, the 1,024-byte stack gate, and
reproducible independent Android-v0 container validation. The exact full boot2
SHA-256 is `24377665fa5b9112266890844c06c453bb50e17680b6f6f956035c234c26ff0f`.
Its guarded installer, read-only secondary collector, and fixed runtime
decision map now pass offline review. The candidate has been written to
live-GPT-resolved inactive boot2, matched by full-partition readback, and the
device was cleanly powered off. The next ordered action is one physical boot2
selection and attributable changed-cycle runtime observation.

That first observation rejected the image before evaluating scheduler work.
Multiline and parallel phases completed exactly, but the terminal sampled
`coh_reported=-1` because the child ran inside the inherited coherency worker
before its final parent publication. Pair-v7 correctly reported
`parent_pass=0` and reset scheduler state. Recovery was watchdog-class, CPUs
8/9 were offline, and boot2 remained exact. Do not repeat this image. The next
ordered action is a source-ordering child that publishes the inherited worker
unchanged, snapshots and decides the complete parent predicate, and only then
runs the bounded scheduler phase before adjacent pair-v6/pair-v7 terminals. No
scheduler-context runtime claim exists yet.

That corrective source has now been generated from the exact pair-v6 parent on
Buildbox. The inherited coherency worker is unchanged, both hash vectors pass,
and all 28 negative mutations are rejected. The next ordered action is
Buildbox-only child-versus-exact-parent compile, binary, diagnostics, and stack
review. No corrected container or device action is authorized yet.

The corrected child-versus-exact-parent Buildbox review now passes source,
binary, diagnostics, configuration, and stack gates. The inherited coherency
worker source is identical and its frame is restored to 96 bytes; every new or
changed measured frame remains below 1,024 bytes. The next ordered action is a
new reproducible Android-v0 container and independent offline validation from
corrected Image.gz-dtb SHA-256
`f3b021cc8036a2b3ac205a16a6ff135dbeb70210cda27c639b1543b7a385449e`.
No corrected device action is authorized yet.

The corrected Android-v0 container is now byte-reproducible across two
independent output roots and passes the independently pinned structural,
ramdisk, legacy-ID, extent, zero-padding, provenance, and offline-only gates.
Its exact full boot2 SHA-256 is
`d34b2de509021d5fbbfcca62e3676202fe88b449786daf62b4eb466667fae093`.
The next ordered action is to pin this identity and the rejected attempt-1
predecessor in corrected deployment/runtime tooling, mutation-test those
guards, and commit the complete clean provenance before device access.

The corrected deployment/runtime tooling now passes all static gates and
rejects four identity mutations. It authorizes only the exact transition from
rejected attempt-1 boot2 SHA-256 `24377665fa5b9112266890844c06c453bb50e17680b6f6f956035c234c26ff0f`
to corrected SHA-256
`d34b2de509021d5fbbfcca62e3676202fe88b449786daf62b4eb466667fae093`.
The next ordered action is to commit and push these clean guards, prearm the
changed-cycle pstore observer from ordinary Gemian, perform the guarded boot2
write/readback/shutdown, arm the read-only USB/netcat collector, and physically
select boot2 once.

The guarded write has now resolved inactive, unmounted live-GPT boot2,
confirmed the rejected attempt-1 predecessor, written the corrected image,
matched the full-partition readback, removed temporary state, and shut the
device down without requesting reboot. A changed-cycle pstore observer was
prearmed and observed the deployment shutdown. The next ordered action is to
arm the read-only USB/netcat collector and physically select boot2 once; only
the fixed adjacent pair-v6/pair-v7 and recovery decision map may classify it.

That corrected runtime observation closes the publication-ordering question
and rejects the busy-spin rendezvous. Pair-v6 passed completely and pair-v7
reported `parent_pass=1`; both bound kernel threads entered ordinary task
context on their exact CPUs. CPU9 completed the exact workload and hash. CPU8
entered on CPU8 but exhausted the peer-ready spin before CPU9 joined, after
which both parent waits expired. Changed-cycle watchdog recovery returned CPUs
8/9 offline with boot2 exact and no fatal console marker. This is not a CPU8
dispatch failure. Do not repeat the image. The next ordered action is a source
child with a bounded scheduler-friendly start protocol that cannot monopolize
CPU8 while awaiting CPU9, followed by generation and negative mutation tests;
no Buildbox compile, container, or device action is authorized yet.

The bounded start-gate source tooling is now prepared. Each exact-CPU task
publishes its own ready completion and blocks; the parent boundedly observes
both, authorizes and releases one shared start gate, then applies a fresh
bounded deadline to the unchanged independent workloads and done completions.
The terminal separately reports parent-ready and task-start waits, and 33
negative mutations cover the new protocol. The next ordered action is exact-
parent generation and mutation validation on Buildbox. No compile, container,
or device action is authorized yet.

Exact-parent Buildbox generation now passes both scheduler hash vectors and
rejects all 33 start-gate mutations. The generated patch changes only
`arch/arm64/kernel/psci.c` and has patchset SHA-256
`970c090c080f0a5b03738ea7bdec65edaebc7b1d3b179488202587c157edc845`.
The next ordered action is a Buildbox-only child-versus-exact-parent compile,
binary, diagnostics, terminal, and stack review. No container or device action
is authorized yet.

The start-gate child-versus-exact-parent Buildbox review now passes source,
mutation, compile, binary, expanded-terminal, diagnostics, configuration,
package, and stack gates. Every measured child frame remains below 1,024 bytes;
the start-gate `Image.gz-dtb` SHA-256 is
`21a64e59bbf0a83123ee936cc0dc7bdf00e793d8c290a0e557e24d826abefd2a`.
The next ordered action is a new reproducible Android-v0 container and two
independent offline validations. No device action is authorized yet.

The start-gate Android-v0 container is now byte-reproducible across two
independent roots and passes structural, ramdisk, legacy-ID, extent,
zero-padding, provenance, and offline-only gates. Its exact full boot2 SHA-256
is `2e8c611b1dbe5b79b13f2dec9cf9d77d9b7973a732f63702a6228600bef464b3`.
The next ordered action is to pin this successor, the currently installed
rejected predecessor, and the four new ready/start fields in deployment and
runtime tooling; static and mutation validation must pass before device access.

The start-gate deployment/runtime tools now pass all static gates and reject
four installer identity mutations. They authorize only the transition from
installed rejected checksum
`d34b2de509021d5fbbfcca62e3676202fe88b449786daf62b4eb466667fae093` to
start-gate checksum
`2e8c611b1dbe5b79b13f2dec9cf9d77d9b7973a732f63702a6228600bef464b3`,
and require all four new ready/start fields. The next ordered action is to
commit and push the clean guards, prearm changed-cycle pstore, perform the
guarded write/readback/shutdown, arm USB/netcat, and select boot2 once.

The guarded start-gate write has now resolved inactive, unmounted live-GPT
boot2, confirmed the rejected predecessor, written the exact successor,
matched its full-partition readback, removed temporary state, and shut the
device down without requesting reboot. The prearmed changed-cycle observer saw
the deployment shutdown. The next ordered action is to arm the expanded
read-only USB/netcat collector and physically select boot2 once; only the fixed
start-gate decision map may classify the result.

Start-gate runtime attempt 1 completed a changed-boot-ID, watchdog-class
candidate/recovery cycle, and Gemian recovered on its normal root with CPUs
8/9 offline and inactive boot2 still matching the exact candidate. Both
prearmed observers expired before the delayed physical selection, however,
and the later pstore capture contains only recovery-kernel startup with no
pair-v6 or pair-v7 terminal. This is evidence loss, not a scheduler result.
The next ordered action is one exact repeat with changed-cycle pstore and the
expanded USB/netcat collector armed just in time; the repeat is earned solely
because that new independent observation path can distinguish capture loss
from terminal-not-reached. No design change, Buildbox build, or new boot2 write
is authorized or needed before that observation.

The just-in-time repeat now distinguishes terminal-not-reached from capture
loss. Its changed-cycle console spans candidate userspace startup through a
fatal NULL-pointer dereference at 14.121403 seconds, contains neither pair-v6
nor pair-v7, and ends before PC/LR or a call trace. The exact child runs the
start-gate oracle before emitting either terminal, so the failure is
consistent with that bounded region but cannot yet be assigned to creation,
readiness, release, workload, completion, or cleanup. Watchdog recovery is
healthy, CPUs 8/9 are offline, and boot2 remains exact. Reject this artifact
unchanged. The next ordered action is a one-path source child from the exact
rejected parent that adds durable pre/post markers around each existing
start-gate phase, with marker/order mutation validation before a Buildbox-only
compile. Do not change the workload, synchronization protocol, timeouts, power
boundary, or recovery path, and do not build a container or access the device
yet.

The phase-attribution source tooling is now prepared. It derives from the exact
rejected start-gate series, adds 31 short markers around task readiness/start/
work/done and parent create/wake/ready/release/done/stop phases, and requires
that stripping those marker lines restores the parent `psci.c` byte for byte.
All 31 missing-marker mutations plus task-order and parent-order swaps are
rejected by the new validator. Local syntax and whitespace checks pass; local ShellCheck is
unavailable and remains pending. The next ordered action is clean pushed-commit
Buildbox generation from the exact rejected parent, including the parent
contract, marker equivalence, all negative mutations, and one-path patch
inventory. No compile, container, or device action is authorized yet.

Buildbox exact-parent generation now passes after two bounded tooling-gate
corrections that produced no patch. The accepted job reconstructed and
validated the rejected start-gate parent, retained its two hash vectors and 33
negative mutations, inserted exactly 31 phase markers, rejected all 33 marker
mutations, and proved marker-stripped `psci.c` byte-identical to the parent.
The generated `0002` changes only `arch/arm64/kernel/psci.c`; its SHA-256 is
`30f2b94232d6cf87991a761dd533a4d90a21545c98132079dd73cbeb2cd00234`.
The next ordered action is a Buildbox-only child-versus-exact-parent compile
with diagnostics, configuration, symbols, stack, expanded-terminal, and all
phase-marker strings reviewed. No container or device action is authorized
yet.

The phase-attribution child-versus-exact-parent Buildbox review now passes
source, all 66 parent/marker negative mutations, compilation, identical
diagnostics, configuration, symbols, expanded-terminal, 31 phase-marker,
package, ShellCheck, and stack gates. Every measured child frame remains below
1,024 bytes; the exact accepted `Image.gz-dtb` SHA-256 is
`932dfc84eaea2aa5971a0ade98d5ddb8d592e400830fba47aa81d2a7b02c5811`.
The next ordered action is a reproducible Android-v0 construction from that
exact input in two independent roots, followed by independent structural,
ramdisk, legacy-ID, extent, zero-padding, provenance, and offline-only
validation. No device action is authorized yet.

Phase-attribution attempt 1 produced an attributable restart with incomplete
trace. Exact [deployment evidence](../experiments/2026-08-03-a72-scheduler-context/results/deployment-phase-attribution-20260804.txt),
[runtime classification](../experiments/2026-08-03-a72-scheduler-context/results/runtime-phase-attribution-attempt-1-incomplete-trace-20260804.txt),
and the subsequent
[source/binary audit](../experiments/2026-08-03-a72-scheduler-context/results/source-binary-kthread-park-contract-20260804.txt)
remain in the experiment record. The audit identifies the deterministic design
error: the per-CPU tasks are created parked, the selected wake operation does
not release that state, and ordered stop cleanup does.
Reject the artifact unchanged. The unpark successor was generated from the
clean pushed source-tooling revision, independently reviewed, admitted after
the exact historical parent, and pinned in the compile/package gates; exact
identities and validation remain in the
[generation record](../experiments/2026-08-03-a72-scheduler-context/results/source-generation-unpark-20260804.txt).
The Buildbox-only child-versus-phase-parent compile and package review now
passes; exact identities and acceptance evidence remain in the
[compile record](../experiments/2026-08-03-a72-scheduler-context/results/compile-review-unpark-20260804.txt).
Two independent retained Android-v0 constructions from that exact accepted
child kernel are byte-identical and pass structural, ramdisk, legacy-ID,
extent, zero-padding, provenance, offline-only, pinned-tool-chain, and negative-
mutation validation. Exact identities and review remain in the
[offline-container record](../experiments/2026-08-03-a72-scheduler-context/results/offline-container-review-unpark-20260804.txt).
The guarded live-GPT boot2 installer, fixed runtime decision map, changed-cycle
pstore observer, and read-only USB/netcat collector now pass independent
review for the exact successor and rejected phase predecessor. The final
parser source-pins the unpark marker and pair-v7 schema, requires exact unpark
field/marker causality, and rejects legacy wake evidence; the exact review is
in the
[runtime-tool record](../experiments/2026-08-03-a72-scheduler-context/results/runtime-tools-unpark-20260804.txt)
under the fixed
[decision map](../experiments/2026-08-03-a72-scheduler-context/results/runtime-decision-map-unpark-20260804.txt).
The
[scheduler-context experiment](../experiments/2026-08-03-a72-scheduler-context/README.md)
establishes repeatable bounded CPU8/CPU9 task execution, completion, and cleanup
with attributable watchdog recovery. Do not run a third identical cycle or
enable CPU_OFF.

The offline [Gate 4 safe-off ownership contract](../experiments/2026-08-05-a72-safe-off-ownership-contract/README.md)
now separates CPU9-off with CPU8 retained from the final A72-off transaction
and freezes each boundary's owner, pre-state, readback, timeout, inverse, and
failure response. It rejects the vendor pre-affinity shared-state ordering and
remains blocking: neither transition is implementation-eligible, and another
unchanged device boot cannot close an ownership gap.

The exact offline [secure CPU-off attribution audit](../experiments/2026-08-05-a72-secure-cpu-off-attribution/README.md)
now pins the verified private payload's generic TF-A v1.1 path and corrects a
critical contract assumption: target `CPU_OFF` parks the A72, while the
controlling CPU's later `AFFINITY_INFO` call actively invokes the hardware
teardown. CPU9-off with CPU8 retained changes the target core, a diagnostic
monitor, and the private secure membership ledger without entering any
cluster-power branch. Last-CPU8 teardown additionally owns CCI withdrawal,
cluster/SPM shutdown, the B mux and PLL, and SPM external-isolation bit 1.
Several secure WFI and acknowledgement waits are unbounded. The audit finds no
MP2 DCM or SRAM-LDO write in that callgraph and does not establish provider,
independent readback, policy, notifier, suspend, or runtime completion.

The source-only
[A72 membership and admission contract](../experiments/2026-08-05-a72-membership-admission-contract/README.md)
now freezes the exact operation-bearing token, boot-local one-shot operation
attempts, the only legal Linux membership sequence
(`0x0 -> 0x1 -> 0x3 -> 0x1 -> 0x0`), durable provider-reference transitions,
symmetric public/internal up/down admission with frozen, thaw, and suspend
bypasses denied, callback non-reentrancy, and the target-only one-query rule.
Firmware-private `big_on` remains separate from Linux membership. M02 is exact
rather than a generic observer gate: P15 first records CPU_ON return and
same-MPIDR secondary completion; only after later generic callbacks, both CPUs
online, and inherited cluster/DCM publication may its delayed work be
scheduled. The exact order is initial schedule, approximately 1-second sample,
first reschedule, approximately 6-second sample, second reschedule, then the
approximately 10-second sample. All three require exact CPU8/CPU9 identities,
equal cumulative hits, and final `3/3`. Any post-full-bringup M02 proof or
scheduling failure enters P19 `FAULT`, and P10 cannot commit before sample 3.

The exact source-only
[A72 CPU-up source closure](../experiments/2026-08-05-a72-cpu-up-source-closure/README.md)
now completes the source-attributed early-secondary and post-CPU_ON path
inventory and freezes its branch contracts, while exact same-boot dynamic
CPUHP slot identity remains an explicit A25 proof gap. A41 identifies the first
deterministic admission blocker: an A53-only boot finalizes arm64 state before
a late A72 can introduce BHB (`k=8`), erratum 1742098, and speculative-AT
capabilities.
Their mitigation parameters, alternatives, vectors, compat-HWCAP effects, and
every conditional local capability must be pre-accounted before finalization;
a raw late capability bit is unsafe. Strict boot-capability and ELF-HWCAP
compatibility remain explicit proof rows.

The source-only
[A41 partial capability profile](../experiments/2026-08-05-a72-a41-capability-profile/README.md)
now adds the first default-off, isolated implementation scaffold. Canonical
patches 0148/0149 provide a boot-scoped arm64 attestation lifecycle, independent
MT6797 profile activation, bounded target registration, immutable staged
verification, and release/acquire publication. The exact pre-A41 source parent
and ordered configuration inputs are recorded without claiming that they prove
the running image. Expected target identities are separate from unresolved
observations. The selected profile plans exactly BHB loop `k=8`, erratum
1742098, and speculative-AT, but source/configuration, capability inventory,
registers, firmware, cache/ASID/translation, GIC, HWCAP, and attestation-user
proofs remain explicit blockers; preparation therefore always returns
`-EAGAIN` before any live capability or CPU path can change. The patch-0092
boot and disable vetoes, together with inherited `maxcpus=8`, remain the
independent CPU admission/removal safety boundary. This closes only the
fail-closed lifecycle/profile scaffold. A41 is not complete, READY is
unreachable for the selected profile, and no build, boot candidate, or device
action is authorized.

The source-only
[A41 canonical read-only planner](../experiments/2026-08-05-a72-a41-canonical-planner/README.md)
now extends that scaffold with iteration-bounded traversal of the surviving
canonical arm64 capability descriptors before system finalization. It derives
only the known
BHB loop `k=8`, erratum 1742098, and speculative-AT draft and records their
required future effects; it performs no capability, mitigation, vector,
alternative, HWCAP, or CPU-path mutation. Every other local predicate remains
unresolved, so the capability-inventory blocker stays set. Exact configuration
and source identity, target and cache registers, firmware responses,
ASID/granule/active-VA compatibility, GIC, strict/system/boot capabilities,
native/compat HWCAPs, and A36/P17/P18 consumers remain open. This advances A41
only to `PARTIAL_READ_ONLY_PLANNER`; it does not relax A26/A14, authorize a
build, or justify device action.

The follow-on source-only
[A41 immutable-plan boundary](../experiments/2026-08-05-a72-a41-immutable-plan/README.md)
corrects the partial planner's three-row completeness assumption. The exact
selected expected profile contains 40 compiled local descriptors: 4 can be
classified PRESENT from source/profile-static inputs, 30 ABSENT, and 6 remain
evidence-dependent (GICv5 legacy, ICH_HCR_EL2.TDIR, mismatched cache type,
Spectre-v2, Spectre-v4, and BHB). AMU and hardware dirty-bit management are
already early-present and are not new effects. BHB capability state depends
on target CSV2.3; ClearBHB, ECBHB, WA3, conduit, Spectre-v2 state, and policy
select its method, so loop `k=8` is not evidence of presence.

Patch 0151 introduces ABI 3 separation between fallible per-target evidence,
a state-free immutable complete plan, an architecture-owned monotonic
receipt, and the only READY token later admission consumers may observe. It
describes full separate CPU8/CPU9 AArch64 and AArch32 ID images, cache,
GIC/hyp, WA1/WA2/WA3, ASID, granule, active-VA, native/compat-HWCAP, and typed
CTR/Spectre/BHB/compat-AES/speculative-AT effects. The architecture commit
entry now precedes normal system capability finalization, but its mutation
implementation is unavailable. The MT6797 classifier returns UNRESOLVED for
every row, validation and preparation return `-EAGAIN`, no canonical plan
identity is written, and PLAN_FROZEN, COMMITTED, and READY remain unreachable.
This advances A41 only to `PARTIAL_IMMUTABLE_PLAN_BOUNDARY`; the A26 boot
and A14 disable vetoes plus `maxcpus=8` remain, and no build, boot candidate,
or device action is authorized.

The follow-on source-only
[A41 expected-A72 static census](../experiments/2026-08-05-a72-a41-static-census/README.md)
implements the provisional evaluator across that complete 40-row inventory.
It resolves exactly 4 profile-static rows PRESENT and 30 ABSENT while leaving
the 6 target/firmware-dependent rows unresolved. Source-owned helpers inspect
the actual private KPTI, BBML2, and erratum matcher data without executing a
target predicate on an A53; KPTI command-line state and the architecture's
hypervisor target-implementation override both fail closed. The partial
validator requires the exact expected-only identities, standing blockers,
bitmaps, required-cap set, and provisional compat-AES/speculative-AT effects,
then deliberately returns `-EAGAIN`. No observed target MIDR, dynamic method,
plan identity, PLAN_FROZEN, COMMITTED, or READY state is produced. This
advances A41 only to `PARTIAL_STATIC_CAPABILITY_CENSUS`; all build and device
prohibitions remain unchanged.

The subsequent source-only
[A41 per-target capability planning](../experiments/2026-08-05-a72-a41-per-target-plan/README.md)
bumps the boundary to ABI 4 and binds slot 0 to CPU8 and slot 1 to CPU9 before
any classification. The core evaluates all local descriptors independently,
retains exact per-target classified/present bitmaps, forms the aggregate only
from both attributable results, and rejects duplicate, substituted, residual,
or unregistered target mappings. A versioned provenance record separates
resolved/running configuration, built/running image, and expected/running
command-line identities; only complete matching fields declared RUNTIME could
pass the architecture guard, never a record declared FIXTURE. The origin and
identity fields still come from the profile and are not independently attested
by this milestone, so a trusted runtime producer remains a separate gate. Both
targets remain at the same
34-classified, 4-present, 30-absent, 6-unresolved census; runtime binding and
typed effects remain blocked, validation and preparation return `-EAGAIN`, and
the plan identity stays zero. This advances A41 only to
`PARTIAL_PER_TARGET_PLAN_BOUNDARY`; `maxcpus=8`, patch-0092 boot/disable vetoes,
and all build/device prohibitions remain unchanged.

The follow-on source-only
[A41 six-row fixture evaluator](../experiments/2026-08-05-a72-a41-six-row-fixture/README.md)
bumps the plan boundary to ABI 5 and implements pure Linux-owned GICv5/ICH,
effective-CTR, Spectre-v2, Spectre-v4, and BHB evaluation independently for
CPU8 and CPU9. An exact immutable FIXTURE record classifies all 40 rows for
both targets, including the six previously unresolved rows, and derives the
complete typed CTR, v2, v4, BHB, compat-AES, and speculative-AT effects. The
fixture reaches 40 classified / 8 present / 32 absent with exact target masks,
but it remains non-runtime evidence. The profile validator deliberately returns
`-EAGAIN`; runtime binding, the architecture-owned commit path, plan identity,
PLAN_FROZEN, COMMITTED, READY, and CPU admission remain unavailable. This
advances A41 only to `PARTIAL_SIX_ROW_FIXTURE_EVALUATOR`; it is not arbitrary
firmware-domain coverage, hardware evidence, a build, or a device result.

The follow-on source-only
[A41 runtime-evidence owner boundary](../experiments/2026-08-05-a72-a41-runtime-evidence-owner/README.md)
bumps the lifecycle to ABI 6. The arm64 core now owns a private evidence
record, seals it after hyp-mode resolution and before profile preparation,
and rejects a profile-declared RUNTIME origin or origin NONE paired with any
runtime observation. Release/acquire publication defines the future producer
boundary. The explicit fixture remains available only to the pure evaluator.
No producer exists yet, so the current record seals `SEALED_EMPTY`, retains
the runtime-binding and commit-path blockers, and cannot freeze a plan or
admit CPU8/CPU9. This advances A41 only to
`PARTIAL_RUNTIME_EVIDENCE_OWNER_BOUNDARY`; it is not a build or runtime result.

The next source-only
[A41 kernel-identity binding](../experiments/2026-08-05-a72-a41-kernel-identity/README.md)
bumps the lifecycle to ABI 7 and closes only the configuration, image, and
command-line sub-contract. A strict static expected record is parsed from the
exact `/chosen/gemini-late-cpu-provenance` leaf while the arm64 core derives
the running embedded IKCONFIG, exact GNU build ID, and forced command line
independently. Complete matching inputs can publish `SEALED_IDENTITY`; every
missing, malformed, duplicate, dynamic, substituted, partial, or drifted input
seals empty. Profile ID, configuration-input identity, CPU numbers, MPIDRs,
and the registered target mask must cross-bind before only the runtime-binding
blocker can clear. The record publishes no target observations, system
evidence, capability commitment, plan identity, READY state, or CPU-admission
authority. This advances A41 only to `PARTIAL_KERNEL_IDENTITY_BINDING`; it is
not a build, boot candidate, runtime result, or hardware-support claim.

Actual CPU8/CPU9 register, cache, GIC/hyp, firmware, ASID, translation,
capability, and HWCAP evidence still requires each target to execute or an
independently trusted pre-Linux attestation. Standard PSCI cannot read those
registers remotely, and no direct CPU_ON/CPU_OFF side call may bypass A26,
A14, P30, or the standing boot/disable vetoes.

P30K/C/P/E/U separate CPU_KILL_ME, post-C bare STUCK, panic, pre-C reasoned
STUCK, and default timeout. The timeout path now requires exact-generation
cancellation-versus-publication arbitration because global task, status,
early-status, and completion state can be reused while a target publishes
late. No bounded target park acknowledgment means global CPU-up quarantine and
panic/platform reset, not ordinary runtime failure. P14/P15 publication belongs
immediately after `__cpu_up()==0` before later CPUHP synchronization.

The current canonical series now freezes the first implementation slice as
`PARTIAL_P30_PROTOCOL_MODEL`; the
[P30 generation arbitration experiment](../experiments/2026-08-05-a72-p30-generation-protocol/README.md)
owns its exact provenance and audit evidence. Its dormant C-only object models
exact-token CPU8/CPU9 arbitration, sticky first-cause quarantine, indivisible
publication completion and draining, per-operation opaque one-shot retirement,
and K/C/P/E/U terminal ownership. Static review and a bounded independent
oracle accepted that source-only model, while its KUnit coverage remains
unexecuted.

It has no production callers: P24 ownership, global startup-state replacement,
bounded waits, the actual target park point, P14/P15, branch effect enforcement,
and panic/reset enforcement remain absent. The object is not an assembly ABI
and proves no P30E MMU-off visibility, cache, PoC, or barrier ordering. The
existing MT6797 CPU boot path still returns `-EAGAIN`, CPU disable still returns
false, and A26/A14 remain closed. No build, package, candidate, deployment, or
device action occurred.

The follow-on source-only
[P24 closed transaction-owner model](../experiments/2026-08-05-a72-p24-closed-owner/README.md)
adds the lifecycle and storage boundary that future P17/P18/P24 integration
will require. It begins `CLOSED` and explicitly `UNINITIALIZED`; CPU8 and CPU9
probes are denied before P31 or A38 and cannot consume an attempt, mint a
transaction, claim a P30 token, change provider or membership state, or reach
CPU_ON. Read-only snapshots make that no-effect boundary independently
reviewable. There is deliberately no production caller or opener, and the
default-off KUnit coverage remains unexecuted. This advances the source only
to `PARTIAL_P24_CLOSED_OWNER_MODEL`; it does not implement P17, P18, P24, a
generic admission hook, the P31/A28/mint/A36 transaction, or any hardware
operation.

The next source-only
[P24 closed admission-hook model](../experiments/2026-08-05-a72-p24-closed-hooks/README.md)
adds two generic CPU-up gates. Public requests reach a weak preflight before
CPU-map work, while direct thaw and SMT paths reach a leaf-only validation
before CPUHP locking, state changes, or callbacks. Arm64 dispatches optional
CPU-method callbacks: methods without them and MT6797 CPU0 through CPU7 retain
their existing behavior, while CPU8 and CPU9 route to the read-only closed
owner. The hooks add no transaction, transaction-begin caller, opener,
attempt, token, P30 publication, or positive A72 path; the existing MT6797
boot and disable vetoes remain independent backstops. The exact isolated
profile now passes Buildbox after the R03/P29 proof-storage correction, with
all 119 DTBs and package checksums validated. This advances the source to
`PARTIAL_P24_CLOSED_ADMISSION_HOOKS` but remains compile-only; it is not P17,
P18, P24 success, or runtime CPU admission.

The follow-on source-only
[A28 read-only entry-gate experiment](../experiments/2026-08-05-a72-a28-entry-gate/README.md)
adds an exact validator for the CPU8 and CPU9 entry snapshots: attempt
identity, presence/possible bits, membership, provider, online mask, CPUHP
state, and MPIDR. It is read-only and leaves the owner and dormant P30 state
unchanged. P31 still owns attempt consumption, and there is no production
caller, transaction success, P30 mutation, CPU_ON operation, build, package,
candidate, or device result. This advances the source only to
`PARTIAL_A28_READ_ONLY_ENTRY_GATE`.

The next source-only
[P31 attempt-ledger experiment](../experiments/2026-08-05-a72-p31-attempt-consumption/README.md)
adds the one-shot boot-local attempt edge before A28. It requires the explicit
observer window, consumes only the matching operation bit under the transition
owner, and never rearms it after A28 rejection. The production owner remains
closed, the test-only AVAILABLE seed is not an opener, and no token, P30,
provider, CPUHP, CPU_ON, build, package, candidate, or device result exists.
This advances the source only to `PARTIAL_P31_ATTEMPT_LEDGER`.

The follow-on source-only
[A36 frozen-token experiment](../experiments/2026-08-05-a72-a36-frozen-token/README.md)
retains the transition lock from P31 through A28 and token minting. It binds
the frozen transaction to the exact READY profile identity, target MPIDR, and
operation budgets, but does not validate hardware prestate, arm P30, publish
P17/P18, call a provider, change CPUHP state, issue CPU_ON, build, package, or
touch the device. This advances the source only to
`PARTIAL_A36_FROZEN_TOKEN_MINT`.

The follow-on source-only
[A36 prestate-gate experiment](../experiments/2026-08-05-a72-a36-prestate-gate/README.md)
validates the immutable operation-specific prestate after token minting. CPU8
is bound to the exact one-way DA921x/SPM/PWRAP/DCM and observer-owner record;
CPU9 is bound to the inherited CPU8 cluster/DCM state and empty shared-write
set. Both require the exact generation, cookie, MPIDR, observer window, and
physical `secondary_entry`; a mismatch retires the token as terminal
`REJECTED` without rearming or producing hardware, P17/P18, provider, CPUHP,
CPU_ON, build, package, candidate, or device effects. This advances the source
only to `PARTIAL_A36_PRESTATE_GATE`.

The follow-on source-only
[P17/P18 publication experiment](../experiments/2026-08-05-a72-p17-p18-publication/README.md)
adds the pre-effect `ON_ISSUED` ledger edge. CPU8/P17 requires provider
`NONE`; CPU9/P18 requires the exact durable M01 provider identity still
`HELD`. The edge is one-shot and C-only: it does not call a provider, change
CPUHP or membership, arm P30, issue CPU_ON, build, package, deploy, or touch
the device. This advances the source only to
`PARTIAL_P17_P18_PUBLICATION`.

The follow-on source-only
[P27 preparation-ledger experiment](../experiments/2026-08-05-a72-p27-preparation-ledger/README.md)
adds the CPU8-only preprovider preparation boundary after P17. It consumes
the one-shot preparation budget before any real effect and records only the
same-generation exact MP2-reset-release, B-PLL-ordering, and owner-locked
PWRAP prefix. The C ledger has no MMIO, provider, CPUHP, P30, or CPU_ON effect;
R01/R02 and P28 remain contract-only. This advances the source only to
`PARTIAL_P27_PREPARATION_LEDGER`.

The follow-on source-only
[R01/R02 provider-acquire ledger experiment](../experiments/2026-08-05-a72-provider-acquire-ledger/README.md)
adds the CPU8 provider boundary after P27. R01 consumes the one-shot acquire
budget and publishes `ACQUIRE_INFLIGHT`; R02 accepts only a same-generation
proof of the inherited settle/page/BUCKB/VSEL facts and a durable M01-origin
identity before publishing `HELD`. This is still an attestation-shaped C
ledger: it makes no provider call, regulator vote, hardware mutation, P28
effect, or CPU_ON request. R03/P29 refusal and rollback plus P28 remain open;
the source advances only to `PARTIAL_R01_R02_PROVIDER_LEDGER`.

The follow-on source-only
[R03/P29 provider refusal and rollback experiment](../experiments/2026-08-05-a72-provider-refusal-rollback/README.md)
adds the clean returned-before-vote refusal edge and exact pre-isolation
rollback. R03 requires a same-generation rejection with no provider vote,
provider mutation, or rail mutation and returns the provider ledger to `NONE`;
P29 requires restoration of the complete P27 effect mask with no residual
effect, no P28 start, and no CPU_ON issue before retiring the generation as
`REJECTED`. This remains an attestation-shaped C ledger with no provider call,
MMIO, CPUHP, P30, or CPU_ON effect. The source advances only to
`PARTIAL_R03_P29_REFUSAL_ROLLBACK`; P28 and the real provider owner remain
open.

The follow-on source-only
[P28 post-provider preparation experiment](../experiments/2026-08-05-a72-p28-postprovider-preparation/README.md)
adds the CPU8-only post-provider boundary after R02. It consumes a one-shot
same-generation budget and accepts only the exact isolation `0x2 -> 0x0`,
PWRAP deassertion, software-guard release, two 240 us waits, 1.1 V SRAM-LDO
request, selector `0x8fb`, and stable/valid calibration proof bound to the
held provider identity. Buildbox validates the exact 158-patch commit and
all 119 DTBs; the ledger still performs no isolation write, provider call,
MMIO, CPUHP, P30, or CPU_ON effect. The source advances only to
`PARTIAL_P28_POSTPROVIDER_PREPARATION`; the real provider owner and P24 remain
open.

The next source-only
[resource-only legacy provider experiment](../experiments/2026-08-05-da921x-resource-only-provider/README.md)
adds an explicit opt-in Kconfig boundary after the fixed identification
transcript. It registers two internal descriptors with only linear voltage
listing, selector reads, and enable-state reads; no writable regulator
operation, Device Tree consumer, IRQ, page selector, A72 hook, or CPU_ON path
is present. The provider profile remains separate from the identification and
lifecycle profiles. Buildbox validates the exact pushed 159-patch commit,
all 119 DTBs, and the package checksums; the source therefore advances to
`PARTIAL_RESOURCE_ONLY_PROVIDER`. This is compile-only evidence and does not
establish hardware support or open any device gate.

P32A/D/F/X/R freezes the automatic rollback closure. The controller publishes
P32 before `cpuhp_reset_state()` and the outer reverse range. Target
`.cpu_disable` is the first guard before topology/NUMA removal, online clear,
IPI teardown, and IRQ migration; die/kill remain mandatory defense for the
early and deeper paths. Because higher callbacks may already be removed and
cleanup failures are swallowed behind the original startup error, every
branch is fail-stop, preserves its exact callback/architecture prefix, and
requires a side channel. P32 is not retained-up success.

The off side remains blocked independently. `DEAD` precedes PSCI `CPU_OFF` and
is not physical-off proof; generic pre-CPU_OFF synchronization and later
`cpu_kill` failures are warn-only, and generic PSCI can repeat active
`AFFINITY_INFO` without bounding its first secure call. A40 also requires the
private `big_on` branch proof to stay fresh from A31/P26 through P20 by a
complete writer/caller exclusion or an immediately serialized, non-SMC or
independently concurrency-safe revalidation. The A26 boot veto and A14 disable
veto are all-applicable: neither may be relaxed until every requirement each
names for that operation is implemented and proven.

The next ordered work remains source-only:

1. Implement the authoritative P17/P18/P24 transaction behind the closed hooks
   in the frozen P31 -> A28 -> mint -> A36 -> P17/P18 -> P27 order. The next
   bounded seam is the real provider-owner R01/R02 transaction: the isolated
   resource-only provider and explicit pre-vote refusal callback are now
   Buildbox-validated, and the paired release callback is explicitly refused
   until its owner is proved. A writable provider transaction, the source-only
   P28 post-provider preparation, and the R03/P29 rollback closure still
   precede integrating its exact token with the dormant P30 model and
   controller call sites. The [DA921x page/ownership audit](../experiments/2026-08-06-da921x-page-owner-audit/README.md)
   reconciles the existing legacy page-window, `PAGE_REVERT`, vendor mutex,
   and vendor transfer evidence: it partially explains the recurring
   `0x80`/`0x46` values, but does not prove mainline I2C6/DVFSP ownership or a
   rollback-capable provider transaction. Existing direct-address reads and
   vendor-shaped writes therefore still do not authorize a mainline DA921x
   page-selector or register-data write. The provider-owner refusal profile
   now selects the existing MT6797 DVFSP handoff owner and passed exact
   Buildbox validation; this closes a configuration omission only and does not
   advance the writable-provider or device gates. The source audit now
   attributes the I2C6 ready gate from the Gemini DT access-controller through
   the MT65xx transfer check, and the pinned I2C core confirms that
   `__i2c_transfer()` reaches `master_xfer` under the provider's root adapter
   lock. Linux-side bus serialization is therefore closed; the separate
   firmware/DVFSP owner lease remains open: patch `0174` now holds a validated
   generation/cookie lease across each MT65xx I2C6 transfer and serializes
   suspend/resume permission changes, but it does not represent the vendor
   `SEMA_I2C_DRV` operation. The exact package and checksum evidence is in the
   [page/ownership audit](../experiments/2026-08-06-da921x-page-owner-audit/results/buildbox-transfer-lease-20260806.txt),
   and the reconciled firmware contract is recorded in
   [firmware-owner-lease-20260806.txt](../experiments/2026-08-06-da921x-page-owner-audit/results/firmware-owner-lease-20260806.txt).
   The retained nine-file Gemian PCM archive adds only a bounded negative
   literal scan: no direct CSPM base, PCM control address, CSRAM base, or
   `FW_DONE` value appears, while the vcorefs key/bit patterns are not
   decodable owner proof. The archive contains no LK/TEE/SCP payloads; this
   remains a negative literal-only result, not the final receiver attribution.
   See the [PCM scan](../experiments/2026-08-06-da921x-page-owner-audit/results/pcm-firmware-owner-scan-20260806.txt).
   A decoder-backed audit of the public Gemini MT6797 hybrid PCM source then
   matched the exact `pcm_dvfs_v0.1_160131_02` version named by the retained
   vendor ELF. It finds calls that write SW_PAUSE bit 13 to
   `0x11015608/0c/10`, read/write FW_DONE bit 15 in
   `0x11015614/18/1c/20`, and the same decoded hybrid function's direct I2C6
   path at `0x1100e000` with a CSRAM log update. This positively attributes
   the historical receiver protocol to embedded hybrid PCM firmware, but it
   still does not establish a callable mainline firmware lease or authorize a
   replacement. The evidence is in the [public hybrid PCM owner audit](../experiments/2026-08-06-da921x-page-owner-audit/results/public-hybrid-pcm-owner-disassembly-20260806.txt).
   A source-only mainline load-path audit now makes the missing prerequisite
   explicit: the selected handoff maps only CSPM `0x11015000 + 0x1000`, does
   not map CSRAM `0x0012a000`, does not request or retain a PCM image, and does
   not implement the vendor reset/IM kick/PCM kick/CSRAM initialization
   sequence. I2C6 has no firmware acquire/release call; `0174` is only the
   Linux generation/cookie lease and `0175` remains an unregistered contract.
   Direct `SW_PAUSE`/`FW_DONE` access would therefore target a stopped,
   unstarted receiver and is not a valid next patch. See the
   [mainline PCM load-path audit](../experiments/2026-08-06-da921x-page-owner-audit/results/mainline-pcm-load-path-audit-20260806.txt).
   The minimum replacement/loader boundary is now written as the
   [PCM residency/start contract](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/PCM_START_CONTRACT.md): exact image identity and license,
   stable image memory, CSPM plus CSRAM ownership, clock/semaphore lifetime,
   reset/IM-ready/PCM-kick ordering, CSRAM initialization, and sticky
   generation-bound fault/resume behavior are all required before callback
   registration. Its source-only result keeps the provider fail-closed; it is
   not a firmware copy or a build/device authorization.
   The retained full-backup LK, TEE/ATF, and SCP images were then scanned
   read-only: LK exposes generic bootloader I2C markers, ATF exposes PSCI/iDVFS
   secure-power paths and its existing direct-immediate audit attributes CSPM
   secure-semaphore writes, while SCP exposes DVFS/SPM/IPI paths. The exact
   external audit still finds no PCM-restart writer or `SEMA_I2C_DRV` owner in
   those six secure/boot images; an SCP-local alias remains unexcluded, and none of the six images contains
   the direct controller or CSPM/CSRAM literals. This bounded cross-check adds
   no `SEMA_I2C_DRV` authority. See the
   [secure-image scan](../experiments/2026-08-06-da921x-page-owner-audit/results/secure-owner-image-scan-20260806.txt).
   A bounded AArch64 disassembly of the retained TEE tightens the ATF result:
   its 20 direct CSPM accesses are limited to the keyed `+0` write
   (`0x0b160001`) and the secure-semaphore `+0x448` write/poll on bit 0; no
   direct PCM `+0x18` kick/reset or `SW_RSV0..6` lease words appear in the
   exact code extent. ATF is therefore an interfering secure
   control/semaphore owner, not the missing `SEMA_I2C_DRV` receiver; computed
   or secure aliases remain unexcluded. See the
   [TEE owner disassembly](../experiments/2026-08-06-da921x-page-owner-audit/results/tee-owner-disassembly-20260806.txt).
   The exact retained vendor-kernel ELF separately confirms the historical
   Linux-side contract: semaphore user 1 routes to `PAUSE_I2CDRV`, writes
   SW_PAUSE bit 13 across three clusters, polls FW_DONE bit 15 across three
   status words for 2 ms, and releases the paired clock/reference state around
   one I2C transaction. Together with the decoded public PCM audit, this
   attributes the historical receiver implementation; the current mainline
   invocation path remains unproven. See the
   [vendor-kernel contract](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-kernel-sema-contract-20260806.txt).
   The vendor ELF and Candidate AN observer also match exactly on the CSPM
   register window and offsets (`0x11015000..0x11015fff`, `CON1 0x01c`,
   `PWR_IO_EN 0x02c`, `REG15 0x13c`, timer `0x150`, FSM `0x178`, and
   `SW_RSV0..6 0x608..0x620`). This proves receiver register-window identity,
   including the three pause and three FW_DONE words. Together with the
   decoded public PCM audit this attributes the historical receiver, but
   Candidate AN did not exercise a runtime handshake, observed no FW_DONE
   response, and left I2C_APPM ungated. See the
   [register identity reconciliation](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/receiver-register-identity-20260806.txt).
   A bounded Thumb disassembly now explains the most tempting SCP aliases:
   the bit-13 branch is the DMA 4GB-remap initializer, the nearby `0x2000`
   write clears a Cortex-M NVIC pending bit, and the DVFS/SPM path only logs
   and polls local SPM status. None exposes a physical CSPM/PCM base, I2C6
   owner, or pause/release transaction. This narrows the SCP ambiguity but
   does not exclude computed or secure aliases; the literal-pool inventory
   classifies the remaining `0x400a…` SPM/PMIC, `0xa000…` clock, and
   `0xe000e100+0x180` NVIC paths without promoting an owner. See the
   [SCP disassembly](../experiments/2026-08-06-da921x-page-owner-audit/results/scp-owner-disassembly-20260806.txt)
   and [SCP alias inventory](../experiments/2026-08-06-da921x-page-owner-audit/results/scp-alias-inventory-20260806.txt).
   A follow-up bounded computed-address scan follows the PC-relative literals
   in the DVFS/SPM, clock-setting, and interrupt-control windows and checks
   immediate address construction. It classifies the additional
   `0xa000601c`, `0x400a4010`, and `0x400a4004` references as SCP-local
   control/clock/IRQ state; the only address-like immediate (`orr #0xa0000`)
   builds an encoded SPM request/status value rather than a pointer. No AP
   I2C6/CSPM/PCM/CSRAM or shared-memory target is constructed in those paths,
   and no pause/release transaction appears. Complete CM4 and secure address
   translation remains unavailable, so this strengthens but does not close
   the owner proof; see the [computed-address audit](../experiments/2026-08-06-da921x-page-owner-audit/results/scp-computed-address-audit-20260806.txt).
   Patch `0175` now defines a separately reviewed, default-unregistered
   callback contract for the vendor pause-source lease, including exact
   generation/cookie, 2 ms timeout, three-word pause/acknowledgement checks,
   and paired release. Its exact pushed profile now passes Buildbox compilation
   and package checksums at the current pushed commit
   `23c793aefaccef36253b37654397199c24a228d1`; its single validated package
   has been fetched locally. It performs no MMIO or device operation and does
   not prove an external owner. Attributable firmware evidence remains
   required. See the
   [firmware lease contract](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/).
   Candidate AO already provides the named-unit receiver-side stopped-state
   and shared-clock normalization evidence, with a stable 45-second late check
   while I2C6 remained disabled; do not repeat that boot. The next source-only
   discriminator is to identify a callable mainline path to the historical
   `SEMA_I2C_DRV` lease or specify a separately reviewed replacement protocol,
   followed by page/control-mask ownership, settled readback, and
   rollback-owner proof.
   Before any preflight may return success, add the paired lifecycle closures: clean abort only when
   CPU_ON is proven unissued, exact arming at the platform CPU_ON boundary,
   timeout cancellation/publication arbitration, bounded publication and
   PARKED waits, the real target park acknowledgment, and the immediate
   post-`__cpu_up()` P14/P15 hook. Replace the reused global startup
   task/status/completion state, enforce branch-specific effects and global
   panic/reset, and preserve the current A26/A14 vetoes throughout.
2. Prove and implement P30E through one authoritative MMU-off-visible object
   shared with the controller, including exact tuple layout, cache maintenance,
   point-of-coherency and barrier ordering, assembly failure publication, and
   fail-closed P30U routing for every ambiguous or stale observation. The
   [P30E wire-object contract](../experiments/2026-08-06-a72-p30e-mmuoff-contract/README.md)
   now freezes that source-only boundary: a 20-word object intended for a
   physical handoff, separate
   controller/target writers, full-range clean/readback, and exact-token
   P14/P15 prerequisites. The pinned implementation seam now selects a
   dedicated `.mmuoff.data.bidirectional` section with separate 2 KiB CPU8 and
   CPU9 slots, MPIDR `0x200`/`0x201` selection in a dormant `.idmap.text`
   implementation seam, target CPU/MPIDR validation, and full-range cache
   publication/readback;
   the [implementation seam audit](../experiments/2026-08-06-a72-p30e-mmuoff-contract/results/implementation-seam-audit-20260806.txt)
   records the source evidence. The default-off assembly/C implementation now
   applies through the full series and passes the exact Buildbox package
   validation recorded in the
   [Buildbox result](../experiments/2026-08-06-a72-p30e-mmuoff-contract/results/buildbox-validation-20260806.txt).
   The first implementation-to-contract comparison found compile-invisible
   control-flow and operation-identity gaps. Those repairs now pass the
   corrected source comparison and the complete Buildbox package validation;
   the current evidence is in the
   [implementation comparison](../experiments/2026-08-06-a72-p30e-mmuoff-contract/results/implementation-contract-comparison-20260806.txt)
   and [Buildbox result](../experiments/2026-08-06-a72-p30e-mmuoff-contract/results/buildbox-validation-20260806.txt).
   Patch `0178` now closes the API-side portions of those observations: the
   request carries an explicit slot physical address, the controller checks it
   against the retained static slot and 2 KiB alignment, and the MMU-off side
   compares a separate four-word target-identity sidecar before operation or
   terminal-state publication. Patch `0179` adds the dormant authoritative
   owner-side handoff: the frozen P17/P18/P24 transaction and a distinct
   READY-owned target expectation are equality-checked and copied into one
   exact slot request description. The handoff does not arm P30E, call
   `secondary_entry`, issue CPU_ON/OFF, or change Linux membership. The
   pushed-head 168-patch Buildbox package and local fetch/revalidation pass are
   recorded in the
   [Buildbox result](../experiments/2026-08-06-a72-p30e-mmuoff-contract/results/buildbox-validation-20260806.txt).
   Patch `0180` now closes the reserved-range proof: link-time assertions
   enforce exact two-slot placement without directional-section overlap and
   inside `_text.._end`, which arm64 reserves with memblock; the controller
   rejects a selected slot outside those bounds. Its 169-patch Buildbox
   package and validated local fetch are recorded in the same result. Patch
   `0181` now closes that source-only entry seam: the authoritative owner and
   request carry the exact `__pa_symbol(secondary_entry)` address, the
   canonical entry performs a guarded P30E claim, and malformed/ambiguous state
   parks fail-closed. Target publication is ordered before `CPU_BOOT_SUCCESS`
   and Linux online, with an early-failure publication path. Its exact
   pushed-head 170-patch Buildbox package and validated local fetch are recorded
   in the [Buildbox result](../experiments/2026-08-06-a72-p30e-mmuoff-contract/results/buildbox-validation-20260806.txt),
   with the source comparison and physical audit in the linked experiment
   records. This closes the `secondary_entry` implementation gate only; the
   broader P30/P32/A41/provider/A26/A14 integration and admission gates remain
   open. The existing MT6797 PSCI method still returns `-EAGAIN`, so no CPU_ON,
   device action, or CPU8/CPU9 support claim is authorized.
3. The read-only [P32 hook audit](../experiments/2026-08-06-a72-p32-hook-audit/README.md)
   now maps the exact implementation seams: publish before the outer
   `cpuhp_reset_state()`/reverse range, retain the nested AP rollback prefix,
   guard target `.cpu_disable` before topology/NUMA/online/IPI/IRQ teardown,
   park from target `.cpu_die` without CPU_OFF, and suppress controller
   affinity in `.cpu_kill`. Patch `0182` now implements that exact-generation
   side channel and those fail-stop guards behind a default-off profile.
   Patches `0183`–`0186` now close side-channel consumption, consumed-generation
   retirement, exact operation-to-target identity binding, and the warning-clean
   publication check. The 175-patch Buildbox package, fetched checksum
   validation, and independent 13-probe mutation oracle pass, with no hardware
   write. The current PSCI boot and disable vetoes remain intact.
   The [P32R integration review](../experiments/2026-08-06-a72-p32-r-review/README.md)
   confirms that complete callback/architecture-effect prefix retention and
   the membership/provider/A30 ledger handoff are still open. Its
   [integration design](../experiments/2026-08-06-a72-p32-r-review/DESIGN.md)
   now fixes the bounded callback vector, effect mask, overflow/unknown
   fail-stop behavior, and owner-only ledger handoff that the next source
   patches must implement; the accompanying nine-probe model is design
   evidence, not kernel or runtime validation. The first P32A source slice
   (`0187`) now records the bounded callback prefix, nested AP reset marker,
   outer reset, and reverse-range completion, with a source/format-patch audit
   recorded in the experiment. Buildbox was unavailable during that audit;
   the required Buildbox compile remains the next gate, followed by P32X
   architecture-effect capture and the P32R ledger handoff. The P32X placement
   review now fixes the arm64 disable order and separate DEAD/RCU/park,
   lockdep, and controller-kill boundaries for the next source patch. No
   device action is authorized.
4. Complete the A25 callback/rollback review and re-audit P32R against the
   mutation result, then finish P32A/D/F/X/R using either a reviewed core
   no-auto-rollback interface or the fail-stop `.cpu_disable` plus die/kill
   guard design, retaining every partial callback and architecture effect.
   The current [A25 review](../experiments/2026-08-06-a72-a25-callback-review/README.md)
   passes H01–H15, mandatory dynamic ordering, conditional insertion
   classification, and P32A/D/F/X/R; H13 remains open because no same-boot
   numeric CPUHP-state capture exists yet.
5. Revalidate every applicable A26 CPU-up gate and its A14 CPU-off dependency.
   Only after those closures may a separately reviewed evidence-only target
   transaction be considered; a trusted pre-Linux handoff is the alternative.
   Then return to A41 for separate CPU8/CPU9 registers, cache, WA1/WA2/WA3,
   ASID, translation, GIC/hyp, boot/system/strict capabilities, native/compat
   HWCAPs, canonical evidence/plan identity, the infallible architecture-owned
   pre-finalization commit, and READY binding to A36/P17/P18. Source tests alone
   do not authorize a build, CPU_ON/OFF request, or device action.
6. Close the M02 delayed-work scheduler/observer owner and failure propagation,
   then close A40 private-ledger writer/caller freshness.
7. Only after those CPU-up and branch-selection gates pass, specify the full
   A14 off-completion owner: complete CPU-ops and CPUHP/PM inventories, exact
   target handoff, secure-call concurrency, one-query result propagation, and
   bounded independent post-OFF observers.

Until all applicable A26/A14 gates close, do not generate a CPU_ON/CPU_OFF
candidate or use the device. Source-only builds and static review may proceed
for the explicitly blocked profiles; passive provider work may proceed in
parallel only within its existing no-write, no-consumer boundary.

CPU_OFF, suspend/resume, later power boundaries, a mainline provider write,
and default-profile A72 consumers remain blocked until their separate ownership
and rollback gates close.

Exit: observations and inference are separated, every required writer has one
owner, every pre-irreversible failure has a bounded no-effect or rollback
proof, and every post-irreversible uncertainty has an attributable terminal
recovery path.

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
