# Sixteenth Phase B deployment, runtime 17 awaiting the owner's boot

Status: candidate 16 is installed and fully read back; the device was cleanly
powered off and is unbooted, awaiting the owner's physical boot2 start. The
laptop, as sole custodian, will execute the reviewed runtime-17 capture and
session exactly once after that; no radio action, mainline boot or runtime
evidence exists yet.

The [guarded deployment receipt](results/deployment-16.json) (the owner's
22-field summary, SHA-256 `4376f039…`) pins candidate 16: receipt
`1aaf85ea…`, full padded boot2 `c773902c…`, written over predecessor candidate
15 `eb43ddef…`, synced and flushed, with the independent full 16 MiB byte
readback matching. The installer was prepared from source `c41ab7b8`
(generated installer SHA-256 `11053f97…`; its difference from the
deployment-15 installer is only the candidate, receipt, predecessor, boot
identity, validation-tool digests and names, the guard mechanism identical;
prepare, syntax and ShellCheck passed) and executed once under the standing
boot2 authorization; the probe, write and post-write device guards passed on
the re-verified live Gemian boot `485cca7c…` (3.18.41+), target `179:30`
(`/dev/mmcblk0p30`), non-root `179:29`, stable power; no fresh predecessor
backup, temporary readback removed, evidence flushed, the installer exited 0,
the power-off SSH exchange ended with rc 255 (the remote closed the
connection during power-off), unreachable afterwards, nothing rebooted.

Runtime-17 preparation on the laptop at `c41ab7b8`: a fresh evidence root
with `wifi-phase-b/session-17` holding only the actual deployment-16 summary
(mode 0600) and `capture-17` absent; both offline preflights
(`laptop-capture.py`, `laptop-session.py`) passed on candidate 16 with the
owner's PSK-bound script (syntax, mode and single link passed, source body
unchanged); no execution claim exists.

The committed receipt [results/candidate-16.json](results/candidate-16.json)
(SHA-256 `1aaf85ea…`, the owner's receipt byte for byte) pairs the compile-21
package `f429ebe9…` (input `4983499e`) with candidate 15's RAM root,
byte-identical: boot image `41699010…` (12296192 bytes), full padded boot2
`c773902c…` (16 MiB), kernel image `4429011b…` (6642539 bytes), kernel config
`975f8703…`, initramfs `449832a3…` (63 members with the helper `bc499f28…`
and the supplicant `0487b710…`), board DT `25ab60f4…`. The owner verified
every member digest and size, the zero padding, the composer's parent
provenance, PSCI, clock, configuration, member, helper and supplicant checks.
Both receipt slots and the runtime-17 identity copy carry the receipt digest.
The owner's fresh PSK-bound script was generated from the `4983499e` join
script, whose bytes are unchanged since.

## This is a diagnostic boot

Runtime 17 is not a C2 success or data test. Frame admission is unchanged
from runtime 16: the only driver change, [proposal 0159](COMPILE_21.md),
names what the frame gate refuses (RXD header, group set, frame control,
receiver-is-this-station and transmitter-is-the-target flags, security mode)
for software frames as well as data RXDs, and names a key command the driver
refuses with its status and state flags. The tooling counts message 3 under
either prefix, counts the key installs, and samples the channel-40 IR state
every tick while the supplicant owns the connection. Finite radio budgets,
evidence preservation, the A53 regression, the reviewed native recovery and
every stop branch are unchanged.

## Hypothesis, unique observation and branches

Expected: the runtime-16 sequence repeats (message 1 delivered, message 2
sent, the after-activation EAPOL-shaped packet delivered, message 4 sent, the
supplicant's handshake completed) and the frame the gate then refuses is
named: its type word, group set, header length and flags, frame control (and
so its subtype), whether it is addressed to this station from the target,
and its security mode; if the supplicant's key install reaches the driver
after the fail-stop, the key refusal record names that too; the channel-40
state during the join is measured for the first time. Branches: the frame is
named (its policy is decided from that measurement, not before); the refused
frame differs from runtime 16's (named likewise); the join completes
differently (the existing records decide); or a stop branch fires earlier
(fail-stop, seal, reviewed recovery). No branch repeats a boot without a
decision-changing change; the measurement itself is the change this boot
makes.
