# Gate-7 remaining-boundary audit design

## Decision rule

Select the earliest boundary that is a hard predecessor of a CPU8 request,
can be implemented and tested without target execution or hardware mutation,
and does not require pretending that fixture or historical evidence is live
arm64 target evidence.

## Dependency result

The canonical tree through patch `0301` contains four separately closed
domains, but they are not peers in reachability order:

```text
A34 eligibility evaluator
  -> reviewed reset/bootstrap provenance owner
     -> production A34 lifecycle opener
        -> future transaction caller
           -> P27/provider/P28 effect ownership
           -> P30/P32 CPU_ON lifecycle
           -> evidence-only target observation
              -> A41 immutable commit and READY
                 -> production CPU8 admission
```

The arrows describe required authority, not permission to implement the whole
chain at once. In particular, A41 cannot be completed by deleting its commit
blocker. The non-fixture profile has no target observations, its preparation
and validation deliberately return `-EAGAIN`, and it cannot form a plan
identity. The existing fixture is a pure evaluator input, not runtime proof.

P28 is also not the next boundary. Its C object records an attested result but
does not execute or invert P27/P28 hardware effects. Connecting the positive
provider to that ledger would cross isolation/SRAM effects without complete
ownership and rollback.

The P24/P30 request path is downstream of all of those prerequisites. The
current admission hooks correctly return `-EOPNOTSUPP` even if a harness seeds
the owner as AVAILABLE, and the MT6797 CPU method still rejects before
`CPU_ON`.

## Selected implementation slice

Implement only a pure A34 eligibility evaluator behind a new default-off
profile. It has no production boot-time caller and performs no state
transition. A complete immutable input is eligible only when it proves:

- a known-good platform or external reset is complete through an explicit
  provenance field that cannot default to true or be inferred from ordinary
  Linux boot;
- CPU8 and CPU9 are present and possible, both offline, and their CPUHP states
  agree with the offline mask;
- their non-aliased logical MPIDRs are exactly `0x200` and `0x201`;
- membership is empty, the provider is `NONE`, no durable provider identity or
  controller exists, and no active/retired transaction or fault is present;
- P30 is FREE, unquarantined, and has no live or retired generation;
- an owner-safe source proves the private replay ledger is zero; and
- the proposed first generation and cookie seeds are nonzero and
  nonterminal.

Any mismatch returns a fail-closed rejection. Success returns eligibility only:
it does not initialize attempts, mutate the owner, or authorize a caller. KUnit
must exercise every field. A later reviewed production reset/bootstrap owner
must supply the two provenance inputs, serialize the full observation, recheck
it at publication, and own the atomic transition from CLOSED/UNINITIALIZED to
AVAILABLE/IDLE. That owner is explicitly outside this slice.

## Explicit non-scope

This slice adds no production init caller, lifecycle open, transaction caller,
A41 token, provider call, P27/P28 effect, P30 arm, PSCI call, `CPU_ON`,
`CPU_OFF`, boot-veto change, device candidate, or device action. The owner
remains CLOSED and the existing admission and CPU boot vetoes remain in force.
