# Gemini display and panel path

Scope: the internal 5.99-inch panel on the named Gemini PDA (MT6797X) as driven
by the working Gemian stack, the userspace compositor path around it, and the
relationship between the panel and the Mali-T880 GPU. Boot artwork is covered
separately in [boot graphics](boot-graphics.md); touch is covered in
[touchscreen](touchscreen.md).

This document describes the vendor stack that currently works. It is not a
claim that the mainline DRM/panel path is enabled; that status remains in the
[support matrix](../HARDWARE_SUPPORT.md) and [roadmap](../ROADMAP.md).

## 1. Summary

- The panel's logical scan is **1080 x 2160, single-DSI, four-lane,
  burst-video**. Gemian's kernel selects the vendor
  `aeon_nt36672_fhd_dsi_vdo_x600_xinli` LCM driver by name from the
  bootloader handoff. The physical controller identity is still an open gate;
  see section 2.1.
- The display controller is the MediaTek **MMSYS/DDP** block
  (`OVL -> ... -> RDMA -> DSI0`), not DRM/KMS. The kernel exposes it through
  **fbdev `mtkfb`** plus private MediaTek ioctls.
- Gemian's X server uses the **`hwcomposer` Xorg driver**. It hands a
  gralloc/ION buffer to the vendor **`hwcomposer.mt6797.so`** HAL through
  **libhybris**. The HAL programs `mtkfb`; `mtkfb` programs DDP and DSI0.
- The **Mali-T880 GPU is not connected to the panel or the DSI link**. It
  renders Xorg and application content into dma-buf/gralloc memory. The display
  controller scans that memory out. GPU and display meet only at shared
  buffers and synchronisation fences.
- The backlight is **display PWM0**, reached through the Android lights HAL and
  the kernel `lcd-backlight` LED class.
- Gemian's cold boot normally inherits an already-initialised panel from the
  retained Planet LK; the kernel's own full reset/bias/init sequence is used on
  resume and recovery.

## 2. Panel and DSI link

### 2.1 Selected driver and identity caveat

| Fact | Value | Confidence |
| --- | --- | --- |
| Selected LCM driver | `aeon_nt36672_fhd_dsi_vdo_x600_xinli` | `observed` in the running vendor kernel |
| Hybris kernel config | `CONFIG_CUSTOM_KERNEL_LCM="aeon_nt36672_fhd_dsi_vdo_x600_xinli"` | `confirmed` in `aeon6797_6m_n_hybris_defconfig` |
| Device-tree LCM selection | `DISP_OPT_USE_DEVICE_TREE=0`; the LCM name normally comes from the LK/chosen `videolfb` tag | `observed` + source |
| Inactive tree alternative | `r63419_wqhd_truly_phantom_2k_cmd_ok` dual-DSI description | `confirmed` in the board DTS, not the active path |
| Physical controller identity | NT36672 is the selected driver, not a direct silicon read on the named unit | `unresolved` |

The kernel-side `compare_id()` returns success unconditionally; only the
bootloader build reads NT36672 page registers `0xDB`/`0xF4` and expects
`0x8070`. LK's target builds both the NT36672 and SSD2092 drivers and selects
one by `compare_id`, then passes the selected name through `tag_videolfb`. The
SSD2092 compare function in this LK tree also returns success unconditionally
(its `0xA1` read is compared but both branches return 1), so LK's selection is a
boot-time hint, not an identity proof. The Gemian kernel builds only the NT36672
driver, so a working boot constrains the LK/kernel combination rather than the
panel silicon.

An independent Gemini unit examined by the bsg100 project read SEEPROM words
for an AUO 5.99-inch SSD2092 panel. The two units may not share a panel, so the
named unit's physical controller remains unproven. Do not enable a mainline
panel descriptor as hardware-proven until a controlled DSI readback or SEEPROM
capture exists on this unit.

