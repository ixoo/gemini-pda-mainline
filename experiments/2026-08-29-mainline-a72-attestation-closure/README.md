# Experiment: mainline A72 attestation and READY closure

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-29-mainline-a72-attestation-closure` |
| Status | `completed-source-definition` |
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
- [`results/definition-validation-20260829.txt`](results/definition-validation-20260829.txt):
  exact source hashes, field-consumer audit, positive validation, and 21
  rejected unsafe mutations.

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
6. Only after this definition passes may one source-only expectation/entry
   validation patch be designed; no Buildbox build occurs at this stage.

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

## Conclusion

`confirmed-reference-only-mapping-and-multi-owner-ready-gap`: the exact CPU8
and CPU9 vectors map cleanly as prior-cycle target expectations, but not as a
complete ABI-7 runtime-evidence record. Twenty-three register-image fields and
all current-mainline GIC/hyp, SMCCC, address-space, target-policy,
system-capability, commit, verification, alternatives, and HWCAP owners remain
open. No CPU request or build is justified by the recovered capsule alone.

## Follow-up

Finish the hardware-free ledger and mutation proof, then implement only the
separate expected-target schema and fail-closed early-entry validator. Keep
current-boot observation fields distinct. Define and prove architecture commit
and finalization in later logical patches before constructing another physical
candidate.
