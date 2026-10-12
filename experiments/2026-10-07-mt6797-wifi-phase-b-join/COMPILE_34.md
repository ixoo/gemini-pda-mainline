# Phase C compile 34: proposal 0177, the after-removal group-data variant discarded during the cleanup

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `4cf4b465b9f8e302aba635be893480dc5fe2fbed`, clean, the revision
  carrying the runtime 29 result, proposal 0177 and the classifier's cleanup-discard
  records; one job, the existing entry point and profile, no profile change. The driver
  files built are the reviewed ones (`mac.c` SHA-256 `9ff0ad54…`, `group-data.h`
  SHA-256 `7c0d05ea…`, `action-frame.h` unchanged at `51a19415…` in the authoring
  tree whose series reproduces them).
- Profile: `mt6797-a53-wifi-phase-b-compile`, 676 selected patches: the compile-33
  selection plus 0177 after 0176, in canonical order; patchset
  `64cba9bdfb83cc113a4cd00c51ec192e4e10d1934da9f7f5a14cb924043551fe`, source
  `be41c068…` unchanged; the package provenance series equals the selected series.
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend after the
  existing-job, clean-input, capacity, lock and free-space checks; generated
  `2026-10-12T01:21:28Z`, job completed and validated `2026-10-12T01:21:54Z`.
- Job: `4cf4b465b9f8e302aba635be893480dc5fe2fbed-mt6797-a53-wifi-phase-b-compile-m0`
  (record and log under the managed `jobs/` directory on Buildbox-1; job log SHA-256
  `61477d1e7f634f89c267c75a1b1f2552c3066bfcea53f89d14e9975b0b084cdf`).
- Validated package inventory SHA-256: `f6ef3ead14bf7685705d3da53b6f9c15140c641c644856a030edf2278b88bac4`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- `kernel.config` SHA-256: `975f8703…`, identical to compiles 19 to 33.
- `Image.gz` SHA-256: `e6d0e1f95e47f99709349b5d253fc80a669bf692cb93a21ad696fd14bdaab9e7`
  (6647789 bytes; decompressed 15960072 bytes, one 64 KiB alignment below compile 33,
  the size of compiles 31 and 32; the configuration is unchanged).

The board DT is unchanged (123 DTBs, checksums passed at validation; the built board
DT digest `07b097d5…` equals compiles 24 to 33). Warnings against the compile-33 job
log: identical: the two pre-existing non-driver lines (the trailing-whitespace note
while applying v7.1.3 patch 0261 and the unused-function warning in `kernel/cpu.c`)
and the same fourteen pre-existing dtc `ranges_format` notes on the SoC DT include;
zero MT6797 driver warnings.

The built gate, stated exactly: the after-removal variant is discarded while the
cleanup is requested and not done and `join_key_group == 2`, the state the worker sets
when it submits the group key removal command; the discard therefore does not wait for
that command's credit (one source comment says "submitted and credited"; the state
test is the gate). Before that submission, or after stage 3, the variant is a refusal
as before.

## Candidate 29 composition (waits for the custodian)

The custodian composes candidate 29 privately with the reviewed composer, whose
`COMMIT` and `PACKAGE` pins now name this input and package; the RAM root, board DT
and kernel configuration are expected byte-identical to candidate 28 (`449832a3…`,
`25ab60f4…`, `975f8703…`). No deployment or device step has run. No replay-protection
or operational claim follows from this build.
