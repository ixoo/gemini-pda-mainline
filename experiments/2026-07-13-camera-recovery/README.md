# Experiment: Gemini camera identity and mainline boundary

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-13-camera-recovery` |
| Status | `completed` for read-only identity and static source comparison; mainline camera runtime remains untested |
| Subsystem | Camera sensor, autofocus, SENINF/ISP pipeline |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant is not independently established |
| Date(s) | 2026-07-13 to 2026-07-14 |
| Investigator(s) | Repository maintainer with Codex assistance |
| Tracking issue | None |

## Question or hypothesis

Which camera sensor is actually selected by the running Gemini image, and can
its sensor and MediaTek camera pipeline be represented by existing Linux 7.1.x
drivers rather than by copying the vendor camera ABI?

## Provenance and environment

- Live kernel: Linux `3.18.41+`, AArch64, Gemian Debian 9 userspace.
- Vendor source: Planet MT6797 tree commit
  `c5b0be85017ad0c599725e8273842efdbecdd88a`.
- Mainline comparison: Linux `7.1.3` in the development VM.
- Live device: `gemini@192.168.1.50` over the owner's private LAN.
- Private raw capture: `artifacts/device-inventory/20260713-live/camera.txt`
  (Git-ignored and access-restricted).
- Fresh read-only repeat: [`results/live-camera-repeat-20260714.txt`](results/live-camera-repeat-20260714.txt),
  with a stable SP5509 SLS identity and an additional vendor bus-8 camera
  wrapper visible in sysfs.
- Private userspace evidence is the immutable VM view at
  `~/reverse-engineering/gemini-vendor`; proprietary camera libraries are not
  copied into this repository.
- Vendor-kernel ELF evidence is the immutable VM file
  `~/reverse-engineering/work/gemini-kernel/vmlinux.elf`; its SHA-256 is
  recorded in `results/sp5509-vendor-elf-validation.txt`.

## Safety assessment

The live collector is read-only. It reads existing I2C/platform sysfs metadata,
the four vendor camera proc diagnostics, filtered `/proc/kallsyms`, device
names, and filtered kernel messages. It also enumerates existing adapter and
client objects; the candidate-address check is only a sysfs existence check,
not an I2C bus scan or transaction. It does not open a camera, read or write
I2C registers, change GPIOs or regulators, start streaming, access calibration
files, or write any device state.

The vendor camera proc files are used only because their read handlers return
short identity strings in this image. They are not treated as a general camera
control interface; future probes must source-audit any new proc entry before
reading it.

## Associated code

From the repository root:

```sh
mkdir -p artifacts/device-inventory/20260713-live
ssh -i artifacts/credentials/gemini_ed25519 \
  -o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes \
  gemini@192.168.1.50 'bash -s' \
  < experiments/2026-07-13-camera-recovery/scripts/collect-live-camera.sh \
  > artifacts/device-inventory/20260713-live/camera.txt
chmod 700 artifacts/device-inventory/20260713-live
```

The static comparison runs in the VM:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-13-camera-recovery/scripts/analyze-camera-contract.sh
```

The implementation-facing boundary is summarized in
[`results/mt6797-camera-mainline-design.md`](results/mt6797-camera-mainline-design.md).

The bounded ELF pass runs without executing the vendor image:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-13-camera-recovery/scripts/analyze-sp5509-vendor-elf.sh
```

The pinned vendor-source contract is checked without copying or building the
vendor camera sources:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-13-camera-recovery/scripts/analyze-sp5509-source-contract.sh
```

See the resulting [SP5509 source contract](results/sp5509-source-contract.md)
for the recovered IDs, I2C transaction format, mode tables, and power sequence.

The MT6797 camera-pipeline resource contract is recovered by a separate
source-only pass:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-13-camera-recovery/scripts/analyze-mt6797-camera-pipeline.sh
```

Its result is [MT6797 camera pipeline contract](results/mt6797-camera-pipeline-contract.md).

The current packaged-kernel boundary is audited with:

```sh
./scripts/dev-vm run bash -lc \
  'CURRENT_PACKAGE=/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-b7721ab55e41 \
   experiments/2026-07-13-camera-recovery/scripts/audit-current-package-camera.sh'
