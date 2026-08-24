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
| DVFSP/PCM firmware lease | The historical receiver is positively attributed to the embedded MT6797 hybrid PCM. Mainline's stopped-state handoff maps the CSPM, SCP-configuration, and Device-APC AO windows and held SCP reset asserted across all 32 entries/exits of the successful bounded transaction. | No firmware request, PCM residency, start/kick sequence, or callable `SEMA_I2C_DRV` path exists. Keep general or concurrent I2C6 writes blocked. |
| I2C6 transfer | Native packed/FIFO pointer-read and one exact one-message two-byte FIFO write are runtime proven. The write completed once with payload `[0xda, 0x46]`, exact no-retry accounting, and stable readback. | This closes only the reviewed same-value shape; arbitrary writes, failure recovery, stress, and resume remain open. |
| Legacy board contract | The fixed `0x68`/`0x69` tuple is stable and DA9213/DA9214/DA9215-compatible. | The read-only board-contract gate is closed; unique silicon identity remains open. |
| Linux regulator provider | The dedicated legacy-family driver registers two read-only providers. A default-off experiment completed one exact same-value write/readback while the target buck was disabled and unselected. A separate hardware-free implementation now models exact positive Buck-B acquire/release and passes all six focused fake-adapter cases. | Gate 6 is closed for the reviewed no-op, and the first Gate-7 provider source boundary is complete offline. Physical transition, production integration, consumers, and CPU requests remain disconnected. |
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

`positive-provider proof -> Gate-7 integration review -> production CPU8 -> production CPU9`

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

The
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
authority. The exact profile also passed a Buildbox compile/package validation
at commit `b81126b0…`. The package authority emitted and the fetched Gemini DTB
contains exactly one `/chosen/gemini-late-cpu-provenance` leaf with a
recomputed matching `record-identity`. This closes only the package-producer
sub-step: the record has not been accepted by a running kernel and supplies no
target observation. This advances A41 only to
`PARTIAL_KERNEL_IDENTITY_BINDING`; the package is not a boot candidate,
runtime result, or hardware-support claim.

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
   while I2C6 remained disabled; do not repeat that boot. The public Gemian
   hybrid source now supplies a positive historical owner path: one driver owns
   CSPM+CSRAM, the I2C_APPM clock, PCM start, and the `SEMA_I2C_DRV`
   pause/release sequence. This closes source attribution only; it does not
   select the embedded image variant, establish redistribution rights, or
   create a callable current-mainline owner. The exact source hashes and line
   anchors are in the [public hybrid owner source result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/public-hybrid-owner-source-20260806.txt).
   The public start path also requires a structured startup-state owner before
   the PCM kick: current OPP, frequency, voltage, VSRAM, ceiling/floor,
   cluster membership, and clock/rail state must be sampled under a transition
   lock and written into the initial CSRAM/control records. The current
   mainline handoff has no MT6797 owner for that state; generic OPP support and
   unrelated VSRAM couplers are not a substitute. The exact inventory and
   decision are in the [startup-state boundary result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/public-owner-startup-state-20260806.txt).
   The next source-only discriminator is therefore a reviewed state-owner
   interface, starting with a disabled read-only MT6797 clock/state contract:
   the existing A72 observer reads Vproc only, while the protected CPU-PLL
   path needs the MCUMIXED/DVFSP semaphore and the A72 path needs a separate
   BigiDVFS secure backend. Direct CPU-PLL MMIO or a static OPP table is not an
   owner. After that contract is independently reviewed, build the bounded
   mainline PCM adapter: admit the exact image and loader domain, replace
   vendor `BUG()`/unbounded waits with bounded sticky-fault paths, prove
   suspend/resume and clock rollback, then register the existing callback
   contract. Only after that owner path is independently reviewed do
   page/control-mask ownership, settled readback, and rollback-owner proof
   advance.
   A public Gemian source rerun independently reproduces the protected
   MCUMIXED/DVFSP clock boundary and the separate BigiDVFS path; it is
   corroboration only because its MT6797 cpufreq source differs from the
   separately pinned Planet reference. See the [public CPU-clock
   corroboration](../experiments/2026-07-12-mt6797-clock-power-reset-recovery/results/public-gemian-cpu-clock-backend-20260806.txt).
   The disabled state-owner contract now applies and compiles through the full
   series on Buildbox at pushed commit `e537c2c`; its validated package is
   compile-only evidence and leaves the owner unregistered, with no PCM start,
   provider write, or device action. See the [state-owner Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-owner-contract-buildbox-20260806.txt).
   Its transition-hold extension (`0193`) now also passes the exact 182-entry
   full-profile Buildbox build at pushed commit `9ba1748`; the package was
   fetched and checksum-validated, but remains compile-only. The hold token
   binds startup-state generation, cluster mask, and owner handle,
   while the owner remains unregistered and the provider stays blocked. See
   the [transition-hold Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-owner-transition-hold-buildbox-20260806.txt).
   The following adapter admission boundary is now modeled source-only: exact
   image identity/residency, complete startup-state generation, exact
   CSPM/CSRAM and clock/semaphore ownership, ordered start acknowledgements,
   and generation-bound lease registration. The model rejects premature or
   stale use and invalidates across suspend/resume; it is not a firmware owner
   or boot evidence. See the [PCM adapter model](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/pcm-adapter-model-20260806.txt).
   A bounded Buildbox source inventory confirms the target seam: generic
   topckgen/apmixedsys clocks and the read-only A72 observer are present, but
   MT6797 cpufreq, protected MCUMIXED/DVFSP ownership, and the BigiDVFS secure
   backend are absent. See the [clock/state-owner inventory](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/mainline-clock-owner-inventory-20260806.txt).
   Patch `0194` now adds a bounded, default-off PCM admission shell around the
   reviewed contract. The exact pushed commit `e1c88a6` applies the complete
   183-entry series on Buildbox, compiles the full arm64 profile, produces 119
   DTBs, passes package checksums, and has its validated package fetched. This
   remains compile-only evidence: no adapter is registered, no provider or
   MMIO path is enabled, and no device action is authorized. See the
   [PCM admission shell Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/pcm-adapter-shell-buildbox-20260806.txt).
   The next gate is still the real protected MCUMIXED/DVFSP and BigiDVFS
   startup-state owner; only after that is independently reviewed may the
   external callbacks be bound and PCM image residency/start and runtime lease
   evidence be collected.
   Patch `0195` now makes the owner identity prerequisite exact and
   default-off: registration must identify both the MCUMIXED/DVFSP CPU-PLL
   backend and the separate BigiDVFS secure backend, claim the complete
   protected resource mask, and return a nonzero owner handle. The full
   184-entry series and package passed Buildbox at commit `5e94f04`; the
   owner remains unregistered, with no provider, MMIO, firmware start, or
   device action. See the [protected identity Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-owner-identity-buildbox-20260806.txt).
   The next ordered step is to implement and independently review those two
   protected startup-state backends, including authoritative OPP/frequency/
   voltage/VSRAM capture and transition ownership, before binding callbacks or
   admitting PCM image residency/start.
   Patch `0196` now supplies the bounded composition seam for those two
   protected domains. It accepts only exact MCUMIXED/DVFSP CPU-PLL and BigiDVFS
   secure descriptors, merges complete LL/L/CCI and B snapshots only when
   generations and owner handles agree, and pairs both transition holds with
   fail-closed rollback/invalidation. The exact pushed commit `06f0a87` applies
   all 185 series entries on Buildbox, compiles the full profile, produces 119
   DTBs, passes package checksums, and has its validated package fetched. This
   is compile-only evidence: the backend callbacks are external and
   unregistered, with no provider, MMIO, secure call, firmware action, or
   device boot. See the [protected composition Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/protected-state-backend-composition-buildbox-20260806.txt).
   Patch `0197` now adds the smallest disabled-only MCUMIXED/CSPM clock
   readback transport. The exact pushed commit `2c9d1b9` applies all 186
   canonical entries on Buildbox, compiles the dedicated arm64 profile,
   produces 119 DTBs, passes package checksums, and has its validated package
   fetched. The profile keeps the DT node and infracfg driver disabled; the
   transport only performs a bounded semaphore acquire/read/release sequence
   and does not register an owner or clock provider. This is compile-only
   protocol evidence with no secure call, firmware action, device write, or
   CPU8/CPU9 admission. See the [protected clock readback Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/protected-clock-readback-buildbox-20260806.txt).
   Patch `0198` now adds the matching disabled-only BigiDVFS readback
   transport. It calls only the documented `0xc200035f` secure REG_READ
   service, whitelists the four exact protected addresses, and rejects
   sign-extended or unknown returns as a sticky fault; unvalidated getter FIDs
   and secure writes are excluded. The exact pushed commit `43b596a` applies
   all 187 canonical entries on Buildbox, compiles the combined arm64
   profile, produces 119 DTBs, passes package checksums, and has its validated
   package fetched. Both nodes remain disabled, with no owner/provider,
   firmware action, device write, or CPU8/CPU9 admission. See the [combined
   protected-readback Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/protected-readback-buildbox-20260806.txt).
   The clean pushed follow-up revision `6c3cb4f` was rebuilt on Buildbox after
   the resume request and reproduced byte-identical kernel, DTB, and map
   outputs; it adds no device or CPU8/CPU9 evidence.
   The next ordered gate is the real, independently reviewed implementation of
   both protected startup-state backends, including authoritative
   OPP/frequency/voltage/VSRAM capture, transition locks, suspend/fault
   invalidation, and runtime identity evidence.
   Patch `0199` now binds the CPU-PLL and BigiDVFS snapshots, protected owner
   identity, and every paired transition hold to one nonzero opaque
   transition-owner handle, in addition to the existing generation and owner
   checks. The exact pushed commit `8f0aadf` applies all 188 canonical entries
   on Buildbox, produces 119 DTBs, passes package checksums, and has its
   validated package fetched. This is still a compile-only contract: it does
   not implement or validate the historical `cpufreq_mutex`, register an
   owner/provider, perform a secure or firmware operation, or admit CPU8/CPU9.
   See the [protected transition-owner Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/protected-transition-owner-buildbox-20260806.txt).
   The next step is the independently reviewed calibrated state owner and
   transition-lock implementation with clock/rail arbitration,
   suspend/fault invalidation, and runtime identity evidence.
   Patch `0200` now makes that boundary reject guessed static tables: the
   protected identity and both backend snapshots must carry efuse-variant,
   EEM/PTP, PPM-limit, live VPROC/VSRAM, clock-owner, and rail-owner
   provenance, a mutable-table epoch, and a nonzero calibration handle, with
   identical provenance across the two backends. The exact pushed revision
   `4cecc04` applies all 189 canonical entries on Buildbox, produces 119 DTBs,
   passes package checksums, and has its validated package fetched. Both
   backends remain unregistered and default-off; the byte-identical dormant
   image is not a hardware-support or CPU8/CPU9 result. See the
   [calibrated-state provenance Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/calibrated-state-provenance-buildbox-20260806.txt).
   A read-only public-source protocol revalidation now closes the exact
   BigiDVFS secure-call family and the MCUMIXED/DVFSP semaphore sequence:
   `0xc20003b0`--`0xc20003c1` plus secure read/write, the protected
   `0x1001a000` window, CSPM `+0x440`, the 2 ms bounded acquire, and the
   IRQ/spinlock release ordering. This is protocol identity only; the target
   firmware variant/response, authoritative OPP/rail/cluster state, and
   mainline arbitration with SPM/ATF remain unproven. The historical fatal
   timeout paths cannot be copied directly. Keep the 0196 owner unregistered
   and the provider/CPU8/CPU9 gates closed while the default-off adapters and
   their rollback/state proof are implemented. See the
   [protected-owner protocol result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/protected-owner-protocol-20260806.txt).
   A public DVFS-state audit also revalidates the historical
   `__set_cpuhvfs_init_sta()` owner: it samples OPP, physical frequency,
   Vproc, VSRAM, ceiling/floor limits, and cluster membership under the
   vendor `cpufreq_mutex` before the PCM kick. Its state tables depend on
   efuse-selected variants, EEM/PTP mutation, and PPM limits, so a static OPP
   table is not portable. Mainline still lacks the equivalent cpufreq,
   calibration, and CPU-rail owner. The next implementation task is to define
   that owner boundary and bind both protected backends under one transition
   lock; keep the 0196 owner and provider gates closed meanwhile. See the
   [public DVFS state-owner result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/public-dvfs-state-owner-20260806.txt).
   Patch `0201` now binds that required calibration provenance to the protected
   owner lifecycle. A future provider must snapshot and validate the complete
   mutable EEM/PTP/PPM state, hold it across the paired CPU-PLL/BigiDVFS
   transition, release it, and receive suspend/fault invalidation; generation,
   transition-owner, and provenance values must be echoed exactly by the
   calibration owner and both protected backends. The exact pushed revision
   `f984738` applies all 190 canonical entries on Buildbox, produces 119 DTBs,
   passes package checksums, and has its validated package fetched. This is
   compile-only admission evidence: the owner/provider remain unregistered and
   default-off, with no calibration provider, firmware action, device boot, or
   CPU8/CPU9 admission. See the
   [calibration lifecycle Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/calibration-lifecycle-buildbox-20260806.txt).
   Patch `0202` now requires an explicit external transition lock/unlock pair
   from that future clock/rail owner and holds it across composite snapshot,
   validation, paired hold/release, and invalidation; failed CPU-PLL holds also
   roll back the calibration hold. The exact pushed revision `d85cffe` applies
   all 191 canonical entries on Buildbox, produces 119 DTBs, passes package
   checksums, and has its validated package fetched. This remains compile-only
   admission evidence: the owner/provider remain unregistered and default-off,
   with no calibration provider, firmware action, device boot, or CPU8/CPU9
   admission. See the
   [transition-lock Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/transition-lock-buildbox-20260806.txt).
   Patch `0203` now makes that lock-protected admission require a concrete
   calibrated-state payload: stable MON phase, the BIG/L/2L/CCI EEM/PTP banks,
   ordered frequency rows with VPROC/VSRAM/PPM values, and independent
   thermal, clock-owner, and rail-owner generations. The exact pushed revision
   `652d164` applies all 192 canonical entries on Buildbox, produces 119 DTBs,
   passes package checksums, and has its validated package fetched. This is
   still compile-only admission evidence: the owner/provider remain
   unregistered and default-off, with no EEM/thermal or PMIC/clock access,
   firmware action, device boot, or CPU8/CPU9 admission. See the
   [calibrated table-state Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/calibrated-table-state-buildbox-20260806.txt).
   Patch `0204` now adds a source-backed, readback-only EEM/PTP boundary through
   the existing MT6797 thermal resource owner. It serializes PTPCORESEL bank
   selection under the thermal lock, reads raw status plus the documented
   frequency/VOP anchors for BIG/L/2L/CCI, and restores the exact selector
   word. Revision `20ad8b6` applies all 193 canonical entries on Buildbox,
   compiles the thermal object and full arm64 kernel, produces 119 DTBs, passes
   package checksums, and fetches the validated package. The thermal node and
   provider remain default-off; no EEM phase, calibrated VPROC/VSRAM/PPM table,
   rail/clock/secure-firmware action, device boot, or CPU8/CPU9 admission
   occurred. See the [EEM readback Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/eem-readback-buildbox-20260806.txt).
   Patch `0205` now adds the source-backed, read-only conversion boundary from
   that locked readback into the calibrated-state contract. It requires
   caller-owned silicon-selected frequency/PPM rows, recorded VPROC caps, live
   VSRAM, voltage limits, temperature, owner generations, and complete
   provenance; it matches the eight anchors, applies the BIG versus normal EEM
   units, interpolates all sixteen rows, applies the low-temperature offset and
   caps, and validates the VSRAM delta. Revision `df2c410` applies all 194
   canonical entries on Buildbox, compiles the full arm64 kernel without
   warnings from the new helper, produces 119 DTBs, passes package checksums,
   and has its validated package fetched. This remains compile-only: the
   thermal node and provider remain default-off, no EEM phase or hardware write
   occurred, and CPU8/CPU9 admission remains closed. See the
   [EEM calibration-builder Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/eem-calibration-builder-buildbox-20260806.txt).
   Patch `0206` now adds a pure, source-backed decoder over the existing
   disabled protected clock readbacks. It preserves generation tags and raw
   mux/divider selectors, rejects malformed or in-flight PLL samples, and
   applies the recovered 26 MHz PCW/POSDIV and ARMPLLDIV_CKDIV formulas to LL,
   L, B, and CCI frequencies. Revision `4d5d8da` applies all 195 canonical
   entries on Buildbox, compiles the full arm64 kernel, produces 119 DTBs,
   passes package checksums, and has its validated package fetched. This is
   still compile-only: no clock or rail owner, provider, secure call, hardware
   write, firmware action, device boot, or CPU8/CPU9 admission is enabled. See
   the [clock-state decoder Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/clock-state-decoder-buildbox-20260806.txt).
   Patch `0207` now binds the vendor-identified CPU and PM transition events
   (`CPU_ONLINE`, `CPU_DOWN_PREPARE`, `CPU_DOWN_FAILED`,
   `PM_SUSPEND_PREPARE`, and `PM_POST_SUSPEND`) plus clock, rail, and PCM-fault
   events to the existing state-owner invalidation reasons through a default-off
   monotonic event ledger. Replayed or non-monotonic sequence/generation events
   are rejected; no notifier is registered and no hardware operation is added.
   Revision `870dcc1` applies all 196 canonical entries on Buildbox, compiles
   the full arm64 profile, produces 119 DTBs, passes package checksums, and has
   its validated package fetched. This remains compile-only: the owner/provider
   stay unregistered and no secure call, firmware action, device boot, or
   CPU8/CPU9 admission occurred. See the [runtime invalidation Buildbox
   result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/runtime-invalidation-buildbox-20260806.txt).
   Patch `0208` now connects that ledger to the Linux 7.1.3 lifecycle APIs:
   the CPU-hotplug state machine supplies online/down-prepare/down-failed
   events, and the PM notifier chain supplies suspend/resume events. Binding
   registration requires an active state owner, arms only after both hooks
   succeed, serializes the generation-tagged source callback with the ledger,
   and disarms before removing hooks. Revision `44f617d` applies all 197
   canonical entries on Buildbox, compiles the full arm64 profile, produces
   119 DTBs, passes package checksums, and has its validated package fetched.
   No caller registers the binding, so this remains compile-only evidence with
   no provider, hardware, firmware, device, or CPU8/CPU9 action. See the
   [runtime notifier binding Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/runtime-binding-buildbox-20260806.txt).
   Patch `0209` adds the missing source-to-owner conversion boundary: it joins
   the decoded protected-clock state, calibrated MON/EEM table state, and the
   future owner's complete live fields for all four clusters. It rejects
   incomplete or guessed state, requires each current frequency to match both
   the decoded clock and a calibrated table row, and checks provenance,
   generations, and bank/phase identity. Revision `7b59354` applies all 198
   canonical entries on Buildbox, produces 119 DTBs, passes package checksums,
   and has its validated package fetched. This is still compile-only; the
   owner/provider remain unregistered and no hardware, firmware, device, or
   CPU8/CPU9 action occurred. See the [state-snapshot Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-snapshot-buildbox-20260806.txt).
   Patch `0210` now supplies one callback-only source adapter for the future
   owner. Under the owner's transition lock it orders protected clock and
   BigiDVFS readback, EEM readback and calibration construction, live-field
   collection, and the four-cluster assembler; any missing source or
   conversion failure aborts without publishing a snapshot. Revision `8b7434c`
   applies all 199 canonical entries on Buildbox, produces 119 DTBs, passes
   package checksums, and has its validated package fetched. This remains
   compile-only: callbacks are external, no owner/provider is registered, and
   no hardware, firmware, device, or CPU8/CPU9 action occurred. See the
   [state-source adapter Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-source-adapter-buildbox-20260809.txt).
   Patch `0211` now makes the three readback inputs concrete: a caller-owned
   device tuple feeds the existing protected clock, BigiDVFS, and thermal EEM
   transports into that adapter. Initialization fails closed for missing
   devices or disabled backend configuration, retains no device references,
   and leaves calibration-table and live-state callbacks mandatory for the
   eventual owner. Revision `e962efb` applies all 200 canonical entries on
   Buildbox, produces 119 DTBs, passes package checksums, and has its validated
   package fetched. This remains compile-only: no provider/platform driver is
   registered, and no direct MMIO, secure write, firmware, device, or CPU8/CPU9
   action occurred. See the [source-backend bridge Buildbox
   result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-source-backend-bridge-buildbox-20260809.txt).
   The clean pushed documentation head `75aa3e0` was subsequently rebuilt on
   Buildbox to resume the workflow. It reapplied the same 200-entry series,
   reproduced the package hashes, passed the 119-DTB checksum validation, and
   fetched only the validated package; see the [Buildbox rerun result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-source-backend-bridge-buildbox-rerun-20260809.txt).
   This is a reproducibility confirmation only and does not change hardware
   support or open the owner/provider and CPU8/CPU9 gates.
   The later documentation head 85f3fb6 was rebuilt through the same explicit
   Buildbox profile, again applying all 200 canonical entries, producing 119
   DTBs, passing package checksums, and fetching only the validated package.
   See the [Buildbox resume result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-source-backend-bridge-buildbox-resume-20260809.txt).
   This is reproducibility evidence only and does not change hardware support
   or open the owner/provider and CPU8/CPU9 gates.
   Patch `0212` now exposes the retained LK `/chosen/atag,devinfo` 19-word
   `M_HW_RES` handoff as a separately named, read-only NVMEM cell and passes
   its validated ABI into the dormant calibration callback. The exact
   `dvfsp_handoff` DTS consumer target is present but no owner or provider is
   registered. Revision `91a64e6` applies all 201 canonical entries on
   Buildbox, compiles the Gemini DTB and full arm64 image, produces 119 DTBs,
   passes package checksums, and fetches only the validated package. See the
   [PTP handoff Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-source-ptp-handoff-buildbox-20260809.txt).
   This remains compile-only: no calibration values were read from hardware,
   no firmware/rail/clock operation or device boot occurred, and CPU8/CPU9
   admission remains closed.
   Patch `0213` now decodes the source-backed `M_HW_RES1`, `M_HW_RES7`, and
   `M_HW_RES9` fields into explicit BIG/L/2L/CCI INIT/MON, DVFS-level, and
   bin-selection state before the dormant calibration callback is reached.
   The decoder is pure and fail-closed: all four detector banks must report
   both INIT and MON enabled, and calibration provenance now requires a
   nonzero efuse-variant identity. It adds no provider, MMIO, secure call,
   rail/clock operation, firmware action, device boot, or CPU8/CPU9 admission;
   revision `e335ba8` applies all 202 canonical entries on Buildbox, compiles
   the Gemini DTB and full arm64 image, produces 119 DTBs, passes package
   checksums, and fetches only the validated package. See the [PTP state
   decoder Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-source-ptp-decode-buildbox-20260809.txt).
   This remains compile-only: no runtime calibration was read and no hardware,
   firmware, device, or CPU8/CPU9 action occurred.
   Patch `0214` now makes the decoded PTP state a required calibration-builder
   input and validates the BIG/L/2L/CCI bank identity, INIT/MON enablement,
   DVFS level, and bin range before the builder accepts it. Revision `be44cbc`
   applies all 203 canonical entries on Buildbox, compiles the Gemini DTB and
   full arm64 image, produces 119 DTBs, passes package checksums, and fetches
   only the validated package. See the [PTP calibration-binding Buildbox
   result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-source-ptp-calibration-buildbox-20260809.txt).
   This remains a pure, default-off conversion seam: no provider registration,
   runtime calibration read, hardware, firmware, device, or CPU8/CPU9 action
   occurred.
   Patch `0215` now binds the PTP-derived silicon identity, calibration rows,
   live state, full provenance, and owner/transition handles under one
   transition mutex, with dormant owner callbacks for
   identify/snapshot/validate/invalidate. Revision `180d5d7` applies 204
   canonical series entries on Buildbox, produces 119 DTBs, passes package
   checksums, and fetches only the validated package. See the [calibrated
   state-owner source Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-owner-source-buildbox-20260809.txt).
   This remains a source-only, default-off binding layer: the actual
   efuse/EEM, PMIC/clock, and generation-producing source callbacks plus
   protected owner registration are still the next implementation gate. No
   hardware, firmware, device, or CPU8/CPU9 action occurred.
   Patch `0216` now binds that source to an external clock/rail transition lock
   and monotonic generation callback. It rejects a generation change during a
   full readback/conversion snapshot and rejects generation rollback, while
   exposing only dormant owner callbacks. Revision `0808526` applies 205
   canonical series entries on Buildbox, produces 119 DTBs, passes package
   checksums, and fetches only the validated package. See the
   [transition-generation arbitration Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-owner-arbitration-buildbox-20260809.txt).
   This is still compile-only and unregistered: the real efuse/EEM/PMIC/clock
   provider and protected owner registration remain open.
   Patch `0217` now latches arbitration faults: generation read errors,
   zero/rollback, mid-snapshot changes, and explicit invalidation invalidate
   the source and reject reuse until reinitialization. Revision `29ca791`
   applies 206 canonical series entries on Buildbox, produces 119 DTBs, passes
   package checksums, and fetches only the validated package. See the
   [arbitration-fault Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-owner-arbitration-fault-buildbox-20260809.txt).
   This remains a compile-only lifecycle guard: no real owner/provider,
   hardware operation, device boot, or CPU8/CPU9 admission was added.
   Patch `0218` now provides the explicit opt-in registration and
   unregistration lifecycle for the arbitrated state owner. It stores the
   callback table in the arbitration object, binds the external transition
   hold/release callbacks, runs the existing protected identity check before
   registration, and invalidates the source before unregistration. Revision
   `340b9bd` applies 207 canonical series entries on Buildbox, produces 119
   DTBs, passes package checksums, and fetches only the validated package; see
   the [state-owner registration Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-owner-registration-buildbox-20260809.txt).
   The lifecycle remains uncalled in the default profile: no provider is
   registered, no hardware operation or device boot occurred, and CPU8/CPU9
   admission remains closed.
   The clean documentation head `668a62f` was then rebuilt on Buildbox with
   the same explicit profile; it reproduced the 207-entry package, all image
   and DTB checksums, and fetched only the validated package. See the
   [registration Buildbox rerun receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-owner-registration-buildbox-rerun-20260809.txt).
   This is compile-only reproducibility evidence and does not change the
   provider, hardware, device, or CPU8/CPU9 gate.
   Patch `0219` now requires the existing complete snapshot and validation
   callbacks to succeed before publishing the owner registry, and clears the
   private callback table on every failed registration. It is default-off and
   contains no hardware operation; a real calibrated EEM/PTP/PPM and
   PMIC/clock provider is still required.
   Corrected revision `accd595` applies all 208 canonical entries on Buildbox,
   produces 119 DTBs, passes package checksums, and fetches only the validated
   package. See the [0219 Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-owner-registration-gate-buildbox-20260809.txt).
   This confirms patch application and compilation only: the provider is still
   absent and CPU8/CPU9 admission remains closed.
   Clean follow-up head `4e7c502` was then rebuilt with the same explicit
   profile, reproducing the same 208-entry package and checksums and fetching
   only the validated package. See the [Buildbox resume receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-owner-registration-gate-buildbox-resume-20260810.txt).
   This remains compile-only evidence: no provider or hardware support claim
   was added, no device action occurred, and CPU8/CPU9 admission remains
   closed.
   A bounded read-only Gemian resource-owner probe confirms that vendor
   `cspm`, `mt-eem`, `mt-ppm`, `mt-cpufreq`, and `mt_idvfs_driver` bindings are
   present, but no authoritative generation or transition-lock endpoint is
   exported. Existing procfs/debugfs surfaces therefore cannot serve as the
   mainline owner. See the [resource-owner boundary probe](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/live-resource-owner-boundary-probe-20260810.txt).
   The next provider must bridge efuse/PTP identity, mutable PPM rows, live
   VPROC/VSRAM, and clock/rail generations under one transition lock.
   A read-only Gemian probe now confirms the runtime source boundary on the
   named device: the EEM handoff and 16-entry PPM tables are exposed, while
   one-second samples show OPP and VPROC/VSRAM changes that are not a coherent
   frequency snapshot. Raw calibration/table payloads were redacted. See the
   [sanitized live-source probe](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/live-dvfs-owner-source-probe-20260809.txt).
   The next implementation must therefore hold the real transition lock and
   publish one generation-tagged frequency, VPROC/VSRAM, PPM/membership, and
   EEM/PTP state snapshot.
   The next ordered gate remains an independently reviewed implementation of
   the real calibrated EEM/PTP/PPM state provider: it must supply the actual
   efuse-selected variant, mutable PPM rows and limits, live VPROC/VSRAM, and
   clock/rail generation under one transition lock. The registration lifecycle
   now exists, but it must continue to fail closed until those callbacks are
   backed by named runtime evidence. The decoder, event ledger, notifier
   binding, snapshot assembler, and registration bridge are conversion and
   lifecycle seams, not hardware ownership proof. Until that provider exists,
   the protected backends and CPU8/CPU9 admission remain closed.
   Patch `0220` now carries the calibrated thermal-zone maximum in the locked
   MT6797 EEM readback and requires the calibration builder to consume that
   exact value, restoring the selector before return. Revision `109aaf3` applies
   all 209 canonical entries on Buildbox, produces 119 DTBs, passes package
   checksums, and fetches only the validated package; see the [EEM temperature
   readback Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/eem-temperature-readback-buildbox-20260810.txt).
   This remains a compile-only prerequisite: no real provider, generation
   callback, hardware operation, device boot, or CPU8/CPU9 admission was added.
   The next implementation must still bind real EEM/PTP/PPM, PMIC/clock rails,
   and transition generations under one authoritative owner.
   Patch `0221` now extends the disabled clock readback through the vendor-
   mapped CSPM hardware-semaphore transaction. It captures the three physical-
   cluster limit words and four current-state words, and decodes the vendor OPP
   reversal, pause/enable flags, and raw VPROC/VSRAM codes while retaining the
   CCI current word without fabricating a CCI limit. Revision `4fada45` applies
   all 210 canonical entries on Buildbox, produces 119 DTBs, passes package
   checksums, and fetches only the validated package; see the
   [CSPM live-state readback Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/cspm-live-state-readback-buildbox-20260810.txt).
   This remains a compile-only source prerequisite: PPM rows, real rail/clock
   generation, provider registration, hardware operation, device boot, and
   CPU8/CPU9 admission remain closed.
   Patch `0222` adds a strict, disabled MT6797 PPM snapshot contract for the
   vendor's LL/L/B physical clusters. It validates the exact 16-entry tables,
   cluster topology, current client limits, advice fields, descending frequency
   order, and explicit floor/ceiling index mapping. A caller-held vendor PPM
   lock and nonzero table epoch are required; CCI limits, per-row PPM limits,
   provider registration, and hardware actions are intentionally not supplied.
   Revision `028c460` applies all 211 canonical entries on Buildbox, produces
   119 DTBs, passes package checksums, and fetches only the validated package;
   see the [PPM snapshot contract Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/ppm-snapshot-contract-buildbox-20260810.txt).
   This remains compile-only: the real PPM/EEM/PTP and PMIC/clock owner,
   generation source, device boot, and CPU8/CPU9 admission remain closed.
   Patch `0223` binds the validated PPM snapshot into the protected
   state-source pipeline. A PTP-bound PPM read is mandatory; its nonzero epoch
   must match calibrated and live provenance; every LL/L/B live frequency must
   be an exact vendor-table row; and physical-cluster floor/ceiling values are
   derived from the current client index interval. CCI still has no fabricated
   PPM limit. The initial `dd89fbc` attempt was rejected before compilation by
   a whitespace-only patch-context mismatch; corrected revision `7c4bd43`
   applies all 212 canonical entries on Buildbox, produces 119 DTBs, passes
   package checksums, and fetches only the validated package. See the [PPM
   state-source binding Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/ppm-state-source-binding-buildbox-20260810.txt).
   This remains compile-only and default-off: the real external PPM/EEM/PTP
   and PMIC/clock owner, generation callbacks, device boot, and CPU8/CPU9
   admission remain closed.
   The clean pushed documentation commit `3f07c40` was subsequently rebuilt
   on Buildbox and reproduced the same content-addressed package; the receipt
   records both validated job identities.
   Patch `0224` now requires the exact 16-row LL/L/B PPM frequency tables to
   match the EEM-derived calibration rows, accounting for PPM's descending
   order versus the calibration state's ascending order. CCI remains excluded
   because no vendor CCI PPM table is available. Clean revision `04e7ad0`
   applies all 213 canonical entries on Buildbox, produces 119 DTBs, passes
   package checksums, and fetches only the validated package; see the
   [PPM/EEM table-identity Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/ppm-eem-table-identity-buildbox-20260810.txt).
   This remains compile-only and default-off: a real EEM/PTP/PPM and PMIC/clock
   provider, generation callbacks, device boot, and CPU8/CPU9 admission remain
   closed.
   Patch `0225` binds the exact validated PPM snapshot into the EEM calibration
   builder. Calibration receives the PPM snapshot directly, requires its
   nonzero table epoch to match calibration provenance, and checks the
   descending PPM B/L/LL rows against the ascending EEM BIG/L/2L rows before
   constructing calibration state. CCI remains excluded because no vendor CCI
   PPM table is available; per-row PPM limits remain provider-owned and are not
   invented here. Clean revision `47339d7` applies all 214 canonical entries on
   Buildbox, produces 119 DTBs, passes package checksums, and fetches only the
   validated package; see the [PPM calibration binding Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/ppm-calibration-binding-buildbox-20260810.txt).
   This remains compile-only and default-off: the real EEM/PTP/PPM and PMIC/clock
   provider, generation callbacks, device boot, and CPU8/CPU9 admission remain
   closed.
   Patch `0226` tightens the protected snapshot assembler at the next coherence
   boundary. After the live frequency selects an exact calibrated row, live
   VPROC and VSRAM must equal that row's calibrated rail pair; a mixed-frequency
   rail sample is rejected. This closes the incoherent condition seen in the
   read-only Gemian source probe while leaving generation production, PMIC/clock
   ownership, and PPM policy ownership to the real provider. Clean revision
   `26341a4` applies all 215 canonical entries on Buildbox, produces 119 DTBs,
   passes package checksums, and fetches only the validated package; see the
   [live-rail coherence Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/live-rail-coherence-buildbox-20260810.txt).
   This remains compile-only and default-off: no provider registration,
   hardware operation, device boot, or CPU8/CPU9 admission was added.
   Patch `0227` now makes the missing PPM policy source explicit. A provider
   must supply exact frequency and per-row limit rows for all four EEM banks,
   including CCI, with one epoch shared by calibration; the state-source ABI
   and owner callback carry both the PPM snapshot and policy object. Final
   revision `31edbb9` applies all 216 canonical entries on Buildbox, produces
   119 DTBs, passes package checksums, and fetches only the validated package;
   see the [PPM policy binding Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/ppm-policy-binding-buildbox-20260810.txt).
   This closes only the source boundary. A real provider must still obtain
   those rows and live rails under one transition lock, publish generations,
   and remain the prerequisite for any CPU8/CPU9 admission.
   Clean documentation follow-up `d10796f` was rebuilt on Buildbox and
   reproduced the same content-addressed package, 119-DTB validation, and
   checksums; see the [Buildbox resume receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/ppm-policy-binding-buildbox-resume-20260810.txt).
   It changes documentation only and adds no new kernel or hardware evidence.
   Patch `0228` now binds calibrated rows, live state, and the final snapshot to
   one provider-owned `source_generation`. The builder publishes the epoch and
   the owner wrapper, source adapter, and assembler require exact equality; the
   independent clock and BigiDVFS backend counters remain distinct. Corrected
   clean revision `fb6697f` applies all 217 canonical entries on Buildbox,
   produces 119 DTBs, passes package checksums, and fetches only the validated
   package; see the [shared-generation Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/generation-coherence-buildbox-20260810.txt).
   This remains compile-only and default-off: the real EEM/PTP/PPM and
   PMIC/clock owner under one transition lock is still required, and device boot
   plus CPU8/CPU9 admission remain closed.
   Patch `0229` now requires an explicit PPM owner lock boundary. The owner
   copies the PPM snapshot and all four policy banks atomically, validates one
   shared table epoch, and preserves that exact policy copy into calibration;
   the outer transition lock remains the first lock. Clean revision `692a6a5`
   applies all 218 canonical entries on Buildbox, produces 119 DTBs, passes
   package checksums, and fetches only the validated package; see the
   [PPM owner-lock Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/ppm-owner-lock-buildbox-20260810.txt).
   This is still compile-only and default-off: a real EEM/PTP/PPM plus
   PMIC/clock provider must implement the owner, and device boot plus CPU8/CPU9
   admission remain closed.
   A source-only audit of the current managed vendor checkout now confirms why
   that provider cannot be assembled by reusing one existing vendor lock:
   PPM policy, CCI frequency rows, CSPM/PLL state, and EEM/PTP state have
   separate authorities, and no shared generation or single transition lock
   exists in the vendor structs. The exact revision, source hashes, and
   sanitized field summary are recorded in the [vendor PPM owner-boundary
   result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-ppm-owner-boundary-20260810.txt).
   The next implementation still requires a real mainline state provider;
   the resource-only lifecycle below supplies serialization and device
   lifetime, but not the missing state callbacks. Until that provider is
   backed by named runtime evidence, provider registration and CPU8/CPU9
   admission remain closed.
   Patch `0230` adds that resource-only lifecycle: explicit attach/detach
   retains the four backend device references, one transition mutex and a
   monotonic generation are exposed through an arbitration adapter, and the
   write path is permanently disabled. Clean revision `d506e28` applies all
   219 canonical entries on Buildbox, produces 119 DTBs, passes package
   checksums, and fetches only the validated package; see the
   [resource-owner Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/resource-owner-buildbox-20260810.txt).
   This is still compile-only and default-off: it has no DT match, consumer
   binding, hardware operation, owner registration, device boot, or CPU8/CPU9
   admission. The next implementation must connect the real PPM/CCI rows,
   EEM/PTP identity, live VPROC/VSRAM, and clock/rail callbacks to this
   lifecycle before any provider registration can succeed.
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
   publication check. The earlier 175-patch Buildbox package, fetched checksum
   validation, and independent 13-probe mutation oracle pass, with no hardware
   write; the current 179-entry package and later P32 source slices are
   recorded below. The current PSCI boot and disable vetoes remain intact.
   The [P32R integration review](../experiments/2026-08-06-a72-p32-r-review/README.md)
   initially confirmed that complete callback/architecture-effect prefix
   retention and
   the membership/provider/A30 ledger handoff are still open. Its
   [integration design](../experiments/2026-08-06-a72-p32-r-review/DESIGN.md)
   now fixes the bounded callback vector, effect mask, overflow/unknown
   fail-stop behavior, and owner-only ledger handoff; the accompanying
   15-probe model now also checks
   full trace identity, membership/provider snapshot handoff, A30 fault
   disposition, and rejection after premature side effects. It remains design
   evidence, not kernel or runtime validation. The first P32A source slice
   (`0187`) now records the bounded callback prefix, nested AP reset marker,
   outer reset, and reverse-range completion, with a source/format-patch audit
   recorded in the experiment. Buildbox was unavailable during that audit; the
   required Buildbox compile was subsequently completed for pushed commit
   `49e2d6f4c0e634c8beaedb99a0c29ead1ad0ff6f`, with the fetched package and
   checksum/provenance record in the
   [P32R Buildbox result](../experiments/2026-08-06-a72-p32-r-review/results/p32r-buildbox-validation-20260806.txt).
   The P32X source
   slice (`0188`) now records the arm64 disable order and separate
   DEAD/RCU/park, lockdep, and controller-kill boundaries; its source audit
   passes. Patch `0189` now adds the owner-only P32R ledger handoff: it captures
   the exact transaction and pre-fault membership/provider snapshots, preserves
   callback/effect completeness, marks a held provider `FAULT_UNKNOWN` without
   calling it, and retires only an accepted generation. Its source audit is
   recorded in the experiment. Patch `0190` now closes the source-level
   inventory/capacity and required/seen/missing/forbidden effect coverage
   gaps, and the owner handoff rejects incomplete coverage. A read-only
   Buildbox-source audit then found that P32 publication was gated on the
   declared-but-never-entered `VERIFYING` phase; patch `0191` now requires the
   live `ON_ISSUED` phase established by P17/P18 publication. The exact
   180-entry dedicated `a72-p32-rollback` profile passed Buildbox with
   `CONFIG_ARM64_MT6797_A72_P32_ROLLBACK=y` at pushed commit
   `f8b407420677dfdf2e641eebe02697ee6f65bb13`; its package and checksums are
   recorded in the linked result. This closes the P32 publication reachability
   and compile/package gates only; A39 early-secondary terminal attribution,
   A25/H13, provider, A40, A41, A26, and A14 remain open. No device action is
   authorized. The separate [A39 early-secondary inventory](../experiments/2026-08-06-a72-a39-early-secondary-inventory/README.md)
   now covers all controller status branches, `cpu_die_early()`, and the
   capability-failure callsites. It confirms that branch-specific terminal
   guards are still open; inventory completion does not close A39.
