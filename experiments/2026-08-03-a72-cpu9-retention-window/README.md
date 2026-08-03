# Experiment: CPU9 retention window

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-03-a72-cpu9-retention-window` |
| Status | `runtime-map-passed-deployment-pending` |
| Subsystem | MT6797 CPU8/CPU9 retained pair sampling and HPS down pressure |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-03 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 8 CPU9 retained execution |

## Question or hypothesis

Can the exact CPU9 cluster-reuse child finish three synchronous CPU8/CPU9
callbacks inside the fixed watchdog window while keeping every CPU8/CPU9
public-down request vetoed and reducing repeated HPS console churn to one
directly attributable record?

## Provenance and environment

- Exact source: `59e00a9144d782e148332009a835b99c43382467`.
- Exact parent: `2026-08-03-a72-cpu9-cluster-reuse`, including its rejected
  runtime result and positive CPU9 execution boundary.
- Build backend: Buildbox only; no native VM kernel build.
- No device artifact exists until source generation, static/mutation review,
  exact-parent compilation, binary/stack review, container validation, and a
  predeclared runtime map pass.

## Safety assessment

The standard PSCI-only CPU9 startup and all inherited power, rollback,
watchdog, and CPU-off prohibitions remain unchanged. The child changes only
delayed-work timing and console reporting around an already-proven `-EPERM`
barrier. Every request still enters public `cpu_down()` and is rejected before
notifiers or platform callbacks.

No device write is authorized by this design record. A later validated
candidate may use the standing guarded boot2 procedure, with no fresh backup
and clean shutdown after verified readback.

## Associated code

- [`DESIGN.md`](DESIGN.md): exact hypothesis, changes, pass predicate, and
  safety boundary.
- [`scripts/source_edits.py`](scripts/source_edits.py): deterministic exact-
  parent transformation.
- [`scripts/test_static.py`](scripts/test_static.py): source contract and
  rejected mutation checks.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox): Git-pinned
  Buildbox-only patch generation.
- [`scripts/build-on-buildbox`](scripts/build-on-buildbox): exact CPU9-parent
  versus retention-window-child compilation, binary, diagnostics, and stack
  comparison.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh),
  [`scripts/assemble.py`](scripts/assemble.py), and
  [`scripts/test_candidate.py`](scripts/test_candidate.py): pinned Android-v0
  construction and independent offline validation.
- [`patches/`](patches/): one accepted Buildbox-generated logical child patch.
- [`results/patch-generation-review-20260803.txt`](results/patch-generation-review-20260803.txt):
  rejected broad anchor, exact accepted identities, checks, and decision.
- [`results/compile-review-20260803.txt`](results/compile-review-20260803.txt):
  exact-parent full builds, binary/source anchors, stack use, and decision.
- [`results/offline-container-review-20260803.txt`](results/offline-container-review-20260803.txt):
  rejected derivations, two exact constructions, parser checks, and accepted
  full-partition identity.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh),
  [`scripts/capture-live-outcome.sh`](scripts/capture-live-outcome.sh), and
  [`scripts/test_runtime_tools.py`](scripts/test_runtime_tools.py): guarded
  boot2 deployment, optional read-only netcat capture, and offline contract
  validation.
- [`results/runtime-decision-map-20260803.txt`](results/runtime-decision-map-20260803.txt):
  predeclared changed-cycle hypothesis, exact pass/failure classes, tool
  identities, and deployment boundary.

## Procedure

1. Reconstruct the exact CPU9 parent from its pinned patch chain on Buildbox.
2. Apply only the timing, one-shot HPS reporting, and marker-version edits.
3. Generate one logical child patch and run source/mutation validation.
4. Compare the full child build against the exact CPU9 parent before creating
   any boot container.

## Observations

The parent retained pair sample 2 at 11.995489 seconds and ended at 13.979104
seconds. Its third callback was scheduled around 15.995 seconds. It also
retained 83 public-down veto records, each immediately paired with an HPS
CPU9-down warning, while CPU9 remained online for the second pair sample.

## Analysis

The parent proved the CPU9 entry and callback path but gave its terminal no
chance to precede recovery. Moving only the delayed callbacks supplies about a
three-second terminal margin. One HPS-local atomic report preserves direct
caller attribution without allowing repetitive console traffic to overwrite
the decision terminal.

## Conclusion

`runtime-map-passed-deployment-pending`: Buildbox source and compile review
pass. Two independent Android-v0 construction roots are byte-identical, and
the independent parser accepts the exact kernel, inherited ramdisk, header,
padding, provenance, and offline-only boundary. The guarded installer and
read-only capture tools pass their static contracts against the predeclared
runtime map. No boot or runtime claim exists yet.

## Follow-up

Commit and push the exact runtime map and tools, then install only the accepted
full image to live-GPT-resolved inactive boot2. After verified readback and
automatic shutdown, arm the independent capture paths before manual boot2
selection.
