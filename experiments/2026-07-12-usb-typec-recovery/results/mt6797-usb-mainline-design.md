# MT6797 USB controller mainline design

Status: `inconclusive` for runtime support; the controller register and
resource contracts are recovered from source and the idle device capture. No
USB, PHY, VBUS, role-switch, or Type-C register was written by this
investigation, and the local patch series leaves the USB nodes disabled.

## Reproducible evidence

The source comparison is emitted by the read-only analyzer:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-12-usb-typec-recovery/scripts/analyze-mt6797-usb-contract.sh
```

It reads vendor files from Git objects, which keeps the report reproducible
even though the VM's vendor checkout is sparse. It prints hashes, register
anchors, binding matches, and a decision summary; it never maps hardware or
writes a register.

The vendor evidence is Planet's MT6797 tree at commit
`c5b0be85017ad0c599725e8273842efdbecdd88a`. The Linux comparison is the
prepared Linux `7.1.3` source in the development VM.

| Source | SHA-256 |
| --- | --- |
| Vendor `drivers/misc/mediatek/mu3d/drv/musb_init.c` | `868289308c0f228a7594d2195647e63ffc1c2c615ab32ebc53d68141e978cb47` |
| Vendor `drivers/misc/mediatek/mu3d/hal/mu3d_hal_hw.h` | `515348e8ce4fdfb2ac0fe40ea890a1bbbcefb4a2e0cfd82241228aabc9895e71` |
| Vendor `drivers/misc/mediatek/mu3d/hal/ssusb_sifslv_ippc_c_header.h` | `8dab4a93eb3f416db78bc03ca4bc274e903e013252c29b015aeec72115290764` |
| Vendor `drivers/misc/mediatek/mu3d/hal/ssusb_dev_c_header.h` | `0fb8653c5b065a5b3ffb7e500d8ee0c95aa0cec165bb3971d25efe7ed8d86d1b` |
| Vendor `drivers/misc/mediatek/mu3d/hal/ssusb_epctl_csr_c_header.h` | `0bac7bc6f26dd049f99aa947fd98ef5a9c876f34b2fbf161e7ee0dfcea45ce19` |
| Vendor `drivers/misc/mediatek/mu3d/hal/ssusb_usb2_csr_c_header.h` | `f669084432308b1bed42a58054746475f1e1cec89441edfc7cf82ae7f1e7a4b9` |
| Vendor `drivers/misc/mediatek/mu3d/hal/ssusb_usb3_mac_csr_c_header.h` | `ae7dc88e8e45cee46d0f1c30af0f4571880c24b4cacd8f2c3aa988e72536c8d5` |
| Vendor `drivers/misc/mediatek/usb11/mt6797/musbfsh_core.c` | `4fd444c3cd7999a493c6aaf137bd191fa6558d9f338fdf8f31465776e672bde9` |
| Vendor `drivers/misc/mediatek/usb11/mt6797/musbfsh_mt65xx.c` | `2553a10ddb2a01b02ae08b9b614a808f2024aaea1bedc340c78ff7816c1e2f0f` |
| Vendor `drivers/misc/mediatek/usb11/mt6797/musbfsh_mt65xx.h` | `b577f4bd908d8732be8897b355f72ab711eedca940cac5eff3f1a1e2f5b15743` |
| Vendor `drivers/misc/mediatek/usb11/musbfsh_regs.h` | `63b24dc077bd12ca73ee88c75c3d989e2860e502a1d003a7c20be31b3d312c0f` |
| Linux `drivers/usb/mtu3/mtu3_hw_regs.h` | `79b54c78080ff1e1f9522a6143f7fd5d3363b90f73f95b4a0d12af67d2b5bb12` |
| Linux `drivers/usb/mtu3/mtu3_plat.c` | `905e47f5c64c8410e8b9f4142249857143c5b10f5f5cd99b483070446ea90482` |
| Linux `drivers/usb/mtu3/mtu3_core.c` | `2c9faf54a109e310a7eff319566124f1367d840e14030b43ffd2f464fc57c6f0` |
| Linux `drivers/usb/host/xhci-mtk.c` | `444ec257792f4998a7a2960877be044119b78127f4209ec0f731eb0f24d68a66` |
| Linux `drivers/usb/musb/mediatek.c` | `33502cc67a3853560a26439fb93a81e034fdd519cb89ffb2dd0e9c2d069137f2` |
| Linux `Documentation/devicetree/bindings/usb/mediatek,mtu3.yaml` | `48c96112e5b178af97f100e767bd303f68e32a2adaac4ae15fc8c3aeb93fd176` |
| Linux `Documentation/devicetree/bindings/usb/mediatek,mtk-xhci.yaml` | `a9983cabe4f93fde26851128532e5f47350328e27a2a5a2bf5c5af0033be0a15` |

The live idle capture reports USB1 at `0x11200000` with SIF
`0x11210000`, SPI 73 (Linux IRQ 105), and USB3 at `0x11270000`,
`0x11280000`, and `0x11290000`, with MUSB SPI 127 and xHCI SPI 126. The
vendor USB1 `musbfsh` driver owns the observed USB1 root hub. The USB3 MUSB
child is bound, but the `usb3_xhci` platform child has no driver link and no
xHCI interrupt line appears in the idle `/proc/interrupts` capture. This
does not prove the xHCI block is defective or absent; it is a useful vendor
runtime state to reproduce after a mainline boot. No accessory or cable
transition was part of this experiment.

## USB3: reuse the MTU3/xHCI controller code

The vendor USB3 HAL defines these offsets from its first window (`u3_base`):

| Function | Vendor offset | Physical address |
| --- | ---: | ---: |
| device/MUSB MAC | `+0x1000` | `0x11271000` |
| endpoint control | `+0x1800` | `0x11271800` |
| USB3 MAC/SYS | `+0x2400` | `0x11272400` |
| USB2 CSR | `+0x3400` | `0x11273400` |
| IPPC power/reset | `u3_sif_base + 0x700` | `0x11280700` |

Linux MTU3 uses the same register families at offsets `0x0000`, `0x0800`,
`0x1400`, and `0x2400` relative to its `mac` resource, and the same IPPC
register offsets relative to its `ippc` resource. This gives a source-level
resource split to validate:

| Linux view | Proposed physical resource | Why it is a candidate |
| --- | --- | --- |
| MTU3 parent `mac` | `0x11271000 + 0x3000` | Begins at the vendor device MAC and covers endpoint, USB3, and USB2 CSRs |
| MTU3 parent `ippc` | `0x11280700 + 0x0100` | Begins at the vendor IPPC power/reset block |
| xHCI child `mac` | `0x11270000 + 0x1000` | The vendor parent base is the host view; keep the child separate from the MTU3 device MAC |

This is a proposed DT decomposition, not a tested mapping. The old vendor
tree gives both MUSB and xHCI children all three 64-KiB windows, which hides
ownership and is not the Linux 7.1.x binding contract. Linux's MTU3 parent
owns IPPC and can instantiate an xHCI child with its own MAC resource; Linux
xHCI also accepts an optional IPPC resource for non-dual-role layouts.

The mainline consequence is therefore not a new USB3 MAC driver. The first
implementation should extend the MTU3 and xHCI compatible/binding data for
MT6797, describe the actual clocks, `vusb33`/VBUS supplies, PHY handles, and
role mode, and keep the vendor IDDIG and FUSB301 board glue out of the SoC
controller driver. The Linux MTU3 lifecycle and register helpers are the
reuse boundary. Any MT6797-specific reset, clock, or PHY quirk must be a
narrow data/operation selected by an explicit compatible.

## USB1: reuse the MUSB core, add a USB11 glue/PHY contract

The vendor USB1 node is `mediatek,mt6797-usb11` with MAC
`0x11200000 + 0x1000`, SIF/PHY `0x11210000 + 0x1000`, SPI 73, and clocks
`infra_icusb` and `sssub_ref_clk`. The driver maps both windows directly and
registers a vendor `musbfsh` child. Its recovered board configuration is
host mode (`mode = 1`) with six endpoints; the custom level-1 interrupt
registers are `0xa0`/`0xa4`/`0xa8`, and the USB11 PHY starts at
`USB_SIF_BASE + 0x800`.

The source comparison now establishes a narrower boundary. Vendor
`musbfsh_regs.h` and Linux `musb_regs.h` define the same core and endpoint
register offsets and bitfields. The vendor 8-KiB FIFO allocation (`EP0=64`,
`EP1..5 TX/RX=512`) maps to Linux `ram_bits = 11`, `num_eps = 6`, and a
custom FIFO table. The vendor HSDMA block at `0x200` uses the same channel
stride, control bits, and address/count registers as Linux Inventra DMA; the
Linux MediaTek glue already has a shared-IRQ `create_noirq` path. The vendor
level-1 mask/status bits also match Linux's `0xa0`/`0xa4` bits 0–3. These
facts argue against a new MUSB core or register fork.

The remaining mismatch is platform integration: Linux 7.1.3's
`drivers/usb/musb/mediatek.c` assumes three clocks (`main`/`mcu`/`univpll`),
a PHY phandle and generic USB-PHY lifecycle, and role-switch handling. USB11
has two legacy clocks, a second SIF/PHY resource, host-mode board policy, a
vendor polarity register, and hardcoded save-current/recover writes. The
upstream shape should therefore be a small MT6797 USB11 glue/data variant
plus explicit USB11 behavior/hooks in the existing MTK T-PHY V1 driver,
reusing Linux MUSB core and (after PIO proof) Inventra DMA. A separate PHY
driver is only warranted if those T-PHY hooks cannot represent the USB11
bank/calibration/power contract. The detailed equivalence result is
[`usb1-core-equivalence-20260713.txt`](usb1-core-equivalence-20260713.txt).

Patch 0069 now implements the first, narrow part of that boundary: it adds
match-data-driven USB11 clock names and MUSB FIFO/endpoint configuration to
the existing MediaTek glue and extends its binding. The USB11 compatible and
DT node remain disabled; the SIF/T-PHY variant, PIO-first runtime test, VBUS,
role, and Type-C ownership are still open gates. Compile and package
provenance is in
[`usb1-musb-mainline-validation-20260713.txt`](usb1-musb-mainline-validation-20260713.txt).

This is still not an enabled-node recommendation: no live USB11 register was
read and no mainline runtime probe has been attempted. The vendor PHY power
sequence must be translated into a reviewed Linux PHY contract, not copied
as opaque writes.

## Bring-up gates

Before enabling either controller in a Gemini DT:

- confirm the USB3 IPPC/MAC identity with bounded read-only capability reads;
- prove the MT6797 clock IDs and 3.3-V/1.0-V rail ownership in the mainline
  clock and regulator trees;
- model the two-SIF T-PHY resources from the companion
  [`MT6797 T-PHY design`](mt6797-tphy-mainline-design.md), without copying
  vendor PLL or eye-tuning tables;
- map each FUSB301 instance and IDDIG/switch GPIO to a physical connector;
- start with one USB3 device-only gadget-serial test and no VBUS drive;
- validate USB1 separately, then host VBUS and Type-C role transitions; and
- record every failed or inconclusive cable/role result in a new experiment.

No raw PHY write, VBUS transition, Type-C mode write, or vendor firmware
operation is justified by this source comparison.

## Decision

The USB3 controller is a strong reuse candidate: Linux MTU3/xHCI already
models the register protocol once the vendor's shared windows are split and
MT6797 clock/PHY/role data is supplied. The USB1 block is only a partial reuse
candidate because its MUSB-like core is surrounded by a distinct USB11 SIF,
PHY, interrupt, and host configuration. If that contract cannot be represented
without compatibility hacks, a new MT6797 USB11 driver is the correct result;
the closest existing driver must not be made to emulate the vendor ABI.
