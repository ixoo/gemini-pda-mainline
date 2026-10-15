# CCMP4 — finite CCMP-IP repeated; failure-only hint0x4000, gap48 unresolved

**Closed to unchanged repetition. Full protocol/maintained Wi-Fi is false.**
Exactly one capture/session on boot `5bb85ac9-8f26-4523-996b-b784d23dca90`,
kernel input `92be8e69a39aa899701026294776c9ea79c9806a`, source
`b5969e62f02486f70fec2f202e21ec3e724286d9`, package949d7d04, completed tooling
`7cd7f401e158585327e7decdf8794461aa504a76`. The [real receipt](results/ccmp-stable-monitor-candidate-4.json)
1e8efbea binds rawb0402a25/full
`ee5dd8ad261496a387cf755b755982e0280f13a259e49619eb2de26e4a8dfc16`.
Source, package, tooling and installed bytes are distinct identities. ROOT alone
performed device actions; no new install, retry or build follows this result.

## Verified data and evidence boundary

All15 sanitized final payload hashes independently verified, inventory
`27f481d32c1dbef21ca188c56b55fd5ac49295e00315836be1bdf00da881f2de`.
The full private kernel log was also read and independently hash/size/mode
verified:164933B, SHA256
`c9e01e4121ddfa9e3199dd86a922385d66d488e633ce4494d477771553d813c9`,
mode0600. It contains2085 contiguous kmsg records, sequence0–2084, and408 property
continuation lines:2493 text lines, **not2493 records**. Each of the56 supplied
[sanitized chronology lines](results/ccmp4-numeric-chronology.txt) matches the
raw log exactly. [Derived scalar analysis](results/ccmp4-derived-scalars.json)
retains only counts/times/register metadata/hashes, not raw logs or identifiers.

The raw log, addresses, private paths, key/peer material and firmware remain
private. Broader owner authorization for trusted technical collaborators does
not grant publication rights or make credentials necessary to analysis.

## Positive finite compatibility, not a full pass

Common285/calibration/prerequisites/normal configuration/TC4 readiness passed;
BT_H1 absent. AUTH/ASSOC status0, WPA2 messages1–4, initial PTK then GTK command/
owned event/credit sequence and supplicant key-negotiation completed. These are
not typed hardware key-generation/deletion or firmware integrity certificates.

- 16 checked CCMP Ethernet frames queued, first347B/flags0x40200512; native
  ciphertext0. Firmware-decrypted/host strict-PN/standard-decap stepping stone,
  not native mac80211 AEAD/MIC or hardware replay proof.
- Normal DHCP exit0/bound1/lease_written1/prefix24;194-byte DHCP log confirms
  lease acquisition. Listener started/ready and digest matched.
- [Network-log scalars](results/ccmp4-network-log-scalars.json) show one actual
  ICMP echo reply, sequence0/TTL64/95.138ms, in101-byte ping.log. Final statistics
  are absent; frozen leaf0/0 are defaults, **not zero actual packets** or three
  measured losses. One reply does not satisfy ping3/3.
- 210-byte Dropbear log has a child TCP connection, no public-key authentication.
  Host READY seen after3.9s (host-relative); SSH attempted, exchange timed out,
  aggregate29.0s, no command/boot proof or host ACK. Host timing has no shared
  origin with kmsg; the cap is not proven the sole SSH failure cause.

Cycles0/terminals0/overall1; eligible queue/full provisional protocol false,
healthy cleanup false. Frozen `authenticated=false` means missing fresh SSH/ACK,
not absent WPA2 handshake; eligible_queue=false does not erase16 queued frames.
No static-IP fallback, GTK RX, rekey/reuse or new radio effect was used.

## Exact chronology and counters from this full log

Times below are microseconds since boot; intervals are differences, not firmware
processing latency or a causal identification.

| Boundary | Time | Fields |
|---|---:|---|
| AUTH response | 56488707 | subtype11/status0 |
| ASSOC response | 56540804 | subtype1/status0 |
| Data phase | 56717881 | budget6188ms/teardown margin5000ms |
| ARM | 56738440 | state1/act1/total0 |
| ACTIVE | 56763476 | state2/act0/total1/bytes442 |
| First CCMP Ethernet | 57235624 | bytes347/flags0x40200512 |
| Last ordinary TX-done | 60022458 | pid20/status0/advanced1/count1 |
| DISABLE submit | 60046382 | state3/act2/total512/bytes76098 |
| Data end | 60071437 | elapsed3353ms/tx_queued17/done16/failed0/credits38 |
| CLOSED | 60076593 | state4/act0/total512 |
| Deauth submit | 60077924 | subtype12/pid21/pages1 |
| Header refusal | 60079234 | selected449/header401/staging456/hint0x4000 |
| Join stopped | 60082459 | -71/first0/debt1/cleanup0/branch4 |

