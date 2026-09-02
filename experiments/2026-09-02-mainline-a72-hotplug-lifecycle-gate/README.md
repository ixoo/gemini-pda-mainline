# Mainline A72 physical-hotplug lifecycle gate

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-02-mainline-a72-hotplug-lifecycle-gate` |
| Status | offline gate defined; generic down-handoff generator prepared |
| Subsystem | arm64 CPU hotplug, PSCI, MT6797 A72 membership |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-09-02 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 8, A72 lifecycle correctness |

## Question or hypothesis

Can current mainline physically offline CPU9 while retaining CPU8, CPUs 0--7,
and USB serviceability, then restore CPU9 in the same boot through a separately
owned transaction without retrying an unbounded secure call or entering the
last-A72 power-down branch?

## Provenance and environment

- Repository parent: `0dc07a6bc46da6bb1b074ffee4ce5efd26908411`.
- Canonical series: 474 entries, SHA-256
  `3f55b6be379d540d947c68deb74966b2a7f0ae05819305841f1a077c33da4610`.
- Manifest SHA-256:
  `af9331a6d97a73475243dc1f79df6ca70206d3daf69405c20e9145e7c9930b43`.
- Exact prepared-source file identities are in
  [`contract.json`](contract.json).
- Runtime parent: accepted exact 4+4+2 topology/RAM and concurrent dual-A72
  execution on the named device.
- Build backend for future kernel work: Buildbox only.
- Boot path and target: none in this definition phase.

## Safety assessment

This phase is read-only with respect to the device and kernel source. It
defines no boot candidate and performs no CPU, PSCI, MMIO, watchdog,
retained-RAM, partition, or reboot operation.

The selected eventual physical action is CPU9-off with CPU8 retained. CPU8 as
the last A72, CPUs 0--7, primary boot, and every shared power-policy change are
forbidden. The secure affinity call is explicitly recorded as internally
unbounded; the physical candidate cannot proceed until the independent
watchdog, immutable pre-CPU_OFF attribution, one-query rule, reset-only fault
handling, and exact restore token are implemented and machine-checked.

## Associated code

- [`DESIGN.md`](DESIGN.md) fixes the end state, lifecycle ownership, failure
  boundary, and phase order.
- [`contract.json`](contract.json) is the machine-readable gate.
- [`scripts/validate_contract.py`](scripts/validate_contract.py) validates the
  contract and optionally the exact prepared source.
- [`scripts/test_contract.py`](scripts/test_contract.py) requires critical
  unsafe mutations to fail closed.
- `scripts/source_edits.py`, `validate_source.py`, and
  `test_source_validator.py` define and reject mutations of the first generic
  handoff slice.
- `scripts/generate_patch.py` and `generate-on-buildbox` create a normal
  format-patch from the exact managed source without changing it.
- [`results/contract-validation-20260902.txt`](results/contract-validation-20260902.txt)
  records the local contract/mutation pass and exact Buildbox prepared-source
  validation.

## Procedure

1. Pin the current repository, canonical series, manifest, prepared-source
   files, and accepted runtime parents.
2. Audit generic `cpu_down`, arm64 target disable/die/kill, MT6797 P32 guards,
   and membership attempts.
3. Select CPU9-off with CPU8 retained; reject last-A72-off.
4. Define the exact generic, target, controller, physical readback, restore,
   watchdog, and recovery handoffs.
5. Validate the contract locally and against the Buildbox-managed source; run
   the rejecting mutation suite.
6. Do not build or boot until each hardware-free implementation phase passes.

## Observations

The current source has no normal A72 down or restore owner and deliberately
hides the hotplug control. P32 guards protect failed CPU-up rollback only. The
secure-source audit establishes a per-core-only CPU9-off effect set when CPU8
remains present, but also establishes that the active affinity call contains
unbounded waits.

The exact contract passed locally, the 21 unsafe mutations all failed closed,
and the same validator passed against the six hash-pinned files in the
Buildbox-managed prepared source.

The user-reported boot immediately before this audit did not produce a boot
cycle: Gemian remained reachable under the unchanged boot ID for the complete
observation window, and the mainline netcat endpoint did not appear. It is not
classified as a kernel attempt.

## Analysis

The accepted online/topology/load evidence closes the entry-state uncertainty
that blocked earlier offlining designs. It does not close CPU-down ownership,
the active-affinity timeout, or a same-boot restore. Exposing the existing
generic path would skip all three requirements.

A CPU9-first transaction is decision-bearing because its successful effect set
does not include cluster shutdown. The independent watchdog converts a stuck
secure call into bounded reset recovery, not into a successful hotplug return.
Only the independent per-core readback and retained-CPU observation can permit
the membership commit and subsequent restore.

## Conclusion

The physical hypothesis remains untested. The exact current code is confirmed
incapable of safely running the experiment as-is. The new gate defines the
necessary path without weakening the final requirement: physical CPU9-off and
same-boot CPU9 restore remain the success condition.

## Follow-up

Generate, admit, and Buildbox-compile the four no-op-by-default generic down
handoffs. Then implement a distinct CPU9-down/restore owner before any
configuration, candidate, deployment, or boot action.
