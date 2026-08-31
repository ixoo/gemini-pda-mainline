# Design: post-capabilities P30E checkpoints

## Frozen reason values

| Value | Meaning |
| ---: | --- |
| 0 | P30E claimed; no added checkpoint completed |
| 1 | `__cpu_setup` returned while the identity mapping was active |
| 2 | virtual entry and secondary-task setup completed |
| 3 | `secondary_start_kernel()` began |
| 4 | the identity mapping was uninstalled |
| 5 | local CPU capabilities were accepted |
| 6 | CPU-operations postboot completed |
| 7 | CPU-info capture completed |
| 8 | exact late-target validation failed; detail is mandatory |
| 9 | exact late-target validation succeeded |
| 10 | topology storage completed |
| 11 | CPU-starting notification, IPI setup, and NUMA addition completed |

Reasons 1--11 keep target state CLAIMED and target sequence zero. Existing
terminal publication changes state to PUBLISHED, increments target sequence,
and replaces the reason and detail words with the terminal tuple.

## Expectation-failure detail

Reason 8 uses the existing target effects word as a mismatch bitmap. The
existing target entry-PC and entry-SP words carry the expected and observed
values for the lowest-numbered mismatch bit. The fields are interpreted this
way only while target state is CLAIMED and reason is 8.

| Bit | Compared field |
| ---: | --- |
| 0 | MPIDR |
| 1 | MIDR |
| 2 | REVIDR |
| 3 | CNTFRQ |
| 4 | CTR |
| 5 | DCZID |
| 6 | CLIDR_EL1 |
| 7--13 | ID_AA64DFR0, ISAR0, ISAR1, MMFR0, MMFR1, PFR0, PFR1 |
| 14--19 | AArch32 ID_ISAR0--5 |
| 20--23 | AArch32 ID_MMFR0--3 |
| 24--25 | AArch32 ID_PFR0--1 |
| 61 | caller CPU does not match `smp_processor_id()` |
| 62 | immutable expected-pair contract is incomplete |
| 63 | CPU-to-target slot mapping is absent |

Reason 8 with a zero bitmap, any nonzero detail on another checkpoint, an
unknown bit, or a mismatched state/sequence is rejected rather than
interpreted.

## Write contract

The existing MMU-off writer remains unchanged. The normal-text writer accepts
only known monotonic checkpoints. For a normal checkpoint all detail words must
remain zero. For reason 8 it requires a nonzero known bitmap, writes the bitmap
and first value pair before the reason word, cleans the complete slot, and
returns without changing target state or sequence.

## Decision map

- reason 5: stop in CPU-operations lookup/postboot, or the next writer refused;
- reason 6: stop in CPU-info capture, or the next writer refused;
- reason 7: stop in late-target validation before a classified return;
- reason 8: validator rejection; use bitmap and first values to select repair;
- reason 9: validator passed; stop in topology storage;
- reason 10: topology completed; stop in GIC/IPI/NUMA setup;
- reason 11: setup completed; stop before existing publication;
- PUBLISHED/sequence 1: existing late publication completed;
- CPU8 online: continue with bounded architecture/accounting validation.

Any malformed, decreasing, out-of-range, contradictory, CPU9-bearing,
CPU_OFF-bearing, retry-bearing, or repeated transcript is rejected.
