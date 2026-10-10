# Eighteenth Phase B deployment, runtime 19 awaiting the owner's boot

Status: candidate 18 is installed and fully read back; the device was cleanly
powered off and is unbooted, awaiting the owner's physical boot2 start. The
laptop, as sole custodian, will execute the reviewed runtime-19 capture and
session exactly once after that; no radio action, mainline boot or runtime
evidence exists yet, and an installed candidate is not a Wi-Fi result.

The [guarded deployment receipt](results/deployment-18.json) (the owner's
22-field summary, SHA-256 `5ab16803…`) pins candidate 18: receipt
`b0d577ba…`, full padded boot2 `dfdf6bcb…`, written over predecessor candidate
17 `5135b2f8…`, synced and flushed, with the independent full 16 MiB hash and
byte-comparison readback matching. The installer was prepared from source
`3235f639` (generated installer SHA-256 `b9f41abc…`; its difference from the
deployment-17 installer is only the pins, names and current boot identity;
syntax and ShellCheck passed) and executed once under the standing boot2
authorization; the probe, write and post-write device guards passed on the
live Gemian boot `9ad08944…` (3.18.41+), target `179:30` (`/dev/mmcblk0p30`),
non-root `179:29`, power `1|100|Good|0` (battery-reported, no external
supply claimed); no fresh predecessor backup, temporary readback removed,
evidence flushed, the installer exited 0, the power-off SSH exchange ended
with rc 0, unreachable afterwards, nothing rebooted.

Runtime-19 preparation on the laptop, frozen at `3235f639`: a fresh evidence
root with `wifi-phase-b/session-19` holding only the actual deployment-18
summary (mode 0600) and `capture-19` absent; both offline preflights
(`laptop-capture.py`, `laptop-session.py`) passed on candidate 18 with the
owner's PSK-bound script; no execution claim exists.

The committed receipt [results/candidate-18.json](results/candidate-18.json)
(SHA-256 `b0d577ba…`, the owner's receipt byte for byte) pairs the compile-23
package `4f07d571…` (input `f5477df6`) with candidate 17's RAM root,
byte-identical: boot image `1de73be9…` (12296192 bytes), full padded boot2
`dfdf6bcb…` (16 MiB), kernel image `104cec2a…` (6643164 bytes), kernel
config `975f8703…`, initramfs `449832a3…` (63 members with the helper
`bc499f28…` and the supplicant `0487b710…`), board DT `25ab60f4…`. The owner
verified every member digest and size, the zero padding, the composer's
parent provenance, PSCI method, clock flag, gzip, configuration, built-DT,
helper, supplicant and member checks. Both receipt slots and the runtime-19
identity copy carry the receipt digest. The owner's PSK-bound script source
is unchanged since `4983499e`.

## What differs from runtime 18

One driver change, [proposal 0161](COMPILE_23.md): while the station is
active, a received packet of exactly the class runtime 18 refused (the
software-frame type word `0xee01`, the measured descriptor bytes with the
unicast-to-me flag, WLAN index 1 and status `0xe000`, frame control `0x00d0`
with only the Retry bit free, receiver this station, transmitter and BSSID
the target, at least two unread body bytes) is discarded without delivery or
interpretation, each one recorded, at most eight per join; the ninth or any
other shape is refused and named as before. Proposal 0160's group-data
discard (never yet exercised) and every other gate, the guard and recovery
tooling, the kernel configuration, RAM root, supplicant, binder, export,
session and classifier are unchanged except for the pins and names of this
runtime.

## Hypothesis, unique measurement and branches

Those of [Phase C2](PHASE_C.md#device-protocol-stated-in-advance) with
proposals 0157, 0158, 0160 and 0161: the supplicant's one passive scan,
open-system authentication and RSN association, message 1 delivered (tag 15),
message 2 sent, the target's Action frame discarded and recorded when it
arrives (and its group traffic likewise if it arrives first), the
after-activation EAPOL-shaped packet delivered (tag 1), message 4 sent, the
pairwise then the group key command each submitted with its credit returned,
the hold shortened by the group credit, the deauthentication, the two key
removals and the three-stage teardown. Unique measurement: `action frame
discarded` records (count 1 to 8) between the activation and the
deauthentication; two `eapol delivered` and two `eapol sent` records; `key
command: pairwise submitted` and `key credit returned: pairwise`, then the
group pair; `key removal` pairwise then group after the deauthentication's
TX done; the final cleanup record with credits returned and slots retired;
the supplicant's messages 1 to 4, key installs, key negotiation completed and
connected once each; the channel-40 state clear during the join; the
complete private export with the reported byte count. The conjunction
holding is a C2 pass: the handshake path and the firmware key commands are
demonstrated; no data, DHCP, ping, SSH, C3 or operational claim follows from
it. Branches: a ninth Action frame or another shape is refused and named
(the record decides); the target's traffic after the keys ends the hold
(named; the first C3 question); a key command is refused or its credit
ambiguous or late (fail-stop, no teardown command on a poisoned credit); the
removals or the final stage fail (named stage record); or a stop branch fires
earlier (fail-stop, seal, reviewed recovery). No branch repeats a boot
without a decision-changing change.
