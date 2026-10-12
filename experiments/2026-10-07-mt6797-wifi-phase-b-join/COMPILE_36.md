# Phase C compile 36: proposal 0179, the delivered data classes' GROUP_VLD group-1 presence recorded

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `7fa36c01db2deb27b55d0d77bc8279dc62b140b3`, clean, the revision carrying
  the runtime 31 result, the RX replay-boundary review and proposal 0179; one job, the
  existing entry point and profile, no profile change. The driver files built are `mac.c`
  SHA-256 `2d7e5a33…` and `data-rx.h` SHA-256 `6330bac2…` (`group-data.h` `7c0d05ea…`,
  `action-frame.h` `51a19415…` unchanged). This input already carries the reviewed comments
  (the 0178 prose was corrected at 96fc35e2 before this build), so the built driver files
  are the reviewed files; there is no built-versus-corrected split as in compile 35.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 678 selected patches: the compile-35
  selection plus 0179 after 0178, in canonical order; patchset
  `ccf43622f6c6a69fd301fa935b50aa3cd89e774414785a2d9e9d9ab2a9803fdb`, source
  `be41c068…` unchanged; the package provenance series equals the selected series.
- Builder: the managed Buildbox backend, 32 jobs, one heavy build after the clean push;
  job `7fa36c01…-mt6797-a53-wifi-phase-b-compile-m0`, generated
  2026-10-12T11:17:52Z, `hardware_write=none`.
- Package: `521e1ce391a9801ebd7eaf179c98da1fb0928ee4f4168d21ba81673c3aea3511`
  (`linux-7.1.3-gemini-521e1ce3…`), `sha256sums=passed`. Kernel image `Image.gz`
  SHA-256 `ded2f6db15cc14228819080f3f0eb2111662c2e0090f7c1daacb8b46f2f186d4`
  (6-series gzip, 6649132 bytes; decompressed 16025608 bytes, 65536 larger than compiles
  31, 32, 34 and 35 — a difference consistent with the added observation, the exact cause
  not read from the image map; the image effective size is 16646144). The kernel configuration is unchanged (`975f8703…`, 24
  fragments).
- The board DT is unchanged (123 DTBs, checksums passed at validation; the built board DT
  digest `07b097d5…` equals compiles 24 to 35). Warnings against the build: the two
  pre-existing non-driver lines identical to compile 35 — the trailing-whitespace note
  while applying a v7.1.3 patch and the unused-function warning in `kernel/cpu.c`; zero
  MT6797 driver warnings.

The built change, stated exactly: the receive decoder returns the 4-bit GROUP_VLD mask it
already computes in a new `group_vld` field; the data phase keeps, per delivered class,
counters of frames with group 1 (the received PN group) present or absent and a per-class
`u16` bitmap of which mask values 0..15 were seen, printed once at the data phase end, and
the first data RX record carries the mask. No PN bytes, payload or addresses are read or
stored, nothing reaches the crypto path, and no delivery, drop, radio, transmit or timing
behaviour changes. This settles only whether group 1 is available on the sampled delivered
classes; no replay ownership, firmware enforcement, operational or replay-protection claim
follows from this build.

## Candidate 31 composition (waits for the custodian)

`build-candidate.py` now pins the built input `7fa36c01` and this package `521e1ce3…` for
candidate 31; every other pin (parent, DT digest `07b097d5…`, release, firmware) is
unchanged, and the RAM root, board DT and kernel configuration are expected byte-identical
to candidate 30 (`449832a3…`, `25ab60f4…`, `975f8703…`) with the reviewed helper and
supplicant preserved. The custodian composes candidate 31 privately with the existing
parent, helper and supplicant; nothing has been installed or booted.
