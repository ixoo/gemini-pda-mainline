# Experiment: read-only A28 entry gate

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-a28-entry-gate` |
| Status | `completed` (source-only, static and bounded-model review) |
| Subsystem | Generic A28 entry snapshot for the MT6797 A72 owner model |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-05 America/New_York |
| Claim | `PARTIAL_A28_READ_ONLY_ENTRY_GATE` |

## Question

Can the dormant owner model verify the exact A28 entry snapshot for CPU8 and
CPU9 without consuming the P31 attempt, taking a transition lock, allocating a
transaction, changing P30, or authorizing CPU_ON?

## Scope and result

Patch 0161 adds a pure read-only validator for the two A72-up entry tuples. It
requires the exact attempt identity, four presence/possible bits, membership
ledger, provider state, online mask, CPUHP states, and the two expected MPIDRs.
The existing closed-owner transaction-begin function validates this snapshot
before returning its unchanged `-EAGAIN` denial. There is still no production
caller, opener, P31 attempt consumer, token mint, P30 mutation, provider/member
effect, CPU_ON operation, kernel build, KUnit execution, package, or device
result.

The validator is deliberately not a replacement for the frozen contract's
ordering: a future P31 implementation must consume the exact boot-local
attempt before A28 runs. This slice accepts that attempt as input and never
mutates it or any owner state.

## Provenance

- Patch: [0161](../../patches/v7.1.3/0161-arm64-add-read-only-A28-entry-admission-gate.patch)
- Prepared source commit: `351b77201` (`arm64: add read-only A28 entry admission gate`)
- Profile: `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate-a41-kernel-identity-p30-protocol-p24-closed-owner-hooks`
- Profile remains bound to the existing closed-owner and closed-hook fragments.
- Independent oracle and mutation runner use only Python standard-library
  values; they do not read Linux source, patches, configs, build output, or
  device state.

## Safety

The C validator performs no writes, locks, firmware calls, CPUHP operations,
CPU_ON call, or hardware access. The experiment scripts are bounded and
repository-local. No device was contacted, rebooted, written, or backed up.

## Evidence

- [DESIGN.md](DESIGN.md) records the exact tuples and rejection boundary.
- [Independent oracle](scripts/oracle.py) checks both valid tuples and state
  immutability.
- [Mutation runner](scripts/test_mutations.py) checks each targeted mismatch.
- [Exact validator](scripts/validate.py) binds the patch, profile, series
  order, source tokens, and scripts.
- [Oracle transcript](results/source-oracle-validation-20260805.txt)
- [Mutation transcript](results/mutation-validation-20260805.txt)
- [Static/offline transcript](results/offline-validation-20260805.txt)
- [Static review transcript](results/static-review-20260805.txt)

Run from this directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/oracle.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_mutations.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate.py
```

## Conclusion

`PARTIAL_A28_READ_ONLY_ENTRY_GATE` is confirmed for the exact reviewed source
model and independent bounded model. It narrows the next implementation seam
without claiming that CPU8 or CPU9 can boot. The ordered follow-up remains in
[the roadmap](../../docs/ROADMAP.md): integrate P31 attempt consumption and a
production transaction lifecycle only after their safety contracts close.
