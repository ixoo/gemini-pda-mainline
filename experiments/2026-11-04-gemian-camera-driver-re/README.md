# Experiment: Gemian camera driver split and receiver contract

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-04-gemian-camera-driver-re` |
| Status | `completed` (offline source and binary analysis; no build, boot or device access) |
| Subsystem | Camera sensor driver, board power/clock, SENINF/MIPI receiver, CAM/CAMSV/ISP boundary |
| Device variant | Named Gemini PDA (MT6797X) running Gemian `3.18.41+` |
| Date(s) | 2026-11-04 |
| Investigator(s) | Repository maintainer with OpenCode assistance |
| Tracking issue | Not assigned |

## Question

The [Gemini camera path record](../2026-10-04-gemini-camera-re/README.md)
established the SP5509 sensor, board wiring and kernel boundaries from public
GPL source. It left one technical gap explicit: the CSI-2 receiver, lane,
SENINF and MIPI PHY programming exists only in the proprietary camera HAL, not
in any GPL file. Which userspace component owns that programming, which kernel
windows and interfaces does it use, and what register-level contract can be
recovered from the retained HAL binaries without executing them?

This record answers that question for the named unit. It adds no mainline
camera code, no DT node, no boot candidate and no device action.

## Provenance and environment

- Live unit identity used by the earlier read-only captures: Gemian
  `3.18.41+`, `AEON_CAMERA1 = sp5509mipirawsls`, `AEON_CAMERA0 = non_sensor`.
- Public GPL source compared: Gemian kernel
  `8cfe6596a503612e3332d9c26e292a19525a7f07`, principally
  `drivers/misc/mediatek/imgsensor/`, `drivers/misc/mediatek/cameraisp/`, and
  the `sp5509_mipi_raw_sls` sensor directory; Linux 7.1.3 for the mainline
  boundary.
- Retained 64-bit Gemian userspace extraction from 2026-07-12. The exact
  library sizes and SHA-256 values are in
  [`results/seninf-hal-contract.txt`](results/seninf-hal-contract.txt).
- Tools: GNU binutils `readelf`, `objdump` and `nm` in the ARM64 development
  VM. No library was loaded, no proprietary code was executed, and no source
  or binary is copied into this repository.

## Safety assessment

Read-only. The procedure opens no device node, performs no I2C or register
transaction, changes no GPIO, rail, clock or buffer, and starts no camera
stream. It reads an already extracted, Git-ignored userspace payload and
public source. No Buildbox build was required: the question is a static
ABI/register boundary, not a compiled artifact.

## Associated code

None. The analysis is a fixed sequence of binutils commands over the retained
`libcam.halsensor.so`, `libcamdrv_isp.so`, `libcameracustom.so` and
`camera.mt6797.so`; the recovered facts and command scope are recorded in
[`results/seninf-hal-contract.txt`](results/seninf-hal-contract.txt).

## Observations

### 1. The split is kernel power/I2C/IRQ, HAL receiver/ISP

The GPL kernel owns the sensor I2C transport and identity, the rails, reset and
power-down pins, the CAMTG parent selection, the camera-ISP register windows,
interrupts, clocks and M4U/SMI plumbing. The retained HAL owns the SENINF/MIPI
RX/TG programming and the CAM/CAMSV task sequences. `libcam.halsensor.so` maps
four `/dev/camera-isp` windows and writes the receiver directly; the kernel
`ISP_mmap()` accepts those windows among its allowed CAM/CAMSV/UNI/DIP/SENINF/
MIPI/GPIO set and caps their sizes.

### 2. MCLK is split at one register

`SeninfDrvImp::setMclk2()` writes `SENINF + 0x0`, `+0x600`, `+0x1600`,
`+0x1604` and `+0x1614` relative to the mapped `0x1a040000` base. The kernel's
`ISP_MCLK2_EN()` writes bits 31/29 of `SENINF1_BASE + 0x600`, which is
`0x1a041600` for `SENINF1_BASE = 0x1a041000`; the HAL address is the same word.
The kernel selects the `TOP_MUX_CAMTG` parent through
`KDIMGSENSORIOC_X_SET_MCLK_PLL` (`_IOWR('i', 60, 8)` = `0xc008693c`); the HAL
writes the shared enables, the generator source/edge fields and the divider.
The station record measured the divider at `n = 2` from a 48 MHz CAMTG, giving
24 MHz. This confirms and localises the earlier inference that the 24 MHz
sensor clock is not programmed by GPL code alone.

### 3. SENINF and CSI selection are HAL data, not source constants

`setSeninfCSI2(Seninf_para*)` chooses the MIPI analog block and SENINF register
group from its first structure field: value `2` selects the `+0x400` analog
block and `SENINF + 0x1000`, value `3` selects the `+0x0` analog block and
`SENINF + 0x3000`, and other values select the `+0x0` block with the base
SENINF group. The HAL's own debug labels identify `+0x400` as CSI1 and `+0x800`
as the third block. The live unit's SUB sensor reports port 1 through
`NSCamCustomSensor::getMipiSensorPort()`, but the `seninfSrc` value used for
that socket is not established by this static pass.

### 4. The receiver gate is real

The routine has a two-lane-only error path (`CSI2 only support two lane!`) and
logs its computed termination, settle, clock-termination, virtual-channel,
lane-count, NCSI2, header-order and ISP-clock fields. The SP5509 SLS source
requests two lanes. A reviewed runtime log capture while the stock camera opens
is the cheapest way to settle the actual values; it is not performed here.

## Analysis

The earlier record treated the missing receiver sequence as an irreducible
binary boundary. This pass narrows that boundary usefully:

- the boundary is not the whole camera stack; it is specifically the
  SENINF/MIPI RX/TG and CAM/CAMSV task programming in the HAL;
- the kernel ABI that carries it is small and visible: four mmap windows, one
  `mmap` gate in `camera_isp.c`, and the `kd_camera_hw` MCLK ioctl;
- the MCLK handoff is now reconciled by address, not by inference alone;
- the sensor identity, rails, pins, bus and two-lane mode from the earlier
  record remain sufficient for a sensor-side V4L2 probe.

The remaining uncertainty is not "where is the code" but "what do the fields
mean". Register offsets and control flow are observed; the field encoding of
the CSI timing and the board-specific `seninfSrc` selection are not.

## Conclusion

`confirmed`, scoped to the retained Gemian userspace and the pinned public
source: Gemian's camera receiver programming is in `libcam.halsensor.so`
(`SeninfDrvImp`), reached through `/dev/camera-isp` and `/dev/kd_camera_hw`;
the kernel exposes the register windows and selects the CAMTG parent, while the
HAL writes the TG divider and CSI-2 receiver sequence. The exact field values
and the SUB socket's `seninfSrc` remain `unresolved`. No hardware behaviour is
claimed.

## Follow-up

- Durable summary: [Gemini camera path](../../docs/hardware/gemini-camera.md).
- The active station bring-up independently reached the same HAL-boundary
  conclusion and has now passed the driver's own probe (T12):
  [the front camera's sensor from a module](../2026-11-04-gemini-camera/README.md).
  Its [receiver record](../2026-11-04-gemini-camera-receiver/README.md) reaches
  the mux at 2592 x 1944 (R1/R2) and a diagnostic CAMSV frame (C2); C1/C2/C3
  leave the DMA buffer empty, and C4 is not run. The DMA write and a standard
  capture interface remain open.
- Sensor-side design remains in the
  [2026-10-04 camera record](../2026-10-04-gemini-camera-re/README.md).
- Pipeline resources remain in the
  [camera recovery contract](../2026-07-13-camera-recovery/results/mt6797-camera-pipeline-contract.md).
- The DMA/buffer ABI is summarized in the durable document from
  `camera_isp.h`/`camera_isp.c` (ION import, ring control, write-DMA ports);
  that part is source-derived, not part of this static HAL pass.
- Next discriminating observation: a filtered Gemian log capture containing
  the HAL's `seninfSrc`, `MIPI pad`, `TermDelay`/`SettleDelay` and
  `CSI2-1 calibration` lines. The station record's G1 capture settled the
  sensor address and ID but did not report those lines. Any capture requires
  its own read-only admission and must not issue a stream or register
  transaction.
