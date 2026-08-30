# Experiment: one-shot CPU8 admission after READY publication

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-ready-admission-one-shot` |
| Status | `complete; one-shot stopped before core consumption at unpublished READY` |
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

The first published runner invocation failed before opening USB because it
materialized the location-sensitive derived wrapper one directory below its
source-pinned support files. It created no runtime output and sent no token.
The corrected runner materializes a uniquely named file beside those support
files, retains the same exact contract and derived-collector hashes, and still
removes the temporary file on every exit.

The corrected runner then revalidated the same exact boot and consumed the
token once. The write and read-only remount both succeeded. The terminal frame
was `operation_ret=-11`, `core_consumed=0`, advisory
`entry_trace_ret=-5`, successful terminal tracing, CPUs 0--7 online, CPUs 8--9
offline, and zero CPU8, CPU9, CPU_OFF, or retry requests. The trigger was not
retried.

A separate bounded read-only same-boot log capture reported that the static
runtime identity record was unavailable or invalid and that profile
`mt6797-a53-a72-a41-v7` was blocked at proof mask `0x75008`. That mask is
exactly bits 3, 12, 14, 16, 17, and 18: capability inventory, HWCAP, source
identity, effect plan, plan validation, and runtime binding. Controller order
and `core_consumed=0` localize the terminal `-EAGAIN` to a null READY accessor,
before source registration or `add_cpu(8)`.

Package evidence already contains the exact generated A41 record, but the
candidate retained serviceability DT `1478f2c8...` unchanged. That DT omits
`/chosen/gemini-late-cpu-provenance`. The primary runtime-binding failure is
therefore an attributable container-construction omission; the other five
mask bits are its downstream planning consequences. Sanitized exact fields and
private-capture hashes are in
[`results/runtime-attempt-1-ready-unpublished-20260830.txt`](results/runtime-attempt-1-ready-unpublished-20260830.txt).

## Analysis

Serviceability and controller binding were directly observed, but READY was
not. The pre-trigger validator proved only the consumer/controller state and
did not independently observe the architecture profile state. The one-shot
correctly failed closed before any hardware request and exposed that missing
qualification dimension.

This result does not show a CPU power-on failure. It shows that the candidate
assembler discarded the package-owned provenance leaf when it substituted the
separately transformed serviceability DT. The exact kernel package remains a
valid foundation: composing its A41 record with the same serviceability
transform is a DT-only, decision-bearing correction.

## Conclusion

`decisive-pre-core-ready-unpublished`: the exact one-shot executed once and
stopped at the missing runtime identity binding before core consumption and
before any CPU8 request. CPU8 hardware behavior remains untested; CPU9 remains
vetoed.

## Follow-up

Do not repeat this boot or candidate. Reuse the exact validated Buildbox kernel
package, compose its generated provenance record with the proven serviceability
DT transform, validate the resulting DT/container independently, and run one
new CPU8-only candidate. Extend pre-trigger qualification to require the
architecture's verified runtime-binding/READY state before consuming a token.
