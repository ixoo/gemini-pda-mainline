# Current upstream and related Wi-Fi source audit

This source-only audit was performed on 2026-09-05 UTC. It changes no kernel
selection and makes no device, association, traffic, or stability claim. The
repository's build baseline remains pinned by `kernel/manifest.json`.
Individual public source files and revision metadata were read over HTTPS in
memory; no Linux tree, firmware image, or third-party source was retained.

## Implementation decision

The smallest defensible path for the built-in radio is an explicit MT6797
CONSYS lifecycle owner plus a narrowly implemented MT6797 AHB Wi-Fi
firmware/HIF driver, exposing standard wireless interfaces. There is no
verified compatible driver to enable with an ID or DT edit. First implement
and test the non-radio boundaries: identity/resource classification and
bounded firmware-container/command parsing. A firmware loader or network
interface is premature until power, transport, memory ownership, and firmware
contracts are closed.

This does **not** require finishing A72 work or implementing Bluetooth/GNSS
function drivers first. It requires coordination with their shared CONSYS
owner. A53 serviceability and an authenticated USB/logging path can carry the
first experiment. The eventual wireless control interface should be
cfg80211; selection of a direct cfg80211 driver versus mac80211 integration
still requires a precise host/firmware MLME and frame-format inventory.
The presence of vendor cfg80211 hooks alone does not establish a FullMAC
firmware contract.

## Identity and transport limits

The [existing named-device evidence](../2026-07-12-connectivity-wmt-recovery/README.md)
observes `CONSYS_MT6797`, property ID `0x6797`, WMT label `MT279`/ROM `E1`,
and an active platform Wi-Fi owner with the `0x180f0000+0x1100` aperture.
The image identifies Gemini 4G UK 6M15BS/X600; its physical SKU was not
independently inspected. No evidence in that record establishes an external
MT6630 or MT6625L SDIO Wi-Fi device on Gemini. Firmware filenames, generic
vendor SDIO tables and `HIF-SDIO` log text do not supply that missing identity.
Preserve the SoC, internal firmware label, and any future RF companion
identity as separate fields.

