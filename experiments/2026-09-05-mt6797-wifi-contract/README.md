# Experiment: MT6797 Wi-Fi implementation contract

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-05-mt6797-wifi-contract` |
| Status | Bounded contract investigation completed; `inconclusive` for mainline operation |
| Subsystem | Integrated gen3 WLAN, CONSYS/WMT and AHB/AP-DMA |
| Device variant | Named project Gemini, Gemian model MT6797X; installed image identifies Gemini 4G UK 6M15BS/X600; physical SKU and RF die revision not independently inspected |
| Date | 2026-09-05 UTC |
| Investigator | Wi-Fi workstream, with Codex assistance |
| Tracking | [Wi-Fi issue 25](https://github.com/ixoo/gemini-pda-mainline/issues/25) |
| Frozen repository parent | `de48e24af88ef4647f8e94ec69975e5bd00d12ec` |
| Preparation / device | Metadata protocols completed and consumed; physical custody released; active radio candidate remains `planned` |

## Question and decision

Does Gemini expose an existing upstream-compatible Wi-Fi device, or does it
need a generation-specific WLAN core and integrated transport?

**Decision:** pursue the MT6797 integrated **gen3 AHB SDIO-like** WLAN path, with one shared
CONSYS lifecycle owner and standard Linux wireless interfaces. No audited
upstream driver is a demonstrated protocol match. Do not extend an `mt76` or
Bluetooth device-ID table on the basis of names. The initial usable target is
managed-station Wi-Fi; Bluetooth, GNSS, FM, AP/P2P, manufacturing commands and
power-save expansion need separate acceptance. Shared ownership must account
for those functions even when their function drivers are absent.

This is a feasible architecture, not a ready firmware loader. The implemented
bounded pieces are the **sysfs parent discriminator** and **MTKE metadata
validator**, each with refusal fixtures. The admitted follow-up confirms the
netdev platform ancestry; private file inspection validates the actual MTKE
structure. Neither performs a firmware or radio operation. A kernel that registers an empty wireless interface,
a vendor ABI wrapper, or a disabled speculative DT node would not remove the
missing protocol and ownership contracts.

## Provenance and observations

The [July connectivity experiment](../2026-07-12-connectivity-wmt-recovery/README.md)
and its [post-reboot capture](../2026-07-12-connectivity-wmt-recovery/results/live-connectivity-postreboot-20260714.txt)
are the named-device evidence, on vendor kernel `3.18.41+` build 7. Their
observations are not a new measurement or evidence of mainline association.

| Claim | Evidence and confidence | Limit |
| --- | --- | --- |
| Integrated MT6797 family | Android `CONSYS_MT6797` / `0x6797`; WMT status `MT279`, ROM E1, W1715MP, patch 20180307; observed software fields | Different naming layers; not a read of the WLAN RF silicon ID; do not rename it MT6625L or MT6631 |
| Platform Wi-Fi owner | `180f0000.wifi` bound to `mt-wifi`; live DT `mediatek,wifi`, `0x180f0000 + 0x1100`, SPI 283 level low, `wifi-dma` / `INFRA_AP_DMA` | New presence observation confirms exact WLAN platform ancestry; OF metadata link unavailable; first full classifier remains inconclusive |
| AHB host path | Top-level Planet WLAN Makefile selects gen3 for CONSYS_6797; gen3 selects `ahb_sdioLike`, including a private SDIO-function shim and AP-DMA; source-supported | A macro named `_HIF_SDIO`, SDIO comments and HIF-SDIO log initialization do not establish an active SDIO Wi-Fi bus |
| Shared owner | Live `mtk_wmt`, BTIF and GPS bindings; source function-power callbacks and WMT/STP routing | Successful BT/GNSS function operation is not a prerequisite, but their shared rails, memory and reset cannot have competing owners |
| Firmware files | WMT configuration, ROMv3 patches and WLAN image hashes retained privately/sanitized | File presence is not exact load attribution, legal redistribution permission or calibration applicability |

The [current primary-source audit](UPSTREAM.md) pins upstream, vendor and
related-work revisions. It corrects two overly broad historical statements:
the audited gen2 and selected gen3 host files carry GPLv2 terms, and the
BPI-R2 derivative cannot be dismissed as SDIO-only. Neither fact establishes
an upstream-ready implementation or licenses the installed firmware.

The first source comparison audited gen2. The exact retained firmware then
returned MTKE, not MTKW, and the top-level build selector established that
CONSYS_6797 selects **gen3**. The gen2 hashes below are comparator evidence,
not selected MT6797 inputs. The selected gen3 source, format, download/EMI
split and full hashes are documented in [FIRMWARE_FORMAT.md](FIRMWARE_FORMAT.md).
No gen2 loader or frame layout is promoted to a Gemini implementation.

Initial comparator source identities:

| Planet path below `drivers/misc/mediatek/connectivity/wlan/gen2/` | SHA-256 | Relevant fact |
| --- | --- | --- |
| `Makefile` | `4c374760e32142a31ea7e020ec2a251d04d18600f2e735f8ad4dc3de52a52807` | SDIO-named macro coexists with AHB object selection |
| `os/linux/hif/ahb/ahb.c` | `62fbadbbac5f3062a23435cf66f39b2286bc6d15807da8cf2a299914467a5e42` | Platform match/registration, Wi-Fi DMA clock and IRQ setup |
| `os/linux/hif/ahb/mt6797/ahb_pdma.c` | `b2db0e01ccae1ad21da8236adb49b7edfe82152df82e665eecf0f4cdd7273046` | DMA init maps a separate hard-coded window and programs DMA/MPU state |
| `os/linux/hif/ahb/include/hif_pdma.h` | `28424fd8e1bff338ed9297709f990fe067c6ecc81b155a0f0fd80519d23930a8` | CONFIG_OF selects AP-DMA `0x11000080 + 0x80` |
| `include/nic_init_cmd_event.h` | `97b46a8fc76065724552b904bee9c1dd4784a5fc1820cfede757de0a68d0afe6` | Separate download/start/register/query-pending-error command protocol |
| `include/nic_cmd_event.h` | `89a6c97e17a6fd3b78ffa14eb0a8c5dedcf442dd0c12ecbd6f457fb44a1de269` | WLAN command/event headers differ from STP/HCI |

All Planet paths above refer to commit
[`c5b0be85017ad0c599725e8273842efdbecdd88a`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/tree/c5b0be85017ad0c599725e8273842efdbecdd88a).
Sources were read selectively over HTTPS, not cloned or imported. No source
tree, blob, firmware, private capture or proprietary document was added.

## Actual missing dependencies

| Boundary | Established input | Missing implementation contract / discriminator |
| --- | --- | --- |
| Power, clocks and reset | CONSYS windows `0x18070000+0x200`, AP RGU `0x10007000+0x100`, TOPCKGEN `0x10000000+0x2000`, SPM `0x10006000+0x1000`; BGF/WDT SPIs 284/285; VCN18/28/33 BT/33 Wi-Fi supplies | Translate vendor `SCP_SYS_CONN`, reset/ack/protection and AFE/PMIC sequencing into exclusive standard providers with bounded timeout and rollback; DT clock naming alone is not that contract |
| HIF/DMA | Platform HIF window/IRQ; separate source-derived AP-DMA channel at `0x11000080` | Reconcile hard-coded DMA channel and MPU programming with live DT, I2C/AP-DMA preservation and generic DMA ownership; buffer addressing, coherency, ownership handoff and IRQ acknowledgement need exact semantics |
| Shared firmware | WMT loader and BTIF/STP owners, ROM patch sequence, 2 MiB no-map reservation | Exact memory subranges, firmware destination/length checks, boot/status handshake, crash containment, WMT function-on/off and reset arbitration; never generically map the whole reservation |
| WLAN commands/data | Selected gen3 MT6797 command/event and MTKE section structures | Verify endian/length/sequence/status handling, descriptor format, queues/credits, firmware-own handoff, event routing and firmware offloads. STP framing reuse for Bluetooth is not a WLAN protocol implementation |
| Regulatory/calibration | Vendor test library depends on NVRAM; protected calibration partitions intentionally uncollected | Identify mandatory per-device calibration/regulatory inputs and sanctioned read/validation path without exposing identifiers or inventing defaults; no RF admission before this technical contract is resolved |
| Firmware rights | Exact installed hashes below; GPLv2 notices in audited host files | Technical: exact version/hardware applicability and update provenance. Distribution-only: file-specific redistribution terms; kernel source license grants no blob rights |
| Observation/recovery | Authenticated USB design being prepared by A53 workstream | Frozen mainline baseline first-pass receipt and independent recovery before any mainline power/HIF test; all ten cold boots and A72 completion are not dependencies |

The selected vendor code mixes cfg80211 operations, host management state machines and
firmware offloads. Choose the exact cfg80211/mac80211 division only after that
offload audit; do not label this a proven full-MAC or `mt76` MAC implementation.
The eventual upstream scope is a generic MT6797 CONSYS provider plus a
generation-specific AHB WLAN driver in the wireless subsystem, with bindings
reviewed by MediaTek/DT maintainers. Topic certification, implementation,
kernel checks and a deletion condition after upstream acceptance remain
separate from this experiment's host tooling.

## Firmware boundary

The retained [firmware inventory](../../docs/hardware/firmware.md) records:

| File | Bytes | SHA-256 | Present versus loaded |
| --- | ---: | --- | --- |
| `WMT_SOC.cfg` | 80 | `f4a59b622a4e0c1470e475ce33f3edae43b27f1fbdeba54dc7cf07503d132880` | Vendor fallback load recorded |
| `ROMv3_patch_1_0_hdr.bin` | 210904 | `450c2b0949cf879217ac9aef81b18b860982f0e69340784b448b54365d8cf630` | Vendor fallback load recorded |
| `ROMv3_patch_1_1_hdr.bin` | 46472 | `5732c0730380e937b48ad169f2805b65e8d4a178265566c5083cb2cc2d249f1e` | Vendor fallback load recorded; GNSS-related strings do not prove exclusive GNSS ownership |
| `WIFI_RAM_CODE_6797` | 411632 | `a69383d74d829430487c39eef6b5e281b25f901595c903a632a10aa8631426dd` | Installed file; independent attribution of the successful WLAN load is missing |

The owner authorizes private reverse engineering and use of the retained
firmware as a blob. Firmware replacement is not a prerequisite. Abandonment
does not establish a redistribution grant; distribution rights remain
unresolved for all four exact assets. This does not block source development
or an otherwise technically admitted private test. The first probe needs
none of them and neither reads nor redistributes them. A future loader should
use `request_firmware()` with validated immutable inputs; Android ueventd
fallback and the WMT character ABI are not a permanent userspace dependency.
No firmware is selected for a new candidate by this decision.

## Associated code and first session

[`wifi_sysfs.py`](scripts/wifi_sysfs.py) implements a metadata-only collection
and classification path; [`test_wifi_sysfs.py`](scripts/test_wifi_sysfs.py)
uses synthetic filesystem fixtures. The CLI defaults to a plan without live
reads. It needs explicit collection, expected kernel and boot identity to
read a live system, and never runs a remote command itself.

The [session packet](SESSION.md) records the completed admitted Gemian recovery
session and its separately admitted presence follow-up. It does **not** construct, select or deploy a boot2 derivative.
Authenticated USB administration is preferred; an existing reviewed Gemian
SSH connection may itself use Wi-Fi without changing radio settings;
the first probe remains stock-Gemian-only because the minimal A53 initramfs
does not include Python. The existing OS may transmit autonomously: read-only
collection means no radio operation issued by this tool, not radio silence.

## Validation and conclusion

Run the synthetic protocol tests with:

```sh
python3 experiments/2026-09-05-mt6797-wifi-contract/scripts/test_wifi_sysfs.py
```

The corrected MTKE validator passed on the exact retained firmware; its
[receipt](results/firmware-mtke.json) identifies four sections: two HIF and two
shared-EMI sections under the selected source contract. The 24 unreferenced
bytes remain uninterpreted. The [format record](FIRMWARE_FORMAT.md) separates
source-defined checks from stricter inspection policy.

Exact completed checks and limitations are retained in
[`results/host-validation.txt`](results/host-validation.txt). Host tests cannot
prove real sysfs layout, driver behavior, radio silence or silicon identity.
No kernel/DT/config/manifest/patch-series change is made, so no kernel rebuild
is needed for this deliverable. No Buildbox or VM kernel build is required. The admitted recovery and first
metadata observation are recorded in [results/device-session.md](results/device-session.md).
The first observation was inconclusive, with its finite attempt consumed.
The initial MTKW firmware comparator likewise rejected the exact retained
MTKE file ([receipt](results/firmware-v1.json)), prompting the gen3 correction.

The drop-in-driver hypothesis is **rejected within the audited sources**.
Gen3 AHB SDIO-like is the supported source direction; the distinct
[presence result](results/parent-presence.json) observes exact platform
ancestry while OF metadata remains unavailable. Mainline Wi-Fi operation is **inconclusive**.
Source ownership facts are recorded separately in the
[durable hardware contract](../../docs/hardware/mt6797-wifi.md). Shared queue,
roadmap and existing hardware-map corrections are proposed in
[HANDOFF.md](HANDOFF.md); those files remain integrator-owned.
