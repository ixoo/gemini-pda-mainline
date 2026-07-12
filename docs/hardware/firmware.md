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
| Touchscreen | `novatek_ts_fw.bin` | NVT driver requested it and reported a matching checksum | Required by the vendor NVT path; license unknown |
| MT6797 SPM | Nine `pcm_*.bin` files | Vendor kernel reported all nine SPM program versions | Power-management microcode; license unknown |
| Connectivity | `WMT_SOC.cfg`, two `ROMv3_patch_*.bin` files | WMT loader reported successful loads | MT6797 connectivity/BT patch and config; license unknown |
| Wi-Fi | `WIFI_RAM_CODE_6797` | Present in the active vendor firmware directory; `mt-wifi` bound | Load was not independently observed in the retained boot-log excerpt |
| FM | `fm_cust.cfg`, MT6631 coefficient and patch files | `fm_cust.cfg` load observed; kernel configured for MT6631 FM | Other two files are present candidates, not exercised |
| Cellular modem | `modem_3_3g_n.img` | Active CCCI/CLDMA stack; file present in vendor directory | Proprietary baseband firmware; never load outside the intended modem path |
| Modem logging | Catcher and engineering filter files | Present alongside modem image | Diagnostic filters, not executable modem firmware |

The connectivity loader first received normal `request_firmware` failures and
then Android `ueventd` supplied files from `/system/vendor/firmware`. The NVT
touchscreen followed the same fallback path from `/system/etc/firmware`.

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

Before packaging any blob for a distributable system, establish its source,
license, exact hardware applicability, security-update provenance, expected
load address/interface, and whether it contains regional or device-specific
configuration.