See the [panel recovery record](../../experiments/2026-07-11-gemini-panel-recovery/README.md)
and the [bsg100 cross-check](../../experiments/2026-07-13-bsg100-gemini-linux-comparison/results/bsg100-panel-crosscheck-20260714.txt).

### 2.2 Link and timing contract

| Property | Value |
| --- | --- |
| Logical frame | 1080 x 2160 |
| DSI links | one, DSI0 |
| Lanes | four |
| Pixel format | packed RGB888 |
| Video mode | burst video, CMDQ enabled, low-power clock between lines |
| Vertical timing | sync 3, back porch 15, front porch 10, active 2160 |
| Horizontal timing | sync 10, back porch 42, front porch 42, active 1080 |
| DSI PLL request | 440 MHz; host derives `data_rate = PLL_CLOCK * 2` (880 Mbit/s per lane) |
| SSC | disabled |
| ESD check | DCS `0x0A` must return `0x9C` |

The live retained dump reports a 435 MHz MIPI TX clock and a 1088-pixel
framebuffer stride at 32 bpp. The 440 MHz value is a downstream D-PHY input,
not a DRM pixel clock. The vendor debug field reports `5405` where `6000` means
60.00 Hz, and mainline at these settings measures 54.00 flips per second.

### 2.3 Reset, bias and power sequence

The active path does not use a reset GPIO descriptor. The vendor
`lcm_set_reset_pin()` writes `LCM_RST_B` directly at MMSYS offset `0x150`;
pin 180 is muxed to the `LCM_RST` hardware function. The board DTS pinctrl
low/high states exist but are not the active branch.

Power-on on resume/recovery:

1. drive reset low;
2. enable positive bias (GPIO 60), then negative bias (GPIO 251);
3. wait 20 ms;
4. write `0x0F` to LP3101 registers `0x00` and `0x01` at I2C1 address `0x3E`;
5. drive reset high for 10 ms, low for 10 ms, then high for at least 20 ms;
6. send the panel-specific initialisation table.

Suspend:

1. DCS `0x28` (display off), wait 50 ms;
2. DCS `0x10` (sleep in), wait 120 ms;
3. disable the bias enables.

The vendor LCM has no regulator consumer and no panel-supply phandle:
controllable power is the LP3101 bias device plus the two GPIO enables. The
LP3101 register values are observed writes, not a datasheet-backed voltage
contract. A mainline panel/bias implementation must not assume TPS65132
semantics merely because a similar I2C address/register shape exists.

### 2.4 Initialisation and suspend commands

The active initialisation branch contains the panel vendor command table
(167 vendor commands in the mechanical comparison) across pages `0x10`,
`0x20`, `0x21`, and `0x24`-`0x27`. The tail is decisive:

| Command | Value | Meaning |
| --- | --- | --- |
| `0x51` | `0xFF` | display brightness |
| `0x53` | `0x24` | write CTRL display (backlight/display control) |
| `0x55` | `0x00` | content adaptive brightness off |
| `0x36` | `0x03` | MADCTL: row/column order bits |
| `0x11` | `0x00` | sleep out, then 120 ms |
| `0x29` | `0x00` | display on, then short delay |

Suspend sends only `0x28`, delay 50 ms, `0x10`, delay 120 ms. The ESD table
reads `0x0A` and expects `0x9C`; the generic DSI ESD machinery and
`disp_recovery.c` provide the recovery policy.

### 2.5 Backlight

The board DTS marks the `lcd-backlight` LED as `led_mode = <5>`, which is
`MT65XX_LED_MODE_CUST_BLS_PWM`. The callback is `disp_bls_set_backlight()`:
the display PWM block (`DISP_PWM0` at `0x1100f000`) with a 10-bit level
(0-1023). The kernel LED class exposes `/sys/class/leds/lcd-backlight/brightness`;
the 0-255 sysfs level is scaled to the internal 10-bit value.

