# Mainline A72 attestation and READY closure design

## Provenance rule

The pmsg-observed capsule is a prior-cycle measurement made by two bound tasks
under the exact experiment-only Gemian kernel. It may establish an expected
target contract for this named device and source lineage. It may not populate
ABI-7 fields whose names or validation semantics claim a current-mainline
runtime observation.

In particular, the implementation must not copy the capsule into
`observed_target_mpidr`, `observed_target_midr`,
`observed_target_revidr`, or a production `target_cap` while describing the
record as `ARM64_LATE_CPU_BINDING_RUNTIME`. A new schema must make expectation,
field validity, and current-entry validation explicit.

## Exact mapping boundary

The capsule measures 24 of the 47 fields in
`arm64_late_cpu_register_image`. It separately measures MPIDR and CLIDR. The
remaining 23 register-image fields stay unmeasured; a zero value is not a
substitute for a missing observation.

The coarse ABI-7 `ID_REGS_VALID` bit therefore cannot truthfully describe the
capsule as a complete current target image. The expected-target schema needs a
field-valid mask or an exact named-field version. Only fields consumed by a
reviewed capability, HWCAP, or entry predicate may be required; every other
field remains explicitly absent.

## Ownership layers

1. **Prior-cycle target expectation** — the frozen capsule values and their
   committed result identity. This layer has no current-boot mutation right.
2. **Current-image binding** — the existing arm64 producer verifies the exact
   IKCONFIG, GNU build ID, and command line against the candidate provenance
   leaf. Container construction must include the leaf.
3. **Current-system and policy input** — arm64 owns boot-CPU/system feature
   state; the MT6797 profile may describe immutable board expectations but may
   not invent runtime observations. SMCCC conduit and mitigation command-line
   policy must come from the current mainline boot.
4. **Canonical planning** — arm64 classifies every compiled local capability,
   derives typed effects, intersects user-visible capabilities, and hashes
   named fields rather than structure padding.
5. **Architecture commit** — one callback-free arm64 path applies the frozen
   effects monotonically before system capability finalization and records an
   exact receipt. A platform callback cannot mutate alternatives or HWCAPs.
6. **Verification/finalization** — architecture and profile checks prove the
   committed effects, strict capability state, alternatives, and user HWCAPs
   equal the plan before READY publication.
7. **Target-entry enforcement** — after READY and the one CPU8 request, the
   target compares its current state against the expected contract before
   ordinary secondary startup. Any mismatch remains fail-closed. CPU9 is not
   requested; no error path calls CPU_OFF.

The exact current secondary C path first runs standard local capability/HWCAP
verification, then records `cpu_data`, then notifies the GIC/timer owners, and
only later publishes the CPU online. Linux 7.1.3's existing CPU-info reader
already covers the modern ID-register image with feature-conditional reads for
registers that may trap. The new contract comparison belongs immediately after
`cpuinfo_store_cpu()` and before `notify_cpu_starting()`. It separately reads
raw CTR and CLIDR because the CPU-info record intentionally stores effective
CTR.

## Required ordering

The immutable order is recorded in the JSON ledger. READY cannot precede
current-image binding, current-system/policy capture, expectation freeze,
canonical planning, plan identity, architecture commit, system verification,
alternatives finalization, or user-HWCAP finalization. A physical CPU request
cannot precede READY. Target-entry validation cannot run until the requested
target executes, and ordinary secondary startup cannot run until that
validation passes.

## Logical implementation slices

The closure is intentionally split so each patch has one reviewable claim:

1. add the expected-target schema, canonical field serializer, and parser with
   no producer, consumer, commit, or CPU request;
2. add the fail-closed `secondary_entry` comparison seam with no production
   expectation and no request;
3. add current-mainline system/policy producers and exact negative tests;
4. extend the pure planner and canonical identities;
5. implement the callback-free architecture commit and receipt;
6. implement system/alternatives/HWCAP verification and READY publication;
7. bind the exact Gemini expectation and construct one CPU8-only candidate.

Every slice remains unreachable or fail-closed until all prior owners exist.
The first physical candidate is not permitted to request CPU9, retry, or call
CPU_OFF.

## Rejection conditions

Reject a definition or implementation that:

- labels the Gemian capsule a current-mainline runtime observation;
- treats an unmeasured register as zero or complete;
- marks ABI-7 `ID_REGS_VALID` complete from the 24-field subset;
- imports Gemian GIC, hyp, SMCCC, ASID/granule/VA, mitigation, or system policy;
- clears a blocker without the corresponding evidence owner;
- allows a profile/platform callback to commit architecture state;
- publishes READY before exact receipt and finalization checks;
- requests CPU8 before READY, requests CPU9, retries, or calls CPU_OFF; or
- lets an entry mismatch continue to normal secondary startup.
