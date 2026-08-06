# Experiment: A39 early-secondary status inventory

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-06-a72-a39-early-secondary-inventory` |
| Status | `completed` (inventory complete; terminal guard closure remains open) |
| Subsystem | arm64 early-secondary capability failures and controller status handling |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date(s) | 2026-08-06 America/New_York |
| Investigator(s) | Gemini Mainline Experiment |
| Tracking issue | A39 admission gate |

## Question or hypothesis

Does the fully patched arm64 source provide an attributable, fail-closed path
for every early-secondary capability failure and every `__cpu_up()` status
branch before P32 terminal handling is considered complete?

## Provenance and environment

- Kernel source: Linux 7.1.3, Buildbox prepared tree for pushed commit
  `f8b407420677dfdf2e641eebe02697ee6f65bb13`.
- Patchset: 180 entries through `0191`; patchset SHA-256
  `14dad7835e8ca830e4ea74b3660fc7620cf856e906412471161b5501a7f52c35`.
- Dedicated package: `linux-7.1.3-gemini-a72-p32-rollback-14dad783-a52199d2`.
- Build backend: Buildbox cross-build; no native VM build.
- Source inventory: `results/early-secondary-inventory.tsv`.

## Safety assessment

This is read-only source inspection. It performs no device access, CPU_ON,
CPU_OFF, affinity query, provider operation, partition operation, or boot.
The package is compile/provenance evidence only.

## Associated code

- `scripts/inventory.py` validates the complete, sanitized inventory.
- `results/early-secondary-inventory.tsv` records each status or early-failure
  branch and the currently attributable guard.
- Source references are to the exact Buildbox-prepared tree named above.

## Procedure

1. Inspect `__cpu_up()` status handling, `secondary_start_kernel()`,
   `cpu_die_early()`, and all `cpufeature.c` callers in the exact prepared
   source tree.
2. Record each branch and the current P32/controller guard in the TSV.
3. Run `python3 scripts/inventory.py` and preserve its result.

## Observations

The inventory covers the unknown, `CPU_KILL_ME`, `CPU_STUCK_IN_KERNEL`, and
`CPU_PANIC_KERNEL` controller branches; the secondary entry and P30E failure
status; `cpu_die_early()` present-mask/RCU/status effects; eight capability
failure callsites; and the P32 publish/die/kill guards.

`cpu_die_early()` still clears `cpu_present`, reports RCU death, publishes
`CPU_KILL_ME`, and parks before the P32 publication side channel is armed. The
controller `CPU_PANIC_KERNEL` branch still panics unconditionally. The current
P32 guards require an active, exact `p32_valid` identity and therefore do not
close these early branches.

## Analysis

The inventory is complete for the pinned source, but it does not prove a
terminal attribution design. A39 therefore remains blocked: the next source
change must bind each early branch to an exact up-token and fail closed without
CPU_OFF or affinity, or prove the branch impossible for the target. The 0191
phase fix makes ordinary P32 publication reachable from `ON_ISSUED`; it does
not cover this earlier path.

## Conclusion

`confirmed` — the A39 source inventory is complete and the implementation gate
remains open. No hardware-support or boot claim follows.

## Follow-up

Use this inventory to design and separately review the early-status ownership
hook before revisiting A26/A14 or any device candidate. The admission re-audit
must continue to report A39 blocked until those branch-specific guards are
implemented and independently validated.
