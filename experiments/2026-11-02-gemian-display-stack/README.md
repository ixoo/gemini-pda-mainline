# Experiment: Gemian display stack audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-02-gemian-display-stack` |
| Status | `completed` offline source audit |
| Subsystem | Internal panel, DSI, MMSYS/DDP, Gemian graphics userspace, Mali GPU relationship |
| Device variant | Named Gemini PDA (MT6797X) running Gemian |
| Date | 2026-11-02 |
| Investigator | Repository maintainer with OpenCode assistance |
| Device access | None |

## Question

How does the working Gemian stack drive the internal display panel end to end,
including the userspace compositor path and any connection between the Mali GPU
and the panel?

## Provenance and method

This audit reads public Gemian kernel and userspace source and reconciles it
with the retained read-only captures already recorded by this repository. No
device was booted or contacted, no DSI/GPIO/I2C/display state was changed, and
no mainline image was built.

Pinned inputs:

| Input | Revision |
| --- | --- |
| Gemian kernel | `d388d350cb2dda8f23b99be6fa5db9628896e87f` |
| Planet LK | `f4988d74bb70a0a15d7f362f412afba7e7fcda46` |
| Planet vendor reference tree | `c5b0be85017ad0c599725e8273842efdbecdd88a` |
| `xf86-video-hwcomposer` | `163cd71436416f4303a99c292aab85354f1f67f8` (0.3.9+gemian1) |
| `libhybris` | `9cbda6a9250530d73680cddbfbda29f267619b35` |
| `glamor-hybris` | `6d369b94e8cc858587eb510af7bc97f6a3c1a453` |
| `drihybris` | `d275fa5d57cb6a659da0a76a2d9a9e3eeee56b1a` |
| `gemian-multistrap-config` | `a9646f2c2facaf991faa9cce6158245cb5dacbe7` |
| Reference-docs archive | `0e299d6ed1ffad41deebd4d84a7cb5edfa5ea638` |

The sources were fetched into Git-ignored storage on the development machine.
The detailed source-to-fact mapping is in
[`results/source-audit-20261102.txt`](results/source-audit-20261102.txt).
Existing private captures were not re-read; only the sanitized results already
committed to this repository were used.

## Safety assessment

Read-only. No device operation, no partition access, no firmware execution, no
DSI transaction and no display state change. The audit only reads public source
and retained sanitized summaries.

## Associated code

None. This record adds no executable analysis; the reproducible source-to-fact
mapping is [`results/source-audit-20261102.txt`](results/source-audit-20261102.txt).

## Findings

### 1. Kernel path

`mtkfb` registers an fbdev framebuffer, publishes the framebuffer memory as an
ION heap, and exposes private `MTKFB_*` ioctls. The active display route is
`OVL0/OVL1 -> OVL0-2L -> OVL1-2L -> COLOR0 -> CCORR -> AAL -> GAMMA -> OD ->
DITHER -> RDMA0 -> PATH0 -> UFOE -> DSI0`, serialised by display mutex 0 and
normally programmed through CMDQ. This matches the earlier retained register
capture.

### 2. Panel contract

The hybris defconfig selects only
`aeon_nt36672_fhd_dsi_vdo_x600_xinli`, with `DISP_OPT_USE_DEVICE_TREE=0`. The
driver describes a 1080 x 2160, four-lane, RGB888, burst-video DSI panel with
vertical timings 3/15/10, horizontal timings 10/42/42, a 440 MHz PLL request and
an ESD `0x0A -> 0x9C` check. Reset is an MMSYS `0x150` write (pin 180 muxed to
`LCM_RST`), not a GPIO descriptor. Bias is GPIO 60/251 plus LP3101 writes
`0x00=0x0F`, `0x01=0x0F` at I2C1 `0x3E`. Suspend sends `0x28`, then `0x10`.

### 3. Cold-boot handoff

LK's target builds both the NT36672 and SSD2092 LCM drivers and selects one by
`compare_id`; its `tag_videolfb` carries the framebuffer base, `islcmfound`,
`fps`, VRAM size and selected LCM name but no separate "inited" field. The
kernel sets `is_lcm_inited = 1` whenever that tag is present, so `mtkfb` takes
the LCM name and the "already initialised" state from LK. `disp_lcm_init()`
then skips the kernel's `init_power()` and init table. The full
reset/bias/init sequence is the resume/recovery path. Gemian therefore depends
on LK's panel/LCM state at cold boot.

The identity gate is not closed by this handoff: LK's SSD2092 compare function
returns success unconditionally in this tree, and the kernel's own
`compare_id()` is unconditional in a non-bootloader build.

### 4. Userspace path

Gemian's `xorg.conf` selects `Driver "hwcomposer"` at depth 24 with rotation
left commented out. The DDX sets `EGL_PLATFORM=hwcomposer`, opens the vendor HWC
module through libhybris, starts a minimal SurfaceFlinger helper when needed,
and uses a GLES2 renderer to draw the X root texture into a gralloc-backed EGL
window. The window allocates RGBA8888 buffers with
`GRALLOC_USAGE_HW_COMPOSER|GRALLOC_USAGE_HW_FB` and two buffers. On
`eglSwapBuffers()` the DDX places the buffer in the HWC framebuffer-target layer
and calls `prepare`/`set`; HWC programs `mtkfb`.

### 5. GPU relationship

The Mali-T880 is a separate MFG island with its own MMU and `/dev/mali0`. The
Kbase driver imports dma-buf allocations; the display side maps the same
allocations into M4U/SMI. There is no `iommus` link from the Mali node and no
GPU client in the M4U port table. The GPU is a renderer only: it writes gralloc
buffers, and the display controller scans them out. GPU/display coordination is
limited to buffers, fences and GED performance hints.

### 6. Reconciled uncertainties

- The selected NT36672 driver is not a direct silicon identification; the
  bsg100 unit's SSD2092 SEEPROM evidence keeps panel identity open.
- The kernel scans 1080 x 2160 portrait while the UI is landscape. No kernel
  consumer of `CONFIG_MTK_LCM_PHYSICAL_ROTATION` was found; the DDX rotation
  option is off. The rotation stage is unresolved and is above the kernel.
- The requested 440 MHz PLL, the retained timings and the vendor `5405` debug
  value do not establish a measured refresh rate.
- The vendor HWC module version and its overlay-vs-GPU policy are not retained;
  the live register dump is consistent with direct OVL scanout of a single
  full-screen layer.

## Conclusion

`confirmed` for the source-level stack and the panel/backlight contract on the
pinned Gemian revisions; `unresolved` for physical panel identity, the exact
rotation stage, refresh rate and vendor HWC composition policy. The durable
facts are in [Gemini display and panel path](../../docs/hardware/display-panel.md).
No mainline runtime result is claimed.

## Follow-up

- Durable document: [Gemini display and panel path](../../docs/hardware/display-panel.md).
- Existing work linked from that document: panel recovery, MMSYS routing, DRM
  component recovery, input/backlight, display H2.
- Next discriminating hardware observation, in priority order: controlled DSI
  readback or panel SEEPROM capture on the named unit; a captured HWC log that
  shows display attributes and layer composition; a measured frame interval.
- Mainline work remains the standard DRM/DSI/panel + PWM backlight + dma-buf
  path; the vendor FB/HWC ABI must not be reproduced.
