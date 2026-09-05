# Frozen attribution host protocol

This protocol binds the [attribution design](WORKLOAD_ATTRIBUTION.md) to one
fresh cycle and one bounded execution. Protocol revision `70cc45e5` is published and the
[final exact-shell fixture pass](results/final-protocol-shell-pass.json) now
covers SIGPIPE cleanup and the host entrypoint. The guarded shutdown command
below is selected after publication of this result.
The currently consumed no-workload boot cannot run this workload.

## Hypothesis and limits

Reuse the deployed candidate `666961b6...`, release
`7.1.3-gemini-thermal-snapshot`, and its exact A41 record. The new evidence is
per-bank converted temperature, tied/first winning slots and callback timing
at post-lifecycle, writers-waiting and workers-complete boundaries. A rise in
one slot and a change in winning slot are distinguishable observations. They
do not establish conversion freshness or explain a physical cause by themselves.
The prior thermal comparison remains rejected.

The program keeps one admission, one CPU9 down/restore, three frequency reads,
three snapshots, four rounds per writer/peer reader, the original payload and
spin ceiling. It performs no partition access, backup, cpufreq/OPP change,
additional hotplug, idle, suspend, longer stress or default integration.
The initial aggregate and every converted snapshot slot must be 0--58500
millicelsius. Preserve rise targets 700/700/900 with allowance 5000 and aggregate
spread at most 5000. Refusal thresholds do not provide hardware protection.

## Source and cycle binding

The [host entrypoint](scripts/run-attribution.py) pins every local dependency;
the builder and classifier additionally pin their inherited dependencies.
The exact full-readback deployment receipt is hash-bound. Cycle preparation
accepts only the consumed no-workload boot, its exact kernel/record, unchanged
pristine lifecycle, offline A72s, zero frequency attempts and three already
consumed snapshot attempts. It reads status, not a temperature or frequency
observer. The [shutdown program](scripts/remote-attribution-shutdown.sh) checks
that no device-backed filesystem is mounted, emits the attributable request
frame, syncs and requests kernel power-off through the RAM initramfs shell.

Run from the repository root only after the offline gates are published:

```sh
python3 experiments/2026-09-04-mt6797-thermal-snapshot/scripts/run-attribution.py prepare-cycle --execute
```

The exclusive cycle capture is
`artifacts/runtime-captures/thermal-snapshot-attribution-cycle-1`. Its shutdown
request is flushed before transport. The complete request frame and two
successive failed bounded TCP probes are required for a cycle receipt; a
connection reset or timeout is acceptable only with that complete frame and
subsequent unreachability. This is request/disconnect evidence, not measurement
of electrical rail discharge. No automatic reboot or new partition write occurs.
The owner then physically selects boot2 using the established sequence. The
screen may remain blank as reported on the prior boot; USB/netcat at
`10.15.19.82:2323` is the authoritative serviceability path.

## One bounded runtime

After physical selection:

```sh
python3 experiments/2026-09-04-mt6797-thermal-snapshot/scripts/run-attribution.py run --execute
```

Without `--execute`, either mode validates its available source/receipt inputs
without contacting the device. Runtime additionally verifies the complete cycle
manifest, request seal, raw shutdown frame and matching receipt/classification.
A changed or incomplete cycle capture refuses. Runtime uses only
`artifacts/runtime-captures/thermal-snapshot-workload-attribution-1`; an existing
capture always refuses reopening, even if interrupted before CPU admission.
Never rename or remove a capture to bypass refusal.

There are at most three USB shell sessions: a new full pristine frame, the
single boot-bound program, and a final accounting frame. Preflight requires a
new boot distinct from deployment and all consumed boots, exact identity,
full pristine lifecycle, CPUs 0--7 online/8--9 offline, zero observers, unique
root-only snapshot pair and read-only sysfs. The host records and flushes the
generated program and workload request before starting its transport session.
It never retries a request on timeout, partial data or failure.

Pre/post state sessions each permit one ordinary aggregate read, with a
five-second connection limit, fifteen-second idle limit and twenty-second
outer timeout. The workload keeps the inherited 120-second idle limit with a
125-second outer timeout; these transport limits do not increase any device
work count. Cycle preparation uses the same bounded state-session transport and
at most ten TCP probes, each with a two-second connection/idle limit and
four-second outer limit, separated by two seconds until two failures occur.

Malformed or incomplete runtime data stops without postflight. A structurally
complete runtime, including a thermal-comparison rejection, gets the one declared
postflight frame so final accounting is retained. It requires the same boot,
record, serviceability fields and read-only sysfs; CPU0--9 online; exactly three
frequency and snapshot attempts; and lifecycle state byte-equal to the validated
terminal state captured immediately after the CPU transaction. Its ordinary
aggregate must also remain 0--58500. Thermal rejection remains nonzero after a
successful postflight; a final-state mismatch rejects the whole run.

The finite worker cleanup now catches SIGPIPE as well as HUP/INT/TERM and defers
caught exits during child registration. It cooperatively cancels and reaps owned
workers before file removal. A foreground RAM operation may complete first.
Transport loss does not prove immediate remote cancellation or cleanup; only
complete evidence can establish the runtime cleanup predicate. Uncatchable
termination or stalled kernel IO has no cleanup guarantee. Partial evidence and
attempt seals remain permanently retained; no recovery workload is admitted.


## Final offline admission result

The exact-candidate shell run passed all worker/observer fixtures, four caught
signals including SIGPIPE, the registration race and the real host entrypoint
with injected USB. Seventeen started captures refused restarting; malformed,
changed and incomplete evidence rejected. Temporary artifacts and checkout were
removed. The source and image are frozen; no build, partition write or extra
read on the consumed mainline session was needed for validation. Cycle
preparation and a fresh pristine frame remain mandatory before the workload.
