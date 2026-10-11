# Phase C compile 27: proposal 0169, the group-data class by the declared broadcast entry

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `85cbc78f50ef9cd443bbff7a068121659475487c`, clean, the revision
  carrying the runtime 22 result and proposal 0169.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 668 selected patches: the compile-26
  selection plus proposal 0169 after 0168, in canonical order; patchset
  `68c775b9…`, source `be41c068…` unchanged; the package provenance series equals
  the selected series (0169 present).
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend after the
  existing-job, clean-input, capacity, lock and free-space checks; generated
  `2026-10-11T01:04:51Z`, job validated `2026-10-11T01:05:16Z`.
- Job: `85cbc78f50ef9cd443bbff7a068121659475487c-mt6797-a53-wifi-phase-b-compile-m0`
  (record and log under the managed `jobs/` directory on Buildbox-1; job log SHA-256
  `db4dfa85…`).
- Validated package inventory SHA-256: `d1cbc042126cb6af3964af0178ea635bc8e4a1287e50193a0eb1a262680e0992`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- `kernel.config` SHA-256: `975f8703…`, identical to compiles 19 to 26.
- `Image.gz` SHA-256: `63c72b521903eaad831241073fcf53a91c4011daaefac66e19bbaa0c67e38cc4`
  (decompressed 15960072 bytes, the same as compiles 19 to 26).

The board DT is unchanged (123 DTBs, checksums passed at validation; the built board
DT digest `07b097d5…` equals compiles 24 to 26). Warnings against the documented
baseline: exactly the same two pre-existing non-driver lines (the trailing-whitespace
note while applying v7.1.3 patch 0261 and the unused-function warning in
`kernel/cpu.c`); zero MT6797 driver warnings.

## Candidate 22 composition (waits for the custodian)

The custodian composes candidate 22 privately with the reviewed composer at the pushed
head: this package with candidate 21's RAM root byte-identical, the same board DT and
kernel configuration; only the kernel image, boot image and padded partition change.
The current boot2 content is candidate 21 (`79cde346…`) and the known-good stock boot
`720fcced…`; the runtime-23 and deployment-22 bindings follow the committed receipt.
No candidate, deployment or device step has run. No replay-protection or operational
claim follows from this build.
