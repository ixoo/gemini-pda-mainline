# Experiment: CPU8/CPU9 same-version pmsg witness

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-a72-pmsg-witness` |
| Status | `definition` |
| Subsystem | Gemian pstore/ramoops and retained Cortex-A72 experiment attribution |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-28 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 7 target-register evidence recovery |

## Question or hypothesis

Can the exact target-register-capsule parent leave a bounded, independently
recoverable candidate-entry, pre-scheduler, and pre-capsule result sequence in
Gemian's separate pmsg ramoops ring when console-ramoops and USB are absent?

## Provenance and environment

- Exact Gemian source commit:
  `59e00a9144d782e148332009a835b99c43382467`.
- Exact register-capsule parent patchset SHA-256:
  `71ef281aae8d0b99d0421b81bd3d61d82ab090125c4885977ba39d8280838469`.
- Exact parent `arch/arm64/kernel/psci.c` SHA-256:
  `144ef9dda2ecee098ac285a7f3189a84401eccf39bc8da67f15cfc98da1d1bcc`.
- Exact parent observer SHA-256:
  `403c0bd179204c669f8733b71779b7f95d271eb415c1b7b0212f598e9c91ff79`.
- Exact unchanged pmsg frontend and pstore header SHA-256:
  `d068bcef6cae...` and `7c3aa62a1006...`.
- Build backend: Buildbox only. No native VM kernel build is permitted.
- Recovery pairing: Gemian-derived candidate to known-good Gemian only.
  Mainline's differently aligned pmsg allocation is explicitly out of scope.

## Safety assessment

The child adds one fixed process-context pmsg helper and three constant record
sites. The helper accepts only 1--256 bytes, requires the registered `ramoops`
backend and `write_buf`, serializes with the existing pmsg mutex, and appends
only to the already-configured pmsg persistent ring. It exposes no userspace or
generic physical-address control.

The entry record is written by the existing late initcall. A pre-scheduler
record is written immediately before the inherited bounded scheduler run. One
PASS or FAULT record is written after the inherited terminal predicate is
computed and before capsule emission. The parent power, CPU_ON, CPU_OFF
prohibition, watchdog, workload, register reads, console terminals, and
recovery are unchanged.

The observation writes less than one KiB in total to the existing retained
pmsg ring. It performs no block-storage, partition, MMIO, regulator, clock,
reset, PSCI, firmware, or reboot action. No candidate may be built until exact
parent reversal, call-site order, bounds, backend restriction, console-schema
preservation, forbidden-action inventory, and negative mutations pass.

## Associated code

- [`DESIGN.md`](DESIGN.md): exact writer, record, ordering, and decision map.
- [`scripts/witness_edits.py`](scripts/witness_edits.py): deterministic
  four-file transformation of the exact register-capsule parent.
- [`scripts/test_witness_child.py`](scripts/test_witness_child.py): exact
  transformation, reversal, semantic, and negative-mutation validation.
- `scripts/generate-on-buildbox`: pending Buildbox-only source reconstruction
  and patch generation.
- `patches/series`: pending admission after deterministic generation review.

## Procedure

1. Run the self-test and exact source generator on Buildbox.
2. Review and admit the generated child only if every source and mutation gate
   passes and the diff changes exactly four pinned files.
3. Compile both exact parent and child on Buildbox; compare configuration,
   diagnostics, symbols, stack use, disassembly, marker inventory, and forbidden
   calls.
4. Define and validate a pmsg-aware changed-cycle collector before constructing
   or deploying one candidate.

## Observations

Definition work only. No kernel build, boot image, device access, retained-RAM
write, or hardware action has occurred.

## Analysis

The helper is intentionally narrower than `/dev/pmsg0`: it has no user pointer,
allocation, chunking, or arbitrary backend support. The two late records sit
near the inherited watchdog return, reducing the chance that ordinary Android
pmsg traffic wraps them out of the 64-KiB ring. The early entry remains useful
when retained, but cannot be the sole success criterion.

## Conclusion

Pending source generation and validation. This experiment currently makes no
runtime or CPU support claim.

## Follow-up

Follow only the ordered step in [`docs/ROADMAP.md`](../../docs/ROADMAP.md):
freeze and validate this observation path before Buildbox compilation or any
physical candidate.
