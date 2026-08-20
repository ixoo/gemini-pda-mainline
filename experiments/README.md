# Experiments and reverse engineering

This directory contains reproducible investigations of the Gemini PDA and its
software-visible hardware. The write-up, probe code, and sanitized evidence for
an investigation stay together so another contributor can repeat or challenge
the result.

Retrospective evidence note: the owner reported on 2026-07-31 that some
white/grey-screen cycles followed by an apparent reboot may have been reboot or
boot-selection issues rather than kernel failures. Individual records retain
their exact chronology and predeclared decision maps, but a visual state plus
return to Gemian alone is now treated as inconclusive unless exact kernel
identity, a durable stage record, or attributable crash/reset evidence closes
the loop. Positive identity-gated observations are unaffected.

## Index

### Current repository audit

- [2026-07-28 manifest profile-series invariant audit](2026-07-28-profile-series-invariant-audit/README.md)
  — records the current canonical-subsequence findings and enforcement
  boundary.

### Current DA921x, I2C6, and A72 line

- [2026-08-20 mainline CPU8 Gate-7 admission audit](2026-08-20-mainline-cpu8-gate7-admission-audit/README.md)
  — reconciles the completed mainline same-value write with the retained Buck-B
  rollback, CPU8 startup/execution, A41, P24/P28/P30, and safe-off evidence.
  The pinned 12-row audit rejects immediate current-mainline CPU8 admission:
  the existing provider-owner acquire/release seam still returns structured
  refusal. It selects a hardware-free, default-off positive Buck-B
  acquire/release state machine as the first missing implementation while
  retaining the A26/A14 vetoes and prohibiting a build candidate or device
  action.
- [2026-08-20 mainline DA921x same-value DT contract repair](2026-08-20-mainline-da921x-same-value-dt-contract-repair/README.md)
  — repairs the missing named handoff windows without changing the kernel,
  ramdisk, or LK contract. Exact deployment and one selected boot passed the
  corrected 20-entry pretrigger, issued one `0xda: 0x46 -> 0x46` write, and
  retained the complete 32-entry ledger with immediate/delayed `0x46`
  readback, unchanged full-byte poststate, zero retry/second write, and CPUs
  8--9 closed. A source-backed host-classifier correction accounts for the
  write as the sole non-combined transfer; the immutable capture passes. This
  closes the Gate-6 bounded no-op write and is closed to repetition.
- [2026-08-19 mainline DA921x same-value-write implementation](2026-08-19-mainline-da921x-same-value-write-implementation/README.md)
  — implements the admitted Gate-6 contract as three deterministic logical
  source phases: controller ledger v2/prefix verification, the one-shot
  12-transfer regulator action, and hardware-free KUnit. The exact temporary
  Buildbox delta passes semantic validation and strict style with zero errors,
  warnings, or checks. Normal patch generation, canonical admission, compile,
  and KUnit execution remain pending; no candidate or device action exists.
- [2026-08-19 mainline DA921x same-value-write preflight review](2026-08-19-mainline-da921x-same-value-write-preflight-review/README.md)
  — reconciles the exact B1--B4 closure receipts into the only eligible Gate-6
  implementation: five full-byte preflight reads, one `0xda: 0x46 -> 0x46`
  write, immediate/delayed target readback, and four full-byte poststate reads
  under one root-adapter lock with zero retries. The 12 actions exactly fill
  the 32-entry ledger, so the implementation must verify the retained
  20-entry prefix under lock and extend attribution to both write bytes. The
  review is hardware-free and permits only default-off implementation and
  Buildbox validation; no candidate or physical write exists and CPU8/CPU9
  remain closed.
- [2026-08-19 mainline I2C6 write-transport KUnit proof](2026-08-19-mainline-i2c6-write-transport-kunit/README.md)
  — closes Gate-6 blocker B2 without device access. Two canonical patches
  factor the production MT6797 FIFO plan, completion accounting, no-retry
  root-lock wrapper, and lease-result precedence into a focused default-off
  KUnit profile. Buildbox compiled the exact clean source and the original
  isolated arm64 QEMU log passes all 12 ordered cases with no failure or skip.
  This proves only the controller/software contract; the physical same-value
  write and CPU8/CPU9 remain closed pending a fresh explicit pre-write review.
- [2026-08-18 mainline I2C6 firmware-writer transaction window](2026-08-18-mainline-i2c6-firmware-writer-transaction-window/README.md)
  — closes Gate-6 blocker B1 on the named unit and exact revision. One
  attributable mainline boot held the stopped-DVFSP/reset-control exclusion at
  every transfer entry and exit, retained the exact read-only ledger with no
  write-shaped or foreign traffic, preserved CPU0--7 and serviceability, and
  returned natively to changed-identity Gemian. The exact artifact is closed
  to repetition and does not itself authorize a DA921x write.
- [2026-08-18 mainline DA921x runtime-triggered read-only preflight](2026-08-18-mainline-da921x-runtime-preflight-ledger/README.md)
  — closes Gate-6 blockers B3 and B4. Its exact one-shot read-only runtime
  attributed every startup and preflight transfer, observed stable disabled
  Buck B with clear `V_LOCK` and both selectors at `0x46`, retained zero
  register-data writes, restored sysfs read-only, and returned natively to
  changed-identity Gemian with CPUs 8--9 offline.
- [2026-08-17 mainline DA921x read-only preflight ledger](2026-08-17-mainline-da921x-readonly-preflight-ledger/README.md)
  — implemented the automatic child intended to attribute all 20 Gate-5 I2C6
  transfers and add two fixed five-register preflight passes. A 32-entry
  controller ledger records only message shape, pointer, and final result; the
  provider records registration/observer/preflight read counts plus full-byte
  `CONTROL_A`, `STATUS_B`, `BUCKB_CONT`, `VBUCKB_A`, and `VBUCKB_B` state. It
  added no hardware write, consumer, firmware-owner claim, or CPU request.
  Buildbox, candidate validation, guarded deployment, and full readback passed,
  but its one pre-armed attempt saw preloader and then changed-identity Gemian
  without mainline USB. No ledger survived, boot2 remained exact, and the
  automatic artifact is stopped without closing B3 or B4.
- [2026-08-17 mainline DA921x bounded no-op write review](2026-08-17-mainline-da921x-bounded-noop-write-review/README.md)
  — reconciles the Gate-5 runtime, the official legacy register map, prior
  firmware-owner audit, and rollback evidence into one exact least-invasive
  Gate-6 candidate: a same-value `0x46 -> 0x46` write to disabled Buck B's
  unselected `VBUCKB_B` register. The review performs no build or hardware
  action. Its four original evidence blockers are now closed by later named
  experiments, but the historical design-only decision remains unchanged
  until a fresh explicit pre-write review reconciles those receipts. CPU8/CPU9
  remain closed; Roadmap gate 6 owns the ordered follow-up.
- [2026-08-17 LK-repaired DA921x read-only provider baseline](2026-08-17-mainline-da921x-readonly-provider-baseline/README.md)
  — freezes the ten runtime-proven CPU clock properties into the kernel-built
  Gemini DT and enables only the read-only LK-devinfo NVMEM supplier and
  existing DA921x observer. Buildbox, container, guarded boot2 deployment, and
  one exact runtime attempt pass. The handoff and I2C6 reached ready; the
  DA921x provider bound with 14 identity reads, two providers, four completed
  provider reads, internally consistent buck states, and zero register-data
  writes. CPUs 0--7, USB/netcat, I2C5/AW9523, polling keyboard, tty1,
  watchdog, and native reboot remained serviceable while CPUs 8--9 stayed
  closed. Changed-ID Gemian recovery found empty pstore and the exact candidate
  still unmounted on boot2. This closes Roadmap gate 5 for the named unit and
  opens only the bounded-write design review; it is not writable-provider,
  rollback, resume, or A72 support.
- [2026-08-17 LK CPU clock-frequency iterator repair](2026-08-17-mainline-lk-cpu-clock-iterator-repair/README.md)
  — audits the pinned Planet LK path before Linux entry and identifies a
  concrete non-progress loop: the current DT's first CPU lacks
  `clock-frequency`, while LK advances its CPU iterator only after reading
  that property. The selected DT-only candidate adds the ten exact Stage-27
  values and changes nothing else from the stopped I2C5 predecessor. Two DT
  derivations and two container assemblies agree; all 32 inherited LK gates,
  six container mutations, five serviceability mutations, five CPU-clock
  mutations, exact provenance, CPU8/9 closure, and the guarded installer's
  offline gates pass. Guarded live-GPT boot2 installation, exact full readback,
  and clean shutdown passed without a fresh backup or automatic reboot. Its
  one observed attempt produced the exact mainline USB identity, kernel and
  netcat serviceability, all ten final-DT clock values, CPUs 0–7 online with
  8–9 closed, the expected I2C5/AW9523/keyboard/watchdog path, and a successful
  native return to Gemian. This confirms the LK iterator diagnosis and promotes
  the repaired DT as the next serviceability baseline.
- [2026-08-17 MT6797 I2C5 serviceability restoration](2026-08-17-mainline-i2c5-serviceability-restoration/README.md)
  — recomputes the remaining Stage-27/current DT partition after the stopped
  USB, SCP, and watchdog derivatives. The selected candidate restores the full
  runtime-proven I2C5/AW9523/polling-keyboard group, including shared AP_DMA
  clock ownership and the polling control's absence of an AW9523 parent IRQ,
  while keeping the exact kernel, initramfs, peripheral USB, disabled SCP,
  no-watchdog-IRQ path, xHCI closure, and CPU8/9 closure fixed. Two DT
  derivations and two container assemblies agree; all 32 LK gates, exact
  provenance, SCP/watchdog contracts, the serviceability contract, five
  independent mutations, and the guarded installer's offline gates pass.
  Guarded live-GPT boot2 installation, full readback, and clean shutdown also
  passed without a fresh backup or automatic reboot. Its one freshly observed
  attempt showed preloader only before a changed Gemian return; no mainline USB
  identity appeared, pstore stayed empty, reset tokens were watchdog-block
  class, and boot2 remained exact. The coherent serviceability group is
  insufficient by itself and this candidate is stopped. Incremental DT
  property changes now give way to a post-LK/earlier-observation reassessment.
- [2026-08-16 MT6797 watchdog IRQ isolation](2026-08-16-mainline-wdt-irq-isolation/README.md)
  — re-ranks the remaining Stage-27/current DT groups by their earliest built
  kernel consumer. The selected candidate deletes only the optional watchdog
  `interrupts` property so probe follows the runtime-proven no-IRQ takeover
  path; the exact kernel, initramfs, USB observation properties, disabled SCP
  node, watchdog reset-provider property, xHCI closure, and CPU8/9 closure stay
  fixed. Deterministic DT/container reproduction, inherited LK and entry-ledger
  gates, the exact manifest, SCP contract checks, and independent watchdog
  mutations pass. Guarded live-GPT boot2 installation, full readback, and clean
  shutdown passed without a fresh backup or automatic reboot. Its one attempt
  showed preloader only before a changed Gemian return; no mainline USB
  identity appeared, pstore stayed empty, and boot2 remained exact. The
  watchdog IRQ deletion is insufficient by itself and this candidate is
  stopped.
- [2026-08-16 MT6797 LK SCP handoff node](2026-08-16-mainline-scp-handoff-node/README.md)
  — partitions the remaining stopped-current versus runtime-proven Stage-27 DT
  delta and isolates a strict public MT6797 LK contract: absent
  `mediatek,scp` makes `platform_fdt_scp()` fail through
  `platform_atag_append()` before Linux handoff. The selected derivative adds
  only the exact input-disabled SCP node, keeping Linux SCP probe, xHCI,
  CPU8/9, and hardware writes closed. Its exact candidate passes two
  assemblies, two padding methods, 32 LK gates, the complete manifest, and six
  negative mutations. Guarded boot2 write, full readback, and clean shutdown
  passed. Its one attempt showed preloader only before a changed Gemian return;
  no mainline USB identity appeared, pstore stayed empty, and boot2 remained
  exact. The SCP node is insufficient by itself and this candidate is stopped.
- [2026-08-16 current-DT USB observation restoration](2026-08-16-mainline-current-dtb-usb-observation/README.md)
  — corrects the prior DT lineage comparison: the serviceable Stage-27 line
  reused a frozen USB-enabled observation DT, while the stopped current-DT
  GAEL attempt used a package DT with those nodes disabled. The selected
  candidate changes exactly three existing USB `status` properties and leaves
  xHCI disabled, peripheral-only policy intact, and CPU8/9 closed. Its two
  assemblies, independent padding, 32 LK gates, exact manifest, and six
  negative mutations pass. Its exact guarded boot2 write, independent full
  readback, and clean shutdown passed. Its pre-armed attempt observed only the
  MT65xx preloader before a changed Gemian return—no Linux USB, exact interface,
  or netcat—and boot2 remained exact with empty pstore. The candidate is stopped;
  remaining Stage-27/current DT deltas require offline partitioning.
- [2026-08-16 LK handoff DTB control](2026-08-16-mainline-lk-handoff-dtb-control/README.md)
  — the offline lower-boundary audit found that stopped GAEL and the last
  serviceable Stage-27 container both satisfy their Android-v0, gzip, load,
  Image-header, and entry-branch contracts. Planet LK source actively rewrites
  the appended DTB before disabling cache/MMU and branching. The selected
  decision-changing candidate keeps the exact GAEL kernel and crosses it with
  the exact runtime-proven Stage-27 DTB. Two assemblies, independent padding,
  all 32 LK gates, six negative mutations, guarded deployment, and full
  readback passed. Its one runtime reached `/init`, exact USB/netcat, CPU0--7,
  and native reboot with CPU8/9 closed. This proves current Image entry and
  strongly implicates current-DTB processing. Empty returned slots also reject
  the ledger's negative post-return stage oracle.
- [2026-08-16 arm64 entry-ledger implementation](2026-08-16-mainline-arm64-entry-ledger/README.md)
  — implements the authorized `GAEL-20260816-A` four-stage lower-boundary
  discriminator as canonical patch 0281 and one isolated Buildbox profile.
  Two call-free checkpoints run with MMU/data-cache-off refusal before the
  primary switch; two independent early-mapped checkpoints retain later proof.
  Its exact one boot2 attempt completed with a changed return to Gemian but no
  valid retained stage. The later serviceable DTB control retained the same
  empty returned headers, so this establishes no surviving record, not absent
  Image entry. The artifact and negative causal interpretation are stopped.
- [2026-08-16 arm64 entry-ledger safety audit](2026-08-16-mainline-arm64-entry-ledger-audit/README.md)
  — audits the lower observation boundary selected after the pre-ramoops
  candidate retained no stage. It defines four independent checkpoints from
  `primary_entry` through the reserved-memory scan, exact register and
  MMU/cache guards for the two physical-mode stages, the four-header runtime
  fingerprint, and an offline oracle. The audit remains read-only design work;
  its exact successor implementation and one boot2 attempt are now authorized.
