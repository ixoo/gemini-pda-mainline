# Work item: one demonstrable boot2 keyboard session

- **Outcome:** Freeze the shortest safe path to one owner-run boot2 keyboard
  observation covering exactly the existing 20 cases / 25 distinct keycodes.
  Return either a session package that is offline-ready for final admission, or
  one concrete defect and the minimal repair needed to remove it.
- **Owner and reviewer:** Sol Medium owns the cross-file readiness audit;
  Project Planning integrates and implements accepted repairs; Astra Medium
  reviews process/VT/input ownership and device-session safety.
- **Scope:** This experiment directory for the worker. Inspect the existing
  keyboard packet, capture/supervisor/build sources, duration receipt, exact
  authenticated-baseline and supplemental recovery evidence, queue, current
  package/artifact references and guarded boot2 workflow. The integrator alone
  may edit shared keyboard code, queue, roadmap or deployment records.
- **Model route:** Sol Medium because readiness spans source closure, process
  lifecycle, evidence binding, baseline provenance and device-session ordering.
  Astra Medium is required for the final exclusive-reader, disconnect,
  power/budget and recovery decision. This is direct session preparation, not a
  new subsystem architecture audit.
- **Stop/escalation:** Do not broaden beyond the existing 20 cases/25 keycodes,
  add a second device observation, infer full keyboard coverage, or build/deploy.
  Stop with one concrete defect when readiness cannot be established from exact
  evidence. Escalate immediately on ambiguous process ownership, consumed
  budget, candidate drift, recovery contradiction or need for a kernel/DT change.
- **Parent:** repository commit
  `fa29ac5949416774f3bb5b46e76b34e8e4d049f8`; frozen SHA-256 values:
  `capture.py` `4523aa18b30e18b4a99449b8f61ec410d6566ef54e6f09c774b97f621676a238`,
  `monitor.c` `eb74dc09f6086aa47a7520f323f18728ab232b338ed02056d5b26338db9e5047`,
  `build-monitor.sh` `26bc8132735c2619c85afceed461d452f82ca7c9118cddcf214352140c10cfca`,
  `protocol.json` `5dd8b42b00a60041a9d5cb85f586ce639af6b62172a5488d8c0b73a0ed764306`,
  `classify.py` `be55d4d816c4c0709bed44dd77057b404aa3baf15d23aa7be46e966c98aaefa9`,
  duration receipt `a32fb3828de42ab5f214ea62b9ebf6df600ddeb64a67682907904f198204f9db`,
  attended outcome `589cacb51b21e4ca7e9e790caf1aadb0b0bb5c2eebf70972ea017d19db36dc23`,
  recovery review `bec1377df7135cf552eac0f299bfbd97e0fe6554ec030d820bd4d37f0e484aa6`,
  foundation `a32fcfb2dd8d8e446c202e3fd7af68342b93db5f642975c05685b470e4c0b994`,
  queue `8198768d4c994432b460c34cb4bc2cd46b907654734e9d9d3526d03e7c7b1449`.
- **Dependencies:** Reuse the exact proven baseline kernel/DT/config if it
  supplies the required AW9523 matrix, map, tty1, USB and logging contracts.
  Identify a kernel/DT change only from a concrete missing predicate; any needed
  kernel build is Buildbox-only. An enabled monitor userspace build and exact
  Dropbear disconnect proof may be required and must be separately pinned.
- **Worktree:** Shared checkout; worker ownership is limited to
  `experiments/2026-09-07-keyboard-boot2-session/`. Other work exists; do not
  revert or overwrite it.
- **Validation:** Recompute frozen identities. Enumerate every readiness
  predicate with evidence or a named gap. Inspect normal/disconnect lifecycle,
  partial preservation, target shell, input and tty reader exclusion, map/meta
  checks, boot/logger/session/power ceilings, one-shot claims and changed-ID
  known-good recovery. Verify protocol counts mechanically.
- **Hardware:** Audit only. No device access, installation, boot, key press,
  capture, power action or recovery action in this work item. The later session
  has one capture claim, no retry, stable external power, and one owner physical
  boot2 selection; the custodian owns all other operations.
- **Upstream:** Not an upstream topic. It measures the already-developed
  keyboard path and changes no support claim until exact runtime evidence passes.
- **Owner-away work:** Complete the offline readiness/defect packet and release
  the worker. Do not substitute another architecture investigation.
- **Device readiness:** `preparing` until exact candidate/package/admission,
  disconnect proof, exclusive-reader preflight, budgets and recovery card pass
  independent review. Queue selection remains null until the integrator freezes
  a conditional/ready packet.
- **Handoff:** Create `READINESS_AUDIT.md` and `results/readiness.json` with the
  exact adequate kernel/candidate decision, evidence matrix, minimal required
  source/build changes, finite session phases, refusal/recovery branches,
  owner card outline, one concrete current blocker and `review_ready_utc`.
- **State:** active at `2026-09-07T20:59:41Z`.
- **Efficiency loop:** If accepted as an offline item, append its measured route
  and outcome to pilot 04. A later device session is excluded from that ledger.
