# Phase C compile 14: proposal 0149, the RSN element admitted

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `9ce81bc3ee2833f19e64a5cb57c31c0f80a0c149`, clean, the revision accepted in review.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 648 patches: the compile-13
  selection plus proposal 0149 after 0148, in canonical order; the package
  provenance series equals the selected series.
- Builder: Buildbox-1, 32 jobs, one heavy build after capacity, lock and
  free-space checks; generated `2026-10-09T12:12:56Z`.
- Job: `9ce81bc3ee2833f19e64a5cb57c31c0f80a0c149-mt6797-a53-wifi-phase-b-compile-m0`.
- Validated package inventory SHA-256: `3ecfdecbbc115528e8f6a36add90f05a431095edd059a52730125454a20125c0`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- Managed job log SHA-256: `f18cbd0d27c25dbad7f77ca0d4a4a886cfd567d5914cef896e809bcf43978853`.
- `Image.gz` SHA-256: `b8e7c827c22f536aea6872829a7f00432ae99f3f5a38d9e476ba2f353fcc84df`.

`kernel.config` (`153ea2d0…`) and the board DT (`07b097d5…`) are
byte-identical to compiles 7 to 13; only the image differs. All 802 package
checksums pass after fetch (802 entries, 802 files); proposal 0149 in the
provenance is identical to the repository's patch at this input. Warnings
against the documented baseline: exactly the same two pre-existing non-driver
lines as compiles 12 and 13 (the trailing-whitespace note while applying
v7.1.3 patch 0261 and the unused-function warning in `kernel/cpu.c`), and
zero MT6797 driver warnings.

Candidate 9 pairs this package with candidate 8's RAM root unchanged; see the
[runtime 10 bindings](README.md#runtime-10-bindings-2026-10-09).
