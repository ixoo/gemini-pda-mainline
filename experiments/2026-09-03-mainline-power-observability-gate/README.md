# Experiment: current-mainline power-observability gate

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-03-mainline-power-observability-gate` |
| Status | `running` |
| Subsystem | Cortex-A72 thermal, frequency, and calibration observability |
| Device variant | Named Gemini PDA development unit |
| Date(s) | 2026-09-03 |
| Investigator(s) | Codex and device owner |
| Tracking issue | None |

## Question or hypothesis

Can the exact topology-preserving CPU8/CPU9 candidate provide attributable
temperature and frequency state before any longer workload is admitted?

The first falsifiable sub-question is narrower: does this current boot path
preserve the structurally valid LK devinfo property and bind the existing
read-only calibration provider, without exposing calibration values or
touching the disabled thermal/AUXADC blocks?

## Provenance and environment

- Linux package commit: `8ae7643c3be90349fbad17e97c9babbb75747f12`.
- Implementation commit: `315f361d6b140391fe4f9159266ea0b964dfa1ac`.
- Patchset SHA-256: `413456201b2f489ca1c56b6e88d14976e185b05800037a3821239a7c9fe15411`.
- Resolved configuration SHA-256:
  `a76237ab140491d0c11dd9560cf3eb11176476c910f0a5c889c70d1cf324e70a`.
- Composed DTB SHA-256:
  `1f34ddb965a1f14ef1e4cd3f68589b7a93d8186c8045c2804bd16beed9bc92c7`.
- Installed full-`boot2` SHA-256:
  `6ba8c9538dcff6559066088da943d96aaa8ad32d10a93b34c8bbeddc97464f75`.
- Boot path: owner-selected inactive logical `boot2`; direct USB netcat shell
  at `10.15.19.82:2323`.

## Safety assessment

The runtime probe is read-only. It opens one bounded USB/netcat session, reads
kernel identity, CPU masks, existing admission status, flattened-DT metadata,
provider-binding metadata, and counts existing thermal/cpufreq class entries.
It hashes the complete LK property but never emits it, reads no NVMEM binary
cell, prints no calibration word, executes no CPU admission/hotplug or load,
and accesses no block device. Any rejected gate ends the attempt.

The exact candidate remains installed, so no partition write or fresh backup
is needed. The recovery watchdog, not the observer, returns the device to
Gemian.

## Associated code

- `scripts/remote-observe.sh` — device-side metadata-only observer.
- `scripts/classify-observation.py` — strict identity, redaction, binding, and
  interface classifier.
- `scripts/collect-runtime.sh` — changed-boot-aware, exact-interface host
  orchestrator with one netcat session.
- `scripts/test-classifier.py` — ten rejection mutations.
- `scripts/test-tooling.py` — source-pin, action-boundary, and transport audit.
- `results/exact-candidate-offline-audit-20260903.txt` — exact package/config/DT
  audit and decision.
- `results/tooling-validation-20260903.txt` — syntax, ShellCheck, source pins,
  ten rejected mutations, and the no-write/no-trigger boundary.

## Procedure

1. Audit the exact validated package configuration and composed DTB offline.
2. Refuse a longer or more intense load if either temperature or frequency is
   not attributable.
3. From a fresh owner-selected `boot2`, make one read-only USB/netcat capture.
4. Require a new mainline boot ID, pristine zero-trigger admission state, exact
   record identity, the 412-byte opaque LK-property shape, and live binding of
   the root-only read-only NVMEM provider.
5. Record whether thermal zones and cpufreq policies are absent, without
   enabling their disabled hardware nodes.

## Observations

The offline audit proves `CONFIG_CPU_FREQ` and `CONFIG_THERMAL` are unset in
the exact candidate. The DT keeps both `mediatek,mt6797-thermal` and
`mediatek,mt6797-auxadc` disabled, contains no thermal zones, and gives the A72
nodes neither `operating-points-v2` nor `cpu-supply`. The built-in
`CONFIG_NVMEM_MTK_ATAG_DEVINFO=y` provider and its read-only DT node are
present. The A72 `clock-frequency = 2288000000` property is descriptive DT
data, not live-rate evidence.

The first physical start reported during preparation produced neither the
exact USB interface nor a changed Gemian boot ID. Gemian remained on boot ID
`d45c1790-64d0-41bb-b50f-7a3298034f6a`; this is a no-cycle observation, not a
kernel failure. Gemian was then shut down cleanly for an attributable retry.

## Analysis

The exact candidate cannot provide the requested temperature/frequency frame;
repeating or extending load would add risk without answering the safety
question. A fresh boot is still justified because it can independently prove
whether the already-built calibration provider actually binds on the current
supported boot path. A bound provider implies its parser accepted the LK
property's exact header, length, tag, and trailer while retaining only the
three ordered thermal words. Failure to bind selects provider/DT population
repair before thermal-controller work.

## Conclusion

`confirmed` for the offline scope: thermal and frequency observability are
absent from the exact candidate, so load duration or intensity must not be
increased. Live calibration-provider binding remains pending one fresh,
read-only boot.

## Follow-up

After a passing provider-binding observation, implement and hardware-free test
an MT6797-specific fail-closed thermal-calibration policy, then resolve the
AUXADC register/idle contract before enabling thermal hardware. Do not add
trips, cooling, OPP/cpufreq, or more load in that step.
