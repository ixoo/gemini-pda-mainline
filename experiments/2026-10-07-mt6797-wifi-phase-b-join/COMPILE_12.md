# Phase B compile 12: BSS absence indication admitted in teardown

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `65c2fa81f083bc4baec83266786219cda2d57c64`, clean.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 645 patches: the compile-11
  selection plus proposal 0147. Proposal 0140 stays unselected.
- Builder: Buildbox-1, 32 jobs; one submission, generated `2026-10-09T01:53:21Z`.
- Job: `65c2fa81f083bc4baec83266786219cda2d57c64-mt6797-a53-wifi-phase-b-compile-m0`.
- Validated package inventory SHA-256: `784aef7580aef01d34ad953c8e5f6ce87dbc1ff2b0973766feb55985278ec034`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- Managed job log SHA-256: `aeda4dc551d004098c1eaaf93da43f1d01bf9a4a2935b9f9b8616ede3437796a`.
- `Image.gz` SHA-256: `5ba80f4a14b99e71e4ddcc25f801dcc02b736f363a08afdb646b849aee1ef9d9`.

Kernel-only change, reviewed and accepted before the build. `kernel.config`
(`153ea2d0…`) and the board DT (`07b097d5…`) are byte-identical to compiles 7
to 11; only the image differs. All 799 package checksums pass after fetch,
proposals 0143 to 0147 are in the package provenance with 0147 identical to
the repository's patch at this input, and the build log has no MT6797 driver
warning. The later commit `3c3d43b7` changed only the host-side join
classifier. Before submission every fixture in `tests/` passed against the
identical source tree with ASan and UBSan, and `check-repository` exited 0.

Candidate 7 pairs this package with the candidate-4 RAM root and helper; see
the [runtime 8 bindings](README.md#runtime-8-bindings-2026-10-09).
