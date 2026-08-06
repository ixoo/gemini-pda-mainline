# Dormant P27 preparation design

The source-only order is:

```text
P31 -> A28 -> frozen token -> A36 -> P17/P18 -> P27 begin -> P27 complete
```

P27 is valid only for a live CPU8 transaction already published by P17. The
owner must still show `members=0`, provider `NONE`, and the exact transaction
generation/cookie. The begin edge consumes the single preparation budget under
the transition and state locks, then exposes an `INFLIGHT` stage. The source
ledger does not perform the effects; the later completion record is accepted
only when it names the same generation and the exact three-part prefix:

1. MP2 reset release with the required SPM 0x218 ordering;
2. the B-PLL ordering read; and
3. the owner-locked PWRAP assertion.

The completion edge changes only the C ledger to `COMPLETE`; it does not call
the regulator, touch MMIO, clear isolation, request SRAM-LDO, alter the member
mask, call CPUHP, hand off P30, or issue CPU_ON. A malformed record, duplicate
begin, wrong operation, stale identity, or nonzero members/provider state is
rejected without relaxing the owner.

The next seam is P28 after R02 has produced a real durable provider identity.
R01/R02, P28 rollback, P24 CPU_ON, P14/P15, and P30 remain contract-only.