```

See the [current 77-patch package validation](results/mainline-camera-current-77-package-20260714.txt)
for exact config, module-tree, and DTB hashes. The older module-bearing
package record remains historical.

## Procedure

1. Confirm the key-only, noninteractive SSH path with `BatchMode=yes`.
2. Run the collector once while no camera application is active.
3. Compare the runtime identity strings and registered symbols with the pinned
   vendor DT/source and private HAL metadata.
4. Compare the identified sensor and MT6797 camera resources with Linux 7.1.3.

## Observations

- I2C camera wrapper devices are bound at live addresses `2-002d`
  (`kd_camera_hw`) and `3-0036` (`kd_camera_hw_bus2`). Their generic vendor
  compatibles are `mediatek,camera_main` and `mediatek,camera_sub`; these names
  do not identify a sensor.
- A third vendor control wrapper is bound at `8-0036` as `camera_main_hw` with
  driver `kd_camera_hw_trigger`; it is not a sensor client and must not be
  translated into a mainline sensor `reg` value.
- Main and secondary autofocus wrapper devices are bound at `2-0072` (`MAINAF`)
  and `3-000c` (`SUBAF`). The lens/voice-coil model is not identified by this
  capture.
- The live adapter topology maps the wrapper buses to controller windows
  `i2c2=0x11013000`, `i2c3=0x11014000`, and `i2c8=0x11009000`. No existing
  sysfs client object is present at candidate sensor addresses `0x20` or
  `0x28` on buses 2, 3, or 8. This is consistent with vendor code creating a
  camera client dynamically; it does not establish the physical sensor bus or
  address and no probe was attempted.
- Platform devices `1a040000.kd_camera_hw1` and `1a040000.kd_camera_hw2` bind
  to vendor `image_sensor` and `image_sensor_bus2`; `seninf0` through `seninf7`
  are present, and `/dev/camera-isp`, `/dev/camera-fdvt`, `/dev/camera-dpe`,
  `/dev/kd_camera_hw`, `/dev/kd_camera_hw_bus2`, and
  `/dev/kd_camera_flashlight` exist.
- The read-only vendor diagnostics report `AEON_CAMERA0=non_sensor` and
  `AEON_CAMERA1=sp5509mipirawsls`. This is the strongest direct runtime sensor
  identity captured so far. It does not prove whether the selected sensor is
  physically the main or secondary module without a separate orientation
  correlation.
- `/proc/kallsyms` contains the registered sensor entry points
  `sp5509_MAIN_MIPI_RAW_SensorInit`, `sp5509_MIPI_RAW_SensorInit_sls`,
  `OV5675_MIPI_RAW_SensorInit`, and `S5K5E2YA_MIPI_RAW_SensorInit`. The
  `sp5509` entry and the `AEON_CAMERA1` string agree; the other names are
  compiled-in alternatives, not proof of populated sensors.
- The private HAL libraries include `camera.mt6797.so`, `libcameracustom.so`,
  and `libSonyIMX230PdafLibrary.so`. `libcameracustom.so` contains strings for
  `SP5509_MAIN_MIPI_RAW`, `SP5509_RAW_SLS`, `OV5675_MIPI_RAW`, and
  `S5K5E2YA_MIPI_RAW`; those are capability/registration evidence and are not
  used to override the direct runtime identity.
- The pinned Planet tree contains separate SP5509 SLS and main implementations
  (`sp5509_mipi_raw_sls/` and `sp5509_main_mipi_raw/`), including sensor IDs,
  16-bit I2C transactions, mode tables, and sensor callbacks. The
  [source-derived contract](results/sp5509-source-contract.md) is sufficient
  design input for a new V4L2 sensor driver. The private camera HAL remains a
  stripped AArch64 ELF; its static identity and live runtime name independently
  corroborate SLS, but physical slot, populated address, and endpoint wiring
  remain unverified.
- The vendor-kernel ELF does contain the sensor implementation. Its SLS
  registration probes register `0x0f16` for raw sensor ID `0x0556`, at an I2C
  speed of 300 kHz, using two-byte register and two-byte response transfers.
  Candidate write-ID bytes include `0x40` and `0x50` (Linux 7-bit address
  candidates `0x20` and `0x28`); the capture does not establish which
  candidate is populated or whether the main and SLS tables select the same
  module.
- The main registration is a separate vendor function table. This confirms
  that the direct runtime name is backed by real code, but it does not convert
  the vendor wrapper addresses (`0x2d`/`0x36`) into a safe sensor `reg` value.
- Vendor board data supplies GPIO32/GPIO33 reset lines, GPIO28/GPIO29
  power-down lines, GPIO73/GPIO254 camera-rail GPIO controls, the camera PMIC
  rails (`vcama`, `vcamd`, `vcamaf`, `vcamio`), camera clocks, and the SENINF
  and ISP clock/power hierarchy. These controls are shared platform resources,
  not a complete sensor-specific DT description.
- The pinned Planet tree also contains the monolithic MT6797 `camera_isp.c`
  driver. It maps CAMTOP/CAM A/B, six CAMSV nodes, four explicit SENINF nodes,
  and the IMGSYS/CAMSYS windows, then exposes `/dev/camera-isp` through a
  private ioctl/mmap ABI. Its source-derived clocks, IRQ masks, and larb2/larb6
  M4U port table are recorded in the [pipeline contract](results/mt6797-camera-pipeline-contract.md);
  they are design evidence, not a mainline-compatible API.
- Bounded strings from the immutable vendor ELF enumerate shared camera
  resource labels (`vcamd_sub`, `vcamaf`, `vcama_sub`, `vcama_main2`,
  `vcamd_main2`, `vcamio_sub`, `vcamio_main2`, and cam0/cam1/cam2 reset,
  power-down, and camera-LDO pin states). `kdCISModulePowerOn` is table-driven;
  these labels do not prove which SP5509 module uses which rail or the exact
  sequencing.
- The current `linux-7.1.3-gemini-b7721ab55e41` package selects generic media,
  MT6797 CAMSYS clocks, IOMMU, and SMI support, but has no SP5509 or OV5675
  sensor module and no Gemini SENINF/CAM/CAMSV/ISP capture node. Its DTB keeps
  the image/camera syscon providers while disabling the camera SMI common node
  and both camera/image larbs. This is a package/DT boundary only; no camera
  module was loaded and no stream was attempted. See the [current package
  validation](results/mainline-camera-current-77-package-20260714.txt).

## Analysis

The populated runtime sensor is identified as an SP5509-family MIPI RAW sensor
(`sp5509mipirawsls`). The pinned Planet source now supplies the SLS/main
identity transactions, candidate I2C IDs, mode tables, and SLS power sequence;
the vendor ELF and live diagnostic independently corroborate the SLS path.
None of these sources proves the populated physical slot, address, endpoint,
or board-specific rail ownership. Linux 7.1.3 contains an OV5675 driver and
binding, but no SP5509 driver or binding. Therefore the OV5675 implementation
must not be selected by changing a compatible string; a new SP5509 V4L2 sensor
driver (or a carefully reviewed common backend only after register-level
identity/protocol comparison) is required.

The sensor driver is only one boundary. Linux 7.1.3 already has MT6797 camera
clock, SMI/IOMMU, power-domain, reset, `camsys`, `imgsys`, and `larb2/6`
building blocks. It does not provide a matching MT6797 SENINF/CSI2,
CAM/CAMSV, or ISP V4L2 pipeline driver. The vendor
`image_sensor`/`camera_hw`/`camera-isp` device ABI and Android HAL cannot be
treated as a mainline media graph. A future implementation needs a standard
V4L2 media-controller graph, explicit sensor supplies/clocks/reset, a
SP5509-specific control/mode table, and a separate MT6797 receiver/capture
backend with verified DMA/IOMMU port ownership. The vendor source also shows
six CAMSV register/IRQ nodes but only three CAMSV clocks and three configured
M4U ports; that discrepancy must be resolved before enabling more than one
capture path.

The existing OV5675 implementation is useful only as a framework example: its
V4L2 sub-device, fwnode endpoint, clock, regulator, reset, controls, and runtime
PM structure are reusable mechanics. Its chip ID, register addresses, mode
tables, lane limit, and link frequencies are silicon-specific and must not be
carried into SP5509 code.

The exact sensor I2C address, MIPI lane count/link frequency, orientation, and
autofocus actuator identity remain unmeasured. The generic vendor I2C labels
(`0x2d`/`0x36`) are wrapper addresses and must not be used as the SP5509 sensor
address without a source-audited, bounded identity transaction.

## Conclusion

`confirmed` for the named Gemian image's runtime identity string and vendor
registration path: camera 1 selects `sp5509mipirawsls`, while camera 0 reports
`non_sensor`. `inconclusive` for physical module mapping and all mainline
runtime behavior. The existing OV5675 driver is not a substitute for SP5509,
and a new sensor driver plus a substantial MT6797 camera pipeline boundary is
needed.

## Follow-up

- Preserve the sensor and platform nodes disabled in mainline until the exact
  SP5509 register ID, populated candidate address, reset sequence, lanes,
  clocks, and supplies are correlated to the physical module.
- Use the ELF-derived `0x0f16`/`0x0556` transaction only as a design input for a
  future, explicitly authorized read-only probe. Do not use generic
  `i2cdetect`, arbitrary writes, or camera streaming as an identity probe.
- Recover the MT6797 SENINF/CSI/ISP register and DMA contract from vendor
  symbols, source, and controlled traces before adding a media-controller
  driver.
- Update the camera row in [`docs/HARDWARE_SUPPORT.md`](../../docs/HARDWARE_SUPPORT.md)
  only after those contracts are independently validated.
- Use the [mainline design boundary](results/mt6797-camera-mainline-design.md)
  to stage sensor, receiver, and capture work as separate reviewable changes;
  do not re-create the Android camera ioctl ABI.