4. The current [A25 review](../experiments/2026-08-06-a72-a25-callback-review/README.md)
   and P32R mutation re-audit now cover the 180-entry series, pass H01–H15,
   mandatory dynamic ordering, conditional insertion classification, all five
   P32 closure rows, and P32 patches 0182–0191. H13 remains open because no
   same-boot numeric CPUHP-state capture exists yet. The fail-stop
   `.cpu_disable` plus die/kill guard design retains every partial callback and
   architecture effect, but it remains source-only and does not relax the
   current boot or disable vetoes.
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

The vendor-side writer lifecycle candidate is now source-backed and object-
compile validated on Buildbox: probe/remove ordering, PM/PPM/hotplug cleanup,
CPU/PM/clock/rail event forwarding, and deferred PCM-fault delivery are all
covered in the exact seven-patch experiment series. The cross-tree adapter that
connects this lifecycle hook to the mainline owner registration is still absent;
until it is bound and its failure/remove/event paths are independently validated,
the owner remains unregistered and CPU8/CPU9 admission stays closed.

Exit: observations and inference are separated, every required writer has one
owner, every pre-irreversible failure has a bounded no-effect or rollback
proof, and every post-irreversible uncertainty has an attributable terminal
recovery path.

### 5. Register a resource-only provider — complete

Register the provider with all consumers disconnected and writable operations
disabled or unreachable.

The resource-only provider lifecycle is now compile-validated on Buildbox at
clean revision `3b18307e42cb0ce6daefd26cec2790bed570a5b5` with the named
`dvfsp-resource-owner-readonly` profile. The profile applies 223 patches,
builds 119 DTBs, passes package checksums, and fetches only the validated
package; the receipt is in the
[DVFSP provider experiment](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/resource-owner-provider-buildbox-20260810.txt).
Patches 0232--0234 repair canonical ABI/source boundaries exposed by that
compile. This is still compile-only: the provider and DT node remain disabled,
the owner is unregistered, and no hardware or device action occurred.

The next ordered action is the real calibrated provider contract: efuse/PTP
identity, coherent PPM/CCI rows, live VPROC/VSRAM, clock/rail generation, and
one transition lock, followed by source-backed registration and runtime
validation. CPU8/CPU9 admission remains closed until those gates pass.

Patch 0235 now composes that source and generation-arbitration contract with
the resource owner's lifetime: detach is rejected while the calibrated source
is bound, and exit invalidates before unbinding. Its named Buildbox profile is
validated at clean revision `a28dd0f9d57b747258d2c70fbae7b14a9e3c010d` with
224 patches, 119 DTBs, and package checksums; see the
[calibrated-provider receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/calibrated-provider-buildbox-20260810.txt).
This is still a dormant callback binding, not a registered provider or
hardware-support result. The next ordered implementation is the actual
source-backed callback provider for efuse/PTP identity, PPM/CCI rows and
limits, live VPROC/VSRAM, and clock/rail generation under that lock.

Patch `0236` takes the first source-backed readback step without pretending to
be that provider: it passes the decoded CSPM sample into the live callback and
requires an exact backend sample-generation echo, while preserving the
independent provider transition generation. The clean `0044311` Buildbox run
applied 225 patches, produced 119 DTBs, passed checksums, and fetched the
validated package; see the [CSPM live-binding receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/cspm-live-binding-buildbox-20260810.txt).
Registration, hardware writes, runtime evidence, and CPU8/CPU9 admission
remain closed. The next ordered implementation is still the real callback
provider for efuse/PTP identity, all PPM/CCI rows and limits, live VPROC/VSRAM,
and a single transition-lock generation source.

Patch `0237` now adds the next narrowly bounded source layer: a read-only
NVMEM cell for the vendor efuse identity words, the documented PTP identity
decode, and pure CSPM VPROC/VSRAM code-to-microvolt converters. Buildbox
validated clean revision `85e96f7` with 226 patches, 119 DTBs, package
checksums, and the fetched package; see the [efuse/rail helper receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/efuse-rail-helper-buildbox-20260810.txt).
This does not read efuse MMIO, write a rail, build an OPP table, register the
provider, or admit CPU8/CPU9. The next ordered implementation remains the
source-backed PPM/CCI rows and limits, live rail callbacks, and one shared
transition generation/lock; only after those pass can provider registration,
runtime validation, and device boot be reconsidered.

Patch `0238` now binds that read-only identity cell to the dormant owner-source
seam. It decodes the silicon-selected PTP variant and requires explicit
provider callbacks for the u64 table epoch and calibration handle; neither
provenance value is fabricated, and the owner-source ABI is widened to match
the existing u64 PPM/generation contracts. Buildbox validated clean revision
`6ffe283` with 227 patches, 119 DTBs, package checksums, and the fetched
package; see the [identity-source bridge receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/identity-source-bridge-buildbox-20260810.txt).
The bridge is read-only and dormant: no owner/provider registration, MMIO or
rail/clock write, mutable table read, device boot, or CPU8/CPU9 admission was
added. The next ordered implementation is the source-backed PPM/CCI rows and
limits, live rail callbacks, and one shared transition generation/lock.

Patch `0239` now provides that PPM/CCI source boundary without claiming to be
the provider. Under the vendor `ppm_main_info.lock` callback it requires
explicit physical LL/L/B rows, the separate CCI frequency table, all four
policy-limit banks, and one nonzero shared table epoch; it maps the physical
rows into canonical EEM order and validates both snapshots. Buildbox validated
clean revision `51b3f30` with 228 patches, 119 DTBs, package checksums, and the
fetched package; see the [PPM/CCI source-adapter receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/ppm-cci-source-adapter-buildbox-20260810.txt).
This remains compile-only and dormant: no provider registration, MMIO or
rail/clock operation, device boot, or CPU8/CPU9 admission was added. The next
ordered implementation is the live VPROC/VSRAM and clock/rail callback layer
plus one shared transition generation under the existing outer lock.

Patch `0240` now supplies the dormant live-state callback adapter. It requires
one explicit generation, owner handle, transition handle, and provenance plus
per-cluster clock/rail samples; protected clock frequencies, the three physical
PPM rows, and raw CSPM VPROC/VSRAM codes are compared before pure conversion
and snapshot publication. Buildbox validated clean revision `84cfb27` with 229
patches, 119 DTBs, package checksums, and the fetched package; see the
[live-state source-adapter receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/live-state-source-adapter-buildbox-20260810.txt).
This remains compile-only and dormant: no provider registration, MMIO or
rail/clock operation, device boot, or CPU8/CPU9 admission was added. The next
ordered implementation is binding the adapter to the calibrated provider,
policy-derived CCI bounds, and runtime generation invalidation.

