# Experiment: mainline A72 production-input ownership audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-24-mainline-a72-production-input-ownership-audit` |
| Status | completed offline audit; production publication rejected |
| Subsystem | MT6797 A72 A34 replay and physical direct-state inputs |
| Device variant | Planet Gemini PDA named development unit; canonical-source audit |
| Date(s) | 2026-08-24 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, A34 production inputs |

## Question or hypothesis

Does canonical source through patch `0347` contain production-owned inputs
that can safely call the atomic A72 bootstrap publisher, or must replay
applicability and physical direct state remain closed as distinct authorities?

The positive hypothesis requires two independently valid inputs. One producer
must prove that the exact primary-BL31 replay clear applies to this boot. A
separate, lifetime-safe physical source must produce the complete exact
DA921x, platform, protected-clock, and BigiDVFS tuple under the existing A72
transition owner. Neither authority may be inferred from the other.

## Provenance and environment

- Repository input: signed and pushed commit
  `84325e329b4c2605071c9704a2e49572121077fd`.
- Canonical series tail: patch `0347`, SHA-256
  `53a59d1976d95eaba1095fbdb8811f20d8c9e2a1e875368fa716f26e907b1a83`.
- Managed Buildbox source state:
  `ac57421ae45c6e55ba34f2cac4131647e89762ad5988baf1b47364c2c75e77cb`.
- Managed-source integrity:
  `d87fe0d866aec4825c2e2c2bf5f1df628299692e5bad63e581b07c64d0f3c22d`.
- The exact managed tree was inspected read-only on Buildbox. No source tree
  was copied to or from it.

Exact file identities and bounded call-graph counts are in
[`results/source-ownership-audit-20260824.txt`](results/source-ownership-audit-20260824.txt).
The input decisions are decomposed in
[`results/decision-matrix.tsv`](results/decision-matrix.tsv).

## Safety assessment

This audit performed no build, source-tree edit, device contact, MMIO, SMC,
I2C transfer, clock operation, CPU request, boot-image construction, partition
access, `boot2` write, reboot, or shutdown. It does not authorize a production
publisher caller or a physical device attempt.

Both CPU-up vetoes and the CPU-disable veto remain unchanged. The membership
owner remains `CLOSED / UNINITIALIZED`, and no lifecycle state was published.

## Associated code

- [`DESIGN.md`](DESIGN.md) freezes producer lifetime, lock order, failure, and
  selected-next boundaries.
- [`contract.json`](contract.json) pins exact source and prior-evidence inputs.
- [`scripts/validate.py`](scripts/validate.py) validates this record offline.
- [`results/source-ownership-audit-20260824.txt`](results/source-ownership-audit-20260824.txt)
  is the sanitized source audit.
- [`results/decision-matrix.tsv`](results/decision-matrix.tsv) records each
  independent authority and stop condition.

No privilege or hardware access is needed to validate this audit:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 \
  experiments/2026-08-24-mainline-a72-production-input-ownership-audit/scripts/validate.py
