# Experiment: one-shot CPU8 admission after ATAG prerequisite closure

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-mainline-a72-admission-atag-one-shot` |
| Status | `definition validated; device action pending` |
| Subsystem | MT6797 A72 admission controller and CPU hotplug |
| Device variant | Planet Computers Gemini PDA, named project device |
| Date(s) | 2026-08-28 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 7, first attributable CPU8 request |

## Question or hypothesis

After the entire ATAG/handoff/I2C6/DA921x/clock/BigiDVFS/platform/binder graph
binds, does the existing one-shot admission transaction reach its core and sole
CPU8 request, and does CPU8 become online or return an attributable terminal
error?

This follow-up changes no kernel, configuration, DT, ramdisk, LK container, or
device partition. It binds the unchanged action to installed candidate
`fd611a4c...`, mainline boot ID `515b4618...`, and the exact armed state already
published by the prerequisite experiment.

## Provenance and environment

- Published deployment and binding proof: signed commit `24064ab3`.
- Exact release `7.1.3-gemini-a72-admission-live`; CPU0--7 online and CPU8--9
  offline before the action.
- ATAG devinfo, DVFSP handoff, I2C6, DA921x, clock backend, BigiDVFS, platform
  state, A72 binder, and admission controller are all bound.
- The trigger script is byte-identical to already reviewed source
  `93e6ee4b...`; its only accepted token remains
  `run-a72-admission-20260828-a`.
- No build is needed or performed. In particular, no native VM build is used.
- The display is frozen on the boot image with no console. Exact USB/netcat is
  live and is the attribution and recovery channel.

## Safety assessment

Before any write, the host re-captures and validates the exact candidate,
release, boot ID, USB interface, controller binding, CPU0--7/CPU8--9 state, and
armed zero-execution status. The accepted frame and trigger intent are fsynced
before the sole trigger connection opens.

The kernel can consume the admission core once and issue at most one CPU8
request. CPU9, CPU_OFF, retry, storage, partition, firmware, watchdog-reset,
and reboot paths remain absent. The host never retries after a commit-bearing
response or transport loss. On a returning path it restores virtual sysfs
read-only before reading terminal state.

The three accepted results remain CPU8 online with terminal success, terminal
admission error, or post-commit transport loss. Every other transcript fails
closed. No framebuffer observation is used for classification.

## Associated code

- `scripts/remote-pretrigger.sh`: read-only exact live frame for candidate
  `fd611a4c...`.
- `scripts/validate-pretrigger.py`: source-pinned exact boot-ID gate.
- `scripts/remote-trigger.sh`: byte-identical reviewed one-shot action.
- `scripts/classify-attempt.py`: source-pinned corrected three-branch
  classifier.
- `scripts/test-runtime.py`: seven pre-trigger and six attempt mutations plus
  all three accepted branches.
- `scripts/run-one-shot.sh`: source-pinned durable collector with one fixed
  private output path.
- `results/offline-one-shot-gates-20260828.txt`: exact tooling and pre-action
  validation receipt.

Private transcripts remain below ignored `artifacts/runtime-captures/`.

## Procedure

1. Validate source pins, shell/Python syntax, ShellCheck, and all runtime
   mutations.
2. Materialize the collector twice and require byte-identical SHA
   `581f896a...`.
3. Revalidate the still-running exact boot ID and armed zero-execution frame.
4. Publish this definition before the device action.
5. Re-capture and fsync the same exact frame plus the one-shot intent.
6. Send the exact accepted token in one netcat session and never retry.
7. Classify and publish one accepted terminal branch or the precise blocker.

## Observations

The published prerequisite boot has the complete supplier graph bound and the
controller armed with no prior execution. A fresh read-only prepublication
frame again accepts candidate `fd611a4c...`, boot ID `515b4618...`, CPU0--7
online, CPU8--9 offline, read-only sysfs, and zero action counters.

The runtime suite accepts exactly three result branches and rejects all 13
unsafe mutations. Two independent collector materializations are byte-identical
at `581f896a...`. The trigger source remains byte-identical to the prior action.
No device write or trigger occurred during definition validation.

## Analysis

The predecessor stopped before the core because the A72 binder was unbound.
That exact prerequisite is now closed, so this one action can distinguish a
later admission-stage result from the already repaired configuration defect.
The frozen framebuffer does not weaken attribution because candidate, boot ID,
commit marker, terminal state, and CPU lists all come from exact USB/netcat.

## Conclusion

The separately attributable one-shot definition is ready to publish. CPU8 is
still offline and no result is claimed before the one permitted action.

## Follow-up

After publication, execute exactly one trigger session on boot ID
`515b4618...`, classify the result, and never retry this boot after a commit
marker. CPU9 remains out of scope.