In Gemian, Xorg's hwcomposer driver opens the Android lights HAL
(`LIGHT_ID_BACKLIGHT`) and writes the brightness on DPMS transitions.
`repowerd` and the Android power/display policy can also use the same LED
class; the kernel remains the single owner of PWM0.

## 3. Kernel display controller

### 3.1 Framebuffer and memory

`mtkfb` registers an fbdev framebuffer and publishes the framebuffer memory as
an ION heap (`ion_drv_create_FB_heap()`). The live device reports:

```text
name=mtkfb
virtual=1088x4320, bpp=32, stride=4352 bytes, pages=2
active=1080x2160
```

The private `MTKFB_*` ioctls create/configure display sessions, set overlay and
video layers, exchange fences, power the display, and return interface
information. These are the interfaces the vendor HWC HAL uses; they are not an
upstream ABI.

### 3.2 DDP path

The retained active route is:

```text
OVL0 -> OVL0-2L -> OVL1-2L -> COLOR0 -> CCORR -> AAL -> GAMMA ->
OD -> DITHER -> RDMA0 -> PATH0 -> UFOE -> DSI0
```

`OVL0` and `PWM0` are controlled alongside the path, but the vendor route
connector skips `OVL0`; `OVL0 virtual` and `PATH0` are routing pseudo-components.
`UFOE` is physically present but the live `START` value selects bypass. The live
layer format word `0x010020ff` is the MT8173-generation encoding of DRM
`ABGR8888` with byte swap and alpha enable.

Display mutex 0 (`0x1401f000`, SPI 202) serialises the path. Its live module
mask decodes to OVL0, both OVL-2L blocks, RDMA0, COLOR0, CCORR, AAL, GAMMA, OD,
DITHER, UFOE and PWM0, with DSI0 SOF/EOF selected. Register programming normally
runs through the GCE/CMDQ; the live display gates are prepared in the MM power
domain and report 325 MHz, while the DSI interface gate reports rate zero (a
normal downstream-gate report).

The full resource map, register chain and contract checks are in the
[MT6797 live resource map](mt6797-live-resource-map.md), the
[MMSYS routing record](../../experiments/2026-07-12-mt6797-mmsys-routing-recovery/README.md),
and the [DRM component record](../../experiments/2026-07-12-mt6797-drm-component-recovery/README.md).

### 3.3 Memory path and fences

Gralloc allocates the scanout buffers from ION. The vendor HWC/gralloc code
imports the handles, configures the M4U display ports, and supplies MediaTek
virtual addresses to `mtkfb`; OVL/RDMA consume those addresses through the
display SMI ports (LARB0/LARB5). Buffer completion uses the vendor
`/dev/swsync`/sync fence path. The display side therefore sees memory, not a
GPU surface.

### 3.4 Power states

`MTKFB_POWEROFF` calls `primary_display_suspend()`; `MTKFB_POWERON` calls
`primary_display_resume()`. The HWC blank/power path reaches these through the
fbdev interface. Suspend runs the panel sleep sequence and turns the bias off;
resume runs the full reset/bias/init sequence. `mtkfb` also implements the PM
suspend/resume callbacks and the ESD/recovery machinery.

### 3.5 Cold-boot ownership

LK's `tag_videolfb` carries the framebuffer base, `islcmfound`, `fps`, VRAM
size and the selected LCM name; it has no separate "inited" field. The kernel
sets `is_lcm_inited = 1` whenever that tag is present. `disp_lcm_init()` then
skips `init_power()` and the initialisation table, and the kernel continues from
LK's panel state. The kernel's own reset/bias/init path is exercised on resume
and recovery. This inherited state is a compatibility assumption: LK's panel
configuration and the kernel's command table must agree. A mainline boot that
replaces LK must initialise the panel itself.

## 4. Gemian userspace path

### 4.1 Xorg display driver

Gemian's `/etc/X11/xorg.conf` selects:

