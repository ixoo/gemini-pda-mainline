# MT6797 SuperSpeed PHY mainline design

Status: `inconclusive` for runtime support; source-level register and resource
contract recovered. No PHY registers were written by this experiment and no
USB/PHY DT node is enabled by the local patch series.

## Evidence

The comparison uses the pinned Planet MT6797 tree at commit
`c5b0be85017ad0c599725e8273842efdbecdd88a` and Linux `7.1.3` in the
development VM. The source analyzer is reproducible with:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-12-usb-typec-recovery/scripts/analyze-mt6797-tphy-contract.sh
```

The analyzer is intentionally a source-contract report: it prints hashes and
selected definitions, but never maps or writes a PHY register on hardware.

The relevant source hashes from that run are:

| Source | SHA-256 |
| --- | --- |
| Vendor `drivers/misc/mediatek/mu3phy/mtk-phy.h` | `c7c344787f441826db90b26810810befce5f699cc0dfca86e273f86ce3f31b44` |
| Vendor `drivers/misc/mediatek/mu3phy/mtk-phy-a60810.c` | `a4565236be822526f244269d1f4c775eab1021feb603ca0ef2e2e32428e977c8` |
| Vendor `drivers/misc/mediatek/mu3phy/mt6797/mtk-phy-asic.c` | `b383855ff3d5c73d744a048d7c47087aa6437a5a5431487118c952fe7748006e` |
| Vendor `drivers/misc/mediatek/mu3phy/mt6797/mtk-phy-asic.h` | `06d128e7229638d1b4b57fdafe156bdfa2fd25f281f6647b97e16b57091a2dcd` |
| Vendor `drivers/misc/mediatek/mu3d/hal/mu3d_hal_hw.h` | `515348e8ce4fdfb2ac0fe40ea890a1bbbcefb4a2e0cfd82241228aabc9895e71` |
| Linux `drivers/phy/mediatek/phy-mtk-tphy.c` | `f5b70dbbd62024552a96b3823c94e6e05974ef398be07fcb4126e97ce5b1db97` |
| Linux `mediatek,tphy.yaml` | `f84d39c93013a2229cbad55c27003eaf73917fa0ba01e02c88e43e736057feda` |

The vendor DT describes `mediatek,usb3_phy` with five clocks but no `reg`
resource. The USB3 controller separately exposes `ssusb_base` at `0x11270000`,
`ssusb_sif` at `0x11280000`, and `ssusb_sif2` at `0x11290000`. The vendor PHY
driver obtains and uses those globals rather than a normal PHY child-resource
topology.

## Bank layout

The vendor HAL maps the active project PHY as follows:

| Function | Vendor address | Relative bank |
| --- | --- | --- |
| SSUSB IPPC reset/power | `u3_sif_base + 0x700` (`0x11280700`) | separate SIF window |
| SPLLC | `u3_sif2_base + 0x000` (`0x11290000`) | shared clock/PLL bank |
| FM/frequency meter | `u3_sif2_base + 0x100` (`0x11290100`) | shared calibration bank |
| USB2 PHY common | `u3_sif2_base + 0x800` (`0x11290800`) | U2 register bank |
| USB3 PHYD | `u3_sif2_base + 0x900` (`0x11290900`) | U3 digital bank |
| USB3 PHYD bank 2 | `u3_sif2_base + 0xa00` (`0x11290a00`) | U3 digital bank 2 |
| USB3 PHYA | `u3_sif2_base + 0xb00` (`0x11290b00`) | U3 analog bank |
| USB3 PHYA-DA | `u3_sif2_base + 0xc00` (`0x11290c00`) | U3 analog data bank |

The U2 and U3 register fields and the per-port bank shape match the broad
MediaTek T-PHY V1 protocol. In particular, Linux’s V1 child-port mapping uses
U2 common at child offset `0x000`, U3 PHYD at `0x000`, and U3 PHYA/DA at
`0x200`/`0x300` (the latter two are folded into Linux’s `phya` pointer). The
vendor `u3_sif2 + 0x800` and `+0x900` bases can therefore be represented as
separate V1-style child resources.

This is not an exact generic-T-PHY V1 topology, however. Linux V1 expects one
shared `reg` resource containing SPLLC at `0x000`, FM at `0x100`, and CHIP at
`0x300`; MT6797 puts the PHY SPLLC/FM banks in SIF2 while IPPC reset/power is in
the other SIF window at `0x700`. Linux V2/V3 is also not a fit: it expects U2
MISC/FM/U2PHY_COM at `0x000`/`0x100`/`0x300`, whereas MT6797 places U2PHY_COM at
`0x800`.

## Initialization boundaries

The active vendor project path is `CONFIG_PROJECT_PHY` and calls
`phy_init_soc()`. It performs all of the following in one vendor-specific
sequence:

- turns on PMIC USB 3.3 V and 1.0 V rails and the SSUSB clocks;
- releases USB2 isolation, UART forcing, pull-downs, BC1.1, OTG VBUS
  comparator, and suspend controls;
- runs a 26 MHz frequency-meter slew calibration using SIF2 `0x100`/`0x110`;
- applies USB2 termination/squelch and USB3 impedance/equalization values,
  including eFuse-derived values;
- forces USB2 validity/session signals for vendor bring-up paths; and
- accesses IPPC reset/power registers in the separate SIF window.

The same tree also contains an optional `phy_init_a60810()` implementation with
PLL SSC, PLL divider, XTAL/bias, and PIPE phase/drive tuning. Its presence is
evidence of a silicon-family tuning path, not proof that the Gemini boot uses
that optional operator. Neither the optional table nor the active vendor
sequence should be copied into a mainline DT node without electrical evidence.

### USB11 is a closer V1 match than USB3's shared topology

The USB1 SIF is a separate window at `0x11210000`, and the vendor USB11 PHY
base is `USB_SIF_BASE + 0x800` (`0x11210800`). A generic T-PHY V1 USB2 child
uses `port_base + 0x000` for `U2PHY_COM`, so a child resource at `0x11210800`
maps the common USB2 fields exactly. The vendor power-on writes at offsets
`0x00`, `0x12`, `0x15`, `0x18/0x1a`, `0x20/0x21`, and `0x68`–`0x6e` line up
with Linux's `USBPHYACR*`, `U2PHYACR4/6`, and `U2PHYDTM0/1` fields for
interrupt enable, BC1.1, VBUS comparison, force/suspend, and IDDIG mode.
The source-only comparison is recorded in
[`usb1-phy-v1-comparison-20260713.txt`](usb1-phy-v1-comparison-20260713.txt);
the fixed-slew validation is in
[`usb1-fixed-slew-validation-20260713.txt`](usb1-fixed-slew-validation-20260713.txt).

The shared calibration bank is the exception. Generic V1 assumes FMREG at
the parent SIF `+0x100`; USB11's slew-meter helper addresses the USB11 PHY base
plus `0x700` (SIF `+0xf00`). The captured vendor config has
`CONFIG_MTK_ICUSB_SUPPORT` unset, so its active `poweron_volt_50` path uses
`icusb=0` and enters that helper. In the audited source the helper writes the
`+0xf00` meter controls but unconditionally sets its timeout flag, skips the
measurement, and programs the fallback slew value `4`; if
`MTK_DT_USB_SUPPORT` is enabled it returns before all of those writes. An
alternate ICUSB build skips calibration and selects voltage-dependent bias at
PHY offsets `0x12`/`0x15`. Enabling generic V1 unchanged would therefore risk
touching the wrong FMREG bank. The preferred mainline shape is an explicit
MT6797 USB11 variant in the existing T-PHY driver that reuses the common V1
fields, maps the child at `+0x800`, and uses the existing
`mediatek,eye-src = <4>` fixed-slew escape (which avoids the wrong FMREG bank)
unless a later runtime experiment justifies a USB11 meter hook, together with
bias and
runtime save-current/recover. A separate PHY register driver is not yet
justified.

Linux 7.1.3 already has the useful generic pieces: the PHY framework, safe
read/modify/write helpers, V1 U2 field operations, U2 mode/power handling, U3
common initialization, and optional eFuse support. It has no USB11-specific
calibration/bias/runtime-PM data record; its probe model accepts only one
shared V1 resource (or per-port V2/V3 resources), so the USB11 variant must
avoid the generic parent `+0x100` calibration assumption.

## Mainline boundary

The preferred implementation is an MT6797-specific extension of
`phy-mtk-tphy.c` (and its binding) that:

1. keeps the generic T-PHY field helpers and lifecycle;
2. maps SIF2 SPLLC/FM separately from the SIF IPPC resource;
3. exposes U2/U3 child resources at the recovered `0x800`/`0x900` banks;
4. makes IPPC reset/power ownership explicit rather than hiding it in a PHY
   probe; and
5. adds only narrowly justified MT6797 data for clocks, eFuse policy,
   USB11 bias, and calibration suppression; and
6. keeps vendor save-current/recover and clock/PLL handling behind explicit
   USB11 lifecycle hooks.

If Linux’s common driver cannot represent the two SIF windows without adding
compatibility hacks or silently addressing the wrong bank, a small
MT6797-specific PHY driver is justified. It should still reuse the Linux PHY
framework and common I/O helpers; it must not fork the entire vendor USB HAL.

The disabled implementation now takes the narrower configuration-first path:
patch 0070 describes a separate USB11 V1 parent at `0x11210000`, a child at
`0x11210800`, and `mediatek,eye-src = <4>`. This deliberately reuses the
existing MT6797/generic-V1 code because the child bank fields match and the
fixed-slew property bypasses the only unsafe generic access (parent FMREG
calibration). No USB11-specific PHY code is claimed until runtime evidence
shows that bias or save-current/recover cannot be represented by this
configuration and a small explicit hook.

This is a driver/resource distinction, not a request to preserve vendor
behavior by default. Existing Linux T-PHY behavior should remain the default
where the register protocol is proven identical; MT6797-specific behavior
belongs behind an explicit compatible and documented data table.

## Safety gates before enabling a node

- Confirm the silicon version and field generation from read-only evidence. A
  vendor version read at `U3_PHYD_B2_BASE + 0xe4` is not yet a live Gemini
  capture.
- Reconcile the five vendor clocks with mainline clock parents and PMIC
  regulator supplies. Do not make the PHY driver reach into PMIC registers.
- Model the two SIF resources and IPPC reset ownership in DT before any PHY
  write is attempted.
- Start with USB2 device-only mode and a bounded gadget-serial test. Keep
  SuperSpeed, host VBUS, Type-C role switching, and redriver GPIOs detached.
- Validate USB2 eye/slew and SuperSpeed link behavior with owner-authorized
  hardware tests. Record failures and negative results in a new experiment.
- Do not add the vendor PLL/eye/PIPE constants, force-valid/session writes, or
  SIB/debug controls to an enabled mainline path without a reviewable reason
  and a measured result.

## Conclusion

MT6797 is not a wholly unrelated PHY chipset: USB3 follows the MediaTek T-PHY
V1 bank protocol with a split SIF/IPPC topology, and USB11's U2 PHY fields are
an even closer V1 match at `SIF + 0x800`. Generic T-PHY remains unsafe to
enable unchanged because of the FMREG/calibration and runtime power
differences. Reuse is appropriate at the common-driver/helper layer; add
explicit USB11 variant data/hooks only if the disabled fixed-slew topology
fails a controlled runtime test. The current patch series therefore leaves
USB/PHY disabled.
