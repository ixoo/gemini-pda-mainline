# MT6797 integrated Wi-Fi contract

This record applies to the project Gemini running the observed Gemian image
(model MT6797X; image properties identify Gemini 4G UK 6M15BS/X600). Physical
SKU and RF silicon revision have not been independently inspected. Source
descriptions are evidence, not measured electrical behavior.

| Fact | Method / confidence | Contradictions and limits |
| --- | --- | --- |
| `wlan0` has platform parent `180f0000.wifi` and driver `mt-wifi` | Named-device sysfs capture; observed | Exact parent/subsystem/driver links observed in the bounded follow-up; OF metadata link unavailable |
| HIF resource is `0x180f0000+0x1100`, level-low SPI 283, `wifi-dma` / `INFRA_AP_DMA` | Live DT and matching Planet source; observed | Does not include every resource hard-coded by the vendor driver |
| MT6797 WLAN selector chooses gen3 AHB SDIO-like transport and a platform driver | Pinned top-level selector and gen3 Makefile/AHB implementation; source fact | Private SDIO-function shim explains SDIO-like names without standard SDIO registration; those names are not physical-bus evidence |
| Vendor PDMA init maps `0x11000080+0x80` independently of the Wi-Fi DT window | Pinned MT6797 source and CONFIG_OF register definitions; source-derived | A new mainline DMA node or access requires separate channel, clock, memory protection and shared-owner validation |
| CONSYS owns common power/firmware and routes several radio functions | Live WMT/BTIF/GPS bindings plus source callbacks; observed/source-supported | Separate function drivers must not independently reset or power the shared block |
| `CONSYS_MT6797` / `0x6797`, `MT279` ROM E1 and MT6631 FM names are distinct labels | Image properties, WMT status and firmware/configuration inventory; observed | They do not establish a Wi-Fi RF die named MT6625L, MT6630 or MT6631 |
| Audited gen2 comparator and selected gen3 host files carry GPLv2 notices | Exact public source headers; source-supported | A derivative still needs file-level provenance and review; host-source licensing does not license firmware |
| Retained WLAN image has a CRC-consistent MTKE section structure; runtime load attribution remains incomplete | Exact retained-file checksum, bounded RE-VM parser and vendor runtime evidence | Presence, a network interface and HIF log activity do not prove which image booted or permit redistribution |
| The selected gen3 host consumes a fixed-size filesystem calibration record, with incomplete read/error enforcement and no audited record checksum gate | Pinned layout, reader and startup control flow; source-supported | Record presence and compatible versions do not establish factory provenance, board applicability, firmware application or regulatory approval; see the [calibration contract](../../experiments/2026-09-05-mt6797-wifi-contract/CALIBRATION.md) |

The supporting [implementation experiment](../../experiments/2026-09-05-mt6797-wifi-contract/README.md)
owns source hashes, current upstream comparison, historical corrections and
the bounded ancestry probe. The [original connectivity record](../../experiments/2026-07-12-connectivity-wmt-recovery/README.md)
owns named-device captures. The [firmware boundary](firmware.md) owns private
retention policy; no raw image or calibration data belongs in this repository.

An upstream implementation needs an explicit CONSYS lifecycle owner, a matching
AHB/HIF and WLAN protocol, standard wireless interfaces, and verified
firmware/calibration applicability and loading contracts. Private retained-blob
use is owner-authorized; distribution requires separately established rights. Existing MediaTek names,
generic cfg80211 modules, successful compilation or a downstream driver port
do not establish runtime support. Current support claims remain in the
[support matrix](../HARDWARE_SUPPORT.md); ordered work remains in the
[roadmap](../ROADMAP.md).