```text
Driver "hwcomposer"
```

with `DefaultDepth 24`; the `Rotate` option is present but commented out. The
installed package is `xserver-xorg-video-hwcomposer` 0.3.9 (Gemian 1). The DDX:

1. sets `EGL_PLATFORM=hwcomposer`;
2. loads the Android HWC module with `hw_get_module("hwcomposer")` through
   libhybris and opens the primary display;
3. starts a minimal SurfaceFlinger helper (`libminisf.so`) when the vendor HWC
   expects that binder service; it does not hand the desktop to Android's full
   SurfaceFlinger;
4. creates a gralloc-backed EGL window and a GLES2 renderer;
5. renders the X root texture and presents it with `eglSwapBuffers()`.

The driver supports the HWC 1.x `prepare`/`set`/`blank` API and a 2.x path for
other devices. The Gemini path uses the 1.x API; the exact vendor module
version is not retained, but Android 7.1 headers imply 1.5 (inferred).

### 4.2 libhybris and buffer flow

libhybris provides the bionic/glibc bridge and loads the vendor EGL/GLES
libraries (`libEGL.so`, `libGLESv2.so`, backed by `libGLES_mali.so`) with
`android_dlopen`. Its `hwcomposer` EGL platform allocates buffers through
`gralloc.mt6797.so`:

```text
format = HAL_PIXEL_FORMAT_RGBA_8888
usage  = GRALLOC_USAGE_HW_COMPOSER | GRALLOC_USAGE_HW_FB
count  = 2 (double buffered)
```

`eglSwapBuffers()` queues the buffer, and the DDX `present()` callback fills the
HWC `HWC_FRAMEBUFFER_TARGET` layer with that handle, calls
`prepare`/`set`, and propagates the release fence. The steady-state path is
therefore: **Mali renders -> gralloc buffer -> HWC -> mtkfb -> DDP -> DSI ->
panel**. `glamor-hybris` gives Xorg accelerated 2D through the same EGL/GLES
stack; `drihybris` is the DRI3 buffer-sharing fallback.

The DDX's `hwc_set_power_mode()` maps DPMS off/on to HWC power mode
(`blank` on 1.x), and `hwc_toggle_screen_brightness()` uses the lights HAL.
The vendor HWC HAL itself is the component that turns the layer list into
`mtkfb` session/layer ioctls, which program DDP; its internal overlay-vs-GPU
composition policy is proprietary and not retained. The live mtkfb dump shows
the OVL path active, which is consistent with a single full-screen X layer
being scanned out directly.

### 4.3 Android container

Gemian runs Android 7.1.1 in an LXC container for HALs and services. The
retained process inventory includes `surfaceflinger`, `cameraserver` and
`sensorservice`; the Android graphics stack uses the same vendor
`gralloc.mt6797.so`, `hwcomposer.mt6797.so` and `libGLES_mali.so`. The Xorg DDX
starts its own minimal SurfaceFlinger helper when needed, so the observed
Android process should not be read as proof that Android owns the panel during
normal Gemian desktop use. Which component owned the display in each captured
session is not established.

HAL identities retained from the read-only userspace inventory:

| Path | SHA-256 |
| --- | --- |
| `system/vendor/lib/hw/gralloc.mt6797.so` | `284766e8cb607f9efca69dd399b2abb5f60481f79ed5efdda0249a13d874b691` |
| `system/vendor/lib/hw/hwcomposer.mt6797.so` | `7d80da7c016104c3cff18846dfd2170a17c4b4548a8ed970ae5332a50292f273` |
| `system/vendor/lib64/hw/gralloc.mt6797.so` | `29fb68a36eb098f86b5ddae1b0f265fae803b717445748c29f94c5376a7a082d` |
| `system/vendor/lib64/hw/hwcomposer.mt6797.so` | `7994b769a4966a3060f18844fafad14939b53e3ddec073e3a32816bc8498a22c` |

