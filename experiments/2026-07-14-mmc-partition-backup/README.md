# MMC partition backup

## Question

Can an owner-authorized Gemian device expose a complete, read-only set of MMC
partition images for recovery provenance and reverse engineering without
opening a whole-disk write path?

## Method

[`scripts/backup-device-mmc`](../../scripts/backup-device-mmc) connects over SSH,
uses root only for `blockdev`, sysfs label discovery, and `dd`, and writes the
stream into a mode-0700 Git-ignored directory below
`artifacts/device-partitions/`. It excludes `/dev/mmcblk0` itself and handles
each numbered GPT, eMMC boot-area, and RPMB node independently. Every image is
accepted only when its local byte count matches the remote `blockdev` size and
its SHA-256 is recorded in `MANIFEST.tsv`.

The command requires explicit `--all --confirm-read` flags. A dry run is
available before any bytes are copied. The authorized capture used the device
at `gemini@192.168.1.50` and a transient sudo password read from stdin; no
credential was saved in the repository.

## Capture result

The device exposed 36 nodes: `mmcblk0p1` through `mmcblk0p33`,
`mmcblk0boot0`, `mmcblk0boot1`, and `mmcblk0rpmb`. The GPT labels included
`recovery`, `lk`, `lk2`, `boot`, `linux`, `boot2`, `boot3`, `nvram`, `nvcfg`,
`nvdata`, `protect1`, `protect2`, `metadata`, `system`, `cache`, `userdata`,
and `flashinfo`. The labels `boot`, `boot2`, and `boot3` mapped to `p22`, `p30`,
and `p31` on this device. The `linux` partition (`p29`) reported
61,765,303,808 bytes; it was the dominant transfer cost.

The complete private result is under
`artifacts/device-partitions/20260715T020041Z/`. Thirty-five nodes produced
complete raw images with SHA-256 entries in `MANIFEST.tsv`; the RPMB node
returned `Input/output error` and is recorded as a zero-byte `.partial` with
`status=short-read`. The manifest checksum itself is in
`MANIFEST.tsv.sha256`. Inspect these files locally; they are intentionally not
linked or hashed here. A row with `status=ok` is a complete image; a `.partial`
row is not. The RPMB refusal is a useful negative result and must not be
“fixed” by trying a write-capable utility.

## Interpretation and limits

- Raw images may contain IMEI/serial values, MAC addresses, filesystem UUIDs,
  keys, calibration, proprietary firmware, credentials, and user data.
- The read is not a filesystem snapshot. Mounted partitions may change while
  they are being copied, so use checksums for transport integrity, not claims
  of crash consistency.
- The capture does not establish that any partition is safe to flash. Keep it
  offline and preserve a separate known-good recovery path.
- Derived facts belong in sanitized hardware documents and dated experiments;
  the raw images, manifest, and logs must remain Git-ignored.

## Follow-up

Use the private images to compare LK/boot-image headers, partition labels,
vendor firmware placement, and filesystem layout. Record only redacted offsets,
formats, and reproducible observations in a new experiment; never copy raw
partition contents into this repository.
