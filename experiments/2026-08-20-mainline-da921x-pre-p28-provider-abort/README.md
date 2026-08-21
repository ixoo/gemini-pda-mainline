# Experiment: mainline DA921x pre-P28 provider abort

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-20-mainline-da921x-pre-p28-provider-abort` |
| Status | canonical patch `0301` imported; focused Buildbox/QEMU proof pending |
| Subsystem | MT6797 CPU8 membership owner and DA921x Buck B provider |
| Device variant | Planet Gemini PDA named development unit |
| Date(s) | 2026-08-20 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7 |

Attempt 1 on published commit `feaa97f601925b68484ec222f385adca70175215`
passed contract, edited-source, patch-inventory, and exact replay validation.
Strict checkpatch rejected 74 formatting checks with zero warnings and zero
errors, so no validated package was published. The exact bounded result is in
[`results/patch-generation-attempt-1-checkpatch-20260820.txt`](results/patch-generation-attempt-1-checkpatch-20260820.txt).
Attempt 2 on `0e2a1a74642d58542834cb876dc3d80b1663cd4e` applied all
four source phases, then exposed one stale validator boundary for the newly
wrapped acquire signature; no package was accepted. The bounded trace result
is in
[`results/patch-generation-attempt-2-validator-boundary-20260820.txt`](results/patch-generation-attempt-2-validator-boundary-20260820.txt).
Attempt 3 on `700a87bf4967e8ab44d954c83d7d2a7f96f69eb4` restored all
semantic and replay validation and reduced strict checkpatch from 74 to 17
alignment-only checks, with patch `0298` already clean. The remaining exact
column corrections and bounded result are recorded in
[`results/patch-generation-attempt-3-checkpatch-20260820.txt`](results/patch-generation-attempt-3-checkpatch-20260820.txt).
Attempt 4 on `52451875a7bd1e7daa554b0d2b8feeeb8a9a4e1e` left only one
four-column continuation offset in patch `0297`; the other three patches were
strict-clean and all semantic/replay validators passed. The bounded result is
in
[`results/patch-generation-attempt-4-checkpatch-20260820.txt`](results/patch-generation-attempt-4-checkpatch-20260820.txt).
Attempt 5 on exact clean commit
`809b0caf263bb180a4dddf2a52b06fb3fc5bcb56` passed contract,
edited-source, inventory, exact replay, and strict checkpatch validation. The
validated package `da921x-pre-p28-provider-abort-patches-809b0caf263b` contains
four patches with zero errors, warnings, or checks. Their exact SHA-256
identities are pinned in [`contract.json`](contract.json) and verified against
the canonical import by [`scripts/validate.py`](scripts/validate.py). The
bounded result is in
[`results/patch-generation-attempt-5-success-20260820.txt`](results/patch-generation-attempt-5-success-20260820.txt).

The exact focused Buildbox build from signed commit
`14723ceee84f94fd5ce6b9b26f5f1357ec5e637f` compiled and passed package
validation. QEMU attempt 1 then failed before provider semantics: the first
case's large automatic membership state overflowed the 16 KiB arm64 kernel
stack while being cleared. The fail-closed classifier rejected the incomplete
KTAP. The remediation moves all six cases and the release-callback snapshot to
KUnit-managed heap state; it changes test storage only, not the production
owner/provider implementation. The bounded failure is in
[`results/qemu-attempt-1-stack-overflow-20260820.txt`](results/qemu-attempt-1-stack-overflow-20260820.txt).
The original four-patch generator correctly refused to run after canonical
import because its prepared-parent pin ends at `0295`, while Buildbox now holds
the verified tree through `0299`. That boundary is preserved. A separate
one-patch generator pins the current source state and will produce reviewable
follow-up `0300`; the bounded parent-boundary result is in
[`results/stack-fix-generation-attempt-1-parent-boundary-20260820.txt`](results/stack-fix-generation-attempt-1-parent-boundary-20260820.txt).
The dedicated generator then passed its source, one-file patch, and exact replay
validators. Strict checkpatch rejected 16 continuation-style checks with zero
errors and zero warnings. The storage change was refactored through short
test-only helpers to eliminate only those reported continuations. The bounded
result is in
[`results/stack-fix-generation-attempt-2-checkpatch-20260820.txt`](results/stack-fix-generation-attempt-2-checkpatch-20260820.txt).
Attempt 3 on exact clean commit
`597c528b80c671b9e3b27ed74889462ccc8b13a0` passed pinned-parent,
source, one-file patch, exact replay, and strict checkpatch validation. The
validated package `da921x-pre-p28-provider-abort-stack-fix-597c528b80c6`
contains patch `0300` with SHA-256
`a4ad7024887d4477f219846abbe744ad5432b682b2a47b0329c6425ceded93da`
and zero errors, warnings, or checks. The exact patch is now at the end of the
canonical series. The bounded result is in
[`results/stack-fix-generation-attempt-3-success-20260820.txt`](results/stack-fix-generation-attempt-3-success-20260820.txt).

The stack-safe Buildbox rebuild from exact signed commit
`1f8eae375ae8458a495b7236b18ef647e7af5b7d` passed, and QEMU attempt 2
reached all six test families. Five passed. The malformed-release family
failed only mutation 1: changing the provider callback response ABI was
accepted as a successful release, while mutations 2--14 were rejected. The
abort wrapper copied the remaining response fields into an independently
versioned proof without first checking `response->abi`. The classifier
rejected the five-pass/one-fail KTAP. The bounded failure is in
[`results/qemu-attempt-2-release-abi-gap-20260820.txt`](results/qemu-attempt-2-release-abi-gap-20260820.txt).
The remediation is one fail-closed production condition before proof
construction: a noncanonical provider-call ABI becomes `-EPROTO` and follows
the existing terminal provider-fault path. It adds no caller, hardware action,
or production reachability.
Buildbox generated that exact condition from clean pushed commit
`06b4768509ff421e24110ec73b68d2f7851f8ff7`. The one-file patch passed
pinned-parent, source, exact replay, and strict checkpatch validation with zero
errors, warnings, or checks. Canonical patch `0301` has SHA-256
`577316da88e4cb569c8d84670ec8090db14456789ee08c1efbfae71d8b748dd8`.
The bounded generation result is in
[`results/release-abi-fix-generation-attempt-1-success-20260820.txt`](results/release-abi-fix-generation-attempt-1-success-20260820.txt).

## Question or hypothesis

Can the current closed membership owner consume exactly one successful DA921x
vote, release it before P28 with the exact provider handle, and retire the P27
prefix without making P28, CPU_ON, or production hotplug reachable?

The falsifiable claim is that a default-off production seam can map every
ambiguous acquire/release return to reset-only `FAULT_UNKNOWN`, while the sole
successful path advances `HELD -> RELEASE_INFLIGHT -> NONE` and reaches P29
only with an exact positive-abort proof.

## Provenance and environment

- Exact parent: Linux 7.1.3 plus canonical patches through `0295`.
- Prepared parent source-state SHA-256:
  `2e804ec33835f0e14b050773c52d1d39acf573e6e71eee8257f8c282b54c8f2a`.
- [`contract.json`](contract.json) pins all edited parent file identities.
- Stack-fix parent: the verified canonical tree through `0299`, source-state
  `a44f45709ef40655d871ff81d0829906781febbd9c3eafc62725e71216f543a0`.
- Release-ABI-fix parent: the verified canonical tree through `0300`,
  source-state
  `292db59582fe1842fa3e94960bcf1ea508fa9ee126b88c8de289bfa223517079`.
- Patch generation and kernel builds run only on Buildbox from a clean pushed
  repository commit. No native VM build is permitted.
- The focused proof uses an unregistered in-memory I2C adapter. It registers
  no adapter, client, device, regulator consumer, MMIO range, or CPU callback.

## Safety assessment

The lifecycle owner remains closed with no production `CLOSED -> AVAILABLE`
writer or CPUHP caller. The new config is default-off. P27 and P28 remain
attestation ledgers rather than hardware executors. The test makes no physical
DA921x call, P28 effect, CPU_ON, CPU_OFF, boot image, boot2 write, or device
connection. A26 and A14 remain unchanged; CPU8 and CPU9 admission stays closed.

## Associated code

- [`DESIGN.md`](DESIGN.md) freezes the state edges and terminal policy.
- [`scripts/source_edits.py`](scripts/source_edits.py) applies four logical
  source phases to the exact prepared Buildbox parent.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox) creates normal
  `git format-patch` output, replays it, validates the edited source, and runs
  strict checkpatch.
- [`scripts/generate-stack-fix-on-buildbox`](scripts/generate-stack-fix-on-buildbox)
  creates only follow-up `0300` from the separately pinned `0299` parent.
- [`scripts/generate-release-abi-fix-on-buildbox`](scripts/generate-release-abi-fix-on-buildbox)
  creates only proposed follow-up `0301` from the separately pinned `0300`
  parent.
- [`source/da9213-legacy-membership-test.c`](source/da9213-legacy-membership-test.c)
  is the hardware-free integration KUnit source.
- [`scripts/validate.py`](scripts/validate.py),
  [`scripts/validate_source.py`](scripts/validate_source.py), and
  [`scripts/validate_patches.py`](scripts/validate_patches.py) fail closed on
  contract, source, patch, profile, and forbidden-effect drift.
- [`scripts/validate_stack_fix_source.py`](scripts/validate_stack_fix_source.py)
  and [`scripts/validate_stack_fix_patch.py`](scripts/validate_stack_fix_patch.py)
  require the six heap allocations and the one-file remediation boundary.
- [`scripts/validate_release_abi_fix_source.py`](scripts/validate_release_abi_fix_source.py)
  and [`scripts/validate_release_abi_fix_patch.py`](scripts/validate_release_abi_fix_patch.py)
  require the single pre-confirmation ABI check and terminal protocol-error
  path.
- [`scripts/run-kunit-qemu`](scripts/run-kunit-qemu) accepts only the exact
  published Buildbox package and one focused KUnit suite; its separate
  [`scripts/classify-kunit.py`](scripts/classify-kunit.py) requires exact KTAP
  success before the expected rootfs-panic timeout boundary.
- [`scripts/test-kunit-classifier.py`](scripts/test-kunit-classifier.py)
  demonstrates fail-closed rejection of altered suite, case, plan, checksum,
  kernel-release, exit, and panic-boundary evidence.

## Planned procedure

1. Commit and push the source tooling and isolated profiles. Complete.
2. Generate four normal patches on the integrity-verified Buildbox parent.
   Complete.
3. Fetch only the validated patch package, review it, and import it at the end
   of canonical `patches/series`. Complete.
4. Generate and import follow-up `0300`, then rebuild the exact integration
   KUnit profile on Buildbox. Complete.
5. Run the focused suite under QEMU with no network and classify the KTAP.
   Attempt 2 reached semantics and exposed the missing release-response ABI
   check: five cases passed and one failed.
6. Generate and import the one-condition `0301` remediation from the exact
   canonical `0300` parent. Complete. Rebuild and run one distinct QEMU proof.
7. Record exact package, config, Image, QEMU, and suite identities.

## Decision rule

The slice passes only if all six test families pass, source replay is exact,
strict checkpatch and Buildbox compile pass, and no P28/CPU/device path becomes
reachable. Any incomplete acquire or release proof is terminal, keeps
conservative provider ownership, consumes its one-shot budget, and permits no
retry or speculative inverse.

## Follow-up

Passing this experiment will close only the pre-P28 owner/provider inverse.
It will not authorize a physical provider call or CPU8 boot. The next boundary
must be selected separately by [Roadmap Gate 7](../../docs/ROADMAP.md#7-bring-up-cpu8).
