# Experiment: mainline A72 attestation and READY closure

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-29-mainline-a72-attestation-closure` |
| Status | `completed-closure-definition; dormant slices 1-6 linked cleanly; slice 7 admitted and source-validated; enabled compile pending` |
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
- [`scripts/preflight_edits.py`](scripts/preflight_edits.py),
  [`scripts/validate_preflight_source.py`](scripts/validate_preflight_source.py),
  and [`scripts/test_preflight_mutations.py`](scripts/test_preflight_mutations.py):
  deterministic logical-slice-7 edits, positive source validation, and
  rejecting mutations for the target-only strict-verification preflight.
- [`scripts/generate_preflight_patch.py`](scripts/generate_preflight_patch.py)
  and
  [`scripts/generate-preflight-on-buildbox`](scripts/generate-preflight-on-buildbox):
  exact post-`0430` Buildbox generation, strict style, replay, and bounded
  source-only package workflow for logical slice 7.
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
- [`results/system-policy-generation-20260829.txt`](results/system-policy-generation-20260829.txt):
  exact generation, 36 rejecting mutations, and source-only admission of the
  current-system and mitigation-policy producer.
- [`results/system-policy-compile-20260829.txt`](results/system-policy-compile-20260829.txt):
  exact enabled-profile Buildbox package, linked call ordering, section and
  stack proof, and the unchanged-warning comparison after the compile repair.
- [`results/compile-validation-20260829.txt`](results/compile-validation-20260829.txt):
  configuration-off control, both rejected linked attempts, and the final
  configuration-enabled linked binary/configuration/stack proof.
- [`results/expectation-compile-20260829.txt`](results/expectation-compile-20260829.txt):
  exact enabled-profile Buildbox package, linked expected-field cache/HWCAP
  call graph, sections, stack frames, and unchanged-diagnostic comparison.
- [`results/conservative-entry-audit-20260829.txt`](results/conservative-entry-audit-20260829.txt):
  exact post-link source audit of conservative GIC/hyp/SMCCC handling,
  address-space owners, and the pre-standard-check serviceability gap.
- [`results/preflight-generation-20260829.txt`](results/preflight-generation-20260829.txt):
  exact slice-7 Buildbox attempts, package and patch checksums, 24 rejecting
  source mutations, byte-identical admission, and canonical-series audit.

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

The exact `a72-p30e-wire` rebuild at signed commit `e71ed352` passes artifact
and fetched-package checksums with 415 patches and all three required late-CPU
configuration options enabled. The linked `secondary_start_kernel()` directly
calls `arm64_validate_late_cpu_expected_target()` after
`cpuinfo_store_cpu()`. `arm64_prepare_late_cpu_profile()` now allocates only
80 bytes of stack, and neither the section mismatch nor its former 3,232-byte
frame warning appears in the complete Buildbox log. The two older unrelated
warnings are unchanged. This validates dormant linkage, not READY or hardware
support; the package is not a boot candidate. See the
[compile validation](results/compile-validation-20260829.txt).

Logical slice 3 is now generated as canonical patch `0427`. `cpufeature.c`
captures the sanitized CTR value, its strict mask, and system SSBS availability;
`proton-pack.c` maps its private current SMCCC conduit, mitigation policy,
mitigation states, and BHB method/loop state. The core accepts only a complete,
identical two-target policy record, seals it before finalization, and merges it
only after runtime-image identity cross-binding. Seven stopped attempts failed
closed on exact anchors, validator classification, or strict style. A first
successful package at `0b9d80dd` was deliberately superseded after review added
the direct string-header dependency. The first exact Buildbox generation at
`d841add7` passed checksums, replay, strict checkpatch with zero findings, all
35 rejecting source mutations, and the 158-profile series invariant. Its
configuration-enabled compile at `6c886b33` then stopped before linking: three
helper parameters named `current` collided with arm64's task-current macro,
producing strict-prototype and pointer-type errors. No package was produced.
The repaired generator at `61f45db0` renames only those parameters to `value`,
rejects restoration of the macro collision as a 36th source mutation, and
reproduces canonical patch `0427` from the same integrity-pinned post-`0426`
source. Exact checksums, replay, and strict style pass. It still adds no
target-cap producer, active expectation, planner extension, architecture
commit, READY path, CPU request, candidate, or device action. See the
[system/policy generation result](results/system-policy-generation-20260829.txt).

The exact configuration-enabled rebuild at signed commit `3d00db48` passes
Buildbox artifact validation and fetched-package checksum validation with 416
patches and all required late-CPU options enabled. Linked `smp_cpus_done()`
directly calls runtime-identity capture, system/policy capture, evidence seal,
and profile preparation in that order before system-feature setup. The new
system owner, policy owner, and combined collector allocate 32, 80, and 112
bytes of stack respectively; all are in `.init.text`, there are no section
mismatches or new frame warnings, and the three older warnings are unchanged
from the pre-`0427` build. This proves linked source ownership, not target-cap
evidence, READY, hardware support, or a boot candidate. See the
[system/policy compile result](results/system-policy-compile-20260829.txt).

Logical slice 4 is now canonical patch `0428`. It computes prospective native
and compat HWCAP intersections from the sanitized early system and both
complete target register images, then derives domain-separated SHA-256
evidence and plan identities by serializing named scalar and register fields in
big-endian order rather than hashing structure padding. The initial package at
signed commit `25777a3c` had an exact five-file manifest and passed all declared
checksums, deterministic replay, strict checkpatch with zero findings, the
positive source validator, and all 16 rejecting source mutations. Independent
review also confirmed no checkpatch cache remained in either the package or
the integrity-pinned prepared source. Current target-cap production, the
architecture commit, READY publication, every CPU request, and all device
actions remain absent. See the
[planner generation result](results/planner-generation-20260829.txt). The next
gate is an exact configuration-enabled `a72-p30e-wire` Buildbox compile and
linked-output inspection; this source-only result is not a boot candidate.

The first enabled compile at signed commit `6507f881` stopped in
`cpufeature.c` before linking because the generated compat-HWCAP gate named a
nonexistent `ARM64_HAS_32BIT_EL0` capability token. Linux 7.1.3 deliberately
names that internal pseudo-capability `DO_NOT_USE`; its public policy owner is
`system_supports_32bit_el0()`, backed by the sanitized ID_AA64PFR0_EL1 EL0
field. The generator repair uses that system policy and intersects it with the
same field in both complete target register images. A new rejecting mutation
restores the invalid token so this compile failure cannot recur silently. No
package, candidate, or device action resulted from the failed compile.
Two subsequent generation attempts stopped before packaging on strict line
break style checks. The final repaired package at signed commit `8e9d7765`
passes its exact five-file manifest, all checksums, deterministic replay,
strict checkpatch with zero findings, the positive validator, and all 17
rejecting mutations. Canonical patch `0428` is byte-identical to that package.
The exact enabled-profile rebuild at signed commit `6f3c6c07` now passes
Buildbox artifact validation and independent fetched-package checksums with 417
patches. The linked prepare path directly orders capability, effect, and HWCAP
planning before profile validation and canonical evidence/plan identity
generation. The compat path calls `system_supports_32bit_el0()` and checks both
target ID_AA64PFR0_EL1 EL0 fields. The planner remains in `.init.text`, its
stack allocation is 32 bytes, prepare remains 80 bytes, there are no section
mismatches or new frame warnings, and the three older warnings are unchanged.
The commit path is still the fail-stop panic stub; current target-cap producers,
READY publication, and every CPU request remain absent. This is linked
source-only proof, not a boot candidate. See the
[planner compile result](results/planner-compile-20260829.txt).

Logical slice 5 is now canonical patch `0429`. It removes only the obsolete
commit-path blocker, validates the frozen plan and its six audited
late-required capabilities, seeds the typed Spectre/BHB state monotonically,
sets only the planned system-capability bits, and publishes an exact COMMITTED
receipt with release ordering. It invokes no profile callback and adds no
target-cap producer, READY publication, CPU request, CPU9 path, CPU_OFF path,
candidate, or device action. Five stopped Buildbox attempts exposed three
mutation-anchor defects, two structural-validator gaps, and six strict
line-break findings; none produced a retained package. Final generation at
signed commit `52dcaaa8` rejects all 18 unsafe source mutations, passes
deterministic replay and strict checkpatch with zero findings, and produces an
exact five-file package. Canonical patch `0429` is byte-identical to that
package, and all 158 manifest profiles retain the canonical-series invariant.
The synthetic experiment-only patch identity carries no synthetic sign-off and
is not submission-ready. See the
[commit generation result](results/commit-generation-20260829.txt). The patch
remains unreachable in the production profile because current target-cap
producers are absent; the next gate is its exact enabled `a72-p30e-wire`
Buildbox compile and linked-output inspection.

That exact enabled-profile build now passes at signed commit `3c224300` with
418 patches and independently verified Buildbox and fetched-package checksums.
The plan, mitigation, profile-commit, and prepare functions all link in
`.init.text`; their stack allocations are 96, 48, 48, and 80 bytes. Linked
`setup_system_features()` calls the profile commit before system-capability
update, capability enable, and alternatives. The profile commit calls the plan
commit, copies the exact effects, sets the completion byte, and release-stores
COMMITTED. The plan calls the mitigation commit before its one set-only live
capability-bitmap update. The complete diagnostic set is identical to the
pre-`0429` baseline: there is no new section mismatch, frame warning, or
compiler warning. This proves integration only. The production profile still
has no current target-cap producer, so the commit remains unreachable; READY,
CPU requests, candidate status, hardware writes, and device actions remain
absent. See the [commit compile result](results/commit-compile-20260829.txt).

The post-build target-capability boundary audit rejects that missing-producer
description as an implementation direction. Exact source deliberately forbids
production profiles from declaring runtime target observations and deliberately
keeps the architecture runtime record target-empty before the first request;
the planner's remaining direct `target_cap[]` consumers therefore create a
READY-before-execution provenance cycle. The separate 28-field prior-cycle
expected pair is the legitimate pre-request contract, but it cannot set the
coarse current `ID_REGS_VALID` bit or zero-fill its 23 unmeasured fields.
Logical slice 6 must separate a field-valid expected-target planning view from
current runtime evidence and migrate only pure, completely owned decisions to
that view. See the
[target-capability boundary audit](results/target-cap-boundary-audit-20260829.txt).

Logical slice 6 is now canonical patch `0430`. It exposes the existing complete
expected-pair contract to the pure planner, uses named valid prior-cycle CTR and
CLIDR fields for production cache planning, and intersects the sanitized system
HWCAP view with only the eight expected register fields actually measured.
Unavailable target fields omit the corresponding HWCAP; they are never
zero-filled or promoted to the coarse current `ID_REGS_VALID` state. The
fixture path retains its explicit current-target input, while production keeps
all runtime target observations empty and still returns `-EAGAIN` because it
does not yet activate an expected pair. GIC, hyp, SMCCC workaround, and
unmeasured modern-ID decisions remain unresolved. Four stopped Buildbox
attempts exposed one exact-source anchor mismatch, two mutation-fixture anchor
defects, and 13 strict line-break findings; none retained a package. Final
generation at signed commit `a2c7b737` passes its exact five-file package and
checksums, positive source validation, all 22 rejecting source mutations,
deterministic replay, and strict checkpatch with zero findings. Canonical patch
`0430` is byte-identical to that package, and all 158 manifest profiles retain
the canonical-series invariant. READY, CPU requests, candidate status, and
device actions remain absent. See the
[expectation generation result](results/expectation-generation-20260829.txt).
The exact enabled `a72-p30e-wire` Buildbox build now passes at signed commit
`4f57918c` with 419 patches and independently verified Buildbox and fetched
package checksums. The runtime expected-pair completeness and entry-validator
symbols remain in `.text`; the cache and HWCAP planning helpers link in
`.init.text`. Their direct call edges are present, the largest new-path stack
allocation is 112 bytes, and the complete warning set—including both MT6797
USB device-tree warning forms and counts—is identical to the immediate `0429`
baseline. There is no new section mismatch, frame warning, or compiler warning.

This closes logical slice 6 as linked integration evidence, not hardware
support. Production still has no active expected pair and returns `-EAGAIN`;
GIC, hyp, CPU-local SMCCC workaround, and unmeasured modern-ID inputs remain
unresolved. READY, CPU requests, candidate status, hardware writes, and device
actions remain absent. See the
[expectation compile result](results/expectation-compile-20260829.txt).

The post-link ownership audit resolves the measurement-versus-policy choice.
Another prior-cycle target measurement can refine an expectation, but it
cannot become a current-mainline pre-request observation. GICv5 legacy and ICH
TDIR can be planned absent when the finalized early system does not use them;
a late CPU is explicitly permitted to have those unused features. Unknown WA1
and WA2 outcomes can be planned as the worst Spectre state—vulnerable, with no
firmware callback—and BHB remains vulnerable when v2 is vulnerable. Missing
modern-ID fields remain HWCAP omissions.

The audit also finds one ordering prerequisite. The full expected-target check
runs after `check_local_cpu_capabilities()`, so it cannot prevent the existing
whole-kernel panic path for a smaller ASID width or a strict boot-capability
conflict. Page-granule and 52-bit-VA mismatches already park safely in assembly.
Logical slice 7 must therefore add a generic target-only boot-capability and
ASID preflight before the standard checks, while retaining every existing
check afterward. It remains dormant until READY and must not activate the exact
expected pair or add a CPU request. See the
[conservative entry audit](results/conservative-entry-audit-20260829.txt).

Logical slice 7 is now canonical patch `0431`. It compares the current late
target's ASID width without mutation and walks every linked boot-scope
capability descriptor before the standard panic-shaped verifier. The preflight
applies only to a complete READY target, parks that target on conflict, and
retains the standard verifier and later full expected-target validator.
Assembly granule and VA gates are unchanged. Two stopped Buildbox attempts
exposed mutation fixtures that changed earlier same-text regions in large
kernel files; no package was retained. The final suite scopes every
function-level mutation to its named function. Exact generation at signed
commit `7e7a401c` passes deterministic replay, strict checkpatch with zero
findings, positive source validation, all 24 rejecting source mutations, and
the bounded five-file package checksums. Canonical `0431` is byte-identical to
that package, and all 158 manifest profiles retain the canonical-series
invariant. Expected-pair activation, READY publication, CPU requests, candidate
status, native VM builds, and device actions remain absent. See the
[preflight generation result](results/preflight-generation-20260829.txt).

The logical-slice-7 generator is now prepared against the exact post-`0430`
source hashes. Its architecture facade is READY- and target-gated, its ASID
predicate is non-mutating, and its generic boot-scope walk uses the existing
descriptor match and optional/permitted semantics without calling
`cpu_enable()` or changing a system capability. The secondary call site parks
on failure before the standard verifier, then retains the standard verifier,
CPU postboot, CPU-info storage, and full expected-target check on the success
path. Descriptor match callbacks intentionally retain the same CPU-local
discovery semantics as the standard verifier. Local Python syntax, `bash -n`,
ShellCheck, and `git diff --check` pass. Exact Buildbox generation, rejecting
source mutations, replay, and strict style remain pending; there is no patch,
kernel build, candidate, or device action yet.

## Conclusion

`confirmed-reference-only-mapping-dormant-planner-linked`:
the exact CPU8 and CPU9 vectors map cleanly as prior-cycle target expectations,
but not as a complete ABI-7 runtime-evidence record. The dormant schema,
fail-closed entry validator, their section/stack integration repairs, and the
current-mainline system/policy owner, pure planner, canonical identities, and
dormant architecture commit/receipt are now reproducibly generated, admitted,
and linked. Pre-request expected-target planning separation is now reproducibly
generated, admitted, and linked. Conservative entry constraints,
expected-contract activation, alternatives/HWCAP finalization, READY, and
physical admission remain open. No CPU request is justified by the recovered
capsule alone.

## Follow-up

Follow only the selected action in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md). Keep current-boot observation fields
distinct; these dormant patches do not by themselves authorize a physical
candidate or CPU request.
