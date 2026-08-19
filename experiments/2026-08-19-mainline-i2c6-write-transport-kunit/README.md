# Experiment: mainline I2C6 write-transport KUnit proof

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-19-mainline-i2c6-write-transport-kunit` |
| Status | `running` design frozen; implementation not yet built |
| Subsystem | MT6797 iDVFS I2C6 native FIFO transport |
| Device variant | Hardware-free arm64 QEMU; no Gemini device action |
| Date(s) | 2026-08-19 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 6 blocker B2 |

## Question or hypothesis

Can the exact production MT6797 I2C6 path prove, without a physical I2C
transfer, that one two-byte write is programmed as one FIFO transaction and
that success, timeout, NACK, arbitration loss, unexpected IRQ state, retry,
and transaction-window exit failures have exact one-attempt accounting?

The falsifiable claim is limited to the controller/software contract. It does
not claim that a DA921x accepts a write, that a rail is writable, or that a
same-value write is safe to execute.

## Provenance and environment

- Functional parent source commit:
  `21728a382e771d7e11b4b9bf0392037002ffd572`.
- Parent kernel release: `7.1.3-gemini-i2c6-fwtxn`.
- Parent patchset SHA-256:
  `64c9e7cbd5bd292f4f0b02f8cf06f3713724c67bdb1451485aed2c46dbbf5d45`.
- B1 parent evidence:
  [firmware-writer transaction-window runtime](../2026-08-18-mainline-i2c6-firmware-writer-transaction-window/results/runtime-attempt-1-success-20260819.txt).
- Build backend: Buildbox only; no native VM kernel build.
- Planned execution backend: isolated `qemu-system-aarch64` KUnit boot using
  only the fetched Buildbox `Image`.
- Boot path and target slot: none; this experiment must not construct or
  install a boot candidate.

## Safety assessment

This experiment is hardware-free. Its test message uses fake address `0x2a`
and sentinel bytes `[0xa5, 0x5a]` inside an in-memory fixture. It must not map
I2C MMIO, write a START register, register a physical adapter or client, name a
DA921x address, expose a runtime trigger, access the Gemini, construct a boot
container, write `boot2`, request a regulator state, or admit CPU8/CPU9.

The implementation must factor the production planning and result-accounting
logic so KUnit executes the same helpers used by `i2c-mt65xx.c`; a detached
reference model is insufficient. KUnit-only hooks must disappear when the
focused test option is disabled.

## Associated code

- [`DESIGN.md`](DESIGN.md) freezes the production-path and test cases.
- [`contract.json`](contract.json) is the machine-readable B2 gate.
- [`scripts/validate.py`](scripts/validate.py) validates the frozen design and
  representative unsafe mutations without touching hardware.
- [`scripts/source_edits.py`](scripts/source_edits.py) applies the deterministic
  production and KUnit source phases to a bounded temporary source view.
- [`scripts/validate_source.py`](scripts/validate_source.py) proves the edited
  source remains coupled to the production path and hardware-free test seam.
- [`scripts/validate_tool.py`](scripts/validate_tool.py) validates the editor,
  profile, Buildbox generator, patch validator, and unsafe workflow mutations.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox) generates and
  verifies two normal format-patches from the pinned managed source state.
- [`scripts/validate_patches.py`](scripts/validate_patches.py) enforces the
  exact patch inventory, changed paths, missing synthetic sign-off, and
  executable-test prohibitions.
- [`scripts/test-patch-validator.py`](scripts/test-patch-validator.py) tests
  that validator against nine decision-changing normal-patch mutations.
- [`scripts/run-kunit-qemu`](scripts/run-kunit-qemu) verifies the fetched
  package and launches a bounded network-free arm64 virtual machine.
- [`scripts/classify-kunit.py`](scripts/classify-kunit.py) requires the exact
  12-case KTAP pass before the later runtime evidence can close B2.
- [`scripts/test-kunit-classifier.py`](scripts/test-kunit-classifier.py)
  exercises the classifier against eight decision-changing log mutations.
- [`results/design-freeze-20260819.txt`](results/design-freeze-20260819.txt)
  records the initial design validation.
- [`results/source-tool-validation-20260819.txt`](results/source-tool-validation-20260819.txt)
  records the deterministic editor/profile validation before patch generation.

Run the design validator from the repository root:

```sh
python3 experiments/2026-08-19-mainline-i2c6-write-transport-kunit/scripts/validate.py
```

## Procedure

1. Freeze the exact fake message, programmed values, result classes, retry
   contract, lease-result precedence, prohibited effects, and exit criteria.
2. Add one production-path refactor/fix patch and one default-off KUnit patch
   in canonical order, plus a focused manifest profile and fragment.
3. Validate source coupling, configuration isolation, patch application,
   coding style, and decision-changing mutations.
4. Commit and push the clean source, then build only with
   `./scripts/build-kernel --backend buildbox` using the focused B2 profile.
5. Fetch the validated package and run its exact `Image` under isolated arm64
   QEMU. Require every named KUnit case to pass with zero failure or skip.
6. Record whether B2 closes. Do not build a device candidate or perform a
   physical I2C transfer in this experiment.

## Observations

Read-only review of the exact parent production source established:

- MT6797 I2C6 has an eight-byte FIFO, so a two-byte write selects PIO and
  leaves `I2C_CONTROL_DMA_EN` clear;
- the production path programs `TRANSFER_LEN = 2`, `TRANSAC_LEN = 1`, and
  writes both message bytes to `DATA_PORT` before START;
- the adapter is initialized with one retry, while `__i2c_transfer()` retries
  `-EAGAIN` through `adap->retries`, so a future no-retry operation must prove
  retries are zero only during its locked call and restored afterward; and
- the current lease cleanup uses `if (!ret && lease_ret)` even though success
  is the positive message count. A failed exit check therefore cannot replace
  a positive success result. B2 must correct and test that accounting before
  any write candidate can be reviewed.

The frozen design validator passes and rejects twelve unsafe contract
mutations.
The deterministic two-phase source editor, exact KUnit-only profile extension,
generated production/helper bodies, and 12-case suite contract also pass their
tool validator, which also covers the first-class Buildbox generate/fetch
transport, generator, patch validator, QEMU runner, and classifier and rejects
twenty source/tool/workflow mutations; the patch validator independently
rejects nine patch mutations. No kernel source, build, QEMU run, device, or
hardware state has yet been changed by this experiment.

## Analysis

The existing FIFO code is compatible with the required message shape, but
source inspection alone does not close B2. The retry and lease-result findings
show why a compile-only or message-layout-only test would be too weak: the
same physical request could otherwise execute twice after arbitration loss,
race an unrelated adapter user while retries are overridden, or be reported as
successful after the transaction-window exit gate failed.

The smallest decisive proof is a hardware-free KUnit suite coupled to the
production helper boundaries. It must capture the two FIFO bytes in order,
exercise every result class, prove one root-adapter lock around one underlying
call with retries forced to zero, prove retry restoration and one matching
unlock on every result, and prove negative lease results override only
nonnegative transport results.

## Conclusion

`confirmed` for the design gap: B2 requires exact FIFO-plan, no-retry, and
lease-result accounting proof, not another Gemini boot.

`inconclusive` for B2 itself until the production-coupled patches compile on
Buildbox and every focused KUnit case executes successfully in isolated QEMU.
Every DA921x write and CPU8/CPU9 admission remains closed.

## Follow-up

The authoritative next action remains
[Roadmap Gate 6](../../docs/ROADMAP.md#6-prove-one-bounded-writable-operation).
After B2 closes, update the bounded no-op review's blocker ledger and perform a
fresh explicit pre-write review. Do not infer permission to execute the
same-value write from this hardware-free transport proof.
