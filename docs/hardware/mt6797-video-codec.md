# MT6797 video codec hardware

The MT6797 has three video blocks: a multi-format decoder (VDEC), an H.264/HEVC
encoder (VENC) and a ClearMotion frame-rate converter (MJC). This page records
their established resources, the vendor control model and the mainline gap.
Evidence, chronology, file identities and the staged plan are in the
[video codec record](../../experiments/2026-11-09-mt6797-video-codec/README.md).

Status on mainline: a prototype V4L2 stateless decoder (`mt6797-vdec`,
local) decodes HEVC Main 8-bit and progressive H.264 (Baseline, Main, High)
bit-exact on test clips. VP9 and the
encoder have no driver; players need a VA-API bridge. Bring-up diagnostics also showed the
hardware works:

- the VDEC power domain, clocks and interrupt behave as described;
- a register replay of the vendor sequence decoded an HEVC picture
  bit-exactly, with physical buffers
  ([Stage 1 and 3a](../../experiments/2026-11-09-mt6797-video-codec/README.md#stage-3a-replay-one-hevc-picture-on-mainline-v9-passed-2026-11-11)). On Gemian, the vendor stack's hardware
HEVC decode has been observed working on the named unit
([V5](../../experiments/2026-11-09-mt6797-video-codec/README.md#v5-vendor-hevc-decode-on-gemian-2026-11-11)).

## Resources

Sources: Gemian kernel `8cfe6596`, the vendor `mt6797.dtsi` and drivers; the
public MT6797 functional specification (96Boards publication, pp. 275 to 286)
and register table (part 2, sections 4.7 and 4.8; part 1, TOPRGU).

| Block | Registers | GIC SPI | Domain (SPM `PWR_CON`, status bit) | Clocks | Larb and M4U ports |
| --- | --- | --- | --- | --- | --- |
| VDEC | GCON `0x16000000`; core `0x16020000` (MISC), `+0x1000` VLD, `+0x1800` VLD_TOP, `+0x2000` MC, `+0x3000` AVC_VLD, `+0x4000` AVC_MV, `+0x5000` PP, `+0x6800` VP8_VLD, `+0x7800` VLD2, `+0x8000` HEVC_VLD | 240 | VDE `0x10006300`, bit 7 | `vdec_sel`; gates `vdec_cken`, `vdec_active`, `vdec_cken_eng`, `vdec_larb1_cken` | larb1 `0x16010000` (SPI 241), ports 0 to 9 |
| VENC | GCON `0x17000000`; core `0x17002000` | 235 | VEN `0x10006304`, bit 21 | `venc_sel`; gates `venc_0` to `venc_3` | larb3 `0x17001000` (SPI 236), ports 0 to 4, 9 to 14 |
| JPEG enc, dec | `0x17003000`, `0x17004000` | 237, 239 | VEN | `venc_0` with `venc_2`, `venc_3` | larb3 ports 5 to 8 |
| MJC | config `0x12000000` (SPI 244); top `0x12001000` | 243 | MJC `0x10006310`, bit 20 | `mjc_sel` (UNIVPLL/5 or IMGPLL); six MJCSYS gates; two MMSYS larb4 ASIF gates | larb4 `0x12002000` (SPI 242), ports 0 to 3 |

- All three domains are children of MM and need SMI common; the vendor parents
  them on their muxes and adds no bus protection.
- Resets: TOPRGU `0x10007018` bit 4 (VDEC), bit 3 (VENC), bit 13 (MJC); VDEC
  GCON `+0x10` (sub-system) and `+0x14` (larb).
- VDEC interrupt: GCON `+0x0` bit 4 means busy; MISC `+0xA4` bit 16 means decode
  done; clear by setting `0x11` and then clearing `0x10` in MISC `+0xA4`.
- VENC interrupt: status `+0x05C`, acknowledge `+0x060`; SPS `0x1`, PPS `0x2`,
  frame `0x4`, DRAM `0x8`, pause `0x10`, switch `0x20`, VPS `0x80`.
- The specification asks for 500 MHz VDEC and SMI clocks; the vendor raises the
  MMDVFS (Vcore) step while decoding. Observed on Gemian: `vdec_sel` at 338 MHz
  from VDECPLL; `venc_sel`, `mjc_sel` and `mm_sel` at 325 MHz.
- Linux interrupt numbers under Gemian: GIC 272 (VDEC), 267 (VENC), 275 (MJC).
  The vendor HEVC decode raised one VDEC interrupt per picture for both
  single-slice and four-slice pictures, and its register trace shows one
  decoder start per picture.
- After the VDEC domain powers on, LARB1's per-port MMU enable (`+0xFC0`)
  reads `0x3ff`: all ten decoder ports translated. Without an IOMMU driver it
  must be cleared for physical addresses.
- Decoder output is MediaTek MM21 (`V4L2_PIX_FMT_MM21`): 16x32 luma tiles,
  16x16 interleaved-CbCr tiles, chroma in a separate buffer. This is
  bit-exact with a software decode of the same frame
  ([V6](../../experiments/2026-11-09-mt6797-video-codec/README.md#v6-hevc-register-traces-and-a-decoded-frame-2026-11-11)).
- Reference chroma: with `MC+0xB5C = 1` the motion compensation takes each
  reference's chroma address from its own table (P list `MC+0xB60`, B lists
  and HEVC L0/L1 `MC+0xBE0` and `MC+0xC60`), next to the luma tables
  (`MC+0x3DC`, `+0x45C`, `+0x4DC`). Without it, H.264 derives reference
  chroma from luma plus one offset, which fails when the planes are
  allocated apart
  ([V11, V12](../../experiments/2026-11-09-mt6797-video-codec/README.md#v12-result)).

Open: which of `venc_0` and `venc_1` clocks larb3 (vendor references
disagree); whether VENC and MJC SRAM power up without their muxes running.

## Capabilities

Per the public specification: decode of MPEG-1/2, MPEG-4 ASP, DivX/Xvid,
H.263/Sorenson, H.264 CBP/MP/HP, HEVC Main up to level 5, VC-1/WMV9, VP8 and
VP9 up to 4096x2160 at 30 fps, output in MediaTek block-tiled NV12; encode of
H.264 High up to 1080p60 and HEVC Main up to 2160p30. Gemian's codec
configuration limits all decoders to 1920x1088 and adds eFuse gating from the
`dev_info` capability bits read by the vendor library; on the named unit those bits
leave HEVC, above-1080p, DivX 3.11 and MJC enabled. The vendor decoder selects
its hardware path for VP8, VP9 and VC-1 as well; hardware decode is
demonstrated only for HEVC and H.264 so far.

## Vendor control model

- The kernel driver (`/dev/Vcodec`, `mediatek,mt6797-vdec_gcon`) only locks,
  powers, waits for interrupts and maps register windows to userspace. The MJC
  driver (`/dev/MJC`) is similar, with ioctl register access.
- `libvcodecdrv.so` in the Android container parses bitstreams and programs
  the codec registers directly through those mappings. VP8, VP9, VC-1 and some
  encoders also load MediaTek software codec libraries.
- There is no coprocessor and no firmware file. The VENC rate-control program
  (16448 bytes per variant) is embedded as data in `libvcodecdrv.so`. The SCP
  runs a sensor-hub program unrelated to video.
- Gemian's Debian side, as captured, had no hardware decode bridge (no
  `droidmedia` or `gst-droid`).

## Mainline coverage

| Present (Linux 7.1.3 plus local series) | Missing |
| --- | --- |
| VDEC, VENC, MJC domains in `mtk-scpsys`; VDECSYS, VENCSYS, MJCSYS gates; the three muxes; SMI common and larbs 1, 3, 4 (disabled); M4U with matching port IDs (disabled); TOPRGU VDEC and VENC reset IDs | any VDEC, VENC or MJC node, binding or driver; a TOPRGU ID for the MJC reset; hardware proof of SMI and M4U; MDP for de-tiling |

The upstream `mtk-vcodec` MT8173 decoder uses the same VDEC sub-block map and
the same interrupt handling, and its encoder the same interrupt layout. Every
upstream configuration hands per-frame programming to VPU or SCP firmware,
which MT6797 does not have. A mainline decoder would be a new AP-driven
stateless V4L2 driver reusing upstream's resource and V4L2 plumbing. MJC has no
upstream equivalent.