```

## Procedure

1. Pin the final managed source through canonical patch `0347`.
2. Enumerate all definitions and call sites of the direct-source registry and
   atomic bootstrap publisher.
3. Trace the typed replay record from its publisher argument to every source
   that can construct a positive value.
4. Trace each physical reader's initialization, invalidation, local lock,
   generation, zero-on-failure, and hardware-effect contract.
5. Compare A34's exact expected record byte-for-byte with the already
   qualified named-device protected-clock record.
6. Freeze the complete outer and nested lock order for a future physical
   adapter without adding that adapter.
7. Select only the next observation that can change a blocked input decision.

## Observations

### Replay authority

The public atomic publisher takes a caller-supplied
`struct mt6797_a72_a34_replay`. Canonical production source contains no caller
of that publisher and no producer that can populate the positive
`APPLICABLE_PRIMARY_BL31_CLEAR` value. Positive record construction occurs
only in static A34 expectations and injected tests.

The prior secure-replay audit proves that exact primary BL31 entry clears the
range containing the private replay byte. It deliberately leaves that result
conditional on a separately proven current boot reaching the applicable
primary entry. The later platform-reset classifier found no positive Linux-
transported row. Raw TOPRGU state, its correlated ram-console projection, LK
boot reason, preserved ATF logs, an ordinary reboot, a Linux-owned zero, or a
caller-supplied constant remain rejected.

### Physical direct-state authority

The direct-source registry has correct single-owner mechanics: first register
wins, exact-pair unregister clears it, and its mutex remains held through the
snapshot callback. There is no production registration. Its three non-
definition call sites are confined to two KUnit source files.

All four component readers exist, but no device-lifetime adapter composes
them:

- the DA921x callback is registered with the provider owner after successful
  I2C probe and removed by a managed device action; its provider-registry,
  endpoint, and root-adapter locks cover two stable read samples;
- the platform-state source is device-managed and takes two stable read-only
  samples under its mutex, but its base DT node is disabled and it has no
  direct-source adapter;
- the protected-clock source is device-managed, boot-generation-bound, and
  sticky-faulted after an attempted protected snapshot error. Its operation
  mutex and handoff lease serialize the call, but the read uses bounded CSPM
  power-on/semaphore coordination writes plus one clock enable/disable pair;
- the BigiDVFS source is device-managed and boot-generation-bound. It takes
  two complete four-word samples under its operation mutex and sticky-faults
  on errors other than instability. Its named-firmware read-only ABI is
  confirmed, but no named-device mainline runtime sample has returned.

The base Gemini DT enables the DA921x child and its DVFSP handoff, while the
platform-state, protected-clock, and BigiDVFS nodes remain disabled unless an
explicit experiment overlay enables them.

### Exact A34 vector

`mt6797_a72_direct_source_valid()` checks shape, ABI, reserved fields, raw
byte width, and nonzero sample generations. A34 then uses one complete
`memcmp()` against a static expected record.

That expected record leaves every protected-clock raw field zero. The already
qualified named-device ABI-2/generation-1 clock record has 17 of its 18 raw
words nonzero: mux selection, all nine PLL words, all three CSPM software
words, and all four CSPM hardware-status words. Therefore that physical record
cannot pass the canonical A34 comparator. This is an exact hard mismatch, not
an adapter-only gap.

The expected BigiDVFS record likewise supplies ABI and generation while
leaving all four raw words zero. No physical result yet justifies those zeros.
The complete platform-state callback also lacks a current-mainline named-
device sample under the future outer owner.

## Analysis

The positive hypothesis is rejected on both independent branches.

Replay publication is blocked architecturally: a typed positive exists, but
no current-boot owner can assert it. Binding physical readers cannot repair
that gap. Conversely, replay authority would not make the physical input
valid: the direct adapter is absent, two component sources still need exact
named-device qualification in the composed path, and the current comparator
already rejects the qualified clock payload.

The atomic publication mechanics remain useful. They correctly hold the CPU
hotplug read lock and A72 transition mutex across direct capture, then use the
P30 nested finalizer and `a72_state_lock` for the final commit. Those mechanics
must stay dormant until both inputs are independently owned.

The next decision-bearing work should refine the physical branch without
pretending to solve replay. A separate offline contract should design one
default-off, staged physical-source qualification observer. It should retain
the established outer lock order, invoke platform, DA921x, clock, and
BigiDVFS sequentially, attribute entry and return of the first unqualified
secure read, publish no A34 result, and make no CPU request. Only that separate
experiment may review a Buildbox build and one device attempt.

## Conclusion

`rejected-current-production-inputs`: canonical source has neither a positive
current-boot replay-applicability owner nor an admissible complete physical
direct-state producer.

`replay-block`: `blocked-no-current-boot-primary-bl31-applicability-owner`.

`physical-block`:
`blocked-no-production-adapter-a34-clock-vector-mismatch-and-unqualified-physical-fields`.

There is no production publisher caller, physical binding, A34 vector
revision, build, boot candidate, device attempt, or CPU request admitted by
this audit.

## Follow-up

The selected next action is to freeze the separate staged physical-source
qualification contract described in [`DESIGN.md`](DESIGN.md). The
authoritative execution order remains in
[Roadmap Gate 7](../../docs/ROADMAP.md#7-bring-up-cpu8).
