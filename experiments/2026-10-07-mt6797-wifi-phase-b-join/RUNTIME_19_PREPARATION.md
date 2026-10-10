# Eighteenth Phase B deployment, runtime 19: candidate 18 composed, not installed

Status: candidate 18 is composed and offline-validated by the owner with the
reviewed composer at `cf599cc4`; it is not installed, no device action has
happened since runtime 18's reviewed recovery, and the device was last
verified in changed-boot Gemian `9ad08944…` with the installed candidate 17
(full padded boot2 `5135b2f8…`) as the predecessor; the owner re-verifies
before installing. The owner alone prepares and reviews the guarded
installer, performs deployment 18, runs both offline preflights on the actual
deployment-18 summary, shuts down cleanly and hands over to the physical
boot2 start; the frozen laptop wrappers then run once each.

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
