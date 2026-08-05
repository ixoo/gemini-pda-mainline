# Experiment: dormant P31 attempt consumption

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-p31-attempt-consumption` |
| Status | `completed` (source-only, static and bounded-model review) |
| Subsystem | MT6797 A72 transaction-owner attempt ledger |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-05 America/New_York |
| Claim | `PARTIAL_P31_ATTEMPT_LEDGER` |

## Question

Can the dormant owner consume one exact boot-local A38 attempt under the
transition owner, after the observer window opens and before A28, while making
the consumption one-shot and preserving it across A28 rejection?

## Result

Patch 0162 adds a private P31 ledger step to the existing dormant
`begin_up()` path. It requires the exact CPU8/CPU9 operation, `CPUHP_ONLINE`,
attempt bit, and an explicit observer-window-open marker. In an AVAILABLE
owner state it consumes exactly one attempt while holding the transition mutex
and state spinlock, then invokes the read-only A28 validator. A malformed A28
snapshot returns `-EPERM` without restoring the attempt. A repeated attempt
returns `-EALREADY`. The CLOSED production state still returns `-EAGAIN`, and
the test-seeded AVAILABLE state still returns `-EOPNOTSUPP` after consumption:
no generation, token, P30 handoff, provider/member effect, CPUHP effect, or
CPU_ON operation exists.

P31 is deliberately dormant. The test-only seed is not an opener and is not
compiled into a production path. A34 remains the future reset authority for
consumed attempts.

## Provenance

- Patch: [0162](../../patches/v7.1.3/0162-arm64-add-dormant-P31-attempt-consumption.patch)
- Prepared source commit: `950bdf936` (`arm64: add dormant P31 attempt consumption`)
- Parent milestone: [A28 entry gate](../2026-08-05-a72-a28-entry-gate/README.md)
- Profile remains the source-only closed-hooks profile; no new build profile
  or configuration authority was added.

## Safety and nonclaims

The implementation uses only owner locks and scalar ledger updates. It does
not call CPU hotplug, firmware, PSCI/SMC, CPU_ON, provider code, hardware, or
the device. No kernel build, KUnit execution, package, boot candidate, or
runtime result was produced. The test-only AVAILABLE seed is isolated behind
`CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST` and is not an opener.

## Evidence

- [DESIGN.md](DESIGN.md) records the ordering and state transitions.
- [Independent oracle](scripts/oracle.py)
- [Mutation runner](scripts/test_mutations.py)
- [Exact validator](scripts/validate.py)
- [Oracle transcript](results/source-oracle-validation-20260805.txt)
- [Mutation transcript](results/mutation-validation-20260805.txt)
- [Offline/static transcript](results/offline-validation-20260805.txt)

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-p31-attempt-consumption/scripts/oracle.py
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-p31-attempt-consumption/scripts/test_mutations.py
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-p31-attempt-consumption/scripts/validate.py
```

## Conclusion

`PARTIAL_P31_ATTEMPT_LEDGER` is confirmed for the exact reviewed source model
and bounded model. The next implementation gate remains A36/token minting
after A28, followed by P17/P18 and P30/P32 closure. The roadmap remains the
only owner of that ordered work.
