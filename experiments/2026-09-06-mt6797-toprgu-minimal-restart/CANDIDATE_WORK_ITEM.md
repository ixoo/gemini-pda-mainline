# Work item: minimal TOPRGU authenticated runtime candidate

- **Outcome:** Construct and independently validate one deterministic,
  secret-bearing Android-v0 boot candidate that combines the exact validated
  `mt6797-toprgu-minimal-restart` kernel package with the runtime-proven
  current-tree serviceability DT contract and the authenticated A53 userspace.
  Freeze a one-restart session packet and refusal fixtures. Preparation stops
  before queue selection, device access, installation, or physical admission.
- **Owner and reviewer:** implementation owner Hume; integration reviewer
  Curie; the primary task owns integration, private artifact construction,
  Buildbox use, the experiment queue, the workflow ledger, commit, push, and
  every device action. The implementation owner is not alone in the
  repository and must preserve and accommodate concurrent work.
- **Scope:** the implementation owner owns new candidate, DT-composition,
  installer-adapter, session/classifier and test files below this experiment,
  plus narrow updates to this experiment's README and this work item. Do not
  edit the kernel patch, canonical or named series, configuration fragments,
  manifest, roadmap, experiment queue, workflow ledger, shared scripts, or
  historical experiment files. Derive reusable behavior through exact
  source-identity checks; do not rewrite historical evidence.
- **Model route:** bounded implementation uses `gemini_implementer`,
  `gpt-5.6-luna`, high effort. Cross-file integration and safety review use
  `gemini_reasoner`, `gpt-5.6-sol`, medium effort. This is the project default
  route for bounded implementation with a multi-file candidate contract.
- **Stop/escalation:** stop on ambiguity about the runtime-proven DT resource
  contract, a need to enable another power/CPU/clock action, any automatic
  reboot path, inability to obtain exact authenticated-userspace inputs, or a
  candidate larger than logical `boot2`. After two repair attempts, return the
  exact failures and next discriminating check. Do not weaken an identity,
  attribution, authentication, safety, or recovery gate to obtain a pass.