Patch `0241` now binds the read-only identity, live-state, and PPM/CCI source
adapters into the calibrated provider's existing callback seam, composing the
state-owner and PPM-owner operations without registering a provider or calling
hardware. Patch `0242` adds fail-closed policy-derived CCI validation: the live
CCI frequency must match the calibrated row and remain below the provider-owned
PPM ceiling. Patch `0243` adds a callback form of the generation-tagged runtime
ledger and routes validated lifecycle events through the provider invalidator,
without registering CPU-hotplug or PM notifier hooks. The preceding `eedafc7`
submission stopped during 0243 patch application; corrected revision
`da7cad7` applies all 232 canonical patches, builds the arm64 image and Gemini
DTB plus 119 total DTBs on Buildbox, passes package checksums, and fetches only
the validated package. See the [source/runtime gates Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/source-runtime-gates-buildbox-20260810.txt).
These are still compile-only, dormant contracts: no owner or provider is
registered, no hardware or firmware action occurred, and CPU8/CPU9 admission
remains closed. The next ordered gate is named-device runtime evidence for the
real lock, generation, identity, PPM/CCI, and live rail/clock callbacks; only
after that evidence can source-backed registration validation be reconsidered.

The first named-device runtime boundary probe on Gemian confirms the source
surfaces are readable (`/proc/eem`, the three PPM tables, cpufreq frequency,
voltage, and OPP endpoints, and the clock debug tree), but the bounded sysfs
search finds no authoritative generation, transition-lock, or owner endpoint.
Only the generic `mt-cpufreq` and `mt-ppm` platform nodes are visible. The
sanitized hashes and negative result are recorded in the [runtime owner
boundary v2 receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/runtime-owner-boundary-v2-20260810.txt).
This confirms availability of source data, not a coherent owner contract; the
next implementation must introduce one dedicated generation/lock owner before
registration validation or any device boot is considered.

A three-sample, one-second read-only hash repeat observed frequency, voltage,
and OPP changes while the PPM and EEM hashes stayed stable. This demonstrates
mutable live state but not an atomic snapshot. The [live hash repeat receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/runtime-owner-live-hash-repeat-20260810.txt)
therefore keeps the gate closed until one owner supplies a transition lock,
before/after generation, and live frequency/VPROC/VSRAM/PPM membership. No
provider or hardware path was enabled, and CPU8/CPU9 admission remains closed.

The pushed head was then rebuilt with the explicit `full` Buildbox profile:
all 232 canonical patches applied, the arm64 Image/Gemini DTB and 119 total
DTBs passed checksums, and only the validated package was fetched. The exact
[full-profile receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/source-runtime-gates-buildbox-full-20260810.txt)
records this compile-only rerun; it does not change the dormant owner/provider
boundary or reopen CPU8/CPU9 admission.

The exact current pushed head `ea0b43c` was then resumed on Buildbox with the
managed prepared source and cache. It again applied all 232 canonical patches,
produced the same content-addressed package, passed all package checksums, and
fetched only the validated package. See the [current-head resume receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/source-runtime-gates-buildbox-resume-current-head-20260810.txt).
This remains compile-only evidence: no owner or provider is registered, no
hardware or firmware action occurred, and CPU8/CPU9 admission remains closed.

A bounded content scan of the named Gemian surfaces found no attributable
generation, epoch, transition, owner, mutex, or atomic token. Generic clock
debug output was the only source of `lock` matches and does not establish a
DVFSP owner; the [token-content receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/runtime-owner-token-content-probe-20260810.txt)
retains only bounded labels and scan metadata. The procfs/debugfs discovery branch is now
closed; implementation must proceed through a real mainline callback/provider
owner, not a scraped endpoint.

Patch `0244` adds hardware-free KUnit coverage for the dedicated resource-owner
boundary: invalid initialization and absent-source refusal, single-owner lock
admission, monotonic generation under the lock, duplicate attach/bind refusal,
and detach refusal while a source is bound. The exact pushed revision `7bffe69`
was validated on Buildbox with the named `dvfsp-owner-kunit` profile: all 233
canonical patches applied, 119 DTBs and package checksums passed, and only the
validated package was fetched. The [KUnit Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/owner-kunit-buildbox-20260810.txt)
records the provenance. This is still compile-only contract evidence: the
fixture uses fake devices, no DT node is enabled, no provider is registered,
no hardware or firmware operation occurs, and CPU8/CPU9 admission remains
closed.

The next ordered implementation is a reviewed source-backed owner/provider
bridge that can bind real identity, PPM/CCI, live rail/clock, and generation
callbacks to this tested lifecycle boundary. Runtime registration, any
writable operation, device boot, and CPU8/CPU9 admission remain blocked until
that bridge has an attributable owner and separate runtime evidence.

Patch `0245` adds hardware-free KUnit coverage for the calibrated-provider
bridge. The exact pushed revision `cbb162a` was validated on Buildbox with the
`dvfsp-owner-kunit` profile: all 234 canonical patches applied, 119 DTBs and
package checksums passed, and only the validated package was fetched. The
[provider-bridge KUnit receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/provider-bridge-kunit-buildbox-20260810.txt)
records the provenance. The fixture rejects incomplete callback contracts,
binds complete identity/live/PPM/calibration tables to the resource owner,
constructs dormant owner callbacks, and verifies exit invalidation/unbind. It
invokes no callback and performs no Device Tree, MMIO, firmware, clock, rail,
provider-registration, device, or CPU operation. CPU8/CPU9 admission remains
closed.

The next ordered action is not another compile-only derivative: obtain and
review an attributable implementation for the real identity, PPM/CCI, live
rail/clock, and generation callbacks, then validate its read-only registration
boundary separately. Until that owner and runtime evidence exist, provider
registration, writable operation, device boot, and CPU8/CPU9 admission stay
blocked.

The public kernel repository's newer `main` ref `d388d350` was then rechecked
against the earlier `master`-ref audit. The exact MT6797 PPM, hybrid cpufreq,
EEM, and PPM-internal files still provide separate locks but no shared
generation or single transition owner; the [public-main owner-boundary receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-public-main-owner-boundary-20260810.txt)
records the source hashes and bounded token scan. This confirms the blocker is
not stale-source drift. The next ordered action remains an attributable
mainline owner implementation or new named runtime owner evidence, followed by
a separate read-only registration check.

The exact current pushed head `f7864e3` was subsequently resumed on Buildbox
with the named `dvfsp-owner-kunit` profile. All 234 canonical patches and 119
DTBs passed validation, and only the checksummed package was fetched; see the
[current-head Buildbox resume receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-f7864e3-20260810.txt).
This does not alter the owner boundary: registration, writable operation,
device boot, and CPU8/CPU9 admission remain closed.

A fresh read-only symbol census on the named Gemini found 75 concrete vendor
cpufreq/PPM/EEM/iDVFS symbols, including table/voltage callback registration
entrypoints, but no shared transition lock, generation/epoch, or owner token.
The three lock-name matches are only clock-switch/no-lock helpers. The bounded
result is recorded in the [runtime owner symbol census](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/runtime-owner-symbol-census-20260810.txt).
This is the first runtime identity evidence for the callback surface, not a
coherent-owner proof; the next ordered implementation is an explicit bridge
around those sources with a separately supplied generation/lock owner.

The exact pushed head `a81b5e4` was then resumed on Buildbox with the
`dvfsp-owner-kunit` profile. All 234 canonical patches and 119 DTBs passed
validation, package checksums passed, and only the validated package was
fetched; see the [current-head Buildbox resume receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-a81b5e4-20260810.txt).
This compile-only rerun changes no owner boundary: no registration, writable
operation, device boot, or CPU8/CPU9 admission occurred.

The named Gemini's read-only PPM tables now match the public SB/0119 arrays
exactly, including the date-specific Big-cluster table; the [table-family
receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/runtime-ppm-table-family-20260810.txt)
records the active policy rows and the missing CCI/owner-generation surface.
Patch `0246` captures only that proven frequency identity in a fail-closed
source reader with hardware-free KUnit coverage. It deliberately does not
claim the mutable PPM policy, vendor lock, calibration handle, or transition
generation. The next ordered implementation remains a separately supplied
owner for those fields; no provider registration, device boot, write, or
CPU8/CPU9 admission is authorized by this table fixture.

The exact pushed head `f9e8c58` then passed the full 235-patch
`dvfsp-owner-kunit` Buildbox build, including Patch 0246. The arm64 Image,
Gemini DTB, all 119 DTBs, package checksums, provenance, and
validated-package-only fetch passed; see the [Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-f9e8c58-20260810.txt).
This confirms source/build reproducibility only. The next ordered gate is still
the separately attributable runtime owner for mutable policy, calibration,
transition lock, and generation; no device boot/write or CPU8/CPU9 admission
occurred.

Patch `0247` now binds the proven SB/0119 table epoch to the existing identity
source callback without inventing a calibration handle. The exact pushed head
`979991b` passed the full 236-patch `dvfsp-owner-kunit` Buildbox build, all 119
DTBs, package/provenance checksums, and validated-package-only fetch; see the
[Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-979991b-20260810.txt).
The next gate remains an attributable calibration, mutable-policy, PPM-lock,
and transition-generation owner; no registration, device boot/write, or
CPU8/CPU9 admission occurred.

The exact pushed head `96607a3` was rebuilt on Buildbox with the
`dvfsp-owner-kunit` profile after the current-head receipt was recorded; all
234 canonical patches, 119 DTBs, package checksums, and the validated-package
fetch passed. See the [resume receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-96607a3-20260810.txt).

A source-only callback audit against the pinned public Gemian `main` revision
`d388d350` found that the apparent vendor registration entrypoints are
single-slot replacements, not composable observer hooks. The PTP table setter
would replace the existing EEM private-table callback, and the PPM DVFS client
setter would replace the cpufreq policy-limit callback. A separate owner cannot
call either setter without disabling an existing policy path. The bounded
[callback replacement audit](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-callback-replacement-audit-20260810.txt)
therefore closes the unsafe observer-bridge route. The next implementation must
be integrated at the vendor-aware driver boundary or introduce an explicit
mainline owner contract with cooperation from those writers; no provider,
hardware action, device boot, or CPU8/CPU9 admission is justified by this audit.

The exact pushed head `75986f0` was then resumed on Buildbox with the named
`dvfsp-owner-kunit` profile. All 236 canonical patches, 119 DTBs, package
checksums, and the validated-package-only fetch passed; see the [current-head
Buildbox resume receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-75986f0-20260810.txt).
This confirms compile-only reproducibility for the callback-boundary audit;
the vendor-aware owner/provider gate remains open, and no device action or
CPU8/CPU9 admission occurred.

Patch `0248` corrected a dormant provider wiring bug: the calibrated provider
now passes its embedded PPM source as the callback context, matching the PPM
source ABI, with a hardware-free KUnit identity assertion. The exact pushed
head `72be3a2` was resumed on Buildbox with the named `dvfsp-owner-kunit`
profile. All 237 canonical patches, 119 DTBs, package/provenance checksums,
and the validated-package-only fetch passed; see the [Buildbox resume
receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-72be3a2-20260810.txt).
This repairs the compile-only provider contract but does not supply a real
vendor owner, register a provider, or authorize device action; CPU8/CPU9
admission remains closed.

Patch `0249` adds a dormant cooperative vendor-owner adapter. It validates one
ABI-stable callback table for identity, PPM/CCI policy, live state, and
calibrated-provider invalidation, binds those sources to the existing resource
owner, and deliberately avoids the vendor's single-slot registration setters.
The exact pushed head `fc425cf` passed the full 238-patch `dvfsp-owner-kunit`
Buildbox build, all 119 DTB checks, package/provenance checksums, and the
validated-package-only fetch; see the [Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-fc425cf-20260810.txt).
This is compile-only contract evidence, not hardware support: no vendor owner
or provider was registered, no device or firmware action occurred, and CPU8/
CPU9 admission remains closed. The next ordered implementation is the real
vendor-aware writer integration that supplies these callbacks and one shared
transition generation/lock, followed by a separate read-only runtime
registration check.

Patch `0250` adds that shared writer-side boundary as a dormant, ABI-stable
contract. It requires an explicit provenance callback, serializes future PTP,
PPM, and voltage writer updates with one supplied transition mutex, and advances
a checked generation only after commit; abort leaves the generation unchanged.
It does not call the vendor's single-slot setters, perform MMIO, or register an
owner/provider. The exact pushed head `0708096` passed the full 239-patch
`dvfsp-owner-kunit` Buildbox build, all 119 DTB checks, package/provenance
checksums, and the validated-package-only fetch; see the [Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-0708096-20260810.txt).
This remains compile-only and does not advance hardware support or CPU8/CPU9
admission. The next ordered implementation is an attributable integration at
the actual vendor-aware writer sites, followed by a separate read-only runtime
registration check proving that those writers supply the callback table and
share the transition generation.

A bounded source-only audit at the pinned public Gemian revision records the
actual PTP-table, voltage, and PPM writer call sites and confirms that the
legacy setters are single callback slots with no shared transition-generation
field or existing transition owner; see the [writer call-site audit](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-writer-callsite-audit-20260810.txt).
Patch `0251` binds the dormant writer contract to the resource owner's mutex
and generation, composes it into the cooperative owner adapter, and refuses
unbind while a writer transaction is held. This remains source/contract work:
there is no vendor payload, setter call, provider/runtime registration, device
action, or CPU8/CPU9 admission. The next ordered action is Buildbox validation
of the exact committed series; only then can attributable vendor-aware writer
integration and separate read-only runtime registration evidence proceed.

The exact pushed head `af5a289` completed the named `dvfsp-owner-kunit` Buildbox
job: all 240 canonical patches applied, the arm64 kernel linked, all 119 DTBs
and package/provenance checksums passed, and the validated package was fetched;
see the [Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-af5a289-20260810.txt).
This advances compile and provenance confidence only. No vendor owner/provider
or runtime registration occurred, no device was booted or written, and CPU8/
CPU9 admission remains closed. The next ordered action is attributable
integration at the actual vendor writer sites, followed by separate read-only
runtime registration evidence.

A corrected lock-context audit shows that the pinned public revision's active
`cpufreq_lock` branch is a mutex; its `spin_lock_irqsave` alternative is under
`#if 0`. PPM dispatch also holds its mutex before entering the cpufreq callback
path; see the [lock-context audit](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-writer-lock-context-audit-20260810.txt).
The shared owner must therefore be acquired before the cpufreq critical
section, with every vendor callback chained under one transaction and an abort
on every failure. The atomic/IRQ-disabled refusal remains necessary for callers
that are already non-sleepable and for a variant that enables the spinlock
branch. This sharpens the integration boundary but is not runtime evidence: no
vendor source was copied, no setter or provider was called, no device action
occurred, and CPU8/CPU9 admission remains closed. The next ordered action is an
attributable vendor-boundary implementation at that pre-cpufreq-lock point,
followed by separate read-only runtime registration evidence.

Patch `0252` makes this safety boundary fail closed in code: writer acquisition
returns `-EWOULDBLOCK` when interrupts are disabled or execution is atomic, and
KUnit covers the IRQ-disabled refusal. This prevents a future call-site adapter
from sleeping on the shared mutex after entering a non-sleepable vendor
critical section, including the disabled spinlock variant.
It remains dormant contract work; no vendor callback slot, provider, device,
or CPU8/CPU9 path is enabled. The next ordered action remains the attributable
vendor-boundary implementation at the pre-cpufreq-lock point, followed by separate
read-only runtime registration evidence.

The exact pushed head `69f1638` then completed the named `dvfsp-owner-kunit`
Buildbox job. All 241 canonical patches applied, the arm64 kernel linked, all
119 DTBs and package/provenance checksums passed, and the validated package was
fetched into the ignored Buildbox artifact tree; see the [Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-69f1638-20260810.txt).
This validates the fail-closed atomic/IRQ-disabled boundary and its KUnit test,
but remains compile-only evidence: no vendor owner/provider or runtime
registration occurred, no device was booted or written, and CPU8/CPU9
admission remains closed. The next ordered action remains attributable
integration at the vendor-aware writer boundary before the cpufreq critical
section, followed by separate read-only runtime registration evidence.

Patch `0253` closes the terminal-generation edge case before any vendor callback
can run: a writer transaction now refuses `~0ULL` with `-EOVERFLOW`, leaving the
generation and held state unchanged. Patch `0254` adds the reusable pre-lock
writer boundary, which acquires the shared owner, passes its captured generation
through the existing vendor callback chain, and commits or aborts as one
transaction. The exact pushed head `0d990f7` completed the named
`dvfsp-owner-kunit` Buildbox job: all 243 canonical patches applied, the arm64
kernel linked, all 119 DTBs and package/provenance checksums passed, and only the
validated package was fetched; see the [Buildbox resume receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-0d990f7-20260810.txt).
This is compile-only boundary evidence: no vendor source was copied, no actual
vendor setter or provider/runtime registration was called, no device was booted
or written, and CPU8/CPU9 admission remains closed. The next ordered action is
binding the pre-lock wrapper at attributable vendor writer sites, followed by
separate read-only runtime registration evidence.

Patch `0255` gives the pre-lock wrapper explicit descriptors for the PTP-table,
voltage-observer, and PPM callback boundaries. Invalid site identities and missing
callbacks are rejected before the shared owner is acquired; valid descriptors
all use the same generation transaction. The exact pushed head `87923a0`
completed the named `dvfsp-owner-kunit` Buildbox job: all 244 canonical patches
applied, the arm64 kernel linked, all 119 DTBs and package/provenance checksums
passed, and only the validated package was fetched; see the [Buildbox resume
receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-87923a0-20260810.txt).
This remains a source-independent compile contract: the pinned vendor sources
are not copied, no external vendor caller is wired, no setter or
provider/runtime registration was called, no device was booted or written, and
CPU8/CPU9 admission remains closed. The next ordered action is binding these
descriptors at the external vendor callers, followed by separate read-only
runtime registration evidence.

The follow-up source-only design separates the mutable PTP/voltage-table
writers from `g_pCpuVoltSampler`, which is an observer callback invoked from
multiple transition paths. It records the exact outer-function and lock-order
requirements for PTP, voltage, and PPM without copying vendor code; see the
[site integration design](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-writer-site-integration-design-20260810.txt).
The corrected [call-site audit](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-writer-callsite-audit-20260810.txt)
and [lock-context audit](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-writer-lock-context-audit-20260810.txt)
keep actual external caller binding and runtime registration as open gates.

A fresh symbol-name-only census of the currently deployed Gemian kernel confirms
the expected PTP and voltage callback setters, both exported voltage-table
writers, the PPM setter, and `ppm_limit_callback`; it still exposes no shared
owner, generation, or transition lock. The [runtime symbol census](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/runtime-vendor-writer-symbol-census-20260810.txt)
is identity evidence only: raw addresses and payloads were not retained, and
no device state changed. The next ordered gate remains an external
vendor-aware caller implementation using the named descriptors, followed by
separate read-only owner registration evidence.

The exact current head `6a01dc5` was then resumed on Buildbox with the same
`dvfsp-owner-kunit` profile. All 244 canonical patches applied, the arm64
kernel linked, all 119 DTBs and package/provenance checksums passed, and only
the validated package was fetched; see the [current-head Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-6a01dc5-20260810.txt).
This commit records runtime symbol identity only, so the result adds no new
hardware claim: vendor callers remain unbound, runtime owner registration is
absent, no device was booted or written, and CPU8/CPU9 admission remains
closed.

The bounded Buildbox source search found no existing vendor-aware implementation
of `mt6797_dvfsp_vendor_writer_run_site` and no prepared caller-integration
checkout or branch. The pinned vendor revision is present in Buildbox's managed
Git mirror, so the source is available for a reviewable clean-room integration;
it has not been copied into this repository or wired into the mainline caller
sites. The [integration handoff](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-writer-integration-handoff-20260810.txt)
records the exact external source/cooperation input and acceptance checks still
required. This is an explicit integration gap, not runtime or hardware
evidence: no setter/provider was called, no device action occurred, and CPU8/
CPU9 admission remains closed.

The exact current head `10439af` was resumed on Buildbox with the same
`dvfsp-owner-kunit` profile. All 244 canonical patches applied, the arm64
kernel linked, all 119 DTBs and package/provenance checksums passed, and only
the validated package was fetched; see the [current-head Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-10439af-20260810.txt).
This compile-only rebuild does not change the integration gate or authorize a
device boot/write; vendor callers remain unbound and CPU8/CPU9 admission stays
closed.

The exact current head `c53084b` was resumed on Buildbox with the same
`dvfsp-owner-kunit` profile. All 244 canonical patches applied, the arm64
kernel linked, all 119 DTBs and package/provenance checksums passed, and only
the validated package was fetched; see the [current-head Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-c53084b-20260810.txt).
This compile-only rebuild records the current artifact identity but does not
change the integration gate or authorize a device boot/write: vendor callers
remain unbound and CPU8/CPU9 admission stays closed.

The exact pushed current head `b2425cd` was resumed on Buildbox with the
manifest's `full` profile. All 244 canonical patches applied, the arm64 kernel
linked, all 119 DTBs and package/provenance checksums passed, and only the
validated package was fetched; see the [current-head Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-b2425cd-20260810.txt).
This compile-only rebuild confirms the current mainline artifact but does not
promote the experiment-only vendor candidate, register a runtime owner, or
authorize a device boot/write; CPU8/CPU9 admission remains closed.

The clean-room candidate at [0001-mt6797-vendor-writer-boundary.patch](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/patches/0001-mt6797-vendor-writer-boundary.patch)
now binds the four pinned PTP/voltage-table writers and the PPM policy callback
to one fail-closed, externally registered transaction bridge. Each hook begins
before the vendor `cpufreq_lock` and finishes after it; atomic/IRQ-disabled
entry is refused, and the voltage observer's sleepable outer transition is not
wrapped recursively. The exact project commit `b671930` was applied to the
pinned vendor revision on Buildbox through Git; `git apply --check`, the
vendor defconfig, the bridge object, and the affected `mt_cpufreq.o` all passed;
the [vendor-boundary Buildbox review](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-writer-boundary-buildbox-20260810.txt)
records the exact inputs and static checks. This remains compile-only
integration evidence: the bridge has no registered owner/provider, no vendor
setter was called, no device action occurred, and CPU8/CPU9 admission remains
closed. The next ordered gate is mapping the sleepable outer voltage-observer
transition, followed by separate read-only owner-registration evidence.

The [voltage-observer outer audit](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-voltage-observer-outer-audit-20260810.txt)
now maps all three observer call paths. Normal policy transitions have a
sleepable `_mt_cpufreq_set(lock=1)` boundary, but PPM already owns the bridge,
CPU-hotplug paths already hold `cpufreq_lock`, and the hardware-governor
callback takes that mutex before notifying. The public direct voltage/frequency
helpers also need their own outer mapping. The observer itself therefore
remains intentionally unwrapped; the next candidate must bind those outer
contexts independently and preserve the existing PPM/lock ordering.

Candidate [0002-mt6797-voltage-observer-outer-boundary.patch](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/patches/0002-mt6797-voltage-observer-outer-boundary.patch)
now binds the sleepable normal policy path and the two public direct
voltage/frequency helpers to the voltage descriptor. The PPM path remains bound
by 0001, while CPU-hotplug and hardware-governor callers remain unbound because
they already hold `cpufreq_lock`; the observer callback still performs no
recursive bridge acquire. Both patches applied to the exact pinned vendor
revision on Buildbox, and the vendor defconfig, bridge object, and affected
`mt_cpufreq.o` all passed; see the [outer-boundary Buildbox review](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-voltage-observer-boundary-buildbox-20260810.txt).
This is still compile-only integration evidence: no owner/provider was
registered, no setter was called, no device action occurred, and CPU8/CPU9
admission remains closed. The next ordered gate is the remaining lock-held
contexts, then separate read-only owner-registration evidence.

