# Experiment: A72 pre-isolation rollback discriminator

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-02-a72-pre-isolation-rollback-discriminator` |
| Status | `implementation-preparation`: exact rollback contract and source-owner changes are specified; the clean-pushed Buildbox generation lane is ready for source-drift-checked patch generation; no compile, deployment, or device action is authorized |
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
- [`results/design-validation-20260802.txt`](results/design-validation-20260802.txt):
  exact inputs, selected boundary, hashes, positive path, seventeen fail-closed
  cases and the explicit no-implementation decision.
- [`results/source-owner-review-20260802.txt`](results/source-owner-review-20260802.txt):
  pinned call-chain review, rejection of the existing observer helpers as
  safety gates, exact owner-local primitive requirements and patch structure.

Run from the repository root:

```sh
python3 experiments/2026-08-02-a72-pre-isolation-rollback-discriminator/scripts/test_rollback_model.py
```

## Decision

`pending`: the exact successful forward evidence selects a bounded and
falsifiable rollback question. The generation inputs are reviewable, but their
actual vendor patches must be generated and pass source/static review before a
compile submission is permitted.

## Follow-up

Commit and push these generation inputs, generate/fetch the three logical
vendor patches on Buildbox, and review them together with the independent
static/mutation validation change. Only a separately reviewed clean revision
may enter the compile-only observer/baseline comparison. Do not deploy or run
the discriminator merely because generation, the model, or compilation passes.
