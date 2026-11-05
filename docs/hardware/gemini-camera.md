# Gemini camera path

Scope: the built-in 5 MP camera on the named Gemini PDA (MT6797X) as driven by
the working Gemian stack, the split between the GPL kernel and the proprietary
camera HAL, and the mainline boundary. The rear camera is an optional
accessory and is not present on the development unit. This document describes
the vendor stack that works; it is not a claim that a mainline capture path is
enabled.

Related records: [Gemini camera reverse engineering](../../experiments/2026-10-04-gemini-camera-re/README.md)
for the sensor and board contract, [Gemian camera driver split](../../experiments/2026-11-04-gemian-camera-driver-re/README.md)
for the HAL/SENINF analysis, the [station camera bring-up](../../experiments/2026-11-04-gemini-camera/README.md)
and [receiver record](../../experiments/2026-11-04-gemini-camera-receiver/README.md)
for the current mainline chronology, and the [camera recovery contract](../../experiments/2026-07-13-camera-recovery/results/mt6797-camera-pipeline-contract.md)
for the CAM/CAMSV/ISP resources. Current support remains in the
[support matrix](../HARDWARE_SUPPORT.md) and [roadmap](../ROADMAP.md).

## 1. Summary

- The populated camera is the **SUB socket**; the vendor proc names report
  `AEON_CAMERA1 = sp5509mipirawsls` and `AEON_CAMERA0 = non_sensor`. The SUB
  socket is the built-in front camera; the MAIN socket is the empty rear
  accessory port (`inferred` from the product description and the live
  identity).
- The module is an **SP5509 SLS** on **I2C3** (`0x11014000`) at 7-bit address
  `0x20`; Gemian logs record write ID `0x40` and raw ID `0x0556`. It uses
  16-bit register addressing, two MIPI lanes, a **24 MHz** MCLK and a
  2592 x 1944 RAW10 mode. The register map and identity match the Hynix
  **Hi-556** family (`observed` for the address and ID on this unit; the
  register-map match is from source and the vendor ELF; the physical die is
  `inferred`).
- The stack is split. The GPL kernel owns the sensor I2C driver, rails, reset
  and power-down pins, CAMTG parent selection, camera register windows,
  interrupts, clocks and M4U/SMI plumbing. The proprietary HAL owns the
  **SENINF/MIPI RX/TG and CAM/CAMSV task programming** and reaches the
  hardware through `/dev/camera-isp` mmap and private ioctls.
- The kernel exposes `/dev/camera-isp`, `/dev/kd_camera_hw`,
  `/dev/kd_camera_hw_bus2`, `/dev/MAINAF`, `/dev/SUBAF`,
  `/dev/camera-fdvt`, `/dev/camera-dpe` and `/dev/kd_camera_flashlight`.
  These are vendor interfaces, not a Linux media-controller graph.
- The mainline path reaches the receiver and a diagnostic capture. From modules on the station, the
  `hi556` probe powers the sensor, starts its clock through `mt6797-seninf`, reads `0x0556` and powers it
  off (T12). `mt6797-seninf` adds the CSI-2 receiver and graph binding; the first stream reaches the mux
  at 2592 x 1944 (R1/R2), and a diagnostic CAMSV capture shows a full frame reaching CAMSV (C2). C5 writes
  the sensor's colour bars to memory through a diagnostic path. No standard V4L2 capture node or M4U/VB2
  path exists. Through the same path, stills of a real scene reached the panel (D2).

## 2. Sensor and board

### 2.1 Socket and identity

| Item | Value | Confidence |
| --- | --- | --- |
| Populated socket | SUB (camera 1), MAIN empty | `observed` / `inferred` |
| Sensor driver | `sp5509_mipi_raw_sls` (`sp5509mipirawsls`) | `observed` |
| Bus | I2C3 at `0x11014000`, pins GPIO74/75 | `confirmed` |
| 7-bit address | `0x20` (write ID `0x40`); `0x28`/`0x50` did not answer | `observed` (Gemian logs G1, mainline T8/T11) |
| Speed | 300 kHz | `confirmed` |
| ID register | `0x0f16` returns `0x0556` | `observed` (Gemian logs G1, mainline T8/T11) |
| Sensor family | Hynix Hi-556 register map | `inferred` |
| Link | two-lane MIPI, NCSI2 PHY, RAW Gr first pixel | `confirmed` |
| MCLK | 24 MHz | `confirmed` |
| Modes | 2592 x 1944 at 30 fps class, 1296 x 972, 640 x 480 at 120 fps class | `confirmed` |

