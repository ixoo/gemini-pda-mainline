# Repository instructions

## Purpose

This repository is the reproducibility and patch layer for bringing the Gemini
PDA to upstream Linux. Do not vendor a Linux tree here. Store reviewable patches,
configuration, safe tooling, hardware knowledge, and reproducible evidence.

## Before changing anything

- Read `docs/SAFETY.md`, `CONTRIBUTING.md`, and `docs/ARCHITECTURE.md`.
- For kernel work, also read `docs/KERNEL_WORKFLOW.md`.
- Preserve unrelated user changes; the worktree may be intentionally dirty.
- Treat historical or vendor material as evidence, not code to copy.

## Required workflow

- Pin upstream inputs in `kernel/manifest.json`.
- Store `git format-patch` files below `patches/` and order them in
  `patches/series`; keep one logical upstream change per patch.
- Add required kernel options to `configs/gemini.fragment`.
- Build with `./scripts/dev-vm build-kernel`. Generated Linux sources, builds,
  and artifacts belong in the VM, not Git.
- A compile result is not hardware support. Update `docs/HARDWARE_SUPPORT.md`
  only from reproducible evidence on a named device and exact revision.

## Hardware and reverse engineering

- Record durable hardware facts in `docs/hardware/` with variant, source,
  confidence, method, contradictions, and links to supporting experiments.
- Put each investigation in `experiments/<date>-<name>/`; start from
  `experiments/TEMPLATE.md` and keep its scripts/source beside the write-up.
- Distinguish observation from inference. Record negative and inconclusive
  results; never silently promote a guess to a fact.
- Redact serials, IMEI values, keys, calibration data, credentials, and personal
  identifiers. Do not commit firmware, partition dumps, proprietary source or
  documents, or other material without verified redistribution rights.

## Safety and validation

- Never add a default action that writes the preloader, NVRAM, GPT, or an entire
  device. Hardware-writing operations require an explicit target and opt-in.
- Prefer read-only probes, bounded operations, and dry-run defaults.
- Run `bash -n` and ShellCheck for shell changes, `git diff --check`, the relevant
  kernel checks, and the smallest meaningful VM build. Document what was and was
  not tested.
