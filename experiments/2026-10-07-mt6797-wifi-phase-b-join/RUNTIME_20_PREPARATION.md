# Nineteenth Phase B deployment, runtime 20 awaiting the owner's boot

Status: candidate 19 is installed and fully read back; the device was cleanly
powered off and is unbooted, awaiting the owner's physical boot2 start. The
laptop, as sole custodian, will execute the reviewed runtime-20 capture and
session exactly once after that; no radio action, mainline boot or runtime
evidence exists yet, and an installed candidate is not a Wi-Fi result.

The [guarded deployment receipt](results/deployment-19.json) (the owner's
22-field summary, SHA-256 `085330ad…`) pins candidate 19: receipt
`92b60a90…`, full padded boot2 `5d9aa34b…`, written over predecessor candidate
18 `dfdf6bcb…`, synced and flushed, with the independent full 16 MiB hash and
byte-comparison readback matching. The installer was prepared from source
`db1c1673` (generated installer SHA-256 `4b16c2d3…`; its difference from the
deployment-18 installer is only the pins, names and current Gemian identity;
syntax and ShellCheck passed) and executed once under the standing boot2
authorization; the probe, write and post-write device guards passed on the
live Gemian boot `e66144f8…` (3.18.41+), target `179:30` (`/dev/mmcblk0p30`),
non-root `179:29`, power `1|100|Good|1` (external supply present this time;
deployment 18 reported none); no fresh predecessor backup, temporary readback
removed, evidence flushed, the installer exited 0, the power-off SSH exchange
ended with rc 255 (the remote closed the connection during power-off),
unreachable afterwards, nothing rebooted.

Runtime-20 preparation on the laptop, frozen at `db1c1673`: a fresh evidence
root with `wifi-phase-b/session-20` holding only the actual deployment-19
summary (mode 0600) and `capture-20` absent; both offline preflights
(`laptop-capture.py`, `laptop-session.py`) passed on candidate 19 with the
owner's PSK-bound script; no execution claim exists.

The committed receipt [results/candidate-19.json](results/candidate-19.json)
(SHA-256 `92b60a90…`, the owner's receipt byte for byte) pairs the compile-24
package `295e881b…` (input `4be81db8`) with candidate 18's RAM root,
byte-identical: boot image `c9822c2f…` (12296192 bytes), full padded boot2
`5d9aa34b…` (16 MiB), kernel image `7b3a1dad…` (6643018 bytes), kernel
config `975f8703…`, initramfs `449832a3…` (63 members with the helper
`bc499f28…` and the supplicant `0487b710…`), board DT `25ab60f4…`. The owner
verified every member digest and size, the zero padding, the composer's
parent provenance, PSCI method, clock flag, gzip, configuration, compiled-DT,
helper, supplicant and member checks. Both receipt slots and the runtime-20
identity copy carry the receipt digest. The owner's PSK-bound script source
is unchanged since `4983499e`. The guard and recovery logic is unchanged
except for these pins and names.

## What differs from runtime 19

One driver change, [proposal 0162](COMPILE_24.md): the firmware's unsolicited
add-key-done event (`0x24`, 16 bytes, sequence 0) is admitted exactly once
after the pairwise key command was submitted, while the station is active and
the BSS configured, during the handshake hold with the reserved
deauthentication queued and before the deauthentication is in flight or done,
any cleanup stage or the pairwise key's removal, with BSS index 0 and the
target's address compared and never logged; it is recorded as `key done:
pairwise bss=0 peer=1` and changes nothing the hold, the teardown, the key
slots or the credit ledger depend on. Any other event of that id stays
refused. The classifier requires exactly one such record, after the pairwise
command and the activation and before the deauthentication's transmission,
for the handshake-path pass. Proposals 0160 and 0161 and every other gate,
the tooling, kernel configuration, RAM root, supplicant, binder, export and
session are unchanged except for the pins and names of this runtime.

## Hypothesis, unique measurement and branches

Those of [Phase C2](PHASE_C.md#device-protocol-stated-in-advance) with
proposals 0157, 0158, 0160, 0161 and 0162: the supplicant's one passive scan,
open-system authentication and RSN association, message 1 delivered (tag 15),
message 2 sent, the target's Action frame discarded and recorded when it
arrives (its group traffic likewise if it arrives first), the
after-activation EAPOL-shaped packet delivered (tag 1), message 4 sent, the
pairwise key command submitted with its credit returned and the firmware's
add-key-done event recorded for this BSS and the target, the group key
command with its credit, the hold shortened by the group credit, the
deauthentication, the two key removals and the three-stage teardown. Unique
measurement: `action frame discarded` records between the activation and the
deauthentication; two `eapol delivered` and two `eapol sent` records; `key
command: pairwise submitted`, `key credit returned: pairwise`, exactly one
`key done: pairwise bss=0 peer=1` in that window, then the group pair; `key
removal` pairwise then group after the deauthentication's TX done; the final
cleanup record with credits returned and slots retired; the supplicant's
messages 1 to 4, key installs, key negotiation completed and connected once
each; the channel-40 state clear during the join; the complete private export
with the reported byte count. The conjunction holding is a C2 pass: the
handshake path, both firmware key commands with their credits and the
firmware's add-key-done notification for the pairwise key are demonstrated;
no firmware notification exists for the group key and none is claimed; no
data, DHCP, ping, SSH, C3 or operational claim follows. Branches: the
add-key-done event arrives outside its window, twice or for another BSS or
peer (refused and named; the ownership question is answered by that record);
a ninth Action frame or another shape is refused and named; the target's
traffic after the keys ends the hold (named; the first C3 question); a key
command is refused or its credit ambiguous or late (fail-stop, no teardown
command on a poisoned credit); the removals or the final stage fail (named);
or a stop branch fires earlier (fail-stop, seal, reviewed recovery). No
branch repeats a boot without a decision-changing change.
