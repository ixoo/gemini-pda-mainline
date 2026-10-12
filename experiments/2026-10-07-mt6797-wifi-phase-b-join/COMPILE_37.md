# Phase C compile 37: proposal 0180, the bounded two-lifetime re-arm (hardware-free compile, reviewed kernel)

Status: validated compile-only; no candidate composed, no device test. This is the
custodian-admitted independent compile of the source-reviewed re-arm kernel, run while the
executable two-lifetime protocol is finished; the device stays on hold.

- Repository input: `5d6323e11edcddad6ca5574c0a225b1c23a32255`, clean, on a branch. Its kernel
  inputs are byte-identical to the reviewed `b33ba5a2` — the only files that differ between
  the two are `join-twice.sh` and `TWO_LIFETIME_PROTOCOL.md` (the executable protocol), not any
  patch, series, config, manifest or driver source. The driver files built are `mac.c` SHA-256
  `9cb2a85a…`, `join-rearm.h` `afb7caa8…` and `data-rx.h` `6330bac2…` (`group-data.h` `7c0d05ea…`,
  `action-frame.h` `51a19415…` unchanged).
- Profile: `mt6797-a53-wifi-phase-b-compile`, 679 selected patches: the compile-36 selection plus
  0180 after 0179, in canonical order; patchset
  `8c81659b30058dc739704b288cfdba82f6a654f10109d3b34b8a9f80f95cafe7`, source `be41c068…`
  unchanged; the package provenance series equals the selected series.
- Builder: the managed Buildbox backend, 32 jobs, one heavy build after the clean push; job
  `5d6323e1…-mt6797-a53-wifi-phase-b-compile-m0`, generated 2026-10-12T13:30:45Z, `hardware_write=none`.
- Package: `fba8f3160888341e3d638b3e3f8f052b345d3900adf5f715b1072d8197716038`, `sha256sums=passed`.
  Kernel image `Image.gz` SHA-256 `92865754c9067e6a43af39bcfc0ab4c9f92459efe0f26508f04c19be7dbbda99`
  (6-series gzip; decompressed 15960072 bytes, image effective size 16580608). The kernel
  configuration is unchanged (`975f8703…`, 24 fragments). The decompressed size is an
  alignment-bucketed value, not a code-size measure; proposal 0180's presence is shown by the
  patch count (679), the distinct patchset digest and the distinct Image.gz digest, not by that
  number.
- The board DT is unchanged (123 DTBs, checksums passed; built DT digest `07b097d5…` equals
  compiles 24 to 36). Warnings: the two pre-existing non-driver lines identical to compiles 35 and
  36 — the trailing-whitespace note while applying a v7.1.3 patch and the unused-function warning
  in `kernel/cpu.c`; zero MT6797 driver warnings.

The built change is proposal 0180 (the bounded two-lifetime re-arm; the dedicated serialized
re-arm pass, the join_closed fence on close and on `.start`/`.hw_scan`, the first-effect scan cap,
the monotonic TX pids, the named refused/wrap records, the expected cap terminal). No candidate is
composed and nothing is installed or booted; the device stays on hold until the complete executable
two-lifetime protocol (the pinned `wpa_cli`, the device hook and the host adapters) is reviewed. No
operational, replay-protection or sustained-operation claim follows from this compile.
