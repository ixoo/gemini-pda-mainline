# Phase B compile 11: join-tick branch and ledger diagnostics

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `d88d6e22909539944ea532db374e1718b12ce94f`, clean.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 644 patches: the compile-10
  selection plus proposal 0146. Proposal 0140 stays unselected.
- Builder: Buildbox-1, 32 jobs; one submission, generated `2026-10-08T10:18:26Z`.
- Job: `d88d6e22909539944ea532db374e1718b12ce94f-mt6797-a53-wifi-phase-b-compile-m0`.
- Validated package inventory SHA-256: `86b0a20889560530f41a1a54f5ca30fa2cdd567a2745d2543a321ee3a70a9687`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- Managed job log SHA-256: `694410356cdba64a08aeabf9f4db60efa2f0cfd7c123d21769173fcbfb0c4247`.
- `Image.gz` SHA-256: `2871523e8ded92548111a831a9bb0338b1ba68571ec8b9117e9ab4f990e563f4`.

Kernel-only, diagnostic-only change. `kernel.config` (`153ea2d0…`) and the
board DT (`07b097d5…`) are byte-identical to compiles 7 to 10; only the image
differs. All 798 package checksums pass after fetch, proposals 0143 to 0146
are in the package provenance with 0146 identical to the repository's patch at
this input, and the build log has no MT6797 driver warning. Before submission
every fixture in `tests/` passed against the identical source tree with ASan
and UBSan, and `check-repository` exited 0.

Candidate 6 pairs this package with the candidate-4 RAM root and helper; see
the [runtime 7 bindings](README.md#runtime-7-bindings-2026-10-08).
