# Experiment: align CPU8 admission with expectation-only READY evidence

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-ready-token-contract-repair` |
| Status | `source contradiction proven; Buildbox patch generation pending` |
| Subsystem | arm64 late-CPU READY token and MT6797 CPU8 admission |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-30 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

The exact live trigger retained `failure_stage=2`, `derive_stage=2`, and
`operation_ret=-EPERM`, identifying `mt6797_a72_ready_token_validate()` before
A34 or any CPU request. Does the validator contradict the production READY
evidence contract by requiring pre-execution target observations that READY
must keep empty?

## Safety assessment

The production plan accepts only bound expectation evidence and explicitly
requires `observed_target_mpidr[]`, MIDR, REVIDR, and target-cap observations
to remain empty before either dormant A72 executes. READY copies that exact
validated evidence into its immutable token. The membership validator instead
requires `observed_target_mpidr[]` to equal `0x200/0x201`.

The repair keeps the target mask, target ordering, expected MPIDRs, profile,
ABI, and all identity checks. It changes the contradictory observed-MPIDR
predicate from “already equals the expected target” to “still empty,” matching
the production contract and remaining fail-closed. It adds no observation,
hardware effect, request, CPU9, CPU_OFF, retry, storage, device, or reboot path.

## Procedure

1. Reconstruct the exact canonical source through patch `0445` from the pinned
   managed Buildbox source and canonical patches `0442`--`0445`.
2. Generate one normal format-patch that requires empty pre-execution observed
   MPIDRs and updates all exact READY fixtures.
3. Add a focused mutation proving that either premature observed MPIDR is
   rejected before source capture or owner mutation.
4. Replay and audit the patch on Buildbox, admit it canonically, then run the
   smallest affected KUnit profiles through the explicit Buildbox backend.
5. Only if every offline gate passes, construct one separate boot2 candidate
   with the existing one-shot CPU8-only route and CPU9 veto.

## Observations

Exact candidate `7c962888...` reached serviceable mainline boot ID
`ae5a4cdf...`, verified runtime identity, and an armed zero-execution
controller. One trigger returned `operation_ret=-1`, `failure_stage=2`,
`derive_stage=2`, and zero requests while CPUs 0--7 stayed online and CPUs
8--9 stayed offline. See the
[runtime result](../2026-08-30-mainline-a72-live-a34-predicate-repair/results/runtime-attempt-1-ready-token-rejection-20260830.txt).

The exact prepared source shows:

- production plan validation accepts only bound expectation evidence and
  rejects any nonzero `observed_target_mpidr[]` before READY;
- READY copies that validated zero-valued pair unchanged into the immutable
  token; and
- `mt6797_a72_ready_token_validate()` requires the copied pair to equal
  `0x200/0x201`, then checks the selected member a second time.

No valid production token can satisfy both contracts. This is a deterministic
source contradiction at the exact runtime-retained substage, not an inference
from screen or reboot behavior.

## Analysis

The observed fields represent target-local facts and cannot exist before the
target CPU executes. The expected fields already bind CPU8/9 to MPIDRs
`0x200/0x201`; topology and the selected CPU slot are checked separately.
Requiring the observed fields to remain zero preserves the distinction between
expectation and observation and does not weaken target identity.

## Conclusion

`production-ready-token-contract-contradiction`.

## Follow-up

Generate and independently validate the one-patch repair on Buildbox. Do not
repeat candidate `7c962888...`. CPU9 remains vetoed until CPU8 is reproducibly
online.
