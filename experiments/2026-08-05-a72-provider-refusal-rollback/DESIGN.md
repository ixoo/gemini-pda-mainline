# Dormant R03/P29 refusal and rollback design

The source-only order is:

```text
P31 -> A28 -> frozen token -> A36 -> P17 -> P27 -> R01 -> R03 -> P29 -> P21
```

R03 is a returned refusal, not a second acquire. It is accepted only while the
same CPU8 transaction is `ON_ISSUED`, P27 is complete, the provider state is
`ACQUIRE_INFLIGHT`, the acquire budget is consumed, membership is zero, and no
R02 proof has been accepted. The rejection record must identify the exact
transaction generation and cookie, state that the provider call returned the
specific before-vote result, and set `vote_requested`, `provider_mutated`, and
`rail_mutated` to zero. A bad, stale, or duplicate record leaves the owner
unchanged. A valid record sets provider state to `NONE`, clears any provider
identity, and retains `ON_ISSUED` until P29 completes.

P29 is the only clean rollback edge after R03. It requires the same live
identity and recorded rejection, completed P27, zero members, provider `NONE`,
an unused CPU_ON budget, and a rollback record that restores the complete P27
effect mask, has no residual effects, and explicitly says P28 and CPU_ON were
not started. It copies the attestation into the transaction, marks P29 valid,
retires the generation, and publishes `REJECTED`. The provider and P27
one-shot budgets are not rearmed; only a later known-good reset/bootstrap can
reinitialize them.

This patch deliberately records caller-supplied proof; it does not execute the
provider refusal, inspect hardware, or perform inverse writes. Any uncertainty
or a refusal after a vote belongs to `FAULT_UNKNOWN`, not this clean edge.
