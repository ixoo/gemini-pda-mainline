# Firmware boundary

This document records firmware supplied by the installed Gemian system on the
observed Gemini PDA. The files themselves are proprietary or have an
unestablished redistribution license and are deliberately excluded from Git.

## Captured vendor set

On 2026-07-11, 28 files totaling 5,024,607 bytes were copied read-only from the
Gemian system partition into the owner's private local artifact directory:

```text
artifacts/firmware/gemian-2019-vendor/
```

The directory and files are owner-only, and `/artifacts/` is ignored by Git. A
compressed source-layout archive is retained at:

```text
artifacts/firmware/gemian-2019-vendor/gemini-vendor-firmware-20260711.tar.gz
```

Its SHA-256 is
`4cced5d9684faef305eda2bf5a7528a3a47e77d46cf4788cb13112992ec0879c`.
Do not commit, publish, or transfer this archive until every file's license and
the destination's access controls have been reviewed.

The sanitized per-file manifest is in the
[firmware inventory experiment](../../experiments/2026-07-11-gemian-firmware-inventory/README.md).

## Functional groups

| Function | Files | Runtime evidence | Boundary |
| --- | --- | --- | --- |
| Touchscreen | `novatek_ts_fw.bin` | NVT driver requested it and reported a matching checksum; seven private extractions are byte-identical at 118,784 bytes (SHA-256 `4cab8b83dfabe89864521539fb4da9ee0fbea1737b03d5f0d3e159cd076f4f1c`) | Required by the vendor NVT path; redistribution/license unknown; keep out of Git and keep mainline firmware update disabled by default. See the [copy audit](../../experiments/2026-07-12-input-backlight-recovery/results/nvt-firmware-copy-audit-20260714.txt) |
| MT6797 SPM | Nine `pcm_*.bin` files | Vendor kernel reported all nine SPM program versions | Power-management microcode; license unknown |
| Connectivity | `WMT_SOC.cfg`, two `ROMv3_patch_*.bin` files | `wmt_launcher` is running; WMT status reports MT279 ROM E1, branch W1715MP, patch `20180307`, matching the ROMv3 header text | MT6797 CONSYS/WMT connectivity, BT, and GNSS/FLP patch/config; per-file load log and license remain unresolved |
| Wi-Fi | `WIFI_RAM_CODE_6797` | Present; `mt-wifi` has observed platform ancestry. HIF-SDIO log messages do not establish an SDIO bus or exact image load | Retained MTKE structure validated; runtime load attribution and redistribution rights remain unresolved. See the [Wi-Fi contract](mt6797-wifi.md) |
| FM | `fm_cust.cfg`, MT6631 coefficient and patch files | Vendor config is installed; kernel config and `/dev/fm` identify the MT6631 FM path | Coefficient/patch load and physical FM population remain unverified; license unknown |
| Cellular modem | `modem_3_3g_n.img` | Active CCCI/CLDMA stack; file present in vendor directory | Proprietary baseband firmware; never load outside the intended modem path |
| Modem logging | Catcher and engineering filter files | Present alongside modem image | Diagnostic filters, not executable modem firmware |

The dated 2026-07-14 Linux 7.1.3 loader comparison is recorded in the [firmware-loader
boundary audit](../../experiments/2026-07-14-transport-firmware-boundary-audit/results/firmware-loader-boundary-current-77-20260714.txt)
and is reproducible with its [read-only audit script](../../experiments/2026-07-14-transport-firmware-boundary-audit/scripts/audit-firmware-loader-boundary.sh).
The package examined by that audit had no `firmware-name` DT properties and no active
CONSYS, WMT, BTIF, CCCI, camera, or SCP consumer. Linux's `novatek-nvt-ts`
driver has neither a firmware request nor a firmware-name property, so the
vendor `novatek_ts_fw.bin` cannot be made a dependency by adding only a
compatible string. The packaged Bluetooth transports are unset/absent and
their Linux source has no MT6797 match; `WMT_SOC.cfg`, ROMv3 patches, and
`WIFI_RAM_CODE_6797` therefore remain inputs to a new CONSYS/WMT backend.
`mtk_scp.ko` and `mtk_rpmsg.ko` are generic optional framework modules, not
evidence that the nine SPM PCM programs or any SCP image can be loaded by this
board. The modem image remains behind a new CCCI/CLDMA/EMI-MPU boundary, and
FM files have no active mainline Gemini consumer.

## Files the mainline Wi-Fi driver loads

The mainline Wi-Fi stack (CONSYS owner and WLAN driver, patches 0390-0394)
requests four files through the kernel firmware loader, all from the
standard directory `/lib/firmware/mediatek/mt6797/`. Copy the three
firmware files there from the device's Gemian system; the repository does
not ship them.

