# Sixteenth Phase B deployment, runtime 17: candidate 16 composed, not installed

Status: candidate 16 is composed and offline-validated by the owner with the
reviewed composer at `c65f3d93`; it is not installed, no device action has
happened since runtime 16's reviewed recovery, and the device was last
verified in changed-boot Gemian `485cca7c…` with the installed candidate 15
(full padded boot2 `eb43ddef…`) as the predecessor; the owner re-verifies
before installing. The owner alone prepares and reviews the guarded
installer, performs deployment 16, runs both offline preflights on the actual
deployment-16 summary, shuts down cleanly and hands over to the physical
boot2 start; the frozen laptop wrappers then run once each.

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
