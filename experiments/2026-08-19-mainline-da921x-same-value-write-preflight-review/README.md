# Experiment: mainline DA921x same-value-write preflight review

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-19-mainline-da921x-same-value-write-preflight-review` |
| Status | `completed` hardware-free review; implementation eligible |
| Subsystem | DA921x, MT6797 I2C6/DVFSP ownership, bounded write recovery |
| Device variant | Planet Gemini PDA, MT6797 named development unit |
| Date(s) | 2026-08-19 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 6 |

## Question or hypothesis

Do the exact B1--B4 closure receipts support one implementation contract for
the previously selected same-value `VBUCKB_B` write, without yet building a
kernel, making a boot candidate, accessing the Gemini, or performing an I2C
write?

The falsifiable claim is that implementation may proceed only if the complete
preflight/write/readback sequence fits the remaining controller ledger, holds
one root-adapter lock, suppresses automatic retry, attributes both write bytes,
and has an exhaustive stop-without-inverse failure map.

## Provenance and environment

- Fixed repository parent:
  `60b8de7e0d3dbf15e36071a7a9ae9aade5e1d931`.
- B1 runtime closure: [transaction-window result](../2026-08-18-mainline-i2c6-firmware-writer-transaction-window/results/runtime-attempt-1-success-20260819.txt),
  SHA-256 `4df19155b07334da33fe4fabbb4789879cadd7a61dbcd52f61fe220a57f76ffe`.
- B2 hardware-free closure: [KUnit result](../2026-08-19-mainline-i2c6-write-transport-kunit/results/qemu-attempt-1-success-20260819.txt),
  SHA-256 `48bb5834fc11aee4c7189cd0e285c2bf87d6106ab7d617d81d132638a95745df`.
- B3/B4 runtime closure: [finalized preflight result](../2026-08-18-mainline-da921x-runtime-preflight-ledger/results/runtime-attempt-1e-finalized-20260818.txt),
  SHA-256 `42ba653f1c19f96131c64e4abd1410f09d8faa157d6b8707b8f594813ec97e0e`.
- Historical proposal: [initial bounded no-op review](../2026-08-17-mainline-da921x-bounded-noop-write-review/README.md).
- No compiler, kernel build, boot image, device, USB endpoint, or I2C adapter was
  used by this review.

## Safety assessment

This experiment is repository-only and hardware-free. It performs no kernel
build, device access, boot2 installation, boot, power transition, register
write, regulator request, or CPU8/CPU9 request.

The review permits only implementation and hardware-free validation. A
physical DA921x write remains unauthorized until the new source, complete
failure tests, canonical series, all manifest profiles, exact clean pushed
Buildbox package, candidate, collector, and predeployment gates pass and their
sanitized evidence is reviewed. CPU8 and CPU9 remain closed.

## Associated code

- [`contract.json`](contract.json) freezes the closure receipts, exact 12-
  transfer action window, payload attribution, failure stages, recovery, and
  implementation gates.
- [`DESIGN.md`](DESIGN.md) explains the implementation seam and review decision.
- [`scripts/validate.py`](scripts/validate.py) verifies the receipt checksums
  and markers, the complete contract, and representative unsafe mutations.
- [`results/initial-review-20260819.txt`](results/initial-review-20260819.txt)
  is the sanitized validator receipt.

Run from the repository root:

```sh
python3 experiments/2026-08-19-mainline-da921x-same-value-write-preflight-review/scripts/validate.py
```

## Procedure

1. Verify the exact B1, B2, and combined B3/B4 receipt checksums and closure
   markers.
2. Reconcile the retained 20-entry startup ledger with its 32-entry capacity.
3. Freeze five preflight reads, one same-value write, immediate and delayed
   target readback, and four full-byte poststate reads as the only 12 action
   transfers.
4. Require pretrigger ledger verification under one root-adapter lock, use
   only unlocked `__i2c_transfer()` within that lock, force adapter retries to
   zero, and restore them on every exit.
5. Require a v2 ledger entry that records and validates both write bytes
   `[0xda, 0x46]`; the existing first-byte-only ledger is insufficient.
6. Freeze a stop-at-first-failure terminal state for each of the 12 possible
   transfer stages, with no retry, inverse write, rail action, or CPU request.
7. Validate the contract and unsafe mutations without touching hardware.

## Observations

- B1 proves stopped-SCP reset control at all 20 startup transfer entries and
  exits with zero reset failure on the exact named runtime.
- B2 proves the production MT6797 one-message two-byte FIFO plan, completion
  classes, no-retry single-transfer wrapper, and retry restoration without
  hardware.
- B3/B4 prove the exact 20-entry startup ledger and stable full-byte prestate:
  `CONTROL_A=0x7b`, `STATUS_B=0xc1`, `BUCKB_CONT=0x00`, and both Buck B
  selectors `0x46`.
- The action sequence needs exactly 12 transfers, reaching ledger entry 32.
  There is no spare entry for an extra sample, retry, rollback, or foreign
  transfer.
- The existing v1 ledger records only the register pointer. It cannot prove
  that the controller received data byte `0x46`; implementation therefore
  requires bounded v2 payload attribution before a candidate can exist.
- The static validator passes and rejects 36 unsafe mutations.

## Analysis

The four original evidence blockers are closed, so the historical design no
longer needs to remain implementation-blocked. Their combination does not
authorize a physical write: it exposes two implementation obligations that
were not represented in the original review.

First, per-transfer use of the B2 helper would release the root adapter lock
between reads and the write. The implementation must instead lock the root
adapter once, verify the exact pretrigger ledger under that lock, save and set
the adapter retry count to zero, and call the I2C core's unlocked
`__i2c_transfer()` for each bounded action. Calling `i2c_transfer()` while the
root lock is held risks nested locking and is forbidden. The regulator driver
must not import the controller-private B2 header.

Second, requested payload and physical-controller attribution are different
claims. A driver-local `0x46` constant proves intent only. The controller
ledger must record both bytes of the sole write-shaped entry and retain its
result and completion state. This is a source/build/test requirement, not a
reason to spend a device boot now.

## Conclusion

`confirmed` for implementation eligibility on parent `60b8de7`: all original
B1--B4 blockers have exact closure receipts, and the complete one-shot
software contract is now frozen.

`rejected` for current hardware execution: no implementation, Buildbox
package, validated candidate, or reviewed collector exists yet. No physical
DA921x write is authorized by this result, and CPU8/CPU9 admission remains
closed.

## Follow-up

The authoritative next action and exit conditions are in
[Roadmap Gate 6](../../docs/ROADMAP.md#6-prove-one-bounded-writable-operation):
implement this exact default-off experiment, validate every failure stage and
payload-attribution boundary without hardware, and build the exact clean
pushed commit on Buildbox.