- [2026-08-16 pre-ramoops four-stage retained ledger](2026-08-16-mainline-pre-ramoops-ledger/README.md)
  — completed its one approved attempt after the exact post-ramoops candidate
  returned with empty pstore. Buildbox validation, guarded boot2 deployment,
  shutdown, and changed-cycle capture passed, but pstore and the bounded raw-
  zone follow-up retained no stage. The candidate is stopped; arm64 Image
  entry remains unestablished and no hardware-support claim exists.
- [2026-08-05 P30 generation arbitration model](2026-08-05-a72-p30-generation-protocol/README.md)
  — adds canonical patch 0158 and a dormant, raw-lock-serialized C model for
  exact CPU8/CPU9 startup arbitration, sticky quarantine, indivisible success
  publication, completion/online draining, per-operation one-shot retirement,
  and K/C/P/E/U terminal ownership. Two independent static reviews returned GO;
  an independent 144-state oracle has zero violations and rejects all 17 unsafe
  mutations, including any global generation-order assumption. This is only
  `PARTIAL_P30_PROTOCOL_MODEL`: there are zero production callers, KUnit was
  not run, P24/P14/P15 and bounded park/wait/panic hooks are absent, P30E has no
  MMU-off object or coherency proof, and A26/A14 remain closed.
- [2026-08-06 P30E MMU-off-visible object contract](2026-08-06-a72-p30e-mmuoff-contract/README.md)
  — defines the fixed physical 20-word controller/target object, separate
  field writers, cache/barrier order, exact-token publication, and fail-closed
  P30U handling. It is a source-only contract; no assembly implementation,
  CPU_ON/OFF action, build, or device result exists yet.
- [2026-08-05 A41 kernel-identity binding boundary](2026-08-05-a72-a41-kernel-identity/README.md)
  — advances the blocked lifecycle to ABI 7 with a strict static expected
  record and independent arm64-core producers for the running embedded
  IKCONFIG, exact GNU build ID, and forced command line. Complete matching
  inputs can publish only `SEALED_IDENTITY`; no package record was emitted,
  and target/system evidence, capability commit, READY, boot, and disable
  gates remain closed. This is `PARTIAL_KERNEL_IDENTITY_BINDING`, not a build,
  runtime, device, or hardware-support result. The roadmap alone owns the
  remaining ordered gates.
- [2026-08-05 A41 core-owned runtime-evidence boundary](2026-08-05-a72-a41-runtime-evidence-owner/README.md)
  — advances the blocked lifecycle to ABI 6 with a private arm64-core evidence
  record, an exact post-hyp/pre-finalization seal, release/acquire publication,
  and rejection of profile-declared RUNTIME origin or profile observations.
  The core has no producer, so it seals `SEALED_EMPTY`; the fixture remains
  evaluator-only and every plan, commit, READY, boot, and disable gate stays
  closed. This is `PARTIAL_RUNTIME_EVIDENCE_OWNER_BOUNDARY`; its ABI-7
  identity-binding successor is recorded above.
- [2026-08-05 A41 pure six-row fixture evaluator](2026-08-05-a72-a41-six-row-fixture/README.md)
  — advances the blocked planner to ABI 5 and evaluates the six formerly
  unresolved GIC/ICH, cache, Spectre-v2, Spectre-v4, and BHB rows for CPU8 and
  CPU9 from an exact immutable fixture. Both targets reach 40 classified / 8
  present / 32 absent and a complete typed-effect draft, but FIXTURE provenance,
  runtime binding, the unavailable commit path, deliberate `-EAGAIN`, and the
  existing CPU admission vetoes prevent publication. This is
  `PARTIAL_SIX_ROW_FIXTURE_EVALUATOR`; its runtime-owner successor is recorded
  above. It is not a build or device action.
- [2026-08-05 A41 attributable per-target capability planning](2026-08-05-a72-a41-per-target-plan/README.md)
  — advances the blocked planner to ABI 4, binds target slots uniquely to CPU8
  and CPU9 before classification, and preserves independent classified/present
  bitmaps so one target cannot hide disagreement from the other. Complete
  matching fields declared RUNTIME are now an architecture-owned publication
  prerequisite; data declared FIXTURE cannot satisfy it. ABI 4 does not yet
  attest the profile-supplied origin, so a trusted runtime producer remains a
  later gate.
  Both targets remain at 34 classified / 4 present / 6 unresolved and the
  partial validator returns `-EAGAIN`. This is
  `PARTIAL_PER_TARGET_PLAN_BOUNDARY`: no build, boot candidate, device action,
  or hardware-support claim is authorized.
- [2026-08-05 A41 expected-A72 static capability census](2026-08-05-a72-a41-static-census/README.md)
  — implements the source-owned provisional evaluator for all 40 compiled
  local descriptors. It classifies exactly 4 expected-A72 rows PRESENT and 30
  ABSENT while leaving GICv5 legacy, ICH_HCR_EL2.TDIR, cache-type mismatch,
  Spectre-v2, Spectre-v4, and BHB unresolved. KPTI and private MIDR-list
  predicates are evaluated without running target callbacks, hypervisor target
  substitution fails closed, and the partial validator requires the exact
  identities, blockers, bitmaps, and two provisional effects before returning
  `-EAGAIN`. This is `PARTIAL_STATIC_CAPABILITY_CENSUS`: no plan identity,
  build, boot candidate, device action, or hardware-support claim is
  authorized.
- [2026-08-05 A41 immutable evidence/plan/receipt boundary](2026-08-05-a72-a41-immutable-plan/README.md)
  — replaces the mixed three-capability draft with ABI 3 separation between
  fallible evidence, a state-free immutable plan, an architecture-owned
  receipt, and the copied READY token. The exact selected-profile census is
  40 compiled local descriptors: 4 source/profile-static PRESENT, 30 ABSENT,
  and 6 evidence-dependent. Full per-target register, cache, GIC/hyp,
  WA1/WA2/WA3, ASID, granule, VA, HWCAP, and typed-effect boundaries are
  described, but the classifier resolves nothing, validation and preparation
  return `-EAGAIN`, and the architecture mutation implementation is
  unavailable. This is `PARTIAL_IMMUTABLE_PLAN_BOUNDARY`: no build, boot
  candidate, device action, or hardware-support claim is authorized.
- [2026-08-05 A41 canonical read-only capability planner](2026-08-05-a72-a41-canonical-planner/README.md)
  — extends the blocked A41 lifecycle with iteration-bounded traversal of
  surviving canonical arm64 descriptors and a read-only plan for BHB loop
  `k=8`, erratum
  1742098, speculative-AT, and their required future effects. Every other
  local predicate and all configuration, source-identity, firmware,
  register/cache/ASID/translation, GIC, HWCAP, and attestation-user proofs
  remain blocked. This is `PARTIAL_READ_ONLY_PLANNER`: A41 is incomplete, the
  A26 boot and A14 disable vetoes plus `maxcpus=8` remain, and no build, boot
  candidate, device action, or hardware-support claim is authorized.
- [2026-08-05 A41 partial fail-closed capability profile](2026-08-05-a72-a41-capability-profile/README.md)
  — adds canonical patches 0148/0149 and one default-off isolated profile for
  the first arm64 pre-finalization attestation scaffold. Independent activation,
  bounded target registration, immutable stage checks, exact non-circular
  source/configuration inputs, expected-versus-observed target fields, and
  READY publication guards are machine-checked. The selected MT6797 profile
  records only the three known capability-plan bits and BHB `k=8`, remains
  unconditionally BLOCKED before any live capability or CPU-path mutation, and
  retains patch 0092 plus `maxcpus=8` as the separate CPU admission/removal
  boundary. This is `PARTIAL_FAIL_CLOSED`, not complete A41, a build, a boot
  candidate, or a hardware-support result.
- [2026-08-05 A72 CPU-up source closure](2026-08-05-a72-cpu-up-source-closure/README.md)
  — pins the exact Linux 7.1.3 source and selected configuration, proves that
  an A53-only boot cannot admit a late A72 without pre-finalizing the complete
  A72 capability set, and freezes A41 plus the P30K/C/P/E/U and P32A/D/F/X/R
  failure closures. The selected post-CPU_ON callback set is fallible;
  `.cpu_disable` is the first target rollback guard before topology, online,
  IPI, and IRQ teardown, while die/kill remain defense for early and deeper
  paths. Timeout requires cancellation-versus-publication arbitration and a
  target park acknowledgment. Dynamic numeric CPUHP slots remain a same-boot
  A25 proof gap. This is source-only: the A26 veto remains and no patch, build,
  CPU_ON/OFF, or device action is authorized.
- [2026-08-05 A72 membership and admission contract](2026-08-05-a72-membership-admission-contract/README.md)
  — freezes the exact token and boot-local one-shot attempts, the only legal
  Linux membership/provider transitions, symmetric public/internal admission
  with direct frozen/suspend bypasses denied, the target-only query budget,
  and fresh private-branch proof through that query. After P15 secondary and
  later generic callback completion, M02 requires an initial schedule and one
  reschedule after each of the first two exact same-generation CPU8/CPU9
  samples at about 1, 6, and 10 seconds. Any later M02 proof failure enters
  retained-state P19 `FAULT`; no membership commit precedes sample 3. The
  later source closure corrects and supersedes its detailed P30/P32 mechanism:
  A39 interception ends in branch-specific P30, and A37 rollback first needs
  a `.cpu_disable` guard before the retained die/kill defense. Both remain
  terminal `FAULT`, not retained success. `DEAD`
  and generic warn-only sync/kill paths do not prove physical off. The A26
  boot and A14 disable vetoes are all-applicable while startup/PM,
  scheduler/observer,
  private-ledger, provider, secure-concurrency, completion-propagation, and
  reset owners are unresolved; no implementation, build, CPU_OFF, or device
  action is authorized.
- [2026-08-05 A72 secure CPU-off attribution](2026-08-05-a72-secure-cpu-off-attribution/README.md)
  — audits the exact verified private payload without publishing binary bytes.
  Target `CPU_OFF` follows the generic TF-A v1.1 path into WFI, and the
  controlling CPU's `AFFINITY_INFO` call actively invokes A72 teardown. CPU9
  with CPU8 retained has an exact decision-relevant diagnostic-monitor,
  per-core, and private secure-ledger write subset and avoids every
  cluster-power branch. Last CPU8 additionally withdraws CCI and runs
  cluster/SPM, B-mux/PLL, and `0x10006290` bit-1 teardown. Querying retained
  CPU8 through `AFFINITY_INFO` would itself enter teardown rather than observe
  ON state. Unbounded secure waits and unresolved SRAM/DCM, provider,
  independent-readback, admission, notifier, and runtime ownership keep
  CPU_OFF prohibited.
- [2026-08-05 A72 safe-off ownership contract](2026-08-05-a72-safe-off-ownership-contract/README.md)
  — reconciles the Gate 4 evidence into separate fail-closed contracts for
  CPU9-off with CPU8 retained and for the final A72-off transition. Explicit
  owners, pre-states, readbacks, timeouts, inverses, and failure responses are
  frozen. The later secure audit closes the branch attribution but corrects the
  passive-`AFFINITY_INFO` assumption. Membership/provider ledger,
  policy/suspend admission, notifier exclusion, bounded observers, SRAM/DCM,
  runtime, and final provider release remain unresolved, so no CPU_OFF
  candidate, build, or device boot is authorized.
- [2026-08-03 A72 CPU8/CPU9 scheduler-context execution](2026-08-03-a72-scheduler-context/README.md)
  — diagnosed parked-task activation in the rejected phase parent, changed only
  the two activations to explicit unpark, and passed two exact fixed-map runtime
  cycles. In each fresh changed-cycle pstore record, both normal-priority bound
  tasks ran on CPUs 8/9, rendezvoused, completed the finite workload, and exited
  through the same ordered cleanup with identical task hashes.
  Watchdog recovery returned with CPUs 8/9 offline and boot2 unchanged both
  times. Bounded scheduler-context execution is repeatable. CPU_OFF and
  production enablement remain prohibited; complete power-owner rollback
  remains open.
- [2026-08-03 A72 CPU8/CPU9 parallel disjoint load](2026-08-03-a72-cpu9-parallel-disjoint-load/README.md)
  — passed twice after one observation-loss cycle. In each accepted run CPUs 8
  and 9 concurrently wrote disjoint halves of a 64 KiB set for 128 rounds and
  completed 1,048,576 exact peer checks with identical deterministic hashes,
  zero errors/mismatches, watchdog recovery, offline recovery CPUs 8/9, and
  unchanged boot2. The bounded IPI-context gate is repeatable; no third
  unchanged run is permitted.
- [2026-08-03 A72 CPU8/CPU9 multi-cacheline integrity](2026-08-03-a72-cpu9-multiline-integrity/README.md)
  — passed twice with exact 64-round alternating exchange over 256 aligned
  cachelines, 262,144 peer checks per cycle, identical cross-matching hashes,
  watchdog recovery, offline recovery CPUs 8/9, and unchanged boot2. The
  pair-v5 gate is closed and must not run unchanged again.
- [2026-08-03 A72 CPU8/CPU9 bounded coherency](2026-08-03-a72-cpu9-bounded-coherency/README.md)
  — predeclares a CPU0-pinned, 1,024-round concurrent CPU8↔CPU9 shared-memory
  handshake with finite spin budgets and a durable pair-v4 terminal. Startup,
  HPS vetoes, CPU_OFF prohibition, pair timing, power state, and watchdog
  recovery remain exact; kernel source is not yet changed.
- [2026-08-03 A72 CPU9 terminal attribution](2026-08-03-a72-cpu9-terminal-attribution/README.md)
  — carries the first HPS CPU-down veto and accumulated matching count into the
  already-proven sample-3 pair terminal. Exact-parent Buildbox compilation and
  two byte-identical offline Android-v0 constructions pass. The guarded
  no-backup, two-readback, clean-shutdown deployment and predeclared runtime
  contracts pass offline review. The exact candidate is installed on inactive
  boot2 with two matching full readbacks. Two exact runtime cycles pass: CPUs
  8/9 completed three callbacks in each, and the durable terminals attribute
  91 then 89 CPU9 HPS down requests to the expected public `-EPERM` veto.
  Bounded retained execution is repeatable; a changed coherency/load design is
  next, while CPU_OFF and later power boundaries remain prohibited.
- [2026-08-03 A72 CPU9 retention window](2026-08-03-a72-cpu9-retention-window/README.md)
  — preserves the proven PSCI-only CPU9 startup and every public CPU-down
  veto, moves all three synchronous CPU8/CPU9 pair samples inside the fixed
  watchdog window, and bounds repeated HPS down-pressure reporting to one
  directly attributable record. Exact-parent Buildbox source generation,
  compilation, diagnostics, binary anchors, and stack review pass. Two
  deterministic Android-v0 constructions and the guarded runtime/deployment
  contract pass offline review. The live-GPT-resolved inactive boot2 write,
  independent full readback, no-backup policy, and clean shutdown passed.
  Runtime then retained the exact sample-3 pass: CPUs 8 and 9 were online and
  each completed all three synchronous callbacks with no retained fault. The
  console tail lost the earlier required one-shot HPS `-EPERM`, so the result
  is inconclusive and must not be repeated unchanged; the next child must fold
  that accumulated HPS result into the durable terminal.
