# Seventeenth Phase B deployment, runtime 18 awaiting the owner's boot

Status: candidate 17 is installed and fully read back; the device was cleanly
powered off and is unbooted, awaiting the owner's physical boot2 start. The
laptop, as sole custodian, will execute the reviewed runtime-18 capture and
session exactly once after that; no radio action, mainline boot or runtime
evidence exists yet, and an installed candidate is not a Wi-Fi result.

The [guarded deployment receipt](results/deployment-17.json) (the owner's
22-field summary, SHA-256 `96eae241…`) pins candidate 17: receipt
`cf5958f2…`, full padded boot2 `5135b2f8…`, written over predecessor candidate
16 `c773902c…`, synced and flushed, with the independent full 16 MiB checksum
and byte comparison readback matching. The installer was prepared from source
`f4010c87`, the bindings revision (generated installer SHA-256 `8a69feee…`;
its difference from the deployment-16 installer is only the candidate,
receipt, predecessor, boot identity, pins and names, the guards identical;
prepare, syntax and ShellCheck passed) and executed once under the standing
boot2 authorization; the probe, write and post-write device guards passed on
the re-verified live Gemian boot `fbf740cb…` (3.18.41+), target `179:30`
(`/dev/mmcblk0p30`), non-root `179:29`, power `1|100|Good|0`; no fresh
predecessor backup, temporary readback removed, evidence flushed, the
installer exited 0, the power-off SSH exchange ended with rc 255 (the
remote closed the connection during power-off), unreachable afterwards,
nothing rebooted.

Runtime-18 preparation on the laptop, frozen at `f50b98e0` (the
documentation follow-up of `f4010c87`; every executable identical): a fresh
evidence root with `wifi-phase-b/session-18` holding only the actual
deployment-17 summary (mode 0600) and `capture-18` absent; both offline
preflights (`laptop-capture.py`, `laptop-session.py`) passed on candidate 17
with the owner's PSK-bound script, whose source is unchanged; no execution
claim exists.

The committed receipt [results/candidate-17.json](results/candidate-17.json)
(SHA-256 `cf5958f2…`, the owner's receipt byte for byte) pairs the compile-22
package `096b50b5…` (input `6a3b000d`) with candidate 16's RAM root,
byte-identical: boot image `59a2c509…` (12296192 bytes), full padded boot2
`5135b2f8…` (16 MiB), kernel image `13dbdeb6…` (6642715 bytes), kernel config
`975f8703…`, initramfs `449832a3…` (63 members with the helper `bc499f28…`
and the supplicant `0487b710…`), board DT `25ab60f4…`. The owner verified
every member digest and size, the zero padding, the composer's parent
provenance, PSCI, clock, gzip, configuration, helper, supplicant and member
checks. Both receipt slots and the runtime-18 identity copy carry the receipt
digest. The owner's fresh PSK-bound script was generated from the `6a3b000d`
join script, unchanged since `4983499e`.

## What differs from runtime 17

One driver change, [proposal 0160](COMPILE_22.md): while the station is
active and before a group key command has returned its credit, a received
packet of exactly the class runtime 17 refused (a data RXD with the measured
descriptor bytes, status `0xc004`, a protected FromDS non-QoS frame control
with the consistent flags, a group receiver address and the target as
transmitter) is discarded without delivery or interpretation; the first
eight are recorded, at most sixty-four are accepted per join, and anything
else, including unicast or decrypted protected frames, the same class after
the group key, and the unmeasured software frame of runtime 16, is refused
and named as before. The group receiver address is checked on the device for
the first time: runtime 17 recorded the descriptor's broadcast flag, not the
address. The classifier gains bounded support for the new record: the
`group data discarded` notification is admitted only between the activation
and the deauthentication's TX done, numbered 1 to 8 in order, and the
sanitized result reports the recorded count with its limit of eight (the
driver accepts up to sixty-four; the total is not in the log); the existing
handshake, export and session gates are unchanged from runtime 17's frozen
`c41ab7b8` tooling, as are the kernel configuration, RAM root, supplicant,
binder, export and session pieces.

## Hypothesis, unique observation and branches

Those of [Phase C2](PHASE_C.md#device-protocol-stated-in-advance) with
proposals 0157, 0158 and 0160: the supplicant's one passive scan, open-system
authentication and RSN association, message 1 delivered (tag 15), message 2
sent, the AP's group traffic discarded and recorded while it arrives, the
after-activation EAPOL-shaped packet delivered (tag 1), message 4 sent, the
two key commands with their credits, the hold, the deauthentication, the two
key removals and the three-stage teardown. Unique observation: `group data
discarded` records (count 1 to 8) between the activation and the
deauthentication, two `eapol delivered` and two `eapol sent` records, both
`key command … submitted` with `key credit returned`, both removals, the
final cleanup stage; the supplicant's message 3 (either prefix), message 4,
key installs, key negotiation completed and connected once each; the
channel-40 state clear during the join; the complete private export with the
reported byte count. Branches: the conjunction holds and runtime 18 passes
C2 (no operational claim); a group frame fails the receiver-address or any
other decoder check and is refused and named (the record decides); the
runtime-16 software frame or another shape is refused and named; the AP's
traffic after the group key ends the hold (named; the next question); a key
command is refused or its credit ambiguous or late (fail-stop); or a stop
branch fires earlier. No branch repeats a boot without a decision-changing
change.
