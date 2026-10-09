# Phase C compile 13: C1 accepted association with bounded EAPOL observation

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `8efe639e750d76f82050c375e2635497605c047c`, clean.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 647 patches: the compile-12
  selection plus proposals 0140 (selected after 0139) and 0148 (after 0147),
  in canonical order; the package provenance series equals the selected series.
- Builder: Buildbox-1, 32 jobs, one heavy build after capacity, lock and
  free-space checks; generated `2026-10-09T03:05:08Z`.
- Job: `8efe639e750d76f82050c375e2635497605c047c-mt6797-a53-wifi-phase-b-compile-m0`.
- Validated package inventory SHA-256: `07caf6b555debfcaa20c642d336f702705fca8f36c71b20a402cef4fd273dd79`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- Managed job log SHA-256: `4aaeefa440ececda609142c780c613927c35807622313b9ed8fa6b43bf3ae802`.
- `Image.gz` SHA-256: `4bed248ecf8d4944a4ce7e06b61a0c161854ce6c8e270b3efe598d90ca3161ba`.

Kernel change reviewed and accepted before the build, with checkpatch clean.
`kernel.config` (`153ea2d0…`) and the board DT (`07b097d5…`) are
byte-identical to compiles 7 to 12; only the image differs. All 801 package
checksums pass after fetch; proposals 0140 and 0148 in the provenance are
identical to the repository's patches at this input. The build log has no
MT6797 driver warning; its only two warnings are pre-existing and identical
in compile 12: a trailing-whitespace note while applying v7.1.3 patch 0261
and an unused-function warning in `kernel/cpu.c` from the pinned CPU-profile
series, both outside the Wi-Fi change.

Candidate 8 pairs this package with a new RAM root: the Phase C1 helper
(`bc499f28…`) replaces the Phase B helper, so the initramfs digest differs
from candidates 4 to 7 while the parent members stay unchanged; see the
[runtime 9 bindings](README.md#runtime-9-bindings-2026-10-09).
