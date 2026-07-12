# Experiments and reverse engineering

This directory contains reproducible investigations of the Gemini PDA and its
software-visible hardware. The write-up, probe code, and sanitized evidence for
an investigation stay together so another contributor can repeat or challenge
the result.

## Index

- [2026-07-11 Gemian hardware inventory](2026-07-11-gemian-hardware-inventory/README.md)
  — read-only whole-device discovery baseline and reusable collector.
- [2026-07-11 Gemian firmware inventory](2026-07-11-gemian-firmware-inventory/README.md)
  — private vendor-firmware capture, sanitized hashes, and load evidence.
- [2026-07-11 Gemian hardware-userspace inventory](2026-07-11-gemian-hardware-userspace-inventory/README.md)
  — Android HAL, vendor library/daemon, and native compatibility-boundary map.

## Layout

Create a directory named with the start date and a short subject:

```text
experiments/2026-07-11-uart-identification/
  README.md
  scripts/       collection, decoding, and analysis helpers
  src/           purpose-built probe or test source
  fixtures/      small redistributable inputs needed for tests
  results/       small sanitized logs, tables, or summaries
```

Copy `experiments/TEMPLATE.md` to the new directory as `README.md`. Omit unused
subdirectories. Code must state its dependencies and default to read-only or
dry-run behavior. A command that can modify hardware must require an explicit
target and opt-in flag.

## Evidence policy

- Keep raw private captures outside Git. Commit only the smallest sanitized
  evidence needed to support the result.
- Redact serial numbers, IMEI values, identifying MAC addresses, keys,
  credentials, calibration blobs, and user data.
- Do not commit firmware, partition images, NVRAM, proprietary source or
  documents, or artifacts without verified redistribution rights.
- Hash externally retained evidence when its identity matters, but do not
  publish a hash if it could identify a person or device.
- Record failures, negative results, and ambiguity. They prevent repeated unsafe
  work and are valid outcomes.

When an experiment establishes a durable fact, summarize it in
`docs/hardware/` and link back to the experiment. When it changes runtime support,
update `docs/HARDWARE_SUPPORT.md` with the exact evidence. When it produces a
kernel change, export the logical commit into `patches/` and link all three.