- [2026-08-03 A72 CPU9 cluster reuse](2026-08-03-a72-cpu9-cluster-reuse/README.md)
  — brought CPU8 and CPU9 into Linux online accounting and completed two
  synchronous callbacks on each. Its declared run is rejected because HPS
  requested CPU9 down 83 times and the third terminal was scheduled beyond
  the inherited watchdog window; the exact artifact must not be repeated.
- [2026-08-03 A72 late CPU8 hold](2026-08-03-a72-cpu8-late-hold/README.md)
  — passed twice with a third substantive synchronous CPU8 callback at about
  twelve seconds, establishing the repeatable exact parent for CPU9 while
  CPU_OFF, load, DVFS, thermal, and suspend remain blocked.
- [2026-08-02 A72 CPU8 held online](2026-08-02-a72-cpu8-held-online/README.md)
  — adds HPS and generic pre-notifier down barriers plus synchronous CPU8
  samples at about one and six seconds. Its first runtime returned through the
  fixed watchdog with no retained fault, but the 64 KiB console tail began
  after both required samples. The result is inconclusive, and the unchanged
  artifact must not be repeated.
- [2026-08-02 A72 recovery-only watchdog/pstore discriminator](2026-08-02-a72-recovery-only-discriminator/README.md)
  — defines the immediate no-A72 prerequisite for the one-way CPU8 path. Its
  deterministic source generator rejects CPU8/9 before platform action,
  transfers watchdog ownership under the normal kicker lock, arms one fixed
  reset-only deadline, and emits an exact console-ramoops marker. Patch
  generation and ten mutation tripwires pass after closing a hotplug no-lock
  reload race. The full Buildbox comparison, binary ordering review,
  kernel-only container reconstruction, and guarded installer pass. Runtime
  attempt 1 automatically returned on the designed time scale with a changed
  boot ID and watchdog-class reason while boot2 stayed exact and CPU8/9 stayed
  offline, but pstore was empty. Attempt 2 recovered the exact one-time armed
  marker from console-ramoops, correlated it with another automatic
  changed-boot-ID watchdog return, and proved every CPU8/9 request rejected
  before A72 action. The recovery prerequisite now passes; unchanged retry is
  prohibited and one-way CPU8 source generation is unblocked.
- [2026-08-02 A72 one-way CPU8 startup boundary](2026-08-02-a72-one-way-cpu8-boundary/README.md)
  — reconciles the accepted rollback with the public Linux and natural Gemian
  isolation paths, rejects an unobserved Linux isolation inverse, and
  machine-checks the next state-machine boundary: exact rollback before
  isolation, fault-retain/reset recovery afterward, one reconciled CPU8
  request, and no CPU9 or CPU-off path. The independent no-A72 watchdog/pstore
  gate has now passed, so source generation and offline review are unblocked.
- [2026-08-02 A72 pre-isolation rollback discriminator](2026-08-02-a72-pre-isolation-rollback-discriminator/README.md)
  — completed the exact one-shot stop after CPU8 BUCKB enable but before
  external-isolation clear. The revised pre-latch gate produced the expected
  immutable rollback, restored the complete entry state without crossing a
  forbidden boundary, and returned the device to known-good Gemian. This
  closes only the pre-isolation BUCKB/reset rollback row.
- [2026-08-02 Gemian A72 first-complete-cycle latch](2026-08-02-gemian-a72-first-cycle-latch/README.md)
  — completed an exact Buildbox-built, guarded-boot2, no-load run. ABI v2 froze
  the first natural CPU8 up/down pair in 46 immutable records with no overflow
  or CPU9 activity; two delayed reads were identical and every lifecycle and
  owner-transition check passed. This closes the clean successful vendor-cycle
  observation, not mainline provider, rollback, resume, or CPU9 support.
- [2026-08-02 MT6797 A72 ownership and rollback audit](2026-08-02-a72-ownership-rollback-audit/README.md)
  — machine-checks 19 forward, observation, rollback, CPU9, and resume
  boundaries. Sixteen now have clean first-pair evidence and all nine forward
  decisions remain closed, but Gate 4 is open on five failure rollbacks, one
  CPU9-only observation, and suspend/resume ownership. The first independent
  failure/rollback discriminator is now specified above.
- [2026-08-02 bounded Gemian A72 observer boot image](2026-08-02-gemian-a72-bounded-observer-boot/README.md)
  — replaces only the exact active Gemian Android-v0 kernel field with the
  compiler/timing-reviewed five-patch observer. Two raw assemblies and two
  independent 16 MiB padding methods are byte-identical; the active ramdisk,
  command line, addresses, and appended-DTB contract are pinned. Guarded
  `boot2` deployment and full readback passed, and both the no-load and exact
  single-two-worker collectors pass their fail-closed static gates. Exact
  running-kernel identity later confirmed `boot2` selection. The overwritten
  ring retained five complete CPU8-up and six complete CPU8-down transactions
  with internally valid owner evidence and no CPU9 record, but clean initial
  attribution failed; no pulse ran, and the next revision must latch its first
  complete natural cycle before late userspace retrieval.
- [2026-08-01 DA921x post-event identification lifecycle](2026-08-01-da921x-post-event-lifecycle/README.md)
  — natural bind, zero-transaction unbind, and one read-only rebind reached
  exact `14 -> 14 -> 28` counts with every DMA/write/other counter zero,
  restored both ownership links after bounded page-2 visibility delay, and
  preserved the complete serviceability baseline.
- [2026-08-01 DA921x single uevent multicast](2026-08-01-da921x-uevent-single-multicast/README.md)
  — input-validates the stage-22 discriminator: one exact multicast call to
  the runtime-proven single listener plus independent exact-datagram receipt
  and bounded no-duplicate validation. Its first buildbox package was rejected
  before fetch because it exposed a stale frozen patchset identity; the
  metadata-only identity correction is recorded and a replacement build is
  required.
- [2026-08-01 DA921x bounded uevent listener](2026-08-01-da921x-uevent-bounded-listener/README.md)
  — input-validates the stage-21 discriminator: one independent userspace
  group-1 listener, one exact-token replay, and consumption before multicast.
  Its exact Buildbox package and two byte-identical LK assemblies passed
  offline validation; guarded boot2 deployment passed full readback and ended
  in shutdown. Runtime stage 21 then passed with one socket, exactly one
  listener, zero broadcasts, bounded no-receipt, restored read-only sysfs, and
  the unchanged zero-I2C serviceability baseline.
- [2026-07-31 DA921x uevent no-listener delivery](2026-07-31-da921x-uevent-no-listener-delivery/README.md)
  — reached runtime stage 20 with one socket, zero listeners, zero allocations,
  zero broadcasts, and return value zero while preserving the unbound-client,
  zero-I2C, and serviceability baseline.
- [2026-07-31 DA921x uevent listener discovery](2026-07-31-da921x-uevent-listener-discovery/README.md)
  — reached runtime stage 19 after traversing the normal uevent socket list;
  it observed one socket and zero group-1 listeners, returned before multicast,
  and preserved the unbound-client, zero-I2C, and serviceability baseline.
- [2026-07-31 DA921x netlink skb serialization](2026-07-31-da921x-netlink-skb-serialization/README.md)
  — reached runtime stage 18 after allocating and byte-validating the exact
  293-byte target skb, then consumed it before socket traversal or multicast;
  the unbound-client, zero-I2C, and serviceability baseline passed.
- [2026-07-31 DA921x corrected OF event layout](2026-07-31-da921x-of-event-layout-correction/README.md)
  — validates the runtime-proven eight fixed entries plus final `SEQNUM`,
  suppresses transport, and proves successful assembly and cleanup serviceable
  with an unbound client and zero I2C activity.
- [2026-07-31 DA921x bounded event-entry classification](2026-07-31-da921x-dual-modalias-entry-classification/README.md)
  — classifies expected-entry presence, duplicates, ordering, `SEQNUM`, and
  unexpected entries without exposing arbitrary event text or altering the
  event.
- [2026-07-31 DA921x dual-modalias live-path validation state](2026-07-31-da921x-dual-modalias-path-state/README.md)
- [2026-07-31 DA921x ordered validation-stage state](2026-07-31-da921x-dual-modalias-stage-state/README.md)
- [2026-07-31 DA921x event-envelope read-only state](2026-07-31-da921x-dual-modalias-envelope-state/README.md)
  — corrects only the two live-proven root-level path strings while preserving
  no-printk read-only state, transport suppression, and the zero-I2C baseline.
- [2026-07-31 DA921x dual-modalias read-only validation state](2026-07-31-da921x-dual-modalias-state/README.md)
  — preserves exact event validation and transport suppression, removes the
  immediate printk, and exposes successful validation through read-only sysfs.
- [2026-07-31 DA921x dual-modalias event pre-dispatch suppression](2026-07-31-da921x-dual-modalias-pre-dispatch-suppression/README.md)
  — validates the exact ten-entry event, including ordered OF and I2C
  modaliases, then returns success while suppressing only netlink transport.
- [2026-07-31 DA921x complete OF uevent pre-dispatch suppression](2026-07-31-da921x-of-modalias-pre-dispatch-suppression/README.md)
  — remained fully serviceable with zero hardware activity, but the asserted
  layout failed closed before its success marker; later bounded classification
  superseded its source interpretation and proved nine total entries.
- [2026-07-31 DA921x real OF-modalias uevent rollback](2026-07-31-da921x-of-modalias-real-env-rollback/README.md)
  — inserted and validated the exact OF entry in the real event environment,
  restored its pointer, indices, and bytes exactly, and remained fully
  serviceable; this isolates the failure boundary to final event emission.
- [2026-07-31 DA921x private OF-modalias uevent insertion](2026-07-31-da921x-of-modalias-private-insertion/README.md)
  — inserted and validated the exact `MODALIAS=` entry in a private bounded
  uevent environment, discarded it, and remained fully serviceable with zero
  transfers; this isolates the remaining boundary to final event emission.
- [2026-07-30 DA921x private OF-modalias generation](2026-07-30-da921x-of-modalias-private-generation/README.md)
  — generated and validated the exact real-compatible modalias in a private
  buffer, discarded it, and remained fully serviceable with zero transfers;
  this isolates the remaining boundary to environment insertion or emission.
- [2026-07-30 DA921x post-serviceability name-only client](2026-07-30-da921x-name-only-client/README.md)
  — disables the OF child, boots with no module, and creates one unbound
  `da9214-legacy` client after serviceability to isolate I2C identity handling;
  attempt 1 failed safely because inherited sysfs is read-only.
- [2026-07-30 DA921x real-compatible module-file isolation](2026-07-30-da921x-module-file-isolation/README.md)
  — restores the real enabled compatible on the module-profile kernel while
  removing the DA921x module file and every possible load path; attempt 1
  failed before serviceability and exonerated module availability.
- [2026-07-30 DA921x unmatched-compatible client discriminator](2026-07-30-da921x-unmatched-client/README.md)
  — keeps an enabled `0x68` client but changes only its compatible to
  distinguish generic instantiation from real-compatible/modalias matching;
  attempt 1 was serviceable with one unbound client and zero transfers.
- [2026-07-30 DA921x module-profile client isolation](2026-07-30-da921x-module-client-isolation/README.md)
  — preserves the exact failed module-profile kernel and disables only the DT
  child to distinguish enabled-client creation from a kernel/config effect.
- [2026-07-29 DA921x post-serviceability module probe](2026-07-29-da921x-post-serviceability-module/README.md)
  — separates enabled-child creation from the fourteen-read driver probe by
  deferring the driver to one explicit post-serviceability module load.
- [2026-07-29 DA921x automatic-probe boot isolation](2026-07-29-da921x-probe-isolation/README.md)
  — preserves the exact failed Gate 3 kernel and disables only the new DT child
  to implicate the enabled child’s automatic creation/probe path while
  preserving full serviceability and zero I2C6 transfers.
- [2026-07-29 legacy DA921x driver lifecycle](2026-07-29-da921x-legacy-lifecycle/README.md)
  — runs Roadmap Gate 3 with an independent read-only I2C6 message-shape
  oracle; attempt 1 failed before recoverable serviceability and must not be
  repeated unchanged.
- [2026-07-29 legacy DA921x identification integration](2026-07-29-da921x-legacy-bind/README.md)
  — completes the offline binding, driver, board node, zero-write validator,
  and two-build reproducibility gate without accessing the device.
- [2026-07-29 legacy DA921x driver contract](2026-07-29-da921x-legacy-driver-contract/README.md)
  — specifies the separated identification-only driver, binding, exact
  14-transfer probe, and zero-transaction lifecycle boundary.
- [2026-07-28 Gauss exact D3 discriminator](2026-07-28-da9214-gauss/README.md)
  — completed the fixed, serviceability-gated read-only legacy-family
  board-control tuple on the native I2C6 path.
- [2026-07-28 Fermi topology fingerprint](2026-07-28-da9214-fermi/README.md)
  — obtained the bounded direct-address fingerprint and rejected its original
  masked-D3 predicate without changing regulator state.
- [2026-07-28 Curie board tuple](2026-07-28-da9214-curie/README.md)
  — records a pre-serviceability failure and watchdog return; its endpoint did
  not run and it supplies no tuple evidence.
- [2026-07-27 Quasar native I2C6 canary](2026-07-27-mt6797-i2c6-quasar/README.md)
  — established the native packed/FIFO one-byte-pointer plus one-byte-read
  controller path.
- [2026-07-27 Vega I2C6 discriminator](2026-07-27-mt6797-i2c6-vega/README.md)
  — isolated packed/FIFO success from the invalid auxiliary-APDMA path.
- [2026-07-27 Orion I2C6 discriminator](2026-07-27-mt6797-i2c6-orion/README.md)
  — records the exact-node-identity failure that was corrected before Vega.
- [2026-07-27 Mariner API-path differential](2026-07-27-i2c6-api-path-mariner/README.md)
  — showed pointer echo surviving the standard i2c-dev bounce-buffer path.
- [2026-07-27 Voyager split-pointer reads](2026-07-27-i2c6-split-pointer-voyager/README.md)
  — repeated pointer-dependent split-read echo with two register pointers.
- [2026-07-27 Kepler split read](2026-07-27-i2c6-split-read-kepler/README.md)
  — localized the earlier receive failure with separate pointer and receive
  calls.
- [2026-07-27 Hubble transient-probe base](2026-07-27-da9214-transient-probe-hubble/README.md)
  — preserved the serviceable Cassini base for one volatile Photon observation.
- [2026-07-27 Photon RX-sentinel test](2026-07-27-da9214-rx-sentinel-photon/README.md)
  — proved that the broken AP-DMA receive path retained distinct prefills.
- [2026-07-27 Cassini direct-address reads](2026-07-27-da9214-direct-address-cassini/README.md)
  — records the initial failed readback and the independent Gemian
  direct-address reconciliation.
