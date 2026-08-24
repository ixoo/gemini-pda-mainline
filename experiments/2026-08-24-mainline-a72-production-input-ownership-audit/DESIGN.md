# A72 production-input ownership decision

## Two-authority boundary

Atomic publication requires two independent positive records:

1. a boot-local replay-applicability record that proves the exact primary-
   BL31 clear applies to this boot and the private replay value is zero; and
2. one owner-held physical direct-state record covering DA921x, A72 platform
   state, protected clocks/CSPM, and BigiDVFS.

Neither record may derive its authority from the other. A recovered physical
tuple does not prove which secure entry initialized private replay state, and
a static secure-entry proof does not attest current physical state.

## Exact producer and lifetime inventory

| Input | Initialization and lifetime | Lock/order | Failure and current decision |
| --- | --- | --- | --- |
| Replay applicability | No production initializer, storage owner, invalidator, or caller exists. The publisher borrows a caller record for one call. | Validated under the outer CPU-hotplug/A72 transition ownership, but the caller owns its bytes. | Null/malformed is `-EINVAL`/`-EPROTO`; unknown is `-ENODATA`; non-applicable/nonzero is `-EPERM`. Positive production input is absent. |
| Direct-source registry | Static null at boot; one exact callback/context may register; exact-pair unregister clears it. | Registry mutex is held through the callback, preventing concurrent teardown. | Missing is `-ENODEV`; duplicate is `-EBUSY`; malformed output is `-EPROTO`. Production registration is absent. |
| DA921x provider snapshot | Registers after successful I2C/provider probe; `devm_add_action_or_reset()` unregisters before device storage is released. The callback and helper currently exist only under the positive writable provider Kconfig option. | A72 provider registry, endpoint mutex, root-adapter lock; retries forced to zero; two complete samples. | Output starts zero; read error or instability returns error without publication. A read-only profile cannot select the callback without compiling the Buck-B writer, so source separation is required before physical composition. |
| A72 platform state | Device-managed after SPM/reset/MMIO probe; invalid when the platform device is unbound. Base node is disabled. | Source mutex across two complete samples; outer A72 transition lock must serialize PSCI. | Read error, CCI busy, or movement rejects; output remains zero. No current-mainline named-device composed sample exists. |
| Protected clock/CSPM | Device-managed after MCUMIXED, handoff, and clock probe; generation starts at zero and advances per successful boot-local read. Base node is disabled. | Backend operation mutex, handoff execution/transfer ownership, clock enable, local IRQ exclusion, semaphore spinlock. | Output starts zero; an attempted protected error is sticky. The call performs bounded coordination writes. One named-device read is qualified, but its 17 nonzero raw words contradict A34's zero vector. |
| BigiDVFS | Device-managed after exact `method = "smc"` probe; generation starts at zero and advances per successful boot-local read. Base node is disabled. | Backend operation mutex across two complete four-call samples. | Output starts zero; instability is `-EAGAIN`; other transport errors become sticky. Named-firmware ABI is confirmed; named-device mainline runtime is unqualified. |

No registered source context or boot-local generation authority survives
device unbind, module removal, or reboot. A copied record must not be reused
after any of those invalidations or after a newer successful generation. A
future direct adapter must hold references to all three platform devices and
rely on the existing DA921x provider registry; it must unregister its direct
callback before releasing those references.

## Complete lock order

The existing atomic publisher fixes the outer and final order:

```text
cpu_hotplug_lock (read)
  -> a72_transition_lock
    -> direct-source registry mutex
      -> physical callback, sequential readers only
    -> P30 pristine-claim/finalizer raw lock
      -> a72_state_lock for the non-sleeping final commit
```

The physical callback preserves the previously reviewed sequential order and
never nests one component reader inside another:

```text
platform-state source mutex
DA921x provider registry -> endpoint mutex -> I2C root-adapter lock
protected-clock operation -> handoff/clock/IRQ/semaphore locks
BigiDVFS operation mutex
```

Every component output and the complete direct-source destination are cleared
before use. The callback may set direct-source `valid=1` only after all four
component results are complete and valid. Any failure returns the first exact
errno and leaves the complete destination all-zero.

## Rejected replay substitutes

The following are not a positive current-boot replay producer:

- the static BL31 clear range without current-boot applicability;
- raw TOPRGU zero or its correlated retained ram-console projection;
- LK boot reason or overwritten `INTERVAL` state;
- preserved ATF logs;
- ordinary Linux reboot or a changed Linux boot ID;
- a Linux-owned zero, test fixture, constant initializer, or DT property;
- `AFFINITY_INFO` or CPU8/CPU9 offline state; or
- a recovered physical direct-state tuple.

Until a separately reviewed producer has boot-local initialization,
invalidation, and exact source-backed semantics, the only admissible replay
record is `UNKNOWN`, which rejects before source capture.

## A34 vector correction boundary

The canonical A34-v2 evaluator uses full-record `memcmp()`. This is safe in
the fail-closed direction but its physical vector is not admitted:

- every protected-clock raw field is statically zero, while 17 of 18 are
  nonzero in the one qualified physical ABI-2 record;
- all four BigiDVFS words are statically zero without a physical result; and
- unspecified platform-state fields are zero without a current-mainline
  composed observation.

Do not weaken `memcmp()`, ignore fields, or accept any structurally valid
record. A later A34 revision may change the exact values or use explicit
masked predicates only after one attributable physical qualification record
establishes each field and its stability rule.

## Selected next experiment contract

The next experiment is a new, separately reviewed physical-source
qualification contract, not an implementation authorization from this audit.
Its offline design must require:

1. a hardware-free first slice that separates the stable DA921x snapshot from
   the writable positive-provider option and proves the writer stays absent;
2. a later default-off diagnostic adapter with no production publisher caller;
3. the exact outer and component lock order above;
4. device-lifetime source registration only after every dependency is bound,
   and unregister-before-release cleanup;
5. one complete staged snapshot, with zero retries at the compositor level;
6. durable attribution immediately before and after the first named-device
   BigiDVFS call, while distinguishing platform, DA921x, and clock returns;
7. exact raw output for every field, ABI, generation, and return code;
8. no A34 evaluation, P30 claim, owner publication, provider acquire/release,
   CPU_ON, CPU_OFF, or CPU8/CPU9 request; and
9. a predeclared stop on mismatch, timeout, sticky fault, or incomplete
   attribution.

Only after that contract passes offline review may its own experiment admit a
clean pushed Buildbox build and at most one physical selection. The qualified
record can then decide whether to revise the A34 vector, repair a source, or
stop the physical branch.

## Explicit exclusions

This audit adds no source adapter, replay producer, DT enablement, hardware
operation, A34 change, publisher caller, lifecycle state, CPU-veto change,
build, boot candidate, device access, partition write, or CPU request.
