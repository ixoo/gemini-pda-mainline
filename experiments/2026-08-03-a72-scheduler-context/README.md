# Experiment: CPU8/CPU9 scheduler-context execution

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-03-a72-scheduler-context` |
| Status | `attempt-1-pass-repeat-earned` |
| Subsystem | MT6797 retained Cortex-A72 pair and scheduler |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-03 through 2026-08-05 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 8 scheduler-context execution |

## Question or hypothesis

After reproducing the exact pair-v6 startup and coherency/load gates, can one
normal-priority kernel thread bound to CPU8 and one bound to CPU9 both be
dispatched in task context, rendezvous concurrently, finish identical bounded
integer workloads on their assigned CPUs, and exit cleanly before the retained
watchdog recovery?

## Provenance and environment

- Exact parent experiment:
  `2026-08-03-a72-cpu9-parallel-disjoint-load`.
- Exact parent repository compile commit:
  `ad7807ccc50bebd0aaeafcbe4dadb4c11c44b850`.
- Exact parent parallel patchset SHA-256:
  `94d3b07355e1ddb67f3f643165570255bb1f42131b3b67c074d270e8581989e2`.
- Exact parent full boot2 SHA-256:
  `0beead0b00485ad18333aca4d688fcd549c813113b7ec0554a6761c7147b17fb`.
- Parent runtime: two complete pair-v6 passes with identical deterministic
  hashes, 128/128 rounds per CPU, 1,048,576 exact cross-CPU checks per cycle,
  safe changed-cycle watchdog recovery, offline recovery CPUs 8/9, and
  unchanged boot2.
- Kernel thread API reference: exact upstream Linux v7.1 `kernel/kthread.c`
  and `include/linux/kthread.h`.
- Build backend: Buildbox only; no native VM kernel build.
- The generated successor patch retains a synthetic, non-certifying `From:`
  identity without a `Signed-off-by`. This experiment-only archive is
  explicitly not submission-ready.
- Attempt-1 source-generation repository commit:
  `53307958dcbd715039e5cbab326b0094488d7c90`.
- Exact reconstructed parent commit:
  `0bbc78db41f0334550232ad9b56734d57721faf3`.
- Attempt-1 generated scheduler source commit:
  `d62f75d8a2f1759bdffc4f318303ed613fb2760f`.
- Attempt-1 generated patch SHA-256:
  `ed2abf428ec51af4614b9e9adb94a1a12b9333224868a241a0525139f85e6625`.
- Attempt-1 scheduler patchset SHA-256:
  `30316bc63934d7fdc022367bb8b465e794c8c91ec9956d6233e02bddad55fffe`.
- Attempt-1 stable patch ID:
  `9e4f5361be7ef72f8eb11f289827ec7e6370e764`.
- Compile attempt 1 built both exact sources but failed the stack acceptance
  boundary; no accepted compile review, container, deployment, or runtime claim
  exists yet.
- Accepted compile repository commit:
  `697ac3984c9b52c285cb7fcdb076dcec4dbf8ef0`.
- Accepted `Image.gz-dtb` SHA-256:
  `9d2d9db5bd66bcc33c7c072248b5d907b75e5ceb8bf810c88bfd0019e128f402`.

## Safety assessment

The child may add only one finite task-context phase after every pair-v6 parent
predicate passes. It must not alter CPU startup, HPS veto/timing, CPU_OFF
prohibition, watchdog, power sequencing, clocks, reset, MMIO, regulator state,
sample timing, or recovery. It creates exactly two normal-priority kernel
threads, binds them before activation to CPUs 8 and 9, bounds all internal waits
and work, stops both before publication, and treats incomplete cleanup as a
terminal fault. The retained watchdog remains the independent recovery bound.

## Associated code

- [`DESIGN.md`](DESIGN.md): historical exact lifecycle, workload, task-context
  oracle, bounds, terminal, result classes, and invariants for the rejected
  wake-based child.
- [`DESIGN-UNPARK.md`](DESIGN-UNPARK.md): bounded successor contract correcting
  only parked-thread activation and its evidence schema.
- [`scripts/source_edits.py`](scripts/source_edits.py): deterministic exact-
  parent scheduler-context transformation.
- [`scripts/test_static.py`](scripts/test_static.py): inherited-boundary,
  lifecycle, hash-vector, safety-inventory, and negative-mutation validator.
- [`scripts/unpark_edits.py`](scripts/unpark_edits.py): deterministic one-path
  activation correction for the exact rejected phase-attribution source.
- [`scripts/test_unpark_child.py`](scripts/test_unpark_child.py): exact-parent
  equivalence, lifecycle-source, schema, ordering, and negative-mutation
  validator for the unpark child.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox): clean-pushed-
  commit reconstruction of the exact phase parent and one-patch unpark
  successor generator.
- [`scripts/build-on-buildbox`](scripts/build-on-buildbox): Buildbox-only
  unpark child versus exact rejected phase parent compile, diagnostics,
  lifecycle/call-target disassembly, and stack comparison.
- [`scripts/assemble.py`](scripts/assemble.py): pinned pair-v6 Android-v0
  assembler specialization for the exact unpark kernel.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh): reproducible,
  offline-only candidate construction with two raw and padded constructions.
- [`scripts/test_candidate.py`](scripts/test_candidate.py): independent tool,
  inventory, manifest, Android-v0, extent, image-ID, ramdisk, padding,
  provenance, offline-only, and negative-mutation validator.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh): exact predecessor,
  live-GPT target, inactive/unmounted, full-readback, cleanup, and clean-shutdown
  deployment contract.
- [`scripts/capture-live-outcome.sh`](scripts/capture-live-outcome.sh): optional
  read-only USB/netcat capture of numbered complete phase/pair snapshots.
- [`scripts/validate_phase_capture.py`](scripts/validate_phase_capture.py):
  exact-occurrence, source-order, monotonic-snapshot, success/fault, and
  transport-truncation validator for the captured USB format.
- [`scripts/test_runtime_tools.py`](scripts/test_runtime_tools.py): installer,
  no-backup, shutdown, read-only collector, and decision-map validator.
- [`patches/series`](patches/series): exact historical phase parent followed by
  the generated experiment-only unpark child.

## Procedure

1. Freeze the design and exact parent identities.
2. Generate one deterministic exact-parent source patch on Buildbox.
3. Reject lifecycle, affinity, bound, cleanup, parent-gate, and terminal
   mutations before compilation.
4. Compile child and exact parent on Buildbox and compare configuration,
   diagnostics, binary boundaries, and stack.
5. Reproduce and independently validate an Android-v0 boot2 container.
6. Commit and push exact deployment/runtime tooling before device access.
7. Install only through the guarded live-GPT boot2 helper, verify full readback,
   and shut down.
8. Run one attributable boot under a fixed decision map; repeat only if that map
   earns a decision-changing repeat.

## Observations

- Buildbox source generation from repository commit
  `1d3d8911b75d5ace78ffd05f83bec69384b178b0` reconstructed and validated the
  exact pair-v6 parent, then rejected the child before patch publication. The
  static validator incorrectly searched the C format string for the rendered
  value `sc_reported=1`; the source correctly contains `sc_reported=%d`. No
  patch package survived validation, and no compile or device action occurred.
- The retry from commit `9aead87c4fbdf3a7f2b5e8f22025d10d70e21c46`
  reached the pointer-cleanup inventory and exposed a second validator-only
  assumption: reset, create-error cleanup, and post-stop cleanup produce three
  legitimate clears per CPU, not two. The validator was tightened to inventory
  all three and require stop-then-clear adjacency. Again, no patch package,
  compile, or device action occurred.
- The retry from commit `4df04b0e951cc917ef6d25eab753ec75a93cd10d`
  reached the negative-mutation suite. Its changed recurrence constant was not
  rejected because the independently recomputed hash vectors were not yet tied
  to the exact source recurrence. The validator now requires the full recurrence
  function body. No patch package, compile, or device action occurred.
- The retry from commit `a82c15d668bb07e3c9c174c58b1a24cf40ace8c4`
  showed that the recurrence mutation changed an identical constant in inherited
  pair-v6 code rather than the uniquely named scheduler function. The mutation
  target is now scoped to the full scheduler-function prefix. No patch package,
  compile, or device action occurred.
- Buildbox generation from commit
  `5efae676bfdf568c99c19c7f3e6bb0ee0d6f64de` passed the inherited pair-v6
  validator, both scheduler hash vectors, all 22 scheduler negative mutations,
  generated-source validation, changed-path inventory, and package checksums.
  The accepted package contains one patch changing only
  `arch/arm64/kernel/psci.c`; it remains source-review-only and performed no
  compile or device action.
- Buildbox compile attempt 1 from repository commit
  `32056dde05e24cbb3d478579d6bbad298032c750` compiled the scheduler child and
  exact pair-v6 parent, then rejected the child because
  `mt6797_a72_hold_workfn` used 1,056 bytes of static stack, above the
  1,024-byte boundary. The cause was two scheduler result structures copied
  onto that worker's stack. No package was accepted and no device action
  occurred. See
  [`results/compile-attempt-1-stack-reject-20260803.txt`](results/compile-attempt-1-stack-reject-20260803.txt).
- Stack-safe generation from commit
  `0e1140b887db1ef04fe9b7dbb12e857cd1cefa64` passed both hash vectors and all
  23 negative mutations. Local patch review found only misaligned continuation
  indentation in the pointer-snapshot signature; that source-only package was
  not admitted or compiled, and no device action occurred.
- Final generation from commit
  `d9dd2f9e95cfed30aa322da672083d969a70fe8a` passed exact pair-v6 validation,
  both hash vectors, all 23 negative mutations, changed-path inventory, and
  package checksums. The admitted patch uses immutable static-result pointers
  and contains no result-structure copy on the terminal stack.
- Buildbox compile attempt 2 from repository commit
  `eba35a959d6fe69f46f9b2fa08feb7a543f03757` compiled both exact sources and
  passed source, symbol, disassembly, and terminal checks before rejecting
  `mt6797_a72_hold_workfn` at 1,072 bytes. Isolating result storage alone did
  not restore the 1,024-byte boundary; the enlarged all-in-one terminal argument
  list remained in the parent worker. The next revision preserves pair-v6
  byte-for-byte and emits pair-v7 through a separate `noinline` reporter. No
  package was accepted and no device action occurred. See
  [`results/compile-attempt-2-terminal-stack-reject-20260803.txt`](results/compile-attempt-2-terminal-stack-reject-20260803.txt).
- Isolated-terminal generation from commit
  `53307958dcbd715039e5cbab326b0094488d7c90` preserved the two complete pair-v6
  terminals, added one no-inline pair-v7 reporter, passed both hash vectors and
  all 25 negative mutations, and produced a one-file checksum-verified patch.
  No compile or device action occurred.
- Buildbox compile from repository commit
  `697ac3984c9b52c285cb7fcdb076dcec4dbf8ef0` built the scheduler child and
  exact pair-v6 parent. Their diagnostics were identical, CPU9 startup source
  was unchanged, all 25 negative mutations were rejected, and the source,
  symbol, disassembly, terminal, package, and configuration checks passed. The
  accepted stack use is 784 bytes for the inherited parent worker, 176 bytes
  for the isolated reporter, and 96 bytes for each scheduler thread, all below
  the 1,024-byte boundary. This is compile-review evidence only; no container
  or device action occurred. See
  [`results/compile-review-20260803.txt`](results/compile-review-20260803.txt).
- Two independent offline candidate roots each performed two raw assemblies and
  two padded constructions. All copies are byte-identical and both independent
  validations passed. The accepted raw Android-v0 SHA-256 is
  `f9fddf01576aa6915c030b1952b290d937ef9a0ba9512a6adb0ab02de2e5fff3`;
  the exact 16 MiB boot2 SHA-256 is
  `24377665fa5b9112266890844c06c453bb50e17680b6f6f956035c234c26ff0f`.
  No device was accessed. See
  [`results/offline-container-review-20260803.txt`](results/offline-container-review-20260803.txt).
- The deployment and runtime tools reject four installer identity mutations,
  preserve the exact live-GPT/inactive/unmounted/readback/shutdown gates, keep
  the USB/netcat collector read-only, and require adjacent complete pair-v6 and
  pair-v7 terminals. The decision map fixes all scheduler lifecycle values and
  exact hashes before device access. No deployment occurred. See
  [`results/runtime-decision-map-20260803.txt`](results/runtime-decision-map-20260803.txt).
- The guarded installer resolved live GPT `boot2` as `/dev/mmcblk0p30`, proved
  active root `/dev/mmcblk0p29`, recorded the exact pair-v6 predecessor, wrote
  the pair-v7 image, matched the full-partition readback, removed the temporary
  readback, and confirmed clean shutdown without requesting reboot. No fresh
  backup was created. See
  [`results/deployment-20260803.txt`](results/deployment-20260803.txt).
- Runtime attempt 1 reached complete, correct multiline and parallel results,
  but the pair-v6 terminal observed `coh_reported=-1` and pair-v7 observed only
  reset scheduler state with `parent_pass=0`. Source review establishes that the
  child runs before the inherited worker's final publication, allowing the
  terminal work to race that publication. The device recovered by watchdog,
  CPUs 8/9 were offline, and boot2 remained exact. Do not repeat this image.
  See
  [`results/runtime-attempt-1-parent-publication-race-20260803.txt`](results/runtime-attempt-1-parent-publication-race-20260803.txt).
- The corrective source design removes every scheduler reference from the
  inherited coherency worker. Sample 3 now resets child state after all parent
  snapshots and runs the scheduler only inside the complete pair-v6 pass
  branch. Three new negative mutations cover child execution before parent
  publication, missing post-snapshot reset, and missing pre-terminal execution.
  This revision is design/source-tooling only until Buildbox regenerates and
  validates a new patch.
- Buildbox regeneration from repository commit
  `a2bec2d89edfdf7c5c9c70907ef90fb7d064bbfb` reconstructed the exact pair-v6
  parent, kept its coherency worker source unchanged, passed both scheduler hash
  vectors, rejected all 28 negative mutations, and produced one changed-path-
  checked patch. Corrected generated source commit:
  `bf100f042aaa6d5e4eecccc077b5d82d076d704e`; patch SHA-256:
  `eaebe9bcf22450ccf18016f5272d835c68aba4c413f947d3035b46f2a0b39df5`;
  patchset SHA-256:
  `8a5b32d331493680e0a554d96572c9ec3d769e8075baf4f998cd7a2cfc617c28`;
  stable patch ID: `109450306004a18cdcd0c342c6edb1b7759a31a0`.
  No compile, container, or device action occurred.
- Buildbox compile from repository commit
  `66f3592aa281915a1fa998684353ea9f9395c85d` built the corrected child and
  exact pair-v6 parent. The inherited coherency worker source is identical,
  child/parent diagnostics match, CPU9 startup is unchanged, all 28 mutations
  are rejected, and binary, terminal, configuration, package, and stack checks
  pass. Corrected stack use is 96 bytes for the coherency worker, 784 for the
  sample-3 terminal worker, 176 for the isolated reporter, and 96 for each
  scheduler thread. The corrected `Image.gz-dtb` SHA-256 is
  `f3b021cc8036a2b3ac205a16a6ff135dbeb70210cda27c639b1543b7a385449e`.
  No container or device action occurred. See
  [`results/compile-review-ordering-fix-20260803.txt`](results/compile-review-ordering-fix-20260803.txt).
- Two independent corrected container roots are byte-identical and pass the
  independently pinned Android-v0 validator. The corrected raw SHA-256 is
  `e40ee8a50694f49d75cd023d6b2b29df4505e83dc7316f54b6fa15d5151742a7`;
  the exact 16 MiB boot2 SHA-256 is
  `d34b2de509021d5fbbfcca62e3676202fe88b449786daf62b4eb466667fae093`.
  No device was accessed. See
  [`results/offline-container-review-ordering-fix-20260803.txt`](results/offline-container-review-ordering-fix-20260803.txt).
- Corrected deployment/runtime tooling pins the rejected attempt-1 predecessor
  `24377665fa5b9112266890844c06c453bb50e17680b6f6f956035c234c26ff0f`
  and corrected successor
  `d34b2de509021d5fbbfcca62e3676202fe88b449786daf62b4eb466667fae093`.
  All four installer identity mutations are rejected; the live-GPT,
  inactive/unmounted, no-fresh-backup, full-readback, cleanup, and shutdown
  gates remain pinned. The read-only USB/netcat collector and complete decision
  classes pass static validation. No corrected deployment occurred. See
  [`results/runtime-decision-map-ordering-fix-20260803.txt`](results/runtime-decision-map-ordering-fix-20260803.txt).
- The guarded corrected deployment resolved live GPT boot2 as
  `/dev/mmcblk0p30`, proved active root `/dev/mmcblk0p29`, matched the rejected
  attempt-1 predecessor, wrote and fully read back the corrected 16 MiB image,
  removed the temporary readback, and confirmed clean shutdown. No fresh backup
  was created and no reboot was requested. The prearmed changed-cycle observer
  saw the deployment shutdown. See
  [`results/deployment-ordering-fix-20260803.txt`](results/deployment-ordering-fix-20260803.txt).
- Corrected runtime attempt 1 produced adjacent complete pair-v6 pass and
  pair-v7 `parent_pass=1`, so the publication fix worked and the scheduler
  oracle ran. Both bound tasks entered ordinary task context on their exact
  CPUs. CPU9 completed the exact workload and hash; CPU8 exhausted the
  peer-ready spin before CPU9 joined, then both parent waits expired. Recovery
  was changed-cycle and watchdog-class with CPUs 8/9 offline and boot2 exact.
  This is a rendezvous/timing design failure, not evidence that CPU8 failed to
  dispatch. Do not repeat this image. See
  [`results/runtime-ordering-fix-attempt-1-rendezvous-timeout-20260804.txt`](results/runtime-ordering-fix-attempt-1-rendezvous-timeout-20260804.txt).
- The next source revision replaces the peer-ready busy spin with three bounded
  completion phases. Each task publishes a per-CPU ready completion and blocks;
  the parent observes both readiness completions before releasing one shared
  start gate; only then do both tasks run the unchanged workload and publish
  independent done completions. Separate 2,000 ms ready and done deadlines,
  explicit start authorization, four new terminal fields, and 33 negative
  mutations distinguish readiness, release, workload, and cleanup. Observed
  `wake_up_process()` returns of either zero or one are accepted only alongside
  independently proven task execution. This is source-tooling preparation
  only; Buildbox has not generated or compiled the revision.
- Buildbox generation from repository commit
  `236dd0631c2a50ac34a3fa9b8cd8651c9e1a45bc` reconstructed the exact pair-v6
  parent, passed both scheduler hash vectors, rejected all 33 mutations, and
  produced a one-path patch. Generated source commit:
  `7de241d42df128848ddbc37a090d4440fb7fa09f`; patch SHA-256:
  `23cfff979bee079a41c0a82e43d5c7b3b0f55f8fc29115b2337fb6121f06409b`;
  patchset SHA-256:
  `970c090c080f0a5b03738ea7bdec65edaebc7b1d3b179488202587c157edc845`;
  stable patch ID: `6a0ddf1846650bd5e3b70a22b47adc3289449d0d`.
  No compile, container, or device action occurred. See
  [`results/source-generation-start-gate-20260804.txt`](results/source-generation-start-gate-20260804.txt).
- Buildbox compilation from repository commit
  `703d59b239aae6c6f66308a097ede32fc3bdd678` built the start-gate child and
  exact pair-v6 parent. Both diagnostics contain only the same 69 section-
  mismatch warning; CPU9 startup source, configuration, package, symbols,
  disassembly boundaries, expanded terminal, and all 33 mutations pass. Stack
  frames are 96 bytes for the inherited coherency worker, 784 for the terminal
  work, 208 for the isolated reporter, and 96 for each scheduler thread, all
  below 1,024 bytes. The `Image.gz-dtb` SHA-256 is
  `21a64e59bbf0a83123ee936cc0dc7bdf00e793d8c290a0e557e24d826abefd2a`.
  No container or device action occurred. See
  [`results/compile-review-start-gate-20260804.txt`](results/compile-review-start-gate-20260804.txt).
- Two independent start-gate container roots are byte-identical and pass the
  independently pinned Android-v0 validator. The raw SHA-256 is
  `78dd52721a762eb8dbeca29af3b9ca7c0ac7546e9aeaf1aaccf7585c25752d1f`;
  the exact 16 MiB boot2 SHA-256 is
  `2e8c611b1dbe5b79b13f2dec9cf9d77d9b7973a732f63702a6228600bef464b3`.
  No device was accessed. See
  [`results/offline-container-review-start-gate-20260804.txt`](results/offline-container-review-start-gate-20260804.txt).
- Start-gate deployment/runtime tooling pins the installed rendezvous-rejected
  predecessor
  `d34b2de509021d5fbbfcca62e3676202fe88b449786daf62b4eb466667fae093`
  and successor
  `2e8c611b1dbe5b79b13f2dec9cf9d77d9b7973a732f63702a6228600bef464b3`.
  Four installer identity mutations are rejected; all live-GPT,
  inactive/unmounted, no-fresh-backup, full-readback, cleanup, and shutdown
  gates remain pinned. The read-only collector now requires all four ready/start
  fields, and the fixed decision map covers every readiness, workload,
  recovery, and serviceability branch. No start-gate deployment occurred. See
  [`results/runtime-decision-map-start-gate-20260804.txt`](results/runtime-decision-map-start-gate-20260804.txt).
- The guarded deployment resolved live GPT boot2 as `/dev/mmcblk0p30`, proved
  active root `/dev/mmcblk0p29`, matched the rendezvous-rejected predecessor,
  wrote and fully read back the start-gate 16 MiB image, removed temporary
  state, and confirmed clean shutdown. No fresh backup or reboot was requested.
  The prearmed changed-cycle observer saw the deployment shutdown. See
  [`results/deployment-start-gate-20260804.txt`](results/deployment-start-gate-20260804.txt).
- Start-gate runtime attempt 1 completed a real boot/recovery cycle, but both
  prearmed observers expired before the delayed physical selection. The
  post-recovery pstore record contains only Gemian 3.18.41+ userspace startup
  and no pair-v6 or pair-v7 terminal. Changed boot ID and watchdog-class
  recovery establish the cycle; normal root, CPUs 8/9 offline, inactive boot2,
  and the exact full boot2 checksum establish safe recovery. They do not
  establish a start-gate result. One exact repeat is earned solely with
  just-in-time USB/netcat and changed-cycle pstore as a new independent
  observation path. See
  [`results/runtime-start-gate-attempt-1-evidence-loss-20260804.txt`](results/runtime-start-gate-attempt-1-evidence-loss-20260804.txt).
- Start-gate runtime attempt 2 used just-in-time changed-cycle pstore and an
  already-matching checksum verification; no write occurred. The attributable
  console contains no pair-v6 or pair-v7 terminal and ends at 14.121403 seconds
  with a kernel NULL-pointer dereference at virtual address `00000166` before
  PC/LR or a call trace could be retained. The console covers the interval in
  which the preceding candidate emitted both terminals, so this distinguishes
  terminal-not-reached from attempt 1's evidence loss. Watchdog-class recovery
  returned the normal root with CPUs 8/9 offline and boot2 exact. Reject this
  artifact unchanged. See
  [`results/runtime-start-gate-attempt-2-preterminal-null-deref-20260804.txt`](results/runtime-start-gate-attempt-2-preterminal-null-deref-20260804.txt).
- Phase-attribution source tooling now derives from the exact rejected
  start-gate patch series and adds 31 short durable lines around the unchanged
  task and parent phases. Its validator strips those lines and requires
  byte-for-byte equality with the parent, fixes phase order, and rejects every
  individual missing-marker mutation plus two ordering swaps. Local Python
  syntax/CLI, generator shell syntax, and whitespace checks passed; ShellCheck
  was unavailable locally at that checkpoint, and later exact-checkout
  Buildbox checks passed. No exact-parent generation, compile, container, or
  device action occurred. See
  [`results/source-tooling-phase-attribution-20260804.txt`](results/source-tooling-phase-attribution-20260804.txt).
- Buildbox exact-parent generation at repository commit `baf7370a13675fe62e08ba19ba168448753058a0`
  reconstructs and validates the rejected start-gate parent, retains its two
  hash vectors and 33 negative mutations, adds exactly 31 marker lines, rejects
  all 33 marker mutations, and proves byte-identical parent source after marker
  stripping. The generated `0002` changes only `arch/arm64/kernel/psci.c` with
  31 insertions; patch SHA-256 is
  `30f2b94232d6cf87991a761dd533a4d90a21545c98132079dd73cbeb2cd00234`.
  Two earlier generation submissions stopped at an incorrect create anchor and
  validator layering respectively, before producing a patch. No compile,
  container, or device action occurred. See
  [`results/source-generation-phase-attribution-20260804.txt`](results/source-generation-phase-attribution-20260804.txt).
- Buildbox child-versus-exact-parent compilation from repository commit
  `a50c12f11862bde5b27de8de0a91ac72529b1bd7` passes source, mutation,
  configuration, diagnostics, symbol, expanded-terminal, focused-disassembly,
  package, and stack gates. All 31 phase-marker strings are present in the
  child binary, and both exact builds produced 2,484 stack-usage files. The four
  measured child frames are 96, 784, 208, and 96 bytes, all below the 1,024-byte
  boundary. The exact accepted `Image.gz-dtb` SHA-256 is
  `932dfc84eaea2aa5971a0ade98d5ddb8d592e400830fba47aa81d2a7b02c5811`.
  Two earlier end-to-end submissions exposed only stale package-purpose and
  ShellCheck-annotation gates; the exact final checkout fixes both and passes
  all relevant ShellCheck invocations. No cross-job byte-reproducibility claim
  is made because build time and output path metadata were not normalized. No
  container or device action occurred. See
  [`results/compile-review-phase-attribution-20260804.txt`](results/compile-review-phase-attribution-20260804.txt).
- Container tooling committed at
  `b2f11e96dc4141c801d3e02fa10970f42fc9dea8` pins the exact accepted kernel,
  compile commit, phase patchset, retained ramdisk, raw image, and padded image.
  The accepted validator at `396017d751c345929edada3a008f49e0572d07be`
  pins the sidecars and complete manifest, parses unique exact evidence records,
  rejects conflicting provenance, and pins and scans the complete 11-assembler
  construction chain plus both builders for offline-only violations.
  Two independent ignored roots are byte-identical after two raw assemblies
  and two padding constructions per root. Both pass the independent Android-v0
  validator and each rejects all six candidate mutations. The raw SHA-256 is
  `d06e220da65830b7a58620b03a9ecd8e78d27ee28b2ca905b046fe3198c7375c`;
  the exact 16 MiB boot2 SHA-256 is
  `2268e23559e8d36e4339a4fd912d0108721ed818e628dfc857cab2ab8e8049a8`.
  No device was accessed. See
  [`results/offline-container-review-phase-attribution-20260804.txt`](results/offline-container-review-phase-attribution-20260804.txt).
- Phase-attribution deployment/runtime tooling pins the rejected start-gate
  boot2 predecessor, exact padded successor, candidate manifest, and artifact
  name. The inherited live-GPT, inactive/unmounted, no-fresh-backup,
  full-readback, temporary-cleanup, and clean-shutdown gates remain intact.
  The read-only USB/netcat collector now emits numbered complete snapshots
  instead of count-based deltas and invokes the same parser exercised by the
  static suite. The parser requires one exact marker occurrence per line,
  reachable parent/task structure, monotonic event history, source-pinned
  complete pair terminals, exact PASS vectors, successful-fault-field causal
  edges, all 39 records for PASS, and a distinct transport-truncated class.
  Four installer identity mutations, ten marker/order mutations, and
  twenty-six captured-format mutations are rejected; valid alternate CPU
  interleaving, create-failure, timeout, undispatched-task, and marker-free
  parent-fault branches remain accepted. Bash syntax, ShellCheck, Python
  compilation, the complete runtime test, and whitespace checks pass. No
  deployment or device access occurred. See
  [`results/runtime-tools-phase-attribution-20260804.txt`](results/runtime-tools-phase-attribution-20260804.txt).
- The guarded deployment resolved live-GPT boot2 as `/dev/mmcblk0p30`, proved
  it inactive and unmounted against ordinary Gemian root `/dev/mmcblk0p29`,
  matched the exact rejected predecessor, wrote only the exact 16 MiB
  phase-attribution successor, synchronized and flushed it, and matched a full
  readback. No fresh backup was created. Temporary state was removed and the
  device was cleanly shut down without an automatic reboot before the owner
  selected boot2 once. See
  [`results/deployment-phase-attribution-20260804.txt`](results/deployment-phase-attribution-20260804.txt).
- The prearmed observer recorded one attributable changed-boot-ID cycle after
  boot2 started and automatically returned to Gemian. Pstore retains a valid
  15-parent-marker prefix through `release-after` and then
  `done8-wait-before`, but ordinary logging continues for 1.274391 seconds
  without a fatal/reset tail. The fixed map therefore classifies the result as
  `ATTRIBUTABLE RESTART WITH INCOMPLETE TRACE`, not a first-unmatched boundary.
  There are no retained task markers or pair terminals. Reject the exact image
  unchanged without assigning a failing CPU or operation at reset. See
  [`results/runtime-phase-attribution-attempt-1-incomplete-trace-20260804.txt`](results/runtime-phase-attribution-attempt-1-incomplete-trace-20260804.txt).
- A separate exact-source/binary audit identifies a deterministic design
  error: `kthread_create_on_cpu()` returns each worker parked,
  `wake_up_process()` does not release `TASK_PARKED`, and ordered
  `kthread_stop()` cleanup does unpark the tasks. This accounts for the
  retained no-task prefix and supersedes the earlier causal interpretation of
  serialized CPU8/CPU9 execution, without changing either fixed runtime
  classification. See
  [`results/source-binary-kthread-park-contract-20260804.txt`](results/source-binary-kthread-park-contract-20260804.txt).
- The source-only unpark successor preserves the exact rejected `0001+0002`
  parent and prepares a future one-path `0003`. Six finite replacements change
  only the two parked-task activations and their void-operation fields/markers;
  reverse normalization must restore parent `psci.c` byte-for-byte. The finite
  fixture and an exact reconstructed vendor/parent source both pass the
  lifecycle and equivalence validator and reject all 20 mutations. The
  Buildbox generator exports only `0003`, while compile and package-fetch paths
  deliberately hard-stop on a pending all-three-patch hash until that generated
  patch is reviewed. No Buildbox generation, compile, container, or device
  action has occurred. See
  [`results/source-tooling-unpark-20260804.txt`](results/source-tooling-unpark-20260804.txt).
- Buildbox source generation from clean pushed repository commit
  `152fe6287951fb707b92aeaf04ecaf1aa3499d92` reconstructed and validated both
  historical parent patches, then exported only the unpark `0003`. Strict
  package checksums, exact path and hunk inventories, finite-editor
  equivalence, the pinned lifecycle contract, and all 20 mutations passed.
  Patch SHA-256 is
  `7b05002ff89f53a15e1eeb7d3b9588ac08443902626da4b706045d418513f486`;
  stable patch ID is `17a4a7b455d15ca8a5bbfc17288ae232c4a2b951`;
  admitted three-patch series SHA-256 is
  `bd5799cecd14aa34a87562b09507a6d9f18f11cd138420bcba629f12793e7bfe`.
  No compile, container, device action, or native VM build occurred. See
  [`results/source-generation-unpark-20260804.txt`](results/source-generation-unpark-20260804.txt).
- Buildbox compiled the exact unpark child and rejected phase parent from
  repository commit `4f647c333056fd51aa2850957bb94ace508bedee`. Both builds
  pass with byte-identical configurations and diagnostics; focused
  disassembly proves the intended two unpark calls only in the child while
  retaining the pinned park/unpark/stop state masks and call edges. All 31
  phase strings remain, each measured frame stays within its 512- or
  1,024-byte bound, and all package checksums pass. Accepted child
  `Image.gz-dtb` SHA-256 is
  `b7ed626161490c64939f791e1caaaf6f4ffb03ecf55466776a19b74f02bb349c`.
  This is compile review only: `boot_candidate=false`, no container, no native
  VM build, and no device action. See
  [`results/compile-review-unpark-20260804.txt`](results/compile-review-unpark-20260804.txt).
- Current-main source regeneration at repository commit
  `300cf6fa3026190f21656449c202603ec5b2e62b` reproduced admitted `0003`
  byte-for-byte and records `generated_matches_admitted=yes`. The offline
  candidate tooling is retargeted to the exact accepted compile package,
  kernel, phase-parent/child, raw, padded, and sidecar identities while
  preserving two raw assemblies, two padding constructions, the 11-assembler
  offline chain, and six negative mutations. A disposable end-to-end
  construction passed and was removed; no retained container or device action
  has occurred. See
  [`results/offline-container-tooling-unpark-20260804.txt`](results/offline-container-tooling-unpark-20260804.txt).
- Two retained constructions in separate ignored roots now reproduce every
  unpark container file byte-for-byte. Each root passed strict manifests, two
  raw assemblies, two padding paths, independent Android-v0, ramdisk,
  legacy-ID, extent, zero-tail, provenance, and offline-only review, the pinned
  11-assembler chain, and all six negative mutations. The accepted exact
  16 MiB image SHA-256 is
  `5b38e542586cf70f3fcf3de049f351671f96fab985e0d93fa79f90e2d04012c5`.
  No native VM build or device action occurred. See
  [`results/offline-container-review-unpark-20260804.txt`](results/offline-container-review-unpark-20260804.txt).
- The guarded installer, fixed decision map, changed-cycle pstore contract,
  and read-only USB/netcat observer are now pinned to that exact successor and
  the rejected phase predecessor. The parser derives final marker and pair-v7
  schemas from admitted `0003`, requires both PASS unpark fields to equal one,
  preserves a valid task-before-unpark-after interleaving, and enforces both
  directions of unpark field/marker causality, including complete pair
  snapshots whose later host terminator is lost. Four installer, 14 marker/order,
  and 39 capture/schema/semantic mutations are rejected; all nine result
  classes and the no-backup/readback/shutdown boundary pass. No device action
  occurred. See
  [`results/runtime-decision-map-unpark-20260804.txt`](results/runtime-decision-map-unpark-20260804.txt)
  and
  [`results/runtime-tools-unpark-20260804.txt`](results/runtime-tools-unpark-20260804.txt).
- The guarded unpark deployment resolved live GPT boot2 as
  `/dev/mmcblk0p30`, proved ordinary Gemian root `/dev/mmcblk0p29`, matched the
  rejected phase predecessor, wrote and fully read back the exact accepted
  16 MiB successor, removed temporary state, and cleanly shut the device down
  without requesting a reboot. No fresh backup was created. The already-armed
  pstore observer confirmed the shutdown. See
  [`results/deployment-unpark-20260805.txt`](results/deployment-unpark-20260805.txt).
- Unpark runtime attempt 1 passes the fixed map. Changed-cycle primary pstore
  retains the complete 39-record trace, `run-exit`, and adjacent exact pair-v6
  and pair-v7 PASS terminals. CPU8 and CPU9 each ran all 262,144 bounded
  scheduler-context iterations on the intended CPU with their exact hashes;
  both readiness, release, completion, unpark, and cleanup contracts passed.
  Watchdog-class recovery returned ordinary Gemian with CPUs 8/9 offline,
  inactive unmounted boot2, and its full checksum unchanged. Physical boot2
  selection preceded the optional USB observer, so no secondary USB record
  exists; the complete primary pstore satisfies every fixed PASS predicate.
  One exact repeat is earned. See
  [`results/runtime-unpark-attempt-1-pass-20260805.txt`](results/runtime-unpark-attempt-1-pass-20260805.txt).

## Analysis

Pair-v6 proves bounded concurrent IPI callback execution and shared-memory
integrity. It does not prove that the scheduler can dispatch and cleanly retire
ordinary tasks on both retained A72 CPUs. This child changes only that execution
context while preserving the established power and recovery boundary.

The first exact unpark cycle now proves that bounded dispatch and cleanup once:
both per-CPU tasks entered normal scheduler context on their intended CPUs,
rendezvoused through the predeclared start gate, completed the deterministic
workload, and exited cleanly. Repeatability, production scheduling, CPU_OFF,
and every later power-management boundary remain separate claims.

## Conclusion

`attempt-1-pass-repeat-earned`: the source/binary diagnosis was correct.
Replacing only the two parked-task activation calls with `kthread_unpark()`
produced one complete scheduler-context PASS without changing the inherited
pair-v6, safety, or recovery boundary. Both CPU8 and CPU9 tasks ran on their
intended CPUs, completed the exact finite workload, and exited through ordered
cleanup; changed-cycle watchdog recovery, offline recovery CPUs, and unchanged
boot2 all passed. This closes one bounded observation, not repeatability or
production support. The fixed map earns exactly one identical repeat. CPU_OFF,
the HPS-veto removal, sustained scheduling/load, OPP/cpufreq, thermal,
suspend/resume, and default-profile integration remain unauthorized or
unproved. Continue only through the ordered action in `docs/ROADMAP.md`.

## Follow-up

Continue only through the ordered Gate 8 action in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md).