- **Parent:** repository commit
  `e1553f472cb4a1c9ff0a193c0910cb83c26ddb1d`; exact validated Buildbox package
  inventory SHA-256
  `9b14f15515bb56ec19eb39611a1262edfe56d9df25d3ed69828c4318d76498ca`;
  package `Image.gz` SHA-256
  `78f4c931fbb03ea18ea1cbb5c4bff72d68376a39a92f2b9c57b8fb86d4f5f2da`;
  package base Gemini DTB SHA-256
  `d7b583545fc3b4916c363d9e4b70d0ee7aef815675ca8ba58894bdbaa2e1dccc`;
  resolved configuration SHA-256
  `273e9c60fd0036551e5f1c295cd4fb8cb5acd3bcd41307485deb9979f510287c`;
  source SHA-256
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`.
  The current-tree serviceability control experiment owns the hardware-passed
  DT/resource lineage. Its DT transformer SHA-256 is
  `550527d86331bd5eb037ba60e787dc7f132a136f005c89e8864c58721ed9dc7d`
  and its independent candidate/DT validator SHA-256 is
  `332aa7baf063f817552c3394ef55c6448aa19c9703703fc6148475d9520b355a`.
  The authenticated-baseline experiment owns the userspace, credential,
  logging and recovery contracts. This item selects the already published and
  locally fetched userspace from revision
  `e9c028005b88ef8536ecb58c095e8d172253fa12`, whose `SHA256SUMS` SHA-256 is
  `dfeb746505b7ad01423e91e952e76620f845b048ae2e8c5cf8a311e0d4443e60`.
  Its candidate builder, independent validator and credential provisioner have
  SHA-256 values `365e6ba85693abb4a273efc4160abaeea78e425867903c9a5a706738694dc104`,
  `ef76e8b99aeb94dc56651752855efdb493bdfabbd31fbd91a0cba07f1a7f22bb`
  and `eabe2167a4bfb97a4ca763d5d1a6c918ae65e8738d57736323a86e45d5ef163c`.
  The accepted runtime and supplemental-recovery evidence are pinned by
  `ATTENDED_OUTCOME.md` SHA-256
  `589cacb51b21e4ca7e9e790caf1aadb0b0bb5c2eebf70972ea017d19db36dc23`
  and `RECOVERY_WITNESS_REVIEW.md` SHA-256
  `bec1377df7135cf552eac0f299bfbd97e0fe6554ec030d820bd4d37f0e484aa6`.
  They establish authenticated serviceability, complete log preservation and
  changed-ID return for preparation; the original native-disconnect witness
  and whole-session aggregate remain inconclusive.
- **Dependencies:** source-pin an adapter to the exact current-tree DT
  transformer and replay its same 20 property mutations plus one added disabled
  SCP node against base DTB `d7b583...`. Require all unrelated nodes,
  properties and raw values from that base unchanged. Independently recheck USB
  peripheral mode, I2C5/AW9523 polling keyboard, the three handoff windows,
  disabled SCP/clock/BigiDVFS/ram-console paths, absent watchdog IRQ, CPU8/9
  closure and every retained ramoops/reserved-memory region. Build two
  byte-identical outputs; the old transformer cannot be run unchanged because
  its old base/output hashes are historical evidence. Use only the fetched
  published userspace named above. Fresh private credentials have been selected
  and provisioned through the exact reviewed provisioner; this establishes the
  proven key format and transport, not runtime proof for the new key bytes. Any
  credential change creates a new candidate identity. The initramfs must require release
  `7.1.3-gemini-mt6797-toprgu-minimal-restart`, authenticate over the existing
  USB-only address, preserve bounded kernel-log capture, expose exactly one
  candidate-specific native ordinary-restart wrapper, and replace every old
  release and Candidate-AB marker in executable paths. The root shell and
  BusyBox retain effectful applets, so the enforceable closure is: no automatic
  or admitted userspace-watchdog, storage, radio, load, thermal, CPU8/9,
  experimental power/register or other effectful action. The builder computes
  a canonical `input_id` over the exact public kernel/DT/foundation/userspace/
  credential/source inputs and substitutes it into both durable markers; the
  host classifier rejects a marker with a different input identity. The session generator
  must source-pin its exact allowlisted remote command; only the single restart
  wrapper is admitted.
- **Worktree:** this small patch-repository checkout only. Generated userspace,
  credentials and candidates stay mode-private below ignored `artifacts/`.
  Use the managed Buildbox only for an exact published userspace fetch/build;
  do not use the native VM kernel-build backend and do not copy a Linux source
  tree.
- **Validation:** require clean-source and exact-origin checks; complete kernel
  package inventory/provenance validation; two byte-identical DT, initramfs,
  raw Android-v0 and exact-size padded constructions; Android-v0/LK address,
  header, alignment, appended-DTB and size checks; exact initramfs inventory
  and credential modes; release/profile/config/series/patch identities;
  serviceability-resource and action-closure checks; guarded-installer source
  pinning and refusal fixtures; session state-machine tests for identity,
  authentication, marker, reboot count, timeout/disconnect, log preservation
  and changed-boot recovery. Run normal and optimized Python tests, shell
  syntax/ShellCheck where applicable, `git diff --check`, and the repository
  gate. Offline fixtures must not access a device, network, credential private
  key, or boot image outside their disposable roots.
- **Hardware:** none for implementation. Before readiness, the session packet
  must freeze the current known-good Gemian identity; the exact recovery key,
  host pin and native recovery-tool identities; a named custodian; and the
  complete guarded deployment contract. Deployment resolves logical `boot2`
  from the live GPT and refuses unless it is the exact writable target,
  inactive, unmounted, holder-free, swap-free, distinct from root and its whole
  parent, the expected current selection/predecessor, large enough, and on
  stable power. It records the predecessor checksum, pads to the exact target
  size, writes once, syncs/flushes, requires matching full-partition readback,
  then shuts down cleanly without reboot. A preflight must prove the recovery
  path/tool before the physical action.

  A later admitted session may spend one physical `boot2` selection and exactly
  one ordinary restart request. The collector is armed before selection. Allow
  at most 90 seconds for the exact USB interface, then 15 seconds per strict
  SSH exchange. First require the exact raw and padded candidates, release,
  boot ID, authenticated SSH host/key, USB-only transport, CPU0--7 online,
  CPU8/9 offline, healthy logger, reserved ramoops identity and absence of a
  userspace watchdog. Observe at least 45 seconds of stable idle—past the known
  roughly 31-second watchdog timeout—with no countdown or automatic reset.
  Then invoke exactly one candidate-specific wrapper. It must durably record in
  ramoops the candidate entry marker, candidate/boot-bound request marker and
  the subsequent `reboot: Restarting system` line, while the host observes the
  reset/USB disconnect within 5 seconds. The host preserves available evidence
  before recovery, and recovery must establish known-good Gemian with a boot ID
  different from both the deployment OS and mainline. The watchdog-class boot
  reason is supporting evidence only and cannot distinguish direct software
  reset from watchdog expiry.

  Offline candidate, deployment or recovery-preflight identity failure before
  selection is a refusal and consumes no physical action. Once the owner has
  selected `boot2`, absent exact USB at 90 seconds or any runtime identity,
  authentication, serviceability or logger failure is inconclusive, consumes
  the selection, and permits evidence preservation and recovery only—no restart
  request or retry. After selection, an automatic reset, missing durable
  marker/order, returned restart command, disconnect/reset in the greater-than-5
  through less-than-25-second interval, a timeout-band reset from 25 through 40
  seconds, no reset by 40 seconds, incomplete/partial retained evidence, or
  failed changed-ID recovery is likewise inconclusive and consumes the session.
  Preserve evidence, recover only, and never retry. Only the exact ordered
  markers plus reset within 5 seconds and changed-ID Gemian classify a
  one-attempt pass. The device custodian is assigned only at admission.
- **Upstream:** Linux watchdog subsystem. Runtime success would support only
  the exact Gemini result and the minimal-delta comparison; it does not certify
  generic MT6797 policy. Actual author identity, DCO, current-tree overlap and
  maintainer policy review remain submission gates. Remove the local diagnostic
  after an equivalent change is accepted upstream or the hypothesis is retired.
- **Owner-away work:** all implementation, private construction, host/refusal
  validation, review and readiness classification may finish without a
  physical selection. Stop with a conditional/ready handoff; never install or
  select the candidate merely because preparation passes.
- **Device readiness:** `candidate-validated`; guarded deployment, receipt
  review and physical admission remain pending.
  Any change to patch, profile, package, DT,
  initramfs, credentials, candidate, installer, collector, classifier, time
  bound, action budget or recovery tool invalidates readiness. The experiment
  queue remains unselected until the primary task accepts a complete packet.
- **Handoff:** exact changed paths and revision, every source and generated
  artifact identity, test counts, rejected mutations, timestamps, private
  artifact locations described without secrets or personal absolute paths,
  known limitations, and an explicit statement that no device action occurred.
- **State:** candidate, deployment and one-process session preparation tooling
  accepted after independent Sol Medium integration review and Astra Medium
  action-boundary review. Exact clean published revision `8b0e8ff7...` produced
  two byte-identical private candidates and passed the independent validator;
  the derived guarded installer also passed local validation. No deployment or
  session admission exists, and no device or network action occurred.
- **Efficiency loop:** if this offline handoff is accepted, the primary task
  appends exactly one considered/accepted item to the active workflow ledger
  with observed timestamps, actual routes, first-review result, rework and
  measured credits or `unavailable`.
