# Experiment: MT6797 A72 ownership and rollback audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-02-a72-ownership-rollback-audit` |
| Status | `static audit complete; synchronized Gemian observer capture pending` |
| Subsystem | Cortex-A72 external rail, SPM, TOPRGU, secure firmware, clocks, CCI, and rollback |
| Device variant | Named Gemini PDA development unit |
| Date(s) | 2026-08-02 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 4 |

## Question or hypothesis

Do the exact active-Gemian binary audit, public source equivalence, secure
firmware analysis, natural CPU8 trigger calibration, and completed mainline
DA921x identification lifecycle assign every forward writer and define a safe
inverse for a first CPU8 request?

The audit deliberately separates a known forward owner from a proven pre-state,
readback, rollback, CPU9 delta, and suspend/resume owner. A reconstructed
forward sequence is not treated as a reversible implementation contract.

## Provenance and environment

- Mainline identification lifecycle: exact Stage 27 result in
  [`../2026-08-01-da921x-post-event-lifecycle/results/runtime.txt`](../2026-08-01-da921x-post-event-lifecycle/results/runtime.txt).
- Active Gemian boot partition SHA-256:
  `1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513`.
- Active Gemian kernel-field SHA-256:
  `b53d191dc41d3f7364b0fa62b4bc920b1d013a1942b2e6b06727263fc56fcf4d`.
- Observer-source equivalent: public Gemian commit
  `59e00a9144d782e148332009a835b99c43382467`; it is not claimed as the exact
  active source revision.
- Secure-firmware slots: private identical 5 MiB captures, SHA-256
  `2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3`.
  No firmware bytes or disassembly are included here.
- Forward contract and fail-closed boundaries:
  [`../2026-07-22-a72-firmware-power-contract/`](../2026-07-22-a72-firmware-power-contract/).
- Natural CPU8 trigger calibration:
  [`../2026-07-23-gemian-a72-load-assisted-observation/`](../2026-07-23-gemian-a72-load-assisted-observation/).

No kernel was built for this static audit. In particular, no native VM kernel
build was run.

## Safety assessment

This audit is offline and read-only. It performs no device access, partition
read, register access, SMC, CPU request, load pulse, build, deployment, or
reboot. Private binaries remain in their existing Git-ignored locations. The
matrix contains only sanitized source/binary/firmware conclusions and hashes.

The audit does not authorize DA921x register-data writes or CPU8/CPU9. Rows
whose pre-state, readback, rollback, or resume owner is missing remain explicit
blockers. Draft patch 0093 remains unselected.

## Associated code

- [`results/ownership-matrix.tsv`](results/ownership-matrix.tsv): one row per
  forward, observation, rollback, CPU9, or resume boundary.
- [`scripts/validate-matrix.py`](scripts/validate-matrix.py): validates the
  exact 19-row inventory, controlled vocabulary, unique ownership, and
  fail-closed classification of every unresolved boundary.
- [`results/audit-validation.txt`](results/audit-validation.txt): exact audit
  counts and validation result.

Run from the repository root:

```sh
python3 experiments/2026-08-02-a72-ownership-rollback-audit/scripts/validate-matrix.py
```

## Procedure

1. Enumerate every boundary in the exact active forward CPU8 path and the
   required off, CPU9, and resume paths.
2. Assign the physical writer and requester separately where secure firmware
   performs a Linux-requested transition.
3. Classify the strongest evidence for that ownership assignment.
4. Mark transaction-local pre-state, independent readback, bounded rollback,
   CPU9 delta, and suspend/resume coverage independently.
5. Fail the Gate 4 completion decision whenever an owner is unresolved or a
   required pre-state/readback/rollback/resume observation is missing.
6. Derive the smallest next observer capture from the unresolved rows; do not
   design a writable provider from static ordering alone.

## Observations

All forward hardware writers can be assigned at bit or service granularity:
Linux owns external preparation and post-success DCM; secure firmware owns the
SRAM-LDO register writes requested by Linux and the PSCI-internal PLL, MTCMOS,
reset, bus-protection, and CCI work; later vendor policy owns dynamic iDVFS and
B/CCI rate changes. CPU9 shares secure per-core logic but must not replay the
cluster-singleton preparation.

The matrix still contains one unresolved ownership boundary—system
suspend/resume—and multiple missing transaction-local observations. In
particular, existing captures do not bracket BUCKB enable/VSEL/page state, SPM
reset/isolation, TOPRGU PWRAP reset, SRAM-LDO state, protected B/CCI clocks, or
MP2 DCM around the natural CPU8 online/offline cycle. The vendor last-A72-off
path is not a safe inverse.

## Analysis

The forward-owner half of the hypothesis is supported, but the reversible
contract half is rejected. The first mainline CPU8 path must be one-way and
fail-closed beyond the external-isolation boundary unless new evidence proves
a bounded inverse. A passive resource-only provider can be designed in
parallel because registration need not write hardware or connect consumers,
but any writable provider or CPU request remains blocked.

The next discriminating experiment is not another sequential userspace
sampler. It is the already scoped owner-local, read-only Gemian observer built
from the verified `59e00a` equivalent and the exact active boot contract. Its
hooks must capture one calibrated two-worker natural CPU8 online/offline cycle
at the owning DA9214, SPM/TOPRGU, secure-read, protected-clock, PSCI,
secondary-completion, DCM, and last-A72-off boundaries.

## Conclusion

`rejected` for the hypothesis that current evidence defines a complete,
reversible CPU8 contract. Forward writers are substantially assigned, but
Gate 4 remains open on synchronized pre-state, readback, rollback,
suspend/resume ownership, and CPU9-specific evidence.

## Follow-up

Freeze and validate the owner-local Gemian observer source and exact active
boot-image derivation. Build it only on an explicitly approved non-native
backend; the project policy forbids a native VM kernel build unless the owner
specifically requests one. Use the calibrated natural load pulse once, then
update this audit from the synchronized transaction record. Do not select
draft patch 0093 or request CPU8/CPU9.
