# C11: group PN metadata available; SSH remains a separate failure

Consumed once, 2026-10-18 UTC. All 32 observation-eligible group frames carried
G1, with GROUP_VLD 0xf. This reaches the predeclared positive GTK-metadata
availability branch without global SET_MONITOR. No group PN value was read,
no GTK replay state advanced and no group frame delivered. DHCP and three
individual pings succeeded; Wi-Fi SSH exit 255 did not authenticate the boot.
The overall compatibility result is false. Transport and host cleanup passed
independently. Evidence was sealed and changed-boot Gemian independently verified.

## Identity and execution

[Preparation](CCMP11_PREPARATION.md) pins kernel input
`774e08aa5570f96986acc1fd2a40afa0c226777d`, validated 854-member package,
real composition, source/tooling fixtures and guarded installation. Full boot2
readback matched
`3fea3a7cf1572f6f3feae4aeb6b773bca912bcc9e548a665679a20ab2ee92aae`.
After owner physical selection, strict USB SSH verified aarch64, the expected
release and new boot `e86a098f-c62a-4b48-a1c6-153627abbef2`. The standard
kernel-notes export was exactly 84 bytes, SHA-256
`9519a6db2f5922e736534fc922d54784437ba0f8c62ce05d546f5e1220dc6b69`,
matching the validated Image and differing from C10. The legacy release name
alone is not used as C11 image identity.

Execution checkout `71d8df1d46d4b0ea1b11564f6ba971d6ce75feba` ran one
Phase-A capture (ready, exit 0), then one actual session (exit 1). The validated
adapter source cohort remains `00351922`; subsequent changes were documentation.
No unchanged retry or concurrent device accessor. The
[predeclared observer](GROUP_PN_SUCCESSOR.md) retained every acceptance, HIF,
crypto, key, frame/byte/wall/grant and cleanup gate.

## Independent verdicts

| Area | Established evidence | Limit |
| --- | --- | --- |
| Group exposure | reported 32, legacy shape 32, observation-eligible 32. Eligibility requires current group key ID, WLAN index 2, TID 0, AP/G4 shape and an Ethernet-II body excluding EAPOL. | Metadata classification, not key-install certification or authentication. |
| PN metadata | G1 present 32, absent 0, mask bitmap 0x8000 (only GROUP_VLD 0xf). | No PN bytes read or compared. Other lifetimes/shapes and future availability remain unproved. |
| Ordinary RX accounting | All 39 ACTIVE type-2 packets are accounted for by seven checked PTK Ethernet queues and 32 separately observed, withheld group frames. Those classes are disjoint in the unchanged PTK checker and observer. | No additional ACTIVE type-2 rejection is exposed by these counts; packets lost before host acquisition are not measured. |
| Network | Initial WPA2, DHCP exit 0/bound/lease-written; three of three individual ICMP replies. | Seven checked PTK deliveries and seven status-0 data completions are finite observations, not sustained operation or independent over-air ACKs. |
| SSH | Fresh post-ACTIVE readiness marker, attempted exchange, exit 255, no served-boot match or host ACK. | Not authenticated SSH. The retained generic failure does not identify ARP/TCP/listener/authentication cause. |
| Transport | Mask enable and close each submitted once, status 0. Complete sealed log contains no join-stopped, HIF refusal or framing-hint fault. | PIO submission is not a firmware completion acknowledgement. No CLOSED type-2 packet was observed; this run does not explain or repair historical gap48. |
| Cleanup | CLOSED, deauthentication done, stage 3; terminal pending credit 0, no frame in flight. Both local key-disable records report status 0/removal-command-credit 1/no-reuse 1. | Host cleanup and returned pages are not firmware/HIF queue or key retirement proof. |

Individual ICMP replies: seq 0/1/2, TTL 64, 90.300/29.923/46.000 ms.
The data budget was 6156 ms with 5000 ms teardown margin; the footer reported
6175 ms elapsed under the unchanged polling/grant protocol. Diagnostic totals
147 RX / 47148 bytes and seven checked PTK deliveries stayed below 512/1 MiB/64.
No deadline was extended. The old footer's zero unicast/group counters belong
to the bypassed legacy delivery path, not to the checked-delivery accounting.

## Sealed C10/C11 comparison and SSH boundary

Both runs' 63-entry pre-recovery seals were independently reverified. The
comparison uses the sealed leaf export, SSH-helper receipt and complete kmsg,
not a reconstruction of network packets that were never captured.

