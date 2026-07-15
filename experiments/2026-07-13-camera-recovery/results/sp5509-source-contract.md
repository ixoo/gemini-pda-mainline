# SP5509 sensor source contract

## Status

The pinned Planet MT6797 source contains complete, separate SP5509 main and
SLS sensor implementations. This corrects the earlier camera note that
described the source as only a generated selection name. The source contract
is sufficient to design a new V4L2 sensor driver, but not to enable it: the
physical module/address, exact endpoint wiring, and MT6797 capture pipeline
remain untested.

No I2C transaction, GPIO change, regulator change, mode write, or camera stream
was performed.

## Provenance

The analyzer is
[`analyze-sp5509-source-contract.sh`](../scripts/analyze-sp5509-source-contract.sh).
It reads Git objects from Planet MT6797 commit
`c5b0be85017ad0c599725e8273842efdbecdd88a` and compares Linux `7.1.3` in the
development VM. It does not copy vendor source into the repository.

| Source | SHA-256 |
| --- | --- |
| vendor SLS `sp5509mipiraw_Sensor.c` | `fa47f2af853b7d2d8bea3e777d7a141fe2b8ea80821176915c7d1caea111ab92` |
| vendor SLS `sp5509mipiraw_Sensor.h` | `8aac6fc619431666e22acbb8596d973a21eca2d236b60f06b049f3fdd075228f` |
| vendor main `sp5509mainmipiraw_Sensor.c` | `8aa97c9b021503c18d95b968668df6dc20d82f254fc67c830df3993694bb3992` |
| vendor main `sp5509mainmipiraw_Sensor.h` | `8aac6fc619431666e22acbb8596d973a21eca2d236b60f06b049f3fdd075228f` |
| vendor `kd_imgsensor.h` | `82225c583ef763879a2c54d654352068c7b56a1a197cfc04bb70ae474a7f0e20` |
| vendor `kd_sensorlist.h` | `fedf343729550cfebd95bc84ba1c76530b02ba649748467909ff32271c69a5f8` |
| vendor `camera_hw/kd_camera_hw.c` | `980af99f799e2f29df6df62dbdde2234201e5da88262326331aff127218d25dd` |
| vendor `aeon6797_6m_n.dts` | `d1bd9d83941dffb44615f69e9113c7b79d87b3e9e87057619c70370f56456f5a` |
| Linux `drivers/media/i2c/ov5675.c` | `960a3e74ab044a77458aeb2171434c12ec298e01c853b6fb90a73b78f2ebe333` |
| Linux `ovti,ov5675.yaml` | `d6aaa35c7817007d11564d17b93f88f36b3feced2d5191621ee3b470a8412430` |

The Linux checkout has no usable Git `HEAD` identity in the VM; the file
hashes and reported version are the comparison anchors.

## Runtime-to-source identity

The live Gemian diagnostic identifies camera 1 as `sp5509mipirawsls` and camera
0 as `non_sensor`. The source list contains conditional entries for both
`SP5509_MIPI_RAW_SLS` and `SP5509_MAIN_MIPI_RAW`.

The SLS implementation defines sensor ID `0x0556` and reads the 16-bit value
from register `0x0f16` without adjustment. The main implementation defines
`0x0557` and returns `read(0x0f16) + 1`. This explains why the ELF identity probe
and the live SLS name agree on raw ID `0x0556`, while the main and SLS sources
are not interchangeable.

Both implementations use the vendor's 8-bit write-ID convention. SLS probes
`0x40` then `0x50`, corresponding to Linux 7-bit addresses `0x20` and `0x28`;
main probes the reverse order. Each transaction uses a 16-bit register
address and 16-bit big-endian value: reads send two address bytes and receive
two data bytes, while writes send four bytes. The configured I2C speed is
300 kHz.

The `mainsubcam_flag` gate is a vendor module-selection policy: SLS proceeds
when the flag is nonzero and main proceeds when it is zero. It is not proof of
which physical camera connector is populated.

## Sensor link and modes

The SLS data contract recovered from `imgsensor_info` is:

| Property | Vendor value |
| --- | --- |
| MCLK | 24 MHz |
| Interface | 2-lane MIPI, NCSI2 PHY |
| Pixel format | RAW Gr first pixel |
| Preview/capture/video | 2592×1944, 176 MHz pixel clock, line length 2816, frame length 2083, 30 fps class |
| High-speed mode | 640×480, 120 fps class |
| Slim mode | 1296×972, 30 fps class |
| Mode programming | 16-bit register/value tables; output-size registers `0x0a12`/`0x0a14`, MIPI operation register `0x0902` |

The vendor tables contain stale comments referring to “Hi-556” and `0x30c8`;
those comments contradict the SP5509 symbols, IDs, filenames, runtime name,
and actual identity function. The symbols and register code, not the stale
comments, are the authoritative source evidence. The full mode tables are not
copied here.

## Power and board boundary

The vendor `kd_camera_hw` table associates SLS with this sequence:

1. enable camera MCLK;
2. assert reset low and power-down low;
3. enable DOVDD 1.8 V, AVDD 2.8 V, and DVDD 1.2 V;
4. wait 10 ms between the table steps;
5. deassert reset and power-down high.

The board DTS maps the two camera slots to reset/PDN pairs GPIO32/GPIO28 and
GPIO33/GPIO29, with GPIO73 and GPIO254 controlling camera AVDD/DVDD LDO pin
states. Which pair belongs to the runtime SLS module is not established by
the source alone. AFVDD is commented out for SLS, so an autofocus rail cannot
be inferred as required from this table.

## Linux 7.1.3 boundary

Linux 7.1.3 has no SP5509 driver or binding. Its OV5675 driver demonstrates
the reusable mechanics—V4L2 sub-device, fwnode endpoint, regulator bulk data,
standard controls, link-frequency/pixel-rate controls, and mode register
lists—but its chip ID, register map, mode tables, lane/link values, and power
sequence are silicon-specific and must not be copied to SP5509.

The correct implementation boundary is therefore:

- a new SP5509 V4L2 sensor driver using the recovered 16-bit I2C and mode
  contract, with explicit supplies, clocks, reset, and power-down GPIOs;
- a standard DT endpoint describing the verified two-lane link and link rate;
- a separate MT6797 SENINF/CSI/ISP media-controller backend, since Linux 7.1.3
  does not provide a matching Gemini capture pipeline; and
- no vendor `image_sensor`, `kd_camera_hw`, Android HAL, or private ioctl UAPI.

The source is enough to replace “sensor implementation unavailable” with a
reviewable driver-design input. It is not enough to select a physical I2C
address or enable a mode on hardware.

## Next safe gates

1. Keep all SP5509 nodes disabled in the mainline DT.
2. Correlate the runtime camera slot with GPIO/reset/PDN and CSI endpoint
   wiring using board evidence or an explicitly authorized read-only probe.
3. Add a disabled-only SP5509 DT schema/driver skeleton; do not issue the
   identity transaction until the exact bus and power owner are approved.
4. Recover MT6797 SENINF/ISP DMA and IOMMU ownership before attaching a media
   graph or streaming.

The new source evidence justifies a new sensor driver, while preserving the
reuse-first rule for the surrounding V4L2 and media frameworks.
