# Experiment: mainline A72 attestation and READY closure

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-29-mainline-a72-attestation-closure` |
| Status | `completed-closure-definition; dormant source admitted; linked compile exposed and repaired section and prepare-stack defects; rebuild pending` |
| Subsystem | arm64 late-CPU evidence, capability commitment, and MT6797 A72 entry |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-29 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 7 READY-token closure |

## Question or hypothesis

Can the exact recovered CPU8/CPU9 register vectors be mapped into the Linux
7.1.3 arm64 late-CPU schema without promoting prior-cycle Gemian evidence into
a current-mainline runtime observation, and can every remaining owner needed
for a truthful READY token be stated before another kernel build or CPU
request?

## Provenance and environment

- Repository parent: signed commit `f9bd0fc9`.
- Recovered target evidence: the complete pmsg-observed register-capsule pass
  in
  [`../2026-08-28-a72-pmsg-witness/results/runtime-attempt-1-complete-pass-20260829.txt`](../2026-08-28-a72-pmsg-witness/results/runtime-attempt-1-complete-pass-20260829.txt).
- Register-capsule schema and safety contract:
  [`../2026-08-28-a72-target-register-capsule/DESIGN.md`](../2026-08-28-a72-target-register-capsule/DESIGN.md).
- Prepared source: Buildbox-managed Linux 7.1.3 series tree with state marker
  `16b5e467943d87d5fedb162770a7e2229d5a40fed596eb54d9167abba15105ce`.
- Audited header SHA-256:
  `e6bde598f415d8da0ba4073c37d2c8c341a70afb1d0237fc130ad113e494cd36`.
- Audited arm64 lifecycle SHA-256:
  `22ecfb06e8d00972ffdecad6019c11f2b4d695a38c90aa3bbd6977c4c22bc29b`.
- Audited MT6797 membership SHA-256:
  `d9cd9d378e0be9c7b8ee07cc0cfceb681d78f8f3deea7d0cb64bbce93a118ad9`.
- The ledger additionally pins the MT6797 profile, arm64 capability, SMP,
  mitigation, erratum, and CPU-info source files that own the mapped fields.
- Build backend: none. This definition is read-only and hardware-free.

## Safety assessment

This experiment reads committed sanitized evidence and the exact prepared
source on Buildbox. It does not modify a kernel tree, build a kernel, assemble
or install a candidate, contact the device, request CPU8 or CPU9, call CPU_OFF,
write retained RAM, or change power state.

The definition explicitly forbids treating the prior Gemian capsule as a
current-mainline runtime observation. It also preserves READY-before-admission,
CPU8-first admission, no CPU9 request, and no CPU_OFF. A future implementation
must reject the target in `secondary_entry` before ordinary secondary startup
if its current register state differs from the frozen expectation.

## Associated code

- [`DESIGN.md`](DESIGN.md): evidence ownership, ordering, and closure contract.
- [`schema/attestation-ledger-v1.json`](schema/attestation-ledger-v1.json): exact
  two-target values, complete arm64 field partition, and missing-owner ledger.
- [`scripts/validate.py`](scripts/validate.py): independent result parser and
  ledger/ordering validator.
- [`scripts/test_mutations.py`](scripts/test_mutations.py): rejecting mutations
  for overclaim, incomplete inventory, wrong target identity, and unsafe READY
  ordering.
- [`scripts/source_edits.py`](scripts/source_edits.py): deterministic two-stage
  schema and entry-validator edits against the exact prepared source.
- [`scripts/validate_source.py`](scripts/validate_source.py): exact schema,
  comparison inventory, placement, and failure-path validator.
- [`scripts/test_source_mutations.py`](scripts/test_source_mutations.py):
  rejects missing comparisons, partial validity, reordered entry checks,
  current-CPU bypass, online continuation, CPU_OFF, and retry-shaped changes.
- [`scripts/generate_patches.py`](scripts/generate_patches.py) and
  [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox): create the
  staged synthetic-author, non-submission-ready format patches and isolated
  integration fixes from exact Git inputs and the managed prepared source;
  they do not build a kernel.
- [`results/definition-validation-20260829.txt`](results/definition-validation-20260829.txt):
  exact source hashes, field-consumer audit, positive validation, and 21
  rejected unsafe mutations.
- [`results/source-generation-20260829.txt`](results/source-generation-20260829.txt):
  exact Buildbox generation identities, patch checksums, strict style result,
  16 rejected source mutations, replay, and canonical-series audit.
- [`results/runtime-fix-generation-20260829.txt`](results/runtime-fix-generation-20260829.txt):
  exact linked-build section mismatch and the generated runtime-safe follow-up,
  including 17 rejected source mutations and canonical-series audit.
- [`results/stack-fix-generation-20260829.txt`](results/stack-fix-generation-20260829.txt):
  exact linked-build prepare-stack warning and the generated init-only-storage
  follow-up, including 20 rejected source mutations and canonical-series audit.

## Procedure

1. Freeze the exact prepared-source identities and recovered-capsule result.
2. Partition every field in `arm64_late_cpu_register_image` into an exact
   prior-cycle observation or an explicitly unmeasured field.
3. Map every target-capability, target-policy, system-capability, binding,
   identity, plan, commit, verification, alternatives, and HWCAP owner.
4. State the only permitted role of the recovered values: an immutable
   expected-entry contract, never current-boot observation.
5. Validate the ledger against the committed eight-line capsule and reject
   representative unsafe mutations.
6. Define two logical source patches: the empty field-valid schema first, then
   the fail-closed entry validator. Generate and replay them on Buildbox only
   after the exact clean definition commit is pushed.
7. Admit neither patch until strict source review and negative mutations pass.
   A later clean commit may then build them through the explicit Buildbox
   backend; no native VM build occurs.

## Observations

The recovered capsule contains 26 target-local architectural values per CPU:
24 fields from `arm64_late_cpu_register_image`, plus MPIDR and CLIDR. CPU8 and
CPU9 agree on every shared value; their MPIDRs and capsule identities differ as
expected. The exact ABI-7 register image contains 47 fields, leaving 23 fields
unmeasured by the deliberately bounded Gemian capsule.

The prepared arm64 source has only a runtime image/config/cmdline identity
producer. Its private evidence storage must be empty before sealing and can
publish only `SEALED_EMPTY` or `SEALED_IDENTITY`. The production MT6797 profile
accepts expected-only input, leaves target/system/policy evidence empty, and
returns `-EAGAIN`. ABI 7 then unconditionally adds the commit-path blocker;
`arm64_commit_late_cpu_profile()` remains an intentional panic stub. The
profile supplies neither `verify_system` nor `finalize_user` callbacks.

The current Linux 7.1.3 `cpuinfo_store_cpu()` path already reads the complete
modern AArch64 ID-register set and the feature-conditional AArch32, GMID,
SMIDR, and MPAM state using the architecture's existing safe readers. On a late
secondary, standard local-capability and HWCAP verification runs first, then
`cpuinfo_store_cpu()`, then GIC/timer notification, and only later
`set_cpu_online()`. A new exact-contract comparison therefore has a natural
fail-closed C location after the existing CPU-info record and before device
notification or online publication. Raw CTR and CLIDR remain explicit direct
entry reads because the CPU-info record stores effective CTR.

These are independent gaps. Even a complete target vector would not implement
the current-mainline system/policy producer, canonical evidence and plan
identities, architecture commit, alternatives verification, or user-HWCAP
finalization.

## Analysis

The recovered vectors are strong named-device evidence and a useful expected
contract. They are not observations made by the candidate mainline boot.
Writing them into `observed_target_*` or marking the coarse `ID_REGS_VALID` bit
complete would erase both the prior-cycle provenance boundary and the 23-field
measurement gap.

The smallest truthful direction is therefore conditional admission: freeze a
separate field-valid expected-target contract, derive only conservative global
effects from that contract plus current-mainline system and policy state,
commit those effects in architecture code, and include the expectation in the
READY identity. After READY authorizes the single CPU8 request, the already
connected early target-entry seam must compare current CPU8 state with the
contract before ordinary secondary startup. A mismatch refuses admission; it
does not attempt CPU_OFF or weaken the system plan. CPU9 remains unrequested
until its separate gate.

That direction still needs a source audit for the 23 omitted register fields
and the GIC/hyp, SMCCC, ASID/granule/VA, system-policy, alternatives, and HWCAP
owners. The ledger keeps each unresolved rather than manufacturing a zero or
borrowing Gemian policy.

The complete definition passes one positive ledger/capture case and rejects 21
mutations covering wrong target identity, incomplete or overlapping field
inventories, invented zeros, evidence-origin promotion, borrowed Gemian
policy, platform-owned commit, reordered closure, post-online validation, CPU9,
CPU_OFF, and retry. The exact nine-file prepared-source hash gate and
secondary-entry ordering gate also pass. See the
[sanitized result](results/definition-validation-20260829.txt).

The dormant implementation generator now defines two logical patches. Patch 1
adds a 28-field valid mask and one compact homogeneous-pair expectation object
to profile evidence while making the private runtime store reject any injected
expectation. It supplies no initializer or producer. Patch 2 adds a READY-bound
comparison of the 26 measured target-local values after CPU-info capture and
parks any mismatch before topology, GIC/timer notification, or online
publication. It does not change READY construction, activate a contract, or
add a CPU request. Local Python syntax, `bash -n`, ShellCheck, ledger validation,
and evidence mutations pass. Exact-source generation, patch replay, strict
style, and all 16 negative source mutations pass on Buildbox.

Buildbox generation attempt 1 at signed commit `b4e5dbfa` stopped before the
first source edit at the two-line evidence-member insertion anchor. The first
diagnosis attributed that failure to literal tab escapes in the insertion
blocks, and signed commit `431a0357` materialized those blocks with actual
tabs. Attempt 2 at that exact commit reproduced the same anchor failure,
proving the first diagnosis incomplete. Signed commit `e6507297` narrowed the
anchor to the runtime-binding member alone; attempt 3 stopped at the same
fail-closed count check. Instrumentation against the hash-pinned parent then
showed the actual count was two, not zero: the evidence and READY-token
structures both carry that member and its adjacent identity member. The editor
now binds the insertion to the complete `arm64_late_cpu_evidence` prefix and
inserts the expectation immediately before that structure's runtime binding.
No patch, retained package, kernel build, candidate, or device action resulted
from any stopped attempt; every source predicate remains unchanged.

Attempt 4 at signed commit `fec6dbfb` passed both source edits, their positive
validators, patch generation, and replay, then stopped before packaging because
strict checkpatch required a comment for the READY-state acquire barrier. The
generated validator now states that this load pairs with publication of
`late_plan` and `late_receipt`, and the negative source suite rejects removal
of that synchronization rationale. No warning is suppressed.

The final generation at signed commit `7c933ea1` passes both stage validators,
all 16 rejecting source mutations, deterministic patch replay, and strict
checkpatch with zero errors, warnings, or checks. Canonical patches `0423` and
`0424` are byte-identical to the generated package, and all 158 manifest
profiles retain the canonical-series subsequence invariant. The patches remain
dormant: there is no expected-pair initializer, READY publication, CPU request,
architecture commit, candidate, or device action. See the
[source-generation result](results/source-generation-20260829.txt).

The first configuration-enabled Buildbox compile at signed commit `cb797b6f`
reached and packaged the linked `a72-p30e-wire` image, but modpost exposed one
new section mismatch: the runtime secondary-entry validator called
`late_profile_identity_empty()`, which is init-only. The artifact is therefore
an integration-failure result despite a zero build exit and valid package
checksums. The follow-up generator is pinned to the exact post-`0424` prepared
source and replaces only that call with an equivalent runtime-safe
`memchr_inv()` zero check. Generated patch `0425` passes strict checkpatch,
replay, exact checksums, all 17 rejecting source mutations (including
restoration of the init-only call), and the 158-profile series invariant. It
adds no expectation producer, READY publication, CPU request, or device path.
See the [runtime-fix result](results/runtime-fix-generation-20260829.txt).

The configuration-enabled rebuild at signed commit `b28b2676` proves the
runtime-section repair: the prior section mismatch is absent. It also exposes
a second, independent integration defect. `arm64_prepare_late_cpu_profile()`
placed the 1,392-byte evidence object and 1,832-byte plan draft together on the
init thread's stack, producing a new 3,232-byte frame warning against the
2,048-byte limit and a 3,296-byte allocation in the linked image. That package
is therefore rejected despite its zero build exit and valid checksums.

Generated follow-up `0426` moves only those one-shot workspaces to file-static
`__initdata`, clears each before use, restores both ABI fields, and leaves
publication unchanged. Exact Buildbox generation at signed commit `028fbb6c`
passes checksums, replay, strict style, all 20 rejecting source mutations, and
the 158-profile series invariant. It adds no expectation producer, READY
publication, architecture commit, CPU request, or device path. See the
[prepare-stack result](results/stack-fix-generation-20260829.txt).

## Conclusion

`confirmed-reference-only-mapping-and-dormant-validator-integration-fixes-admitted-rebuild-pending`: the exact
CPU8 and CPU9 vectors map cleanly as prior-cycle target expectations, but not
as a complete ABI-7 runtime-evidence record. The dormant schema and fail-closed
entry validator and their section/stack integration repairs are now
reproducibly generated and admitted. Twenty-three register-image fields and all
current-mainline GIC/hyp, SMCCC, address-space, target-policy,
system-capability, commit, verification, alternatives, and HWCAP owners remain
open. No CPU request is justified by the recovered capsule alone.

## Follow-up

Follow only the selected action in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md). Keep current-boot observation fields
distinct; these dormant patches do not by themselves authorize a physical
candidate or CPU request.
