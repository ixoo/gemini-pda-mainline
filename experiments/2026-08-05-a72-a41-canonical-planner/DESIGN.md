# A41 canonical read-only planner design

## Claim boundary

This milestone is `PARTIAL_READ_ONLY_PLANNER`, not a production capability
commit. It adds a canonical planner to the partial lifecycle from patches
0148/0149. It does not clear A41, make READY reachable, build a kernel, or
authorize CPU8/9.

Offline validation requires the exact prepared Git source checkout containing
the pinned baseline and final planner commit. It creates temporary patching
scratch space but no kernel build/output tree. The validator's structural
Python inspection is a review and integrity attestation for the exact scripts;
it is not a protective sandbox for arbitrary modified Python.

The attestation keeps patch 0149's non-circular pre-A41 source-parent digest
and patch 0150 updates the ordered configuration-input digest to the exact
selected planner profile. The experiment separately records the complete
post-0150 source-state digest. None of those input identities proves a resolved
configuration or the image running on a device, so the source and
configuration blockers remain set.

The exact safety chain is:

1. CPU0 activates the MT6797 profile independently of CPU8/9 custom-method
   discovery.
2. CPU8/9 registration remains bounded and exact.
3. `smp_cpus_done()` calls preparation after the early A53 set has updated
   local capabilities but before `setup_system_features()`.
4. The core rejects planning if `ARM64_ALWAYS_SYSTEM` or
   `system_capabilities_finalized()` is already true.
5. The planner reads canonical descriptors and writes only the draft
   attestation.
6. Every unknown local predicate makes planning return `-EAGAIN`.
7. The core owns `CAP_INVENTORY` and sets it on either planner or exact-plan
   validation failure.
8. The selected profile independently returns `-EAGAIN`; all remaining
   evidence blockers also stay set.

## Canonical traversal

`arm64_plan_late_cpu_capabilities()` iterates numeric slots
`0..ARM64_NCAPS-1` and consumes `cpucap_ptrs`, the same indirect table used
by normal arm64 detection, enablement, and late-CPU verification. A non-null
slot must:

- identify its own numeric slot;
- use one exact Linux 7.1.3 canonical composite type;
- use the canonical OR callback for any local `match_list`;
- terminate any `match_list` within `ARM64_NCAPS`;
- contain no nested match list.

Null canonical holes are permitted and skipped. Every non-null slot is
recorded; only local-scope entries enter target classification in this
milestone. Strict, boot, system, and ELF-HWCAP compatibility remain separate
blockers, not silently accepted classes.

`cpucap_ptrs` contains only descriptors accepted while the canonical table is
constructed. It cannot report an out-of-range or duplicate descriptor that
initialization rejected, or a source row hidden behind an early sentinel. The
planner's bitmap therefore inventories surviving canonical slots, not an
externally anchored expected descriptor set. Exact source identity and the
offline source validator remain mandatory for omission and duplicate drift.
Likewise, the `ARM64_NCAPS` loops cap iterations but cannot supply C object
extent metadata; the offline validator proves the exact pinned match-list and
MIDR-list sentinels before this source-only milestone is accepted.

The planner does not call a normal `matches()` callback because that would
evaluate the currently executing A53, not an offline A72. The profile
classifier instead returns PRESENT, ABSENT, or UNRESOLVED from frozen evidence.
For a canonical OR match list, a proven PRESENT member determines target
presence; without a PRESENT member, any unresolved member keeps the result
unresolved.

## Exact current draft

The selected MT6797 profile resolves exactly:

- `ARM64_SPECTRE_BHB`, loop method, `k=8`;
- `ARM64_WORKAROUND_1742098`;
- `ARM64_WORKAROUND_SPECULATIVE_AT`.

The two MIDR-table rows use an init-only helper which recognizes only the
canonical MIDR-range predicates and requires an exact all-revisions A72 entry.
Unknown predicates, unterminated lists, partial A72 revision ranges, and
REVIDR-fixed direct ranges remain unresolved.

BHB remains a conservative source-derived draft. Exact CSV2.3, ECBHB,
ClearBHB, firmware, and target register proof is still required before any
commit. Exact-plan validation nevertheless rejects any method other than loop,
any count other than eight, a missing capability, an unexpected required
capability, a conflict bit, or an incomplete effect mask.

## Planned-only effects

The draft records all work that a future infallible architecture commit would
need for the three current rows:

- BHB `max_bhb_k=8`;
- the global BHB loop-method bit;
- global BHB mitigation state;
- global vector-template selection;
- BHB alternatives;
- a non-vulnerable exact Spectre-v2 dependency;
- compat AES HWCAP suppression for erratum 1742098;
- speculative-AT capability finalization.

These names describe required future assertions. They do not mutate the
corresponding globals. Target-local `this_cpu_vector`, VBAR, and branch
hardening callback installation can occur only on an actual, strictly
validated target CPU and are not claimed by the vector-template bit.

## Remaining local inventory

Every other compiled local predicate remains UNRESOLVED. Important rows include
Spectre-v2/WA1, Spectre-v4/WA2/SSBS, mismatched raw/effective CTR, KPTI policy,
AMU, hardware DBM, early-local GIC/hypervisor predicates, and every conditional
erratum not proven from the exact target record.

This is deliberate. Source tables can identify likely A72 behavior, but they
cannot replace the exact current MIDR/REVIDR, ID registers, firmware responses,
resolved configuration, and command-line overrides.

## Future validate/commit split

The production design still needs a separate transaction:

1. fallibly validate exact source, resolved/running configuration, topology,
   target register image, CTR/CLIDR, firmware responses, policies, strict
   capabilities, and native/compat HWCAPs;
2. freeze an immutable complete plan and exact identity;
3. execute one allocation-free, firmware-free, callback-free, infallible
   architecture-owned commit immediately before `setup_system_features()`;
4. let normal system capability enablement and alternatives operate on the
   pre-accounted state;
5. assert alternatives, vector templates, strict/system/boot capabilities, and
   user HWCAP results;
6. bind the same identity to A36 and immediately before P17/P18;
7. revalidate the actual A72 before normal late-CPU capability checks and
   per-CPU effect installation.

No such commit exists in patch 0150.

## Rejected shortcuts

- Running `matches()` on CPU0 and treating it as CPU8/9 evidence.
- Setting raw capability bits after finalization.
- Treating a capability bit as equivalent to a parameterized mitigation.
- Assuming A53 Spectre-v2/v4 global state can worsen safely after finalization.
- Calling firmware or allocating from an infallible commit.
- Omitting nested match members or accepting an unknown predicate/effect.
- Clearing `CAP_INVENTORY` after partial classification.
- Treating configuration-input or pre-A41 source digests as running-image
  proof.
- Weakening `maxcpus=8`, patch-0092, or the disable veto.
- Spending another boot2 cycle on this source-only scaffold.
