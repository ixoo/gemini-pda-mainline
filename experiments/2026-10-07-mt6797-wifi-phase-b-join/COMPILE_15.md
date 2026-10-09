# Phase C compile 15: proposals 0150 and 0151, refused-frame header and optional RX vector

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `89d6028392146948856c310d430c45d0339eca88`, clean, the revision accepted in review.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 650 patches: the compile-14
  selection plus proposals 0150 and 0151 after 0149, in canonical order; the
  package provenance series equals the selected series.
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend
  after capacity, lock and free-space checks; generated `2026-10-09T19:47:42Z`.
- Job: `89d6028392146948856c310d430c45d0339eca88-mt6797-a53-wifi-phase-b-compile-m0`.
- Validated package inventory SHA-256: `efb0b28a0f5710a6e22586415452cb3c407f7f5a196ee4b5a8b95fff4dda188b`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- Managed job log SHA-256: `1923b091d151346e3ee194d6c08290b872aa5dbf6bd7b64aa266e311d03e1d54`.
- `Image.gz` SHA-256: `929785913bcfcf9c61b3793c59fc21bcc725d1cc6935181b57205b5f88afcbd3`.

`kernel.config` (`153ea2d0…`) and the board DT (`07b097d5…`) are
byte-identical to compiles 7 to 14; only the image differs. All 804 package
checksums pass after fetch (804 entries, 804 files, two more than compile 14
for the two new patches in the provenance); proposals 0150 and 0151 in the
provenance are identical to the repository's patches at this input. Warnings
against the documented baseline: exactly the same two pre-existing non-driver
lines as compiles 12 to 14 (the trailing-whitespace note while applying
v7.1.3 patch 0261 and the unused-function warning in `kernel/cpu.c`), and
zero MT6797 driver warnings.

Candidate 10 pairs this package with candidate 9's RAM root unchanged; see the
[runtime 11 bindings](README.md#runtime-11-bindings-2026-10-09).