The [lock-held context audit](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-lock-held-context-audit-20260810.txt)
then confirmed that the active vendor `cpufreq_lock` is mutex-based, the CPU
notifier uses that mutex in its active lock regions, and the hardware-governor
observer is dispatched from the dedicated `dvfs_nfy` kthread. Candidate
[0003-mt6797-lock-held-observer-contexts.patch](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/patches/0003-mt6797-lock-held-observer-contexts.patch)
therefore acquires the owner before those contexts' existing locks and still
does not acquire it from the observer callback. All three patches applied and
compiled on Buildbox; see the [lock-held Buildbox review](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-lock-held-context-buildbox-20260810.txt).
This remains compile-only evidence with no owner/provider registration, setter
call, device action, or CPU8/CPU9 admission. The next ordered gate is separate
read-only owner-registration evidence.

The exact pushed current head `d6a9ff4` was then resumed on Buildbox with the
manifest's `full` profile. All 244 canonical patches applied, the arm64 kernel
linked, all 119 DTBs and package/provenance checksums passed, and only the
validated package was fetched; see the [current-head Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-d6a9ff4-20260810.txt).
This is a compile-only rebuild of the mainline manifest: the three vendor
boundary patches remain experiment-only and are not in the package, no
owner/provider or vendor setter was registered or called, no device action
occurred, and CPU8/CPU9 admission remains closed. The next ordered gate is
separate read-only runtime owner-registration evidence, followed by a
source-backed provider only if its callbacks can be tied to real calibrated
EEM/PTP/PPM state under the shared transition lock.

The pushed current head `9ab1ca4` was resumed on Buildbox after the
runtime-boundary evidence commit. The same full manifest profile again passed
all 244 canonical patches, the arm64 link, 119 DTBs, package/provenance
checksums, and validated-package-only fetch; see the [current-head Buildbox
receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-9ab1ca4-20260810.txt).
This remains compile-only evidence, with no device action or CPU8/CPU9
admission. The ordered next step remains the source-backed read-only adapter,
then a separate runtime owner-registration review.

A fresh read-only probe on the named Gemian device still reports the ordinary
`3.18.41+` kernel with CPUs `0-1` online and `0-9` possible. Its bounded
platform/procfs scan finds generic `mt-cpufreq`, `mt-ppm`, and `mt-scpdvfs`
surfaces but no attributable owner, generation, or transition-lock endpoint;
see the [runtime owner boundary v3 result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/runtime-owner-boundary-v3-20260810.txt).
The pinned vendor-source audit then maps the static PPM policy/table state,
cpufreq/CSPM live state, and EEM/PTP state to their separate internal locks and
records the exact file identities; see the [source-backed owner audit](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-source-owner-audit-20260810.txt).
This closes the endpoint-search branch. The next implementation is an
in-file, read-only adapter for those real static states, followed by a
separate owner/provider registration candidate only after one shared
generation lock and all invalidation paths are proven. No device boot/write or
CPU8/CPU9 admission is authorized.

The exact pushed vendor-state adapter candidate `3200450` was then applied to
the pinned vendor revision `d388d350` on Buildbox through a temporary Git
checkout. All four experiment patches applied cleanly, the vendor
`gemini_modular_defconfig` passed, and the writer bridge, cpufreq, hybrid CSPM,
EEM, and PPM objects all compiled with the required vendor include roots; see
the [vendor-state adapter Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-state-adapters-buildbox-20260810.txt).
The clean rerun completed with wrapper exit status zero after those five
objects and checksum reporting, so this is recorded as compile evidence, not
as a package or hardware result. The adapters remain
read-only, unregistered, and source-backed; no setter/provider/device action
occurred, and CPU8/CPU9 admission remains closed. The next ordered step is a
separate read-only runtime owner-registration review only after a shared
generation and every invalidation path are proven.

The corrected current head `a463951` was then resumed on Buildbox with the
full manifest profile. The arm64 cross-build passed configuration, the kernel
artifact, all 119 DTBs, provenance and checksum validation, and only the
validated package was fetched; see the [current-head Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-a463951-20260810.txt).
This remains compile-only evidence: no provider or owner was registered, no
vendor setter or device action occurred, and CPU8/CPU9 admission remains
closed. The next ordered gate is still a separate read-only runtime
owner-registration review after the shared generation and every invalidation
path are proven.

The exact vendor-boundary candidate `ee98766` was then applied to the pinned
vendor revision `d388d350` on Buildbox. All five experiment patches applied
cleanly, the vendor `gemini_modular_defconfig` passed, and the writer bridge,
cpufreq, hybrid CSPM, EEM, and PPM objects all compiled; see the [shared-owner
identity Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-writer-shared-owner-identity-buildbox-20260810.txt).
The new bridge requires explicit nonzero owner and transition handles before a
vendor transaction begins, but remains unregistered and performs no setter,
provider, or device action. This closes the identity-contract gap without
claiming runtime ownership. The next ordered action is the actual reviewable
owner callback binding, followed by separate read-only runtime owner evidence;
CPU8/CPU9 admission remains closed.

The follow-on candidate `0006` plus mainline patch `0256` now provide that
reviewable cross-tree binding contract. Mainline exports one ABI-1 table for
`begin`, `commit`, `abort`, and `read_identity` around the already shared
resource-owner mutex/generation; it validates the site and generation on every
finish. The vendor side accepts that exact table through an explicit
`register_mainline_owner()` action, pins the expected owner and transition
handles, translates the private site enum, and rejects identity mismatches.
Neither side registers by default, calls a vendor setter, performs MMIO, or
opens provider/runtime/CPU8/CPU9 admission. The pushed candidate
`6b882064` then passed the full Buildbox profile (245 canonical patches, 119
DTBs, package checksums, and validated-package-only fetch); see the [mainline
resume receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-6b882064-20260811.txt).
The exact pinned vendor revision also accepted all six experiment patches and
compiled the writer, cpufreq, hybrid CSPM, EEM, and PPM objects with the
established include roots; see the [vendor binding Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-writer-mainline-owner-binding-buildbox-20260811.txt).
This is compile-only evidence: runtime owner registration remains unproven and
CPU8/CPU9 admission stays closed. The next gate is a separate read-only
runtime owner-registration review, with no device boot or write.

That read-only review is now complete on the named Gemian device. The runtime
still exposes only generic cpufreq/PPM/EEM/SCPDVFS surfaces; the consistency
sample reports CPUs 0-1 online and 0-9 possible/present, but no attributable
owner, generation, epoch, transition lock, mutex, or owner token. See the
[runtime owner-registration review](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/runtime-owner-registration-review-20260810.txt).
The mainline bridge therefore remains dormant and no provider registration,
device write, boot, or CPU8/CPU9 admission is authorized. The next step is
source-only integration review for a real shared owner and complete
invalidation coverage.

The source-only integration review is now recorded against the exact pinned
vendor revision after all six experiment patches. It anchors the four PTP
outer functions before the active cpufreq mutex, the non-recursive voltage
observer boundary, and the PPM order `ppm_mutex -> owner -> cpufreq_mutex`;
it also confirms that the legacy single-slot setters remain untouched. The
mainline 0207/0208/0243 invalidation path is only a contract: notifier
registration and vendor-aware source callbacks are still absent, so caller
binding and complete invalidation coverage remain open. See the [integration
review](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-writer-mainline-owner-integration-review-20260810.txt).
The next ordered step is a separate reviewable vendor-aware caller candidate
covering PTP, voltage outer, PPM, CPU-hotplug, and hardware-governor contexts,
with fail-closed abort/rollback semantics, followed by exact Buildbox
validation. No device boot/write or CPU8/CPU9 admission is authorized.

Patch `0257` now supplies the missing mainline-side registration handoff: an
external vendor-aware caller may explicitly register and unregister the exact
ABI-1 bridge table, while the adapter pins bridge context and owner identities
and blocks teardown until unregister succeeds. The repaired exact pushed
commit `c5e0bdd` passed the full Buildbox profile: all 246 canonical patches,
119 DTBs, package/provenance checksums, and validated-package-only fetch. This
is compile-only evidence; registration remains default-off, no vendor setter,
provider, MMIO, firmware, or device action occurred, and CPU8/CPU9 admission
remains closed. The next ordered gate is a reviewable vendor-aware caller
covering the named PTP, voltage-observer, PPM, CPU-hotplug, and
hardware-governor contexts plus complete runtime invalidation coverage, then a
separate read-only runtime review. See the [registration handoff Buildbox
result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-writer-registration-handoff-buildbox-20260810.txt).

The post-series caller/lifecycle audit now provides the attributable source
check for that gate. All named writer contexts have fail-closed begin/finish
wrappers, but the vendor probe/remove paths never invoke the owner registration
handoff, PM registration has no matching removal, and the CPU-hotplug, PM,
clock, rail, and fault paths do not forward 0207 invalidation events through a
shared generation. Since an unregistered writer returns `-ENODEV`, the
six-patch vendor series is not a boot candidate. See the [caller lifecycle and
invalidation audit](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-caller-lifecycle-invalidation-audit-20260811.txt).
The next ordered step is to prepare a separate vendor-aware lifecycle
candidate that registers before any wrapped path is reachable, unwinds every
failure/remove path, and forwards all lifecycle invalidations through the
mainline owner contract; then validate that exact candidate on Buildbox. No
device boot/write or CPU8/CPU9 admission is authorized.

Patch `0258` now extends the explicit writer handoff with a source-independent
ABI-1 runtime-event table covering CPU online/down, suspend/resume, clock, rail,
and PCM-fault classes. Registration fails closed unless the event table and
callback are valid, and the exact table/context remain pinned through
unregister; the KUnit contract checks ABI and pointer/context identity without
hardware access. The exact pushed commit `8387f7f` passed the full Buildbox
profile with all 247 canonical patches, 119 DTBs, package/provenance
checksums, and validated-package-only fetch; see the [runtime-event Buildbox
receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-writer-runtime-event-handoff-buildbox-20260811.txt).
This is compile-only evidence: the real vendor probe/remove caller is still
not bound to the owner handoff and does not forward lifecycle events, so no
runtime owner, device boot/write, or CPU8/CPU9 admission is claimed. The next
ordered gate is the actual vendor-aware caller lifecycle integration with
complete failure/remove unwinding and event forwarding, followed by separate
read-only runtime evidence.

Patch `0259` and experiment patch `0008` now bind that boundary through one
source-independent ABI-1 integration adapter. The mainline side requires exact
bridge, runtime-event, lifecycle, context, owner-handle, and transition-handle
identity; the vendor side forwards probe registration and remove unregistration
and refuses teardown while the owner is still registered. The KUnit contract
exercises bind, lifecycle registration, owner registration, reverse teardown,
and unbind without touching hardware. The exact pushed commit `3f7446c` passed
the full Buildbox profile with 248 canonical patches and 119 DTBs, and the
pinned vendor revision passed the sequential eight-patch affected-object
compile; see the [lifecycle-integration Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-writer-lifecycle-integration-buildbox-20260811.txt).
This closes the compile-only cross-tree integration boundary only: the external
adapter remains default-off and unregistered, no provider/setter/runtime owner
or device action is claimed, and CPU8/CPU9 admission stays closed. The next
ordered step is source-backed read-only owner and invalidation evidence from a
real external adapter; no device boot or write is authorized by this result.

Patches `0260` and `0261` now provide the fixed-layout, source-independent
snapshot ABI and bind it to the mainline owner. The ABI covers bounded PPM,
cpufreq, CSPM, and EEM records, exact owner/transition handles, an explicit
invalidation hook, and a separate identity callback that fails closed unless a
real PTP/efuse source supplies variant, table-epoch, and calibration identity.
The owner invalidates before forwarding runtime events and admits an explicit
`OBSERVE` transaction whose release cannot advance the shared generation.
The exact pushed commit `2c2035b` passed the full Buildbox profile with all 250
canonical patches, 119 DTBs, package/provenance checksums, and
validated-package-only fetch. The pinned vendor revision accepted all nine
experiment patches and the writer, cpufreq, hybrid CSPM, EEM, and PPM objects
compiled; see the [source-observation owner Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-source-observation-owner-buildbox-20260810.txt).
This remains compile-only evidence: the external adapter and provider are
default-off, identity remains unsupported, no setter or device action occurred,
and CPU8/CPU9 admission remains closed. The next ordered step is a separate
source-snapshot contract review plus isolated read-only runtime registration
test. The dedicated `dvfsp-owner-kunit` profile then compiled the source
registration fixture and required writer bridge with all 250 canonical patches,
119 DTBs, and passing package/provenance checksums; see the [owner-KUnit
Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-source-observation-runtime-registration-kunit-buildbox-20260810.txt).
The fixture covers source init/exit, invalidation-before-forwarding, exact
callback/context identity, and teardown refusal while registered, but Buildbox
does not execute KUnit. No real external registration, provider, setter, device
action, or CPU8/CPU9 admission is claimed. The next ordered step is source
snapshot semantic review and, only if an isolated runner exists, runtime test;
do not boot or write.

Patch `0262` now aligns the source validator with the mainline CSPM decoder:
physical limit index zero is valid, physical limits are bounded by the 16-entry
OPP range, and the CCI record remains explicitly limit-less. The exact 251-patch
`dvfsp-owner-kunit` Buildbox profile applied and linked all 119 DTBs with
passing package/provenance checksums; see the [CSPM semantic-bound Buildbox
result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-source-observation-cspm-bounds-buildbox-20260810.txt).
This is still compile-only evidence: KUnit was not executed, no external
provider or setter was called, no device action occurred, and CPU8/CPU9
admission remains closed. The next ordered step is to complete the
source-to-provider field/identity mapping review and locate or add an isolated
runtime KUnit runner; do not boot or write a device.

Patch `0263` closes the fail-open direct-registration path exposed by the first
isolated run: writer registration now returns `-ENODEV` until lifecycle
integration is bound, so a callback that can only reject runtime events is not
published. The exact 252-patch `dvfsp-owner-kunit` profile passed on Buildbox
with 119 DTBs, package/provenance checksums, and validated-package-only fetch;
see the [lifecycle-guard Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-source-lifecycle-guard-kunit-buildbox-20260810.txt).
The fetched Image then passed all five existing KUnit suites in isolated QEMU
(14/14, no failures or skips), without device or provider action; see the
[isolated lifecycle-guard result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-source-lifecycle-guard-kunit-qemu-20260810.txt).

Patch `0264` now completes the source-to-provider field and identity review
bridge while remaining registration-default-off. PPM and cpufreq records are
reordered by declared ID; CSPM remains the fixed LL/L/B/CCI raw-code view; all
six EEM detectors are retained with canonical provider banks 0/3/4/5; and the
variant, table epoch, calibration handle, generation, and owner/transition
handles are copied without truncation. Policy rows, EEM voltage units, live
clock ownership, rail conversion, and provider registration are explicitly
unavailable rather than inferred. The exact 253-patch `dvfsp-owner-kunit`
profile passed on Buildbox at commit `8dc7cf7`, with 119 DTBs and passing
package/provenance checksums; see the [field-bridge Buildbox result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-source-provider-field-bridge-buildbox-20260810.txt).
The fetched Image passed all six isolated QEMU KUnit suites (17/17, no
failures or skips), including bridge mapping, rejection, invalidation, and
teardown; see the [field-bridge QEMU result](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-source-provider-field-bridge-qemu-20260810.txt).
No provider registration, vendor setter, device action, or CPU8/CPU9 admission
is claimed. The next ordered step is to complete source-backed policy-row, EEM
voltage-unit, live clock-owner, and rail-conversion mappings under one shared
generation before any provider registration or device boot.

The Buildbox run was resumed at the exact pushed commit `1421893`. The
`dvfsp-owner-kunit` profile reproduced the validated 253-patch package with
all 119 DTBs and passing provenance checksums; see the [resume Buildbox
receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-source-provider-field-bridge-resume-buildbox-20260810.txt).
The fetched Image was rerun in isolated AArch64 QEMU and all six KUnit suites
passed (17/17, no failures or skips), with the guest reaching `System halted`;
see the [resume QEMU receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-source-provider-field-bridge-resume-qemu-20260810.txt).
This is deterministic revalidation only: policy rows, EEM voltage units, live
clock ownership, rail conversion, provider registration, and Gemini hardware
support remain closed.

Patch `0265` now maps the pinned vendor EEM detector's documented 10uV unit
and per-detector PMIC base/step metadata into a checked microvolt view while
retaining the raw tables. The exact 254-patch `dvfsp-owner-kunit` Buildbox
profile passed at commit `20fd59f` with 119 DTBs and validated package and
provenance checksums; the pinned vendor revision accepted experiment patches
0001–0010 and all five affected objects compiled with GCC 6.3. The fetched
Image passed all six isolated QEMU KUnit suites (18/18, no failures or skips)
and reached `System halted`; see the [EEM-unit mainline Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-source-eem-unit-buildbox-20260811.txt),
[vendor compile receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-source-eem-unit-vendor-buildbox-20260811.txt),
and [isolated QEMU receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-source-eem-unit-qemu-20260811.txt).
This remains compile/virtual evidence only: policy rows, live clock ownership,
rail conversion, provider registration, Gemini hardware support, and CPU8/CPU9
admission remain closed. The next ordered gate is source-backed policy-row,
live clock-owner, and rail-conversion evidence under one generation before any
provider registration or device boot.

Patch `0266` and experiment patch `0011` now complete the source-backed
policy/clock/rail mapping gate: four policy states across three clusters,
CPU-DVFS clock-mux ownership, and the documented VPROC/VSRAM conversion
metadata are validated without setters or hardware writes. The corrected
`dvfsp-owner-kunit` Buildbox package at commit `c7ce05d` passed 255 patches,
119 DTBs, and package/provenance checksums. Its fetched Image passed all six
isolated QEMU KUnit suites (19/19, zero failures or skips) and reached
`System halted`; the pinned vendor revision accepted all 11 experiment patches
and the five affected objects compiled with GCC 6.3. See the [vendor compile
receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-policy-clock-rail-buildbox-20260811.txt)
and [QEMU receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/mainline-policy-clock-rail-qemu-20260811.txt).
This is still compile/virtual evidence only. The next ordered gate is a
separate vendor-aware caller lifecycle/runtime candidate that binds the real
registration and invalidation paths, proves one-generation read-only runtime
identity on Gemian, and keeps provider registration default-off until those
checks pass. No device boot/write or CPU8/CPU9 admission follows from this
mapping result. The exact current vendor probe/remove sites and missing
event-forwarding paths are recorded in the [lifecycle candidate audit](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-lifecycle-candidate-audit-buildbox-20260811.txt).
The full profile was subsequently rebuilt from the pushed commit `b52925d` on
Buildbox, again validating 255 patches, 119 DTBs, package checksums, and a
validated-package-only fetch; see the [resume receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-b52925d-20260811.txt).
This is provenance-only revalidation and does not advance provider, runtime,
hardware, or CPU8/CPU9 admission.

Patch `0270` now exposes a separate, raw source-observation ABI for the vendor
function/date words, EEM CPU bin and ATE version, and PPM table selection while
keeping calibrated identity fail-closed. The exact pushed commit `2255b72`
passed the `dvfsp-owner-kunit` Buildbox profile with 259 canonical patches,
119 DTBs, passing package/provenance checksums, and validated-package-only
fetch. The pinned vendor revision then applied experiment patches `0001` through
`0014` sequentially and compiled the vendor writer, cpufreq, hybrid CSPM, EEM,
and PPM objects with GCC 6.3; see the [identity-observation Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-identity-observation-buildbox-20260811.txt).
This is still compile-only evidence: no provider registration, mutable epoch or
calibration handle, device action, hardware write, or CPU8/CPU9 admission is
claimed. The next ordered gate is a read-only runtime observation that obtains
an explicit mutable table epoch and calibration handle before any provider
registration review or device boot.

The repaired anchored vendor series was then resumed at exact pushed commit
`628bb5c`. Buildbox applied all twelve selected patches sequentially, passed
`gemini_modular_defconfig`, `prepare`, and `modules_prepare`, and compiled the
writer, cpufreq, hybrid CSPM, EEM, and PPM objects with the managed GCC 6.3
toolchain; see the [integration-context Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-integration-context-buildbox-20260811.txt).
This closes the repaired patch-application and object-compilation gate only.
The accessor makes the opaque vendor integration context reachable, but no
real caller/coordinator is bound, no owner is registered, no setter or device
I/O occurs, and CPU8/CPU9 admission remains closed. The next ordered step is
a separate reviewable external caller/coordinator that registers only after
complete lifecycle and invalidation coverage, followed by read-only runtime
identity evidence; do not boot or write a device for this compile result.

Patch `0267` now adds that explicit default-off coordinator at exact pushed
commit `ba6dfdd51839612ac55ff7458c93e3f9d6acd325`. Buildbox applied all 256
canonical series entries in the `dvfsp-owner-kunit` profile, compiled the
coordinator and owner-KUnit objects, produced 119 DTBs, passed package
checksums, and fetched only the validated package; see the [coordinator
Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-writer-coordinator-buildbox-20260811.txt).
This closes the source/build coordinator contract only: it does not invoke the
real vendor exported ops/context, register an owner/provider/setter, touch
hardware, or admit CPU8/CPU9. The next ordered gate is source-level review of
the actual external caller invocation plus read-only runtime identity and
invalidation evidence. Do not boot or write a device for this compile result.

Patch `0268` now adds a guarded mainline-side runtime-event forwarder at exact
pushed commit `7926d1ef60d646ad438479429c2a354880866763`. Buildbox applied all
257 canonical series entries in the `dvfsp-owner-kunit` profile, compiled the
coordinator and owner-KUnit objects, produced 119 DTBs, passed
package/provenance checksums, and fetched only the validated package; see the
[runtime-event forward Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-writer-runtime-event-forward-buildbox-20260811.txt).
This closes the guarded event-forwarding compile gate only: Buildbox did not
execute KUnit, the actual vendor probe/remove caller is not bound, runtime
identity/invalidation evidence is absent, and no owner/provider/setter,
hardware action, device boot/write, or CPU8/CPU9 admission is claimed. The next
ordered gate is binding those exact vendor probe/remove callsites and collecting
read-only runtime identity and invalidation evidence.

Patch `0269` and vendor patch `0013` now bind those exact probe/remove callsites
to the coordinator lifecycle gate. The mainline candidate built on Buildbox at
`646746a` with 258 canonical patches, while the pinned vendor tree applied all
thirteen experiment patches and compiled the five affected objects at
`995c998`; see the [caller lifecycle gate Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-caller-lifecycle-gate-buildbox-20260811.txt).
This closes the cross-tree compile gate only: no real owner is bound, runtime
identity/invalidation evidence is absent, and CPU8/CPU9 admission remains
closed. The next ordered gate is read-only runtime identity and invalidation
evidence for a real owner; do not boot or write a device.

The full profile was resumed from exact pushed commit `4403dc0`. Buildbox
applied all 259 selected canonical entries, produced 119 DTBs, passed
source/patch/config/package checksums, and the validated package was fetched;
see the [Buildbox resume receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-4403dc0-20260811.txt).
This is provenance/build evidence only and does not advance provider, runtime,
hardware, or CPU8/CPU9 admission. The next ordered gate remains explicit
read-only runtime epoch and calibration-handle evidence before provider review.

A fresh bounded read-only probe of the named Gemian runtime found active
vendor PPM/EEM state and nonzero EEM calibration records, while CPU1 was
offline in three consecutive samples and CPUs 0-9 remained present/possible.
The exported surfaces still contain no attributable owner, mutable-table
epoch, transition lock, or calibration handle; see the [EEM/PPM identity
surface review](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/runtime-eem-ppm-identity-review-20260811.txt).
This distinguishes available vendor calibration payload from an owner
identity and does not open provider, boot, write, or CPU8/CPU9 admission. The
next implementation is a source-owned identity-observation handoff, followed
by explicit epoch and calibration-handle evidence before any runtime owner
registration.

The source-owned observation handoff is now implemented in mainline patch
`0270` and validated on Buildbox at exact commit `09bd32b`; the
`dvfsp-owner-kunit` profile applied 259 canonical patches, compiled the source
and KUnit fixture, produced 119 DTBs, and passed package checksums. The
observation exposes raw function/date words, CPU bin, EEM ATE version, and PPM
table selection without relabeling them as owner identity; see the
[identity-observation Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-identity-observation-buildbox-20260811.txt).
The pinned vendor adapter patch `0014` is not yet GCC-6.3-compiled, and the
calibrated identity callback remains fail-closed. The next ordered gate is the
vendor-series compile, followed by read-only runtime observation plus explicit
mutable epoch and calibration-handle evidence; no provider registration,
device boot/write, or CPU8/CPU9 admission follows from this build.

