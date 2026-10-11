# Phase C compile 30: proposal 0172, the data phase inside the channel grant

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `da50d8b670cbbd1455a2aeca54eeeffa6e61f6f2`, clean, the revision
  carrying the runtime 25 result and proposal 0172.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 671 selected patches: the compile-29
  selection plus proposal 0172 after 0171, in canonical order; patchset
  `22baf81f…`, source `be41c068…` unchanged; the package provenance series equals
  the selected series (0172 present).
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend after the
  existing-job, clean-input, capacity, lock and free-space checks; generated
  `2026-10-11T15:43:03Z`, job validated `2026-10-11T15:43:29Z`.
- Job: `da50d8b670cbbd1455a2aeca54eeeffa6e61f6f2-mt6797-a53-wifi-phase-b-compile-m0`
  (record and log under the managed `jobs/` directory on Buildbox-1; job log SHA-256
  `db0c54b7…`).
- Validated package inventory SHA-256: `2b219cf38949bbdf8e848e5e7f8f7837338acc4c4d3428e219c1dacfe457fd65`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- `kernel.config` SHA-256: `975f8703…`, identical to compiles 19 to 29.
- `Image.gz` SHA-256: `e6dbc40a61bc62269aac7c28357df43c272416c8a5ce0c01822edf8d2552cfd6`
  (decompressed 16025608 bytes: 65536 bytes more than compiles 19 to 29, which all
  decompressed to 15960072; the image's section alignment moved by one 64 KiB step
  with 0172's added code; the configuration is unchanged).

The board DT is unchanged (123 DTBs, checksums passed at validation; the built board
DT digest `07b097d5…` equals compiles 24 to 29). Warnings against the documented
baseline: exactly the same two pre-existing non-driver lines (the trailing-whitespace
note while applying v7.1.3 patch 0261 and the unused-function warning in
`kernel/cpu.c`); zero MT6797 driver warnings.

## Candidate 25 composition (waits for the custodian)

The custodian composes candidate 25 privately with the reviewed composer at the pushed
head: this package with candidate 24's RAM root byte-identical, the same board DT and
kernel configuration; only the kernel image, boot image and padded partition change
(the boot image grows with the kernel image). The current boot2 content is candidate
24 (`35014d84…`) and the known-good stock boot `c49e4d59…`, both reverified by the
custodian before installation; the runtime-26 and deployment-25 bindings follow the
committed receipt. No candidate, deployment or device step has run. No
replay-protection or operational claim follows from this build.
