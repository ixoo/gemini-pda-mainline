# Experiment: Gemini eMMC block access

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-25-emmc-development` |
| Status | `running` |
| Subsystem | MediaTek MT6797 eMMC host and block layer |
| Device variant | Gemini PDA, named device under test |
| Date(s) | 2026-07-25 |
| Investigator(s) | Codex and device owner |
| Tracking issue | — |

## Question or hypothesis

The retained `mmc0` DT node describes the Gemini's non-removable eMMC and
matches Linux's `mediatek,mt6797-mmc` host driver. Enabling only the built-in
MMC core, block layer, and MediaTek host driver should expose the eMMC as a
Linux block device while preserving the already validated console, keyboard,
USB shell, eight-CPU, DVFSP, I2C6, and watchdog contracts. Candidate AU adds
the existing BusyBox `dd` applet as `/bin/dd` and a separately reviewed helper
for an explicit, GPT-name-resolved `boot2` write.

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

- `scripts/build-candidate-emmc.sh` assembles the AU boot image from a validated
  eMMC kernel package and the exact known-good AO DT baseline plus the
  validated development initramfs transform.
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
2. Assemble and validate two independent AU packages and pin their hashes.
3. Install only the validated, padded AU image to inactive logical `boot2`.
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

The device has not yet booted this exact candidate, so eMMC enumeration and
runtime stability remain unverified.

## Conclusion

Pending the first AU boot test and a read-only helper dry run.

## Follow-up

The next decision is whether AU enumerates a stable `mmcblk` device and the
helper can resolve `boot2` in the initramfs. A successful result enables a
no-Gemian development loop; it does not authorize arbitrary partition writes.
