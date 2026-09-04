# Experiment: MT6797 PMIC-wrapper reset serviceability

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-04-mt6797-pwrap-reset-serviceability` |
| Status | `running`; exact candidate installed and device shut down for boot |
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
- No runtime boot has been classified yet.

## Analysis

The compile result alone is not a hardware claim, but the candidate now has a
single attributable runtime delta and a decision-complete observation path.
Unlike the quarantined historical eMMC profile, the kernel is built from the
current canonical series; unlike the reset KUnit profile, its production
PWRAP, MT6351 regulator, and MediaTek MMC paths are present while test-only and
thermal policy remain absent.

## Conclusion

Pending runtime evidence. The offline candidate is valid and bootable by
contract, but it does not yet establish PWRAP runtime serviceability.

## Follow-up

Record the exact offline and runtime evidence, then update the durable reset
fact and concise support state without claiming thermal readings.
