# Experiment: mainline A72 atomic publication contract audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-24-mainline-a72-atomic-publication-audit` |
| Status | completed offline audit; nested P30 finalizer selected |
| Subsystem | MT6797 A72 bootstrap publication and P30 exclusion |
| Device variant | Gemini PDA contract; canonical-source audit only |
| Date(s) | 2026-08-24 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, atomic membership publication |

## Question or hypothesis

Do canonical A34-v2, direct-state-v2, and the P30 pristine claim now admit one
hardware-free owner publication point without a P30 race, a fallible operation
after commit, a production source binding, or relaxation of either CPU veto?

The positive hypothesis requires the CPU hotplug and transition locks to remain
held from direct capture through the final owner recheck. It also requires P30
to remain unavailable to `prepare()` until the owner store is complete.

## Provenance and environment

- Repository input: signed and pushed commit `d77441e9`.
- Canonical prepared source state: `5f830ffd6050d3831b2a6a5d94b6f8a8125444215f93828de714c5f551dcf0ad`.
- Prepared-source integrity: `6e8edea4e04443353bcc5bc5c6da8eed3914bcca529e864f8af9af52a9ef502d`.
- Canonical series ends at patch `0344`.
- The exact prepared tree was inspected read-only on Buildbox. No source tree
  was copied to or from Buildbox.

Exact file hashes, caller counts, state writes, and veto results are in
[`results/source-audit-20260824.txt`](results/source-audit-20260824.txt).
Rejected and selected commit shapes are in
[`results/decision-matrix.tsv`](results/decision-matrix.tsv).

## Safety assessment

This audit performed no build, source edit, hardware access, MMIO, SMC, I2C
transfer, provider action, CPU request, boot artifact, device contact, or
partition write. It does not authorize a physical source or a device attempt.

The selected implementation remains default-off and has no production caller.
It may open only injected KUnit owner state. CPU-up must still return
`-EOPNOTSUPP` after publication, `mt6797_psci_cpu_boot()` must still return
`-EAGAIN`, and CPU disable must remain vetoed.

## Associated code

- [`DESIGN.md`](DESIGN.md) freezes the selected lock, commit, and failure
  contract.
- [`contract.json`](contract.json) records the machine-readable decision and
  scope closure.
- [`scripts/validate.py`](scripts/validate.py) checks the canonical patch
  identities and this audit's exact evidence.

## Procedure

1. Pin the exact repository and prepared-source identities.
2. Inspect the canonical direct capture, A34 evaluator, P30 claim/release,
   owner state, test seed, CPU-up admission, CPU boot, and CPU-disable bodies.
3. Count production callers and `AVAILABLE` publication assignments.
4. Test every ordering of claim release and owner commit against the existing
   lock order and no-fallible-after-commit rule.
5. Preserve only a shape that closes both the P30 entry gap and post-commit
   failure window while keeping all hardware and CPU effects absent.

## Observations

Canonical A34-v2, direct-state-v2, and the P30 claim pass their independent
hardware-free proof. They still have no production caller or physical source
binding. The only assignment of `MT6797_A72_OWNER_AVAILABLE` is the KUnit-only
test seed.

The public direct snapshot acquires and releases `cpus_read_lock()` and
`a72_transition_lock` internally. A later publisher cannot call that public
API and preserve ownership through its commit; it must use the locked internal
capture while retaining both locks.

The P30 claim blocks `arm64_late_cpu_startup_prepare()`, but its current release
is a separate fallible call. Releasing before the owner store permits
`prepare()` to enter between release and publication. Storing the owner first
leaves a fallible P30 release after the commit and can strand an open owner
behind a live claim.

The existing lock order already permits the missing bridge: P30 private lock,
then `a72_state_lock`. A typed finalizer can validate the opaque claim, clear
it while retaining the P30 lock, invoke one non-sleeping owner callback under
`a72_state_lock`, and release P30 only after the callback returns. A failed
callback leaves the owner unchanged and the claim released. A successful
callback has no fallible operation after `health = AVAILABLE` is stored last.

## Analysis

The selected finalizer is narrower than a general transaction callback. It is
valid only for a held pristine bootstrap claim, executes with interrupts
disabled, and permits its callback to take only the next declared raw lock.
The callback must either reject before mutation or perform the complete scalar
owner commit and return zero.

The future publisher must validate replay input before any source callback,
hold the CPU hotplug read lock and transition mutex across locked direct
capture, A34 evaluation, P30 claim, and finalization, and recompare the exact
pristine owner inside the final callback. The prepared scalar destination
clears only `MT6797_A72_BLOCK_A34_BOOTSTRAP`, publishes health last, and leaves
every transaction, member, provider, controller, and hardware effect empty.

A repeat call must observe `AVAILABLE` before invoking the source and return
`-EALREADY`. Malformed replay, source failure, A34 rejection, a non-pristine
owner, a busy P30 claim, or a final owner mismatch leaves the owner unchanged.

## Conclusion

`selected-nested-finalizer`: the proven inputs admit a default-off,
hardware-free atomic publication implementation, but not through the current
separate P30 release API. The implementation must add the nested finalizer and
one no-production-caller membership publisher with injected KUnit coverage.

This conclusion does not establish current-boot replay authority, physical
source binding, or CPU8 readiness. It creates no boot candidate.

## Follow-up

The authoritative next action and its position in the CPU8 sequence are in
[Roadmap Gate 7](../../docs/ROADMAP.md#7-bring-up-cpu8).
