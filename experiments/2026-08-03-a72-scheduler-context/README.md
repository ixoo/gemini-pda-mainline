# Experiment: CPU8/CPU9 scheduler-context execution

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-03-a72-scheduler-context` |
| Status | `ordering-fix-generated` |
| Subsystem | MT6797 retained Cortex-A72 pair and scheduler |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-03 |
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
threads, binds them before first wake to CPUs 8 and 9, bounds all internal waits
and work, stops both before publication, and treats incomplete cleanup as a
terminal fault. The retained watchdog remains the independent recovery bound.

## Associated code

- [`DESIGN.md`](DESIGN.md): exact lifecycle, workload, task-context oracle,
  bounds, terminal, result classes, and invariants.
- [`scripts/source_edits.py`](scripts/source_edits.py): deterministic exact-
  parent scheduler-context transformation.
- [`scripts/test_static.py`](scripts/test_static.py): inherited-boundary,
  lifecycle, hash-vector, safety-inventory, and negative-mutation validator.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox): clean-pushed-
  commit Buildbox source reconstruction and format-patch generator.
- [`scripts/build-on-buildbox`](scripts/build-on-buildbox): Buildbox-only child
  versus exact pair-v6 compile, diagnostics, disassembly, and stack comparison.
- [`scripts/assemble.py`](scripts/assemble.py): pinned pair-v6 Android-v0
  assembler specialization for the accepted scheduler kernel.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh): reproducible,
  offline-only candidate construction with two raw and padded constructions.
- [`scripts/test_candidate.py`](scripts/test_candidate.py): independent tool,
  manifest, Android-v0, extent, image-ID, ramdisk, padding, and provenance
  validator.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh): exact predecessor,
  live-GPT target, inactive/unmounted, full-readback, cleanup, and clean-shutdown
  deployment contract.
- [`scripts/capture-live-outcome.sh`](scripts/capture-live-outcome.sh): optional
  read-only USB/netcat capture of adjacent pair-v6 and pair-v7 terminals.
- [`scripts/test_runtime_tools.py`](scripts/test_runtime_tools.py): installer,
  no-backup, shutdown, read-only collector, and decision-map validator.
- [`patches/series`](patches/series): exact generated experiment-only scheduler-
  context source patch.

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

## Analysis

Pair-v6 proves bounded concurrent IPI callback execution and shared-memory
integrity. It does not prove that the scheduler can dispatch and cleanly retire
ordinary tasks on both retained A72 CPUs. This child changes only that execution
context while preserving the established power and recovery boundary.

## Conclusion

`ordering-fix-generated`: attempt 1 did not evaluate the scheduler oracle. The
corrected source preserves the inherited coherency worker, passes 28 mutation
tests, and runs the scheduler only after the complete parent predicate is
snapshotted and passes. No corrected compile, container, deployment, or runtime
claim exists yet.

## Follow-up

Continue only through the ordered Gate 8 action in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md).
