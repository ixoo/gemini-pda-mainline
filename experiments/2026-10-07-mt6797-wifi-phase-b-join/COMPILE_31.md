# Phase C compile 31: proposal 0173, the target's keyed beacon variant skipped

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `c7ba623f503a9f5c8d389155fe230413e0e38e44`, clean, the revision
  carrying the runtime 26 result and proposal 0173; one job, the existing entry point
  and profile, no code or profile change.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 672 selected patches: the compile-30
  selection plus proposal 0173 after 0172, in canonical order; patchset
  `7c9729a8…`, source `be41c068…` unchanged; the package provenance series equals
  the selected series (0173 present).
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend after the
  existing-job, clean-input, capacity, lock and free-space checks; generated
  `2026-10-11T22:42:19Z`, job validated `2026-10-11T22:42:46Z`.
- Job: `c7ba623f503a9f5c8d389155fe230413e0e38e44-mt6797-a53-wifi-phase-b-compile-m0`
  (record and log under the managed `jobs/` directory on Buildbox-1; job log SHA-256
  `6fdf1d1b…`).
- Validated package inventory SHA-256: `bc0f928e233a4acb87d2dbfc07d64da3a3975c784e6235f227257b042eb379ac`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- `kernel.config` SHA-256: `975f8703…`, identical to compiles 19 to 30.
- `Image.gz` SHA-256: `c201224516db9da36c0505e3379dfe494e6691b68a21c0d149cb5e2b9fcb07b3`
  (6647778 bytes; decompressed 15960072 bytes, the size of compiles 19 to 29 again:
  compile 30 had stepped up one 64 KiB alignment with 0172's code and 0173's code
  brings the image back under it; the configuration is unchanged).

The board DT is unchanged (123 DTBs, checksums passed at validation; the built board
DT digest `07b097d5…` equals compiles 24 to 30). Warnings against the documented
baseline: exactly the same two pre-existing non-driver lines (the trailing-whitespace
note while applying v7.1.3 patch 0261 and the unused-function warning in
`kernel/cpu.c`); zero MT6797 driver warnings.

## Candidate 26 composition

The custodian composed candidate 26 privately with the reviewed composer at d148745a
(the pins-only commit): this package with candidate 25's RAM root, board DT and kernel
configuration byte-identical (`449832a3…`, `25ab60f4…`, `975f8703…`); the helper,
supplicant, PSCI and `clk_ignore_unused` preserved; boot image `99d1d9e7…` (12300288
bytes), full padded boot2 `e322e068…`. The receipt is
[results/candidate-26.json](results/candidate-26.json); the runtime-27 and
deployment-26 bindings follow it. No deployment or device step has run. No
replay-protection or operational claim follows from this build.
