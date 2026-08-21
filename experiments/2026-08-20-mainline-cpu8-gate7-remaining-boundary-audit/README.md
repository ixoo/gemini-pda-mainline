# Experiment: mainline CPU8 Gate-7 remaining-boundary audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-20-mainline-cpu8-gate7-remaining-boundary-audit` |
| Status | completed offline audit; A34 eligibility evaluator selected |
| Subsystem | MT6797 Cortex-A72 lifecycle, capability finalization, P24/P30, P27/P28 |
| Device variant | Planet Gemini PDA named development unit |
| Date | 2026-08-20 America/New_York |
| Tracking issue | Roadmap Gate 7 |

## Question or hypothesis

After the exact positive-provider inverse is complete through canonical patch
`0301`, which remaining Gate-7 boundary is the first hard dependency that can
produce decision-changing evidence without a physical provider write or CPU8
boot?

The hypothesis is that the hardware-free A34 eligibility evaluator is the only
independently testable predecessor. It can freeze and exhaustively test the
exact zero-state predicate, including explicit reset provenance and private
replay proof inputs, while retaining the closed owner and every request and
hardware veto.

## Provenance and environment

- Repository parent: `7bbd19fb71ff7ae5053cf5f676ce5980169c9c5c`.
- Linux baseline: pinned 7.1.3 with the canonical 293-entry prefix through
  patch `0301`; exact prefix and input hashes are in [`contract.json`](contract.json).
- Exact Buildbox prepared source state:
  `1db1fb912bc7a0f35e4511f314d4300e52d0ab4f687b4b06a1556d8b687b5f3b`;
  recursive integrity:
  `608267dc1bcb809d42075df33ed2320bba86831f18607a6d7e7c186b1d27c97f`.
- The audit used read-only repository inspection and read-only SSH inspection
  of that exact source. No source tree was copied to or from Buildbox.
- No compiler, package, device endpoint, partition, regulator, CPU request,
  reboot, or retained private artifact was used.

## Safety assessment

This audit authorizes no physical write, P27/P28 effect, CPU request, boot
image, boot2 write, reboot, or device action. CPU8 and CPU9 remain behind the
A26 boot veto and A14 disable veto.

The selected implementation is default-off and hardware-free. It is a pure
evaluator with injected immutable input and no production caller. It cannot
open the transaction lifecycle, begin a transaction, or call a provider,
firmware, PSCI, CPUHP mutation, or hardware register.

## Associated records

- [`DESIGN.md`](DESIGN.md) records the dependency proof and exact implementation boundary.
- [`contract.json`](contract.json) pins the canonical prefix, exact source, and non-scope.
- [`results/remaining-boundary-matrix.tsv`](results/remaining-boundary-matrix.tsv) ranks the six separable boundaries.
- [`scripts/validate.py`](scripts/validate.py) checks the pinned repository inputs and decision consistency.
- `results/audit-validation-20260820.txt` records the sanitized validation run.

## Procedure

1. Reconstruct reachability from exact source through patch `0301`.
2. Trace the only A41 READY producer into membership token validation and the
   only membership token into P30/P30E.
3. Separate A41 identity binding from absent target evidence and mutation.
4. Separate P27/P28 attestations from absent hardware executors and inverses.
5. Compare the A34 evaluator, unresolved production reset/bootstrap owner,
   request caller, P28 executor, A41 completion, and P24/P30 integration by
   dependency and hardware-free testability.
6. Select only the earliest boundary and retain every downstream veto.

## Observations

- The owner initializes `CLOSED / UNINITIALIZED`; only a KUnit seed can create
  `AVAILABLE / IDLE`.
- Even in AVAILABLE, the current admission hook returns `-EOPNOTSUPP`; there is
  no production call to `begin_up()`.
- `begin_up()` requires an exact A41 READY token before minting P30 identity.
- A41 preparation unconditionally adds `COMMIT_PATH`; more importantly, the
  selected non-fixture profile supplies no target observations and both
  preparation and plan validation return `-EAGAIN`.
- P27 and P28 record preparation ledgers but execute no hardware effects. P28
  is downstream of A36, P27 completion, and a held provider identity.
- Frozen P13/A34 requires a known-good platform or external reset and an
  owner-safe private replay-zero proof. It explicitly forbids assuming that an
  ordinary Linux reboot satisfies either condition; both owners remain
  unresolved.
- The durable
  [TOPRGU resource record](../../docs/hardware/mt6797-live-resource-map.md)
  says the returned watchdog-class reason cannot distinguish a TOPRGU software
  reset from expiry. It therefore cannot supply A34 reset provenance by itself.
- The P24/P30 caller is therefore downstream of a completed A34 production
  owner, A41, P27/P28, P30E/P32, and the A26 review; it is not an independent
  next slice.

## Analysis

Deleting the A41 commit blocker would manufacture reachability without the
evidence needed to derive its capability and mitigation effects. Implementing
P28 now would instead create the first unowned physical edge. Connecting
P24/P30 would combine both errors and approach `CPU_ON` before its prerequisites.

A34 is different only at its pure decision boundary: the complete reset-zero
predicate is frozen and can be proven with injected immutable observations.
The frozen contract also says that the reset and bootstrap owners are
unresolved. Therefore a boot-time caller based only on a new kernel instance
or software-zero state would be a false implementation: it would silently
replace the required known-good platform/external-reset proof and owner-safe
private replay proof with an ordinary Linux reboot assumption.

The separable next slice is consequently the pure A34 eligibility evaluator
and its explicit input ABI. A positive evaluator result is not reset evidence
and grants no authority; only a later reviewed production owner may combine it
with independently established provenance and atomically open the lifecycle.

## Conclusion

`confirmed`: implement the hardware-free A34 eligibility evaluator next. It
must reject missing or ambiguous reset provenance, missing owner-safe private
replay-zero proof, and every mutation of the frozen topology/mapping/ledger
tuple. It has no production caller and cannot perform the future
`CLOSED -> AVAILABLE` transition. It does not include the future transaction caller.

`rejected` for a physical provider write, P28 executor, A41 READY shortcut,
P24/P30 CPU request, CPU8 boot, or boot-veto change at this boundary.

The authoritative next-step order is maintained only in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md).
