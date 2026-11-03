# Experiment: native display on the station

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-02-gemini-native-display` |
| Status | `running`: T0 read back the loader's state; patches and profile written, compile-checked; no display driver has run on the device |
| Subsystem | MT6797 MMSYS, DRM pipeline, DSI0, MIPI TX, Gemini panel |
| Device variant | named Gemini PDA (MT6797X), boot2 station |
| Date(s) | 2026-11-02 |
| Investigator(s) | Display session; device runs by the project custodian |
| Tracking issue | none |

## Question or hypothesis

Can the mainline MediaTek pipeline take over the panel the loader left running,
without resetting it or sending it a command, and put a frame on it?

It is falsified if a frame the owner can recognise never reaches the panel with
the pipeline and link programmed as they read on a running panel. A pass shows the
pipeline, DSI host and PHY. It does not show the panel's own power and init
sequence, identity, suspend or GPU scanout. Those are later stages below.

## What the evidence already settles

The retained Gemian capture, `display-state-mtkfb.txt`, from the [DRM component
record](../2026-07-12-mt6797-drm-component-recovery/README.md), holds a full
register dump from this unit taken at 2.98 s, before the kernel's first display
suspend. The [display record](../2026-10-04-gemini-display-re/README.md) cited it
for a few values. Read in full, it closes several questions that record left as
inference:

| Question | Read value | Consequence |
| --- | --- | --- |
| Lane rate (H3) | `PLL_CON2` `0x43b13b13`, `PLL_CON0` `0xf0002001` | Exactly 880 Mbit/s. Mode clock 146667 kHz |
| S2Q field (the [bsg100 audit](../2026-07-13-bsg100-gemini-linux-comparison/results/fbcon-commit-035d4b0-20260716.md) flagged a mismatch) | `0x2000` | [0039](../../patches/v7.1.3/0039-phy-mediatek-add-MT6797-MIPI-DSI-TX-support.patch) writes this value; the vendor's bit layout agrees |
| D-PHY timing | `TIMCON0-3` `0x080f0708 0x10280c20 0x0a280100 0x00102406` | Use these at 880 Mbit/s |
| Video timing | VSA 3, VBP 15, VFP 10, word counts 28/148/116 | Vendor formula confirmed. Patch 0043's mode had them in the wrong slots |
| Link mode | `MODE_CTRL` 3, `TXRX_CTRL` `0x1003c` | Burst, four lanes, clock LP between lines, EOT on |
| Routes | The MMSYS selector values | The [0031](../../patches/v7.1.3/0031-soc-mediatek-mtk-mmsys-add-MT6797-routes-and-resets.patch) table gives exactly these for the 12-block path |
| Mutex | `M0_MOD` `0x5fcb400`, `M0_SOF` `0x41` | [0029](../../patches/v7.1.3/0029-soc-mediatek-mtk-mutex-add-MT6797-support.patch)'s bits match, plus PWM0, which the path omits |
| OVL cascade | `DATAPATH_CON` 1, 5, 5 | Both two-layer overlays need background input; the common code set it on one |
| Reset | `LCM_RST_B` 1 | Out of reset through MMSYS, as the source says |

The retained Gemian boot log also shows this unit's panel takes the vendor's
NT36672 path through a full suspend, `lcm_poweron`, the bias writes and
`lcm_resume` at 3.3 s, on every boot, and works afterward. So the table in the
vendor kernel drives this unit's panel, whatever the silicon. It is behaviour, not
identity. The retained binary of that vendor kernel holds that table: all 181 writes
in [0043](../../patches/v7.1.3/0043-drm-panel-novatek-nt36672e-add-gemini-descriptor.patch)
match, byte for byte and in order, at one 72-byte-entry table followed by sleep-out.
So the generated table is the one this unit runs.

[bsg100](../2026-07-13-bsg100-gemini-linux-comparison/README.md), on another unit
with a different panel, reached a native console on Linux 6.6. Three of its
findings are used here, reimplemented, after reading the code they apply to:

- **DSI interrupt.** It is unmasked at probe while the loader's engine is live. On
  its unit that hung CPU0. Fixed by keeping it masked until the engine is reset
  ([0495](../../patches/proposals/0495-drm-mediatek-dsi-keep-the-IRQ-masked-until-the-engin.patch)).
- **Command mode.** The engine reset does not clear video mode, so a transfer waits
  for a `VM_DONE` that never comes ([0496](../../patches/proposals/0496-drm-mediatek-dsi-select-command-mode-after-the-engin.patch)).
- **First frame interrupt.** It can arrive before the CRTC has a state. Its fix
  enables then disables the OVL clock at probe, which would close the gate under the
  loader's running scanout. [0503](../../patches/proposals/0503-drm-mediatek-quiesce-OVL-and-RDMA-interrupts-only-be.patch)
  quiesces only behind a gate it finds open, and leaves the gate alone.

## T0: the loader's state on the mainline station

Reads only, boot `145d8512`, image `2b9ba33e`, under the running console. Every value
below is from this boot.

| Observation | Value | Meaning |
| --- | --- | --- |
| MM domain | `PWR_STATUS` bit 3 set in both words | On |
| MMSYS gates | `CG0` `0x00110000`, `CG1` `0xffffff00` | Only OVL1 and RDMA1 closed in the first bank, so every block in the path is open. DEVAPC does not block these reads here |
| DSI | Same words as the Gemian capture, including TIMCON and word counts | The capture holds on mainline |
| MIPI TX | Same words as the capture | 880 Mbit/s, bandgap `0x01249241` |
| DSI interrupt | `INTSTA` `0x80000792`, `INTEN` `0x3` | `CMD_DONE` pending and enabled with `DSI_BUSY` set. The stock handler would spin in hard IRQ, so 0495 is needed |
| OVL0 interrupt | `INTEN` `0xe`, `INTSTA` `0x2` | Armed and pending, so 0503 is needed |
| RDMA0 interrupt | `INTEN` `0x3f`, `INTSTA` `0x26` | Upstream's probe already clears these |
| Scanout | OVL0 L0 at `0x7dfb0000`, pitch 4352 | The console buffer |
| Routes and mutex | Same as the capture | As the tables give |
| Larbs | `0x380-0x3fc` and `0xf00-0xffc` read zero on larb0 and larb5 | Consistent with bypass. Inferred: the scanout address is physical |
| Pads | GPIO180 mode 1 (`LCM_RST`), input 1; GPIO60 and GPIO251 GPIO mode, output 1; GPIO178 mode 1 (`DISP_PWM`) | Bias enables on. Reset is the pad's hardware function |
| CMA | 32 MiB at `0xfe000000`, 31.6 MiB free | Below 4 GiB, as OVL's 32-bit address needs. Two 1080x2160 XRGB buffers fit |

The retained capture's `MM_CG_CON0` read `0xfffffff8`, gates closed with the overlay
running. This boot does not reproduce that, so it most likely belonged to that moment
in the vendor's suspend path, and it does not apply to the takeover.

## T1, first run: bind did not happen

Boot `01fcd554`, image `cffd5597`, package `b3b841d4`. All 12 modules loaded and every
component probed. The ten sampled registers were identical before and after, and no
display interrupt fired, so loading the drivers left the running scanout alone.
Three bugs stopped it there:

- The master failed with "Failed to find disp-mutex node": the MT6797 mutex was in
  `mtk-mutex` but not in the DRM component table. No bind or modeset ran. Fixed by
  [0504](../../patches/proposals/0504-drm-mediatek-recognise-the-MT6797-display-mutex.patch).
- Unload oopsed in `__mtk_clk_simple_remove`, an upstream gap: remove lacks probe's
  fallback for drivers registered without a DT match. It left that boot's `mtk-mmsys`
  stuck and the kernel tainted. Fixed by
  [0505](../../patches/proposals/0505-clk-mediatek-find-the-clock-description-on-remove-wi.patch),
  built-in code, so it needs an image.
- A WARN in `mipi_dsi_detach` when the host unloads first, fixed by
  [0506](../../patches/proposals/0506-drm-panel-nt36672e-don-t-detach-twice-when-the-host.patch).

The script's rc hid the failed unload, so it now exits non-zero on one.

## Design

| Decision | Why |
| --- | --- |
| Upstream `mediatek-drm`, `mtk_dsi`, `phy-mtk-mipi-dsi`, `mtk-mmsys`, `mtk-mutex` with the MT6797 data already in the station series | The read protocol matches. No new driver is needed |
| No MM power domain named in DT | `mtk-pm-domains` here has no MM entry. Nothing can power it down, so no bus-protection or SRAM sequence is at stake. `simplefb` already holds `mm_sel` |
| No SMI driver, no M4U, physical CMA buffers | The loader scans physical `0x7dfb0000` through the larbs in bypass. Binding SMI would add clock and larb transitions for no first-frame gain. Panfrost imports these buffers through its own MMU, so this does not block GPU scanout |
| No CMDQ | The CPU programs the pipeline at vblank |
| The panel driver adopts by default: no command, reset line or supply | The vendor kernel continues from the loader's panel state on a cold boot too. It separates the pipeline from the panel's power, so a failure means one thing. Bias and reset stay as the loader left them, so a wrong voltage or sequence cannot arise |
| `keep_firmware_fb` | Binding otherwise unregisters `simplefb`, which costs the owner's console before any frame is tried |
| Vendor porch and timing words at 880 Mbit/s only | Other rates keep the formula |

Failure paths: the link and panel are reprogrammed by LK on every boot, so a dark
panel recovers with `poweroff` and the owner selecting boot2. USB SSH shares nothing
with this path. A bus hang drops SSH and needs the same power cycle.

The one unknown no reading can settle is whether this panel tolerates the HS link
stopping and restarting with no sleep or reset around it. The vendor never does
that. T2 is the test.

## Stages

Each is a separate custodian request, with its own decision table.

| Stage | Effect | Decides |
| --- | --- | --- |
| T0 | Reads only, running boot. Done | Live gates, larb bypass, pad modes |
| New image | DSI bus core, display DT, nothing loads | Nothing changes at boot |
| T1 | Load the modules with `keep_firmware_fb`. RDMA interrupt writes. No modeset | Binding leaves the console running |
| T2 | First modeset, PHY and link restart, one frame | Whether the panel takes the restarted link |
| T3 | `read_identity`: DCS reads in command mode | Panel identity on this unit |
| T4 | Repeated modesets, `fbcon` on the native path | Drop `simplefb` as the console |
| T5 | Panfrost renders, the pipeline scans out | The goal: GPU frames on the panel |
| T6 | Bias, reset, full init table, once its preconditions are read | The panel's own power, so Linux owns it from cold |

T6 needs its own evidence first: the bias chip's readback and how to drive
`LCM_RST_B`. The table is already checked against the running binary.

## Associated code

- [`display-t0-read.sh`](display-t0-read.sh): the read-only snapshot.
- [`display-t1.sh`](display-t1.sh): load, bind with no modeset, unload.
- [`kms-frame.c`](kms-frame.c): sets the first output to a test frame, measures flips.
  `aarch64-linux-gnu-gcc -O2 -static -o kms-frame kms-frame.c`.
- Patches [0495](../../patches/proposals/0495-drm-mediatek-dsi-keep-the-IRQ-masked-until-the-engin.patch)
  to [0503](../../patches/proposals/0503-drm-mediatek-quiesce-OVL-and-RDMA-interrupts-only-be.patch),
  and [`gemini-a53-station-display.fragment`](../../configs/gemini-a53-station-display.fragment),
  in the `mt6797-a53-station-a72` profile only.

## Observations

Package, not yet run: commit `b3b841d4`, profile `mt6797-a53-station-a72`, modules
built, Buildbox-2, `SHA256SUMS` `fa8ca23a`, `Image.gz` `782ee797`, station-a72 DTB
`fcb00229`. It also carries the GPU session's defaults. Its image gains only the
DSI bus core and small display helpers.

T0 above is the only device run. The driver patches are compile-checked only: `W=1`
on the changed DRM and panel objects in the VM gives no warning.

## Follow-up

Results go here, then durable facts to [display and panel](../../docs/hardware/display-panel.md)
and demonstrated support to [HARDWARE_SUPPORT](../../docs/HARDWARE_SUPPORT.md).