The SLS and "main" vendor drivers are not interchangeable: the main variant
expects ID `0x0557` and returns `read(0x0f16) + 1`. Both use 16-bit register
addresses and big-endian 16-bit values. The vendor driver's own log line prints
the winning write ID and raw ID; the [station camera record](../../experiments/2026-11-04-gemini-camera/README.md)
captured `sp5509 i2c write id: 0x40, ReadOut sensor id: 0x556` at boot and
after a `cameraserver` restart, and its mainline T8/T11 runs read the same ID at
`0x20`. Do not treat the generic wrapper addresses (`3-0036` and friends) as the
sensor address; they are board control objects.

Source anchors:
[`kd_sensorlist.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/kd_sensorlist.c#L125-L131),
[`sp5509mipiraw_Sensor.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/sp5509_mipi_raw_sls/sp5509mipiraw_Sensor.c#L49-L250),
and the [SP5509 source contract](../../experiments/2026-07-13-camera-recovery/results/sp5509-source-contract.md).

### 2.2 Rails, pins and power sequence

| Signal | Connection | Confidence |
| --- | --- | --- |
| AVDD (`vcama`) | MT6351 LDO, 2.8 V | `confirmed` |
| DVDD (`vcamd`) | MT6351 LDO, 1.21 V requested (1.2 V nominal) | `confirmed` |
| DOVDD (`vcamio`) | MT6351 LDO, 1.8 V | `confirmed` |
| Reset | GPIO33 (`cam1_rst`) | `confirmed` |
| Power-down | GPIO29 (`cam1_pnd`) | `confirmed` |
| MCLK | TG2/SENINF1; GPIO31 toggles with it | `observed` (G1, T11); `CMMCLK1` label inferred |
| AFVDD | not enabled for the SLS table | `confirmed` |

Power-on follows the vendor table: enable MCLK; drive reset low and
power-down low; enable DOVDD 1.8 V, AVDD 2.8 V and DVDD 1.2 V with 10 ms
steps; then release reset and drive power-down high. The 1.2 V request is
rewritten to 1.21 V by the vendor board code because the MT6351 `vcamd`
range ends at 1.21 V. Upstream `hi556` has no power-down GPIO; the station
series adds it (0546), and without that a DT description must hold PDN high
through pinctrl.

Source anchors:
[`kd_camera_hw.c` power table](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/camera_hw/kd_camera_hw.c#L193-L204),
[`kd_camera_hw.c` socket selection](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/camera_hw/kd_camera_hw.c#L812-L832),
and [`aeon6797_6m_n.dts`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L1133-L1159).

### 2.3 Lens, flash and calibration

- **Autofocus.** The only compiled actuator driver is DW9714AF at 7-bit
  `0x0c`; the live `3-000c SUBAF` wrapper matches. The SLS power table never
  enables AFVDD, so the front module is treated as fixed focus and the
  actuator belongs to the rear accessory path (`inferred`). Upstream has
  `dw9714.c`; no new driver would be needed if an actuator is found.
- **Flash.** The vendor builds `dummy_flashlight`, the board flash pin states
  are commented out, and the product has no rear flash. There is nothing to
  port for the built-in camera (`confirmed`).
- **Calibration EEPROM.** `CONFIG_MTK_CAM_CAL` and several EEPROM names are
  configured, but the `cam_cal` source directory is absent from the public
  commit. Whether the front module carries an EEPROM is unknown. Raw capture
  does not need it; colour and lens-shading data would live in a libcamera
  tuning file.

## 3. Kernel driver stack

### 3.1 Components

| Kernel component | File(s) | Userspace interface | Role |
| --- | --- | --- | --- |
| Image-sensor core | `imgsensor/src/mt6797/kd_sensorlist.c`, `kd_sensorlist.h` | sensor char devices and `KDIMGSENSORIOC_*` ioctls | selects the sensor, I2C transactions, mode/feature control |
| SP5509 SLS driver | `imgsensor/src/mt6797/sp5509_mipi_raw_sls/` | through the core | register tables, ID, modes, exposure/gain |
| Board power/clock | `camera_hw/kd_camera_hw.c` | `/dev/kd_camera_hw`, `/dev/kd_camera_hw_bus2` | rails, reset/PDN pinctrl, MCLK enable, socket selection |
| Camera ISP | `cameraisp/src/mt6797/camera_isp.c` | `/dev/camera-isp` ioctl and mmap | CAM/CAMSV/SENINF/UNI/DIP register windows, IRQ, clocks, M4U |
| Lens | `lens/main/`, `lens/sub/` | `/dev/MAINAF`, `/dev/SUBAF` | DW9714AF and dummy lens drivers |
| Flashlight | `flashlight/src/mt6797/` | `/dev/kd_camera_flashlight` | `dummy_flashlight`; no real flash |
| Calibration | `cam_cal/` (not public) | internal | absent from the public tree |

The sensor ioctls use magic `'i'`; the camera-ISP ioctls use magic `'k'`.
`KDIMGSENSORIOC_X_SET_MCLK_PLL` is `_IOWR('i', 60, 8)` = `0xc008693c`; the HAL
uses exactly that command. `ISP_mmap()` accepts the windows the HAL maps
(section 4.1) among its allowed CAM/CAMSV/UNI/DIP/SENINF/MIPI/GPIO set.

### 3.2 MCLK handoff

The 24 MHz sensor clock is split across two owners:

1. The kernel's `kdSetSensorMclk()` enables `TOP_MUX_CAMTG` and selects its
   parent: `UNIVPLL_D26` for the 48 MHz group (`freq == 1`) or
   `UNIVPLL2_D2` for the 52 MHz group (`freq == 2`).
2. The HAL sets the shared clock enables at SENINF `+0x0` (bits 10/11), the
   generator's source/edge fields at `+0x600`/`+0x1600`/`+0x2600`, and the
   divider in the `+0x4`/`+0x14` companions.

The two register addresses agree:

| Socket | TG | Kernel enable | HAL routine | Registers (from `0x1a040000`) |
| --- | --- | --- | --- | --- |
| MAIN | SENINF0/TG1 | `ISP_MCLK1_EN`, `0x1a040600` | `setMclk1` | `+0x0`, `+0x600`, `+0x604`, `+0x614` |
| SUB | SENINF1/TG2 | `ISP_MCLK2_EN`, `0x1a041600` | `setMclk2` | `+0x0`, `+0x1600`, `+0x1604`, `+0x1614` |
| MAIN2 | SENINF2/TG3 | no board consumer | `setMclk3` | `+0x0`, `+0x2600`, `+0x2604`, `+0x2614` |

The kernel's `SENINF1_BASE` is `0x1a041000`; adding `0x600` gives
`0x1a041600`, the same word as the HAL's `+0x1600` from `0x1a040000`. This is
the clearest confirmation that the SUB socket uses TG2/SENINF1. The HAL also
writes the shared `+0x0` enables and the first generator's `+0x600` source.
The station record measured the TG2 divider at `n = 2` from a 48 MHz CAMTG,
giving 24 MHz (T2/T7). A mainline driver must replace both halves, not just
the CAMTG mux.

Source anchors: [`kd_sensorlist.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/kd_sensorlist.c#L3798-L3812)
and [`kd_imgsensor.h`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/inc/kd_imgsensor.h#L88-L94).

## 4. Receiver and capture path

### 4.1 What the HAL maps

`SeninfDrvImp::init()` in `libcam.halsensor.so` opens `/dev/camera-isp` and
`/dev/kd_camera_hw`, then maps four windows through the camera-ISP fd:

| Window | Physical base | Size | Purpose |
| --- | --- | --- | --- |
| CAM_A | `0x1a004000` | `0x1000` | CAM A registers |
| SENINF | `0x1a040000` | `0x8000` | SENINF0..3 and TG/CSI control |
| MIPI RX | `0x10217000` | `0x2000` | CSI-2 analog blocks |
| GPIO | `0x10002000` | `0x1000` | camera GPIO view |

The kernel's `ISP_mmap()` accepts `CAM_A`, `CAM_B`, `CAMSV_0`..`CAMSV_5`,
`UNI_A`, `DIP_A`, `SENINF`, `MIPI_RX` and `GPIO`, and rejects anything else
or an oversized request. The four windows are therefore the intended ABI, not
a debug escape.

Source: [`camera_isp.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/cameraisp/src/mt6797/camera_isp.c#L9051-L9110)
and [`camera_isp.h`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/cameraisp/src/mt6797/inc/camera_isp.h#L37-L49).

### 4.2 SENINF and timing-generator programming

From the retained HAL (static analysis; exact offsets in the
[split record](../../experiments/2026-11-04-gemian-camera-driver-re/results/seninf-hal-contract.txt)):

- **Top mux:** `SENINF + 0x8`, one 4-bit field per input index 0..7.
- **Per-channel control:** `+0x200`/`+0x204`, `+0x1200`/`+0x1204`,
  `+0x2200`/`+0x2204`, `+0x3200`/`+0x3204`. These carry an enable bit, a
  data-pad field and a source field. The HAL's `SENINF1` control at `+0x200`
  lies inside the DTS `seninf0` 4 KiB block and `SENINF2` at `+0x1200` inside
  `seninf1`; use the addresses, not the names.
- **Additional mux/control words** at `+0xd00`, `+0x1d00`, `+0x2d00`,
  `+0x3d00`, `+0x4d00`, `+0x5d00`, `+0x6d00`, `+0x7d00`.
- **TG/MCLK:** shared enables at `+0x0`; `+0x600` (TG1), `+0x1600` (TG2) and
  `+0x2600` (TG3), each with `+0x4` and `+0x14` companions. The `+0x4` word
  carries the divider and the `+0x14` word the period/value; the kernel does
  not write either.

The HAL's `setSeninfCSI2()` dispatches on a `seninfSrc` field in its parameter
block (observed pointer selection):

| `seninfSrc` | MIPI RX block | SENINF group |
| --- | --- | --- |
| `2` | `+0x400` (CSI1) | `+0x1000` (SENINF1) |
| `3` | `+0x0` (CSI0) | `+0x3000` (SENINF3) |
| other | `+0x0` (CSI0) | `+0x0` (SENINF0) |

The `+0x400`/`+0x800` block labels come from the HAL's own symbols and log
strings (`CSI1_OffsetCal`, `CSI2-1 calibration`). The value used on the SUB
socket is **not** established statically; the TG2/SENINF1 agreement and the
CSI1 labels make CSI1 the strong inference, but it remains `inferred`.

### 4.3 CSI-2 receiver programming

The same routine writes the MIPI RX analog block and the selected SENINF
group. Observed offsets include:

- MIPI RX: `+0x00`, `+0x04`, `+0x18`, `+0x1c`, `+0x20`, `+0x28`, `+0x2c`,
  `+0x34`, `+0x38`, `+0x44`, `+0x48`, `+0x80`, and the mirrored
  `+0x200`/`+0x204`/`+0x218`/`+0x21c`/`+0x220`/`+0x228`/`+0x22c`/`+0x234`/
  `+0x238` group.
- SENINF: `+0x200`/`+0x204`, `+0x700`..`+0x738`, `+0x838`..`+0x8d0`,
  `+0xa00`..`+0xa38`, `+0xa74`..`+0xb10`.

The routine computes and logs termination delay, settle delay, clock
termination delay, virtual channel, lane count, NCSI2 enable, header order,
settle-count, ISP clock and DPCM fields:

```text
TermDelay:%d SettleDelay:%d ClkTermDelay:%d Vsync:%d lane_num:%d
NCSI2_en:%d HeaderOrder:%d SettleDelay(cnt):%d ISP_clk:%d dpcm:%d
```

It has a two-lane-only error path (`CSI2 only support two lane!`). The SP5509
SLS source requests `SENSOR_MIPI_2_LANE`, so that path is not expected to
trigger. The actual numeric values depend on the selected CAMTG parent and the
sensor mode and are computed at runtime; they are not static constants.

**Practical observation.** The station record's G1 capture read the Gemian log
while `cameraserver` opened the sensor and settled the address and ID, but it
does not report `seninfSrc`, the MIPI pad, `TermDelay`, `SettleDelay` or the
`CSI2-1` calibration line. A filtered capture for those strings, without any
register access, remains the next discriminator.

### 4.4 Capture, interrupts and memory

The receiver feeds the vendor CAM/CAMSV blocks, not a V4L2 graph:

| Block | Base | IRQ | Notes |
| --- | --- | --- | --- |
| IMGSYS config | `0x15000000` | - | clock/power |
| DIP A | `0x15022000` | SPI260 | hardware ISP |
| CAMSYS config | `0x1a000000` | - | camera clocks |
| CAMTOP | `0x1a003000` | SPI247 | top control |
| CAM A / CAM B | `0x1a004000` / `0x1a005000` | SPI248 / SPI249 | capture |
| CAMSV0..5 | `0x1a050000`..`0x1a055000` | SPI252..SPI257 | simple view/capture |
| SENINF0..7 | `0x1a040000`..`0x1a047000` | - | receiver/TG |

The vendor M4U table attaches camera clients to LARB2 (CAM_IMGO/RRZO/AAO/AFO/
LSCI/SV/LCSO/UFEO/BPCI/PDO/RAWI) and LARB6 (CAM_IMGI/IMG2O/IMG3O/VIPI/ICEI/
RP/WR/RB/DPE). The buffer path is ION allocation plus M4U mapping, with
completion through the private ISP buffer/IRQ ABI. The local series adds MT6797
CAM clock gates and disabled `larb2`/`larb6` nodes; Linux 7.1.3 itself has the
IMG clocks and ISP/MM power domains, but no SENINF, CSI-2, CAM or CAMSV V4L2
driver.

The userspace side of this block is `libcamdrv_isp.so`: `ISP_DRV_CAM`,
`IspDrvCamsv` and `IspDrvDipPhy` expose `readReg`/`writeReg`/`waitIrq` and
`/dev/camera-isp` ioctls to the rest of the HAL. None of this is a standard
V4L2 media graph.

### 4.5 DMA and buffer ABI

The vendor path is not a V4L2 queue. **ION** buffers are filled by the CAM/CAMSV
write-DMA engines, and the HAL queues them itself through frame buffer control.
This subsection describes that Gemian ABI; the separate
mainline diagnostic capture is noted under "Mainline replacement".

**Write-DMA ports.** The vendor header names the CAM write ports and comments
their register offsets inside the CAM window: `IMGO` `0x0220`, `RRZO`
`0x0250`, `AAO` `0x0280`, `AFO` `0x02b0`, `LCSO` `0x02e0`, `UFEO` `0x0310`,
`PDO` `0x0340`, `BPCI` `0x0370`, `CACI` `0x03a0`, `LSCI` `0x03d0`.
`EISO`/`FLKO`/`RSSO` reuse the first three slots in that table; the
frame-header registers are at `0x0c04`..`0x0c1c` and `0x03c4`..`0x03cc`.
These are header facts, not live register reads. CAMSV has its own
`_camsv_imgo_` ring entry and `ISP_IRQ_TYPE_INT_CAMSV_0`..`5` modules.

**Ring contract.** `ISP_BUFFER_CTRL_STRUCT` carries `ctrl`
(`ISP_RT_BUF_CTRL_DMA_EN` or `CLEAR`), `module` (CAM_A/CAM_B/CAMSV_n),
`buf_id` (DMA port), `data_ptr`/`ex_data_ptr`, and `pExtend` (per-port active
flags). Its `ring_buf[]` has `start`, `total_count`, `empty_count`,
`pre_empty_count`, `active`, `read_idx`, `img_cnt`, and `ISP_RT_BUF_SIZE`
`ISP_RT_BUF_INFO_STRUCT` entries. Each entry carries `memID`, `size`,
`base_vAddr`, `base_pAddr`, timestamps, `bFilled`, `bProcessRaw`, image/RRZ/
crop metadata, `bDequeued` and `bufIdx`. The ring state is INIT/SOF/DONE; each
buffer is EMPTY/FILLED/LOCKED.

**ION bridge.** `ISP_ION_IMPORT` and `ISP_ION_FREE` take
`ISP_DEV_ION_NODE_STRUCT` (`devNode`, `dmaPort`, `memID`) and keep a
reference-counted handle per camera device and DMA port;
`ISP_ION_FREE_BY_HWMODULE` drops all handles for a module. The kernel stores
`G_WRDMA_IonHnd[devNode][dmaPort][slot]` with a per-port spinlock, so the same
ION fd can back several buffers but is only imported once. `ISP_SET_MEM_INFO`,
`ISP_WAIT_IRQ`, `ISP_CLEAR_IRQ` and `ISP_CQ_SW_PATCH` complete the path.

**Flow.** ION allocation → fd → import → M4U port → enqueue → DMA fill → IRQ wait
→ dequeue. The kernel does not reap the ring: `camera_isp.c` never uses `bFilled`,
and its ring control handles only `DMA_EN` and `CLEAR`. The HAL's `ISP_DRV_CAM`,
`IspDrvCamsv` and `IspDrvDipPhy` wrap the ioctls and register access, with `CQ_*`
commanding register updates and `waitIrq`/`clearIrq` ordering frames. There is
no standard dma-buf/VB2/fence queue.

**CAMSV frame buffer control.** From the retained `CAMSV_BUF_CTRL` (static
analysis), with field names from the public kernel's layout for the CAM block at
the same offsets:

1. Before streaming, `CAMSV_FBC_IMGO_CTL1` (`0x110`) is written 0, then bit 16
   (`FBC_MODE`, queue mode) is set and stays set.
2. Enabling sets the top byte (`SUB_RATIO`, which the library logs as the
   subsample), then bit 15 (`FBC_EN`), then bit 22, which the layout does not
   name.
3. Each enqueue writes the address to `CAMSV_FBC_IMGO_ENQ_ADDR` (`0x118`) and sets
   bit 0 of `CAMSV_IMGO_FBC` (`0x02c`). The library also keeps its own queue of the
   buffers, and dequeue takes from that queue.

`CAMSV_FBC_IMGO_CTL2` (`0x114`) holds `FBC_CNT`, `RCNT`, `WCNT` and `DROP_CNT`.

**Mainline replacement.** Use dma-buf heaps, the MT6797 IOMMU/SMI providers,
dma-fence and a VB2 queue; the first path should be one CAMSV output to memory.
The local series has `larb2`/`larb6` and M4U nodes. A diagnostic CAMSV path
exists (0558-0564): C2 shows a full frame reaching CAMSV, but C1/C2/C3
leave the coherent buffer at its fill value. C3's `CAMSV_FBC_IMGO_CTL2` top
byte (`DROP_CNT`) moved while `FBC_CNT`/`RCNT`/`WCNT` stayed zero. The inference
is that frames were dropped because of the frame-buffer-control setup (queue mode
off, `FBC_NUM` 0); that rests on the CAM block's layout, and nothing checked the
rest of memory. 0561 sets queue mode. `larb2` then read `0x3fff` at `0xfc0`, its
per-port MMU enable (C4), so all 14 ports, CAMSV0's included, go through M4U, unlike
larb0 and larb5 on the display path. C5 (0562) clears the CAMSV0 bit and the sensor's
colour bars reach the buffer: 10-bit little-endian packing, 4 pixels in 5 bytes, stride
3240, Gr first, one frame written and the rest dropped. This is a diagnostic with no
V4L2 node.
`CLK_MM_SMI_COMMON` is shared with the display, which relies on the gate the loader
left open with nobody counting it. Enabling and disabling it closes the gate and hangs
the display at its next blank (inferred from C3 and C4); 0563 leaves it alone.
A bypassed port does not validate the vendor ION/M4U ring or a standard capture interface. The vendor
descriptor/CQ format and the SP5509 port binding remain open.

Source anchors: [`camera_isp.h`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/cameraisp/src/mt6797/inc/camera_isp.h#L260-L330)
(write-DMA enum), [`camera_isp.h`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/cameraisp/src/mt6797/inc/camera_isp.h#L330-L443)
(ION node and ring structures), and
[`camera_isp.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/cameraisp/src/mt6797/camera_isp.c#L5410-L5560)
(ring control) and
[`camera_isp.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/cameraisp/src/mt6797/camera_isp.c#L7841-L7935)
(ION import/free).

## 5. Userspace stack

| Component | Role |
| --- | --- |
| `system/bin/cameraserver` | Android camera service; the app-facing owner |
| `system/vendor/lib64/hw/camera.mt6797.so` | Android camera HAL module |
| `libcam.halsensor.so` | `HalSensorList`, `HalSensor`, `ImgSensorDrv`, `SeninfDrvImp`; sensor and receiver setup |
| `libcamdrv_isp.so` | `ISP_DRV_CAM`, `IspDrvCamsv`, `IspDrvDipPhy`; register/IRQ/DMA ABI |
| `libcameracustom.so` | per-sensor static metadata and custom sensor tables, including `getMipiSensorPort()` |
| `libcam.*` | camera adapter, device1/device3, 3A, pipeline, stream and image-buffer layers |

The live identity of the retained payload is recorded by size and SHA-256 in
the [split record](../../experiments/2026-11-04-gemian-camera-driver-re/results/seninf-hal-contract.txt).
The Android HAL is the working path; Gemian does not drive this camera through
libcamera or a native V4L2 application.

## 6. Mainline mapping

| Gemian boundary | Standard replacement | Current state |
| --- | --- | --- |
| `kd_sensorlist` + SP5509 SLS char driver | V4L2 sensor sub-device, `hi556` | Upstream `hi556` is ACPI-only; the station series adds the binding, OF match, power-down GPIO and 24 MHz table (0545-0547). T12 passes the driver's own probe, reading `0x0556` on two loads on one boot |
| `kd_camera_hw` rails/GPIO/MCLK | regulator, `gpio`, `pinctrl`, clock framework | Station series adds the ISP power domain (0543), CAM clock-provider fix (0544), SENINF master-clock driver (0548/0549) and station DT (0550). The `hi556` probe runs the power sequence through these (T12) |
| `/dev/camera-isp` SENINF/MIPI RX mmap | MT6797 SENINF/CSI-2 receiver driver | Receiver exists (0555) with graph binding; the first stream reaches the mux at 2592 x 1944 (R1/R2), error bits still open. The HAL sequence is mapped in this document |
| CAM/CAMSV and DMA | V4L2 capture entity and VB2/dma-buf | Diagnostic CAMSV capture exists (0558-0564); a full frame reaches CAMSV (C2) but C1/C2/C3 leave the DMA buffer empty. With queue mode, the CAMSV0 port bypassing M4U and the shared SMI gate left alone, C5 wrote colour bars to memory. No V4L2 node yet. No VB2/M4U capture path; MT8365 "ISP3.0" is the nearest public template |
| DIP/hardware ISP | libcamera software ISP | Out of scope for a first raw path |
| ION + M4U + private fences | dma-buf heaps, IOMMU, dma-fence | Local M4U/larb nodes exist; the diagnostic does not use M4U, though larb2 read as routing all its ports there (C4), so the camera M4U consumer remains unproven |
| DW9714AF / dummy flashlight / cam_cal | `dw9714`, LED class, tuning data | Not needed for the built-in fixed-focus, flashless camera |

The realistic first target is still **SP5509 -> two-lane CSI -> SENINF ->
CAMSV -> memory**, with libcamera's simple pipeline and software ISP, not the
vendor DIP/CAM hardware ISP. The sensor power/clock/ID, the CSI-2 link and the
first CAMSV frame are shown, and colour bars reach memory (C5); the next step is a standard
capture interface. The station chronology is in the
[camera record](../../experiments/2026-11-04-gemini-camera/README.md) and the
[receiver record](../../experiments/2026-11-04-gemini-camera-receiver/README.md),
with patches under `patches/proposals/0543`-`0570`. A capture node exists
in the series (0568) but has not run; the picture on the panel (D1/D2) came from the diagnostic it replaces.

### Master clock on mainline

The interface's enable, bit 0 of `0x1a041200`, must be set before generator 2 starts. Started the other way
round the pad is low; setting the enable later lets the pad move but the sensor does not answer, and
restarting the generator then works (T9 to T11). Hardware facts on one unit, from the
[station record](../../experiments/2026-11-04-gemini-camera/README.md). CAMTG measures 47.99 MHz with the SoC's
frequency meter (T7).

## 7. Confidence and open questions

| Question | Current position |
| --- | --- |
| Physical sensor die | `inferred` - SP5509 SLS ID and register map match Hi-556; no die read |
| SUB on the second interface and generator | `observed` - T11 set the second interface's enable (`+0x1200`) and started generator 2, then read the ID; G1 saw GPIO31 toggle |
| SUB on CSI1 | `observed` - the receiver uses the `0x10217400` analog block and the first stream reaches the mux (R1/R2) |
| Driver's own probe | `observed` - T12, `chip id 0x0556` on two loads on one boot, with 0553 enabling the interface before starting its generator |
| Receiver link | `observed` - R1/R2 reached the mux at 2592 x 1944 at about 30 fps; status bits and pixel content remain open |
| Diagnostic CAMSV frame | `observed` - C2 reached `CAMSV_TG_DAT_NO` one short of a full frame |
| DMA write and image | `observed` on a diagnostic path with CAMSV0 bypassing M4U: colour bars in memory (C5), and on the panel with a real scene as stills (D1/D2). The owner reported that it worked and that colours may need adjustment; orientation and exposure were not reported |
| MIPI pad for the SUB sensor | `inferred` - `getMipiSensorPort()` returns the device index (SUB = 1); mapping to `seninfSrc` unresolved |
| Exact CSI timing values | `unresolved` - computed at runtime from the selected mode and CAMTG parent |
| PDN polarity | `observed` in the vendor table; upstream `hi556` has no PDN control |
| Front module autofocus | `inferred` fixed focus; no AFVDD in the SLS table |
| Calibration EEPROM | `unresolved` - sources absent from the public tree |
| Cold-boot / resume camera state | `unresolved` - no camera stream or suspend capture on this unit |
| Rear accessory support | `unresolved` - MAIN socket empty; OV5675/S5K5E2YA/"SP5509 main" are candidate parts |

## 8. Evidence index

- [Gemini camera path reverse engineering](../../experiments/2026-10-04-gemini-camera-re/README.md)
- [Gemian camera driver split and receiver contract](../../experiments/2026-11-04-gemian-camera-driver-re/README.md)
- [The front camera's sensor from a module on the station](../../experiments/2026-11-04-gemini-camera/README.md)
- [The front camera's CSI-2 receiver on the station](../../experiments/2026-11-04-gemini-camera-receiver/README.md)
- [Camera identity and mainline boundary](../../experiments/2026-07-13-camera-recovery/README.md)
- [MT6797 camera pipeline contract](../../experiments/2026-07-13-camera-recovery/results/mt6797-camera-pipeline-contract.md)
- [SP5509 source contract](../../experiments/2026-07-13-camera-recovery/results/sp5509-source-contract.md)
- [Gemian hardware baseline](gemini-gemian-baseline.md) and [vendor userspace](vendor-userspace.md)
- [Vendor kernel ABI](vendor-kernel-abi.md)
- Station series `patches/proposals/0543`-`0570`; profile fragment
  `configs/gemini-a53-station-camera.fragment`.
- Pinned Gemian kernel `8cfe6596a503612e3332d9c26e292a19525a7f07`:
  `drivers/misc/mediatek/imgsensor/src/mt6797/`,
  `drivers/misc/mediatek/imgsensor/src/mt6797/camera_hw/kd_camera_hw.c`,
  `drivers/misc/mediatek/cameraisp/src/mt6797/camera_isp.c`,
  `drivers/misc/mediatek/lens/`, `drivers/misc/mediatek/flashlight/`.
- Linux 7.1.3: `drivers/media/i2c/hi556.c`, `drivers/media/i2c/dw9714.c`,
  `drivers/media/platform/mediatek/`, `drivers/iommu/mtk_iommu.c`,
  `drivers/memory/mtk-smi.c`.
