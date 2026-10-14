# CCMP3 — WPA2, CCMP Ethernet, DHCP, one ICMP reply and TCP; partial only

**Closed to unchanged repetition. Full provisional compatibility is false.**
ROOT executed exactly one capture/session on boot
`5fc8eaad-e459-4340-a920-8bece173f787`, kernel input
`47a23e6aea65be56246ca2b0fce023cf17028698`, approved source
`e1ecfcd967a246ad72627b9fd2d92caaa31c59a0`, MAC
`261a159513497d6e541831f1db442ddbd4974f781173fac4d3c718d095cc6139`,
package inventory `f811ca7f261927cb5e953abbddeb474915bf5fa88607e6496c01a7eff9a02316`.
Completed tooling is frozen at `766e34ab1f577c7153faa345715c16b566b88723`.
The [real receipt](results/ccmp-stable-monitor-candidate-3.json)84722412 binds
raw77d0a567/full
`4e3c8ef7cc3f6470ef76f3337e038160ba29ba996b32d4d0534f597c30f175e5`.
Source/tooling/package/installed identity are distinct. No worker device access.

## What worked, and what the frozen verdict means

- Common285/calibration/registration/regulatory0/TC4 reconciliation and wiphy
  readiness passed. AUTH/ASSOC responses had status0 and reached the existing
  management path. WPA2 messages1–4, initial PTK/GTK installation and key-
  negotiation completed. Both approved registration/management source repairs
  are now demonstrated on the identified hardware, not merely compiled.
- First firmware-decrypted CCMP Ethernet RX:347B, flags0x40200512; queued11,
  native ciphertext0. This is the selected firmware-decrypted/host epoch-PN/
  standard decap path, **not** native-ciphertext mac80211 AEAD/MIC verification.
- Normal DHCP exit0/bound1/lease_written1/prefix24; the194-byte DHCP log confirms
  lease acquisition. Listener started/ready with expected digest and sameboot/
  mode readiness evidence. No static bootstrap was used.
- The101-byte retained ping log has a PING header and **one real echo reply**:
  sequence0/TTL64/79.464ms, no final statistics and no error/usage line. Leaf
  ping0/0 are the unchanged missing-statistics defaults, **not zero traffic or
  three lost packets**. One reply is not three transmitted/received or ping3/3.
- The210-byte Dropbear log reports a child TCP connection, no public-key
  authentication success and an exit signal. TCP reached the listener; no fresh
  authenticated SSH command/boot proof or host ACK completed. Host receipt:
  ready_seen=true/ready_wait3.8s/ssh_attempted=true, exchange timed out after25s,
  aggregate28.8s, ssh_exit=null/boot_match=false/ack_written=false.

These are meaningful bidirectional protected-data compatibility observations,
not firmware integrity, hardware replay enforcement, hardware key deletion or
maintained support. In the frozen classifier, `authenticated=false` denotes
missing fresh SSH/ACK proof, **not denial of the observed WPA2 handshake**;
`eligible_ccmp_queue=false` also requires healthy cleanup/no fault, **not a zero
queue**. Preserve these original results rather than relabel them. Overall1,
cycles_completed0/terminals0, healthy_cleanup/provisional/full support=false.

## A. Short finite window and incomplete SSH/ping proof

Numeric chronology uses microseconds from boot:

The [complete sanitized numeric chronology](results/ccmp3-numeric-chronology.txt)
and [retained network-log scalar analysis](results/ccmp3-network-log-scalars.json)
are byte-exact payloads from the verified final bundle, not new hardware samples.

| Boundary | Time | Fields |
|---|---:|---|
| Data phase | 58840559 | budget6140ms/teardown margin5000ms |
| ARM | 58865120 | state1/act1/total0 |
| ACTIVE | 58894178 | state2/act0/total8/bytes990 |
| First CCMP Ethernet | 59274285 | bytes347/flags0x40200512 |
| DISABLE | 61749077 | state3/act2/total512/bytes77740 |
| Data end | 61774207 | elapsed2933ms/tx_queued13/tx_done11/tx_failed0 |
| CLOSED | 61779390 | state4/act0/total512 |
| Deauth submitted | 61780743 | subtype12/pid16/pages1 |
| HIF refusal | 61806354 | selected76/header28/staging80 |

