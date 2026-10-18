# Wi-Fi resume checkpoint — INCOMPLETE

Current continuation: [C11](CCMP11_RESULT.md) is consumed once. G1 was present
on 32/32 eligible group shapes, still withheld from delivery. DHCP and three
pings passed; SSH exit 255 had no authenticated boot/ACK. Transport and host
cleanup passed independently. Seals, quiescence, regression and changed-boot
Gemian were verified. [Unchanged C10 run 2](CCMP10_BASELINE.md) is now installed
with matching full readback, clean shutdown and complete host preparation.
Await owner physical boot2 selection; no run-2 capture/session has started.
C10 is the earlier finite authenticated-SSH pass.

Next: follow the [owner-directed unchanged C10 baseline](CCMP11_RESULT.md#owner-directed-next-decision-unchanged-c10-baseline),
up to three total C10 sessions including its original pass. No new candidate
or build. Compare separate SSH and transport/network/cleanup verdicts before
choosing a diagnostic. Only then review 60 s / 2 min / 10 min lifetimes.
GTK delivery, rekey, key reuse and reconnect stay disabled. No length adjustment,
longer transport deadlines or unresolved-callback RE without a specific test need.
Each fresh session needs its own physical boot2 selection; stop at that handoff.
The pause record below is historical.

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
