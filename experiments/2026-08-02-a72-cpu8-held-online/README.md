# Experiment: Hold CPU8 online before hotplug notifiers

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-02-a72-cpu8-held-online` |
| Status | `design-and-model` |
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
- [`results/source-order-audit-20260802.txt`](results/source-order-audit-20260802.txt):
  exact runtime-to-source call ordering and chosen insertion points.

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

`confirmed-design-boundary`: the post-success crash precedes the existing
platform veto. Source generation is authorized for the exact two-layer early
veto plus bounded IPI hold proof; another unchanged one-way candidate is not.

## Follow-up

Generate, mutate, review, and compile the exact three-patch follow-up on
Buildbox. Do not access the device until the new container and runtime gates
pass and their evidence is pushed.
