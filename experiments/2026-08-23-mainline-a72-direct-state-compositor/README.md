# Experiment: mainline A72 direct-state compositor

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-23-mainline-a72-direct-state-compositor` |
| Status | offline test-target correction defined; Buildbox generation pending |
| Subsystem | MT6797 A72 direct-state composition and hotplug ownership |
| Device variant | Gemini PDA contract; injected KUnit phase |
| Date(s) | 2026-08-23 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, direct-state composition |

## Question or hypothesis

Can the existing A72 membership owner expose one default-off physical-state
composition boundary that holds the Linux CPU-hotplug read lock and its own
transition lock, publishes only a complete injected record, and leaves A34,
owner lifecycle, hardware operations, and CPU admission closed?

## Provenance and environment

- Decision authority: the
  [source/lock audit](../2026-08-23-mainline-a72-direct-state-compositor-audit/README.md).
- Repository parent: signed and pushed commit
  `a8734f1d`.
- Canonical kernel parent: patch `0336`.
- Managed prepared source state and exact file identities are pinned in
  [`contract.json`](contract.json).
- Generation and compilation use Buildbox only. No native VM build is
  permitted and no source tree is copied to or from Buildbox.

## Safety assessment

The first phase is hardware-free. It adds no physical reader caller, DT node,
device match, MMIO, SMC, I2C transfer, setter, retry, polling loop, A34 ABI
change, lifecycle publication, CPU veto change, CPU_ON, CPU_OFF, boot image,
device access, or partition write.

The destination is cleared before every lookup. Every source, topology, owner,
or lifecycle failure must leave it all-zero. A successful injected snapshot
must leave the A72 owner byte-identical and still `CLOSED / UNINITIALIZED`.

## Associated code

- [`source/mt6797-a72-direct-state.h`](source/mt6797-a72-direct-state.h) is the
  proposed platform-private hardware-only source record.
- [`source/mt6797_a72_direct_state_test.c`](source/mt6797_a72_direct_state_test.c)
  is the focused injected KUnit suite.
- [`scripts/source_edits.py`](scripts/source_edits.py) applies the deterministic
  owner and test changes to the exact managed source.
- [`scripts/validate_source.py`](scripts/validate_source.py) validates the
  edited source semantics.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox) generates two
  normal format patches, replays them, and runs strict checkpatch.
- [`scripts/generate-stack-fix-on-buildbox`](scripts/generate-stack-fix-on-buildbox)
  preserves those admitted patches and generates two stack-safety follow-ups
  from the exact prepared source through patch `0338`.
- [`scripts/stack_source_edits.py`](scripts/stack_source_edits.py) moves the
  production workspace under the existing transition lock and the large test
  records into KUnit-managed per-case storage.
- [`scripts/generate-target-fix-on-buildbox`](scripts/generate-target-fix-on-buildbox)
  reconstructs the exact source through patch `0340` and generates the
  test-only CPU-hotplug target correction.
- [`scripts/target_fix_edits.py`](scripts/target_fix_edits.py) replaces only
  the two preservation probes' invalid `CPUHP_OFFLINE` argument with the
  admission API's required `CPUHP_ONLINE` target.
- [`scripts/run-kunit-qemu`](scripts/run-kunit-qemu) accepts only the exact
  fetched Buildbox package for the current published commit and runs the sole
  focused suite under bounded no-network arm64 QEMU.
- [`scripts/classify-kunit.py`](scripts/classify-kunit.py) requires all seven
  named cases, exact KTAP summaries, and the expected post-test rootfs panic.

## Procedure

1. Validate the repository-side definition and deterministic source editor.
2. Commit and push a clean exact input.
3. Generate two normal patches on Buildbox from the prepared source through
   canonical patch `0336`.
4. Require exact replay, semantic source validation, strict checkpatch, and a
   checksum-covered review package.
5. Admit the reviewed patches canonically and add an isolated KUnit profile.
6. Build that profile on Buildbox. Reject the package before QEMU if the new
   compositor or its focused suite introduces an over-limit stack frame.
7. Generate, review, and canonically admit stack-safety follow-ups if needed.
8. Rebuild on Buildbox, require the new frame warnings to be absent, then run
   the focused suite under no-network arm64 QEMU.
9. If the offline classifier rejects a test-contract mismatch, preserve that
   result and generate one exact test-only follow-up before repeating the same
   compile and QEMU gates.

## Observations

- Buildbox submission `bf563205` stopped before patch creation because the
  source validator counted older `cpu8_online`/`cpu9_online` fields outside
  the new direct-state ABI. The source editor had completed, but no patch was
  packaged or admitted.
- The validator now scopes that count to the direct-state definition itself.
- Buildbox submission `38c17b2a` then completed semantic validation and exact
  replay, but strict checkpatch rejected declarations split immediately after
  `(` and its generic MAINTAINERS warning for new experiment-review files. The
  declarations now use normal kernel continuation style; only the named
  `FILE_PATH_CHANGES` heuristic is ignored during generation.
- Buildbox submission `0ceb6509` stopped before packaging when the semantic
  validator still searched for the declaration's old return-type layout. Its
  production-wrapper anchor now uses the stable function name instead.
- Buildbox submission `bc774b52` passed semantics and replay; strict
  checkpatch found one remaining continuation-column mismatch in the public
  registration prototype. That exact whitespace is corrected.
- Buildbox submission `46a5dac3` proved the core patch strict-clean and found
  only two continuation-column checks in the KUnit patch. Both short calls are
  now kept on one line.
- Buildbox submission `24bc92a7` generated two checksum-covered patches from
  canonical patch `0336`. Semantic validation, exact replay, and strict
  checkpatch all passed. The admitted patch hashes are pinned in
  [`contract.json`](contract.json).

The generated patches and isolated `a72-direct-state-kunit` profile are now
admitted. Buildbox compilation of exact repository commit `0dbe657d` completed
and produced a checksum-valid package, but GCC found ten newly introduced
over-limit stack frames: two production frames of 33,312 and 66,880 bytes and
eight focused-test frames ranging from 33,600 to 100,944 bytes. The exact
result is retained in
[`results/buildbox-attempt-1-stack-rejection-20260823.txt`](results/buildbox-attempt-1-stack-rejection-20260823.txt).

The compile package is rejected before QEMU and is not a boot candidate. Two
follow-up patches are now defined against the exact prepared source through
patch `0338`: one uses a transition-lock-serialized static workspace and
scrubs it on every exit; the other places large observations and preservation
records in the existing KUnit-managed per-case allocation. Neither follow-up
adds a physical reader or hardware action.

Buildbox submission `5d7122c0` stopped before source copying or patch creation
because Bash rejected a line break between the equality operator and its
right-hand operand in the prepared-source integrity gate. Keeping that guarded
comparison on one line corrects the generator syntax without changing the
kernel edits or their pinned parent.

Submission `93e7e006` then reached the edited core source and its semantic
validator, which mistook the intended `owner_after` member of the static
workspace type for the removed function-local record. The large-record
prohibition now scopes that token to the compositor function body; global
effect prohibitions remain scoped to the whole compositor section.

Submission `c2cac541` passed both core and KUnit source validators and reached
the generated-patch validator. That patch-only gate incorrectly required the
already-existing `kunit_kzalloc()` line to appear among added lines. The source
gate continues to require that allocation; the patch gate now requires the
actually added heap-resident records and observation pointers.

Submission `f1f0088b` passed source validation, patch validation, and exact
replay. Strict checkpatch then found only two continuation-column checks in
the KUnit owner/P30 preservation comparisons. Their nested `memcmp()` calls
are now placed on normal macro-continuation lines with aligned arguments.

Submission `6805c496` generated both follow-up patches from the exact prepared
source through patch `0338`. Both source phases and the generated-patch
contract passed, exact replay reproduced commit `2083c4d9`, and strict
checkpatch reported zero errors, warnings, or checks for both patches. The
reviewed bytes are admitted as canonical patches `0339` and `0340`; their
SHA-256 identities are pinned in [`contract.json`](contract.json).

Buildbox compilation of the repaired series at exact repository commit
`a0e5ff3a` completed and its package validated. The prior ten compositor and
focused-test frame warnings are absent; the log contains only the two known
pre-existing frames outside this change. The checksum-covered result is
retained in
[`results/buildbox-attempt-2-stack-pass-20260824.txt`](results/buildbox-attempt-2-stack-pass-20260824.txt).

The first no-network arm64 QEMU run then executed the sole seven-case suite.
Six cases passed. `direct_snapshot_success` reported one failed expectation:
the test passed `CPUHP_OFFLINE` to `mt6797_a72_membership_preflight_up()` and
expected `-EAGAIN`, while the API correctly returned `-EINVAL` because its
contract accepts only `CPUHP_ONLINE`. The compositor itself returned success,
all composed-record checks passed, the before/after owner and lifecycle
records remained byte-identical, and the post-call preflight result remained
unchanged. The exact sanitized failure is retained in
[`results/qemu-attempt-1-target-mismatch-20260824.txt`](results/qemu-attempt-1-target-mismatch-20260824.txt).

The correction therefore changes only those two bracketing test calls from
`CPUHP_OFFLINE` to `CPUHP_ONLINE`. It changes no production code, expected
closed-owner result, lock, source record, hardware operation, owner lifecycle,
CPU request, or boot policy. A Buildbox-only generator now pins and
reconstructs the canonical source through patch `0340` before producing one
normal patch for review.

## Analysis

The split keeps the outer ownership proof independent from physical reader
binding. A hardware-free pass will establish only the registry, lock order,
complete-record validation, failure behavior, and closed-owner preservation.
It cannot establish a physical value, firmware call, device support, A34
eligibility, or CPU8/CPU9 admission.

The first QEMU rejection is a test-contract defect, not evidence that the
compositor mutated admission state: both probes returned the same `-EINVAL`,
and every state-preservation comparison passed. Using `CPUHP_ONLINE` makes the
probe reach the intended closed-owner branch, where `-EAGAIN` is the existing
contract, without relaxing that contract or opening admission.

## Conclusion

`pending-target-fix-generation`: the stack-safe implementation now compiles
without any newly introduced frame warning. The first offline run proved six
cases and exposed one invalid test target; it did not expose a compositor,
state-preservation, or production failure. The two-call, test-only correction
must now be generated and reviewed on Buildbox, admitted canonically, rebuilt,
and rerun under the same no-network classifier. This remains hardware-free and
is not a boot candidate.

## Follow-up

The authoritative execution order remains in
[Roadmap Gate 7](../../docs/ROADMAP.md#7-bring-up-cpu8). This experiment owns
the exact implementation chronology and generated identities.
