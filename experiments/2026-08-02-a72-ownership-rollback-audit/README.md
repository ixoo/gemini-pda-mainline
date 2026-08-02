# Experiment: MT6797 A72 ownership and rollback audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-02-a72-ownership-rollback-audit` |
| Status | `post-latch audit complete`: 16 boundaries have clean first-pair evidence; five failure rollbacks, CPU9, and suspend/resume remain open |
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
- Superseded overwritten observer result:
  [`../2026-08-02-gemian-a72-bounded-observer-boot/results/runtime-attempt-1-summary-20260802.txt`](../2026-08-02-gemian-a72-bounded-observer-boot/results/runtime-attempt-1-summary-20260802.txt).
- Exact clean first-pair result:
  [`../2026-08-02-gemian-a72-first-cycle-latch/results/runtime-summary-20260802.txt`](../2026-08-02-gemian-a72-first-cycle-latch/results/runtime-summary-20260802.txt),
  with sanitized snapshot SHA-256
  `6db6ea41ba4689541cb504a0486c0a1b7249834ebdb8613f0e73b0bf56e808f5`.

No kernel was built for this static audit. In particular, no native VM kernel
build was run.

## Safety assessment

The original audit was offline and read-only. This revision consumes only the
sanitized immutable first-pair result; it performs no new device access,
partition read, register access, SMC, CPU request, load pulse, build,
deployment, or reboot. Private binaries remain in their existing Git-ignored
locations. The matrix contains only sanitized source/binary/firmware and
runtime conclusions.

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

The clean latch directly brackets the first natural CPU8-up and CPU8-down
transactions in 46 immutable records. Sixteen matrix rows now carry clean
first-pair evidence: DA9214 page `0x80` is restored on every snapshot; BUCKB
enable changes `0 -> 1` and `1 -> 0`; SPM reset/isolation and TOPRGU masked
readbacks match; secure SRAM-LDO/iDVFS snapshots are stable; protected B/CCI
clock snapshots succeed; raw/mapped PSCI, secondary completion, affinity, MP2
DCM, and the complete natural last-A72-off path are retained. The exact pair
shows VSEL `0x46` before enable, `0x32` after secondary online, `0x3a` before
the last-off sequence, and `0x46` after disable.

This retains nine closed forward-only rows, upgrades secondary completion to
clean first-pair evidence, and leaves missing live pre-state/readback at two
rows. It does not convert the observed natural inverse into a bounded failure
rollback. Five rollback rows remain open, CPU9 has no retained record, and
system suspend/resume ownership remains unresolved. Clean initial attribution
is now established without a pulse.

## Analysis

The forward-owner half of the hypothesis is now supported by transaction-local
runtime evidence, but the reversible failure contract remains rejected. The
first mainline CPU8 path must still be one-way and fail-closed beyond the
external-isolation boundary unless a bounded inverse is proven. A passive
resource-only provider can be designed in parallel because registration need
not write hardware or connect consumers, but any writable provider or CPU
request remains blocked.

The next discriminator is not another successful natural cycle: the latch has
closed that question. It must independently observe a bounded failure unwind
for one of the five open rollback rows without introducing a mainline consumer
or requesting CPU9. CPU9 and suspend/resume remain separate experiments;
neither is inferred from CPU8.

## Conclusion

`rejected` for the hypothesis that current evidence defines a complete,
reversible CPU8 contract. Clean first-pair evidence now covers 16 rows and
supports all nine closed forward decisions, but Gate 4 remains open on five
failure-rollback rows, one CPU9-only observation row, and unresolved
suspend/resume ownership.

## Follow-up

Design a failure/rollback discriminator for the five open rows. It must define
the exact injected or naturally observed failure, independent pre/post state,
bounded unwind, stop conditions, and recovery path before any implementation
or device boot. Build any later revision only on Buildbox from an exact clean
pushed commit; do not use the native VM kernel-build backend. Do not repeat the
successful latch image, run the pulse, select draft patch 0093, or request
CPU9. Recover suspend/resume ownership separately.
