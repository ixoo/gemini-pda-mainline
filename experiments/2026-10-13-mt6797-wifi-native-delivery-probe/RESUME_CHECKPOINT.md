# Wi-Fi resume checkpoint — INCOMPLETE

**I50 consumed once: duration/network/acknowledged cleanup PASS; SSH NOT REACHED.**
Boot `e8a4c5ca-1fda-42ad-a0f7-1b68e99c08f7`, kernel `00f351eb`, bindings
`eca5e7dd`, handoff `6908713d`. [One row and analysis](SESSION_0202_PLAN.md#i50-consumed--acknowledged-idle-tail-teardown-ssh-not-reached),
[one scalars file](results/i50-runtime-scalars.json). Data budget 50.005 s,
initial 3/3 and periodic 4/4 replies, release credit and whole-ledger stage 3
pass. Reserved deauth ACK followed a measured 10.099-second data-completion
idle gap; this weakens idle-only causation without identifying a mechanism.
The host helper refused the I50 namespace before client/TCP; no SSH result or
host ACK exists. The exact child-CLI guard is reproduced offline. The immutable
full-session verdict remains false. All 62 seals, 2,134 contiguous records,
eight available cycle frames, quiescence/regression and reviewed return verify.
Independent Gemian `0ad152bc-0456-4298-82d2-eb50d09ada81`. No pending physical
action or unchanged I50 retry. Correct the narrow host admission gate with an
actual-main test, then resume connected-lifetime/PID/accounting/monitoring
source work before longer-window admission. Key reuse/rekey/reconnect remain
disabled and full Wi-Fi acceptance remains incomplete.

**S1 consumed once: controlled core disconnect and 20-second SSH stream PASS.**
Unchanged GTK8 image, boot `cff2c4f8-466d-406b-a7ad-d9f1e8bfee1e`; host inputs
`2a197328`, handoff `f12da769`. [One row and analysis](SESSION_0202_PLAN.md#s1-consumed--ssh-stream-and-standard-disconnect-pass),
[one scalars file](results/s1-runtime-scalars.json). DHCP, initial 3/3 and
post-release periodic 5/5 pings pass. Fresh authenticated SSH produced five
chunks spanning 20.450 seconds across the +6.252 s channel-release credit;
client exit 0, no stderr. Standard disconnect accepted near PM +55.6 s ended
data with reason `disconnect`, elapsed 55.502 s. This planned stop is not a
full 60-second duration pass. PM abort, acknowledged deauth and all remaining
cleanup commands completed; whole-ledger stage 3, zero debt, local disables 0.
No HIF refusal, capacity stop or 0x13 event. Owned-beacon admissions were stale;
no continuous-beacon claim. All 75 seals / 2,202 contiguous records, one-cycle
export, remote/local/device quiescence, regression and one reviewed return
verify. Independently confirmed Gemian `9dac50f6-816c-4c08-981d-79535cb56f69`.
No physical action or S1 retry is pending. No S1 kernel build/change occurred.

The I50 preparation/handoff and S1 successor plans below are consumed history;
use the current I50 result at the top. Connected-lifetime prototype remains
unarchived/unbuilt; longer-window admission still needs the source gates above.

**GTK8 consumed once: finite capability, post-release protected traffic,
60-second duration and whole-ledger host cleanup PASS.** Boot
`a996ec5e-fc20-49d3-a160-2ed321e3e156`, kernel `8792a406`, bindings `49ff0b1c`,
handoff `b9555ddf`.
[One row and analysis](SESSION_0202_PLAN.md#gtk8-consumed--protected-traffic-beyond-the-join-privilege),
[one scalars file](results/gtk8-runtime-scalars.json).

The 9,000 ms join privilege was submitted for release at PM +6.275 s and
credited at +6.300 s (25.016 ms, no deadline extension). All five periodic
probes replied beyond that credit and the original reported grant horizon;
owned successful data completions continued through PM +50.296 s. The window
ended by budget at 60,009 ms. DHCP, three initial pings and SSH exit 0 in
1.397 s passed. SSH authenticated **before** release and closed; no maintained
post-release authenticated stream is claimed. Checked PTK/GTK 42/231, GTK ARP
handoffs 106, withheld 0. No HIF refusal, capacity stop, pre-budget AP loss or
0x13 event. Standard scan acceptance remains open.

PM abort credited first; reserved deauth PID 40 still missed 750 ms and later
returned status 5 during removals. No ACK or invented refund. The ledger
returned whole at station removal; cleanup skipped a second channel abort and
credited BSS-off at floor zero. Host stage 3, zero debt, local key disables
status 0. This is host cleanup success, not acknowledged deauth or independent
firmware key/queued-RX retirement. Owned-beacon admissions were 21 total/20
since PM, last age 58.114 s; do not infer continuous beacon delivery or RF loss.

All 71 seals and 2,186 contiguous records, complete one-cycle export,
helper/device quiescence, regression and one reviewed return verify.
Independently confirmed Gemian `4f0120ad-fa64-462a-82d3-c2c3f9b0a30e`.
Two read-only identity invocations preceded the one capture/session: the first
used the SSH helper incorrectly and exited nonzero; the corrected stdin
invocation verified identity. No radio/session retry. No live device process
is pending for GTK8, which is consumed; S1 is also consumed as recorded above.

The S1 preparation/handoff above is historical and consumed; use the current
S1 result at the top for the next source decision.

Prior GTK7 result follows as history; its successor below is now consumed.

**GTK7 consumed once: capability and 60-second low-traffic duration PASS;
whole-ledger cleanup stage 3 reached, deauthentication still unacknowledged.**
Boot `138674d4-2aff-4ff5-ad75-a0670d432b36`, source `8aed6b61`, tooling
`cd1a81ef`, handoff `1cfeb81e`.
[One row and analysis](SESSION_0202_PLAN.md#gtk7-consumed--whole-ledger-cleanup-with-late-deauthentication),
[one scalars file](results/gtk7-runtime-scalars.json).

Data ended by budget at 60,011 ms. DHCP, initial three replies, SSH exit 0 in
1.618 s and all five periodic numeric-router probes passed. Checked PTK/GTK
41/238; GTK ARP handoffs 107, withheld 0; no named HIF refusal or 0x13 event.
Every owned TX completion and cleanup command timestamp is exported relative
to the 0x16 credit. No continuous SSH-traffic claim is made. Standard scan
acceptance remains open; the passive-scan classifier reports no standard BSS.

PM abort credited **before** reserved deauth. PID 41 still missed 750 ms and
was retired with one page debt, without ACK/refund. Removals proceeded under
the existing 100 ms bounds. The ledger returned whole during station removal;
late retired completion status 5 followed. Channel abort/BSS-off credited at
floor zero; healthy stage 3, `deauth=0`, both local disables status 0. This is
whole-ledger cleanup with an unacknowledged frame, not a bounded-debt terminal
or timely deauth success. PM-abort-first did not cure the missing completion;
periodic traffic also changed, so unique causal attribution is unavailable.

Owned-beacon admissions at data end: total 21, since PM 20, last age 58.162 s.
Do not claim continuous beacon delivery or infer RF loss from this counter;
phase-1 type-7 total 110 is not an owned-beacon count. All five periodic pings
replied, so the predeclared fixed-offset host-TX failure trigger did not occur.

All 71 seals, 2,185 contiguous kmsg records, complete one-cycle export,
helper/device quiescence and A53 regression verify. One reviewed return and
independent Gemian identity confirm `78b701cf-cb65-4283-bc32-dbe7dadb5497`.
GTK7 has no live device process or retry pending and is consumed; the new
GTK8 physical handoff is recorded above.
A default-off [connected-channel comparison](SESSION_0202_PLAN.md#after-gtk7--bounded-connected-channel-ownership-comparison)
is prepared under 0217: a nine-second join grant released during the unchanged
60-second window, original command/frame/tail limits, periodic traffic and
GTK7 teardown. Local and Linux actual-source/option-off/HIF fixtures and the required
Buildbox build pass at `8792a406`; [GTK8 package/host bindings](SESSION_0202_PLAN.md#gtk8-validated-package--host-binding-validation-pending)
are prepared from the validated package. Five host fixtures and the
strict post-release verdict pass locally and on Linux. Guarded installation
and offline host preparation now pass; physical GTK8 selection is pending
as recorded above. No GTK8 hardware observation is claimed. Two/ten minutes of authenticated SSH traffic and same-boot reusable
lifetimes remain unproved.

Keep 0x16 before keys, counter-only 0210/fatal event refusal, connection-monitor
flag, no nullfunc, existing frame/command deadlines and resource caps. No PID
or key reuse, rekey or reconnect. Keep publications on `main`; preserve public
measurements and exclude firmware-RE explanations/private source identities.

Earlier GTK6 command-path credit with one retained page and its whole-ledger
stop remain recorded in the [prior analysis](SESSION_0202_PLAN.md#gtk6-consumed--command-path-credit-with-a-retained-page)
and [scalars](results/gtk6-runtime-scalars.json). Do not repeat it unchanged.

GTK1's prior ERANGE is classified and its [0205 correction](../../patches/proposals/0205-wifi-mt6797-retain-the-validated-channel-grant-horizon.patch)
is proved to permit the requested data budget in GTK2. GTK1 had both keys
submitted/credited before refusal and lacked healthy cleanup; it did not test
GTK/network/SSH. Earlier intermittent SSH silence remains unclassified. D3 and
GTK2 both resolved an initially absent neighbor without proving how.

The [reviewer reassessment](SESSION_0202_PLAN.md#reviewer-reassessment-before-further-implementation-or-any-build)
corrects the all-`0xc200` premise: C11's 32 eligible groups required `0xc000`.
Expanded 2,718 actual-source cases and eleven paired-helper cases pass locally
and on Linux from clean pushed input `f45b7645`. The owner adopted group-first
preparation. The independent 60-second window and permanent standard client
stderr/netstat retention passed locally and on Linux at `5b92d39a`.
The strict initial-GTK context/checker is implemented under the
[predeclared source contract](MAC80211_GROUP_RX_CONTRACT.md#predeclared-initial-gtk-preparation).
Its actual-source fixtures pass locally and on Linux from clean pushed input
`4bde0dbf`, including canonical overlay compatibility and seven standard-client
cases. See the source contract for scope and deliberate checkpatch exclusions.
No hardware GTK acceptance or SSH-cause proof is claimed. Preserve strict
PN/integrity/ownership requirements.
0202 remains separate and unbuilt. The owner resumed regular builds/tests;
0203/0204/0205 ran as GTK2 and the admitted capacity successor is built. Keep one scalars
file and one table row per future run; no per-run result documents. No -48
adjustment, longer transaction deadlines, rekey, reuse or reconnect.

Prior framing result: [D2](SSH_D2_RESULT.md) consumed once on unchanged C10.
Port 0 advertised 94, staged descriptor 142; complete advertised PIO transfer
then equality refusal/poison/no-copy. Fault at ENABLE_PENDING, branch 4/-71,
23.238 ms after data-phase log, not a timeout. DHCP/pings/SSH and all local
queries were not reached. Healthy cleanup failed; one page debt retained.
Seal/quiescence/A53 regression and changed-boot Gemian independently verified.
C10 remains installed but consumed; no physical selection is pending.

The [bounded RX contract review](D2_RX_CONTRACT_REVIEW.md) verifies exact C10
source, TX-only arm quiescence and retained pre-arm WHISR 0x2. Public gen3 mapping
suggests an RX indication; this is not a FIFO/producer fence. New enable-time
+48 differs from historical close-time -48. The actual-source regression now
covers 94/142 on both ports, valid 94 and I/O faults; local ASan/UBSan passed.
No host framing correction is proved. The [follow-up source review/proposal](RX_FORMAT_OWNERSHIP_SUCCESSOR.md)
selects one fixed-format ownership comparison: initialize before scan-ready,
retain the format for the firmware instance, keep data-window/crypto gates.
Exact C10 EAPOL headers passed 48 existing cases on Linux with ASan/UBSan.
The [0202 prototype](FIXED_RX_FORMAT_PREPARATION.md) is implemented and passes
1482 ASan/UBSan cases plus RX/option-off comparisons locally and on Linux.
The separate approved 0203 window patch passes actual-source boundary/parity
checks. Final strict patch review has only the intentional missing DCO sign-off.
The old A/B plan is superseded: no further ARP-pair boot. Initial GTK plus the
independent window is next; no kernel build or execution is admitted.

The [three-run C10 baseline](CCMP10_BASELINE.md) remains SSH 2/3, all its finite
transport/network/host-cleanup windows passed. [D1](SSH_D1_RESULT.md) passed
without reproducing failure. Exact earlier TCP/KEX/auth failure stage remains
unknown; D2 does not classify it. [C11](CCMP11_RESULT.md) did not enable GTK.

Keep equality, complete transfer, poison/no-copy; no -48 adjustment, longer
transport deadline, speculative register or unrelated callback RE. GTK delivery
remains disabled on tested images; the default-off prototype is unbuilt. Rekey,
reuse and reconnect stay disabled. Staged 60 s / 2 min / 10 min and full
Wi-Fi acceptance remain incomplete. The pause record below is historical.

Historical pause boundary. The owner explicitly resumed implementation on
2026-10-17; see the [completion successor](CCMP_COMPLETION_SUCCESSOR.md) for
the new source/evidence review and candidate gates. The frozen C5 result and
old launch commands below remain consumed, not repeatable instructions.

**Owner stopped work after the single CCMP5 test and reviewed return. This
checkpoint authorizes nothing beyond preserving the record.** No driver work,
tests/builds, analysis execution, candidate selection or device action resumes
automatically. No unchanged C5 retry. No next candidate or fix is decided.

## Read these records, not the old launch commands

1. [CCMP5 result](CCMP5_RESULT.md): earlier -110/branch1 timeout, one checked
   Ethernet queue, no DHCP lease/SSH/full pass, no observed HIF refusal. Exact
   frozen kernel/profile/package/receipt/tool/deployment/boot identities and
   evidence seals are there; the deployment's full checksum is custodian-verified
   supplemental metadata, not a copied deployment record or new live inspection.
2. [CCMP5 preparation](CCMP5_PREPARATION.md): package/composition/receipt pins
   and tooling bindings; historical instructions are consumed, not a new run.
3. [0195 controlled comparison](RUNTIME_NO_POST_PROPOSAL.md): exact source,
   patch/body, two MAC entry points, preserved boot-reader post metadata and
   boot-drain invariants, focused actual-source tests and causal limits.
4. [C4 result](CCMP4_RESULT.md) and [C3 result](CCMP3_RESULT.md): finite WPA2/
   DHCP/one-ping progress, no SSH ACK/full pass, later post-CLOSED gap48. C4's
   staged0x4000 is an untrusted hint, not a certified packet/producer identity.

Latest executed tooling is `0f70e74bcd0d1fcafa4b47f8e94996e04cedc65a`; immutable
kernel input is `ea1fc0056738453a6e0d76cbea1d82db7ebbea48`; source85d1d621.
This documentation checkpoint does not require another kernel build. Candidate,
receipts, completed tools and prior evidence remain unchanged.

## Preserved state and boundaries

- Last confirmed current OS: Gemian3.18.41+/aarch64, changed boot
  `d09f829e-2a7e-4b5f-a240-b718c63f26ff`. Boot2 retains full C5
  `776cccbe841af9e36ccf981f19ec30456c61b819c6fa3d113dcd59c59533b812`.
- One capture/session, one reviewed return, helper/device children quiescent,
  full log preserved and63-entry seal verified by the custodian. See result for
  exact hashes and independent-verification scope. No pending retry is owed.
- Previously proposed bounded analysis remains **UNEXECUTED / HOLD**; it is not
  an approved next action. No new output or producer mechanism is established.
- Maintained Wi-Fi is incomplete: normal-mode per-frame PN/integrity/replay,
  key-epoch retirement/GTK/rekey/reuse, transport/resource/lifetime reliability
  and clean-profile ten-minute acceptance are unresolved. See the existing
  [support matrix](../../docs/HARDWARE_SUPPORT.md) and
  [roadmap](../../docs/ROADMAP.md); this checkpoint does not promote support.

## Next decision, only after an explicit owner resume

First review the **recorded earlier timeout and the read-sequence comparison**:
what stopped branch1 before the C3/C4 comparison point, which required evidence
is actually present, and which explanations remain unproved. Absence of a later
refusal cannot discriminate a repair when the trial terminates earlier. That
decision is not an instruction to boot, build, scan, add observers, relax RX or
retry C5. Resolve scope and review a concrete next proposal before new effects.

Keep one custodian for any eventually admitted device work; retained identities
are not fresh live checks. All safety/boot2/evidence/finite-budget/one-return
rules remain mandatory. Until the owner resumes: **HOLD**.
