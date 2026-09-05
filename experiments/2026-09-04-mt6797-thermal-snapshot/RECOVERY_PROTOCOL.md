# Frozen recovery host protocol

The [recovery design](RECOVERY_DESIGN.md) and source-pinned program are now
connected to [the host runner](scripts/run-recovery.py). Its execution remains
unselected until the complete exact-candidate shell suite passes and that
result is published. This document is the reviewable protocol, not evidence
of another boot or successful thermal comparison.

## Identity and cycle

Reuse the deployed candidate and exact kernel/record from the recovery design.
The source cycle is consumed attribution boot
`056703de-bf29-4956-891e-ff69d19fdd68`. Its published classification SHA256 is
`4e4bc2b635e9f3a8b4ae908725dff5ac52bfedc3cc2b766d9bb4ee2622a3ad8f`;
its captured terminal lifecycle line, including newline, has SHA256
`8aac24ee30576659fe7d4ffb5e58d17dab087165bf1dc3e6f6d800593e310044`.
These derive from the completed, independently replayed attribution result,
not from an assumption that the current device remains unchanged.

The [guarded shutdown](scripts/remote-recovery-shutdown.sh) checks that boot,
kernel, A41 record, CPUs 0--9 online/no offline CPUs, exact terminal lifecycle,
three consumed snapshot/frequency attempts, and no device-backed mounts.
It reads observer status only, not temperature or frequency. Only then does it
emit its complete shutdown frame, sync and request power-off. No partition
operation, backup or automatic reboot occurs.

After offline admission is published, prepare the cycle once:

```sh
python3 experiments/2026-09-04-mt6797-thermal-snapshot/scripts/run-recovery.py prepare-cycle --execute
```

The exclusive capture is `artifacts/runtime-captures/thermal-snapshot-recovery-cycle-1`.
The runner binds the exact deployment receipt and published source classification,
flushes a shutdown request marker before transport, and requires the complete
frame plus two consecutive failed bounded TCP probes. A timeout/disconnect is
accepted only with that frame and subsequent unreachability. This is not proof
of electrical rail discharge. The owner then physically selects boot2. As on
the prior session, the visible console may remain absent; USB/netcat at
`10.15.19.82:2323` is the serviceability path.

## One-shot fresh runtime

After physical selection and USB readiness, run once:

```sh
python3 experiments/2026-09-04-mt6797-thermal-snapshot/scripts/run-recovery.py run --execute
```

Without `--execute`, the runner checks its source/receipt inputs without device
access. Runtime also verifies the exact cycle directory inventory, manifest,
request marker, transport metadata, raw frame, source evidence and matching
classification/receipt. Changed, missing, duplicate or extra evidence refuses.
A fresh full pristine frame must pass the inherited exact identity, unique
snapshot interface, read-only sysfs and zero accounting gates. All consumed
boot IDs are refused. This is followed by the one boot-bound program and one
final accounting frame. The new exclusive capture is
`artifacts/runtime-captures/thermal-snapshot-workload-recovery-1`.

A started capture cannot reopen, including interruption before CPU admission.
The generated program and workload request marker are durably written before
transport. Never remove or rename a capture to permit retry. Malformed or
incomplete runtime evidence stops without another device request. Structurally
complete recovery evidence, including shared-boundary comparison rejection,
gets the one declared postflight; rejection remains nonzero. Postflight requires
the same boot/record/serviceability fields, CPUs 0--9 online, exact terminal
lifecycle and exactly three frequency and snapshot attempts. Its ordinary
aggregate remains bounded by 0--58500 mC.

Limits remain three shell sessions, two ordinary thermal reads, three snapshots,
three frequency reads and one four-round owned workload with the unchanged
lifecycle/size/spin ceilings. Pre/post transports have connection 5 s, idle 15 s
and outer 20 s limits. The workload retains idle 120 s and outer 125 s limits,
including its single two-second recovery sleep. Shutdown uses the state limits;
reachability permits at most ten probes with connection/idle 2 s, outer 4 s and
2 s between probes until two failures. No timeout increases hardware work.

The complete comparison cannot pass merely because reported temperature falls.
The missing waiting thermal sample prevents a full baseline comparison, and
conversion age remains unknown. Broader hotplug, cpufreq/OPP, idle/suspend,
longer stress, forced conversion, filter changes and default integration stay
closed. No kernel rebuild is required by this host-only protocol.

## Offline evidence

Host fixtures exercise the actual entrypoint, request-marker persistence,
cycle/receipt refusal, partial transport, interruption and postflight mismatch.
The guarded shutdown is executed with injected device operations; no real
shutdown occurs in those fixtures. Exact-candidate BusyBox validation must run
from a clean published revision with `run-candidate-shell-tests.py --suite recovery`.
Its adapter limitations and source identities must be retained with the result
before any real preparation command above is selected.
