# Experiment: bind READY to one CPU8 admission candidate

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-ready-admission` |
| Status | `running` |
| Subsystem | arm64 late CPU profile and MT6797 CPU8 admission |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-30 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

Can the exact serviceability-first CPU8 live-trigger profile reach the existing
one-shot admission controller only after the architecture-owned READY token is
published, while the generic configuration with the profile disabled still
compiles and passes through the late-target preflight?

The hardware-free hypothesis is that two independent defects currently prevent
that test: the profile-disabled header lacks its preflight stub and always-built
boot-capability prototype, and the production MT6797 profile still names the
older `699f1478...` configuration-input identity instead of the exact candidate
identity `5968c24f...`.

## Provenance and environment

- Parent kernel series: canonical Linux 7.1.3 series through patch `0434`.
- Parent prepared source state:
  `b347cf26c4201b6a37ad677f498a66a0097753b00c023d16a1d0bb0e96975de0`.
- Parent prepared source integrity:
  `1b5ba3d2f785fe4c4ed6cfb4b43452e99594575a31e05f487e14e7ce6883410f`.
- Candidate profile: `a72-admission-live-trigger-candidate`.
- Reconnaissance package:
  `linux-7.1.3-gemini-a72-admission-live-trigger-candidate-8b1ce2aa-5968c24f`.
- Candidate configuration-input SHA-256:
  `5968c24f1904c0559dea25480c41fbc7db49e822dc3600d1bdd7632330853f40`.
- Build backend: Buildbox only; no native VM build.

## Safety assessment

Patch generation, mutation testing, and compilation are hardware-free. The
repair adds no CPU request, CPU9 request, retry, CPU_OFF, partition write, or
device action. Its generated review is explicitly not a boot candidate.

Any later boot2 deployment remains subject to the repository's candidate,
partition-resolution, checksum, readback, and clean-shutdown gates. The first
runtime attempt may request CPU8 exactly once only after a root-only live token;
CPU9 remains vetoed.

## Associated code

- `scripts/generate-on-buildbox` pins and runs generation on the managed source.
- `scripts/generate_patches.py` emits and replays two logical format-patches.
- `scripts/source_edits.py` contains deterministic exact-anchor edits.
- `scripts/validate_source.py` validates the config-off and identity contracts.
- `scripts/test_mutations.py` proves representative unsafe changes are rejected.

## Procedure

1. Generate two patches from the integrity-pinned post-`0434` source on
   Buildbox and fetch only the checksum-covered review.
2. Admit the patches in canonical order and audit every manifest profile.
3. Compile the default configuration-off control on Buildbox.
4. Compile the exact `a72-admission-live-trigger-candidate` profile on Buildbox.
5. Confirm the new package retains configuration-input identity `5968c24f...`,
   links the one-shot controller and READY consumer, and introduces no CPU9,
   CPU_OFF, or retry path.
6. Only then decide whether the package is the next boot2 candidate.

## Observations

- The exact pre-repair candidate profile compiled successfully at repository
  commit `6069088eb1e121934721aff1763dc3e6bc7a4687`.
- Its package records configuration-input identity `5968c24f...` and resolved
  configuration SHA-256 `9b9118fd...`.
- The linked production profile still expects `699f1478...`, so the package is
  reconnaissance-only: runtime binding would retain the blocker rather than
  publish READY.
- A separate default-profile control fails before link because
  `arm64_validate_late_cpu_preflight()` is undeclared when the profile is off,
  while always-built `arm64_late_cpu_validate_boot_caps()` lacks a visible
  prototype.
- Exact-source generation at repository commit `9b17b571` produced two logical
  patches with strict style, deterministic replay, positive source validation,
  and all nine rejecting mutations passing. The first generation attempt found
  and corrected a validator that counted only the production identity binding
  while the historical fixture intentionally owns a second comparison.
- Canonical patch `0435` is byte-identical to generated SHA-256 `f07cd67c...`;
  patch `0436` is byte-identical to generated SHA-256 `1a439a82...`.
- The admitted series passes all 158 manifest profiles and rejects all eight
  canonical-series invariant mutations. Compilation remains pending.
- Full generation and admission chronology is in
  [`results/generation-20260830.txt`](results/generation-20260830.txt).

## Analysis

The enabled-profile compile proves that the existing controller and READY
closure link together, but not that the runtime identity gate can open. The
identity mismatch is deterministic and precedes physical CPU8 evidence. The
configuration-off failure is independent and must be repaired so the feature
does not regress unrelated arm64 configurations.

## Conclusion

Inconclusive for hardware behavior. Both repairs are generated, mutation-tested,
replayed, and canonically admitted. The configuration-off control and exact
enabled candidate must still compile on Buildbox before candidate selection.

## Follow-up

Generate, mutation-test, admit, and compile both controls. If the exact enabled
package passes all gates, select one attributable CPU8-only boot2 attempt and
record its retained and live terminal evidence before changing the CPU9 veto.
