# A34 publication contract decision

## Canonical boundary

The canonical tree has three separate objects:

1. the A34-v1 pure evaluator, whose complete observation is caller supplied;
2. the direct-state-v1 compositor, which owns stable raw source composition
   and a pristine membership snapshot; and
3. P30, which owns its own protocol state under a private raw spinlock.

None may be silently treated as another. In particular, a complete raw record
is not a recovered-state decision, and a static BL31 zeroing proof is not a
current-boot applicability source.

## Rejected production input

The following cannot authorize owner publication:

- `direct.source.valid == 1` without field-level recovered-state checks;
- A34-v1 reset provenance supplied as `PLATFORM` or `EXTERNAL` by an
  unowned caller;
- the KUnit direct-state fixture values as physical evidence;
- generic CPU8/CPU9 offline state without the physical source;
- a P30 snapshot sampled before the commit without an interlock;
- primary-BL31 replay-clear source analysis without current-boot
  applicability; or
- any combination of raw TOPRGU zero, retained ram-console zero, LK boot
  reason, ordinary Linux reboot, or Linux-owned zero state.

## Required A34-v2 input ownership

The next source-only slice must define one A34-v2 observation with exactly two
top-level authorities:

- one complete `mt6797_a72_direct_state_snapshot`, created by the compositor
  while holding the CPU hotplug read lock and A72 transition lock; and
- one typed replay-applicability record whose default/unknown value rejects.

It must not repeat caller-populated owner, topology, CPUHP, MPIDR, generation,
cookie, or P30 structures beside the direct-state record. Any target identity
missing from direct-state-v1 must be added to the next direct-state ABI and
collected by the same owner, not copied into A34 from an unowned caller.

The replay record must distinguish at least:

- unknown/unavailable, which always rejects; and
- exact applicable primary-BL31 replay clear with private replay value zero.

The second value is an interface definition only. This audit identifies no
production Linux source allowed to publish it.

## Recovered-state predicate

The next evaluator must test every member needed for A72 safety. Structural
validity is only an entry gate. The field decision must cover:

- exact DA921x control/status/Buck-B state;
- both A72 CPU-status bits in both SPM status words;
- the source-backed masks of cluster and per-core SPM control words;
- external-buck isolation, PWRAP reset, and MP2 DCM state;
- CCI MP2 request and global change-pending state;
- protected B/CCI clock and CSPM state;
- all four BigiDVFS secure readback words;
- CPU8/CPU9 method identity, MPIDRs, possible/present/offline state;
- the exact pristine membership owner, including private next identity; and
- exact pristine P30 state through the interlock below.

Unknown values or fields without a source-backed safe predicate reject. An
over-strict predicate may reject real hardware and be refined by a separate
read-only result; it must never accept a field merely because it was stable.

## Lock and P30 interlock contract

The future owner order is:

1. CPU hotplug read lock;
2. A72 transition mutex;
3. direct-source registry mutex and source-local locks during capture;
4. P30 private lock to claim exact pristine state;
5. A72 state raw spinlock for the final owner recheck and commit.

No path may acquire the A72 transition mutex while holding the P30 lock. The
P30 claim must be opaque and owner-scoped. While held, it blocks the only edge
from exact pristine P30 state, `arm64_late_cpu_startup_prepare()`. All other
P30 operations already require non-pristine token/state and cannot originate
from the claimed state.

Claim failure leaves both owners unchanged. Any A34 failure after a successful
claim releases it before returning. The claim is not lifecycle publication and
must not remain held after success or failure.

## Future single publication contract

Publication is deliberately not admitted by this audit. When the evaluator
and interlock have independent passing evidence, a later review may admit one
commit point with these exact properties:

- final pristine-owner comparison under `a72_state_lock`;
- destination fully prepared before mutation;
- one locked update to `AVAILABLE / IDLE`, empty members/provider/controller,
  valid bootstrap/membership, all four attempts available, first generation
  `1`, first cookie `0xa7200001`, and all other transactional state empty;
- clear only the diagnostic A34-bootstrap blocker, because diagnostics are not
  capabilities and every later blocker remains true;
- publish `health = AVAILABLE` last;
- no fallible operation after the commit;
- a second call fails before any source callback or state mutation; and
- CPU-up still returns `-EOPNOTSUPP`, `mt6797_psci_cpu_boot()` still returns
  `-EAGAIN`, and CPU disable remains vetoed.

## Fail-closed results

| Condition | Required result | Owner effect |
| --- | --- | --- |
| Null, ABI, reserved, or malformed input | `-EINVAL` or `-EPROTO` | unchanged |
| Missing source or replay applicability | source error or `-ENODATA` | unchanged |
| Stable but non-recovered raw value | `-EPERM` | unchanged |
| Topology, target identity, or owner mismatch | `-EPERM` | unchanged |
| P30 not pristine or already claimed | `-EBUSY` or `-EPERM` | unchanged |
| Repeated successful publication attempt | `-EALREADY` | unchanged |

Every failed output record is all-zero. A pre-commit failure is retryable only
after its external condition changes; it does not fault the still-unopened
membership owner. No failure may consume an attempt, mint a token, call a
provider, arm P30, or reach PSCI.

## Explicit exclusions

No physical source registration, DT enablement, MMIO, SMC, I2C operation,
provider action, membership publication, CPU-veto relaxation, CPU_ON, CPU_OFF,
boot image, device access, or partition write is authorized by this audit.
