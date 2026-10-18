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

Linux validation from clean pushed inputs and one standard corrected-budget
kernel build are next. The candidate remains low traffic: no PID reuse and no
continuous SSH workload is promised. If a different ceiling binds or a protocol,
transport or cleanup fault occurs, record that first point separately.
