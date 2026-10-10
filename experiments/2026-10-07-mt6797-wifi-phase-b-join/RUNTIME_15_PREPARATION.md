# Fourteenth Phase B deployment, runtime 15 awaiting the owner's boot

Status: candidate 14 is installed and fully read back; the device was cleanly
powered off and is unbooted, awaiting the owner's physical boot2 start. The
laptop, as sole custodian, will execute the reviewed runtime-15 capture and
session exactly once after that; no radio action, mainline boot or runtime
evidence exists yet.

The [guarded deployment receipt](results/deployment-14.json) (the owner's
22-field summary, SHA-256 `431f794c…`) pins candidate 14: receipt
`889b101f…`, full padded boot2 `911e3d67…`, written over predecessor candidate
13 `ec412ce9…`, synced and flushed, with the independent full 16 MiB byte
readback matching. The installer was prepared from source `da5a776a`
(generated installer SHA-256 `b99c021a…`; prepare, syntax and ShellCheck
passed) and executed once under the standing boot2 authorization; the probe,
write and post-write device guards passed on live Gemian boot `572f3ea9…`
(3.18.41+), target `179:30` (`/dev/mmcblk0p30`), non-root `179:29`, stable
power; no fresh predecessor backup, temporary readback removed, evidence
flushed, clean power-off (rc 0) confirmed unreachable, nothing rebooted.

Runtime-15 preparation on the laptop at `da5a776a`: a fresh evidence root with
`wifi-phase-b/session-15` holding the actual deployment-14 summary and
`capture-15` absent; both offline preflights (`laptop-capture.py`,
`laptop-session.py`) passed on candidate 14 with the owner's fresh PSK-bound
script (syntax passed); no execution claim exists.

The committed receipt [results/candidate-14.json](results/candidate-14.json)
(SHA-256 `889b101f…`, the owner's receipt byte for byte) pairs the compile-19
package `46f3682f…` (input `9aa567d7`) with candidate 13's RAM root,
byte-identical: boot image `223f886e…` (12296192 bytes), full padded boot2
`911e3d67…` (16 MiB), kernel image `ce526e77…` (6642169 bytes), kernel config
`975f8703…` (113104 bytes), initramfs `449832a3…` (5621445 bytes: the parent's
61 members, the release gate, the Phase C1 helper `bc499f28…` and
`bin/wpa_supplicant` `0487b710…`), board DT `25ab60f4…`. The owner verified
every file digest and size, the zero padding, the composer's LK gates, the
package inventory and provenance, the exact configuration delta from
`153ea2d0…` to `975f8703…` (packet sockets enabled, `PACKET_DIAG` left off)
and the unchanged PSCI and clock contract. Both receipt slots and the
runtime-15 identity copy carry the receipt digest.

## What differs from runtime 14

Exactly one measured dependency: the kernel now provides packet sockets
(`CONFIG_PACKET=y`, [compile 19](COMPILE_19.md)), which the pinned supplicant
needs to add its interface ([RUNTIME_14](RUNTIME_14.md)). The join script
(no `-f`, redirected private log), the binder, the log export, the session,
host and classifier tooling, the supplicant binary and its configuration
template, the driver (proposals 0153 to 0157) and the RAM root are unchanged.
The owner regenerates the private PSK-bound script from the unchanged
`join-once.sh` for this runtime.

## Hypothesis, unique observation and branches

Those of [Phase C2](PHASE_C.md#device-protocol-stated-in-advance) with
proposal 0157, as stated for [runtime 14](RUNTIME_14_PREPARATION.md): the
supplicant adds `wlan0` (its packet socket now opens), performs its one
passive channel-40 scan, open-system authentication and RSN association
(capabilities 0x000c admitted), the two EAPOL frames each way, the two key
commands with their credits, the hold, the driver's deauthentication, the two
key removals and the three-stage teardown. Unique observation: the driver's
`eapol delivered`, `eapol sent`, `key command … submitted`, `key credit
returned` and `key removal … submitted` records with the final cleanup
stage, the supplicant's fixed phrases (one scan result set, key negotiation
completed, connected) and the complete private log export with the byte
count the join reported. Branches: the conjunction holds and runtime 15
passes C2 (no installed-key or operational claim); the supplicant starts but
does not complete (its phrases and the driver records decide, the healthy
teardown runs at the hold's end); a key command is refused or its credit
ambiguous or late (fail-stop); a scan or association shape is refused (named
refusal); the supplicant still fails to add the interface (its log names the
next dependency); or the AP's behaviour differs. No branch repeats a boot
without a decision-changing change. Runtimes 13 and 14 were tool-environment
startup failures and are not counted as handshake measurements.
