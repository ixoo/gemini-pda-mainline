# A41 static-census design

## Boundary

Patch 0152 advances the ABI 3 lifecycle only from an all-unresolved classifier
to a blocked expected-model census:

```text
expected MT6797 topology + pinned source/config inputs
        |
        v
pure source-owned descriptor evaluation
        |
        +-- 4 PRESENT --+--> two provisional effects
        +-- 30 ABSENT --+
        +-- 6 UNRESOLVED ----> mandatory CAP_INVENTORY blocker
                                      |
                                      v
                        validator returns -EAGAIN
                                      |
                                      v
               no plan identity / PLAN_FROZEN / commit / READY
```

The result describes the profile's expected Cortex-A72 model. It is not an
observation of CPU8 or CPU9.

## Exact partition

| State | Slots | Meaning |
| --- | --- | --- |
| PRESENT | 9, 66, 94, 121 | Compiled unconditional weak-local state or an all-revision A72 erratum range. |
| UNRESOLVED | 33, 36, 69, 79, 81, 82 | Requires target registers, GIC/hyp state, effective cache state, or firmware/method evidence. |
| ABSENT | remaining 30 rows | The actual source-owned matcher data is disjoint from all A72 revisions under the guarded profile policy. |

AMU and hardware DBM are already present on the early CPUs and remain
weak-local/permitted. Erratum 1742098 and speculative-AT are the only newly
required rows, producing only compat-AES clearing and speculative-AT
finalization in the provisional draft.

## Matcher ownership

- `cpufeature.c` owns AMU, hardware DBM, GIC/hyp shape checks, BBML2, and KPTI.
  BBML2 and KPTI reuse the actual private lists; KPTI additionally requires an
  unforced internal state and the selected forced-command-line policy.
- `cpu_errata.c` owns pure model/range evaluation for normal, list, multi-entry,
  and custom erratum matchers. A populated target-implementation override makes
  every MIDR-derived answer unresolved.
- `mt6797_psci.c` owns only the expected-model partition, exact arrays,
  profile identities, blocker checks, and provisional validator.

No helper invokes a capability callback on an A53 to predict an A72 result.
Unknown slots, matcher shapes, member predicates, partial A72 revision ranges,
or fixed-revision exceptions return UNRESOLVED.

## Partial validator

The profile validator requires:

- exact 40-slot compiled bitmap;
- exact 34-slot classified bitmap and 4-slot target bitmap;
- required set `{94, 121}` and an empty conflict set;
- early AMU/HW-DBM present and early KPTI/1742098/speculative-AT absent;
- only the two provisional static effects;
- exact source-parent and ordered-config-input identities;
- every standing MT6797 blocker, with only the conditional topology bit
  additionally allowed;
- no observed target identity, capability validity, target method, system
  evidence, evidence identity, HWCAP draft, or plan identity; and
- `local_caps_planned == 0`.

Even after every condition passes, it returns `-EAGAIN`. The framework then
adds CAP_INVENTORY and publishes only BLOCKED.

## Failure and mutation semantics

| Change | Result |
| --- | --- |
| target-implementation override active | MIDR-derived rows unresolved; exact validator rejects draft |
| KPTI forced or command-line policy changed | slot 85 unresolved; exact validator rejects draft |
| source/config identity or mandatory blocker changed | validator returns `-EINVAL`; framework remains blocked |
| static set, required set, or effects drift | validator returns `-EINVAL`; framework remains blocked |
| any of six rows remains unresolved | core planner returns `-EAGAIN` |
| any observed/method evidence appears in this milestone | validator returns `-EINVAL` |
| plan identity or publication added | archive validator rejects source |
| CPU boot/disable veto changes | archive validator rejects source |

## Deferred complete-plan requirements

Before a complete plan can exist, both targets need valid observed A72 MIDRs
and a bound resolved/running configuration and image. The six unresolved rows
then require separate per-target register/cache/GIC/hyp and WA1/WA2/WA3
evidence plus exact typed effect and method choices. Architecture-owned commit,
post-commit verification, HWCAP finalization, and A36/P17/P18 READY consumers
remain separate later milestones.
