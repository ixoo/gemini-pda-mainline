# Phase C compile 26: proposal 0168, the clear broadcast Action class discarded

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `f53636a371d467702054e90cbbb065933f17aa34`, clean, the revision
  carrying the runtime 21 result, proposal 0168 and the classifier corrections.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 667 selected patches: the compile-25
  selection plus proposal 0168 after 0167, in canonical order; patchset
  `43894449…`, source `be41c068…` unchanged; the package provenance series equals
  the selected series (0168 present).
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend after the
  existing-job, clean-input, capacity, lock and free-space checks; generated
  `2026-10-11T00:04:38Z`, job validated `2026-10-11T00:05:04Z`.
- Job: `f53636a371d467702054e90cbbb065933f17aa34-mt6797-a53-wifi-phase-b-compile-m0`
  (record and log under the managed `jobs/` directory on Buildbox-1; job log SHA-256
  `44eedf06…`).
- Validated package inventory SHA-256: `dd35c1d2d2026e6192a6d82024ad04311c4375252bf075fcb24c1c27bfbc79a4`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- `kernel.config` SHA-256: `975f8703…`, identical to compiles 19 to 25.
- `Image.gz` SHA-256: `19f6a2cf561bb3125765a83ae28f1128634ea7bb4577482a0133fe2a4ff6a3cf`
  (decompressed 15960072 bytes, the same as compiles 19 to 25).

The board DT is unchanged (123 DTBs, checksums passed at validation; the built board
DT digest `07b097d5…` equals compiles 24 and 25). Warnings against the documented
baseline: exactly the same two pre-existing non-driver lines (the trailing-whitespace
note while applying v7.1.3 patch 0261 and the unused-function warning in
`kernel/cpu.c`); zero MT6797 driver warnings.

## Candidate 21 composition (waits for the custodian)

The custodian composes candidate 21 privately with the reviewed composer at the pushed
head: this package with candidate 20's RAM root byte-identical, the same board DT and
kernel configuration; only the kernel image, boot image and padded partition change.
The current boot2 content is candidate 20 (`d01f3304…`) and the stock boot
`a2265c06…`; the runtime-22 and deployment-21 bindings follow the committed receipt.
No candidate, deployment or device step has run.
