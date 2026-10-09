# Phase C compile 17: proposals 0153 to 0156, the C2 handshake path

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `0e333617ae046d461857fab4a746cc2f948c2278`, clean, the revision accepted in review.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 655 patches: the compile-16
  selection plus proposals 0153 to 0156 after 0152, in canonical order; the
  package provenance series equals the selected series.
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend
  after capacity, lock and free-space checks; generated `2026-10-09T21:59:35Z`.
- Job: `0e333617ae046d461857fab4a746cc2f948c2278-mt6797-a53-wifi-phase-b-compile-m0`.
- Validated package inventory SHA-256: `1997dffb97a3089cbd3a83ba6286236d288e56bd3e541fd1379514888b79d346`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- `Image.gz` SHA-256: `0c24f88f663173fbd3d041819deec56596462d46cc66b3328e8bc85808ea622d` (6624463 bytes).

`kernel.config` (`153ea2d0…`, 113083 bytes) and the board DT (`07b097d5…`,
29736 bytes) are byte-identical to compiles 7 to 16; only the image differs.
The package checksums pass after the owner's independent fetch (809
inventory entries, four more than compile 16 for the new patches in the
provenance); all 655 selected patches in the provenance are byte-identical
to the repository's patches at this input. Warnings against the documented
baseline: exactly the same two pre-existing non-driver lines as compiles 12
to 16 (the trailing-whitespace note while applying v7.1.3 patch 0261 and the
unused-function warning in `kernel/cpu.c`), and zero MT6797 driver warnings.

Candidate 12, deployment 12 and runtime 13 are not yet composed or pinned;
the composer carries this input and package, and the owner composes once the
runtime tooling review passes.
