# Experiment: native display on the station

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-02-gemini-native-display` |
| Status | `running`: the native console loads at boot, and the kernel turns the display off on the lid and on a blank. Linux's own panel init, the fade by eye and a battery figure are not done |
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
| T2 | First modeset, PHY and link restart, one frame. Done: it does | Whether the panel takes the restarted link |
| T3 | Teardown by unload, second modeset with DCS reads in command mode, one frame. Done: it recovers | Whether teardown recovers, panel identity on this unit, colour order |
| T4 | `fbcon` on the native path, blank and wake, a master taking over, reload | Whether the console can leave `simplefb` |
| T5 | Panfrost renders, the pipeline scans out. Done | The goal: GPU frames on the panel |
| T6 | Bias, reset, full init table, once its preconditions are read | The panel's own power, so Linux owns it from cold |

T6 needs its own evidence first: the bias chip's readback and how to drive
`LCM_RST_B`. The table is already checked against the running binary.

## Associated code

- [`display-t0-read.sh`](display-t0-read.sh): the read-only snapshot.
- [`display-t1.sh`](display-t1.sh): load, bind with no modeset, unload.
- [`display-t2.sh`](display-t2.sh): load, first modeset with a test frame, read the
  pipeline while it runs.
- [`display-t3.sh`](display-t3.sh): teardown, second modeset, identity reads.
- [`display-t5.sh`](display-t5.sh) and [`gpu-scanout.c`](gpu-scanout.c): the GPU renders
  into display buffers through dma-buf, and the display flips them. Build as
  `gpu-gles` in [`build-mesa.sh`](../2026-11-02-mali-t880-first-job/build-mesa.sh), adding `-lm`.
- [`display-t4.sh`](display-t4.sh): console on the native path.
- [`display-power.sh`](display-power.sh): battery draw awake, backlight off and blanked,
  run on battery on a fixed schedule.
- [`display-t6-brightness.sh`](display-t6-brightness.sh): whether a brightness step reaches
  the live level, with no one at the device.
- [`kms-frame.c`](kms-frame.c): sets the first output to a test frame, measures flips.
  `aarch64-linux-gnu-gcc -O2 -static -o kms-frame kms-frame.c`.
- Patches [0495](../../patches/proposals/0495-drm-mediatek-dsi-keep-the-IRQ-masked-until-the-engin.patch)
  to [0503](../../patches/proposals/0503-drm-mediatek-quiesce-OVL-and-RDMA-interrupts-only-be.patch),
  and [`gemini-a53-station-display.fragment`](../../configs/gemini-a53-station-display.fragment),
  in the `mt6797-a53-station-a72` profile only.

## Observations

Package, not yet run: commit `967983c2`, profile `mt6797-a53-station-a72`, modules
built, Buildbox-2, `SHA256SUMS` `4e86246c`, `Image.gz` `e65a739e`, station-a72 DTB
`fcb00229`. It also carries the GPU session's defaults. Against the T1 package
`b3b841d4`, the DTB is identical and only the image and two modules differ. `kms-frame`
`3edd7090`, built on Buildbox-2 from `86752e86`.

In T1's first run the owner saw the three markers with no change on screen.

T1 second run, boot `505d2716`, image `677021f2`, package `967983c2`: rc 0, tainted 0,
`card0` and `card0-DSI-1` appeared, all 12 modules unloaded, the ten sampled registers
unchanged, no display interrupt, and the owner saw no change. So bind and unload pass.

T2 first attempt, same boot: `kms-frame` reported no connected output and no modeset
ran. It asked for modes without the zero-count call that makes the kernel probe a
connector, a bug in the tool.

**T2, the first native frame**, same boot, tool `fb10debf`. The owner, watching the
panel: "vertical colored bars and a black rectangle moving right to left in the middle
of the screen", then "all looked correct the corners had boxes. right now the screen is
black".

- Tool: connector connected, one mode, 1080x2160 at 146667 kHz, nominal 57 Hz. 1621
  flips in 30.018 s, 54.00 per second, none late. OVL0's interrupt count rose as
  expected; the other blocks' stayed 0. Tainted 0, no warning or flip timeout.
- Read while running, against the loader's state: scanout at `0xfe200000` in CMA, DSI
  and PHY otherwise the same words, with `PLL_CON2` `0x43b14528`, 880.002 Mbit/s against
  the loader's `0x43b13b13`. Layer format `0x20ff`, the loader's format 2 without alpha.
- When the tool exited its framebuffer was removed. The plane turned off and the CRTC
  stayed active, so the link kept running on a black background. That is the black the
  owner saw.
- Not sent: any panel command. Not touched: reset, bias, supplies, MM domain, SMI.

**Analysis.** The panel accepts the HS link stopping and restarting with no sleep or
reset around it, at least on this one run. 54.00 Hz, measured for the first time on
this unit, agrees with the vendor's `lcm_fps=5405`. The nominal 57 Hz in the mode is
wrong by the time the LP transitions take, and should be corrected if anything
depends on it. "Vertical" bars and "right to left" agree with scan lines running along
the long side, the portrait panel held in landscape. Colour order and which corner is
which were not reported, so byte order is not established. T3 asks.

**T3, teardown, second modeset and identity**, same boot. rc 0, tainted 0, 54.00 flips
per second, modeset in 0.026 s. After unload the display gates read closed and the PLL
off (`CG0` `0x3f9f8000`, `PLL_CON0` `0xf0002010`), with the panel about 5 s without a
signal and no sleep command. After the second modeset they read the loader's values.
The panel came back: the owner sent a photo, held in landscape with the keyboard toward
them.

| Seen in the photo | Frame as drawn | Meaning |
| --- | --- | --- |
| Bars, right to left: white, yellow, cyan, green, magenta, red, blue, grey | First scan line to last | Scan lines run along the short side, the first at the right |
| Top-right red, bottom-right green | Start and end of the first line | Each line runs top to bottom |
| Top-left blue, bottom-left white | Start and end of the last line | No mirror |
| Colours named as drawn, white border, straight edges | XRGB8888 | Byte order is right, geometry is right |

In landscape the panel scans rotated 90 degrees, unmirrored, as the console's
`fbcon=rotate:3` already assumes. A photo cannot show flicker.

First DCS reads from mainline, in LP with bus turnaround:

| Register | `0a` | `0b` | `0c` | `0d` | `0e` | `0f` | `da` | `db` | `dc` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Read | `9c` | `03` | `07` | `00` | `00` | `c0` | `00` | `80` | `00` |

`0a` = `0x9c` is the value the vendor's ESD check expects, and `db` = `0x80` is half of
the loader's NT36672 ID check, which wants `0xdb` = `0x80` and `0xf4` = `0x70`. The
other project's SSD2092 unit reads `0a` = `0x1c` and `0f` = `0x80`. So on this unit the
panel behaves as the NT36672 path says, and not as that SSD2092 does. `0xf4` was not
read, and it follows a vendor unlock write this run did not send, so this is strong
evidence and not the full check. The read path works, so read timing is fine with the
read TIMCON words.

The owner on T3: "no flicker, it was smooth".

**T5, GPU frames on the panel**, same boot, after the GPU session's first load, which
also passed with the display modules loaded. `gpu-scanout` `3d12e160`: the display
driver allocates two dumb buffers from CMA with pitch 4352, Panfrost imports them through
dma-buf and renders into them through its own MMU, and page flips show them. 3240 frames
in 60.005 s, 54.00 per second, mean draw 4.32 ms, worst 8.07 ms, none late, SoC peak about
34 C, tainted 0, no fault. In the owner's photo, a triangle shaded red, green and blue on
a blue background with the sweeping band. Owner, by eye, answering a question: "Dark
grey, smooth".

**Tone check, T5c.** Both photos made dark values look bright. By eye the owner calls
`0x404040` dark grey and says "my phone is affecting the colors", so this was exposure.
Read while running: CCORR, AAL, GAMMA and OD in relay, UFOE in bypass, dither engine on.
COLOR0's two main registers were lost to a redirect in the request. Colour was judged
by eye only, not measured.

## Conclusion

On one boot, from modules, frames rendered by the Mali reach the panel through the
mainline pipeline and DSI, using upstream drivers with MT6797 data and no new driver.

Not shown, and what stands in the way of Linux owning the display:

- **The panel's own power and init.** It is adopted, and Linux sent it only DCS reads.
  The table is checked against the running binary. The bias chip's readback and how to
  drive `LCM_RST_B` remain. Until then a boot depends on LK having lit it.
- **Console.** `simplefb` is still the console. Once the pipeline takes the panel the
  console is gone until the next boot. Native `fbcon` needs fbdev emulation in the
  profile and `keep_firmware_fb` off.
- **Clean ownership.** No MM domain, SMI or IOMMU is modelled, and `clk_ignore_unused`
  and `simplefb`'s `mm_sel` hold are still needed. The path's gates have had one close and
  open cycle, the MM domain none.
- **DPMS, suspend, ESD, the panel `backlight` link, DRM rotation property.** Not tried.
- **Upstream shape.** `keep_firmware_fb` is bring-up only, and the static path in 0041
  and the fixed TIMCON should be revisited for submission.
- **Modes.** The nominal 57 Hz is not the measured 54.00 Hz.

T0 above is the only device run. The driver patches are compile-checked only: `W=1`
on the changed DRM and panel objects in the VM gives no warning.

## T4: the console on the native path

Owner's direction: native console next. Reading the code first found two things the
frame tests did not reach:

- **The MM root clock.** Binding without `keep_firmware_fb` unregisters `simplefb`, the
  only holder of `mm_sel`. With the display off the root would close, and the gate check
  in [0503](../../patches/proposals/0503-drm-mediatek-quiesce-OVL-and-RDMA-interrupts-only-be.patch)
  reads MMSYS registers that need it. So MMSYS now holds it
  ([0507](../../patches/proposals/0507-soc-mediatek-mmsys-optionally-hold-a-root-clock.patch)),
  the state T3 passed in.
- **Blanking.** The station blanks the console after two idle minutes, which `simplefb`
  ignored and only `lid-guard` acted on. Under DRM it turns the output off. An adopted
  panel would stay initialised and display-on with no signal for as long as the blank
  lasts. [0508](../../patches/proposals/0508-drm-panel-nt36672e-put-an-adopted-Gemini-panel-to-sl.patch)
  sends the vendor's `0x28`, 50 ms, `0x10`, 120 ms, and on the way back `0x11`, 120 ms,
  `0x29`, 10 ms, decided from the panel's own power mode. These are the first panel
  writes from Linux. Read: the vendor's suspend and delays. Inferred, new to this panel:
  waking with no reset or table. The vendor always runs the full sequence on resume.

### T4, first run: console moved, DSI interrupt lost

Boot `444a7d22`, image `34306c22`, package `27f7a9b2`. The console moved to the DRM
framebuffer, came back after a master and after a reload, and flips ran at 54.00 per
second. It also tainted with a WARNING, and every DSI transfer timed out. The cause
is the interaction of [0495](../../patches/proposals/0495-drm-mediatek-dsi-keep-the-IRQ-masked-until-the-engin.patch)
with the order in `mtk_dsi_probe()`: registering the DSI host binds the whole device,
and with an fbdev client runs the first modeset, before probe has requested the
interrupt. The earlier tests had no client, so their modeset came later. Fixed by
[0509](../../patches/proposals/0509-drm-mediatek-dsi-finish-probe-s-setup-before-registe.patch).

Because the first prepare failed, DRM skipped every later unprepare, so display-off and
sleep-in were never sent. What went to the panel, unconfirmed since no completion
returned: `0x0a` reads and `0x11` to an awake panel. So sleep and wake remain untested.

Sysfs `blank` also reaches the VT: `lid-guard` logged blanks at it, contrary to the
request's claim. One of the three blanks read its gates open immediately after.

### T4b, with the fix: console, sleep and wake

Fresh boot `20195f1b`, same image, with `mediatek-drm` from `30711586`. rc 0, tainted 0,
no timeout. The console stayed through a master and a reload. Power mode read `0x9c`
on the first prepare, so nothing was sent, and `0x08` on each wake, so sleep-in took and
the panel reads asleep. Three script blanks and three real idle blanks each woke, the
panel showing the console again, by the owner's "all was good!" and "All worked". Typing
worked. This is the first evidence the panel wakes from `0x10` on `0x11` and `0x29` alone,
without a reset or the table.

### The blank and the backlight: what the mutex does

The owner's first report: "it doesn't turn the screen off (or maybe it's just the
backlight that's on)". Blanked, PWM `CON_1` read duty 0, live level `0x28` the old level,
and mutex 0 `MOD` `0x04000000`, the loader's PWM0 bit alone. Awake, `0x28` followed the
level.

The loader leaves PWM0 in mutex 0, and a PWM change latches on the mutex's frame start. I
first read the bit as stale and removed it with a patch, 0510. That was wrong. With it
gone, on boot `f04ffc20`, `CON_1` followed every brightness step and `0x28` stayed at
`0x200`: brightness froze at its load value, which also hid the fade. So `0x28` is the
live level, the commit bit alone does not latch here, and the membership is what makes
brightness work. 0510 is dropped.

It also means the glow was real. On a blank the frames stop first, so duty 0 cannot latch,
and the backlight stayed lit. The owner's "Dark" with 0510 does not fit that, and they
doubted it themselves, so it is not evidence. What turns it off is the enable bit below,
which does not wait for a frame.

### The display off with the lid and the blank

The owner: "we really need to switch the display fully off, it's not ok, even when I
close the lid it stays on", and that this is "too sensitive to stay user side". So the
kernel does it, with no daemon:

- **Lid bug.** Four lid events ended in a refcount underflow and the backlight device
  disappeared, leaving the PWM driving behind a sleeping panel. `gemini-lid` called
  `put_device()` on `backlight_device_get_by_type()`'s result, which takes no reference.
  Fixed by [0513](../../patches/proposals/0513-input-gemini-lid-drop-a-reference-the-lid-never-took.patch).
- **Any blank takes the backlight with it.** The panel node names the backlight, the
  upstream link: DPMS off disables it before the video stops, DPMS on enables it after.
- **The lid blanks the display.** `gemini-lid` turns the backlight off and blanks the
  console in a hold that a key from another input device cannot wake
  ([0515](../../patches/proposals/0515-vt-let-a-driver-hold-the-console-blank.patch),
  [0516](../../patches/proposals/0516-input-gemini-lid-blank-the-console-while-the-lid-is.patch)).
- **A bind behind a blanked console.** `fbcon_init()` sets the mode whether or not the
  console is blanked, which would light the panel behind a closed lid. [0521](../../patches/proposals/0521-fbcon-keep-a-blanked-console-blanked-when-taking-ove.patch)
  blanks the new framebuffer as the takeover finishes. [0522](../../patches/proposals/0522-input-gemini-lid-always-leave-the-display-on-when-un.patch)
  leaves the display on when `gemini-lid` unloads.
- **The PWM stayed enabled at duty 0.** [0514](../../patches/proposals/0514-pwm-mtk-disp-turn-the-MT6797-block-off-at-duty-0.patch)
  clears the enable bit at level 0, as the vendor does.
- **The native path only helps when loaded.** `display-start` in the RAM root loads the
  modules at boot, subject to the owner's decision. It loads in the background so it cannot
  hold SSH back. A load that does not reach the panel, including a hang or a power loss,
  leaves a marker on the data partition, so the next boot stays on `simplefb` and clears
  it. `/mnt/data/no-native-display` skips it outright. With no writable data partition it
  also stays on `simplefb`, since a hang could then never be skipped. Without it, the lid still turns the backlight off and blanks `simplefb`, but an
  idle blank does nothing to the panel or backlight.
- **Built in or module:** the VT hold and the PWM change are built in. `gemini-lid`,
  the panel and the pipeline are modules. `lid-guard` is reduced to brightness keys and
  the fade.
- **Fade.** `lid-guard` fades the backlight down over the last 3 s before the idle
  deadline and up over about 0.5 s on waking. If it is stopped, the kernel path is
  unchanged, and only the fade goes. A content fade is left out: on this LCD, dimming the
  backlight dims all content together, which a content fade would only repeat. Doing it
  would need a private gamma or alpha interface, since fbcon's palette does not reach the
  pipeline.

Bias stays on during a blank. The vendor cuts it after `0x10`: negative off, positive
off, and on resume runs reset, both enables, 20 ms, two I2C writes, the reset pulse and
the whole table. Turning it off here is T6. What it saves is unmeasured.

### The lid and the blank on the running image

Boot `f04ffc20`, image `4ad593fc`, package `53fcd0a0`, still with 0510. The display loaded
at boot, `display=native`, with no marker left and tainted 0. 12 lid cycles, 24 events,
with no refcount, warning or timeout, and the backlight device intact. Closed: PWM enable
0, display gates closed, PLL off. The owner: "all looks good, when I close the lid, the
screen turns off for real".

With `lid-guard` killed: lid closed read PWM enable 0, gates closed and PLL off. A write
to the console did not wake it, but console output does not poke the VT at all, so that
did not exercise the hold. A key from another input device would, and has not been tried. A forced blank read PWM enable 0, gates closed and PLL off, then enable
1 awake, so the panel's backlight link works. The fade and brightness keys could not show
on this image, for the reason above, and no battery figure exists yet.

A clean apply of main's series compiles every changed object with `W=1` and no warning,
and `station-dt.sh` passes with the panel's backlight and MMSYS's clock in place.

### Brightness back through the mutex, by register

Same boot, with `mtk-mutex` without 0510 swapped in and bit 26 of `MOD` written back to
the loader's value. The live level followed every step: 128, 384, 700 and 512, then after
a blank and wake 256 and 512, and the restored 640. Blanked, the enable bit read 0 and
`bl_power` 4; woken, 1. Tainted 0, no new errors. So brightness latches through the mutex
membership and the enable bit does the off. Before the bit was set, the live level read
`0x8e` with brightness 640, so the level frozen without the bit was not always 512. That
is not explained. Nobody watched this run, so whether the steps are visible, and the fade,
wait for the morning.

The combined image with this, the review fixes, the charging guard and Bluetooth's modules
is written to boot2 and not booted: image `6bc70ab8`, package `b590193b`.

### The fade

Live on boot `7197708f`. A blank's fade reached the dim level about 1.7 s before the
backlight went off, and a wake showed no fade: the rest of the waking key's press cancelled
it. `ea6e7684` makes input wait for the end of a wake fade, and the owner: "the dimming
works, but there is a gap between the lowest brightness and the screen turning off, we need
to fix it. The wake up works great." `lid-guard` then timed the deadline from the key event's timestamp, in
milliseconds, but the gap stayed, at 1.95 s, and the owner: "there is still a gap when it
dims. the screen off should come slightly sooner". The kernel's blank is a wheel timer.
At HZ 250, an interval of 60 s or 120 s sits in the wheel level with 2.048 s granularity,
so it fires up to about 2 s late and never early. That is read from the source; the 1.69 s
and 1.95 s samples fit it. So no timing in userspace can meet it. `lid-guard` now powers
the backlight down at the end of the fade, and the kernel's blank follows up to 2 s later
and lights it again on waking. With `lid-guard` dead, the kernel path is as before.

Measured with no keys, on `a56c0705`: about 170 ms from the first sampled dim level to the
backlight off, at about 35 ms per sample, and the blank followed 0.66 s later. A wake with
no keyboard key then faded straight out again, because `lid-guard` only counted keyboard
keys. Any wake now restarts its deadline, as it does the kernel's. A power-key press with
the screen awake still moves the kernel's deadline unseen.

On `c6d4d2cb`, boot `7197708f`, no keys pressed, tainted 0: a wake with no key ran the wake
fade from 16 to 512 in 0.54 s, and no down fade followed until the next was due. That one
reached the dim level with the backlight off about 150 ms later, in coarse samples, and
the kernel blanked 2.1 s after that. With `lid-guard` replaced by a stub, the kernel blanked
about 61.6 s after a 60 s poke, with gates closed, enable 0, DPMS off and `bl_power` 4, and
unblanking restored them, so an idle blank needs no daemon.

By eye, on boot `64622312`, image `370f589b`, package `b590193b` with this `lid-guard`, the
owner: "screen blank fades are working amazing."

Later on the same boot, the owner: "all loks good for key press and fade in/out". Whether
that key press fell in the window with the light off is not known. The log shows 17 lid
cycles, some about 2 s apart, with the keyboard inhibited and restored each time, no warning
or respawn, tainted 0, and brightness back at 512. That is log evidence only: the owner did
not comment on the lid by eye.

Not run on this image: closed-lid register reads, the kernel-only lid test, a bind behind a
closed lid, and the power key under a closed lid. There is no power figure: the owner had "nothing to say on battery", so what a blank saves is
unmeasured, and with it whether turning bias off is worth doing.

### The console's size at the handover

The owner asked whether the two resizes when the native console starts could be avoided.
The boot log shows the console going to the dummy console at 80x25 and back to 135x33 when
`simplefb` goes, and it starts at 80x25 at boot for the same reason, and each resize reflows
the text. The dummy console's size is a config value, so it is now the panel's 135x33.
On the next image, by eye, the owner: "the console resize fix worked".

## After the review fixes

Boot `fccba04c`, image `96338704`, with the fixes from the review. The dummy console read
135x33 at 2.61 s, `display=native`, tainted 0, no oops. Unloading `gemini-lid` with the lid
open, and loading it again, left `bl_power` 0 and brightness 512 throughout, with no lid
lines beyond its start.

The owner closed the checks on this image: "for now let's consider all is ok, it looks ok,
I'll raise it if I experience any issue while using the device". Fn+B and Fn+N work, by
their word. The log, from 749 s to 2558 s, shows one blank at 882.4 s, consistent with a
2-minute idle, and an unblank at 2523.6 s by an unidentified input, with tainted 0 and no
errors.

**Not tested on this image, not passed:** the lid, with no lid event on this boot; a fade by
log, or its cancel; the lid during a fade; a key in the window with the light off. **Never
run:** 0521's bind behind a closed lid, and the battery run, so what a blank saves is
unmeasured. The owner will raise anything they notice in use.

## Panel orientation (built, not yet booted)

`0649` has the panel driver read the standard `rotation` property and report it, and `0650`
sets `rotation = <270>` on the Gemini panel, its left side up in the clamshell. DRM then
gives the connector `panel orientation` = Left Side Up. The fbdev helper maps that to a
90-degree counter-clockwise console, the same as `fbcon=rotate:3`, which still takes
precedence while it stays on the command line. niri 26.04 reads the property itself, as a
90-degree transform, and adds any `transform` in its config to it, so a config that keeps
`transform "90"` would end up at 180. Compiled with `W=1` and the DTB checked in the dev VM;
nothing is booted on it yet.

## CMA for compositors (built, not yet booted)

Under a wlroots compositor with SceneFX on package `37c50274`, `CmaTotal` was 32768 kB and
`CmaFree` 4036 kB just after start. About 40 `DRM_IOCTL_MODE_CREATE_DUMB` calls then failed
with ENOMEM. Scanout and effect buffers are mediatek-drm dumb buffers from CMA, 9.3 MB each.
The display fragment now sets `CONFIG_CMA_SIZE_MBYTES=256`. The logged reservations all lie
below 0xc0000000, and the default pool sits at the top of the first 4 GiB, so it should land
at 0xf0000000. Panfrost's own buffers are shmem and are not affected. The config resolves in
the dev VM; `CmaTotal` and the errors still have to be checked on the device.

## CMA on the device, and the swiotlb message

On station-work-91 (`65549ff5`, boot `50572be9`) the kernel reserved 256 MiB of CMA at
0xf0000000, and `CmaTotal` read 262144 kB. With Umbriel, blur, foot and qutebrowser running,
about 192 MiB stayed free. There were no `CREATE_DUMB` failures, and the owner reported
"Smooth now".

Twice around qutebrowser's start, the OVL logged that the swiotlb buffer was full for a
4 MiB mapping. Our reading, not traced: the compositor imported a client's GPU buffer to try
scanning it out directly. The display has no IOMMU here, so the OVL keeps the default 32-bit
DMA mask. A shmem page above 4 GiB then has to bounce, and a 4 MiB segment is larger than
swiotlb can bounce, so the mapping fails. Without an IOMMU the OVL can only scan out
contiguous memory, and this import would fail anyway. The compositor then composites the
buffer instead, which matches "no visible effect". The message is harmless until the display
gets its IOMMU (M4U). We leave the DMA mask alone: nothing here shows the OVL can reach past
4 GiB in the loader's bypass.

## What stands before upstream

An independent review of the display and lid patches found these, not changed here
because none affects the station and nothing boots until they are retested:

- **Off has no single owner.** The VT hold in 0515 does not hold against `KDSETMODE`, a
  console switch, `TIOCL_UNBLANKSCREEN`, an oops's console unblank or a DRM restore.
- **0503** uses the clock-provider API from consumer drivers, reads MMSYS gates on every
  SoC, and has a bisect hazard before 0507. `IRQF_NO_AUTOEN` may remove the need for both.
- **0502 and 0507's device tree** deletes required properties and omits required panel
  ones, and the backlight link exists only through `station-dt.sh`.
- **0513's pointer** has no lifetime guarantee, and it takes the first raw backlight.
- **0507** mixes binding, device tree and driver, and holds the MM root permanently.
- **Form.** No sign-offs, a placeholder author, fixups to squash into their parents, and
  the subject prefix should be `Input: gemini-lid -`.
- **The mode.** 146667 kHz with these totals gives a nominal 57.1 Hz in a mode whose code
  name says 60, against a measured 54.00 Hz. The clock is chosen for the lane rate.

## Follow-up

T6 is not started. Durable facts are in
[display and panel](../../docs/hardware/display-panel.md) and demonstrated support in
[HARDWARE_SUPPORT](../../docs/HARDWARE_SUPPORT.md).
