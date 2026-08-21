# Protected-readback runtime observer

## Status

Buildbox generation, canonical admission, the exact isolated kernel build,
offline boot-image validation, live TEE identity, guarded `boot2` deployment,
and one physical selection are complete. The candidate returned to Gemian
without ever exposing its exact USB identity. A changed Gemian boot ID confirms
a cycle, and the installed `boot2` still matches exactly, but pstore,
`last_kmsg`, and the pre-armed collector contain no candidate identity or
observer record. The result is therefore `inconclusive-pre-transport`, not a
protected-read failure or success. The exact artifact must not be repeated.

One guarded deployment attempt reached the exact known-good Gemian system. An
independent live-GPT check then confirmed that both unmounted 5 MiB `tee1` and
`tee2` partitions match the required audited payload. The installer stopped
before staging or writing because the battery was 38% and no external source
was online; its gate requires at least 40% with external power or 80% without
it. The device was deliberately left running because no successful write had
occurred. See
[`results/deployment-attempt-1-power-gate.txt`](results/deployment-attempt-1-power-gate.txt).

After AC came online and the battery reached 40%, attempt 2 re-ran every gate.
It resolved inactive, unmounted logical `boot2` as `/dev/mmcblk0p30`, recorded
the predecessor checksum, wrote the exact padded candidate, synchronized and
flushed it, and obtained matching device-side and independently streamed
full-partition readback checksums. The temporary readback was removed and the
device cleanly powered off; it was confirmed unreachable and was not rebooted.
See [`results/deployment-attempt-2-success.txt`](results/deployment-attempt-2-success.txt).

The one permitted runtime attempt was pre-armed before physical selection. No
mainline USB interface appeared and no netcat command, including reboot, was
sent. The owner reported an automatic return to Gemian. Recovery found a
changed boot ID, empty pstore and `last_kmsg`, a nondiscriminating watchdog-
block reset token, and the exact candidate unchanged on inactive, unmounted
`boot2`. A read-only check also found the four final persistent-RAM headers
valid and empty. See
[`results/runtime-attempt-1-inconclusive-pre-transport-20260821.txt`](results/runtime-attempt-1-inconclusive-pre-transport-20260821.txt).

## Question

Can the remediated MT6797 protected-clock and BigiDVFS transports each produce
one complete attributable raw record on the named Gemini while all eight A53
CPUs, USB, and the console retain their proven serviceability and CPU8/CPU9
remain closed?

## Hypothesis and attributable evidence

The candidate adds one built-in observer and a separate Gemini DTB derivative.
The derivative enables exactly the protected-clock backend, the BigiDVFS
backend, and the observer. The ordinary Gemini DTB remains unchanged.

The observer defers without calling either transport until both backend devices
are bound. It then calls the clock transport once and the BigiDVFS transport
once, logs each return code and every raw record field, logs a terminal
`state=complete` receipt, and returns success. Returning success after the two
calls is deliberate: the platform core cannot automatically repeat a failed
read. There is no sysfs trigger or other retry endpoint.

A successful device observation requires all of the following from one exact
boot:

1. both live `tee1` and `tee2` checksums still match the already audited named
   payload before deployment;
2. exactly one clock and one BigiDVFS record plus one completion receipt;
3. successful ABI and nonzero generation fields for both records;
4. CPUs 0--7 online, CPUs 8--9 offline, and zero CPU requests;
5. working USB shell and console; and
6. no owner registration, secure write, automatic retry, or second boot.

Any missing, duplicate, failed, unstable, or contradictory observation rejects
the candidate and keeps composition closed.

## Provenance

- Canonical parent ends at patch `0319`.
- Prepared parent source state:
  `0f91989ff1d1a929c16aabf492e341adfa4fe302fdbf5f95ce27fe9ef65a6685`.
- Exact parent file identities are pinned in
  [`contract.json`](contract.json).
- Patch generation and kernel compilation run only on Buildbox from a clean
  pushed commit. No native VM kernel build is permitted.

### Generation attempts

1. At `2026-08-21T17:20:30Z`, Buildbox job
   `192b1af59eabf69bf1993f3bc8e94c8422bca2da-protected-readback-observer-patchgen`
   passed the complete generated-source validator, including exact call counts,
   raw-field coverage, candidate-only enables, and absence of write/CPU/owner
   effects. It then rejected the second patch because `git format-patch` folded
   the long email `Subject:` header while the validator required one physical
   line. The partial package was cleaned and no job record was promoted. This
   is a validator false negative, not implementation or hardware evidence.
2. At `2026-08-21T17:22:29Z`, Buildbox job
   `0753ef68d7e9dafe75e9f068a2252d2593cfaaa8-protected-readback-observer-patchgen`
   passed source validation, exact patch validation, and replay. Strict
   `checkpatch` then rejected the combined binding/driver patch and five C
   alignment checks. The partial package was cleaned and no job record was
   promoted. The remedy is a separate binding patch plus corrected alignment;
   the intentional adjacent format strings remain narrowly suppressed because
   they preserve each raw record as one atomic log entry.