512 sample reads =1 pending type7 +511 ACTIVE (480 type2 +31 type7). ACTIVE
beacons27 are a separate counter, not additional reads. Drain phase2 records
57 type2+2 type7=59 reads, below its64-read ceiling. CLOSED phase3 has4 successful
type2 entries before the refusal; the refused transfer is not an accepted fifth
type2 entry. First-state4-RX and all512-ACTIVE interpretations are incorrect.

ACTIVE-to-DISABLE3.282906s; data-phase elapsed3.353556s, consistent with3353ms
footer. CLOSED-to-refusal2.641ms; deauth **submission** to refusal1.310ms. No
pid21 TX-done exists in the full log, and page debt remained1. Do not substitute
another PID's completion or a page credit for deauth completion.

## Refusal and the new word: source-supported meaning and limits

Port0/pre_valid1/WRPLR0x1c1/selected449/header_valid1/header401/setup1/complete1/
staging456/post_valid0/unread; refused_type_valid1/refused_type_word0x4000.
Exactly one such report. `first0` is printed before MAC latches `-EPROTO`; it is
not success. Two local key disables report removal_command_credit0/status-71/
no_reuse1: no hardware deletion or healthy three-stage cleanup proof.

Reviewed source reads offset2 only from the already-staged buffer after the
existing header mismatch and completion/span checks, then immediately poisons.
The valid bit means **staged bytes available**, not a validated RXD/frame/event,
group mask, packet boundary, peer ownership or producer. Arithmetic high bits
`0x4000 >> 13 == 2` make it a **data-like hint only**. In particular it does not
establish valid type2, Group1 absence, or a packet accepted by either parser.
The source does not publish successful packet_type/logical_bytes or copy the
caller buffer on this branch, and does not reach the post-WRPLR read. Runtime
metadata is consistent with that source/test contract; `post_valid0` is unread,
not an empty-FIFO measurement.

The exact deauth TX-done parser still requires24-byte class7/typeword0xe000/
event0x0f/PID21/index1. This hint cannot certify that event, nor establish what
earlier C3/ND6 refused transfers contained. An event-only story covering every
failure has no support from this observation; no alternative packet identity is
certified either.

| Run | Selected/header | Difference | Staging span | Untrusted word | CLOSED-successful type2 before refusal |
|---|---|---:|---:|---|---:|
| ND6 | 80/32 | 48 | 84 | unobserved | 12 |
| CCMP3 | 76/28 | 48 | 80 | unobserved | 12 |
| CCMP4 | 449/401 | 48 | 456 | 0x4000 | 4 |

The mismatch persists with a much larger header and a different tail count;
neither12 prior reads nor a small event-like length is a universal trigger.
Different intervals/counts are not controlled tests of aggregation/coherence.
Four successful CLOSED transfers do not exclude later intermittent incoherence.
The additional full private ND6/C3 logs were independently hash/mode verified;
[comparative scalars](results/ccmp4-comparative-scalars.json) now establish actual
deauth submissions for all three boots. ND6 submission391444354us to refusal
391467137us is22.783ms; C3 is25.611ms; C4 is1.310ms. No matching deauth TX-done
was observed in any of those full logs. Earlier ND6 sanitized omission need not
be used as absence evidence. These cross-boot records do not isolate mode effects.

### Does48 establish a Group1+Group2+Group3 effect?

No. Source descriptor walkers use optional Group1=16, Group2=8, Group3=24 bytes,
so their sum is48. But those walkers run **after** a successful HIF equality/
copy. The PIO path stores raw words contiguously; it does not remove groups or
rewrite byte counts before comparison. There is no host group-stripping step
here to blame or fix. A producer/controller layout change remains a hypothesis
requiring a proven descriptor/length lifetime contract; the untrusted word does
not establish group presence or a transformation.

