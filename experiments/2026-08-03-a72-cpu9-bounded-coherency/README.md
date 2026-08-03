# Experiment: CPU8/CPU9 bounded coherency

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-03-a72-cpu9-bounded-coherency` |
| Status | `patch-generation-passed-compile-pending` |
| Subsystem | MT6797 retained Cortex-A72 pair and cache coherency |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-03 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 8 CPU9 retained coherency/load |

## Question or hypothesis

Can CPUs 8 and 9 complete a bounded concurrent shared-memory ping-pong with
explicit publish/consume barriers while the exact repeatable retained-execution
parent preserves CPU startup, HPS down-pressure vetoes, fixed watchdog
recovery, and every power boundary?

## Provenance and environment

- Exact parent: `2026-08-03-a72-cpu9-terminal-attribution`, including two
  exact runtime passes and its self-contained pair-v3/HPS terminal.
- Exact generated parent kernel commit:
  `0cea53b8b19e5b58e6b2cb748466d6e620a4c911`.
- Exact parent terminal patchset SHA-256:
  `2d94a2cd489e33a7df854ffec7533fbf969dc9c810e9eece57d118b905060310`.
- Build backend: Buildbox only; no native VM kernel build.
- No patch, compile, container, deployment, or runtime claim exists at this
  design stage.

## Safety assessment

The child may add only one CPU0-pinned observation worker, one concurrent
cross-call to already-online CPUs 8 and 9, bounded shared-memory handshakes,
and a self-contained terminal snapshot. It must not enable CPU_OFF, initiate
hotplug, alter startup or pair timing, change HPS policy, touch a regulator or
power register, modify the watchdog, allocate persistent userspace control, or
continue after recovery.

## Associated code

- [`DESIGN.md`](DESIGN.md): exact concurrency oracle, boundedness, terminal,
  result classes, source invariants, and safety boundary.
- [`scripts/source_edits.py`](scripts/source_edits.py): deterministic exact-parent
  source transformation.
- [`scripts/test_static.py`](scripts/test_static.py): source contract and 11
  rejected mutation checks.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox): Git-pinned,
  Buildbox-only exact-parent patch generation.
- [`patches/`](patches/): one accepted Buildbox-generated logical child patch.
- [`results/patch-generation-review-20260803.txt`](results/patch-generation-review-20260803.txt):
  exact identities, rejected generation attempts, source/mutation audit, and
  compile-only acceptance decision.

## Conclusion

`patch-generation-passed-compile-pending`: Buildbox reconstructed the exact
terminal-attribution parent, exercised the deterministic transformer, rejected
11 mutations, and generated one patch changing only `psci.c`. The accepted
source contains the exact CPU0-pinned, 1,024-round, finite-budget handshake and
complete pair-v4 terminal. It has not compiled yet.

## Follow-up

Commit and push the accepted patch review. Then add the exact-parent Buildbox
compile workflow and compare full child/parent builds, linked barriers/loops,
configuration, diagnostics, and stack bounds before container construction.
