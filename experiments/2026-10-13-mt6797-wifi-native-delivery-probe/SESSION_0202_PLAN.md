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
| GTK1 | `b1417555-b2f2-4d07-89cc-9608874f78a8` | no named HIF refusal; host `-ERANGE` | not reached | not reached | not attempted; before ready marker | healthy stage 3 absent | 0 / 60 s; window unopened | [one scalars file](results/gtk1-runtime-scalars.json) |
| GTK2 | `f77aa006-7757-40b3-960e-2a96ddc82804` | finite capability pass | bound | 3/3 | authenticated, exit 0, 1.410 s | host stage 3 clean | 5.925 / 60 s; checked-frame cap 64 | [one scalars file](results/gtk2-runtime-scalars.json) |
| GTK3 | `1fa923f3-aab1-43e1-83f9-f6d12c2aa422` | no named HIF refusal; host control-event `-EPROTO` | bound | 3/3 | authenticated, exit 0, 1.256 s | healthy stage 3 absent; quiescence/return pass | 30.144 / 60 s; event 0x13 refused | [one scalars file](results/gtk3-runtime-scalars.json) |
| GTK4 | `c2efe494-648e-44ca-9bb1-519ffce4496d` | complete event; host `-EPROTO`, no named HIF refusal | bound | 3/3 | authenticated, exit 0, 1.325 s | healthy stage 3 absent; quiescence/return pass | 29.955 / 60 s; BSS 0/reason 6, recent beacons | [one scalars file](results/gtk4-runtime-scalars.json) |
| GTK5 | `f015f0f2-1320-4e12-98d5-dbacc7c69cb2` | no named HIF refusal in data; cleanup completion timeout | bound | 75.305 / 69.919 / 49.575 ms | authenticated, exit 0, 1.439 s | FAIL: deauth PID 33 timeout; no stage 3; quiescence/return pass | 60.019 / 60 s PASS; cleanup stop +0.813 s | [one scalars file](results/gtk5-runtime-scalars.json) |
| GTK6 | `6f5dbd31-9ed7-4f91-9c42-6a7ccd432bfd` | no named HIF refusal; command-path credit observed | bound | 94.942 / 89.260 / 37.169 ms | authenticated, exit 0, 1.739 s | FAIL: missing deauth; PM abort credited with one retained page; whole-ledger stop | 60.015 / 60 s PASS | [one scalars file](results/gtk6-runtime-scalars.json) |
| GTK7 | `138674d4-2aff-4ff5-ad75-a0670d432b36` | no named HIF refusal; six cleanup command paths credited | bound | initial 3/3; periodic 5/5 | authenticated, exit 0, 1.618 s | stage 3, zero debt; deauth missed bound, late status 5; return verified | 60.011 / 60 s PASS | [one scalars file](results/gtk7-runtime-scalars.json) |
| GTK8 | `a996ec5e-fc20-49d3-a160-2ed321e3e156` | no HIF refusal; release + five cleanup commands credited | bound | initial 3/3; post-release 5/5 | authenticated before release, exit 0, 1.397 s | host stage 3, zero debt; late deauth status 5, no ACK; return verified | 60.009 / 60 s PASS | [one scalars file](results/gtk8-runtime-scalars.json) |
| S1 | `cff2c4f8-466d-406b-a7ad-d9f1e8bfee1e` | no HIF refusal; release + five cleanup commands credited | bound | initial 3/3; post-release 5/5 | fresh authenticated stream, five chunks / 20.450 s across release; exit 0 | stage 3, zero debt, deauth ACK; return verified | controlled disconnect, 55.502 s data; not full 60 s | [one scalars file](results/s1-runtime-scalars.json) |
| I50 | `e8a4c5ca-1fda-42ad-a0f7-1b68e99c08f7` | no HIF refusal; release + five cleanup commands credited | bound | initial 3/3; periodic 4/4 | NOT REACHED: host helper namespace refusal before client/TCP | stage 3, zero debt, deauth ACK; return verified | 50.005 / 50 s PASS; full-session FAIL | [one scalars file](results/i50-runtime-scalars.json) |
| P1 | `b79d576c-5449-4899-8260-a61f350e0a5d` | no HIF refusal; 154/154 data TX completed; 32 completed PID reuses | bound | initial 3/3; periodic 6/11, five not reached | authenticated; 116 ticks / 57.563 s received; exit 255, server maximum duration | whole-ledger stage 3, deauth 127 ACK; preservation continuation and changed Gemian verified | 63.924 s data; received SSH 57.563 / 120 s FAIL, harness limit | [one scalars file](results/p1-runtime-scalars.json) |

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

## Latest owner direction after D3: group-first, permanent client evidence

