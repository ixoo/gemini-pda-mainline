# Experiment: A72 P32 rollback hook audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-06-a72-p32-hook-audit` |
| Status | `in progress` (source-only implementation build validated; runtime remains blocked) |
| Subsystem | arm64 CPUHP rollback, target `cpu_disable`/`cpu_die`, controller `cpu_kill` |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-06 America/New_York |
| Claim | `P32_SOURCE_GUARDS_AND_MUTATIONS_BUILD_VALIDATED` |

## Question

Where must a future P32 implementation publish and guard the exact late-A72
rollback generation so generic CPUHP cleanup cannot issue CPU_OFF, affinity, or
an optimistic success result?

## Provenance and safety

This is a read-only audit of the pinned Linux 7.1.3 source after the current
canonical patch series. The source archive SHA-256 is
`be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`; the
current 174-patch series SHA-256 is
`f4ac9f743e1e12da58bfe1f5e0e8714e443714c117e1164b34e13f0bd0ae65dd`.
The source-only profile was built and fetched through Buildbox; no candidate
was assembled for boot, and no device, CPU, PSCI, or partition operation
occurred.

The patched-source file identities used for the audit are recorded in
[`results/p32-hook-source-audit-20260806.txt`](results/p32-hook-source-audit-20260806.txt).
The initial default-off implementation and its Buildbox provenance are recorded in
[`results/p32-implementation-build-20260806.txt`](results/p32-implementation-build-20260806.txt);
the tightened identity/consumption build is recorded in
[`results/p32-identity-build-20260806.txt`](results/p32-identity-build-20260806.txt).
The independent mutation oracle result is recorded in
[`results/p32-mutation-validation-20260806.txt`](results/p32-mutation-validation-20260806.txt).
The normative branch contract remains the
[A72 CPU-up source-closure design](../2026-08-05-a72-cpu-up-source-closure/DESIGN.md).

## Observations

The audit finds four distinct boundaries:

1. `cpuhp_kick_ap()` performs a nested AP rollback at its own
   `cpuhp_reset_state()` call. An outer hook cannot pretend that this prefix
   did not execute.
2. `cpuhp_up_callbacks()` is the first controller-owned point after the
   callback range returns an error and before its `cpuhp_reset_state()` and
   outer reverse callback range. This is the P32A publication seam.
3. arm64 `op_cpu_disable()` invokes the target `.cpu_disable` before topology,
   NUMA, online-mask, IPI, or IRQ teardown in `__cpu_disable()`. This is the
   P32D guard seam.
4. arm64 `cpu_die()` reports `DEAD` and then calls the target `.cpu_die`; the
   controller cleanup reaches `op_cpu_kill()`, and the current PSCI
   implementation performs active `AFFINITY_INFO` polling. These are the P32F
   target-park and controller-no-affinity seams.

The selected MT6797 PSCI operation still returns `-EAGAIN` for CPU_ON and
retains the existing CPU-disable veto. Therefore this audit changes no runtime
reachability.

## Conclusion

`confirmed` as an exact source hook map. Patches `0182`–`0185` now supply a
default-off exact-generation side channel, target `.cpu_disable`/`.cpu_die`
guards, a controller `.cpu_kill` path that avoids affinity, one-shot
consumption, and exact operation-to-target identity binding. The 174-patch
profile builds successfully through Buildbox and the independent 13-probe
mutation oracle passes, with all existing CPU_ON/CPU_OFF and provider vetoes
intact. A25 review and the A41/provider/A26/A14 admission gates remain open;
CPU_ON, CPU_OFF, and device gates remain closed.

## Follow-up

Review the P32R source against the oracle result, then re-audit A25, A41,
provider, P30, and the remaining A26/A14 gates. Do not relax the boot or disable
vetoes and do not create a device candidate until those gates are independently
closed.
