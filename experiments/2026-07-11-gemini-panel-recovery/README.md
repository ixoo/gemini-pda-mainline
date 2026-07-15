# Experiment: Gemini panel recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-11-gemini-panel-recovery` |
| Status | `completed` |
| Subsystem | Internal display panel and bias supply |
| Device variant | Gemini PDA running Gemian |
| Date | 2026-07-11 through 2026-07-14 |
| Investigator | Repository maintainer with Codex assistance |

## Question

Which panel driver is actually selected on the running Gemini, and what DSI,
power, reset, initialization, and suspend contract must a mainline DRM panel
implementation preserve?

## Method and safety

The owner-authorized SSH session used read-only sysfs, debugfs, running-kernel
configuration, and kernel messages. The committed
[`collect-live-panel.sh`](scripts/collect-live-panel.sh) probe filters out
volatile buffer addresses and fence dumps. Private raw output belongs at
`artifacts/device-inventory/20260711-live/panel.txt`; the normalized,
non-identifying facts used here are preserved in
[`results/runtime-summary.txt`](results/runtime-summary.txt).

The live result was correlated with the exact Planet 3.18 source at commit
[`c5b0be85017ad0c599725e8273842efdbecdd88a`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/tree/c5b0be85017ad0c599725e8273842efdbecdd88a),
especially the
[`aeon_nt36672_fhd_dsi_vdo_x600_xinli` LCM](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/lcm/aeon_nt36672_fhd_dsi_vdo_x600_xinli/aeon_nt36672_fhd_dsi_vdo_x600_xinli.c)
and [`lp3101.c`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/gpio/lp3101.c).
The official product specification independently describes a 5.99-inch
2160x1080 display.

No DSI transaction, GPIO, I2C write, suspend request, or display-state change
was issued by this experiment.

## Associated code

- [`scripts/collect-live-panel.sh`](scripts/collect-live-panel.sh) performs the
  bounded read-only runtime capture.
- [`scripts/decode-lcm-capture.py`](scripts/decode-lcm-capture.py) decodes the
  private vendor DT parameter/operation ABI without retaining addresses.
- [`scripts/compare-nt36672-command-tables.py`](scripts/compare-nt36672-command-tables.py)
  mechanically compares the active Gemini command table in the pinned Git
  object with Linux 7.1's existing NT36672E variant.
- [`scripts/check-bias-protocol.py`](scripts/check-bias-protocol.py) compares
  the vendor's address/register writes with Linux 7.1's existing TPS65132
  regulator protocol without claiming a physical chip identity.
- [`scripts/emit-gemini-panel-init.py`](scripts/emit-gemini-panel-init.py)
  regenerates the reviewable DSI command function from the pinned vendor Git
  object, retaining page-0x24 register writes and omitting only the framework-
  owned page-0x10 sleep/display commands.
- [`scripts/apply-gemini-panel-framework.py`](scripts/apply-gemini-panel-framework.py)
  applies the descriptor change to a disposable Linux authoring clone; it is
  not part of the kernel build.
- [`scripts/audit-nt36672-packet-semantics.py`](scripts/audit-nt36672-packet-semantics.py)
  checks the MT6797 vendor DSI helper's `0xb0` packet boundary against the
  generated mainline sequence.

The current Linux 7.1.3 package carries the shared NT36672E panel framework as
`panel-novatek-nt36672e.ko`, but the Gemini panel consumer remains absent from
the DT and no DSI transfer has run under mainline. The authoritative module-
inclusive package identity, command-table comparison, bias-protocol comparison,
and runtime gates are recorded in
[`mainline-panel-current-72-validation-20260714.txt`](results/mainline-panel-current-72-validation-20260714.txt);
the earlier 71-patch record is historical.
The normalized reproducible comparison records are
[`panel-command-audit-20260714.txt`](results/panel-command-audit-20260714.txt)
and [`panel-bias-audit-20260714.txt`](results/panel-bias-audit-20260714.txt).

## Decisive runtime result

The running framebuffer reports:

- LCM driver `aeon_nt36672_fhd_dsi_vdo_x600_xinli`;
- 1080x2160, DSI, connected;
- video mode with CMDQ enabled;
- `DISP_OPT_USE_DEVICE_TREE=0`;
- a 1088-pixel framebuffer stride, 32 bits per pixel, and physical rotation
  configured as 90 degrees.

