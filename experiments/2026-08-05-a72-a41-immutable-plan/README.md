# Experiment: A41 immutable evidence, plan, receipt, and READY boundary

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-a41-immutable-plan` |
| Status | `completed` (offline source-contract validation only) |
| Subsystem | arm64 capability finalization and MT6797 late Cortex-A72 profile |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date(s) | 2026-08-05 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 4, A41 |

## Question or hypothesis

Can A41 replace the mixed partial-planner attestation with four explicit
objects—fallible evidence, an immutable complete plan, an
architecture-owned commit receipt, and a copied READY token—without making
any capability mutation or A72 transition reachable?

This experiment does not implement the exhaustive evaluator or architecture
mutation transaction. It cannot close A41, create a boot candidate, or
establish hardware support.

## Provenance and environment

- Kernel release: Linux 7.1.3, official archive SHA-256
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`.
- Pinned source baseline: commit
  `df9447fb8be9b03a643b00111dd25f6ce62be719`, tree
  `265ffcaf56d7ec453e0dd017f19a5373a13960ba`.
- Exact patch 0151 source parent:
  `4c0300398ae77c99faca19bb6333868e1f70b299`.
- Patch 0151 source commit:
  `9257e46ea3fd8da4766cfd0dba4b15af56cf0d6a`, tree
  `30c9cf493dda6501620e0713e657184566e5f339`, diff SHA-256
  `efb8fc57f27609efbf9a6d87eec29c11da8b0d70b1683b6603e225241d8e052c`.
- Format-patch:
  [0151](../../patches/v7.1.3/0151-arm64-split-late-CPU-evidence-from-commit-receipt.patch),
  SHA-256
  `f85f02103974b56fbb5f4c94c76fb1fd73184b72b170fe8a1240bdfb5b1f9e1f`.
  It uses a synthetic, non-certifying experiment author, has no
  `Signed-off-by`, and is not submission-ready.
- Selected series:
  [`patches/series-a72-reject-gate-a41-immutable-plan`](../../patches/series-a72-reject-gate-a41-immutable-plan),
  93 entries, SHA-256
  `617d2d4c16822bd77ee74d4ce8f50dafd5a95ad1787a753b4bb6a0b887584b05`.
- Ordered patchset identity:
  `bd2a98a26989b787e070b219eb310092aa78d4d55eada7f251ce405f9587b030`.
- Externally computed selected source-state identity:
  `bf192fa874aea9838cece3f58eec0bba2a18dc43bfe094ad9f6d635b9809ca32`.
- In-source non-circular parent identity:
  `a1573b40b7b8f5a8a87f7a2b9a431090bf714ed52c79cf1e93c78d28ce633c56`.
  It identifies the exact patch-0150 selected source state, not patch 0151
  or a running image.
