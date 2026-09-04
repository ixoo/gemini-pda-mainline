# Cold-cycle comparison using temperature rise

This is a distinct prospective host protocol. The [rejected first protocol](COLD_REPEAT.md)
and its 34.0-degree pretrigger refusal remain unchanged. No past result is
reclassified as an integrated pass. The baseline remains the exact
[published integrated pass](results/zero-divider-runtime-pass-20260904.txt).

## Hypothesis and thermal reasoning

The unchanged candidate can reproduce its bounded lifecycle, topology,
frequencies, accounting, cleanup and 16 RAM hashes across the recorded poweroff
and physical boot2 selection, despite a colder initial thermal state. Identical
absolute temperatures are not the reproducibility claim. Thermal evidence is
now separated into starting temperature, temperature rise from that starting
point, within-run spread, and unchanged absolute upper refusal limits.

The original private pretrigger, whose digest was already published, reports
52800 millicelsius. Its integrated samples were 53500, 53500 and 53700. Thus the
baseline rises from pretrigger are 700, 700 and 900 millicelsius. This reconciles
the earlier mistaken use of a warm runtime sample as a cold-start minimum.
The raw baseline pretrigger SHA-256 remains
`aabc444b8336c94387a42adb771ff8aa515c6b2504bcba642624653fba34d0cc`.

The revised policy admits initial values from 0 through 58500 millicelsius.
Zero retains the original production validator's nonnegative plausibility
boundary; 58500 preserves the first cold protocol's upper refusal boundary.
It does not invent a silicon operating limit or claim cold-environment support.
For each integrated sample, require all of:

- nonnegative temperature and the unchanged corresponding absolute upper
  limit: 58500, 58500, 58700 millicelsius;
- its rise from this run's pretrigger within 5000 millicelsius of the
  corresponding baseline rise (700, 700, 900); and
- at most 5000 millicelsius spread across the three integrated samples.

These deliberately conservative experiment refusal rules permit a common
cold offset while still rejecting excessive heat, rapid cooling, rise, spread
and malformed evidence. The 5-degree margin is the existing experiment's
comparison allowance, not a statistically derived confidence interval or a
validated hardware safety limit. One warm run does not establish such limits.
The device's finite program remains unchanged; thermal comparison is performed
on the completed bounded capture, not by hardware trips or cooling control.

## Selected unspent boot and action budget

The selected boot is exclusively `1afc43e5-d4cd-4df6-a0e1-431eeef140df`, release
`7.1.3-gemini-a72-frequency-thermal`, candidate
`ea2aae419220b3c2ea11780f9c91dbb51d509286cd76d2ba1741d9e08e837c9c`.
The [Gemian shutdown receipt](results/cold-repeat-shutdown.txt) and owner-reported
physical selection establish the cycle. Both baseline and recovery boot IDs
remain forbidden. The failed pretrigger spent zero admissions, observer reads
or workloads, so this new protocol can use the unspent workload attempt on
that same independently booted session without spending another device boot.
A new pristine frame is mandatory after publication. Do not reuse the old
frame, admit another boot, or infer pristine state from the earlier result.
Passive elapsed time is not controlled; this is power-cycle repeatability,
not a timed immediate-after-power-on thermal experiment.

Before triggering, require the original exact candidate/deployment/record and
release checks, CPUs 0--7 online with CPU8/CPU9 offline, armed zero-consumption
lifecycle, zero observer accounting, read-only sysfs, thermal serviceability,
and the revised initial range. The runtime program then rechecks boot identity
and lifecycle before its sole trigger. This contract does not re-open the
retired cold-repeat collector/runner or permit warming load.

The new capture directory refuses overwrite. The runtime builder and raw
classifier remain hash-pinned and byte-unchanged: one admission, one CPU9-only
down/restore, three frequency records, four rounds per A72, original payload
and spin bound, exact affinity, all topology fields, independent scheduler
progress, 16 exact hashes, cleanup, and no storage writes/retries/reboot.
Compare every summary field against the pinned baseline; only positive
accounting deltas and temperatures under the explicit rules may vary.
All frequencies and action counts must match. A missing or duplicated field,
raw classifier failure, cold-cycle mismatch or thermal anomaly rejects.

After publishing tooling, hypothesis and offline fixtures, run from repository
root exactly once:

```sh
experiments/2026-09-04-mt6797-a72-frequency-observation/scripts/collect-cold-rise-pretrigger.sh \
  --deployment-summary artifacts/runtime-captures/a72-frequency-thermal-zero-divider-attempt-1/deployment-summary.txt \
  --output artifacts/runtime-captures/a72-frequency-thermal-cold-rise-1
experiments/2026-09-04-mt6797-a72-frequency-observation/scripts/run-cold-rise-runtime.sh \
  --capture artifacts/runtime-captures/a72-frequency-thermal-cold-rise-1
```

Success establishes two distinct power-cycle executions of the exact finite
integrated predicate, with temperature-rise comparison; it does not prove
statistical reliability, equal ambient conditions or sustained thermal safety.
Any refusal or failure preserves evidence and closes this attempt without
retry. A missing/changed session requires a newly selected cycle, never a
silent replacement. cpufreq/OPP, broader hotplug, idle, suspend, longer stress,
default-profile integration and upstream-readiness claims remain closed.
Ordered follow-up is owned by the [roadmap](../../docs/ROADMAP.md).
