# Fifteenth Phase B deployment, runtime 16: candidate 15 composed, not installed

Status: candidate 15 is composed and offline-validated by the owner with the
reviewed composer at `8101a563`; it is not installed, no device action has
happened since runtime 15's reviewed recovery, and the device is in
changed-boot Gemian `b3805d07…` with the installed candidate 14 (full padded
boot2 `911e3d67…`) as the predecessor. The owner alone prepares and reviews
the guarded installer, performs deployment 15, runs both offline preflights on
the actual deployment-15 summary, shuts down cleanly and hands over to the
physical boot2 start; the frozen laptop wrappers then run once each.

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
