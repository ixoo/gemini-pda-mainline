# Experiment: A72 pre-isolation rollback discriminator

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-02-a72-pre-isolation-rollback-discriminator` |
| Status | `deployed-awaiting-manual-boot2`: the owner-authorized 75% deployment matched the exact predecessor, wrote only live-GPT-resolved boot2, passed synchronized flush and independent full readback, removed temporary copies, and shut the device down; the owner now manually selects boot2 |
| Subsystem | CPU8 external BUCKB preparation, MP2 reset, TOPRGU PWRAP reset, and fail-closed rollback |
| Device variant | Named Gemini PDA development unit |
| Date(s) | 2026-08-02 |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 4, ownership-matrix rows 02, 04, and 06 |

## Question or hypothesis

When the exact offline pre-state is present, can one CPU8 attempt stop after
BUCKB enable and settled readback but before clearing external isolation, then
restore only the state uniquely changed by that attempt and prove the complete
pre-state returned?

This discriminator targets the first open rollback row without crossing the
current one-way boundary. It must never clear SPM external-isolation bits, call
the SRAM-LDO service, invoke PSCI `CPU_ON`, enable MP2 DCM, request CPU9, or
permit a retry.

## Provenance and rationale

- The exact first-cycle latch retained one successful natural CPU8 pair in 46
  immutable records. See
  [`../2026-08-02-gemian-a72-first-cycle-latch/results/runtime-summary-20260802.txt`](../2026-08-02-gemian-a72-first-cycle-latch/results/runtime-summary-20260802.txt).
- The clean offline pre-state includes BUCKB disabled at VSEL `0x46`, DA921x
  page `0x80`, SPM reset state `0x00010132`, external-isolation state
  `0x00000002`, TOPRGU bit 11 clear, secure zero state, and MP2 DCM zero.
- The successful forward path changed SPM reset `0x00010132 -> 0x00010133`,
  asserted/deasserted TOPRGU bit 11, and changed BUCKB `0 -> 1` before the
  external-isolation clear.
- The Gate 4 contract permits a bounded inverse before isolation clear only
  when the attempt uniquely owns each change and current readback still
  matches. At or after isolation clear, power must instead be retained and the
  cluster faulted.

## Safety boundary

The design is intentionally narrower than CPU bring-up. Its sole future
stimulus would be an internal one-shot stop after settled BUCKB enable. CPU8
must remain offline; there is no PSCI call or secondary entry. The experiment
must use the existing owner locks and fixed DA921x/SPM/TOPRGU helpers, never raw
userspace I2C, `/dev/mem`, an arbitrary register interface, or a writable proc
control.

No implementation may proceed until source location, action ordering, owner
locks, exact readbacks, watchdog recovery, immutable evidence, and all
fail-closed mutations pass review on a clean pushed commit. Any kernel build
must use Buildbox. A real regulator write or device boot requires a separate
predeployment decision after compiler and timing review.

## Associated code

- [`DESIGN.md`](DESIGN.md): exact pre-state, injection point, rollback order,
  evidence, stop conditions and result matrix.
- [`scripts/rollback_model.py`](scripts/rollback_model.py): executable
  fail-closed reference model with no hardware or network access.
- [`scripts/test_rollback_model.py`](scripts/test_rollback_model.py): positive
  rollback plus ownership/readback and forbidden-boundary mutations.
- [`scripts/source_edits.py`](scripts/source_edits.py): deterministic three-step
  vendor-source transformation, restricted to the pinned Buildbox tree.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox): temporary
  Buildbox source, logical commits, `git format-patch`, provenance and cleanup.
- [`scripts/validate_patches.py`](scripts/validate_patches.py): exact path,
  owner, ordering, no-control and forbidden-boundary validation.
- [`scripts/test_static.py`](scripts/test_static.py): generated-patch mutation
  tripwires; it runs inside the generation job before results are fetchable.
- [`scripts/build-on-buildbox`](scripts/build-on-buildbox): exact rollback
  versus parent-observer compiler, diagnostic, symbol, and dual-stack-evidence
  comparison.
- [`scripts/test_build_lane.py`](scripts/test_build_lane.py): pins both
  patchset identities and proves the compile lane remains Buildbox-only,
  non-bootable, and device-inert.
- [`scripts/assemble.py`](scripts/assemble.py): experiment-local exact-kernel
  wrapper around the checksum-pinned Android-v0 assembler.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh): reproducible dual
  container assembly, dual padding, structural, provenance, and checksum gates.
- [`scripts/collect-passive.sh`](scripts/collect-passive.sh): checksum-pinned,
  bounded host retrieval into the ignored private evidence tree.
- [`scripts/remote-passive-capture.sh`](scripts/remote-passive-capture.sh):
  identity-gated two-read capture before optional power reporting.
- [`scripts/validate-passive.py`](scripts/validate-passive.py): exact ABI-v3
  rollback, rejected-prestate, fault-retain, and forbidden-boundary classifier.
- [`scripts/test-passive.py`](scripts/test-passive.py): positive terminal paths
  plus 18 fail-closed and no-stimulus checks.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh): source-pinned exact
  logical-boot2 installer with full-readback and clean-shutdown enforcement.
- [`scripts/install-boot2-owner-battery-override.sh`](scripts/install-boot2-owner-battery-override.sh):
  explicit one-deployment 70% battery-floor override retaining every other
  checksum-pinned installer gate.
- [`patches/series`](patches/series): the exact three-patch rollback ABI,
  owner-operation, and CPU8 orchestrator series generated from the pinned
  vendor source.
- [`results/design-validation-20260802.txt`](results/design-validation-20260802.txt):
  exact inputs, selected boundary, hashes, positive path, seventeen fail-closed
  cases and the explicit no-implementation decision.
- [`results/source-owner-review-20260802.txt`](results/source-owner-review-20260802.txt):
  pinned call-chain review, rejection of the existing observer helpers as
  safety gates, exact owner-local primitive requirements and patch structure.
- [`results/patch-generation-review-20260802.txt`](results/patch-generation-review-20260802.txt):
  exact generation provenance, tracked hashes, validation, checkpatch
  adjudication, and the compile-only decision.
- [`results/buildbox-compile-attempt-1-20260802.txt`](results/buildbox-compile-attempt-1-20260802.txt):
  both builds passed, followed by a fail-closed packaging correction for a
  file-local orchestrator symbol that GCC validly inlined.
- [`results/buildbox-compile-attempt-2-20260802.txt`](results/buildbox-compile-attempt-2-20260802.txt):
  exact successful rollback/parent comparison, output identities, inherited
  diagnostic proof, retained symbols, and stack-use deltas.
- [`results/compiler-and-timing-review-20260802.txt`](results/compiler-and-timing-review-20260802.txt):
  owner-lock composition, bounded successful-path operations, forbidden
  boundaries, stack adjudication, and the predeployment-only decision.
- [`results/predeployment-contract-20260802.txt`](results/predeployment-contract-20260802.txt):
  exact compiled identity, natural one-shot trigger, 30-record rollback result,
  14-record pre-state rejection, owner expectations, recovery, and guarded
  deployment boundary frozen before container assembly.
- [`results/offline-container-validation-20260802.txt`](results/offline-container-validation-20260802.txt):
  exact raw and padded identities, retained ramdisk, independent Android-v0
  structure, reproducibility, checksum, syntax, and ShellCheck results.
- [`results/passive-collector-validation-20260802.txt`](results/passive-collector-validation-20260802.txt):
  exact collector dependencies, identity/order gates, terminal semantics,
  mutation results, and device-inert runtime-use decision.
- [`results/installer-validation-20260802.txt`](results/installer-validation-20260802.txt):
  source identity, exact derivation tokens, retained safety behavior, syntax,
  ShellCheck, candidate-manifest, and deployment-eligibility decision.
- [`results/deployment-attempt-1-20260802.txt`](results/deployment-attempt-1-20260802.txt):
  clean pre-write deferral at 76% with USB offline, no upload, partition write,
  readback, shutdown, boot selection, or runtime action.
- [`results/owner-battery-override-20260802.txt`](results/owner-battery-override-20260802.txt):
  exact owner instruction, narrowed risk acceptance, unchanged guards, wrapper
  identity, syntax, ShellCheck, and one-write decision.
- [`results/deployment-20260802.txt`](results/deployment-20260802.txt): exact
  live target, predecessor, owner-authorized power state, full write/readback,
  cleanup, shutdown, and owner expectation record.

Run from the repository root:

```sh
python3 experiments/2026-08-02-a72-pre-isolation-rollback-discriminator/scripts/test_rollback_model.py
python3 experiments/2026-08-02-a72-pre-isolation-rollback-discriminator/scripts/test_build_lane.py
```

## Decision

`deployment-verified`: the exact generated series implements the
bounded and falsifiable rollback question without crossing external isolation,
compiles against its exact parent observer with no new diagnostic, and adds no
unsafe owner-lock nesting, polling loop, or semaphore wait loop. Its offline
runtime and recovery decisions are explicit, and its Android-v0 container is
reproducible. Its passive decision path is now mutation-tested. The result is
eligible for one guarded deployment after the exact evidence is pushed, but is
not yet runtime hardware evidence or a hardware-support claim. The exact image
is verified on boot2 and the device is powered down for manual selection.

## Follow-up

The owner manually selects boot2. Expect ordinary Gemian visuals and possibly
delayed console/USB service; those do not prove identity. Once service appears,
run only the exact passive collector, then return to known-good Gemian and
review the immutable ABI-v3 result before any further A72 action.
