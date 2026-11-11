# Experiment: MT6797 video decoder, encoder and MJC, what they offer and what using them takes

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-09-mt6797-video-codec` |
| Status | `completed` (offline source, configuration and binary analysis, plus one read-only vendor decode on Gemian, V5; no mainline build or boot) |
| Subsystem | VDEC, VENC, MJC; their power domains, clocks, SMI larbs, M4U ports and userspace stack |
| Device variant | Named Gemini PDA (MT6797X); retained Gemian `3.18.41+` captures |
| Date(s) | 2026-11-08 |
| Investigator(s) | Repository maintainer with Claude Code assistance |
| Tracking issue | Not assigned |

## Question

Mainline has no MT6797 video decoder, so the Arch card's mpv decodes in
software. The owner asked: identify the relevant elements of the MT6797 video
hardware and how to use them. Concretely:

1. Which register windows, interrupts, clocks, power domains, larbs, IOMMU ports
   and resets do the decoder (VDEC), encoder (VENC) and frame-rate converter
   (MJC) use, and which of these mainline already describes?
2. How does Gemian drive them: which kernel interface, which userspace
   libraries, and is there a coprocessor or firmware?
3. What would a mainline driver need, which upstream driver is closest, and
   what should be brought up first?

This record adds no code, DT node, candidate or device action.

## Provenance and environment

- Gemian GPL kernel
  [`8cfe6596a503612e3332d9c26e292a19525a7f07`](https://github.com/gemian/gemini-linux-kernel-3.18/tree/8cfe6596a503612e3332d9c26e292a19525a7f07):
  the MT6797 `videocodec` and `mjc` drivers, the vendor `mt6797.dtsi`, the
  clock and power-gate drivers, the M4U and SMI drivers. Read from Git objects
  in the RE VM.
- The Android root that Gemian's LXC container runs, `/data/system.img` inside
  the private `linux` partition capture of 2026-07-15, read with `debugfs -c`
  in the RE VM. The retained `scp1` and `tee1` partition images were scanned
  for strings.
- The retained Gemian Debian root in the same capture (its `dpkg` status and
  library directories), for the userland-bridge question.
- Linux 7.1.3 with the local series in `patches/series` (clock, scpsys, SMI,
  M4U, TOPRGU reset and `mtk-vcodec` sources).
- The public 96Boards publication of the MT6797 functional specification and
  register table, cited by page.

Exact file names, sizes and SHA-256 values are in
[`results/vendor-identities.md`](results/vendor-identities.md). No vendor
source, binary, configuration file or document text is copied here.

## Safety assessment

Read-only and offline. No device was accessed; every device observation
proposed below is a proposal for the device custodian, not something run here.
Captures were read without mounting or replaying their journals. Binaries were
inspected with `readelf`, `nm` and `strings` only; nothing was loaded or
executed. Private extracts stay in the RE VM's private work directory.

## Associated code

None.

## Procedure

1. Export the vendor video, MJC, SMI, M4U, clock and DT sources at the pinned
   commit and read the MT6797 paths.
2. Locate the Android root in the `linux` partition capture, copy it into the
   RE VM, and extract only `etc`, `vendor/etc`, the codec libraries and the two
   codec tools.
3. Summarise the codec configuration; list each library's dependencies,
   imports, exported symbols and strings.
4. Scan the SCP and TEE images for any video firmware.
5. Read the matching chapters of the public specification and register table.
6. Compare every resource with the local Linux 7.1.3 tree and with the upstream
   `mtk-vcodec` driver and its MT8173 DT.

## Observations

### 1. Blocks and resources

From the vendor DT, drivers and the public specification (Functional
Specification pp. 275 to 286; Register Table part 2 section 4.7):

| Block | Registers | IRQ (GIC SPI, level low) | Power domain | Clock gates and muxes | SMI larb, M4U ports |
| --- | --- | --- | --- | --- | --- |
| VDEC_GCON | `0x16000000` (0x10000) | none | VDEC | gate register for `vdec_cken`, `vdec_active`, `vdec_cken_eng` (`+0x0` set, `+0x4` clear) and `vdec_larb1_cken` (`+0x8`, `+0xc`) | - |
| VDEC core | `0x16020000` MISC, `0x16021000` VLD, `0x16021800` VLD_TOP, `0x16022000` MC, `0x16023000` AVC_VLD, `0x16024000` AVC_MV, `0x16025000` PP, `0x16026800` VP8_VLD, `0x16027800` VLD2, `0x16028000` HEVC_VLD | 240 | VDEC | `vdec_sel` (topckgen `0x0050` bits 8 to 10), `vdec_cken`; spec gives 500 MHz for both `vdec_clk` and `smi_clk` | larb1 `0x16010000`, IRQ 241; ports 0 to 9: MC, PP, UFO, VLD, VLD2, AVC_MV, PRED_RD, PRED_WR, PPWRAP, TILE |
| VENC_GCON | `0x17000000` (0x1000) | none | VENC | gates `venc_0` (bit 0, parent `mm_sel`), `venc_1` (bit 4), `venc_2` (bit 8), `venc_3` (bit 12), the last three from `venc_sel` | - |
| VENC core | `0x17002000` (0x1000) | 235 | VENC | `venc_sel` (`0x0050` bits 16 and 17), `venc_1` | larb3 `0x17001000`, IRQ 236; ports 0 to 4 and 9 to 14 (RCPU, REC, BSDMA, SV_COMV, RD_COMV, CUR/REF luma/chroma, NBM RDMA/WDMA) |
| JPEG enc / dec | `0x17003000` / `0x17004000` | 237 / 239 | VENC | `venc_0` plus `venc_2` / `venc_3` | larb3 ports 5 to 8 |
| MJC config | `0x12000000` (0x1000) | 244 | MJC | six gates `mjc_smi_larb`, `mjc_top_clk_0..2`, `mjc_fake_engine`, `mjc_larb4_asif` | - |
| MJC top | `0x12001000` (0x1000) | 243 | MJC | `mjc_sel` (`0x0090` bits 24, 25) from UNIVPLL/5 (250 MHz) or IMGPLL (450 MHz); MMSYS gates `mm_larb4_axi_asif_mm`/`_mjc` | larb4 `0x12002000`, IRQ 242; ports 0 to 3: MV_RD, MV_WR, DMA_RD, DMA_WR |

Power domains are SPM `PWR_CON` registers `0x10006300` (VDE), `0x10006304`
(VEN) and `0x10006310` (MJC), with status bits 7, 21 and 20 and SRAM power-down
fields 8/12, 8-11/12-15 and 8/12. Vendor power-gate code adds no bus
protection for these three; it parents them on `vdec_sel`, `venc_sel` and
`mjc_sel` respectively. The vendor vcodec node also holds the DIS (MM) domain
and `MM_SMI_COMMON` whenever VDEC or VENC is on.

Resets: TOPRGU `WDT_SWSYSRST` (`0x10007018`) bit 4 resets VDEC, bit 3 VENC and
bit 13 MJC (Register Table part 1). VDEC_GCON `+0x10` and `+0x14` are
sub-system and larb reset registers. The specification's software reset is
VLD register 66 bit 0.

Interrupt handling (vendor ISR and specification p. 281): the VDEC ISR first
checks VDEC_GCON `+0x0` bit 4 (engine active) and MISC `+0xA4` bit 16 (decode
done), then clears through MISC register 41 (`+0xA4`): set bits `0x11`, then
clear bit `0x10`. The CPU does not clear the interrupt directly. VENC status is
at `+0x05C` and acknowledge at `+0x060`, with SPS `0x1`, PPS `0x2`, frame `0x4`,
DRAM `0x8`, pause `0x10`, switch `0x20`, VPS `0x80`; `+0x0A8` is a soft reset
and `+0x0AC` a pause.

### 2. The vendor kernel driver is a lock and power service

`drivers/misc/mediatek/videocodec/mt6797/videocodec_kernel_driver.c` binds to
`mediatek,mt6797-vdec_gcon` and creates `/dev/Vcodec` (character major 160).
It contains no codec logic. It:

- maps `mediatek,mt6797-vdec`, `-venc` and `-vdec_gcon`, requests SPIs 240 and
  235, and keeps both disabled until a client locks the hardware;
- lets userspace `mmap` four physical windows, uncached: VDEC
  `0x16000000`..`0x16029000`, VENC `0x17002000` (4 KiB), `0x10000000` (4 KiB,
  topckgen) and `0x07FFF000` (8 KiB), plus its own non-cached buffers;
- provides ioctls with magic `'M'`: `VCODEC_LOCKHW` (`0x0d`) and
  `VCODEC_UNLOCKHW` (`0x33`), `VCODEC_WAITISR` (`0x0b`), `VCODEC_INITHWLOCK` /
  `DEINITHWLOCK` (`0x20`, `0x21`), non-cached buffer allocation (`0x22`, `0x23`),
  power and EMI user counts (`0x15` to `0x18`, `0x27`, `0x28`), CPU loading and
  OPP hints (`0x29` to `0x32`);
- has one decoder lock and one encoder lock. Locking the decoder powers VDEC
  (DIS domain, SMI common, VDE domain, `vdec_cken`, `vdec_larb1_cken`) and
  enables its IRQ; the H.264 and HEVC encoder types power VENC; JPEG encode
  takes the encoder lock without powering VENC here. The decoder lock covers
  MPEG-4, H.264, HEVC, MPEG-1/2, VC-1 and VP8/VP9 driver types. Locks are never
  stolen; a waiter times out;
- raises the MMDVFS step (`SMI_BWC_SCEN_VP`) while VDEC is busy, from a 4 s
  load monitor;
- loads no firmware.

`drivers/misc/mediatek/mjc/v1.0/mjc_kernel_driver.c` binds to
`mediatek,mjc_top-v1`, creates `/dev/MJC`, and offers ioctls with magic `'N'`:
`MJC_LOCKHW`, `MJC_WAITISR`, `MJC_READ_REG`/`WRITE_REG` (range checked to the
MJC window), register tables, `MJC_SOURCE_CLK` and `MJC_REG_INFO`. Opening it
enables the MJC domain and eight gates and configures the four larb4 M4U ports
with fault callbacks. `MJC_SOURCE_CLK` selects UNIVPLL/5 for 60 fps output and
IMGPLL with a high MMDVFS step for 120 fps output.

### 3. Userspace programs the codec registers

All codec work runs on the application processor, in the Android container:

| Layer | Component | Role |
| --- | --- | --- |
| Android media | `libstagefright`, `libstagefrighthw.so`, `MtkCodecService` | OMX client and MediaTek codec service |
| OMX components | `libMtkOmxVdecEx.so`, `libMtkOmxVenc.so` (`mtk_omx_core.cfg`) | one component per format; up to 16 instances; secure AVC/HEVC variants |
| Codec driver | `libvcodecdrv.so` (32- and 64-bit) | per-format parsing and register programming; exported HAL functions such as `H264_HAL_SetSPSAVLD`, `H264_HAL_SetPPSAVLD`, `H264_HAL_SetSHDRAVLD1`, `H264_HAL_SetPRefPicListReg`, `H264_HAL_WriteMC`/`WritePP`/`WriteVLD`, `H265_HAL_DecStart`, `VP9_HAL_ReadMC` |
| Kernel glue | `libvcodec_utility.so`, `libvcodec_oal.so` | opens `/dev/Vcodec`, `mmap`s the windows, wraps lock, ISR wait, power and register writes (`VCodecDrvRegSyncWrite*`) |
| Software codecs | `lib*_sa.ca7.so`, `libHEVCdec_sa.ca7.android.so` | NEON and thread code with no hardware imports, opened by `libvcodecdrv.so` |
| MJC | `libClearMotionFW.so` (linked by the decoder OMX), `libmjc.so`, `libmjcFakeEngine.so` | ClearMotion algorithm in software; `libmjc` drives `/dev/MJC` and the M4U |

- `libvcodecdrv.so` contains 64 `H264_HAL_*` exports and many HEVC, VP9 and VP8
  ones. Its build path string names `libvcodec/mt6797`.
- It embeds the VENC rate-control processor code as data:
  `ucH264RCPUCode_6797`, `ucWFDH264RCPUCode_6797`, `ucVILTEH264RCPUCode_6797`
  and HEVC variants, 16448 bytes each. No separate firmware file exists.
- It reads `/proc/device-tree/chosen/atag,devinfo` and the `dev_info` platform
  driver, and logs `HEVC disabled by eFuse`, `4K disabled by eFuse`,
  `Over 1080p disabled by eFuse`, `DIVX disabled by eFuse`; on a read failure it
  falls back to 1080p for encode and 720p for decode.
- It opens software libraries for VP8, VP9 and VC-1 decode and for H.264
  (`_sa`, `_sb`), MPEG-4 and VP8 encode, and names `libhevce_sc.ca7.so`,
  which is not in the image.
- `libMtkOmxVdecEx.so` reads `/proc/svp_region` for secure playback.
- `vendor/bin/mfv_ut` is a MediaTek codec test tool that links the decoder
  entry points (`eVDecDrvCreate`, `eVDecDrvDecode`, ...) directly.

### 4. Capabilities

| Function | Public specification | Gemian codec configuration |
| --- | --- | --- |
| Decode | MPEG-1/2, MPEG-4 ASP, DivX 3 to 6 and Xvid, Sorenson H.263 and H.263, H.264 CBP/MP/HP, HEVC Main up to level 5, VC-1/WMV9, VP8, VP9; up to 4096x2160 at 30 fps | HEVC, MPEG-4, H.263 (to 1408x1152), AVC, VP8, VP9, VC-1, DivX, DivX3, Xvid, S263 (FLV1); all limited to 1920x1088; adaptive playback for HEVC, MPEG-4, H.263, AVC, VP8, VP9 |
| Decode output | NV12 in MediaTek block (tiled) layout, frame or field-compact | - |
| Encode | H.264 High at level 4.2 to 1920x1088 at 60 fps; HEVC Main at level 5.0 to 3840x2176 at 30 fps | AVC to 1920x1080, HEVC to 3840x2176; MPEG-4 and H.263 only 176x144; VP8 to 1280x720 |
| Encode input | NV12/NV21, YV12/I420 or MediaTek block | - |
| MJC | ClearMotion | input 256x120 to 1920x1088 at 12 to 35 fps, output 120 fps |

### 5. No coprocessor firmware

No firmware file is loaded for VDEC, VENC or MJC. The only processor code is
the VENC rate-control blob inside `libvcodecdrv.so`. The SCP image is a
FreeRTOS sensor and DVFS program with no video strings; the TEE image has none
either.

### 6. What mainline already has

| Resource | Linux 7.1.3 plus local series |
| --- | --- |
| VDEC, VENC, MJC power domains | upstream `mtk-scpsys` MT6797 data; offsets, status and SRAM bits match the vendor; VDEC takes `CLK_TOP_MUX_VDEC`, VENC and MJC take no clock; all three are children of MM |
| VDECSYS, VENCSYS gates | upstream `clk-mt6797-vdec.c`, `clk-mt6797-venc.c`; gates and parents match the vendor |
| MJCSYS gates, MMSYS larb4 ASIF gates | local patch 0022 (MJC) and upstream `clk-mt6797-mm.c` |
| `vdec_sel`, `venc_sel`, `mjc_sel` | upstream `clk-mt6797.c`, same registers and parents |
| SMI common, larbs 0 to 6 | local patches 0023 to 0025; larb1 (VDEC), larb3 (VENC), larb4 (MJC) nodes exist, all `disabled` |
| M4U | local patch 0024, `mediatek,mt6797-m4u`; port IDs in `mt6797-larb-port.h` match the vendor table; node `disabled` |
| TOPRGU resets | upstream `MT6797_TOPRGU_VDEC_SW_RST` (4) and `MT6797_TOPRGU_VENC_SW_RST` (3); no ID for MJC bit 13 |
| VDEC, VENC, MJC devices | none: no DT node, compatible or driver |

On the station the display scans out of physical CMA buffers through larbs in
bypass, with no SMI driver and no M4U bound
([native display](../2026-11-02-gemini-native-display/README.md)). The camera
receiver likewise bypasses larb2 by hand. The M4U and SMI patches are
therefore compiled but not yet proven on hardware.

### 7. Upstream `mtk-vcodec` and the MT8173

- The MT8173 decoder node uses the same register map: MISC `0x16020000`, LD
  `0x16021000`, TOP `0x16021800`, CM `0x16022000`, AD `0x16023000`, AV
  `0x16024000`, PP `0x16025000`, HWD `0x16026800`, HWQ `0x16027000`, HWB
  `0x16027800`, HWG `0x16028400`, with VDECSYS at `0x16000000` and larb1 at
  `0x16010000`. The MT6797 adds an HEVC VLD at `0x16028000`.
- Upstream's decoder interrupt handler uses the same active bit (VDEC_SYS `+0x0`
  bit 4) and the same clear sequence (MISC `+0xA4`, `0x11` then `0x10`).
- Upstream's encoder uses the same status and acknowledge offsets (`0x05C`,
  `0x060`) and status bits. The MT8173 H.264 encoder sits at `0x18002000`.
- Every upstream configuration delegates bitstream parsing and register
  programming to firmware: on MT8173 to the VPU (`mediatek,mt8173-vpu`, TCM at
  `0x10020000`, configuration at `0x10050000`, firmware
  `mediatek/mt8173/vpu_d.bin` and `vpu_p.bin`), on MT8183 and later to the SCP
  through `mtk_scp` (`mediatek/<soc>/scp.img`), stateless or stateful.
- On MT6797 those two addresses belong to the SCP, which runs the sensor hub
  program above. The vendor stack does not use it for video.
- Upstream `mtk-jpeg` (`mediatek,mt8173-jpgdec`, `mediatek,mtk-jpgenc`) and
  `mtk-mdp` (MT8173 RDMA, RSZ, WDMA, WROT) exist; neither has MT6797 data.
- MJC has no upstream counterpart: no V4L2 or DRM driver for a hardware
  frame-rate converter of this kind exists.

### 8. Gemian's Debian side never had a decode bridge in the capture

The captured Gemian root has `libhybris`, `drihybris`, `glamor-hybris`,
`lxc-android`, `pulseaudio-module-droid`, GStreamer 1.0 base, good and bad
plug-ins, `libavcodec57`, `mpv` and VLC. It has no `droidmedia`, no
`gst-droid`, and no droid, OMX or hybris plug-in in its GStreamer directory.
The Android root has `libminisf.so` but no `libdroidmedia.so`. The live check
queued with the custodian remains the authority for the running unit.

## Analysis

**Inferred from the observations above:**

- The MT6797 VDEC is the MT8173 VDEC's register generation with HEVC and VP9
  additions; the identical sub-block map, interrupt sequence and encoder
  interrupt layout leave little doubt. The difference is the control model:
  MediaTek moved the per-frame programming from a VPU core (MT8173) into the
  application processor's userspace (MT6797). A mainline driver therefore
  inherits upstream's resource handling, V4L2 plumbing and interrupt code, but
  not its firmware interface.
- A firmware-backed route would need a new SCP program doing H.264 parsing and
  VDEC programming, next to (or instead of) the sensor-hub program. That is not
  a realistic project route. The MT8173 VPU firmware is for a different core
  type (inference; the SCP core type was not checked here) and would also
  conflict with the SCP's current owner.
- The realistic route is an AP-driven stateless V4L2 decoder, as Hantro,
  rkvdec and Cedrus do: userspace parses (the V4L2 stateless H.264 controls),
  the kernel writes VDEC registers per frame. The register contract exists only
  in `libvcodecdrv.so`. Its named, exported HAL functions make static recovery
  tractable, by the method used for the camera HAL
  ([camera HAL contract](../2026-11-04-gemian-camera-driver-re/README.md)).
  Upstream's MT8173 stateful VP8/VP9 code also writes a few VDEC registers
  from the kernel.
- The decoder writes MediaTek block-tiled NV12. Upstream V4L2 has MediaTek
  tiled formats (`MT21C`, `MM21`); whether MT6797's tile matches one of them is
  not established. Displaying the result needs a de-tiling step: MDP (not yet
  supported on MT6797), the GPU or the CPU.
- The encoder needs the 16 KiB RCPU program from `libvcodecdrv.so`. A mainline
  encoder would load it with `request_firmware` from a privately extracted
  file; its redistribution is unresolved.
- MJC is a ClearMotion interpolator with its algorithm in a proprietary
  userspace library. With no upstream API, it has little value on this panel
  and is not a candidate.
- The eFuse capability words come from LK's `atag,devinfo`. If that property
  reaches mainline, a driver can respect the same HEVC and 4K limits; otherwise
  the vendor's own fallback is 1080p encode and 720p decode.

**Contradictions and unknowns:**

- The larb3 gate is ambiguous. The vendor SMI and M4U drivers and the
  `smi_common` node clock larb3 with `venc_1`; the vendor vcodec and JPEG nodes
  call `venc_0` the larb clock and `venc_1` the encoder clock. The mainline
  clock driver parents `venc_0` on `mm_sel`, as for other larb clocks. The local
  larb3 node uses `venc_1`. A first consumer should enable both until a
  measurement separates them.
- Mainline's VENC and MJC domains have no clock, while the vendor powers them
  with `venc_sel` and `mjc_sel` running. Whether SRAM power-up acknowledges
  without those muxes is unknown.
- VP8, VP9 and VC-1 were first left open here. A later, deeper static pass
  settled them: the vendor decoder selects its hardware path for all three on
  this chip. The software libraries are reachable only through an export that
  nothing calls. That pass rests on decompiled vendor code and is kept
  private.
- The VDEC clock rate and voltage: the specification asks for 500 MHz, and the
  vendor raises the MMDVFS (Vcore) step while decoding. Mainline has no Vcore
  scaling, so the safe `vdec_sel` parent at the station's fixed Vcore is
  unknown.
- The purpose of the `0x07FFF000` window in the vendor `mmap` filter is not
  established.

## Conclusion

`confirmed`, scoped to the pinned vendor source, the retained Gemian captures
and Linux 7.1.3 with the local series:

- MT6797 has a multi-format VDEC (`0x16020000`, SPI 240, VDEC domain, larb1),
  an H.264/HEVC VENC (`0x17002000`, SPI 235, VENC domain, larb3) and an MJC
  (`0x12001000`, SPI 243, MJC domain, larb4).
- Mainline already describes their power domains, clock gates, muxes, larbs,
  M4U ports and VDEC/VENC resets. It has no device node or driver for any of
  them.
- Gemian drives them from AP userspace through `/dev/Vcodec` and `/dev/MJC`,
  with no coprocessor and no firmware file. The VENC rate-control program is
  embedded in `libvcodecdrv.so`.
- Upstream `mtk-vcodec` matches the MT6797 VDEC/VENC register layout and
  interrupt handling, but relies on VPU or SCP firmware that MT6797 lacks. A
  mainline decoder would be a new AP-driven stateless driver.

No hardware behaviour is claimed by the static analysis; V5 below adds the
first device observation.

## V5: vendor HEVC decode on Gemian (2026-11-11)

**What ran.** The device custodian ran this read-only check on Gemian boot
`56e31061` (`3.18.41+`), and the owner approved it.

- **Decode:** the vendor test tool `vendor/bin/mfv_ut`, in the Android
  container, decoded two synthetic HEVC Main clips: 352x288, 30 frames,
  generated with ffmpeg `testsrc2`. One has one slice per picture; the other
  has four slices with WPP.
- **Trace attempt:** the vendor register-trace property was set during the
  runs and reset afterwards.
- **What the tool cannot test:** `mfv_ut` has no plain H.264 decode test;
  its only H.264 test is the secure one, and that needs a library Gemian
  lacks.
- **Changes:** nothing outside the container was written.

**Observed:**

- **Device nodes:** `/dev/Vcodec` (char 160:0) and `/dev/MJC` (168:0).
- **Interrupts:** `/proc/interrupts` lists GIC 267 and 272 as `Vcodec` and
  275 as `MJC`. These are SPI 235 (VENC), 240 (VDEC) and 243 (MJC) plus 32,
  as the DT says.
- **HEVC decode:** both clips decoded completely ("success", 30 output
  buffers each). Each took under a second, and SoC temperature rose from 29.8
  to 31.3 °C.
- **Interrupt counts:** the VDEC count went from 0 to 30 for the single-slice
  clip and from 30 to 60 for the four-slice clip, so one interrupt per
  picture in both cases. VENC and MJC stayed at 0.
- **Lock timeout:** the vendor driver logs one hardware-lock timeout on its
  first lock, then proceeds normally.
- **Clocks at idle:** `vdec_sel` runs at 338 MHz from VDECPLL; `venc_sel`,
  `mjc_sel` and `mm_sel` run at 325 MHz.
- **eFuse:** in the `dev_info` capability word, the bits that the vendor
  library uses to disable HEVC, above-1080p decode, DivX 3.11 and MJC are all
  clear.
- **DEVAPC at boot:** violations on the `MJC_CONFIG` and `VDEC_GLOBAL_CON`
  slaves.
- **Gemian container:** ClearMotion is supported but off by default
  (`persist.sys.display.clearMotion=0`).

**Not obtained:**

- **Register trace:** the trace file could not be created, because the
  container's `/mnt/sdcard` points at storage that does not exist there.
- **Decoded output:** the test wrote no decoded output files.
- **VP9 and VP8:** both runs failed right after reading their configuration,
  with no interrupt. Their error text goes only to the Android log daemon,
  which the container lacks.

**Analysis:**

- **Hardware decode works:** this is the first observation of VDEC decoding
  on this unit. HEVC decode works in hardware through the vendor stack on the
  named Gemini.
- **One trigger per picture [I]:** one interrupt per picture regardless of
  slice count supports the hardware decoding a whole multi-slice picture from
  one trigger. That fits a frame-based V4L2 stateless decoder.
- **Clock rate:** the 338 MHz VDEC clock is lower than the specification's
  500 MHz and is the vendor's own working point. It is a safe first target for
  mainline.
- **DEVAPC violations:** they suggest early vendor code touching the VDEC and
  MJC control blocks while protected or unpowered. A mainline driver should
  access them only with the domain on.

**Next device run (V6):** give the trace property a writable `/mnt/sdcard`
in the container, rerun the two HEVC clips for a register trace, and
diagnose the VP9 and VP8 failures statically first. An H.264 trace needs a
small harness, since `mfv_ut` has no plain H.264 test.

## V6: HEVC register traces and a decoded frame (2026-11-11)

**What ran.** The device custodian ran this on Gemian boot `2487bfc8`
(`3.18.41+`), at the owner's choice. All changes stayed inside the container.

- **Earlier diagnosis:** before the run, static analysis had settled two V5
  failures.
  - `mfv_ut`'s VP9 and VP8 tests query the decoder with a 0x0 picture size,
    which this vendor library always refuses, so `mfv_ut` cannot test those
    codecs.
  - The HEVC test writes decoded output only when its golden-reference check
    fails.
- **Trace path:** the container's `/storage` is a tmpfs, and
  `/storage/self/primary` was a dangling symlink. Creating its target gave
  the vendor trace file somewhere to go.
- **Runs:** the two V5 HEVC clips decoded again with the trace on. One more
  run used the golden check with a missing reference, to dump frame 0.
- **Order:** the dump ran first, because the first attempt to create the
  directory failed for want of `PATH`; the traces were run after it.

**Observed:**

- **Traces:** about 13,400 register accesses for the single-slice clip and
  14,400 for the four-slice clip, over 30 pictures each.
- **One start per picture:** both traces contain exactly one decoder start
  per picture. A four-slice picture adds only three extra iterations of the
  decoder's hardware start-code scan, which locates the later slices; they are
  never programmed separately. The VDEC interrupt count rose by 30 per clip.
- **Coverage:** every register the vendor library wrote falls on a register
  or register array that the earlier static analysis had already described,
  and the constant values agree with it.
- **Frame 0:** the dump is bit-exact with the ffmpeg software decode of
  frame 0 when read as MediaTek's MM21 layout: 16x32 luma tiles, 16x16
  interleaved-chroma tiles, a separate chroma buffer, the 384x320 allocation
  cropped to 352x288. Reading it as linear NV12 does not match.
- **Device state:** no fault; SoC 28.4 → 30.5 °C; each run took under a
  second.

**Analysis.**

- **Driver mode settled:** the hardware decodes every slice of a picture
  from a single start, so a V4L2 stateless driver can work frame by frame. It
  takes the whole access unit plus the first slice's parameters, and positions
  the decoder's bit reader at the first slice header, as the vendor code does.
- **Output format settled:** `V4L2_PIX_FMT_MM21` exactly. A VA-API backend or
  MDP has to detile it to NV12 for the browser and GPU.
- **Prototype order:** the static HEVC register contract is now confirmed
  against a real decode, with no unknown registers left for this clip type.
  An HEVC-first prototype is therefore at least as well grounded as H.264.
  The register-level traces and contract stay private, because they rest on
  vendor code.

## Stage 1: VDEC resource probe (built and run 2026-11-11, V7)

**Package.** The build ran on the `buildbox` alias, chosen by the owner
because buildbox-1 to -3 were unreachable from the laptop.

- Commit `6ee24da5`, profile `mt6797-a53-station-dvfs`, modules built, 874
  patches. It carries everything else committed up to that point too.
- Job `6ee24da5…-mt6797-a53-station-dvfs-m1`, package inventory and
  `SHA256SUMS` `2d983244`; fetched and checked locally.

| File | SHA-256 |
| --- | --- |
| `Image.gz` | `50681900c5133612a7a5b59b785f43ccdf51b2f13ce71a2ddc871dda0571d2f0` |
| `mt6797-gemini-pda-station-dvfs.dtb` | `5fec0913a0f51d54f24a8484e5bb7b8bd0e017952c61a8e74fe5fd70c80232b9` |
| `clk-mt6797-vdec.ko` | `307ea6d8fcdf471ccf88d86b79d48eb9964673225b7db9393096c50750bc0acc` |
| `mt6797-vdec-probe.ko` | `7fea7bb1179fff1a8cc7dd32d1e284a5e5fdfccd622190c2e651fa1a4d0d9036` |

The DTB contains `power-domain@0` (VDEC and MM muxes), VDECSYS with
`power-domains`, and `video-codec@16020000`.

**Station facts that shaped it.** All three come from a package
configuration and a station capture.

- **Power domains:** the station uses `mtk-pm-domains`. Its DT declares
  domains one by one under `&conn_power`, each with `KEEP_DEFAULT_OFF`. On
  the 2026-11-09 capture only CONN, AUDIO, ISP and the MFG domains exist.
  MM is not modelled: it stays physically on for the display, unowned.
- **Clocks and SMI:** the newest station package
  (`9046a224`, `mt6797-a53-station-dvfs`) has the VDECSYS clock driver, SMI
  and the IOMMU off.
- **VDEC clock:** `vdec_sel` is at 338 MHz from VDECPLL, unprepared, the same
  as under Gemian.

**Changes** (proposals `0696`–`0699`, appended to `patches/series` and
`patches/series-a53-station`; new fragment
[`gemini-a53-station-vdec.fragment`](../../configs/gemini-a53-station-vdec.fragment)
in the three station profiles):

| Patch | What | Kind |
| --- | --- | --- |
| 0696 | VDEC domain in the MT6797 `mtk-pm-domains` table: PWR_CON `0x300`, status bit 7, one SRAM bank, `KEEP_DEFAULT_OFF`, as ISP was added | built-in |
| 0697 | VDECSYS clocks use runtime PM. Their gate registers sit inside the VDEC domain, so the clock core powers the domain for access, and `clk_summary` cannot read an unpowered block | module (`COMMON_CLK_MT6797_VDECSYS=m`) |
| 0698 | `mt6797-vdec-probe`: powers the domain through runtime PM and enables the VDEC core and LARB1 gates. It logs VDECSYS `+0x00`–`+0x1C` and VDEC_MISC `+0x84`, `+0xA4`, `+0xC8`, `+0xCC`, `+0x178`, counts SPI 240 for 100 ms (stops at 1000), then powers off. It refuses a VDEC clock of 0 or above 338 MHz. It writes no decoder register | module (`MTK_MT6797_VDEC_PROBE=m`), local only |
| 0699 | Station DT: the VDEC domain (clocks: VDEC and MM muxes), VDECSYS placed in it, and a decoder node (`video-codec@16020000`, SPI 240, the domain, two gates). The compatible `mediatek,mt6797-vcodec-dec` is local until a binding exists. No driver binds at boot | DT |

**Checked so far.** The series applies (863 + 4 patches) to a VM tree. The
probe, the VDECSYS clock driver and the domain table compile with `W=1`
against the dvfs package's configuration, without warnings. The station-a72
DTB builds; the dvfs DTS includes it. Checkpatch reports only the expected
warnings: the compatible is undocumented and there is no MAINTAINERS entry.
`check-repository` and the series validation pass. **Not checked:** Buildbox
build, DT schema and the device.

The release profile shares this series, so it gets the domain entry and the
DT nodes but neither module. That is harmless.

**Image.** 0696 and 0699 need a new boot2 image, so they ride the next
batched station image. The two modules then iterate without a boot.

**Device protocol (V7, for the custodian once the image is installed).**

- *Hypothesis:* with MM physically on, the VDEC domain powers on and off
  through genpd. The gates set the VDECSYS clock-enable bits. VDEC_MISC reads
  back the vendor's reset values. SPI 240 stays quiet.
- *Unique observation:* the probe's log lines and the `vdec` genpd state,
  with the display checked before and after.

Steps:

1. Identity; `pm_genpd_summary` shows `vdec off-0`; the panel shows the
   console.
2. `insmod clk-mt6797-vdec.ko`. The domain powers on once during clock
   registration, then off. Read dmesg, `pm_genpd_summary` and the `vdec_*`
   lines of `clk_summary`.
3. `insmod mt6797-vdec-probe.ko`. Read its lines, then `pm_genpd_summary`
   (`vdec` off again) and the panel.
4. `rmmod mt6797_vdec_probe`. `insmod` once more for a second, non-first
   load.

| Observation | Meaning | Next |
| --- | --- | --- |
| Domain on, both CKEN bits set, MISC readable, 0 interrupts, display intact | Resource description right | Stage 3: HEVC-first stateless prototype |
| `VDEC domain did not power on` (genpd timeout) | SRAM acknowledge or clock order differs from the vendor's | Stop; compare with the vendor sequence; no retry |
| Hang on a register read | Block not really powered or clocked | Power off and preserve evidence; no retry; rethink the DT |
| Interrupt count > 0 | Line asserted at power-on | Note it; check the MISC `+0xA4` value; module change |
| `outside 1..338000000` | Unexpected VDEC clock | No power-on happened; read `clk_summary`; rethink |
| Display disturbed | MM or a shared clock touched | `rmmod`, preserve logs, stop, tell the owner |

*Risks:* VDEC is a hardware child of MM, which genpd does not model; the
probe relies on MM being on, as it is whenever the display runs. The VDECSYS
driver's own registration is the first VDEC power cycle on mainline.

**V7 result (2026-11-11).** The device custodian ran it on station-work-101:
boot2 image from main `ac39772d` (which contains `6ee24da5`), card 32, boot
`0bad0df9`. The two modules were taken from that package with the same
hashes as above (`307ea6d8`, `7fea7bb1`). Private evidence:
`artifacts/card-32/v7-step4.txt` and `dmesg-0bad0df9-after-v7.txt`.

- **Domain registration:** at boot the `vdec` domain registered and stayed
  `off-0`.
- **Clock driver:** loading `clk-mt6797-vdec` probed VDECSYS in about 1 ms,
  and the domain was `off-0` afterwards.
- **Probe, both loads:** each load reported `vdec clock 338000000 Hz, larb
  clock 325000000 Hz`, then `VDEC domain on`. Interrupt 246 (SPI 240) fired 0
  times in 100 ms. The domain was released and back to `off-0`. Each probe
  took about 105 ms. Both loads read identical values:

  | Register | Value | Reading |
  | --- | --- | --- |
  | VDECSYS `+0x00` | `0x111` | core, active and engine clock enables set |
  | VDECSYS `+0x08` | `0x1` | LARB1 clock enable set |
  | VDECSYS `+0x10`, `+0x14` | `0x1`, `0x1` | sub-system and larb out of reset |
  | VDECSYS `+0x18` | `0x10` | DCM control |
  | VDECSYS `+0x1C` | `0x0aaaaaaa` | SRAM configuration |
  | VDEC_MISC `+0x84` | `0x0` | clock select at reset value; the vendor programs it |
  | VDEC_MISC `+0xA4` | `0x0` | no interrupt pending |
  | VDEC_MISC `+0xC8`, `+0xCC`, `+0x178` | `0xffffffff` each | every sub-module power-down bit set, the reset state the specification describes |

- **No faults:** no hang, and no new display-driver errors. Only
  `swiotlb`-full lines appeared, and they predate the test. The session
  stayed active.

**Open:**

- **VDEC mux clock: no leak; the observer caused it (V8, same boot
  `0bad0df9`).** An idle re-read had shown `vdec_sel` and `vdecpll` at enable
  and prepare count 1 with the domain `off-0`. V8 traced every `vdec_sel`
  event across an unload and reload of `clk-mt6797-vdec`.
  - **The events are balanced.** Loading the driver enables `vdec_sel` once
    through `scpsys_power_on` ← `genpd_dev_pm_attach` ← `platform_probe`, and
    the asynchronous genpd power-off disables it 2 ms later. The probe load is
    balanced too.
  - **The summary itself raises the count.** The read of `clk_summary`
    runtime-resumes the VDECSYS provider to read its gates. That powers the
    domain and enables `vdec_sel` while the summary prints, so it reports
    counts it holds itself. The same explains `vdec_larb1_cken` reading
    hardware-on.
  - **The counts balance.** The saved trace has 6 prepares, 6 enables, 6
    disables and 6 unprepares of `vdec_sel`: one cycle from the load and
    five from the `grep` of `clk_summary`. The probe trace is 1/1/1/1.
  - **Direct reads show nothing left on**, as reported by the custodian (the
    read is not in the saved files). The per-clock files show `vdec_sel` and
    `vdecpll` at 0 and 0.
  - **Rule:** with runtime-PM clock providers, judge counts from
    `/sys/kernel/debug/clk/<clk>/clk_{enable,prepare}_count`, not from
    `clk_summary`.

  The trace setup's stack triggers carried no filter of their own, so stacks
  were captured for every clock event (85k lines). This is harmless, and the
  `vdec_sel` lines were still separable. Tracefs cleanup was verified.
  Private evidence: `artifacts/card-32/v8-*.txt`.
- **Panel: no change (closed).** The owner watched a rerun on the same boot,
  `0bad0df9`: unload and reload the clock driver, load the probe (domain on
  about 0.1 s, 0 interrupts), unload it. No flicker and no blank. Afterwards
  `vdec` was `off-0` and the `vdec_sel` enable count 0.

**Analysis.** The resource description holds on mainline:

- the VDEC domain powers on and off through genpd with MM unmodelled;
- the two gates and the register windows are where the DT says;
- the decoder interrupt is quiet at power-on;
- the registers come up in the documented reset state: everything out of
  reset, sub-modules powered down.

Stage 3, a decoder prototype, can build on this. The registers the vendor
programs before decoding (the clock select and power-down masks) start from
known values.


## Stage 3a: replay one HEVC picture on mainline (built 2026-11-11, not run)

Before writing a V4L2 driver, prove the whole hardware path on mainline with
the register sequence the vendor library actually used. The V6 trace of
picture 0 of the single-slice clip (an I picture) is converted privately
into a replay blob. It holds:

- the register writes, with the three buffer addresses (bitstream,
  collocated MV buffer, output frame) relocated;
- the register reads, with the values Gemian returned;
- the bitstream chunk Gemian fed: 3786 bytes, `dumpBistream000.raw`.

The trace, the converter and the blob stay private, because they come from
vendor code.

**0716, `mt6797-vdec-replay` (module, local only):**

- loads the blob with `request_firmware()` and allocates its buffers below
  4 GiB;
- powers the VDEC domain and the two gates;
- clears the LARB1 per-port MMU enable (`+0xFC0`), so the decoder uses
  physical addresses (the station has no IOMMU);
- runs the sequence.
  - Bit-reader reads are checked exactly.
  - Other reads poll up to 2 ms for the recorded value.
  - After the start write it waits for SPI 240 and clears it as the vendor
    driver's interrupt handler does.
- logs the SHA-256 of the output planes and leaves the frame in debugfs.

It only touches the VDEC window (`0x16000000`–`0x16028FFF`) and LARB1
`+0xFC0`, and keeps the 338 MHz clock guard. It binds the same compatible as
the probe, so only one of the two is loaded at a time.

**Checked:** the converter produces 294 operations, 3 buffers and an
8544-byte blob. The module compiles with `W=1` without warnings, and 0716
applies on top of the committed series. Checkpatch shows only the expected
warnings.

**Package.** Buildbox-2 built commit `d03147b6`, profile
`mt6797-a53-station-dvfs`, with modules; the package's `SHA256SUMS` is
`06e6f16f…`, fetched and checked locally.

- `Image.gz` `3a4721d59534c67d63a946638d35e2a84ca9cb649925406ba27bb565ad6dc4b6`
- `mt6797-vdec-replay.ko` `17d5a84af6984d48de8f58e00eef44b521173c5ed5feab19bcca8f9e0192ef7a`
- The DTB (`5fec0913…`), `clk-mt6797-vdec.ko` and `mt6797-vdec-probe.ko` are
  byte-identical to the V7 build.

The image differs from the one the station runs (`34a85195…`, built from
`ac39772d`) because of other sessions' changes since then. So V9 needs this
package as a new boot2 image.

**Not checked:** device.

**Next device run (V9).** This package as the boot2 image, then 0716's module
loaded by hand.

- *Hypothesis:* the mainline VDEC, driven by Gemian's recorded sequence with
  physical buffer addresses, decodes picture 0 identically.
- *Pass:* every read matches, one decoder interrupt, and the output planes'
  SHA-256 equal Gemian's dump (`dumpY000` `5914fc2c…`, `dumpC000`
  `8e86aa52…`). If only the padding outside 352x288 differs, the detiled,
  cropped frame must still match the software reference frame 0 (MD5
  `2aa334e9…`), checked on the host from the debugfs copy.

| Observation | Meaning | Next |
| --- | --- | --- |
| Hashes equal, reads match | Hardware path proven on mainline | Stage 3b: V4L2 stateless HEVC driver computing these registers from controls |
| Reads match, no interrupt in 1 s | Decode stalled; likely DMA addressing (larb or physical address) | Read the MISC and HEVC status registers; check LARB1 MMU_EN; no retry |
| Early read mismatch (bit reader) | Bitstream not where the hardware reads it | Check buffer content and VLD window registers |
| Output differs inside 352x288 | Wrong reference or MV buffer contents, or a missing initialisation | Compare against the trace; no device change |
| Any hang or display disturbance | Stop as in V7 | Power off, preserve evidence |


## Follow-up

Durable facts: [MT6797 video codec hardware](../../docs/hardware/mt6797-video-codec.md).

### Staged plan

**Stage 0, decide whether it is worth it.** Measure what software decode costs
today: mpv on the station playing a public 1080p H.264 clip and a 720p one, with
CPU load, dropped frames and cluster frequencies recorded. If the A72 cluster
plays 1080p H.264 without drops at an acceptable power, hardware decode is
an efficiency project, not a usability one, and its priority belongs in the
roadmap.

**Stage 1, resources only (no decoding).** Prove the VDEC power and clock path
on the station without touching the display's MM resources:

- an opt-in DT profile with a disabled-by-default VDEC node: `reg` for
  VDEC_GCON and the VDEC core windows, SPI 240, `power-domains = <&scpsys
  MT6797_POWER_DOMAIN_VDEC>`, clocks `vdec_cken` and `vdec_larb1_cken` with
  `vdec_sel` held at a low parent, reset `MT6797_TOPRGU_VDEC_SW_RST`;
- a `=m` probe module, loaded by hand, that powers the domain, enables the
  gates, reads VDEC_GCON `+0x0`/`+0x8`/`+0x10`/`+0x1C` and MISC `+0xA4`, and
  powers off;
- no SMI or M4U binding yet. Like the display and camera, the first decode tests
  can use physically contiguous CMA buffers with larb1 in bypass.

A probe compatible would be local (`mediatek,mt6797-vdec-probe`); the eventual
binding would follow upstream's `mediatek,mt8173-vcodec-dec` pattern as
`mediatek,mt6797-vcodec-dec`.

**Stage 2, register contract for H.264 decode.** Recover, statically in the RE
VM, the field-level contract of the `H264_HAL_*` functions in
`libvcodecdrv.so`: soft reset, bitstream DMA and barrel shifter, SPS/PPS/slice
fields, reference lists, MC/PP buffers, trigger and completion. Record the
contract in an independently written document, not code. Cross-check offsets
against the MT8173 kernel register writes.

**Stage 3, a stateless H.264 decoder module.** A `=m` V4L2 stateless decoder
(`V4L2_PIX_FMT_H264_SLICE`) reusing upstream `mtk-vcodec` power, clock and IRQ
handling, writing VDEC registers from the kernel. First target: one public
H.264 Main-profile clip, frame CRC or checksum compared with a software
decode, then GStreamer `v4l2slh264dec` or FFmpeg `v4l2-request`. Then bind SMI
and M4U, and add the de-tiling path for display. HEVC and VP9 follow the same
pattern only after H.264 works.

**Stage 4, userspace: one VA-API backend for qutebrowser and mpv.** The owner
wants qutebrowser itself to decode in hardware, not hand videos to mpv. The
packages were checked on 2026-11-11 against the Arch Linux ARM aarch64
`extra` repository:

- `qt6-webengine` (library 6.12.0) has Chromium's VA-API decoder
  (`VaapiVideoDecoder`, `VaapiWrapper`). It loads `libva` at run time, and
  carries the `AcceleratedVideoDecodeLinuxGL`, `...ZeroCopyGL` and
  `VaapiIgnoreDriverChecks` feature switches. It has no V4L2 decoder.
  Chromium's V4L2 decode path is built only for ChromeOS, so VA-API is the
  only route into QtWebEngine.
- `ffmpeg` 9.0.2 links `libva` and has the stateful `*_v4l2m2m` decoders, but
  no V4L2 request (stateless) decoder. `mpv` 0.41.0 links `libva`.
- So a VA-API driver over the V4L2 stateless decoder serves both
  qutebrowser and `mpv --hwdec=vaapi` with stock packages.
- Bootlin's `libva-v4l2-request` has had no commit since 2019. An actively
  maintained successor,
  [live-display/libva-v4l2_request](https://github.com/live-display/libva-v4l2_request)
  (updated 2026-11), covers MPEG-2, H.264, HEVC, VP8, VP9 and AV1. Its README
  reports unpatched Firefox and mpv working through it. Chromium is not
  reported there.

What the stage needs:

- MediaTek support in that backend, or a fork of it.
- Conversion of the decoder's tiled MM21 output to linear NV12, so Chromium
  and Panfrost can import frames: CPU or GPU at first, MDP later.
- In qutebrowser, the QtWebEngine VA-API features enabled through
  `QTWEBENGINE_CHROMIUM_FLAGS`, with the driver checks ignored.
- A Greasemonkey userscript that makes YouTube offer H.264 (it reports VP9
  and AV1 as unsupported). MT6797 has no AV1 decoder, and H.264 then covers
  YouTube up to 1080p.

Chromium's acceptance of a non-Intel/AMD VA-API driver on Panfrost is the
least certain link and is tested first, once Stage 3 decodes.

**Later or not at all.** VENC (needs the RCPU blob path and its own contract),
JPEG (try upstream `mtk-jpeg` with MT6797 data, which is far smaller), MJC (no).

### Device reads proposed for the custodian (not run)

| ID | System | Read | Decision it informs |
| --- | --- | --- | --- |
| V1 | station, read only | `pm_genpd_summary` lines for `vdec`, `venc`, `mjc`, `mm`; `clk_summary` lines for `vdec`, `venc`, `mjc`, `mm_sel`; `ls /proc/device-tree/chosen` | domains registered and off; mux rates and parents; whether `atag,devinfo` reaches mainline for the eFuse limits |
| V2 | station, read only | Stage 0 measurement: mpv software decode of a public 1080p and 720p H.264 clip, CPU load, drops, frequency | whether hardware decode is worth Stages 1 to 3 |
| V3 | Gemian, read only, only if Gemian is booted for another reason | `ls -l /dev/Vcodec /dev/MJC`; `/proc/interrupts` lines for `Vcodec` and `MJC`; vcodec lines in `dmesg` | confirms the vendor binding and SPI numbers live |
| V4 | station, reviewed `=m` module (powers VDEC) | Stage 1 probe: domain status bit 7, GCON reads, clean power-off; display checked before and after | resource description correct; go to Stage 3 tests |

V4 changes power state and needs its own reviewed protocol before it runs.

### Risks

- **Display and MM ownership.** VDEC, VENC and MJC are children of the MM
  domain that the live display depends on, and SMI common is shared. Binding
  SMI or M4U can change clocks the display uses unowned. Stage 1 avoids both.
- **Bus hangs.** Reading a VDEC or larb register with its domain or gate off can
  hang the bus. The probe must read only after genpd and clock enable succeed.
- **Vcore and clock.** Running VDEC at 500 MHz without the vendor's Vcore step
  may be unstable. Start at the lowest working `vdec_sel` parent.
- **Unproven IOMMU.** M4U has never run on this station; the decoder can start
  with CMA buffers in larb bypass.
- **Scale.** Stage 2 is substantial reverse engineering, H.264 first. Write the
  contract independently; never copy vendor code.
- **Output format.** Tiled output needs conversion before display, and MDP has no
  mainline support on MT6797.
- **Encoder blob.** The RCPU program has no known redistribution right; any
  encoder path stays a private local-firmware path.
