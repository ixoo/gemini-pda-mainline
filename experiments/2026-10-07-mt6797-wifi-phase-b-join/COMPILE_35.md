# Phase C compile 35: proposal 0178, the LLC-mismatch group variant discarded inside the data phase

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `8ccf249c26ddd630fdd7000ca8cf2e41410213ac`, clean, the revision
  carrying the runtime 30 result, proposal 0178 and the classifier's LLC-discard
  records; one job, the existing entry point and profile, no profile change. The
  driver files built are `mac.c` SHA-256 `e9882ff1…` and `data-rx.h` SHA-256
  `fa65a7e4…` (`group-data.h` `7c0d05ea…`, `action-frame.h` `51a19415…` unchanged).
  The following commit 96fc35e2 recast proposal 0178's comments and message as
  unmeasured inference after the custodian's review; its two driver files
  (`mac.c` `5fce99d6…`, `data-rx.h` `411b33f8…`) differ from the built ones in
  comments only: with comments stripped and blank lines removed both pairs hash
  identically (`mac.c` `231b9e71…`, `data-rx.h` `56b3cf23…`). The compiled code is
  therefore the reviewed code; the built input's prose is the uncorrected one.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 677 selected patches: the compile-34
  selection plus 0178 after 0177, in canonical order; patchset
  `becebc6fc44ef50fe2fe10599bca06dde0d8b673500af6a5c6e65bc7e2e5b72b`, source
  `be41c068…` unchanged; the package provenance series equals the selected series.
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend after the
  existing-job, clean-input, capacity, lock and free-space checks; generated
  `2026-10-12T01:48:32Z`, job completed and validated `2026-10-12T01:48:58Z`.
- Job: `8ccf249c26ddd630fdd7000ca8cf2e41410213ac-mt6797-a53-wifi-phase-b-compile-m0`
  (record and log under the managed `jobs/` directory on Buildbox-1; job log SHA-256
  `f68eabd6713eee62f9bcbb9d47a895d6bdcceecfb1a880f3f66a34c05c77c71e`).
- Validated package inventory SHA-256: `bfa7516aeeb5d0f3e28c2972631d5aae40c83dbe7c5bbd962b2163d42c301c98`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- `kernel.config` SHA-256: `975f8703…`, identical to compiles 19 to 34.
- `Image.gz` SHA-256: `7258b7cbfc2d4bfe64bb56f82efed2772364330a382611516c6f71809a5c9276`
  (6648105 bytes; decompressed 15960072 bytes, the size of compiles 31, 32 and 34; the
  configuration is unchanged).

The board DT is unchanged (123 DTBs, checksums passed at validation; the built board
DT digest `07b097d5…` equals compiles 24 to 34). Warnings against the compile-34 job
log: identical: the two pre-existing non-driver lines (the trailing-whitespace note
while applying v7.1.3 patch 0261 and the unused-function warning in `kernel/cpu.c`)
and the same fourteen pre-existing dtc `ranges_format` notes on the SoC DT include;
zero MT6797 driver warnings.

The built gate, stated exactly: the LLC-mismatch group variant is discarded under the
data receive delivery gate (data phase open and not ended, both keys installed, no
deauthentication done, cleanup not done); outside it the variant is a refusal as
before; the unicast form is a refusal in every state.

## Candidate 30 composition (waits for the custodian)

The custodian composes candidate 30 privately with the reviewed composer, whose
`COMMIT` pin names the built input 8ccf249c and whose `PACKAGE` pin names this
package; the RAM root, board DT and kernel configuration are expected byte-identical
to candidate 29 (`449832a3…`, `25ab60f4…`, `975f8703…`). No deployment or device step
has run. No replay-protection or operational claim follows from this build.