The distinct follow-up read-only census searched bounded debugfs, sysfs,
device-tree, and vendor `/proc` identity surfaces on boot
`6d50bdf0-7a85-4083-9917-4591a4aca32d`. It found the expected `cpuhvfs`
debugfs endpoints and active PPM/EEM/cpufreq surfaces, but no attributable
epoch, generation, calibration handle, owner token, or shared transition lock
in endpoint names or the first 4096 bytes of each candidate; see the [runtime
identity-surface census](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/runtime-identity-surface-census-20260811.txt).
CPU0 was the only online CPU in this sample while CPUs 0–9 remained
present/possible. This keeps the runtime-owner gate closed and is not CPU8/CPU9
support evidence. The next ordered implementation is an explicit vendor
epoch/calibration-handle owner contract, followed by new read-only validation;
do not boot or write a device.

Patch `0271` now defines that explicit default-off cooperation boundary. A vendor
adapter must return nonzero variant, mutable table epoch, and calibration handle
values together with exact source-generation, owner, and transition-handle
echoes for one source snapshot. The mainline side rejects zero or mismatched
values, and the bridge transition generation remains an echo only rather than a
table epoch. Buildbox applied the selected 260-patch `dvfsp-owner-kunit` profile
at exact pushed commit `42df64a`, produced 119 DTBs, passed package/provenance
checksums, and the validated package was fetched; see the [provenance cooperation
Buildbox receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-provenance-cooperation-buildbox-20260811.txt).
This is compile/package evidence only: no real vendor callback, runtime owner,
provider, setter, hardware write, device action, or CPU8/CPU9 admission exists.
The next ordered gate is implementing the real vendor callback from pinned source
evidence and collecting new read-only runtime validation; do not boot or write a
device.

A follow-up read-only audit of the pinned vendor revision confirms that the
remaining callback cannot be filled from existing fields. `ateVer`,
`cpuBinLevel`, and `infoIdvfs` are efuse selection/status values; EEM calibration
mutates private detector state without publishing a handle. The vendor PPM and
cpufreq paths have separate locks, no shared generation/owner/transition fields,
and single-slot callback registration. The source-backed SB/0119 epoch already
in mainline identifies a table family, but does not prove a vendor mutable epoch.
See the [vendor provenance source audit](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-provenance-source-audit-20260811.txt).
The next ordered implementation is explicit vendor cooperation: publish a
calibration-lifecycle handle and mutable table epoch at the vendor commit points,
invoke the provenance callback inside the shared writer transaction, echo its
generation and owner handles, and chain the existing single-slot callbacks.
Only after that compile review and a new read-only runtime identity/invalidation
sample may owner/provider registration be reconsidered; device boot, writes, and
CPU8/CPU9 admission remain closed.

Patch `0015` now implements the explicit vendor cooperation boundary in the
pinned tree: EEM publishes and invalidates a calibration-lifecycle handle, the
shared writer advances a separate mutable table epoch for committed PTP/PPM
table updates, and the source adapter returns both values with exact generation
and owner/transition-handle echoes. The corrected mainline candidate was rebuilt
at pushed commit `2f46dea`; Buildbox validated all 260 canonical entries, 119
DTBs, package checksums, and the validated-package-only fetch (see the [mainline
receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-2f46dea-20260811.txt)).
The pinned vendor revision accepted all fifteen selected patches and compiled
the five affected objects with the managed GCC 6.3 toolchain against the
prepared patched Linux headers (see the [vendor receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/vendor-provenance-publication-buildbox-20260811.txt)).
This closes the cross-tree compile gate only. Runtime owner identity and
invalidation evidence remain absent; provider registration, setters, hardware
writes, device boot, and CPU8/CPU9 admission remain closed. The next ordered
gate is a new read-only runtime sample that can attribute the epoch and
calibration handle, followed by a separate provider-registration review.

The exact pushed documentation head `78f478f` was then resumed on Buildbox with
the named `dvfsp-owner-kunit` profile. All 260 canonical entries, 119 DTBs, and
package/provenance checksums passed, and only the validated package was fetched
locally; see the [Buildbox resume receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/buildbox-resume-78f478f-20260811.txt).
This is a reproducibility confirmation, not new hardware evidence: no provider
was registered, no runtime owner or setter was called, no device was booted or
written, and CPU8/CPU9 admission remains closed. The next ordered gate is still
the read-only runtime epoch/calibration-handle sample, followed by provider
registration review.

The direct USB netcat census helper is now prepared and syntax-checked at
[`runtime-identity-surface-census-nc.sh`](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/scripts/runtime-identity-surface-census-nc.sh).
It validates the expected Gemini USB interface and route before sending a
bounded, label-only read-only census. The follow-up availability check found no
expected USB interface, and the known LAN netcat port did not answer; no runtime
sample or device action occurred. See the
[transport availability receipt](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/runtime-identity-nc-transport-20260811.txt).
The next ordered gate is unchanged: run this helper when the USB link is
present, then require attributable epoch and calibration-handle evidence before
provider review.

The owner-confirmed SSH path supplied a fresh bounded census on 2026-08-14.
It again found no attributable epoch, calibration handle, owner, transition,
or shared-lock field in the running stock Gemian kernel. The linked
[source/build audit](../experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/runtime-provenance-link-gap-20260814.txt)
shows why: the vendor caller and Linux 7.1 coordinator are only separately
object-compiled, and the successful provenance path requires them to be linked
and lifecycle-bound in one runtime kernel. Repeating the unchanged census is
therefore not an ordered gate. The full-source reconstruction also shows that
porting the Linux 7.1 experimental coordinator into vendor Linux 3.18 would
create a large vendor-only owner stack without advancing the upstream kernel.
The next ordered implementation is instead the
[default-off vendor provenance observer](../experiments/2026-08-14-mt6797-runtime-provenance-observer/README.md):
it instruments the real EEM calibration and PPM table-commit lifecycle, but
permanently reports zero owner and transition handles. Its exact Buildbox job
now passes normal patch application, the complete kernel link, zero unresolved
symbols, linked-marker validation, and the compile-review-only package gate.
The separate LK boot-container construction and validation gate now passes with
the known-good Gemian header and ramdisk, exact replacement kernel, independent
assembly and padding paths, and negative mutation checks. The next ordered gate
also passes: the frozen pre-boot hypothesis, exact runtime decision map,
read-only direct-USB/netcat collector, mutation-tested classifier, and guarded
installer preserve attribution, inactive live-GPT boot2, stable power, full
readback, no-fresh-backup, and clean-shutdown invariants. The first guarded write
and readback passed, but its one selected cycle stuck at the splash and exposed
no runtime interface. Recovery showed a manual power-key reason, empty pstore,
offline CPU8/CPU9, and unchanged boot2. Offline inspection then proved the
container retained the stock Gemian ramdisk and therefore could not provide the
expected project USB/netcat shell. Do not repeat it. A kernel/DT/config-identical
derivative then passed independent construction and mutation review with a new
early debugfs record and the live-verified legacy Android RNDIS observation
path. Its guarded boot2 write and independent readback passed. On its one
physical selection, however, no Gemini USB device or RNDIS path appeared within
the complete 900-second window. Manual power-key recovery found empty pstore,
only the generic 74-byte last-kmsg header, CPUs 8/9 offline, and unchanged exact
boot2. The missing stock splash is not an early-kernel discriminator because
the diagnostic ramdisk does not launch it. No retained evidence distinguishes
kernel entry, initramfs entry, or failure before Android USB service; runtime
EEM/PPM publication therefore remains unobserved. Do not repeat either
artifact. The subsequent offline audit confirms that the linked vendor image
registers ramoops and the MT6797 reset handler before the observer late initcall,
while the vendor watchdog kicker remains a separate late-init kernel owner. An
initramfs-only watchdog takeover is therefore rejected. The selected successor
is a separate default-off kernel companion that emits an attributable
pre-`/init` pstore-console checkpoint after the existing observer and kicker,
then schedules one 120-second `emergency_restart()` through the registered
MT6797 handler. It preserves the exact corrected initramfs and DTB, performs no
storage, DVFSP, regulator, or CPU action, and makes RNDIS a fast path rather than
the sole observation path. Its deterministic source editor and validator now
pass local syntax and static checks, reject a second application, and reject all
thirteen decision-changing mutations. Exact pushed commit `fdd511e` then
generated one normal format patch on Buildbox from the exact observer parent;
an independent clean clone reapplied both patches, reproduced child commit
`2dbf7be`, passed the source validator, and remained clean. The fetched package
and repository patch are byte-identical, and thirteen semantic patch mutations
are rejected. Exact pushed job `b2d638f` then passes the Buildbox-only full
kernel link, exact three-entry configuration delta, binary marker and symbol
checks, zero-unresolved-symbol closure, strict restart/ramoops/watchdog/
observer/kicker/recovery initcall ordering, bounded disassembly, and direct
`emergency_restart()` call. It remains compile-review-only with CPU8/CPU9
admission closed. The next ordered action is a new Android-v0 container that
preserves the corrected diagnostic initramfs, appended DTB, and vendor address
contract while changing only the validated kernel and canonical image ID.
Two independent roots now produce byte-identical raw and exact-size images;
both independent validators pass and reject all six structural mutations, and
the generic LK analyzer retains only the same three inherited vendor differences
as the corrected reference. The exact padded SHA-256 is `99414cdecc4e...`.
The next ordered action is to freeze the pre-boot hypothesis and result map,
then pin the collector, pstore recovery path, classifier, and guarded installer
to this exact candidate and its expected single restart near 120 seconds. That
offline review now passes both positive paths, distinguishes fourteen direct
and retained-evidence mutations, keeps RNDIS as the fast path, and requires the
independent pstore/recovery cycle. The next ordered action is one read-only
Gemian OS/root/live-GPT/power/sudo preflight. That preflight now passes with
unique inactive `/dev/mmcblk0p30`, stable full battery plus external power, and
the prior corrected image still present. The guarded deployment then resolved
that same inactive live-GPT boot2, wrote and independently read back exact full
image `99414cdecc4e...`, created no fresh backup, and shut the device down
cleanly. Its one physical selection appeared static at the boot screen but
automatically returned to ordinary Gemian. Retained pstore proves the candidate
reached its checkpoint at 1.99 seconds, recorded two stable complete read-only
observer snapshots, launched the diagnostic services, and invoked the
registered MT6797 restart path at 122.07 seconds. The recovery boot ID changed,
and boot2 still matched the exact candidate after return. The snapshots publish
variant 274, generation 9, table epoch 1, calibration handle 1, all three PPM
clusters, all five required EEM banks, three table commits, five bank
publications, and one calibration publication, while owner and transition
handles remain zero and provider, hardware-write, and CPU-admission claims stay
closed. See the [pre-init runtime result](../experiments/2026-08-14-mt6797-runtime-provenance-observer/results/preinit-runtime-attempt-1-20260815.txt).
This closes the runtime provenance-publication measurement; do not repeat the
candidate. The next ordered implementation is one native transition owner
spanning the DVFSP/I2C6/DA921x operation and rollback boundary. Provider
registration must first remain read-only and fail closed. Setters, hardware
writes, and CPU8/CPU9 admission remain closed until their later dedicated
gates.

The intervening read-only registration contract is now complete. Patches
`0272` through `0276` preserve the 64-bit epoch and assembled attribution,
cross-check the exact vendor provenance view, bound the bridge snapshot, and
add one explicit default-off registration entry point with registry-identity
recheck, a second stable observation, rollback, and guarded teardown. Exact
focused Buildbox compile and isolated arm64 QEMU validation pass all 25 tests;
the normal full profile also applies all 265 patches and builds 119 DTBs at
exact pushed commit `5a28b62`. See the
[registration experiment](../experiments/2026-08-15-mt6797-readonly-owner-registration/README.md).
No physical device was accessed, and this does not claim a live owner: the last
Gemini sample's owner and transition handles are both zero and must fail the new
gate.

The subsequent complete-tree call-site audit found no production Linux 7.1
caller for either experimental registration entry point. The only external
caller is retained in the separate vendor/Gemian 3.18 patch, so an "actual
external vendor caller/coordinator boundary" does not exist in the upstream
runtime tree. Do not create another synthetic caller or port the Linux 7.1
coordinator back into the vendor tree merely to satisfy that design. The same
audit exposed a broad profile-link defect: handoff sources called four pure
clock/CSPM decoders whose objects were owned only by the optional protected-
clock transport. Patch `0277` moves those two pure decoder objects behind a
hidden union gate while leaving transport default-off. Exact pushed commit
`ede1f47` passes the previously failing transport-free DA921x profile and the
paired transport-enabled profile on Buildbox; all four helpers occur exactly
once in each linked image. See the
[decoder-link experiment](../experiments/2026-08-15-mt6797-handoff-decoder-link/README.md).
This is build closure only, not live provider or owner evidence.

The single next ordered implementation is a default-off, attributable,
read-only observation of the native Linux 7.1 DA921x resource-only provider.
It must uniquely report successful chip identification and registration of
both regulator descriptors, bounded current selector/voltage/enable samples
for both rails, bind/unbind and failed-probe cleanup, and an exact zero
register-data-write count. First require source review, focused fault-path tests,
and normal full Buildbox validation. Only then may one new runtime candidate be
considered. The result decides whether this native provider can become the
resource boundary for the later transition owner; it does not itself create an
owner. Provider setters, hardware writes, and CPU8/CPU9 admission remain
closed.

That implementation and every offline gate now pass at exact kernel commit
`d0d511e`: five focused arm64 KUnit cases, the normal Buildbox profile, fetched
package checksums, two independent Android-v0/LK output roots, all 32 LK gates,
and twelve structural mutation rejections. Exact padded candidate
`7a3ce120de99...` was installed to live-GPT logical boot2, independently read
back, and followed by clean shutdown. Runtime attempt 1 automatically returned
to ordinary Gemian with a changed boot ID, but the pre-armed collector had
expired before physical selection and its replacement started after boot2.
No direct USB interface appeared before return; pstore was empty and the
74-byte last-kmsg held only its generic header. This is cycle evidence only,
not a kernel or provider result. See the
[attempt record](../experiments/2026-08-15-da921x-readonly-observer/results/runtime-attempt-1-inconclusive-20260815.txt).

The one permitted same-artifact repeat is complete. Boot2 already had the exact
full checksum and was not rewritten; independent readback and clean shutdown
passed. A fresh read-only USB/netcat collector was confirmed waiting before
physical selection. The candidate again returned automatically to a changed
ordinary-Gemian boot, but no USB interface appeared, pstore was empty, and
last-kmsg was the same generic 74-byte header. This is a repeated pre-transport
service failure, not provider or kernel-fault attribution. Do not repeat the
observer image. See the
[repeat record](../experiments/2026-08-15-da921x-readonly-observer/results/runtime-attempt-2-pretransport-20260815.txt).

The single next ordered discriminator is a matched current-tree
`da921x-resource-only-provider` control with the observer disabled. Hold the
patch series, DT, serviceability ramdisk, LK addresses and command line,
provider registration, CPU0--7 baseline, and recovery policy fixed; change only
the observer configuration, four live observer reads, unique kernel release,
and resulting container identity. Build through Buildbox and independently
review the container before any device action. Attributable control USB or
retained pstore implicates the observer path; the same pre-transport failure
instead moves localization to the current base/container boundary against the
last retained-pstore baseline. Screen color and automatic return remain
non-attributable.

That matched control is now built and independently validated at exact pushed
commit `1ab09cd`. The patch series and Gemini DTB are byte-identical to the
observer package; its configuration differs on exactly the unique local
version and observer-disabled lines, and both decompressed Images have the same
size and effective arm64 layout. Exact padded candidate `3188d474f5d6...`
passes its fetched-package manifest, two independent construction paths, all
32 LK gates, six structural mutations, and the frozen read-only runtime-tool
suite. See the
[matched-control experiment](../experiments/2026-08-15-da921x-provider-control/README.md).
The guarded installer then resolved live-GPT logical boot2 as inactive and
unmounted `/dev/mmcblk0p30`, replaced the exact observer predecessor, verified
the exact control by full-partition hash and independent byte comparison, and
confirmed ordinary Gemian powered off. No fresh backup was created. The owner
selected boot2 after the original collector's 900-second window expired; an
identical replacement started immediately after the report but saw no exact USB
interface before the device had automatically returned to a changed ordinary-
Gemian boot. Immediate recovery found empty pstore and the identical generic
74-byte last-kmsg header. This timing-limited control does not establish kernel
entry, but it supplies no evidence implicating the observer-only reads. Stop
both exact candidates. See the
[deployment receipt](../experiments/2026-08-15-da921x-provider-control/results/deployment-20260815.txt)
and [runtime result](../experiments/2026-08-15-da921x-provider-control/results/runtime-attempt-1-pretransport-20260815.txt).

The single next ordered action is offline localization of the shared current
kernel/container against the last serviceable mainline container and last
retained-pstore mainline baseline. Pin the exact first changed boundary in
patch series, configuration, DT, Image header, and ramoops registration. If
those checks do not already isolate a defect, add one default-off, exact
candidate marker at the earliest proven post-ramoops point, before DA921x
provider probe, with the same provider-only configuration, DT, ramdisk, LK
layout, CPU0--7 policy, and recovery path. That marker must be the independent
decision-changing observation path; do not add regulator reads, writes, an
owner, or CPU8/CPU9 admission.

That audit has isolated an earlier broad configuration boundary before new
checkpoint code is justified. The last serviceable mainline Stage-27 image and
failed current control have the exact same module-free serviceability ramdisk,
LK addresses and command line, pstore/console configuration, ramoops DT region,
and ramoops-before-DA921x initcall order. Stage 27, however, restored
`CONFIG_MODULES=y`; the failed current profile inherits module support disabled.
The resolved configs contain 302 changed add/remove lines as defconfig module
selections become built-ins, and the current decompressed Image is 1,816,576
bytes larger. See the
[baseline localization](../experiments/2026-08-15-mainline-module-policy-control/results/baseline-localization-20260815.txt).

The configuration-only `da921x-resource-only-provider-modules-control` profile
is now built at exact pushed commit `09ba93d`. It exactly extends the failed
provider-only profile with `CONFIG_MODULES=y` and a unique local version; the
external initramfs remains module-free, while the DA921x driver/provider remain
built-in, read-only, and observer-free. The fetched package passes its complete
manifest, keeps the exact parent Gemini DTB and 267-patch series, and produces
no external module package. Its decompressed Image shrank by 1,818,624 bytes
from the failed parent and is only 2,048 bytes smaller than serviceable Stage
27, with the same 12,517,376-byte effective size. Independent assembly and
padding agree byte-for-byte, all 32 LK gates pass, and six container mutations
are rejected. See the
[offline review](../experiments/2026-08-15-mainline-module-policy-control/results/offline-validation-20260815.txt).

The exact candidate/tooling record is pushed and full boot2 SHA-256
`044461e57d207f5ddd6e68cc463ea3ee1dd65260c27afe5fd00730137d13a2ff` is
installed on live-GPT logical boot2. The write, sync, flush, full-partition
checksum, independent readback, and byte comparison passed; no fresh backup
was created. Gemian then shut down and is confirmed unreachable. See the
[deployment receipt](../experiments/2026-08-15-mainline-module-policy-control/results/deployment-20260815.txt).

The single exact runtime discriminator is complete and stopped. The one-hour
read-only collector was armed before selection and remained active through the
reported automatic return, but no exact USB interface appeared. Ordinary
Gemian returned with a changed boot ID; immediate recovery found empty pstore
and the same generic 74-byte last-kmsg header as the observer and provider-only
attempts. Boot2 still matched the exact deployed candidate. No exact kernel or
provider identity survived. See the
[runtime result](../experiments/2026-08-15-mainline-module-policy-control/results/runtime-attempt-1-pretransport-20260815.txt).

Restoring module policy is therefore not sufficient and is not accepted as the
localized cause. The exact candidate must not be repeated. The single next
ordered action is one default-off earliest post-ramoops checkpoint on the same
module-policy/provider-only base. It must record a unique exact-candidate token
after ramoops registration and before DA921x provider probe, without regulator
reads, writes, transition ownership, or CPU8/CPU9 admission. Retained token
evidence localizes failure after kernel entry; another empty-pstore cycle moves
the boundary before that checkpoint. Screen color and automatic return alone
remain non-attributable.

That checkpoint is now built and independently validated at exact pushed
commit `cac458c1`. The package retains the module-policy/provider-only base,
read-only built-in provider, observer-disabled policy, exact Gemini DTB, and
unchanged serviceability ramdisk/LK layout. The marker
`GEMINI_MAINLINE_POST_RAMOOPS_20260815_A` occurs exactly once after successful
pstore registration. Two independent construction paths agree on full boot2
SHA-256 `ae6b354d51a9...`; all 32 LK gates pass and six structural mutations
are rejected. The one-hour USB collector and guarded no-backup/full-readback/
shutdown installer are frozen. See the
[checkpoint experiment](../experiments/2026-08-15-mainline-post-ramoops-checkpoint/README.md).

The single ordered action is to install that exact candidate to live-GPT
logical boot2, require a matching full readback, shut Gemian down, and arm the
collector before one selected boot. Recover pstore immediately after any
return. A retained exact marker moves localization after successful ramoops
registration; another empty-pstore confirmed cycle moves the boundary before
that point without claiming that the kernel never entered. Do not repeat the
exact candidate after its one attempt.

The guarded deployment is complete. Live GPT resolved inactive, unmounted
`boot2` as `/dev/mmcblk0p30`; its predecessor was recorded without making a
fresh backup. The exact candidate was written, synced, flushed, and verified
by matching full-partition checksum and independent byte comparison. Gemian
then shut down and is confirmed unreachable. The remaining ordered action is
to arm the one-hour collector before the owner selects boot2 once. See the
[deployment receipt](../experiments/2026-08-15-mainline-post-ramoops-checkpoint/results/deployment-20260815.txt).

The checkpoint's single selected boot is now complete and the exact candidate
is stopped. The original collector expired before selection; an identical
late-window replacement started immediately after the boot report and saw no
exact USB interface before the automatic return. The disconnect was confirmed,
ordinary Gemian returned with a changed boot ID, and immediate recovery found
empty pstore plus the same generic 74-byte last-kmsg header. Boot2 still
matched the exact candidate. No exact checkpoint token or kernel identity
survived. See the
[runtime result](../experiments/2026-08-15-mainline-post-ramoops-checkpoint/results/runtime-attempt-1-pre-ramoops-20260816.txt).

The boundary therefore moves before successful ramoops registration, without
claiming that the kernel never entered. A capture-method review explains why
the recent wave was low-yield: USB depends on late userspace/gadget progress,
and the attempted token depended on the same successful ramoops registration
being tested. Visual return remains non-attributable, while the vendor
last-kmsg SRAM path lacks a proven mainline-to-Gemian preservation contract.

The selected next discriminator reuses the already proven cross-version
persistent-RAM format without requiring normal ramoops registration. The final
four dmesg slots (indices 171--174, `[0x444bb000, 0x444bf000)`) have exact
shared addresses and were read-only verified as `DBGC` with zero start/size.
An isolated profile will keep the reservation but disable the normal ramoops
probe, then write one short unique record per stage: after reserved-memory
scan, early initcall, core initcall, and postcore initcall. Each slot is
independent, so a partial later write cannot destroy the last completed stage.
Returned Gemian will archive the slots; USB is secondary and screen color is
ignored. See the
[capture-method review](../experiments/2026-08-15-mainline-post-ramoops-checkpoint/results/capture-method-review-20260816.txt).