3. At `2026-08-21T17:25:01Z`, Buildbox job
   `081528c518560c21292428fa43c446f10f070cfb-protected-readback-observer-patchgen`
   passed the three-patch split, all source and patch validators, replay, and
   every prior C alignment check. The remaining adjacent-string diagnostic was
   not suppressed because the supplied name described its text rather than the
   pinned checker's internal `SPLIT_STRING` type. The partial package was
   cleaned and no job record was promoted. Reading the pinned checker confirmed
   the exact narrow type; no generated implementation change is required.
4. At `2026-08-21T17:26:49Z`, Buildbox job
   `181ed445f7afc264b53553498526ba1f1701437f-protected-readback-observer-patchgen`
   generated, replayed, and validated the three exact patches. Every retained
   strict-checkpatch report has zero errors, warnings, and checks. The fetched
   bundle and admitted patch bytes match, and the 102-profile canonical-series
   audit plus its eight mutation tests pass. See
   [`results/generation-181ed445.txt`](results/generation-181ed445.txt).

### Validated build

At `2026-08-21T17:31:35Z`, exact clean pushed commit `1bd49d97673731509f0e2c7dcadbb2f03ed343ca`
produced Buildbox job
`1bd49d97673731509f0e2c7dcadbb2f03ed343ca-protected-readback-observer-m0`
and package
`linux-7.1.3-gemini-protected-readback-observer-e90eb76f-50826861`.
The complete package inventory validates, and its kernel release is
`7.1.3-gemini-protected-readback-ro`.

The resolved configuration selects the two protected readback backends and the
one-shot observer as built-ins, retains the SMP-8 serviceability profile, and
leaves both A72 power and A72 platform-state support disabled. The linked image
contains both backend read entry points and the observer probe/init path. A
decompiled base-versus-candidate DTB comparison finds only the model label,
the two backend status changes from `disabled` to `okay`, and the new observer
node with its two phandles. It contains no CPU or owner change. See
[`results/build-1bd49d9.txt`](results/build-1bd49d9.txt).

### Validated boot candidate

The candidate builder pins every package member, the candidate DTB, the
serviceability initramfs, and both LK serializer/analyzer tools. Two raw
assemblies are byte-identical, two independent 16 MiB padding constructions
are byte-identical, and the retained-LK analyzer passes all 32 gates. A separate
Python validator reconstructs the Android-v0 layout and canonical image ID,
verifies every input and runtime marker, and rejects six mutations spanning
the magic, kernel, DTB, initramfs, image ID, and padded tail.

The validated raw candidate is `a3cb0e1c79447345d700fefc5eb68f3d136c893db8a87ecf0ebf54d0ffc0189c`
at 7,636,992 bytes. Its exact `boot2`-sized form is
`30ec9c56d6be78635f0ccf3ea626727763d71590c23778774c5c6366e4a5e75a`
at 16,777,216 bytes. This promotes the artifact to `boot_candidate=true`;
it does not claim a device write, boot, or hardware result. See
[`results/candidate-a3cb0e1c.txt`](results/candidate-a3cb0e1c.txt).

### Deployment and runtime tools

The source-pinned guarded installer adds an exact live-GPT identity and
full-partition checksum gate for both `tee1` and `tee2` before retaining all
existing `boot2` target, power, write, full-readback, and clean-shutdown gates.
It never makes a fresh partition backup. The read-only USB/netcat probe captures
the kernel identity, candidate model, CPU state, and only the three tagged
observer records; it requests no reboot or device change.

The classifier accepts only one successful ABI-1/generation-1 clock record,
one successful ABI-1/generation-1 BigiDVFS record, the exact completion receipt,
CPUs 0--7 online, CPUs 8--9 offline, the exact release/model, and the forced
`maxcpus=8` policy. Offline tests pass the positive fixture and reject or
distinguish nine attribution, transport, and safety mutations. See
[`results/runtime-tools-offline.txt`](results/runtime-tools-offline.txt).

The firmware prerequisite is the
[protected-readback firmware audit](../2026-08-21-mainline-protected-readback-firmware-audit/README.md),
and the transport prerequisite is the
[protected-readback remediation](../2026-08-21-mainline-protected-readback-remediation/README.md).

## Scope and safety

The observer introduces no raw MMIO, SMC, clock, regulator, or CPU primitive;
it can call only the two typed readback APIs. The clock backend retains its
bounded existing CSPM internal-clock/semaphore protocol. The BigiDVFS backend
retains exactly eight calls to the audited read-only FID on a successful stable
sample. CPU8/CPU9 admission, the protected-state owner, and the resource owner
remain disabled.

The candidate is read-only at runtime, but installation still follows the
guarded logical-`boot2` policy: live GPT resolution, inactive/unmounted target,
stable power, exact-size padded image, full readback checksum, then clean
shutdown. No fresh partition backup is required.

The build profile inherits the hardware-passed serviceability fragments through
`gemini-smp8.fragment`, then adds only the protected-clock backend, the
BigiDVFS backend, and the observer. It does not select an A72 observer, a
protected-state/resource owner, a DA921x provider path, or a CPU transition.

## Decision rule

The generation, canonical admission, Buildbox link, candidate-DTB, container,
live TEE, guarded deployment, full-readback, and shutdown gates passed. The
single runtime attempt did not reach an attributable transport record or the
serviceability boundary, so composition remains closed. Do not repeat the
exact artifact. The next discriminator must add two independently recoverable
retained checkpoints around the first protected-clock call while preserving
the same two read operations and every CPU/owner closure.