## 5. GPU connection

The GPU is a Mali-T88x MP4 (product `0x0880`, Panfrost model `t880`). It is a
separate MFG power/clock island at `0x13040000` with its own MMU and its own
job/MMU/GPU interrupts (SPI 264/263/262). The vendor kernel runs Kbase r12p1
(`mali midgard r12p1`) and exposes `/dev/mali0`; the vendor userspace uses
`libGLES_mali.so`.

**There is no GPU-to-panel or GPU-to-DSI connection.** The evidence is:

- the Mali DT node has no `iommus` phandle and its own MMU interrupt;
- the MT6797 M4U port table has display, MDP, video, camera and MJC clients but
  no GPU client;
- the MMSYS routing graph has no GPU input; its sources are OVL/RDMA memory
  ports;
- the display registers and the MFG registers are separate apertures
  (`0x14000000` display vs `0x13040000` GPU).

The GPU's connection to the display is indirect and consists of:

1. **Buffers** - gralloc/ION allocations exported as dma-buf. Kbase imports a
   dma-buf with `dma_buf_get()`/`dma_buf_attach()` and maps it through the GPU
   MMU; the display side maps the same allocation into the M4U/SMI address
   space.
2. **Fences** - Android sync fences (`/dev/swsync`, acquire/release fence FDs)
   order GPU rendering against HWC scanout.
3. **Performance hints** - the vendor HWC/GED interface supplies GPU/display
   frequency and VSync hints through `/proc/ged`; this changes DVFS, not pixel
   routing.

In Gemian's desktop path the GPU is the **renderer**: glamor-hybris and the DDX
renderer thread draw with GLES2 into the gralloc window buffer, and the display
controller scans that buffer out. The GPU never drives DSI, the panel reset,
the bias rails or the backlight. A GPU failure can therefore blank or corrupt
content, but it cannot change the panel's link state.

The GPU-side power, clock, DVFS and Panfrost plan is in the
[Mali-T880 record](mali-t880.md).

## 6. Mainline mapping

| Gemian boundary | Standard replacement | Current state |
| --- | --- | --- |
| `mtkfb` fbdev + private ioctls | MediaTek DRM/KMS (`mtk_drm`, OVL, RDMA, mutex, DSI) | [A test frame reached the panel](../../experiments/2026-11-02-gemini-native-display/README.md) from modules on the station |
| Vendor LCM driver | DRM panel driver with DSI timings, reset GPIO, bias supplies, backlight | Gemini descriptor adopts the loader's panel state and sends nothing; the driver's own power and init path has not run |
| `MTKFB_POWEROFF/ON` and ESD | DRM modeset, panel prepare/enable, ESD work | Not exercised on the station |
| ION + M4U + sw_sync | dma-buf heaps, IOMMU, dma-fence | CMA with the larbs in bypass scans out; display IOMMU remains open |
| Vendor HWC + libhybris + Xorg DDX | Mesa/Panfrost + DRM/KMS compositor | Panfrost renders into display buffers through dma-buf and they reach the panel; no compositor yet |
| `lcd-backlight` + PWM0 | `pwm-backlight`/DRM backlight with PWM0 | H2/H8 work prepared; not the default |

The mainline display work is tracked by the
[native display experiment](../../experiments/2026-11-02-gemini-native-display/README.md)
and the [support matrix](../HARDWARE_SUPPORT.md).

Read on the named unit, from a running panel, on both the Gemian kernel and the
mainline station: `PLL_CON2` `0x43b13b13` (880 Mbit/s), `TIMCON0-3` `0x080f0708
0x10280c20 0x0a280100 0x00102406`, word counts 28/148/116, VSA/VBP/VFP 3/15/10,
`TXRX_CTRL` `0x1003c`, `LCM_RST_B` 1 with GPIO180 in its `LCM_RST` function. The
measured refresh under mainline at those settings is 54.00 Hz.

