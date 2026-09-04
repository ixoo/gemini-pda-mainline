# Experiment: MT6797 thermal-stage retained ledger

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-04-mt6797-thermal-stage-ledger` |
| Status | `pre-build` |
| Subsystem | MT6797 thermal probe and ordered AUXADC transaction |
| Device variant | Planet Computers Gemini PDA, MT6797 |
| Date(s) | 2026-09-04 |
| Tracking goal | thermal observability prerequisite for sustained CPU8/CPU9 validation |

## Hypothesis

The first thermal-serviceability candidate returned before USB/netcat without
durable attribution.  A default-off, empty-only record-5 ledger can identify
the last MT6797 thermal probe boundary without changing the transaction's
hardware order.  One boot of the resulting exact candidate will distinguish
pre-probe entry, calibration and resource acquisition, every reset/clock/
AUXADC/bank/sample operation, zone registration, and explicit probe return.

## Safety and exclusions

Patch generation and builds run only on Buildbox from an exact clean pushed
revision.  Hardware-free tests use injected memory and callbacks.  The runtime
ledger writes only the independently empty 4 KiB retained-RAM record 5 and is
enabled only in the named isolated profile.  It never clears or repairs a
nonempty record and performs no device-storage write.

Installation, when reached, is limited to the standing guarded inactive
live-GPT-resolved `boot2` workflow with full-partition readback and clean
shutdown.  The project-wide backup remains the recovery source; no new device
backup is made.  CPU admission, CPU hotplug, load, cpufreq/OPP, idle, suspend,
thermal trips, cooling, and writes to primary boot or any other partition stay
outside this experiment.

## Planned procedure

1. Generate three normal patches from prepared source state `53247e0f...`: the
   record-5 owner, its injected-memory KUnit suite, and optional thermal probe /
   transaction instrumentation plus trace tests.
2. Prove the existing forward hardware order and cleanup remain unchanged when
   tracing is absent, and prove exact before/after ordering and fail-closed
   behavior when tracing is active.
3. Admit the patches in canonical order and audit every manifest profile.
4. Build the KUnit and production profiles on Buildbox from their exact clean
   pushed revision; fetch only validated packages.
5. Construct and independently reproduce the Android-v0 boot candidate, apply
   the complete offline identity and safety gates, install only to guarded
   inactive `boot2`, verify full readback, and shut the device down.
6. Pre-arm recovery, select `boot2` once, then decode record 5 from changed-ID
   Gemian or capture exact USB/netcat runtime if the probe completes.

The full wire, instrumentation, and fixed result map are in
[DESIGN.md](DESIGN.md).  The retired parent and its inconclusive result remain
owned by the [thermal-serviceability experiment](../2026-09-04-mt6797-thermal-serviceability/README.md).
