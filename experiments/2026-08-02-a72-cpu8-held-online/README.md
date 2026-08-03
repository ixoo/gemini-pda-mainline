# Experiment: Hold CPU8 online before hotplug notifiers

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-02-a72-cpu8-held-online` |
| Status | `runtime-attempt-1-inconclusive-retention-window` |
| Subsystem | MT6797 HPS, generic CPU hotplug, CPU8 IPI/coherency |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-02 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 7 stability follow-up |

## Question or hypothesis

Can the already-proven one-way CPU8 startup remain online through two bounded
cross-CPU IPI/accounting samples when HPS is prevented from entering CPU8-down
and generic hotplug rejects every CPU8/9 down request before notifier dispatch?

## Provenance and environment

- Pinned Gemian source: `59e00a9144d782e148332009a835b99c43382467`.
- Exact accepted parent: the one-way CPU8 patchset and first online runtime.
- Build backend: Buildbox only; no native VM kernel build.
- Intended boot path: exact Android-v0 image on live-GPT-resolved `boot2` only
  after all offline gates pass.

## Safety assessment

This follow-up changes no CPU8 startup, voltage, isolation, SRAM-LDO, PSCI, or
DCM operation. It adds two earlier policy barriers against CPU8/9 down and two
read/accounting-only synchronous IPIs to CPU8. CPU9 startup, CPU_OFF, userspace
control, load generation, OPP/cpufreq changes, and offlining remain forbidden.

The existing exclusive twelve-second watchdog remains the independent terminal
recovery path. Any missing sample, wrong executing CPU, CPU8 disappearance,
CPU9 presence, hotplug notifier entry, panic, or conflicting marker stops the
experiment and prohibits unchanged retry.

## Associated code

- [`DESIGN.md`](DESIGN.md): exact HPS floor, generic pre-notifier veto, IPI
  sampling, timing, and decision contract.
- [`scripts/hold_model.py`](scripts/hold_model.py): executable abstract state
  model with no I/O or hardware action.
- [`scripts/test_hold_model.py`](scripts/test_hold_model.py): positive and
  fail-closed model cases.
- [`scripts/source_edits.py`](scripts/source_edits.py): deterministic three-step
  source transformation for the exact one-way parent.
- [`scripts/validate_patches.py`](scripts/validate_patches.py) and
  [`scripts/test_static.py`](scripts/test_static.py): ordering, forbidden-path,
  inventory, and mutation gates.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox): Buildbox-only
  source preparation and three-patch generation.
- [`scripts/build-on-buildbox`](scripts/build-on-buildbox): Buildbox-only exact
  held-online versus one-way-parent compile review entry point.
- [`scripts/assemble.py`](scripts/assemble.py) and
  [`scripts/build-candidate.sh`](scripts/build-candidate.sh): pinned Android-v0
  assembly and two-path offline candidate construction.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh): source-pinned guarded
  live-GPT boot2 write, full readback, no-fresh-backup, and shutdown path.
- [`scripts/capture-live-outcome.sh`](scripts/capture-live-outcome.sh): optional
  read-only USB/netcat marker capture.
- [`results/source-order-audit-20260802.txt`](results/source-order-audit-20260802.txt):
  exact runtime-to-source call ordering and chosen insertion points.
- [`patches/`](patches/): exact three-patch Buildbox-generated follow-up.
- [`results/patch-generation-review-20260802.txt`](results/patch-generation-review-20260802.txt):
  two rejected validator drafts, final identities, 11 mutations, and manual
  source-flow review.
- [`results/compile-review-20260802.txt`](results/compile-review-20260802.txt):
  exact Buildbox identities, diagnostics, disassembly, and stack-use decision.
- [`results/offline-container-review-20260802.txt`](results/offline-container-review-20260802.txt):
  reproducible Android-v0 assembly, padding, parsing, and offline-only decision.
- [`results/runtime-decision-map-20260802.txt`](results/runtime-decision-map-20260802.txt):
  exact deployment boundary and mutually exclusive runtime decisions.
- [`results/deployment-20260802.txt`](results/deployment-20260802.txt): exact
  live-GPT write/readback and post-success shutdown evidence.
- [`results/runtime-attempt-1-inconclusive-20260803.txt`](results/runtime-attempt-1-inconclusive-20260803.txt):
  changed-cycle retained-console result and observation-window decision.

## Procedure

1. Pin the exact public source and accepted one-way parent identities.
2. Generate three logical patches: generic early veto, HPS floor, bounded IPI
   hold proof.
3. Reject mutations that move either veto after `cpu_down` or notifier entry,
   weaken CPU9/CPU_OFF rejection, alter the startup sequence, or turn IPI
   sampling into load.
4. Commit and push before Buildbox generation/compilation.
5. Compare changed and exact parent builds, disassembly, diagnostics, and stack
   usage; independently reconstruct the container and runtime decision map.
6. Only then install once, shut down, manually select boot2, and recover exact
   ramoops after the automatic reset.

## Observations

The parent runtime brought CPU8 online exactly once, then faulted about 1.17
seconds later when HPS entered `_cpu_down` and a CPU_DOWN_PREPARE notifier called
`cpuhvfs_notify_cluster_off` before the platform CPU-disable veto.

The exact held-online child and one-way parent both compile on Buildbox with
identical diagnostics. Binary review confirms the two early barriers and the
one- and six-second IPI path; existing affected stack frames do not grow.

Runtime attempt 1 automatically returned to known-good Gemian with a changed
boot ID, watchdog-class reason, and byte-identical boot2. The 65,524-byte
console-ramoops tail begins at 9.166 seconds, after the parent completion and
the expected one- and six-second samples at about 2.932 and 7.932 seconds. It
therefore retains none of the required exact markers. From 9.166 through
14.010 seconds it records 14 CPU9 rejections before A72 action and no held
fault, down-veto, or panic token. Those later observations are encouraging but
cannot replace the predeclared success sequence.

## Analysis

The startup path is no longer the blocker. An HPS-only skip would prevent the
observed caller but leave every other caller able to enter unsafe notifiers. A
generic-only veto would be safe but allow HPS to request an impossible target
repeatedly. The smallest complete boundary therefore uses both: make HPS keep
one CPU in the CPU8/9 cluster, and reject any residual CPU8/9 `cpu_down()` call
before `cpu_hotplug_begin()` and `CPU_DOWN_PREPARE`.

Two synchronous, widely separated IPIs are decision-changing evidence that
CPU8 executes callbacks and remains visible to generic accounting, rather than
merely preserving the original online marker.

## Conclusion

`runtime-inconclusive-observation-window`: no attributable failure was retained,
but normal console traffic overwrote both substantive IPI measurements before
the watchdog recovery. CPU8 bounded hold is not yet established.

## Follow-up

Do not repeat the unchanged artifact. Add a later substantive synchronous CPU8
execution/accounting sample close enough to the unchanged watchdog deadline to
survive in console-ramoops. Preserve the existing early HPS and generic-down
barriers, CPU9 and CPU_OFF prohibitions, startup sequence, and recovery owner.
