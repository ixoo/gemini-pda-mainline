# Phase C compile 33: proposals 0175 and 0176, the recorded regulatory stop and the delivered beacons

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `94e9c89091a12c1d6249cc6a27cf0a0c3bc07c94`, clean, the revision
  carrying the runtime 28 result, proposals 0175 and 0176 and the classifier's
  terminal and beacon records; one job, the existing entry point and profile, no
  profile change. The driver files built are the reviewed ones (`mac.c` SHA-256
  `5d136f4f…`, `action-frame.h` SHA-256 `51a19415…` in the authoring tree whose
  series reproduces them).
- Profile: `mt6797-a53-wifi-phase-b-compile`, 675 selected patches: the compile-32
  selection plus 0175 and 0176 after 0174, in canonical order; patchset
  `a7631d7be302482ad91dfc7c7129ab031d959d37848365666cf36e2a003a7fce`, source
  `be41c068…` unchanged; the package provenance series equals the selected series.
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend after the
  existing-job, clean-input, capacity, lock and free-space checks; generated
  `2026-10-12T00:26:03Z`, job completed and validated `2026-10-12T00:26:29Z`.
- Job: `94e9c89091a12c1d6249cc6a27cf0a0c3bc07c94-mt6797-a53-wifi-phase-b-compile-m0`
  (record and log under the managed `jobs/` directory on Buildbox-1; job log SHA-256
  `80dfba2e5f31b89fb02f960fe08b0b2c8e374c7b8236ee51dad0266e834f0637`).
- Validated package inventory SHA-256: `bf244275d57b01884b738ec4d4db9b19977b1143b5f2439077488d82428c8302`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- `kernel.config` SHA-256: `975f8703…`, identical to compiles 19 to 32.
- `Image.gz` SHA-256: `4c213d67d3caa157d633a8dc6d066cbbfae537e90a5334b3e2dec1cfbb1e4304`
  (6648311 bytes; decompressed 16025608 bytes, one 64 KiB alignment above compiles 31
  and 32 with the two proposals' code, the size compile 30 had; the configuration is
  unchanged).

The board DT is unchanged (123 DTBs, checksums passed at validation; the built board
DT digest `07b097d5…` equals compiles 24 to 32). Warnings against the compile-32 job
log: identical: the two pre-existing non-driver lines (the trailing-whitespace note
while applying v7.1.3 patch 0261 and the unused-function warning in `kernel/cpu.c`)
and the same fourteen pre-existing dtc `ranges_format` notes on the SoC DT include;
zero MT6797 driver warnings.

## Candidate 28 composition (waits for the custodian)

The custodian composes candidate 28 privately with the reviewed composer, whose
`COMMIT` and `PACKAGE` pins now name this input and package; the RAM root, board DT
and kernel configuration are expected byte-identical to candidate 27 (`449832a3…`,
`25ab60f4…`, `975f8703…`). No deployment or device step has run. No replay-protection
or operational claim follows from this build.
