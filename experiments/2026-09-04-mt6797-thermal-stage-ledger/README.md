# Experiment: MT6797 thermal-stage retained ledger

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-04-mt6797-thermal-stage-ledger` |
| Status | KUnit compile and 15-case QEMU runtime passed; production build pending |
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

## Observations

- Buildbox generated and normally replayed patches `0521`--`0523` from clean
  pushed revision `051e1b917c8b...` and exact prepared source state
  `53247e0ff37e...`. The source validator proved 23 operation identities, 64
  ordered transaction trace events, zero cleanup trace events, six ledger
  KUnit cases, nine total transaction cases, and no CPU or storage action.
  Strict Checkpatch reported zero errors, warnings, or checks. See
  [results/patch-generation-20260904.txt](results/patch-generation-20260904.txt).
- The first exact KUnit-profile build from admitted revision `210067af8aad...`
  stopped while compiling the record-5 owner because its translation unit used
  `MODULE_DESCRIPTION` and `MODULE_LICENSE` without including
  `<linux/module.h>`. No KUnit, device, or storage action occurred. The
  experiment template now carries that explicit include. See
  [results/kunit-build-compile-failure-20260904.txt](results/kunit-build-compile-failure-20260904.txt).
- Buildbox regenerated and normally replayed corrected patches `0521`--`0523`
  from clean pushed revision `2893813feada...`. The corrected review again
  passed its source validator and strict Checkpatch with zero errors, warnings,
  or checks; the only source change is the explicit module-header include and
  consequent deterministic patch identities. See
  [results/patch-regeneration-20260904.txt](results/patch-regeneration-20260904.txt).
- Exact pushed revision `22ff6be964b9...` compiled and packaged the focused
  KUnit profile on Buildbox with all package and provenance checks passing. See
  [results/kunit-buildbox-20260904.txt](results/kunit-buildbox-20260904.txt).
- The fetched Image then ran in isolated four-vCPU AArch64 QEMU with networking
  disabled. Both intended suites and all 15 named cases passed with zero
  failures or skips; the run performed no MMIO, retained-RAM, CPU, storage, or
  device action. See
  [results/kunit-qemu-20260904.txt](results/kunit-qemu-20260904.txt).