- [2026-07-26 Pioneer active-A72 attempt](2026-07-26-a72-active-pioneer/README.md)
  — failed before a recoverable console and established no A72 execution.
- [2026-07-26 Nova active-A72 construction](2026-07-26-a72-active-nova/README.md)
  — records a superseded CPU8 candidate package and its pre-runtime boundary.
- [2026-07-26 Galileo active-A72 construction](2026-07-26-a72-active-galileo/README.md)
  — records the earlier superseded CPU8 implementation and validation work.
- [2026-07-25 legacy DA9214 identification](2026-07-25-da9214-legacy-identification/README.md)
  — documents the first fixed legacy-family identification candidate and its
  electrical hypothesis.
- [2026-07-25 shared AP-DMA baseline preservation](2026-07-25-mt6797-dvfsp-i2c6-baseline-preserve/README.md)
  — corrected I2C6 cleanup so the working I2C5 AP-DMA owner is preserved.
- [2026-07-25 eMMC development access](2026-07-25-emmc-development/README.md)
  — records guarded block access, live GPT resolution, readback, and protected
  primary-boot constraints.
- [2026-07-23 Gemian A72 owner observer](2026-07-23-gemian-a72-owner-observer/README.md)
  — records the five-patch owner-local diagnostic series. Exact observer and
  unpatched-baseline builds pass with pinned GCC 6.3, byte-identical diagnostics,
  2484 case-preserved stack reports, a 256-record ring, immediate-only clock
  semaphore probe, four boundary snapshots, and bounded timing acceptance for
  one diagnostic capture. Hardware evidence remains pending.
- [2026-07-22 Gemian A72 read-only discovery](2026-07-22-gemian-a72-readonly-discovery/README.md)
  — collected safe, read-only power and clock surfaces without an A72
  transition.

### Earlier records added to the index

- [2026-07-21 superseded userspace CPU8 request](2026-07-21-cortex-a72-cpu8-diagnostic/README.md)
  — archives an unbooted active-hotplug draft and explains why it must not be
  selected.
- [2026-07-15 `boot2` framebuffer-console write](2026-07-15-display-console-write-boot2/README.md)
  — synchronized and fully read back the early console prototype from the
  non-primary slot.
- [2026-07-15 `boot3` framebuffer-console write](2026-07-15-display-console-write/README.md)
  — records the reversible write and inconclusive owner-reported boot loop.
- [2026-07-15 framebuffer-console recovery](2026-07-15-display-console-recovery/README.md)
  — static LK/simplefb/fbcon investigation whose runtime attempt remained
  unattributable.
- [2026-07-15 first `boot3` mainline write](2026-07-15-boot3-mainline-write/README.md)
  — records one explicitly authorized non-primary write and full readback.
- [2026-07-14 transport and firmware boundary](2026-07-14-transport-firmware-boundary-audit/README.md)
  — reconciles connectivity, modem, camera, SCP, and firmware ownership.
- [2026-07-14 patch quality audit](2026-07-14-patch-quality-audit/README.md)
  — records the review-oriented static audit of the then-current patch set.
- [2026-07-14 MMC partition backup](2026-07-14-mmc-partition-backup/README.md)
  — documents the owner-authorized, read-only, private all-partition capture.
- [2026-07-14 live kernel ownership audit](2026-07-14-live-kernel-ownership-audit/README.md)
  — compares working vendor ownership with the prepared Linux package.
- [2026-07-13 mainline handoff closure](2026-07-13-mainline-handoff-closure/README.md)
  — checks static arm64 entry, PSCI, timer, GIC, console, storage, and memory
  closure.
- [2026-07-13 retained LK FDT fixups](2026-07-13-lk-fdt-fixup-recovery/README.md)
  — establishes why retained-LK DT mutation and dynamic reservations must be
  treated as part of the handoff contract.

### Established index

- [2026-07-11 Gemian hardware inventory](2026-07-11-gemian-hardware-inventory/README.md)
  — read-only whole-device discovery baseline and reusable collector.
- [2026-07-11 Gemian firmware inventory](2026-07-11-gemian-firmware-inventory/README.md)
  — private vendor-firmware capture, sanitized hashes, and load evidence.
- [2026-07-11 Gemian hardware-userspace inventory](2026-07-11-gemian-hardware-userspace-inventory/README.md)
  — Android HAL, vendor library/daemon, and native compatibility-boundary map.
- [2026-07-11 MT6797 device-tree recovery](2026-07-11-mt6797-device-tree-recovery/README.md)
  — decoded live resources for mainline DTS and driver data.
- [2026-07-11 vendor userspace to kernel ABI](2026-07-11-vendor-kernel-abi/README.md)
  — static interface extraction and Linux 7.1.3 replacement-gap analysis.
- [2026-07-11 Gemini panel recovery](2026-07-11-gemini-panel-recovery/README.md)
  — runtime panel selection, DSI mode, command, bias, reset, false-DT-lead,
    and the descriptor-based mainline NT36672E framework recovery.
- [2026-07-11 MT6351 PMIC recovery](2026-07-11-mt6351-pmic-recovery/README.md)
  — direct PMIC identity, pwrap/reset clocks, regulators, RTC, power keys, and
  the missing MT6797 EINT prerequisite.
- [2026-07-12 MT6797 MSDC recovery](2026-07-12-mt6797-msdc-recovery/README.md)
  — storage-controller register contract, live eMMC/card-slot state, and a
  conservative Linux 7.1 bring-up plan.
- [2026-07-12 MT6797 M4U and SMI recovery](2026-07-12-mt6797-m4u-smi-recovery/README.md)
  — multimedia IOMMU topology, SMI larbs, fault IDs, ports, clocks, and
  power-domain recovery for Linux 7.1.
- [2026-07-12 MT6797 CMDQ/GCE recovery](2026-07-12-mt6797-cmdq-gce-recovery/README.md)
  — live mailbox execution, thread/address format, subsystem selectors,
  hardware events, clock gating, and normal/secure IRQ separation.
- [2026-07-12 MT6797 display-mutex recovery](2026-07-12-mt6797-display-mutex-recovery/README.md)
  — module bits, SOF/EOF encoding, register layout, live IRQ/clock evidence,
  DEVAPC boundary, MM power domain, and GCE client contract.
- [2026-07-12 MT6797 MMSYS routing recovery](2026-07-12-mt6797-mmsys-routing-recovery/README.md)
  — complete mux graph, active OVL/RDMA/UFOE/DSI route, reset banks, and GCE
  client contract.
- [2026-07-12 MT6797 DRM component recovery](2026-07-12-mt6797-drm-component-recovery/README.md)
  — OVL, fixed-function PQ, RDMA, UFOE, DSI, and MIPI-PHY register-generation,
  clock, interrupt, and safe first-light contract recovery.
- [2026-07-12 input and backlight recovery](2026-07-12-input-backlight-recovery/README.md)
  — live Novatek touchscreen/EINT, AW9523 keyboard matrix, and MT6797 display
  PWM contracts compared with Linux 7.1.3 reuse boundaries, plus a disabled
  standard AW9523 matrix-keypad candidate and vendor-ELF/source parity for the
  eleven-entry NT36xxx trim table.
- [2026-07-12 sensor and IIO recovery](2026-07-12-sensor-iio-recovery/README.md)
  — live I2C1 sensor bindings, vendor virtual-sensor boundary, and Linux 7.1.3
  reuse versus new-driver decisions.
- [2026-07-12 USB and Type-C recovery](2026-07-12-usb-typec-recovery/README.md)
  — live USB1/USB3 windows, MT6797 PHY clocks and tuning boundary, and the
  generic FUSB301 controller candidate plus the unresolved board/role contract.
- [2026-07-12 connectivity/WMT recovery](2026-07-12-connectivity-wmt-recovery/README.md)
  — MT6797 CONSYS/WMT identity, Wi-Fi/BTIF/GNSS/FM resources, firmware hashes,
  and the standard Linux 7.1 reuse boundary.
- [2026-07-12 audio AFE recovery](2026-07-12-audio-afe-recovery/README.md)
  — live ASoC endpoints, MT6797 AFE/MT6351 codec graph, and the existing
  Linux 7.1.3 reuse boundary.
- [2026-07-12 CPU DVFS, thermal, and suspend recovery](2026-07-12-cpufreq-thermal-suspend-recovery/README.md)
  — live cpufreq policies, vendor OPP diagnostics, thermal-zone sentinels,
  cpuidle/PSCI state evidence, and the missing MT6797 mainline contracts.
- [2026-07-13 CPU/PSCI/timer recovery](2026-07-13-cpu-psci-timer-recovery/README.md)
  — live ten-CPU DT topology, PSCI 0.2 SMC IDs, architectural timer PPIs,
  clocksource/clockevent selection, and the generic Linux reuse boundary.
- [2026-07-13 MT6797 thermal recovery](2026-07-13-mt6797-thermal-recovery/README.md)
  — live disabled thermal zones, six-bank/five-sensor mapping, efuse
  calibration contract, and the new MT6797 thermal-driver boundary.
- [2026-07-12 MT6797 GPU/Panfrost recovery](2026-07-12-mt6797-gpu-panfrost-recovery/README.md)
  — live Mali-T88x identity, vendor GPU DVFS/clock contracts, and the
  Panfrost-versus-platform integration boundary.
- [2026-07-12 RT5735 VGPU recovery](2026-07-12-rt5735-vgpu-recovery/README.md)
  — external GPU-buck identity, register/voltage contract, and the dedicated
  regulator-driver boundary.
- [2026-07-12 boot contract recovery](2026-07-12-boot-contract-recovery/README.md)
  — Android boot-image layout, retained LK chosen properties, root partition,
  and the reversible mainline boot-artifact boundary.
- [2026-07-12 charger and fuel-gauge recovery](2026-07-12-charger-power-recovery/README.md)
  — live BQ25890/FAN49101 ownership, the inactive RT9466 alternative, and the
  standard power-supply versus new-driver boundary, including the bounded
  FAN49101 register contract and disabled-only mainline driver candidate.
- [2026-07-12 MT6797 watchdog recovery](2026-07-12-mt6797-watchdog-recovery/README.md)
  — TOPRGU register/protocol reuse, the Gemini bark IRQ, and the vendor WDK
  side-channel boundary.
- [2026-07-12 MT6797 clock/power/reset recovery](2026-07-12-mt6797-clock-power-reset-recovery/README.md)
  — live clock summary, SCPSYS resource ordering, MFG/core SRAM handshake,
  and the generic-provider extension boundary.
- [2026-07-12 MT6797 EINT and pinctrl recovery](2026-07-12-mt6797-eint-recovery/README.md)
  — vendor-versus-live EINT contract, recovered GPIO map, virtual PMIC input,
  and the generic Linux reuse/new-data boundary.
- [2026-07-12 hall/lid/switch recovery](2026-07-12-hall-lid-switch-recovery/README.md)
  — GPIO66/EINT5 hall input, GPIO93/EINT16 toggle input, vendor polarity and
  debounce behavior, and the standard `gpio-keys` replacement boundary.
- [2026-07-12 kernel configuration gap audit](2026-07-12-kernel-config-gap-audit/README.md)
  — vendor 3.18 versus prepared Linux 7.1.3 options, modern symbol mappings,
  and the distinction between missing drivers and private policy switches.
- [2026-07-13 driver coverage audit](2026-07-13-driver-coverage-audit/README.md)
  — linked-in/module-only driver ownership and live vendor-driver comparison
  for the packaged Linux 7.1.3 candidate.
- [2026-07-13 bsg100 comparison](2026-07-13-bsg100-gemini-linux-comparison/README.md)
  — independent-reference audit, including a focused review of the later
  native-fbcon milestone, the portable MT6797 DRM/PHY findings, the targeted
  simplefb backlight-clock test, and the unresolved SSD2092/NT36672 variant
  boundary.
- [2026-07-14 first-boot probe audit](2026-07-14-first-boot-probe-audit/README.md)
  — static PWRAP/MT6351/regulator/MSDC probe ordering and write-side-effect
  boundary for the conservative first boot.
- [2026-07-14 mainline module closure audit](2026-07-14-mainline-module-closure-audit/README.md)
  — built-in versus optional-module availability and exact packaged dependency
  closures for the current 7.1.3 kernel artifact.
- [2026-07-16 LK handoff alignment](2026-07-16-lk-handoff-alignment/README.md)
  — modern arm64 placement, LK pre-jump DT properties, a probe-minimal kernel
  profile, reproducible serial/simplefb Android v0 test candidates, and the
  dark/serial-silent/non-looping `boot2` attempt whose Linux runtime remains
  unknown.
- [2026-07-16 USB gadget diagnostic](2026-07-16-usb-gadget-diagnostic/README.md)
  — MTU3/T-PHY peripheral candidate and storage-inert initramfs, now written
  and fully read back from `boot2`; two bounded host checks found no USB child
  while the device remained dark and steady, leaving that cycle's Linux
  execution unknown. Later exact M/N retained pstore independently proves the
  T-PHY and MTU3 probes, forced B-device session, `g_ether` registration, and
  MTU3 gadget pull-up log on the inherited path, but not electrical D+ state
  or host enumeration; see the
  [sanitized retained-pstore result](2026-07-16-usb-gadget-diagnostic/results/retained-pstore-mtu3-gadget-evidence-20260718.txt).
- [2026-07-16 fixed-delay reboot diagnostic](2026-07-16-timed-reboot-diagnostic/README.md)
  — reproducible ramdisk-only follow-up that preserves the tested USB kernel
  and DTB while arming a 10-second reset request from `/init`; owner-approved
  `boot2` write is synchronized and fully read back. Its first boot changed
  from the baseline's dark steady state to a delayed backlight-off, off-like
  state after an owner-estimated 5–10 seconds with no automatic restart. The
  timing and one-file delta strongly support `/init` execution but do not yet
  directly confirm it.
- [2026-07-16 deterministic screen marker](2026-07-16-screen-marker-diagnostic/README.md)
  — preserves exact candidate D's kernel while adding an allowlisted LK
  simplefb node and one bounded early-userspace framebuffer fill; two builds
  are byte-identical. The image was written and fully read back from `boot2`,
  but its first owner-run boot remained black with no expected marker. This is
  a failed positive screen test, not proof of kernel failure. The next
  one-variable derivative retains `CLK_INFRA_DISP_PWM` through simplefb based
  on the hardware-working bsg100 history.
- [2026-07-16 simplefb clock-retention diagnostic](2026-07-16-screen-clock-retention-diagnostic/README.md)
  — Candidate F reconstructs exact Candidate E and adds only its path-resolved
  `CLK_INFRA_DISP_PWM` simplefb reference. Its first boot showed sideways
  console text for about one second before black, the first positive visual
  Linux 7.1.3 handoff signal on this unit; unread text does not prove `/init`.
- [2026-07-16 fbcon text retention diagnostic](2026-07-16-fbcon-text-diagnostic/README.md)
  — Candidate G keeps exact F's kernel, DTB and simplefb clock reference while
  replacing only initramfs, removing all raw framebuffer access, and holding a
  distinctive sideways console banner. Its attended boot reproduced sideways
  scrolling for 1–2 seconds before black with the backlight apparently off,
  rejecting Candidate F's raw-write explanation but not confirming `/init`.
