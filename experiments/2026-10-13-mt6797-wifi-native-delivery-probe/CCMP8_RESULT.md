# C8: post-CLOSED selection exercised; gap-48 persists

Consumed once, 2026-10-18 UTC. WPA2 and DHCP completed; one real ICMP reply
was retained and Wi-Fi SSH was attempted but failed. After monitor CLOSED,
four transfers passed length equality and were counted as type 2, then the
selected reader refused advertised/header lengths 88/40. No healthy cleanup or
maintained Wi-Fi. The device returned to independently confirmed Gemian.
No unchanged C8 repetition or next device candidate is selected.

## Identity and one execution

[Preparation](CCMP8_PREPARATION.md) pins kernel input `3dafb066`, profile,
849-member validated package, source, configuration, real receipt and guarded
installation. Full boot2 readback matched
`e3c347f1f45a942746dec025a5666242807c849fdc91f71c5fb9279c73e0ec66`.
After owner selection, strict USB SSH verified aarch64, the expected release
and the new selected-reader symbol on boot
`69e90265-77e3-4aa9-9610-5e7607647ab1`. Release alone does not distinguish C7/C8;
the verified installation, source chain and new symbol bind this candidate.

Tooling `6bcb0334f1d0f27775b18621ea74dcfc44ccd03b` ran one Phase-A capture
(exit 0, ready), then one actual session (exit 1). No host-preflight retry,
second capture or alternate candidate. The [source comparison](CLOSED_RX_SELECTION_COMPARISON.md)
changed only opted-in post-CLOSED receive selection. ACTIVE/scan, firmware
commands, strict equality/full transfer/poison/no-copy, PN/key and finite
budget/deadline gates remained unchanged.

## Independent verdicts

| Area | Established evidence | Limit / decision |
| --- | --- | --- |
| Transport | Four CLOSED length-equal type-2 transfers; then port 0 WRPLR 88 / header 40, complete staged span 92, hint `0x4000`. Stop -71, branch 4. | The selected-from-one-word cleanup sequence is insufficient. No 48-byte exception, short read, prefix copy or retry. |
| Network | Initial WPA2 negotiation, four checked CCMP Ethernet deliveries, DHCP lease and one individual ping reply. | No three replies, authenticated SSH ACK, ten-minute session or complete cycle. |
| Cleanup | Disable's one-page credit returned and state CLOSED. Deauthentication PID 9 submitted; stop shared debt 1, cleanup stage 0. | That new obligation did not retire. CLOSED is not station/resource teardown or healthy re-arm. |
| Timeout/credit | Branch-1 site 0; pending flag 0; cached guard release is one CPU/FFA pair, TC4 free 26, TC1 free 16, pending remainders 0. | This run is not C5's in-flight timeout or C6's pending-disable stop. Cached free counts precede deauthentication's new debit; they are not terminal debt 0. No C6 retrospective cause or ledger repair. |
| Security | Existing initial stable-PTK, monitor-assisted host-PN/checked-decap path only. | No ordinary-mode integrity/PN, GTK attribution, rekey, key deletion or safe slot reuse proof. |

Four ordinary data submissions, PIDs 5-8, each have status-0 completion and
returned pages. Firmware completion status is not an independent over-air ACK.
Native ciphertext queued 0. The separate legacy footer RX-unicast 0 does not
negate the four checked Ethernet deliveries.

DHCP exit/bound/lease-written are 0/1/1. The retained partial ping transcript
contains sequence 0, TTL 64, 103.125 ms, with no final transmission/loss summary.
Leaf ping 0/0 are interrupted-completion defaults, not observed packet counts.
The SSH listener passed its binary/readiness checks; the host helper saw the
fresh boot/mode/after-ACTIVE marker and attempted SSH (exit 255), without
verified authenticated boot match or ACK. A ready marker is not authentication.

## Chronology and retained terminal fields

The [chronology](results/ccmp8-numeric-chronology.txt) and
[scalars](results/ccmp8-runtime-scalars.json) contain only fixed numeric fields.
Times below are host log microseconds since boot, not firmware arrival times.

