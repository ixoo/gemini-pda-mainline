# Experiment: mainline MT6797 A72 A34 eligibility evaluator

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-20-mainline-a72-a34-reset-bootstrap` |
| Status | canonical evaluator patch generated and validated; build pending |
| Subsystem | MT6797 A72 reset/bootstrap eligibility and membership/P30 state |
| Device variant | Planet Gemini PDA; hardware-free implementation phase |
| Date | 2026-08-20 America/New_York |
| Tracking issue | Roadmap Gate 7, A34 |

## Question or hypothesis

Can the frozen A34 zero-state predicate be implemented as a pure evaluator
without pretending that a normal Linux boot proves a platform/external reset
or owner-safe private replay state?

The falsifiable claim is that a default-off evaluator accepts only the exact
tuple with explicit platform/external-reset provenance and owner-safe private
replay-zero proof. Every byte mutation rejects, and neither result changes the
closed owner or makes a request reachable.

## Provenance and environment

- Parent decision: the completed
  [Gate-7 remaining-boundary audit](../2026-08-20-mainline-cpu8-gate7-remaining-boundary-audit/README.md).
- Kernel baseline: pinned Linux 7.1.3 and canonical series through patch
  `0301`.
- Source authority: exact Buildbox managed tree; no source tree will be copied
  to or from Buildbox.
- Build policy: commit and push a clean repository input, then use only
  `./scripts/build-kernel --backend buildbox` and fetch its validated package.
- Current phase uses repository and read-only exact-source inspection only.

## Safety assessment

The signed audit prerequisite is satisfied. The implementation remains
default-off, pure, and hardware-free. It has no production caller and cannot
open the software owner lifecycle, initialize an attempt, invoke a CPU
operation, or call a provider.

There is no boot candidate, boot2 write, device access, shutdown, physical
provider transition, P28 effect, CPU request, or CPU8 support claim.

## Associated records

- [`DESIGN.md`](DESIGN.md): exact immutable input, result, and non-scope.
- [`results/test-matrix.tsv`](results/test-matrix.tsv): implementation and evidence matrix.
- [`results/design-validation-20260820.txt`](results/design-validation-20260820.txt): repository-side design and generator validation.
- [`results/patch-generation-attempt-1-checkpatch-20260821.txt`](results/patch-generation-attempt-1-checkpatch-20260821.txt): strict Buildbox style rejection and cleanup proof.
- [`results/patch-generation-validated-20260821.txt`](results/patch-generation-validated-20260821.txt): exact second-attempt patch-generation identity and safety result.
- Focused KUnit and Buildbox build receipts will be added only after their
  exact results exist.

## Current result

The corrected decision and source design are complete, and the required audit
is signed and published. The Git-pinned Buildbox patch-generation lane is
ready. The first exact-commit generation passed source and patch validation but
was correctly rejected by strict checkpatch for one short Kconfig help block
and four function-line breaks. It admitted no package or job record and its
partial output was removed. The corrected second attempt generated canonical
patch `0302`, replayed it byte-for-byte, passed exact source validation and
strict checkpatch with zero findings, and retained a checksum-covered review
package. The patch and its default-off production and focused KUnit profiles
are now admitted locally; no kernel build or device work has been attempted.
The read-only provenance audit also confirms that the existing watchdog-class
boot reason is nondiscriminating and cannot be wired into this evaluator as a
substitute for the unresolved reset owner. Vendor source does expose a finer
TOPRGU `WDT_STATUS` latch, and current mainline does not read it. A
pre-initialization read is now recorded as a candidate, not as proof, pending
LK preservation and reset-class semantics.

## Follow-up

The authoritative order remains in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md). After the audit commit is signed and
pushed, generate the single logical evaluator patch from the exact Buildbox
source, validate it, add the default-off source and KUnit profiles, sign and
push, then run the Buildbox-only compile and focused QEMU proof.