- [2026-07-16 simplefb MM-root retention](2026-07-16-simplefb-mm-root-retention/README.md)
  — Candidate H keeps exact G's kernel and initramfs and appends only
  `CLK_TOP_MUX_MM` to simplefb's retained clocks. Two builds are recursively
  byte-identical. In one attended series, two attempts visibly progressed
  farther and the owner approximately recognized H's initramfs-only marker;
  the backlight remained on with the text and went off at the black transition.
  Later attempts did not reproduce the progress, so stable retention remains
  unresolved.
- [2026-07-16 fbcon refresh-timing diagnostic](2026-07-16-fbcon-refresh-timing-diagnostic/README.md)
  — Candidate I keeps H's exact kernel and DTB and exact initramfs tree except
  `/init`, then emits one tty0 line per second through `T+60` before a silent
  static hold. Two builds are byte-identical; the exact image is exported,
  synchronized and fully read back from `boot2`. The reported intended
  selection went directly to black without I's marker, counter, or other text;
  selection and `/init` remain unconfirmed and the timing hypothesis is
  untested.
- [2026-07-17 unused-clock cleanup diagnostic](2026-07-17-clk-ignore-unused-diagnostic/README.md)
  — Candidate J rebuilds the kernel to append `clk_ignore_unused` to forced
  `CONFIG_CMDLINE` while retaining exact I's DTB, initramfs, and Android header
  command line. A header-only draft was rejected as a no-op under
  `CONFIG_CMDLINE_FORCE=y`. The raw image is
  `6d5bad08c2f93eba7fbd66ea5c54de2437f81e44832426a97d4d65d550c659f4`;
  an isolated clean build reproduced the config, kernel payload, `System.map`,
  all 119 DTBs, and boot image byte-for-byte. It was synchronized, flushed, and
  fully read back from logical `boot2`; that full 16 MiB partition/readback hash
  was `465e4c747138e12191d38fd6b4cde68cd0b9a19f918030dea05c9b8dbdd4d3fc`.
  No reboot was part of the [write/readback operation](2026-07-17-clk-ignore-unused-diagnostic/results/boot2-write-candidate-j-20260717.txt).
  On the first later owner-attended intended selection, the last visible suffix
  before black was reported as `4/60`. Only the tracked shared I/J `/init` emits
  that counter, so this strongly supports Linux/fbcon/tty0 and `/init` tick 04
  for the verified J target in that attempt, without an exact full-line or
  marker transcription. A later two-bullet report is provisionally interpreted
  as two additional intended J/`boot2` selections because the outcomes are
  mutually exclusive, with owner confirmation pending. One reached "iteration
  4" before black, compatible with and corroborating tick 04; one went directly
  black with no console and cannot establish selected slot, kernel entry, or
  `/init`. Provisionally, two of three intended selections had
  tick-04-compatible visible output and one of three was no-console and
  unattributable. The [first runtime](2026-07-17-clk-ignore-unused-diagnostic/results/runtime-candidate-j-attempt-1-20260717.txt)
  and [repeat report](2026-07-17-clk-ignore-unused-diagnostic/results/runtime-candidate-j-repeat-report-20260717.txt)
  preserve the unknowns. Stable visibility and clock causality are not
  established. Further J repetition is stopped; the completed reassessment
  initially selected Candidate K rather than a matched-I rollback, then the
  strategy review cancelled K without runtime. This broad control
  does not enable already-off clocks, prevent explicit disables, or retain
  regulators or power domains.
- [2026-07-17 fbcon newline-boundary diagnostic](2026-07-17-fbcon-newline-boundary-diagnostic/README.md)
  — Candidate K is a reproducible exact-J initramfs-only newline/scroll
  derivative. Its write/readback record is retained, but the strategy review
  cancelled the device test without a runtime selection because it changes no
  kernel, DT, or configuration input and would not alter the next action.
- [2026-07-17 UART/pstore observability](2026-07-17-uart-pstore-observability/README.md)
  — Candidate L was the bounded observability gate:
  UART0 GPIO97/98 correction, exact mainline-console/Gemian
  primary `console-ramoops` alignment validated from pinned source and the
  exact active binary, and MT6797 watchdog auto-restart plus IRQ-dependent dual-stage
  policy with persistent post-reset evidence. Pmsg supplies address alignment,
  not a cross-version recovery channel. A clean fresh-source rebuild reproduced
  the candidate exactly; it is exported and its synchronized logical-`boot2`
  write has a matching full readback. Attempt 1 showed the LK splash then black
  and was unattributable. Attempt 2 strongly reached tracked `/init` suffix
  `watchdog0=waiting remaining=5s`; connected serial stayed silent, the screen
  switched off, manual power recovery was required, and pstore was empty.
  Unchanged repetition is stopped. A source audit rejects changing the
  falling-edge flag because MediaTek SYSIRQ translates it for the parent GIC.
  Candidate M therefore omits only the optional bark IRQ and adds early
  binding diagnostics, matching an independent hardware-tested basic-watchdog
  configuration. See [attempt 1](2026-07-17-uart-pstore-observability/results/runtime-candidate-l-attempt-1-20260718.txt),
  [attempt 2](2026-07-17-uart-pstore-observability/results/runtime-candidate-l-attempt-2-20260718.txt),
  and the [registration audit](2026-07-17-uart-pstore-observability/results/watchdog-registration-audit-20260718.txt).
- [2026-07-18 watchdog registration diagnostic](2026-07-18-watchdog-registration-diagnostic/README.md)
  — Candidate M keeps Candidate L's exact Linux `Image.gz` and LK header
  contract, deletes only the optional watchdog bark interrupt from the
  appended DTB, and replaces only initramfs `/init`. A live-DT gate plus
  platform, driver, class, devnode, ramoops, kmsg, and filtered-dmesg evidence
  distinguishes an IRQ-blocked registration from the next probe-stage fault.
  Two clean VM builds are recursively identical; raw SHA-256 is
  `a0a6c520fcc170ee0a422e66384559c50100ee65645811c331149beec8c347da`.
  Its synchronized, flushed logical-`boot2` target and complete readback match
  padded SHA-256
  `53234ca7e81b23c77b0910e1e2bcdf54dc7a2984e28bbe9baac30ad26eeb7c2b`.
  Its first controlled runtime passed the decision oracle: retained
  `console-ramoops` proves the live IRQ omission, successful `mtk-wdt` probe,
  `/dev/watchdog0`, one handoff ping, a 31-second timeout, and progress through
  `watchdog_wait=30s`. The console remained visible and the device returned to
  Gemian automatically; Gemian reported `wdt_by_pass_pwk`, `reboot`, and set
  PMIC watchdog-reboot flags. This establishes the basic no-IRQ TOPRGU reset
  and cross-version console retention for this revision, not bark/pretimeout,
  native display, SMP, or repeatability. See the
  [runtime record](2026-07-18-watchdog-registration-diagnostic/results/runtime-candidate-m-attempt-1-20260718.txt);
  do not repeat unchanged M.
- [2026-07-18 CPU1 online diagnostic](2026-07-18-cpu1-online-diagnostic/README.md)
  — Candidate N passed its first bounded runtime gate. It retains Candidate M's exact
  kernel, embedded configuration, no-IRQ DTB, LK container contract, pstore,
  fbcon, and 31-second recovery timer, changing only initramfs `/init`. The
  exact kernel already has SMP, CPU hotplug, PSCI, and sysfs; the intended
  first secondary DT CPU is Cortex-A53 MPIDR `0x1`, and N gates the live CPU1
  `of_node` against it. N arms the watchdog before writing
  `1` exactly once to CPU1's standard `online` control, then records the return,
  masks, kernel lines, and CPU1 accounting without retrying or pinging again.
  Two clean VM builds are recursively byte-for-byte identical; the raw image
  SHA-256 is
  `43aea71224f6261001ff00904b30dae29063334172a2f6b0163b424a84c0e3aa`.
  It was synchronized to live-resolved logical `boot2`, flushed, and fully
  read back with exact padded SHA-256
  `a5cc12372ece5e50364a88bc0bf4401ff092e335281352b062ed0ad229fbb7bf`.
  Its one attended selection produced the exact N record in retained
  `console-ramoops`. The CPU-hotplug request returned success, CPU1 booted as
  MPIDR `0x1` / Cortex-A53, the online mask changed from `0` to `0-1`, and two
  `/proc/stat` samples proved advancing CPU1 accounting. CPU1 remained online
  through the 25-second marker, then the watchdog returned the device to
  Gemian automatically without owner help. This promotes only the first
  secondary Cortex-A53 path from one run; do not repeat unchanged N. The next
  candidate may request the remaining A53s in sequence, provided every request
  has a durable execution checkpoint and the sequence stops at its first
  failure; keep the A72 pair separate. See the
  [build reproduction](2026-07-18-cpu1-online-diagnostic/results/final-build-reproduction-20260718.txt),
  [write/readback](2026-07-18-cpu1-online-diagnostic/results/boot2-write-candidate-n-20260718.txt),
  and [runtime record](2026-07-18-cpu1-online-diagnostic/results/runtime-candidate-n-attempt-1-20260718.txt).
- [2026-07-18 Cortex-A53 sweep diagnostic](2026-07-18-cortex-a53-sweep-diagnostic/README.md)
  — Candidate O is the deterministic initramfs-only derivative of exact N. It
  validates all CPU1–9 logical-to-DT mappings, arms the proven no-IRQ watchdog,
  and requests CPU1 through CPU7 online in sequence with a durable
  boot/accounting checkpoint after each. It stops at the first failure and
  never writes the deferred Cortex-A72 CPU8/9 controls.
  The raw image is pinned to SHA-256
  `4376579c3b1a9ddfbec485eb62ba6cfc0af38183527924b5a250246345cb2146`;
  two clean VM builds are recursively byte-identical and the exact artifact is
  available in the Git-ignored host export. The exact padded image was then
  synchronized, block-flushed, and fully read back from live-resolved logical
  `boot2`; the full target matches SHA-256
  `5efda7d18ebb99d0152d872d6dd23e7e6345c56920a77fb1129c350e8e02102d`.
  Its first controlled run passed: retained `console-ramoops` proves every
  CPU1–7 request returned, every Cortex-A53 booted and advanced accounting, the
  cumulative online mask reached `0-7`, and CPU8/9 remained offline. The
  cycle-aware collector observed a changed-cycle return to Gemian, whose
  sanitized boot reason was watchdog-class. This is one successful hotplug
  run, not boot-time SMP, repeatability, stress, A72, DVFS, idle, or thermal
  evidence. Do not repeat unchanged O. Candidate P subsequently passed the
  isolated rotation gate.
  See the
  [build reproduction](2026-07-18-cortex-a53-sweep-diagnostic/results/final-build-reproduction-20260718.txt),
  [write/readback](2026-07-18-cortex-a53-sweep-diagnostic/results/boot2-write-candidate-o-20260718.txt),
  and [runtime record](2026-07-18-cortex-a53-sweep-diagnostic/results/runtime-candidate-o-attempt-1-20260718.txt).
- [2026-07-18 framebuffer-console rotation diagnostic](2026-07-18-fbcon-rotation-diagnostic/README.md)
  — Candidate P was reproducibly built from exact O's DTB, initramfs, and
  Android-v0/LK container contract. Its only resolved kernel-configuration
  changes enable framebuffer-console rotation and append forced
  `fbcon=rotate:3`. The raw artifact is
  `artifacts/vm-export/boot-candidates/candidate-P-fbcon-rotation-170a640`
  with SHA-256
  `d192dac9e4516eac9319da2a885abaf3203da6c357c574e7f1f6deef2208d341`.
  It was synchronized, block-flushed, and fully read back from live-resolved
  logical `boot2`; the padded target SHA-256 is
  `cea00d591e74a29d74200f4d292a92aaca2f890bd965af37a7673ab906f4afbc`.
  Its first attributable runtime selection passed: the owner observed readable
  normal-landscape text and an unassisted return to Gemian, while post-return
  `console-ramoops` retained every CPU1--7 checkpoint, final `online=0-7`
  success, CPU8/9 offline, and the 5/10-second waits. Collection began after
  return and therefore did not capture the tested cycle's changed boot ID or
  boot reason. The inherited `GEMINI_A53_SWEEP_20260718_O` marker identifies
  only the preserved O initramfs; exact P configuration, artifact/readback,
  intended selection, and P-only rotation behavior establish P. See the
  [build reproduction](2026-07-18-fbcon-rotation-diagnostic/results/final-build-reproduction-20260718.txt),
  [write/readback](2026-07-18-fbcon-rotation-diagnostic/results/boot2-write-candidate-p-20260718.txt),
  and [runtime record](2026-07-18-fbcon-rotation-diagnostic/results/runtime-candidate-p-attempt-1-20260718.txt).
- [2026-07-18 keyboard and supervised-shell diagnostic](2026-07-18-keyboard-shell-diagnostic/README.md)
  — completed Candidate Q build/write work and its failed first runtime gate.
  The exact installed image did not provide a working text console; no marker,
  AW9523/input/shell observation, or retained pstore evidence identifies a
  deeper boundary. Static review found that its parent interrupt specifier used
  raw line 87 although GPIO87 maps to EINT10, but the runtime result does not
  prove that defect caused the failure. Unchanged Q must not be repeated.
  Candidate U was the polling follow-up. It retained the upstream AW9523 driver
  and reset polarity plus the GPIO87/EINT10 pinmux while omitting its
  parent-IRQ consumer from the active path; it added generic
  schema-described matrix polling and made the shell independent of bounded
  event capture. Two builds matched and its full `boot2` readback matched, but
  its first intended selection produced a black screen and dark console with
  no visible marker or automatic reboot. A later changed Gemian boot ID and
  empty post-return pstore establish no deeper U gate. A later packaging audit
  found that U's final DTB came from the kernel package rather than exact P; it
  omitted P's loader-framebuffer, no-IRQ watchdog, and other LK-aligned fixups.
  That explains why U did not carry P's configured console path, but does not
  prove U entered Linux or identify the black-screen cause. Do not repeat
  unchanged U.
- [2026-07-19 keyboard polling diagnostic](2026-07-19-keyboard-polling-diagnostic/README.md)
  — Candidate U's build, guarded install, and failed first visible-console
  gate. Series patch
  0083 adds the polling binding, 0084 implements generic matrix polling, and
  0085 corrects the disabled board description from raw EINT87 to EINT10.
  Candidate-only packaging removes
  the AW9523 parent-IRQ hierarchy, retains GPIO87/EINT10 pinmux with no active
  consumer, and pins the polling transport/timing policy. Two independent
  builds produced matching validated outputs; the exact candidate was installed
  to live-resolved logical `boot2` and its full-partition readback matched. Its
  first intended selection then stayed black with no visible marker or
  automatic reboot. Post-return pstore was empty, so kernel, `/init`, console,
  keyboard, and shell entry remain unestablished. See the [build reproduction](2026-07-19-keyboard-polling-diagnostic/results/final-build-reproduction-20260719.txt),
  [write/readback](2026-07-19-keyboard-polling-diagnostic/results/boot2-write-candidate-u-20260719.txt),
  and [runtime](2026-07-19-keyboard-polling-diagnostic/results/runtime-candidate-u-attempt-1-20260719.txt)
  records; do not repeat unchanged U.
