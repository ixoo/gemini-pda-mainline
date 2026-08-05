# Experiment: A41 kernel-identity binding boundary

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-a41-kernel-identity` |
| Status | `completed` (offline source-contract validation only) |
| Subsystem | generic ELF build-ID parsing, arm64 capability finalization, and MT6797 late Cortex-A72 profile |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date(s) | 2026-08-05 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 4, A41 |
| Claim | `PARTIAL_KERNEL_IDENTITY_BINDING` |

## Question or hypothesis

Can ABI 7 independently bind an exact static OF record to the running kernel's
embedded IKCONFIG, GNU build ID, and forced command line, publish only
`SEALED_IDENTITY`, and retain every target-evidence, commit, and CPU-admission
gate?

This experiment tests that source boundary. It does not produce the package OF
record, build a kernel, collect CPU8/CPU9 observations, freeze or commit a
plan, publish READY, or admit a late CPU.

## Provenance and environment

- Kernel release: Linux 7.1.3, archive SHA-256
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`.
- Reviewed ABI-6 parent: commit
  `bcfb60248633bec2cdb6ab70540d5807d305c4e7`, tree
  `b23bf9e6332c865ef15606a41f11e75262e06fbf`.
- Build-ID helper commit:
  `15d862a4fc495505104d1732b3c97f0ad0aa867c`, tree
  `b065acbe5785436ac9b89164e31f6e64bf668bb9`.
- Final arm64 commit:
  `22942d1697a9506132165ff8bfd30c92d5a5fe1e`, tree
  `c9d028016968c6f5b0439be23e26e55a175b7cbf`.
- [Patch 0156](../../patches/v7.1.3/0156-lib-buildid-add-an-exact-GNU-note-parser.patch),
  SHA-256 `4bdf4f1d264ab3a7a1debaf4a731df9d7edcf6fa292ab72ab0eaabe9c72597b6`.
- [Patch 0157](../../patches/v7.1.3/0157-arm64-bind-late-CPU-profile-to-kernel-identity.patch),
  SHA-256 `e184e3c9e04bc51a75001d8dfcdde87ff333dfdab235cf7780dc89f491561950`.
  Both patches use the synthetic non-certifying author
  `Gemini Mainline Project <noreply@invalid>`, contain no `Signed-off-by`, and
  are not submission-ready.
