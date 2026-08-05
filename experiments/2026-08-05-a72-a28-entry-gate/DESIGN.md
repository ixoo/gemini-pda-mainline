# A28 entry-gate design

The validator receives a boot-local attempt value and an immutable snapshot.
It accepts only these tuples:

| Target | Attempt | Members | Provider | Online | CPUHP8 | CPUHP9 |
| --- | --- | --- | --- | --- | --- | --- |
| CPU8 | `ATTEMPT_CPU8_UP` | `0` | `NONE` | `0` | `OFFLINE` | `OFFLINE` |
| CPU9 | `ATTEMPT_CPU9_UP` | `BIT(0)` | `HELD` | `BIT(0)` | `ONLINE` | `OFFLINE` |

Both tuples also require all four `present/possible` bits and MPIDR values
`0x200` and `0x201`. Any other CPU or target returns `-EINVAL`; a malformed
snapshot or attempt returns `-EPERM`.

This is the A28 read-only boundary only. P31 attempt consumption, A38 budget
checks, transaction allocation, P17/P18 publication, provider ownership,
membership effects, P30 integration, and CPU_ON remain absent. The owner state
and the dormant P30 state must compare byte-for-byte unchanged around every
validator call.

The check is intentionally separate from generic CPU-up hooks. It does not
move per-CPU lookup ahead of the public bounds/possible checks and does not
take a transition mutex on the generic callback path.
