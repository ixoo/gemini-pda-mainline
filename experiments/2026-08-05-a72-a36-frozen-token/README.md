# Experiment: dormant A36 frozen-token mint

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-a36-frozen-token` |
| Status | `completed` (source-only, static and bounded-model review) |
| Subsystem | MT6797 A72 P31/A28/A36 transaction-owner seam |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-05 America/New_York |
| Claim | `PARTIAL_A36_FROZEN_TOKEN_MINT` |

## Question

Can the owner retain the transition mutex across P31 and A28, then mint a
frozen CPU8/CPU9 transaction bound to the immutable READY profile identity and
exact one-shot budgets, without arming P30 or issuing CPU_ON?

## Result

Patch 0163 extends the dormant `begin_up()` seam with a READY-token validator
and frozen transaction mint. The validator requires the exact profile ID,
READY ABI, non-empty plan/source/config/evidence identities, target mask,
logical targets, and matching expected/observed MPIDRs (`0x200`/`0x201`). The
transition mutex is acquired before P31 and released only after A28 and mint;
no second transaction can interleave that sequence.

The minted transaction carries an immutable P30 token identity, generation,
cookie, plan identity, copied entry snapshot, and branch-specific budgets:
CPU8 gets preparation/provider-acquire/CPU_ON budgets; CPU9 gets only CPU_ON.
The owner enters `FROZEN`, but A36 hardware prestate, P17/P18 publication, P30
arming, provider/member effects, CPUHP effects, CPU_ON, and production callers
remain absent.

## Provenance

- Patch: [0163](../../patches/v7.1.3/0163-arm64-mint-frozen-A72-transaction-tokens.patch)
- Prepared source commit: `70b98c307` (`arm64: mint frozen A72 transaction tokens`)
- Parent: [P31 attempt ledger](../2026-08-05-a72-p31-attempt-consumption/README.md)
- Profile: existing source-only closed-hooks profile; no new build profile.

## Safety and nonclaims

The code only validates immutable input and updates the dormant owner ledger
under its existing locks. It calls no profile mutation, CPU hotplug, firmware,
provider, hardware, P30 startup, or CPU_ON operation. The AVAILABLE state is
reachable only through the existing KUnit-only seed. No kernel build, KUnit
execution, package, candidate, deployment, or device result was produced.

## Evidence

- [DESIGN.md](DESIGN.md) records token identity and budget invariants.
- [Independent oracle](scripts/oracle.py)
- [Mutation runner](scripts/test_mutations.py)
- [Exact validator](scripts/validate.py)
- [Oracle transcript](results/source-oracle-validation-20260805.txt)
- [Mutation transcript](results/mutation-validation-20260805.txt)
- [Offline/static transcript](results/offline-validation-20260805.txt)

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-a36-frozen-token/scripts/oracle.py
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-a36-frozen-token/scripts/test_mutations.py
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-a36-frozen-token/scripts/validate.py
```

## Conclusion

`PARTIAL_A36_FROZEN_TOKEN_MINT` is confirmed for the reviewed source and
bounded model. The next gate is operation-specific A36 prestate validation,
then P17/P18 publication and P30/P32 closure. This milestone does not make a
CPU-up request safe or successful.
