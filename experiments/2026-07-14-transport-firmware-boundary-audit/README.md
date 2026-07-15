# Experiment: current transport and firmware ownership boundary

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-14-transport-firmware-boundary-audit` |
| Status | `completed` for static package/DT/firmware ownership reconciliation; runtime transport bring-up remains untested |
| Subsystem | MT6797 CONSYS/WMT, BTIF/GNSS, CCCI/CLDMA modem, camera/SCP, and firmware |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant is not independently established |
| Date | 2026-07-14 |

## Question

Which parts of the vendor-only connectivity, modem, camera, and SCP stack can
reuse Linux 7.1.x subsystem interfaces, and which parts require a new transport,
platform backend, or firmware-ownership contract?

## Method and safety

This is a read-only reconciliation of the exact authoritative current 77-patch package,
generated Gemini DTB, pinned vendor source audits, sanitized userspace/firmware
inventory, and the existing subsystem package audits. It does not load firmware,
bind or unbind a driver, scan a bus, open a CCCI/WMT/camera device, transmit
radio data, stream a camera, or write hardware.

The proprietary firmware and userspace payload remain private under the
Git-ignored `artifacts/` tree. Only hashes and sanitized interpretation are
recorded here; no firmware, calibration, modem image, or vendor binary is
copied into the repository.

The Linux firmware-loader/source comparison is reproducible with
[`scripts/audit-firmware-loader-boundary.sh`](scripts/audit-firmware-loader-boundary.sh).
Its current 7.1.3 result is
[`results/firmware-loader-boundary-current-77-20260714.txt`](results/firmware-loader-boundary-current-77-20260714.txt);
two runs were byte-identical. The audit inspects source hashes, loader
call-sites, packaged configuration/modules, the sanitized 28-file manifest,
and the packaged DTB without opening or requesting any blob.

The focused connectivity, CCCI, and camera package-boundary audits were rerun
against the current 77-patch Image/DTB-only artifact. They independently confirm that
the SPI additions leave the five no-map firmware reservations intact and add
no active CONSYS/WMT/BTIF/GNSS or CCCI/CLDMA/CCIF transport nodes; see the
[connectivity result](../2026-07-12-connectivity-wmt-recovery/results/mainline-connectivity-current-77-package-20260714.txt),
[CCCI result](../2026-07-13-modem-ccci-recovery/results/mainline-ccci-current-77-package-20260714.txt),
and [camera result](../2026-07-13-camera-recovery/results/mainline-camera-current-77-package-20260714.txt).

## Current package boundary

The authoritative package is `linux-7.1.3-gemini-b7721ab55e41`, with Image
SHA-256 `9975b0faf659ddd91e33607de47a4814b9ad4c72292f4c8f7af39582f1a49362`,
config SHA-256 `c46e0d135ed290420362638ca36448055e19bb7029deaa7aad897d885275f7db`,
and Gemini DTB SHA-256
`7a95f79eb39e25d56c1f8407ecee3d606cf9397f8522c3ca1d17e01d3865672b`.

The DTB preserves five no-map firmware/carve-out regions relevant to these
subsystems: MD1 CCCI (`0xa100000`), CCCI shared memory (`0x600000`), CONSYS
(`0x200000`), SPM (`0x16000`), and SCP shared memory (`0x1000000`). It has no
active CONSYS/WMT/BTIF/GNSS, CCCI/CLDMA/CCIF, or camera/SENINF capture node.

The package's Image/config contain generic framework code and options for
unrelated family modules, but the Image/DTB-only package has no module tree and
no vendor transport:

| Boundary | Packaged evidence | Reuse decision | Missing contract |
| --- | --- | --- | --- |
| CONSYS/WMT/Wi-Fi | `cfg80211`, `mac80211`, GNSS, and unrelated `mt76` modules; no `MTK_WMT`, `MTK_BTIF`, or MT6797 CONSYS symbol | Reuse cfg80211/mac80211/HCI/GNSS above a new backend | CONSYS power/clock/reset, firmware load, legacy SDIO/HIF framing, BTIF DMA, BGF/WDT ownership |
| Bluetooth | Generic `btmtk`/HCI layers; no `btmtkuart`/`btmtksdio` transport | Reuse standard HCI/STP/H:4 interfaces only | Old-combo IDs `0x6628/0x6630/0x6632`, four-byte header, 512-byte blocks, 2080-byte FIFO, WMT firmware owner |
| GNSS | Generic GNSS serial/MTK-serial modules; no active GNSS DT node | Reuse GNSS core/serial-facing interface only if transport is separated | Combo-firmware message routing, `/dev/stpgps` replacement, GPS-LNA GPIO/power owner |
| Cellular modem | `wwan.ko` and MHI WWAN helpers; no `t7xx`, CCCI, CLDMA, or CCIF transport | Reuse WWAN port/TTY/netdev APIs above a new transport | 16-byte CCCI header, CLDMA/CCIF rings, descriptors, firmware handshake/reset, EMI-MPU/remap |
| Camera | Generic media, JPEG/MDP3/Vcodec modules; no SP5509, OV5675, SENINF, or active capture graph | Reuse V4L2/media-controller and generic codec APIs | SP5509 sub-device, MT6797 SENINF/CSI/CAM pipeline, sensor power/reset/endpoint, DMA/IOMMU |
| SCP/codec firmware | `mtk_scp.ko`, `mtk_scp_ipi.ko`, and `mtk_rpmsg.ko` are packaged; VCODEC SCP support is selected, but no active SCP consumer is in the Gemini DTB | Treat SCP as a firmware-owned optional boundary, not proof of camera or codec support | Firmware image applicability/load address, reserved-memory ownership, IPI/RPMSG ABI, reset and recovery |

## Firmware correlation

The private Gemian firmware inventory contains 28 files and the sanitized
manifest is hashed as
`2d545b6c4f61173479b00bf0fd8fe4657c6a41571e31926579349a7203792e8c`.
Observed or strongly correlated groups are:

- nine SPM PCM programs, loaded/reported by the vendor power path;
- `WMT_SOC.cfg` and two `ROMv3_patch_*.bin` connectivity patches, correlated
  with WMT MT279/ROM E1 status;
- `WIFI_RAM_CODE_6797`, present while vendor Wi-Fi/HIF-SDIO is active but not
  independently attributed to a load event;
- `novatek_ts_fw.bin`, requested by the vendor touchscreen path;
- `modem_3_3g_n.img`, present alongside the active CCCI/CLDMA baseband path;
- FM configuration/coefficients/patch and diagnostic catcher/filter files.

These correlations establish firmware ownership boundaries, not permission to
load a blob from mainline. Applicability, redistribution rights, load address,
and security/update behavior remain unresolved for every proprietary group.

## Conclusions

1. Generic Linux interfaces are reusable above the boundary: cfg80211,
   mac80211, HCI, GNSS, WWAN, V4L2/media-controller, RPMSG, and standard
   firmware-loader APIs.
2. The lower layers are not name-compatible substitutions: `mt76`,
   `btmtksdio`, `gnss-mtk`, MHI/t7xx, and OV5675 must not be enabled by family
   name alone.
3. The no-map reservations are evidence of firmware ownership and must stay
   intact until bootloader placement, firmware handshake, and DMA/EMI-MPU
   ownership are independently recovered.
4. Camera and modem support are new backend projects; SCP/RPMSG support is an
   optional firmware contract and must not be inferred from packaged modules.

## Evidence

- [Connectivity package audit](../2026-07-12-connectivity-wmt-recovery/results/mainline-connectivity-current-77-package-20260714.txt)
- [Connectivity/WMT recovery](../2026-07-12-connectivity-wmt-recovery/README.md)
- [Modem CCCI package audit](../2026-07-13-modem-ccci-recovery/results/mainline-ccci-current-77-package-20260714.txt)
- [Modem CCCI recovery](../2026-07-13-modem-ccci-recovery/README.md)
- [Camera package audit](../2026-07-13-camera-recovery/results/mainline-camera-current-77-package-20260714.txt)
- [Camera recovery](../2026-07-13-camera-recovery/README.md)
- [Firmware inventory](../2026-07-11-gemian-firmware-inventory/README.md)
- [Firmware boundary](../../docs/hardware/firmware.md)
- [Current driver coverage](../2026-07-13-driver-coverage-audit/README.md)

The current 77-patch reconciliation is recorded in
[`results/firmware-loader-boundary-current-77-20260714.txt`](results/firmware-loader-boundary-current-77-20260714.txt).
The original result remains historical provenance for the same static
transport/firmware conclusions.

No runtime transport, firmware load, camera stream, modem handshake, or
hardware write was attempted.