For449, PIO stages ALIGN4(449+4)=456, matching the observation. Hypothetically
ALIGN4(401+4)=408, also48 apart; the same alignment arithmetic holds for the old
pairs. This is arithmetic, not a valid shorter-read instruction, aggregation
walk or evidence of a second packet. WRPLR-total semantics, appended-word rules
for a combined stream, producer coherence and reset/epoch state remain unproved.
449 is not a sum of4-byte-aligned spans under a literal aligned-span-total
interpretation; that does not settle any other raw-length aggregation format.
No subtract48/trust401/copy-prefix/reread/skip-cleanup repair follows.

The existing actual-HIF oracle now also includes449/401 and449/449 alongside
76/28 and80/32. Parent/child results/transport tables match under ASan/UBSan;
mismatch stages456 and stops after117 transport calls, no post-read/caller copy/
successful publication, with owner/transaction poison and no second report.
Its synthetic type word is not this runtime's packet-family evidence. No kernel
code, acceptance rule, runtime harness, hardware operation or budget was changed.

## Existing WHCR acquisitions: what is and is not retained

This raw log contains three complete named WHCR snapshots, allzero:
snapshot0 at40280628us, snapshot1 at40323188us, snapshot2 at40334715us;
valid_words0x3ff/status0. They are **this boot's early acquisition records**, not
old-boot values. Full-log/source ordering locates snapshot0 after START-ready
before capability, and snapshots1/2 after successful mac80211 registration/
regulatory configuration but before scan readiness. They are not all pre-normal-
command observations; all precede association/monitor. Last sample is19.744519s
before refusal. They do not establish fault-time WHCR, aggregation, reset default
or a safe register write. Zero is not anomalous merely because vendor enhance/
aggregate initialization also uses len-num0.

Actual `hif.c:335–449` also reads logical WHCR0x0c inside runtime reconciliation,
used by scan/join guards. Join guard receives a local status object, reconciles
page debt, then discards the value. Thus a near-CLOSED read exists in the source
path, but its **value/time are not retained in this log**. The already-reviewed
logical F1 command path is not direct MMIO at bridgebase+0x0c.

Source-only possibility for later review: retain the value/validity from an
already successful existing guard acquisition with an honest acquisition-bound
age/phase, not call it a fault-time snapshot. That would require new diagnostic
state/output and explicit ROOT review despite adding no MMIO. This record adds
none. Do not insert a pre/post-refusal WHCR read, consume counters again, program
WHCR, assume configuration persisted, or infer producer semantics from zero.

## Next bounded source question, not a new implementation

The smallest useful next step is the already admitted producer/retained-record
consolidation: trace which byte count advertises WRPLR and which constructs the
staged prefix across monitor disable, pending RX and deauth submission. Require
source/retained evidence for any48-byte contribution or packet/queue lifetime,
not an uncovered instruction idiom or arithmetic alone. Existing host locking
and same spans as the single-packet reference do not settle producer semantics;
vendor enhanced/aggregate routing does not by itself define this bridge's WRPLR.

Branches: exact contract discrepancy proven -> smallest reviewed framing/
ownership proposal plus negative oracles; ambiguity -> preserve refusal and
specify the minimal discriminating observation/resource protocol for ROOT review;
missing records -> state the gap, no broad firmware scan. No repair body is
justified yet. An already-acquired WHCR cache would help only if a concrete
state-dependent question is identified; it is not automatic permission or a
substitute for length/producer proof. No new observer, kernel build or radio test.

Normal-mode Group1/PN availability, firmware integrity, key-epoch retirement,
GTK/rekey/reuse, IRQ-DMA/resource/lifetime and clean-profile ten-minute operation
remain separate unresolved production prerequisites. The16 admitted frames
provide neither a same-session pre/post-arm group comparison nor a pre-arm
substitute for future per-frame checking. Full maintained driver work continues.

## Preservation and return

ROOT independently verified all63 seal entries, manifest
`3ba2792bde6b05330fd90888f1438c8e1677806008f8fc525c1c13d2b1209d1f`.
Full log-through-seal, helper safe/group-quiescent, device children quiesced and
A53 regression PASS. Exactly one reviewed recovery/two LAN connection attempts,
15.339s return; strict changed Gemian `b8867d12-71c8-4562-aa08-c52bbdcf84f9`,
3.18.41+/aarch64 independently confirmed. Device remains ROOT-only in Gemian.
No retry/new install, unreviewed recovery or stronger Wi-Fi/replay verdict.
