# Experiment: Gemini eMMC block access

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-25-emmc-development` |
| Status | `completed; eMMC enumeration and guarded boot2 read/write passed; primary boot remained protected` |
| Subsystem | MediaTek MT6797 eMMC host and block layer |
| Device variant | Gemini PDA, named device under test |
| Date(s) | 2026-07-25 to 2026-07-26 |
| Investigator(s) | Codex and device owner |
| Tracking issue | — |

## Question or hypothesis

The retained `mmc0` DT node describes the Gemini's non-removable eMMC and
matches Linux's `mediatek,mt6797-mmc` host driver. Enabling the built-in MMC
core, block layer, MediaTek host, PMIC-wrapper, MT6351 MFD, and MT6351
regulator drivers should expose the eMMC as a Linux block device while
preserving the already validated console, keyboard, USB shell, eight-CPU,
DVFSP, I2C6, and watchdog contracts. Candidate AU added the existing BusyBox
`dd` applet as `/bin/dd` and a separately reviewed helper for an explicit,
GPT-name-resolved `boot2` write.

## Provenance and safety

- Kernel release: pinned Linux 7.1.3 source and the existing 107-patch series.
- Configuration: the isolated `gemini-emmc-development` fragment, with
  `CONFIG_MMC=y`, `CONFIG_MMC_BLOCK=y`, and `CONFIG_MMC_MTK=y`.
- DT: exact Candidate AS final DT; its `mmc0` node is already enabled and is
  not changed by this experiment.
- Boot target: logical `boot2`, resolved from the live GPT each time.
- The first hardware test is read-only: enumerate `/dev/mmcblk*`, inspect the
  kernel log, and do not mount or write any partition.
- The initramfs helper is not a default action: it requires an explicit
  `--confirm-boot2`, resolves exactly one GPT `PARTNAME=boot2` node from sysfs,
  requires an exact 16 MiB target, rejects mounts and holders, backs up the
  full partition, uses `dd` with `conv=fsync`, and verifies a full-partition
  SHA-256 readback. `--dry-run` performs all checks without writing.

## Associated code

- `scripts/build-candidate-emmc.sh` assembles the current boot image from a
  validated eMMC kernel package and the exact known-good AO DT baseline plus
  the validated development initramfs transform.
- `scripts/validate-package-emmc.py` checks the pinned profile, config, image,
  and required MMC host symbol.
- `scripts/validate-boot-emmc.py` checks the Android-v0 container and preserves
  the existing compiled handoff audit.
- `scripts/build-emmc-dtb.sh` deliberately reuses the exact AS DT derivation;
  the DT already enables `mmc0`.
- `scripts/build-emmc-initramfs.sh` and `scripts/validate-emmc-initramfs.py`
  prove that only `/bin/dd` and `emmc-flash-boot2` were added to the exact AO
  initramfs and that the BusyBox `dd` applet is present.

## Procedure

1. Configure and build the pinned eMMC profile in the recovery VM.
2. Assemble and validate two independent candidate packages and pin their
   hashes.
3. Install only the validated, padded candidate image to inactive logical
   `boot2`.
4. Boot it manually and inspect the eMMC node and log without mounting or
   writing anything.
5. Exercise the helper first with `--dry-run`; reserve an actual write for an
   explicitly reviewed development operation.

## Observations

The pinned profile built twice with identical kernel payloads; only the VM
generation timestamp in the package provenance differed. Candidate AU's full
artifact inventory and boot container were assembled twice identically:
raw `89a609b5adbdaf986fb33b34d18804640114e8f713800386101078729725ce49`,
exact-16-MiB padded `5052739e14ea8e8086709d52346beac0508ade4f56ac58911d78060fc34c9fff`,
and initramfs `344d8a8464bee60764df467f166aa73eddfcbd4d362d835aa2d6895534c31c4b`.

The guarded installer wrote only GPT-resolved `/dev/mmcblk0p30` (`boot2`),
whose exact size was 16 MiB and which was not the active root (`/dev/mmcblk0p29`).
For AU it preserved the previous AT full-partition image
`ca66d151c9772f3e7f3237c9b87b52d5067c6381d438609dd9b4b0d8a7f0bc09`, synced and
flushed the write, and verified the AU readback checksum. The detailed
sanitized record is in `results/candidate-au-build-install-20260725.txt`.

Candidate AW booted successfully on the named device. The PMIC wrapper bound,
the MT6351 VEMC/VIO18 regulators registered, and the eMMC host enumerated a
58.2 GiB `mmcblk0` with all 33 GPT partitions plus boot0, boot1, and RPMB.
The detailed sanitized record is in
`results/candidate-aw-runtime-20260726.txt`.

## Conclusion

AU passed its first boot test but failed eMMC enumeration. AV added the
MT6351 MFD/regulator drivers, but its runtime probe showed that the PMIC
wrapper was still disabled (`CONFIG_MTK_PMIC_WRAP=n`), leaving only the dummy
regulator and repeated `-EPROBE_DEFER` from `11230000.mmc`. AW adds the wrapper
driver and passed the read-only boot test: `1000d000.pwrap` and its MT6351
child returned success, `11230000.mmc` returned success, and `mmcblk0` appeared.

The exact 16 MiB primary Gemian boot image was later copied from read-only
`boot` to GPT-resolved, inactive `boot2`, synchronized, block-flushed, and read
back in full with a matching checksum. This closes the bounded development
read/write gate for `boot2`; it does not establish broad eMMC reliability,
filesystem safety, suspend/resume, or permission to write another partition.

## Follow-up

Candidate AU booted successfully with all eight CPUs and the USB shell, but
its eMMC host remained deferred (`probe of 11230000.mmc returned -517`) because
only the dummy regulator was registered. The DT's `vmmc-supply` and
`vqmmc-supply` phandles resolve to the MT6351 VEMC/VIO18 rails. Candidate AV
added the MFD/regulator drivers, and Candidate AW adds the missing
`CONFIG_MTK_PMIC_WRAP=y` dependency while preserving the AV DT and initramfs
contract. AW booted with the expected configuration and exposed the named
VEMC (`regulator.18`) and VIO18 (`regulator.24`) rails; no MMC probe defer was
observed.

This enables a no-Gemian development loop for explicitly guarded `boot2`
operations. It does not authorize arbitrary partition writes.

An owner-requested attempt to copy AW to the primary `boot` partition was
rejected by the eMMC path. Mainline and Gemian vendor writes returned a zero
userspace status but left p22 unchanged; Gemian's kernel logged
`mmc_check_write: data error = -30` (`EROFS`). `boot2` writes remain verified,
but primary-boot writes require a separate investigation of the vendor
write-protection contract. See
`results/aw-to-primary-boot-protected-20260726.txt`.

The experiment is closed at this boundary. Storage stress, filesystem use,
suspend/resume, and the protected primary-boot policy require separate
experiments.
