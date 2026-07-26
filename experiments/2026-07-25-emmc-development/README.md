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
USB shell, eight-CPU, DVFSP, I2C6, and watchdog contracts.

## Provenance and safety

- Kernel release: pinned Linux 7.1.3 source and the existing 107-patch series.
- Configuration: the isolated `gemini-emmc-development` fragment, with
  `CONFIG_MMC=y`, `CONFIG_MMC_BLOCK=y`, and `CONFIG_MMC_MTK=y`.
- DT: exact Candidate AS final DT; its `mmc0` node is already enabled and is
  not changed by this experiment.
- Boot target: logical `boot2`, resolved from the live GPT each time.
- The first hardware test is read-only: enumerate `/dev/mmcblk*`, inspect the
  kernel log, and do not mount or write any partition.
- No installer, initramfs command, or default action writes storage. A future
  USB-only flashing helper must resolve and verify the named `boot2` partition,
  require an explicit confirmation, and verify a full-partition readback.

## Associated code

- `scripts/build-candidate-emmc.sh` assembles the AT boot image from a validated
  eMMC kernel package and the exact known-good AO initramfs/DT baseline.
- `scripts/validate-package-emmc.py` checks the pinned profile, config, image,
  and required MMC host symbol.
- `scripts/validate-boot-emmc.py` checks the Android-v0 container and preserves
  the existing compiled handoff audit.
- `scripts/build-emmc-dtb.sh` deliberately reuses the exact AS DT derivation;
  the DT already enables `mmc0`.

## Procedure

1. Configure and build the pinned eMMC profile in the recovery VM.
2. Assemble and validate two independent AT packages and pin their hashes.
3. Install only the validated, padded AT image to inactive logical `boot2`.
4. Boot it manually and inspect the eMMC node and log without mounting or
   writing anything.
5. If the block device is stable, add a separately reviewed, explicitly
   guarded USB flashing helper.

## Observations

The pinned profile built twice with identical kernel payloads; only the VM
generation timestamp in the package provenance differed. The candidate boot
container was assembled twice with the same SHA-256:
`e157899b9d57070610d1f04e4f5d12b404c78b28b5f459b9407aa16a31356ff6`.

The guarded installer wrote only GPT-resolved `/dev/mmcblk0p30` (`boot2`),
whose exact size was 16 MiB and which was not the active root (`/dev/mmcblk0p29`).
It preserved a full backup, synced and flushed the write, and verified the
full-partition readback checksum. The detailed sanitized record is in
`results/build-and-install-20260725.txt`.

The device has not yet booted this exact candidate, so eMMC enumeration and
runtime stability remain unverified.

## Conclusion

Pending the first read-only boot test.

## Follow-up

The next decision is whether the host enumerates a stable `mmcblk` device. A
successful result enables a no-Gemian development loop; it does not by itself
authorize arbitrary partition writes.
