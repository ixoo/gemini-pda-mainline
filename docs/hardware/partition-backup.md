# Private MMC partition captures

[`scripts/backup-device-mmc`](../../scripts/backup-device-mmc) makes a
read-only, checksummed copy of every discoverable MMC partition node on a
Gemini PDA. It is intended for recovery provenance and reverse engineering,
not for flashing. The whole-disk node (`/dev/mmcblk0`) is deliberately never
read; numbered GPT partitions, eMMC boot hardware partitions, and RPMB are
handled as separate named nodes.

## Safety boundary

Partition images are more sensitive than normal hardware logs. They can contain
IMEI and serial values, MAC addresses, filesystem UUIDs, keys, calibration,
proprietary firmware, credentials, and user data. Keep the output encrypted and
owner-only. Do not commit it, publish it, attach it to an issue, or transfer it
to a shared VM without a separate review. `/artifacts/` is Git-ignored, but that
does not replace encryption or access control.

The script never writes to the device and does not unlock, mount, or repair a
partition. It requires an explicit `--all --confirm-read` for a real capture;
without those flags it only permits an inventory dry run. A read failure or
short read is kept as a `.partial` file and marked in `MANIFEST.tsv`, never
presented as a complete image. RPMB access may be unavailable on a given
kernel; that is an expected, recorded negative result rather than a reason to
retry with a write-capable tool.

`--layout-config` is a naming aid only. The live `blockdev` size and sysfs
partition node remain authoritative; a flash file may describe a different
capacity or layout revision and must never be used as a write recipe without a
fresh reconciliation.

## Usage

First inspect the target and partition labels without copying bytes:

```sh
./scripts/backup-device-mmc \
  --target gemini@192.168.1.50 \
  --dry-run
```

For a complete private capture, provide a local mode-0600 file containing the
device's sudo password. Do not put the password in shell history or a command
argument:

```sh
umask 077
printf '%s\n' 'device-password' > /private/tmp/gemini-sudo-password
chmod 600 /private/tmp/gemini-sudo-password

./scripts/backup-device-mmc \
  --target gemini@192.168.1.50 \
  --layout-config /path/to/Gemini_WIFI_A16GB_L40GB_Multi_Boot.txt \
  --sudo-password-file /private/tmp/gemini-sudo-password \
  --all \
  --confirm-read

rm -f /private/tmp/gemini-sudo-password
```

For a one-off capture, `--sudo-password-stdin` reads one password line before
the SSH session starts and does not create a local password file:

```sh
./scripts/backup-device-mmc \
  --target gemini@192.168.1.50 \
  --layout-config /path/to/Gemini_WIFI_A16GB_L40GB_Multi_Boot.txt \
  --sudo-password-stdin \
  --all \
  --confirm-read
```

The default output is
`artifacts/device-partitions/YYYYMMDDTHHMMSSZ/`. It contains:

- `REMOTE_INVENTORY.tsv` — root-owned remote discovery of device, size,
  partition label, and read-only flag;
- `*.img` — complete images whose manifest row has `status=ok`;
- `*.partial` — incomplete or failed reads retained for diagnosis;
- `MANIFEST.tsv` — expected/captured byte counts, physical `mmcblk` node,
  flash-config logical name, and SHA-256 checksums;
- `MANIFEST.tsv.sha256` — checksum of the manifest itself;
- `SOURCE.txt`, `README.txt`, and `collector.log` — provenance, warnings, and
  transport errors.

The capture is not a flash package. In particular, do not use it as input to a
preloader, GPT, NVRAM, or whole-device write command. Preserve a separate
known-good recovery path and keep offline copies of the checksummed images.

For an older capture made before logical naming was added, use
[`scripts/rename-device-mmc`](../../scripts/rename-device-mmc) with the same
flash config. It only renames files inside the Git-ignored capture directory
and rewrites its manifest; it does not contact the device.

## Interpreting labels

Gemini Android/Gemian layouts commonly expose labels such as `boot`, `boot2`,
and `boot3` on numbered nodes (`mmcblk0pN`). The label-to-node mapping in
`MANIFEST.tsv` is authoritative for the device that was captured. The script
also attempts `mmcblk0boot0`, `mmcblk0boot1`, and `mmcblk0rpmb`; these are eMMC
hardware areas, not the GPT labels `boot`, `boot2`, or `boot3`.

Raw images are immutable evidence. Analyze copies in the Linux development VM
and keep Ghidra/Radare2 databases outside this repository. Record any derived,
sanitized fact in `docs/hardware/` and the associated dated experiment rather
than committing the image.
