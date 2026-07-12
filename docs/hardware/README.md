# Hardware knowledge base

This directory is the canonical record of Gemini PDA hardware facts. It expands
the concise [hardware support matrix](../HARDWARE_SUPPORT.md) without conflating
component identity with runtime support.

## Inventory

- [Gemini PDA Gemian hardware baseline](gemini-gemian-baseline.md) — sanitized,
  read-only observations from the 2019 vendor kernel on one physical device.
- [Firmware boundary](firmware.md) — installed vendor blobs, observed load
  evidence, private-artifact policy, and protected exclusions.
- [Gemian hardware-specific userspace](vendor-userspace.md) — Android HALs,
  MediaTek services/libraries, native compatibility bridges, and mainline
  migration implications.

## What belongs here

Create one focused Markdown document per stable subject, such as a device
variant, boot-chain boundary, SoC block, board bus, connector, power rail, or
peripheral. Prefer durable subject names:

```text
docs/hardware/
  variants.md
  boot-chain.md
  mt6797-clocks.md
  keyboard.md
  usb-c.md
```

A hardware document should contain:

- scope and affected Gemini variants;
- confirmed facts, each tied to a source or experiment;
- inferred or disputed claims, clearly labeled;
- register, bus, address, IRQ, GPIO, clock, regulator, memory-map, or protocol
  details when independently established;
- firmware and calibration boundaries;
- safety constraints and known destructive operations;
- open questions and the next discriminating experiment;
- links to associated experiment code, kernel patches, issues, and upstream
  discussions.

Use a compact fact table where it helps:

| Claim | Variant | Confidence | Evidence | Last verified |
| --- | --- | --- | --- | --- |
| Example claim | Wi-Fi + LTE | inferred | `experiments/...` | YYYY-MM-DD |

Confidence should be one of:

| Level | Meaning |
| --- | --- |
| `reported` | A secondary source states it; not independently checked |
| `inferred` | Evidence suggests it, but alternatives remain |
| `observed` | Directly measured or read from named hardware |
| `confirmed` | Reproduced with an explicit method and consistent evidence |

## Provenance rules

For every nontrivial claim, record enough information to locate and reassess
the evidence:

- exact device variant, with personal identifiers removed;
- evidence type and acquisition method;
- source URL, public document revision, kernel/vendor-tree path and commit, or
  experiment identifier;
- date observed and author/reporter;
- known uncertainty, conflicting evidence, and assumptions.

Vendor trees and proprietary documents may be cited as research inputs when
lawful, but do not copy their code or contents into this repository. Record
independently established facts and an appropriate source reference.

## Relationship to support status

Knowing that a component exists does not mean Linux supports it. Runtime and
upstream states remain in `docs/HARDWARE_SUPPORT.md`. A matrix state changes only
when a linked experiment or test report identifies the device, kernel revision,
patch-series revision, configuration, procedure, repetitions, and redacted
evidence.