Kernel messages from real suspend/resume cycles contain the exact NT36672 LCM
strings. The I2C device at bus 1, address `0x3e`, is bound to the downstream
`lp3101` driver. These observations prove which compiled-in board driver is in
use. They do **not** independently read the panel's silicon ID: outside the
bootloader build, this driver's `compare_id()` returns success unconditionally.
The bootloader-only branch selects the vendor page, reads `0xdb` and `0xf4`,
and expects the combined value `0x8070`; no retained log proves that result for
this physical unit. A mainline compatible must therefore remain module-specific
and provisional until a controlled read or physical identification confirms it.

## Active panel contract

| Property | Recovered value |
| --- | --- |
| Downstream controller ID | `NT36672`, expected bootloader ID `0x8070` |
| Logical frame | 1080 x 2160 |
| DSI links | one, DSI0 |
| Lanes | four |
| Pixel format | packed RGB888 |
| Mode | burst video mode |
| Vertical timing | sync 3, back porch 15, front porch 10, active 2160 |
| Horizontal timing | sync 10, back porch 42, front porch 42, active 1080 |
| DSI PLL request | 440 MHz |
| Clock behavior | low-power clock between lines; SSC disabled |
| ESD check | DCS `0x0a` must return `0x9c` |
| Reset | Active path writes MMSYS `LCM_RST_B` at `0x150`; pin 180 is muxed to hardware function `LCM_RST` |
| Positive bias enable | GPIO 60 |
| Negative bias enable | GPIO 251 |
| Bias controller | I2C1 `0x3e`, downstream name `LP3101` |

The vendor `PLL_CLOCK` value is a downstream D-PHY configuration input, not a
DRM pixel clock. A mainline mode clock and MediaTek DSI rate must be calculated
using the host driver's conventions and verified against the resulting line
and frame rate.

## Power and command sequence

Power-on is ordered as follows:

1. drive reset low;
2. enable positive bias, then negative bias;
3. wait 20 ms;
4. write `0x0f` to LP3101 registers `0x00` and `0x01`;
5. drive reset high for 10 ms, low for 10 ms, then high for at least 20 ms;
6. send the panel-specific initialization table.

Although the board DTS contains low/high pinctrl states for pin 180, the active
`lcm_set_reset_pin()` branch does not select them: it writes value 0/1 directly
to MMSYS offset `0x150`. Mainline already describes pin 180's alternate
`LCM_RST` function, but the existing NT36672E panel framework expects a reset
GPIO. The least invasive bring-up hypothesis is to mux pin 180 as GPIO and use
the existing `reset-gpios` interface, documenting that this differs from the
vendor path and validating the physical reset waveform. Do not add a new reset
driver unless that configuration proves electrically insufficient.

The initialization table uses the Novatek page-select command `0xff` and
reload/unlock command `0xfb`, then programs pages `0x20`, `0x24`, `0x25`,
`0x26`, and `0x27`, including panel-specific gamma data. The pinned MT6797
vendor DSI helper is not packet-neutral: commands below `0xb0` use DCS packet
types, while `0xb0` and above (including `0xfb` and `0xff`) use generic packet
types. The mainline candidate now preserves that boundary through a dedicated
Gemini write helper; the reproducible audit is in
[`nt36672-packet-semantics-20260714.txt`](results/nt36672-packet-semantics-20260714.txt).
Its final page `0x10` sequence sets brightness/control registers (`0x51=0xff`,
`0x53=0x24`, `0x55=0x00`), sets address mode `0x36=0x03`, exits sleep with
`0x11`, waits 120 ms, enables the display with `0x29`, and waits 10 ms.

Suspend sends display-off `0x28`, waits 50 ms, sends sleep-in `0x10`, waits
120 ms, then disables negative bias followed by positive bias. Mainline code
must preserve those rail and reset orders, including unwind paths.

