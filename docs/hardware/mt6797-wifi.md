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
| Selected built-in source conditionally reaches the gen3 WLAN initializer through connection and WLAN wrappers; wrapper results are arithmetically aggregated. Fresh original Kallsyms entries classify all four required wrapper/init/exit targets as ordinary global text (`T`) symbols | Pinned detector/lifecycle source plus one source-forced, no-database parse of the exact retained image; source/static fact | The externally supplied chip value and every gen3 exit invocation/order remain unresolved. The retained ELF still reports zero sizes. Next-distinct-symbol distances of 368, 280, 760 and 160 bytes are conservative inspection envelopes, not exact function ends, instruction evidence or teardown proof. See the [drv-init audit](../../experiments/2026-09-06-mt6797-wlan-drv-init-lifecycle-source-attribution/README.md), [retained-ELF boundary result](../../experiments/2026-09-06-mt6797-wlan-final-linkage-teardown-attribution/README.md) and [accepted Kallsyms provenance](../../experiments/2026-09-06-vmlinux-to-elf-symbol-provenance-v3/README.md) |
| The mainline passive CONSYS provider bound its opaque WLAN client at generation 1 without invoking power, reset, remap, protection, firmware, radio or DMA operations | Exact candidate/release, changed-boot identity, authenticated healthy logger and unique bounded kernel record on the named device; observed | This validates only the effect-free provider/binding and instrumentation slice. It does not establish shared-resource ownership, activation, firmware success, radio operation, standard wireless interfaces or usable Wi-Fi; see the [passive runtime record](../../experiments/2026-09-06-mt6797-consys-passive-boot/results/runtime-20260906.txt) |
| The detector's level-6 built-in initcall registers its character interface and SDIO detector, while a later `COMBO_IOCTL_DO_MODULE_INIT` request passes its scalar argument to `do_connectivity_driver_init` and returns the integer aggregate unchanged through the compat handler | Pinned selected detector/stub bodies and direct registration/header/cleanup edges; source fact | Registration does not initialize connectivity. Configuration alone does not force `0x6797`, and cleanup only establishes SDIO-detector unregister rather than a gen3 teardown join; see the [producer audit](../../experiments/2026-09-06-mt6797-connectivity-producer-source-attribution/README.md) |
| The exact retained `wmt_loader` statically opens `/dev/wmtdetect`, performs cleanup before module init, and passes a property/query-derived normalized scalar; `0x6797` is conditional, and init status is logged then discarded locally | Fresh single-batch bounded disassembly of the hash-pinned private binary, joined to pinned command definitions; static compatibility fact | Actual runtime branch/value/effects, libc/process conversion, resource lifetime and a standard mainline interface remain unresolved. The private vendor ABI is not a mainline design; see the [single-batch attribution](../../experiments/2026-09-06-mt6797-wmt-loader-ioctl-static-attribution-v3/README.md) |
| Vendor PDMA init maps `0x11000080+0x80` independently of the Wi-Fi DT window | Pinned MT6797 source and CONFIG_OF register definitions; source-derived | A new mainline DMA node or access requires separate channel, clock, memory protection and shared-owner validation |
| CONSYS owns common power/firmware and routes several radio functions | Live WMT/BTIF/GPS bindings plus source callbacks; observed/source-supported | Separate function drivers must not independently reset or power the shared block |
| `CONSYS_MT6797` / `0x6797`, `MT279` ROM E1 and MT6631 FM names are distinct labels | Image properties, WMT status and firmware/configuration inventory; observed | They do not establish a Wi-Fi RF die named MT6625L, MT6630 or MT6631 |
| Audited gen2 comparator and selected gen3 host files carry GPLv2 notices | Exact public source headers; source-supported | A derivative still needs file-level provenance and review; host-source licensing does not license firmware |
| Retained WLAN image has a CRC-consistent MTKE section structure; runtime load attribution remains incomplete | Exact retained-file checksum, bounded RE-VM parser and vendor runtime evidence | Presence, a network interface and HIF log activity do not prove which image booted or permit redistribution |
| Live `consys-reserve-memory` is a reg-less, no-map dynamic declaration with two-cell widths, 2 MiB size/alignment and allocation window `0x40000000..0xbfffffff` | Stable-identity read-only Gemian DT collection; observed | Sequential property reads establish declaration syntax only, not the initialized allocation, physical reservation, protection or ownership; see the [dynamic-declaration result](../../experiments/2026-09-06-mt6797-consys-dynamic-declaration/README.md) |
| The selected gen3 host consumes a fixed-size filesystem calibration record, with incomplete read/error enforcement and no audited record checksum gate | Pinned layout, reader and startup control flow; source-supported | Record presence and compatible versions do not establish factory provenance, board applicability, firmware application or regulatory approval; see the [calibration contract](../../experiments/2026-09-05-mt6797-wifi-contract/CALIBRATION.md) |


The shared SPM control register is `0x10006000 + 0`; CSPM
`0x11015000 + 0` is a different block despite using the same key value.
Pinned public sources and the retained-kernel static audit attribute keyed
SPM enabling writes to normal-world initialization and CONN transition paths.
This is high-confidence static attribution, not proof of current execution,
exclusive ownership, suspend lifetime or safe clearing/restoration. The
[source decision](../../experiments/2026-09-05-mt6797-wifi-contract/SPM_KEY_ORDER.md),
[retained attribution](../../experiments/2026-09-05-mt6797-wifi-contract/RETAINED_SPM_ATTRIBUTION.md)
and [independent scope review](../../experiments/2026-09-05-spm-attribution-review/README.md)
record the exact inputs, methods and remaining uncertainty.

For this variant, selected Planet/Gemian source and retained-kernel control
flow place CONN clock-disable before reset assertion during power-off. The
legacy upstream provider uses the opposite order. This supports a per-domain
ordering distinction; it does not establish electrical equivalence, successful
transitions or a reason to reorder unrelated domains.

The selected producer family adds a two-byte storage envelope around the WIFI
record; the kernel consumer reads the logical payload. Retained-file presence,
static producer analysis and public configuration mapping are separately
attributed in the [storage contract](../../experiments/2026-09-05-mt6797-wifi-contract/PROVENANCE.md).
A matching envelope does not authenticate calibration or prove its restoration
history or applicability to this RF board and firmware.

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
