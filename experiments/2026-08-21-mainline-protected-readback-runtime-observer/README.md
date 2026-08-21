# Protected-readback runtime observer

## Status

Implementation is prepared for exact Buildbox generation. The first generation
attempt reached and passed source validation, then stopped fail-closed on a
validator-only folded-header mismatch. No patch package was admitted, and no
kernel build, boot image, secure read, hardware semaphore access, or device
action has yet occurred in this experiment.

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

## Decision rule

First generate two exact patches, replay them, and require strict checkpatch.
Then admit them canonically, add one isolated profile, and require a successful
Buildbox link plus exact candidate DTB validation. Only that validated package
may be assembled into one boot2 candidate. Composition under the transition
owner remains the next gate and cannot begin from compile-only or partial
runtime evidence.
