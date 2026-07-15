# MT6797 connectivity mainline design

Status: `inconclusive` for runtime support; the vendor transport, power, and
firmware boundaries are recovered from source and the idle Gemian capture. No
radio was powered, no SDIO/BTIF transaction was issued, and no firmware was
loaded by this investigation.

## Evidence and reproducibility

Run the source-only analyzer in the development VM:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-12-connectivity-wmt-recovery/scripts/analyze-mt6797-connectivity-contract.sh
```

The analyzer reads vendor files from Git objects, which keeps the result
reproducible even when the checkout is sparse. It emits hashes, register and
protocol anchors, Linux framework matches, and a decision summary. It does not
map hardware, touch `/dev/stpwmt`, access SDIO, or change radio state.

The vendor evidence is Planet's MT6797 tree at commit
`c5b0be85017ad0c599725e8273842efdbecdd88a`. The Linux comparison is the
prepared Linux `7.1.3` source in the VM.

Selected source hashes from the analyzer run:

| Source | SHA-256 |
| --- | --- |
| Vendor `mtk_wcn_consys_hw.h` | `3ee7631a95a12f5cddd860c213e51e75e1cb3146ca858a892aaae55b4d22fad1` |
| Vendor `mtk_wcn_consys_hw.c` | `0ec8e9c1594626d0b31f2d2623927d614f63af4437c16df838e10e11258663ce` |
| Vendor `wmt_plat_alps.c` | `b81db9778bfebf0230cf67a924f25270112ef2c369fb221328f3f4aef3bea1ec` |
| Vendor `stp_core.h` | `78abfa5601723b0dd2aac93b2c79d5e7fb6a75a948aa06d516df7dfc5102b30f` |
| Vendor `stp_core.c` | `7bc7a5bf3f2231b6fca8eac1fa8744eb792de75c79f6e859f6109a50008956ea` |
| Vendor `stp_btif.c` | `cadce8870cf8b1933862064ea91832a37abd071663c88d9c38c204ead5774b34` |
| Vendor `stp_sdio.c` | `bb564d19938c807af3ae7a173e0378c791d93d04a0b898606e95dc348f87cd45` |
| Vendor `stp_uart.c` | `83ff2ed18e614f4739c30de68fcb111a27f41ce684d786b69f34d0e7cb4b24b3` |
| Vendor `wmt_dev.c` | `d7be291ca5e2962be24def406260b5bb21a4b85438f64a1064944686a84fd62e` |
| Vendor `hif_sdio.c` | `04c528ce589400194dc1f206b3f5e9478a1903059493e7f0bec8c31fb2d3ec90` |
| Vendor `sdio_detect.c` | `62aa85cf82777be34084ff2c9b5cb70f89627a4a9eb00dfa3d9719065a5afc48` |
| Vendor `btif_priv.h` | `3cb7cc939b2d59be36f48f6c0d4093acd552e7cd7058bf736ec83c398db82110` |
| Vendor `btif_plat.c` | `91744beb769a3414cba3cfc2920fffd7b2254b8e6a7861ea0abafa37e90c5872` |
| Vendor `btif_dma_plat.c` | `2f247d8a7a6ee60913f318a5db43da7813c047cb8980790d15073dd269ee693a` |
| Vendor MT6797 Wi-Fi `hif_pdma.h` | `28424fd8e1bff338ed9297709f990fe067c6ecc81b155a0f0fd80519d23930a8` |
| Vendor MT6797 Wi-Fi `ahb_pdma.c` | `b2db0e01ccae1ad21da8236adb49b7edfe82152df82e665eecf0f4cdd7273046` |
| Linux `drivers/bluetooth/btmtkuart.c` | `f0ed75c1de8a08bcf543975c927078be5d8de988bb25bc37898a8c37a29914af` |
| Linux `drivers/bluetooth/btmtksdio.c` | `4cf63fbc0c63cd8fb489c6426dcf90994dbfa0fae6900180ea819ceeb2ea7dc1` |
| Linux `drivers/bluetooth/btmtk.c` | `032bc289e8da1f3114b9a56894bb8ab7abfa82950c0d618ad26ed5d8be43af66` |
| Linux `drivers/gnss/mtk.c` | `662889ca84f6b703a8a9e802501a0fb30994fff9edd5b348902e164551f790bb` |

The live capture establishes the observed board contract:

- `mediatek,mt6797-consys` has windows `0x18070000+0x200`,
  `0x10007000+0x100`, `0x10000000+0x2000`, and `0x10006000+0x1000`, level-low
  SPIs 284/285, clock `SCP_SYS_CONN`, and supplies `vcn18`, `vcn28`,
  `vcn33_bt`, and `vcn33_wifi`;
- Wi-Fi has `0x180f0000+0x1100`, SPI 283, and `INFRA_AP_DMA`/`wifi-dma`;
- BTIF has `0x1100c000+0x1000`, SPI 130, plus TX/RX DMA windows
  `0x11000a00+0x80`/`0x11000a80+0x80`, SPIs 116/117; and
- firmware metadata identifies `CONSYS_MT6797`/chip property `0x6797`, WMT
  status label `MT279`/ROM `E1`, and installed WMT, Wi-Fi, GNSS, and MT6631 FM
  blobs whose redistribution terms are unresolved.

The current prepared source and package were rechecked on 2026-07-13. The
71-patch Linux `7.1.3` source hash is
`be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`, the
patchset hash is
`86145c09fc00fd3c65fb822f7834c5bb3dc08eb76f5117b90538141a429a1623`, and the
Gemini DTB hash is
`fb910c8d96b7d4f533c750ce0717ced8998c992834abc44a4ed86ec5a9cf1f97`. The
source-only analyzer output hash is
`f7f6311aa341e3dadb67d0bf63128476f2d7fe47a93b6b78b499a5cf9c3a7a5a`; its
full current result is [recorded here](mainline-connectivity-current-71-validation-20260713.txt).
That result deliberately reports `mainline_connectivity_driver=not_enabled`,
`runtime_radio_bringup=not_attempted`, `firmware_load=not_attempted`, and
`hardware_write=none`.

The extracted userspace audit adds a second, independent boundary record. The
payload is not executed; hashes and bounded static output are in
[`userspace-binary-audit.txt`](userspace-binary-audit.txt):

- `wmt_launcher` is AArch64 and explicitly selects UART, BTIF, or SDIO,
  opens `/dev/stpwmt`, reads the chip ID with a private ioctl, and consumes
  `WMT.cfg`/Android properties;
- `wmt_loader`, `wmt_loopback`, `wmt_concurrency`, and `stp_dump3` expose
  additional private WMT detect, loopback, concurrency, and debug/ioctl
  surfaces;
- `mtk_agpsd` is an ARM32 SUPL/TLS daemon with local `agpsd2`/`agpsd3`
  sockets, while both 32-bit and 64-bit `gps.mt6797.so` HALs export the same
  `hal2mnl_*`/`gpshal2mnl_*` callback family and UDP helpers; and
- `libwifitest.so` exposes manufacturing TX/RX, MCR/eFuse, rate, channel, and
  power operations through `/dev/wmtWifi`, separate from the normal Wi-Fi
  MAC/HIF path.

The disassembly neighborhoods retain private request-word construction without
pretending to know command names: `wmt_launcher` directly loads `0x5423` and
`0x400455c8`, then assembles requests around `0x8004a00c`, `0x4004a00e`,
`0x4008a00f`, `0x8004a016`, and `0xc008a014`. These values are useful anchors
when matching a future vendor-kernel header or a non-transmitting trace, but
they are not a mainline ABI proposal.

These observations reinforce the ownership decision: mainline needs standard
HCI, cfg80211, and GNSS interfaces behind an explicit consys/firmware owner;
it must not preserve the Android character devices or factory-test ABI.

## Consys is the power and firmware owner

The vendor MT6797 source does not treat Wi-Fi, Bluetooth, GPS, and FM as
independent chips. `mtk_wcn_consys_hw.c` matches `mediatek,mt6797-consys`,
obtains the four VCN regulators, maps the four DT windows, controls the
`SCP_SYS_CONN` clock, and sequences SPM power/ack bits before reading a
connectivity MCU chip ID at `mcu_base + 0x08`. It also writes MT6797-specific
CONSYS AFE registers at `0x180b6000` and installs the BGF wake IRQ through the
consys node. The power path has direct PMIC and clock-manager fallbacks and
vendor-specific reset/protection keys; it is not a generic fixed-regulator
consumer.

Mainline should therefore have one explicit MT6797 consys owner for clocks,
regulators, reset/wake, and firmware lifecycle. It must not expose each
function as an independently powered platform device or copy direct PMIC
register writes into a Bluetooth/Wi-Fi child driver. The four-window map and
VCN supply names are good DT evidence, but the exact reset/protection sequence
needs a bounded bring-up experiment before any node is enabled.

## STP framing is reusable; Gemini's BTIF/old-combo SDIO transports are not yet upstream

The vendor `stp_core.h` defines a common transport protocol with UART, BTIF,
and SDIO modes. Its packet state machine uses a four-byte header, a 12-bit
length/type field with prefix `0x80`, H:4 or WMT payloads, and a two-byte
trailer. `stp_btif.c` submits the same packets through `mtk_wcn_btif_write()`
with bounded retries; `stp_sdio.c` uses the SDIO host-function client and
firmware-own handshake; `stp_uart.c` exposes a legacy line discipline
(`N_MTKSTP`) rather than a modern serdev device.

Linux `btmtkuart.c` independently implements the same broad wire shape: a
`0x80`-prefixed four-byte STP header, H:4 packet dispatch, two-byte trailer,
WMT vendor events, and firmware setup through `btmtk.c`. Linux also has
`btmtksdio.c`, but that driver is table-bound to MT7663/MT7668/MT7921/MT7902,
uses a five-byte SDIO header and 256-byte blocks, and carries newer-chip
firmware/chip data. The vendor table recovered here names 0x6628/0x6630/0x6632
function-2 devices, uses a four-byte SDIO header, 512-byte blocks, and a
2080-byte FIFO. This is strong evidence for reusing HCI/WMT framing and
firmware-helper semantics, not for binding either existing transport directly:
the captured active path has BTIF resources and custom DMA, wake, ownership,
and IRQ behavior.

The mainline boundary should be a transport adapter that feeds standard HCI
and WMT handling. A small `mediatek,mt6797-btif` driver must model the BTIF
registers, DMA channels, BGF IRQ, clock, and consys wake callback. If the
transport is later proven to use SDIO for the HCI function, a separate SDIO
function driver should implement the vendor own/interrupt/block/four-byte-header
protocol and reuse only the common STP/HCI layer; extending `btmtksdio`'s
newer-chip table would be insufficient. Do not preserve `/dev/stpwmt` or its raw
ioctl ABI as the mainline interface.

## Wi-Fi is a proprietary MAC over an AP-DMA HIF

The vendor Wi-Fi gen2 tree contains a full cfg80211/netdev implementation,
firmware configuration, management state machines, and an MT6797 AHB PDMA
HIF. Its PDMA register block has control, source, destination, length, reset,
interrupt, and debug registers; the vendor DT exposes only the live
`0x180f0000+0x1100` window and SPI 283. The code is not a thin transport
driver for a standard MT76 MAC, and the vendor SDIO/WMT layers are shared with
Bluetooth/GPS rather than a standalone Wi-Fi bus device.

Linux `mt76` therefore cannot be selected by compatible-string or MediaTek
family similarity. A mainline Wi-Fi implementation needs a new firmware-aware
MAC/HIF driver (or a separately documented upstream protocol implementation),
standard cfg80211 integration, and an explicit consys/SDIO/AP-DMA ownership
model. The installed `WIFI_RAM_CODE_6797` is evidence of a firmware boundary,
not a redistributable asset. Keep this path disabled until licensing and a
non-transmitting SDIO/function-identification protocol are available.

## GNSS and FM are later function drivers

The observed `ROMv3_patch_1_1_hdr.bin` contains GNSS/geofence/FLP strings and
the vendor image exposes `stpgps`/`gps` character paths. Linux `gnss-mtk.c` is
a serial GNSS consumer for a different `globaltop,pa6h` contract, so it is not
a direct match. A mainline GNSS driver can reuse the GNSS core only after the
consys message routing and ownership are proven.

The MT6631 FM configuration/patch/coefficients and `/dev/fm` path are separate
from ordinary MT6351 audio. No Linux 7.1.3 MT6631 driver was found. Keep FM
and FM-I2S board wiring out of the first audio or Bluetooth series.

## Bring-up gates and implementation order

1. Prove the consys chip-ID/clock/VCN sequence using a read-only identity test
   and an owner-approved power-cycle plan; never begin with firmware loading.
2. Add disabled-only consys and BTIF resource descriptions, then validate IRQ
   domains, DMA windows, and wake polarity without transmitting.
3. Reuse Linux STP/HCI framing and firmware helpers behind a BTIF transport;
   test only bounded controller identification and HCI reset with an external
   recovery path.
4. Describe the SDIO function IDs and block/own protocol only after live SDIO
   enumeration is captured; keep Wi-Fi and BT function ownership separate.
5. Treat Wi-Fi, GNSS, and FM as independent subsequent drivers with explicit
   firmware/license records. Record negative and inconclusive results.

The current repository therefore needs a new MT6797 consys/BTIF transport
boundary, but not a fork of Linux's HCI/STP protocol layer. It also needs a
new Wi-Fi MAC/HIF boundary unless a future protocol audit proves compatibility
with an existing upstream driver. No connectivity patch is enabled by this
experiment.
