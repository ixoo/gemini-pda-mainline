# Experiment: legacy DA921x driver and binding contract

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-29-da921x-legacy-driver-contract` |
| Status | `completed; Gate 1 contract specified and statically validated` |
| Subsystem | Regulator, I2C, and Devicetree design |
| Device variant | Named Gemini PDA unit; no device access in this work |
| Date(s) | 2026-07-29 |
| Investigator(s) | Codex |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Can the proven fixed DA9213/DA9214/DA9215-compatible tuple be expressed as a
reviewable, fail-closed Linux driver and binding contract in which every probe
transaction is statically enumerable and no lifecycle path writes regulator
state?

## Provenance and environment

- Repository baseline: `ff8bd3f` (`Repair profile-series invariant`).
- Kernel baseline: Linux 7.1.3 pinned by `kernel/manifest.json`.
- Hardware evidence:
  [Gauss exact board-contract result](../2026-07-28-da9214-gauss/README.md).
- Durable boundary:
  [Gemini DA921x, I2C6, and Cortex-A72](../../docs/hardware/da921x-i2c6-a72.md).
- Manufacturer reference: Renesas, *DA9213, DA9214, and DA9215
  Multi-Phase 5 A/Phase DC-DC Buck Converter*, R16DS0598EJ0361 Rev.03.61,
  2025-11-03.
- Upstream comparison: Linux 7.1.3 `da9211-regulator.c`,
  `da9211-regulator.h`, and `dlg,da9211.yaml`.
- Historical patches 0096 and 0104–0110 were inspected only as rejected
  evidence. No code or policy was copied from them.
- Boot path, target partition, kernel configuration, toolchain, and package:
  not applicable.

## Safety assessment

This work is repository-only. It does not access the device, build or package
a kernel, write a register, touch storage, install a boot candidate, request a
CPU, or reboot anything.

The contract is deliberately narrower than a regulator provider. It permits
only fixed one-byte-pointer plus one-byte-read observations, registers no
regulator, and gives failed probe, unbind, shutdown, suspend, and resume zero
hardware transactions.

## Associated code

- `DESIGN.md`: driver, binding, ownership, error, and lifecycle contract.
- `probe-contract.json`: machine-readable enumeration of all permitted probe
  transactions and forbidden lifecycle/provider behavior.
- `scripts/validate-contract.py`: rejects drift from the exact 14-read,
  zero-register-data-write boundary.

Validation requires only Python 3:

```sh
python3 experiments/2026-07-29-da921x-legacy-driver-contract/scripts/validate-contract.py
```

No privilege, VM, network, or hardware access is required.

## Procedure

1. Compare the exact Gauss tuple with the public non-A
   DA9213/DA9214/DA9215 direct-address register model.
2. Compare that model with the upstream DA9211/A-family page-selector and
   device-ID probe.
3. Define a separate programming-model compatible with no fallback to the
   incompatible probe.
4. Define fixed primary and page-2 addresses in the binding.
5. Enumerate two exact passes of the seven proven reads.
6. Define the provider, consumer, IRQ, error-cleanup, unbind, shutdown,
   suspend, and resume boundaries.
7. Run the machine-readable contract validator and repository documentation
   checks.

## Observations

- The non-A manufacturer register model documents direct page-2/page-3 I2C
  access through the adjacent address and does not require a page-selector
  write for the proven tuple.
- The current upstream DA9211-family driver uses a paged regmap and device ID
  at `0x201`, which does not match the proven Gemini path.
- Gauss already established the only transaction shape and values allowed by
  this contract: two passes of seven fixed combined pointer/read transfers at
  `0x69` and `0x68`.
- A Linux I2C client can describe and claim a named secondary address without
  issuing bus traffic.

## Analysis

A separated identification driver avoids all previously rejected selector,
regmap, device-ID, provider, and consumer behavior. Requiring raw I2C and one
locked `__i2c_transfer()` call per combined two-message observation preserves
the exact proven controller shape without the adapter retry loop. Immediate
comparison makes every failure trace a prefix of one fixed table.

The `-legacy` compatibles are an intentional integration distinction for the
non-A programming model. They prevent accidental fallback into the currently
ambiguous upstream compatible. The name can change through upstream review,
but the programming-model separation and zero-write behavior cannot.

The contract represents DA9213, DA9214, and DA9215 topology explicitly, while
the first board enablement selects only DA9214. The tuple is still a board
contract rather than a unique silicon identity. A successful future bind
therefore cannot be used as provider, voltage, rail-ownership, suspend, or A72
evidence.

## Conclusion

`confirmed` for the Roadmap Gate 1 design question. The driver and binding
contract is reviewable from public manufacturer and upstream interfaces, all
successful probe transactions are enumerated, all failure traces are strict
prefixes, and every non-probe lifecycle path has zero transactions.

This is a specification result, not an implementation, compile, or hardware
support result.

## Follow-up

Proceed to [Roadmap Gate 2](../../docs/ROADMAP.md#2-implement-and-validate-an-isolated-profile):
implement the binding, identification-only driver, board node, isolated
profile, and pre-boot zero-write validators as separate canonical patches.
Do not boot a candidate until all Gate 2 offline checks and reproducibility
requirements pass.