The selected ledger's one permitted boot is now complete; see the
[pre-ramoops experiment](../experiments/2026-08-16-mainline-pre-ramoops-ledger/README.md).
Its Buildbox package and exact container passed offline gates, all four live
headers were empty before deployment, boot2 write/readback and shutdown
completed, and a pre-armed observer proved a changed return to Gemian.
Immediate pstore recovery and the bounded raw-zone follow-up found no valid
stage or exact payload. The artifact is stopped. This localizes the useful
boundary before successful completion of the post-`arm64_memblock_init()`
checkpoint or inside that checkpoint's fail-closed gates; it does not prove
that LK entered the arm64 Image.

The lower-boundary audit is complete and the owner authorized its exact
`GAEL-20260816-A` successor plus one boot2 attempt. The design uses independent
records after `record_mmu_state`, after `__cpu_setup`, after early-ioremap
initialization, and after `arm64_memblock_init`. The two MMU-off stages preserve
the boot ABI, accept only EL1/EL2 with MMU and data cache off, and require the
exact four-header physical fingerprint. Later stages accept an earlier slot
only when empty or byte-exact. See the
[entry-ledger audit](../experiments/2026-08-16-mainline-arm64-entry-ledger-audit/README.md).

The exact entry-ledger attempt retained no stage and remains stopped; see the
[runtime result](../experiments/2026-08-16-mainline-arm64-entry-ledger/results/runtime-attempt-1-no-stage-20260816.txt).
Its original absent-entry interpretation is superseded: the later positive DTB
control reached `/init` and USB with the same kernel and ledger, yet its
returned-Gemian raw zones were also empty. Returned empty slots therefore do
not establish absent Image entry; they may reflect writer refusal or payload
clearing during the warm return/Gemian ramoops initialization.

The lower-boot-boundary audit is complete. The stopped GAEL and runtime-proven
Stage-27 containers both satisfy their Android-v0, gzip, decompression, Image
header/branch, load-range, and overlap contracts. Pinned public Planet LK source
disables unified cache and the MMU before its final arm64 branch, matching E0's
normal state gate, and actively opens, merges, and mutates the appended DTB
before that branch. The two DTBs retain the exact board, memory, and GAEL
ramoops reservation contract but differ structurally across `/chosen` and
multiple loader handoff/overlay targets. Static analysis cannot prove that the
installed loader accepts the exact current DTB. See the
[lower-boundary audit](../experiments/2026-08-16-mainline-lk-handoff-dtb-control/results/lower-boundary-audit-20260816.txt).

The exact GAEL kernel crossed with the runtime-proven Stage-27 DTB completed its
one attempt. Exact USB identity proved release `7.1.3-gemini-entryled-a`, arm64,
execution through `/init`, CPU0--7 online, CPU8/9 offline, and the established
netcat shell; dmesg had no panic, BUG, call trace, or unable-to-handle record.
The identity-gated native reboot returned to changed-identity Gemian and boot2
remained exact. This proves LK decompression/final branch and current Image
serviceability. With every container input except the DTB unchanged, the
current DTB path is strongly implicated. See the
[positive runtime result](../experiments/2026-08-16-mainline-lk-handoff-dtb-control/results/runtime-attempt-1-serviceable-20260816.txt).

The LK-sensitive DTB repair audit is complete and corrects the experiment
lineage. The serviceable Stage-27 candidates reused a frozen Gate-3
USB-enabled observation DT; the stopped current-DTB GAEL attempt instead used
its package base DT, where the USB T-PHY, USB2 PHY port, and MTU3 peripheral
controller were disabled. No audited `/chosen`, CPU, reserved-memory, overlay,
or handoff delta isolates a strict stop in the pinned public LK contract. The
prior absence of USB therefore did not cleanly establish an LK or Image-entry
failure. See the
[current-DT USB audit](../experiments/2026-08-16-mainline-current-dtb-usb-observation/results/lk-sensitive-dtb-audit-20260816.txt).

The minimal derivative changes only those three existing `status` properties
to `okay`; xHCI remains disabled, the role remains peripheral, and every other
decompiled property remains equal to the package DT. The exact derived DTB is
`e93264b32e0a42098fa6556e454abc99b75373e92e1e3b6eef50285542251331`.
The exact raw container is
`a9d4f9516d761bfb30faf95e8b3d3f9e9d19282bc67d508fbc5ff308e84954be`
and the exact 16 MiB boot2 payload is
`fa107a988d860f017905c61a4b52110bc8dc3cc1ce5f407424fa3dd47c9b8b87`.
Two assemblies, independent padding, all 32 LK gates, the exact manifest, and
six negative mutations pass without rebuilding the kernel.

The exact payload has now been installed to live-GPT-resolved inactive boot2.
Its predecessor matched the Stage-27 control, and the guarded write, sync,
flush, independent full readback, and clean shutdown all passed. No fresh
backup was made and no automatic reboot occurred. See the
[deployment receipt](../experiments/2026-08-16-mainline-current-dtb-usb-observation/results/deployment-1-20260816.txt).

The one pre-armed attempt is complete. The host saw only MT65xx preloader
enumeration, followed by its detach; no Linux USB device, exact fixed-MAC
interface, or netcat endpoint appeared before Gemian enumerated separately and
returned with a changed boot ID. Pstore remained empty and boot2 still matched
the exact payload. The three USB `status` properties are therefore insufficient
for serviceability. The result remains bounded before or inside the mainline
USB observation path and does not prove absent Image entry. See the
[runtime result](../experiments/2026-08-16-mainline-current-dtb-usb-observation/results/runtime-attempt-1-no-mainline-usb-20260816.txt).

The remaining semantic partition is complete. In pinned public Planet LK,
`platform_fdt_scp()` returns failure when no `mediatek,scp` node exists;
`platform_atag_append()` propagates it and the caller returns before Linux
handoff. The stopped DT lacks that node while the runtime-proven Stage-27 DT
contains it. Other remaining loader-group differences either log and continue,
write properties to an already-present `/chosen`, or retain identical reserved
ranges. Later ownership and keyboard/I2C groups are not loader prerequisites.
See the
[strict-boundary result](../experiments/2026-08-16-mainline-scp-handoff-node/results/strict-lk-scp-boundary-20260816.txt).

The selected derivative adds only the exact input-disabled SCP node. Linux SCP
probe remains closed, USB remains peripheral-only, xHCI remains disabled, and
CPU8/9 remain offline. Its exact DTB is
`53ceeaddcae13ff10ddc219441ac46a300324e5490e436626601f0d928c1558b`;
the exact raw container is
`d13f110ad38e3a515d2f339619f32d529c76612543e89d3fe2df45689141c3a4`;
the exact 16 MiB payload is
`73be76fd4eb26d6d1d718bb4c0a77653839ca40e00267a5a35defb5b8a45b0f7`.
Two assemblies, two padding paths, all 32 LK gates, the exact manifest, and six
negative mutations pass without a kernel rebuild. See the
[offline validation](../experiments/2026-08-16-mainline-scp-handoff-node/results/offline-candidate-validation-20260816.txt).

The single next ordered action is one guarded install of that exact payload to
live-GPT-resolved inactive boot2, full readback, clean shutdown, and one
pre-armed USB/netcat attempt. Exact mainline USB identity would support the SCP
contract as causal; mainline USB without netcat localizes later; preloader-only
or no mainline USB before changed Gemian stops this derivative without repeat.
Screen color and returned empty ledger slots remain non-oracles.

The guarded install is complete. Live GPT resolved inactive, unmounted
`boot2` as p30 while Gemian used p29; stable external power and 100% capacity
passed. The exact 16 MiB payload was written, synchronized, flushed, and fully
read back with SHA-256
`73be76fd4eb26d6d1d718bb4c0a77653839ca40e00267a5a35defb5b8a45b0f7`.
No fresh backup was created. Clean shutdown was requested and the device was
confirmed unreachable without an automatic reboot. See the
[deployment receipt](../experiments/2026-08-16-mainline-scp-handoff-node/results/deployment-1-20260816.txt).

The single attempt is complete. The live observer timed out shortly before the
physical selection, but immediate bounded Mac-log recovery retained the exact
USB sequence: MT65xx preloader enumerated and detached, no USB device appeared
between it and Gemian, then Gemian enumerated with RNDIS. Authenticated recovery
proved a changed Gemian boot ID, empty pstore, and the exact candidate still on
live-GPT p30. The disabled SCP node is therefore not sufficient for
serviceability; installed-loader causality remains unestablished. The candidate
is stopped. See the
[runtime result](../experiments/2026-08-16-mainline-scp-handoff-node/results/runtime-attempt-1-no-mainline-usb-20260816.txt).

The offline re-ranking is complete. The working Stage-27 DT has no watchdog
IRQ and its runtime proved that the built-in MT6797 watchdog driver took over a
bootloader-running timer before one second. The stopped current DT supplies an
optional IRQ whose mapping and request occur before that takeover. The next
candidate therefore deletes only the watchdog `interrupts` property while
preserving the exact kernel, initramfs, Android-v0 layout, USB observation
properties, disabled SCP input, watchdog reset-provider input, DA921x-write
closure, and CPU8/9 closure. Its deterministic assembly, independent semantic
validation, and guarded installer checks pass. See the
[watchdog IRQ isolation experiment](../experiments/2026-08-16-mainline-wdt-irq-isolation/README.md).

The exact candidate is published and its guarded installation is complete.
Live GPT resolved inactive, unmounted boot2 as p30 while Gemian used p29;
stable external power, the full write/readback comparison, and clean shutdown
all passed without a fresh backup or automatic reboot. See the
[deployment receipt](../experiments/2026-08-16-mainline-wdt-irq-isolation/results/deployment-1-20260817.txt).

The single attempt is complete. The observer had expired before physical
selection, but immediate bounded Mac-log recovery captured preloader, no
intervening USB identity, and then Gemian/RNDIS. Authenticated recovery proved
a changed Gemian boot ID, empty pstore, and the exact candidate still on
live-GPT p30. Removing the watchdog IRQ is therefore not sufficient. The small
fallback-timing change is supporting only and does not identify the reset
source. See the
[runtime result](../experiments/2026-08-16-mainline-wdt-irq-isolation/results/runtime-attempt-1-no-mainline-usb-20260817.txt).

The remaining partition is now recomputed. Passive differences do not add a
unique failing branch in their exact built consumers. The selected active
boundary restores the complete runtime-proven I2C5/AW9523/polling-keyboard
group, including I2C5's shared AP_DMA clock role and the positive control's
polling/no-parent-IRQ contract. This group probes after MTU3, so it tests the
missing established serviceability foundation and does not claim to explain an
earlier MTU3 failure. The exact kernel, initramfs, container, peripheral USB,
disabled SCP, no-watchdog-IRQ path, xHCI closure, DA921x/I2C6 closure, and
CPU8/9 closure remain fixed. See the
[I2C5 serviceability experiment](../experiments/2026-08-17-mainline-i2c5-serviceability-restoration/README.md).

The exact candidate passes deterministic DT and container reproduction, all
32 inherited LK/container gates, package and manifest provenance, SCP and
watchdog closure, the complete serviceability contract, five independent
negative mutations, and guarded-installer checks without a kernel rebuild.
The single next ordered action is to publish that definition, install the exact
payload once to live-GPT-resolved inactive boot2, require full readback and
clean shutdown, then arm a fresh USB/netcat observer immediately before the
physical selection. Mainline identity promotes the current-DT serviceability
foundation; preloader-only before a changed Gemian return stops this derivative
and triggers a reassessment of LK DT mutation or the observation boundary.

The candidate definition is published and guarded deployment is complete.
Live GPT resolved inactive, unmounted boot2 as p30 while Gemian used p29; the
predecessor was the stopped watchdog candidate. Stable external power, exact
write, sync, flush, full readback, and clean shutdown all passed without a fresh
backup or automatic reboot. See the
[deployment receipt](../experiments/2026-08-17-mainline-i2c5-serviceability-restoration/results/deployment-1-20260817.txt).

The single observed attempt is complete. Preloader enumerated and detached;
no intervening USB identity appeared before Gemian/RNDIS returned with a
changed boot ID. Authenticated recovery proved empty pstore, watchdog-block-
class reset tokens, active root p29, and the exact candidate still installed
and unmounted on boot2 p30. The complete I2C5/AW9523/polling-keyboard group is
therefore not sufficient. Timing remains supporting only and does not identify
the reset source. See the
[runtime result](../experiments/2026-08-17-mainline-i2c5-serviceability-restoration/results/runtime-attempt-1-no-mainline-usb-20260817.txt).

The offline reassessment found a concrete loader-side boundary. Pinned Planet
LK calls `target_fdt_cpus()` before kernel decompression and final handoff. Its
CPU loop advances `last_node` only after an active node supplies
`clock-frequency`; the stopped DT's first child, `cpu@0`, lacks that property,
so the missing-property `continue` selects the first child again. All ten
current CPU nodes lack the property, whereas the runtime-proven Stage-27
control supplies exact values for all ten. Live `lk` and `lk2` match the
project-start loader capture and carry the corresponding diagnostic and final-
jump strings; installed-source control-flow equivalence remains a
high-confidence inference rather than a symbolized byte-level proof. See the
[LK CPU-clock iterator experiment](../experiments/2026-08-17-mainline-lk-cpu-clock-iterator-repair/README.md).

The selected candidate adds only the ten exact Stage-27 CPU clock properties
to the stopped I2C5 predecessor. CPU8/9 admission remains closed; the exact
kernel, initramfs, peripheral USB path, disabled SCP input, no-watchdog-IRQ
path, I2C5/AW9523 polling serviceability group, DA921x closure, and recovery
path remain fixed. Two DT derivations and two container assemblies agree. All
32 inherited LK/container gates, six container mutations, five serviceability
mutations, five CPU-clock mutations, provenance, manifest, syntax, ShellCheck,
and guarded-installer gates pass without a kernel rebuild or native VM build.

The candidate definition is published and guarded deployment is complete.
Live GPT resolved inactive, unmounted boot2 as p30 while Gemian used p29; the
predecessor was the stopped I2C5 candidate. Stable external power, exact write,
sync, flush, full readback, and clean shutdown all passed without a fresh
backup or automatic reboot. See the
[deployment receipt](../experiments/2026-08-17-mainline-lk-cpu-clock-iterator-repair/results/deployment-1-20260817.txt).

The single observed attempt is a confirmed positive. The physical observer
captured the exact mainline USB product; a host sandbox restriction blocked
only the first route probe, not the device. Without another reboot, the same
published observer completed exact identity and service probes on its first
permission-corrected try. Runtime proved the expected kernel, arm64, CPUs 0–7
online with 8–9 closed, all ten exact Stage-27 clock values in the final DT,
`/init`, USB/netcat, I2C5, watchdog takeover, AW9523, and the polling keyboard.
One authorized native reboot returned to changed-ID Gemian with empty pstore
and the exact candidate still on unmounted live-GPT boot2 p30. See the
[runtime result](../experiments/2026-08-17-mainline-lk-cpu-clock-iterator-repair/results/runtime-attempt-1-serviceable-20260817.txt).

This confirms the LK CPU-iterator non-progress diagnosis and promotes the
ten-property repair as the current serviceability prerequisite. Do not repeat
the artifact. The next ordered action resumes gate 5: freeze this exact DT
prerequisite into a named runtime baseline, enable the resource-only provider
with every consumer disconnected and register-data writes disabled or
unreachable, and build only on buildbox after committing and pushing the exact
source change. Runtime must preserve CPU0–7, USB, console, keyboard,
I2C5/AP-DMA, watchdog takeover, cleanup, and native reboot while CPU8/9 remain
closed. Only that read-only provider result can open the bounded-write gate.

The gate-5 prebuild definition now does exactly that at the source/profile
boundary. Canonical patch `0282` places the ten runtime-proven Stage-27 clock
rates in the kernel-built Gemini DT. The named
`da921x-lk-clock-readonly-provider` profile extends the exact serviceable
entry-ledger configuration with only the read-only LK-devinfo NVMEM provider,
the existing DA921x observer, and a unique release. This addresses the precise
positive-predecessor runtime boundary: the DVFSP handoff waited for the
disabled NVMEM supplier, I2C6 waited for the handoff, and the DA921x client was
therefore never probed. The existing access-controller edge remains intact;
no regulator consumer, setter, owner, register-data write, or CPU8/CPU9 request
is added. Static source/profile validation and the all-profile canonical-series
audit pass; see the
[LK-repaired provider experiment](../experiments/2026-08-17-mainline-da921x-readonly-provider-baseline/README.md).
Buildbox has now built exact clean commit `7199e8229c6a...` as
`7.1.3-gemini-da921x-lkro`. Package checksums pass; the built board DT contains
all ten exact LK CPU clocks; and the resolved configuration retains
`maxcpus=8` while enabling only the read-only LK-devinfo supplier and DA921x
observer path plus expected framework dependencies. The final DT adds no
second CPU-clock mutation and restores only the exact proven USB, disabled-SCP,
no-watchdog-IRQ, I2C5/AW9523, and polling-keyboard serviceability group. Its
I2C6 access-controller edge and childless DA921x client remain intact.

The exact Android-v0 candidate and two independent padding constructions are
byte-identical. All 32 LK/container gates pass, and an independent validator
rejects twelve CPU-clock, provider-identity, read-only, ownership, consumer,
and serviceability mutations. The exact 16 MiB boot2 payload is
`eeee7adea53134c8146e10591708725649a8331bdef7ad418a847b5d04c8e854`.
No native VM build or device write occurred. The single next ordered action is
to publish this frozen candidate, install it once to live-GPT-resolved inactive
boot2 with full readback and clean shutdown, then pre-arm the exact provider
collector before one physical selection. See the
[offline validation](../experiments/2026-08-17-mainline-da921x-readonly-provider-baseline/results/offline-candidate-validation-20260817.txt).

Guarded deployment is now complete. Live GPT resolved inactive, unmounted
boot2 as p30 while Gemian used p29. The predecessor checksum was recorded
without a fresh backup; stable external power, exact write, sync, flush,
full-partition readback, temporary-readback cleanup, and clean shutdown all
passed. The device was not rebooted and is confirmed unreachable. See the
[deployment receipt](../experiments/2026-08-17-mainline-da921x-readonly-provider-baseline/results/deployment-1-20260817.txt).

The single observed attempt is a confirmed positive. Exact
`7.1.3-gemini-da921x-lkro` reached the pre-armed USB/netcat collector with
CPUs 0--7 online and CPUs 8--9 closed. The LK-devinfo handoff passed late
validation, I2C6 reached ready through its existing access-controller edge,
and one DA921x bound record reported 14 identity reads, two providers, four
completed provider reads, internally consistent selector/voltage/enable
tuples, and zero register-data writes. USB, I2C5/AP-DMA, AW9523, the polling
keyboard, tty1, watchdog, and native reboot remained serviceable. Changed-ID
Gemian recovery found empty pstore and the exact candidate still unmounted on
boot2. See the [runtime result](../experiments/2026-08-17-mainline-da921x-readonly-provider-baseline/results/runtime-attempt-1-success-20260817.txt).

The initial host classification stop was a false negative after the complete
capture: the USB prompt shared the begin-marker line and the procfs keyboard
probe used a driver-like name instead of the exact `keyboard-matrix` input
name. The repaired classifier preserves unique marker spelling and requires
the exact dmesg registration, polling, binding, and event-node records; the
immutable capture passes. This correction does not change or repeat the device
observation.

Combined with the already-passing five-case observer KUnit suite and the prior
natural zero-transaction identification unbind/rebind lifecycle, the required
read-only bind, failure/cleanup, no-write, and serviceability evidence is
closed. The provider-enabled runtime itself ended through native reboot rather
than a provider unbind, so it establishes no provider-enabled lifecycle
repeatability claim.

Required evidence:

- provider registration performs no register-data write;
- current selector, enable, and constraint reporting is internally consistent;
- bind/unbind and failed-probe cleanup preserve the original state;
- console, keyboard, USB, I2C5/AP-DMA, CPU0–7, and native reboot remain intact.

Test resume in a separate experiment; a successful boot does not establish
resume ownership.

Exit: a provider can exist without changing hardware state.

Exit met on the named unit and exact revision. Do not repeat this artifact.
Gate 6 below records the later bounded no-op completion; CPU8/CPU9 admission
remains closed until Gate 7.

### 6. Prove one bounded writable operation — complete

Gate 6 closed on 2026-08-20 for the reviewed no-op operation. This does not
authorize a changed-value transition, writable consumer, rail enable/disable,
or CPU8/9 request.

The [initial Gate-6 design review](../experiments/2026-08-17-mainline-da921x-bounded-noop-write-review/README.md)
selects the least-invasive future transaction: one no-retry same-value write
of `0x46` to disabled Buck B's unselected `VBUCKB_B` register `0xda`, followed
by immediate/delayed readback and full pre/post comparison. It explicitly
performs no build or hardware action. At review time, implementation was
blocked by firmware-writer exclusion, the native one-message two-byte write
shape, two unattributed Gate-5 transfers, and absent live `V_LOCK`/status
preflight.

The read-only I2C6 entry-ledger and DA921x direct-register-preflight candidate
was frozen offline. Buildbox built exact clean commit `f2837f05083b...` as
`7.1.3-gemini-da921x-preflight`; package checksums pass and no native VM build
ran. Two independent Android-v0 constructions and padding paths are
byte-identical, all 32 LK/container gates pass, and twelve independent DT
mutations are rejected. The exact 16 MiB boot2 payload is
`41c652225d3627f5aaaba2272e29a58171008e17b0f7c936116842e7ab0166e3`.
It can only attribute the 30 expected startup reads and test two stable
read-only preflight passes; it adds no register-data write, writable provider
operation, consumer, firmware-owner claim, or CPU8/CPU9 request. Guarded
deployment then resolved inactive, unmounted live-GPT `boot2` as p30 while
Gemian used p29. The exact write, sync, flush, full readback, and clean shutdown
passed without a fresh backup or automatic reboot. The checksum-pinned
read-only collector and classifier were validated against one complete
30-entry fixture and eight unsafe mutations.

The automatic-preflight candidate's one permitted runtime attempt is complete
and stopped. A collector
published and armed before selection observed MT65xx preloader attach/detach,
but no exact mainline USB gadget, fixed-MAC interface, or netcat endpoint. The
later `0fce:7169` device was changed-identity Gemian returning; no collector
command was sent. Pstore was empty, and inactive, unmounted live-GPT p30 still
matched exact payload `41c652225d36...`. No I2C6 ledger or preflight value was
captured, so that candidate closed none of B1--B4. See the
[runtime result](../experiments/2026-08-17-mainline-da921x-readonly-preflight-ledger/results/runtime-attempt-1-no-mainline-usb-20260818.txt),
[deployment receipt](../experiments/2026-08-17-mainline-da921x-readonly-preflight-ledger/results/deployment-1-20260818.txt),
[collector pre-arm receipt](../experiments/2026-08-17-mainline-da921x-readonly-preflight-ledger/results/collector-prearm-validation-20260818.txt), and
[offline candidate record](../experiments/2026-08-17-mainline-da921x-readonly-preflight-ledger/results/offline-candidate-validation-20260818.txt).

Do not repeat either exact artifact. The runtime-triggered read-only successor
reached the inherited serviceability boundary, durably classified the exact
20-entry startup ledger, accepted one checksum-pinned trigger, and added the
expected ten reads. Two stable samples observed `CONTROL_A=0x7b` with
`V_LOCK` clear, record-only `STATUS_B=0xc1`, disabled Buck B, and both selector
bytes at `0x46`. The final 30-entry ledger had zero overflow and zero
write-only, register-data-write, other-shape, or other-address transfers.
Read-only sysfs restoration, CPUs 8--9 offline, and one native return to
changed-identity Gemian also passed. This closes B3 exact transfer attribution
and B4 stable safe prestate only; see the
[finalized runtime result](../experiments/2026-08-18-mainline-da921x-runtime-preflight-ledger/results/runtime-attempt-1e-finalized-20260818.txt).

