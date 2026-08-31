# Design: distinguish expected CPU model from exact target MIDR

## Observed contradiction

Production intentionally carries two related representations:

- `expected_target_midr[]` is the revision-neutral model used by capability
  classification and profile-shape validation: Cortex-A72 `0x410fd080`;
- `expected_pair.midr` is the exact prior-cycle target value used by secondary
  late-target validation: Cortex-A72 r0p1 `0x410fd081`.

The generic completeness helper currently requires these values to be exactly
equal. The stage ledger proves that predicate returns false before effect
planning, even though both representations describe the same CPU model.

## Repair boundary

Change only the generic completeness comparison from:

```c
expected->midr != plan->evidence.expected_target_midr[target]
```

to:

```c
(expected->midr & MIDR_CPU_MODEL_MASK) !=
        plan->evidence.expected_target_midr[target]
```

The target field remains required to be a normalized model value; masking both
sides would incorrectly accept a revision-bearing target field. The exact
pair is not modified.

The later validator remains:

```c
late_expected_target_compare(pair->midr, info->reg_midr, ...)
```

so the observed CPU must still match exact r0p1. This change does not make a
different A72 revision acceptable to the physical target gate; it only makes
the generic representation-consistency check compare the fields at their
shared model granularity.

## Validation contract

- Pin exact post-`0461` source state and `late_cpu_profile.c` identity.
- Generate one normal one-file format-patch with a one-line source delta.
- Accept exact A72 r0p1 and another A72 revision against model base.
- Reject A53 r0p1 and reject a revision-bearing target model field.
- Preserve the exact target-register comparison and its mismatch bit.
- Preserve all CPU, power, storage, retry, and reboot call inventories.
- Replay deterministically, reject source mutations, audit every manifest
  profile, and build only on Buildbox.

One physical CPU8-only attempt is eligible only after offline validation and a
fresh exact READY pretrigger. CPU9 remains vetoed.
