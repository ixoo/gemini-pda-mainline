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
| Touchscreen | `novatek_ts_fw.bin` | NVT driver requested it and reported a matching checksum; seven private extractions are byte-identical at 118,784 bytes (SHA-256 `4cab8b83dfabe89864521539fb4da9ee0fbea1737b03d5f0d3e159cd076f4f1c`) | Required by the vendor NVT path; redistribution/license unknown; keep out of Git and keep mainline firmware update disabled by default. See the [copy audit](../experiments/2026-07-12-input-backlight-recovery/results/nvt-firmware-copy-audit-20260714.txt) |
| MT6797 SPM | Nine `pcm_*.bin` files | Vendor kernel reported all nine SPM program versions | Power-management microcode; license unknown |
| Connectivity | `WMT_SOC.cfg`, two `ROMv3_patch_*.bin` files | `wmt_launcher` is running; WMT status reports MT279 ROM E1, branch W1715MP, patch `20180307`, matching the ROMv3 header text | MT6797 CONSYS/WMT connectivity, BT, and GNSS/FLP patch/config; per-file load log and license remain unresolved |
| Wi-Fi | `WIFI_RAM_CODE_6797` | Present; `mt-wifi` is bound and live dmesg shows HIF-SDIO traffic | Load was not independently attributed to this file in the retained log; license unknown |
| FM | `fm_cust.cfg`, MT6631 coefficient and patch files | Vendor config is installed; kernel config and `/dev/fm` identify the MT6631 FM path | Coefficient/patch load and physical FM population remain unverified; license unknown |
| Cellular modem | `modem_3_3g_n.img` | Active CCCI/CLDMA stack; file present in vendor directory | Proprietary baseband firmware; never load outside the intended modem path |
| Modem logging | Catcher and engineering filter files | Present alongside modem image | Diagnostic filters, not executable modem firmware |

The current Linux 7.1.3 loader comparison is recorded in the [firmware-loader
boundary audit](../../experiments/2026-07-14-transport-firmware-boundary-audit/results/firmware-loader-boundary-current-77-20260714.txt)
and is reproducible with its [read-only audit script](../../experiments/2026-07-14-transport-firmware-boundary-audit/scripts/audit-firmware-loader-boundary.sh).
The authoritative package has no `firmware-name` DT properties and no active
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

The connectivity loader first received normal `request_firmware` failures and
then Android `ueventd` supplied files from `/system/vendor/firmware`. The NVT
touchscreen followed the same fallback path from `/system/etc/firmware`.

The MT6797 WMT/BTIF/Wi-Fi/GNSS transport and its source-level comparison are
documented in the [connectivity/WMT recovery experiment](../../experiments/2026-07-12-connectivity-wmt-recovery/README.md).

## Exclusions

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

The observed files define several different boundaries. Touchscreen and Wi-Fi
support may need standard Linux firmware-loading integration. SPM programs are
closely tied to vendor power management and must not be assumed suitable for a
mainline driver. The modem image remains behind the retained proprietary
baseband boundary. Logging filters are not kernel dependencies.

The current package-to-firmware reconciliation is recorded in the
[transport and firmware boundary audit](../../experiments/2026-07-14-transport-firmware-boundary-audit/README.md).
It confirms that the packaged SCP/RPMSG, WWAN, GNSS, HCI, media, and cfg80211
objects are framework or optional-firmware pieces only: no active CONSYS,
CCCI/CLDMA, camera, or SCP consumer exists in the Gemini DTB. The audit keeps
the five no-map reservations intact and records the new backend contracts
required before any blob is loaded from a mainline image.

Before packaging any blob for a distributable system, establish its source,
license, exact hardware applicability, security-update provenance, expected
load address/interface, and whether it contains regional or device-specific
configuration.
