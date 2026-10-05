# Experiment: MT6797 Wi-Fi common initialization

| Field | Value |
| --- | --- |
| ID | `2026-10-06-mt6797-wifi-common-init` |
| Status | Driver draft; host and schema checks pass; runtime untested |
| Profile | `mt6797-a53-wifi-common-init-compile` |
| Subsystem | MT6797 CONSYS WMT common initialization |
| Date | 2026-10-06 |
| Device action | None |

## Decision and purpose

The owner chose the upstream shape on 2026-10-06: the sequence lives in the
CONSYS/WMT owner driver as a fixed table, and private inputs load as firmware
files. There is no userspace command channel. This draft implements Phase A's
common-init step up to, but not including, WLAN START and scan. The
[common-init review](../2026-10-03-mt6797-wifi-audit/COMMON_INIT_REVIEW.md)
owns the selected branches.

## Sequence

The new `mediatek,one-shot-wmt-common-init` flag extends the one-shot
negotiation. After the checked full-mode query, in the same root trigger, the
driver runs 285 steps in the selected vendor order for chip 0x0279:

| Steps | Content | Accepted reply |
| --- | --- | --- |
| 0–2 | DLM power: three masked writes to `0x80100060` | exact register event |
| 3–6 | MCU clock raise: enable, ratio, divider, HCLK | exact register event |
| 7–270 | Both ROM patches: two address commands, all fragments, a WMT reset, per patch | exact events |
| 271–273 | MCU clock restore | exact register event |
| 274–278 | LTE coexistence table, external component zero | exact coexistence event |
| 279–280 | VCN33-BT, then VCN33-WIFI on at 3.3 V | rail reads enabled |
| 281 | RF calibration `01 14 01 00 01` | six bytes starting `02 14 02 00`; status captured |
| 282–283 | Both PA rails off | regulator success |
| 284 | Antenna mode from `mediatek,coex-antenna-mode` | exact coexistence event |

The vendor expects calibration to reply `02 14 02 00 00 01` but never compares
it. The driver records the two status bytes instead of declaring success from
them. Crystal trim, co-clock, merged PCM and FM strap are not selected.

The two ROM patches load with `request_firmware` from `mediatek/mt6797/` and
must match pinned SHA-256 digests and the selected metadata before any command
is sent. The retained `WMT_SOC.cfg` sets only `coex_wmt_ant_mode=1`, already
recorded in the [WMT configuration summary](../2026-07-12-connectivity-wmt-recovery/results/wmt-config-summary.txt).
With no filter-mode key, the vendor defaults select the LTE table above, so the
kernel needs no configuration parser; the antenna mode is one DT property.

Each exchange has a 500 ms deadline, calibration 2 s, within a 30 s budget.
The first failure stops the sequence and keeps power, clocks and rails for
reviewed recovery. The flag requires the AFE region, so the AFE stage always
runs before MCU release, and it excludes the Bluetooth H1 flag.

## Patches

- [0111](../../patches/proposals/0111-dt-bindings-soc-mediatek-mt6797-consys-add-one-shot-common-init.patch)
  adds the flag and `mediatek,coex-antenna-mode` to the binding.
- [0112](../../patches/proposals/0112-soc-mediatek-add-one-shot-MT6797-WMT-common-initialization.patch)
  adds the step table, the existing ROM patch constructor and the executor.

The profile is the STP task-routing profile plus these two patches; the C3
profile is unchanged.

## Validation

[test-common-init.c](test-common-init.c) runs the whole sequence with synthetic
patch files of the exact sizes. It checks 285 steps, 281 exchanges and four
rail steps, full body coverage, exact vendor vectors for DLM, clock restore,
resets, the LTE filter, calibration and antenna mode, and refusals that leave
outputs unchanged. It passes with ASan and UBSan.

```sh
d=$(mktemp -d); cp PREPARED/drivers/soc/mediatek/{stp-full,wmt-full-stp,wmt-rom-patch,mt6797-wmt-common-init}.h "$d"
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -I"$d" test-common-init.c -o "$d/t"
setarch "$(uname -m)" -R "$d/t"
```

The binding passes `dt-doc-validate`. A test DTB with the flag, antenna mode,
supply and AFE region validates. Adding the Bluetooth flag, dropping the
antenna mode or dropping the AFE region each fails. Both patches pass strict
checkpatch, excluding only the missing sign-off and the new files' maintainer
entry.

## Candidate inputs, later

A runtime candidate needs both ROMv3 patch files in the RAM root under
`lib/firmware/mediatek/mt6797/`, with these digests:

| File | SHA-256 |
| --- | --- |
| `ROMv3_patch_1_1_hdr.bin` | `5732c0730380e937b48ad169f2805b65e8d4a178265566c5083cb2cc2d249f1e` |
| `ROMv3_patch_1_0_hdr.bin` | `450c2b0949cf879217ac9aef81b18b860982f0e69340784b448b54365d8cf630` |

It also needs the negotiation and common-init flags, the antenna mode, the
VCN33-BT supply and the AFE region in the CONSYS node. A protocol, the C3
result and the owner's review come first. Calibration success semantics and
WLAN START composition remain open.

## Build

Buildbox compilation on buildbox-3 and remote package validation pass for
input `04a42218`. Fetch and all local checksums pass.

| Item | Value |
| --- | --- |
| Package inventory | `aee609f8384b14912e94f54293d08d5c1123d5514ad231cb4ccd4538bc5d45f9` |
| Board DTB | `07b097d581cae6208eea8387d534e14bb2c2bc30752b0d4b783f711284284734`, identical to the C3 package |
| Release | `7.1.3-gemini-a53-wmt-versions`, inherited from the profile's fragments |

The image contains the executor's log strings and firmware names, and
`CRYPTO_LIB_SHA256` is built in. No new compiler warning appears.
