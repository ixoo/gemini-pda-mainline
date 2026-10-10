# Fifteenth Phase B deployment, runtime 16 awaiting the owner's boot

Status: candidate 15 is installed and fully read back; the device was cleanly
powered off and is unbooted, awaiting the owner's physical boot2 start. The
laptop, as sole custodian, will execute the reviewed runtime-16 capture and
session exactly once after that; no radio action, mainline boot or runtime
evidence exists yet.

The [guarded deployment receipt](results/deployment-15.json) (the owner's
22-field summary, SHA-256 `1bf2a9a7…`) pins candidate 15: receipt
`a99fc4f9…`, full padded boot2 `eb43ddef…`, written over predecessor candidate
14 `911e3d67…`, synced and flushed, with the independent full 16 MiB byte
readback matching. The installer was prepared from source `e094ff6f`
(generated installer SHA-256 `60a155eb…`; its difference from the
deployment-14 installer is only the candidate, receipt, identity, predecessor
and tool digests and names, the guard mechanism identical; prepare, syntax
and ShellCheck passed) and executed once under the standing boot2
authorization; the probe, write and post-write device guards passed on live
Gemian boot `b3805d07…` (3.18.41+), target `179:30` (`/dev/mmcblk0p30`),
non-root `179:29`, stable power; no fresh predecessor backup, temporary
readback removed, evidence flushed, the power-off SSH exchange ended with rc
255 (the remote closed the connection during power-off; the whole installer
exited 0 with its reviewed receipt), unreachable afterwards, nothing rebooted.

Runtime-16 preparation on the laptop at `e094ff6f`: a fresh evidence root
with `wifi-phase-b/session-16` holding the actual deployment-15 summary and
`capture-16` absent; both offline preflights (`laptop-capture.py`,
`laptop-session.py`) passed on candidate 15 with the owner's fresh PSK-bound
script (syntax passed); no execution claim exists.

The committed receipt [results/candidate-15.json](results/candidate-15.json)
(SHA-256 `a99fc4f9…`, the owner's receipt byte for byte) pairs the compile-20
package `ee32128d…` (input `67a37ca1`) with candidate 14's RAM root,
byte-identical: boot image `b0c1ff8d…` (12296192 bytes), full padded boot2
`eb43ddef…` (16 MiB), kernel image `6aba6108…`, kernel config `975f8703…`,
initramfs `449832a3…` (63 members with the helper `bc499f28…` and the
supplicant `0487b710…`), board DT `25ab60f4…`. The owner verified every file
digest and size, the zero padding, the composer's LK, parent, member,
provenance and configuration gates. Both receipt slots and the runtime-16
identity copy carry the receipt digest. The owner's fresh PSK-bound script
was regenerated from the `67a37ca1` join script (unchanged at `8101a563`).

## What differs from runtime 15

One driver change, [proposal 0158](COMPILE_20.md): the clear EAPOL admission
binds the RXD BSSID tag to the two measured values and intervals, 15 until
the BSS command's credit completion and 1 while the station is active, so the
after-activation EAPOL-shaped packet that runtime 15 refused at that field
is now examined by the decoder's remaining framing gates. The tool side
counts the one scan by the nl80211 driver's debug line and the four handshake
messages by the supplicant's debug lines, and records the channel-40 query's
status, line count and flag words. Kernel configuration, RAM root, supplicant
binary, configuration template, binder, export, session and classifier
structure are otherwise unchanged.

## Hypothesis, unique observation and branches

Those of [Phase C2](PHASE_C.md#device-protocol-stated-in-advance), as in
[runtime 15](RUNTIME_15_PREPARATION.md), now with the after-activation packet
admitted at the tag: message 1 delivered before the activation (tag 15),
message 2 sent, the next EAPOL-shaped packet delivered (tag 1) if its framing
passes, message 4 sent, the two key commands with their credits, the hold,
the deauthentication, the two key removals and the teardown. Unique
observation: two `eapol delivered` records (one `activated=0 bss=15`, one
`activated=1 bss=1`), two `eapol sent`, both `key command … submitted` with
`key credit returned`, both removals, the final cleanup stage; the
supplicant's `RX message 3`, `Sending EAPOL-Key 4/4`, key negotiation
completed and connected lines each once, one nl80211 scan result set; the
complete private export with the reported byte count. Branches: the
conjunction holds and runtime 16 passes C2 (no installed-key or operational
claim); the after-activation packet is refused by another framing gate (its
named summary decides the next step); the packet is delivered but the
supplicant does not complete (its phrases and the driver records decide); a
key command is refused or its credit ambiguous or late (fail-stop); the
channel-40 flag is 0 again (its recorded query status, line count and words
name why); or the AP's behaviour differs. No branch repeats a boot without a
decision-changing change.
