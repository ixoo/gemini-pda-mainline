# MT6797 camera mainline design boundary

This is an implementation map, not a claim that any camera path works on
mainline. It separates observed vendor objects from the standard Linux media
objects that still need to be implemented and tested.

## Observed vendor graph

| Layer | Observed object | Evidence | Mainline interpretation |
| --- | --- | --- | --- |
| Sensor selection | `/proc/AEON_CAMERA1=sp5509mipirawsls`; `/proc/AEON_CAMERA0=non_sensor` | Read-only live capture and matching kallsyms entry points | Active sensor family is SP5509; exact chip ID, physical address, and module orientation remain unknown |
| Camera wrappers | I2C2 `0x2d` `camera_main`; I2C3 `0x36` `camera_sub`; I2C8 `0x36` `camera_main_hw` | Live sysfs plus vendor `cust_i2c.dtsi`/SoC DTS | These are vendor wrapper/control nodes, not proof of the sensor's I2C address; do not use them as a SP5509 `reg` value |
| Autofocus | I2C2 `0x72` `MAINAF`; I2C3 `0x0c` `SUBAF` | Live sysfs and bound vendor drivers | Separate actuator sub-devices are plausible, but VCM model, register protocol, and active module mapping are not recovered |
| Receiver/platform | `seninf0`–`seninf7`; `1a040000.kd_camera_hw1` → `image_sensor`; `kd_camera_hw2` → `image_sensor_bus2` | Live platform sysfs and vendor `mt6797.dtsi` | A vendor camera-hardware ABI spans receiver selection and sensor control; it is not a Linux media-controller graph |
| User ABI | `/dev/camera-isp`, `/dev/camera-fdvt`, `/dev/camera-dpe`, `/dev/kd_camera_hw*`, `/dev/kd_camera_flashlight`, `/dev/MAINAF`, `/dev/SUBAF` | Live device-node inventory | Replace private ioctl/file-descriptor consumers with V4L2 sub-devices, media graph, video nodes, controls, and standard power/clock APIs |
| DMA fabric | M4U larb2 camera output/statistics/raw ports; larb6 camera input/output and DPE ports | Vendor port table and live M4U resource map | Existing MT6797 M4U/SMI data is reusable only after each capture node's exact port and buffer ownership is proven |

## Board resources

The vendor board DTS supplies camera clocks and `vcama`, `vcamd`, `vcamaf`, and
`vcamio`. Camera pin states use reset GPIO32/GPIO33, power-down GPIO28/GPIO29,
and GPIO-controlled rail states on GPIO73/GPIO254. These are source-derived
board resources; the live capture did not prove which sensor consumes which
state or whether the rail GPIOs are still required on this variant.

The live adapter topology identifies the wrapper controller windows as
`i2c2=0x11013000`, `i2c3=0x11014000`, and `i2c8=0x11009000`. Sysfs contains no
pre-existing client object at candidate sensor addresses `0x20` or `0x28` on
those buses. That absence is compatible with the vendor's dynamic probe path,
but is not evidence that either address is safe to contact.

The immutable vendor ELF also contains shared resource labels for
`vcamd_sub`, `vcamaf`, `vcama_sub`, `vcama_main2`, `vcamd_main2`,
`vcamio_sub`, `vcamio_main2`, and cam0/cam1/cam2 reset, power-down, and
camera-LDO states. The `kdCISModulePowerOn` path is table-driven, so labels
alone do not recover the SP5509 module's exact rail/reset sequence.

The pinned Planet tree does contain complete SP5509 sources, even though it
does not contain a mainline-style media driver. The SLS and main implementations
are under `sp5509_mipi_raw_sls/` and `sp5509_main_mipi_raw/`; the sensor list
registers both conditionally. SLS uses ID `0x0556` from register `0x0f16`, the
main variant returns the same register value plus one (`0x0557`), and both use
16-bit register/value transfers at 300 kHz with vendor write IDs `0x40`/`0x50`
(Linux addresses `0x20`/`0x28`). SLS source tables provide the 24 MHz, two-lane
MIPI-NCSI2 contract, RAW_Gr formats, output sizes, timing classes, and the
camera-hardware power sequence. These facts are summarized and hash-anchored
in the [SP5509 source contract](sp5509-source-contract.md); the full vendor
tables are not copied into this repository.

