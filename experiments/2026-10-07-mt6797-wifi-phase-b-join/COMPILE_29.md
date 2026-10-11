# Phase C compile 29: proposal 0171, the keyed descriptor variant of the directed Action class

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `1057b6b5a35962737b7ddad6bd37989ddc96949e`, clean, the revision
  carrying the runtime 24 result and proposal 0171.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 670 selected patches: the compile-28
  selection plus proposal 0171 after 0170, in canonical order; patchset
  `d7127307…`, source `be41c068…` unchanged; the package provenance series equals
  the selected series (0171 present).
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend after the
  existing-job, clean-input, capacity, lock and free-space checks; generated
  `2026-10-11T13:25:07Z`, job validated `2026-10-11T13:25:33Z`.
- Job: `1057b6b5a35962737b7ddad6bd37989ddc96949e-mt6797-a53-wifi-phase-b-compile-m0`
  (record and log under the managed `jobs/` directory on Buildbox-1; job log SHA-256
  `da69a9fe…`).
- Validated package inventory SHA-256: `0ce04178354bb0d4f6fdbf2b0f75bf3804817df73865bec26b1e5b552705e4d1`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- `kernel.config` SHA-256: `975f8703…`, identical to compiles 19 to 28.
- `Image.gz` SHA-256: `f1b6778ac39577254617c4f2aa20cce55af5b7a60b0c81209ae7e35c0966ce43`
  (decompressed 15960072 bytes, the same as compiles 19 to 28).

The board DT is unchanged (123 DTBs, checksums passed at validation; the built board
DT digest `07b097d5…` equals compiles 24 to 28). Warnings against the documented
baseline: exactly the same two pre-existing non-driver lines (the trailing-whitespace
note while applying v7.1.3 patch 0261 and the unused-function warning in
`kernel/cpu.c`); zero MT6797 driver warnings.

## Candidate 24 composition (waits for the custodian)

The custodian composes candidate 24 privately with the reviewed composer at the pushed
head: this package with candidate 23's RAM root byte-identical, the same board DT and
kernel configuration; only the kernel image, boot image and padded partition change.
The current boot2 content is candidate 23 (`1b07a2bb…`) and the known-good stock boot
`40295547…`; the runtime-25 and deployment-24 bindings follow the committed receipt.
No candidate, deployment or device step has run. No replay-protection or operational
claim follows from this build.
