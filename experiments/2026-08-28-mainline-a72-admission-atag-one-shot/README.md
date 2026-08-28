# Experiment: one-shot CPU8 admission after ATAG prerequisite closure

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-mainline-a72-admission-atag-one-shot` |
| Status | `complete; one shot stopped at pre-core trace entry with -EIO` |
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
- `scripts/collect-postterminal-recovery.sh`: source-pinned bounded read-only
  Gemian recovery of the exact trace slots, transition ledger, and boot2
  identity.
- `results/offline-one-shot-gates-20260828.txt`: exact tooling and pre-action
  validation receipt.
- `results/runtime-attempt-1-terminal-precore-trace-eio-20260828.txt`: sanitized
  terminal, recovery, and source-order localization receipt.

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

The sole trigger session then returned a complete terminal frame on the same
USB connection: `operation_ret=-5`, `core_consumed=0`, zero CPU requests, CPUs
0--7 online, and CPUs 8--9 offline. No retry, CPU9, CPU_OFF, storage, or reboot
request occurred. The display remained frozen on the boot image without a
console, while USB/netcat stayed live.

After a read-only terminal check, the exact boot ID, zero block mounts, and
known reboot dispatch passed before one USB reboot to Gemian. Gemian returned
with changed boot ID `a30458b2...`; a bounded read-only recovery matched the
installed full boot2 checksum and found zero pstore files, both immutable
admission-trace slots empty, and the transition ledger logically empty. The
device remains on known-good Gemian.

## Analysis

The predecessor stopped before the core because the A72 binder was unbound;
that exact prerequisite is now closed. The new `-EIO` is also pre-core, but for
a different and exact reason. In the compiled controller,
`gemini_admission_trace_entry()` runs before the binder-ready check, READY-token
lookup, and atomic core consumption. Source registration, CPU8 derivation,
publication, and `add_cpu(8)` are all after successful consumption. Therefore
`operation_ret=-5` with `core_consumed=0` localizes the failure to the mandatory
trace-entry call; it cannot be a physical-source, publication, or CPU failure.
The empty recovered trace and ledger corroborate that no durable entry or later
transition committed, although the live terminal frame—not post-return
retention—is the decisive stage oracle.

The frozen framebuffer does not weaken this attribution because candidate,
boot ID, commit marker, terminal state, and CPU lists all came from exact
USB/netcat. It remains a display limitation and no framebuffer-console support
is claimed.

## Conclusion

The one permitted action is complete and must not be repeated. It did not test
the physical-source or CPU8 path: a mandatory retained diagnostic failed first
with `-EIO`. CPU8 remains offline, but the repaired prerequisite graph stayed
serviceable and the failure is now localized to one pre-core instrumentation
call.

## Follow-up

Keep retained tracing fail-closed for automatic/non-serviceable admission, but
make its failure non-gating only for the explicit root-triggered live one-shot.
Expose the trace return separately in the terminal status, retain the single
core-consumption and CPU8-request budgets, and build the one-change follow-up
only on Buildbox. CPU9 remains out of scope.
