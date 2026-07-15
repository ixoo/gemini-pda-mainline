# Experiment: Gemini USB and Type-C recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-usb-typec-recovery` |
| Status | `inconclusive` for mainline runtime support; live vendor topology captured |
| Subsystem | USB1/MUSB, USB3/MUSB+xHCI, SuperSpeed PHY, FUSB301 Type-C ports |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant not independently established |
| Date(s) | 2026-07-12 — 2026-07-14 |
| Investigator(s) | Repository maintainer with Codex assistance |
| Tracking issue | None |

## Question or hypothesis

Can the live Gemini USB and Type-C wiring be represented by the Linux 7.1.x
MediaTek MUSB/MTU3/T-PHY and Type-C frameworks, or does MT6797 require new
SoC/board drivers and data?

The hypothesis is intentionally split: the USB controller register windows may
be reusable with existing generic blocks, but the vendor SuperSpeed PHY and
Type-C switch/role logic may require new data or drivers because the vendor
tree uses MT6797-specific compatibles and hardcoded PHY banks.

## Provenance and environment

- Live kernel: Linux `3.18.41+`, AArch64, Gemian Debian 9 userspace.
- Live device: `gemini@192.168.1.50` over the owner's private LAN.
- Vendor source: Planet MT6797 tree commit
  `c5b0be85017ad0c599725e8273842efdbecdd88a`.
