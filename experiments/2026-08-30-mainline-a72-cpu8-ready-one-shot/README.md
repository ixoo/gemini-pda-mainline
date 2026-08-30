# Experiment: one-shot CPU8 admission from proven READY

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-cpu8-ready-one-shot` |
| Status | `preparing fresh boot-bound contract` |
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
are intentionally deferred until the fresh pre-arm frame supplies their exact
boot ID and frame hash.

## Analysis

Pending.

## Conclusion

`preparing`.

## Follow-up

Boot exact installed candidate `2245c1c4...` only after the pre-arm tooling is
published.