The vendor source declares eight SENINF windows beginning at `0x1a040000`, plus
`kd_camera_hw1` and `kd_camera_hw2` wrappers over the same camera-hardware
region. This overlap is a vendor ABI detail, not a safe template for a modern
DT binding. A mainline design must assign non-overlapping receiver, PHY, ISP,
and DMA resources after the register map and interrupt ownership are recovered.
The complete source-derived window, IRQ, clock, SENINF mapping, and larb2/larb6
port summary is preserved in the [MT6797 camera pipeline contract](mt6797-camera-pipeline-contract.md).

## Linux 7.1.3 coverage

Linux already provides useful pieces:

- `drivers/media/i2c/ov5675.c` demonstrates the standard I2C V4L2 sub-device,
  endpoint, regulator, clock, reset, controls, runtime-PM, and mode-table
  mechanics.
- `drivers/clk/mediatek/clk-mt6797-cam.c` provides MT6797 camera clock data.
- The MT6797 DTS has camera-related `camsys`, `imgsys`, and larb resources, but
  they remain disabled and are not a complete capture path.
- Generic MediaTek IOMMU/SMI, reset, regulator, and power-domain providers can
  be reused when the live register and ownership contracts match.

The tree has no SP5509 sensor driver or binding and no matching MT6797 SENINF,
CSI receiver, ISP, or camera media-controller driver. The vendor SP5509
sources provide a silicon-specific design contract, while the immutable
vendor-kernel ELF and live diagnostic independently corroborate the SLS probe
path. They do not prove the populated address, physical slot, endpoint, or
board-specific power ownership. Therefore a compatible-string substitution or
a copied vendor camera ioctl ABI would be incorrect; a new SP5509 V4L2 driver
must be paired with a separately recovered MT6797 capture pipeline.

## Proposed standard media boundary

The eventual graph should be staged as independent, reviewable pieces:

1. An SP5509 I2C V4L2 sub-device with a documented chip-ID transaction,
   supplies, clock, reset/power-down GPIOs, CSI-2 endpoint, supported raw Bayer
   formats, controls, and per-mode link frequency/timing tables.
2. A separately identified VCM actuator sub-device only after the `MAINAF` or
   `SUBAF` protocol and physical module mapping are recovered.
3. An MT6797 SENINF/CSI receiver sub-device with explicit lane routing and
   media-bus formats, using the correct clock/reset/PHY contracts.
4. A capture/ISP driver exposing standard V4L2 video nodes and media links,
   attaching buffers through the verified MT6797 M4U larb/port assignments.
5. Board DT graph endpoints connecting the sensor, receiver, and capture path;
   no vendor `camera_main`/`camera_hw` compatible strings or Android HAL nodes.

## Safe bring-up gates

The order matters because the current vendor stack can hide wrong addresses
and power sequencing:

1. Recover the vendor sensor transaction path from source or the immutable ELF
   evidence. Do not use `i2cdetect`, generic writes, or camera streaming as an
   identity probe.
2. Perform one bounded, read-only chip-ID transaction with explicit adapter,
   candidate address, reset, rail, and rollback evidence; the ELF-derived
   `0x0f16`/`0x0556` transaction is not sufficient authorization by itself.
3. Probe the SP5509 sub-device without enabling a stream; verify controls and
   endpoint metadata only.
4. Exercise the receiver with a sensor test pattern or a separately verified
   source, keeping ISP/DMA consumers disabled until the SENINF register and IRQ
   contract is known.
5. Attach one raw capture buffer to one verified M4U port, with a recovery path
   and no default write to firmware-owned or display-shared memory.

Until gates 1–3 are complete, the sensor and camera consumers should remain
`status = "disabled"` in the Gemini DT. The authoritative evidence and private
capture locations are recorded in the [camera recovery README](../README.md)
and [source validation](mainline-camera-source-validation.txt).
