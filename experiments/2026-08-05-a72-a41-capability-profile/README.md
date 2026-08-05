# Experiment: fail-closed MT6797 late-A72 capability profile

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-a41-capability-profile` |
| Status | `completed` (offline source-contract validation only) |
| Subsystem | arm64 capability finalization and MT6797 CPU operations |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-05 |
| Investigator(s) | Julien Etienne; OpenAI Codex |
| Tracking issue | [Roadmap A41](../../docs/ROADMAP.md) |
| Kernel | Linux `7.1.3` |
| Implementation state | `PARTIAL_FAIL_CLOSED` |
| A41 complete | `no` |

## Question or hypothesis

Do patches [0148](../../patches/v7.1.3/0148-arm64-add-a-fail-closed-late-CPU-profile-lifecycle.patch)
and [0149](../../patches/v7.1.3/0149-arm64-mediatek-register-blocked-MT6797-A72-profile.patch),
when applied after the exact [patch 0092](../../patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch)
reject gate, add a default-off and isolated A41 profile that is blocked before
READY or any production capability mutation while the existing veto continues
to prevent CPU_ON?

The narrower positive claim is that the partial implementation records exactly
three planned local capabilities and a Spectre-BHB loop count of eight, exposes
the lifecycle and attestation interfaces, and enumerates every unresolved proof
as a blocker. Non-circular input identities are provenance rather than runtime
proof, while target-register values remain separate expected/observed fields
with explicit validity. It does **not** claim that the capability inventory or
commit path exists, that CPU8 or CPU9 can start, or that A41 is complete.

## Provenance and environment

- Source archive SHA-256:
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`.
- Exact pre-`0148` source commit:
  `df9447fb8be9b03a643b00111dd25f6ce62be719` (tree
  `265ffcaf56d7ec453e0dd017f19a5373a13960ba`).
