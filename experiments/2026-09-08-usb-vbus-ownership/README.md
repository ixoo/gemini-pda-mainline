# USB VBUS ownership and FAN49101 contract correction

Status: source-only investigation, 2026-09-08. USB connector power ownership
remains unresolved. The historical FAN49101 voltage model is rejected as a
basis for enabling hardware or preparing an upstream driver.

## Question and inputs

Can the USB1 GPIO path, charger boost path and FAN49101 provider be connected
into one supported board power description? The answer from the inspected
source is no: software control paths are visible, but their electrical
relationship and physical connector mapping are not established.

The [source receipt](source-inputs.json) pins six public vendor files by commit
and SHA-256. Paths and line numbers below refer to that exact revision. This
investigation used source inspection only; it performed no device access,
register operation, cable change, boot or kernel build. Earlier runtime facts
remain owned by the [USB recovery experiment](../2026-07-12-usb-typec-recovery/README.md)
and [charger recovery experiment](../2026-07-12-charger-power-recovery/README.md).

## Two distinct software control paths

| Source | Observation | Limit |
| --- | --- | --- |
| `drivers/misc/mediatek/usb_c/Makefile` and `fusb302/usb_typec.c`, lines 96–167 | The FUSB302-named directory contains the board callback matching `mediatek,fusb301a`. Initialization lowers `usb1_drvvbus`; the callback raises it for orientation status values `0x10` or `0x20`, and resets it on detach or invalid orientation. GPIO70/71/72 select the HDMI/USB path. | Directory naming does not establish FUSB302 silicon. This callback has no charger-boost or FAN49101 call. |
| `arch/arm64/boot/dts/aeon_gpio.dtsi`, lines 229–244 | `usb1_drvvbus_low/high` select GPIO94 as a GPIO output with low/high levels. | The name and output level do not identify the electrical switch, power source, current limit or physical connector. |
| `drivers/misc/mediatek/xhci/xhci-mtk-driver.c`, lines 425–460 and 536–571 | Host-driver loading enables charger OTG before port power. Compile-time branches select BQ25898 or a BQ25890/charger-interface path; the latter depends on `chargin_hw_init_done_rt`. Disable follows separate conditional branches. | Source alternatives do not prove the running branch, populated charger variant or connection to GPIO94. Current-limit arguments are vendor code observations, not admitted board limits. |

These paths must not become independent mainline VBUS providers until their
shared ownership is resolved. A useful next observation must join physical
connector identity, selected role, GPIO94 ownership and the populated charger's
boost path in the same attributable session. Source naming alone cannot do so.

## FAN49101: withdraw the historical voltage contract

The vendor `fan49101_vosel()` helper at lines 394–410 computes a six-bit
selector from a 603000 microvolt base and 12826 microvolt step, then sets bit 7
in register `0x01`. Those 64 codes span 0.603–1.411038 V. A whole-tree literal
search for `fan49101_vosel` at the pinned commit finds only its definition and
log string. The initialization voltage writes at lines 340–359 are inside
`#if 0`. Thus the inspected source does not demonstrate that this formula
controls a working FAN49101 rail.

Manufacturer evidence contradicts that table. Onsemi's
[FAN49101 short datasheet](https://www.onsemi.com/download/data-sheet/pdf/fan49101-d.pdf)
(April 2025, revision 3, page 1) specifies operation delivering 2 A at 3.4 V.
The [FAN4910x evaluation manual](https://www.onsemi.com/download/eval-board-manual/pdf/evbum2955-d.pdf)
(April 2026, revision 0, page 1) identifies FAN49101 and FAN49103 as the I2C
versions and describes programmable output from 2.5 to 2.8 V in 50 mV steps,
then 2.8 to 4.0 V in 25 mV steps. These documents were inspected as published
PDF text; no local PDF or register-panel image is included in this record.

This is sufficient to reject the old table, but insufficient to implement a
replacement selector map or enable operation. The evaluation software is
labelled FAN49103; its register GUI must not be transferred to FAN49101 by
family resemblance. FAN49101-specific selector encodings, enable/control/reset
semantics, board rail ownership and constraints remain required. Neither a
buck/boost label nor these output specifications prove a USB VBUS connection.

[Patch 0055](../../patches/v7.1.3/0055-regulator-add-FAN49101-buck-boost-driver-and-Gemini-node.patch)
copies the unsupported voltage formula into its driver and binding. Its
historical compile/schema results do not validate that electrical contract.
The earlier claim that its probe is read-only is also withdrawn: the probe
registers a regulator with write-capable operations, and the complete
registration/constraint path has not been established as free of writes.
The disabled board node is not permission to enable it. Patch bytes and the
[old source-derived contract](../2026-07-12-charger-power-recovery/results/fan49101-register-contract.txt)
remain historical evidence, not a reusable implementation foundation.

## Decision and validation

Retain the historical manufacturer/die-ID observation separately from the
rejected voltage/enable assumptions. Do not introduce a replacement regulator
or USB power connection until the chip protocol and board ownership are known.
No manifest, series, profile, driver or DT input changes in this investigation.
Source hashes and the whole-tree helper search are reproducible from the pinned
public revision; documentation links and repository checks cover publication.
There is no new hardware-support claim or validated boot candidate.
