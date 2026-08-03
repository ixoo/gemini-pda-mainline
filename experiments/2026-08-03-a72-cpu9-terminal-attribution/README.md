# Experiment: CPU9 terminal attribution

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-03-a72-cpu9-terminal-attribution` |
| Status | `source-design-review-pending` |
| Subsystem | MT6797 CPU8/CPU9 retained pair and HPS down-pressure attribution |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-03 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 8 CPU9 retained execution |

## Question or hypothesis

Can the already-proven sample-3 terminal carry a coherent snapshot of the
first HPS `-EPERM` result and total matching request count, so the retained
terminal independently proves both three-pair execution and fail-closed
down-pressure handling despite loss of early console text?

## Provenance and environment

- Exact source: `59e00a9144d782e148332009a835b99c43382467`.
- Exact parent: `2026-08-03-a72-cpu9-retention-window`, including its positive
  three-pair boundary and inconclusive missing-HPS-attribution result.
- Build backend: Buildbox only; no native VM kernel build.
- No device artifact exists until exact-parent source generation,
  static/mutation review, full child/parent compilation, binary/stack review,
  deterministic container construction, and runtime-map review pass.

## Safety assessment

The child must not change CPU8 or CPU9 startup, sample timing, the public
CPU-down veto, watchdog ownership/deadline, voltage/frequency, DA921x, cluster
power, or failure recovery. It adds observation state at the already-observed
HPS caller and reads that state only after the third already-proven callback.

## Associated code

- [`DESIGN.md`](DESIGN.md): exact source scope, state publication contract,
  pass predicate, mutations, and safety boundary.
- [`scripts/source_edits.py`](scripts/source_edits.py): deterministic
  exact-parent transformation.
- [`scripts/test_static.py`](scripts/test_static.py): source contract and
  rejected mutation checks.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox): Git-pinned,
  Buildbox-only patch generation.
- [`scripts/build-on-buildbox`](scripts/build-on-buildbox): exact retention
  parent versus terminal-attribution child compilation.

## Conclusion

`source-design-review-pending`: the runtime result defines a decision-changing
observation-only child. No source patch, compile result, boot artifact, or
runtime claim exists yet.

## Follow-up

Generate the exact child patch on Buildbox, reject source mutations, and review
the complete diff before extending the shared Buildbox compile mode.
