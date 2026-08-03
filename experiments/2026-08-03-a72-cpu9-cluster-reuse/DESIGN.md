# CPU9 cluster-reuse design

## Accepted parent

The exact parent is the late CPU8 child with two independent runtime passes.
It owns the fixed watchdog, performs the one-way cluster-singleton sequence,
holds CPU8 against HPS/public down requests, and reaches a validated late CPU8
callback while CPU9 is rejected.

## CPU9 entry contract

The first natural HPS request for CPU9 is the sole trigger. Before standard
PSCI `CPU_ON`, require all of the following without mutation:

- logical CPU is exactly 9 and its MPIDR is the existing `0x201` map;
- the CPU9 one-shot is unused;
- CPU8's PSCI request was accepted and its completion path published the
  verified cluster-online/DCM state;
- CPU8 is online and CPU9 is offline;
- the existing reset-only watchdog remains the exclusive recovery owner by
  construction from the completed parent transition.

Failure of any check emits one CPU9 `rejected-prestate` record, performs no
PSCI call or cluster write, and rejects retry.

## Forward sequence

1. Atomically consume the CPU9 software one-shot before checking the remaining
   read-only parent state, so a mismatch cannot be retried.
2. Invoke only `psci_ops.cpu_on(cpu_logical_map(9), __pa(secondary_entry))`.
3. Record the mapped PSCI result with the inherited lifecycle observer.
4. If PSCI returns success, publish acceptance and return to generic ARM64
   secondary completion. Do not touch DA921x, SPM external state, TOPRGU,
   SRAM-LDO, DCM, iDVFS, PLL, voltage, frequency, or cluster clocks in Linux.
5. At generic completion, require accepted state, CPU8 online, CPU9 online,
   and the inherited cluster-online/DCM publication.
6. Schedule static delayed work only after CPU9 completion. At about one, six,
   and ten seconds, issue one synchronous callback to CPU8 and one to CPU9.
   Each sample requires callback identities 8 and 9, both CPUs accounted
   online, and exact equal cumulative hit counts.
7. Only sample 3 emits the success terminal:

```text
gemini-a72-pair-v1 result=pass sample=3 cpu8=8 cpu9=9 online8=1 online9=1 hits8=3 hits9=3
```

## Failure and recovery

If CPU9 PSCI returns failure, record `fault-retain-psci`; secure firmware may
have begun per-core work, so do not retry or issue an inverse. If generic
secondary completion fails, record `fault-retain-secondary`. If either IPI,
CPU identity, online state, hit count, or rescheduling check fails, emit one
pair `result=fault` record. Every post-PSCI failure retains CPU8, cluster power,
and the watchdog-only recovery path.

CPU8 and CPU9 public down requests and platform CPU-disable remain rejected.
The child never calls CPU_OFF, never refreshes the watchdog, never disables a
rail or SRAM state, never restores isolation, and never adds load or a control
interface.

## Result decisions

| Result | Meaning | Next action |
| --- | --- | --- |
| exact pair sample-3 pass | CPU9 completed PSCI startup and both A72 CPUs executed bounded synchronous callbacks while accounted online | repeat once before broader pair validation |
| CPU9 rejected-prestate | repeatable CPU8 foundation did not satisfy the exact CPU9 entry contract | preserve state and audit; no unchanged retry |
| CPU9 fault-retain-psci/secondary | CPU9 per-core startup failed or became ambiguous | preserve pstore; reject implementation; no retry |
| pair fault | IPI, identity, accounting, hit count, or scheduling failed | preserve exact sample/error; no retry |
| down-veto | an unexpected policy caller requested CPU8/9 down; notifier remained dominated | classify caller; reject run |
| restart without exact terminal | recovery only, not CPU9 evidence | improve observation with a changed artifact |

No result authorizes CPU_OFF, load/stress, OPP/cpufreq, thermal, suspend,
default profile enablement, or upstream support.