| File in `/lib/firmware/mediatek/mt6797/` | Copy from (Gemian) | Bytes | SHA-256 | Check by the driver |
| --- | --- | --- | --- | --- |
| `ROMv3_patch_1_0_hdr.bin` | `/vendor/firmware/ROMv3_patch_1_0_hdr.bin` | 210,904 | `450c2b0949cf879217ac9aef81b18b860982f0e69340784b448b54365d8cf630` | Exact hash; any other file is refused |
| `ROMv3_patch_1_1_hdr.bin` | `/vendor/firmware/ROMv3_patch_1_1_hdr.bin` | 46,472 | `5732c0730380e937b48ad169f2805b65e8d4a178265566c5083cb2cc2d249f1e` | Exact hash; any other file is refused |
| `WIFI_RAM_CODE_6797` | `/vendor/firmware/WIFI_RAM_CODE_6797` | 411,632 | `a69383d74d829430487c39eef6b5e281b25f901595c903a632a10aa8631426dd` | Container structure: four sections, two ordinary (14,832 bytes) and two EMI (396,688 bytes) |
| `WIFI.storage` | Not copied: a symlink to `/nvdata/APCFG/APRDEB/WIFI` | 514 | Differs per device | Record envelope only |

The first three come from the 2019 Gemian vendor set (see the
[firmware inventory](../../experiments/2026-07-11-gemian-firmware-inventory/README.md)). That set is
expected to be the same across Gemian installs, which is an inference: one unit has been read.
Bluetooth's start and the GNSS host use the same CONSYS start, so they need the same files and nothing more.
`WIFI.storage` is not firmware: it is the device's own Wi-Fi NVRAM record,
with the board's RF calibration, and it is read in place from the `nvdata`
partition, which every Gemini has. The system mounts that partition
read-only at `/nvdata`, as Gemian does (`noload` keeps an unclean journal
from being replayed onto the partition), and links the record into the
firmware directory:

```text
PARTLABEL=nvdata  /nvdata  ext4  ro,noload,nosuid,nodev,noexec  0  0
ln -s /nvdata/APCFG/APRDEB/WIFI /lib/firmware/mediatek/mt6797/WIFI.storage
```