The raw `0x0f` selector writes are established, but the downstream `LP3101`
name is not a reliable physical identity. LowPowerSemi's current
[LP3101 product entry](https://lowpowersemi.com/Product-series/Panel_Power)
describes a fixed ±5.5–5.9 V, 300 kHz, DFN-12 charge pump. The available
[official LP3101A datasheet](https://www.lowpowersemi.com/storage/files/2023-05/f5bad406d73e022ef15f04205805aaac.pdf)
shows an EN pin and no I2C interface. That is inconsistent with a live client
at `0x3e` accepting two selector-register writes.

The protocol instead matches Linux's existing TPS65132 regulator exactly:
I2C address `0x3e`, positive/negative selectors at `0x00`/`0x01`, five-bit
selectors starting at 4.0 V in 100 mV steps, and a separate enable GPIO for
each output. The mechanical result is:

```text
PASS candidate=tps65132 protocol=addr-3e-regs-00-01 selector-0f=5500mV enables=per-output identity=unproven
```

Thus the retained writes mean ±5.5 V *if* the device is TPS65132-compatible.
This is strong protocol evidence, not proof of TI silicon: TPS65132 exposes no
identity register in the upstream driver, and multiple LCD-bias parts use this
layout. Do not add `ti,tps65132` to DT until a board marking, schematic,
datasheet-level compatible identity, or controlled electrical verification
establishes it.

The downstream `lp3101.c` driver provides no register-read path or chip-ID
check; it only stores the I2C client and emits the two raw writes from
`lp3101_poweron()`. Thus the current device cannot resolve the silicon identity
through its existing driver without adding a deliberate read-only diagnostic
interface.

## Live pin-control cross-check

On the named Gemian device (`gemini@192.168.1.50`), the vendor pinctrl debug
state reports:

| Pin | Live observation | Interpretation |
| --- | --- | --- |
| GPIO60 | claimed by `aeon_gpio`, muxed as `GPIO60` | matches positive-bias helper ownership |
| GPIO180 | mux and GPIO unclaimed | consistent with the vendor callback using the MMSYS `LCM_RST_B` path rather than a gpiolib consumer |
| GPIO251 | mux and GPIO unclaimed | consistent with direct Aeon bias-state selection; not evidence that the pin is unused |

The vendor pinctrl states explicitly set GPIO60 and GPIO251 low/high and expose
GPIO180's alternate `LCM_RST` function. The live ownership state corroborates
the wiring, but does not prove that a mainline `reset-gpios` consumer can
replace the MMSYS reset write. That equivalence requires a bounded waveform or
panel bring-up test with a recoverable image.

## The R63419 false lead

The live root device tree also contains a complete
`r63419_wqhd_truly_phantom_2k_cmd_ok` description: 1440x2560, dual DSI,
command mode, lane swapping, and UFOE left/right compression. The
[`decode-lcm-capture.py`](scripts/decode-lcm-capture.py) tool decodes that
vendor `/lcm_params` and `/lcm_ops` ABI from a private inventory capture.

It is an inactive board-family alternative, not the running Gemini display.
The contradiction is resolved by `DISP_OPT_USE_DEVICE_TREE=0`: the kernel
selects a compiled-in LCM driver. This is a reusable warning for every vendor
DT node—presence and even `status = "okay"` are weaker evidence than runtime
binding or use.

## Linux 7.1.3 mapping

Linux 7.1.3 has DRM panel drivers for NT36672A and NT36672E panels. They
provide useful structure for regulator consumers, reset GPIO handling,
page-based command tables, four-lane RGB888 video mode, and DSI attach. Neither
existing compatible describes this Gemini panel: their modes, command tables,
supplies, and power sequences differ. The Gemini should receive a specific
panel compatible and data set; it must not claim one of those compatibles based
only on the controller-family name.

The exact comparison with `panel-novatek-nt36672e.c` reports:

```text
PASS vendor-commands=167 upstream-commands=234 address-overlap=69 exact-overlap=4 vendor-id=8070 linux-probe=unconditional reset=mmsys-0x150 bias-gpios=60,251 vendor-pages=10,20,21,24,25,26,27 upstream-pages=10,20,21,24,25,26,27,2a,2c,f0
```

This is strong evidence for reusing the upstream driver's framework, not its
existing panel data. The shared page/reload protocol and seven common pages
establish the controller family. Only four complete command/payload tuples
match, while the upstream variant programs three pages absent from the Gemini
table. Sending the upstream NT36672E sequence to the Gemini would therefore be
an uncontrolled panel write, not a reasonable fallback.

The packet audit is a separate transport constraint: using DCS for the entire
table would silently diverge from the vendor MT6797 host implementation even
when command bytes are identical. No hardware transfer has yet validated the
generic/DCS boundary on this physical panel.

Patch
[`0043-drm-panel-novatek-nt36672e-add-gemini-descriptor.patch`](../../patches/v7.1.3/0043-drm-panel-novatek-nt36672e-add-gemini-descriptor.patch)
now extends the shared driver with descriptor-selected supply names, reset and
suspend delays, the inferred 1080x2160 mode, and the 165 panel-register writes
from the vendor table. The existing NT36672E descriptor remains unchanged in
behavior. Gemini's descriptor requests `outp` then `outn` rails, a 20 ms settle,
10/10/20 ms reset timing, and 50/120/120/10 ms display delays; this models the
observed contract without asserting that `outp`/`outn` prove a TPS65132 chip.

The patch is mechanically checked and compiles as an arm64 panel object in the
canonical reconstructed tree. The Gemini compatible is deliberately not wired
into the disabled board DT node yet: the panel sequence is mainline-ready for
review, not hardware support. No `ti,tps65132` compatible or direct bias-chip
identity claim is included.

There is also a host-rate discrepancy to preserve for testing. The recovered
timing totals are 1174 by 2188. Interpreting the live diagnostic `5405` as
54.05 Hz gives a 138.839 MHz pixel clock, for which Linux's MediaTek DSI formula
requests 833.033 Mbit/s per lane. The retained live PHY is 435 MHz, or about
870 Mbit/s, 4.44% higher. The diagnostic interpretation remains an inference,
but it identifies a bounded first-light variable: record the programmed PHY
rate and measured refresh before changing host rate calculations or panel
porches.

The active panel removes dual-DSI, SPLIT, and UFOE from the first-light path.
The immediate display target is a single DSI0 burst-video pipeline, with the
bias regulator, reset GPIO, and panel variant modeled explicitly. The local
series now supplies native MT6797 DSI/PHY support and disabled SoC nodes. The
remaining board blocker is the panel/bias contract, not a reason to substitute
an existing NT36672E command table.

## Independent bsg100 cross-check

The bsg100/gemini-linux revision
`82321ce64752d5bf006fe7c40c331edbd0dfb702` contains a later hardware-tested
panel path. Its stock-vendor harvest names the selected LCM
`aeon_ssd2092_fhd_dsi_solomon` at 1080x2160 in video mode, and its suspend/resume
capture reads SEEPROM words decoding to `AUO`, `599`, `SSD`, `2092`, and version
`0x16`. A separate DSI debug session reads `0x0f=0x80`, `0x45=0x00`, and
`0x0a=0x1c`, followed by a Linux panel registration message. These are stronger
identity observations than a compiled-in driver string.

That evidence conflicts with this repository's named-device capture, which only
shows the software-selected `aeon_nt36672_fhd_dsi_vdo_x600_xinli` driver and an
unconditional vendor `compare_id()` path. The two units may carry different
panel variants, or the legacy vendor tree may mix display and touch labels. The
named-device capture also retains both LCM candidates in its vendor config and
has a separate `solomon_touch@0x53` node unbound alongside the active NVT
`cap_touch@0x62`; its filtered log contains both `NT36672` and `SSD2092` suspend
labels, but does not identify the emitting component. The current capture cannot
distinguish these cases. The normalized comparison and source hashes are in the [bsg100 panel cross-check](../2026-07-13-bsg100-gemini-linux-comparison/results/bsg100-panel-crosscheck-20260714.txt),
generated by [`audit-bsg100-panel-crosscheck.sh`](../2026-07-13-bsg100-gemini-linux-comparison/scripts/audit-bsg100-panel-crosscheck.sh).

Consequently the local NT36672 descriptor patch remains a source-audited,
disabled candidate, not hardware support. Do not enable either the NT36672 or
SSD2092 consumer until a controlled DSI readback or panel SEEPROM capture is
made on the named device. The shared 1080x2160 single-DSI video geometry is
useful for host-pipeline planning, but command tables, controller identity, and
readback values are not interchangeable. The `solomon_touch@0x53` node and
mixed suspend label are inventory evidence only, not a display identity proof.

## Limitations and next experiment

- The observed driver selection is high confidence; the NT36672 silicon suffix
  and module manufacturer remain described rather than independently probed.
  The independent bsg100 direct-probe result names SSD2092, so panel identity is
  now an explicit cross-device/variant contradiction rather than a resolved
  fact.
- The 68x136 mm mode dimensions are an inference from the published 5.99-inch,
  2:1 specification, not a measurement of this module. Debugfs `lcm_fps=5405`
  is retained as a downstream diagnostic value, not interpreted as a standard
  DRM refresh rate; the 138.839 MHz mode clock is consequently provisional.
- The LP3101 name conflicts with the documented LowPowerSemi interface;
  TPS65132 protocol semantics are a strong match, but actual rail voltage and
  silicon identity remain unverified.
- No mainline DSI host or panel code has yet been run on hardware.

After a mainline DSI host can perform bounded transfers, the next controlled
experiment should first identify the panel family on the named device (the
NT36672 `0xdb`/`0xf4` path and the SSD2092 readback/SEEPROM path are separate
candidate protocols), with strict timeouts and no rail changes. Bias-chip
identity and rail voltages should be established separately from a datasheet,
board measurement, or non-destructive identification method before regulator
code is enabled.
