# Mainline A72 physical-hotplug lifecycle gate

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-02-mainline-a72-hotplug-lifecycle-gate` |
| Status | all disconnected prerequisites including CPU9 restore proven; one-task down/restore binder pending |
| Subsystem | arm64 CPU hotplug, PSCI, MT6797 A72 membership |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-09-02 America/New_York |
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
- Boot path and target: none in this definition phase.

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
  package and require all ten in-memory record-4 cases to pass.
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

Patches `0483`--`0496` are experiment-only archives with a synthetic,
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

The physical hypothesis remains untested. The exact parent code is confirmed
incapable of safely running the experiment as-is. Patch `0483` supplies and
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
isolated runtime cases pass. All disconnected prerequisites are therefore
complete. The remaining software gate is the one-task production binder that
owns the complete down/restore transaction. Only after that binder passes may
a separate candidate commit select one physical CPU9-off and same-boot CPU9
restore attempt.

## Follow-up

The parent-proof, watchdog-validator, record-4, snapshot, bounded CPU8
observer, and CPU9 restore prerequisites are complete and must remain fixed.
Continue under the authoritative selected-next order and exit criteria in
[the roadmap](../../docs/ROADMAP.md); this experiment record does not redefine
that sequence.
The selected next slice is the disconnected one-task down/restore binder. CPU8
and CPUs 0--7 stay non-disableable throughout. No candidate or device boot is
selected until the complete binding passes exact replay, rejecting mutations,
Buildbox compile, and no-network runtime review.
