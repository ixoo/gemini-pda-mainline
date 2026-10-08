# Phase B compile 10: scanned beacons through mac80211

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `00dc3c7a0a8a286788a9afafbca1460bbaa717a3`, clean.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 643 patches: the compile-9
  selection plus proposal 0145. Proposal 0140 stays unselected.
- Builder: Buildbox-1, 32 jobs; one submission, generated `2026-10-08T02:26:49Z`.
- Job: `00dc3c7a0a8a286788a9afafbca1460bbaa717a3-mt6797-a53-wifi-phase-b-compile-m0`.
- Validated package inventory SHA-256: `7ee0f0586e17259aeff008e341d61c05ec5194a956bf94038afb41824bffba12`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- Managed job log SHA-256: `3db8b108c3bb67979f4d8dde9217836f4fae217c8d7556efd950184cd12b985d`.
- `Image.gz` SHA-256: `578d877ba60ffdb1f1a72b6da05aef34d103fc9f64137991b6d0f320380d31b2`.

Kernel-only change. `kernel.config` (`153ea2d0…`) and the board DT
(`07b097d5…`) are byte-identical to compiles 7 to 9; only the image differs.
All 797 package checksums pass after fetch, proposals 0143 to 0145 are in the
package provenance, and the build log has no MT6797 driver warning. The 0145
patch in the provenance is the one at input `00dc3c7a0a8a286788a9afafbca1460bbaa717a3`; the later revision
`46c05a59` changed only a comment in that patch, so the built code is the
current code. Before submission every fixture in `tests/` passed against
the identical source tree with ASan and UBSan, including the two new scan
fixtures, and `check-repository` exited 0.

Candidate 5 pairs this package with the candidate-4 RAM root and helper; see
the [runtime 6 bindings](README.md#runtime-6-bindings-2026-10-08).
