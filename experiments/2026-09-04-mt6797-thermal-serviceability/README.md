# Experiment: MT6797 thermal serviceability

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-04-mt6797-thermal-serviceability` |
| Status | `running`; first boot inconclusive pre-transport, retained-stage discriminator selected |
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
- `scripts/validate_package.py`: exact Buildbox package, linkage, and structural
  base/service DT validator.
- `scripts/build_candidate.sh` and `scripts/validate_candidate.py`: independent
  deterministic Android-v0 construction and exact selected-candidate gate.
- `scripts/remote_observe.sh`, `scripts/classify_observation.py`, and
  `scripts/collect_runtime.sh`: one bounded read-only USB/netcat runtime frame.
- `scripts/install_boot2.sh`: live-GPT-resolved, full-readback-verified guarded
  `boot2` install followed by clean shutdown; no fresh backup.
- `scripts/request_native_reboot.sh`: post-pass native reboot to changed-ID
  Gemian without partition access.
- `scripts/test_runtime_tools.py`: positive, rejection, source-integrity, and
  static safety tests for the runtime path.

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
- The owner reported that the framebuffer console was working on the boot used
  for installation. Exact preflight identity subsequently proved that boot was
  known-good Gemian `3.18.41+`, not this thermal candidate, so the observation
  is not attributed to this experiment and is not thermal proof.
- Buildbox generated and replayed normal patches `0519` and `0520` from exact
  pushed revision `ea657e202935...` and prepared source state
  `b4dae5f2b949...`. The three-path source validator passed with one zone,
  zero trips, zero cooling maps, disabled standalone AUXADC, and the SoC node
  still default-disabled. Strict Checkpatch reported zero errors, warnings, or
  checks. See [results/patch-generation-20260904.txt](results/patch-generation-20260904.txt).
- Buildbox built the clean pushed revision `b023e88940f098...` as exact release
  `7.1.3-gemini-mt6797-thermal-serviceability`. Independent package validation
  pinned the source, patchset, configuration, kernel, System.map, base DT, and
  service DT identities; required PWRAP, MT6351, eMMC, ATAG NVMEM, reset, and
  thermal symbols are linked. The service DT contains PWRAP reset input 1,
  thermal reset input 0, exactly one trip-free and cooling-free zone, and a
  disabled standalone AUXADC consumer. See
  [results/offline-package-20260904.txt](results/offline-package-20260904.txt).
- Two independent Android-v0 assemblies matched byte-for-byte. The selected
  raw candidate is `ea54021dbe1a...` (7,553,024 bytes), and its exact 16 MiB
  zero-padded `boot2` image is `6f3d8d6e94ff...`. It contains the packaged
  service DT and the retained serviceability netcat initramfs without
  transformation. See
  [results/offline-candidate-20260904.txt](results/offline-candidate-20260904.txt)
  and the fixed [preboot hypothesis](results/preboot-hypothesis-20260904.txt).
- The complete runtime, installer, and native-recovery tooling passes one
  positive and fifteen decision-changing rejection fixtures, Shellcheck, pinned
  source hashes, static read/write boundaries, and an independent reconstruction
  of the selected candidate. See
  [results/offline-runtime-tooling-20260904.txt](results/offline-runtime-tooling-20260904.txt).
- The guarded installer resolved logical `boot2` from the live GPT as inactive,
  unmounted `/dev/mmcblk0p30`, recorded predecessor `5c7429b297c...`, wrote the
  selected candidate, flushed it, and obtained exact full-partition readback
  `6f3d8d6e94ff...`. No fresh backup or other partition write occurred. The
  device then shut down cleanly for owner selection. See
  [results/deployment-attempt-1-20260904.txt](results/deployment-attempt-1-20260904.txt).
- The observer was armed before the owner selected `boot2`, but the exact
  mainline USB interface never appeared. The device instead returned on fresh
  Gemian boot ID `f54c4692...`; pstore was empty and the exact candidate still
  occupied inactive `boot2`. Gemian reported its usual watchdog-style boot
  tokens, which are not treated as causal under the existing visual/reboot
  evidence caution. No mainline identity, thermal binding, or temperature was
  captured, so the candidate is retired as inconclusive and must not be
  repeated. Recovery also found the otherwise-unused 4 KiB ramoops record 5 at
  `0x44415000` in exact pstore-empty state. See
  [results/runtime-attempt-1-inconclusive-pre-transport-20260904.txt](results/runtime-attempt-1-inconclusive-pre-transport-20260904.txt).
- A later owner-reported start/return event was watched for four minutes and
  retained the same Gemian boot ID `f54c4692...` before, throughout, and after
  the event. It exposed no mainline USB and no pstore file, so Linux did not
  reboot and this is explicitly not a second candidate attempt. See
  [results/selection-event-2-not-a-boot-20260904.txt](results/selection-event-2-not-a-boot-20260904.txt).

## Analysis

The exact Buildbox package and deterministic boot candidate pass their offline
identity, linkage, configuration, structural DT, container, and padding gates.
This is construction evidence only; it does not prove
that calibration, reset, clocks, bank preparation, first samples, registration,
or temperature reads work on hardware.

The install and readback gate passed, but the first runtime attempt produced no
mainline transport or durable stage evidence. It therefore neither validates
nor localizes thermal activation. An unused, pstore-empty retained record is
available for a decision-changing derivative that records entry and ordered
thermal stages before transport; this is stronger than either a same-artifact
repeat or screen-state inference.

## Conclusion

`inconclusive`: the exact first candidate is retired after a pre-transport
return to changed-ID Gemian. No thermal hardware claim has been made.

## Follow-up

Add one default-off, empty-only, CRC-valid two-copy thermal-stage ledger in
retained record 5 and instrument the existing transaction without changing its
hardware order. The next attempt must distinguish kernel entry, calibration,
reset, clocks, global idle, bank prepare/commit/release, first samples, zone
registration, and explicit failure return. It retains every current exclusion
and does not authorize CPU admission, OPP/cpufreq, load, idle, suspend, trips,
or cooling.
