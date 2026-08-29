# Experiment: CPU8/CPU9 target-register capsule

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-a72-target-register-capsule` |
| Status | `runtime-attempt-1-inconclusive-evidence-loss` |
| Subsystem | MT6797 retained Cortex-A72 pair and arm64 ID-register evidence |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-28 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 7 READY runtime-evidence closure |

## Question or hypothesis

After the exact repeatable scheduler-context parent passes every existing
startup, coherency, workload, placement, completion, and cleanup predicate, can
one bounded task on CPU8 and one on CPU9 each publish a complete immutable
architectural-register capsule that agrees with the target's existing
per-CPU `cpu_data` record?

## Provenance and environment

- Exact parent experiment:
  [`2026-08-03-a72-scheduler-context`](../2026-08-03-a72-scheduler-context/README.md).
- Exact parent Gemian source commit:
  `59e00a9144d782e148332009a835b99c43382467`.
- Exact parent scheduler patchset SHA-256:
  `bd5799cecd14aa34a87562b09507a6d9f18f11cd138420bcba629f12793e7bfe`.
- Exact reconstructed parent `arch/arm64/kernel/psci.c` SHA-256:
  `a09af27d80e502a7c62e365f271ed74f6f09212935882e242d4d0f432ec29f34`.
- Parent runtime: two attributable cycles with adjacent exact pair-v6/pair-v7
  PASS terminals, bounded scheduler-context work on CPU8 and CPU9, clean task
  retirement, watchdog recovery, and unchanged boot2.
- Build backend: Buildbox only. No native VM kernel build is permitted.

## Safety assessment

The child changes only the two already-bound scheduler tasks after the complete
pair-v6 parent gate. Each task disables preemption briefly, reads a fixed list
of read-only architectural identification/cache/timer registers, compares the
overlapping values with its already-populated `cpu_data`, publishes one static
capsule, and resumes the unchanged parent rendezvous and workload.

It adds no CPU_ON, CPU_OFF, PSCI, SMC/HVC, MMIO, regulator, clock, reset,
watchdog, affinity, scheduling-policy, retry, storage, or reboot action. It
does not read arbitrary newer system-register encodings. The fixed list is the
register inventory already read by the exact 3.18 `cpuinfo_store_cpu()` path,
plus MPIDR, REVIDR, CLIDR, and ID_AA64DFR0; the latter DFR0 access is already
used by the same kernel's debug/perf paths. Existing watchdog recovery and the
CPU_OFF prohibition remain byte-identical.

No candidate may be built until deterministic transformation, exact-parent
reversal, field serialization, output schema, forbidden-action inventory, and
negative mutations pass. A future physical boot must use one new candidate and
one fixed decision map; the proven parent must not be rerun unchanged.

## Associated code

- [`DESIGN.md`](DESIGN.md): exact capture, publication, result, and decision
  contract.
- [`scripts/capsule_edits.py`](scripts/capsule_edits.py): deterministic
  one-file transformation of the exact scheduler parent.
- [`scripts/test_capsule_child.py`](scripts/test_capsule_child.py): exact-parent
  reversal, semantic inventory, output-schema, and negative-mutation tests.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox): reconstructs
  the exact parent from public Git inputs and emits only the child patch.
- [`scripts/build-on-buildbox`](scripts/build-on-buildbox): selects the exact
  scheduler-unpark parent and the register-capsule comparison mode in the
  shared Gemian compile-review lane.
- [`scripts/assemble.py`](scripts/assemble.py): pins the proven scheduler
  Android-v0 contract and substitutes only the accepted capsule kernel field.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh): performs two raw
  assemblies and two independent exact-size padding constructions offline.
- [`scripts/test_candidate.py`](scripts/test_candidate.py): independently pins
  and parses the complete container/tool chain and rejects candidate mutations.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh): derives the guarded
  installer with the exact observed predecessor and candidate identities.
- [`scripts/capture-live-outcome.sh`](scripts/capture-live-outcome.sh): retains
  read-only numbered USB snapshots through all eight capsule records.
- [`scripts/validate_capture.py`](scripts/validate_capture.py): validates live
  or raw-pstore phase, terminal, schema, and recomputed-identity evidence.
- [`scripts/test_runtime_tools.py`](scripts/test_runtime_tools.py): freezes
  deployment, collection, parser, decision-map, and negative-mutation gates.
- [`patches/series`](patches/series): the exact admitted one-patch child series.
- [`results/definition-validation-20260828.txt`](results/definition-validation-20260828.txt):
  local syntax, ShellCheck, serialization, exact-reversal, and mutation result.
- [`results/source-generation-20260828.txt`](results/source-generation-20260828.txt):
  exact fourth-generation identity, style result, and admission decision.
- [`results/compile-review-attempt1-20260828.txt`](results/compile-review-attempt1-20260828.txt):
  both exact compile passes and the rejected standalone-symbol gate assumption.
- [`results/compile-review-20260828.txt`](results/compile-review-20260828.txt):
  accepted exact child-versus-parent Buildbox binary and stack review.
- [`results/offline-container-review-20260828.txt`](results/offline-container-review-20260828.txt):
  two-root deterministic Android-v0 and full boot2 candidate validation.
- [`results/runtime-decision-map-20260828.txt`](results/runtime-decision-map-20260828.txt):
  fixed one-attempt observation sequence and complete outcome map.
- [`results/runtime-tooling-validation-20260828.txt`](results/runtime-tooling-validation-20260828.txt):
  read-only predecessor observation and accepted runtime-tooling gates.
- [`results/retention-path-audit-20260828.txt`](results/retention-path-audit-20260828.txt):
  rejects returned-empty custom ledgers and selects the exact same-version
  Gemian pmsg witness contract.
- [`results/deployment-20260828.txt`](results/deployment-20260828.txt): exact
  live-GPT boot2 write, full readback, cleanup, and clean-shutdown evidence.
- [`results/runtime-attempt-1-evidence-loss-20260828.txt`](results/runtime-attempt-1-evidence-loss-20260828.txt):
  safely recovered marker-free cycle and fixed-map classification.

## Procedure

1. Freeze the exact parent source, patchset, `psci.c`, and runtime evidence.
2. Validate the deterministic editor and negative mutations locally.
3. Commit and push the clean definition, then generate the one-file child patch
   from that exact commit on Buildbox.
4. Fetch, review, admit, and pin the generated patch and patchset identities.
5. Extend the existing Buildbox compile review so the exact unpark parent is
   the binary comparison and capture symbols/reads/output/stack are inspected.
6. Define deterministic container, guarded boot2 deployment, and one-attempt
   runtime classification before any device write.
7. Commit and push the runtime tools, arm changed-cycle pstore and read-only
   USB capture, deploy exact boot2 once, recover, and apply the fixed map.

## Observations

- The exact 3.18 `cpuinfo_store_cpu()` path already runs on every secondary and
  stores CNTFRQ, CTR, DCZID, MIDR, six AArch64 ID registers, and twelve
  AArch32 ID registers in per-CPU `cpu_data`.
- The same source already reads ID_AA64DFR0 in debug, hardware-breakpoint,
  perf, and KVM code. MPIDR, REVIDR, and CLIDR are architected read-only
  identity/cache registers on the target architecture.
- The accepted scheduler child runs one normal-priority bound task on each A72
  only after the complete pair-v6 parent predicate. Its result storage is
  static and zeroed before the one run.
- Ordinary Gemian's passive hotplug state does not naturally retain CPU8/CPU9;
  the already-proven experiment-only parent is the available bounded execution
  source. A same-day 12-second passive sample therefore supplied no substitute
  target evidence.

At the definition stage, the deterministic editor and validator passed Python
syntax, one positive definition case, exact field inventories, and thirteen
unsafe mutations. Both shell files pass `bash -n` and ShellCheck, and the
Buildbox command is exposed by the local help path. No source generation,
build, candidate, deployment, or new runtime result had occurred at that gate. See
[`results/definition-validation-20260828.txt`](results/definition-validation-20260828.txt).

Buildbox generation attempt 1 reconstructed and reversed the exact parent and
produced a one-file child, but source review rejected that patch before build:
the writer published `complete` after `smp_wmb()`, while the terminal reader did
not explicitly execute the matching `smp_rmb()` before recomputing and printing
the identity. The definition now adds that read-side barrier and a thirteenth
negative mutation. Attempt-1 patch SHA-256 `4b510a1b...` is rejected and must
not be admitted or built.

Generation attempt 2 added the barrier pair and again passed exact-parent
reversal and all source mutations. The exact older Gemian `checkpatch.pl` could
not run under Buildbox's current Perl because its own unescaped-brace regexes
are incompatible. Linux 7.1.3 strict Checkpatch then identified only local
formatting, barrier-comment, and the expected synthetic-signoff findings. Patch
`4b00eb82...` is rejected before build while those substantive style findings
are corrected. The experiment-only patch will remain explicitly
non-submission-ready and without a synthetic `Signed-off-by`.

Generation attempt 3 passed exact reconstruction, byte-identical reversal,
field/source validation, and all thirteen mutations. Modern strict Checkpatch,
with only `MISSING_SIGN_OFF` ignored, reported zero errors, zero warnings, and
two declaration-alignment checks. Patch `79d592e6...` is therefore also
rejected before build. The definition now uses canonical continuation alignment
for those final two declarations.

Generation attempt 4 from signed repository commit `74e3fe0e` again
reconstructed the complete public parent chain and reversed the child to exact
parent `psci.c`. All thirteen mutations and the exact one-path inventory pass.
The generated source commit is `5ce64e79...`; the admitted patch SHA-256 is
`f4070ea0...`. Linux 7.1.3 strict Checkpatch reports zero errors, warnings, or
checks when only the intentionally absent synthetic signoff is ignored. The
patch and one-entry series are now admitted, and the generator is pinned to
reproduce them byte-for-byte. No kernel build has run.

The Buildbox compile lane compares that exact child against
the scheduler-unpark parent under identical configuration and toolchain inputs.
Its pre-package gates require the two child-only standalone functions and the
two expected inlined helpers, four complete output parts, both target-task
capture phases, exactly 26 additional compiled `mrs` instructions in the child
scheduler task relative to the parent, no PSCI/MMIO/clock/regulator/sleep call,
unchanged inherited scheduler terminals, identical compiler diagnostics, and
bounded stack use for every emitted capsule and affected scheduler function.

Compile attempt 1 at exact signed commit `44d3dce7` reconstructed and validated
the source, then both child and exact scheduler-parent kernels compiled. The
binary gate correctly stopped before packaging because pinned GCC 6.3 inlined
the static capture and cpuinfo-match helpers, while the first lane definition
incorrectly required standalone symbols for both. The admitted source remains
unchanged. The corrected lane instead freezes that exact compiled shape and
measures the fixed register-read inventory as the child-versus-parent task
disassembly delta. Attempt 1 has no package, candidate, device write, or runtime
claim.

Compile attempt 2 at signed commit `f3627d4e` passed that corrected gate. Both
exact trees compile, resolve byte-identical configurations, and emit identical
inherited diagnostics. Child task disassembly contains exactly 26 `mrs`
instructions while the exact parent contains zero, with no forbidden call.
The two expected standalone helpers, four output records, both capture phases,
all inherited scheduler terminals, and focused stack bounds pass. The fetched
package independently validates; accepted `Image.gz-dtb` is `de81aa06...`.

Offline candidate construction then retained two independent roots. Each root
performed two byte-identical Android-v0 assemblies and two independent padding
paths. Both complete five-file roots are byte-identical, strict manifests pass,
the 12-assembler validator parses the header, extents, kernel, ramdisk, legacy
image ID, and all-zero tail, and 12/12 mutation instances are rejected. The raw
identity is `d4ae9ee1...`; exact 16 MiB boot2 identity is `f8e247e5...`. No
device access, deployment, or runtime result occurred.

Before deployment, a read-only known-good Gemian observation resolved live-GPT
boot2 to inactive, unmounted `/dev/mmcblk0p30` with predecessor `df82bbfa...`;
root remained `/dev/mmcblk0p29`, CPUs online were `0-1`, and battery state was
present, 100 percent, Good. The derived installer pins that predecessor and
exact candidate `f8e247e5...` while retaining full-partition readback,
no-fresh-backup, cleanup, and confirmed-shutdown gates.

The read-only collector fixes a decision-relevant race in the inherited tool:
pair-v7 is no longer enough to stop capture because the new capsule records
are emitted immediately afterward. Terminal capture now requires all eight
source-ordered records. The parser accepts numbered live snapshots or raw
pstore, validates 43 phase records and both inherited terminals, checks exact
field schemas, and recomputes both 64-bit capsule identities. Four installer
identity mutations and twelve capture mutations are rejected. No device write
or runtime attempt had occurred at that tooling gate.

Deployment from signed commit `fab8f7e8` matched observed predecessor
`df82bbfa...`, resolved only inactive `/dev/mmcblk0p30` boot2 against root
`/dev/mmcblk0p29`, wrote exact `f8e247e5...`, matched the synchronized full
readback and independent 16 MiB stream, removed temporary state, and confirmed
the device unreachable after clean shutdown. No fresh backup or reboot was
requested.

Runtime attempt 1 used changed-cycle pstore and the read-only USB/netcat helper
already armed while the device was off. The owner selected boot2 once and
reported its automatic return toward Gemian. Recovery had a changed boot ID and
watchdog-class reason; CPU8/CPU9 were offline, boot2 remained inactive and
unchanged, and battery state was healthy. However, console-ramoops contained no
candidate, phase, pair, or capsule marker, and the exact USB interface never
appeared during the collector's full 300-second window. The fixed map therefore
classifies `NO ATTRIBUTABLE MARKER OR EVIDENCE LOSS`. This is not a capsule or
kernel failure and establishes no target-register result. The exact candidate
is retired and must not be repeated unchanged.

The follow-up retention audit rules out simple console-tail truncation: the
marker-free 64-KiB window spans the time where the proven scheduler parent
previously emitted its complete trace. It also rejects the prior GAEL/DBGC and
admission ledgers as negative entry oracles because positive-control execution
has returned those slots empty. Exact source and repeated recovery evidence do
support one distinct same-version path: Gemian's separate 64-KiB pmsg ring.
The next child will add a bounded kernel pmsg helper plus entry, pre-scheduler,
and mutually exclusive pre-capsule terminal records. That path is deliberately
not valid for the differently aligned mainline-to-Gemian pmsg layout.

## Analysis

Copying `cpu_data` alone would rely on source attribution for target locality.
Reading the same safe inventory from within each bound task and comparing it
field-by-field with that CPU's prior record provides two independent paths:
the current task placement oracle and the secondary-startup record. The capsule
hash serializes named fields rather than structure bytes, so padding and host
layout cannot affect its identity.

This capsule is target evidence, not a mainline policy decision. It deliberately
does not claim system capability state, GIC/hyp usability, SMCCC mitigation
policy, ASID/page/VA configuration, capability commitment, READY, production
scheduling, CPU_OFF, or sustained load. Those fields must be derived and
validated by the mainline architecture owner after the raw target record is
captured.

## Conclusion

`runtime-attempt-1-inconclusive-evidence-loss`: deployment and safe recovery are
established, but no candidate identity survived either observation path. The
target-register hypothesis was not exercised, READY did not advance, and no
hardware-support claim exists.

## Follow-up

Continue only through the ordered action in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md): do not repeat `f8e247e5...`. Audit
the exact successful scheduler-unpark retention path and available reserved
retained-RAM contracts, then freeze one distinct pre-scheduler candidate-entry
and pre-capsule-terminal observation path that remains recoverable when both
console-ramoops and USB are absent. That audit is now complete and selects the
same-version Gemian pmsg ring. Define and mutation-test the bounded pmsg child
before Buildbox or deployment. That definition now lives in the
[`same-version pmsg witness`](../2026-08-28-a72-pmsg-witness/README.md)
experiment.