- Selected profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate-a41-kernel-identity`.
- [Selected series](../../patches/series-a72-reject-gate-a41-kernel-identity):
  99 entries, SHA-256
  `d81fba3214e53bf3f05f4fde64e43f70638e863d04e01355e396a5990f21289d`.
- Ordered patchset identity:
  `b048363e27e86326bf0fdd24af2d739d69658929b3de7e147634ecf266d134e5`.
- Selected source-state identity:
  `1bafbcc101bb2094216fb1d25e33045984f50bd4d49d3c48b5ec3283664abcf3`.
- Ordered configuration-input identity:
  `4dca4e50ab039fbc60593e86d20d02e74e257dc6b5bb1afa94b38be6295b5203`.
- Aggregate source diff SHA-256:
  `90e8ad3c3f9be58ef8f089f72f935e6f54aaa2473ada1145eebdb67a79593239`.
- ABI/profile: `ARM64_LATE_CPU_PLAN_ABI=7`,
  `mt6797-a53-a72-a41-v7`.
- No configuration was resolved and no compiler, build, package, boot image,
  deployment path, or target partition was used.
- Network and device access: none.

## Safety assessment

The work changed and inspected source, generated two format patches, and ran
bounded local repository/source validation. It did not build a kernel, call
firmware, request CPU_ON, connect to the Gemini, write a partition, reboot, or
shut down a device.

The inherited `maxcpus=8`, patch-0092 CPU-boot `-EAGAIN`, CPU-disable false,
profile `-EAGAIN`, and COMMIT_PATH gates remain. `SEALED_IDENTITY` contains no
target observation and cannot authorize admission.

The contemporaneous owner report that Gemian was rebooting is recovery-only
context. It was not observed or attributed to these unbuilt patches and is not
evidence for this experiment.

## Associated records

- [Design and exact contracts](DESIGN.md)
- [Field ownership](results/field-ownership.tsv)
- [Implementation markers](results/implementation.tsv)
- [Independent identity oracle](scripts/oracle.py)
- [Oracle tests](scripts/test_oracle.py)
- [Offline validator](scripts/validate.py)
- [Intended-check mutation suite](scripts/test_mutations.py)
- [Oracle transcript](results/identity-oracle-validation-20260805.txt)
- [Offline transcript](results/offline-validation-20260805.txt)
- [Mutation transcript](results/mutation-validation-20260805.txt)
- [Kernel static review](results/kernel-static-review-20260805.txt)
- [Patches 0156](../../patches/v7.1.3/0156-lib-buildid-add-an-exact-GNU-note-parser.patch)
  and [0157](../../patches/v7.1.3/0157-arm64-bind-late-CPU-profile-to-kernel-identity.patch)
- [Selected series](../../patches/series-a72-reject-gate-a41-kernel-identity)
- [Selected fragment](../../configs/gemini-a72-a41-kernel-identity.fragment)
- Parent experiment:
  [ABI-6 runtime-evidence ownership](../2026-08-05-a72-a41-runtime-evidence-owner/README.md)

## Procedure

1. Start from exact ABI-6 source commit `bcfb6024…`.
2. Apply patch 0156 and require the exact intermediate tree `b065acbe…`.
3. Apply patch 0157 and require the exact final tree `c9d02801…`.
4. Inspect the generic exact build-ID helper, unchanged legacy API, and its
   nine-case KUnit source contract.
5. Trace exact OF topology/allowlist parsing, domain-separated hashes,
   big-endian serialization, and the three bounded running producers.
6. Trace stack-local collection, sealed-empty failure, sealed-identity success,
   release/acquire publication, profile cross-binding, and binding-only overlay.
7. Confirm that fixture, target-evidence, plan, commit, READY, CPU boot, CPU
   disable, and `maxcpus=8` boundaries remain closed.
8. Run the independent 48-case identity oracle.
9. Run the exact repository/source validator and intended-check mutation suite.
10. Run source diff whitespace, Checkpatch, and duplicate-include review. Do
    not compile, build, package, deploy, or access the device.

## Observations

- Patch 0156 adds a full-buffer, exact-one GNU note parser and nine KUnit source
  cases without changing the legacy parser.
- Patch 0157 adds a 16-property static OF contract, three independent running
  producers, atomic private staging, and `SEALED_IDENTITY`.
- Reordered OF properties are accepted; missing, duplicate, unknown,
  `running-*`, dynamic, malformed, or mismatched inputs are rejected.
- Successful profile overlay copies only the verified identity binding and
  clears only RUNTIME_BINDING after profile/config/CPU/MPIDR cross-binding.
- No target observation, runtime evidence identity, plan identity, capability
  mutation, commit, READY token, or admission path is added.
- The independent oracle passed 48/48 cases.
- No KUnit execution, kernel build, runtime test, network access, or device
  action was performed.

## Analysis

ABI 7 closes the immediate missing-producer gap without conflating kernel
identity with target runtime safety. The expected record is intended to be
supplied by the validated package authority; no package authority was emitted
or exercised in this source-only milestone. The running values come only from
architecture-owned memory. Equality is useful only because those authorities
are distinct and the core publishes a complete binding atomically.

The record does not establish secure boot or measure mutable live text. Its
build-ID component inherits the strength of a 20-byte SHA-1 build ID, and the
record digest is an integrity cross-reference rather than a signature.

The deliberately narrow overlay matters: removing RUNTIME_BINDING does not
remove target, capability, effect, validation, or commit blockers. CPU8 and
CPU9 remain offline and unobserved.

## Conclusion

Confirmed only for exact patches 0156/0157 and their offline contracts:
`PARTIAL_KERNEL_IDENTITY_BINDING`. The core can produce and seal a verified
kernel identity binding as `SEALED_IDENTITY`, while complete runtime evidence,
PLAN_FROZEN, COMMITTED, READY, and CPU admission remain unreachable.

`a41_complete=no`, `runtime_evidence_complete=no`,
`target_evidence_complete=no`, `boot_candidate=false`, `build_authorized=no`,
and `device_action_authorized=no`.

This is not a build result, runtime result, hardware-support result, or claim
that CPU8 or CPU9 can execute safely.

## Follow-up boundary

[The roadmap](../../docs/ROADMAP.md) alone owns ordered next steps. This source
experiment does not authorize a build, package, deployment, CPU_ON request,
boot, or device action.