| Boundary | Time | Observation |
| --- | ---: | --- |
| Data phase begins | 95390063 | 6204 ms data budget, 5000 ms teardown margin |
| ACTIVE | 95435738 | total 3, bytes 1602 from enable-pending |
| First ordinary submit / completion | 95906702 / 95931982 | PID 5 |
| Last ordinary completion | 97424044 | PID 8 |
| DISABLE_PENDING | 97478686 | all-RX 512, bytes 93341 |
| Disable credit / CLOSED | 97502678 / 97509013 | one page returned |
| Deauthentication submitted | 97510392 | PID 9, one page |
| Length refusal / stop | 97511745 / 97526446 | 88/40, -EPROTO, shared debt 1 |

The CLOSED class counter is type-2 count 4, all other types 0. These transfers
passed HIF length equality; the counter does not certify their security,
payload identity or admission to mac80211. There are no per-transfer accepted
length/timestamp records.

Port 0 terminal history: 547 attempts, 516 successes, 12 type-7 records,
status -71, pre-WRPLR `0x00000058`. Port 1: 541 attempts, no successful
transfers, 485 opposite-half advertisements, status -EAGAIN and older pre-WRPLR
`0x000001ab`. Before CLOSED, the requested-port acquisition pattern is unchanged.
Selected-runtime whole-word-empty queries have no selected FIFO and use the
legacy loop's port-0 observation bucket. Attempts are not FIFO-read counts.

The last valid guard returned at `97456096698` ns, WHCR 0 / WHISR 3, WTQCR7
`0x00010001`. Its release result has TC4/TC1 free 26/16 and no accumulated
CPU/FFA/AC1 remainder. Terminal worker timestamp is `97468457621` ns; port-return
boundaries are `97465165851` / `97404313082` ns. These cached acquisition values
are not fault-time samples and printk records are not exact acquisition times.
Current in-flight PID is 9 with frame deadline `98214955928` ns; last ordinary
submit is PID 8, return boundary `97348095544` ns. No data-TX-timeout line.

## What the comparison establishes

The actual source routes engaged stable-CCMP CLOSED reads through one existing
WRPLR acquisition, selecting port 0 if nonempty else port 1 from that same
word. The legacy empty-request/opposite-work read is absent in that phase.
The state/flag chain and CLOSED counters establish that this route was
exercised. It still hit gap-48, so changing this cleanup sequence alone does
not prevent the refusal.

This does not exclude effects accumulated during unchanged ACTIVE, scan or
boot acquisitions. It also does not prove a firmware conversion defect,
FIFO-pop trigger, packet identity, metadata-stripping rule or transport cause.
The untrusted staged type hint has group bits zero; it is not permission to
interpret or deliver the refused bytes. Constant 48 remains a clue.

The next source question is the relationship between pending length entries,
monitor disable and the refused descriptor's actual framing. The retained
four-byte hint does not identify its translation/header/status contract. Review
that missing distinction before selecting another observation or correction;
no automatic broader read-sequence change, new register access, cache, credit
refund, deadline extension or unchanged retry follows from this result.
Ordinary crypto and healthy reusable lifetimes remain part of the full goal.

## Preservation and reviewed return

The complete 163516-byte log has SHA-256
`5b829ad913120ada7bc703ed5dc79548d3afca9c9ec2c893d2b70caf7df05204`,
2073 contiguous records 0-2072, classified complete through explicit seal.
All 63 pre-recovery entries independently match seal SHA-256
`c252a9930a0e267d77b00a19af68042dfe1a9e6e9b77bcd637d136c16bfecf76`.
Raw captures, network exports, addresses, credentials, packet bytes and private
analysis identities remain in ignored evidence.

Owned helper SAFE/group-quiescent and boot-matched device-child quiescence
passed, with no helper timeout/probe/kill error. A53 regression passed. One
reviewed native recovery request and two finite watcher connections confirmed
changed-boot Gemian `8cffe5a0-4a2e-4441-aa93-1cc8be97cd59`. Separate read-only
LAN SSH confirmed `3.18.41+` / aarch64 and the same boot. C8 remains installed
in boot2 but consumed; no physical selection is pending.