The512 sample total comprises8 ENABLE_PENDING and504 ACTIVE frames. ACTIVE phase
type2=483/type7=21;27 delivered beacons are a separate counter, not an additional
27 reads to add to the total. ACTIVE-to-DISABLE is2854.899ms;2933ms is the
**data-phase** end footer, not literal ACTIVE duration. CLOSED follows DISABLE
by30.313ms. The all-RX cap was reached well below64 CCMP deliveries/1MiB/10s,
not evidence that a crypto predicate or the delivery ceiling prematurely failed.

The finite window precludes a sustained-support claim and can interrupt SSH/
ping completion. It does not establish the exact cause or stage of the SSH
stall: helper elapsed/ready-wait are host-relative and cannot be aligned to
kmsg without a shared origin. A TCP child is not authenticated SSH. One echo
reply plus absent final statistics is consistent with interruption, not a
complete ping measurement or proof of its termination cause. No additional
RX must be excluded from budget accounting, and no cap/static-IP change follows.

## B. Separate post-CLOSED HIF refusal and failed cleanup

HIF refused26.964ms after CLOSED, after deauth submission and its returned page:
port0/pre_valid1/WRPLR0x4c/selected76/header_valid1/header28/setup1/complete1/
staging80/post_valid0. Join status=-71/first0/submitted0x1801/debt0/cleanup0/
branch4. Two local key disables: removal_command_credit0/status-71/no_reuse1.
No three-stage healthy cleanup, credited key removal or hardware-deletion proof.

Pinned e1ec `mac.c:1605–1607` permits inherited IDLE/CLOSED cleanup receives;
1659–1665 lifts the TX fence at CLOSED. Branch4 at2260–2262 calls
`mt6797_hif_receive_packet`. In `hif.c:1105–1110`, WRPLR selects76;1128–1134
stages selected+4=80. At1140–1146 the scratch header28 fails equality and poisons
the owner. Post-WRPLR read, packet-type assignment and caller copy are at1148–
1155 and do **not** execute. `post_valid0` is unread, not an empty-FIFO observation;
packet type, payload and producer cause remain unproved. `first0` is printed
before fail-stop latches ret into first_error at `mac.c:1853–1854`, not success.

Retained ND6 chronology places its refusal24.116ms after CLOSED, versus26.964ms
here. Both phase3 counters record12 successfully received type2 frames before
refusal. That does not identify the refused packet or prove a shared producer.
The sanitized ND6 chronology does not supply its deauth submission timestamp;
no comparative deauth-completion interval can be invented. These near timings
show reproducible post-transition proximity, not whether disable, submission,
residual queue content or another producer is the cause.

The48-byte discrepancy recurs across ND6(80/32) and CCMP3(76/28). It is a clue,
not proof of descriptor padding, aggregation, a particular event, stale WRPLR
or a mode-transition race. No subtract48/trust28/copy-prefix/reread/ignore-poison
or skip-owed-cleanup repair is justified. Correct monitor state/credit retirement
does not imply that queued producer output was flushed or hardware keys removed.
This later transport refusal is distinct from the earlier incomplete data proof;
neither should be used to manufacture the other's cause.

## C. Production driver approach remains unproved

The observed path supports retaining the source-owned station/firmware-key/
host-PN/standard-decap approach as a **finite compatibility stepping stone**;
there is no evidence requiring rollback of the demonstrated registration or
management repair. It does not resolve normal non-monitor PN production, firmware
integrity attribution, GTK RX, rekey/same-slot retirement/reuse, transport IRQ-DMA,
resource/lifetime ownership, or clean-profile ten-minute operation. Those are
separate production gates, not reasons to weaken the current predicates.
In particular, [ordinary-mode Runtime32](../2026-10-07-mt6797-wifi-phase-b-join/RUNTIME_32_RESULT.md)
observed60 delivered frames without Group1, while this selected CCMP gate
requires Group1. No no-monitor maintained run, pre-arm substitution, unchecked
ordinary delivery or firmware-wide PN assumption is admitted by the positive.

