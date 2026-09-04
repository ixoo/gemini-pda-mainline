# Experiment: MT6797 thermal serviceability

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-04-mt6797-thermal-serviceability` |
| Status | `running`; source and offline candidate gates in progress |
| Subsystem | MT6797 thermal controller, AUXADC transaction, reset, and NVMEM calibration |
| Device variant | Planet Computers Gemini PDA, MT6797 |
| Date(s) | 2026-09-04 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | CPU8/CPU9 prerequisite chain |

## Question or hypothesis

Can the named Gemini complete the source-proven thermal reset, ordered
thermal/AUXADC transaction, valid-calibration gate, all-six-bank first-sample
gate, and thermal-zone registration while preserving the accepted PWRAP,
MT6351, eMMC, USB/netcat, framebuffer-console, and eight-A53 serviceability
baseline?

The unique device-side kernel/DT hypothesis is the first activation of the
existing MT6797 thermal consumer with reset input 0 and one policy-free thermal
zone. The standalone AUXADC platform consumer remains disabled.

## Provenance and environment

- Parent production gate: [ordered MT6797 thermal transaction](../2026-09-04-mt6797-thermal-transaction/README.md).
- Reset prerequisite: [source-proven infracfg resets](../2026-09-03-mt6797-infracfg-reset-repair/README.md).
- Runtime control: [PWRAP reset serviceability](../2026-09-04-mt6797-pwrap-reset-serviceability/README.md).
- Kernel profile: `mt6797-thermal-serviceability`, canonical
  `patches/series`, Buildbox only.
- Boot target: inactive live-GPT-resolved logical `boot2` after every offline
  package, DT, initramfs, Android-v0, classifier, and safety gate passes.

Exact build, package, candidate, partition, boot, temperature, and recovery
identities are recorded below and in `results/` as each gate completes.

## Safety assessment

Patch generation and kernel construction run only on Buildbox and cannot
access the device. The SoC description adds the exact reset input already
proved to translate to infracfg SET/CLEAR `0x120/0x124`. The isolated board
variant enables only the thermal consumer and a trip-free, cooling-free zone;
the standalone AUXADC node stays disabled. The transaction never changes the
AUXADC power bit, requests no IRQ, and closes all acquired state on failure.

Any installation uses only the standing guarded `boot2` workflow: resolve the
live GPT, reject the active root, mounts, holders, size mismatch, unstable
power, or ambiguous identity, then write once, flush, require a full-partition
readback checksum, and shut down. No fresh partition backup is made. Primary
`boot`, preloader, NVRAM, GPT, firmware, and whole-device writes are outside
scope.

Unexpected heat, charging anomalies, storage errors, recovery changes, or a
watchdog loop are stop conditions. No load, CPU8/CPU9 admission, frequency
change, idle, suspend, trip, cooling, or storage write is permitted.

## Associated code

- `scripts/source_edits.py`: deterministic two-commit DT source edit.
- `scripts/validate_source.py`: exact reset, activation, and isolation gate.
- `scripts/validate_patches.py`: generated-patch boundary validator.
- `scripts/generate-on-buildbox`: pinned source, replay, and strict
  Checkpatch lane.

Candidate, package, runtime, recovery, and installer tooling is added only
after the source patches and focused Buildbox profile pass their offline gates.

## Procedure

1. Generate two normal patches from the exact prepared source: add the
   source-proven thermal reset while leaving the SoC node disabled, then add a
   dedicated Gemini serviceability DT that enables only the thermal consumer
   and one zone without trips or cooling maps.
2. Admit the patches to the canonical series and audit every manifest profile.
3. Build the exact clean pushed profile on Buildbox and fetch only its validated
   package.
4. Construct and independently validate a deterministic Android-v0 candidate
   using the packaged serviceability DT and the retained serviceability
   initramfs.
5. Install only to guarded inactive `boot2`, require full readback, and shut
   down for one owner-selected boot.
6. In one bounded read-only frame, require exact identity, NVMEM provider,
   thermal binding, a plausible nonzero temperature, runtime-DT reset and
   enablement, PWRAP/MT6351/eMMC, CPUs 0--7, USB/netcat, and console
   serviceability. Then request native reboot and confirm changed-ID Gemian plus
   unchanged `boot2`.

The decision branches are fixed before boot: a complete frame advances the
CPU8/CPU9 prerequisite chain; a calibration-provider failure returns to NVMEM;
a reset/clock/idle/first-sample failure returns to that transaction boundary;
a downstream serviceability regression returns to its named provider. Missing
exact identity or transport is inconclusive and authorizes no repeat of the
same artifact.

## Observations

- The upstream binding permits a single unnamed reset and a thermal zone with
  no trips or cooling maps. The driver acquires reset index 0 with
  `devm_reset_control_get_exclusive(..., NULL)`.
- The prepared source already uses symbolic PWRAP reset input 1. The thermal
  node lacks its required reset and remains disabled; standalone AUXADC is also
  disabled.
- The owner reports that the framebuffer console is working on the currently
  running boot. This observation is not attributed to this experiment until
  exact runtime identity is collected, and it is not thermal proof.

## Analysis

Pending exact Buildbox and hardware evidence.

## Conclusion

`inconclusive` while the source, package, candidate, and single runtime gates
are in progress. No thermal hardware claim has yet been made.

## Follow-up

On a complete pass, use the thermal serviceability evidence only as a
prerequisite for the separately gated CPU8/CPU9 path. It does not itself
authorize CPU admission, OPP/cpufreq, load, idle, suspend, trips, or cooling.
