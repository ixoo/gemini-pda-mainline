# Experiment: MT6797 connectivity, WMT, Wi-Fi, Bluetooth, GNSS, and FM recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-connectivity-wmt-recovery` |
| Status | `inconclusive` for mainline runtime support; transport and firmware boundary recovered |
| Subsystem | MT6797 connectivity subsystem, WMT/STP, Wi-Fi, Bluetooth, GNSS, FM |
| Device variant | Gemini PDA running Gemian; Android property identifies the observed image as Gemini 4G UK 6M15BS/X600, but physical SKU is not independently inspected |
| Date(s) | 2026-07-12 through 2026-07-14 |
| Investigator(s) | Repository maintainer with Codex assistance |
| Tracking issue | None |

## Question or hypothesis

What silicon, buses, interrupt resources, power supplies, firmware, and
userspace/kernel interfaces make up the Gemini connectivity stack, and can any
of it be represented by Linux 7.1.3 drivers already present upstream?

The reuse-first hypothesis is deliberately split by function: generic
`btmtkuart`/serdev and `gnss-serial` may be useful protocol layers, but the
Gemini's vendor `mediatek,mt6797-consys`, STP framing, Wi-Fi DMA engine, BTIF
transport, firmware boot, GPS LNA pin, and MT6631 FM path need a board-specific
transport/firmware design. A vendor WMT character-device wrapper is not an
upstream boundary.

## Provenance and safety

- Live device: `gemini@192.168.1.50`, Gemian, kernel `3.18.41+`, model `MT6797X`.
- Live collector: [`collect-live-connectivity.sh`](scripts/collect-live-connectivity.sh).
- Sanitized result: [`results/runtime-summary.txt`](results/runtime-summary.txt).
- Read-only rerun (2026-07-13), including current platform bindings and IRQ
  counters: [`results/live-connectivity-rerun-20260713.txt`](results/live-connectivity-rerun-20260713.txt).
- Fresh read-only repeat (2026-07-14), including active Wi-Fi/HIF and BTIF DMA
  counters: [`results/live-connectivity-repeat-20260714.txt`](results/live-connectivity-repeat-20260714.txt).
- Fresh post-reboot read-only capture (after the device returned from a battery
  depletion reboot): [`results/live-connectivity-postreboot-20260714.txt`](results/live-connectivity-postreboot-20260714.txt).
- Static user-space string/hash summary: [`results/userspace-summary.txt`](results/userspace-summary.txt).
- Sanitized WMT configuration fields: [`results/wmt-config-summary.txt`](results/wmt-config-summary.txt).
- Raw output, if regenerated, belongs only below a date-stamped, Git-ignored
  `artifacts/device-inventory/*-connectivity-live/` directory.
- Generic vendor source: [Planet MT6797 tree commit
  `c5b0be85017ad0c599725e8273842efdbecdd88a`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/tree/c5b0be85017ad0c599725e8273842efdbecdd88a), especially
  `arch/arm64/boot/dts/mt6797.dtsi` and `aeon6797_6m_n.dts`.
