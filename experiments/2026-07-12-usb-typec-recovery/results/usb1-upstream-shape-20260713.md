# Proposed MT6797 USB11 upstream shape

Status: disabled-only implementation shape. Patches 0069–0070 add USB11
glue/binding data and the recovered MUSB/T-PHY topology, but no USB1 DT node
is enabled and no register or VBUS write was performed.

## Evidence-backed reuse boundary

The vendor USB11 MAC is source-equivalent to Linux MUSB/Inventra at the core,
FIFO, DMA, and level-1 interrupt layers. The USB11 PHY is a close MediaTek
T-PHY V1 U2 match when its child resource is based at `0x11210800`, but the
generic V1 calibration bank and runtime power lifecycle are not equivalent.
See [`usb1-core-equivalence-20260713.txt`](usb1-core-equivalence-20260713.txt)
and [`usb1-phy-v1-comparison-20260713.txt`](usb1-phy-v1-comparison-20260713.txt).

This yields three small integration changes, rather than a new USB protocol.
The first is now compile-tested as patch 0069; the compatible and all board
nodes remain disabled:

1. Add MT6797 USB11 glue data to the existing MediaTek MUSB glue. Patch 0069
   does this without changing the MUSB core. Its clock IDs are `infra_icusb`
   and `sssub_ref_clk`, its MUSB config is
   `multipoint=false`, `num_eps=6`, `ram_bits=11`, and a single-buffer FIFO
   table for EP1–EP5 TX/RX at 512 bytes. Keep Inventra DMA optional and start
   with PIO.
2. Add an explicit USB11 variant to the existing MTK T-PHY V1 code. Map the
   SIF shared resource at `0x11210000`, the U2 child at `0x11210800`, reuse the
   common V1 U2 field helpers, and prevent the generic parent `+0x100`
   calibration access. The captured active path writes the USB11 `+0xf00`
   meter controls but deterministically falls back to slew value `4`; model
   that fixed value (or the meter location after a rationale) and keep
   alternate ICUSB bias plus save-current/recover lifecycle behind the
   explicit compatible.
3. Keep board role/VBUS/Type-C ownership separate. The live vendor image
   proves USB1 host operation and GPIO94 appears in FUSB301A board glue, but
   it does not prove which connector or polarity should be encoded in a
   mainline node.

## Disabled DT decomposition (not to be enabled yet)

The eventual DT should separate the vendor's two USB1 windows instead of
passing the SIF window as an opaque second MUSB resource:

```dts
usb11_tphy: t-phy@11210000 {
	compatible = "mediatek,mt6797-usb11-tphy";
	reg = <0 0x11210000 0 0x1000>;
	mediatek,eye-src = <4>;
	/* fixed vendor fallback suppresses generic FMREG calibration */
	#address-cells = <2>;
	#size-cells = <2>;
	ranges;

	usb11_u2: usb-phy@11210800 {
		reg = <0 0x11210800 0 0x100>;
		clocks = <&infrasys CLK_INFRA_SSUSB_REF>;
		clock-names = "ref";
		#phy-cells = <1>;
		status = "disabled";
	};
};

usb11: usb@11200000 {
	compatible = "mediatek,mt6797-usb11", "mediatek,mtk-musb";
	reg = <0 0x11200000 0 0x1000>;
	interrupts = <GIC_SPI 73 IRQ_TYPE_LEVEL_LOW>;
	clocks = <&infrasys CLK_INFRA_ICUSB>,
		 <&infrasys CLK_INFRA_SSUSB_REF>;
	clock-names = "infra_icusb", "sssub_ref_clk";
	phys = <&usb11_u2 PHY_TYPE_USB2>;
	dr_mode = "host"; /* board/role proof required before use */
	status = "disabled";
};
```

The names and exact parent/child placement are binding work, not a patch
proposal. In particular, a generic `mediatek,mtk-musb` node cannot consume
the two legacy clock names or the USB11 PHY lifecycle without the glue data
change. A `dr_mode = "host"` candidate also cannot be claimed usable until
the GPIO94 VBUS owner and FUSB301/connector mapping are proven.

## Implementation and validation order

1. Add the binding/schema shape, driver data, and fixed-slew DT topology with
   all nodes disabled (patches 0069–0070 are focused-validated).
2. Build MUSB, T-PHY, and the binding examples; confirm no generic calibration
   path addresses USB11 SIF `+0x100`.
3. Add a PIO-only, device-mode test path if a connector can be identified
   without VBUS; capture early logs and USB gadget enumeration.
4. Test one USB1 host transfer only after the board VBUS owner is explicit.
5. Enable DMA, runtime save-current, and suspend/resume only after repeated
   PIO transfers and bounded power-state transitions succeed.

No step above authorizes flashing or a hardware write. The current hashed UART
boot candidates are the prerequisite for a named, non-primary runtime test:
[`mainline-boot-current-validation-68.txt`](../../2026-07-12-boot-contract-recovery/results/mainline-boot-current-validation-68.txt).
