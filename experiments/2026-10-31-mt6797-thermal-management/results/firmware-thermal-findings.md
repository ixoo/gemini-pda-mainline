# Firmware thermal content: static scan results

Scope: the retained private partition images and the installed Gemian vendor
firmware set for the named MT6797X Gemini PDA. Method: read-only hashing,
ASCII-string extraction, 256 KiB entropy summaries and 32-bit address-constant
search (`scripts/scan-firmware-thermal.py`). This is a triage inventory, not a
full disassembly. Absence of a string or constant is not proof of absence of
functionality.

Raw scan: [firmware-thermal-scan.tsv](firmware-thermal-scan.tsv).

## Image identity

The four retained slot pairs are byte-identical:

| Pair | SHA-256 |
| --- | --- |
| `boot0`/`boot1` preloader | `25319ce877bd17b204fa264645aebf4583ec10ae2f05f6d8a7fff5efe4c06246` |
| `scp1`/`scp2` | `3c65097eeeb4e2d29dd125752cfb648c6da5e3651eabc9dad1da672b2558cd66` |
| `lk`/`lk2` | `75ec9f0ba97af9e68d964b304e0de809f9b4546982570bd16b2e7fe88823282c` |
| `tee1`/`tee2` | `2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3` |

Every image uses the MediaTek container header (`0x58881688`, name at +8) with
a section descriptor (`0x58891689`) at +0x30; payload regions are followed by
`0xFF` padding.

## Thermal-relevant content by image

| Image | Thermal content | Thermal management role |
| --- | --- | --- |
| Preloader (`boot0`/`boot1`) | Efuse data-register table including `0x10206180`, `0x10206184`, `0x10206188`; `xxxxEEM`, `[EEM][VCORE]`, `[VCORE] - Kernel Got efuse`, CPU DVFS table names `MT_CPU_DVFS_B`/`_L`/`_LL`, `picachu_dvfs.c`, `vproc/vsram run as hw default`, PMIC efuse-trim messages | Boot-time voltage/frequency initialisation from calibration. No temperature-sensor, trip-point or throttling strings found. |
| LK (`lk`/`lk2`) | `atag,devinfo`; efuse register table; `atag,vcore_dvfs`, `Not Support VCORE DVFS`, `atag,ptp`, `PTP_INFO Only support in MT6795` | Forwards 100 efuse words to Linux (`atag,devinfo`), including the three thermal-calibration words. PTP voltage tagging is disabled for MT6797 in this binary. |
| ATF/TEE (`tee1`/`tee2`) | `plat/mt6797/power.c`, PSCI power on/off strings, `iDVFS enable/disable`, `IDVFS_PLLINDEX`, `rg_armpll_sdm_pcw_r`, `IDVFS_SWREQ`, `big armpll`, `Posdiv` | Secure-world AArch64 firmware containing an ARMPLL/POSDIV frequency-control path ("iDVFS"). No thermal-zone or trip-point strings found. The AUXADC-base "hit" in the raw scan is an AArch64 instruction encoding (`add w0, w0, #4`), not an address reference. |
| SCP (`scp1`/`scp2`) | TinySys CM4 image (`tinysys-loader-CM4_A`, `tinysys-scp-CM4_A`); FreeRTOS; modules `dma`, `dvfs`, `ipi`, `spm`; `[DVFS-SCP]` messages; `pwrap_scp_write(0x02F0)`; IPI commands `IPI_DVFS_SET_FREQ`, `IPI_DVFS_LIMIT_OPP_SET/EN`, `IPI_DVFS_FIX_OPP_SET/EN`, `IPI_DVFS_DISABLE/SLEEP/WAKE` | SCP-side DVFS service (clock/SPM/PMIC-wrapper access) with AP-visible IPI OPP controls. No thermal sensor, temperature or trip-point strings and no thermal/AUXADC/efuse address constants found. |
| DVFSP/PCM microcode (`pcm_*.bin`) | Nine SPM program images (deep idle, SODI, suspend, VCORE high/low/ultra); binary instruction words only | Power/sleep and VCORE-DVFS sequencing; no readable policy strings. Already covered by the [firmware boundary document](../../../docs/hardware/firmware.md). |
| Modem (`md1img`, `md3img`) | `MOLY.LR11.W1630.MD.MP.V105.8`; `l1cal_temperatureADC_T` NVRAM size check; `+ETHERMAL`, `+EADC`, `EEMODE`/`EEMCINFO`, `set_throttling_level`, `support_throttling_algo`, `HwdTstReadCurrentXoTemperature`; `CCMSG_ID_SYSMSGSVC_SW_TPUT_THROTTLING` callback (`tmc_md_thermal_feature_ctrl_sysmsgsrv_cbk`) | Baseband-internal thermal ADC calibration from NVRAM, thermal throttling levels and an AP-CCCI sysmsg control path. Independent of the AP thermal zone. |
| Wi-Fi (`WIFI_RAM_CODE_6797`) | `THERM_THERMCR0`, `Thermo Init: Lower/Upper/Curr`, `Thermo T`, `rlmThermoOverheat`, ADC value reads, efuse PA-bias/DPD calibration | Connectivity-firmware thermal loop for RF calibration and overheat handling; autonomous, not driven by AP thermal zones. |
| Touch (`novatek_ts_fw.bin`) | None found | Not thermal-related. |

## What this establishes

1. AP-visible thermal calibration for the SoC sensors is carried by the LK
   `atag,devinfo` handoff, not invented by the kernel. The vendor thermal driver
   reads words 32/31/33 of that payload, which correspond to efuse data
   registers `0x10206184`/`0x10206180`/`0x10206188`.
2. The SCP image is a DVFS/Power service, not a thermal-policy engine. Its
   strings and address references give no evidence of temperature handling.
3. Temperature policy on the vendor Android stack is therefore an AP-kernel and
   userspace responsibility, with firmware acting as the calibration and
   actuation layer (preloader DVFS tables, LK devinfo, ATF ARMPLL changes,
   SCP/DVFSP OPP
   execution, modem and Wi-Fi local loops).
4. The modem and connectivity firmware own independent thermal loops that the
   AP can influence (modem through CCCI sysmsg throttling) but does not read as
   ordinary thermal zones.

## Limits

- The scan uses printable strings and 32-bit constants only; code paths that use
  computed addresses or no strings are invisible to it. Raw constant hits are
  noisy: the TEE hits are AArch64 instruction encodings (`add w0, w0, #4`), the
  md3 hits are halfword tables, and the modem DSP hits remain unexplained.
  Only the preloader and LK hits are validated, because they sit in word-aligned
  tables of consecutive efuse registers.
- The images are mostly padding; only the leading payload was meaningful.
- Modem and TEE payloads include compressed or encrypted regions; their internal
  tables were not decoded.
- No runtime claim is made: none of this was exercised on hardware in this
  analysis.
