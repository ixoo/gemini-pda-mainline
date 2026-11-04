# Experiment: the front camera's sensor from a module on the station

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-04-gemini-camera` |
| Status | `running`: hardware map done, chip ID test not run |
| Subsystem | Hi-556 sensor, I2C3, MT6351 camera rails, ISP power domain, CAMSYS clocks, SENINF master clock |
| Device variant | Planet Computers Gemini PDA, MT6797X, boot2 station |
| Date(s) | 2026-11-04 |
| Investigator(s) | project session, device custody with the custodian session |
| Tracking issue | none |

## Question or hypothesis

Can modules on the mainline station power the front camera's sensor and read its
chip ID over I2C?

Hypothesis: with the ISP domain up, master clock 1 running at 24 MHz on CMMCLK1 and
the three rails on, register `0x0f16` at 7-bit address `0x20` on I2C3 reads `0x0556`,
then the driver powers the sensor back off.

This is the first milestone and stops before streaming. It proves the sensor's power,
clock and control path. It says nothing about the receiver or an image.

## Provenance and environment

- Linux 7.1.3 with the station series, profile `mt6797-a53-station-a72`.
- Public vendor kernel `gemian/gemini-linux-kernel-3.18`, commit
  `8cfe6596a503612e3332d9c26e292a19525a7f07`.
- Retained Gemian logs and the DTB of the retained vendor boot image, read privately;
  only the facts below are recorded.
- The vendor camera library `libcam.halsensor.so`, SHA-256 prefix `6faba2ed96b8`,
  disassembled in the development VM; only the register use below is recorded.
- Prior records: [camera identity](../2026-07-13-camera-recovery/README.md) and
  [camera path review](../2026-10-04-gemini-camera-re/README.md).

## Design

The sensor is a Hi-556 that the vendor calls SP5509, and upstream has a driver for
that chip, so this uses it rather than a new one. It needed a device tree match, a
power-down pin, a 24 MHz clock and ordered rails
([0546](../../patches/proposals/0546-media-i2c-hi556-support-device-tree-and-a-power-down.patch),
[0547](../../patches/proposals/0547-media-i2c-hi556-accept-a-24-MHz-input-clock.patch)).

The master clock comes from a generator in the sensor interface block. That is a new
driver,
[0548](../../patches/proposals/0548-media-mediatek-add-the-MT6797-sensor-interface-s-mas.patch),
that only exposes the four generators as clocks for now. The CSI-2 receivers it will
later drive live in the same register window, so a later patch grows this driver
instead of replacing it.

Two things the station lacked:

- The ISP power domain. The station uses the newer power controller, whose MT6797
  table had no such domain
  ([0543](../../patches/proposals/0543-pmdomain-mediatek-describe-the-MT6797-ISP-domain.patch)).
- A correct CAM clock provider. Its IDs started at 1 with one slot per gate, so
  registering the last gate wrote past the array, the defect the
  [clock allocation record](../2026-09-08-mt6797-clock-id-allocation/README.md)
  found in its siblings. Nothing consumes the numbers yet, so they now start at 0, and
  the provider holds the domain around its registers
  ([0544](../../patches/proposals/0544-clk-mediatek-mt6797-cam-number-from-zero-and-use-run.patch)).

The board changes are in the station DTB only
([0550](../../patches/proposals/0550-arm64-dts-mediatek-gemini-station-describe-the-front.patch));
the release DTB gains only a disabled SoC node. The drivers and the media core are
modules that nothing loads at boot. What a boot does change: I2C3 registers with no
bound client, the ISP domain is registered and left off, and the rails have fixed
voltages set and are switched off if found on.

## Safety assessment

- No calibration, no protected partition. The new image goes to boot2 through
  `flash-boot2`.
- The rails carry only what the vendor selects: selectors 3, 6 and 6, for 2.8 V, 1.21 V
  and 1.8 V. The vendor DTB names no other consumer of them.
- The first ISP domain power-on under this kernel. It polls with a timeout, so a stuck
  domain is an error rather than a hang.
- Reading CAMSYS or SENINF with the domain off can stall the bus. Both drivers access
  them only under runtime PM. No `devmem` read of these windows is admitted without
  the domain held on.
- A failed probe removes power: the driver's error path disables the rails and clock.

## Associated code

Patches 0543 to 0550 and
[`gemini-a53-station-camera.fragment`](../../configs/gemini-a53-station-camera.fragment).

## Procedure

See [T1](#t1-the-chip-id) below.

## Observations

### From retained evidence, with no device access

- The fitted sensor answers at write ID `0x40`, 7-bit `0x20`, with ID `0x0556`, on all 58
  such lines in the retained Gemian boot logs. The driver's probe of the main
  socket reads `0x1` and fails on the same boots, which fits an empty rear socket.
- The HAL runs that probe by itself about 10 s into a Gemian boot, so this needs no
  camera application. The same logs show the rail selectors above.
- The vendor DTB places `camera_sub` on `i2c@11014000` at 400 kHz, confirms reset on
  GPIO33 and power-down on GPIO29, and names no other consumer of the three rails.

### Register use, from the disassembly of `SeninfDrvImp::setMclk2`

Base `0x1a040000`, the second generator at `+0x1600`:

| Register | Write | Meaning |
| --- | --- | --- |
| `+0x0000` | set bits 10 and 11 | clock enables shared by the sensor interface |
| `+0x1604` | divider `n-1` in `[21:16]`, `0` in `[13:8]`, `n/2` in `[5:0]` | divide by `n` |
| `+0x1600` | `[1:0]` = 1, bit 2 = `~(n-1) & 1`, bit 28 polarity, bit 6 pad inversion | source and edges |
| `+0x0600` | `[1:0]` = 1 | the first generator's source, written whichever is used |
| `+0x1600` | set bit 31 | phase counter on |

The GPL kernel sets bits 31 and 29 of the same register, the second being the output
enable (`ISP_MCLK2_EN`). 24 MHz is `n` = 2 from CAMTG at 48 MHz from `univpll_d26`.

## Inference

- CMMCLK1 on GPIO31 carries this generator's clock. The pad and the generator pair up
  by number and the vendor's main-socket code uses the first of each, but no source
  states it. T1 tests it only if the sensor needs the clock to answer.
- The [earlier review](../2026-10-04-gemini-camera-re/README.md) called the receiver
  programming an irreducible blocker. It is not: the same library exports the sequence
  with symbols (`setSeninf2CSI2`, `setSeninfMuxCtrl`, `setSeninfTopMuxCtrl`), and the
  DMA side is in `IspDrvCamsv` in `libimageio_plat_drv.so`.

## Negative results

None yet.

## Limitations

- A chip ID is not capture. No image, no receiver, no lane or link frequency evidence.
- 437 MHz in the DTB is the only rate the driver takes, and is unmeasured at 24 MHz.
- One unit.

## T1: the chip ID

Not run.
