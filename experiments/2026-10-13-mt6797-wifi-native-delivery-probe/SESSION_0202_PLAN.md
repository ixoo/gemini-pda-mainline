# 0202 session preparation — UNBUILT, NOT ADMITTED

The latest [reviewer reassessment](#reviewer-reassessment-before-further-implementation-or-any-build)
puts an unchanged-C10 diagnostic choice before any new candidate build. C11's
eligible group counts contradict the proposed all-LLC-error premise. The owner-approved conditional C10 boot is now consumed: D3 Arm A authenticated,
so B was skipped. The result and independent preservation/recovery checks are
recorded below. No further C10 boot or successor build follows automatically. Keep 0202 separate for the framing fault.

The earlier owner order superseded six-second successor-trial preparation:
scan/group regression first, controlled SSH priming A/B, then a staged sustained
window. No new kernel build or device action has occurred. The local 0202
ownership prototype remains unbuilt. This document is preparation, not a result.

## Scan prerequisite result

The actual C10 and local 0202 `mt6797_mac_scan_packet` function, `scan-wire.h`,
`native-beacon.h` and `action-frame.h` are byte-identical. Scan frames are
selected by descriptor type, independently of the requested metadata mask.
The scan decoder walks G4/G1/G2/G3 as 16/16/8/24 bytes, then optional two-byte
padding. It requires G3 for RCPI and checks bounds before reading vector/MPDU.
The handler queues only the decoded MPDU with channel/frequency/signal.
Unsupported forms are withheld; malformed lengths are errors.

The existing scan-report fixture covered only G3. Its
[actual-source cases](../2026-10-07-mt6797-wifi-phase-b-join/tests/scan-report-test.c)
now cover all 16 masks, padding both ways, beacons and probe responses, exact
queued bytes, missing-G3 withholding and every truncation before the required
fixed fields. ASan/UBSan passed locally against both source trees. The runner's
Linux-only non-PIE flags are now conditional for local Clang. An initial local
invocation failed at that compiler flag, before executing any case.

The existing [joined-beacon fixture](tests/native-beacon-test.c) already covers
all 16 masks and padding, strict addresses/status/frame shape and truncation;
it also passed against 0202 locally. The class7 keyed-beacon selector remains
strict about its existing shape; it is not broadened to reinterpret class2 or
scan frames. These are host parsing results, not proof of firmware behavior
after requesting mask 7 before scan-ready. Linux ASan/UBSan scan delivery and
joined-beacon cases, and all seven A/B helper tests, passed from clean pushed
input `cf927f441e58369912687b49faaa2e50d4f0aff0` against the retained C10 source.
Its scan headers and MAC digest matched the frozen local C10 source. The 0202
scan function/headers are identical; the full 0202 prototype has not received
Linux validation. Repository checks passed locally; no kernel build or device
test ran. No framing check or production decoder changed for this prerequisite.

## Earlier unadmitted 0202 A/B preparation — superseded for SSH diagnosis

Hypothesis: an otherwise healthy session can fail before TCP acceptance because
the laptop needs group ARP delivery. Device-originated traffic to the laptop may
populate its neighbor entry. C11's acquired data accounting contains no extra
unicast SYN, but does not observe losses before acquisition. Timing correlation
does not establish the ARP/cache cause; the long-gap passing run contradicts a
simple expiry-only model.

The [prepared operation](ssh-prime.py) is deliberately not wired into the old
C10 session or admitted as a standalone tool. The future 0202 adapter must bind
the validated candidate, fresh boot, ACTIVE ready block, listener and lease.
Preflight must independently verify the laptop's current numeric LAN IPv4
address on the actual routed Wi-Fi interface, excluding the device lease,
router, USB endpoint, network and broadcast addresses. DHCP/local interface
evidence stays private. No hostname resolution, cache flush, packet capture,
laptop privilege or alternate device control API is allowed.

The earlier alternating-boot A/B is superseded by the reviewer reassessment
below. Keep the helper as unadmitted preparation; do not use 0202 to infer
unchanged-C10 group behavior. An unprimed arm is not a cold-cache assertion. After fresh readiness:

1. Read numeric route and laptop neighbor entry for the device's fresh lease.
2. ON: one guarded USB command makes the device ping the laptop's verified LAN
   address through `wlan0`, once, with a two-second reply limit and three-second
   process limit. Recheck boot, exact ready identity, listener, ACTIVE and fatal/
   terminal gates before ping. OFF: no device ping.
3. Read the neighbor entry again, then perform the original boot-bound Wi-Fi
   SSH authentication/challenge. Retain stdout, stderr and process exit/timing.
4. Read neighbor state afterward, including after a failed SSH attempt.

Local reads retain D2's 0.5-second limit. The optional operation and reads consume
the original exchange budget of at most 25 seconds; they cannot extend it.
Unknown query results are not absent entries. A guard/transport refusal prevents
SSH; an unanswered admitted ping is recorded and SSH is still observed. No retry.
Seven focused helper cases pass locally: arm ordering, no control-arm ping,
guard refusal, unanswered ping, query timeout, shared-budget exhaustion and
non-numeric/non-unicast refusal. Runtime binding and sustained SSH are pending.

Decision branches: compare successful priming plus actual neighbor change against
OFF runs, not merely arm labels. Failures with a present neighbor require the
client failure stage (TCP/KEX/auth) and separate transport evidence. An ON pass
or OFF failure alone is not causation. No DHCP/listener/ACTIVE means the A/B was
not reached. Do not continue an invalid or shortened run as a successful sample.

## Duration conflict and smallest proposed change

Current C10 limits, also retained by the ownership prototype:

| Source limit | Consequence |
| --- | --- |
| `mac.c`: request 9,000 ms; `join-commands.h`: request ceiling 10,000 ms | A 60-second grant is currently refused by host encoding. |
| Actual grant minus 2,500 ms tail minus association/key setup | Explains a roughly six-second available data phase; only the actual grant event establishes its expiry. |
| `native-diag.h`: wall 10,000 ms | Independently prevents a 60-second ACTIVE observation. |
| `mac.c`: data budget 60,000 ms | Already sufficient for the first stage, insufficient for 120/600 seconds. |
| 4,096 worker polls; 20 ms scheduled cadence | About 81.92 seconds at nominal cadence; no assurance of a 120-second lifetime. The exact counter remains authoritative. |
| RX 512 frames / 1 MiB; checked PTK 64; data PIDs through 126 | Any may end a run earlier, including beacon traffic or sustained SSH. No reuse or counter reset is permitted. |
| `join-ccmp.sh`: listener 90 seconds, overall 300 seconds | Blocks later 120/600-second stages. Its current SSH proof is one exchange, not sustained authenticated traffic. |
| Existing SSH helper: one process exchange capped at 25 seconds | A successful one-shot exchange cannot demonstrate sustained authenticated traffic for 60 seconds. Keep initial identity/authentication admission within this cap; sustained observation needs a separately bounded post-authentication phase in the same owned SSH process. |
| Teardown 5,000 ms; grant tail 2,500 ms; command 100 ms; frame/drain 750 ms | Preserve these failure/cleanup limits; do not make timeouts disappear by increasing them. |

Owner-approved first-stage preparation, implemented as a separate unbuilt
[0203 patch](../../patches/proposals/0203-wifi-mt6797-bound-first-fixed-format-window-to-60s.patch):
request 65,000 ms and narrowly admit that request in the encoder; retain the
matching token/channel grant validation and refuse a nominal 60-second trial
unless at data opening at least 62,500 ms of granted ownership remains. Raise
only the diagnostic observation wall to 60,000 ms. The existing data budget is
already 60,000 ms. A 32-bit interval field can encode this request, but does not
prove firmware will grant it: a smaller/refused grant is a distinct admission
failure, never a shortened pass. No renewal, new callback interpretation or
speculative register access is proposed. The owner explicitly approved preparing this exception while keeping kernel
builds on hold. All other limits below remain unchanged; this approval is not
a build or device admission.

Keep all other resource, poison, PN, transaction and cleanup limits. If one ends
the run before 60 seconds, report its exact counter/time as the first sustained
operation failure and stop. Do not silently increase it. A later 120-second and
then 600-second stage needs a separate evidence-based budget/ownership review;
they are not authorized by the first-stage proposal. Update the owned session's
bounded SSH operation to keep authenticated traffic throughout the admitted
window, binding the same boot/listener and checking every scheduled exchange;
an initial successful login does not count as a full-duration pass.

Rekey, key reuse, reconnect and GTK delivery remain disabled. Therefore one
lifetime per boot is the current maximum; batching several lifetimes in one
boot would violate those boundaries. Drop the repeated-boot sampling model. Prefer a predeclared measurement that
can distinguish a concrete cause in one boot, without promising that a passing
or time-censored boot will settle the hypothesis. Each admitted boot needs its
own reviewed handoff and owner physical selection.

## Reviewer reassessment before further implementation or any build

The owner supplied a shorter-path proposal. Source review changes several of
its premises; no device action or candidate build follows this review.
The sustained-client implementation is held while the C10 diagnostic is resolved.

| Point | Established fact / implication |
| --- | --- |
| Router versus laptop | `join-ccmp.sh` pings the DHCP router. It does not actively prime the laptop. A pre-existing laptop neighbor entry is a measured initial condition, not evidence of an empty cache in an unprimed arm. |
| Client deadline | The baseline explicitly uses `ConnectionAttempts=1` and `ConnectTimeout=10`. Failed C10 #2 spent ten seconds in its attempt; its data phase lasted 6,167 ms. A complete A/B pair cannot be guaranteed in unchanged C10. |
| C11 group status | All 32 reported groups also passed the shape and eligibility gates. The pinned C11 observer calls the unchanged `mt6797_data_rx`, which requires exactly `0xc000`. These groups were therefore not all `0xc200` LLC errors. This is a source-conditioned inference from the counters, not a retained per-frame status log. |
| Status regression | The actual-source fixture now explicitly accepts `0xc000` into observation, refuses `0xc200` from that observation, recognizes the latter as the separate LLC-mismatch discard shape, and confirms the strict PTK checker rejects the clean group without reading PN or changing replay state. All 2,718 exact-allocation cases pass locally and on Linux from clean input `f45b7645`. No GTK delivery is introduced. |
| Future candidate scope | 0202 remains a framing/format-ownership comparison. Its boot cannot substitute for unchanged C10 when explaining C10 group behavior. A future counters-only protocol classifier must be a separate logical change, not a receive-gate relaxation. |
| Credit limits | The source admits normal TC4 limit 26, with the data TC1 pool separately limited to 16. D2 snapshot 2 retained free 14 and pending FFA 12. Do not describe that as TC4 14/16 or combine the pools. |
| Failure ownership | The CONSYS firmware worker's `stopped` label logs and retains state; it does not tear down or poison the whole provider. HIF faults poison the HIF transaction; failed preparation closes MAC/scan admission. Preserve these fail-closed rules rather than suppressing genuine transport/accounting faults. |
| Shared credit budget | 0202 already reports admission/prior-credit/submit/mask-credit/done phase and the software ledger on error. The two phases retain one absolute 100 ms ceiling. Before building, retain the entry/previous phase and phase timing explicitly; do not split it into two fresh 100 ms deadlines. |
| RTNL | The inspected credit path is synchronous HIF mutex/guard/MMIO plus normal-ledger reconciliation. It neither acquires RTNL nor waits for an RX worker, network callback or completion requiring RTNL. Holding RTNL across the bounded sleep does not introduce that callback dependency in this path. This does not prove a firmware credit response. |
| Sequence limits | The initialization sender consumes one command sequence and accepts through 255. The inherited diagnostic uses `seq_ok <= 253`, historically reserving mode-command space. Fixed format removes those mode writes. Audit all remaining cleanup command needs and boundary cases before unifying these guards; a cosmetic equality of constants is not a lifetime ownership proof. |
| Scan readiness | Failure already withholds scan-ready and logs the preparation/parent stop. A direct no-op `scan_ready` call is still silent; make that refusal explicit before a future build. |

### One unchanged-C10 boot: predeclared proposal, now consumed as D3

A runs first using the original numeric lease, retained route/neighbor reads,
one original SSH command and full D1 stdout/stderr/exit/timing retention. If A
succeeds, stop: the missing-neighbor hypothesis was not reproduced. Record its
initial and final neighbor entry, not an assumed cold-cache condition.

If A fails, record its exact client stage and whether its attempt outlasted the
data window. B is a separately predeclared intervention, never an automatic
retry: it requires a fresh live boot/window/listener/lease check; one guarded
device-to-laptop ping; a neighbor read after the ping; and one separately retained
SSH attempt. If A consumed the window, B is not admitted and is recorded as
unreached. Do not change the grant, client timeout, keys or receive path silently
in order to manufacture a pair. The owner approved preparing this conditional boot, keeping the original
client timeout and all driver limits. B may be unreachable. A partial handshake
can also consume remaining PTK/PID resources; preserve their existing caps.

`No route to host` plus an incomplete neighbor is evidence consistent with a
neighbor-resolution problem, not exclusive proof: also retain the numeric route.
A timeout with a populated entry does not prove that a SYN left the laptop, nor
that the entry was valid throughout the attempt. A's own resolution activity
may change neighbor state before B. Successful B after priming is useful
correlation, not deterministic causation. A phase that overlaps diagnostic
termination is time-censored, not evidence that the driver rejected a SYN.

The [paired helper](laptop-wifi-ssh-paired.py) reuses the actual C10 verifier,
D1 output retention and D2 numeric route/neighbor reads in separate private
`arm-a`/`arm-b` directories. A's original receipt and failed verdict are never
replaced by B. B's client gets only the remainder of the shared original exchange
budget; neither ConnectTimeout nor any driver deadline is increased. The helper
verifies the routed interface's address, DHCP mask and lease with local numeric
queries before priming. Unknown or inconsistent results stop B. Additional local
reads retain 0.5-second ceilings; the ping has one three-second process bound and
one two-second reply wait. The fresh post-prime probe must match the exact ready
identity before B. The [session adapter](laptop-session-ccmp10-ssh-paired.py)
changes only the owned helper path; the original C10 image, leaf, child group,
seal and reviewed recovery remain. All raw arm/query files must be included in
the existing recursive pre-recovery seal. Produce one public scalars file with
both arms and one table row for this boot; no new per-run result document.

Eleven [actual-source host cases](tests/ssh-paired-test.py) pass locally and on
Linux from clean pushed input `f45b7645`: A success
stops, separate B success preserves A failure, closed window, prime guard refusal,
post-prime window change, unverified laptop address, unanswered ping/no retry and
retained A timeout, exhausted original budget, no third exchange after B failure,
and the actual CLI/receipt binding. These are host-control tests, not a device result. The complete host preparation passed before the handoff. The reviewed 603-line
installer skipped the already-matching C10 image, verified the full readback and
shut down cleanly. The owner then started boot2; the fresh boot and 84-byte
kernel notes matched the validated C10 image before the one capture/session.

A future group classifier may inspect bounded Ethernet/LLC header fields to
export only ARP/IPv4/IPv6/other/SNAP booleans alongside descriptor counters. That
necessarily reads those header fields, but must retain no frame contents or
addresses, read no PN, make no HIF acquisition, deliver nothing and mutate no
key/replay state. The exact consumer and decision branches must be specified
before implementation. Clean C11 groups already show that changing `0xc200` to
`0xc000` acceptance alone cannot resolve group key ownership. Strict GTK design
and delivery remain deferred until the separate framing result as directed.

## Evidence and later work

Use exactly one sanitized scalars JSON and one table row per run, with links to
sealed private evidence rather than a new per-run result document. Retain arm,
boot/image/source identity, grant interval and available budget, neighbor
before/after-prime/after-SSH status, ping exit/results, SSH stage and monotonic
failure offset, resource counters, actual/planned duration and independent
transport/network/cleanup verdicts. Unknown is explicit. Raw client/query logs
remain in the existing private evidence seal, not public scalars.

| Run / arm | Boot ID | Transport | DHCP | Individual pings | SSH / failure stage | Cleanup | Actual / planned duration | Scalars |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C10 D3 / A only | `ccce2504-bdbf-470b-ba7c-267b61f102d0` | finite pass | bound | 3/3 | A authenticated, exit 0; B skipped | host stage 3 clean | 6.205 / 6.178 s | [one scalars file](results/ssh-d3-runtime-scalars.json) |

D3's SSH process lasted 1.410 seconds with empty stderr. Its numeric ARP read
was absent before A and complete afterward. The route read returned exit 71,
`Operation not permitted`; treat route state as unknown. There was no privileged
fallback, extra query or repeat. A succeeded, so the device-to-laptop ping and B
were not attempted. Absence of an initial entry therefore did not prevent this
connection, but the resolution mechanism and earlier failure cause remain
unproved. Thirty-six checked PTK frames were queued; no named transport refusal
occurred. The data phase met its original finite budget, not a sustained stage.

All 70 pre-recovery seal entries, including nested Arm A files, independently
matched; the 169,765-byte log contains 2,113 contiguous records. Helper/device
children quiesced, the A53 regression passed, one reviewed return ran, and a
separate authenticated read confirmed changed-boot Gemian
`216ec26f-5811-444c-9422-40c1b23af081`. Healthy host cleanup is not key retirement
or firmware replay proof. No additional boot or retry is admitted by this result.

No 0202 run has occurred. Stop for a physical handoff only after a validated
build/package, reviewed session preparation and guarded install/readback/clean
shutdown. After reporting the 0202 result, the next design item is strict GTK
delivery with per-frame group PN checking grounded in C11's observed metadata.
No GTK implementation is part of this preparation.