The first B1 read-only attestation candidate completed one attributable
runtime attempt and failed its frozen compound gate closed. It observed SCP
reset control `0` twice and debug PC `0xfffffffe` twice; the stable AP-visible
Device-APC AO permission/master words were all zero and control was `1`.
Because the original predicate also required PC zero and decoded domain 1
permission `3`, it faulted before stopped-DVFSP validation, created no DA921x
client, made zero I2C6 transfers and register writes, then performed its
predeclared native return to changed-identity Gemian. Pinned public source
shows reset-control zero is the asserted-reset state and one releases SCP;
the source names the PC register but does not support zero as its reset value.
The AP-visible all-zero AO view is retained as a diagnostic, not promoted to a
secure-policy observation. Preserve this result and do not repeat the exact
artifact; see the
[runtime record](../experiments/2026-08-18-mainline-i2c6-firmware-writer-attestation/results/runtime-attempt-1-failed-closed-20260819.txt)
and [contract correction](../experiments/2026-08-18-mainline-i2c6-firmware-writer-attestation/results/runtime-attempt-1-contract-correction-20260819.txt).

The corrected B1 transaction-window successor completed one exact read-only
runtime and passed. SCP reset control was zero in both pre-handoff samples;
debug PC `0xfffffffe` and the all-zero AP-visible Device-APC view remained
record-only diagnostics. Stopped-DVFSP reached ready with late validation
passed and zero faults. Reset control remained zero at all 20 transfer entries
and 20 exits, and the exact 20-entry pointer/read ledger completed with zero
overflow, failure, write-shaped, foreign-address, or other traffic. The
provider retained 14 identity reads, four provider reads, and zero register-
data writes; CPUs 8--9 and serviceability closures held through the planned
native return to changed-identity Gemian. Combined with the retained firmware
audits and disabled mainline SCP driver/node, this closes B1 on the named unit
and exact revision. Preserve and do not repeat the artifact; see the
[runtime result](../experiments/2026-08-18-mainline-i2c6-firmware-writer-transaction-window/results/runtime-attempt-1-success-20260819.txt).

The hardware-free
[B2 write-transport proof](../experiments/2026-08-19-mainline-i2c6-write-transport-kunit/README.md)
now passes. The exact production-coupled one-message two-byte FIFO plan,
completion and error classes, no-retry root-lock wrapper, retry restoration,
and lease-result precedence compiled on Buildbox and passed all 12 focused
arm64 QEMU cases with no failure or skip. No Gemini device, DA921x address, or
physical I2C transaction was involved. This closes B2 only.

B1--B4 now each have named closure evidence. The fresh explicit
[same-value-write preflight review](../experiments/2026-08-19-mainline-da921x-same-value-write-preflight-review/README.md)
reconciles their exact receipts and closes the historical design-only hold. It
freezes five exact preflight reads, one `0xda: 0x46 -> 0x46` write,
immediate/delayed target readback, and four full-byte poststate reads. Those 12
actions exactly consume the remaining 32-entry ledger capacity. One root-
adapter lock must cover an under-lock recheck of the retained 20-entry prefix
through the last action or first failure; retries remain zero and are restored
on every exit. Because the old ledger records only the register pointer, the
successor must attribute both `0xda` and data byte `0x46` in its sole
write-shaped entry.

The default-off implementation and its hardware-free proof now pass. Canonical
patches 0290--0292 build from exact clean pushed commit `7c012d736f78...` as
production release `7.1.3-gemini-da921x-same-write`; the focused six-case QEMU
suite covers every transfer and value-mismatch ordinal. The production package
has KUnit disabled. Two independent Android-v0 constructions and two 16 MiB
padding paths are byte-identical at raw `b84f3ba8d86e...` and padded
`b81813d13acc...`; all 32 LK gates pass and eight semantic DT mutations are
rejected. The checksum-pinned collector preserves the exact 20-entry pretrigger
ledger before one token, permits no retry or second write, accepts success and
both bounded terminal failure families, and requests native reboot only after
durable terminal classification. Its classifier rejects thirteen runtime
mutations, including moving attribute writability outside the bounded
read-write sysfs window.

No device or physical I2C transaction was involved in those production,
candidate, or collector validations. Their sanitized predeployment evidence
was published at signed commit `b1d251abc081`. The guarded deployment then
passed exact known-good-OS, stable-power, inactive-target, predecessor, write,
sync, flush, remote checksum, independent 16 MiB readback, and byte-comparison
gates. Live GPT resolved unmounted `boot2` as p30 while Gemian root remained
p29; the predecessor was recorded without a fresh backup, and the device shut
down cleanly without rebooting.

The exact candidate was selected once and reached its named release, USB shell,
keyboard, and CPU0--7 serviceability baseline. The original collector had
expired before physical selection and contained no pretrigger or token entry;
the unchanged collector was therefore re-armed on the same live boot. Six
retained read-only probes consistently found zero `*-0068` I2C clients and
stopped before an action attribute, accepted pretrigger ledger, or trigger
token. Thus no physical DA921x write was attempted. A native USB-shell reboot
returned to changed-identity Gemian; pstore was empty, CPU8/9 remained offline,
and live-GPT boot2 still matched the exact candidate. Preserve this
failed-closed result and do not repeat the artifact. Offline localization found
a DT/kernel resource-contract mismatch: that candidate had only the CSPM
handoff window, while the selected kernel required named `scp-cfg` and
`devapc-ao` windows before it could release I2C6 and instantiate the DA921x
client.

The DT-only repaired successor restored those already proven windows without
changing the kernel, ramdisk, configuration, or LK contract. Its guarded
deployment passed full boot2 readback. On one selected boot, the exact
20-entry idle ledger and firmware-writer transaction window passed; one token
then produced the exact 12-action suffix. Ledger entry 25 was the sole
one-message write to address `0x68`, with payload `[0xda, 0x46]`, return value
one, and completion set. Preflight was `7b,c1,00,46,46`, immediate and delayed
target readback were `46`, and poststate was `7b,c1,00,46`. The final ledger
was 32/32 with zero overflow, failure, foreign address, retry, second write,
`PAGE_CON` access, consumer request, or CPU request; transaction entry and exit
checks were both 32 with reset failures zero. CPUs 0--7 remained online and
8--9 remained offline. A source-backed host-classifier correction recognized
that the legacy oracle counts the sole write as its sole non-combined transfer;
the immutable capture then passed, and native return reached changed-identity
Gemian with empty pstore and boot2 unchanged. See the
[runtime result](../experiments/2026-08-20-mainline-da921x-same-value-dt-contract-repair/results/runtime-attempt-2-success-20260820.txt)
and [classifier correction](../experiments/2026-08-20-mainline-da921x-same-value-dt-contract-repair/results/classifier-oracle-correction-20260820.txt).

The first writable test must:

- keep CPU8 and CPU9 disconnected;
- request one predeclared no-op or bounded state transition;
- read back the exact affected state;
- restore the starting state or execute the reviewed rollback;
- stop immediately on any mismatch;
- retain an independent reboot/recovery path.

Exit met: one exact same-value write/readback protocol retained the starting
state by construction and observation. This is not yet an active rail
transition or A72 support. Preserve it and do not repeat it.

### 7. Bring up CPU8

Request CPU8 only after the external provider, SPM/SRAM, clocks, CCI, PSCI,
error handling, and recovery sequence are all represented.

The immediate next action is an offline Gate-7 admission audit. Reconcile the
newly closed I2C6/DA921x no-op boundary with the retained natural-owner cycle,
pre-isolation rollback, one-way CPU8 startup, held-online execution, secure
CPU-off attribution, and safe-off contract. Freeze which production-mainline
owners, state predicates, checkpoints, timeouts, and inverse operations already
have evidence and identify any still-missing prerequisite before changing the
kernel or spending another device boot.

That [Gate-7 admission audit](../experiments/2026-08-20-mainline-cpu8-gate7-admission-audit/README.md)
is complete. It separates twelve boundaries and rejects immediate current-
mainline CPU8 admission. The mainline same-value runtime closes the exact I2C6
short-write shape, while the isolated A72 provider acquire and release
callbacks still deliberately return structured `-EOPNOTSUPP` before any vote
or mutation. Historical named-unit evidence confirms Buck B can enable,
settle, and restore before isolation and that CPU8 can reach online and bounded
execution, but those Gemian-derived implementations are not current Linux 7.1
owners. P28 remains a dormant effect ledger, A41 is partial, no positive
P24/P30 production caller exists, and the A26/A14 vetoes remain required.

The next ordered implementation is hardware-free: add one isolated,
default-off positive DA921x Buck-B acquire/release state machine behind the
existing provider-owner seam. It must freeze the exact full-byte prestate,
hold one root-adapter lock per complete acquire or release, force zero retries,
retain the stopped-firmware edge checks, perform the exact `BUCKB_CONT 0x00 ->
0x01` transition and 1 ms settled readback, return a generation-bound handle,
and admit the exact owned `0x01 -> 0x00` inverse with full-state restoration.
The lock must not span the handle lifetime. Every transfer/failure ordinal
requires hardware-free coverage. `PAGE_CON`, selector writes, consumers, P28,
CPU_ON, CPU_OFF, boot images, and device actions remain closed. Commit and push
the reviewable source before the required Buildbox-only compile and focused
test run.

That [positive-provider implementation](../experiments/2026-08-20-mainline-da921x-positive-provider-transaction/README.md)
has now produced canonical hardware-free patches 0293--0295. The frozen design uses eleven
transfers for acquire and eleven for release, binds the handle to the exact
transaction generation and cookie, treats `STATUS_B` as record-only, and
stops ambiguous write outcomes in a terminal fault-retain/reset-only state.
The cumulative source review also found that the release-refusal function is
present but its ops-table member was lost by a later patch; an independent
first patch restores that intended registration before the positive change.
Buildbox semantic, patch, replay, and strict style validation pass with zero
findings; isolated source and KUnit profiles retain the stopped-firmware window
and disconnect every CPU caller. The exact KUnit profile also compiles and
links on Buildbox. One bounded, network-free fake-adapter QEMU run at exact
repository revision
`43099ac1dcfa5da1fa0bb3bd4a8b9de71f033f50` passes all six focused cases with
zero failures or skips. This closes the hardware-free positive-provider
implementation proof only; no physical transition, CPU request, boot image, or
device action occurred.

The separate
[Gate-7 integration review](../experiments/2026-08-20-mainline-cpu8-gate7-integration-review/README.md)
is complete and rejects direct P28 or CPU8 integration. Current source can
publish a successful positive acquire as `HELD`, but any other returned
positive acquire outcome lacks an explicit owner fault terminal. More
importantly, CPU8-up has no membership-owned exact release for a successful
vote when the transaction stops before P28, and P29 can retire only the old
before-vote refusal. P27/P28 remain attestation ledgers, A41 cannot publish
READY, P24/P30 still have no production caller, and A26/A14 remain required.

The next ordered implementation is the smallest default-off, hardware-free
production-seam slice: map every returned non-refusal acquire error or invalid
success to `FAULT_UNKNOWN`/transaction `FAULT`; add one CPU8-up-only pre-P28
abort budget; publish `RELEASE_INFLIGHT` before exact-handle release; accept
only the complete positive release response; and let P29 retire the P27 prefix
only after either the existing refusal or the new exact positive-abort proof.
Its focused KUnit test must traverse the production provider registry and
positive DA921x transaction on an unregistered fake adapter. The lifecycle
owner stays closed with no production caller. P27/P28 hardware effects,
physical DA921x execution, CPU_ON/OFF, boot images, and device access remain
closed.

The
[pre-P28 provider-abort experiment](../experiments/2026-08-20-mainline-da921x-pre-p28-provider-abort/README.md)
owns that implementation. Its first four deterministic patches cover acquire
fail-stop mapping, exact positive abort/P29 admission, the injectable production
DA921x callback endpoint, and focused registry integration tests. Buildbox
generated and strictly validated them, and the focused compile passed. The
first QEMU run stopped before provider semantics because large automatic test
state overflowed the arm64 kernel stack. Separate one-file follow-up patch
`0300` now strictly validates and is pinned at the end of the canonical series;
it moves that state to KUnit-managed heap storage without changing production
code. The distinct stack-safe Buildbox/QEMU attempt reached all six families:
five passed, while malformed release-response mutation 1 showed that the abort
wrapper did not validate the provider callback ABI before constructing its
internal proof. Mutations 2--14 were rejected. The next ordered action is one
pinned fail-closed patch requiring the canonical provider-call ABI before
confirmation. Canonical patch `0301` now implements and strictly validates
that four-line condition from the exact tree through `0300`. The distinct
focused Buildbox/QEMU proof now passes all six families with zero failures or
skips, including every malformed acquire/release response and the exact
positive abort/P29 path. This closes the hardware-free pre-P28 provider inverse
but does not make the lifecycle owner, P28, CPU_ON, or CPU8 admission reachable.

The next ordered action is a fresh Gate-7 remaining-boundary audit against the
canonical tree through `0301`. It must identify the smallest independently
testable step among the still-closed lifecycle opener/caller, P28 effect
executor, A41 READY completion, and P24/P30 request path, and must reject a
physical provider write or CPU8 boot until the selected boundary has its own
attributable evidence and fail-closed recovery rule.

That
[remaining-boundary audit](../experiments/2026-08-20-mainline-cpu8-gate7-remaining-boundary-audit/README.md)
is complete. It re-derives the dependency order from the exact Buildbox source
through patch `0301` and rejects the apparent A41 shortcut: the selected
non-fixture profile has no CPU8/CPU9 target observations, returns `-EAGAIN`
from both preparation and validation, and cannot form a plan identity. P28 is
also not independently admissible because P27/P28 remain attestation ledgers
without current-mainline effect executors and inverses. The P24/P30 caller is
downstream of both boundaries plus A36, P30E/P32, and A26 review.

The audit's fidelity review found one earlier boundary: frozen P13/A34 requires
a known-good platform or external reset plus owner-safe private replay-zero
proof, explicitly not an ordinary Linux reboot assumption. The reset and
bootstrap owners remain unresolved. A boot-time caller based only on software
zero state would therefore open the lifecycle without its required authority.

Canonical patch `0302` now implements the smallest honest separable part of
A34: a default-off, pure eligibility evaluator with no production caller or
state transition. Its immutable input includes explicit non-default reset
provenance and private replay-zero proof, both A72 CPUs present, possible,
offline, CPUHP-consistent, and non-aliased at MPIDRs `0x200` and `0x201`, plus
empty membership/provider/controller/transaction/fault/P30 state. The exact
Buildbox profile compiled, and its sole five-case QEMU suite passed both reset
provenance positives, null input, every-byte mutation rejection, missing
provenance rejection, and unchanged CLOSED admission with zero failures or
skips. A positive result still means only “eligible”; it does not initialize
attempts or open the `CLOSED / UNINITIALIZED` state. No transaction caller,
provider call, P27/P28 effect, P30 arm, PSCI call, CPU_ON/OFF, boot-veto change,
boot image, or device action was added.

The
[production A34 provenance-owner audit](../experiments/2026-08-21-mainline-a72-a34-provenance-owner-audit/README.md)
resolves the first observation boundary without pretending it is complete
authority. Pinned LK has a raw TOPRGU `WDT_STATUS` reader but no caller and no
write to that register; mainline can therefore capture offset `0x0c` once
after resource mapping and before `mtk_wdt_init()`. The audit also identifies
the exact secure payload's private A72 replay byte as zero in the image, with
CPU_ON as its set writer and deferred secure teardown as its clear writer.
That proof is owner-safe only for a proven fresh secure-platform epoch. Raw
TOPRGU status, Linux zero state, an active `AFFINITY_INFO` call, or an ordinary
Linux reboot cannot supply A34 authority alone.

The next ordered boundary is one default-off, capture-only patch in the
existing MediaTek watchdog owner. It must store exactly one raw 32-bit status
word plus explicit validity before watchdog initialization, expose only a
typed read-only snapshot, and test invalid, exact, every-bit, and immutable
behavior without MMIO. It must add no reset classifier, ram-console mapping,
A34 production caller, lifecycle publication, provider action, P30 arm, PSCI
call, CPU veto change, boot image, or device action. After that independent
capture is proven, audit a strict retained-ram-console reader and the
cold/platform-epoch combiner before implementing the production A34 owner.

Canonical patch `0303` now implements and closes that capture-only boundary.
Its exact Buildbox generation, replay, semantic validation, strict style,
cross-compile, and link checks pass. The sole network-free QEMU suite passes
invalid, exact, every-bit, and second-capture immutability with zero failures
or skips and without a production MT6797 device or MMIO access.

The
[retained-ram-console authority audit](../experiments/2026-08-21-mainline-retained-ram-console-authority-audit/README.md)
now freezes the common 64-byte header, exact record chaining, raw preloader
status location, and strict corruption behavior. It confirms that a pure
caller-buffer parser is separable, but rejects the currently known preloader
status, LK boot reason, raw TOPRGU status, or their combination as proof of a
fresh secure-platform epoch. The complete public preloader enum/writer is
unavailable, zero means only LK's normal-boot category, and the optional
full-PMIC bit is not enabled by the public target configuration.

Canonical patch `0304` now implements that default-off, hardware-free retained
ram-console parser. Its fourth exact Buildbox generation passed source
semantics, one-patch inventory, byte-for-byte replay, and strict style after
three preserved alignment-only rejections. It validates all prefix arithmetic
and exact current/prior preloader and LK chaining, returns only the complete raw
current-preloader status plus validity, rejects the legacy fixed-offset
fallback, and contains eight focused corrupt, exact, and every-bit KUnit cases.
It adds no reserved-memory lookup, physical mapping, reset classifier, A34
caller, lifecycle publication, provider action, P30 arm, PSCI call, CPU veto
change, boot image, or device action.

The exact patch `0304` Buildbox profile now compiles and links. Its sole bounded,
network-free QEMU suite passes all eight cases with zero failures or skips and
the exact corrupt, chaining, raw-word, and every-bit inventory. This closes
only the pure caller-buffer parser boundary.

The next ordered boundary is an audit of the immutable physical mapping/copy
owner and, separately, independent secure-epoch attestation. Do not implement a
mapping, classifier, or production A34 caller until those authority contracts
are frozen, and do not manufacture authority by combining correlated reset-
history fields.

That
[copy-owner audit](../experiments/2026-08-21-mainline-retained-ram-console-copy-owner-audit/README.md)
is now complete. Linux 7.1.3 `no-map` handling, arm64 `memremap()` semantics,
OF platform population, and pinned LK/vendor writer ordering select one normal
default-off platform consumer with a sole `memory-region` reference. It must
require the exact 64 KiB `no-map` reservation, make one transient
`MEMREMAP_WB` mapping, copy the entire region once, unmap before parsing, and
publish only the immutable typed raw snapshot. Current mainline through `0304`
has no physical writer; any future writer invalidates that ordering unless it
is explicitly sequenced behind the copy. A direct reserved-memory child,
generic NVMEM provider, magic physical address, persistent mapping, direct
physical parse, retry, and raw export are rejected.

The same audit found no new independent secure-epoch input. LK completion and
all known ram-console, TOPRGU, boot-reason, or manually described cold-looking
boot observations remain reset-path evidence, not attestation that the exact
secure payload initialized private replay state in the current epoch. The
combiner and production A34 owner remain closed.

Canonical patches `0305`--`0307` now implement that selected default-off
mapping/copy owner, binding, and disabled Gemini DT consumer. The exact
Buildbox profile compiles and links the kernel and Gemini DTB, packages all 119
DTBs with validated checksums, and exposes the expected typed getter and seven
test cases. Its sole bounded, network-free QEMU suite passes all seven
injected-memory cases with zero failures or skips, including exactly one
copy/publication, failure invalidation, second-capture refusal, source
independence, and every-bit preservation. The production physical mapping
remains unexecuted because the consumer is disabled. The targeted binding
schema check is explicitly not run because Buildbox lacks `dtschema`; its
structural experiment validator and strict checkpatch passed.

This closes the immutable copy transport only.

The
[secure replay epoch audit](../experiments/2026-08-21-mainline-secure-replay-epoch-audit/README.md)
then closes the private replay initialization half of A34. Both retained
preloader boot regions are byte-identical, both retained TEE slots contain the
same exact secure payload, and the regular preloader path loads `tee1` with a
`tee2` fallback before ATF handoff. Most importantly, primary BL31 entry calls
an explicit zero helper over `[0x11d340, 0x122acc)`, which contains the private
A72 replay ledger at analysis address `0x11ea24`. The helper performs paired
zero stores plus a byte tail; the result does not depend on image padding,
DRAM loss, Linux zero state, or preserved ATF logs. A26 prevents the only
pre-A34 set writer.

This proof is conditional on separately established platform/external-reset
provenance. It does not accept ordinary Linux reboot, add a kernel-visible
secure-image measurement, or promote correlated ram-console, TOPRGU, and LK
boot-reason fields into authority. The next ordered boundary is therefore a
strict platform/external reset-classifier audit using the already implemented
immutable TOPRGU and retained ram-console snapshots. It must prove reset to
the regular preloader/primary-BL31 path and sufficient recovery of every A34
hardware/cross-owner prefix, reject unknown or contradictory values, and add
no production caller. Until that classifier is frozen and proven, the
production A34 owner, lifecycle opener, CPU8 request, boot image, and device
attempt remain closed.

That
[platform-reset classifier audit](../experiments/2026-08-21-mainline-platform-reset-classifier-audit/README.md)
is now complete, with no admissible positive result from the current inputs.
Exact private-preloader analysis proves that the retained preloader status is
a lossy projection of the same raw TOPRGU status already captured by patch
`0303`; agreement is therefore correlated by construction. The preloader does
have a stronger power-off/on classifier: raw status zero plus entry-time
`INTERVAL[1:0] == 3` produces private class `4`. But the retained writer does
not receive that class, preloader and pinned LK both overwrite the interval
before Linux, and LK exports neither its private Boolean nor the original
value. A direct read-only access to the analyzed preloader cell stalled
known-good Gemian before returning data and is permanently rejected. Changing
LK would cross the separate bootloader-partition contract and is not the next
boot2 kernel step.

Do not implement a reset-cause classifier with a manufactured raw-zero
positive. The next ordered boundary is an audit of direct, immutable A34
recovery-state attestation. It must determine whether owner-safe observers can
prove the complete exact recovered tuple—external DA921x Buck B, SPM power/
reset/isolation/SRAM state, TOPRGU PWRAP reset, protected clocks, CCI/DCM,
CPU8/CPU9 physical and generic state, the proven BL31 replay clear, and the
complete empty Linux owner tuple—without relying on reset cause. Any missing,
mutable, unsafe, or contradictory prefix keeps A34 closed. No implementation,
build, boot image, or device attempt follows until that audit is complete.

That
[direct recovery-state attestation audit](../experiments/2026-08-21-mainline-a34-direct-recovery-state-audit/README.md)
is now complete. The exact historical first natural CPU8 cycle supplies a
coherent direct-state reference: its pre-attempt and post-off DA921x,
six-word SPM, twelve-word secure, protected-clock, and MP2 DCM observations are
identical. Current mainline does not yet have a complete positive tuple. Its
DA921x snapshot is private to a provider transaction, its A72 power observer
is a stale probe-time subset whose Gemini DT node is deleted, TOPRGU has no
reset-state getter, the protected readers remain disabled and uncomposed, and
MT6797 has no A72 CCI description or state source. The current A34 ABI also
contains no hardware tuple or production collector. Do not use the old
caller-supplied A36 constants as observations.

The
[A72 CCI and platform-state ownership audit](../experiments/2026-08-21-mainline-a72-cci-platform-state-owner-audit/README.md)
is now complete. It identifies MP2 CCI port control at `0x10396000` and the
sole global change-pending word at `0x1039000c` bit 0. It explicitly corrects
the older `0x1039600c` effect row, rejects the generic five-port ARM CCI-400
driver as MT6797's owner, and pins the A72-relevant SPM, TOPRGU PWRAP, and MP2
DCM fields. The selected source is read-only and default-off. Its local lock
cannot serialize secure PSCI; that exclusion remains the later transition
owner's responsibility.

