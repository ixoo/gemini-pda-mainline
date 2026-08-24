# Experiment: mainline A72 physical-source qualification contract

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-24-mainline-a72-physical-source-qualification-contract` |
| Status | completed offline contract; implementation and device attempt not admitted |
| Subsystem | MT6797 A72 direct state, DA921x, protected clocks, BigiDVFS |
| Device variant | Planet Gemini PDA named development unit; source-only contract |
| Date(s) | 2026-08-24 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, physical direct-state input |

## Question or hypothesis

What is the smallest safe sequence that can produce one attributable physical
direct-state record under the existing A72 owner, without enabling a writable
provider merely to obtain DA921x state or invoking the production publisher?

The hypothesis is that the work requires two distinct phases. A hardware-free
source slice must first make the stable DA921x snapshot available while the
positive writable transaction remains uncompiled. Only then may a staged
diagnostic adapter perform one owner-held physical snapshot with durable
records immediately before and after the first BigiDVFS call.

## Provenance and environment

- Repository input: signed and pushed commit
  `3d7eae1f33cfb8d8837df68ed6317e85c5cbfdba`.
- Canonical source remains through patch `0347` at managed Buildbox state
  `ac57421ae45c6e55ba34f2cac4131647e89762ad5988baf1b47364c2c75e77cb`.
- Managed-source integrity:
  `d87fe0d866aec4825c2e2c2bf5f1df628299692e5bad63e581b07c64d0f3c22d`.
- The exact source was inspected read-only on Buildbox. No kernel source tree
  was copied to or from it.

Exact identities and scope are in [`contract.json`](contract.json) and
[`results/source-contract-20260824.txt`](results/source-contract-20260824.txt).
The ordered decisions are in
[`results/decision-matrix.tsv`](results/decision-matrix.tsv).

## Safety assessment

This contract audit performed no build, device contact, MMIO, SMC, I2C
transfer, retained-RAM write, clock operation, provider operation, CPU request,
boot-image construction, partition access, or `boot2` write. It does not admit
a boot candidate or physical selection.

Phase A below is hardware-free. Phase B is design only until Phase A passes
its separate exact Buildbox proof and a later review admits the candidate
tooling and one device attempt. Both CPU vetoes, CPU-disable veto, A34, P30,
and the membership owner remain unchanged.

## Associated code

- [`DESIGN.md`](DESIGN.md) freezes both phases, lock order, attribution, and
  stop rules.
- [`contract.json`](contract.json) pins exact source and prior evidence.
- [`scripts/validate.py`](scripts/validate.py) validates this offline record.
- [`results/source-contract-20260824.txt`](results/source-contract-20260824.txt)
  records the bounded source decision.

Run without privilege or hardware access:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 \
  experiments/2026-08-24-mainline-a72-physical-source-qualification-contract/scripts/validate.py
```

## Procedure

1. Inspect the final direct-state registry and physical reader definitions.
2. Trace the DA921x provider snapshot through all preprocessor gates and prove
   whether a no-write configuration can register it.
3. Compare the current protected-readback observer with the owner-held direct
   compositor contract.
4. Reuse only the independently qualified two-record retained-RAM mechanism,
   while assigning new record ownership and stage semantics.
5. Freeze the two source phases, result map, and stop conditions before any
   patch generation or build.

## Observations

The direct-state compositor and atomic publisher already supply the correct
outer mechanics. `mt6797_a72_direct_state_snapshot()` holds the CPU-hotplug
read lock and `a72_transition_lock`, retains the direct registry mutex through
one callback, verifies the membership owner before and after, and publishes an
all-or-zero result. The future diagnostic must call this public entry point;
it must not reproduce the topology or owner checks in a new observer.

The current protected-readback observer is not a substitute. It independently
gets the clock and BigiDVFS devices and invokes them from its probe. It does
not sample platform or DA921x state, register the direct source, take the A72
transition mutex, or produce the direct-state ABI.

The DA921x path has a configuration blocker. Its stable five-register
snapshot callback, endpoint, raw read helper, and `.snapshot` member are all
inside `REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION`. Selecting that
option also compiles the Buck-B enable/disable writer and its writer-transaction
dependency. The acquire and release callbacks already fail cleanly with
`-EOPNOTSUPP` when the positive option is off, but `.snapshot` is then absent.
Currently, no read-only profile can consume it without also compiling the
writer. Therefore Phase B must not select the positive option; Phase A must
separate the read-only snapshot first.

The protected clock has one qualified named-device read. Repeating exactly
one call is justified only inside the non-identical combined-record
hypothesis: it proves the read can execute after platform and DA921x sampling
while the CPU-hotplug/A72 outer owner remains held. BigiDVFS's exact firmware
ABI is confirmed, but its mainline call has never returned in attributable
named-device evidence.

Records 1 and 2 at `0x44410000` and `0x44411000` already have qualified empty-
header, payload-before-metadata, signature-last, full-readback, warm-retention,
and changed-ID Gemian recovery behavior. The staged observer may reuse that
mechanism with a new token only after requiring both headers empty.

## Analysis

The hypothesis is confirmed as an ordered contract, not as hardware support.

Phase A is the only currently admissible implementation. It moves or factors
the fixed read-only DA921x snapshot machinery so `ARM64_MT6797_A72_PROVIDER_OWNER`
can always register `.snapshot`, while acquire/release remain the existing
read-only `-EOPNOTSUPP` stubs and the positive writable option stays off. Its
focused tests must prove two matching samples, every read failure, short
transfer, instability, zeroed output, unregister lifetime, and absence of the
writer symbol/configuration. This phase performs no physical I2C transaction.

After Phase A passes, Phase B may add one default-off candidate-only direct-
source observer. It obtains bound platform, clock, and BigiDVFS device
references, registers one temporary physical callback, calls the existing
public direct snapshot exactly once, unregisters before releasing references,
and logs the complete result. The callback order is platform, DA921x, clock,
record 1, BigiDVFS, record 2. Record 1 therefore proves all earlier readers
returned and the BigiDVFS call is next; record 2 proves that call returned.

Neither phase may evaluate A34, claim P30, call the bootstrap publisher,
acquire or release the provider, clear a diagnostic blocker, or request a CPU.

## Decision map

- Neither retained record: the observer did not reach the BigiDVFS boundary,
  or platform/DA921x/clock/direct-state preconditions failed. Keep BigiDVFS
  unqualified and use live/console evidence only to subdivide the earlier path.
- Exact record 1 only: the first BigiDVFS call was entered next and did not
  return before reset or hang. Reject without retry.
- Exact records 1 and 2: BigiDVFS returned. Accept only if the exact live or
  retained console record supplies one complete all-or-zero direct result,
  every component return, generation, owner/topology field, and serviceability
  gate.
- Record 2 without exact record 1, malformed/duplicate records, multiple
  calls, retry, writer linkage, provider action, A34/P30/publication, or CPU
  activity: reject attribution and stop.

## Conclusion

`confirmed-two-phase-contract`: source separation must precede the staged
physical direct-state observer.

`selected-next`: implement and prove only the hardware-free DA921x read-only
snapshot separation. Keep the positive writable transaction off and add no
physical adapter, build candidate, device action, or CPU request in that
source slice.

## Follow-up

[`DESIGN.md`](DESIGN.md) is the exact implementation boundary. The repository-
wide order remains in [Roadmap Gate 7](../../docs/ROADMAP.md#7-bring-up-cpu8).
