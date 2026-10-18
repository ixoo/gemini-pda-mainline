# D2 consumed: early RX length refusal, SSH diagnostic not reached

One admitted run on unchanged C10, 2026-10-18 UTC, from pushed host input
`faa5e182`. Strict USB identity verified boot
`61d0351a-5fe7-4bf5-8c55-21825fb867e6`, expected release/aarch64/mask helper and
exact C10 installation provenance. One original capture passed 285/285, exit 0;
one D2 session exited 1. No unchanged retry, new candidate or kernel build.
See the [predeclared D2 observation](SSH_NEIGHBOR_DIAGNOSTIC.md).

| Run | Boot ID | Transport | DHCP | Pings | SSH | Host cleanup | Data actual/planned |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D2 | `61d0351a-5fe7-4bf5-8c55-21825fb867e6` | Header-length refusal, -71 | Not reached | Not attempted | Not attempted; no failure-stage measurement | Failed, no stage-3 terminal; debt 1 retained | 0.384 / 5.196 s, early termination |

The first failure was logged 23.238 ms after data-phase start and 2.741 ms after
the enable=1/status=0 mask-submission log. Those are differences within the
kernel log clock, not firmware execution or packet-arrival times. The footer
at 384 ms is later disconnect reporting, not a healthy 384 ms lifetime. The
calculated 5196 ms grant-bounded budget and 5000 ms teardown margin were not
changed. This run must not be counted as a duration pass.

## Exact refusal and independent verdicts

Port 0 advertised WRPLR `0x0000005e` / 94 bytes. PIO setup and the requested
transfer completed, staging 100 bytes (aligned advertised length plus the
appended word); the descriptor declared 142. Equality refused the packet before
publication/copy. Retained bounded base hints: type word `0x5faf`, control
`0xce`, status `0xc000`. They do not validate a packet or its missing body.
Post-read was absent. No further read or -48 adjustment was attempted.

The diagnostic was ENABLE_PENDING (state 1), no frame in flight, one mask-command
page/credit pending. Branch 4 stopped with `-EPROTO` (-71), not a timeout. The
last successful register guard was valid; receive return preceded its credit
deadline by 97.243462 ms. The [retained-source review](D2_RX_CONTRACT_REVIEW.md)
separates established ordering from unproved producer behavior.

Supplicant completed initial WPA2 negotiation, but no DHCP cycle, individual
ping or Wi-Fi SSH process ran. The helper stopped after 3.5 s on the named join
fault, before readiness. No observation directory or local route/ARP queries
exist; all three intended D2 queries were unexecuted. These are missing network
measurements, not packet loss, an SSH failure or a neighbor-cache result.

No ACTIVE/CLOSED transition or healthy cleanup terminal was retained. Checked
PTK queues and data TX were zero. Both local key-disable records report status
-71, removal-command-credit 0, no-reuse 1. Poison and the owed page were not
forgiven; no re-arm/reuse/reconnect. Reviewed OS recovery is separate from
healthy firmware/resource cleanup.

## Preservation and return

All 63 pre-recovery seal entries independently rehashed. Complete kmsg has
160696 bytes and 2056 contiguous records, SHA-256
`1048c329f0184b29b912e4a53c3a41a24c4bfbf6e820964ce021c68388e232b4`.
Seal SHA-256
`06c2b121627c3c1835c0ec8372837b0f2a365e3396b616f4e930dc2e70d5dd1e`.
The owned helper was safe/group-quiescent with no timeout/probe/kill error;
boot-matched device quiescence and A53 regression passed. One reviewed native
return and three finite watcher attempts returned Gemian. Independent strict
LAN SSH verified 3.18.41+/aarch64 and changed boot
`e062dfca-3176-4135-88b0-681e57e80f0b`. Raw evidence stays private.
See [scalars](results/ssh-d2-runtime-scalars.json) and
[numeric chronology](results/ssh-d2-numeric-chronology.txt).

## Decision

This takes the earlier/different-failure branch, not a D2 SSH verdict. Mask-only
control does not eliminate framing refusal across lifetimes. Prior close-time
pairs were header = advertisement - 48; this enable-time pair is +48. Neither
sign is a framing rule. Keep complete advertised transfer, equality, poison
and no-copy. The C10 three-run SSH baseline remains 2/3; D1 succeeded without
classifying the earlier failure. No new evidence establishes its TCP/KEX/auth stage.

Do not repeat D2 unchanged or extend timers. Resolve the mask-transition/RX
ownership question from retained source before selecting another device test;
no successor candidate is admitted here. GTK delivery, rekey, key reuse and
reconnect remain disabled. Sustained 60 s / 2 min / 10 min acceptance is incomplete.
