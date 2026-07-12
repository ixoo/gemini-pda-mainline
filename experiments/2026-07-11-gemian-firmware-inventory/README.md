# Experiment: Gemian firmware inventory

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-11-gemian-firmware-inventory` |
| Status | `completed` |
| Subsystem | Firmware boundary |
| Device variant | Gemini PDA; retail variant not independently established |
| Date | 2026-07-11 |
| Environment | Gemian, Debian 9 userspace, vendor kernel `3.18.41+` |

## Question

Which files supplied by Gemian are candidates for firmware used by this
device, which loads can be observed, and which private/device-specific areas
must remain outside the collection?

## Safety and privacy

Collection was read-only with respect to device hardware and persistent
storage. A temporary root-owned archive was created under `/tmp`, changed to the
SSH user's ownership, copied to the host, and removed. The sudo password was
entered only at an interactive prompt, never stored, and invalidated before the
session ended.

Only `/system/etc/firmware` and `/system/vendor/firmware` were copied. NVRAM,
calibration/protection partitions, user data, block devices, secure firmware,
and device identifiers were excluded. The copied blobs remain private beneath
the Git-ignored `artifacts/` directory with owner-only permissions.

## Procedure

1. Enumerate firmware-named directories under the Gemian and Android system
   roots without crossing filesystems.
2. Record file paths and sizes, deduplicating Android LXC bind-mount views.
3. Compare kernel boot messages with filenames to distinguish observed loads
   from merely installed candidates.
4. Archive the two vendor firmware directories without reading unrelated
   partitions or user directories.
5. Copy the archive to the host's ignored artifact directory, extract it, set
   owner-only permissions, and remove the remote temporary archive.
6. Calculate SHA-256 identifiers locally and retain only this sanitized manifest
   in Git.

The reusable read-only inventory helper is
[`scripts/inventory.sh`](scripts/inventory.sh). It does not copy files.

## Result

- Vendor set: 28 files, 5,024,607 bytes.
- Private archive: 3,005,304 bytes.
- Archive SHA-256:
  `4cced5d9684faef305eda2bf5a7528a3a47e77d46cf4788cb13112992ec0879c`.
- Per-file hashes: [`results/manifest.sha256`](results/manifest.sha256).
- Durable interpretation: [firmware boundary](../../docs/hardware/firmware.md).

Observed boot-time loads cover the nine SPM programs, `WMT_SOC.cfg`, both
connectivity ROM patches, `fm_cust.cfg`, and `novatek_ts_fw.bin`. Presence plus
an active subsystem, rather than a captured load message, supports the Wi-Fi,
FM patch, and modem candidates. Catcher files are diagnostic filters.

## Limitations

This is the complete content of the two Gemian vendor firmware directories, not
proof that every possible firmware source or hidden partition was collected.
Firmware embedded in the kernel, boot chain, hardware, or protected partitions
was deliberately not extracted. Runtime load evidence is limited to the current
boot log and does not cover every optional feature.