- Earlier Gemian GPL reference tree: [commit
  `d388d350cb2dda8f23b99be6fa5db9628896e87f`](https://github.com/gemian/gemini-linux-kernel-3.18/tree/d388d350cb2dda8f23b99be6fa5db9628896e87f); it contains the public-facing
  WCN callback declarations but not the proprietary connectivity driver body.
- Mainline comparison: pinned Linux `7.1.3` in the development VM.

The collector is read-only. It does not call `rfkill`, `iw`, `hciconfig`, WMT
ioctls, HCI test tools, network scans, firmware loaders, or debugfs write
interfaces. Firmware files are hashed in place only; they are not copied into
Git. MAC addresses, serial-like properties, and radio payloads are excluded.

The 2026-07-14 repeat confirms `mtk_wmt`, `mtk_btif`, vendor BTIF TX/RX DMA,
`mt-wifi`, and vendor GPS owners are still bound. It observed an operational
`wlan0`/HIF path and cumulative BTIF DMA IRQ activity without issuing a
transaction; the raw capture remains private and Git-ignored.
The post-reboot capture shows the same owners, resources, interface state, and
firmware hashes. Its early log also makes the loader boundary explicit:
Android's `ueventd` fallback satisfies initial `Direct firmware load ... -2`
requests for `WMT_SOC.cfg` and both ROMv3 patches from the vendor firmware
directory. Mainline must provide a normal firmware-class path and explicit
ownership rather than depending on that Android fallback.

## Live observations

The normalized capture records these durable contracts:

- Android properties identify the combo as `CONSYS_MT6797`, expose chip ID
  `0x6797`, and set the Wi-Fi module postfix `_consys_mt6797`; Wi-Fi advertises
  `wlan0`, `p2p0`, and `ap0` names. The same image's WMT status file reports
  internal chip label `MT279`, ROM `E1`, branch `W1715MP`, and patch date
  `20180307`. These are two naming layers, not silently treated as identical
  silicon IDs.
- `wmt_launcher` is running with `/vendor/firmware/`; `bluetoothd`,
  `mtk_agpsd`, and `stp_dump3` are present. `wmt_loader` is stopped after the
  launch sequence. The vendor exposes `/dev/stpwmt`, `/dev/wmtdetect`,
  `/dev/wmtWifi`, `/dev/stpgps`, `/dev/gps`, and `/dev/fm`.
- The live `consys@18070000` node is `mediatek,mt6797-consys` with four
  register windows: `0x18070000 + 0x200`, `0x10007000 + 0x100`,
  `0x10000000 + 0x2000`, and `0x10006000 + 0x1000`. It has level-low GIC
  SPIs 284 (BGF EINT) and 285 (WDT EINT), the `SCP_SYS_CONN` clock, and
  `vcn18`, `vcn28`, `vcn33_bt`, and `vcn33_wifi` supplies.
- The board DTS adds four consys pinctrl states for GPIO69 (`gps_lna`):
  initialization output-low, output-high, and output-low runtime states.
  The WMT config independently says `wmt_gps_lna_pin=0` and
  `wmt_gps_lna_enable=0`; this is a software configuration distinction, not
  proof that the LNA is physically populated or enabled.
- The live Wi-Fi platform node is `wifi@180f0000`, compatible
  `mediatek,wifi`, with `0x180f0000 + 0x1100`, GIC SPI 283, and the
  `INFRA_AP_DMA`/`wifi-dma` clock. The Planet board DTS has only this window
  and IRQ; a different generic reference tree adds a second DMA window and
  `hardware-values`, so those additions are rejected for Gemini until live
  evidence supports them.
- BTIF has the vendor resources `btif@1100c000` (`0x1100c000 + 0x1000`, SPI
  130, `INFRA_BTIF` plus `INFRA_AP_DMA`), `btif_tx@11000a00` (SPI 116), and
  `btif_rx@11000a80` (SPI 117). The vendor `/proc/interrupts` labels show
  active BTIF TX/RX DMA traffic. The printed vendor IRQ numbers include the
  GIC offset; DT SPI numbers must not be compared to them without accounting
  for that offset. By that consistent +32 mapping, the `BTIF_WAKEUP_IRQ` line
  corresponds to the consys BGF SPI path; retain this as an IRQ-name inference
  until a mainline-visible interrupt-domain mapping confirms it.
- The vendor DT also exposes `gps` (`mediatek,gps`) and `gps_emi`
  (`mediatek,gps_emi-v1`) pseudo/platform nodes, and a dynamically allocated,
  no-map `consys-reserve-memory` region of 2 MiB aligned within the 0x40000000
  to 0xc0000000 range. This is a retained firmware/transport contract, not a
  reason to expose arbitrary reserved RAM to a mainline user.
- The firmware inventory contains `WMT_SOC.cfg`, two `ROMv3_patch_*` images,
  `WIFI_RAM_CODE_6797`, and MT6631 FM configuration/patch/coefficients. The
  WMT files share header date/version text `20180307b001005`; the second ROMv3
  image contains GNSS/geofence strings. Presence and hash are evidence of the
  installed boundary, not redistribution permission or proof that every file
  is loaded by every function.
- The current 7.1.3 package retains only generic HCI/STP, cfg80211/mac80211,
  GNSS, and unrelated MT76 modules. `btmtkuart`, `btmtksdio`, and all MT6797
  CONSYS/BTIF/WMT/Wi-Fi transport support are absent; the Gemini DTB keeps only
  the `no-map` CONSYS reservation and has no active connectivity nodes. See the
  [current 77-patch package validation](results/mainline-connectivity-current-77-package-20260714.txt).

## Associated source analyzer

The source-level comparison is read-only. It reads vendor files from Git
objects and compares the MT6797 consys, BTIF, STP, SDIO, and Wi-Fi HIF
contracts with Linux 7.1.3 Bluetooth, firmware, and GNSS layers:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-12-connectivity-wmt-recovery/scripts/analyze-mt6797-connectivity-contract.sh
```

Its design record is
[`mt6797-connectivity-mainline-design.md`](results/mt6797-connectivity-mainline-design.md).
The source-contract recheck is retained as historical evidence from the
superseded package `86145c09fc00`:
[`mainline-connectivity-current-71-validation-20260713.txt`](results/mainline-connectivity-current-71-validation-20260713.txt).
The authoritative current package/provenance boundary is
[`mainline-connectivity-current-77-package-20260714.txt`](results/mainline-connectivity-current-77-package-20260714.txt).
The Image/DTB-only package's config/module/DT boundary is byte-identical across
two direct VM runs and can be regenerated with:

```sh
./scripts/dev-vm run bash -lc \
  'CURRENT_PACKAGE=/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-b7721ab55e41 \
   experiments/2026-07-12-connectivity-wmt-recovery/scripts/audit-current-package-connectivity.sh'
```
The earlier 70-patch and 61-patch records remain historical at
[`mainline-connectivity-current-70-validation-20260713.txt`](results/mainline-connectivity-current-70-validation-20260713.txt) and
[`mainline-connectivity-current-validation.txt`](results/mainline-connectivity-current-validation.txt).

The extracted userspace payload is also audited statically by
[`analyze-connectivity-userspace.sh`](scripts/analyze-connectivity-userspace.sh).
The report records ELF architecture, dependency edges, exported GNSS/Wi-Fi
test symbols, bounded string anchors, and disassembly neighborhoods around
private `ioctl` calls. It never executes a payload binary or invokes an ioctl;
the report is [`userspace-binary-audit.txt`](results/userspace-binary-audit.txt).

## Source and Linux 7.1.3 comparison

The Planet DTS source confirms that the connectivity block is a single
`consys` power/firmware owner, not a collection of independent Wi-Fi and
Bluetooth chips. Its public WCN stub describes function types BT, FM, GPS,
WIFI, WMT, and STP, and common interfaces UART, MSDC/SDIO, and BTIF. The same
stub exposes callbacks for audio-pin control, function power control, thermal
queries, deep-idle coordination, reset, and SDIO external IRQ/PM registration.
These callbacks explain why copying only the `wifi@` node is insufficient.

The deeper source comparison confirms that the vendor STP wire format itself
is a reusable layer: a `0x80`-prefixed four-byte length/type header, H:4 or WMT
payload, and two-byte trailer are also handled by Linux `btmtkuart.c`. Linux
also has `btmtksdio.c`, but that driver is table-bound to MT7663/MT7668/MT7921/
MT7902 and uses a five-byte SDIO packet header with 256-byte blocks. The
vendor Gemini-era SDIO table instead names 0x6628/0x6630/0x6632 function-2
devices, uses a four-byte SDIO header, 512-byte blocks, and a 2080-byte FIFO.
The captured active path is BTIF with custom DMA, firmware-own, wake, and IRQ
handling, so neither existing transport binds directly. The exact source hashes and register anchors are in
the [connectivity design record](results/mt6797-connectivity-mainline-design.md).

Linux 7.1.3 has useful generic layers:

- `drivers/bluetooth/btmtkuart.c` implements MediaTek STP/H:4 framing over
  serdev and WMT command events, but it expects a serdev UART and does not bind
  `mediatek,btif` or own the Gemini consys power/firmware sequence.
- `drivers/bluetooth/btmtksdio.c` implements a reusable HCI/WMT SDIO core for
  newer MT7663/MT7668/MT7921/MT7902 IDs. Its ownership registers overlap the
  vendor SDIO block, but its ID table, five-byte packet header, 256-byte block
  size, and firmware/chip-data contracts do not match the Gemini evidence; do
  not add the old IDs or bind it by family name alone.
- `drivers/gnss/mtk.c` is a generic serial GNSS consumer for `globaltop,pa6h`
  with `vcc`/`vbackup`; it does not match the vendor `mediatek,gps` pseudo-node
  or the combo firmware's GNSS/FLP path.
- `drivers/net/wireless/mediatek/mt76` supports different standalone MT76
  silicon and buses; there is no MT6797 `mediatek,wifi`/WMT SDIO binding in
  the pinned source. No MT6631 FM driver is present.
- Generic regulator, clock, pinctrl, SDIO, serdev, Bluetooth HCI, cfg80211,
  and GNSS core APIs remain the preferred integration layers after the
  firmware/transport contracts are understood.

### Userspace boundary recovered from extracted binaries

The static audit adds evidence that the vendor userspace is coupled to the
private kernel WMT ABI, rather than merely opening a normal serial or SDIO
device:

- `wmt_launcher` is AArch64, opens `/dev/stpwmt`, reads the chip ID through an
  ioctl, loads `/system/vendor/firmware/WMT.cfg`, and explicitly selects a
  common interface of UART, BTIF, or SDIO. Its UART path configures the
  `N_MTKSTP` line discipline and `HCIUARTSETPROTO`; the default selection text
  falls back between BTIF and SDIO when no mode is supplied.
- `wmt_loader` opens `/dev/wmtdetect`, changes WMT debug proc ownership, and
  contains an SDIO 3.0 auto-calibration path. `wmt_loopback`,
  `wmt_concurrency`, and `stp_dump3` all open `/dev/stpwmt` and issue private
  test/debug operations. These tools are evidence of the ABI, not candidates
  for a mainline userspace contract.
- `mtk_agpsd` is a separate 32-bit ARM executable with OpenSSL, netd, ICU, and
  local-socket dependencies. Its strings identify SUPL/TLS state machines,
  `/dev/socket/agpsd2`, `/dev/socket/agpsd3`, and a large `/data/agps_supl`
  control/log tree. It is not a serial GNSS daemon that can be replaced by
  `gnss-serial` without preserving the modem/CONSYS message owner.
- Both 32-bit and 64-bit `gps.mt6797.so` HALs export the same `hal2mnl_*` and
  `gpshal2mnl_*` interface family, plus UDP socket helpers and callbacks for
  measurements, navigation messages, network availability, and data
  connections. This confirms an Android HAL-to-MNL/userspace boundary, not a
  direct Linux GNSS character-device contract.
- `libwifitest.so` exports factory/test operations for MCR/eFuse access, TX/RX,
  channel/rate/power control, and `wifi_set_power`; it opens `/dev/wmtWifi` and
  depends on `libnvram`. These symbols are write-capable manufacturing tools,
  not evidence for the normal Wi-Fi MAC/HIF protocol, and were not executed.

The report also preserves raw ioctl call-site neighborhoods and their observed
request-word construction without assigning vendor command names. For example,
`wmt_launcher` directly loads `0x5423` and `0x400455c8`, and assembles further
requests around `0x8004a00c`, `0x4004a00e`, `0x4008a00f`, `0x8004a016`, and
`0xc008a014`. Decoding those words requires the matching proprietary kernel
headers or a controlled non-transmitting trace; guessing names from `_IO*` bit
patterns would create a false ABI contract.

As a build-only source check, Linux 7.1.3 `btmtk.o`, `btmtksdio.o`, and
`btmtkuart.o` all compile in the current VM tree. The generic SDIO object is
not enabled in the Gemini fragment because its table/header/block contract is
not a Gemini match; compiling it here verifies that the reusable HCI/WMT core
remains available without claiming a bindable device.

## Analysis and mainline boundary

The current evidence supports the following decomposition:

1. Add a mainline MT6797 consys power/clock/reset/firmware transport only
   after the WMT firmware protocol, reserved-memory ownership, BGF/WDT IRQs,
   VCN supplies, and SDIO external IRQ path are specified. Keep it disabled
   while the firmware license and exact load protocol are unresolved.
2. Treat the vendor Wi-Fi node as a DMA/HIF engine feeding a WMT/SDIO combo
   device, not as a complete Wi-Fi MAC. The first upstream Wi-Fi milestone is
   a standard cfg80211 interface behind a documented firmware boundary; do not
   reuse `mt76` by compatible-string similarity.
3. For Bluetooth, reuse the standard HCI/STP framing and `btmtk` WMT core where
   packet traces prove compatibility, but add a `mediatek,mt6797-btif`
   transport for the `0x1100c000` and DMA resources. If SDIO is proven to carry
   HCI, add a separate old-combo SDIO transport rather than extending
   `btmtksdio`'s newer-chip table. Do not expose `/dev/stpwmt` as a permanent
   mainline API.
4. GNSS is combo-firmware-owned in the observed image (the ROMv3_1_1 strings
   include GNSS/geofence and the vendor path uses `stpgps`/`gps`), so the
   generic serial GNSS driver is not enough. A standard GNSS character/serdev
   interface can be added only after ownership and message routing are proven.
5. FM and audio are separate: the MT6631 blobs and vendor `/dev/fm`/FM-I2S
   path must not be conflated with the ordinary MT6351 ASoC card.

No connectivity kernel patch is added by this experiment. The evidence is
strong enough to replace “unknown combo chip” with a precise MT6797 consys
transport description, but not strong enough to enable radio hardware or
invent a firmware loader.

## Conclusion

`inconclusive` for mainline runtime support. The live device, Planet DTS, WMT
status, firmware metadata, and Linux 7.1.3 source comparison identify the
transport boundary and the generic reuse candidates. A future implementation
must first obtain owner-authorized, non-transmitting protocol traces or a
redistributable firmware specification, then add disabled-only DT and bounded
probe tests.

## Follow-up gates

1. Verify exact `consys-reserve-memory` placement and firmware ownership under
   the mainline boot contract; never map it generically.
2. Capture a controlled Bluetooth HCI bring-up trace and Wi-Fi SDIO function
   enumeration with radio transmission disabled; compare STP framing to
   `btmtkuart.c`.
3. Identify whether `mt6631_fm_*` is physically populated and whether FM uses
   BTIF, I2S, or a separate path; keep FM disabled until then.
4. Add a disabled-only consys/BTIF DT schema/driver patch only after the above contracts
   are reviewable and firmware licensing is understood.
