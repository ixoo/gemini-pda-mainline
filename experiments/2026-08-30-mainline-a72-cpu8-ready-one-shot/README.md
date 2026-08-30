# Experiment: one-shot CPU8 admission from proven READY

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-cpu8-ready-one-shot` |
| Status | `terminal pre-add_cpu admission error; localized follow-up required` |
| Subsystem | arm64 late CPU admission and MT6797 CPU8 hotplug |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-30 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

From exact candidate `2245c1c4...`, which has now produced a silent,
unblocked, armed, zero-execution READY frame, does one fresh boot-bound trigger
consume the admission core and bring CPU8 online, or produce one attributable
terminal error?

This experiment changes no kernel, configuration, DT, ramdisk, container, or
device partition. It first qualifies a fresh boot read-only, then publishes a
contract binding the sole action to that boot ID and immutable frame.

## Safety assessment

The pre-arm step has no trigger path. The later action is permitted only after
the exact candidate, release, boot ID, runtime identity, silent READY state,
read-only sysfs, CPU lists, and zero action counters are durably accepted. The
existing kernel route can consume at most once and request only CPU8. CPU9,
CPU_OFF, retry, storage, partition, firmware, and automatic reboot paths remain
absent. There is no trigger retry after the commit marker.

## Procedure

1. Capture and validate one fresh read-only READY frame from the already
   installed exact candidate; send no trigger.
2. Bind the one-shot contract to its boot ID and immutable frame, validate all
   accepted branches and unsafe mutations, and publish the contract.
3. Revalidate the same boot, fsync the frame and intent, and open exactly one
   trigger session.
4. Classify CPU8 online, one attributable terminal error, or post-commit
   transport loss. Never retry the token. Keep CPU9 vetoed.

## Observations

The no-action pre-arm collector is published. The action script is byte-for-
byte identical to the previously reviewed one-shot trigger
(`79bc42ca...`): it rechecks the exact armed status, opens sysfs for the single
token write, restores it read-only, and reports the terminal status and CPU
lists. The terminal classifier is source-pinned to the reviewed three-branch
classifier. No action was taken; the device remains off pending a fresh boot.

The boot-ID-bound validator, complete collector, immutable contract, and runner
were then bound to fresh boot `1f2dcf6a...` and immutable frame `53644427...`.
The frame independently repeats the complete silent READY result with CPUs
0--7 online, CPUs 8--9 offline, and zero actions. Two collector
materializations are byte-identical at `fa1dc4cb...`; the runtime suite accepts
one pre-trigger and three terminal branches while rejecting thirteen
pre-trigger and seven terminal mutations. See
[the pre-arm and offline record](results/prearm-and-offline-gates-20260830.txt).

The published runner then revalidated that same boot and fsynced both its
accepted pre-trigger and irreversible intent before opening one trigger
session. The token write and read-only remount both succeeded. The controller
consumed the trigger and admission core exactly once, returned `-EPERM`, and
issued zero CPU requests. CPUs 0--7 remained online and CPUs 8--9 remained
offline. Entry and terminal trace writes returned `-EIO` and `-EALREADY`, but
the live route explicitly treats those trace failures as advisory; neither
replaced the `-EPERM` operation result. There were no CPU9, CPU-off, retry,
storage, partition, or reboot requests. A later read-only diagnostic confirmed
the unchanged CPU lists and terminal status on the same boot. See
[the terminal attempt record](results/terminal-pre-add-cpu-eperm-20260830.txt).

## Analysis

`operation_ret=-1`, `core_consumed=1`, and `cpu_requests=0` places the failure
after the one-shot admission core consumed its attempt but before its sole
`add_cpu(8)` call. The source-registration API cannot return `-EPERM`; its
runtime errors are `-EINVAL` or `-EBUSY`. Therefore the remaining attributable
universe is state derivation, including bootstrap/frozen-token validation, or
the final membership publication. This result does not test PSCI, generic CPU
hotplug, A72 power sequencing, or CPU8 hardware execution.

Repeating this artifact cannot distinguish those branches. The next candidate
must retain the exact pre-request failure stage in the controller status and,
within derivation, the first rejected substage. That is a diagnostic-only
observation addition: it must not change the request order, predicates,
hardware effects, or one-shot bounds.

## Conclusion

`terminal-pre-add-cpu-eperm`.

## Follow-up

Add durable, read-only stage attribution, validate it offline, then spend one
fresh boot on the new attributable candidate. Keep CPU9 vetoed until CPU8 is
actually online.