- Selected repository [manifest profile](../../kernel/manifest.json):
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate-a41`.
- Selected profile
  [fragment](../../configs/gemini-a72-a41.fragment): default-off A41 selection
  with no CPU8/9 request.
- Selected series:
  [`patches/series-a72-reject-gate-a41`](../../patches/series-a72-reject-gate-a41).
- Pre-A41 reject-gate source-state identity:
  `2ef15df475d00e5ae0f85a1f25866cd4267a407af974b5c8cf992ad2e15e0a9b`.
- Patch SHA-256 values: [0148](../../patches/v7.1.3/0148-arm64-add-a-fail-closed-late-CPU-profile-lifecycle.patch)
  `953a990c6c9f0f91822b9923a2adf6ebf71e326ea5c570dd133c4178059750fb`;
  [0149](../../patches/v7.1.3/0149-arm64-mediatek-register-blocked-MT6797-A72-profile.patch)
  `3c0911601d73ba73cce6a122d62df4e4f0273aeb9474e81c871aba2214feadc0`.
- Ordered configuration-input SHA-256:
  `ef8a5a3fe57629be71f466008afad67183f5184f9acc2faaddff999c6fe4048e`.
  No resolved `.config` was generated.
- Validation tools: Python `3.14.6`, Git `2.50.1 (Apple Git-155)`, Perl
  `v5.34.1`, and the Linux `7.1.3` Checkpatch/checkincludes scripts whose
  hashes are pinned in the
  [kernel static-review transcript](results/kernel-static-review-20260805.txt).
  No compiler was invoked.
- Boot path and target partition: not applicable; this experiment did not
  build, deploy, boot, or contact the device.
- Public source input: the manifest-pinned official Linux `7.1.3` archive and
  the canonical repository patch series through the exact pre-A41 reject gate.

## Safety assessment

This validation workflow is repository-read-only except for disposable local
scratch space. It does not build a kernel, create a boot candidate, contact the
Gemini, write a partition, issue CPU_ON, reboot, or shut down a device. The
implementation markers explicitly leave build and device action unauthorized.

## Associated code

- [`scripts/validate.py`](scripts/validate.py) checks exact repository
  identities, ordering, applicability, lifecycle placement, veto preservation,
  profile isolation, planned capabilities, blocker completeness, and
  production-path absence.
- [`scripts/test_mutations.py`](scripts/test_mutations.py) makes a fixed set of
  in-memory or disposable-copy contract violations and requires every one to
  fail closed.
- [`results/implementation.tsv`](results/implementation.tsv) is the
  machine-readable partial-milestone claim.
- [`results/blockers.tsv`](results/blockers.tsv) is the complete blocker
  inventory.
- The [offline validation transcript](results/offline-validation-20260805.txt)
  and [mutation transcript](results/mutation-validation-20260805.txt) freeze
  the exact accepted outputs.
- [`results/kernel-static-review-20260805.txt`](results/kernel-static-review-20260805.txt)
  freezes the exact source range,
  tool identities, commands, exit dispositions, and static-review findings.
- [`DESIGN.md`](DESIGN.md) records the reachability argument and explicit
  non-claims.

No script requires privileges or hardware access.

## Procedure

From this experiment directory:

1. Run `python3 scripts/validate.py --source-root /path/to/exact/linux-source`.
   The source repository must contain the pinned pre-`0148` commit; validation
   extracts only the pre-existing paths touched by the two patches into
   temporary scratch space, then performs sequential `git apply --check` and
   apply operations there.
2. Run `python3 scripts/test_mutations.py`.
3. From the exact prepared source, run the source range's `git diff --check`,
   pipe that range to `scripts/checkpatch.pl --no-tree --strict -`, and run
   `scripts/checkincludes.pl` on the four changed C files. Run the same
   Checkpatch script on the two format-patches from the repository root. The
   exact source range, invocations, tool hashes, expected nonzero dispositions,
   and results are frozen in the
   [kernel static-review transcript](results/kernel-static-review-20260805.txt).
4. Compare the validator outputs with
   the [offline validation transcript](results/offline-validation-20260805.txt)
   and [mutation transcript](results/mutation-validation-20260805.txt).

## Observations

The exact patches apply in order to the pinned baseline. Static and applied
source checks preserve the patch-`0092` `-EAGAIN` boot veto and
`cpu_can_disable=false`. Independent CPU0 activation prevents missing custom
CPU8/9 methods from turning the selected profile into a no-op. The profile
records three plan bits and BHB loop `k=8`, then enters BLOCKED because its
mandatory blocker mask is nonzero and its prepare callback returns `-EAGAIN`.

The fixed mutation suite rejects every tested relaxation. No compilation or
device observation was performed.

Kernel static review also passed `git diff --check` and the duplicate-include
check. Strict Checkpatch on the source diff reported zero errors and zero
checks; its only warning was the generic new-file MAINTAINERS warning, already
covered by the arm64 entry. Checkpatch on the format-patches adds only the
intentionally absent `Signed-off-by`, consistent with their synthetic,
experiment-only, explicitly not-submission-ready authorship. No compile or
build was run.

## Analysis

For the selected MT6797 profile, BLOCKED is a source-level reachability result:
the callback installs the mandatory unresolved-proof mask and fails before the
generic lifecycle can publish PREPARED. The later system and user finalizers
return immediately for BLOCKED, so the generic READY state is not reachable by
this profile. The three `__set_bit` operations target only the draft attestation
bitmap; they do not modify arm64's live capability bitmap.

This establishes a useful fail-closed scaffold, not working heterogeneous late
CPU support. See the [design record](DESIGN.md) for the exact claim boundary.

## Conclusion

**Confirmed only as `PARTIAL_FAIL_CLOSED`:** the named source revisions provide
the isolated, blocked A41 interface and preserve the existing boot/disable
vetoes. **A41 remains incomplete.** This source-only result is not hardware
support and is not a boot candidate.

## Follow-up

[The roadmap](../../docs/ROADMAP.md) remains the sole owner of ordered project
work. This record does not authorize a build, deployment, boot, CPU_ON attempt,
or device action.
