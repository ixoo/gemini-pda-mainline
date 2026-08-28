# Experiment: arm64 late-CPU READY evidence-gap audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-mainline-a72-ready-evidence-gap-audit` |
| Status | `completed-source-audit` |
| Subsystem | arm64 late-CPU capability admission and MT6797 A72 entry wire |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-28 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 7 READY-token closure |

## Question or hypothesis

Does the corrected serviceable one-shot stop only because its DT lacks the
late-CPU provenance leaf, or does the exact prepared kernel source still lack
other required runtime-evidence and architecture-commit stages before it can
publish an arm64 late-CPU READY token?

## Provenance and environment

- Repository parent: signed commit `4811f771a292d16b0a7c8360ee1c5c80b39305ed`.
- Runtime discriminator: the exact corrected softtrace boot and terminal
  admission record in
  [`../2026-08-28-mainline-a72-admission-softtrace-serviceable/README.md`](../2026-08-28-mainline-a72-admission-softtrace-serviceable/README.md).
- Prepared source: Buildbox-managed Linux 7.1.3 series tree with state marker
  `16b5e467943d87d5fedb162770a7e2229d5a40fed596eb54d9167abba15105ce`.
- Exact source hashes and line-level findings:
  [`results/exact-source-audit-20260828.txt`](results/exact-source-audit-20260828.txt).
- Build backend: none. This is a read-only source audit; no native VM build ran.

## Safety assessment

The audit read only the already-managed prepared source on Buildbox and existing
sanitized repository evidence. It did not build a kernel, create a candidate,
contact a physical register, request CPU_ON or CPU_OFF, write a partition, or
change device state. The owner-selected repeat of the already-retired softtrace
image supplied no executing shell or new attributable evidence and returned to
ordinary Gemian; it was not triggered.

## Associated code

No source change is associated with this audit. The audited files and their
exact hashes are recorded in
[`results/exact-source-audit-20260828.txt`](results/exact-source-audit-20260828.txt).

## Procedure

1. Bind the audit to the exact corrected softtrace result and prepared-source
   state marker.
2. Trace the controller's READY-token dependency backward through arm64 profile
   preparation, evidence sealing, capability commit, and final publication.
3. Inventory every write to the private runtime-evidence object.
4. Inspect the MT6797 profile's production prepare/validate paths separately
   from its fixture-only evidence.
5. Inspect the P30E target claim/publication path and compare its comments with
   its actual call sites in `secondary_entry` and `smp.c`.
6. Separate observations from the implementation direction; leave ordered work
   to `docs/ROADMAP.md`.

## Observations

### Runtime boundary

The corrected live terminal was `operation_ret=-11`, `core_consumed=0`, with
zero CPU8, CPU9, CPU_OFF, or retry requests. Controller source checks the binder
first and then calls `arm64_get_late_cpu_ready_token()` before source
registration or core consumption. The complete same-boot frame therefore
localizes this attempt to a null READY token, not a CPU_ON failure.

### Runtime evidence has no target producer

The arm64 core owns one private `late_runtime_evidence` object. Its exact write
inventory contains initialization, empty-storage validation, a runtime-binding
blocker, and assignment of the verified identity binding. No production path
writes either target's observed MPIDR/MIDR, register image, target capability
evidence, target policy evidence, or system capability evidence.

`arm64_seal_late_cpu_runtime_evidence()` also requires the object to be empty
before sealing. It can publish only `SEALED_EMPTY` or `SEALED_IDENTITY`; it
cannot currently publish a complete target-evidence record.

### Production profile is intentionally incomplete

The MT6797 READY validator requires both CPU8 and CPU9 in the target mask,
observed MPIDRs `0x200` and `0x201`, and nonzero plan, parent-source,
configuration, and evidence identities. CPU8 admission is therefore coupled to
truthful CPU9 evidence as well.

The production profile does not supply those observations. The arm64 core
rejects a profile that claims `RUNTIME` origin, and accepts fixture origin only
for the explicitly non-runtime test record. The production preparation path
retains its full blocker mask and returns `-EAGAIN`.

### ABI 7 has no capability commit

Even a complete evidence object would not make READY reachable. ABI 7
unconditionally adds `ARM64_LATE_CPU_BLOCK_COMMIT_PATH` during plan preparation.
`arm64_commit_late_cpu_profile()` is an intentional panic stub stating that the
architecture-owned mutation implementation is unavailable. READY publication
occurs only after commit, system verification, alternatives finalization, and
user-HWCAP finalization.

### P30E is connected but cannot break the ordering cycle

The P30E assembly comments say that the primitives are dormant and not
connected to `secondary_entry`, but the exact code is authoritative:
`secondary_entry` calls `arm64_mt6797_a72_p30e_target_claim()`, and the secondary
startup and early-failure paths publish through the matching target function.
The current slot reserves 2,048 bytes while using 160 bytes of wire data plus a
32-byte target boot identity, so a bounded target evidence capsule can fit
without creating another shared object.

That capacity is not itself an evidence source. The current admission path may
issue CPU_ON only after READY, while target evidence can be collected only
after CPU8 and CPU9 execute. Extending P30E alone therefore leaves a circular
dependency unless a separately reviewed evidence-only power path is added.

### Same-day repeat observation

The owner selected the already-retired softtrace image once more. Exact USB was
reachable, but the netcat endpoint only echoed input and never exposed an
executing shell or kernel output. The connection then closed and ordinary
Gemian was reachable as release `3.18.41+` with boot ID
`fcb93f2c-346d-4d81-a626-24227488ebf1`. No trigger, CPU request, partition
read/write, or reboot command was sent. This adds no mainline classification
and does not reopen the retired candidate.

## Analysis

The missing provenance leaf is a real construction requirement, but it is not
the cause of the complete READY failure. Three independent implementation gaps
remain: a truthful target-evidence producer, a production profile that can
derive and validate a canonical plan, and an architecture-owned capability
commit/finalization path. Removing the READY check or clearing blockers would
hide rather than solve the mixed-CPU feature contract.

The lowest-risk evidence source is the already-proven Gemian-derived retained
A72 line, which repeatedly executed bounded task-context work on both CPU8 and
CPU9. A new child can read each target's architectural registers from a bound
callback after the exact proven parent gate, publish only a versioned immutable
capsule, and preserve every existing power, watchdog, CPU_OFF, workload, and
recovery boundary. Mainline-derived policy and system-wide fields must remain
separate; vendor-kernel values cannot be treated as a ready-made mainline
capability decision.

## Conclusion

`confirmed-three-layer-ready-gap`: the exact source cannot publish READY by
restoring provenance alone. It lacks target evidence, leaves the production
profile fail-closed, and deliberately has no ABI-7 architecture commit. The
current P30E seam is already connected to secondary entry and has enough
reserved storage for a future bounded capsule, but it cannot collect evidence
without first resolving the READY-before-CPU_ON ordering cycle.

This is source evidence only. It does not establish new hardware support and
does not change `docs/HARDWARE_SUPPORT.md`.

## Follow-up

Continue only through the ordered READY-closure action in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md). The first child should collect
target-local register evidence on the exact repeatable Gemian-derived
scheduler-context parent without changing its proven power or recovery path.
