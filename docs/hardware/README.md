# Hardware knowledge base

This directory is the canonical record of durable Gemini PDA hardware facts. It
expands the concise [hardware support matrix](../HARDWARE_SUPPORT.md) without
conflating component identity with Linux runtime support.

Detailed investigations, candidate chronology, scripts, raw samples, and
negative branches belong in the [experiment index](../../experiments/README.md).
A hardware document should summarize only the current conclusion and link to
the experiments that support or challenge it.

## Inventory

| Document | Scope |
| --- | --- |
| [Gemian hardware baseline](gemini-gemian-baseline.md) | Sanitized read-only observations from the working vendor kernel on the named unit. |
| [DA921x, I2C6, and Cortex-A72](da921x-i2c6-a72.md) | Current regulator/transport/CPU boundary, evidence limits, and safety invariants. |
| [MT6797 live resource map](mt6797-live-resource-map.md) | Register, IRQ, clock, rail, storage, display, GPU, connectivity, and USB resources mapped to Linux boundaries. |
| [MT6797 thermal observation](mt6797-thermal-observation.md) | Aggregate temperature semantics, shared bank ownership, precision and freshness limits. |
| [Gemini keyboard](keyboard.md) | AW9523 matrix wiring, physical keymap, and kernel/userspace mapping boundary. |
| [Vendor kernel ABI](vendor-kernel-abi.md) | Private interfaces used by the working stack and their standard Linux replacements. |
| [Vendor userspace](vendor-userspace.md) | Android HALs, services, libraries, compatibility bridges, and migration implications. |
| [Firmware boundary](firmware.md) | Installed firmware evidence, licensing/redistribution limits, and protected exclusions. |
| [Boot graphics](boot-graphics.md) | Retained LK logo-container format, complete slot geometry, Gemian Yamui splash, and modification safety boundary. |
| [Partition backup boundary](partition-backup.md) | Safe private capture policy, checksums, naming, permissions, and non-public raw state. |

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
- confirmed facts tied to a source or experiment;
- inference and disputed claims labeled explicitly;
- independently established register, bus, address, IRQ, GPIO, clock,
  regulator, memory-map, or protocol details;
- firmware and calibration boundaries;
- safety constraints and known destructive operations;
- unresolved questions and discriminating observations;
- a concise evidence index.

Use a compact fact table when it helps:

| Claim | Variant | Confidence | Evidence | Last verified |
| --- | --- | --- | --- | --- |
| Example claim | Wi-Fi + LTE | `inferred` | `experiments/...` | YYYY-MM-DD |

Confidence terms:

| Level | Meaning |
| --- | --- |
| `reported` | A secondary source states it; it has not been independently checked. |
| `inferred` | Evidence favors it, but plausible alternatives remain. |
| `observed` | It was directly measured or read on named hardware. |
| `confirmed` | An explicit method reproduced consistent evidence within its stated scope. |

Confidence always applies to the exact scope stated. Repetition inside one
invocation is not cross-boot repeatability; one named unit is not every
hardware variant.

## What does not belong here

Keep these in the associated `experiments/<date>-<name>/` directory:

- candidate-by-candidate narratives;
- build, package, and partition hashes;
- complete register dumps or sample streams;
- mutation-test output and validator transcripts;
- temporary scripts and one-shot interfaces;
- abandoned hypotheses and superseded result branches.

The durable hardware document should retain the conclusion, the uncertainty,
the unresolved discriminators, and links sufficient to find those records.

## Provenance rules

For each nontrivial claim, record enough information to reassess it:

- exact device variant, with personal identifiers removed;
- evidence type and acquisition method;
- public source revision, kernel/vendor-tree path and commit, or experiment ID;
- observation date and investigator;
- uncertainty, assumptions, and contradictory evidence.

Vendor trees, binaries, and proprietary documents may be lawful research
inputs, but do not copy unlicensed code or documents into this repository.
Record independently established facts and cite the source boundary.

Do not link public documentation to private raw captures, credentials,
absolute local paths, serials, IMEI values, keys, calibration data, or
unreviewed proprietary artifacts.

## Relationship to support status

Knowing that a component exists does not mean Linux supports it. Runtime and
upstream states remain in [the support matrix](../HARDWARE_SUPPORT.md). A
support state changes only when a linked experiment identifies the hardware,
kernel and profile, procedure, repetition count, sanitized evidence, and known
negative space.
