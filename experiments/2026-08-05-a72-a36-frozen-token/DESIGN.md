# A36 frozen-token design

The lock and state order is:

```text
transition mutex
  -> P31 exact attempt consumption
  -> A28 exact entry validation
  -> READY identity validation
  -> frozen token mint
  -> release transition mutex
```

The READY identity must carry the exact profile name
`mt6797-a53-a72-a41-v7`, the profile ABI, non-empty plan/source/config/evidence
identity words, both target mask bits, logical CPUs 8/9, and matching expected
and observed MPIDRs `0x200`/`0x201`. A mismatch returns `-EPERM` after P31,
leaving the attempt consumed and the owner `IDLE`.

The token generation and cookie are monotonic owner counters. The transaction
identity and P30 token copy the operation, target, MPIDR, generation, cookie,
and plan identity. CPU8 receives preparation, provider-acquire, and CPU_ON
budgets; CPU9 receives only CPU_ON. The token is frozen, not armed: A36
register prestate, P17/P18, P30 startup preparation, provider work, CPUHP
effects, and CPU_ON remain later gates.

The KUnit-only AVAILABLE seed supplies counters and a zero provider/membership
tuple. It is a harness fixture, not an A34 opener or a production authority.
