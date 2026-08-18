# Experiment: mainline DA921x bounded no-op write review

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-17-mainline-da921x-bounded-noop-write-review` |
| Status | `completed` design review; implementation blocked |
| Subsystem | DA921x, MT6797 I2C6/DVFSP ownership, regulator rollback |
| Device variant | Planet Gemini PDA, MT6797 named development unit |
| Date(s) | 2026-08-17 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 6 |

## Question or hypothesis

Can the completed read-only provider evidence be reconciled into one exact
least-invasive Gate-6 write/readback/rollback protocol without yet performing
a kernel build, device write, regulator write, or CPU8/CPU9 request?

The falsifiable design claim is narrower: a same-value write of `0x46` to
unselected `VBUCKB_B` at primary address `0x68`, register `0xda`, is the safest
candidate transaction if and only if every preflight and ownership blocker is
closed first.

## Provenance and environment

- Fixed runtime parent: `7.1.3-gemini-da921x-lkro`.
- Exact parent boot2 checksum:
  `eeee7adea53134c8146e10591708725649a8331bdef7ad418a847b5d04c8e854`.
- Parent runtime: [Gate-5 result](../2026-08-17-mainline-da921x-readonly-provider-baseline/results/runtime-attempt-1-success-20260817.txt).
- Prior owner audit: [DA921x page and BUCKB ownership](../2026-08-06-da921x-page-owner-audit/README.md).
- Prior rollback evidence: [accepted pre-isolation result](../2026-08-02-a72-pre-isolation-rollback-discriminator/results/runtime-2-20260802.txt).
- Public register source: Renesas
  [DA9213/14/15 Datasheet, revision 03.61](https://www.renesas.com/en/document/dst/da92131415-datasheet).
- No compiler, kernel build, boot image, or device was used by this review.

## Safety assessment

This experiment is repository-only and read-only. It performs no I2C transfer,
hardware write, boot2 deployment, boot, reboot, power transition, or device
access. The standing boot2 authorization does not make the proposed regulator
write eligible.

The [design](DESIGN.md) fixes the exact future message, preflight, readbacks,
failure path, and recovery path. It prohibits retries, a second/rollback write,
`PAGE_CON` access, regulator consumers, and CPU8/CPU9 requests. Four unresolved
blockers keep implementation and hardware action disabled.

## Associated code

- [`contract.json`](contract.json) is the machine-readable transaction and
  blocker ledger.
- [`scripts/validate.py`](scripts/validate.py) validates the exact no-op and
  rejects six representative unsafe mutations.
- [`results/initial-design-review-20260817.txt`](results/initial-design-review-20260817.txt)
  is the sanitized validator receipt.

Run from the repository root:

```sh
python3 experiments/2026-08-17-mainline-da921x-bounded-noop-write-review/scripts/validate.py
```

## Procedure

1. Reconcile the exact Gate-5 runtime counts and DA921x bytes with the public
   register definitions.
2. Compare same-value, changed-value-with-rollback, and page-selector writes.
3. Select the smallest transaction that cannot change the active voltage or
   enable state under the exact observed prestate.
4. Specify full-byte preflight/readback, controller result, failure handling,
   CPU closure, and independent reboot recovery.
5. Reject implementation while any ownership, transport, attribution, or live
   preflight blocker remains.
6. Validate the machine-readable contract and representative unsafe mutations.

## Observations

- The current runtime observed Buck B disabled at selector `0x46`, with
  `BUCKB_CONT = 0x00`, `VBUCKB_A = 0x46`, and `VBUCKB_B = 0x46` across the
  identity/provider evidence.
- The public register contract makes `VBUCKB_B` unselected while
  `BUCKB_CONT = 0x00`; a full-byte same-value write to `0xda` therefore avoids
  an active selector, voltage, enable, GPI, or slew-mode transition.
- `V_LOCK` at `CONTROL_A` bit 7 can suppress writes to the target register
  range, but its live state was not captured by Gate 5.
- Gate 5 counted 20 native I2C6 transfers. Fourteen identity reads plus four
  explicit observer reads explain 18; two remain unattributed.
- The Linux generation/cookie lease exists, but the historical firmware
  `SEMA_I2C_DRV` pause lease is not callable or replaced in mainline.
- Native I2C6 runtime evidence covers the combined one-byte pointer/read shape,
  not the proposed one-message two-byte write.
- The static validator passes and rejects changed-value, rail-enable, CPU-
  request, retry, missing-blocker, and premature-build mutations.

## Analysis

The same-value `0xda: 0x46 -> 0x46` proposal is materially safer than changing
the unselected selector to `0x45` and restoring it: the latter can leave a
latent alternate voltage if the inverse fails. It is more relevant than a
same-value `PAGE_CON` write because it exercises the eventual register-data
path without disturbing shared page state.

It remains a real control-interface write, even though the requested state is
unchanged. The stopped-receiver handoff, unexplained transfers, and unproved
native write shape prevent the review from promoting it to hardware action.
The `V_LOCK` and status preflight also need exact runtime evidence. These are
decision-changing gaps, not reasons to repeat the successful Gate-5 artifact.

## Conclusion

`confirmed` for the design-only claim: the exact same-value write to unselected
`VBUCKB_B` is the least-invasive Gate-6 candidate under the specified prestate.

`rejected` for current implementation or execution. Firmware ownership, write
transport, transfer attribution, and live preflight remain blocking. Roadmap
Gate 6 and CPU8/CPU9 admission remain open/closed respectively.

## Follow-up

See [Roadmap Gate 6](../../docs/ROADMAP.md#6-prove-one-bounded-writable-operation)
for the authoritative ordered follow-up and exit criteria.
