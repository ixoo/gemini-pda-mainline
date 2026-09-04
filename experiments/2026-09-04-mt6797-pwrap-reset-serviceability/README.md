# Experiment: MT6797 PMIC-wrapper reset serviceability

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-04-mt6797-pwrap-reset-serviceability` |
| Status | `completed`; exact runtime serviceability and recovery passed |
| Subsystem | MT6797 infracfg reset, PMIC wrapper, MT6351, and eMMC |
| Device variant | Planet Computers Gemini PDA, MT6797 |
| Date(s) | 2026-09-04 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Thermal/AUXADC transaction prerequisite |

## Question or hypothesis

Does the named Gemini retain the accepted PMIC-wrapper, MT6351 regulator,
eMMC, USB/netcat, and eight-A53 serviceability baseline when PWRAP uses the
source-proven infracfg RST2 SET/CLEAR transaction at `0x140/0x144`?

The unique intentional runtime delta is the PWRAP reset input: compact public
ID 1 replaces the rejected historical linear ID 64. Thermal and standalone
AUXADC remain disabled.

## Provenance and environment

- Production reset gate: [MT6797 infracfg reset repair](../2026-09-03-mt6797-infracfg-reset-repair/README.md).
- Runtime-control record: hardware-passed Candidate AW from the
  [eMMC experiment](../2026-07-25-emmc-development/README.md).
- Kernel profile: `mt6797-pwrap-reset-serviceability`, canonical
  `patches/series`, Buildbox only.
- DT parent: exact ignored Candidate AW DT, SHA-256 `e51891c839ab...`.
- Initramfs parent: exact ignored Candidate AW image, SHA-256
  `344d8a8464be...`.
- Boot target: inactive GPT-resolved logical `boot2`; the exact validated
  padded candidate is SHA-256 `5c7429b297c7...`.

The exact build, package, candidate, partition, boot, and recovery identities
will be recorded in `results/` as each gate completes.

## Safety assessment

Candidate construction is offline and cannot access a device. The DT
transform requires the exact retained control hash, parses the FDT structure,
and changes only PWRAP's second `resets` cell from 64 to 1. It refuses an
already-modified, malformed, or differently attributed input.

Any later installation is covered only by the repository's standing guarded
`boot2` authorization: resolve the live GPT, reject the active root, mounts,
holders, size mismatch, unstable power, or ambiguous identity, then pad,
write, flush, and require a full-partition checksum match. No new partition
backup is required. After a verified write the device must shut down, not
reboot. Primary `boot`, preloader, NVRAM, GPT, and whole-device writes remain
outside scope.

## Associated code

- `scripts/build_dtb.py`: exact one-cell FDT transform.
- `scripts/test_dtb.py`: positive and rejecting transform cases.
- `scripts/validate_package.py`: exact Buildbox package/configuration gate.
- `scripts/build_candidate.sh`: deterministic Android-v0 construction and
  exact 16 MiB padding, with two independent assemblies.
- `scripts/validate_candidate.py`: independent package, DT, container, and
  padding validator.

- `scripts/collect_runtime.sh`, `scripts/remote_observe.sh`, and
  `scripts/classify_observation.py`: one bounded read-only natural-binding
  frame with exact release, boot-ID, runtime-DT, driver, rail, eMMC, USB, and
  CPU predicates.
- `scripts/request_native_reboot.sh`: post-classification USB recovery through
  the exact inherited `/bin/reboot` hash and changed-ID Gemian confirmation.
- `scripts/install_boot2.sh`: live-GPT guarded installation, full readback,
  no fresh partition backup, and clean shutdown.

## Procedure

1. Validate and publish the canonical focused profile and offline tooling.
2. Build that exact pushed commit on Buildbox and fetch only the validated
   package.
3. Construct the candidate twice from the exact package, control DT, and
   control initramfs; require byte-identical results and independent
   validation.
4. Pin the candidate and add a bounded runtime classifier before installation.
5. If every offline gate passes, install only to live GPT-resolved inactive
   `boot2`, verify the full readback, and shut the device down.
6. In one owner-selected boot, observe natural PWRAP/MT6351/eMMC binding and
   USB/netcat serviceability without a CPU trigger, load, thermal access, or
   storage write. Return to changed-ID Gemian through the bounded USB shell
   recovery path.

Before that boot, the hypothesis and branches are fixed: a complete natural
bind plus serviceability pass permits the thermal transaction to depend on the
corrected reset; a PWRAP/reset failure returns to reset/clock ownership; an
MT6351 or eMMC-only failure stays with that downstream consumer; absent exact
identity or transport yields no hardware conclusion.

## Observations

- The historical eMMC profile cannot be selected: the repository invariant
  audit quarantines its noncanonical DA9214 series. This experiment instead
  uses the current canonical series and excludes the quarantined DA9214 path.
- Buildbox compiled exact pushed commit `ded915b81d56...` with kernel release
  `7.1.3-gemini-mt6797-pwrap-reset`, canonical 505-patch set
  `bc6d039d8801...`, and configuration `194834d90eb2...`; package checksums and
  the focused validator passed.
- Two independent assemblies were byte-identical. The raw candidate is
  `305230b1e284...` (7,487,488 bytes), its exact 16 MiB padded form is
  `5c7429b297c7...`, and its DT is `e1e4eca28932...`.
- The FDT parser proves that the exact Candidate AW control DT changed only
  PWRAP's second `resets` cell, from `<3 64>` to `<3 1>`. The inherited exact
  initramfs is unchanged and the Android-v0 LK contract passes.
- The runtime classifier passes one complete fixture and rejects seven
  decision-changing mutations. Shell syntax, ShellCheck, and the observer's
  no-partition/no-write static gate pass.
- A preboot audit additionally excluded the driver directory's `module`
  symlink from bound-device counts and pinned the corrected observer hash;
  installer single-write/live-GPT and native-reboot no-partition static gates
  also pass. See
  [results/runtime-tooling-hardening-20260904.txt](results/runtime-tooling-hardening-20260904.txt).
- The exact offline and predeployment record is
  [results/offline-candidate-20260904.txt](results/offline-candidate-20260904.txt).
- From changed-ID known-good Gemian, the guarded installer resolved inactive
  `boot2` as `/dev/mmcblk0p30` while `/dev/mmcblk0p29` was the active root.
  The 16 MiB target was writable, unmounted, holder-free, and on stable
  external power with full battery. Its predecessor was `6ba8c9538dcf...`.
- The installer wrote only `boot2`, synced, flushed, and read the complete
  partition back as exact candidate `5c7429b297c7...`. It created no fresh
  backup and then shut the device down; SSH disappearance confirmed the power
  transition. See [results/deployment-20260904.txt](results/deployment-20260904.txt).
- Fresh mainline boot ID `30ed4846...` matched the exact release and runtime
  DT reset tuple `<3 1>`. PWRAP, its MT6351 core and regulator child,
  `vemc_3v3`, `vio18`, MSDC, and one MMC card all bound; the 58.2 GiB user
  area and all 33 GPT partitions appeared with zero targeted PWRAP/MMC errors.
- USB/netcat completed one read-only session, CPUs 0--7 were online, and the
  exact ten-CPU topology retained CPUs 8--9 as present but offline. The owner
  also reported a working framebuffer console; screen state was not used as
  the pass criterion. Thermal, cpufreq, idle, suspend, CPU triggers, load,
  thermal reads, and storage access all remained absent.
- The first classifier rejected only because its fixture incorrectly expected
  `possible/present=0-7`. The observed canonical topology is
  `possible/present=0-9`, `online=0-7`, `offline=8-9`; the corrected exact gate
  passes the same complete frame without another device observation. See
  [results/runtime-attempt-1-pwrap-serviceable-20260904.txt](results/runtime-attempt-1-pwrap-serviceable-20260904.txt).
- The exact live release, boot ID, and inherited `/bin/reboot` SHA all matched
  and authorized one native recovery request. The device-side action succeeded;
  the initial host parser stopped afterward because interactive `> ` prefixes
  preceded `request_authorized=yes`. No retry was issued. A bounded SSH check
  confirmed Gemian `3.18.41+` on changed boot ID `00101221...`, and the parser
  now evaluates the exact marker-bounded suffix. A final read-only live-GPT
  attestation resolved inactive, unmounted `boot2` as p30 and reproduced exact
  candidate checksum `5c7429b297c7...`; no recovery-side write occurred. See
  [results/native-recovery-20260904.txt](results/native-recovery-20260904.txt).
- The owner separately observed the framebuffer console working on this boot.
  This is retained as a visual serviceability observation, not as evidence for
  the thermal/AUXADC transaction or CPU8/CPU9 readiness.

## Analysis

The runtime result closes the risk identified by the reset audit: switching
the active PWRAP consumer from historical linear ID 64 to compact public input
1 does not regress its real reset, child creation, required rails, eMMC, A53,
USB, or console serviceability. The present-but-offline CPU8/CPU9 topology is
also preserved, so the classifier repair restores the intended stronger
contract rather than accepting a reduced eight-CPU description.

## Conclusion

`confirmed` on the named unit and exact candidate: MT6797 PWRAP survives the
source-proven RST2 SET/CLEAR mapping and preserves MT6351 VEMC/VIO18 plus eMMC
and development serviceability. This does not enable or validate thermal,
AUXADC, frequency, CPU8/CPU9 load, idle, or suspend behavior.

## Follow-up

Begin the disconnected hardware-free thermal/AUXADC transaction implementation
from the frozen audit design without enabling either DT node. Preserve this
exact PWRAP/MT6351/eMMC/serviceability baseline for the later runtime candidate.
