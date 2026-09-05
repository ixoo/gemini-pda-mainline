# Passive discriminator decision after recovery

Scope: the named MT6797X Gemini, exact snapshot candidate, and the two published
attribution/recovery traces. This offline review closes the question selected
after the [recovery result](results/recovery-runtime-thermal-rejected.txt): does
the retained observation contract support a new passive experiment that can
separate conversion history from physical temperature response?

**Decision: no such discriminator is established by the reviewed evidence.**
Do not spend another boot on a denser temperature trace or new marker. This is
an admission decision for this contract, not proof that the silicon lacks a
usable signal. No device access, rebuild or new hardware observation occurred.

## Reproducible trace analysis

Run `python3 experiments/2026-09-04-mt6797-thermal-snapshot/scripts/summarize-retained-response.py`
from the repository root. The script pins both published JSON inputs by SHA256,
recomputes their maxima, lists all tied winners, and computes slot deltas and
same-sensor bank spreads. Its output is
[retained-response-summary.json](results/retained-response-summary.json).
It is an immutable evidence summary, not a replacement runtime validator or
an admission classifier. The existing runtime classifiers retain authority.

The stage columns differ between runs and must not be aligned by index:
attribution includes writers-waiting; recovery replaces that point with the
post-completion observation. Initial conditions and boot histories differ too.

| Observation | Attribution | Recovery | Inference limit |
| --- | --- | --- | --- |
| Winning slots, in stage order | 6, 4, 0 | 5, 0, then tied 2/4 | Both include a changed value within slot 0; winner selection alone is insufficient. |
| Sensor-ID-1 spread across banks, mC | 300, 400, 300 | 600, 200, 200 | Same mux/calibration index does not imply a shared sampling time or physical independence. |
| Slot 0 completion rise from pre-workload, mC | 6400 | 5900 | Similar direction across two boots is not a controlled estimate of thermal response. |
| Slot 0 completion-to-recovery change, mC | Not measured | -6500 | The elevated reported value did not persist at the sampled recovery point. |
| Other slots at recovery | Not measured | Six slots total decreased; slot 1 increased by 100 mC | Reject a single identical additive change across all slots; do not infer a particular hardware cause. |

The recovery sensor-ID-1 slots each decreased by 2400 mC in the last interval,
but still differed by 200 mC. Their shared conversion index, separate bank
storage, quantization and unknown ages prevent treating this agreement as four
independent confirmations of physical cooling. Slot 0 ended 600 mC below its
own pre-workload value; neither an equilibrium temperature nor a decay constant
can be inferred from these three samples.

## Why plausible passive extensions do not resolve the question

The [source audit](SENSOR_FRESHNESS_AUDIT.md) establishes converted-range
validity, software scan timestamps and sequential bank reads. The
[register review](REGISTER_CONTRACT.md) establishes no verified per-result
conversion counter or timestamp. Its exact source receipts remain the evidence;
this review did not reinspect or modify a kernel tree.

| Proposed observation | Missing discriminator / decision |
| --- | --- |
| More snapshots or a different wait | Adds output values but no input conversion time or independently known sensor temperature. Both a physical transient and delayed/filtered measurement can produce rising then falling outputs. Reject a causal claim from that trace alone. |
| Compare repeated sensor IDs | Bank-local filter/history and acquisition times are not established; disagreement is not a measured age. Existing spreads already disprove exact equality at every sampled boundary. No new boot justified solely to rediscover this. |
| Expose upper measurement bits | No reviewed semantics bind those bits to fresh thermal conversions. Reject inventing a freshness flag. |
| Read AUXADC ready or thermal interrupt status | Ready belongs to the ADC input transaction; thermal-result association and interrupt read side effects are unresolved. No independent register probe admitted. |
| Read timing/filter configuration | Can compare configuration, but does not measure actual conversion age. A mismatch could justify an ownership investigation, not a physical-versus-history classification. |
| Observe a software generation/timestamp | Counts observer execution, not hardware conversions. No additional causal evidence. |

The ambiguity is not solved by fitting an exponential curve: conversion input,
hardware acquisition times, filter state and physical temperature are all
unobserved. The recorded samples do not identify these separately. This is a
limit of the available variables, not a claim that filtering caused the rise.
A future proposal must add an independently supported measurement contract or
address a specific implementation defect before another boot can be justified.

## Preserved outcome and validation

Both thermal rejections remain unchanged. The recovery protocol omits the
writers-waiting thermal boundary, so full integrated comparison remains
unevaluated. CPU/RAM/frequency successes do not establish thermal protection.
No threshold relaxation, longer workload, broader hotplug, cpufreq/OPP,
idle/suspend or default integration follows from this analysis.

Summary output was independently checked against the published slot arrays;
input identity refusal, Python syntax, local links, diff checks and the
repository manifest-series invariant checks passed. No shell or kernel source
changed; no kernel build was required. Source material was referenced rather
than copied, and no raw ADC values or calibration data were used or published.
Ordered follow-up belongs only to the [roadmap](../../docs/ROADMAP.md).
