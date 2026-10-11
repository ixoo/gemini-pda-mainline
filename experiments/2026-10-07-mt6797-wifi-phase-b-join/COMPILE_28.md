# Phase C compile 28: proposal 0170, the key command's credit ownership and terminal path

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `c9781bea0e68f495bec593e79dbc0689b0f3076c`, clean, the revision
  carrying the runtime 23 result and proposal 0170 (the later fixture-only commit
  14031445 changes no kernel input).
- Profile: `mt6797-a53-wifi-phase-b-compile`, 669 selected patches: the compile-27
  selection plus proposal 0170 after 0169, in canonical order; patchset
  `42bfd4b9…`, source `be41c068…` unchanged; the package provenance series equals
  the selected series (0170 present).
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend after the
  existing-job, clean-input, capacity, lock and free-space checks; generated
  `2026-10-11T02:42:46Z`, job validated `2026-10-11T02:43:12Z`.
- Job: `c9781bea0e68f495bec593e79dbc0689b0f3076c-mt6797-a53-wifi-phase-b-compile-m0`
  (record and log under the managed `jobs/` directory on Buildbox-1; job log SHA-256
  `c6931ce0…`).
- Validated package inventory SHA-256: `4d9372a73695b57903d0e0c02232d07b92c19e2c7db6f7aed72354ee9282f34a`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- `kernel.config` SHA-256: `975f8703…`, identical to compiles 19 to 27.
- `Image.gz` SHA-256: `d92a5387f860fc06afc7c7e4fa0b648a0924ded8af95de6c91127bc09b8584cd`
  (decompressed 15960072 bytes, the same as compiles 19 to 27).

The board DT is unchanged (123 DTBs, checksums passed at validation; the built board
DT digest `07b097d5…` equals compiles 24 to 27). Warnings against the documented
baseline: exactly the same two pre-existing non-driver lines (the trailing-whitespace
note while applying v7.1.3 patch 0261 and the unused-function warning in
`kernel/cpu.c`); zero MT6797 driver warnings.

## Candidate 23 composition (waits for the custodian)

The custodian composes candidate 23 privately with the reviewed composer at the pushed
head: this package with candidate 22's RAM root byte-identical, the same board DT and
kernel configuration; only the kernel image, boot image and padded partition change.
The current boot2 content is candidate 22 (`419797dd…`) and the known-good stock boot
`89d49b95…`; the runtime-24 and deployment-23 bindings follow the committed receipt.
No candidate, deployment or device step has run. No replay-protection or operational
claim follows from this build.