The default-off capture-only source is now generated as four logical patches
and admitted canonically through `0311`; exact Buildbox replay, semantic
validation, strict checkpatch, isolated arm64 compilation, Gemini DTB
generation, and package checks passed at commit `aa7dc4f`. The node remains
disabled. This closes capture-source construction, not runtime ownership.

The fresh read-only DA921x provider-state export is now admitted canonically
through `0315`. Exact Buildbox generation, replay, strict checkpatch, isolated
arm64 compilation, package validation, and a hardware-free QEMU run all pass.
The run exercised exactly four new stable-snapshot cases and six inherited
provider-transaction cases with zero failures or skips. The export remains a
transaction-local observer: it performs two immediate five-register samples,
does no write or delay, adds no A34 consumer, and does not open either CPU
veto. See the
[DA921x provider-state experiment](../experiments/2026-08-21-mainline-da921x-provider-state-export/README.md).

This closes the provider-export prerequisite, not runtime ownership. The next
ordered work is:

The
[protected-readback firmware audit](../experiments/2026-08-21-mainline-protected-readback-firmware-audit/README.md)
now confirms that the BigiDVFS read FID, address window, four selected words,
and return convention match the exact live TEE payload. It also rejects a
device run with the two current transports: patch `0197` omits the recovered
200 ns settle between successful semaphore acquisition and the first
MCUMIXED read, while patch `0198` can leave a partial caller record and does
not reject a four-call sample that changes mid-observation.

The
[protected-readback remediation](../experiments/2026-08-21-mainline-protected-readback-remediation/README.md)
is now complete through patch `0319`. Both transports publish only complete
stable records, the recovered 200 ns clock settle is enforced, and the exact
six-case hardware-free suite passes with no failures or skips. Both device
nodes remain disabled and no owner or CPU admission is opened.

The isolated protected-readback observer now has an exact Buildbox kernel and
candidate DTB at commit `1bd49d9`. Package provenance, configuration, linked
symbols, and a decompiled DTB comparison pass offline: the derivative changes
only the model label, enables the two read-only backends, and adds the one-shot
observer. This is build evidence, not runtime evidence, and no device action
was justified by it alone.

The exact Android-v0/LK candidate was assembled and independently validated,
both live TEE identities matched the audited payload, and guarded logical
`boot2` deployment had a matching full-partition readback followed by confirmed
shutdown. Its one physical selection returned to changed-boot-ID Gemian before
the pre-armed collector saw mainline USB. No reboot command was sent, pstore and
`last_kmsg` were empty, and post-cycle `boot2` still matched exactly. The
watchdog-block boot-reason token does not distinguish expiry from a direct
TOPRGU reset. Therefore neither protected reader is yet attributed; the exact
artifact is rejected as `inconclusive-pre-transport` and must not be repeated.
See the [runtime result](../experiments/2026-08-21-mainline-protected-readback-runtime-observer/results/runtime-attempt-1-inconclusive-pre-transport-20260821.txt).

Read-only Gemian recovery found the four final retained dmesg-zone headers at
`0x444bb000`--`0x444be000` valid and empty. The next candidate may therefore
add exactly two independently recoverable records: one immediately before the
protected-clock read and one after it returns but before BigiDVFS. That prefix
separates observer-not-entered, clock-read-nonreturn, and later failure without
adding another protected read or repeating a measurement-identical artifact.

That successor is now admitted canonically as patch `0323`. Deterministic
Buildbox generation, source semantics, byte-identical replay, strict style, the
104-profile series audit, and eight invariant mutations pass. Manual review
also corrected a stopped pre-LK model assumption to the runtime-proven
`MT6797X` fingerprint before admission. The exact isolated Buildbox build at
commit `36027e9` now passes, as do two independent Android-v0 assemblies, two
padding paths, all 32 LK gates, and six negative container mutations. The DTB
and initramfs remain byte-identical to the predecessor. Exact full-`boot2`
candidate `3ce494c971c24c9edab73aac592d0ba8dd0bbd25f06051245f7846f95d0c715a`
is offline-valid. Guarded deployment resolved inactive, unmounted live-GPT
`boot2` as p30 while Gemian used p29. The first write passed its device-side
full checksum but a changing final power sample stopped the run before the
independent readback and shutdown. A resumed pass found the exact candidate,
skipped rewriting it, repeated all gates, independently streamed and compared
the full 16 MiB, and confirmed clean shutdown. Runtime attribution remains
limited to the retained decision prefix.

On its one physical selection, mainline USB never appeared and changed-boot-ID
Gemian recovered automatically. Pstore, `last_kmsg`, both fixed records, and
all sampled retained payload bytes were empty; the four headers remained valid
and zero-length, and inactive `boot2` still matched exactly. This is a strict
`neither` result: neither protected transport was reached, so no transport
failure may be inferred. Reject this artifact without repetition. The first
remaining boundary is observer probe entry versus refusal by the exact ledger
gate.

The non-identical probe/gate successor is now admitted canonically as patch
`0324`. Its default-off mode preserves the historical call-ledger profile while
moving the same two records to probe entry and the full pre-call gate. Its exact
isolated Buildbox kernel and independently validated Android-v0/16 MiB candidate
passed offline. Guarded deployment then resolved inactive live-GPT `boot2` as
p30 while Gemian used p29, replaced exact predecessor `3ce494c9...715a` with
`6cb729ef...2e62`, matched the full readback, and confirmed clean shutdown.

One physical selection returned automatically to changed-boot-ID Gemian.
Immediate recovery found empty pstore, both owned headers valid-empty, both
120-byte record regions still erased, the known generic 74-byte `last_kmsg`
header, and exact unchanged `boot2`. The USB collector was rearmed only after
selection began, so its negative window is not primary evidence. The retained
result is nevertheless strict `neither`: observer entry or its minimal
gate/mapping/write path was not established, and neither protected call was
reached. Reject patch-0324 candidate `6cb729ef...2e62` without repetition.

The linked-image/source audit places clock-backend registration, BigiDVFS-
backend registration, and observer registration consecutively in device-
initcall order. The missing record was the observer probe's first operation.
The next discriminator must therefore move before the observer and must not
call either transport.

The isolated clock-backend-entry successor is now complete. It kept the
observer and BigiDVFS disabled, made zero protected calls, and recorded before
clock-backend registration and at probe entry. Its exact candidate passed
Buildbox, independent container validation, guarded deployment, full readback,
shutdown, and one physical selection. Changed-ID Gemian recovered empty
pstore, four exact empty retained slots, the known generic `last_kmsg`, and the
unchanged candidate. The strict result is `neither`: driver init was not
established, or the shared exact-DT/reservation/prefix/map/write path refused.
Do not repeat it. See the
[clock-backend entry result](../experiments/2026-08-21-mainline-clock-backend-entry-ledger/results/runtime-attempt-1-neither-20260821.txt).

The observation-path audit is complete. The exact DT predicates and linked
initcall are present, and arm64 permits the selected mapping because the
reservation is `no-map`. What remains unproved is the manual checkpoint's live
success and cross-version recovery. The selected control reuses the exact
Image, configuration, and initramfs while switching only to the package's base
DT, which disables the clock node. Exact USB plus the live platform-driver
directory positively proves the first checkpoint and registration without
depending on returned empty RAM. See the
[clock-entry observation control](../experiments/2026-08-21-mainline-clock-entry-observation-control/README.md).

That control is now complete and stopped. Its exact collector was armed before
the single physical selection, but no mainline USB interface appeared before
an automatic changed-boot-ID Gemian return. Immediate recovery found empty
pstore, all four retained slots byte-identical to the known empty image, the
known generic `last_kmsg`, and exact unchanged boot2. Disabling the clock node
therefore did not restore serviceability; it does not establish driver init or
checkpoint success, and the exact artifact must not be repeated. The next
boundary moves back to a non-identical current-tree serviceability control with
the experimental clock-entry writer disabled and the last successful DA921x
same-value DT resource contract retained.

That control is now built from exact clean pushed commit `27622df` on
Buildbox and independently validated offline. Its Image omits the clock-entry
writer and same-value action, while its DT restores the proven three-window
handoff and USB/keyboard serviceability contract. Candidate
`7084f2ee...d52a3` passed all 32 LK gates and rejected 15 negative DT
mutations. This admits one guarded installation and one runtime attempt; it
does not yet establish serviceability. Guarded deployment has now replaced
the exact stopped predecessor on inactive live-GPT boot2, matched the full
16 MiB readback to `7084f2ee...d52a3`, and confirmed clean shutdown. The next
action was to arm the exact observer before the one physical selection.

That single selection passed. Exact USB appeared with release
`7.1.3-gemini-service-ctl`, CPUs 0--7 online, CPUs 8--9 offline, keyboard and
one DA921x client present, and the same-value attribute plus clock, BigiDVFS,
and protected-readback devices absent. A missing newline after the DT model
field caused the first classifier invocation to reject attribution and withhold
reboot. The offline-tested formatting correction reran on the same mainline
boot, passed the exact oracle, and only then sent one native reboot. Changed-ID
Gemian returned and boot2 remained exact. This restores the current canonical
tree and proven DT as a trustworthy serviceability foundation while localizing
the stopped clock-entry lineage to its experimental writer/configuration
boundary. It does not validate the cross-version retained checkpoint path.

The selected next discriminator is the default-off
`da921x-manual-checkpoint-control` profile. On that exact serviceability-proven
base, canonical patch `0327` reuses the existing retained writer from one
isolated late initcall and permits at most two short records, each with a full
local readback. Its unique live result distinguishes local writer success from
later cross-version recovery; the clock backend, observer, BigiDVFS, protected
transports, DA921x action, and CPU8/CPU9 requests all remain absent. The
prebuild definition passes its exact contract and 13 negative source/config
mutations. Corrected exact commit `c1d59f3` built successfully on Buildbox.
Exact padded candidate `53e03cb...e5c` passed all 32 LK gates, rejected 15 DT
mutations, and its tooling rejected 19 live and nine recovery mutations,
including crossed retained-slot attribution. It is admitted for one guarded
boot2 deployment and one physical selection. Guarded deployment resolved
inactive live-GPT boot2, confirmed slots 171--174 empty, matched the exact full
readback, and shut the device down. The one selection stayed fully serviceable
but reported exact live result `first=0 second=0 retained_writes=0`; the
classifier correctly withheld its automatic reboot. After read-only live
diagnostics, a separately recorded native return reached changed-ID Gemian with
unchanged boot2, empty slots 171--174, and empty pstore. This localizes the
negative result inside the shared writer's first-call DT/resource, mapping,
prefix, write, or readback boundary; returned empty RAM is not the causal
oracle. See the
[manual checkpoint control](../experiments/2026-08-21-mainline-manual-checkpoint-control/README.md).

The named next implementation is the default-off
`da921x-manual-checkpoint-stage-control` profile. Canonical patch `0328` keeps
the historical boolean marker and adds one live fixed stage selected from DT/
resource, mapping, prefix/header, write precondition, metadata readback,
payload readback, or success. The prebuild definition passes exact application
to the prepared `0327` source, all 109 manifest-profile series invariants, and
14 negative source/configuration mutations. Its exact Buildbox package,
serviceability DT derivation, Android-v0 container, independent DT mutations,
and pre-armed runtime observer now pass. Its guarded inactive-boot2 deployment
and full readback also pass, and the device is shut down; the next action is
the single observer-armed physical boot2 selection. See the
[manual checkpoint stage control](../experiments/2026-08-21-mainline-manual-checkpoint-stage-control/README.md).

That single selection is now complete. Exact release, candidate identity,
USB/netcat, keyboard, read-only DA921x presence, and CPU0--7 serviceability all
passed. The unique markers reported `first=0 second=0 writes=0` and
`stage=prefix-refused`; thus exact DT/resource conversion and retained mapping
completed, but the live four-slot prefix rejected before selecting or writing
owned slot 173. Only after that exact capture did the collector request one
native reboot. Changed-ID Gemian returned with exact unchanged boot2, empty
owned slots, and empty pstore. The recovery result does not reveal what the
mainline late initcall read and cannot override the live stage. Reject exact
candidate `43e7f44e...eac3` without repetition.

The selected successor is the default-off
`da921x-manual-checkpoint-prefix-control` profile. Canonical patch `0329`
leaves both historical prefix predicates and their loop order unchanged. Only
after the predicate refuses, it performs three bounded `readl()` operations on
the first rejected 12-byte header and reports relative slot, signature, start,
size, and one fixed reason. It adds no payload read, write, protected call,
clock operation, DA921x action, or CPU request. Its prebuild definition passes
exact application to the prepared `0328` source, all 110 profile-series
invariants, 16 negative source/configuration mutations, and strict style with
zero warnings. Its exact Buildbox package and independently assembled candidate
passed their offline gates, and guarded boot2 deployment completed with a full
readback and shutdown. The one physical selection remained serviceable and
reported the first rejected header as relative slot zero with all three words
equal to `0xffffffff`. Only after exact attribution did it return natively to
changed-ID Gemian, where the same physical slot remained an exact empty record.
This rejects a stale/nonempty record as the observed cause. Exact source audit
then found that the ledger profile deliberately skips `ramoops_init()`, so no
owned ramoops mapping exists in that boot; only the parallel `ioremap_wc()` view
does. Reject the exact prefix-control candidate without repetition. See the
[manual checkpoint prefix control](../experiments/2026-08-21-mainline-manual-checkpoint-prefix-control/README.md).

The default-off mapping-model discriminator in item 1 is now implemented as
canonical patch `0330`. Its exact Buildbox package, two independent DT
constructions, two independent container and padding constructions, 32 LK
gates, fixed five-result runtime oracle, and negative mutation suites pass.
The admitted padded candidate is `dd513384...693b5b`. Guarded inactive-boot2
installation, full readback, shutdown, and the single observer-armed selection
all pass. Both mainline mapping models returned the same all-ones header after
three reads each, with zero writes; exact serviceability passed and only then
returned natively to changed-ID Gemian, where the slots remained empty. This
rejects mapper substitution as the next fix. See the
[manual checkpoint mapping control](../experiments/2026-08-22-mainline-manual-checkpoint-map-control/README.md).

The exact raw-entry successor is also complete and stopped. Buildbox produced
release `7.1.3-gemini-protected-raw`; candidate `7c403a38...41a9` passed its
independent container and mutation gates, was written to inactive live-GPT
`boot2`, fully read back, and shut down cleanly. The pre-armed collector
confirmed the disconnect and changed-ID Gemian return, but Gemian recovered
neither owned record. Because the first checkpoint was still reached only
after observer probe entry and clock-backend acquisition, this result does not
establish that raw validation or the first commit ran, and it provides no
evidence that the protected-clock read began or failed. Reject the exact
candidate without repetition. See the
[protected-readback raw-entry ledger](../experiments/2026-08-22-mainline-protected-readback-raw-entry-ledger/README.md).

The independent manual raw-write qualification is now complete. Exact release
`7.1.3-gemini-checkpoint-raw-write` and candidate `c10f2c03...c631` passed the
Buildbox, container, guarded inactive-boot2 write/readback, shutdown, identity,
USB/netcat, keyboard, DA921x-presence, and CPU0--7 serviceability gates. Its
live marker proved one signature-last write and one complete local readback at
record 173 with zero protected, clock, BigiDVFS, DA921x-write, or CPU action.
After the identity-gated native reboot, changed-ID Gemian found that exact
record still valid in retained RAM and record 174 still empty, but exposed no
pstore file. This qualifies the raw writer and warm retention, not
cross-version enumeration. The pinned downstream reader explains the miss:
record 173 is behind empty dmesg records, the backend advances only one dmesg
index per read call, and pstore stops on the first zero return. The same parser
accepts the written `====0.000000-D` prefix. A bounded live probe confirmed
records 1--4 are exact empty while the primary console ring is nonempty, so the
successor must use record 1 rather than overwrite the live console. Do not
repeat the exact record-173 artifact. See the
[manual raw-write qualification](../experiments/2026-08-22-mainline-manual-checkpoint-raw-write-qualification/README.md).

The first-dmesg qualification is complete. Exact live attribution proved one
signature-last commit and full local readback; changed-ID Gemian recovered the
exact record once through pstore and independently in direct retained RAM. This
closes the writer, warm-retention, record-format, and first-record enumeration
boundaries. Do not repeat the sparse record-173 or first-record artifacts. See
the [first-dmesg result](../experiments/2026-08-22-mainline-first-dmesg-raw-write-qualification/README.md).

The clock-backend first-dmesg successor is also complete and stopped. Exact
live attribution plus both exact retained records prove driver init, platform
population, probe entry, and read-free probe completion. Its full
serviceability oracle failed for an independently localized reason: the clock
backend claimed the `0x11015000--0x11015fff` CSPM resource before the existing
handoff provider, whose `-EBUSY` failure left I2C6 deferred and the DA921x
client absent. No protected clock read, BigiDVFS read, register transaction,
clock enable, DA921x write, or CPU request occurred. This qualifies the narrow
entry boundary but rejects the candidate as a composition foundation. Do not
repeat it or proceed to a protected read on the overlapping resource model. See
the [clock-entry split result](../experiments/2026-08-23-mainline-clock-backend-first-dmesg-entry/results/runtime-attempt-1-read-free-pass-resource-conflict-20260823.txt).

Patch `0335` now defines the single-owner successor. The handoff retains the
only CSPM resource request; the clock backend keeps only its disjoint MCUMIXED
resource and resolves the handoff through `access-controllers`. Any future
clock snapshot executes inside the handoff's state lock and complete I2C6
transfer lease. The exact Buildbox candidate passed on the named unit with the
handoff as the sole CSPM owner, the clock backend as the sole MCUMIXED owner,
and I2C6, DA921x, keyboard, USB, and CPU0--7 serviceability intact. Every
protected-read, BigiDVFS, mapped-MMIO, clock-enable, DA921x-write, and CPU
action remained zero; changed-ID Gemian recovered both exact retained records.
This closes read-free resource coexistence only. See the
[coexistence result](../experiments/2026-08-23-mainline-clock-backend-cspm-coexistence/results/runtime-attempt-1-coexistence-pass-20260823.txt).

Patch `0336` now defines the selected one-read successor. Its isolated
Buildbox profile, deterministic serviceability/observer DT, Android-v0/LK
container, independent candidate validator, retained-record recovery oracle,
and live/runtime mutation suites pass offline. BigiDVFS remains disabled in
DT; the only admitted protected operation is one handoff-owned clock snapshot
with no caller retry or CPU request. The exact sanitized tooling is committed
and pushed. Deployment
preflight first failed closed on exact retained predecessor checkpoints; an
ordinary cold Gemian cycle cleared them without a memory write. The guarded
live-GPT `boot2` deployment then passed full readback and shutdown. Its single
selection reached exact serviceability and returned one complete `ret=0`,
ABI-2, generation-1 clock snapshot with the exact one-call terminal receipt.
The pre-armed classifier withheld reboot only because its oracle incorrectly
required ABI 1; canonical patch `0221` explicitly advanced this backend ABI to
2 with the CSPM live-state fields. The corrected read-only oracle then passed
on the same live boot without a second protected call. Only after exact live
attribution did the collector request the bounded native return. Changed-ID
Gemian recovered exact before/after records through pstore and independently
through direct retained RAM, with boot2 unchanged. This closes exactly one
handoff-owned protected clock snapshot and its failure-attribution boundary;
it does not qualify BigiDVFS, retries, writes, resume/error recovery, or CPU
admission. See the
[one-read experiment](../experiments/2026-08-23-mainline-protected-clock-first-dmesg-call/README.md).

The next ordered work is:

1. ~~Qualify exactly one protected clock read with a before-call checkpoint,
   an after-return checkpoint, bounded failure attribution, zero retry, and no
   CPU request.~~ Passed on the named device with ABI 2/generation 1 and exact
   live plus retained evidence; BigiDVFS remained disabled.
2. ~~Compose the validated readers, DA921x, and the platform-state source under
   one transition/hotplug owner.~~ The default-off injected compositor now
   passes its exact stack-safe Buildbox build and all seven no-network arm64
   tests while leaving A34, hardware effects, and CPU requests closed. The
   [implementation experiment](../experiments/2026-08-23-mainline-a72-direct-state-compositor/README.md)
   owns its exact generated identities and test chronology.
3. The
   [A34 publication contract audit](../experiments/2026-08-23-mainline-a72-a34-publication-contract-audit/README.md)
   rejects publication from the current ABIs. Direct-state `valid=1` is structural,
   not a recovered-value predicate; the current boot has no positive owner for
   BL31 replay-clear applicability; and P30 has no pristine bootstrap
   interlock. A34-v1 also duplicates caller-supplied state instead of consuming
   the compositor-owned record. Canonical patches `0342`--`0344` now implement
   the default-off P30 pristine claim, direct-state ABI 2 target identity, and
   A34 ABI 2 over one direct record plus typed replay applicability. Their
   exact Buildbox generation, semantic validation, replay, and strict style
   gates pass. The exact isolated Buildbox profile now also compiles with no
   new over-limit stack warning, and its P30, direct-state-v2, and A34-v2
   suites pass all 32 cases under no-network arm64 QEMU. The
   [implementation experiment](../experiments/2026-08-23-mainline-a72-a34-v2-interlock/README.md)
   owns the exact identities and classifications. The separate
   [atomic-publication audit](../experiments/2026-08-24-mainline-a72-atomic-publication-audit/README.md)
   found that releasing the logical P30 claim before the owner store permits a
   `prepare()` race, while releasing it afterward leaves a fallible operation
   after publication. It selects a nested P30 finalizer that retains the P30
   raw lock across one non-sleeping commit under `a72_state_lock`. Canonical
   patches `0345`--`0347` now implement that finalizer, one default-off
   no-caller atomic publisher, and eight injected success/failure cases. Their
   exact Buildbox generation, semantic validation, replay, and strict style
   gates pass with both CPU vetoes unchanged, no physical reader binding, no
   production replay source, and no device action. The
   [implementation experiment](../experiments/2026-08-24-mainline-a72-atomic-publication/README.md)
   owns the exact identities and rejected-attempt chronology. The final exact
   Buildbox profile has no atomic-test or unused-suite warning, and its strict
   no-network arm64 run passes the 20 late-startup plus eight atomic-publication
   cases with zero failures or skips and no unrelated suite registration.
   The offline
   [production-input ownership audit](../experiments/2026-08-24-mainline-a72-production-input-ownership-audit/README.md)
   now treats replay applicability and physical direct state as independent
   authorities and rejects a production publisher caller. Canonical Linux has
   no positive current-boot owner for the conditional primary-BL31 clear and
   no production direct-source registration. The physical branch also has an
   exact data blocker: A34's static zero protected-clock vector contradicts
   the already qualified named-device record. BigiDVFS's named-firmware ABI is
   confirmed, but its named-device mainline runtime and the composed platform
   record remain unqualified. Follow-up source review also finds that the
   stable DA921x snapshot is compiled only with the positive writable provider
   option. The linked audit owns the exact field counts, producer lifetimes,
   complete lock order, zero-on-failure behavior, and rejected replay
   substitutes; it performed no build, hardware action, device boot, or CPU
   request.
   The separate
   [physical-source qualification contract](../experiments/2026-08-24-mainline-a72-physical-source-qualification-contract/README.md)
   now freezes two phases. The first separates the DA921x read-only snapshot
   from the writable transaction and proves the writer remains absent. Only
   after that source proof may a candidate-only direct observer compose
   platform, DA921x, clock, and BigiDVFS under the existing outer owner with
   two retained checkpoints around the first attributable BigiDVFS call. The
   contract itself performed no build or device action.
   **Selected next:** implement and prove the hardware-free DA921x read-only
   snapshot separation on Buildbox with the positive writable provider option
   off. Add no physical adapter, boot candidate, device action, provider
   acquire/release, A34/P30/publication, or CPU request.
4. Only then build one decision-bearing CPU8 candidate with one request,
   strict per-stage checkpoints, bounded timeout, and fail-closed rollback.

The eventual CPU8 candidate must have a single CPU8 request, strict
checkpoints before and after each power step, a bounded timeout, and a
fail-closed rollback. CPU9
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