## Approved source-only audit and existing refusal oracle

The bounded host-source audit found no intra-context setup/FIFO interleaving:
`hif.c:1093–1160` holds the same HIF mutex across WRPLR setup/read, port setup,
complete PIO staging, comparison and (only on success) post-WRPLR/copy.
Register/FIFO access uses ordered writel/readl; scratch/context share that mutex.
This is host-context serialization, **not** proof that another hardware owner or
firmware producer cannot change the advertised queue/format. The PIO loop issues
one setup then the encoded word count, no internal retry. For selected76 it reads
80 bytes; selected80 reads84. No shorter28/32-byte read is proposed.

The publicly pinned gen3 consumer's
[nicRxReadBuffer](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_rx.c#L2854-L2889)
also reads `ALIGN_4(WRPLR length)+4` and compares the descriptor RX byte count to
the selected length. For76 and80 its transfer spans equal the current PIO spans.
That source comparison gives no permission for a48-byte exception. No retained
producer proof of a changed inner/outer framing contract was established here.

Worker ordering is explicit: shared guard/credit reconciliation at mac2064,
native step2069, TX selection2076/2225, receive2261, cleanup step2884. DISABLE
pending admits no generic RX; register credit retirement moves it CLOSED.
CLOSED resumes inherited bounded RX and lifts the TX fence. Cleanup1405–1434
waits for empty queue, no in-flight/debt/pending credit, permitted native state,
acknowledged owned deauth and whole TC1 pool before key/station removal. The
trace lacks deauth TX-done and reaches refusal first: its returned page is not
deauth completion. No source proof equates monitor-command buffer credit with
producer FIFO quiescence or a packet-format barrier. Do not add skipped cleanup.
The same serialized worker receives the event needed to finish deauth, so
waiting for deauth completion before doing any RX would block that completion,
not establish a safe ownership fix. Source serialization also cannot prove
which firmware packet caused the mismatch. Deauth **submission** to refusal is
25.611ms, not a TX-done-to-refusal interval.

The existing [actual-HIF oracle](tests/native-metadata-hif-test.c), with its
unchanged runner/transport mocks, now includes76/28 and80/32, plus valid76/76 and
80/80 on both ports. Mismatch asserts entire caller buffer unchanged, owner and
transaction poison, setup/complete/staging span, exactly `words+3` transport
calls (23 for76,24 for80), no post-WRPLR setup/read, no packet-type/logical-byte
publication. Existing metadata assertions verify selected/header/gate fields.
Parent/child call/result tables are identical under ASan/UBSan. The current
CCMP3 HIF SHA256 `07763b3ba8f48ae71c2a629dcbe558c06a59b675d1fb7f57615ed148286e3769`
and all14 locally included headers equal the tested metadata-author driver;
this is actual pinned HIF control flow, not a replacement model or new harness.
The synthetic mock type is not evidence of the runtime packet family.

Separate leaf/helper timing audit: prerequisites are prepared before select at
join-ccmp.sh378; ACTIVE wait uses200ms polls; DHCP child/window polls200ms;
listener PID readiness polls500ms (281), then real readiness publication292.
The host's USB-ready probe sleeps200ms and launches exactly one Wi-Fi exchange.
These are concrete polling costs, but the retained scalar logs lack lease/ready/
TCP/ping monotonic timestamps or the shared helper-start origin. They cannot
prove which delay prevented authenticated SSH or whether500ms was paid here.
The helper's25-second exchange timeout runs beyond the brief radio window but
does not extend ACTIVE or authorize late ACK. Reducing timeout would shorten
host waiting, not prove or fix throughput. One ping reply and TCP connection
rule out a claim of no traffic; no timing repair or interval change is justified
from these records alone. No materially new implementation has been made.

## Smallest further decision-changing step — proposal only

**Complete the pending bounded producer-side advisory first**, using exact e1ec
source and already retained records. Host serialization/consumer review above
does not establish a producer cause. No firmware-wide search, new extraction or
device inspection is authorized by this record.

**Hypothesis:** the disable-to-cleanup boundary changes the length/descriptor
ownership contract seen by the next FIFO consumer; a source-supported48-byte
layout contribution or stale advertisement explains76/28 and80/32. This is a
testable source hypothesis, not an assertion that either occurred.

**Measurement/output:** trace the existing advertised-length calculation and
staged header-length calculation to the same packet/queue lifetime, including
pending packets across disable and deauth. Report whether both lengths must be
identical under the retained contract, the exact source-supported contribution
(if any) of48, and whether available records identify the refused packet family.
Limit review to those known paths; if the required producer record is absent,
report absence rather than searching the firmware broadly.

**Decision branches:**

1. Exact framing/ownership discrepancy proven: propose the smallest correction
   with offline positive/negative oracles and preserved fail-closed predicates;
   ROOT reviews the concrete body before implementation/build/device effects.
   Never add an unexplained length exception or generic48-byte subtraction.
2. Lengths must agree and no discrepancy is established: preserve poison/no-copy;
   do not reinterpret the refused transfer. A later proposal could expose only
   the **untrusted16-bit word at staging offset2**, already read, on that existing
   refusal. Exact proposed fields: `refused_type_valid` and `refused_type_word`;
   valid only for header-length refusal with existing setup/complete/header-valid
   and at least4 staged bytes. Emit through the existing refusal line, at most
   once in the one owned lifetime: poison/fail-stop remain immediate. No payload,
   peer/address/key or additional scratch sample is logged; no post-WRPLR/FIFO/
   register read, accepted packet, payload copy or new parser action is added.
   A control-like word directs bounded event/framing review; a data/management-
   like word directs pending-producer/mode-transition review; an unrecognizable
   word leaves framing/coherence unresolved. All are **untrusted hints**, not
   certified packet identity. Refusal/ambiguity stops with preserved evidence,
   no second sample/retry or alternate recovery. If no refusal occurs, apply
   unchanged finite compatibility/cleanup verdicts; do not induce one.
   A fresh, source-reviewed candidate would retain all current gates, budgets,
   effects and one-capture/session/recovery limits. ROOT must materially review
   fields/patch/privacy/one-shot limits/branches before any implementation/build/
   test; neither telemetry nor a new boot is admitted by this document.
3. Retained records insufficient: stop at that limitation and request a narrowly
   identified source/retained-analysis input or reviewable measurement. No broad
   new firmware search or unchanged CCMP3 repetition.

Keep helper timing assessment separate: source already prepares prerequisites
before ACTIVE and starts one real-lease listener/SSH challenge. Optimize only a
demonstrated avoidable cost from retained timing, not by extending the window or
relaxing readiness/ACTIVE/full-proof checks. No production-lifecycle effects are
included in this proposed offline next step.

## Preservation and return

All63 sealed files independently verified by ROOT, manifest
`3397125ee6e41a8d0fc8b342142a9ae29b503b56834769623c3e15cf296c0121`.
Full log through seal, helper/device-child quiescence and A53 regression pass.
Exactly one reviewed recovery, two LAN connection attempts,15.312s return;
strict changed Gemian boot `12b86e35-fee0-4f79-8a7a-29fbb364c261`,3.18.41+/aarch64
independently verified. Device remains ROOT-only, no repeated artifact.

The agent independently verified all15 sanitized final payload hashes, inventory
SHA256 `1b910cde2379128e611ab667d48d6253a697d1e8c370d1b80555497af62b2a98`.
Raw kmsg remains private:164195B/SHA256
`d93be0aff544d19ea24ee79db30be08c69eab4e73733170703424dff9ed8907a`.
No raw IP/AP/key/network logs, private firmware, candidate or RAM are published.
Only the explicitly requested existing offline test oracle changes; completed
runtime tools, kernel inputs, receipts and retained evidence stay immutable.
No kernel implementation, rebuild or new diagnostic effect is made by this
result/proposal. Full Wi-Fi goal remains unmet.
