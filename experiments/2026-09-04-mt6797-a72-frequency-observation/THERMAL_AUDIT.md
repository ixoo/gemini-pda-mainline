# Thermal read-path and capture timing audit

## Question and method

Could the rejected cold-cycle rise be explained by a one-second sysfs cache,
a longer workload interval, a simultaneous temperature/frequency assumption,
or missing sensor attribution? This is an offline follow-up to the
[retained comparison failure](results/cold-rise-runtime-thermal-rejected.txt).
It neither changes its thresholds nor authorizes repetition of either workload.

The managed Buildbox tree was read without modification or copying. Its state
matches the production package's source archive and patchset using the recorded
`source_state_hash()` recipe. Full tree integrity verification passed. Exact
file hashes and source locations are in the [source audit](results/thermal-source-semantics-audit.txt).
The two private captures were independently SHA-256 pinned before extracting
only temperatures and frequency-log timestamps with
[scripts/audit-thermal-capture-timing.py](scripts/audit-thermal-capture-timing.py).
Its eight rejecting fixtures are in
[scripts/test-thermal-capture-timing.py](scripts/test-thermal-capture-timing.py).
No device access, kernel build, new source tree, partition operation or load
was needed for this audit.

## Observations from exact source

`temp_show()` calls `thermal_zone_get_temp()`, which locks the thermal zone
and calls `__thermal_zone_get_temp()`, which invokes `tz->ops.get_temp()`.
The MediaTek callback is `mtk_read_temp()`. Thus the sysfs file does not merely
return `tz->temperature` from the one-second background polling interval.
The 1000 ms DT polling delay does not by itself explain these samples.
`CONFIG_THERMAL_EMULATION=y` is compiled, and the helper can override the
returned value if a nonzero emulated temperature has been set. The recorded
host scripts contain no such write; the snapshots do not independently expose
that internal field, so the audit does not claim readback proof of its value.

The MT6797 callback walks six banks with sensor counts 1, 1, 2, 1, 1, 1. For
each bank it locks the driver's shared mutex, selects that bank through
`PTPCORESEL`, reads the configured measurement registers, converts and validates
the readings, and uses the maximum. The final zone is the maximum of all bank
maxima. The samples are sequential, not an atomic cross-bank snapshot. A
read-only sysfs operation still entails normal bank-selector MMIO writes; it
is not a claim of zero peripheral writes or direct unbanked register access.

The V4 conversion returns a multiple of 100 millicelsius. Identical adjacent
values therefore do not establish a cache hit or no underlying temperature
change. The callback reports neither the winning bank/sensor, per-sensor
validity, nor hardware conversion age. It does not request a new conversion
and wait for completion on every sysfs read; it reads measurement registers
maintained by the thermal/AUXADC engine. The source contains sampling-interval
and AHB-poll configuration, but their comments do not prove actual live
conversion cadence or age. That would require a hardware-backed observation.

## Capture timing and limits

The [reproducible extraction](results/thermal-capture-timing-audit.txt) finds:

| Quantity | Warm baseline | Cold-cycle repeat |
| --- | ---: | ---: |
| Pretrigger temperature | 52.8 °C | 35.0 °C |
| Before / during / after | 53.5 / 53.5 / 53.7 °C | 35.6 / 35.7 / 41.3 °C |
| First-to-third frequency-log interval | 0.809021 s | 0.769864 s |
| During-to-after frequency-log interval | 0.704317 s | 0.663594 s |
| Temperature spread | 0.2 °C | 5.7 °C |

The cold run was not longer by these observable frequency-log intervals. Both
executed the same finite payload/round/spin contract; these times do not prove
identical CPU energy, ambient conditions, prehistory or thermal response.
The host/device script reads frequency and then temperature sequentially.
Frequency log timestamps are not temperature-read timestamps, measurement
conversion timestamps or calibrated bounds on the thermal sample's age.
The record labelled `during` is before releasing the writers' start barrier;
both processes are alive, but it is not an interior sample of their hashing
work. `after` is after the writer and peer-reader children complete.

## Conclusion and prospective observation contract

**Rejected:** a simple sysfs one-second polling-cache explanation and an
increased frequency-log interval in the cold run. **Inconclusive:** actual
cold transient versus a changed hottest sensor, stale hardware measurement,
invalid-bank masking or another sampling artifact. The aggregate values do
not resolve these alternatives. The CPU/lifecycle/frequency/RAM repeat result
and the failed thermal comparison both stand.

A decision-changing successor observation needs timestamps bracketing the
thermal callback and per-bank/per-sensor attribution from that same invocation:
converted temperature, validity, bank/sensor identity and the winning maximum.
Reuse values already returned by the normal bank scan; do not introduce extra
MMIO reads, independent bank selection, calibration export or a raw-register
shell probe. Include a bounded generation/attempt counter and complete failure
shape, and prove the aggregate equals the maximum of the recorded valid values.
Treat conversion age as unknown unless the existing hardware contract supplies
a verified freshness bit; timestamps alone cannot invent it.

The initial new gate should be finite observation without a workload, not a
third integrated load. That can validate complete self-consistent attribution
and timing independently before any future workload-bearing candidate is
selected. Polling callbacks must not silently consume the observer's budget,
and any published observer must preserve shared bank locking and normal
production behavior. Design and test the observation ownership and read budget
offline, including malformed/missing/duplicate records, wrong aggregate, counter
reuse, partial failures and disallowed additional register access. Only a
source change that actually adds this evidence justifies a new Buildbox build
and candidate; no compile or device action is selected by this document alone.
Ordered implementation and admission remain in the [roadmap](../../docs/ROADMAP.md).