No further ARP-pair boot. Prepare initial GTK before the separate framing
comparison, following the [source contract and predeclared preparation](MAC80211_GROUP_RX_CONTRACT.md#predeclared-initial-gtk-preparation).
The 60-second observation is also a timeout discriminator: retain the original
single connect call and verify that its entire measured duration lies inside a
live, authenticated device data window. Kernel/USB liveness alone is not enough
if a resource cap already closed the station data phase.

Both earlier failed receipts returned 255 after approximately ten seconds from
readiness: C10 #2, 4.3 to 14.3 s; C11, 3.8 to 13.8 s. Their owned helpers were
not timed out, and the client returned rather than being killed by the host.
D3's 1.410-second successful client exchange leaves about 0.29 seconds of other
work in the rounded post-readiness interval. Record the earlier signature as a
roughly ten-second silent failure, not a fast local refusal. Its client stderr
was discarded, so the exact TCP/SSH stage remains unproved. For the connect
silence hypothesis, keep SYN-not-emitted and SYN-unanswered explicitly separate;
received-frame counts cannot decide between them.

Authentication with a longer live window is consistent with transient delivery
or retry timing, not proof of a particular lost packet. A repeated ten-second
failure entirely inside a live data window supports investigating a persistent
path problem. Neither branch justifies silently increasing a timeout or
claiming a cause from one outcome.

The standard owned session now selects [permanent client retention](laptop-wifi-ssh-retain.py).
It reuses D1's full stdout/stderr/exit/timing retention and original verifier/ACK
rules for every standard lifetime, not a purpose-built diagnostic boot. Its
active route observation is `netstat -rn -f inet`, with the numeric ARP reads
retained around the client. The complete routing table stays private. This
command succeeded unprivileged in the same helper sandbox (exit 0, 1,517 stdout
bytes, empty stderr); it sends no probe and needs no privilege or cache change.
The completed D1/D2/D3 source inputs remain historical at their recorded commits.
Seven focused standard-client cases pass locally, including default host dispatch,
retained failed-client stderr, unknown-route handling and the owned GTK receipt
namespace, early data-window closure and an unknown post-client probe. The
standard path takes one bounded read-only USB snapshot after the client; it
records open/ended/closed-or-fault/unknown without changing the client verdict
or ACK. This checks the driver admission state, not continued AP association.
All seven cases pass on Linux from clean pushed input `4bde0dbf`; the
independent window checks previously passed there at `5b92d39a`.

## GTK1 result and smallest justified correction

GTK1 is **NOT REACHED** for data, GTK and network/SSH, and consumed once. Firmware reported a validated 65,000 ms channel grant;
PTK and GTK command credits returned. Before the data window could open, the
host required 62,500 ms remaining but reported only 9,466 ms and stopped with
`-ERANGE`, branch 8. No ACTIVE data window, DHCP, ping, listener, Wi-Fi SSH or
checked GTK queue was reached. The withheld-ARP counter was not emitted and is
unknown, not zero. This does not classify the intermittent SSH failure.

The retained source explains the refusal: scan completion creates the existing
10-second setup deadline; channel-event handling stores
`join_grant_deadline = min(join_deadline, now + validated_interval)`. Thus the
65-second resource horizon is clipped to the setup deadline before the new
62.5-second admission check. This is host bookkeeping, not evidence of a short
firmware grant. Healthy cleanup stage 3 was absent. All 63 seal entries and
2,035 contiguous log records independently verified; helper/device quiescence,
A53 regression, one reviewed return and changed-boot Gemian confirmation passed.

The next logical correction will retain the actual validated resource horizon
for the independent 60-second selection while leaving the 10-second setup
and all command/frame/teardown limits unchanged. The setup must still finish
within its existing deadline; only after successful key admission may the
already-approved 60-second data phase replace it. No extra firmware operation,
register access, framing rule, resource-cap change or longer transaction timeout.

Before implementation, the hypothesis is that this separates channel ownership
from setup admission and permits the already-approved window when the actual
grant is sufficient. The regression must feed the actual grant-event branch
into the actual data-opening function, reproducing the parent refusal and
checking the successor without manually inserting a long grant deadline.
A valid sufficient grant may open 60 seconds; a genuine short/expired grant
must still refuse without publication; an expired setup must still stop.
The later device trial must report actual GTK exposure, duration and the first
limit/fault reached separately. No unchanged GTK1 retry is admitted.

The follow-up researcher review agrees on decoupling the grant horizon. Its
claim that no key command was submitted and cleanup was healthy conflicts with
the sealed records: pairwise/group submissions are sequences 2021/2025, credit
returns 2024/2028, window refusal 2029, and the consequent `set_key` error 2030.
There is no healthy stage-3 record. Quiescence and reviewed recovery are separate
successful verdicts. The GTK path is unmeasured, not failed by this run.

`join_deadline` fences every join phase, including commands and frame progress;
it is not merely a grant timer. Keep that fence unchanged until the existing
successful data-opening transition installs the already-approved data/teardown
deadline. Retain the exact +/-1 ns opening boundary. Earlier roughly six-second
windows reflect host-requested grant/setup caps and the 2.5-second tail, not a
proven firmware lifetime ceiling. Ten-minute operation needs persistent station
and channel ownership/monitoring; another increase of the finite join constant
is not that implementation.

## Corrected grant successor: 0205 prepared

[0205](../../patches/proposals/0205-wifi-mt6797-retain-the-validated-channel-grant-horizon.patch)
changes only the grant-event branch under `CCMP_60S_WINDOW`. It stores the full
validated horizon separately from the unchanged join-phase deadline. A grant
below 62,500 ms returns ERANGE before successful channel completion, association
or key commands, while recording the acquired firmware resource. The existing
terminal path wakes the failed waiter and preserves poison; early refusal is
not a claim of healthy firmware cleanup. The authoritative late check is
byte-identical and still accounts for time consumed by setup.

[Actual event-to-window tests](tests/run-grant-horizon-test.py) reproduce the
parent's exact 9,466 ms remaining value, open the successor's 60-second window,
check +/-1 ns at the late boundary, all 65,000 positive millisecond event
intervals at the early boundary, malformed/truncated events, resource retention
on early refusal and option-off MAC parity. The selected GTK callback fixture
also refuses publication when the unchanged 10-second setup limit expires
during the credit wait. Source changes no setup/command/frame/teardown limit,
PN gate, resource cap, HIF operation or the late ERANGE check.

All three profiles selecting the independent 60-second window include this
correction in canonical order; 0202 remains separate and is not selected by the
initial-GTK profile. Source-only tests prove host decisions, not firmware channel
ownership, GTK integrity or sustained Wi-Fi. Linux host validation and one
corrected GTK kernel build precede the next guarded physical handoff.

## GTK2 corrected build and session preparation

The single requested corrected build completed from clean pushed input
`7fe3d616`, profile `mt6797-a53-wifi-ccmp-initial-gtk`, 32 jobs, modules disabled.
The actual grant/GTK/canonical-overlay tests pass on Linux from that same input;
0205 checkpatch has only the deliberate missing DCO error, zero warnings/checks.
Standard package validation/fetch passed. Configuration, DT and RAM root remain
byte-identical to GTK1; its 60-second window and every other limit are unchanged.

| Input | SHA-256 |
| --- | --- |
| Package inventory | `34b72953368b5850ef35694a5689b00f14a61089107822d177daee849e72b4e9` |
| Image.gz | `2b642f01eb6904520054c17f0ed3ad05d91fcd30972afcfeb67795afae3bf97f` |
| Patchset | `675229435abd9c3c2f1db86ae503e5a2419e67fec477578e00498e7b49d638fc` |
| Candidate receipt | `a557a7b7c5c53ddbff10948e9e79119d656016c65e4cf5ca7f3cea29de08ecac` |
| Full boot2 image | `f567d6666b106d1ecc2eaadc12022ab27306b210eabd274aa1c44c2985b95e6e` |
| Live kernel notes, exactly 84 bytes | `c1262456dede57a2594156919d1ba117019b82902c274b05f72e4989f92d3bba` |

The [GTK2 compositor](build-ccmp-gtk2-candidate.py) retains the actual-parent,
inventory, configuration and container checks; the [real receipt](results/ccmp-stable-monitor-candidate-gtk2.json)
equals its [runtime binding](runtime-ccmp-gtk2/results/candidate.json). All private
members have verified size/hash/mode. ELF notes, System.map and packaged Image
agree, and the read-only live fingerprint differs from GTK1. Fresh session and
installer adapters require this receipt, the corrected horizon flag and the
62,500 ms early minimum. Their five local fixtures and all five Linux fixtures pass from clean pushed
tooling `b6ff824b`. The reviewed installer and completed handoff gates follow.

The next admitted GTK2 lifetime separately measures checked GTK queue exposure
and withheld-ARP count, DHCP/individual pings, fresh SSH stage/output, actual
window and cleanup. A sufficient grant plus the host correction permits the
window; it is not itself a protected-data result. Do not count a cap-ended
short run as a 60-second pass. Retain permanent client stderr and the existing
quiescence/preservation/regression/recovery gates. No GTK2 test has started.

## GTK2 guarded installation and handoff

The derived installer is 603 lines, SHA-256
`5d8e76d5f666b7495b57aabf671e7c910d723d977ad74c18c6e1e935160a6c82`.
It matches GTK1 under candidate/tool/receipt/predecessor/boot identity changes
only; Bash syntax and ShellCheck pass. The boot2 guard remains byte-identical.

One execution completed with exit 0 from freshly verified Gemian boot
`9ff760f3-c66a-4aaf-9b91-95a2b48bc26b`. Both live GPT/root/unmounted/inactive
checks passed, with the exact GTK1 predecessor, stable power and correct size.
Write/sync/flush and full 16 MiB readback matched GTK2; receipt validation and
clean shutdown passed. The final summary seal and exact mode-0600 runtime copy
were independently verified. No other partition write or automatic reboot.

Complete actual offline session preparation passed with Wi-Fi client keys/boot
environment unset. The new session contains only the sealed deployment summary;
capture, execution claim and client remain absent. Owner physical boot2
selection with USB connected to the custodian laptop is next. Afterward require
a fresh boot and the exact 84-byte GTK2 notes digest before the one capture and
admitted lifetime. GTK2 has no runtime result yet. All prior failed artifacts
remain consumed; no unchanged GTK1 retry is selected.

## GTK2 consumed: capability pass, duration fail

GTK2 ran once on verified boot `f77aa006-7757-40b3-960e-2a96ddc82804`.
Capability **PASS for this finite run**: a strictly checked GTK frame was queued,
DHCP bound, three individual ICMP replies arrived, and fresh boot/mode/listener-
bound SSH authenticated in 1.410 seconds with exit 0 and empty retained stderr.
The post-client USB snapshot still showed an open driver window. Host cleanup
stage 3 completed; group-removal credit and local disable status 0/no_reuse were
observed. These are not firmware key-retirement or independent core GTK-delivery
proofs. `withheld_arp=0` describes the eligible rejected class, not ARP arrival.

Duration **FAIL**: the existing combined checked-frame cap reached 64. The close
transition was observed at +5.902 seconds, and the data window ended at 5.925
seconds against its full 60,000 ms budget. The 65,000 ms grant and full-budget
opening demonstrate the grant-horizon correction, but not sustained operation.
There was no named HIF refusal or join fault. No unchanged retry is selected.

ACTIVE classes were `t2=64`, `t7=132`, with native-gate `blocked=0`.
ENABLE_PENDING had one blocked frame; do not claim every phase had zero blocks.
The total sample was 198 RX records and 43,974 logical bytes; CLOSED additionally
reported ten type-7 records. Type-7 counts are not independently identified
beacons here. Flat extrapolation gives roughly 2,000 RX records, 650 checked
frames and 445 kB over 60 seconds, with startup/phase boundaries and traffic
variation limiting those estimates. TX 28 was a startup burst, not a measured
steady rate; its non-reusing PID ceiling remains a separate possible stop.

All 71 pre-recovery entries, including all eight client observation files, and
2,115 contiguous log records independently verified. The actual one-cycle
export was complete; the inherited two-cycle completeness flag correctly stayed
false. Helper/device quiescence, A53 regression and one reviewed return passed.
Changed-boot Gemian `cbab7eed-8b34-44de-a9a4-f95cc8fe9838` was independently
confirmed. The finite compatibility process returned 0; it is not a 60-second
acceptance result. Initial neighbor absence followed by completion does not
prove a resolution mechanism or explain earlier SSH silence; D3 passed without
GTK delivery.

## Next admitted preparation: low-traffic 60-second measurement

The owner directed review/action on the researcher's revised budget, superseding
the earlier unchanged-cap constraint for this bounded successor. Select
**1,024 checked CCMP frames, 4,096 total RX records and 2 MiB RX bytes** only for
the approved CCMP 60-second mode. Keep native-ciphertext limits, the 65-second
request, 60-second wall, 10-second pre-data join fence, 2.5-second grant tail,
5-second teardown, 100 ms command, 750 ms frame/drain, retirement, poll and PID
limits unchanged. No PID reuse. The proposed protocol is explicitly low traffic:
one DHCP, three pings, one fresh SSH authentication, then observation to the
planned end. It does not demonstrate sustained SSH traffic for sixty seconds.
Any different first limit or fault is a separate result, not an automatic retry.

Add checked PTK/GTK totals to the terminal counters and count GTK ARP at the
actual driver-to-core handoff after readiness checks, without payload/address
logging, PN changes or new HIF acquisitions. Label the counter's scope: a core
handoff call is not independently observed stack delivery. Reject stale queued
frames without counting them as handed off. Initial ARP absence, a positive
GTK-ARP handoff count and SSH authentication in the same run support the group-
ARP hypothesis but do not establish sender/target attribution or sole causation.
The hypothesis is that these budgets permit a full low-traffic observation;
actual counters, duration, SSH stage and cleanup decide the result. Strict PN,
key ownership, no rekey/reuse/reconnect and no -48 adjustment remain mandatory.
Persistent station/channel ownership and connection monitoring, not further
finite-window duration increases, remain necessary for ten-minute acceptance.

## GTK3 source preparation: capacity and handoff observers

The admitted successor is implemented as two logical archives:
[0206 capacity](../../patches/proposals/0206-wifi-mt6797-bound-low-traffic-CCMP-observation-capacity.patch)
and [0207 observers](../../patches/proposals/0207-wifi-mt6797-report-checked-key-classes-and-GTK-ARP-handoff.patch).
0206 applies the 1024 checked / 4096 all-RX / 2 MiB limits only to CCMP in the
60-second selection, at prospective read, post-read admission, checked queue
and state transition. Native ciphertext budgets remain 64 / 512 / 1 MiB;
retirement and all existing time, poll, PID, transport and crypto rules remain.
Every profile selecting the window includes 0206; only the initial-GTK series
selects the GTK observers. No configuration change or new control interface.

0207 adds exactly two counters: checked GTK queues (PTK is total minus GTK)
and GTK ARP handoff. The terminal reports `queued_ptk`, `queued_gtk`,
`delivered_arp` and the existing `withheld_arp`. `delivered_arp` means a current,
ready group Ethernet frame with EtherType 0x0806 passed to the existing core RX
call. It is counted after the queue/withdrawal decision under the MAC mutex,
not when merely queued. No ARP payload, addresses or PN are retained; no new
HIF acquisition or delivery predicate. A core call does not acknowledge stack
acceptance or identify the SSH peer's ARP.

The [actual-source fixture](tests/run-initial-gtk-test.py), selected with
`--gtk3`, reverses the two overlays and 0204 to recover the exact parent, then
checks GTK-off parity against the same capacity policy. Local ASan/UBSan tests
pass the unchanged 19,007 checker cases, actual native differential engine,
all four capacity gates and boundaries, unchanged native limits, exact queue
splits, ARP handoff versus replay/PTK/non-ARP/stale queues, existing withdrawal
threads and unchanged setup-expiry refusal. Both crypto helpers and all HIF
files remain byte-identical. Host simulations do not establish firmware effects.

The [GTK3-only verdict](classify-ccmp-gtk-budget.py) reuses the frozen one-cycle
protocol/SSH/cleanup grammar in a separate instance with the admitted capacities.
It grades finite capability and duration independently and rejects a short or
quota-ended run as a qualified 60-second result, including a drain that crosses
the target time. It requires consistent split/ARP counters and a positive GTK
queue event. A zero ARP count means no such handoff was observed; it is not itself a failed
GTK capability and does not rule out an earlier arrival or queue.
Default historical classifiers retain their old limits. Synthetic parser cases
cover boundaries, malformed/duplicate records, quota/drain, failed SSH/protocol
and scope preservation. The new session binding must explicitly select this
verdict; preparation is not yet a device admission or result.

Clean pushed input `a32ddfce` passed Linux actual-source fixtures for both the
GTK selection and the separate fixed-format overlay, plus the verdict and
historical binding fixtures. The first attempt exposed only a patch-context
conflict beside the fixed-format guard; 0206 now selects the capacity helper
before that unchanged guard and applies to both. Strict checkpatch reports only
the intentionally absent DCO certification, with zero warnings/checks.

The standard Buildbox build and package validator passed from `a32ddfce`:
700 patches, package inventory
`d960f2c6f48ad8a2be0a1ed5810485bc770a55022b8ff6a7cbd3516539c2a8cc`,
unchanged GTK2 configuration. The [actual receipt](results/ccmp-stable-monitor-candidate-gtk3.json)
and [compositor](build-ccmp-gtk3-candidate.py) bind this package and the capacity /
handoff archives. Kernel ELF notes, Image bounds and the sysfs exporter agree;
the 84-byte identity differs from GTK2. Local composition, namespace/refusal,
no-scan, retained installer and recovery-source checks pass. The new binding
explicitly selects the GTK3 verdict in both standalone and session paths.
All five tooling fixtures also pass on Linux from clean pushed `2aa30db2`.
The generated 603-line installer differs from GTK2 only in identities, retaining
the exact reviewed boot2 guard; Bash syntax and ShellCheck pass. Guarded
installation exited 0 after full readback, sealed deployment evidence and clean
shutdown. Independent seal/summary checks and offline host preparation pass.
GTK3 now awaits owner physical boot2 selection; no radio run has started.
Fresh boot identity and kernel-notes verification remain mandatory before the
single admitted session. This is a handoff, not a runtime table row.

The candidate remains low traffic: no PID reuse and no continuous SSH workload
is promised. If a different ceiling binds or a protocol, transport or cleanup
fault occurs, record that first point separately. Compilation and host fixtures
are not a GTK3 runtime result.

## GTK3 consumed: network observed, control-event stop before 60 seconds

The single admitted run used kernel `a32ddfce`, tooling `2aa30db2`, handoff
`254c4868`, and fresh boot `1fa923f3-aab1-43e1-83f9-f6d12c2aa422`.
Strict GTK queue and driver-to-core ARP handoffs were observed: checked PTK 35,
checked GTK 132, ARP handoffs 53, eligible withheld ARP 0. DHCP bound, individual
pings replied in 84.587 / 51.334 / 38.912 ms, and fresh SSH authenticated with
exit 0, retained empty stderr and a still-open post-client window. The client
process took 1.256 s (the numeric-neighbor observer's inner call measured
1.231 s). Initial neighbor was absent, then complete; route snapshot succeeded.
This is supporting correlation, without peer attribution or GTK-causation proof.

The first fault was a completely transferred 12-byte control event,
`type=0xe000 id=0x13 seq=0`, refused by the host dispatcher with `-EPROTO` at
29.825 s after data opening. Its generic header passed, but the dispatcher has
no 0x13 branch and returns `-EPROTO`. The fault terminal is branch 6, `first=0`,
no page debt or inflight frame, last PID 32, 28 data TX all completed, and
1,243 polls below 4,096. Checked count 167 is below 1,024; observed acquisitions
542 are below 4,096, and even 542 maximum-size 2,352-byte reads are below 2 MiB.
Thus this is a different first failure, not the enlarged sample capacity.
The subsequent device disconnect ended data at 30.144 / 60 s. No named HIF
length/read refusal or framing hint occurred. The final sample-byte counter
was not emitted on this fatal path; do not invent a terminal byte count.

Healthy stage 3 is absent; both local key-disable callbacks returned `-71`
without credited removal. Quiescence, A53 regression and one reviewed return
passed. All 71 seals (including eight client files) and 2,097 contiguous records
were independently verified; a separate authenticated check confirmed changed-
boot Gemian `34302162-2a50-400f-85d9-d7b92ef826c7`. The strict classifier remains
failed for finite session, duration and healthy cleanup. Positive network/GTK
observations do not convert the faulted session into a pass. No retry occurred.

A bounded public-source check identifies event 0x13 as
[EVENT_ID_BSS_BEACON_TIMEOUT](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic_cmd_event.h):
its four-byte body contains BSS index, reason and two reserved bytes. Header
SHA-256 `93c8d67b1bc039a8db5b635e5a00975f2b9e408f4ab1bc8a384f5db49bf00a3a`
matches the retained earlier copy. The
[pinned receiver](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_rx.c)
(`a844bdf75065a152e78d30c789aabb398b0d0f336d30d6ffd028793bf091412b`)
checks BSS ownership, ignores reason 8 (no TX-done), and also ignores a timeout
when its last-RX timestamp is within two seconds, before connection-loss handling. GTK3 did not retain either body scalar, so its BSS ownership,
reason and underlying timeout cause are unmeasured. Do not ignore the event or
call this merely a harmless whitelist gap.

### Predeclared successor diagnostic

Hypothesis: the first sustained failure is an owned BSS timeout notification;
its already-acquired BSS/reason bytes distinguish a TX-completion-watchdog report
from other beacon-timeout reasons or foreign-BSS drift. Retain only those two
scalars for exact 12-byte 0x13 events with sequence zero, before the existing
fatal refusal. Also retain one host-clock timestamp at strict checked PTK/GTK
queue admission and report its age/known flag at this event. This gives the
recent-checked-data discriminator in the same boot; it is narrower than the
vendor's general last-RX clock and does not reproduce its policy. No payload,
address, new register read, event acceptance, deadline, channel or key change. Other headers and malformed lengths stay on the current refusal.

Decision branches: owned BSS 0 / reason 8 leads to the firmware TX-completion-
watchdog contract despite host completions; owned BSS 0 / another reason leads
to beacon/channel/BSS monitoring, distinguishing checked data within two seconds
from older or absent checked data; foreign BSS leads to ownership/configuration
drift. Recent host data qualifies the comparison with the vendor's ignore path;
it does not itself authorize ignoring a firmware event. A malformed or nonzero-sequence event remains a wire/state refusal.
Reason alone is a report, not proof of the physical cause. Preserve the same
60-second low-traffic protocol and strict fault stop; do not repeat GTK3 unchanged.

The diagnostic is implemented as
[0208](../../patches/proposals/0208-wifi-mt6797-observe-refused-BSS-timeout-and-checked-RX-age.patch),
selected only by the initial-GTK series. It adds one host timestamp at checked
queue admission and observes exact timeout scalars only on the existing
control-event refusal path. The control admission function is byte-identical;
no event is accepted, no resource ledger changes and no extra HIF read occurs.
Age is truncated to milliseconds, not an exact firmware/RF timestamp.

The existing actual-source runner's `--timeout-observer` mode passes locally
with ASan/UBSan: unchanged 19,007 crypto cases, all BSS/reason byte combinations,
malformed length/header/sequence silence, unrestricted reserved bytes, absent
or future clocks, two-second +/-1 ns age rounding, strict PTK/GTK-only clock
updates, allocation/replay/stale refusal, existing withdrawal threads and
option-off full MAC parity. Reverse application recovers GTK3 exactly before
the earlier overlays. Strict checkpatch has only the deliberately absent DCO
certification, zero warnings/checks. Clean pushed `aabc1cc3` passed the same
Linux fixture on the initial-GTK and separate fixed-format source selections.
The standard Buildbox build/package validator also passed: 701 patches,
unchanged configuration, package inventory
`4fc69aa055b443b5200d9011cc6687cce6ef27ee4822aa8e590bd42e81c5be02`.
This is preparation, not another device result.

### Researcher follow-up: reason first, then owned state handling

GTK3 has a positive capability observation for checked GTK/ARP core handoff and
network/SSH, alongside failed duration, full finite session and healthy cleanup.
The terminal phase-1 counts are type 2 = 174 and type 7 = 367. Their aggregate
rate is not evidence of uninterrupted, owned-AP beacon reception or an
undegraded link. The last PID 32 is far below the existing ceiling; no PID reuse
is justified here. `reason=disconnect` names host cleanup after the branch-6
fault, not a firmware link-down report. The refusal offset is 29.825 s; the
subsequent data-end offset is 30.144 s.

The reason-first diagnostic was already building when this follow-up arrived.
The pinned receiver can ignore reason 8 and can ignore other reasons when RX
is recent. Thus reason 8 does not prove a host retirement defect, and another
reason does not prove an RF failure. Record BSS/reason and the qualified RX age
before selecting a correction. The four-byte body was staged but not retained
in GTK3; a later read cannot recover those original bytes.

The suggested 0x16 connection indication is a concrete contract to investigate,
not yet a demonstrated fix. The pinned
[command builder](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic.c)
(`6ccae6fbbd21287df1247720f2056c3961a5d1cdeeba5bcc2246a6e8de4b0ce4`)
uses the header's 12-byte layout and no query response. The current host has AID
and beacon interval but no retained DTIM or 0x16 encoder/admission. The
[infrastructure join path](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/mgmt/ais_fsm.c)
(`738b8fcf0d34098fef986c1dba4963ebe0676665b0a914d7a712a50e814838ba`)
defers this indication until the first post-association beacon. The
[beacon consumer](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/mgmt/scan.c)
(`2671e377dde82be4eea99477557596963b060e2a0948b94094da296de0daa161`)
requires connected infrastructure mode, matching BSSID and a beacon, then
updates DTIM and submits 0x16. A future implementation needs that owned fresh
beacon/DTIM contract, bounded command credit and disconnect/abort ownership;
constant defaults or unconditional post-association submission do not match
this path. 0x15 belongs to BSS creation, including the separate ad-hoc path;
its absence alone is not a station-join defect. Header definitions do not prove
runtime firmware acceptance.

No blanket count-and-continue event family is selected. 0x11 is already a
modeled owned-BSS absence/presence notification; the selected GTK path admits
it only during credited BSS-off teardown, while other profiles add a TX gate.
0x12 is
station power-save, 0x14 NoA, and 0x18 roaming status. These need exact shape,
ownership and state consequences, particularly with roaming disabled. Replace
unmodeled fatal stops with source-supported handlers as their contracts are
established; do not conceal connection loss or resource changes. 0208 preserves
the refusal while retaining the currently missing discriminating evidence.

### GTK4 replacement package and host preparation

The first GTK4 package at `aabc1cc3` was validated but never installed. The
[actual GTK4 receipt](results/ccmp-stable-monitor-candidate-gtk4.json) now binds
the replacement Buildbox input `8ac513a3`, source
`bfa21f93137e034c4c1ad474bc97763aee119aab`, 0208/0209 and the 702-patch series.
Package inventory is
`528fdc5eb220a32c7d7803abe6ceb6ca4f820bc7404114a811cfe1e13ce05bee`.
Config, DT and RAM root are identical to GTK3. ELF notes, Image bounds and the
sysfs exporter agree on the fresh 84-byte identity, different from GTK3. The
new namespaces retain the GTK3 duration-aware verdict, permanent client stderr,
numeric neighbor/netstat and post-client window check. Five local tooling
fixtures pass; the replacement 603-line installer has identity substitutions
only from GTK3, with unchanged guard and passing Bash/ShellCheck.

The added beacon-clock source fixtures pass locally and on Linux from clean
pushed `8ac513a3` for both initial-GTK and fixed-format overlay selections. The
standard kernel build and package validation passed. All five replacement
Linux tooling fixtures passed from clean pushed `77760306`. The reviewed
603-line installer exited 0 after guarded boot2 write, matching full readback,
sealed deployment evidence and clean shutdown. Independent seal/summary checks
and actual offline host preparation passed. The owner then selected boot2;
GTK4 was consumed once as recorded below. Only observation was added; neither
0x16 nor event-family/late-completion tolerance was bundled.

If no timeout recurs and the complete window/cleanup pass, report that run's
success and the untriggered diagnostic, without claiming the original timeout
was fixed. An event with missing/malformed observation remains unclassified.

### GTK4 gap closed before installation: owned-beacon recency

The first GTK4 package/tooling passed validation but was not installed or run.
The new review correctly identifies that idle checked-data age alone cannot
distinguish a healthy quiet link from loss. Before physical admission, extend
the same observation with the existing owned-beacon admission count and one
last-beacon queue timestamp. Stamp only the existing successful beacon-delivery
helper, reached through the already validated clear/keyed/native target-beacon
paths. It checks the AP/channel upstream; no new decoder, delivery rule or wire
access is introduced. A generic type-7 timestamp would be misleading because
control events, probe responses or other APs could refresh it. Counts include
post-association beacons before data opening; record that scope. Age is a host
admission clock, not proof of firmware beacon recognition.

Predeclare every outcome, with the timeout event offset measured from the data-
start kmsg timestamp (GTK3 first refusal 29.825 s; later end 30.144 s):

| Outcome | Interpretation and next decision |
| --- | --- |
| Owned BSS, reason 8, recent admitted target beacons | Firmware no-TX-done report alongside a working host beacon path; investigate completion/idle and monitor contracts, without asserting a proven retirement defect. |
| Owned BSS, reason 8, no recent admitted target beacons | Both watchdog report and host beacon-observation gap; distinguish RF loss from host filtering/format or channel ownership before a fix. |
| Another reason code, recent or absent admitted target beacons | Record both dimensions; recent owned admissions support a firmware/host monitor discrepancy, absence alone does not prove RF loss. |
| Foreign BSS, malformed shape/sequence, or absent observation | Preserve refusal; ownership or evidence remains unclassified. No invented reason/zero-age freshness. |
| Event does not recur, full 60-second window and healthy cleanup pass | Pass for this low-traffic run; diagnostic untriggered, original timeout not established as fixed. |
| Event does not recur but another limit/fault ends the run | Separate first-failure result; no automatic retry or nominal-duration pass. |

The known 0x0f fragility is separate: the current worker refuses a TX completion
without the exact in-flight PID. Future handling must distinguish a completion
owed by the current lifetime from stale/unowned notifications before allowing
discard; the next diagnostic changes neither behavior nor PID reuse. No generic
late-completion tolerance is bundled. Sequence/generation ambiguity remains part
of reusable lifecycle ownership. Single-inflight TX pipelining is a roadmap item,
not a gate for this low-traffic run. A future 0x16 uses the existing sequence and
page-credit discipline at the owned post-association beacon/connection indication,
before traffic, with disconnect/abort ownership; never inject it at data opening.

[0209](../../patches/proposals/0209-wifi-mt6797-retain-owned-beacon-recency-at-refused-timeout.patch)
implements the added clock and includes `beacon_known`, `beacon_count` and
`beacon_age_ms` in the timeout observation. It reuses `join_beacons_delivered`
(the existing queue-admission count, despite that legacy name) rather than
adding another counter. The complete join-worker dispatch remains byte-identical;
only the existing successful beacon queue helper gains a timestamp. Actual-source
ASan/UBSan fixtures pass for clear/keyed queue clocks, allocation refusal,
idle checked-data versus recent beacons, zero/future clocks, old/recent ages and
two-second +/-1 ns rounding, with unchanged crypto/gates/withdrawal/option-off
parity. The first fixture extraction duplicated an already included helper;
that fixture-only duplication was removed before the passing run. Checkpatch
has only the intentional missing DCO, zero warnings/checks. Clean-input Linux
source checks and the replacement package passed; tooling/deployment gates are
recorded above. The first prepared GTK4 image must not be installed for this
revised diagnostic.

## GTK4 consumed: owned timeout with recent admitted beacons

The run used kernel `8ac513a3`, tooling `77760306` and verified boot
`c2efe494-648e-44ca-9bb1-519ffce4496d`. Initial capture passed all 285 steps.
The exact 12-byte event (`0xe000`, id 0x13, sequence 0) reported BSS 0, reason 6.
At its observation, checked-data age was 287 ms; the owned-beacon clock was
known, with 293 successful queue admissions and age 71 ms. The event observation
was 29,811.219 ms after data opening, followed by the preserved header refusal
at 29,813.401 ms and branch-6 `-EPROTO`. The data phase later ended under host
`disconnect` cleanup at 29,955 / 60,000 ms. GTK3's corresponding header refusal
was 29,824.588 ms: the repeated near-30-second offset supports a monitor-window
hypothesis, without proving its origin or configuration.

This follows the predeclared non-8 reason with recent owned beacon and checked-
data branch. It argues against a simple absence of host-admitted target beacons;
it does not decode reason 6 or establish a complete RF stream. The pinned host
header names reason 8 only. A detailed reason-6 mapping, if needed later, needs
an explicit bounded VM emitter question rather than inference from a code table.
Beacon intervals are TU (1.024 ms), as the pinned Linux `TU_TO_JIFFIES` conversion
shows, not milliseconds. The admission count includes pre-data frames, does not
deduplicate sequence numbers, and carries host queue times. It cannot prove
completeness or an exact missed-beacon count from 293/window. No DTIM or runtime
beacon-interval value was retained in this result.

Capability observation passed: checked PTK/GTK 35/114; GTK ARP handoffs 55,
withheld eligible ARP 0; DHCP bound; replies 99.248 / 37.802 / 37.563 ms; fresh
SSH authenticated with exit 0 in 1.325 s and retained empty stderr while the
post-client window was open. Initial neighbor was absent then complete; route
snapshot passed. These are independent observations, not GTK-causation proof.
Full finite-session, duration and healthy-cleanup verdicts failed. Healthy stage
3 is absent and both local disables returned `-71` without removal credit.
No named HIF length/read refusal or framing hint occurred. At the fault, 1,248
polls, 149 checked frames, 519 acquisitions and last PID 32 were below their
binding ceilings; all 28 data TX completed. No retry occurred.

All 71 sealed entries, eight client files and 2,098 contiguous records
(167,539 bytes) independently matched. Helper/device quiescence, A53 regression
and one reviewed recovery passed. A separate authenticated check confirmed
changed-boot Gemian `4256d0ec-11e4-4e84-8202-6b2e78281876`. No key retirement,
reuse, reconnect or sustained-operation acceptance is established.

### GTK5 admission and source preparation — incomplete hardware gate

The latest selection supersedes the conditional continuation draft published
in `ef2e2fc3`. That input compiled and packaged, but its image is not admitted
for a device test. Preserve that commit as an attributable compile-only result.

The revised candidate contains three logical archives:

1. **0210 observation/count only:** retain the exact acquired event body, the
   owned-event count, checked-data and owned-beacon ages and committed interval.
   Keep the existing fatal control-event dispatcher byte-identical. Fresh
   beacons do not permit continuing after an event. No reason interpretation,
   credit, TX, key, event-family or deadline change.
2. **0211 connection/abort indication:** the public vendor driver sends 0x16
   after association, using the first qualified owned beacon's TIM/DTIM with
   the validated AssocResp AID and committed interval. Follow that ordering
   through the existing sequence/page-credit path before keys and traffic,
   within the existing association phase and command deadlines. Missing valid
   metadata, refused submission or missing credit stops before keys. Credit
   proves buffer consumption, not an explicit firmware status reply. On healthy
   teardown, send 0x17 and require its credit before key/station removals.
3. **0212 mac80211 ownership:** advertise `IEEE80211_HW_CONNECTION_MONITOR` only
   in the PM-required experiment. Report an unusable live-data terminal or
   healthy teardown once through the standard connection-loss API. Keep nullfunc
   outside the supported firmware Ethernet TX class. This finite test is not
   production monitoring or keep-alive enforcement evidence.

Local ASan/UBSan fixtures cover actual association/metadata waits, PM credit
before keys, deadline ±1 ns, pre-key failures, abort credit before removals,
exactly-once loss reporting, existing GTK/PN checks and option-off parity. The
actual HIF fixture covers exact 0x16/0x17 wire encoding and sequence/page debt,
including transfer cuts and expiry without refund. Synthetic host tests do not
establish firmware behavior. Strict checkpatch's sole deliberate exclusion is
the synthetic experiment author's missing DCO sign-off; this is not an upstream
submission. Linux fixtures and the revised build remain required.

One fresh GTK5 boot retains the 60-second low-traffic window, 65-second requested
grant, 2.5-second tail, 5-second teardown margin, 100 ms transaction deadlines
and all resource caps. Predeclare: pre-key metadata/submission/credit failure;
a refused firmware event with exact scalars and offset from connection
indication/data opening; an unexpected or unowned completion with PID and offset;
a first software connection-loss/nullfunc refusal; the full window with no
such event; or another independently recorded first failure. No event is silently
tolerated or retried. DHCP, three pings, SSH stage, GTK/ARP handoff, duration and
cleanup remain separate verdicts. Use one scalars file and one table row for
an actual run. Installation, physical boot2 selection and hardware result are
still pending.

The pinned mac80211 flag bypasses software beacon/idle probes. The translated
`RX_FLAG_8023` path updates `last_rx` for group data too; this driver does not
advertise RSS. Thus group traffic can refresh its software idle clock. A loss
notification following an already recorded driver stop is a consequence, not
a separate first monitor failure. An existing stage-3 notification alone did
not cover a fatal path; the candidate adds the missing live-data notification.

No nullfunc TX, PID reuse, rekey, key reuse, reconnect, -48 adjustment, broader
event tolerance or longer deadline is admitted. Restored research stays outside
Wi-Fi commits. Preserve published device measurements; keep firmware-RE
explanations and further private analysis out of public text. After a healthy
window, priorities remain trustworthy fault cleanup, connected-BSS data after
privilege release, standard monitoring and TX pipelining. No ten-minute or
reusable-lifecycle acceptance is established.

### GTK5 package and host binding — not yet deployed

Counter-only source input `fa3124b4` passed Linux actual-source fixtures for both
selected and canonical-overlay paths, then compiled through the required
Buildbox backend. Validated package inventory
`7f93e5fcfaf01b3c4715e119693302edc254c8b4af143d9c847c17fb4a2e2448`.
The real [GTK5 receipt](results/ccmp-stable-monitor-candidate-gtk5.json) binds
boot image `8bb9dc767c6f96dc65c48882318b0fe1286b26505cf2743a8ebe328b6da1c0f1`,
with unchanged GTK4 config, board DT and exact RAM root. Runtime notes are
84 bytes, SHA-256 `395ec929f1977d113bae6e0c21b09885f2eb6792ff4b80e82d6e3c0c8c509646`,
independently matched between ELF, Image, map bounds and the pinned sysfs exporter;
they differ from GTK4. This is a host identity check, not a live boot result.

Five focused host fixtures pass: composition/config oracle, actual receipt /
namespace wiring, no-scan ownership, retained recovery sources, and retained
installer sources. Six fresh GTK5 wrappers preserve completed hosts and guarded
installation. The expected predecessor is GTK4's verified full boot2 digest.
Guarded deployment, full readback, clean shutdown and fresh host preparation
still precede the owner's physical selection. No actual GTK5 run exists yet.

### GTK5 installed — physical selection pending

Tooling `e0cf5e17` passed all five Linux host fixtures from a clean pushed
checkout. The reviewed installer differs from GTK4 only in identity pins;
603-line guard/write/readback/shutdown logic, shell syntax and ShellCheck pass.
Live known-good Gemian boot `4256d0ec-11e4-4e84-8202-6b2e78281876` was verified
before the guarded installation. Live GPT boot2 identity and inactive/non-root
checks passed; predecessor matched GTK4. Full candidate and readback SHA-256
both equal `646f1869e9ad9c623d09cc901c237d6e7bf81caf550cd46d9613643974fabeb1`.
The deployment summary seal and clean shutdown were verified. No fresh backup
or other partition write occurred.

Fresh GTK5 runtime preparation and the complete offline host preparation pass
with the exact mode-0600 deployment summary and pinned recovery sources. No
mainline boot, capture or Wi-Fi session has occurred. Next action: owner selects
boot2 physically with USB attached to this laptop. Then verify a fresh boot and
the exact 84-byte notes identity before the single admitted capture/session.
Retain the predeclared outcomes and independent transport/network/SSH/cleanup /
duration verdicts; no retry or reconnect. Create one run scalars file and one
table row only after consuming the session. The earlier `ef2e2fc3` image remains
superseded and is not the installed candidate.

### GTK5 consumed — full window reached, post-window cleanup failed

The single fresh boot `f015f0f2-1320-4e12-98d5-dbacc7c69cb2` matched the
GTK5 notes identity and passed all 285 initialization checks. PM connection
credit returned with DTIM 3, interval 100 TU, AID 6 and keys `00`, before key
submission and data opening. The data window ended by budget at 60,019 ms.
No BSS-timeout body was observed; the owned counter is zero, and event refusal
was never relaxed. No unsolicited completion or first software monitor failure
was observed during the window. This is one measured outcome, not proof of a
firmware mechanism or of production monitoring.

Capability observations pass: DHCP, three individual ICMP replies and fresh SSH
authentication (exit 0, 1,439.179 ms, empty stderr) while the driver window was
open. Checked PTK/GTK queues were 35/237, GTK ARP handoffs 106, withheld ARP 0;
first GTK Ethernet length was 74 bytes. The numeric neighbor read was absent
before SSH and complete afterward; these records do not identify the peer of
an ARP handoff or prove that GTK caused SSH success. Resource caps did not bind.
The duration gate passes for a low-traffic window; continuous authenticated SSH
traffic was not tested.

The first stop is separate: after mask-disable credit and native state CLOSED,
the reserved deauthentication (subtype 12, PID 33, one page) was submitted. Its
completion did not arrive before the existing frame deadline. Branch 1 stopped
with `-ETIMEDOUT`, debt 1 and cleanup stage 0, 812.629 ms after the data-end log.
The retained scalar reports inflight 1 / PID 33, empty last pending-RX lengths,
TC4 free 25, pending CPU 0 / FFA 1, TC1 free 16 and no new page release. These
are host observations; they do not prove whether the frame transmitted or
whether firmware should have generated a completion. The older submit-PID 32
observation belongs to data TX and is not the management PID 33 submission.
Offsets derived from kmsg are log timestamps, not firmware execution times.

PM abort was not reached, no key removal credit or healthy stage 3 was recorded,
and both local disables returned `-110`. The standard loss report occurred once
after this stop, so the later mac80211 AP-loss message is a consequence. Keep
the original finite-session classifier failure; the duration and positive
network observations do not turn it into a healthy lifetime.

All 71 pre-recovery seals, eight client-observation files and 2,106 contiguous
log records (168,734 bytes) verify. Helper/device quiescence, A53 regression and
one reviewed recovery passed; changed-boot Gemian
`c6c0a8ab-0d6b-45e8-8bfc-02cbb274ab4d` was independently confirmed. No device
process or physical handoff is pending. No retry occurred.

Next: classify the reserved deauthentication's submission/completion contract
and compare the public vendor teardown/TX options with the retained host path.
Do not move PM abort earlier, admit unknown completions, extend deadlines or
select another candidate without that evidence. If source cannot distinguish
the remaining causes, predeclare one bounded scalar diagnostic from existing
acquisitions. Resolve healthy cleanup before the longer/persistent lifetime;
no two-minute, ten-minute, rekey, reuse or reconnect acceptance is established.

### Predeclared GTK6: bounded reserved-deauthentication retirement

The public vendor source starts a 100 ms deauthentication done timer in
`AIS_STATE_DISCONNECTING` and calls `aisDeauthXmitComplete` with a lifetime-timeout
result on expiry, continuing disconnect handling
([pinned AIS source](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/mgmt/ais_fsm.c)).
This supports separating missing deauthentication completion from resource
cleanup. It does not authorize inventing a completion, ACK or returned page.

One logical successor, archive 0213, keeps the current 750 ms management-frame
bound and all 100 ms command deadlines. On expiry it retires only the current
lifetime's reserved, driver-owned 26-byte deauthentication after the data phase
and native close. Count the missing completion; leave ACK false and the page
charged. Keep the free outside the MAC lock, including a subsequent failure in
the same worker tick. All other frame timeouts remain fatal.

Our ordinary command encoder requires the whole TC4 pool. A narrow internal
exception permits only the first 0x17 PM abort against exactly one charged
retired-deauthentication page, with TC1 whole and the existing ledger bounds.
Debit the new page too; never refund, reset or alter the pending counters. Then
require the whole pool within the unchanged 100 ms credit deadline before any
key/station removal. One aggregate page return cannot identify which of the
two buffers retired, so a partial return remains blocked and cannot be called
an abort credit or healthy cleanup. Fatal transport poison remains permanent.

Keep deauthentication first. The actual existing final order is PM abort,
pairwise/group removals, station removal, channel abort and BSS-off; preserve
it. A late exact completion for the one retired PID is counted without a second
free or page release. Unknown PID, malformed/status-invalid events, reuse and
reconnect remain refused. No resource cap, grant or data-window change.

Predeclared outcomes for one fresh 60-second low-traffic session:

- Deauthentication completes inside the original bound, all cleanup credit
  returns and stage 3 is reached: healthy host cleanup after PM setup observed.
- Completion is missing, all pages and cleanup command credits return and
  stage 3 is reached: host teardown is healthy, on-air deauthentication /
  completion reporting remains an open item. No reuse is enabled.
- Completion and full cleanup credit retirement are missing: retain exact
  command/stage/debt/deadline scalars, bounded stop. Firmware state is a branch
  to investigate; credit counts alone do not identify its cause. Only then
  consider a separate PM-abort-before-deauthentication comparison.
- Another first failure is its own result, not a retry or substituted pass.

Local actual-source tests cover retirement at deadline ±1 ns, strict owner and
poison gates, same-tick fatal free classification, partial-credit refusal,
original cleanup order, and exact late-PID handling. The pure and actual-HIF
fixtures cover the bounded debit and all transfer cuts/expiry without refund,
while ordinary command admission stays strict. Crypto callbacks and option-off
MAC parity remain covered; the pre-existing PM fixture still runs against
GTK5. Synthetic checks do not establish firmware behavior. Publish to `main`
before Linux checks/build; no new branch or physical test is selected yet.

### GTK6 validated package — deployment pending

Source `af6923d3` was pushed to `main` before Linux fixtures and the required
Buildbox backend build. Both selected and canonical-overlay actual-source
fixtures pass, including page-ledger/HIF transfer cases. Validated inventory
`43849fa3b584d0bf8e7591d2292ae2a712a19e5bb8f9ae6ec418f89c7e01f89a`.
The [real GTK6 receipt](results/ccmp-stable-monitor-candidate-gtk6.json) binds
boot image `af31e2aa18049945fca797e7bf5d339c204d5a960c2129392e436cbb5c147d72`.
Config, board DT and exact RAM root match GTK5. Runtime notes are 84 bytes,
SHA-256 `8a5d78bc3489be692c786c6c5bf74f8ff9a71e0070c3f95a24ed1731972a5285`,
matched between ELF, Image, map bounds and the unchanged sysfs exporter, and
differ from GTK5. Five local host binding/source fixtures pass.

Six fresh GTK6 wrappers bind the bounded deauthentication retirement, one-page
debt exception for the first abort, whole-ledger wait and retired-PID-only late
status rule. The 60-second window, all deadlines and all resource caps remain
unchanged. Linux host binding checks, reviewed guarded deployment, full readback,
clean shutdown and fresh host preparation remain required before physical boot2
selection. GTK6 has no hardware result yet; no new run row is created.

### GTK6 installed — physical selection pending

Tooling `ee5da8c4` passed all five Linux host fixtures from clean pushed `main`.
The 603-line installer differs from GTK5 only in identity pins and passes shell
syntax/ShellCheck. Known-good Gemian boot
`c6c0a8ab-0d6b-45e8-8bfc-02cbb274ab4d` was independently verified before the
live-GPT boot2 guard. The inactive/non-root target and GTK5 predecessor matched.
The new full-partition candidate and readback both equal
`75316795e8a9a732db5f02e5df32393b7f955c402422b72832fb9d5855f5ee09`.
The deployment seal and clean shutdown verify; no fresh backup or other
partition write occurred.

Fresh runtime preparation, the exact mode-0600 deployment summary, retained
recovery sources and complete offline host preparation pass. No GTK6 mainline
boot, capture or Wi-Fi session has occurred. The owner must physically select
boot2 with USB attached to this laptop. After fresh boot/notes verification,
consume one capture and one session under the predeclared cleanup outcomes.
No retry, rekey, reuse or reconnect. One run scalars file and one table row will
be added only after the actual session. All checkpoints are pushed to `main`;
restored research remains unstaged and separate.

### GTK6 consumed — command-path credit with a retained page

Capability observation and duration pass in the one fresh boot
`6f5dbd31-9ed7-4f91-9c42-6a7ccd432bfd`: the data window ended by budget at
60,015 ms with 0x16 present and zero observed 0x13 events. No firmware mechanism
is inferred. DHCP, three individual ping replies and fresh SSH authentication
(exit 0, 1,738.549 ms, empty stderr) passed while open. Checked PTK/GTK queues
were 35/225, GTK ARP handoffs 104 and withheld ARP 0. Limits did not bind.

Cleanup failed. Reserved deauthentication PID 34 had no completion before its
unchanged bound; its host slot was retired with ACK false and one page still
charged. PM abort sequence 30 was submitted successfully, then one TC4 credit
returned with one page still owed. **The command path was credited after the
missing completion.** The whole-ledger requirement stopped before removals:
branch 1/site 3, `-110`, pending credit 1, TC4 free 25, pending CPU 0 / FFA 1,
TC1 free 16, debt 1, cleanup 0. PM abort's buffer identity is not separately
encoded by these aggregate counters; the observed credit is not an explicit
firmware execution acknowledgement. No late retired-PID status was observed.
No healthy stage 3 occurred, and both local disables returned `-110`.

The stop was logged 912.798 ms after data end and 129.777 ms after the PM-abort
submission log; those are kmsg offsets, not replacement deadlines or firmware
execution timings. The configured credit bound stayed 100 ms. The standard
loss report happened once after this stop; the later AP-loss message was not
a first data-window monitor failure. Keep the unchanged finite classifier's
failure and the separate positive capability/duration verdicts.

All 71 seals, eight client-observation files and 2,110 contiguous log records
(169,572 bytes) verify. Helper/device quiescence, A53 regression and one reviewed
return passed. Changed-boot Gemian `0040b209-8b30-4587-b8e4-74c50a24a09b` was
independently confirmed. GTK6 is consumed; no device process or physical handoff
is pending, and no retry occurred.

The owner selects GTK7 to distinguish the retained-page condition from the
teardown frame's order: PM abort before the reserved deauthentication, at most
one retained page throughout remaining teardown, a distinct bounded-debt
terminal, periodic standard device pings and end-of-data beacon recency. Healthy
stage 3 still requires a whole ledger. No deadline extension, PID/key reuse,
rekey, reconnect, nullfunc or event-0x13 tolerance is admitted. Record every
periodic completion offset and cleanup credit timestamp in the next run's one
public scalars file; no per-run result document.

### Predeclared GTK7 inputs and observations

Keep 0x16 credited before keys, the fatal counter-only 0x13 policy, standard
connection-monitor ownership, all current deadlines and caps, no nullfunc,
PID/key reuse, rekey or reconnect. GTK7 makes these separate logical changes:

1. Carry at most one charged retired-deauthentication page through remaining
   teardown. Never reset/free/refund the ledger. Each command debits its own
   page and must return to its pre-submission debt floor within the existing
   100 ms deadline. If the retained page has already returned, the next command
   floor is zero, not one. Admit only cleanup removals/abort/BSS-off in this
   mode. A distinct terminal may report cleanup complete with one bounded page
   debt; it permanently closes the lifetime and is never healthy stage 3.
   Healthy stage 3 still requires the physical ledger whole.
2. Send and credit PM abort before selecting the reserved deauthentication.
   Keep the remainder of the existing removal order. This order comparison
   tests the PM-connected-state explanation; an outcome supports or contradicts
   that explanation for the run, not a general firmware mechanism proof.
3. Retain one immutable host timestamp at the 0x16 credit and report every owned
   TX completion with its class/PID/status and precise offset. Report cleanup
   command submission/credit offsets and owned-beacon count/last-delivery age at
   data end. These are host observations from existing acquisitions, not new
   register reads or firmware execution timestamps.
4. Use a fresh reviewed one-cycle device leaf: five scheduled numeric-router
   pings at PM-credit offsets +10/+20/+30/+40/+50 seconds. A probe is one `-c 1`
   ping under the existing window/boot/fatal guards and a three-second child
   bound; no catch-up burst, retry or +60-second boundary probe. Preserve each
   exit/reply and completion offset in the existing sealed ping log. Export
   userspace clock resolution separately from precise driver completion timing.
   No DNS, host cache flush, capture or additional association.

Predeclare outcomes: deauthentication completes after PM-abort-first and the
whole ledger reaches healthy stage 3; deauthentication remains missing but
remaining command paths credit and cleanup completes with exactly one bounded
page debt; periodic host TX stops completing at a measured offset (only then a
bounded private firmware question may be useful); a remaining cleanup command
fails its credit bound as a separate first failure; or pre-budget mac80211
beacon/AP loss interpreted against the owned-beacon end count and age. Every
other first failure remains separate. Export periodic offsets, beacon metrics
and all teardown credit timestamps into one public run scalars file and one
existing table row. No actual GTK7 result is implied by preparation.

GTK7 preparation now consists of logical archives 0214 (bounded page / distinct
terminal), 0215 (PM-abort-first) and 0216 (PM-relative completion/credit clocks
and end-of-data beacons), plus a reviewed periodic device leaf. Local actual
MAC, pure-ledger and actual-HIF cases pass, including the correct existing
single-STA removal payload, real debit/return at each retained floor, transfer
cuts with no refund, whole-vs-bounded terminals and recovery of the retained
page before a later command. Crypto and option-off MAC parity pass; the frozen
GTK6 source and default reviewed-leaf binding still pass their fixtures.
Strict checkpatch has only the synthetic archive author's deliberate missing
DCO sign-off, with no style warnings/checks.

The periodic leaf passes host simulation for five fixed probes, failure without
retry, missed-slot handling, retained raw outputs, and boot/window/clock/numeric
address refusals. It runs before the SSH-ack wait, so SSH failure cannot suppress
TX measurements. The normal 300-second wall, 90-second listener and 32 KiB leaf
cap remain unchanged. Userspace ping completion offsets have 10 ms clock
resolution; driver TX-status and cleanup-reconciliation observations carry
monotonic nanosecond offsets from the host's PM credit. Neither is a firmware
execution timestamp or proof of per-frame on-air delivery. Raw ping output
stays in the existing sealed `ping.log`; public scalars export only measurements.
The existing classifier's healthy-stage requirement remains unchanged for a
bounded-debt terminal. Linux checks, build and hardware admission remain pending.

### GTK7 validated package — deployment pending

GTK7 source and periodic inputs were pushed to `main` at `8aed6b61` before
Linux fixtures and the required Buildbox build. Selected/canonical actual-source,
HIF, periodic and reviewed-leaf binding tests pass. Validated package inventory
`d928d71aee6a96b3a7ace0d4c24b7da61c432ee63ba4a600cf41de3ae11b546f`.
The [real GTK7 receipt](results/ccmp-stable-monitor-candidate-gtk7.json) binds
boot image `5fa1331e33664ed86c5b4cc6f30369b861ddf768299355c6e75b31b2b37e19ea`.
Config, board DT and exact RAM root match GTK6. The 84-byte runtime notes have
SHA-256 `0b4add89483baa2e91872da3d6b0099845cc4e2336585dbf00a92df4c2962596`,
matched between ELF, Image, map bounds and the unchanged sysfs exporter, and
differ from GTK6. Five local host binding/source fixtures pass.

Fresh GTK7 wrappers require the exact periodic reviewed leaf; the default old
leaf remains unchanged for historical wrappers. The new body is 28,186 bytes,
and the private bound leaf stays below the unchanged 32 KiB cap. Owned-child,
exit-trap, bounded-command and window guards are byte-identical to the historical
leaf. No credentials, private leaf or RAM image is published.

GTK7 changes both teardown order and the preceding traffic pattern. A successful
deauthentication will demonstrate the combined tested path; one run alone does
not uniquely attribute that outcome to order rather than its new traffic
history. Public results will state the measured offsets and observations,
without attributing an absent event to a firmware mechanism.

Linux host binding checks, guarded deployment, full readback, clean shutdown
and complete fresh host preparation remain required before physical selection.
There is no GTK7 hardware result or run row yet.

### GTK7 installed — physical selection pending

Tooling `cd1a81ef` passed all five Linux host fixtures from clean pushed `main`.
The 603-line installer has only identity-pin changes from GTK6 and passes shell
syntax/ShellCheck. Known-good Gemian boot
`0040b209-8b30-4587-b8e4-74c50a24a09b` was independently verified before the
live-GPT guard; inactive/non-root boot2 and the GTK6 predecessor matched.
Full candidate and readback SHA-256 both equal
`d9f0d3407b186b2d314c281af08dd7fcee0660e2a50863dd0e36eb8102c6536f`.
The deployment seal and clean shutdown verify; no fresh backup or other
partition write occurred.

Fresh runtime, the exact mode-0600 deployment summary, new periodic private leaf
and complete offline host preparation pass with the pinned recovery sources.
No GTK7 boot/capture/session has occurred. Next action is the owner's physical
boot2 selection with USB attached to this laptop, followed by fresh boot/notes
identity verification and one admitted capture/session. Export the periodic,
beacon and teardown-credit timing scalars as predeclared; no retry or second
association. A bounded page-debt terminal is separate from healthy stage 3.
All inputs/checkpoints are on `main`; restored research remains separate.


### GTK7 consumed — whole-ledger cleanup with late deauthentication

One admitted boot `138674d4-2aff-4ff5-ad75-a0670d432b36`, source `8aed6b61`,
tooling `cd1a81ef`, handoff `1cfeb81e`. Exact boot2 and kernel-note identities
matched. Phase A passed 285/285; one capture, one session, one SSH attempt,
no retry. The [single scalars file](results/gtk7-runtime-scalars.json) exports
all five periodic probes, every owned TX completion, end-of-data beacon
metrics and all twelve cleanup submission/credit timestamps.

Capability and duration pass for this finite low-traffic run: DHCP, initial
pings 96.085 / 44.519 / 32.367 ms, fresh SSH authentication in 1.618 s with
exit 0 and empty stderr, while the window remained open. The window ended by
budget at 60,011 ms. Five separately scheduled numeric-router pings at PM-credit
+10/+20/+30/+40/+50 s each returned one reply; userspace completion offsets
were 10.557 / 20.407 / 30.507 / 40.717 / 50.487 s (10 ms clock resolution).
Driver TX completions continued through +50.128 s. These host observations do
not identify individual ICMP frames solely by nearby timestamps. Checked
PTK/GTK handoffs were 41/238, delivered GTK ARP 107, withheld ARP 0. No named
HIF refusal, capacity stop or pre-budget AP loss was observed; 0x13 count zero.
The passive-scan classifier still reports no standard BSS result: standard
scan acceptance remains open.

PM abort sequence 30 was credited at +60.224 s, before reserved deauth PID 41.
Deauth still missed the unchanged 750 ms completion bound: its host slot was
retired without ACK or refund, carrying one actual page debt. PTK and GTK
removals returned to floor one; station removal returned the actual ledger to
zero. The exact retired PID then completed late with status 5 at +61.110 s;
this did not credit or free it a second time. Channel abort and BSS-off used
floor zero and credited. All six command paths met their existing 100 ms
credit bounds. Healthy stage 3 followed with a whole ledger, `deauth=0`, and
both local key disables returned status 0 with removal-command credit. No
bounded-debt terminal was needed. This establishes host-ledger cleanup and
credited removal paths, not independent firmware key erasure or an
acknowledged deauthentication.

This is a distinct outcome from the two simple cleanup branches: completion
was missing at the frame bound, but the debt later returned and the ledger
finished whole. PM-abort-first did **not** restore timely frame completion.
The order and preceding periodic traffic changed together; do not attribute
the improved teardown to one of them or claim a firmware mechanism.

End-of-data owned-beacon queue admissions were 21 total, 20 after PM credit;
last-admission age was 58.162 s at data end (last admission about +2.003 s
after PM credit). Continuous owned-beacon delivery is not established. Phase-1
aggregate type-7 count 110 is not an owned-beacon count. These observations do
not prove RF loss; no new acquisition or firmware explanation is inferred.
All periodic TX probes succeeded, so the predeclared fixed-offset host-TX
failure trigger for a private question was not reached.

All 71 pre-recovery seals and 2,185 contiguous kmsg records (184,315 bytes)
verify; eight retained client-observation files are sealed. One-cycle export,
helper/device quiescence and A53 regression pass. One reviewed recovery request
returned to changed-boot Gemian `78b701cf-cb65-4283-bc32-dbe7dadb5497`, independently
confirmed. No physical handoff or live device process remains pending.

Next review should separate the remaining unacknowledged teardown frame from
persistent station ownership and connection monitoring. Do not extend this
finite grant to claim two or ten minutes. Before a successor, account for the
stale owned-beacon observation and preserve the exact late-completion behavior.
No new candidate is selected by this result. Rekey, PID/key reuse and reconnect
remain disabled. Ten-minute authenticated SSH traffic and reusable lifetimes
remain incomplete.


### After GTK7 — bounded connected-channel ownership comparison

GTK7's five periodic replies and whole-ledger terminal are progress toward
persistent operation. They do not establish data after channel-privilege
release: its 65-second grant enclosed the whole data phase. The earlier
[runtime 25](../2026-10-07-mt6797-wifi-phase-b-join/RUNTIME_25_RESULT.md)
released before data and stalled on the first data TX; it did not have the
now-credited PM connection indication. Do not repeat that artifact or assume
that the missing indication was its cause.

The retained public
[AIS source](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/mgmt/ais_fsm.c)
was reverified at SHA-256
`738b8fcf0d34098fef986c1dba4963ebe0676665b0a914d7a712a50e814838ba`.
`aisFsmRunEventChGrant` starts the join timer from the actual grant interval;
`aisFsmRunEventJoinTimeout` in NORMAL_TR calls `aisFsmReleaseCh` without
tearing down the connected BSS. This supports a bounded comparison, not a
firmware execution guarantee or a proof of current driver compatibility.

**Hypothesis:** the current PM-configured connected BSS can continue protected
traffic after returning a short join privilege. One new default-off profile,
`mt6797-a53-wifi-ccmp-channel-release`, selects logical archive 0217 on GTK7.
The existing initial-GTK profile is unchanged. Request 9,000 ms instead of
65,000 ms; reject a shorter returned interval before association/keys. Open
only with the unchanged 2,500 ms grant tail still available, but retain the
existing 60,000 ms observation wall and 5,000 ms teardown margin independently
of the join privilege. Thus the old full-window-within-grant admission applies
to the old profile; this comparison explicitly tests its replacement ownership
contract. No frame, command, teardown or resource limit is extended.

At grant end minus the existing tail, hold selection of new TX. Let existing
owned TX complete and both TC1/TC4 ledgers return whole within their existing
bounds and remaining grant. Submit the existing CH_PRIVILEGE abort once with
its original token, fresh sequence and one real page, under the existing
100 ms command bound, clamped to the grant/lifetime horizon. Continue existing
RX/credit processing without a blocking wait. Mark the privilege released and
resume connected-BSS TX only after real credit returns. A failed/uncertain
submission keeps its debit and takes the fatal path. Cleanup skips a second
channel abort, using the existing released-channel branch; all other GTK7
cleanup behavior stays unchanged. No new wire access, key/PID reuse, rekey,
reconnect, event tolerance or receive-format change.

**Unique observation:** preserve release submission/credit sequence, status and
host timestamps, then individual periodic replies and TX completions after
release and after the original grant horizon. Reuse five scheduled +10 through
+50-second probes and permanent SSH stderr. Export these alongside GTK7's
beacon and teardown clocks in one future scalars file/row. No actual run or
run row exists yet.

**Decision branches:** (1) release cannot drain/submit/credit before its bounds:
report that first ownership/transport failure, no later success claim;
(2) release credits but the first later TX lacks completion or RX/traffic
fails: report the first PID, ledger, offset and network stage, preserving the
runtime-25 comparison without assigning a cause; (3) periodic replies continue
beyond release and the original grant horizon to 60 seconds: connected data
after release is demonstrated for that bounded lifetime; independently grade
healthy stage 3 versus bounded debt and deauthentication acknowledgment;
(4) a monitor event, resource cap, framing refusal or other first failure is
its own result. Owned-beacon count/age still does not identify RF loss.

Actual-source host fixtures pass for the grant branch, data-opening tail
boundaries at +/-1 ns, release/drain/credit ownership, transport failure with
no refund, poisoned/key/sequence refusals, exactly-once release and expired
resource horizons. The option-off preprocessed MAC matches frozen GTK7 under
three selections. Existing GTK7 crypto/callback/pthread and actual-HIF PM/debt
fixtures pass. One first local regression invocation selected the wrong parent
cohort and failed before tests; the correct retained grant-window parent
(with the existing 0205 adjustment) passes. The new grant fixture initially
lacked the existing IS_ENABLED shim; adding that fixture-only shim passes.
Strict checkpatch has only the deliberate missing DCO certification, zero
warnings/checks; this synthetic archive is not an upstream submission.
Linux validation, the required clean/pushed Buildbox build, package binding,
installation and hardware result remain pending. No candidate is installed.


### GTK8 validated package — host binding validation pending

The channel-release input `8792a406` is pushed to `main`. Both primary and
canonical Linux release/actual-HIF fixtures pass; the required Buildbox kernel
build completed from that clean input. The fetched package inventory is
`b53512f0139d2b0a362a6a5d9ea099d6fca42d8dcbfe4985dec4c33dc2d2d56b`.
The [real GTK8 receipt](results/ccmp-stable-monitor-candidate-gtk8.json) binds
profile `mt6797-a53-wifi-ccmp-channel-release`, logical archive 0217 and all
710 selected patches in canonical order. Full configuration equality proves
only the channel-release option is added to GTK7; board DT and the C32-derived
64-member RAM root remain byte-identical to GTK7. This is a finite ownership
comparison, not a persistent-driver or usable-Wi-Fi claim.

The 84-byte kernel-note identity was independently matched across the actual
ELF, packaged Image/System.map and pinned sysfs exporter; expected SHA-256 is
`6725caca78f120244c9fcc00137a3800f4573588fc1424287a1278ffbdf9cd0a`, distinct
from GTK7. Local composition/config-mutation, installer source routing,
session source routing, completed host/no-scan ownership and actual receipt/
namespace fixtures pass. The exact existing GTK7 periodic leaf is reused,
including its hash/namespace guard and permanent client stderr retention.
No credential or raw evidence is published.

A separate host verdict requires the exact 9-second grant, one attributable
release submission/credit within 100 ms, consistent PM clock, all five periodic
replies after release, and owned successful data completions beyond PM+9 s
through PM+50 s, in addition to the existing full-window/crypto/network/cleanup
verdict. PM indication follows the join grant, so PM+10 s is beyond that grant.
It preserves the independent capability/duration values. Synthetic missing,
malformed, duplicate, wrong-grant, credit-bound and missing-traffic cases pass.
The sealed GTK7 export independently parses all five probes, retains its
legacy pass and is correctly refused as proof of channel release. These host
checks do not prove firmware execution or associate individual ICMP frames
solely by nearby aggregate completion timestamps.

Linux validation of the new host bindings, guarded installation, full readback,
shutdown, offline preparation and a new owner physical selection remain pending.
GTK8 has not run; do not reuse the consumed GTK7 physical-selection reply.


### GTK8 installed — physical selection pending

GTK8 source `8792a406`, package/host bindings `49ff0b1c` are on `main`. Both
Linux source variants, the required kernel build, fetched package, five Linux
host fixtures and the strict release-verdict fixture pass. The reviewed
603-line installer differs from GTK7 only in candidate/tool/boot/evidence
identities; the exact device guard, Bash syntax and ShellCheck pass.

Live Gemian boot `78b701cf-cb65-4283-bc32-dbe7dadb5497` was independently
verified before installation. The guard resolved inactive, unmounted, non-root
logical boot2 from live GPT with stable power and the expected GTK7 predecessor.
Full-partition write/readback SHA-256 matches
`ffbb0d343aa7061e1c592488ee6ee92786cc70abe7a6f9008ca1f4a17cce2dff`.
Deployment summary/seal verifies and clean shutdown is confirmed. No fresh
partition backup, other partition write or automatic boot selection occurred.

Fresh runtime, exact mode-0600 deployment summary and complete offline host
preparation pass. Reuse the exact reviewed GTK7 periodic leaf, not the older
six-second leaf. There is no capture, session result or GTK8 run row yet.
Next action is the owner's physical boot2 selection with USB attached, then
verify a fresh mainline boot and the exact 84-byte kernel-note identity
`6725caca78f120244c9fcc00137a3800f4573588fc1424287a1278ffbdf9cd0a`
before one admitted capture/session under the declared release/traffic/cleanup
branches. No retry, key/PID reuse, rekey or second association. Preserve
release sequence/credit timing, periodic outcomes, beacon count/age and
teardown timestamps in one public scalars file and one existing table row.


### GTK8 consumed — protected traffic beyond the join privilege

One boot `a996ec5e-fc20-49d3-a160-2ed321e3e156`, kernel input `8792a406`,
host bindings `49ff0b1c`, handoff `b9555ddf`. Fresh boot and exact 84-byte note
identity matched. The first read-only identity invocation passed its command
incorrectly to the SSH helper and exited nonzero without verification; stdout
was not retained. The corrected stdin invocation verified identity. No capture
or radio session started on the failed invocation. There was one Phase-A
capture (285/285 ready), one session and one Wi-Fi SSH attempt; no session retry.

The [single scalars file](results/gtk8-runtime-scalars.json) records independent
capability, connected-after-release, duration, transport, network and host
cleanup verdicts. The reported grant was 9,000 ms. Channel abort sequence 29
submitted at PM +6.274939 s, status 0, one real page; credit returned at
+6.299955 s with zero debt, a 25.016 ms wait under the unchanged 100 ms bound.
All five scheduled numeric-router probes replied after that credit, at PM
+10.745 / +20.545 / +30.595 / +40.755 / +50.645 s completion offsets (userspace
clock resolution 10 ms). PM indication follows the grant, so these probes are
also beyond the original reported grant horizon. Owned successful data TX
completions continued through +50.296 s. This demonstrates protected traffic
beyond the join privilege for this bounded run; returned pages remain host
buffer-accounting observations, not explicit firmware execution acknowledgments.
Nearby aggregate TX timestamps do not identify individual ICMP frames.

DHCP and initial pings 103.012 / 29.413 / 41.235 ms passed. Fresh SSH
authenticated with exit 0 in 1.397 s, no stderr, while the data window was open
and **before** channel release. Neither a post-release SSH handshake nor a
maintained authenticated SSH stream was measured. The data phase ended by
budget at 60,009 ms, TX queued/done/failed 35/35/0. Checked PTK/GTK handoffs
42/231, delivered GTK ARP 106, withheld ARP 0. No named HIF refusal, capacity
stop, pre-budget AP loss or 0x13 event. The strict post-release host verdict
passes, independently recomputed from the sealed evidence. Standard scan
acceptance remains open: the inherited passive-scan verdict has no standard BSS.

PM abort sequence 31 credited before reserved deauth PID 40. The frame still
missed its unchanged 750 ms completion bound and was retired without ACK or
refund. PTK, GTK and station removals credited under their existing bounds;
the actual ledger returned to zero at station removal. Exact late PID 40 then
returned status 5 at PM +61.069767 s without another credit/free. Cleanup
skipped the already returned privilege, submitted no second channel abort,
and credited BSS-off at floor zero. All five remaining commands credited;
whole-ledger stage 3 followed with `deauth=0`, and both local key disables
returned status 0. No bounded-debt terminal. Host resource cleanup passes;
acknowledged deauthentication and independent firmware key/queued-RX retirement
are still unproved. Moving data beyond the privilege did not restore timely
deauthentication in this run; do not assign a firmware mechanism.

Owned-beacon queue admissions at data end: total 21, since PM 20, last age
58.114 s (last admission PM +2.031 s). Continuous owned-beacon delivery is not
established despite successful periodic protected traffic. This is not proof
of RF loss. No fixed-offset host-TX failure occurred and its predeclared private
question was not triggered.

All 71 pre-recovery seals, eight client-observation files and 2,186 contiguous
kmsg records (184,416 bytes) verify. One-cycle export, helper/device quiescence,
A53 regression and one reviewed recovery request pass. Changed-boot Gemian
`4f0120ad-fa64-462a-82d3-c2c3f9b0a30e` was independently verified afterward.
GTK8 is consumed; no live device process, retry or physical handoff remains.

Next, refresh the current mac80211-initiated disconnect/key-disable ordering
before introducing persistent connected operation and the two-minute SSH
stage. Current success is a finite driver-initiated budget stop; it does not
prove a core-initiated teardown while data is active. Keep the successful
short join-grant release, transaction/resource protections and strict per-frame
crypto gates. Do not obtain two/ten-minute acceptance by requesting a longer
grant or simply raising the finite join constant. Rekey, key/PID reuse and
reconnect remain disabled until their ownership contracts are resolved.


### S1 preparation — unchanged GTK8, stream and core-initiated disconnect

GTK8 passed protected traffic beyond the reported join grant, but its SSH
challenge closed before release and teardown began at the driver's budget
stop. The next unique measurement is a maintained post-release authenticated
stream and teardown initiated through the standard supplicant interface while
data is active. Reuse the exact GTK8 image/package/config/DT/RAM and existing
periodic leaf; no kernel build, new wire command, PN read, key/PID reuse, rekey
or reconnect. S1 has fresh `gtk8-s1` capture/session/deployment namespaces;
its runtime receipt is byte-identical to GTK8, not a new kernel artifact.

The pinned mac80211 source is unchanged from the earlier lifecycle audit:
`key.c` SHA-256 `d86ef8b871244dec3c489706fdd044a8befb4e85aa2dd0671ed6d9c35beb293d`,
`sta_info.c` `c2584dc5cbfa858b8b603113d6cf6a4194626e5f37747b2f87a29b0281baa1b4`,
`util.c` `232eb6328c7f3a7b40844fb188a6f681ef916e7691aba525de8322191bdd646e`,
`mlme.c` `97b33dcf39dd45fa5f00db314be9b1ff2e6aeb00d007060b35e9a0d501befc57`.
The associated `ieee80211_mgd_deauth` path enters `set_disassoc` under the wiphy
lock, stops network polling/carrier, invokes management preparation, and
removes the station. Station destruction descends AUTHORIZED, frees station
keys and then reaches NOTEXIST. DISABLE_KEY is synchronous and its error cannot
be used as evidence of firmware deletion. The current driver management
preparation ends data on DEAUTH/DISASSOC; downward station callbacks withdraw
borrowed RX/key pointers and synchronize handoff, and key disable waits for
cleanup with the MAC mutex released. The worker's connection-loss report queues
wiphy work rather than waiting for it. A missing `.flush` remains no firmware
queue barrier. These source contracts support testing the transition; they do
not replace its hardware result or authorize healthy re-arm.

**S1 hypothesis:** the current path can carry an authenticated SSH stream
across release and complete core-initiated cleanup before the existing budget.
One fresh boot, capture, session and SSH attempt. Preserve the 60-second kernel
wall, 9-second grant, periodic probes at PM +10/+20/+30/+40/+50 s, 25-second
client acquisition, 10-second ConnectTimeout, 90-second helper poll, owned-group
join/grace and every firmware/frame/command/resource bound. The fixed Wi-Fi
command serves the existing boot/ready fields, then five timestamped chunks
spanning 20 seconds. Both the client elapsed time and chunk span must cover the
planned duration. Late authentication can exhaust the unchanged 25-second
bound; retain partial output and classify its actual stage, never silently
extend it. The standard permanent stdout/stderr/neighbor/route retention stays.

The stream explicitly requests a PTY (`-T` becomes `-tt`); an owned stdin pipe
is held open without sending data until the client exits, because stdin EOF
closes this server's PTY. The child inherits the existing helper process group.
Raw stdout is retained up to 64 KiB with actual/truncated byte counts explicit;
authentication, host-key, route, agent and forwarding options remain frozen.
The original verifier accepts the unchanged boot/ready fields in the raw PTY
output; no bytes are rewritten. The existing RAM creates/mounts devpts and the
kernel selects UNIX98 PTYs. From the verified public
[Dropbear archive](https://matt.ucc.asn.au/dropbear/releases/dropbear-2026.94.tar.bz2)
SHA-256 `e098034a843699200c8c977a991fff73159735bf795d5f72ef672c41a6b1ae81`,
the PTY path creates a controlling terminal, and channel cleanup closes its
master. The pinned kernel's PTY close/hangup path signals the foreground group.
The non-PTY cleanup body does not itself establish command-child termination;
that is why S1 does not use an unbounded non-PTY stream.

Before a stream starts, require the expected boot, ACTIVE/no-fault window,
PTY descriptors and PM offset at most five seconds. Before installing a signal
handler, `/proc` must establish that the command PID, process group, session
and foreground group are its own. The existing BusyBox timeout bounds execution
at 22 seconds; HUP/TERM terminates only that verified own group. Failed ownership
or late-start admission launches no sleep loop. A bounded read-only process
observation after PM +6 s requires the boot-specific command tag absent before
sealing/recovery: at most 512 processes, 4,096 command bytes each, scalar counts
only, at most 20 seconds of successful-presence polling within the unchanged
helper budget, each USB call at most 15 seconds. The query cannot match its own
argv. Failed/unknown reads are not retried. The parent additionally refuses
export, seal and recovery without remote-stream quiescence, independently of
local process-group success. Raw observations remain private and sealed.

After the stream/probes, the owned host helper schedules exactly one fresh
boot/window/PM-clock/binary-digest guarded `/bin/wpa_cli -p /tmp/wpa -i wlan0
disconnect` near PM +55 s. Use the existing BusyBox three-second timeout and one
15-second USB call; no remote sleep, cache flush, packet capture or retry.
Refuse outside PM +55 through +56 s or after an earlier data end/fault. A failed
SSH stream does not suppress this independent transition measurement if its
remote work is quiescent and the window is freshly live. Preserve request
start/end timestamps, reply, client ticks, periodic results and all driver
release/beacon/teardown clocks.

**Predeclared outcomes:** owned PTY/start/stream refusal or timeout is a distinct
host/SSH result; uncertain remote quiescence holds preservation/recovery;
request not admitted because the window ended or timing was missed is NOT
REACHED, with no late retry; accepted standard disconnect followed by a data
end reason `disconnect` inside that request's timestamps and healthy stage 3
establishes the core transition for this run; accepted request with a budget
stop, fault, uncredited cleanup or unresolved debt is a separate first failure.
SSH stream, post-release periodic traffic and cleanup are graded independently.
The planned controlled stop is PM +55 s, not a full 60-second run. The new
verdict must keep the inherited duration/60-second result false and report the
actual data-phase duration. Ten-minute SSH traffic and same-boot reconnect
remain incomplete. One scalars file/one table row only after an actual run.

Local client/control cases, raw PTY identity parsing, generated-shell syntax
and ShellCheck, strict controlled-stop verdict, fresh namespace/helper binding,
unchanged installer/recovery source routing and completed no-scan host refusal
fixtures pass. The seal-gate fixture rejects unconfirmed remote work. A Linux
PTY hangup fixture remains pending along with clean pushed-input Linux host
validation, reviewed checksum-skip installation/shutdown, host preparation and
a fresh owner physical boot2 selection. S1 has not executed on the device.


### S1 admitted — unchanged image verified, physical selection pending

Host-only inputs are pushed at `2a197328`. All six Linux fixture groups pass,
including all twelve client cases (real PTY ownership/hangup, held-open stdin,
timeout partial output and actual generated AWK execution). The controlled-stop
verdict, namespace/helper/installer binding, remote-quiescence seal refusal,
retained installer/recovery source routing and completed no-scan refusal cases
pass. The generated outer/inner stream, disconnect and process-observation
commands pass shell syntax and ShellCheck. A preflight found and corrected a
Python escaping error in generated AWK before publication/device admission;
executable parser fixtures now cover every clock path. No S1 radio run occurred.

Fresh known-good Gemian `4f0120ad-fa64-462a-82d3-c2c3f9b0a30e` was independently
verified. The reviewed 603-line installer differs from GTK8 only in tool,
predecessor/boot and evidence identities; guard SHA-256 remains
`0f0fc88ce4650590c6cb86f0ef5ce22b95b2a0f41c9b39b397e24e39cf9f0ebf`.
Bash syntax and ShellCheck pass. The live GPT/non-root/inactive/power guards
passed, and boot2 already matched the exact GTK8 full-partition SHA-256
`ffbb0d343aa7061e1c592488ee6ee92786cc70abe7a6f9008ca1f4a17cce2dff`.
Writing was skipped; full readback, deployment seal and clean shutdown verify.
No new kernel build, image/rootfs change, partition backup or alternate write.

Fresh S1 runtime, exact mode-0600 deployment summary and complete offline host
preparation pass with the unchanged reviewed periodic leaf. No capture/session
or S1 run row exists. Next is a **new** owner physical boot2 selection with USB
to the custodian laptop, then a new boot UUID with the same GTK8 kernel/release
and 84-byte note SHA-256
`6725caca78f120244c9fcc00137a3800f4573588fc1424287a1278ffbdf9cd0a`.
Do not reuse the consumed GTK8 selection reply. Execute one capture/session
under the S1 branches above. Record the 20-second stream and intended PM +55 s
core stop independently; do not label that shorter controlled trial a full
60-second duration pass. Remote and local ownership/quiescence, evidence,
regression and the single reviewed return remain mandatory.


### S1 consumed — SSH stream and standard disconnect pass

One fresh boot `cff2c4f8-466d-406b-a7ad-d9f1e8bfee1e`, unchanged GTK8
kernel/image, host inputs `2a197328`, handoff `f12da769`. One read-only identity
acquisition matched the kernel/architecture/new boot and exact 84-byte notes.
One capture passed 285/285; one admitted session, one SSH attempt and one
standard disconnect request, without retry. The [single scalars file](results/s1-runtime-scalars.json)
records the independent verdicts and timestamps.

DHCP and initial replies 99.680 / 41.982 / 45.835 ms pass. The fresh authenticated
PTY stream returned five chunks at PM +3.375 / +8.475 / +13.585 / +18.705 /
+23.825 s: span 20.450 s, client elapsed 22.109 s, exit 0 and no stderr. The
channel-release credit at +6.252 s lies inside that stream. All five periodic
router probes replied after release, at completion offsets +10.575 / +20.615 /
+30.625 / +40.695 / +50.735 s. These observations establish a maintained
20-second authenticated exchange across release, not two or ten minutes.

The remote stream tag was absent in the single quiescence acquisition at
PM +24.985 s. The guarded standard supplicant disconnect was accepted between
+55.615 and +55.975 s. The driver ended data with reason `disconnect` at
+55.659 s, inside that request interval; data-phase elapsed 55,502 ms. The
controlled-transition verdict passes. The inherited full 60-second duration
and connected-data-after-release duration verdicts remain false, as intended.
Successful periodic traffic after release is recorded independently.

PM abort credited first; reserved deauth PID 48 completed with status 0 at
PM +55.777 s, acknowledged within its unchanged bound. PTK, GTK, station and
BSS-off commands all credited within 100 ms with floor zero; no second channel
abort. Whole-ledger cleanup stage 3 has `deauth=1`, zero page debt and both
local key disables status 0. No missing/retired/late deauth completion this run.
This differs from budget-end GTK8, but one changed host protocol cannot assign
the cause. Host cleanup and removal credits remain distinct from independently
proved firmware key erasure/queued-frame retirement. No rekey, reuse or reconnect.

Checked PTK/GTK handoffs 50/225; GTK ARP handoffs 106, withheld ARP 0. Data
TX queued/done/failed 43/43/0. No HIF refusal, capacity stop or 0x13 event.
Owned-beacon queue admissions remained 21 total/20 since PM; last age 53.648 s
at data end. Do not infer continuous beacon delivery or RF loss from that count.
All 75 seals, 2,202 contiguous log records, complete one-cycle export, local and
remote helper/device quiescence and regression verify. One reviewed return and
independent changed-boot Gemian `9dac50f6-816c-4c08-981d-79535cb56f69` verify.

Next is the source-supported persistent connected-station phase, with the
pre-data join fence and per-operation bounds retained and the existing five-second
teardown fence armed at data end. Do not obtain two/ten minutes by increasing
the finite join window. Before selecting its test, enumerate every remaining
measurement cap and exact monitoring/stop path. Stable-key/PID reuse, reconnect
and standard-scan acceptance remain separate open gates.


### After S1 — separate connected lifetime from join and teardown

**Source change selected, not yet a built or admitted device candidate.** GTK8
and S1 support traffic under the connected BSS after the join privilege is
returned; S1 also supports standard core-initiated teardown. Add one default-off
connected-lifetime option depending on that exact path. Preserve the ten-second
pre-data join fence and nine-second privilege. On successful data opening,
mark the connected data/lifetime horizons as unbounded, retaining all individual
command/frame/credit bounds. On the first data end, arm the existing five-second
teardown fence from that instant, preserving an earlier fence and never renewing
it on repeated calls. No U64 sentinel addition/overflow. Standard disconnect,
key withdrawal, station descent, capacity exhaustion and fatal events keep their
existing paths. Fatal poison and the stable-key re-arm exclusions stay intact.

The connected phase must not consume the cumulative 4,096 **join/teardown poll**
quota; its per-tick receive bound, scheduling period, transport deadlines and
memory/queue caps remain unchanged. Pre-data and teardown still consume that
quota. Bypass only the CCMP diagnostic's 60-second elapsed wall (including the
pre-read, post-read and mode-entry clamp); retain 4,096 RX frames, 1,024 checked
handoffs, 2 MiB RX bytes, 32,768 total lifetime packets, PID ceiling 127, the
8-frame/12,400-byte TX queue, 750 ms completion/drain and all retirement caps.
Native-ciphertext and option-off behavior must remain byte-equivalent after
preprocessing. A quota stop remains a real bounded result, never a duration pass.
These finite measurement quotas still prevent a sustained-support claim.

S1 consumed 2,308 worker polls and 420 received packets over roughly 55 seconds,
with 275 checked handoffs. Linear projections are only sizing estimates, not
firmware guarantees: a two-minute low-traffic stream is below current RX/checked
caps, while the old cumulative poll quota would bind around 80–100 seconds.
Keep the capacities unchanged for the next diagnostic; log the actual first
limit. No PID reuse or extra traffic to consume its remaining range.

**Next test design, not execution admission:** one fresh boot with a 120-second
owned authenticated SSH stream, followed by standard disconnect, using the
existing private leaf overall 300-second wall. The listener's current 90-second
bound, client's 25-second acquisition, 90-second helper poll and the remote
22-second stream wall cannot host it. Those host-only observation bounds need
explicit matched review/fixtures before installation: one bounded listener,
client and remote stream, retained stderr, ownership/quiescence before sealing,
and a predeclared standard-disconnect interval. ConnectTimeout remains 10;
firmware/frame/credit/teardown bounds stay unchanged. Do not launch the old leaf
or S1 helper with a persistent kernel and assume a two-minute measurement.

Decision branches: a complete 120-second stream followed by attributable
standard disconnect and whole-ledger cleanup passes that finite milestone;
an earlier quota, transport, monitor, client or cleanup stop is the first failure
with its exact time/stage. Unknown remote ownership blocks export/recovery.
No event tolerance, longer grant, rekey, key/PID reuse or reconnect is included.
Standard scan and ten-minute/same-boot reconnect acceptance remain open.


### After S1 review — one 50-second idle-tail comparison selected first

The connected-lifetime source above is prepared and its focused local fixtures
pass, including option-off parity and the first-end five-second fence at ±1 ns.
It has not been archived, built or admitted. The owner-supplied review selects
one timing comparison before that work continues; retain it as source-only.

S1 is the first recorded acknowledged reserved deauthentication with PM
indication present, after a standard mac80211 disconnect. Five PM-indication
boots are in the current GTK5–GTK8/S1 record; no sixth boot is inferred.
The last successful ordinary-data completion to reserved-deauth submission,
using the same log timestamp domain, was approximately 10.123 s for GTK7,
9.935 s for GTK8 and 0.223 s for S1. Earlier GTK5/GTK6 lack the same completion
timestamp instrumentation. Thus an idle correlation is supported, but neither
“at least ten seconds” nor a six-run uniform timing assertion is established.
No packet-level attribution of the extra S1 data transmission is available.

**I50 hypothesis and unique observation:** retain GTK8's budget-initiated cleanup,
but move its data/native observation walls from 60 to 50 seconds and remove only
the PM +50 s periodic probe. Leave probes at +10/+20/+30/+40 s and ordinary
short SSH authentication. No live-traffic injection or standard-disconnect
request before the driver budget stop. The new default-off `MT6797_CCMP_50S_IDLE`
profile adds only those two selected kernel constants; no monitoring flag,
crypto, RX format, event, cleanup order, grant or operation-bound change.
All existing capacities and the bounded-debt safety path remain.

**Admissibility/outcomes:** the last actual successful data completion must be
near the final scheduled probe and roughly ten seconds before deauth; unexpected
later host TX makes the intended idle comparison inconclusive, even if cleanup
passes. Missing deauth completion away from the old offset excludes that offset
as a necessary condition for the observed stall, but does not distinguish idle
from budget/core teardown ordering or other causes. Acknowledged deauth makes a
simple idle-only explanation insufficient; it does not identify a timer or
justify avoiding specific offsets. Another first failure is separate. Neither
result authorizes inserting an arbitrary data frame ahead of teardown.
The production direction remains standard mac80211 disconnect; driver budget
termination remains a diagnostic safety boundary.

The pinned `mlme.c` SHA-256
`97b33dcf39dd45fa5f00db314be9b1ff2e6aeb00d007060b35e9a0d501befc57`
confirms `CONNECTION_MONITOR` suppresses both software beacon and connection
monitor reset timers (lines 118–145); the current plan already records both.
The station's `IEEE80211_VIF_BEACON_FILTER` declaration and source-supported
owned-loss routing belong in the subsequent lifecycle candidate, not this
constants-only comparison. The next longer-window design must resolve bounded
PID retirement/reuse and rate/cap accounting before admission; do not assume
linear sizing or reuse a timed-out/uncertain PID. Key reuse, rekey and reconnect
remain disabled. No new firmware analysis or public mechanism claim.

Local actual-source I50 tests pass the selected opening, elapsed-wall boundary,
unchanged capacities, grant/release/uncertain-transport cases and six option-off
MAC/native preprocessing comparisons. Linux fixtures/checkpatch/build, actual
package provenance, the four-probe leaf and helper/classifier/source-routing
validation remain required before a guarded install or physical handoff.


### I50 built and composed — host validation before deployment

Kernel input `00f351eb37da1c52fe25039e5e9d0f495a2d945d`, source archive
`564bf3ce18ac0b915381482b3a096077c5827d3f`, profile
`mt6797-a53-wifi-ccmp-50s-idle`, 711 canonical patches. Linux actual-source
I50 and inherited grant/release tests pass. Strict checkpatch reports zero
errors/warnings/checks with only the deliberate synthetic-author DCO omission
excluded. An incorrect expected-SHA preflight and a filename-mode checkpatch
invocation stopped before compilation; corrected checks preceded the single
required Buildbox backend build. No source or device retry.

The build and fetched package validation pass. Package inventory SHA-256
`2baecfb31bdd9b0e7de7e53b327186433b5ae1a692a3d9fd2ad36a67f0e77dfa`;
[actual receipt](results/ccmp-stable-monitor-candidate-i50.json) SHA-256
`544ba48aa0b2a773d8400ce1db68bf190ff90fc6529fcb4254daef4de232fb87`;
full padded boot2 SHA-256
`7bc347261ba8246dd1a4a53fa0270ab4705e91f73f9bdb850fdc06f29937fa2f`.
The 84-byte boot-note SHA-256
`5b84b38e00d9099d2f9c488d09963b4206cbea14451c659b7e6920ee2d24ce51`
is independently checked against ELF, validated Image/symbol map and the sysfs
exporter; it differs from GTK8. The configuration oracle confirms only the
selected option is added; DT and RAM remain byte-identical to GTK8.

The reviewed four-probe leaf is
[join-ccmp-i50.sh](join-ccmp-i50.sh), body SHA-256
`48e782530ba35c1a8344c622093c50605c1d252086416e5cce4a227a3cd04bc6`.
Its only changes from the existing periodic leaf are comments and removal of
the +50 s probe. Shell syntax and ShellCheck pass. The new classifier requires
four replies, an actual 50-second budget end, the existing release/ownership
records and a measured last-successful-data-to-deauth log gap of 9–11 seconds,
with that last data completion at PM +40–41 seconds. Out-of-slot or extra later
TX makes the idle comparison inconclusive, regardless of cleanup outcome.
Missing cleanup must not erase an otherwise measured deauth observation.
Local parser cases cover those independent branches, malformed/duplicate TX,
wrong duration, missing probes and refusal of old GTK8/S1 evidence as I50.

All five new local host fixture groups pass: exact actual-package configuration
(ten parent refusals/nine child mutations), receipt/namespace/installer binding,
retained installer sources, retained session/recovery sources and completed
no-scan host ownership. No new SSH command, stream, packet capture, neighbor
flush, helper timing extension, monitor flag or device control API. Permanent
client output retention remains. Clean pushed-input Linux host validation and
reviewed guarded installation/readback/shutdown/host preparation still precede
a new owner physical boot2 selection. No I50 deployment or device run yet.


### I50 handoff ready — physical selection pending

Host bindings `eca5e7dd84de0e573f52f2591ea47d825ccfa9b0` are pushed. All six
clean pushed-input Linux host fixture groups pass. Known-good Gemian boot
`9dac50f6-816c-4c08-981d-79535cb56f69` was freshly verified before deployment.
The reviewed 603-line installer differs from the S1/GTK8 installer only in
candidate/tool/receipt/evidence/boot identities; device-guard SHA-256 stays
`0f0fc88ce4650590c6cb86f0ef5ce22b95b2a0f41c9b39b397e24e39cf9f0ebf`.
Bash syntax and ShellCheck pass. Two offline output-directory preparation
refusals were corrected before the single device installation attempt.

Live GPT, inactive/non-root target, power and predecessor checks passed.
Boot2 was written, synced/flushed and fully read back as
`7bc347261ba8246dd1a4a53fa0270ab4705e91f73f9bdb850fdc06f29937fa2f`.
The deployment seal and clean shutdown confirm. No new partition backup or
alternate write. Fresh runtime, exact mode-0600 deployment summary and complete
offline host preparation pass with the reviewed four-probe leaf and retained
short-SSH client output. No I50 capture/session has occurred.

Next requires a **new** owner physical boot2 selection with USB connected to
the custodian laptop. Verify a new mainline boot UUID, expected kernel/architecture
and exact 84-byte note SHA-256
`5b84b38e00d9099d2f9c488d09963b4206cbea14451c659b7e6920ee2d24ce51`
before one capture/session. The S1 physical reply is consumed. Keep the I50
outcome set and actual 9–11 second idle qualification above, no silent retry,
separate transport/network/SSH/cleanup verdicts, all evidence seals, quiescence
and the single reviewed return. One scalars file and one existing table row only
after the actual run. Connected-lifetime prototype and unrelated restored
research remain excluded from these published inputs.


### I50 consumed — acknowledged idle-tail teardown; SSH not reached

One boot `e8a4c5ca-1fda-42ad-a0f7-1b68e99c08f7`, kernel input `00f351eb`,
bindings `eca5e7dd`, handoff `6908713d`. One read-only identity acquisition,
one 285/285 capture, one session and one reviewed return; no retry. The
[single scalars file](results/i50-runtime-scalars.json) keeps the verdicts
independent. The 50,005 ms budget end, DHCP, initial three replies
104.318 / 31.964 / 43.725 ms, four periodic replies, checked PTK/GTK handoffs
11/191 and GTK ARP handoffs 78 passed; withheld ARP 0. Data queued/done/failed
11/11/0. No HIF refusal, capacity stop or 0x13 event.

Release sequence 29 credited at PM +6.259879 s with zero debt (25.079 ms).
The last successful ordinary-data completion was PM +40.144193 s. Its log
record precedes reserved deauth submission by **10,098.634 ms**, inside the
predeclared 9–11 s idle qualification, without another successful data completion.
Reserved PID 16 completed status 0 at PM +50.269067 s and was acknowledged.
PM abort and all five remaining cleanup command paths credited at floor zero;
whole-ledger stage 3, zero debt, no missing/retired/late completion, local key
disables status 0. The measured counterexample weakens a deterministic idle-only
stall explanation; it does not identify a firmware mechanism or justify offset
avoidance or insertion of a data frame. Standard mac80211 disconnect remains
the production direction; budget expiry remains a diagnostic boundary.

**SSH was NOT REACHED.** The owned host helper exited 1 without a receipt,
client observation, host ACK or network client attempt. Its standard CLI admits
numbered/GTK session names but rejects `session-ccmp-i50`. The exact refusal was
reproduced offline from the executed source SHA-256
`6d27cb8b8beccab4b0216e6c4b110935d457268abb0eefb3b784c00694d4477e`,
before client main or any command. Helper stderr itself was discarded by the
parent; this is a source-reproduced diagnosis, not fabricated runtime stderr.
No TCP/SSH failure or success may be inferred. Adapter fixtures exercised the
parent binding but missed the child CLI guard. A focused actual-main fixture
now covers that boundary; the correction admits only the exact I50 name and
keeps root, symlink, filename, platform and other-name refusals.

The immutable full-session classifier stays false: SSH/host ACK are absent.
Its idle-comparison aggregate is also false because it requires authentication
and the complete nine-file cycle protocol. This does not erase the separately
qualified kernel idle/deauth timestamps or the four retained replies. All
62 seals / 2,134 contiguous records and exactly the eight exported c1 frames
verify; the missing host-ACK frame was never created and is not synthesized.
Local helper/device quiescence, regression, one reviewed return and independent
changed-boot Gemian `0ad152bc-0456-4298-82d2-eb50d09ada81` verify. Owned-beacon
admissions were 21 total/20 since PM, last age 48.130 s; no continuous-beacon
or RF-loss claim. Standard scan remains incomplete.

No unchanged I50 repeat is selected merely to obtain a green aggregate. Fix
and verify the host namespace gate offline, then continue the connected-lifetime
source work. Before admitting 120/600-second streams, resolve bounded completed-
PID reuse and measurement accounting, add the source-supported station beacon-
filter declaration and normal owned-loss reporting, retain the pre-data fence
and arm bounded teardown on data end. Keep key reuse, rekey and reconnect
refused until their ownership barriers are supported. No new firmware analysis
or private explanation is published.


### Connected-lifetime successor — source gates before a 120-second stream

I50's result and host correction are pushed at `d05117bc` / `b2ba89d4`;
all seven actual-client-main namespace cases and the I50 verdict fixture pass
on Linux from the clean pushed checkout. No kernel build or unchanged-image
repeat is needed for that host-only correction.

Prepare one initial-key connected-lifetime candidate, with separate logical
archives and one eventual build. Retain all pre-data join/credit/frame bounds,
strict PTK/GTK PN checks, fatal transport poison and key/reconnect refusals.
The existing source-only connected phase is rebased onto the canonical I50
source with I50 disabled, so both profiles can preserve canonical patch order.

1. **Connected data and bounded teardown:** the successful data opening owns
   an independent connected phase, with no finite join/data wall. The first
   standard or resource/loss data end arms the existing five-second teardown
   fence; repeated callbacks cannot renew it, and an earlier fence wins. The
   cumulative 4,096 join/teardown poll quota excludes connected data, retaining
   its 20 ms worker and per-tick RX/transaction limits. Pre-data behavior and
   option-off behavior remain unchanged. Exact boundary/poison/native tests
   already pass locally; Linux and integrated validation remain.
2. **Completed PID ownership:** the verified public gen3
   [allocator and active completion handler](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_tx.c)
   rotate per-WLAN PIDs and match a completion to a pending WLAN/PID entry.
   The checked source SHA-256 is
   `1f479d41bab8e2b5bba68eb6514f3e977559d31d97c39c7833f3dc9f111cd1ed`;
   the public pending-list removal in `nic.c` is separately verified.
   Retain one host frame in flight. Rotate ordinary IDs only after the exact
   owned completion and whole TC1/TC4 ledgers. Reserve 127 for the lifetime's
   deauthentication, so a missing/late reserved completion cannot alias reused
   data. Unknown well-formed completions may be counted/discarded only after
   ownership classification; malformed/current-owned errors remain fatal.
   Local allocation generations are observations, not a new wire generation.
   Vendor matching does not prove that firmware can never duplicate an old
   same-ID event after wrap; no synthetic test or local generation will be
   represented as that proof. No station/key-epoch reuse is enabled.
3. **Monitoring contract:** declare `IEEE80211_VIF_BEACON_FILTER` only on the
   PM-required station path. Both software monitors are already suppressed by
   `CONNECTION_MONITOR`. A well-formed current owned-BSS 0x13 in a healthy data
   phase should end data and report standard connection loss once, with bounded
   cleanup rather than protocol poison. It is a disconnect, not event tolerance.
   Foreign, malformed, stale or pre-data events retain existing refusal. Keep
   reason values observational; no private explanation or decoded mapping.
4. **Observation capacity:** rescale the connected profile before the longer
   run, keeping real queue/memory and per-operation limits unchanged. The earlier
   observed 33 RX/s and roughly 770 KiB/minute imply about 19,800 acquisitions
   and 7.5 MiB over ten minutes before margin. Use connected-only ceilings of
   32,768 RX records, 8,192 checked handoffs, 16 MiB RX bytes and 65,536 total
   lifetime packets; their storage is still per-frame, with no larger queue.
   This also leaves margin for low-rate SSH traffic and the observed group load.
   The original native-ciphertext and existing-profile ceilings stay unchanged.
   These remain finite measurement limits, not an all-day operational claim;
   every actual first cap must be reported and normal-profile promotion must
   remove diagnostic lifetime termination after the path is proved.

Before building, fixture exact PID wrap/completion/credit/failure/retired-ID
ownership, stale and malformed events, first-end teardown at ±1 ns, native and
option-off parity and the integrated RX limits. A missing/uncertain ordinary
completion must poison; never recycle it on timeout. Key PN contexts never
reset with an observation counter or PID wrap. Keep callbacks/worker lock order
and source-proved standard loss reporting. One supported source assumption is
ordinary TX-done completion semantics used by the public driver; unsupported
firmware behavior is not manufactured by the fixture.

The eventual host protocol must carry a real 120-second authenticated SSH stream,
retain stderr/partial output, prove remote/local quiescence and then use standard
mac80211 disconnect with no private control API. Its listener/client/remote/parent
observation bounds need a separate matched review; ConnectTimeout and all firmware,
frame, credit and teardown bounds remain unchanged. Predeclare a first packet,
PID ownership, quota, monitoring, SSH-stage or cleanup failure independently.
Only after a validated 120-second result should the 600-second milestone and
safe second-key/station lifetime be admitted. No new device action is selected
by this source plan alone.


### Connected source prepared — build input validation pending

Four separately scoped archives are now prepared: 0219 separates connected
ownership and arms the first-end five-second fence; 0220 owns/recycles completed
ordinary PID slots and reserves 127; 0221 declares the station beacon-filter
contract and maps an exact owned live-data loss to standard disconnect/cleanup;
0222 selects the connected-only observation capacities declared above. The named
`mt6797-a53-wifi-ccmp-connected-lifetime` profile preserves all 715 selected
patches in canonical order, includes the I50 source option default-off, and
selects connected lifetime/completed PID reuse without selecting I50.

Local actual-source tests pass: six connected-lifetime option-off MAC/header
comparisons and ±1 ns first-end/unchanged native boundaries; 8,192 pure-pool
and 8,192 actual MAC allocation/completion transactions with wraps, pending
and credit/poison/timeout refusals, reserved-ID isolation, current/unowned/
malformed completion branches and three option-off MAC selections; exact
owned-loss body/256 reason values, foreign sequence/BSS, stale/pre-data/poison
states, once-only core reporting, station flag admission/removal and three
option-off MAC selections; capacity ±1/native/drain checks and six option-off
selections. No observer interprets numeric reasons or reads new registers.

The final combined source keeps nine crypto/HIF files and ten key/queue/core
callback bodies byte-identical to I50. The existing actual-header PTK/GTK
fixtures pass all 19,007 GTK/context/layout/PN/refusal cases. This does not prove
firmware enforcement or stale-event exclusion after an indistinguishable wire
ID reuse. Strict checkpatch is clean for all four archives apart from the
explicit non-certifying experiment author's DCO omission. No key/PN context is
reset by a PID wrap or a cumulative counter.

Clean pushed-input Linux fixture runs and the single required Buildbox kernel
build remain. No package or receipt is invented, and no new candidate is admitted
for a boot. The host-only 120-second stream preparation follows independently;
it must handle its own longer observation envelope and explicit namespace at
the actual child CLI, retain all client output, guard the remote PTY owner and
confirm remote/local quiescence before sealing/recovery. Standard connect,
DHCP, ping, SSH and disconnect remain the interfaces. Key reuse, rekey and
same-boot reconnect are still disabled.


### P1 host envelope — predeclared before implementation/admission

The first connected-lifetime run will require **120 seconds of authenticated
SSH traffic**, not a longer nominal join budget. Use 243 boot-bound PTY chunks spanning a scheduled 121 seconds
against absolute monotonic half-second targets, with the first chunk
admitted by PM +5 s. Require the actual device span at least 121 s and the client receive span at
least 120 s, with every chunk timestamped on arrival and no receive gap over
three seconds. The extra scheduled second permits measuring a full 120 s
receive interval despite transit variation; it is not a shorter-duration pass. Absolute targets prevent per-iteration shell overhead
from extending a relative-sleep loop; emission over 400 ms late is a distinct host result,
not a catch-up burst. The rate should exercise ordinary PID wrap; claim wire
reuse only when a completed reused slot is actually observed, not from a wrap
cursor alone. Raw client stdout remains capped at 64 KiB with actual/truncated
counts explicit, and stderr/neighbor/numeric-route retention stays permanent.

Verify the same boot/window before each
chunk, with the existing own foreground PTY PID/group/session guard before any
signal handler. The first-chunk PM +5 s bound is an admission cutoff, not a
periodic interval. The remote BusyBox command bound becomes 125 s, client
acquisition 135 s, helper poll 210 s and parent-owned helper join 270 s with the
existing five-second termination grace. These are **host observation bounds**
for the requested longer command. The parent bound covers the helper's 210 s
poll plus post-client USB observation (15 s), existing remote-owner absence
budget (20 s), one control call (15 s) and ten seconds of margin, including an
early driver failure. ConnectTimeout remains 10 s. Extend the actual child
CLI's poll admission and its exchange bound explicitly; test real main-path
admission, not just the parent adapter (the I50 gap).

The existing one-cycle leaf keeps its 300 s overall wall and finite owned-child
termination. Only its listener bound becomes 180 s, and scheduled single-probe
pings continue at +10 through +110 s (eleven); the full SSH stream covers the
last interval. Stopping probes at +110 avoids racing a final +120 probe against
standard disconnect. After normal SSH command completion and verified remote
stream quiescence, make exactly one guarded standard supplicant disconnect
within PM +120 through +135 s, without waiting for a particular instant or
injecting a teardown frame. That follows freshly completed traffic and avoids
attributing any outcome to a firmware clock. Refuse a stale, faulted or missed
control window and do not retry. If the stream fails earlier but the current window and
remote quiescence are positively verified, allow an explicitly labelled early
standard abort from PM +6 through +135 s; it cannot satisfy the duration or
completed-stream verdict. Keep the three-second BusyBox/15-second USB bounds. Key PN state and all firmware/frame/credit/teardown bounds are unchanged.

The parent refuses export, seal or recovery unless the local helper group and
the remote tagged command are quiescent. A late/failed/unknown owner observation
is a separate blocked preservation state, not an implicit timeout recovery.
Successful 120-second traffic, actual PID retirement/reuse, eleven probes,
standard-disconnect attribution and whole-ledger cleanup are separate verdicts;
a different first limit or failure is recorded with its offset. The 600-second
milestone and a second key/station lifetime remain later admissions. This plan
authorizes no physical run until the actual built package, composed candidate,
all host fixtures and guarded installation/readback/shutdown are validated.


### P1 built and composed — complete host validation before deployment

Clean pushed kernel input `71c4b4a818b5eef6330e0ca844407574941a017c` passed
all six Linux source fixture groups, all four strict checkpatch runs and the
single required Buildbox backend build. The final actual-header PTK/GTK fixture
again passed 19,007 cases. Final source archive
`e7be093e6f4200b03aaff56787dc8d74ca1f3468`; 715 canonical selected patches.
The validated/fetched package inventory SHA-256 is
`1e92619aac81cdc66479cc8d6a17ef168237436a7e2dacdf1feca0d0383055d1`.
The configuration explicitly enables connected lifetime and completed PID reuse,
with I50 disabled. No source/kernel rebuild follows host-only tooling below.

[Actual P1 receipt](results/ccmp-stable-monitor-candidate-p1.json) SHA-256
`d4cb557f4022547bf49d2f4961c9d12a3142332ebb0d19444c2edcfac833b89d`;
full padded boot2 SHA-256
`f19d4e27bd24fc38b091c8847440c051f83e92da3972865125ae4c0a0589e998`.
DT/initramfs are byte-identical to I50. The exact actual-package configuration
oracle passes twelve changed-parent refusals/eleven child mutations. The new
84-byte kernel-note SHA-256
`b0213c37e6080b8b334f73842ca3162390cdfeecb29d8eb93bd41d2c2bf9b160`
is independently checked against ELF, validated Image/symbol map and sysfs
exporter, and differs from I50. Composition changed no firmware/calibration or
credential material and does not establish hardware support.

The eleven-probe leaf [join-ccmp-p1.sh](join-ccmp-p1.sh), body SHA-256
`de6fe61312562e1c1dc429de92df48580c5ebeec6f307bf1488fccda64289a98`,
changes only the original periodic schedule, listener bound and explanatory
comments. It keeps the existing 300 s wall and child quiescence. The scoped
client helper SHA-256 is
`2c28acdf350943a6fc6159a5799d1f039830309d78f68d7cf9683a4ce867173d`.
Its host limit replay reuses the pinned frozen functions with only the reviewed
25-to-135 s exchange and 120-to-210 s CLI/poll constants changed; bytecode
comparison confirms unchanged authentication/ACK/receipt operations. The parent
uses poll 210 s, join 270 s, grace 5 s. The actual parent-generated argv reaches
that child CLI in the fixture; a standalone parent-only assertion is insufficient.

The stdout reader retains raw bytes up to 64 KiB, drains the pipe live and
records chunk arrival times. Device schedule 121 s / 243 absolute half-second
chunks must yield at least 120 s of client receipt span, with no receipt gap
over 3 s. Emission over 400 ms late refuses instead of catching up. Timeout
partial output, over-cap output, buffered-only delivery and receive stalls
remain negative independent results. A real child that cannot finish until
its first line is consumed proves the reader is live. The existing own-PTY
PID/session/foreground-group guard and hangup mechanism remain; real Linux
PTY validation is still required for these host inputs.

Nineteen local client cases pass (the Linux-only PTY case is skipped on the
laptop). Generated outer/inner stream, normal/abort control and owner-query
commands pass shell syntax/ShellCheck, and actual AWK programs execute in the
fixture. Slot trace/duration/controller verdict cases pass separately. All
five local adapter groups pass. The remote-owner parent gate refuses missing,
false or unknown ownership and never clears the inherited local unsafe state.
An unexpected helper exception retains a negative private host receipt and
unknown ownership; it cannot authorize recovery. Clean pushed-input Linux host
checks, guarded deployment/readback/shutdown and fresh preparation remain before
a new physical boot2 handoff. No P1 device run or public run row exists.


### P1 handoff ready — physical boot2 selection pending

Host bindings `2ec08e59b1e0fc37155d858129e3ed3479e97124` passed all eight
clean pushed-input Linux host fixture groups, including real PTY ownership/
hangup. The additional explicit early-SSH-failure cleanup case is published
at `7dc1d4969087556ad383a00b292f580c1a4bca53`; all twenty client cases pass
on Linux, with no skipped PTY case. This test-only refinement changes no
kernel, helper, candidate or receipt. An early abort cannot satisfy the
completed-stream duration/controller verdict.

Fresh known-good Gemian `0ad152bc-0456-4298-82d2-eb50d09ada81` was verified.
The reviewed 603-line installer differs from I50 only in candidate, tool,
receipt, predecessor, evidence and boot identities. Device-guard SHA-256 stays
`0f0fc88ce4650590c6cb86f0ef5ce22b95b2a0f41c9b39b397e24e39cf9f0ebf`;
Bash syntax/ShellCheck pass. One guarded boot2 installation passed live GPT,
inactive/non-root target, power and predecessor checks. Write/sync/flush and
full readback match
`f19d4e27bd24fc38b091c8847440c051f83e92da3972865125ae4c0a0589e998`.
Deployment seal and clean shutdown verify; no new partition backup, automatic
reboot or alternate partition write. Fresh runtime, exact mode-0600 deployment
summary and complete offline host preparation pass with the reviewed P1 leaf,
actual keys and unchanged retained source/recovery routing. No capture/session
yet, and no public P1 run row or result is invented.

Next needs a **new** physical owner boot2 selection with USB connected to the
custodian laptop. The I50 selection is consumed. Verify a new boot UUID,
expected kernel/architecture and exact 84-byte note SHA-256
`b0213c37e6080b8b334f73842ca3162390cdfeecb29d8eb93bd41d2c2bf9b160`
before one capture/session on the actual receipt above. Keep the source-defined
PID ownership, 121-second schedule / minimum 120-second received traffic,
eleven probes and normal/early-abort controller branches independently graded.
Unknown remote ownership holds sealing/recovery. Preserve all evidence before
the single reviewed return and independently verify changed-boot Gemian.
One scalars file/one existing table row only after the actual run; no silent
retry. Ten-minute traffic, standard-scan acceptance, key retirement/rekey/key
reuse and same-boot reconnect remain incomplete. Restored research stays out
of Wi-Fi commits.


### P1 consumed — server-duration limit, not the 120-second gate

The single admitted P1 boot ran the published kernel and host inputs in the
[scalars](results/p1-runtime-scalars.json). DHCP and three initial replies
passed. Six scheduled pings completed through PM +60 s. The SSH client
received ordinals 0–115 across 57.563 s, then exited 255 after 59.692 s. The
retained server log explicitly reports `Max duration reached`: the listener's
outer timeout was 180 s, but its unchanged Dropbear `-M 60` capped each
connection. Extending the outer timeout alone was insufficient. Duration and
the full admitted exchange failed; no host ACK was created. The helper issued
the predeclared early standard disconnect at PM +64.03–64.39 s.

The driver completed all 154 queued data frames, 158 ordinary PID allocations
and completions, including 32 reuses after owned completion. Reserved PID 127
was acknowledged at PM +64.189 s; all five remaining command paths credited
within their existing 100 ms deadlines, with stage 3 and no debt. Checked
PTK/GTK counts were 159/254, including 113 delivered GTK ARP frames and zero
withheld eligible ARP. No owned monitor-loss event or HIF framing refusal
occurred. Filtered beacon admissions totalled 20, with last-admission age
62.152 s at data end; these admissions do not prove continuous RF reception.

The original host stopped before sealing/recovery because the supplicant count
was one after the USB command closed. No retry or second radio session ran.
A bounded read-only inspection subsequently found the owned children absent
and the boot-bound quiescence record clear. A preservation-only continuation
revalidated both original gates, preserved all original evidence, exported the
eight existing cycle files without inventing a host ACK, and verified 89 seal
entries and 2,740 contiguous kernel records. One reviewed recovery was
requested. Its first watcher check was unconfirmed; a separate authenticated
check confirmed changed-boot Gemian. The original failure evidence is retained.

The USB server also has `-I 60`; its closure is consistent with no output from
the leaf during the periodic loop, but no server-side USB closure reason was
retained. Correct the SSH maximum-duration envelope and emit bounded numeric
progress on the existing USB channel before another 120-second attempt. Keep
the installed kernel unchanged and retain the same driver deadlines and caps.

I50's 10.099-second idle gap with an ACK at PM +50.269 s remains an observation
against a deterministic idle-only explanation. Earlier +60-second failures,
S1's +55.777-second ACK, and P1's +64.189-second ACK are an offset pattern;
they do not establish a firmware mechanism or a safe timing exclusion rule.
The suggested exact +63-second comparison has not run. No production rule to
avoid particular offsets or inject traffic is justified by these data. The
current first failure is the host envelope; fix that before another boot.


### P1H host correction — unchanged kernel, new explicit admission required

Hypothesis: the retained server maximum-duration option prevents the declared
121-second SSH stream; the quiet USB leaf also needs bounded progress to stay
inside its existing 60-second idle policy. Change only the external leaf: use
Dropbear `-M 180` under the existing 180-second listener timeout, and emit one
numeric progress line after each of the eleven existing periodic probes. Keep
`-I 30`, connect timeout, host client/remote/process budgets, driver deadlines,
firmware commands, resource limits and traffic schedule unchanged. No new
network frame is added for USB progress. Authentication options remain pinned.

The kernel package/input/profile and every boot artifact are byte-identical to
P1; no kernel rebuild is needed. The external-leaf receipt is repinned for this
correction. P1's historical receipt/source remain reproducible at its recorded
handoff commit. This is a separate run named P1H, with a fresh private runtime
root, not a resumed or repeated P1 attempt. No P1H device result exists yet.

The actual-leaf fixture checks that the server envelope covers the declared
remote/client stream and exercises the existing eleven-slot loop with
deterministic clocks and ping observations: exactly eleven numeric progress
records, all original scheduled offsets, no device or network action. Host
fixtures establish this envelope only; real 120-second received traffic still
requires the new boot.

Predeclared outcomes: full received span at least 120 seconds plus completed
ordinary PID reuse and standard whole-ledger disconnect passes this gate; an
earlier client/server/monitor/transport failure is recorded at its actual
offset and stage; a preservation or child-ownership refusal stops recovery
until classified and all original gates are satisfied. Keep individual
network, SSH duration, PID retirement and cleanup verdicts independent. No
600-second or same-boot reconnect claim follows from this gate.

The host correction is pushed at `15d4cf5e`; its actual-leaf fixture and
actual binding/preparation tests passed on a clean Linux checkout, alongside
Bash syntax and ShellCheck. Local config/provenance, retained installer/source
routing and repository checks passed. The fresh deployment-evidence namespace
is P1H so the original P1 deployment record cannot be overwritten. The reviewed
installer accepts the already matching full checksum and skips writing.
