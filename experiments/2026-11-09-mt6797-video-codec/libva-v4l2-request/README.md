# VA-API on mt6797-vdec: libva-v4l2_request patches

This directory makes the VA-API driver
[libva-v4l2_request](https://github.com/live-display/libva-v4l2_request)
(GPL-3.0-or-later, pinned to `cac6ece`, 2026-07-15) usable with the
`mt6797-vdec` stateless decoder. The goal is hardware H.264, HEVC and VP9
decoding in stock Arch Linux ARM mpv and qutebrowser.

Status: built and unit-tested off the device. Nothing has run on the Gemini
yet. H.264 and HEVC need a kernel with mt6797-vdec patch 0744; see
[Driver requirement](#driver-requirement-on-demand-capture-buffers).

## Driver selection on the Gemini card

libva loads the driver named after the render node's kernel driver, so on
the card it looks for `panfrost_drv_video.so`. `gemini-base` (59 onward)
ships that name as a symlink to `v4l2_request_drv_video.so` and depends on
this package. No `LIBVA_DRIVER_NAME` is needed there. This package installs
only `v4l2_request_drv_video.so`; adding the symlink here would conflict
with `gemini-base`. Elsewhere, set `LIBVA_DRIVER_NAME=v4l2_request`.

## What the patches change

`0001-Detile-MediaTek-MM21-on-the-CPU-into-dma-buf-heap-NV.patch`

- mt6797-vdec outputs only MM21 (16x32 luma tiles, 16x16 CbCr tiles, two
  planes). Nothing can display it, and MT6797 has no converter device.
- The driver now detiles MM21 on the CPU into linear NV12.
- Each surface's NV12 buffer comes from `/dev/dma_heap/system`. It is
  exported as a dma-buf like any other NV12 surface.
- `vaEndPicture` waits for the decode and the conversion. Chromium never
  calls `vaSyncSurface`, so the frame must be ready when `vaEndPicture`
  returns.
- `vaDeriveImage` and `vaGetImage` (`--hwdec=vaapi-copy`) read the NV12
  buffer.
- Surfaces exported before their first decode get the same layout, so
  their dma-buf stays valid. Chromium exports each surface once and keeps
  it.

`0002-Gate-HEVC-Main-10-and-VP9-profile-2-on-the-profile-m.patch`

- The driver no longer advertises HEVC Main 10 or VP9 profile 2 when the
  decoder's profile menu stops below them. mt6797-vdec is 8-bit only.
- `vainfo` should list H.264 Constrained Baseline, Main and High, HEVC
  Main, and VP9 Profile 0. MPEG-2, VP8 and AV1 are not listed, because the
  decoder does not offer them.

`0003-Pass-the-full-plane-array-when-queueing-decode-buffe.patch`

- The driver gave `VIDIOC_QBUF` and `VIDIOC_DQBUF` a one-entry plane array.
  MM21 CAPTURE buffers have two planes, so vb2 rejected every CAPTURE
  queue and dequeue with `EINVAL`. Found on the first device run (V16).

`0004-Ask-for-cached-CAPTURE-buffers-when-the-CPU-detiles-.patch`

- vb2 maps CAPTURE buffers uncached on this SoC. Detiling a 1080p frame
  from them took about 50 ms on the A72 (V17), against about 7 ms for the
  hardware decode. The driver now requests
  `V4L2_MEMORY_FLAG_NON_COHERENT` for MM21 buffers. It needs mt6797-vdec
  patch 0748, which allows that hint; on older kernels the flag is
  ignored.

`0005-Optionally-export-MM21-surfaces-tiled-for-zero-copy-.patch`

- With `LIBVA_V4L2_REQUEST_MM21_EXPORT=1` there is no CPU detile.
  Surfaces export the decoder's two MM21 planes as `DRM_FORMAT_NV12` with
  `DRM_FORMAT_MOD_MTK_16L_32S_TILE`, one dma-buf per plane at offset 0.
  Mesa Panfrost (26.2) imports that modifier and detiles on the GPU.
- Opt-in, because:
  - VA-API has no modifier negotiation;
  - the importer may detile a buffer only once, so clients that keep one
    image per surface (Chromium, so qutebrowser) can show stale frames;
  - `vaDeriveImage` and `vaGetImage` (mpv `--hwdec=vaapi-copy`) cannot
    read tiled surfaces.
- Use it with mpv `--hwdec=vaapi` on an OpenGL (EGL) output.
- It needs a Mesa with the Panfrost fix that detiles all MTK tile rows
  ([patch](../../2026-11-02-mali-t880-first-job/mesa/0001-panfrost-detile-all-MTK-tile-rows-on-Midgard-and-Bifrost.patch)). With stock Mesa 26.2.6 only a
  band at the top of each frame is detiled (V19). With the fix, frames are
  pixel-identical to the CPU detile (V20).

## Permission for the dma-buf heap

The NV12 buffers come from `/dev/dma_heap/system`, which the kernel creates
as root-only. Without access, decoding fails ("cannot open
/dev/dma_heap/system: Permission denied"). A udev rule gives the logged-in
user access, for example `/etc/udev/rules.d/70-dma-heap.rules`:

    SUBSYSTEM=="dma_heap", KERNEL=="system", TAG+="uaccess"

The file name must sort before systemd's `73-seat-late.rules`.

The codec paths needed no other change:

- H.264: the driver already reads the decode-mode and start-code control
  defaults. It picks frame-based mode and Annex-B, and sends SPS, PPS,
  scaling matrix and decode parameters. It does not send slice parameters
  or prediction weights in frame mode.
- HEVC: frame-based mode and Annex-B, as for H.264. It sends SPS, PPS,
  decode parameters, the scaling matrix and up to 64 slice parameters. All
  of these controls exist in mt6797-vdec. `EXT_SPS_ST_RPS` is absent, so
  HEVC is not declined.
- VP9: when `V4L2_CID_STATELESS_VP9_COMPRESSED_HDR` is missing, it sends
  only the frame control, with the whole frame in the OUTPUT buffer.

## Build

On the Gemini, or in an Arch Linux ARM aarch64 chroot:

```
makepkg -si
```

The package is `libva-v4l2-request-mt6797`. It installs
`/usr/lib/dri/v4l2_request_drv_video.so`.

## Select the driver

```
export LIBVA_DRIVER_NAME=v4l2_request
```

The driver scans every `/dev/media*` for a request-API decoder. To pin it
to one node, set `LIBVA_V4L2_REQUEST_MEDIA_PATH=/dev/mediaN`.

The user needs access to `/dev/video*`, `/dev/media*` and
`/dev/dma_heap/system`. The kernel needs `CONFIG_DMABUF_HEAPS_SYSTEM=y`.

Check that it loads:

```
vainfo --display drm --device /dev/dri/renderD128
```

The driver logs to stderr with the prefix `libva-v4l2request:`. During
playback it should print `converting MM21 to NV12 on the CPU`.

## mpv

```
LIBVA_DRIVER_NAME=v4l2_request mpv -v --hwdec=vaapi FILE
LIBVA_DRIVER_NAME=v4l2_request mpv -v --hwdec=vaapi-copy FILE
LIBVA_DRIVER_NAME=v4l2_request mpv -v --hwdec=vaapi --vo=dmabuf-wayland FILE
```

- `--hwdec=vaapi` imports the NV12 dma-buf into the GPU.
- `--hwdec=vaapi-copy` copies frames back to memory. Use it to separate
  decode problems from display problems.
- mpv prints `Using hardware decoding (vaapi)` (or `vaapi-copy`).
- Keep streams within 1920x1088: H.264 (Baseline, Main, High), HEVC Main,
  and VP9 profile 0.

## qutebrowser

Arch Linux ARM ships qt6-webengine 6.11.3, which is based on Chromium 140.
In that version the decoder features are on by default. Listing them does
no harm.

```
LIBVA_DRIVER_NAME=v4l2_request \
QT_LOGGING_RULES="qt.webenginecontext.debug=true" \
QTWEBENGINE_CHROMIUM_FLAGS="--enable-features=AcceleratedVideoDecoder,AcceleratedVideoDecodeLinuxGL,AcceleratedVideoDecodeLinuxZeroCopyGL,VaapiIgnoreDriverChecks --enable-logging=stderr --vmodule=vaapi_wrapper=4,vaapi_video_decoder=4,video_decoder_pipeline=4" \
qutebrowser
```

- Chromium 140 has no `VaapiVideoDecoder` feature. Its Linux switch is
  `AcceleratedVideoDecoder`.
- Do not add `--use-gl=egl`. QtWebEngine's default ANGLE-on-GL path is the
  one VA-API decode uses.
- `--ignore-gpu-blocklist` should not be needed.
- First check that the browser was built with VA-API:
  `grep -c vaExportSurfaceHandle /usr/lib/libQt6WebEngineCore.so.6` should
  print a number above 0.

To confirm hardware decoding:

- The startup log should show `Using GBM: yes`, and no
  `AcceleratedVideoDecoder` in the disabled features.
- `qute://gpu`, under "Video Acceleration Information", should list H264,
  HEVC and VP9 decode profiles.
- During playback, `chrome://media-internals` should show a platform
  decoder (`VaapiVideoDecoder` or `VideoDecoderPipeline`), not FFmpeg or
  libvpx.
- stderr should show the `libva-v4l2request:` lines.
- `ls -l /proc/$(pgrep -f qutebrowser | head -1)/fd` should show
  `/dev/video*` and `/dev/media*`. QtWebEngine runs the GPU code inside the
  browser process (`--in-process-gpu`).

`0006-Report-the-decoder-s-real-maximum-surface-size.patch`

- The driver advertised a 4096x4096 maximum surface for every config.
  Chromium builds its supported-size list from that, so it would pick
  VA-API for 1440p or 4K streams that mt6797-vdec (1920x1088 at most)
  rejects only when the decode context is created. The driver now reports
  the largest size the decoder gives through `VIDIOC_ENUM_FRAMESIZES`.

## Driver requirement: on-demand capture buffers

The backend creates one CAPTURE buffer per surface on demand, with
`VIDIOC_CREATE_BUFS`, also after `STREAMON`. Pools can hold more than 17
buffers. Until patch 0744, mt6797-vdec handled neither case for H.264 and
HEVC: it allocated motion-vector buffers only at `STREAMON` and used the
buffer index, capped at 17, as the hardware slot. VP9 was not affected.

[Patch 0744](../../../patches/proposals/0744-media-mediatek-mt6797-vdec-support-capture-buffers-c.patch)
allocates each motion-vector buffer when its capture buffer is created and
maps pictures to hardware slots 0 to 16. Use a kernel that contains it.

## Tests

All tests ran off the device:

- **Detiler vs. hardware.** The 30 frames of the H.264 352x288 MM21
  capture from the card were detiled by `test/test-mm21.c` (linked with
  the patched `src/mm21.c`). Their I420 MD5s match the ffmpeg framemd5,
  30/30. The capture is private evidence and is not included here.
- **Detiler vs. address formula.** Random data at nine sizes and paddings
  matched a per-pixel address formula with 0 mismatches. Sizes:
  1920x1080 (1088 and 1152 rows), 1280x720 (736, 768), 854x480 (pitch 864
  and 896), 1918x1078, 352x288 (pitch 384) and 176x144.
- **Detiler vs. Python reference.** Random frames at 1920x1080, 854x480,
  1918x1078 and 1280x722 match the reference Python detiler.
- **Speed.** 1080p took about 67 µs per frame from cache, and about
  250 µs with 32 frames cycled to defeat the cache. Both ran on the dev VM
  (aarch64 on an Apple host, gcc -O2). The Gemini's A72 reads uncached
  decoder memory far more slowly; expect a few milliseconds.
- **Build.** Ubuntu 24.04 (libva 2.20, gcc 13) built with no warnings.
  An Arch Linux ARM chroot (libva 2.24.1, libdrm 2.4.134, gcc 16.1)
  built the package with `makepkg`.
- **Loading.** In the chroot, `vainfo` with the installed package:
  - loaded the driver with `LIBVA_DRIVER_NAME=v4l2_request`;
  - with the `visl` test decoder, listed its profiles;
  - with no V4L2 device, failed cleanly: "no V4L2 Request API decoder
    found", `vaInitialize` returned an error, and there was no crash.

Not tested:

- Any decode through the software converter. The dev VM has no MM21
  decoder, and `visl` outputs NV12.
- Patch 0002. `visl` has no profile menus.
- The EndPicture wait, dma-buf sync, and GPU import of the heap NV12
  buffer by Panfrost or ANGLE.
- mpv, ffmpeg and qutebrowser themselves.

Rebuild the detiler test against a patched source tree `$SRC`:

```
gcc -O2 -I "$SRC/src" -o test-mm21 test/test-mm21.c "$SRC/src/mm21.c"
./test-mm21 check 1920 1080 1920 1088
./test-mm21 detile W H PITCH PADDED_HEIGHT <frames.mm21 | python3 test/i420md5.py W H ref.framemd5
```
