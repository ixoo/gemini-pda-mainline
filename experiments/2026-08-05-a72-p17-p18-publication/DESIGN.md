# Dormant P17/P18 publication design

The source-only order is:

```text
P31 -> A28 -> frozen token -> A36 -> P17/P18 (ON_ISSUED)
```

P17/P18 is a pre-effect publication. It is valid only for a live, exact
generation/cookie transaction with a valid A36 record and P30 token. CPU8/P17
requires `provider_state=NONE` and a zero provider identity because provider
acquisition begins only after publication. CPU9/P18 requires `provider_state=HELD`
and the exact nonzero durable M01 identity copied at token mint; it may not
reacquire or replace that identity.

The edge is serialized by `a72_transition_lock` and the short state lock. It
sets `p17_p18_published` and changes the C owner phase from `FROZEN` to
`ON_ISSUED`. A second call, an identity mismatch, a missing A36 record, or a
provider mismatch has no effect and cannot publish.

This slice deliberately stops before P27 preparation, provider calls, P28
post-provider preparation, P24 CPU_ON, secondary completion, P14/P15, and
membership commit. The KUnit-only CPU9 provider seed is evidence scaffolding,
not a production bootstrap or provider authority.
