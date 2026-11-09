# MT6797 video codec: input identities

Identities of every vendor input used by
[the video codec record](../README.md). Names, sizes and SHA-256 values only;
no vendor source, binary content, disassembly or configuration file is copied
into this repository.

## Public GPL kernel source

Gemian kernel
[`8cfe6596a503612e3332d9c26e292a19525a7f07`](https://github.com/gemian/gemini-linux-kernel-3.18/tree/8cfe6596a503612e3332d9c26e292a19525a7f07),
read from Git objects in the RE VM.

| Path | SHA-256 |
| --- | --- |
| `drivers/misc/mediatek/videocodec/mt6797/videocodec_kernel_driver.c` | `43b368561f152d56afd648fa681d106d77001a6de00ce725c9384173db6662cd` |
| `drivers/misc/mediatek/videocodec/mt6797/videocodec_kernel_driver.h` | `08cfeb0ec5703a533e651528cb1dba0654d37e1d20997ebd1560bf633f9d9af2` |
| `drivers/misc/mediatek/videocodec/include/vcodec_OAL_v2.h` | `befe5b14cb50997bfc52233b35f280fccda8a2fdd9da08c7f5c4db1bd155f751` |
| `drivers/misc/mediatek/videocodec/include/val_types_public.h` | `8f89d6607392cc8f80a9d62685cefb347a72e692b196a1a6afd7ea48c6f2842e` |
| `drivers/misc/mediatek/mjc/v1.0/mjc_kernel_driver.c` | `3e8eb0099f993db290b333c700ff679c888c64376b69331a0524980dae86a84e` |
| `drivers/misc/mediatek/mjc/v1.0/mjc_kernel_driver.h` | `e3481cbf24a474dd61b29929835c575fb50d610d3bc7026b7cbc3d3a911bae63` |
| `arch/arm64/boot/dts/mt6797.dtsi` | `eaac86c8752ebd8ddf18b831eb3bc52a08f87475a213bb521650bf95dabb3e5e` |
| `drivers/clk/mediatek/clk-mt6797.c` | `d4bc12ed162488b1df787eaf5a97364f080b0c847d57188686514b0cb11e1473` |
| `drivers/clk/mediatek/clk-mt6797-pg.c` | `4a661ed078bddaba15b7a7a2db27ca59ced8883a1b71c545bbbe24cddd64d58f` |
| `drivers/misc/mediatek/m4u/mt6797/m4u_platform.h` | `8ae0f40beafa3d01dc10b862540087c156d2647092b232fc10f379aebcc5bf8d` |
| `drivers/misc/mediatek/m4u/mt6797/m4u_hw.c` | `4a7f9481f27aece70e386aff1e42a250069cb0e330890363b3a8b85556a4b960` |
| `drivers/misc/mediatek/smi/smi_common.c` | `6848325670f80c66d508501068190245aee6aec458e8184d14901fdfac130b39` |

The retained running config of the Gemian kernel
(`artifacts/vendor-kernel/gemian-2019/running-config.gz`, private) has
`CONFIG_MTK_VIDEOCODEC_DRIVER=y`, `CONFIG_MTK_MJC_DRIVER=y`,
`CONFIG_MTK_JPEG=y`, `CONFIG_MTK_M4U=y`, `CONFIG_MTK_SMI_EXT=y` and
`CONFIG_MTK_ION=y`.

## Android system image

Source: the private 2026-07-15 partition capture. The Android root used by
Gemian's LXC container is the file `/data/system.img` inside the `linux`
partition (`mmcblk0p29`), not the 16 MiB `system` partition. It was read with
`debugfs -c` (read only, journal not replayed) and copied into the RE VM's
private work directory.

| Item | Size (bytes) | SHA-256 |
| --- | --- | --- |
| `/data/system.img` (ext4, volume `system`) | 642129920 | `153484c00cc10baa24f62d2a8c4b9b66e748cdba7455fb3ee4480bcfe4b253ca` |
| `etc/media_codecs_mediatek_video.xml` | 9736 | `3cf6a37840b308083939b02d2b943f86ff3e172f232c7ec64cf1e29d7d5c7155` |
| `vendor/etc/mtk_omx_core.cfg` | 2549 | `453973b83f904e0e6d6cda32ab0032d964507c01eaab366fb679b860f69e922e` |
| `vendor/etc/mtk_clear_motion.cfg` | 133 | `dc254328f1e37bd662e85e083422b279d6d411843fcfb9043d22f581a40d3196` |

Libraries and tools, from `vendor/lib` (32-bit ARM) unless noted:

| File | Size (bytes) | SHA-256 |
| --- | --- | --- |
| `libvcodecdrv.so` | 1126952 | `caa3115ad2912a5a2fca4d94c86363407a87c1bad6e897f8939e75dbc4d3f99e` |
| `vendor/lib64/libvcodecdrv.so` | 643392 | `98c84019e6deeb8fbe4744215ee2750e27e3dfc34f3fdb12348ed69c5ff87263` |
| `libvcodec_utility.so` | 67340 | `8ba48c0a600519ce86b698bf3885ae3ee54dc1a0394f5ef5253669a02c1dba70` |
| `libvcodec_oal.so` | 9408 | `a6819a1898aa2109ce8f166c5759048154dbcef88433fbed0b0f97553f35df90` |
| `libvcodec_cap.so` | 48616 | `5f9d6d7a2f9788c5a6f60060290a1cb9be400b9888a81b1eb36d7ea318277fe4` |
| `libMtkOmxVdecEx.so` | 211364 | `20c7e482654fd8c98dca52c1a730a64baeea814802fccb175c39c14535f27525` |
| `libMtkOmxVenc.so` | 129092 | `78a2a0305fbd17675379c67625b3121358c581f692dfd3af5c58af9e454aa217` |
| `libClearMotionFW.so` | 71276 | `ef4da36d32d1d792f2a3a38dbc5f77a8baa82d2c481a9caced5183ca4ef79433` |
| `libmjc.so` | 83648 | `4542b59d0a8ee27dcc2be9d8172c460dbedbabf3e13040c3a78f33bcf31a3897` |
| `libmjcFakeEngine.so` | 59076 | `c9faa47c27ef638d938022c0adeb7cc5e3d5daa39fc94c381668fd6a428ed645` |
| `libHEVCdec_sa.ca7.android.so` | 294332 | `e942af2f0577a76969e6a1d08563d6f346d8d0f9c8f3bd1a03c61601ed4e9d10` |
| `libvp9dec_sa.ca7.so` | 331396 | `b34d4a8c20308954ea8301665150e73383c982b3a1aa82fce83ea1afb8500791` |
| `libvp8dec_sa.ca7.so` | 333812 | `08b43055ab43a6a865b9f83fef6fe123a035b9d48d16534bae517042ecb971c8` |
| `libvc1dec_sa.ca7.so` | 778856 | `352fb12cbe24b5f04342850d2c8066d6a432e0f51e3a9fcc0e7bdaa580b6765b` |
| `libh264enc_sa.ca7.so` | 214332 | `0c833d36b2a8ae38473960963e7182545e989028141f5f1798c1823292023ece` |
| `libh264enc_sb.ca7.so` | 179988 | `e535d2f6f7ec20c58f38dde88c109a7942384c45bbd4def65e989f7dd79c32eb` |
| `libmp4enc_sa.ca7.so` | 154124 | `8d0d289d73a56e30d83d521030386642b096cfd91d3a8b8c6ddc9fd4d941f5e5` |
| `libmp4enc_xa.ca7.so` | 197464 | `2e8de1a29d9701f2ea261aada76e7d29141a2f420a282a8d2b047e4ef11a17cd` |
| `libvp8enc_sa.ca7.so` | 273332 | `842ca68e58f3a162e8bb357c885657686724f9186945bc9a39365b9e2662d7cb` |
| `vendor/bin/mfv_ut` | 157520 | `dbd37c2d63575189f915b4ea6b56520a077ee2cda48be77ca1c9aea7b8316555` |
| `vendor/bin/MtkCodecService` | 13920 | `4438d78733b6db0503efa0a8483bd2725a56fbd423cbc7045ad250725310c947` |

Not found in the image although `libvcodecdrv.so` names them:
`libhevce_sc.ca7.so`, `libvp9dec_sa.ca7_2core.so`, `libMtkH264SecVencTLCLib.so`.

## Firmware partitions checked

From the same partition capture, `scp1` (`mmcblk0p17`) and `tee1`
(`mmcblk0p24`) contain no string naming a video decoder, encoder, MJC, VPU or
secure video path. The SCP image is a FreeRTOS sensor/DVFS program.

## Public documentation

- 96Boards publication of the *MT6797 Functional Specification*, V1.0
  (2016): <https://www.96boards.org/documentation/consumer/mediatekx20/additional-docs/docs/MT6797_Functional_Specification_V1_0.pdf>,
  sections 6.5 to 6.8, pages 267 to 286.
- 96Boards publication of the *MT6797 Register Table*, part 2:
  <https://www.96boards.org/documentation/consumer/mediatekx20/additional-docs/docs/MT6797_Register_Table_Part_2.pdf>,
  section 4.7 (`VDEC_GCON`, page 799 on) and 4.8 (`VENC_dcm_cg`, page 821);
  part 1, `TOPRGU` `WDT_SWSYSRST` at `0x10007018`.

Tools: GNU binutils `readelf`, `nm`, `strings` and e2fsprogs `debugfs`
(aarch64 Ubuntu 24.04 guest), Poppler `pdftotext`. Nothing was executed.