## 7. Confidence and unresolved questions

| Question | Current position |
| --- | --- |
| Physical panel controller | `observed`, not complete: under mainline DCS `0x0a` reads `0x9c` and `0xdb` reads `0x80`, as the NT36672 path expects and unlike the SSD2092 unit's `0x0a` = `0x1c`. `0xf4` was not read. The vendor kernel's table, byte-identical to the mainline descriptor's, runs on this unit on every Gemian boot |
| Panel bias device semantics | `observed` writes only; LP3101 voltages/currents unproven |
| Landscape rotation stage | `observed` - held in landscape, the panel scans 1080x2160 rotated 90 degrees with no mirror: lines run top to bottom, the first at the right edge. Which stage rotates under Gemian is unresolved |
| Refresh rate | `observed` - 54.00 flips per second under mainline at the vendor's lane rate and porches, agreeing with the vendor's `5405` debug field |
| Vendor HWC composition policy | Proprietary; not retained. The live OVL path is consistent with direct scanout of the X framebuffer |
| Cold-boot panel initialisation | Kernel sets `is_lcm_inited` from the presence of LK's `videolfb` tag and inherits LK's panel state; exact per-session state not captured |
| Android SurfaceFlinger vs Xorg ownership | Android services were observed, but the DDX's mini-SF helper exists; per-session ownership not established |

## 8. Evidence index

- [Gemian display stack audit](../../experiments/2026-11-02-gemian-display-stack/README.md)
- [Panel recovery experiment](../../experiments/2026-07-11-gemini-panel-recovery/README.md)
- [MMSYS routing recovery](../../experiments/2026-07-12-mt6797-mmsys-routing-recovery/README.md)
- [DRM component recovery](../../experiments/2026-07-12-mt6797-drm-component-recovery/README.md)
- [Input and backlight recovery](../../experiments/2026-07-12-input-backlight-recovery/README.md)
- [Display H2](../../experiments/2026-10-06-gemini-display-h2/README.md)
- [Vendor kernel ABI](vendor-kernel-abi.md) and [vendor userspace](vendor-userspace.md)
- Pinned Planet LK `f4988d74bb70a0a15d7f362f412afba7e7fcda46`:
  `lk/project/k97v1_64_bsp.mk`, `lk/platform/mt6797/atags.c`,
  `lk/platform/mt6797/mt_disp_drv.c`, and the `aeon_nt36672`/`aeon_ssd2092`
  LCM directories.
- Pinned Gemian kernel `d388d350cb2dda8f23b99be6fa5db9628896e87f`:
  `drivers/misc/mediatek/lcm/aeon_nt36672_fhd_dsi_vdo_x600_xinli/`,
  `drivers/misc/mediatek/gpio/lp3101.c`,
  `drivers/misc/mediatek/video/common/mtkfb.c`,
  `drivers/misc/mediatek/video/mt6797/dispsys/ddp_dsi.c`,
  `drivers/misc/mediatek/video/mt6797/dispsys/ddp_ovl.c`,
  `drivers/misc/mediatek/video/mt6797/videox/disp_lcm.c`,
  `drivers/misc/mediatek/video/common/aal20/ddp_pwm.c`,
  `drivers/misc/mediatek/leds/mt6797/leds.c`,
  `drivers/gpu/arm/mali` and `drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p1/`.
- Gemian userspace `xf86-video-hwcomposer` `163cd71436416f4303a99c292aab85354f1f67f8`,
  `libhybris` `9cbda6a9250530d73680cddbfbda29f267619b35`,
  `glamor-hybris` `6d369b94e8cc858587eb510af7bc97f6a3c1a453`,
  `drihybris` `d275fa5d57cb6a659da0a76a2d9a9e3eeee56b1a`,
  `gemian-multistrap-config` `a9646f2c2facaf991faa9cce6158245cb5dacbe7`.
