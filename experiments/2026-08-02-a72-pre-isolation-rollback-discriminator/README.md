# Experiment: A72 pre-isolation rollback discriminator

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-02-a72-pre-isolation-rollback-discriminator` |
| Status | `design/source-review`: exact rollback contract and source-owner changes are specified; no implementation, build, deployment, or device action is authorized |
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
falsifiable rollback question, but only the offline design/model exists.

## Follow-up

After the successful runtime evidence and this design are signed and pushed,
prepare the four logical experiment-only source changes on Buildbox and add
static mutations before any compile submission. Do not deploy or run the
discriminator merely because the model and source-location review pass.