- Mainline comparison: Linux `7.1.3` in the development VM.
- Public silicon references: [onsemi FUSB301 datasheet](https://www.onsemi.com/download/data-sheet/pdf/fusb301-d.pdf) and [FUSB301A datasheet](https://www.onsemi.com/download/data-sheet/pdf/fusb301a-d.pdf).
- Sanitized summary: [`results/runtime-summary.txt`](results/runtime-summary.txt).
- Fresh sanitized runtime capture: [`results/runtime-usb-typec-20260714.txt`](results/runtime-usb-typec-20260714.txt).
- Battery-recovery identity/topology capture: [`results/runtime-usb-typec-battery-recovery-20260714.txt`](results/runtime-usb-typec-battery-recovery-20260714.txt).
- Private raw capture, if regenerated, belongs only under the Git-ignored
  `artifacts/device-inventory/20260714-live/` directory.

## Safety assessment

The collector is read-only. It reads platform/I2C/USB sysfs, the live flattened
device tree, `/proc/interrupts`, and filtered kernel messages. It does not
write GPIO, I2C, USB, PHY, Type-C, role-switch, VBUS, or extcon controls; it
does not scan unbound I2C addresses; and it does not probe PHY registers.

The vendor Type-C identification sequence is not a safe collector operation:
the vendor driver writes the FUSB301 mode register during probe. It must not be
replayed through an ad-hoc I2C tool. The vendor PHY tuning tables also contain
write-only electrical tuning and must not be copied into an enabled DT node
without a register-generation and hardware validation plan.

The source-level FUSB301 comparison runs in the development VM and emits only
hashes, symbols, constants, and framework anchors:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-12-usb-typec-recovery/scripts/analyze-fusb301-contract.sh
```

Its design record is
[`fusb301-mainline-design.md`](results/fusb301-mainline-design.md).

The bounded live identity attempt and the Linux 7.1.3 candidate validation
are recorded in [`fusb301-live-identity-attempt.txt`](results/fusb301-live-identity-attempt.txt)
and [`fusb301-mainline-validation.txt`](results/fusb301-mainline-validation.txt).
The refreshed 2026-07-13 register/API audit is recorded in
[`fusb301-register-contract-20260713.txt`](results/fusb301-register-contract-20260713.txt).
The earlier 65-patch FUSB301 rebuild, module object, and focused schema check are in
[`fusb301-current-validation-20260713.txt`](results/fusb301-current-validation-20260713.txt).

The source-level MT6797 T-PHY comparison is read-only and emits source hashes,
bank offsets, initialization anchors, and Linux T-PHY matches:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-12-usb-typec-recovery/scripts/analyze-mt6797-tphy-contract.sh
```

Its design record is
[`mt6797-tphy-mainline-design.md`](results/mt6797-tphy-mainline-design.md).
The USB11-specific V1 field/resource comparison is recorded in
[`usb1-phy-v1-comparison-20260713.txt`](results/usb1-phy-v1-comparison-20260713.txt);
it narrows the USB11 PHY work to an explicit T-PHY variant rather than a new
register model, while retaining the no-enable gate for calibration and power
sequencing.

The source-level MT6797 controller comparison is also read-only. It reads the
vendor USB3/MUSB and USB11 sources from Git objects, then compares register
offsets, DT resources, clocks, and Linux MTU3/xHCI/MUSB bindings:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-12-usb-typec-recovery/scripts/analyze-mt6797-usb-contract.sh
```

Its design record is
[`mt6797-usb-mainline-design.md`](results/mt6797-usb-mainline-design.md).
The concrete, disabled-only driver/DT decomposition is recorded in
[`usb1-upstream-shape-20260713.md`](results/usb1-upstream-shape-20260713.md).
The earlier 56-patch source/object recheck is recorded in
[`mainline-usb-current-validation.txt`](results/mainline-usb-current-validation.txt).
The refreshed 68-patch MT6797 T-PHY/MTU3/xHCI compatibility and disabled-DT
validation is recorded in
[`mt6797-usb3-topology-validation-20260713.txt`](results/mt6797-usb3-topology-validation-20260713.txt).
The first compile-tested MT6797 USB11 MUSB glue/binding patch, the disabled
USB11 DT topology, and their historical package validation are recorded in
[`usb1-musb-mainline-validation-20260713.txt`](results/usb1-musb-mainline-validation-20260713.txt)
and [`mainline-72-patch-build-current-20260713.txt`](../2026-07-13-kernel-integration/results/mainline-72-patch-build-current-20260713.txt).
The authoritative current package provenance is
[`mainline-72-patch-current-20260714.txt`](../2026-07-13-kernel-integration/results/mainline-72-patch-current-20260714.txt).
The current package USB/Type-C boundary audit is
[`mainline-usb-current-72-package-20260714.txt`](results/mainline-usb-current-72-package-20260714.txt);
it is reproducible with:

```sh
./scripts/dev-vm run bash -lc \
   'CURRENT_PACKAGE=/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-c2d9eea95daa \
   experiments/2026-07-12-usb-typec-recovery/scripts/audit-current-package-usb.sh'
```

The package has built-in USB1 MUSB, MTU3/xHCI, and MT6797 T-PHY code plus a
loadable FUSB301 module. The Gemini DTB contains the source-derived USB11,
MTU3/xHCI, and two-SIF T-PHY consumers, but all are disabled; it contains no
FUSB301 client, role-switch owner, or VBUS supply. This is a package boundary,
not a runtime-support claim.
The exact current 74-patch package was rerun separately; its byte-identical
audit and current hashes are in
[`mainline-usb-current-74-package-20260714.txt`](results/mainline-usb-current-74-package-20260714.txt).
The earlier authorized runtime-access retry returned `No route to host`; the
negative result is recorded in
[`usb1-runtime-access-attempt-20260713.txt`](results/usb1-runtime-access-attempt-20260713.txt).
A fresh reachable, read-only capture on 2026-07-14 is summarized in
[`runtime-usb-typec-20260714.txt`](results/runtime-usb-typec-20260714.txt) and
stored privately at `artifacts/device-inventory/20260714-live/usb-typec.txt`.
After the later battery-recovery reboot, a second capture is indexed in
[`runtime-usb-typec-battery-recovery-20260714.txt`](results/runtime-usb-typec-battery-recovery-20260714.txt)
and stored privately under `artifacts/device-inventory/20260714T163000Z-battery-recovery-usb/`.
It reproduces the vendor USB1 root hub and FUSB301 bindings, leaves USB3 xHCI
unbound, and exposes no Type-C/USB-role/PHY class devices. Vendor probe logs
now show both FUSB301 clients returning device ID `0x12`: the I2C0 FUSB301A
path has a valid GPIO64/EINT IRQ, while the I2C1 FUSB301 path attempts GPIO/IRQ
zero and fails `request_irq` with `-EINVAL`. The same boot logs report USB1
slew-rate calibration timeout and missing USB3 `iddig_init` pinctrl; these are
vendor runtime observations, not mainline failures.

### Probe-safety boundary

The Linux 7.1.3 source audit shows that the existing MediaTek MUSB glue is not
a passive description of USB11. `mtk_musb_probe()` enables the parent clocks,
turns on runtime PM, and registers a child MUSB device. The child initialization
then calls `phy_init()` and `phy_power_on()`, writes controller interrupt and
power registers, requests the IRQ, and creates the host HCD. The generic T-PHY
probe mostly maps resources and creates PHY instances, but its later
`phy_init()`/`phy_power_on()` callbacks enable clocks and perform calibration,
power, and tuning writes. These are activation side effects even when no cable
is attached.

The current MT6797 USB11 candidate has `dr_mode = "host"`, but no VBUS supply,
role switch, or MTK glue VBUS callback. Linux's MUSB host path can therefore
register an HCD without a proven board owner for accessory VBUS. `host` is not
itself a safe runtime-enable contract. Keep the USB11 MUSB, T-PHY, Type-C, and
VBUS nodes disabled until VBUS ownership, role policy, and the USB11 PHY
power/calibration sequence are established. The first runtime candidate should
be a device-only gadget-serial test, or a host test with an explicitly identified
and independently verified VBUS owner. No runtime mainline probe or hardware
write was attempted for this audit. The exact source hashes and line anchors
are in [`mainline-usb11-probe-safety-audit-20260713.txt`](results/mainline-usb11-probe-safety-audit-20260713.txt),
generated by [`audit-mainline-usb11-probe-safety.sh`](scripts/audit-mainline-usb11-probe-safety.sh).

## Associated code

Run from the repository root:

```sh
mkdir -p artifacts/device-inventory/20260712-live
ssh -i artifacts/credentials/gemini_ed25519 \
  -o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes \
  gemini@192.168.1.50 'bash -s' \
  < experiments/2026-07-12-usb-typec-recovery/scripts/collect-live-usb-typec.sh \
  > artifacts/device-inventory/20260712-live/usb-typec.txt
chmod 700 artifacts/device-inventory/20260712-live
```

The output must remain below the ignored `artifacts/` tree. Review it before
sharing: USB descriptors can disclose attached-device identity. The committed
result below contains only the idle device's controller topology and no
attached USB device serial.

## Procedure

1. Confirm the key-only, noninteractive SSH path with `BatchMode=yes`.
2. Run the collector once while the device is idle and no USB accessory is
   attached.
3. Repeat after an owner-authorized accessory insertion only if the physical
   port mapping is needed; do not automate VBUS, role, or cable transitions.
4. Compare the capture with the pinned vendor DTS and USB/PHY/Type-C source,
   then compare each contract with Linux 7.1.3 bindings and drivers.

## Observations

### USB controller topology

- USB1 is a vendor `mediatek,mt6797-usb11` controller at
  `0x11200000 + 0x1000`, with a second SIF window at
  `0x11210000 + 0x1000`, SPI 73 level-low, and clocks `infra_icusb` and
  `sssub_ref_clk`. It binds to vendor `musb11_dts`/`musbfsh`; the live
  Linux IRQ is global 105 after GIC mapping.
- USB3 is a vendor `mediatek,usb3` block at three windows:
  `0x11270000`, `0x11280000`, and `0x11290000`, each `0x10000` bytes. Its
  MUSB dual-role IRQ is SPI 127 level-low and its xHCI IRQ is SPI 126
  level-low. The live platform devices expose separate `musb-mtu3d` and
  vendor xHCI children over the shared windows.
- The USB3 ID-detection child uses GPIO181/EINT186, level-low, with the vendor
  debounce tuple `GPIO181, 0`. The live interrupt table also shows an
  `iddig_eint` consumer on EINT186.
- The idle USB bus contains only the root-hub entry; no accessory was attached
  during this capture.
- The USB3 MUSB child is bound to `musb-mtu3d` and consumes the live IRQ
  corresponding to SPI 127, but the `usb3_xhci` platform child has no driver
  symlink and no xHCI interrupt line appears in `/proc/interrupts`. The only
  observed USB root hub is USB1. This is a runtime observation of the vendor
  image, not evidence that the xHCI hardware is absent; the idle capture did
  not exercise a cable or host transition. The sanitized state record is
  [`usb1-live-driver-state-20260713.txt`](results/usb1-live-driver-state-20260713.txt).

### SuperSpeed PHY

- The PHY node is `mediatek,usb3_phy` and binds to the vendor `mt_dts_mu3phy`
  driver. It names five clocks:
  `ssusb_bus_clk`, `ssusb_sys_clk`, `ssusb_ref_clk`,
  `ssusb_top_sys_sel_clk`, and `ssusb_univpll3_d2_clk`.
- Vendor `mtk-phy-asic.c` prepares the first four clocks and stores global PHY
  state. Its active MT6797 project path uses hardcoded bank offsets and a
  vendor initialization/tuning sequence rather than a normal DT `reg`
  resource; the same tree also contains an optional A60810 operator.
- The vendor bank names include SIF2 SPLLC `0x0000`, FM/F-EG `0x0100`, U2 PHY
  `0x0800`, U3 PHYD `0x0900`, U3 PHYD bank 2 `0x0a00`, U3 PHYA `0x0b00`, and
  U3 PHYA-DA `0x0c00`; IPPC reset/power control is at `ssusb_sif + 0x700` in
  the separate SIF window. These are source-derived offsets, not proof that
  Linux's generic T-PHY v1/v2 resource topology applies unchanged.
- The vendor A60810 code writes U2 termination/receiver/slew settings and
  SuperSpeed PLL/PIPE tuning. Those writes are electrical tuning, not yet a
  safe mainline initialization sequence.

### Type-C ports and board switching

- Two FUSB301-compatible I2C devices are present at address `0x25`, on I2C0
  (`fusb301a`) and I2C1 (`fusb301`). Both are bound by vendor drivers.
- The vendor DT has separate pseudo-platform nodes for `fusb301a-pin` and
  `fusb301-eint`. The FUSB301A path uses a GPIO64/EINT-style attach input and
  drives board switch signals; the FUSB301 path has a separate EINT handler.
  The captured interrupt names include `fusb300-eint` and `iddig_eint`, so the
  exact pseudo-node-to-physical-port mapping remains unresolved.
- Source-derived board switch GPIOs are `fusb301a_sw_en = GPIO70`,
  `fusb301a_sw_sel = GPIO71`, `sw7226_en = GPIO72`, and
  `usb1_drvvbus = GPIO94`. Vendor pinctrl states cover redriver/switch
  initialization, low, high, and high-impedance modes.
- FUSB301 register definitions are: device-ID register address `0x01`, mode `0x02`, control
  `0x03`, manual `0x04`, reset `0x05`, mask `0x10`, status `0x11`, type
  `0x12`, and interrupt `0x13`. Status bit 0 is attach, bits 1–2 are BC
  level, bit 3 is VBUSOK, and bits 4–5 encode orientation/CC state.
- Both vendor I2C drivers initialize mode register `0x02` to `0x01` and read
  the device-ID register. The public datasheet identifies the reset signature
  as `0x12` (version 1, revision 2); the post-recovery vendor probe logs show
  both clients returning `0x12`. The FUSB301A path requests GPIO64/EINT and
  receives vendor IRQ `0x183` (global GIC line 387), while the FUSB301 path
  reports GPIO/IRQ zero and fails `request_irq` with `-EINVAL`. The running
  kernel still has no `/dev/i2c-*` character device (`CONFIG_I2C_CHARDEV` is
  unset), no FUSB301 register sysfs/debugfs export, and no safe direct-read
  path. The FUSB301 interrupt work is otherwise an empty stub;
  FUSB301A contains board-specific CC/orientation handling but does not expose
  a Linux Type-C class state machine.
- The datasheet also documents autonomous `SS_SW` orientation output and an
  open-drain `ID` output for sink detection. These signals may explain the
  vendor GPIO64/USB1 and redriver glue, but they do not identify the physical
  connector mapping by themselves.
- In the FUSB301A source, active-low ID state is treated as attached. CC1 or
  CC2 status drives VBUS through GPIO94 and selects the redriver/switch using
  GPIO70/71/72; unplug or invalid CC returns all four outputs to their safe
  low/high-impedance state. This is vendor behavior evidence, not a proposed
  default for mainline.

## Analysis

Linux 7.1.3 has generic MUSB and MTU3 infrastructure, but its MTU3 binding
does not list MT6797 and expects a modern two-resource `mac`/`ippc` topology,
PHY handles, clocks, and role-switch integration. The vendor USB3 source
offsets match that model if its three shared windows are split into an MTU3
device MAC resource at `0x11271000 + 0x3000`, an IPPC resource at
`0x11280700 + 0x100`, and a separate xHCI host MAC resource at
`0x11270000 + 0x1000`. This is a source-derived candidate mapping, not a
runtime-tested DT.

The USB3 conclusion is therefore reuse of Linux MTU3/xHCI controller code,
with MT6797-specific compatible and explicit source-derived resource data.
The historical 72-patch candidate added MT6797 USB11 MUSB match data and a disabled
USB11 MUSB/T-PHY topology, while retaining the
disabled DT topology for
the generic V1 T-PHY, MTU3 device MAC/IPPC, and xHCI host MAC. The vendor
shared-window layout is split rather than copied into a mainline node. VBUS,
power domains, role switching, IDDIG/FUSB301, redriver GPIOs, and PHY tuning
remain separate board contracts and are intentionally absent from the
candidate. Binding examples and all MT6797 DTBs compile, but no runtime probe
or hardware write has been attempted.

USB1 is different at the platform boundary: it has a standard MUSB/Inventra
MAC, but a distinct MT6797 USB11 SIF/PHY, `0xa0`/`0xa4`/`0xa8` level-1
interrupt block, two-clock contract, six-endpoint host configuration, and
vendor wake behavior. Reuse the MUSB core and common T-PHY V1 fields where
the source equivalence is proven; add targeted USB11 glue/variant hooks rather
than forking the protocol driver.

The refreshed USB1 contract result is
[`usb1-contract-validation-20260713.txt`](results/usb1-contract-validation-20260713.txt).
The corrected fixed-slew source result is
[`usb1-fixed-slew-validation-20260713.txt`](results/usb1-fixed-slew-validation-20260713.txt).
It records the live SPI73-to-Linux-IRQ105 mapping and the vendor source
configuration (`mode=host`, six endpoints, four DMA channels), then compares
it with Linux 7.1.3's three-clock, eight-endpoint `mediatek.c` glue. The
vendor USB11 PHY save-current/recover path writes hardcoded USB11 offsets and
voltage variants; its `SIF + 0x800` U2 fields are close to generic T-PHY V1,
but the generic `SIF + 0x100` calibration assumption is not valid unchanged.
The captured vendor config disables `CONFIG_MTK_ICUSB_SUPPORT` and
`CONFIG_MTK_DT_USB_SUPPORT`, so the active vendor path enters the USB11 helper
that writes meter controls at SIF `+0xf00`, then unconditionally takes its
timeout fallback and programs slew value `4`; alternate ICUSB builds use a
different bias path, while DT-USB builds return before the helper. This defines
a small explicit USB11 glue/T-PHY variant boundary, but does not justify
copying a vendor power sequence or enabling a mainline node.

A second source-only comparison tightens the implementation choice:
[`usb1-core-equivalence-20260713.txt`](results/usb1-core-equivalence-20260713.txt)
shows that the USB11 MUSB core, FIFO/RAM sizing, HSDMA register block, and
level-1 interrupt bits are equivalent to Linux's existing MUSB/Inventra
protocol. The new code should be a small USB11 glue/data variant plus explicit
hooks in the existing T-PHY V1 implementation, not a second MUSB core or
standalone protocol driver. DMA remains a post-PIO gate.

Linux 7.1.3's MediaTek T-PHY driver supports MT2701, MT2712, MT8173, and
generic v1/v2/v3 layouts. It has no MT6797 match or binding entry. The source
audit shows that MT6797 shares the broad V1 U2/U3 register protocol, but its
PHY SPLLC/FM banks and IPPC reset/power bank are split across two SIF
resources; that is not a drop-in generic V1/V2 resource topology. USB11's U2
child at `SIF + 0x800` is a closer V1 match, but its calibration and runtime
power paths still need explicit variant data/hooks. The active vendor config
enters the USB11-specific helper at `SIF + 0xf00`, but the audited source
deterministically falls back to slew `4` rather than using a measured result;
Linux's existing `mediatek,eye-src = <4>` path can reproduce that fallback
without touching generic V1 `+0x100`. Reuse the common T-PHY
helpers where possible; add a new MT6797 PHY driver only if the split-resource
and USB11 lifecycle cannot be modeled cleanly. Do not copy vendor tuning
tables by default.

No FUSB301 driver or binding was found in the unpatched Linux 7.1.3 tree. The vendor
FUSB301 interrupt/state paths are incomplete, so simply wrapping them as a
Type-C class driver would preserve an old non-functional behavior. Patch 0056
now adds a generic, datasheet-derived FUSB301/FUSB301A Type-C controller driver
and binding: it validates Device ID `0x12`, configures documented mode/current
and interrupt registers from a connector child, and reports attach, partner
type, BC current, and CC orientation through the standard Type-C class. It
does not claim VBUS or SuperSpeed redriver ownership. The Gemini board nodes
remain absent until both ports, CC orientation, VBUS polarity/current control,
and the SW7226 redriver wiring are identified on hardware.

Comparing the candidate with Linux's existing autonomous Type-C drivers exposed
two state/safety gaps, now corrected in patch 0056: probe rejects a missing IRQ
before unmasking the controller, and detach restores neutral/default power,
data, VCONN, power-opmode, and orientation state instead of leaving stale
attached roles in the Type-C class.

The public [onsemi datasheet](https://www.digikey.com/htmldatasheets/production/1868762/0/0/1/fusb301.html)
confirms that the chip itself is an autonomous
Type-C controller with `SS_SW` and `ID` outputs, and that register `0x01` is a
device-ID register whose reset signature is `0x12`. An older Android FUSB301
[`Android FUSB301 driver`](https://android.googlesource.com/kernel/msm/+/966c8fc3a430933c2506b1112df5f16b782f3205/drivers/usb/misc/fusb301.c)
is useful as a register-map cross-check, but it exposes legacy sysfs and
switch-class interfaces rather than the modern Type-C framework; it also must
not be treated as Gemini board glue. The mainline work should therefore split
the generic FUSB301 register/IRQ driver from the Gemini-specific redriver and
USB-role wiring.

The new live result narrows the eventual board work: the I2C0 FUSB301A client
has a concrete GPIO64/EINT interrupt candidate, whereas the I2C1 FUSB301
client's vendor path has no valid interrupt (`request_irq` returns `-EINVAL`).
This permits a future staged experiment for only the I2C0 controller after its
physical connector and VBUS/redriver ownership are identified; it is not a
reason to instantiate both Type-C nodes in the board DT.

## Conclusion

`inconclusive`: the live topology and vendor contracts are reproducible, but
there is no mainline runtime result. USB3 has a strong MTU3/xHCI reuse case
after resource splitting; USB1 needs a distinct USB11 integration boundary;
the MT6797 PHY and board Type-C logic remain unproven. Patch 0056 supplies the
generic FUSB301 controller layer, but deliberately adds no Gemini board node.
The build and binding evidence is in
[`fusb301-current-validation-20260713.txt`](results/fusb301-current-validation-20260713.txt).

## Follow-up

1. Correlate each FUSB301 instance, ID/VBUS interrupt, and GPIO94 drive path
   with the physical left/right connector using owner-authorized cables and
   read-only descriptors.
2. Complete the source-audited MT6797 PHY and controller resource maps,
   including the two-SIF T-PHY banks, without writing tuning registers.
3. Define and review the USB11 glue/PHY interface (or a standalone USB11
   driver) against the six-endpoint, two-clock, host-mode contract before
   adding any USB1 DT node.
4. Add disabled-only MT6797 MTU3/xHCI/PHY bindings when the resource, clock,
   and rail contracts are complete; keep role switching detached initially.
5. Correlate the generic FUSB301 driver with each physical connector, attach
   IRQ, VBUS switch, and redriver path before adding Gemini nodes; do not
   enable the candidate from the public ID alone.
6. Decide whether USB1 can be a small MUSB glue extension after its SIF and
   wake semantics are tested; otherwise write a separate USB11 driver.
7. Boot one port in device-only mode with gadget serial, then validate host and
   Type-C transitions independently. Record every cable/polarity result in a
   new experiment rather than promoting vendor defaults to hardware support.