- [2026-07-19 keyboard watchdog diagnostic](2026-07-19-keyboard-watchdog-diagnostic/README.md)
  — Candidate V restores exact P's hardware-passed final DT foundation, adds
  only the audited polling-keyboard transform, and reinstates the no-IRQ
  watchdog/ramoops decision path. Two fresh kernel builds and two complete V
  assemblies matched, the package and focused schemas validated, and all 24
  negative mutations were rejected. The 6,864,896-byte raw image is SHA-256
  `9ef0ee8dc1eb49752f9cf8f60b247b9b85e4fd2a9f090473f1d91848114087b0`.
  It is installed, synchronized, and fully read back from live-resolved
  logical `boot2`; the exact padded checksum is
  `57d362a86fae38c0ec2cec909ef6ae8d8ad124b87abb2ee58d179184c1f19168`.
  The installation did not reboot the device. In attempt 1 the owner selected
  V from `boot2`, saw a visible console, had no usable opportunity to test the
  shell or keyboard, and observed an automatic return. Retained
  `console-ramoops` proves exact V kernel/initramfs entry, local-shell's
  `tty1_shell=ready` pre-exec recorder, and the exact `mtk-wdt` open/one-ping
  path through its 30-second wait. It does not prove `ash` exec, a visible or
  interactive prompt, or input. AW9523 probe on adapter 0 at `0x5b` repeatedly
  failed `-110`/`ETIMEDOUT`, including its reset retry; AW9523 and the matrix
  remained unbound and no event node appeared. Read-only disassembly of the
  exact working 3.18 binary shows unconditional MT6797 WRRD with auxiliary RX
  length at offset `0x6c`; V instead falls through to `mt6577_compat`. Latest
  bsg100 independently fixed the same combined-read failure with a direct
  MT6797-to-MT8173 controller-data match. The Gemian return reported
  `boot_reason=4`, `wdt_by_pass_pwk`, and `powerup_reason=reboot`. Do not repeat
  unchanged V. See the [build reproduction](2026-07-19-keyboard-watchdog-diagnostic/results/final-build-reproduction-20260719.txt),
  [guarded write/readback](2026-07-19-keyboard-watchdog-diagnostic/results/boot2-write-candidate-v-20260719.txt),
  [runtime evidence](2026-07-19-keyboard-watchdog-diagnostic/results/runtime-candidate-v-attempt-1-20260719.txt),
  and [working 3.18 controller audit](2026-07-19-keyboard-watchdog-diagnostic/results/working-3.18-aw9523-i2c-binary-audit-20260719.txt).
