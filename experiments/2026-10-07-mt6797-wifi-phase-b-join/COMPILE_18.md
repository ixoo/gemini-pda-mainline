# Phase C compile 18: proposal 0157, the supplicant's RSN replay-counter declaration admitted

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `eba4baa44b273b45e744c4c017508b6efd61b8ce`, clean, the revision accepted in review.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 656 patches: the compile-17
  selection plus proposal 0157 after 0156, in canonical order; the package
  provenance series equals the selected series.
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend
  after capacity, lock and free-space checks; generated `2026-10-09T22:48:11Z`.
- Job: `eba4baa44b273b45e744c4c017508b6efd61b8ce-mt6797-a53-wifi-phase-b-compile-m0`.
- Validated package inventory SHA-256: `49afb45dc20416a4c1882e1cc198b4f1cc6285b283d61cfb611d82dbf1c0c112`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- `Image.gz` SHA-256: `bea1418001cfde2bbf4d4729873f4ad83a824310b9860547c24d344024fa9952`.
- Patchset SHA-256: `1750462f…`; source SHA-256 `be41c068…` unchanged.

`kernel.config` (`153ea2d0…`) and the board DT are byte-identical to compiles
7 to 17; only the image differs, and that only by proposal 0157. The package
checksums passed at validation (123 DTBs, 656 patches in the provenance, one
more than compile 17). Warnings against the documented baseline: exactly the
same two pre-existing non-driver lines as compiles 12 to 17 (the
trailing-whitespace note while applying v7.1.3 patch 0261 and the
unused-function warning in `kernel/cpu.c`), and zero MT6797 driver warnings.

Candidate 13 pairs this package with candidate 12's RAM root (the private
parent, the release gate, the Phase C1 helper and the pinned supplicant)
once the owner composes it; candidate 12 stays unused and deployment 12
never happened. The composer and the preparation tool pin this input and
package; the other runtime bindings follow the owner's candidate-13 receipt.
