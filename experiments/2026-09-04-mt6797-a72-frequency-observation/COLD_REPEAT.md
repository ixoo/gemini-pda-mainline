# Distinct cold-boot repeat protocol

This protocol is closed to retry after its [cold pretrigger rejection](results/cold-repeat-pretrigger-rejected.txt).
The following is the preserved prepublished contract, not authorization for
another attempt.

## Hypothesis and attribution

On the named Gemini PDA, the unchanged kernel, DT, configuration, and exact
candidate from the [published pass](results/zero-divider-runtime-pass-20260904.txt)
will reproduce stage 18, 4+4+2 topology, fixed live frequencies, finite RAM
integrity and independent CPU8/CPU9 progress across a clean power-off and new
physical boot2 selection. This is one additional boot, not permission to rerun
the consumed first session or retry a failed second session.

The padded candidate remains
`ea2aae419220b3c2ea11780f9c91dbb51d509286cd76d2ba1741d9e08e837c9c`;
release remains `7.1.3-gemini-a72-frequency-thermal`. Candidate attribution
combines the existing full-partition deployment readback with exact runtime
record identity and release; it does not claim a new partition read or runtime
measurement of the whole image. No intervening partition write is permitted.
The new boot ID must differ from both deployment and baseline
`50e87880-b73a-46c2-9914-cabe34acff8c`.

The [baseline classifier output](results/cold-repeat-baseline-classification.txt)
is byte-identical to the private output whose SHA-256 was already published.
The additional comparator pins that digest and the original pretrigger,
runtime classifier and runtime builder. Their inherited validators continue to
check exact lifecycle call budgets, affinity, all topology fields, worker
bounds, all 16 hashes, independent accounting, cleanup and no storage writes.

## Admission and comparison

Publish this protocol and offline results before shutdown. The device has
already returned to Gemian, observed on recovery boot
`a59a6e44-5ff2-453e-a78b-4bbba106ed53`, release `3.18.41+`. The mechanism of the
intervening return was not captured; do not claim a host-observed power-off of
the baseline mainline session. A fresh read-only full-partition checksum of
live-GPT-resolved inactive boot2 matches the unchanged candidate.

Record a clean Gemian power-off request and observed SSH disappearance in
`results/cold-repeat-shutdown.txt`, binding that exact recovery boot and boot2
checksum. No partition write or backup is needed. The fresh mainline ID must
also differ from this recovery ID. Physical boot2 selection follows shutdown.
The owner supplies the physical selection; the host preserves shutdown,
disconnect, candidate and fresh identity evidence. Electrical rail discharge
is not measured. Normal Gemian shutdown may flush its filesystem; the
no-storage-write workload claim applies to the mainline measurement, not to
ordinary Gemian shutdown bookkeeping.

The distinct collector and runner use only
`artifacts/runtime-captures/a72-frequency-thermal-cold-repeat-1`, refuse existing
captures/attempts and never retry a trigger. The collector and runner both
apply the additional gate to raw pretrigger evidence. Require CPUs 0--7 online,
CPU8/CPU9 offline, armed zero-execution lifecycle, zero observer attempts,
read-only sysfs, exact record/release, and a valid shutdown receipt. Initial
temperature must be 48.5--58.5 degrees C; outside that deliberately conservative
baseline envelope, stop before admission, without warming load or polling.

Run from the repository root after physical selection:

```sh
experiments/2026-09-04-mt6797-a72-frequency-observation/scripts/collect-cold-repeat-pretrigger.sh \
  --deployment-summary artifacts/runtime-captures/a72-frequency-thermal-zero-divider-attempt-1/deployment-summary.txt \
  --output artifacts/runtime-captures/a72-frequency-thermal-cold-repeat-1
experiments/2026-09-04-mt6797-a72-frequency-observation/scripts/run-cold-repeat-runtime.sh \
  --capture artifacts/runtime-captures/a72-frequency-thermal-cold-repeat-1
```

The device program is unchanged: one admission, one CPU9 down/restore, exactly
three frequency observations, four rounds per A72 writer/peer reader, and the
same payload and spin ceiling. The host reclassifies the complete raw transcript
before comparison, rather than trusting an edited success summary. Every
baseline summary field is mandatory; duplicates and unexpected fields reject.
All categorical, frequency and action-budget fields must match exactly.
CPU8/CPU9 deltas must independently remain positive and at most 10000 ticks;
this is an evidence plausibility bound, not additional runtime allowance.
Temperatures must stay within 5 degrees C of each corresponding baseline sample
and within a 5-degree within-run spread. These are comparison refusal thresholds,
not validated silicon safety limits. The unchanged finite device protocol does
not implement thermal trips; comparison occurs after that bounded transaction.

Success establishes two-boot reproducibility only for this exact finite
protocol. Any missing field, reused identity, budget increase, frequency change,
thermal anomaly, workload/cleanup failure or incomplete USB frame rejects the
repeatability claim; retain the evidence and select analysis through the
[roadmap](../../docs/ROADMAP.md). Do not trigger again or widen the load.
cpufreq/OPP, broader hotplug, idle, suspend, longer stress and default-profile
integration remain closed.

## Validation and visible behavior

The comparison and pristine mutation fixtures are in
[scripts/test-cold-repeat.py](scripts/test-cold-repeat.py); inherited suites
continue to validate materialized workload and raw transcript rejection.
No kernel source, manifest, patch, DT or configuration changes are needed.
No kernel build or device filesystem backup is performed.

After clean shutdown Gemian SSH disappears and the device powers down. The owner physically
selects boot2 using the established hardware sequence. The retained console
may show boot text; screen appearance alone does not admit the experiment.
The expected authoritative service is USB/netcat at `10.15.19.82:2323`, initially
with eight A53 CPUs online and both A72 CPUs offline. The host then collects the
pristine frame and performs at most the single bounded repeat above.
