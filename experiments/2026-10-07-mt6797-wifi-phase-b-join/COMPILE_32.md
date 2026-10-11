# Phase C compile 32: proposal 0174, the clear broadcast Action class counted without its own cap

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `5ee1f55f4c9bd5e5b94df3218f4d900c1305c6e6`, clean, the revision
  carrying the runtime 27 result, proposal 0174 and the classifier's completion
  binding; one job, the existing entry point and profile, no profile change.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 673 selected patches: the compile-31
  selection plus proposal 0174 after 0173, in canonical order; patchset
  `1dee45cae298d7cd322be57443bfaa9da7f6ca1dbaf1971a713b1557d701722a`, source
  `be41c068…` unchanged; the package provenance series equals the selected series
  (0174 present).
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend after the
  existing-job, clean-input, capacity, lock and free-space checks; generated
  `2026-10-11T23:20:48Z`, job completed and validated `2026-10-11T23:21:14Z`.
- Job: `5ee1f55f4c9bd5e5b94df3218f4d900c1305c6e6-mt6797-a53-wifi-phase-b-compile-m0`
  (record and log under the managed `jobs/` directory on Buildbox-1; job log SHA-256
  `aca018be33d10b56393c92abfd16cab0e95464068ad0a6c79cb7e1702671f34d`).
- Validated package inventory SHA-256: `e9610ba518b49a6f4289cff22a0c0c143309492359c66eeb7e194aee97129240`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- `kernel.config` SHA-256: `975f8703…`, identical to compiles 19 to 31.
- `Image.gz` SHA-256: `1640900b486f851395837c0d64eba97234425972faae3167825fdf0f40ffd0c7`
  (6647739 bytes; decompressed 15960072 bytes, the size of compiles 19 to 29 and 31;
  the configuration is unchanged).

The board DT is unchanged (123 DTBs, checksums passed at validation; the built board
DT digest `07b097d5…` equals compiles 24 to 31). Warnings against the compile-31 job
log: exactly the same two pre-existing non-driver lines (the trailing-whitespace note
while applying v7.1.3 patch 0261 and the unused-function warning in `kernel/cpu.c`)
and the same fourteen pre-existing dtc `ranges_format` notes on the SoC DT include;
zero MT6797 driver warnings.

## Candidate 27 composition (waits for the custodian)

The custodian composes candidate 27 privately with the reviewed composer, whose
`COMMIT` and `PACKAGE` pins now name this input and package; the RAM root, board DT
and kernel configuration are expected byte-identical to candidate 26 (`449832a3…`,
`25ab60f4…`, `975f8703…`). No deployment or device step has run. No replay-protection
or operational claim follows from this build.