- Selected manifest profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate-a41-immutable-plan`.
- Ordered configuration-input identity:
  `91694455fdc124725704ea5f0cfdeecbd9e51829d20021f328714aca76b2edb8`.
  It is not a resolved or running `.config` identity.
- Build/compiler: not invoked; no compile claim is made.
- Boot path and target partition: none.

## Safety assessment

The procedure was host-side and read-only with respect to the device. The
selected profile still inherits `maxcpus=8`; patch 0092 still returns
`-EAGAIN` from the A72 boot operation and rejects CPU disable.

Patch 0151 adds an architecture commit entry point before system capability
finalization, but its mutation implementation is deliberately unavailable.
The selected classifier returns UNRESOLVED for every local descriptor,
validation and preparation return `-EAGAIN`, no canonical plan identity is
written, and PLAN_FROZEN, COMMITTED, and READY are unreachable.

## Associated code

- [Design record](DESIGN.md)
- [Implementation markers](results/implementation.tsv)
- [Blocker inventory](results/blockers.tsv)
- [Existing-evidence audit](results/evidence-audit.tsv)
- [Exact 40-row capability census](results/capability-census.tsv)
- [Six unresolved state/effect contracts](results/unresolved-effects.tsv)
- [Kernel static review](results/kernel-static-review-20260805.txt)
- [Offline validator](scripts/validate.py)
- [Adversarial mutation suite](scripts/test_mutations.py)

The scripts require Python, Git, the pinned repository inputs, and an exact
prepared Git source checkout containing the pinned baseline and patch 0151
commit. They require no privileges, network, device access, or generated
kernel build/output tree.

## Procedure

1. Audit every A41 blocker against exact committed evidence and keep
   observation separate from inference.
2. Enumerate the exact local capability descriptors compiled by the selected
   expected profile and classify only source- or profile-static rows.
3. Separate capability-state evidence from mutation-method evidence for every
   unresolved row.
4. Apply patch 0151 to its exact parent and verify the full ABI 3 schemas,
   state transitions, publication ordering, and fail-closed profile behavior.
5. Require the architecture commit call to precede normal system capability
   finalization while proving that the current commit body cannot succeed or
   mutate live state.
6. Reject mutations that weaken provenance, the census, schemas, blockers,
   receipt checks, release/acquire publication, CPU vetoes, or source-only
   claims.
7. Run repository whitespace, manifest-series, duplicate-include,
   Checkpatch, sensitive-data, and link checks. Freeze only sanitized results.

## Observations

- The selected expected configuration has exactly 40 compiled local
  capability descriptors: 4 source/profile-static PRESENT, 30
  source/profile-static ABSENT, and 6 evidence-dependent.
- The four static PRESENT rows are AMU, hardware dirty-bit management,
  erratum 1742098, and speculative-AT. AMU and hardware dirty-bit management
  are already present on the early CPUs and are not newly required effects.
- The unresolved rows are GICv5 legacy, ICH_HCR_EL2.TDIR, mismatched cache
  type, Spectre-v2, Spectre-v4, and Spectre-BHB.
- BHB capability state depends on target CSV2.3. ClearBHB, ECBHB, WA3,
  conduit, Spectre-v2 state, and policy select a method; choosing loop
  `k=8` cannot prove that the capability is present.
- ABI 3 describes separate CPU8 and CPU9 AArch64/AArch32 register images,
  cache, GIC/hyp, ASID, granule, active-VA, and WA1/WA2/WA3 evidence.
- Typed effects cover CTR mismatch, Spectre-v2, Spectre-v4, BHB, compat AES
  suppression, and speculative-AT finalization.
- The profile resolves none of those rows yet. No plan identity, receipt
  completion, committed effect, or READY token is published.
- During this source-only work the owner reported a boot2 start followed by
  a return to Gemian. No exact candidate or measurement was tied to that
  cycle, so it is recovery chronology only and supports no kernel or A72
  conclusion.

Exact pass counts and tool versions are frozen in
[the offline validation](results/offline-validation-20260805.txt) and
[mutation validation](results/mutation-validation-20260805.txt).

## Analysis

The hypothesis is confirmed only for the boundary. Patch 0151 removes the
unsafe implication that a three-capability draft is complete and gives the
future evaluator and commit transaction explicit, typed inputs and outputs.
It also makes receipt identity and effect equality independently checkable
through system verification, user-HWCAP finalization, and READY publication.

The boundary deliberately provides no success path. Exact target register
images, firmware responses, resolved/running configuration, capability and
HWCAP compatibility, canonical plan identity, architecture mutations, and
A36/P17/P18 consumer binding remain unproved.

## Conclusion

Confirmed for exact patch 0151: ABI 3 cleanly separates fallible evidence,
an immutable plan, an architecture-owned receipt, and the only token later
admission consumers may observe. The current profile remains fail closed and
cannot mutate capabilities or admit an A72.

`a41_complete=no`, `boot_candidate=false`,
`build_authorized=no`, and `device_action_authorized=no`.

## Follow-up

[The roadmap](../../docs/ROADMAP.md) remains the sole owner of ordered
project work. This experiment does not authorize a build, deployment, boot,
CPU_ON attempt, or device action.