| Observation | C10 original run | C11 original run |
| --- | --- | --- |
| Boot | `c80f93fe-ea39-4d6e-86b8-bfec0254c65c` | `e86a098f-c62a-4b48-a1c6-153627abbef2` |
| DHCP | Bound, lease written, exit 0 | Bound, lease written, exit 0 |
| Ping seq 0/1/2 RTT, ms | 102.281 / 24.678 / 44.552 | 90.300 / 29.923 / 46.000 |
| ACTIVE type-2 / checked PTK Ethernet | 50 / 36 | 39 / 7 |
| ACTIVE type-7 / CLOSED type-2 | 141 / 2 | 108 / 0 |
| Group withheld | Detailed count not retained | 32 eligible, all withheld; 7 + 32 accounts for all 39 ACTIVE type-2 packets |
| Data TX queued / done / failed; returned credits | 28 / 28 / 0; 59 | 7 / 7 / 0; 11 |
| SSH-helper readiness / final elapsed, s | 3.8 / 5.7 | 3.8 / 13.8 |
| SSH client | Exit 0, fresh boot matched, guarded ACK written | Exit 255, generic `exchange failed`, no boot match or ACK |
| Server evidence | Accepted connection and public-key authentication about 2 s after listener startup; session exited about 3 s after startup | Listener started; terminated about 5 s later; no accepted-connection, KEX or authentication event retained |
| Planned / observed data window, ms | 6200 / 6210 | 6156 / 6175 |
| Transport / host cleanup | No refusal; stage 3, debt 0 | No refusal; stage 3, debt 0 |

The leaf completes DHCP before starting Dropbear and publishing its readiness
marker, then runs three router pings. The asynchronous host SSH attempt can
overlap those pings. DHCP logs have no timestamp, and ping logs retain RTTs,
not packet start times: the exact DHCP-to-SSH interval cannot be recovered.
Server intervals above are coarse whole-second differences within each boot;
helper elapsed times are a different clock and are not directly aligned.

The frozen helper discards client stderr and does not retain client stdout on
nonzero exit. C11 therefore failed before any **observed server-side accepted
connection**. This is consistent with a TCP/connectivity failure but does not
establish the exact TCP, KEX or authentication stage. It is not evidence of a
credential rejection. The 10 s from readiness to failure also includes the
period after the finite data window closed; it is not a ten-second connection.

The old footer's zero drop counters belong to a bypassed legacy path and
cannot establish zero actual discards. C10 did not retain the classification
of its 14 unchecked ACTIVE type-2 packets. C11 accounts for every acquired
ACTIVE type-2 packet as checked PTK or deliberately withheld group traffic;
that does not exclude packets lost before acquisition. No retained evidence
identifies a rejected legitimate SSH frame, TCP retransmission or credit fault.

The C11 observer adds classification and counters on existing acquisitions,
with no new HIF operation, acceptance, crypto or deadline change. It can still
change CPU work, scheduling or timing. One passing C10 and one failing C11
cannot establish causality or a stable C10 baseline.

## Owner-directed next decision: unchanged C10 baseline

Do not build a successor. Restore the exact validated C10 image and admit up
to two further sessions, three total including the original pass. Preserve
unchanged diagnostic limits and separate evidence roots, with one custodian
and an owner physical boot2 selection for each run. Stable re-arm/reconnect
are disabled, so multiple sessions per selection are not admitted.

Record transport, DHCP, individual pings, SSH stage, cleanup and planned versus
actual duration independently. A short session is not a duration pass. If C10
passes SSH consistently, diagnose the C11 observer delta. If C10 also fails,
diagnose the separate SSH problem at its first established stage and specify
one bounded diagnostic with hypothesis and decision branches before implementing.
Only after baselining, review staged lifetime extensions around 60 s, 2 min and
10 min, preserving transport deadlines and reporting the first failure point.

GTK delivery, rekey, key reuse and reconnect remain disabled. No -48 adjustment,
longer transport deadline or further unresolved-callback reverse engineering
without a specific test need. The metadata result alone does not admit GTK
implementation. Full maintained Wi-Fi acceptance remains incomplete.

## Preservation and return

[Scalars](results/ccmp11-runtime-scalars.json) and
[numeric chronology](results/ccmp11-numeric-chronology.txt) contain fixed-prefix
numeric observations and independent verdicts. The complete-through-seal log
has 166464 bytes and 2093 contiguous records 0–2092, SHA-256
`987276a305084ceabe44d34697e8a42117a1e160eb737153468beeb6a73e2682`.
All 63 pre-recovery entries independently matched seal SHA-256
`a9d1982f9109abe07ee81b6e54db96bae0bc295275929c496106a31e616fe1e3`.
Raw captures, network data and credentials remain private ignored evidence.

Owned helper safe/group-quiescent, boot-matched device-child quiescence and A53
regression passed; no helper timeout/probe/kill error. One reviewed native return
and two finite watcher connection attempts confirmed Gemian
`795d2999-8793-46ac-a4b5-b8a6bc69321b`. Independent strict LAN SSH verified
`3.18.41+`, aarch64 and the same changed boot. This recovery SSH is distinct from
the failed mainline Wi-Fi challenge. C11 remains installed but consumed; no
physical selection is pending.