- [2026-07-19 MT6797 I2C WRRD diagnostic](2026-07-19-keyboard-wrrd-diagnostic/README.md)
  — Candidate W implements the V-derived controller hypothesis as exactly one
  driver-match line: `mediatek,mt6797-i2c` selects existing
  `mt8173_compat`, matching the working 3.18 WRRD/auxiliary-RX-length contract
  and latest checked bsg100 `main` revision
  [`60f5f4ac`](https://github.com/bsg100/gemini-linux/commit/60f5f4ac777a0aeccc89b5d3a4f8cd1f1ebe57b3).
  It keeps exact V's final DTB, AW9523/matrix policy, no-IRQ watchdog, and
  ramoops. Observation-only changes move kernel messages to fixed tty2,
  respawn the foreground shell on tty1 without background marker fanout, and
  force the larger `TER16x32` font. Two clean packages match after normalizing
  only `generated_utc` provenance, two final candidate assemblies are
  recursively identical, and all 24 mutation cases pass. The initramfs
  SHA-256 is
  `3793bec7a63074b237d041bcd42e6edfccc80f0a3d7b19869abf99ee7874dac6`;
  the 6,866,944-byte raw image SHA-256 is
  `34c41fad1e86de05b6a1f64f7e5d9229bd26ea88d982b0a57f2b9573aeb782d4`.
  The exported `rebuild4` artifact was installed without reboot to
  live-resolved logical `boot2`; the padded image, remote post-flush checksum,
  and full local readback match SHA-256
  `0ff3220096aa53f792116b3899e356bc2516816c9c330309c3d81e9fe1446608`.
  The owner selected exact W once. Retained evidence proves successful AW9523
  and matrix binding, `/dev/input/event0`, and press/release records for H, E,
  L, P, and Enter. The owner observed a visible shell, working keyboard, and the
  desired font. This is one limited-key hardware run, not full coverage or
  repeatability. Kernel logs remained mixed with the foreground shell, and the
  deliberate watchdog handoff forced an automatic return before useful work.
  See the [build reproduction](2026-07-19-keyboard-wrrd-diagnostic/results/final-build-reproduction-20260719.txt),
  [mutation result](2026-07-19-keyboard-wrrd-diagnostic/results/validator-mutations-20260719.txt),
  [guarded write/readback](2026-07-19-keyboard-wrrd-diagnostic/results/boot2-write-candidate-w-20260719.txt),
  and [runtime result](2026-07-19-keyboard-wrrd-diagnostic/results/runtime-candidate-w-attempt-1-20260719.txt).
- [2026-07-19 clean-tty/manual-reboot diagnostic](2026-07-19-keyboard-manual-reboot-diagnostic/README.md)
  — Candidate X retained W's exact keyboard
  kernel and final DTB, removes only `console=tty2`, removes all initramfs
  watchdog ownership, and adds a typed manual-reboot wrapper. Two clean kernel
  builds reproduced all 220 non-timestamp files, two final assemblies are
  recursively identical, all 32 LK gates passed, and all 47 mutations were
  rejected. The 6,864,896-byte raw image SHA-256 is
  `bf4003871daaba1faa293f2b128021d3a67d41ebf3ddff1c42463409803b9296`;
  the initramfs SHA-256 is
  `b54ce3cd75e7947ed867165e31abbf6ee6cbac7d41d171435f99bba7825bc769`.
  A guarded operation backed up exact W, resolved logical `boot2` as
  `/dev/mmcblk0p30` with active root `/dev/mmcblk0p29`, then synchronized,
  flushed, and fully read back X with padded SHA-256
  `e89d71f15465b544db163b5f0b90b456e913c38ba4d2ed49aa7bde345148c855`.
  The device was not rebooted and its boot ID remained unchanged. The owner
  later reported that X booted and worked, then appeared to hang after typing
  `reboot`. No automatic return was observed; power-key recovery reached Gemian
  and pstore was empty. This does not establish clean tty1, the exact marker, X
  uptime, or individual keyboard subgates. See the [build reproduction](2026-07-19-keyboard-manual-reboot-diagnostic/results/final-build-reproduction-20260719.txt),
  [mutation result](2026-07-19-keyboard-manual-reboot-diagnostic/results/validator-mutations-20260719.txt),
  [guarded write/readback](2026-07-19-keyboard-manual-reboot-diagnostic/results/boot2-write-candidate-x-20260719.txt),
  and [runtime result](2026-07-19-keyboard-manual-reboot-diagnostic/results/runtime-candidate-x-attempt-1-20260719.txt).
- [2026-07-19 typed hardware-watchdog reboot diagnostic](2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/README.md)
  — Candidate Y was reproducibly built and fully read back from logical
  `boot2`, but exact BusyBox command-dispatch validation rejected it before
  selection. Bare `reboot` resolves to BusyBox's internal applet rather than
  Y's external watchdog wrapper, and failed watchdog-open redirection cannot
  reach the promised refusal. Y was never booted and must not be booted. See
  the decisive [pre-boot command-dispatch audit](2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/results/preboot-command-dispatch-audit-20260720.txt).
- [2026-07-19 dispatch-safe typed watchdog reboot diagnostic](2026-07-19-keyboard-reboot-dispatch-diagnostic/README.md)
  — Candidate Z is the hardware-tested keyboard/recovery foundation inherited by AA r1. It preserves
  exact Y's kernel, DTB, and configuration and changes four initramfs members
  plus adds read-only `bin/reboot-dispatch.env`. Two complete builds are
  recursively identical, the exact-BusyBox dispatch gate passed on Linux
  arm64, all 32 LK gates passed, and 75/75 mutations were rejected. The raw
  6,866,944-byte image SHA-256 is
  `985a6472b7fdbfd4c58da4773a8c2cae1e3aa40ea90240eb2b309390ed7674b9`;
  the initramfs SHA-256 is
  `a21cc6bed9024bba9e01864aeb0c6c3339231d217f77ff5fa733ea33e6a0e7d2`.
  The guarded installer backed up exact Y and fully read back Z from
  live-resolved logical `boot2` with padded SHA-256
  `ba21e6424f94c82f14fd51b5681eea68d6cf09e9177e4f9ca2061c9f129abb40`;
  it did not reboot the device. The owner later selected Z once, reported a
  successful boot with the keyboard still working, typed its watchdog reboot,
  and observed an automatic Gemian return. The changed post-return boot ID and
  `androidboot.bootreason=wdt_by_pass_pwk` corroborate a watchdog-class reset.
  Exact Z text, dispatch/preflight subgates, countdown timing, individual keys,
  clean tty1, and repeatability remain unproved. See the
  [build validation](2026-07-19-keyboard-reboot-dispatch-diagnostic/results/build-validation-20260720.txt),
  [dispatch validation](2026-07-19-keyboard-reboot-dispatch-diagnostic/results/ash-dispatch-validation-20260720.txt),
  [installer validation](2026-07-19-keyboard-reboot-dispatch-diagnostic/results/installer-validation-20260720.txt),
  [mutation result](2026-07-19-keyboard-reboot-dispatch-diagnostic/results/validator-mutations-20260720.txt),
  [guarded write/readback](2026-07-19-keyboard-reboot-dispatch-diagnostic/results/boot2-write-candidate-z-20260720.txt),
  and [runtime result](2026-07-19-keyboard-reboot-dispatch-diagnostic/results/runtime-candidate-z-attempt-1-20260720.txt).
- [2026-07-20 Gemini console-keymap diagnostic](2026-07-20-keyboard-console-map-diagnostic/README.md)
  — Candidate AA r0 is historical: it was built, validated, installed, and
  fully read back, but was superseded before boot because it omitted Shift+Fn
  F1–F10 and used an invalid `dumpkmap` byte-comparison oracle. Do not boot it.
  Its immutable 7,120,896-byte raw image SHA-256 is
  `a2ad7a4107abd99cbd349b8f2deadd0185cbdd5bb0884ecbdae8ff2a7499ed4c`;
  its historical keymap SHA-256 is
  `48f1f61a9ad8ba327a3105c0dfbbc698c1e55bb3bcca695b46887888be8ca821`.
  The padded image and full live-GPT-resolved logical-`boot2` readback remain
  SHA-256
  `157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa`
  and add no runtime evidence.

  AA r1 is built, validated, installed, and passed attended runtime attempt 1.
  It retains exact Z's kernel field, final DTB, resolved configuration,
  keyboard, font, and recovery inputs.
  Its 2,311-byte, eight-table map has SHA-256
  `02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c`
  and 53 audited semantic changes: photographed printable/navigation symbols,
  Unicode Fn+period U+263A, Shift+Fn F1–F10, backslash Ctrl/Alt semantics, and
  modifier press/release safety. Media, brightness, phone, airplane, launcher,
  and voice actions remain userspace policy. Its respawn-safe live oracle sets
  Unicode mode, accepts an already exact map or performs exact preflight and
  load, reads all 2,048 planned-table entries with `KDGKBENT`, requires the
  untouched upper halves to be `K_HOLE`, accounts for table 3 payload entry 0
  changing from valid `K_HOLE` to kernel `K_ALLOCATED`, and rejects every
  undeclared table. The canonical static AArch64 verifier is SHA-256
  `29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238`.
  Two clean constructions are recursively byte- and metadata-identical. The
  7,378,944-byte raw image is SHA-256
  `37e82bf3be87dd9e52fb8d60597b69f92a5c0dc5aebd51d178f1e7efd33343d7`.
  The guarded live-GPT installation required exact r0 predecessor
  `157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa`,
  resolved `boot2` as `/dev/mmcblk0p30`, preserved a private full backup, and
  fully read back padded r1 as SHA-256
  `38b49c7c19c2d97fa0c48436545219489221aa367aedf491ae6ebd4ec4856703`.
  The installation did not reboot. In the attended run the owner reported the
  new keymap working. Retained pstore proves `origin=loaded-now`, tty1
  `K_UNICODE`, exact verification of all 2,048 entries plus high-half holes and
  undeclared-table absence, table-3 allocation, `GEMINI-AA-R1#`, and validated
  reboot dispatch at 2.407618 seconds, plus exact AW9523/matrix/event0 identity
  and A/S press-release events. Bare `reboot` arrived at 126.258967
  seconds, so no automatic watchdog owned the preceding >123-second session;
  the wrapper then opened/pinged the 31-second watchdog once, held fd 3, and
  logged 5/10/15/20/25/30-second countdown checkpoints. A changed boot ID and
  Gemian's watchdog-class reasons corroborate the return. F1–F10 and Page
  Up/Page Down remain unconfirmed, not failed, because the console provided no
  visible discriminator. See the r1
  [build validation](2026-07-20-keyboard-console-map-diagnostic/results/build-validation-aa-r1-20260721.txt),
  [installer validation](2026-07-20-keyboard-console-map-diagnostic/results/installer-validation-aa-r1-20260721.txt),
  [guarded write/readback](2026-07-20-keyboard-console-map-diagnostic/results/boot2-write-candidate-aa-r1-20260721.txt),
  [layout reference](2026-07-20-keyboard-console-map-diagnostic/results/layout-reference-aa-r1-20260721.txt),
  and [runtime result](2026-07-20-keyboard-console-map-diagnostic/results/runtime-candidate-aa-r1-attempt-1-20260721.txt).
- [2026-07-20 MT6797 kernel-restart diagnostic](2026-07-20-mt6797-kernel-restart-diagnostic/README.md)
  — Candidate AB passed one attended kernel-restart test. Patch 0087 closes the
  88-entry series and selects restart priority 255 for MT6797 TOPRGU so it runs
  before ARM64 PSCI priority 129; every other supported MediaTek watchdog
  variant retains priority 128. With `KBUILD_BUILD_VERSION=1` pinned, builds 3
  and 4 reproduce all 221 non-dynamic package files and modes. Independent
  container builds from those packages are recursively byte- and mode-exact at
  raw image SHA-256
  `61c74592267466735164c19f8b831ea18db2892de95e32109f2aacd7ec5c5446`;
  each passed 32/32 LK gates, deterministic reconstruction, and the shared
  suite rejected 25/25 focused mutations. The container retains the exact
  AA r1 DTB and keymap but replaces its reboot/countdown path with one forced
  BusyBox reboot request and has no userspace watchdog or automatic reboot.
  The calibrated guarded installer required exact padded AA r1, resolved
  inactive live-GPT `boot2` as `/dev/mmcblk0p30`, preserved a full backup, and
  fully read back padded AB as
  `b58c0347d34a3fd9031c74cb03447dd7a6fc630d5b8ea2b7eabc36827e754350`
  without rebooting or changing the boot ID. In attended attempt 1, retained
  pstore contains the exact AB marker, console-map gate, and `GEMINI-AB#`
  prompt, while the owner confirmed the keyboard worked. The owner waited 45
  seconds without an automatic reset or countdown and then typed bare
  `reboot`; the reset was observed immediately. Pstore places the manual
  request at 66.021584 seconds and the final kernel `reboot: Restarting system`
  line at 66.049438 seconds, 27.854 ms later; that retained interval is not an
  instrumented Enter-to-LK measurement. Gemian returned with boot ID
  `e33a0d8e-0354-4c8c-95b3-07c6970152ec`, changed from
  `0f8def4f-3f94-4c57-a34c-2bb37315b19f`. Its watchdog-class boot-reason
  fields are nondiscriminating, but the timing and absence of a userspace
  watchdog path support prompt kernel TOPRGU SWRST. This is one local
  named-unit pass, not repeatability or universal
  restart reliability. F1–F10 and Page Up/Page Down remain unconfirmed, not
  failed. See the [kernel
  reproduction](2026-07-20-mt6797-kernel-restart-diagnostic/results/kernel-reproducibility-ab-20260721.txt),
  [container validation](2026-07-20-mt6797-kernel-restart-diagnostic/results/container-validation-ab-20260721.txt),
  [installer validation](2026-07-20-mt6797-kernel-restart-diagnostic/results/installer-validation-ab-20260721.txt),
  [guarded write/readback](2026-07-20-mt6797-kernel-restart-diagnostic/results/boot2-write-candidate-ab-20260721.txt),
  and [runtime result](2026-07-20-mt6797-kernel-restart-diagnostic/results/runtime-candidate-ab-attempt-1-20260721.txt).
- [2026-07-21 USB gadget Ethernet serviceability](2026-07-21-usb-gadget-ethernet/README.md)
  — Candidate AC is an initramfs-only derivative of exact hardware-passed AB.
  It preserves AB's kernel, DTB, keymap, local console, and native reboot while
  adding bounded `usb0` discovery, static `10.15.19.82/24`, and a direct-link
  BusyBox TCP shell on port 2323 with an exact AC marker. Clean builds 3 and 4
  are recursively byte- and mode-identical at raw boot SHA-256
  `3491c119d19b7b0af2ac2342659648227182ead0e32bb4c39a66fa22cadfb39d`;
  19/19 initramfs/container mutations were rejected and 32/32 LK gates passed.
  The guarded installer required exact padded AB, preserved a full private
  backup, and fully read back logical `boot2` as padded SHA-256
  `318f418a5e67042ecdd1c98a8767c104c8cfc68c3d56cd7c0d13cb3c5fad8a84`
  without rebooting. In attended attempt 1, macOS observed the exact USB
  descriptor and fixed-MAC `en7`; carrier was active, 3/3 sourced pings passed,
  the exact AC marker and command token arrived through TCP, the UDC reported
  `configured`, and a second session passed after 250 seconds uptime. Physical
  console/keyboard confirmation and native reboot regression testing remain
  pending.
- [2026-07-21 boot-time eight-core SMP diagnostic](2026-07-21-smp8-boot-diagnostic/README.md)
  — Candidate AD is the isolated one-line kernel-policy derivative of AC:
  forced `maxcpus=1` becomes `maxcpus=8`, bringing the already proven eight
  Cortex-A53 CPUs into boot-time SMP while deliberately leaving the two
  unproven Cortex-A72 CPUs offline. Two independent kernel builds reproduce
  all non-timestamp bytes and modes; two independent containers are exactly
  identical at raw SHA-256
  `a1b61d8c34b5a447f1f672663f4e74fed6eb465b90154392a3c42f4db030826b`.
  The container preserves AC's exact initramfs, final DTB, USB service,
  keymap, console, and native reboot path and passes 32/32 LK gates. A guarded
  installer pins exact padded AC as predecessor and padded AD as
  `371fda65cf9c21406d6b08e52ffb46690426a7d356ba67aa9ffe1410e7d1e495`.
  The guarded install, full backup, flush, and 16 MiB readback passed. In one
  attended run the owner saw eight CPUs; exact USB evidence showed CPUs 0--7
  online with advancing accounting, CPU8/9 offline, expected SMP/GICv3 lines,
  no bounded fault signature, a fresh shell at 363 seconds uptime, and no
  automatic reset. The local keyboard and console remained usable. An
  authorized bare reboot over the direct USB shell then reached the native
  restart path 25.459 ms later and returned to changed-boot-ID Gemian with an
  orderly pstore record. CPU8/9 are reserved for separate watchdog-backed
  hotplug tests.
- [2026-07-21 Gemian CPU and scheduler policy](2026-07-21-gemian-cpu-scheduler-policy/README.md)
  — read-only evidence from the working Gemian `3.18.41+` kernel. Despite a
  five-CPU boot cap, its HPS logs show a three-cluster four/four/two policy
  before idle collapse to CPU0. A later active-binary/public-equivalent
  correction establishes that those are unchecked algorithm-local hotplug
  counts, not proof of an all-ten online mask. The active March 29 image is
  distinct from the installed May 24 `gbp59e00a` package, so its exact public
  commit remains unresolved. Gemian uses downstream HMP/HMP+ with HPS, PPM,
  private DVFS, and EEM—not EAS. A separate bounded sysfs capture directly
  proves one vendor CPU8 online/offline cycle; CPU9 remains unconfirmed.
- [2026-07-21 Cortex-A72 power observer](2026-07-21-cortex-a72-power-observer/README.md)
  — Candidate AE keeps the hardware-passed eight-A53 runtime and exact AD
  initramfs while adding a read-only DA9214/SPM/MCUCFG/TOPRGU resource
  observer. CPU8/9 use a kernel-authoritative rejecting PSCI method, so this
  stage issues no `CPU_ON`. Its one hardware cycle failed inconclusively: LK
  was the last visible screen, no mainline console appeared, and the device
  went directly into an automatic reboot. Empty post-return pstore cannot
  locate the post-LK boundary; do not repeat exact AE.
- [2026-07-22 Cortex-A72 observer initcall diagnostic](2026-07-22-cortex-a72-observer-initcall-diagnostic/README.md)
  — Candidate AF is an exact-AE patch/DT and exact-AD-initramfs diagnostic
  whose only resolved configuration delta blacklists the observer platform
  driver's built-in initcall. It distinguishes observer registration/probe
  from the retained I2C6/DA9214 and eight-Cortex-A53 foundation without
  requesting either Cortex-A72 CPU. Two independent kernel packages and two
  17-member containers reproduce exactly at raw SHA-256
  `fe43efa8c9d18174fec97ab7ad6cbe59bbc490df92366bcd254c55daa932d0a3`;
  guarded installation and readback passed, but its first selected cycle was
  inconclusive: the panel became uniformly grey with no text, exact USB was
  not armed, the owner forced a return, and pstore was empty. A static audit
  then proved that AF's final DT had dropped AD's hardware-passed simplefb
  artifact transform. Do not repeat exact AF.
- [2026-07-22 simplefb observation restoration](2026-07-22-simplefb-observation-restoration/README.md)
  — Candidate AG is an artifact/DT-only derivative of exact AF. It restores
  only hardware-passed AD's `/chosen` address/size/ranges contract and exact
  1080×2160 `simple-framebuffer` node with its two path-resolved clocks; every
  kernel, config, initramfs, helper, command-line, CPU-isolation, and other DT
  semantic remains AF. It deliberately adds neither a static copy of LK's
  runtime framebuffer reservation nor a raw framebuffer write. Two independent
  recovery-VM constructions are byte- and mode-identical across 18 members at
  raw SHA-256
  `0552986c885d89fd65d05f3da8513040f756c9cfc84b1b30e1e085ee68238a91`;
  the exact DT transform is
  `7ea5e8f9edb09f2365a112b29359fed897f306422a26449b1cb8870bb1212512`,
  and all 24 focused invalid DT mutations were rejected. A guarded operation
  preserved exact AF, wrote only live-resolved logical `boot2`, then matched
  post-flush, 16 MiB local readback, and independent remote SHA-256
  `63e0b3178072b2945a3537e17fda8c50ebce8032ca00110185993b4e2b7b1e14`
  without rebooting or selecting a boot entry. The owner later confirmed one
  `boot2` selection, a grey console screen with no text, and a forced return;
  no automatic candidate reboot was observed. The cycle returned to known-good
  Gemian without an exact AG USB identity or any AG kernel, initramfs, panic,
  or pretimeout marker in pstore. Selection is now established, but the
  pre-console/pre-USB stall boundary is not; do not repeat unchanged AG.
- [2026-07-22 AD-contract/AF-kernel split](2026-07-22-ad-contract-af-kernel-split/README.md)
  — Candidate AH corrects the broader packaging boundary found after AG: AG
  restored simplefb but still disabled AD's hardware-passed USB and keyboard
  paths and omitted other artifact transforms. AH pairs AF's exact kernel,
  config, `System.map`, initramfs and helpers with AD's complete final DT,
  changing only CPU8/9 from generic PSCI to AF's rejecting method. Two
  independent recovery-VM constructions are byte- and mode-identical across
  18 members. Raw SHA-256 is
  `e5ba6ee0a257b804a02af11b83e733f861b89de17470470a497f07056b6b3197`;
  padded 16 MiB SHA-256 is
  `f107a3e7483c02cb4b2540d185ef2a5fb1f77e4a0acc7b66fce16e37641f5012`;
  all 22 DT and 12 Android/component mutations were rejected. A guarded
  live-GPT operation backed up exact AG, wrote AH once to inactive logical
  `boot2`, synchronized and flushed it, and matched the complete 16 MiB
  readback. The installer did not reboot or select a slot. Attempt 1 returned
  to Gemian after only 24 seconds without exposing the exact AH USB MAC; its
  exact-MAC collector consequently ran zero times. Changed-cycle pstore
  contains the preceding orderly Gemian shutdown but no AH/Linux-7.1.3/
  initramfs identity, panic, fault, or pretimeout. The owner confirmed selecting
  `boot2`, seeing a grey console screen with no text, and forcing the return.
  Attempt 1 remains inconclusive and must not be reinterpreted as kernel or A72
  evidence. A later owner-selected attempt 2 on the unchanged, still-exact AH
  image added the decision-changing observation that attempt 1 lacked. The
  exact-MAC USB collector completed and validated AH's installed hash, AF
  kernel/config/cmdline, AD initramfs and DT contracts, loader-retained
  simplefb, sole USB shell, and bound AW9523/keymap path. The owner observed a
  working console; no physical key was exercised or reported in this run.
  `possible`/`present` stayed `0-9`, CPU0–7 stayed online with advancing
  accounting, and CPU8/9 stayed offline and unrequested. No observer, I2C6, or
  DA9214 device appeared, no fault occurred, and no automatic countdown or
  userspace-watchdog reset occurred. A single bare `reboot` request produced
  retained native-kernel shutdown and `reboot: Restarting system` lines 26.273
  ms apart before Gemian returned under a changed boot ID. A read-only
  post-cycle check again matched the complete logical-`boot2` SHA-256
  `f107a3e7483c02cb4b2540d185ef2a5fb1f77e4a0acc7b66fce16e37641f5012`.
  Attempt 2 is therefore a named-unit PASS for AH's eight-A53 console, USB,
  and native-reboot baseline only. It neither exercises the CPU8/9 reject
  callback nor establishes Cortex-A72 support. See the
  [attempt-2 runtime result](2026-07-22-ad-contract-af-kernel-split/results/runtime-candidate-ah-attempt-2-20260722.txt).
- [2026-07-22 corrected A72 reject-gate kernel split](2026-07-22-a72-reject-gate-kernel-split/README.md)
  — Candidate AI is a local diagnostic that isolates the
  corrected MT6797 A72 PSCI reject gate from AF's regulator, reset, observer,
  and initcall changes. Its selected kernel series is exact Candidate AD
  through patch 0087 plus corrected patch 0092 only; its resolved config stays
  byte-exact AD, CPU8/9 are not requested, and its final DT is byte-exact AH.
  Fail-closed host gates cover series/package lineage, full two-package
  substantive reproduction, bounded compiled disassembly and call/control-flow
  audits for both the `-EAGAIN` boot gate and constant-false disable gate,
  deterministic Android-v0 artifact finalization/reproduction, and exact live
  USB attribution despite the inherited AC userspace banner. Two independent
  package trees now reproduce all 225 substantive files and modes plus
  normalized provenance. Their common SHA-256 values are `Image`
  `fb2c02601a07b49781b97ef9d39b79218db1c158ce1547a2ea53df7fb1e51fe2`,
  `Image.gz`
  `b87984a570567ef47f151024612889f7d5d49b938c10bd08f0aecfea47b481a9`,
  `System.map`
  `622945b38e025db7ee7719f2fa3132e17f8ad0158651e2f77e57918a76ac384d`,
  resolved config
  `32dd13a6704e5fa591236ba114d43e8e7e1aeb3eb123d9d4f124b5f551301d46`,
  packaged Gemini DTB
  `510669e70cd39df3c0e1a1b4c806c0eeaa8e0b0fe02e037ee1bf405d39498af8`,
  and compiled audit
  `67519ff0a82376e2d0628f7061af474b0df6427c0f54878717a6c6b1d672a525`.
  Two independent 20-member Android-v0 artifact trees are byte- and mode-exact,
  with raw SHA-256
  `1ecfc787fec2f5dc11c5b7d30eb4f11d34b0496e57daf42adea567f010282309`
  and manifest SHA-256
  `b8c2953dd07e2a84a05e99f7bd0a981cbe593e928ba7507f16691279d82fa8cc`.
  Two ephemeral 16 MiB padding checks independently verified the all-zero tail
  and SHA-256
  `8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86`;
  both temporary padded files were removed and unpublished. Installer
  validation, guarded installation, and a matching full `boot2` readback
  passed. Exact AI attempt 1 then completed the eight-A53 baseline: the owner
  confirmed the readable console, exact USB attribution showed CPU0–7 online
  with advancing accounting and CPU8/9 offline and unrequested, native reboot
  returned to changed-boot-ID Gemian, and the post-cycle full `boot2` hash
  still matched AI. Patch 0092 remains local-diagnostic and not
  submission-ready. AI requested neither A72, so it established no reject or
  power-path execution.
- [2026-07-22 fail-closed CPU8 request](2026-07-22-a72-reject-cpu8-request/README.md)
  — Candidate AJ is an offline-reproduced, configuration-only derivative of
  exact Candidate AI. It changes only the forced command line from
  `maxcpus=8` to `maxcpus=9`, causing serialized bring-up to visit logical
  CPU8 once while stopping before CPU9. Its predeclared oracle requires one
  exact gate warning and one `CPU8: failed to boot: -11`, continued operation
  of CPU0–7, and no CPU9 request or Cortex-A72 secondary-boot line. The profile,
  configuration inputs, and resolved configuration are statically pinned.
  Two independent 226-member packages, two independent 20-member Android-v0
  assemblies, and two independent zero-padding constructions reproduce. The
  exact raw SHA-256 is
  `a3c649b5ca7a9ac07e290ca9a8838f0a3be33ab9e39554c4bafe50c98d18e2a8`;
  the exact padded 16 MiB SHA-256 is
  `8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257`.
  Guarded installation over exact AI passed with a matching full 16 MiB
  readback and no reboot or slot selection. A first owner console report of the
  inherited `AB` label and eight processors was rejected as an identity
  mismatch: the installed target never left its original Gemian boot, and no
  exact AJ USB interface or runtime appeared. Attempt 2 then passed the exact
  USB/CPU runtime subgate over a 45-plus-5-second window: CPU0–7 advanced,
  exactly one `CPU8 boot rejected: A72 power sequence inactive` and one
  `CPU8: failed to boot: -11` occurred before generic PSCI `CPU_ON`, CPU9 was
  absent, and no other bounded fault signature appeared. One native BusyBox
  reboot request closed the exact USB endpoint; Gemian returned under a changed
  boot-ID, retained pstore ended in watchdog shutdown and
  `reboot: Restarting system`, and one full read-only post-return `boot2` hash
  still matched exact AJ. That pstore collection is deliberately a raw,
  unpaired post-return snapshot (`wait_for_cycle=no`), not paired-cycle
  evidence. AJ remains `PARTIAL` solely because explicit owner confirmation of
  a readable local console during attempt 2 is pending. See the
  [attempt-2 result](2026-07-22-a72-reject-cpu8-request/results/hardware-attempt-2-runtime-reboot-return-20260722.txt).
  A separate [predecessor-gate adjudication](2026-07-22-a72-reject-cpu8-request/results/ak-predecessor-gate-adjudication-20260722.txt)
  preserves that partial status but accepts the exact compound chain as
  sufficient for AK build and guarded installation.
- [2026-07-22 A72 firmware and power contract](2026-07-22-a72-firmware-power-contract/README.md)
  — an offline, read-only audit separates Linux-owned external preparation
  (DA9214 BUCKB, temporary TOPRGU PWRAP reset, MP2 reset release, external-buck
  isolation, SRAM-LDO request, and post-success DCM) from secure-firmware-owned
  initial B PLL/mux/divider, cluster/core MTCMOS/reset, internal bus protection,
  and CCI coherency admission. The captured SRAM-LDO service returns zero
  unconditionally, so independent readback is required. No safe inverse/off
  sequence is established; once external isolation is cleared, failures must
  retain power, fault the provider, and reject retry. Draft patch 0093 remains
  unsafe and unselected. Both live TEE slots now match the exact analyzed
  payload. Offline reconciliation separates the active March 29 boot image
  from the May 24 `gbp59e00a` installed package. The active exact public commit
  remains unresolved; `59e00a` is the chosen equivalent for verified
  owner-safe observer-hook blobs, not exact active provenance. No synchronized
  live register-state capture is claimed yet.
- [2026-07-23 Gemian A72 load-assisted observation](2026-07-23-gemian-a72-load-assisted-observation/README.md)
  — a reviewed bounded load probe used no explicit CPU-online or policy writes.
  One worker did not expose A72; with two workers, direct stable reads observed
  CPU8 online 1.11 seconds after stage start while both workers bracketed the
  sample, followed immediately by an online-to-offline CPU8 bracket. CPU9
  remained offline, all policy/power/temperature/cleanup/same-boot gates
  passed, and no load process remained. This calibrates a two-worker temporal
  trigger but does not prove causality or minimum load. The companion
  sequential observer missed the short transition, so Candidate AM—the first
  active mainline CPU8 experiment—remains blocked on an owner-local in-kernel
  transaction capture from the chosen public equivalent. Candidate AL is the
  separate mainline I2C6/DA9214 resource-only predecessor and requests neither
  A72.
- [2026-07-23 DA9214 resource-only Candidate AL](2026-07-23-da9214-resource-only/README.md)
  — two byte-identical Linux 7.1.3 assemblies and a guarded full-readback
  `boot2` install preceded one exact runtime. I2C6 bound to `i2c-mt65xx`, its
  dynamically numbered adapter and exact `0x68` client appeared, and the
  inherited eight-A53, keyboard, USB and native-reboot path survived. The
  upstream DA9211-family probe read unsupported device ID `0x0`, returned
  `ENODEV`, left the client unbound, and registered neither regulator. The
  focused evidence reported no timeout/NACK. Native reboot returned to
  changed-identity Gemian and the post-return full `boot2` hash remained exact;
  pstore is explicitly an unpaired post-return capture. Result: `FAIL`; do not
  repeat unchanged AL or request an A72 until the identity/page/protocol,
  timing, reset/prerequisite, or driver-family mismatch is isolated.
- [2026-07-24 MT6797 DVFSP handoff observer Candidate AN](2026-07-24-mt6797-dvfsp-handoff-observer/README.md)
  — two clean Linux 7.1.3 packages and two Android-v0 artifacts reproduced,
  followed by a guarded full-readback `boot2` install and one accepted
  read-only runtime. Candidate AN booted with CPU0–7 advancing, CPU8/9
  offline, USB available, and I2C6 disabled. Three CSPM snapshots had identical
  measured register payloads and were reset-like, but the shared I2C_APPM clock
  was ungated, so both the kernel and independent classifier returned
  `unknown`. A private whole-FDT
  comparison accepted exactly the expected LK handoff fixups. The result does
  not authorize DA9214 access. Its then-next vendor pause/stop/arbitration
  analysis is historical and superseded by the recovery immediately below.
  A one-time latched gate remains insufficient.
- [2026-07-24 MT6797 DVFSP/I2C6 arbitration recovery](2026-07-24-mt6797-dvfsp-i2c6-arbitration/README.md)
  — direct read-only analysis of the exact active Gemian ELF, reconciled
  against pinned explanatory GPL blobs, establishes that vendor stop is a
  reversible PCM reset, not an ownership
  latch. `SEMA_I2C_DRV` is not a hardware semaphore: I2C6 pauses DVFSP around
  each physical transaction while the controller holds its own reference to
  the shared I2C_APPM clock. The active binary has two acquire call sites
  (one retry), one release, and matching release coverage after every
  successful acquire; its timeout and unpause failures are deliberately fatal
  and must not be copied. Exact LK/TEE/SCP follow-up found no direct PCM
  restart writer; ATF remains a keyed CSPM/semaphore writer and SCP local
  aliases remain uncertain. Keep I2C6 disabled while a one-way handoff owner
  with post-transition and resume state validation is reviewed.
- [2026-07-24 MT6797 DVFSP one-way handoff Candidate AO](2026-07-24-mt6797-dvfsp-one-way-handoff/README.md)
  — two clean Linux 7.1.3 packages and two complete Android-v0 artifacts
  reproduced with exact live-root/output/DTB linkage. The source-pinned
  16 MiB image was installed from known-good Gemian to live-GPT logical
  `boot2` after verifying the exact Candidate AN predecessor, preserving a
  private full backup, and obtaining matching remote and independent local
  full-partition readbacks. The built-in owner permits at most one balanced
  CCF reference transition from Candidate AN's exact stopped/ungated
  signature, faults closed on every mismatch, rechecks state after 45 seconds,
  and retains I2C6 disabled with no DA9214 or A72-power node. Exact AO then
  booted from `boot2` and passed its predeclared oracle: all six samples kept
  the stopped PCM signature; the gate was open through the held CCF reference,
  closed immediately after one balanced disable, and remained closed at the
  45-second check. Counters were exactly one attempt/enable/disable/late check
  with zero faults. CPU0–7 advanced, CPU8/9 remained offline and unrequested,
  and inherited console, keymap, USB and reboot-dispatch checks passed without
  I2C6, DA9214, A72-power, watchdog-owner, or reboot activity. A 52,567-byte
  private post-LK FDT passed the exact 37-entry allowlist. Result: narrow
  named-unit `PASS`; the separate AP consumer outcome follows below.
- [2026-07-24 MT6797 DVFSP-gated childless I2C6 Candidate AP](2026-07-24-mt6797-dvfsp-i2c6-consumer/README.md)
  — two main packages and artifacts reproduced, while the separate PM-audit
  package compiled/linked but was rejected by assembly and never installed or
  booted. Exact AP was installed and fully read back from live-GPT logical
  `boot2`. Its 52,655-byte post-LK FDT passed the exact 37-entry allowlist.
  Runtime reached AO's 45-second `ready` state and one supplier grant, but
  ended in a structured `FAIL`: I2C_APPM regated in every one of 32 cleanup
  samples while shared AP_DMA remained valid and ungated in every sample. The
  provider faulted closed, I2C6 returned `-EIO` before binding an adapter, and
  no transfer, client, regulator, DA9214, A72, or suspend/resume operation
  occurred. CPU0–7, the keyboard driver/keymap checks, USB, and native reboot
  survived; no physical key was exercised. Changed-ID Gemian returned and one
  full read-only `boot2` hash still matched AP. The
  45-second provider probe also delayed `/init` until 48.143 seconds and tty1
  readiness until 48.266 seconds. Do not repeat AP unchanged; identify the
  existing AP_DMA owner and design a baseline-preserving cleanup oracle first.
- [2026-07-24 MT6797 AP_DMA clock ownership observer Candidate AQ](2026-07-24-mt6797-ap-dma-owner-observer/README.md)
  — keeps the exact AO DT with I2C6 disabled and adds only `CONFIG_DEBUG_FS`
  plus a read-only initramfs observer. It records early and five-second
  `clk_summary` snapshots for AP_DMA, I2C_APPM, UART0, I2C5 and I2C6. AQ was
  built, checked, and installed to inactive logical `boot2` with matching full
  remote/local readbacks. The owner reported a readable console after manual
  slot selection, and the direct USB shell captured complete byte-identical
  early/late summaries. AP_DMA is enabled with refcount 2 and owner
  `1101c000.i2c` (`dma`), while I2C_APPM is disabled and owned by the DVFSP
  handoff provider. This passes the observer gate and identifies the surviving
  reference as the enabled I2C5 DMA path; do not repeat AQ unchanged. Preserve
  that reference and add a baseline-preserving I2C_APPM cleanup oracle before
  another I2C6 experiment. See the [runtime result](2026-07-24-mt6797-ap-dma-owner-observer/results/runtime-candidate-aq-attempt-1-20260725.txt).
- [2026-07-22 fail-closed CPU9 request](2026-07-22-a72-reject-cpu9-request/README.md)
  — Candidate AK uses exact Candidate AJ as its safety predecessor and changes
  only forced `maxcpus=9` to `maxcpus=10`. Exact AK attempt 1 passed the ordered
  CPU8/CPU9 rejection control: CPU0–7 advanced, both A72 requests reached the
  pre-PSCI gate and returned `-11`, neither A72 came online, and no other fault
  signature appeared. The owner attested that the console was readable. Native
  reboot returned to changed-boot-ID Gemian and the post-return full `boot2`
  hash still matched AK; the evidence chain remains unpaired. This establishes
  rejection dispatch only, not Cortex-A72 power or scheduling support.
- [2026-07-14 live vendor-to-mainline gap audit](2026-07-14-live-vendor-mainline-gap-audit/README.md)
  — read-only comparison of the live Gemian vendor contracts with the current
  Linux 7.1.3 handoff and first-boot boundaries.
- [2026-07-14 upstream MT6797 coverage audit](2026-07-14-upstream-mt6797-coverage-audit/README.md)
  — source-level reuse/new-driver census, MT6797 I2C fallback validation, and
  the SPI controller boundary through the existing `mt6765_compat` profile;
  patches 0072–0073 and their validated disabled-node package are recorded in
  the SPI patch-validation result.
- [2026-07-13 camera recovery](2026-07-13-camera-recovery/README.md)
  — runtime SP5509 camera identity, bounded vendor-ELF chip-ID/I2C recovery,
  MT6797 SENINF/ISP resource boundary, and the new-sensor-driver versus
  existing-mainline-driver decision.
- [2026-07-13 external-display recovery](2026-07-13-external-display-recovery/README.md)
  — unbound SII9022/EDID candidates, SII9024A-named vendor wiring, and the
  Linux 7.1.3 `sii902x` bridge reuse boundary.
- [2026-07-13 memory carve-out recovery](2026-07-13-memory-carveout-recovery/README.md)
  — discontiguous DRAM, fixed firmware reservations, dynamic CONSYS/SCP-share/
  SPM ownership, and the Linux 7.1.3 DT boundary.
- [2026-07-13 modem/CCCI recovery](2026-07-13-modem-ccci-recovery/README.md)
  — live MD1 and MD3/C2K CCCI/CLDMA topology, shared-memory/EMI ownership,
  and the new MT6797 transport versus reusable WWAN/TTY boundary.
- [2026-07-13 UART/console recovery](2026-07-13-uart-console-recovery/README.md)
  — live `ttyMT0`–`ttyMT3`, vendor AP-DMA/console behavior, Linux 8250 reuse,
  and the LK command-line naming boundary.
- [2026-07-13 kernel integration](2026-07-13-kernel-integration/README.md)
  — reproducible Linux 7.1.3 preparation, configuration, 57-patch compilation,
  artifact packaging, and checksum/provenance verification.

## Layout

Create a directory named with the start date and a short subject:

```text
experiments/2026-07-11-uart-identification/
  README.md
  scripts/       collection, decoding, and analysis helpers
  src/           purpose-built probe or test source
  fixtures/      small redistributable inputs needed for tests
  results/       small sanitized logs, tables, or summaries
```

Copy `experiments/TEMPLATE.md` to the new directory as `README.md`. Omit unused
subdirectories. Code must state its dependencies and default to read-only or
dry-run behavior. A command that can modify hardware must require an explicit
target and opt-in flag.

## Evidence policy

- Keep raw private captures outside Git. Commit only the smallest sanitized
  evidence needed to support the result.
- Redact serial numbers, IMEI values, identifying MAC addresses, keys,
  credentials, calibration blobs, and user data.
- Do not commit firmware, partition images, NVRAM, proprietary source or
  documents, or artifacts without verified redistribution rights.
- Hash externally retained evidence when its identity matters, but do not
  publish a hash if it could identify a person or device.
- Record failures, negative results, and ambiguity. They prevent repeated unsafe
  work and are valid outcomes.

When an experiment establishes a durable fact, summarize it in
`docs/hardware/` and link back to the experiment. When it changes runtime support,
update `docs/HARDWARE_SUPPORT.md` with the exact evidence. When it produces a
kernel change, export the logical commit into `patches/` and link all three.