The top-level Planet build selector chooses **gen3** for `CONSYS_6797`; its
Makefile selects `os/linux/hif/ahb_sdioLike/`, AP-DMA and a private `sdio_func`
shim. The selected platform source spells its compatible `mediatek,WIFI`,
where retained live evidence says `mediatek,wifi`; preserve that source/runtime
contradiction instead of assuming the installed build is byte-identical.
The selected-source correction and exact hashes are in
[FIRMWARE_FORMAT.md](FIRMWARE_FORMAT.md). These facts are stronger bus evidence
than an SDIO-shaped register name.
An ordinary sysfs device-ancestry/driver/resource inventory is the first
discriminating device observation. It should report ambiguity or missing
ancestry honestly, and must not perform SDIO enumeration transactions,
unbinding, MMIO, firmware loading, or radio control.
[top-level selector](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/Makefile#L27),
[selected gen3 HIF](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/Makefile#L92).

## Current Linux compatibility check

The checked Torvalds revision is
[`4d7d9486c04d917265f64c55bd23b2cc4fe7749c`](https://github.com/torvalds/linux/commit/4d7d9486c04d917265f64c55bd23b2cc4fe7749c),
with committer time `2026-09-05T02:36:11Z`. The separately checked mt76
development head is
[`be5ce7910521492d4a2e4ce7ee3843680a46c047`](https://github.com/openwrt/mt76/commit/be5ce7910521492d4a2e4ce7ee3843680a46c047),
dated `2026-09-01T11:25:05Z`. Detailed file checks below use the Torvalds
revision, not an assumed equivalence between these trees.

| Candidate | Source-supported boundary | Decision for Gemini |
| --- | --- | --- |
| `mt76` | The MediaTek Kconfig sources `mt7601u` and `mt76`; mt76 selects MT76x0/x2, MT7603, MT7615, MT7915, MT7921, MT7996 and MT7925 families. Its DT binding includes integrated MT7628, MT7622, MT7981 and MT7986 WMACs. | No MT6797/gen3 match or demonstrated register/firmware compatibility. Integration into an SoC is not itself a reason to reject mt76; the exact unmatched protocol is. |
| `mt7601u` | USB driver for MT7601U dongles, dependent on USB and mac80211. | Wrong chip and bus for the observed built-in AHB interface. |
| `wlcore` | TI SDIO ID and TI WL12xx/WL18xx compatible table. | Neither chip identity nor firmware/register protocol matches. |
| `mwifiex` | Marvell/NXP firmware devices and SDIO IDs. | A cfg80211 architecture example, not a MediaTek protocol backend. |
| `btmtksdio` | Bluetooth HCI driver with MT7663, MT7668, MT7961 and MT7902 IDs. | Not a Wi-Fi driver; generic MediaTek naming does not connect it to this AHB device. |

Primary sources:
[MediaTek Kconfig](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/net/wireless/mediatek/Kconfig),
[mt76 Kconfig](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/net/wireless/mediatek/mt76/Kconfig),
[mt76 binding](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/Documentation/devicetree/bindings/net/wireless/mediatek,mt76.yaml),
[MT7601U Kconfig](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/net/wireless/mediatek/mt7601u/Kconfig),
[wlcore IDs](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/net/wireless/ti/wlcore/sdio.c#L35),
[mwifiex IDs](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/net/wireless/marvell/mwifiex/sdio.c#L956),
[Bluetooth IDs](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/bluetooth/btmtksdio.c#L76).

Searches for MT6797/MT6625/MT6628 Wi-Fi work in public mailing-list indexes
did not identify a matching upstream driver series. This is a bounded search
result, not proof that no unpublished or unindexed work exists.

## Related work and corrections to earlier assumptions

Frank Wunderlich's BPI-Router-Linux is relevant implementation evidence. Its
`5.15-main` revision
[`13bdf2d646f8d8f7ddbef0fbb353d997305aa7b1`](https://github.com/frank-w/BPI-Router-Linux/commit/13bdf2d646f8d8f7ddbef0fbb353d997305aa7b1)
selects an AHB gen2 HIF with MT8127 PDMA support for the MT7623 platform;
the glue has `mediatek,wifi`/`mediatek,mt7623-wifi` matches and the SoC DT
contains CONSYS and Wi-Fi platform nodes. Therefore, describing this port
as an external SDIO counterpart is inaccurate. That gen2 architecture
helps compare lifecycle ideas, but is not the selected MT6797 gen3 driver and
does not prove MT6797 register
or firmware interchangeability.
[BPI Makefile](https://github.com/frank-w/BPI-Router-Linux/blob/13bdf2d646f8d8f7ddbef0fbb353d997305aa7b1/drivers/misc/mediatek/connectivity/wlan/gen2/Makefile#L119),
[BPI AHB glue](https://github.com/frank-w/BPI-Router-Linux/blob/13bdf2d646f8d8f7ddbef0fbb353d997305aa7b1/drivers/misc/mediatek/connectivity/wlan/gen2/os/linux/hif/ahb/ahb.c#L305),
[BPI SoC DT](https://github.com/frank-w/BPI-Router-Linux/blob/13bdf2d646f8d8f7ddbef0fbb353d997305aa7b1/arch/arm/boot/dts/mt7623.dtsi#L762).

The checked `6.12-main` README at
[`2579ef9e812d8ddcd3fe9542bdd571b6a03cf651`](https://github.com/frank-w/BPI-Router-Linux/blob/2579ef9e812d8ddcd3fe9542bdd571b6a03cf651/README.md#L29)
reports internal Wi-Fi/BT broken on Linux 6.0+ and requires WMT tools for
R2. Those are the port maintainer's reports, not Gemini test results. A
vendor-stack port is consequently not a ready maintained upstream solution.

The small
[`abbradar/mt6625l-wlan-gen2`](https://github.com/abbradar/mt6625l-wlan-gen2/tree/5a8fafb8b3d99da21d356219ed599556efbd990b)
repository ends at `5a8fafb8b3d99da21d356219ed599556efbd990b` (2019-09-01).
Its Makefile also selects AHB and an MT7623/MT8127 PDMA path. Neither its
repository name nor `MT6628` compile define identifies the Gemini's physical
RF companion.

Cyrozap's
[`mediatek-wifi-re`](https://github.com/cyrozap/mediatek-wifi-re/tree/bcbb3b914ce1292add14bffdee4f1e0a8af33500)
at `bcbb3b914ce1292add14bffdee4f1e0a8af33500` (2024-01-05) provides
firmware-container analysis, not a Linux host driver. Its notes report
unsuccessful MT6797/MT6735 firmware decryption experiments on MT7697; their
possible explanations remain hypotheses. Its SoC container schema describes
`MTKE`/`MTKW` section tables and marks that schema CC0-1.0. This makes a
strict, independently written metadata validator a useful offline follow-up;
it does not establish which variant the retained Gemini file uses or require
decryption to implement a loader. No firmware was parsed during this initial source-only audit; later private
inspection and the corrected selected-source analysis are recorded in
[FIRMWARE_FORMAT.md](FIRMWARE_FORMAT.md).
[Notes](https://github.com/cyrozap/mediatek-wifi-re/blob/bcbb3b914ce1292add14bffdee4f1e0a8af33500/Notes.md),
[container schema](https://github.com/cyrozap/mediatek-wifi-re/blob/bcbb3b914ce1292add14bffdee4f1e0a8af33500/mediatek_soc_wifi_firmware.ksy).

## Source licensing and firmware rights are different gates

The exact Planet gen2 `wlan_lib.c`, `wlan_lib.h`, `nic_cmd_event.h`, AHB
glue, and MT6797 PDMA files inspected here have MediaTek copyright notices
and explicit GPL version 2 grants. Earlier descriptions of this entire
host stack as proprietary are therefore too broad. These reviewed files are
public GPL source evidence; this does not license every file in the vendor
tree or justify a wholesale downstream driver import. `wlan_lib.c` provides
source-visible section-download and pending-error-query operations for a
comparative protocol audit. The later top-level selection check established
gen3 as the applicable source branch; gen2 format checks are not sufficient
for the retained MTKE image.
[loader source](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen2/common/wlan_lib.c),
[container declarations](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen2/include/wlan_lib.h),
[command declarations](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen2/include/nic_cmd_event.h),
[MT6797 PDMA](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen2/os/linux/hif/ahb/mt6797/ahb_pdma.c).

Linux-firmware HEAD resolved to
[`e981caea6ed33c48d25b7dbf473327dbd01df163`](https://kernel.googlesource.com/pub/scm/linux/kernel/git/firmware/linux-firmware/+/e981caea6ed33c48d25b7dbf473327dbd01df163)
(2026-08-31). Its WHENCE and MediaTek directory contain no exact
`WIFI_RAM_CODE_6797`, `ROMv3_patch_1_0_hdr.bin`,
`ROMv3_patch_1_1_hdr.bin`, or `WMT_SOC.cfg` record. The MediaTek firmware
license grants rights for the firmware to which it applies; this audit found
no association of that grant with the exact retained Gemini files. Treat
their redistribution status as unresolved and keep them private. A similarly
named MT6639 file in the inventory is unrelated evidence, not permission for
MT6797 firmware. Source GPL grants do not extend to firmware binaries.
[WHENCE](https://kernel.googlesource.com/pub/scm/linux/kernel/git/firmware/linux-firmware/+/e981caea6ed33c48d25b7dbf473327dbd01df163/WHENCE),
[MediaTek inventory](https://kernel.googlesource.com/pub/scm/linux/kernel/git/firmware/linux-firmware/+/e981caea6ed33c48d25b7dbf473327dbd01df163/mediatek/),
[firmware license](https://kernel.googlesource.com/pub/scm/linux/kernel/git/firmware/linux-firmware/+/e981caea6ed33c48d25b7dbf473327dbd01df163/LICENSES/LICENCE.mediatek).

The [retained firmware inventory](../2026-07-12-connectivity-wmt-recovery/results/runtime-summary.txt)
already identifies the installed Wi-Fi file by size and digest. Reuse that
private source for future owner-authorized offline validation; do not download
random replacements or publish a firmware payload. Rights uncertainty does
not block source research, host parser tests, disabled resource design, or a
sysfs-only transport observation.

## Dependencies the first active driver must close

| Boundary | Missing proof required before active use |
| --- | --- |
| Shared CONSYS owner | Exact ordered VCN rail, clock, reset/protection and power-ack sequence; function reference counting; failure unwind that preserves BT/GNSS/FM owners. |
| Host transport | Attributed live AHB/platform ancestry; MT6797 DMA register ownership and mapping, limits, address width, coherency, interrupt acknowledgement and bounded timeout/reset behavior. Do not import another SoC's extra DMA DT window. |
| Firmware/control protocol | Exact WMT patch selection, WLAN function-on dependency, HIF ownership handshake, packet/sequence/status semantics, download/start addresses and bounded failure recovery for the retained firmware revision. |
| Shared RAM | Post-LK CONSYS reservation location and extent, remap/MPU contract, and separation from other firmware and runtime memory. |
| Radio constraints | Board calibration/efuse provenance and handling, regulatory limits and a proven no-transmit state before firmware/controller identification. Raw calibration and identifiers remain private. |
| Wireless stack | Data and management frame formats, firmware versus host MLME responsibilities, key handling, association events and TX/RX completion semantics. |

These gates refine implementation scope; they are not an ordered roadmap.
The owning experiment and coordinator control admission and next actions.

## Reproducible file identities

Hashes are SHA-256 of the raw bytes at the exact revisions above. GitHub
`blob` links identify the files; the corresponding `raw.githubusercontent.com`
path can be hashed directly without checking out a source tree.

| Revision group and file | SHA-256 |
| --- | --- |
| Linux: `drivers/net/wireless/mediatek/Kconfig` | `7637f36bf9f374dde6df785e3caab3a1750b488f9dff841e0578b8c49a4682fd` |
| Linux: `drivers/net/wireless/mediatek/mt76/Kconfig` | `14c631914e62d68a9fa0d2aac6afe5e41d942d48d2c353c4e093ae89b65c3d17` |
| Linux: `Documentation/devicetree/bindings/net/wireless/mediatek,mt76.yaml` | `c26203cf93b48ed4c4cea6c05cfafcb2f12df2baeae1ad39724173ad9c2e5765` |
| Linux: `drivers/net/wireless/mediatek/mt7601u/Kconfig` | `282052159dfae34b0a244de4647ce5b2961270ae4f7b341c95c255c67fb01f41` |
| Linux: `drivers/net/wireless/ti/wlcore/sdio.c` | `9ca02f7e280d742700189b74dcabda994f6e82b6101c3173e67415f2680a3ba3` |
| Linux: `drivers/net/wireless/marvell/mwifiex/sdio.c` | `db506c01557ea2f45050e047ba6bc2ed967de71e0be0a68edc20f69213996ccb` |
| Linux: `drivers/bluetooth/btmtksdio.c` | `30abe2f50dd5113a288ed72b956eaf6194713edb4fe95e3647d0796c53243634` |
| Planet: `drivers/misc/mediatek/connectivity/wlan/gen2/Makefile` | `4c374760e32142a31ea7e020ec2a251d04d18600f2e735f8ad4dc3de52a52807` |
| Planet: `drivers/misc/mediatek/connectivity/wlan/gen2/common/wlan_lib.c` | `4be5fdfece362df656330bd5ca64fb102d8f69de6ed076d7bc0f3677d0645a6e` |
| Planet: `drivers/misc/mediatek/connectivity/wlan/gen2/include/wlan_lib.h` | `d447217c4daec8597b795c49d57250db6b1f88e5b47574a52c2e12ef0a97a5e1` |
| Planet: `drivers/misc/mediatek/connectivity/wlan/gen2/include/nic_cmd_event.h` | `89a6c97e17a6fd3b78ffa14eb0a8c5dedcf442dd0c12ecbd6f457fb44a1de269` |
| Planet: `drivers/misc/mediatek/connectivity/wlan/gen2/os/linux/hif/ahb/ahb.c` | `62fbadbbac5f3062a23435cf66f39b2286bc6d15807da8cf2a299914467a5e42` |
| Planet: `drivers/misc/mediatek/connectivity/wlan/gen2/os/linux/hif/ahb/mt6797/ahb_pdma.c` | `b2db0e01ccae1ad21da8236adb49b7edfe82152df82e665eecf0f4cdd7273046` |
| BPI 5.15: `drivers/misc/mediatek/connectivity/wlan/gen2/Makefile` | `ee00462e601049381d1d093317642e821ba1dc81a547bedbaf75d898c3a3d922` |
| BPI 5.15: `drivers/misc/mediatek/connectivity/wlan/gen2/os/linux/hif/ahb/ahb.c` | `d58e67f83fb05cae794f4732a119ec02ae2dcf071d7f0773c546b36af7e8953c` |
| BPI 5.15: `arch/arm/boot/dts/mt7623.dtsi` | `070dfe2fbd1cf517b65ad8647c001ee0c3249b88458d013edf2f7be47be18630` |
| BPI 6.12: `README.md` | `e174a19ec5e57f54dc69a049dcdea74327414df33c34e4a390f3f2e1a1e9acba` |
| abbradar: `Makefile` | `90d76ecc6330e8fc1da014739d45b177bd2b417557d170e50431c1aaff63f4e4` |
| cyrozap: `Notes.md` | `2fe39f5a128a09b52c41012c2812e24e80d544f56bb356eb7fa369af013a20df` |
| cyrozap: `mediatek_soc_wifi_firmware.ksy` | `aaec29e17725e6fd7b90d455308fed788122fdce5942abc7e990e0824bfb3378` |
| linux-firmware: `WHENCE` | `34f954c7d068ec4fd5fcc216471912dd3cf40ff60a7ffa8d06ff6f9b5999551f` |
| linux-firmware: `LICENSES/LICENCE.mediatek` | `a90d3f66704d85889945fec5525ea77622549da83aced1aac99828383f8f1805` |