`noload` alone doesn't make that mount read-only on disk: ext4 still clears an orphan
list unless the block device itself is read-only, so the release image sets it read-only
first ([release RAM root](../RELEASE_READINESS.md#release-ram-root)).

The record therefore always belongs to the same device. Its provenance is
in the [storage contract](../../experiments/2026-09-05-mt6797-wifi-contract/PROVENANCE.md).
`WMT_SOC.cfg`, `WIFI_CUSTOM` and the raw `nvram` partition are not read.

A missing file stops the start chain with the loader's error in the kernel
log; nothing falls back to another path.

### Getting them from the owner's own device

The release image's [`firmware-get`](../../experiments/2026-10-30-mainline-dev-station/release/firmware-get)
copies the three files into RAM from the owner's Gemian, and `radio-start` calls it on each boot, since
nothing persists. On the one unit read, through its retained backup:

| Step | Observed |
| --- | --- |
| Partition | GPT name `linux`, ext4, already mounted read-only by the image's init |
| File | `/data/system.img`, an ext4 image of 642,129,920 bytes, which Gemian's container uses as `/system` |
| Firmware | `/vendor/firmware/` inside it, with the three hashes above |

The GPT partition named `system` on this unit holds an Android boot image, not these files.

- **Read-only.** The image goes through a read-only loop device on a read-only mount. It writes to no
  partition, and it sends nothing anywhere.
- **Nothing device-unique.** These three files are the same vendor files, and `firmware-get` prints one
  word. `WMT_SOC.cfg`, `nvram` and calibration aren't read by it. The calibration record stays where
  it is in `nvdata`, linked by `radio-start` as above.
- **Hashes.** The expected list is the table above, in the script. A hash is not the file. Whether publishing
  it raises any rights question isn't settled by anything here; the table was already public.
- **Not covered:** a device with no Gemian, another partition layout, or a different vendor set. Those
  are untested, and a mismatch stops the radio. Stock Android's layout hasn't been read.

### The set the card root carries

A persistent root keeps its firmware on disk. The
[Arch card root](../../experiments/2026-11-06-gemini-arch-root/README.md)'s
[`gemian-firmware`](../../experiments/2026-11-06-gemini-arch-root/gemian-firmware) copies six files
into its `/usr/lib/firmware/mediatek/mt6797/`, from Gemian's `system.img` (or a directory holding its
`vendor/`), the same read-only way `firmware-get` does, checking each SHA-256. The three files above
come with:

| File | From (Gemian) | Bytes | SHA-256 | User |
| --- | --- | --- | --- | --- |
| `mt6631_fm_v1_patch.bin` | `/vendor/firmware/mt6631_fm_v1_patch.bin` | 1,028 | `ba35c74d26660729caf83b41a567e700f633b6c99384dfa6cbb3c17ceb767e26` | FM driver, by name |
| `mt6631_fm_v1_coeff.bin` | `/vendor/firmware/mt6631_fm_v1_coeff.bin` | 1,092 | `d32f4a16b35f950ed1a57f2ae88f77ac4b5674d5c4210b65f6fe7912901fd8db` | FM driver, by name |
| `gnss_dsp_6797.bin` | bytes 2,008,669 to 2,070,108 of `/vendor/lib/libmnl.so` | 61,440 | `898a5cca5aa3011d119a7c92a1c74720753a2b1c03e253cfd88bad4f8966f603` | GNSS host |

The GNSS DSP image has no file of its own on Gemian: `libmnl.so` (SHA-256 `a2e3fe69…330f`) carries
it, and it is what crosses the wire at each DSP boot
([stock trace](../../experiments/2026-11-01-gemini-gnss-stock-trace/README.md)). The name is this
project's. No driver requests it yet; today's host reads it at an offset, which is 0 in this file.
Like the rest, the hashes are of one unit's files, and none of the files is redistributed.

The connectivity loader first received normal `request_firmware` failures and
then Android `ueventd` supplied files from `/system/vendor/firmware`. The NVT
touchscreen followed the same fallback path from `/system/etc/firmware`.

The MT6797 WMT/BTIF/Wi-Fi/GNSS transport and its source-level comparison are
documented in the [connectivity/WMT recovery experiment](../../experiments/2026-07-12-connectivity-wmt-recovery/README.md).

## Firmware-file inventory exclusions

These exclusions describe the firmware-file inventory only. The later
[private partition backup](../../experiments/2026-07-14-mmc-partition-backup/README.md)
has a separate scope and includes protected configuration partitions. Applicable
retained captures may be analyzed privately under the standing inspection policy;
their integrity and calibration applicability must be established separately.

- `/lib/firmware` contains 27 Debian package files for unrelated USB, serial,
  audio, and amateur-radio hardware. No Gemini runtime load evidence was found,
  so these were inventoried but not copied into the Gemini vendor bundle.
- `/nvcfg`, `/nvdata`, `/protect_f`, and `/protect_s` were not collected. They
  can contain device-specific radio configuration, calibration, identifiers,
  keys, or other protected state.
- No partition image, preloader, bootloader, secure-world image, crash dump,
  filesystem image, user data, or firmware read back from hardware was copied.
- The Android LXC paths mirror the same `/system` mount and were not duplicated.

## Mainline implications

The observed files define several different boundaries. The mainline Wi-Fi driver loads
[the three files above](#files-the-mainline-wi-fi-driver-loads) through standard firmware
loading, and Bluetooth's start uses the same ROM patches. The mainline touch module loads no
firmware: the controller runs what is in its flash. SPM programs are
closely tied to vendor power management and must not be assumed suitable for a
mainline driver. The modem image remains behind the retained proprietary
baseband boundary. Logging filters are not kernel dependencies.

The current mainline DVFSP handoff is deliberately narrower: it validates a
stopped receiver through the CSPM window only. It does not map CSRAM, request
or retain a PCM image, perform the vendor start/kick sequence, or expose a
callable `SEMA_I2C_DRV` lease. The provider therefore remains read-only until
the firmware residency/start contract or a trusted external owner is proved.
See the [mainline PCM load-path audit](../../experiments/2026-08-06-da921x-page-owner-audit/results/mainline-pcm-load-path-audit-20260806.txt).

The dated package-to-firmware reconciliation is recorded in the
[transport and firmware boundary audit](../../experiments/2026-07-14-transport-firmware-boundary-audit/README.md).
For the package it examined, the audit found that the packaged SCP/RPMSG,
WWAN, GNSS, HCI, media, and cfg80211
objects are framework or optional-firmware pieces only: no active CONSYS,
CCCI/CLDMA, camera, or SCP consumer exists in the Gemini DTB. The audit keeps
the five no-map reservations intact and records the new backend contracts
required before any blob is loaded from a mainline image. Re-run this
reconciliation against the exact selected profile before making a current
package claim.

Before packaging any blob for a distributable system, establish its source,
license, exact hardware applicability, security-update provenance, expected
load address/interface, and whether it contains regional or device-specific
configuration.
