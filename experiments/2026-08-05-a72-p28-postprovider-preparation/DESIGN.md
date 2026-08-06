# Dormant P28 post-provider preparation design

The source-only order is:

```text
P31 -> A28 -> frozen token -> A36 -> P17 -> P27 -> R01 -> R02 -> P28
```

P28 is a CPU8-only, one-shot preparation ledger. Begin requires the exact live
transaction in `ON_ISSUED`, completed P27, zero members, provider `HELD`, the
R02 acquire proof, matching durable provider identity, and an available
post-provider budget. It consumes that budget before any future effect and
publishes `P28_STAGE_INFLIGHT`.

Completion requires the same generation and cookie, the consumed budget, and a
complete proof record. The record fixes the order and values: full-word
isolation `0x00000002 -> 0x00000000`, PWRAP deassertion, release of only the
attempt-owned software guard, 240 µs before and after an exact 1.1 V SRAM-LDO
request, selector `0x8fb`, and stable/valid calibration readback. The held
provider identity must match byte-for-byte. Completion marks P28 complete while
membership remains zero and phase remains `ON_ISSUED`.

The C patch records caller-supplied proof only. It does not invoke secure
services, touch registers, clear isolation, mutate a guard, or issue CPU_ON.
Any missing, stale, ambiguous, or failed proof leaves the inflight owner
unchanged and is not a clean success path.
