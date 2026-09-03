# Mainline A72 physical-hotplug lifecycle gate

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-02-mainline-a72-hotplug-lifecycle-gate` |
| Status | One exact transaction booted CPU8/CPU9, offlined and restored CPU9 with CPU8 retained, returned success at stage 18, and left CPUs 0--9 online; repeatability and broader stability remain open |
| Subsystem | arm64 CPU hotplug, PSCI, MT6797 A72 membership |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-09-02--2026-09-03 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 8, A72 lifecycle correctness |

## Question or hypothesis

Can current mainline physically offline CPU9 while retaining CPU8, CPUs 0--7,
and USB serviceability, then restore CPU9 in the same boot through a separately
owned transaction without retrying an unbounded secure call or entering the
last-A72 power-down branch?

## Provenance and environment

- Repository parent: `0dc07a6bc46da6bb1b074ffee4ce5efd26908411`.
- Canonical series: 474 entries, SHA-256
  `3f55b6be379d540d947c68deb74966b2a7f0ae05819305841f1a077c33da4610`.
- Manifest SHA-256:
  `af9331a6d97a73475243dc1f79df6ca70206d3daf69405c20e9145e7c9930b43`.
- Exact prepared-source file identities are in
  [`contract.json`](contract.json).
- Runtime parent: accepted exact 4+4+2 topology/RAM and concurrent dual-A72
  execution on the named device.
- Build backend for future kernel work: Buildbox only.
- Physical-candidate commit: `43349a53fda1ab1c7389ac0e6da2e89d131177bc`.
- Physical-candidate release: `7.1.3-gemini-a72-hotplug-physical`.
- Configuration-repair build commit:
  `69b7494c211bef04d61cb5869f2ff9fb497799c2`.
- Repaired successor `boot2` identity: `58313c3a8...`.
- Boot path and target: one guarded write to inactive logical `boot2`; no
  device action had occurred when the candidate record below was published.
- Repaired deployment: exact `58313c3a8...` on `/dev/mmcblk0p30`, followed by
  full independent readback and confirmed clean shutdown.

## Safety assessment

This phase is read-only with respect to the device and kernel source. It
defines no boot candidate and performs no CPU, PSCI, MMIO, watchdog,
retained-RAM, partition, or reboot operation.

The selected eventual physical action is CPU9-off with CPU8 retained. CPU8 as
the last A72, CPUs 0--7, primary boot, and every shared power-policy change are
forbidden. The secure affinity call is explicitly recorded as internally
unbounded; the physical candidate cannot proceed until the independent
watchdog, immutable pre-CPU_OFF attribution, one-query rule, reset-only fault
handling, and exact restore token are implemented and machine-checked.

## Associated code

- [`DESIGN.md`](DESIGN.md) fixes the end state, lifecycle ownership, failure
  boundary, and phase order.
- [`PHYSICAL_EXECUTOR.md`](PHYSICAL_EXECUTOR.md) freezes the split physical
  executor, corrects the inherited one-shot watchdog disposition, and defines
  the independent CPU9-off/shared-state predicate.
- [`PHYSICAL_BINDER.md`](PHYSICAL_BINDER.md) freezes the production binding,
  retained record 4, watchdog validation, bounded CPU8 callback, automatic
  down/restore orchestration, and distinct restore routing.
- [`contract.json`](contract.json) is the machine-readable gate.
- [`physical-executor-contract.json`](physical-executor-contract.json) is the
  hardware-free contract for the next implementation slice.
- [`physical-binder-contract.json`](physical-binder-contract.json) is the
  hardware-free contract for the final binding and restore slices.
- [`physical-binder-implementation-contract.json`](physical-binder-implementation-contract.json)
  preserves that frozen contract while pinning the exact post-`0496` source
  and composition boundary for the one-task binder.
- [`scripts/validate_contract.py`](scripts/validate_contract.py) validates the
  contract and optionally the exact prepared source.
- [`scripts/test_contract.py`](scripts/test_contract.py) requires critical
  unsafe mutations to fail closed.
- `scripts/source_edits.py`, `validate_source.py`, and
  `test_source_validator.py` define and reject mutations of the first generic
  handoff slice.
- `scripts/generate_patch.py` and `generate-on-buildbox` create a normal
  format-patch from the exact managed source without changing it.
- `scripts/owner_source_edits.py`, `owner_test_edits.py`,
  `validate_owner_source.py`, and `test_owner_source_validator.py` define the
  second hardware-free owner slice and its rejecting source oracle.
- `scripts/owner_terminal_parent_fix_edits.py` and
  `test_owner_terminal_parent_validator.py` define the follow-up correction
  and six rejecting mutations for the finalized CPU8/CPU9 parent pair.
- `scripts/generate_owner_patches.py` and `generate-owner-on-buildbox` create
  the exact owner/test pair plus its follow-up correction from the canonical
  prepared source through `0485`, while proving the first two patch identities
  remain unchanged.
- `scripts/physical_executor_source_edits.py`,
  `physical_executor_test_edits.py`, `validate_physical_executor_source.py`,
  and `test_physical_executor_source_validator.py` define the disconnected
  physical executor, its eight memory-only tests, and 18 rejecting mutations.
- `scripts/intersected_status_source_edits.py`,
  `validate_intersected_status_source.py`, and
  `test_intersected_status_source.py` define the evidence-selected CPU9-off
  intersection repair while preserving the raw bitmap and rejecting ten
  unsafe source mutations.
- `scripts/generate_intersected_status_patch.py` and
  `generate-intersected-status-on-buildbox` generate the exact one-patch
  repair from the hash-pinned prepared source through `0504`.
- `scripts/generate_physical_executor_patches.py` and
  `generate-physical-executor-on-buildbox` generate its exact two-patch review
  from the canonical prepared source through `0486`.
- `scripts/run-physical-executor-kunit-qemu` and
  `scripts/classify-physical-executor-kunit.py` admit only the exact isolated
  Buildbox package and require all eight executor cases to pass without a
  production binder or network device.
- `scripts/validate_physical_binder_contract.py` and
  `scripts/test_physical_binder_contract.py` pin the audited source boundary
  and reject unsafe entry, attribution, observation, PSCI, callback, restore,
  and candidate changes.
- `scripts/validate_physical_binder_implementation_contract.py` and
  `scripts/test_physical_binder_implementation_contract.py` pin 26 current
  source files and reject 43 unsafe orchestration and enablement mutations.
- `scripts/watchdog_validator_source_edits.py`,
  `validate_watchdog_validator_source.py`, and
  `test_watchdog_validator_source.py` define the read-only recovery-owner
  validator and reject 12 source mutations.
- `scripts/generate_watchdog_validator_patch.py` and
  `generate-watchdog-validator-on-buildbox` generate the exact disconnected
  watchdog prerequisite from the canonical prepared source.
- `scripts/run-watchdog-validator-kunit-qemu` and
  `classify-watchdog-validator-kunit.py` require the exact isolated Buildbox
  package and seven-case no-network runtime proof.
- `scripts/generate-parent-proof-on-buildbox`,
  `generate_parent_proof_patches.py`, `parent_proof_source_edits.py`,
  `validate_parent_proof_source.py`, and `test_parent_proof_source.py`
  generate and validate the disconnected exact membership/binder parent proof
  while rejecting 20 unsafe source mutations.
- `scripts/run-parent-proof-kunit-qemu` and
  `classify-parent-proof-kunit.py` admit only the exact ancestor Buildbox
  package and require all 62 owner, transition, and binder cases to pass.
- `scripts/hotplug_ledger_source_edits.py`,
  `validate_hotplug_ledger_source.py`, and
  `test_hotplug_ledger_source.py` define the dedicated record-4 ledger and
  reject 20 source mutations while keeping every production caller absent.
- `scripts/generate_hotplug_ledger_patch.py` and
  `generate-hotplug-ledger-on-buildbox` generate the exact ledger patch from
  the canonical prepared source.
- `scripts/decode-hotplug-ledger.py` is the strict changed-boot-ID host
  decoder; `test-hotplug-ledger-decoder.py` covers ten accepted and rejected
  payload classes without modifying the retained source.
- `scripts/run-hotplug-ledger-kunit-qemu` and
  `classify-hotplug-ledger-kunit.py` admit only the exact ancestor Buildbox
  package and require all 13 in-memory record-4 cases to pass.
- `scripts/ledger_terminal_source_edits.py`,
  `validate_ledger_terminal_source.py`, and
  `test_ledger_terminal_source.py` repair and prove the three exact terminal
  boundaries needed by the production binder while rejecting 18 unsafe
  mutations.
- `scripts/generate_ledger_terminal_patch.py` and
  `generate-ledger-terminal-on-buildbox` generate the exact one-patch repair
  from the hash-pinned prepared source through `0498`.
- `scripts/ledger_checkpoint_context_source_edits.py`,
  `validate_ledger_checkpoint_context_source.py`, and
  `test_ledger_checkpoint_context_source.py` make record-4 publication safe in
  the non-sleeping target callback and reject ten unsafe source mutations.
- `scripts/generate_ledger_checkpoint_context_patch.py` and
  `generate-ledger-checkpoint-context-on-buildbox` generate that exact
  one-patch repair from the hash-pinned source through `0499`.
- `scripts/hotplug_snapshot_source_edits.py`,
  `validate_hotplug_snapshot_source.py`, and
  `test_hotplug_snapshot_source.py` define the disconnected four-source
  adapter and reject 20 source mutations while keeping all callers absent.
- `scripts/generate_hotplug_snapshot_patch.py` and
  `generate-hotplug-snapshot-on-buildbox` generate the exact adapter patch
  from the canonical prepared source through `0492`.
- `scripts/run-hotplug-snapshot-kunit-qemu` and
  `classify-hotplug-snapshot-kunit.py` admit only the exact ancestor Buildbox
  package and require all six injected-source cases to pass.
- `scripts/cpu8_observer_source_edits.py`,
  `validate_cpu8_observer_source.py`, and
  `test_cpu8_observer_source.py` define the one-shot asynchronous CPU8
  observer and reject 21 unsafe source mutations while keeping it disconnected.
- `scripts/generate_cpu8_observer_patch.py` and
  `generate-cpu8-observer-on-buildbox` reconstruct its exact pre-`0494`
  parent from the pinned prepared source and generate the canonical patch.
- `scripts/run-cpu8-observer-kunit-qemu` and
  `classify-cpu8-observer-kunit.py` admit only the exact ancestor Buildbox
  package and require all seven observer cases to pass.
- `scripts/restore_executor_source_edits.py`,
  `restore_executor_test_edits.py`, `validate_restore_executor_source.py`, and
  `test_restore_executor_source.py` define the disconnected CPU9 restore
  executor and reject 32 unsafe source mutations.
- `scripts/generate_restore_executor_patches.py` and
  `generate-restore-executor-on-buildbox` generate the exact restore/test pair
  from the hash-pinned source through `0494`.
- `scripts/run-restore-executor-kunit-qemu` and
  `classify-restore-executor-kunit.py` admit only the exact ancestor Buildbox
  package and require all ten restore cases to pass with no network device.
- `scripts/binder_core_source_edits.py`, `binder_core_test_edits.py`,
  `validate_binder_core_source.py`, and `test_binder_core_source.py` define the
  disconnected same-task binder core and reject 22 unsafe source mutations.
- `scripts/generate_binder_core_patches.py` and
  `generate-binder-core-on-buildbox` generate its exact source/test pair from
  the hash-pinned source through `0496`.
- `scripts/run-binder-core-kunit-qemu` and
  `classify-binder-core-kunit.py` admit only the exact ancestor Buildbox
  package and require all nine binder cases to pass with no network device.
- `scripts/hotplug_binding_source_edits.py`,
  `hotplug_binding_test_edits.py`, `validate_hotplug_binding_source.py`, and
  `test_hotplug_binding_source.py` define the production composition and
  reject 28 unsafe entry, gate, callback, call-budget, and enablement
  mutations.
- `scripts/generate_hotplug_binding_patches.py` and
  `generate-hotplug-binding-on-buildbox` reconstruct and hash-check the exact
  28-interface post-`0500` parent before generating the binding/test pair.
- `scripts/run-hotplug-binding-kunit-qemu` and
  `classify-hotplug-binding-kunit.py` admit only the exact isolated Buildbox
  package and require all nine private-transition and route cases to pass with
  no network device.
- `scripts/build-physical-composed-dtb.py`,
  `validate-physical-composed-dtb.py`, and
  `test-physical-dtb-mutations.py` source-pin the accepted serviceability DT,
  add only the exact current package provenance leaf, and reject ten mutations.
- `scripts/build-physical-candidate.sh` and
  `validate-physical-candidate.py` independently check the exact production
  package, Android-v0/LK container, configuration, and six container mutations.
- `scripts/install-physical-boot2.sh` source-pins the live-GPT installer,
  records but does not back up the predecessor, performs a full readback, and
  shuts the device down after success.
- `scripts/validate-config-identity-repair.py` and
  `test-config-identity-repair.py` bind the physical profile only to its exact
  package configuration-input identity and reject five scope/identity
  mutations while preserving the predecessor production identity.
- `scripts/remote-physical-pretrigger.sh`,
  `validate-physical-pretrigger.py`, and `test-physical-pretrigger.py` require
  the repaired release and A41 identity, a changed boot ID, read-only sysfs,
  pristine zero-execution state, and the sole arm64 READY line while rejecting
  every proof-mask veto before a trigger can be issued.
- [`results/contract-validation-20260902.txt`](results/contract-validation-20260902.txt)
  records the local contract/mutation pass and exact Buildbox prepared-source
  validation.
- [`results/generic-down-handoff-generation-aa014ea0-20260902.txt`](results/generic-down-handoff-generation-aa014ea0-20260902.txt)
  pins the generated patch, strict review, replay, mutation, and all-profile
  invariant results.
- [`results/generic-down-handoff-build-1f17299f-20260902.txt`](results/generic-down-handoff-build-1f17299f-20260902.txt)
  pins the exact pushed Buildbox compile, validated package identities, and
  linked handoff symbols.
- [`results/hardware-free-owner-generation-d266765e-20260902.txt`](results/hardware-free-owner-generation-d266765e-20260902.txt)
  pins the exact generated owner/test patches, independent review correction,
  strict review, replay, mutation, and all-profile invariant results.
- [`results/hardware-free-owner-kunit-attempt-1-20260902.txt`](results/hardware-free-owner-kunit-attempt-1-20260902.txt)
  records the first no-network QEMU run, its 56 passes and four attributable
  failures, and the common terminal-parent predicate defect.
- [`results/hardware-free-owner-terminal-parent-generation-9a9f0455-20260903.txt`](results/hardware-free-owner-terminal-parent-generation-9a9f0455-20260903.txt)
  pins the exact follow-up generation, preserved predecessor identities,
  strict review, replay, 27 total rejecting mutations, and profile invariant.
- [`results/hardware-free-owner-kunit-attempt-2-20260903.txt`](results/hardware-free-owner-kunit-attempt-2-20260903.txt)
  records the corrected Buildbox package and complete 60-of-60 no-network QEMU
  pass with every physical and production path still disconnected.
- [`results/hardware-free-physical-executor-generation-be8f55a1-20260903.txt`](results/hardware-free-physical-executor-generation-be8f55a1-20260903.txt)
  records the exact Buildbox generation, replay, eight focused cases, 18
  rejecting source mutations, admitted patch identities, and profile audit.
- [`results/hardware-free-physical-executor-kunit-e24e6c45-20260903.txt`](results/hardware-free-physical-executor-kunit-e24e6c45-20260903.txt)
  records the exact Buildbox compile/package identities and complete 8-of-8
  no-network QEMU pass with every production and physical path disconnected.
- [`results/physical-binder-contract-aa03bb01-20260903.txt`](results/physical-binder-contract-aa03bb01-20260903.txt)
  pins the contract identities, local and exact Buildbox prepared-source
  validation, all 54 rejecting mutations, and the still-closed candidate gates.
- [`results/physical-binder-implementation-contract-482cf256-20260903.txt`](results/physical-binder-implementation-contract-482cf256-20260903.txt)
  pins the exact post-`0496` parent, 26 source identities, and all 43 rejecting
  mutations for the final one-task binder implementation.
- [`results/watchdog-validator-generation-9adfbb05-20260903.txt`](results/watchdog-validator-generation-9adfbb05-20260903.txt)
  pins the exact generated patch, two-read/zero-write contract, replay, strict
  review, 12 rejecting source mutations, and all-profile invariant.
- [`results/watchdog-validator-kunit-6607089e-20260903.txt`](results/watchdog-validator-kunit-6607089e-20260903.txt)
  records the exact Buildbox package and complete seven-case no-network runtime
  pass with the validator still disconnected from production.
- [`results/parent-proof-kunit-335d41b0-20260903.txt`](results/parent-proof-kunit-335d41b0-20260903.txt)
  pins exact generation, admission, Buildbox compile/package identities, the
  corrected off-stack test snapshot, and the 62-of-62 no-network runtime pass.
- [`results/record-4-ledger-kunit-38104ac6-20260903.txt`](results/record-4-ledger-kunit-38104ac6-20260903.txt)
  pins exact generation, decoder tests, admission, Buildbox package identities,
  and the 10-of-10 no-network in-memory runtime pass.
- [`results/hotplug-snapshot-kunit-ed64b4f5-20260903.txt`](results/hotplug-snapshot-kunit-ed64b4f5-20260903.txt)
  pins the withheld first artifact, corrected exact generation, 20 rejecting
  mutations, admission, Buildbox package, and 6-of-6 no-network runtime pass.
- [`results/cpu8-observer-kunit-bcde9445-20260903.txt`](results/cpu8-observer-kunit-bcde9445-20260903.txt)
  pins the first compile refusal, dependency correction, exact regenerated
  patch, 21 rejecting mutations, Buildbox package, and 7-of-7 no-network
  runtime pass.
- [`results/restore-executor-kunit-4c98a46a-20260903.txt`](results/restore-executor-kunit-4c98a46a-20260903.txt)
  pins exact generation, 32 rejecting mutations, admission, Buildbox package,
  and the 10-of-10 no-network restore runtime pass.
- [`results/hotplug-binder-core-kunit-6f5eb100-20260903.txt`](results/hotplug-binder-core-kunit-6f5eb100-20260903.txt)
  pins exact generation, 22 rejecting mutations, admission, corrected isolated
  profile, Buildbox package, and the 9-of-9 no-network binder runtime pass.
- [`results/hotplug-ledger-terminal-kunit-b1a1998e-20260903.txt`](results/hotplug-ledger-terminal-kunit-b1a1998e-20260903.txt)
  pins the pre-binding ledger audit, exact terminal repair, 18 rejecting
  mutations, Buildbox package, and the 13-of-13 no-network runtime pass.
- [`results/hotplug-ledger-context-kunit-af9b65d3-20260903.txt`](results/hotplug-ledger-context-kunit-af9b65d3-20260903.txt)
  pins the callback-context audit, non-sleeping record-4 repair, ten rejecting
  mutations, Buildbox package, and the 13-of-13 no-network runtime pass.
- [`results/hotplug-binding-kunit-30125de8-20260903.txt`](results/hotplug-binding-kunit-30125de8-20260903.txt)
  pins exact binding generation, the rejected bit-field compile, corrected
  source and parent reconstruction, 28 rejecting mutations, the validated
  Buildbox package, and the 9-of-9 no-network production-composition pass.
- [`results/physical-candidate-43349a53-20260903.txt`](results/physical-candidate-43349a53-20260903.txt)
  pins the exact production build, package provenance, byte-reproducible DT
  composition, Android-v0/LK container, negative gates, pre-boot hypothesis,
  recovery classification, and one-attempt decision branches.
- [`results/physical-deployment-20260903.txt`](results/physical-deployment-20260903.txt)
  records live-GPT resolution, inactive-root and stable-power gates, predecessor
  identity, the sole write, full readback, temporary cleanup, and confirmed
  shutdown without a fresh partition backup.
- [`results/physical-runtime-attempt-1-config-identity-blocked-20260903.txt`](results/physical-runtime-attempt-1-config-identity-blocked-20260903.txt)
  records the exact serviceable pre-trigger frame, sole consumed trigger,
  pre-CPU8 `0x40000` READY veto, zero CPU or watchdog operations, logical-empty
  records 0 and 4, changed-ID recovery, and unchanged boot2 readback.
- [`results/config-identity-repair-definition-20260903.txt`](results/config-identity-repair-definition-20260903.txt)
  pins patch `0503`, the package-derived `2e50cc09...` identity, its
  physical-profile-only scope, five rejecting mutations, and the 173-profile
  canonical-series audit before Buildbox submission.
- [`results/config-identity-repair-candidate-69b7494c-20260903.txt`](results/config-identity-repair-candidate-69b7494c-20260903.txt)
  pins the corrected Buildbox package, exact embedded identity counts,
  byte-reproducible DT/container constructions, strengthened pre-trigger gate,
  and repaired successor candidate `58313c3a8...` before device deployment.
- [`results/config-identity-repair-deployment-20260903.txt`](results/config-identity-repair-deployment-20260903.txt)
  records live-GPT target resolution, stable power, predecessor identity, the
  sole write, two matching full readbacks, cleanup, and confirmed shutdown.
- [`results/physical-runtime-attempt-2-cpu9-down-readback-mismatch-20260903.txt`](results/physical-runtime-attempt-2-cpu9-down-readback-mismatch-20260903.txt)
  records the repaired READY gate, one trigger, both A72 online terminals, the
  sole CPU9-down transaction, retained CPU8, stage-12 readback mismatch, and
  changed-ID watchdog recovery with unchanged `boot2`.
- [`results/readback-bitmap-hardware-free-7ca200d6-20260903.txt`](results/readback-bitmap-hardware-free-7ca200d6-20260903.txt)
  records exact patch `0504`, both 9-of-9 no-network regressions, and its
  behavior-neutral 24-term mismatch observation contract.
- [`results/readback-bitmap-candidate-46539642-20260903.txt`](results/readback-bitmap-candidate-46539642-20260903.txt)
  pins the exact production Buildbox package, two byte-identical DT and
  container constructions, configuration and pre-trigger gates, 32-of-32 LK
  checks, and the distinct `9b60b576...` one-attempt candidate.
- [`results/readback-bitmap-deployment-20260903.txt`](results/readback-bitmap-deployment-20260903.txt)
  records live-GPT target resolution, stable power, predecessor identity, the
  sole write, two matching full readbacks, cleanup, and confirmed shutdown.
- [`results/physical-runtime-attempt-3-status2-cpu9-present-20260903.txt`](results/physical-runtime-attempt-3-status2-cpu9-present-20260903.txt)
  records the exact bitmap-enabled boot, sole trigger, CPU9 affinity-off and
  Linux-offline state, retained CPU8, the single secondary-status-mirror
  mismatch, and automatic changed-ID recovery without a retry.
- [`results/intersected-status-repair-definition-20260903.txt`](results/intersected-status-repair-definition-20260903.txt)
  ties that result to the established MT6797 two-word on-state semantics and
  fixes the narrow source, raw-evidence, call-budget, and test boundaries for
  patch `0505` before Buildbox generation.
- [`results/intersected-status-generation-4179b8d7-20260903.txt`](results/intersected-status-generation-4179b8d7-20260903.txt)
  records the exact Buildbox generation, byte-identical fetched patch, strict
  review and replay, ten rejected mutations, and all-profile series audit for
  the evidence-selected intersection repair.
- [`../../patches/v7.1.3/0483-arm64-add-CPU-down-lifecycle-handoffs.patch`](../../patches/v7.1.3/0483-arm64-add-CPU-down-lifecycle-handoffs.patch)
  is the exact admitted no-op-by-default implementation.
- [`../../patches/v7.1.3/0484-arm64-mediatek-add-hardware-free-CPU9-hotplug-owner.patch`](../../patches/v7.1.3/0484-arm64-mediatek-add-hardware-free-CPU9-hotplug-owner.patch)
  is the exact admitted one-attempt CPU9-down and distinct-restore owner.
- [`../../patches/v7.1.3/0485-arm64-mediatek-test-hardware-free-CPU9-hotplug-owner.patch`](../../patches/v7.1.3/0485-arm64-mediatek-test-hardware-free-CPU9-hotplug-owner.patch)
  is its focused hardware-free KUnit coverage.
- [`../../patches/v7.1.3/0486-arm64-mediatek-validate-finalized-CPU9-before-hotplug.patch`](../../patches/v7.1.3/0486-arm64-mediatek-validate-finalized-CPU9-before-hotplug.patch)
  preserves the active parent rule and adds the exact finalized-pair rule.
- [`../../patches/v7.1.3/0487-soc-mediatek-add-hardware-free-CPU9-hotplug-executor.patch`](../../patches/v7.1.3/0487-soc-mediatek-add-hardware-free-CPU9-hotplug-executor.patch)
  is the disconnected split target/controller/retained-CPU8 state machine.
- [`../../patches/v7.1.3/0488-soc-mediatek-test-hardware-free-CPU9-hotplug-executor.patch`](../../patches/v7.1.3/0488-soc-mediatek-test-hardware-free-CPU9-hotplug-executor.patch)
  is its eight-case memory-only KUnit coverage.
- [`../../patches/v7.1.3/0489-watchdog-mediatek-validate-recovery-owner-read-only.patch`](../../patches/v7.1.3/0489-watchdog-mediatek-validate-recovery-owner-read-only.patch)
  is the disconnected, locked, read-only exact recovery-owner validator and
  its two focused KUnit cases.
- [`../../patches/v7.1.3/0490-arm64-mediatek-prove-exact-A72-terminal-parent.patch`](../../patches/v7.1.3/0490-arm64-mediatek-prove-exact-A72-terminal-parent.patch)
  publishes the locked read-only proof of exact retired CPU8/CPU9 membership,
  matching provider identity, and idle owner/controller state.
- [`../../patches/v7.1.3/0491-soc-mediatek-prove-exact-A72-binder-parent.patch`](../../patches/v7.1.3/0491-soc-mediatek-prove-exact-A72-binder-parent.patch)
  combines that membership proof with the exact CPU8 binder terminal, all ten
  online CPUs, and a recent read-only watchdog-owner validation.
- [`../../patches/v7.1.3/0492-pstore-add-Gemini-A72-hotplug-record-4-ledger.patch`](../../patches/v7.1.3/0492-pstore-add-Gemini-A72-hotplug-record-4-ledger.patch)
  adds the disconnected, two-copy CRC ledger and ten memory-only KUnit cases.
- [`../../patches/v7.1.3/0493-soc-mediatek-add-disconnected-A72-hotplug-snapshot.patch`](../../patches/v7.1.3/0493-soc-mediatek-add-disconnected-A72-hotplug-snapshot.patch)
  adds the disconnected four-source snapshot adapter and six injected-source
  KUnit cases.
- [`../../patches/v7.1.3/0494-soc-mediatek-add-bounded-retained-CPU8-observer.patch`](../../patches/v7.1.3/0494-soc-mediatek-add-bounded-retained-CPU8-observer.patch)
  adds the disconnected one-shot asynchronous CPU8 observer and seven focused
  KUnit cases.
- [`../../patches/v7.1.3/0495-soc-mediatek-add-disconnected-CPU9-restore-executor.patch`](../../patches/v7.1.3/0495-soc-mediatek-add-disconnected-CPU9-restore-executor.patch)
  adds the disconnected, parent-linked CPU9 restore state machine with one
  injected CPU-on call site and four retained-ledger stages.
- [`../../patches/v7.1.3/0496-soc-mediatek-test-disconnected-CPU9-restore-executor.patch`](../../patches/v7.1.3/0496-soc-mediatek-test-disconnected-CPU9-restore-executor.patch)
  adds its ten focused hardware-free KUnit cases.
- [`../../patches/v7.1.3/0497-soc-mediatek-add-disconnected-A72-hotplug-binder-core.patch`](../../patches/v7.1.3/0497-soc-mediatek-add-disconnected-A72-hotplug-binder-core.patch)
  adds the disconnected same-task transaction coordinator.
- [`../../patches/v7.1.3/0498-soc-mediatek-test-disconnected-A72-hotplug-binder-core.patch`](../../patches/v7.1.3/0498-soc-mediatek-test-disconnected-A72-hotplug-binder-core.patch)
  adds its nine focused hardware-free KUnit cases.
- [`../../patches/v7.1.3/0499-pstore-allow-preidentity-A72-hotplug-terminals.patch`](../../patches/v7.1.3/0499-pstore-allow-preidentity-A72-hotplug-terminals.patch)
  admits only the three truthful preidentity terminal shapes required by the
  production binder and adds their focused record-4 coverage.
- [`../../patches/v7.1.3/0500-pstore-make-A72-hotplug-checkpoints-nonsleeping.patch`](../../patches/v7.1.3/0500-pstore-make-A72-hotplug-checkpoints-nonsleeping.patch)
  keeps setup in process context and makes checkpoint publication safe in the
  target CPU's non-sleeping shutdown callback.
- [`../../patches/v7.1.3/0501-soc-mediatek-bind-one-shot-CPU9-hotplug-transaction.patch`](../../patches/v7.1.3/0501-soc-mediatek-bind-one-shot-CPU9-hotplug-transaction.patch)
  binds the exact admission task, private CPU9 device transition, target and
  controller callbacks, record-4 ledger, retained-CPU8 observation, and
  parent-linked restore while preserving the public disable veto.
- [`../../patches/v7.1.3/0502-soc-mediatek-test-private-CPU9-hotplug-transition.patch`](../../patches/v7.1.3/0502-soc-mediatek-test-private-CPU9-hotplug-transition.patch)
  adds nine focused memory-only cases for task/CPU/device attribution, public
  gate preservation, cleanup on failure, and down/restore route selection.
- [`../../patches/v7.1.3/0503-arm64-bind-Gemini-physical-hotplug-configuration.patch`](../../patches/v7.1.3/0503-arm64-bind-Gemini-physical-hotplug-configuration.patch)
  selects the exact physical-profile configuration-input identity without
  changing the predecessor production or fixture identity.
- [`../../patches/v7.1.3/0504-soc-mediatek-record-CPU9-readback-mismatch-bitmap.patch`](../../patches/v7.1.3/0504-soc-mediatek-record-CPU9-readback-mismatch-bitmap.patch)
  replaces the composite readback observation with a self-identifying 24-term
  retained bitmap while preserving the existing accept/reject decision.

Patches `0483`--`0504` are experiment-only archives with a synthetic,
non-certifying author identity, no DCO sign-off, and are not submission-ready.
Upstream submission requires the actual author metadata and truthful
certification.

## Procedure

1. Pin the current repository, canonical series, manifest, prepared-source
   files, and accepted runtime parents.
2. Audit generic `cpu_down`, arm64 target disable/die/kill, MT6797 P32 guards,
   and membership attempts.
3. Select CPU9-off with CPU8 retained; reject last-A72-off.
4. Define the exact generic, target, controller, physical readback, restore,
   watchdog, and recovery handoffs.
5. Validate the contract locally and against the Buildbox-managed source; run
   the rejecting mutation suite.
6. Do not build or boot until each hardware-free implementation phase passes.

## Observations

The current source has no normal A72 down or restore owner and deliberately
hides the hotplug control. P32 guards protect failed CPU-up rollback only. The
secure-source audit establishes a per-core-only CPU9-off effect set when CPU8
remains present, but also establishes that the active affinity call contains
unbounded waits.

The exact contract passed locally, the 21 unsafe mutations all failed closed,
and the same validator passed against the six hash-pinned files in the
Buildbox-managed prepared source.

The first generation from repository commit `36f746d6...` reached strict
Checkpatch and stopped on five declaration-alignment checks. It produced no
admitted patch. The alignment-only generator correction in `aa014ea0...`
then produced exact patch `0483`: source validation and replay passed, all ten
unsafe source mutations failed closed, and strict Checkpatch reported zero
errors, warnings, or checks. The 165-profile canonical-series invariant passes
with `0483` appended as entry 475.

Exact pushed repository commit `1f17299f...` then compiled successfully on
Buildbox with the isolated `a72-cpu9-progress-candidate` profile. Package
validation passed for `Image`, `Image.gz`, `System.map`, all 123 DTBs,
configuration, and provenance. `System.map` contains all four new arm64
handoff dispatchers. The fetched `Image.gz` identity is
`6356e5bbe433aa76846a444c27336e2b458d004a6cb84774005c0138677843fa`.
One pre-existing frame-size warning remains in an MT6797 A72 membership test
helper; no warning arose from patch `0483`.

The first complete owner package at repository commit `95bb4265...` passed
strict Checkpatch, source replay, 20 rejecting source mutations, and all five
focused lifecycle cases. Independent pre-admission review rejected it because
the restore mint did not reject reserved or overflowing generation/cookie
values. No canonical patch was admitted from that package. Commit
`d266765e...` added the symmetric restore guard and a dedicated rejecting
mutation. Buildbox regenerated exact patches `0484` and `0485`; strict review
and replay passed, all 21 unsafe source mutations failed closed, and the five
focused lifecycle cases remained present. The admitted patch SHA-256 values
are `7f78083783287d2a270197fc537c1a1eba41446a5eb2182be102d44e6995af27`
and `443e2983110c743ecb3f93439f71ea2631a19cc0b66cb58cb208b162487e08e7`.
They append as canonical entries 476--477; the resulting series SHA-256 is
`6e0b25585badd53b66723f9c68213e87d29ca60175afdb4efb1c033cf2baacbb`,
and all 165 manifest profiles retain canonical-order subsequences.

The user-reported boot immediately before this audit did not produce a boot
cycle: Gemian remained reachable under the unchanged boot ID for the complete
observation window, and the mainline netcat endpoint did not appear. It is not
classified as a kernel attempt.

The exact admitted `0484`--`0485` series then compiled successfully on
Buildbox as repository commit `7fbd9ac1...`. Its no-network four-vCPU QEMU
gate ran all 60 expected cases. All 55 pre-existing owner, transition, and
binder cases passed, as did the new entry-rejection case. The other four new
cases failed at the same first down-preparation assertion with `-EPERM`.
Source audit traced this to reuse of the active-CPU9 parent predicate: that
predicate correctly requires retired slot 1 to be empty while CPU9 bring-up is
active, but successful CPU9 finalization correctly fills slot 1 before the
down lifecycle begins. The runtime result is an actionable implementation
defect, not hardware evidence; no physical effect or device action occurred.

Buildbox generation at exact pushed commit `9a9f0455...` then preserved the
admitted `0484` and `0485` byte identities and produced standalone follow-up
`0486` with SHA-256
`a583e8184b39dc51aa0556a5531ebe6d403e54ad8106ca8dbebbf1259c2ea019`.
Strict Checkpatch, exact replay, all 21 predecessor mutations, and all six new
terminal-parent mutations pass. The resulting 475-patch canonical series has
SHA-256 `640f8757299432cf125d34f3049e2aa7b1f1c19b0688e46cbafd1bdb7749bd19`,
and all 165 manifest profiles retain canonical-order subsequences.

Exact admission commit `e8e564f5...` compiled successfully on Buildbox with
the isolated membership/KUnit profile. Package validation covered the kernel,
configuration, provenance, and all 123 DTBs. The only compiler frame warning
is the pre-existing owner-token stack warning; patch `0486` introduced none.
The identical no-network four-vCPU gate then passed all 60 cases with zero
failures or skips: owner 39/39, transition executor 12/12, and binder 9/9.
It also verified zero production callers, physical backends, MMIO,
retained-RAM, watchdog, SMC, physical CPU requests, or device action.

The follow-on callback audit found an incompatibility in the initial prose:
the already-used TOPRGU recovery takeover is deliberately irreversible and
has no cancel or refresh API. CPU9 hotplug must inherit the exact watchdog
identity established by CPU8 bring-up and finish its durable result before the
original 15-second reset. It must not arm a second deadline or invent a cancel
path. The physical-executor contract records that conservative correction,
the split target/controller ownership, and the exact independent readback
predicate. Its validator and 26 unsafe mutations pass without binding a
callback or changing a boot candidate.

The first physical-executor generation at `8d6e450a...` was rejected by 27
strict Checkpatch `OPEN_ENDED_LINE` checks on intentionally wrapped long
signatures. The explicit style exception at `c506b26d...` exposed 14 separate
overlong KUnit continuation lines, so that package was also rejected. Exact
pushed commit `be8f55a1...` corrected those line wraps and generated patches
`0487`--`0488`. Strict review with only the documented synthetic-author,
path-change, and open-ended-signature exclusions passes; exact replay passes;
all 18 unsafe source mutations fail closed; and all eight focused cases remain
present. The admitted patch SHA-256 values are
`41ebcb04209f216d396ea81bbc91b710478ea00ce0fcb6bde98eb735c2d73505`
and `1a759237bba96aa5dfc13b51249311fce90469ea05773eae7317dfb5239c02b2`.
They append as canonical entries 476--477, producing series SHA-256
`6912c6b0b01cd86de634fcae044e864c2a898fa2211b765e6b5e68b06ad28a98`;
all 166 manifest profiles retain canonical-order subsequences. The new code
contains one authorization token but no CPU_OFF implementation, binds no
callback, leaves `cpu_can_disable()` false, and remains ineligible for boot.

Exact admission commit `e24e6c45...` then compiled successfully on Buildbox
with the isolated `a72-physical-executor-kunit` profile. Package validation
covered `Image`, `Image.gz`, `System.map`, configuration, provenance, and all
123 DTBs. The no-network four-vCPU QEMU gate at published harness commit
`4d8822a4...` passed the sole executor suite 8/8 with zero failures or skips.
It exercised successful ordering, entry rejection, reversible pre-commit
failure, target-return faulting, one-shot affinity, readback rejection,
post-commit callback faulting, and terminal one-shot behavior. The profile
links no production binder or admission controller, keeps the disable veto
closed, and performs no physical CPU request, PSCI call, MMIO, retained-RAM,
watchdog, network, or device action.

The binding-interface audit found six prerequisites that a direct callback
hookup would miss. The CPU8 binder does not expose the inherited watchdog
identity or takeover time; the watchdog driver has no read-only exact-owner
validator; the existing physical-source helper writes an unrelated retained
ledger; the generic PSCI kill helper polls affinity repeatedly; the existing
synchronous CPU8 IPI has no controller-side time bound; and the initial CPU9
binder cannot own the distinct restore. It also confirmed that retained record
4 at `0x44414000` has no current owner while records 0--3 do.

The physical-binder contract resolves those gaps without enabling any path.
It allocates one dedicated two-copy CRC ledger in record 4, distinguishes 17
decision-bearing boundaries, bounds the successful path to 451 32-bit retained
writes, requires exact changed-boot-ID recovery, and routes restore through the
normal CPU-up lifecycle under a new parent-linked identity. The contract also
records a correction to the phrase “read-only snapshot”: the existing DVFSP
clock readback transport performs a fixed power-on write and bounded semaphore
request writes. Those exact transport effects are counted; PLL, divider, OPP,
voltage, rail, and BigiDVFS-set writes remain forbidden. Local validation and
all 54 unsafe contract mutations pass. Exact pushed commit `aa03bb01...` also
passes the same contract and mutation suite against Buildbox prepared source
state `2bde772b...`; its temporary Git checkout was removed, and it performed
no compile, QEMU run, device contact, or physical action.

Buildbox generation at exact pushed commit `9adfbb05...` produced standalone
patch `0489` with SHA-256
`940c2158c04376d856b7a0cc6b7aa69702883b5e88b2959b3d82589cfce18b91`.
Strict Checkpatch, exact replay, and all 12 rejecting source mutations pass.
The validator holds the existing recovery lock, accepts only the exact
inherited identity, and performs exactly two register reads with zero writes,
reloads, refreshes, releases, or ownership changes. Its two focused cases
extend the watchdog suite to seven. The code has no production caller,
preserves the MT6797 disable veto, and creates no boot candidate or device
action. Appending `0489` makes 478 canonical patches with series SHA-256
`1a8751eb0285be3362b7434649e4cf8656056030529179f5ae3046b0bc3aa124`;
all 166 manifest profiles retain canonical-order subsequences.

Exact admission commit `6607089e...` compiled successfully on Buildbox with
the isolated watchdog profile. Package validation covered `Image`, `Image.gz`,
`System.map`, configuration, provenance, and all 123 DTBs. The no-network
four-vCPU QEMU gate at published harness commit `c99abc3e...` then passed the
sole watchdog suite 7/7 with zero failures or skips, including both new
validator cases. The exact runtime proof retains the two-read/zero-write
contract and confirms zero production callers, physical watchdog calls, MMIO,
retained RAM, SMC, physical CPU requests, device actions, or boot candidates.

Buildbox generation at exact pushed tooling commit `646108fd...` produced
patches `0490` and `0491` from the hash-pinned post-`0489` source. Their
SHA-256 identities are
`691daec5235f51bec74441dfe7db2c2bfea58962c892da0e00e5563651453e73`
and
`8cdd4e34cdb020b30736604c44fe728dd06b4f754694caf2625bfa02555a16fd`.
Exact replay, strict review, all 20 unsafe source mutations, all 166 manifest
profiles, and the eight-mutation series-invariant self-test pass. The proof
requires exact retired CPU8/CPU9 identities, a matching held provider, idle
owner and hotplug controllers, the exact CPU8 terminal, CPUs 0--9 online with
no extras, the inherited watchdog identity, and a successful read-only
validation no more than five seconds after takeover. It has no production
caller and keeps `cpu_can_disable()` false.

The first compile exposed only a KUnit-quality defect: copying the full binder
onto the test stack produced a new 7,712-byte frame warning. The corrected
`0491` keeps the full-object unchanged assertion but allocates its snapshot
from KUnit-managed memory. Exact admission commit `335d41b0...` then compiled
successfully on Buildbox with patchset
`ac872518784450d38dbffea9ac14b6e605861dcf739347ed1498a62691ccac5e`;
the new frame warning is absent and package validation covers the kernel,
configuration, provenance, and all 123 DTBs. At published harness commit
`17ac3d3c...`, the no-network four-vCPU QEMU gate passed 62/62 cases with
zero failures or skips: owner 40/40, transition executor 12/12, and binder
10/10. Both new parent-proof cases pass, all 60 regressions pass, and no
production callback, physical backend, CPU request, MMIO, retained-RAM, SMC,
device action, or boot candidate is enabled.

Buildbox generation at exact pushed tooling commit `ee5e368f...` then produced
standalone patch `0492` with SHA-256
`293c013301152bcb4ccf1035e6669d262c0d1f8bbb86259a8a739fbe3db47fe8`.
Exact replay, strict review, all 20 unsafe source mutations, all 167 manifest
profiles, and the eight-mutation series-invariant self-test pass. The ledger
owns only retained record 4 at `0x44414000`, preserves records 0--3, accepts
only raw-empty or pstore-empty initial state, and uses two alternating 27-word
copies with CRC written last and full readback. Its normal successful sequence
has 16 records and at most 451 32-bit writes. The separate host decoder passes
ten tests and rejects unchanged boot IDs, malformed headers, bad CRCs,
ambiguous generations, and invalid semantic shapes without changing the
source record.

Exact admission commit `38104ac6...` compiled successfully on Buildbox with
patchset `608dc574bcf2f24ae70f68795dfbb39137509b9be3693e752e5f21cd4d77e70c`.
Package validation covered `Image`, `Image.gz`, `System.map`, configuration,
provenance, and all 123 DTBs. At published harness commit `61d250e4...`, the
no-network four-vCPU QEMU gate passed the sole ledger suite 10/10 with zero
failures or skips. It exercised layout and write budgets, complete success,
pstore-empty admission, nonempty and sequence refusal, both terminal fault
classes, readback corruption, CRC fallback, and semantic-shape refusal. The
production mapping API still has no caller; the run used injected word arrays
and performed no physical backend, MMIO, retained-RAM, SMC, watchdog, network,
device, or boot-candidate action.

The first snapshot generation at `95166c97...` passed its automated oracle,
but independent review withheld it before admission to require an explicit
`WARN_ON_ONCE` include and a null-safe source initializer with a focused test.
Corrected generation at `a170767c...` produced patch `0493` with SHA-256
`54d4d38d7fd9f7337a41a771ab82d06a5ce90d36808a411feae044d5fe97b8d7`.
Exact replay, strict review, all 20 rejecting source mutations, all 168
manifest profiles, and the eight-mutation series-invariant self-test pass.
The adapter holds exactly three supplier device references and captures one
platform, provider, protected-clock, and BigiDVFS sample in that order. It
excludes both sample generations from equality, avoids the historical
protected-readback ledger, and has no production caller or DT node.

Exact admission commit `ed64b4f5...` compiled successfully on Buildbox with
patchset `8f0dee0f7dfe69be853914ae122b6678e74d6a8b00290aaca1b95a5c94535d63`.
Package validation covered `Image`, `Image.gz`, `System.map`, configuration,
provenance, and all 123 DTBs. At published harness commit `a2aca8c0...`, the
no-network four-vCPU QEMU gate passed the sole snapshot suite 6/6 with zero
failures or skips. The proof preserves one call per component, the bounded
clock transport maximum of 401 writes, two BigiDVFS stable samples/eight
register reads/zero SRAM-set calls, and zero physical backend invocations,
MMIO, I2C, SMC, retained-RAM, watchdog, network, or device action.

The first CPU8-observer package, exact patch SHA-256 `cb78f0d0...`, passed its
source oracle but failed the isolated Buildbox compile at the only attributable
error: `mt6797_a72_hotplug_snapshot()` was not declared because the observer
profile had not selected the CPU9-membership owner that publishes the snapshot
API. It was rejected as a usable prerequisite and superseded. The corrected
generator makes that dependency explicit and reconstructs the exact pre-`0494`
parent from prepared source state `fa3ac202...`. Exact patch `0494` SHA-256
`bc9764dd...` then passes replay,
strict review, all 21 rejecting mutations, all 169 manifest profiles, and the
eight-mutation series-invariant self-test. It contains one `wait=0` dispatch to
CPU8, no retry or synchronous dispatch, a 250 ms controller bound, exact
CPU9-down/`OFF_COMMITTED` identity, and binder-owned one-shot storage. It has
no production caller or DT node.

Exact admission commit `bcde9445...` compiled successfully on Buildbox with
patchset `59b748ac89b6410f6b309dac8379f44c2c51442f98fd5ec42ce191da7a13c02a`.
Package validation covered `Image`, `Image.gz`, `System.map`, configuration,
provenance, and all 123 DTBs. At published harness commit `6097b85d...`, the
no-network four-vCPU QEMU gate passed the sole observer suite 7/7 with zero
failures or skips. It exercised success, CPU refusal, identity refusal,
dispatch refusal, terminal timeout with a late callback, one-shot refusal, and
snapshot identity. No production callback, physical backend, CPU request,
MMIO, I2C, retained-RAM, SMC, watchdog takeover, network, device action, or
boot candidate was enabled. A later regeneration request also failed closed
after the managed prepared-source identity advanced to `751075a0...`; it
produced no replacement artifact and does not alter the admitted patch proof.

The restore generator was stabilized in three bounded validator corrections:
Kconfig matching was confined to the target stanza, the Kconfig mutation was
made target-specific, and checkpoint mutations were made deterministic. Exact
Buildbox generation at pushed commit `3e1f4d6a...` then produced patches
`0495` and `0496` with SHA-256 identities `95b9b60f...` and `78c61102...`.
Exact replay and strict review pass, all 32 unsafe source mutations fail
closed, all 170 manifest profiles retain canonical-order subsequences, and
the eight-mutation invariant self-test passes. The executor accepts only the
exact retired CPU9-down parent and a distinct parent-linked restore identity,
uses one injected CPU-on call site after the CPU_ON-committed checkpoint,
records stages 14--17, and suppresses unrelated initial-P32 rollback. It has
no production caller, DT node, or physical-effect implementation.

Exact admission commit `4c98a46a...` compiled successfully on Buildbox with
patchset `2fcbb02f8e760f0b7586c598f83c3ff1b73283e0531852b938a800dcd77bef44`.
The validated package contains the kernel, configuration, provenance, and all
123 DTBs; the restore files introduced no compiler warning. At published
harness commit `ced11d9e...`, the no-network four-vCPU QEMU gate passed the
sole restore suite 10/10 with zero failures or skips. It covered exact entry,
identity and validation refusals; prepare, CPU-on, checkpoint and completion
failures; secondary ordering; rollback; and successful terminal membership.
No physical backend, CPU request, MMIO, I2C, retained-RAM access, SMC,
watchdog takeover, network, device action, or boot candidate was enabled.

Because the original binder contract intentionally pins the earlier
pre-prerequisite source, it remains immutable historical evidence rather than
being rewritten for generation. The successor implementation contract at
exact pushed commit `482cf256...` pins all 26 post-`0496` source interfaces and
all nine prerequisite patch identities. Local validation and all 43 unsafe
mutations pass. The same validator passes against Buildbox prepared-source
state `febbcbb4...`, including the still-closed A72 disable veto, absent down
callbacks, unextended admission chain, and disconnected down/restore
executors. No compile, QEMU run, candidate, or device action occurred.

The binder-core generator was stabilized through two bounded validator fixes:
Kconfig mutations were confined to the target stanza, then the exact
post-commit branch was added to the rejecting set. Exact Buildbox generation
at pushed commit `72f6e8f3...` produced patches `0497` and `0498` with SHA-256
identities `db918ca1...` and `70946723...`. Exact replay and strict review
pass, all 22 unsafe source mutations fail closed, all 171 manifest profiles
retain canonical-order subsequences, and the eight-mutation series-invariant
self-test passes. The core is one-shot and same-task, accepts only the exact
parent and provider identities, and orders one `remove9` request before one
distinct `add9-restore` request. It contains no production caller, DT node, or
physical-effect implementation.

The first isolated compile failed closed because the binder profile omitted
the existing DVFSP clock-transport fragment required by the snapshot
prerequisite. No source patch changed. Exact profile correction commit
`6f5eb100...` then compiled successfully on Buildbox with patchset
`c134677202d3c8656b4141df5c88b3697340a4865fcbdc682c93a603dc9ac498`.
The validated package contains the kernel, configuration, provenance, and all
123 DTBs, and the binder files introduced no compiler warning. At published
harness commit `478db6ec...`, the no-network four-vCPU QEMU gate passed the
sole binder suite 9/9 with zero failures or skips. It exercised success,
wrong-task, parent, ledger, down, restore, checkpoint, terminal-publication,
and one-shot paths. No production callback, physical backend, CPU request,
MMIO, I2C, retained-RAM access, SMC, watchdog takeover, network, device
action, or boot candidate was enabled.

The production-callback audit then found that record 4 could not encode three
truthful failure paths: down preparation before a down identity exists,
CPU_OFF membership-commit failure at stage 7, and restore preparation before a
restore identity exists. Binding the callbacks in that state would have lost
the exact terminal evidence needed to classify those failures. Exact Buildbox
generation at pushed commit `acbda185...` produced patch `0499` with SHA-256
`48449b22...`; replay, strict review, and all 18 unsafe mutations pass. Exact
admission commit `b1a1998e...` retains canonical order across all 171 manifest
profiles and compiles the 488-patch isolated ledger profile on Buildbox. The
validated kernel and all 123 DTBs pass package checks. Its no-network QEMU gate
passes all 13 record-4 cases, including the three new terminal boundaries,
without changing the wire format, successful 16-record/451-write budget, or
invoking a production caller, CPU request, retained RAM, watchdog, SMC,
network, device, or boot candidate.

The next callback audit found two source-level constraints that the frozen
prose had not modeled precisely. Arm64 samples `cpu_can_disable()` only while
registering each CPU device and stores the answer in `offline_disabled`;
`device_offline()` checks that flag before it reaches the CPU bus callback.
Opening the answer for CPU9 would therefore expose the normal sysfs hotplug
control, while leaving it false prevents the binder's ordinary `remove_cpu(9)`
call from entering its down preflight. The target `.cpu_die` callback also runs
after interrupt masking, but the record-4 checkpoint used a mutex and unmapped
the slot on a terminal record. The selected binding now preserves the public
veto and uses an internal, device-hotplug-lock-scoped transition that clears
`offline_disabled` only around the binder-owned request and restores it before
unlock; the target `.cpu_disable` callback must independently require the exact
executor identity. Patch `0500` closes the ledger half by moving checkpoint
serialization to a raw spin lock and retaining the fixed mapping until reset.
Exact generation at `10aa0a01...`, replay, strict review, and all ten rejecting
mutations pass. Exact admission commit `af9b65d3...` keeps canonical order for
all 171 profiles and compiles the 489-patch ledger profile on Buildbox. Package
validation covers the kernel, provenance, configuration, and all 123 DTBs; the
no-network QEMU gate passes all 13 ledger cases. The wire format and
16-record/451-write success budget are unchanged, and no production caller,
physical backend, CPU request, retained-RAM access, watchdog, network, device
action, or boot candidate is enabled.

The production-binding generator initially admitted patches `0501`--`0502`,
but the first exact Buildbox compile at `b8656aa8...` rejected `READ_ONCE()` and
`WRITE_ONCE()` applied to `struct device` bit-fields. No candidate or device
action followed that failure. The correction uses direct bit-field access only
while holding `lock_device_hotplug()`. When the managed prepared tree later
advanced past the required parent, the wrapper was also corrected to
reconstruct only the 28 hash-pinned post-`0500` interfaces by reverse-applying
the already-admitted binding changes in a temporary minimal tree. Exact
generation at pushed commit `c332eb34...` then passed source replay, strict
review, and all 28 rejecting mutations. The admitted patch SHA-256 identities
are `4009c0bf8724be7c05e8e75e8709ef4520425dbe8956109de51cce60b73c1ffa`
and `c09fae1b8fd25050276cb089458e490cd737db96da3a56ecc140812d5028a5bd`.
All 172 manifest profiles retain canonical-order subsequences across the
491-entry series.

Exact correction commit `30125de8...` compiled the isolated
`gemini-a72-hotplug-binding-kunit` profile on Buildbox. Package validation
covered `Image`, `Image.gz`, `System.map`, configuration, provenance, and all
123 DTBs; the exact kernel release is
`7.1.3-gemini-a72-hotplug-binding-kunit`. Its no-network four-vCPU QEMU gate
then passed the sole binding suite 9/9 with zero failures or skips. It covered
success, wrong task, wrong CPU, missing device, unexpectedly public gate,
already-offline device, offline target, failure cleanup, and down/restore
route selection. The success case made exactly one injected private offline
request, and both success and failure restored the cached public gate. The
production binding was linked but not invoked because the virtual DT has no
Gemini admission node. No physical backend, CPU request, PSCI, MMIO, I2C,
retained-RAM, watchdog, network, device action, or boot candidate was selected.

Exact candidate commit `43349a53...` adds a separate production profile with
the hotplug binding built in, KUnit and split startup disabled, and the public
A72 disable veto unchanged. Buildbox validated all package members and 123
DTBs for release `7.1.3-gemini-a72-hotplug-physical`. Two independent DT
compositions are byte-identical at `f373dd19...`; an independent structural
validator proves the sole delta from the accepted serviceability/admission DT
is the current package's exact A41 provenance leaf, and all ten mutations are
rejected. Two Android-v0/LK assemblies and two padding constructions are
byte-identical. Independent parsing passes all 32 LK gates and rejects six
container mutations. The raw identity is `482516ce...`; the exact 16 MiB
`boot2` identity is `4b027c97...`. No native VM build, device access, physical
CPU request, retained-RAM access, partition write, or boot occurred during
validation.

The guarded installer then resolved inactive logical `boot2` to
`/dev/mmcblk0p30` while Gemian root remained `/dev/mmcblk0p29`, observed a
stable 100% healthy battery with external power, and recorded predecessor
`68ec1b78...`. One bounded write of exact padded candidate `4b027c97...` was
synced and flushed. Both the on-device full-partition checksum and a separate
streamed full readback matched the candidate byte-for-byte. Temporary staging
and readback files were removed, no new predecessor backup was made, and the
device became unreachable after the requested clean shutdown.

The pre-boot hypothesis is now fixed: the existing live admission task first
completes CPU8 and CPU9 to the accepted exact parent, after which the production
binder privately offlines only CPU9, proves CPU8 remains live, and restores
CPU9 once in the same boot. Success requires the exact release/provenance,
record-4 stages 1--7 and 9--17, terminal membership `0x3`, CPUs `0-9` online,
and USB/netcat serviceability. A screen or reboot observation alone is
inconclusive. The inherited recovery takeover cannot be cancelled, so an
automatic watchdog reset back to Gemian is expected even after a successful
terminal record. Any truthful failure or hang is decoded only after a changed
boot ID; there is no retry, no CPU8-last-off path, and no cpufreq, thermal,
idle, or suspend change in this attempt.

The sole runtime attempt booted the exact release with fresh ID `5bf5be02...`,
exposed USB/netcat serviceability, bound the admission controller, binder, and
platform-state supplier, and presented CPUs 0--9 with only 0--7 online. The
durable pre-trigger frame also exposed arm64 proof mask `0x40000`: the package
provenance carried physical-profile configuration-input identity `2e50cc09...`
while the kernel still embedded predecessor CPU9-progress identity
`c10a2188...`. Exact little-endian sequence inspection of the built Image found
that progress identity once and the earlier controller identity zero times. The
single trigger was consumed and returned `-EAGAIN` at CPU9 controller failure
stage 1. CPU8 core consumption, CPU8/CPU9 requests, CPU_OFF, hotplug-ledger
entry, and watchdog takeover all remained zero. A validated USB-shell reboot
returned to changed-ID Gemian; read-only recovery found records 0 and 4 exact
logical-empty `DBGC/0/0`, verified boot2 still matched `4b027c97...`, and did
not clear retained state. This retires the exact candidate without testing the
physical CPU9-down hypothesis.

Patch `0503` was corrected after its first Buildbox submission failed safely
at patch application. Exact pushed commit `69b7494c...` then compiled the
492-patch physical profile on Buildbox. Its package records configuration-input
identity `2e50cc09...`; the built Image contains that exact little-endian
four-word identity once and contains neither stale predecessor identity. Two
serviceability-DT compositions, two Android-v0/LK assemblies, and two 16 MiB
padding constructions are byte-identical. Both independent candidate
validations pass all 32 LK gates and reject all six container mutations. The
raw successor is `4a3551c6...`; exact inactive-`boot2` content is
`58313c3a8...`. No device access or write occurred during its construction.

Guarded deployment from pushed commit `1a9b8a9d...` then resolved inactive
logical `boot2` to `/dev/mmcblk0p30` while Gemian root remained
`/dev/mmcblk0p29`. Stable power was present at 100% capacity. One write
replaced retired candidate `4b027c97...`; the post-flush partition checksum and
an independent streamed byte comparison both matched exact successor
`58313c3a8...`. No fresh backup was made, all temporary files were removed,
and both the installer and a separate SSH probe confirmed clean shutdown.

The repaired runtime boot then passed its exact pre-trigger identity and arm64
READY gate. Its first read-only capture exposed only two stale host-side sysfs
paths; live driver and deferred-probe evidence showed the binder and platform
supplier bound, so commit `905a204e...` corrected the probe without changing
the candidate. A second read-only capture passed every gate. One trigger then
booted CPU8 at MPIDR `0x200` and CPU9 at MPIDR `0x201`, both with MIDR
`0x410fd081`. CPU8 and CPU9 reached their CRC-valid online terminals. The sole
private CPU9-down request advanced through affinity-off, post-state capture,
and a bounded CPU8 observation; CPU8 remained online and CPUs 0--8 formed
online mask `0x1ff`. The exact readback predicate then returned `-EIO` before
owner proof or restore. Record 4 retained generation 11, stage 12,
postcommit-down-fault, result flags `0x77f`, one CPU-off authorization, one
affinity query, one CPU8 callback, and mismatch value `0x1`. Automatic
watchdog recovery reached changed-ID Gemian without a manual reboot; the
installed `boot2` checksum remained `58313c3a8...`.

## Analysis

The accepted online/topology/load evidence closes the entry-state uncertainty
that blocked earlier offlining designs. It does not close CPU-down ownership,
the active-affinity timeout, or a same-boot restore. Exposing the existing
generic path would skip all three requirements.

A CPU9-first transaction is decision-bearing because its successful effect set
does not include cluster shutdown. The independent watchdog converts a stuck
secure call into bounded reset recovery, not into a successful hotplug return.
Only the independent per-core readback and retained-CPU observation can permit
the membership commit and subsequent restore.

## Conclusion

The physical hypothesis was not reached by the first candidate. The exact
parent code is confirmed incapable of safely running the experiment as-is.
Patch `0483` supplies and
Buildbox-proves the generic ownership handoffs. Patches `0484`--`0485` add the
hardware-free one-attempt CPU9-down owner, single affinity-proof budget,
distinct parent-linked restore, and reset-only post-commit failure model, but
their first runtime gate exposed the finalized parent-state defect above.
Patch `0486` corrects that source defect without weakening the active-CPU9
rule. Patches `0487`--`0488` add the disconnected physical-executor state
machine, and their exact isolated Buildbox compile and 8/8 no-network runtime
gate now pass. This closes the hardware-free executor phase. The binding
contract also closes the ambiguity about how production ownership,
attribution, observation, and restore must meet. Patch `0489` now supplies the
first disconnected production prerequisite: an exact read-only validator for
the inherited watchdog owner. Its exact Buildbox compile and 7/7 isolated
runtime gate now passes. Patches `0490`--`0491` supply the exact combined
CPU8/CPU9 parent proof, and their corrected exact Buildbox compile and 62/62
isolated runtime gate now pass. Patch `0492` supplies the dedicated record-4
ledger and changed-boot-ID decoder; exact generation, 20 source mutations, ten
decoder tests, Buildbox compile, and 10/10 isolated runtime cases pass. Patch
`0493` supplies the disconnected snapshot adapter; exact generation, 20 source
mutations, Buildbox compile, and 6/6 isolated runtime cases pass. The combined
series still binds no callback, preserves the MT6797 disable veto, and performs
no physical action. Patch `0494` supplies the bounded CPU8 observer; exact
generation, 21 source mutations, Buildbox compile, and 7/7 isolated runtime
cases pass. Patches `0495`--`0496` now supply the distinct CPU9 restore
executor; exact generation, 32 source mutations, Buildbox compile, and 10/10
isolated runtime cases pass. Patches `0497`--`0498` supply the disconnected
same-task binder core; exact generation, 22 source mutations, Buildbox compile,
and 9/9 isolated runtime cases pass. All disconnected orchestration is
therefore complete. Patch `0499` repairs the three exact preidentity terminal
shapes exposed by the production-callback audit; exact generation, 18 source
mutations, Buildbox compile, and 13/13 isolated ledger cases pass without a
wire-format or success-budget change. Patch `0500` then makes those checkpoints
safe in the target CPU's non-sleeping shutdown context; exact generation, ten
source mutations, Buildbox compile, and the same 13/13 ledger cases pass. The
production callback glue in patches `0501`--`0502` now binds that proven core
to the existing admission task, an internal lock-scoped CPU9 device transition,
and the exact down/restore callbacks while keeping the public
`cpu_can_disable()` veto closed. After correcting the rejected bit-field build,
the exact 28-interface generation and mutation gate pass, the Buildbox package
validates, and all 9/9 focused no-network runtime cases pass. This closes the
last hardware-free composition gate. Exact retired production candidate
`4b027c97...` passed its separate package, DT, container, mutation,
serviceability, attribution, recovery, and forbidden-action gates. Its decoded
device attempt instead selected the stale embedded configuration-input
identity before any CPU operation. Repaired successor `58313c3a8...` passed
those gates and advanced the hardware transaction through both A72 online
terminals and the CPU9-only down post-state. It failed only the composite
readback predicate before owner proof, so the lifecycle gate and restore remain
open.

## Follow-up

The parent-proof, watchdog-validator, record-4, snapshot, bounded CPU8
observer, CPU9 restore, binder-core, and production-composition proofs are
complete and must remain fixed.
Continue under the authoritative selected-next order and exit criteria in
[the roadmap](../../docs/ROADMAP.md); this experiment record does not redefine
that sequence.
The behavior-neutral record-4 mismatch bitmap, both focused KUnit regressions,
the production Buildbox package, two independent DT compositions, two
independent Android-v0/LK constructions, negative mutations, and exact
pre-trigger oracle now pass. Distinct candidate `9b60b576...` is the only
selected physical attempt. Do not repeat `4b027c97...` or `58313c3a8...`.

The diagnostic wire plan keeps record 4 at its existing size and version.
Word 25 reserves bit 31 as the self-identifying bitmap-v1 marker; bits 0--23
separately identify null or invalid baseline/post captures, both CPU8 and CPU9
SPM status mirrors, both CCI-pending samples, MP2 cluster and CPU8 power-control
changes, external isolation, DCM, CCI request, provider, clock, and BIGIDVFS
changes. Legacy values `0` and `1` therefore remain unambiguous. The executor's
existing Boolean acceptance helper delegates to the bitmap being zero, while
record publication adds only the format marker. This changes observation, not
the CPU9-down decision, ordering, retry budget, or physical effects.

Exact Buildbox generation from pushed tooling commit `0aff272c...` produced
patch `0504` with SHA-256 `0931c1c3...`. Generation and replay both pass the
24-bit source contract, all ten unsafe mutations fail closed, strict patch
review passes, and the generated change contains no CPU request, MMIO write,
secure call, production trigger, or device action. The host decoder now names
bitmap-v1 terms while preserving legacy Boolean records and rejects unknown
bitmap bits. Kernel compile, focused runtime KUnit, production-package review,
candidate construction, and device action remain gated after patch admission.

Patch `0504` is now admitted at exact pushed commit `7ca200d6...`; all 173
manifest profiles retain canonical series order. Buildbox compiled the
493-patch executor and production-binding KUnit profiles from that commit.
The executor suite passes 9/9, including the new 24-term bitmap case and all
preserved decision/one-shot cases. The production binding also compiles and
its private-transition suite passes 9/9. Both runs used four-vCPU no-network
QEMU, invoked no production binding or physical backend, and performed no CPU
request, MMIO, I2C, retained-RAM, SMC, watchdog, device, or boot-candidate
action. The exact evidence is in
[`results/readback-bitmap-hardware-free-7ca200d6-20260903.txt`](results/readback-bitmap-hardware-free-7ca200d6-20260903.txt).
Exact production package commit `46539642...` and candidate `9b60b576...`
pass all offline gates; the exact evidence is in
[`results/readback-bitmap-candidate-46539642-20260903.txt`](results/readback-bitmap-candidate-46539642-20260903.txt).
Its guarded live-GPT deployment then wrote exact logical `boot2`, passed two
full readbacks, removed temporary files, and confirmed clean shutdown.

The sole physical selection passed the exact read-only pre-trigger gate on
fresh boot ID `4cae6d10...`. One trigger booted CPU8 and CPU9, then completed
one CPU9-down authorization and one affinity-off observation. CPU9 was absent
from Linux's online mask while CPU8 remained online and responsive, producing
online mask `0x1ff`. Record 4 retained generation 11, stage 12,
postcommit-down-fault `-EIO`, one CPU_OFF call, one affinity query, one CPU8
IPI, no CPU_ON restore, and bitmap `0x80002000`. The only named mismatch was
`post-status2-cpu9-present`: the primary SPM CPU-status word showed CPU9 off,
the secondary word still showed it present, and all other 23 comparisons
passed. The watchdog then returned the device automatically to fresh Gemian
boot ID `2a369fda...`; read-only recovery copied and strictly decoded record 4
without removing remote pstore data. This retires `9b60b576...` after its one
decision-bearing attempt.

The observation proves a single-sample disagreement between the two SPM CPU
power-status mirrors after architectural CPU9-off; it does not yet prove
whether the second mirror merely settles later or has different completion
semantics. The earlier live A72-off state already provides the decision: raw
CPU-status pairs `0x00350c08/0x00350cff` and
`0x003d8008/0x003d80ff` legitimately carry A72 bits in only the second word,
the hardware owner records “on” as the intersection of the two words, and
patch `0444` already applies that rule to A34. The executor's independent
absence rule was therefore stricter than the established platform contract.

The selected repair continues to require CPU8 in both words and rejects CPU9
when its bit is in both words. A CPU9 bit in only one raw word remains visible
in the unchanged bitmap but no longer fails the Boolean off proof when every
other term passes. No settling delay or third snapshot is added: the composed
snapshot includes bounded protected-clock transport writes, and its exact
two-call budget is already proven. The patch adds no CPU, PSCI, MMIO, I2C,
watchdog, retained-RAM, or device effect. Generate it from exact post-`0504`
Buildbox source, reject its mutations, then admit and compile it before any
new candidate. Three preliminary generator runs stopped before patch creation
on over-broad assertion or mutation anchors; the exact chronology is retained
in the definition result. Attempt 4 from pushed commit `4179b8d7...` passes
source validation, ten rejecting mutations, strict review, replay, and the
173-profile invariant. Generated patch `0505` is byte-identical to the fetched
Buildbox artifact at SHA-256 `1fb082ca...` and changes only the executor and
its focused test. Commit and push that exact admission, then compile and run
the executor and production-binding KUnit profiles before constructing a new
candidate. Do not repeat `9b60b576...` unchanged.

Patch `0505` is now admitted at exact pushed commit `32e50f48...`. Buildbox
compiled both the isolated executor and production-binding profiles from the
same 494-patch source identity `a1c6d67e...`. Their focused four-vCPU,
no-network QEMU suites each pass 9/9 with no skips. The executor gate preserves
the single CPU_OFF, affinity, post-state snapshot, and CPU8-observer budgets;
the production binding keeps the public disable veto closed and its private
CPU9-only transition linked but uninvoked. Neither run invoked a physical
backend or performed a CPU request, MMIO, I2C, retained-RAM, SMC, watchdog,
network, device, or boot-candidate action. The exact package and runtime
identities are retained in
[`results/intersected-status-hardware-free-32e50f48-20260903.txt`](results/intersected-status-hardware-free-32e50f48-20260903.txt).
The hardware-free repair gate is closed; one newly constructed and
independently validated production candidate is now permitted. Retired
candidate `9b60b576...` remains forbidden to repeat.

Exact production profile commit `1de95a69...` now passes Buildbox package
validation with the same `a1c6d67e...` 494-patch identity. Two independent
provenance-only DT compositions produce `48f7c194...`; both structural
validations pass and all ten DT mutations reject. Two independent Android-v0/LK
assemblies and padding paths are byte-identical, both validators pass all 32
LK gates and reject six container mutations, and the exact pre-trigger gate
rejects all eight unsafe mutations. The raw successor is `a7ac6ac0...`; exact
16 MiB inactive-`boot2` content is `a0114584...`. Its package, container,
hypothesis, and tooling identities are retained in
[`results/intersected-status-candidate-1de95a69-20260903.txt`](results/intersected-status-candidate-1de95a69-20260903.txt).
No device access or write occurred during construction. This distinct
candidate is selected for one guarded physical attempt after the exact tooling
and evidence are published.

The exact tooling and evidence were published at commit `32ed64bd...`. From
ordinary Gemian boot ID `2a369fda...`, the live GPT resolved inactive logical
`boot2` as `/dev/mmcblk0p30` while the active root remained
`/dev/mmcblk0p29`. Stable external power was present. One write replaced
retired predecessor `9b60b576...` with exact 16 MiB candidate `a0114584...`;
the write-path full readback, independent streamed full readback, and byte
comparison all pass. Temporary device and host readback files were removed,
no fresh partition backup was made, and the clean shutdown was followed by
three independent connection-refused observations. Sanitized deployment proof
is retained in
[`results/intersected-status-deployment-20260903.txt`](results/intersected-status-deployment-20260903.txt).
The device is off and ready for the owner to physically select `boot2`; the
host must capture and validate the read-only pre-trigger frame before spending
the candidate's single trigger.

The selected boot passed the exact pre-trigger gate on fresh boot ID
`58ddbcfe...`. One trigger booted CPU8 and CPU9, completed exactly one CPU9
CPU_OFF, one affinity-off observation, the intersected off proof, one retained
CPU8 callback, and generic Linux down-completion with online mask `0x1ff` and
A72 membership `0x1`. It then issued exactly one restore CPU_ON. The call
returned success, but CPU9 did not emit a second arm64 secondary-entry message
or become online before the five-second `__cpu_up()` timeout. Record 4 retained
generation 15, restore-fault `-EIO`, and `result_flags=0x7f7f`. Its terminal
`stage=16` names the next expected `secondary-complete` boundary; bit 15 is
clear, so it is not evidence that the checkpoint completed. The earlier CPU9
`Booted secondary processor` line belongs to initial admission before the
down/restore transaction.

The watchdog returned the device to fresh Gemian boot ID `0ababa54...`.
Read-only recovery copied and decoded record 4 without removing remote pstore
data. The exact runtime proof is retained in
[`results/intersected-status-runtime-attempt-1-restore-entry-timeout-20260903.txt`](results/intersected-status-runtime-attempt-1-restore-entry-timeout-20260903.txt).
This retires `a0114584...`: the off-status intersection repair worked, and the
next boundary is now restart readiness below secondary kernel entry. Do not
repeat this image.

The selected successor is a bounded, read-only restore-readiness observation
between completed CPU9 down and the sole CPU_ON. It must retain exact CPU9 SPM
status-mirror and per-core power-control samples, add no CPU_OFF, CPU_ON,
affinity, retry, provider, cluster, or watchdog call, and issue the existing
single CPU_ON only after its named readiness predicate passes. A timeout must
seal decision-bearing evidence without issuing CPU_ON. This distinguishes a
short post-off settling interval from a persistently different status/control
state before any behavioral repair is inferred.

The successor is frozen in
[`results/restore-readiness-definition-20260903.txt`](results/restore-readiness-definition-20260903.txt).
Its observer takes at most 51 existing platform-state snapshots separated by
at most 50 sleeps of 5--6 ms. It requires CPU8 in both mirrors throughout and
defines CPU9 restart readiness as absence from both mirrors. Record 4 format
v2 retains the first and last raw CPU status pair, CPU9 power-control word,
counts, flags, and error while preserving the 16-record ceiling. The maximum
successful-path retained write count becomes 611 words. No new CPU, firmware,
affinity, provider, cluster, watchdog, MMIO-write, retry, storage, or device
operation is introduced. Buildbox generation, mutation rejection, replay,
ledger/binding KUnit, and the all-profile invariant must pass before candidate
construction.

Buildbox generation from exact pushed commit `fc967bd2...` now passes source
validation, all 13 rejecting mutations, replay, and strict patch review. The
fetched patch is byte-identical to canonical patch `0506` at SHA-256
`e73e5d6c...`; it changes only the binding observer/tests and retained record-4
layout/tests. The 173-profile series invariant passes with 495 canonical
patches. Three preliminary runs stopped before patch creation because their
validators did not yet pin exact field, zero-CPU_ON, or public-bound clauses;
their chronology is retained with the successful package in
[`results/restore-readiness-generation-fc967bd2-20260903.txt`](results/restore-readiness-generation-fc967bd2-20260903.txt).
No device action occurred and this is not yet a boot candidate. Commit and
push the exact admission, then compile and run the binding and ledger KUnit
profiles on Buildbox before constructing any physical candidate.

The exact admission and updated fail-closed QEMU classifiers are published at
commits `0f51cfeb...` and `5e219ac7...`. Buildbox compiled the binding and
record-4 ledger profiles from the same 495-patch source identity
`c49b822e...`. Their focused four-vCPU, no-network suites pass 13/13 and 14/14
with no skips. The former proves immediate readiness, delayed settling,
timeout, and CPU8-mirror rejection; the latter proves that a readiness timeout
is valid only with zero CPU_ON calls and enforces the v2 retained-layout
limits. Neither suite invoked a physical backend or performed a CPU request,
MMIO, I2C, SMC, watchdog, retained-RAM, network, device, or boot-candidate
action. Exact package and runtime identities are retained in
[`results/restore-readiness-hardware-free-5e219ac7-20260903.txt`](results/restore-readiness-hardware-free-5e219ac7-20260903.txt).
The hardware-free gate is closed; one newly built and independently validated
production candidate is now permitted.

Exact production commit `819d8f0d...` now passes Buildbox package validation
with the 495-patch `c49b822e...` source identity. Two independent
provenance-only DT compositions produce `902762c2...`; both structural
validators pass and all ten DT mutations reject. Two independent Android-v0/LK
assemblies and padding paths are byte-identical, both validators pass all 32
LK gates and reject six container mutations, and the exact pre-trigger gate
rejects all eight unsafe mutations. The raw successor is `f411b55d...`; exact
16 MiB inactive-`boot2` content is `44e1b42c...`. Its package, container,
readiness hypothesis, and tooling identities are retained in
[`results/restore-readiness-candidate-819d8f0d-20260903.txt`](results/restore-readiness-candidate-819d8f0d-20260903.txt).
No device access or write occurred during construction. This distinct
candidate is selected for one guarded physical attempt after the exact tooling
and evidence are published; retired `a0114584...` must not be repeated.

The exact candidate tooling and evidence were published at commit
`cfec141d...`. From ordinary Gemian boot ID `0ababa54...`, the live GPT
resolved inactive logical `boot2` as `/dev/mmcblk0p30` while the active root
remained `/dev/mmcblk0p29`. Stable external power was present. One write
replaced retired predecessor `a0114584...` with exact 16 MiB readiness-gated
candidate `44e1b42c...`; the write-path full readback, independent streamed
full readback, and byte comparison all pass. Temporary device and host
readback files were removed, no fresh partition backup was made, and the clean
shutdown was followed by three independent connection-refused observations.
Sanitized deployment proof is retained in
[`results/restore-readiness-deployment-20260903.txt`](results/restore-readiness-deployment-20260903.txt).
The device is off and ready for the owner to physically select `boot2`; the
host must capture and validate the read-only pre-trigger frame before spending
the candidate's single trigger.

The selected boot then passed the exact pristine pre-trigger gate on fresh
mainline boot ID `0fac39d7...`. One trigger again brought CPU8 and CPU9 through
their independent initial admission proofs, completed one CPU9 CPU_OFF and
affinity-off observation while retaining CPU8, and entered the new readiness
observer. All 51 samples and 50 bounded sleeps completed. In the first and
last samples CPU9 was absent from primary `CPU_PWR_STATUS`, remained present
in `CPU_PWR_STATUS_2ND`, and its per-core power-control word remained
`0x10332`; CPU8 remained present in both mirrors. The observer therefore timed
out with `-ETIMEDOUT` and record 4 retained exactly zero CPU_ON calls, online
mask `0x1ff`, membership `0x1`, and the persistent-secondary mismatch. This
rejects the short-settling explanation without reissuing the failed restore.

The watchdog returned the device to fresh Gemian boot ID `7ab26b12...`.
Read-only recovery copied and decoded record 4 without removing remote pstore
data. The exact runtime proof is retained in
[`results/restore-readiness-runtime-attempt-1-persistent-secondary-20260903.txt`](results/restore-readiness-runtime-attempt-1-persistent-secondary-20260903.txt).
This retires `44e1b42c...`; do not repeat it. The next experiment must not
merely wait longer or restore the earlier intersection behavior without new
evidence. First trace the exact generic arm64, PSCI, and secure restart call
boundary. Then hardware-free-prove a durable checkpoint immediately after the
sole CPU_ON returns, retaining the pre/post CPU9 status mirrors and per-core
power-control state. A later distinct physical candidate is justified only if
that observation can distinguish firmware refusal, no power transition,
power-on without arm64 secondary entry, and successful secondary entry.

That exact static trace found a stronger, pre-CPU_ON repair boundary. Initial
CPU9 admission prepares and arms its dedicated P30E MMU-off slot; the mandatory
`secondary_entry` claim consumes it and successful controller readback proves
target state `PUBLISHED` with sequence 1. The ordinary CPU9-down path has no
P30E transition. The private restore path calls the saved generic PSCI boot
callback directly, bypassing the CPU9 admission binder and its P30E arm. On the
second entry, the target claim therefore sees an already-published slot,
publishes failure reason 5, returns `-EPROTO`, and `head.S` parks CPU9 before
`secondary_startup`. This matches the earlier successful CPU_ON return, absent
second CPU9 boot message, and five-second `__cpu_up()` timeout. The hash-pinned
control-flow evidence is retained in
[`results/p30e-restore-root-cause-audit-20260903.txt`](results/p30e-restore-root-cause-audit-20260903.txt).

The selected repair keeps that target-side fail-closed behavior unchanged. A
new controller helper will rearm only CPU9's exact intact initial request after
the proven down/readiness state and before the existing sole restore CPU_ON. It
must validate the complete identity, state, sequence, result, entry, and CRC
contract; reconstruct the same request as an empty target at controller
sequence 2; reject every mismatch before writing; and reject a second rearm.
The private executor will retain a distinct `P30E_REARMED` checkpoint, fail
with zero CPU_ON calls if rearm fails, and preserve the one-CPU_ON/no-retry
ceiling. The frozen definition and required negative tests are in
[`results/p30e-rearm-definition-20260903.txt`](results/p30e-rearm-definition-20260903.txt).
Post-CPU_ON platform sampling is deferred unless this exact lifecycle repair
still fails. No new candidate is allowed before Buildbox generation, rejecting
mutations, replay, focused P30E/executor/binding KUnit, series-ordering, and
production validation pass.

Buildbox generation from exact pushed commit `00f60e75...` now passes against
prepared source state `abcf6814...`. The two fetched patches are byte-identical
to canonical `0507` and `0508` at SHA-256 `f6085065...` and `6ca416f0...`;
their primitive and final validators reject 14 and 25 mutations. The repair
adds no target-claim or `head.S` change, keeps one restore CPU_ON and zero
retries, and records its new checkpoint under ledger semantic version 3 rather
than reinterpreting historical version-2 evidence. The version-aware decoder's
17 hardware-free tests pass, and all 174 manifest profiles retain canonical
ordering across 497 patches. Exact generation and admission facts are retained
in
[`results/p30e-rearm-generation-00f60e75-20260903.txt`](results/p30e-rearm-generation-00f60e75-20260903.txt).
This is not a boot candidate and no device action occurred. The next gate is
Buildbox compilation plus focused no-network P30E, executor, binding, and
record-4 ledger KUnit; no physical boot is justified until all four pass.

That hardware-free gate is now closed on final exact commit `0b9fbb44...` and
498-patch identity `f6af5dea...`. Buildbox compiled all four profiles, and
focused no-network QEMU runs passed P30E 2/2 with 21 rejecting mutations,
executor 11/11, production binding 14/14, and record-4 ledger 14/14. The first
ledger run on implementation commit `9acd1e65...` correctly exposed a stale
success fixture that still marked stage 17 terminal after v3 inserted the
P30E-rearmed stage; test-only patch `0509` makes the fixture exercise all 17
records and seal at stage 18. The final run is green, and the defect was not in
the production path. No physical backend, CPU request, MMIO, I2C, retained-RAM,
SMC, watchdog, network, device, or boot-candidate action occurred. Exact build,
runtime, and failure/correction identities are retained in
[`results/p30e-rearm-hardware-free-0b9fbb44-20260903.txt`](results/p30e-rearm-hardware-free-0b9fbb44-20260903.txt).
One newly built and independently validated production candidate is now the
next permitted step.

Exact production commit `d2161a1e...` now passes Buildbox package validation
with the final 498-patch `f6af5dea...` source identity. Two independent
provenance-only DT compositions are byte-identical at `1396b2e8...`; both
independent validators pass and all ten structural mutations reject. Two
independent Android-v0/LK assemblies and padding constructions are
byte-identical, both validators pass all 32 LK gates and reject all six
container mutations, and the exact pre-trigger gate rejects all eight unsafe
mutations. The raw successor is `c1cf7d7a...`; exact 16 MiB inactive-`boot2`
content is `7ffd60d0...`. Production `System.map` contains exactly one
`arm64_mt6797_a72_p30e_rearm_cpu9`, while KUnit and split-startup policy are
absent. Exact package, composition, container, hypothesis, decision map, and
tool identities are retained in
[`results/p30e-rearm-candidate-d2161a1e-20260903.txt`](results/p30e-rearm-candidate-d2161a1e-20260903.txt).
No device access or write occurred during construction. This distinct
candidate is selected for one guarded deployment after these exact tools and
evidence are published; predecessor `44e1b42c...` remains retired.

The exact tooling and candidate record were published at commit
`5274d0f3...`. From ordinary Gemian boot ID `7ab26b12...`, the guarded live
GPT probe resolved inactive logical `boot2` as `/dev/mmcblk0p30` while the
active root remained `/dev/mmcblk0p29`; stable external power was present.
One write replaced retired predecessor `44e1b42c...` with exact P30E-rearm
candidate `7ffd60d0...`. The write-path full readback, independent streamed
full readback, and byte comparison all pass. Temporary device and host
readbacks were removed, no fresh partition backup was made, and clean
shutdown was followed by confirmed unreachability. Sanitized deployment proof
is retained in
[`results/p30e-rearm-deployment-20260903.txt`](results/p30e-rearm-deployment-20260903.txt).
The device is off and ready for the owner to select `boot2`; no trigger may be
issued until the fresh read-only pre-trigger frame passes the exact validator.

The sole P30E-rearm physical attempt then closed the hardware restore boundary.
The fresh pre-trigger frame passed, the one trigger admitted CPU8 and CPU9,
offlined CPU9 once while retaining CPU8, rebuilt the exact P30E request at
sequence 2, and started CPU9 a second time. The live post-trigger frame showed
CPUs `0-9` online. Changed-ID Gemian recovery yielded a valid v3 record 4 at
stage 18, terminal `restored-success`, error zero, membership `0x3`, online
mask `0x3ff`, and exactly one CPU_OFF, affinity query, CPU8 IPI, and restore
CPU_ON. A read-only recovery check also confirmed that `boot2` still matches
`7ffd60d0...`.

The outer one-shot controller nevertheless reported `-EPROTO` after that
successful retained terminal publication. Static narrowing shows that the
remaining ambiguity is confined to the hotplug-binder return path after the
restore executor has completed; the current status ABI does not expose enough
of that private binder result to distinguish the `add_cpu()` return,
transaction revalidation, binder checkpoint, and terminal-return branches.
The candidate is retired and must not be repeated unchanged. The next
permitted candidate adds one bounded terminal binder diagnostic, changes no
CPU/firmware request budget, and exists solely to identify that post-success
branch. Exact runtime identities and the frozen next decision are retained in
[`results/p30e-rearm-runtime-attempt-1-restored-postsuccess-protocol-20260903.txt`](results/p30e-rearm-runtime-attempt-1-restored-postsuccess-protocol-20260903.txt).

Patch `0510` implements exactly that diagnostic without changing the restore
effect, firmware-call, or retry budgets. Its focused no-network binder-core
KUnit suite passes 9/9, and exact production commit `35170505...` passes
Buildbox package validation with 499-patch identity `a7cbb2da...`. Two
independent provenance-only DT compositions agree at `959247f1...`; two
independent Android-v0/LK builds agree on raw `fd015493...` and exact 16 MiB
candidate `fe333d46...`. Both independent validators pass all 32 LK gates and
reject six mutations; the DT and pre-trigger suites reject ten and eight
mutations respectively. The production image contains exactly one bounded
`GEMINI_A72_HOTPLUG_BINDING_V1` format and no KUnit or split-startup policy.
Construction used no device and performed no hardware write. Exact package,
candidate, decision-map, and tool identities are retained in
[`results/postsuccess-diagnostic-candidate-35170505-20260903.txt`](results/postsuccess-diagnostic-candidate-35170505-20260903.txt).
After publication, this distinct candidate is selected for one guarded
inactive-`boot2` deployment, full readback, clean shutdown, and one physical
attempt. The expected hardware sequence remains the already proven P30E
restore; the sole new observation is the terminal binder line that selects
the exact remaining software branch.

The candidate tooling and evidence were published at `2fdd1a5d...`. Guarded
deployment from Gemian boot ID `915ff15c...` resolved inactive logical
`boot2` as `/dev/mmcblk0p30` while the active root remained p29 and stable
external power was present at full capacity. One write replaced retired
`7ffd60d0...` with exact diagnostic `fe333d46...`; the write-path and
independently streamed full readbacks match, the byte comparison passes,
temporary files were removed, no fresh backup was made, and clean shutdown
was confirmed by SSH unreachability. Sanitized evidence is retained in
[`results/postsuccess-diagnostic-deployment-20260903.txt`](results/postsuccess-diagnostic-deployment-20260903.txt).
The device is off for one owner-selected `boot2` attempt. The trigger remains
forbidden until the fresh read-only frame passes the exact candidate and
record-identity gate.

The one diagnostic attempt then reproduced the successful hardware path and
resolved the remaining software branch. After two interactive-shell prompt
artifacts were rejected without a trigger, a PS1/PS2-suppressed pre-trigger
frame passed and the sole trigger booted CPU8, booted CPU9 twice across the
bounded down/restore transaction, and left CPUs `0-9` online. The terminal
binder line reported `add_cpu_ret=0`, valid restore revalidation, restore
completion at stage 18, and `p30e_rearmed=1`, but the outer binder attempted
its post-restore checkpoint with private stage 17 and returned `-EPROTO` with
`completed=0`. Changed-ID Gemian recovery corroborated a valid restored-success
record 4 at stage 18, error zero, online mask `0x3ff`, and unchanged boot2.

The exact source audit found stage-identity drift: patch `0507` inserted the
public `P30E_REARMED` stage and shifted `RESTORE_COMPLETE` from 17 to 18, while
the disconnected binder core and its mock both retained a private literal 17.
That shared stale macro made the focused mock pass while the production ledger
correctly rejected the physical checkpoint. Patch `0511` is the selected
minimal repair: bind all three private binder checkpoint tokens to the public
ledger symbols and assert those mappings directly. It changes no CPU,
firmware, retry, or retained-record budget. Exact attempt identities, rejected
transport frames, terminal fields, pstore corroboration, and the selected fix
are retained in
[`results/postsuccess-diagnostic-runtime-attempt-1-stage-drift-20260903.txt`](results/postsuccess-diagnostic-runtime-attempt-1-stage-drift-20260903.txt).
No further physical attempt is permitted until the patch and evidence are
published and the exact Buildbox binder-core and binding KUnit gates pass.

Canonical patch `0511` is now present in the exact production source and
passes the two required hardware-free gates: binder-core 9/9 with checkpoint
stages `1,13,18`, and binding 14/14. Exact production commit `8ae7643c...`
passes Buildbox package validation with 500-patch identity `41345620...`.
Two independent provenance-only DT compositions agree at `ecf27851...`; two
independent Android-v0/LK builds agree on raw `09c4f0b7...` and exact 16 MiB
candidate `c84aea47...`. Both independent validators pass all 32 LK gates and
reject six container mutations; the DT and pre-trigger suites reject ten and
eight mutations respectively. Construction invoked no physical backend or
device action. Exact package, KUnit, candidate, tool, hypothesis, and decision
identities are retained in
[`results/stage-binding-fix-candidate-8ae7643c-20260903.txt`](results/stage-binding-fix-candidate-8ae7643c-20260903.txt).
After publication, this distinct candidate is selected for one guarded
inactive-`boot2` deployment, two full readbacks, clean shutdown, and one
physical attempt. The expected result is the already proven CPU8/CPU9
down/restore path with binder `ret=0`, `completed=1`, and stage 18; an
unexpected result must be recovered and classified before any new attempt.

The candidate tooling and evidence were published at `b25775a9...`. From
ordinary Gemian boot ID `d7363598...`, the guarded live-GPT probe resolved
inactive logical `boot2` as `/dev/mmcblk0p30` while the active root remained
`/dev/mmcblk0p29`; stable external power was present at full capacity. One
write replaced retired diagnostic `fe333d46...` with exact stage-binding fix
`c84aea47...`. The write-path full readback, independent streamed full
readback, and byte comparison all pass. Temporary device and host data were
removed, no fresh backup was made, and clean shutdown was confirmed by SSH
unreachability. Sanitized deployment proof is retained in
[`results/stage-binding-fix-deployment-20260903.txt`](results/stage-binding-fix-deployment-20260903.txt).
The device is off for one owner-selected `boot2` attempt. No trigger may be
issued until its fresh read-only frame passes the exact candidate and A41
record-identity gate.

That exact attempt succeeded. A prompt-suppressed read-only frame passed on
fresh mainline boot ID `7dc6b121...`; one trigger then booted CPU8, booted
CPU9 initially and once more after the bounded CPU9-only down transaction,
and left CPUs `0-9` online. The terminal binder diagnostic returned zero with
`completed=1`, public and private stage 18, valid restore revalidation, and no
stage or publication error. Changed-ID Gemian recovery independently yielded
a valid v3 record 4 sealed `restored-success` at stage 18 with error zero,
membership `0x3`, online mask `0x3ff`, and exactly one CPU_OFF, affinity
query, retained-CPU8 IPI, and restore CPU_ON. The symbolic stage-binding fix
therefore closes the CPU8/CPU9 bring-up transaction and its software
completion-accounting boundary. Exact runtime and recovery identities are in
[`results/stage-binding-fix-runtime-attempt-1-success-20260903.txt`](results/stage-binding-fix-runtime-attempt-1-success-20260903.txt).

This is one successful transaction, not yet a repeatability, stress, thermal,
suspend, or general hotplug-stability claim. Post-run DT comparison also found
that the provenance-only composition used the older flat serviceability base
`1478f2c8...` and therefore omitted the canonical `/cpus/cpu-map` already
present in both the package DT and proven topology-serviceability DT
`4b05758f...`. The only substantive topology-serviceability delta is that
4+4+2 map and its ten CPU phandles, so the successful candidate must not be
repeated unchanged. **Selected next:** compose the same proven kernel and A41
identity over `4b05758f...`, independently prove that exact DT delta, and use
one fresh boot for stage-18 repeatability plus exact cluster0 CPU0-3,
cluster1 CPU4-7, cluster2 CPU8-9 topology, without stress. Only after that
passes may the same topology-preserving artifact receive one separate bounded
load/coherency attempt.

That topology-preserving successor is now constructed without rebuilding or
changing the proven kernel package. Two independent compositions retain exact
package commit `8ae7643c...`, A41 identity `d4940602...`, and the previously
accepted topology-serviceability base `4b05758f...`; they are byte-identical
at `1f34ddb9...`. Independent structural validation proves the final delta is
that topology/serviceability tree plus one exact package A41 leaf, confirms
clusters CPU0-3, CPU4-7, and CPU8-9, and rejects all 13 mutations, including
three topology mutations. Two independent Android-v0/LK builds are
byte-identical at raw `e02bfd85...` and exact 16 MiB `6ba8c953...`; both pass
all 32 LK gates and reject all six container mutations. The pristine
pre-trigger suite rejects eight mutations, and the no-load stage-18/topology
classifier accepts its success fixture and rejects seven mutations. Exact
identities and decisions are retained in
[`results/topology-repeat-candidate-8ae7643c-20260903.txt`](results/topology-repeat-candidate-8ae7643c-20260903.txt).

No device or physical backend was used during construction, and no native VM
build occurred. This is not a new kernel-build claim: it deliberately reuses
the exact already-validated Buildbox package and changes only the DT/container
composition needed to restore the canonical CPU map. **Selected next:**
publish the tooling and candidate record, then deploy exact `6ba8c953...` to
live-GPT-resolved inactive `boot2`, require both full readbacks, and shut the
device down. One fresh owner-selected boot may then execute the sole lifecycle
trigger and read only the ten topology views; load remains explicitly absent.

The exact tooling and candidate record were published at `b0555b9d...`.
Guarded deployment from ordinary Gemian boot ID `89680616...` resolved the
sole inactive logical `boot2` as `/dev/mmcblk0p30` while active root remained
p29 and stable external power was present at full capacity. One write replaced
successful retired predecessor `c84aea47...` with topology-preserving
`6ba8c953...`. The post-flush target checksum and an independently streamed
full-partition readback both match, the independent byte comparison passes,
temporary files were removed, and no fresh backup was made. Clean shutdown was
confirmed by unreachability. Sanitized deployment proof is retained in
[`results/topology-repeat-deployment-20260903.txt`](results/topology-repeat-deployment-20260903.txt).

The device is off for one owner-selected `boot2` attempt. The first host action
after USB/netcat appears must be the exact read-only pre-trigger capture and
validation. Only a pristine, fresh frame permits the single no-load lifecycle
trigger and ten-CPU topology readback; no retry or substitute artifact is
allowed.

That exact no-load repeat passed on its first and only trigger. Fresh mainline
boot ID `c1bd9a56...` passed the read-only identity and zero-execution gate;
CPU8 entered once, CPU9 entered before and after exactly one CPU9-only down,
the binder completed at public and private stage 18 with return zero, and CPUs
`0-9` remained online. All ten live topology views reported package siblings
`0-9`, cluster lists `0-3`, `4-7`, and `8-9`, cluster-local core IDs, and
self-only thread siblings. No load, storage access, retry, or manual reboot was
requested. Changed-ID Gemian recovery independently decoded record 4 as
terminal `restored-success`, stage 18, error zero, members `0x3`, online mask
`0x3ff`, and exactly one CPU_OFF, affinity, CPU8 IPI, and CPU_ON call; the live
GPT `boot2` checksum remained exact `6ba8c953...`. The full identities are in
[`results/topology-repeat-runtime-attempt-1-success-20260903.txt`](results/topology-repeat-runtime-attempt-1-success-20260903.txt).

This proves the complete stage-18 transaction on two fresh boots and proves
that the topology-preserving composition retains it. It does not yet test this
exact artifact under load. **Selected next:** source-pin and offline-mutate one
boot-ID-bound integrated trigger that first requires the same stage-18 and
4+4+2 result, then immediately performs the already-proven finite dual-A72
volatile-RAM exchange with exact affinity, independent accounting, four
matching hashes, and cleanup. Permit one boot of unchanged `6ba8c953...` only
after that combined classifier and forbidden-action audit pass; no duration
increase, CPU_OFF beyond the one lifecycle transaction, retry, storage write,
or manual reboot is admitted.
