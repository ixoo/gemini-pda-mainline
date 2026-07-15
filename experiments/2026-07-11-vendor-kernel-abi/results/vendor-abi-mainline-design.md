# Vendor userspace ABI to Linux 7.1.3 boundary

## Result

The extracted Gemian/Android userspace is not a kernel-support specification;
it is a map of private compatibility surfaces that mainline must replace or
leave behind. The latest sanitized inventory contains 790 path strings, 384
Android properties, and 93 ioctl labels. Those counts prove compiled surface
area, not execution of every path.

The mainline target is a standard Linux userspace contract. Private framebuffer
session ioctls, ION handles, GED controls, vendor sensor misc devices, thermal
procfs policy, WMT character nodes, and `/dev/mali0` must not become permanent
new ABIs in the kernel tree.

## Reproducible evidence

- Vendor ABI scanner: [`scan-interfaces.py`](../scripts/scan-interfaces.py).
- Sanitized gap analyzer:
  [`analyze-mainline-abi.sh`](../scripts/analyze-mainline-abi.sh).
- Current inventory: private, Git-ignored guest file
  `~/reverse-engineering/work/vendor-kernel-abi/interfaces.tsv`.
- Latest inventory SHA-256: `d7292d9565364b3ebb77b30cd1edf4fedcfe3f3b5f312c50ab849f1a318485b1`.
- Vendor userspace extraction remains under the ignored `artifacts/` tree and
  is not redistributed here.

The analyzer only emits counts, boolean string-match results, and hashes of
standard Linux source files. A missing string match is not evidence that a
runtime feature is absent; it only means the scanner did not find that exact
literal in the selected ELF/configuration inventory.

## Replacement map

| Private surface | Mainline boundary | Do not carry forward |
| --- | --- | --- |
| `/dev/graphics/fb*`, `DISP_IOCTL_*`, `/dev/mtk_disp_mgr` | DRM/KMS, atomic modesetting, dma-buf, dma-fence/sync_file, MediaTek M4U | framebuffer session manager and private ioctl structures |
| `/dev/ion`, GED controls | dma-buf heaps, DRM render nodes, Panfrost/devfreq once calibrated | ION handles, GED policy ABI |
| `/dev/hwmsensor`, `m_*_misc`, batch device | physical IIO/input devices; userspace fusion for virtual sensors | one misc node per virtual sensor class |
| `/proc/mtktz/*`, vendor thermal policy | thermal zones, cooling devices, OPP/cpufreq throttling | procfs policy and unverified trips |
| `/dev/accdet`, vendor audio controls | ASoC/ALSA DAPM, standard jack/amp controls | vendor calibration and modem speech ABI |
| `/dev/stpwmt`, `/dev/wmtWifi`, WMT launcher | standard HCI and cfg80211 interfaces behind an MT6797 transport/firmware owner | permanent WMT character devices |
| `/dev/mali0` and GED | Panfrost, standard DRM render node, clocks/regulators/power/reset/OPP, independent GPU MMU | proprietary Mali/GED userspace ABI |
| vendor NVT/FUSB301/charger nodes | standard input, Type-C/role-switch, power-supply interfaces after chip identity is proven | legacy device names as hardware identity |

## High-impact details

### Display synchronization

The hardware composer uses a vendor framebuffer descriptor for overlay
sessions, fence preparation, VSync, and frame configuration. Its ioctl payload
sizes range from 4 to 88 bytes, so even matching request numbers would not
define a safe structure ABI. The standard replacement is the DRM atomic state
and dma-buf/fence graph already being built in the MT6797 component work. The
M4U port table and GCE event/subsystem contracts must be attached to each DMA
consumer; the GPU is intentionally separate because no GPU client appears in
the recovered M4U table.

### Sensors and thermal

The sensor HAL exposes many logical devices, but the live/source work proves
that most are fusion or gesture policy. Mainline should bind physical chips to
IIO/input, preserve the recovered BMI160 mount matrix and interrupt contract,
and implement virtual sensors in userspace. Likewise, vendor thermal procfs
names do not prove a safe MT6797 thermal driver: calibration, validity
sentinels, and trip behavior remain explicit bring-up gates.

### Audio and connectivity

The vendor audio stack is ALSA-based, so the MT6797 AFE/MT6351 code is a
legitimate starting point; board DAPM routes, analog supplies, jack detection,
and amplifier identity remain separate. Connectivity is different: WMT/STP,
BTIF/SDIO HIF, firmware ownership, and CONSYS power sequencing require a new
MT6797 transport/owner boundary before standard HCI/cfg80211 interfaces can be
exposed.

## Bring-up rules

1. Treat every ELF string as an observation of compiled code, not proof of live
   use; correlate it with the named device, driver, and source contract.
2. Prefer an existing Linux subsystem only when chip identity, register
   protocol, transport, and resource contract match.
3. If the chipset or transport differs, add a focused driver/data path rather
   than making a close driver emulate the vendor ABI.
4. Keep firmware, calibration, modem speech, secure display, and WMT ownership
   private until redistribution and sequencing are understood.
5. Validate each replacement with a bounded userspace test using standard
   interfaces, not compatibility shims that conceal missing hardware support.

