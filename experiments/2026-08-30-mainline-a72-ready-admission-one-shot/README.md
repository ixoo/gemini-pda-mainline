# Experiment: one-shot CPU8 admission after READY publication

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-ready-admission-one-shot` |
| Status | `running; exact boot armed and unconsumed` |
| Subsystem | arm64 late CPU admission and MT6797 CPU8 hotplug |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-30 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

On exact READY-qualified mainline boot `2ec43fd0...`, does the existing
root-only one-shot transaction consume its core, issue its sole CPU8 request,
and bring CPU8 online, or return one attributable terminal error?

This experiment changes no kernel, configuration, DT, ramdisk, LK container,
or device partition. It binds the already-reviewed action to one exact boot,
candidate, accepted immutable frame, trace-aware armed schema, and private
evidence path.

## Provenance and environment

- Candidate build commit: `5abde763316ab358d7f5cb1a3b6a461eb0a2ed99`.
- Published deployment evidence commit: `ba60f6cb`.
- Kernel release: `7.1.3-gemini-a72-admission-live`.
- Exact full boot2 SHA-256: `8acf9227...`.
- Mainline boot ID: `2ec43fd0-3afb-4a56-bf9f-92bacff303ba`.
- Accepted private pre-trigger frame SHA-256: `c2ab936d...`.
- Before action: CPUs 0--7 online, CPUs 8--9 offline, controller armed, both
  trace return fields zero, and all action counters zero.
- Build backend: none needed; no kernel or candidate bytes change and no native
  VM build is used.

## Safety assessment

Before any write, the collector re-captures and validates the exact candidate,
release, boot ID, USB interface, controller binding, read-only sysfs, CPU lists,
trace-aware armed state, and zero-execution counters. It fsyncs both the
accepted pre-trigger frame and trigger intent before opening the one trigger
session.

The kernel can consume the admission core once and issue at most one CPU8
request. CPU9, CPU_OFF, retry, storage, partition, firmware, and reboot paths
remain absent. A complete terminal frame or any transport loss after the commit
marker is final; the trigger is never retried. The accepted outcomes are CPU8
online, one terminal admission error, or post-commit transport loss.

## Associated code

- `contract.json`: exact candidate, live boot, immutable frame, action budgets,
  and tooling identities.
- `scripts/remote-pretrigger.sh`: read-only exact live frame.
- `scripts/validate-pretrigger.py`: trace-aware validator pinned to this boot.
- `scripts/remote-trigger.sh`: byte-identical reviewed one-shot action.
- `scripts/classify-attempt.py`: trace-aware three-branch classifier.
- `scripts/test-runtime.py`: all accepted branches and 14 rejecting mutations.
- `scripts/collect-live-trigger.sh`: deterministic collector derivation with a
  materialization-only mode.
- `scripts/run-one-shot.sh`: exact contract and derived-collector gate with one
  fixed private output path.
- `results/offline-one-shot-gates-20260830.txt`: pre-action validation receipt.

Private transcripts remain below ignored `artifacts/runtime-captures/`.

## Procedure

1. Validate source pins, derivations, shell/Python syntax, ShellCheck, the exact
   accepted frame, and all runtime mutations.
2. Materialize the collector twice and require byte identity.
3. Publish this exact boot-ID-pinned contract before device action.
4. Re-capture and fsync the same armed zero-execution state on this boot.
5. Fsync the trigger intent, open one netcat session, send the sole token, and
   never retry after the commit marker.
6. Classify and publish the terminal branch before changing the CPU9 veto.

## Observations

The predecessor experiment accepted exact immutable frame `c2ab936d...` after
correcting an older-schema validator. It reports the exact candidate and boot,
CPUs 0--7 online, CPUs 8--9 offline, a bound armed controller, zero trace
errors, and no trigger, CPU, retry, CPU_OFF, storage, or reboot action.

The boot-bound runtime suite accepts one pre-trigger branch and three terminal
branches while rejecting seven unsafe pre-trigger and seven unsafe attempt
mutations. Two derived collector materializations are byte-identical at
`1e372c42...`. No device action occurred during these offline gates.

## Analysis

READY publication, serviceability, controller binding, and the trace-aware
zero-execution precondition are now directly observed on the exact boot. The
sole remaining CPU8 discriminator is the already-bounded admission action.
Offline evidence cannot establish whether CPU8 reaches the online checkpoint.

## Conclusion

The exact boot is qualified for one CPU8-only action after this definition is
published. CPU8 hardware behavior remains inconclusive until that action; CPU9
remains vetoed.

## Follow-up

Run the published one-shot once, preserve either its complete terminal frame or
post-commit transport-loss boundary, and collect recovery evidence if needed.
Use that attributable CPU8 result—not screen color or reboot timing—to select
the next CPU8 correction or the first CPU9-only experiment.
