# Experiment: the front camera's sensor from a module on the station

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-04-gemini-camera` |
| Status | `running`: hardware map done, no chip ID in T1 to T3; the sensor stays silent with the bus and rails shown good |
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

- T1, T2, T3 and T5: no chip ID, in 145 reads across them. See [below](#t1-the-chip-id).
- T3's script wrote to physical address 0 three times by mistake. See
  [below](#a-script-error-writes-to-address-0).

## Limitations

- A chip ID is not capture. No image, no receiver, no lane or link frequency evidence.
- 437 MHz in the DTB is the only rate the driver takes, and is unmeasured at 24 MHz.
- One unit.

## T1: the chip ID

Boot `887dc12b-64fa-4025-bb9e-e0fda2deed68`, image `29fc6fce`, package `94295c1c` from
commit `9770e90f`, one run of one probe, as reported by the custodian.

Observed:

- The image booted with the native display bound, USB SSH and no taint. I2C3 came up as
  `i2c-4`, so the client is `4-0020`. The ISP domain and the rails registered with no
  warning. `vcamd` moved from 1.2 V to 1.21 V.
- `clk-mt6797-cam` and `mt6797-seninf` loaded and probed. The ISP domain cycled at least
  that far with no stall, and its status bit read clear afterwards. Whether it was on
  during the probe was not sampled.
- `hi556` passed its 24 MHz clock check, then failed at the chip ID with `-5`, after
  12 ms. The rails read disabled afterwards, and bit 5 of `PWR_STATUS` clear. No
  controller message, no Oops. The I2C3 controller had taken one interrupt.

Inference: `-5` is the driver's own code for any failed transfer, so the real error was
not seen. One interrupt with no timeout message fits a NACK on the address rather than
a dead controller, but this is not shown. Nothing here tells rail, pin, clock or timing
apart. The rail enable and voltage registers match the PMIC's documented layout.

No retry. T2 holds the power on to read the state.

## T2: the state while powered

Same boot, module `c5638225` from commit `95330518`, one run of 14 s, as reported by the
custodian.

Observed during the hold:

- `vcama`, `vcamd` and `vcamio` read enabled at 2.8, 1.21 and 1.8 V.
- The ISP domain read on (bit 5 of `PWR_STATUS` and its second copy), the first time it
  is seen on under this kernel, and off again at the end.
- `seninf_mclk1` read 24 MHz, from `cam_camtg` at 48 MHz, from `camtg_sel` on
  `univpll_d26`.
- CAMSYS `0x1a000000` read `0xe3f`, so bits 6, 7 and 8 are ungated. SENINF read
  `+0x0000` `0xc00`, `+0x1600` `0xa0000001`, `+0x1604` `0x00010001`, as written.
- GPIO29 and GPIO33 read output, high, and high at the pad. GPIO31 read mode 1. GPIO74
  and GPIO75 read mode 1, high, so the bus idles high.
- All 14 pairs of reads at `0x20` and `0x28` returned `-6`, before and after one reset
  and power-down pulse in the vendor's order and step lengths.
- A read of the AW9120 at `0x2c` also returned no ACK, with its enable GPIO245 low.

Inference: `-6` is the address going unacknowledged, not a timeout. Sensor timing is
unlikely after 14 s and a pulse. This does not show that the bus works, because the only
other chip tried was in shutdown, or that the clock reaches the pad, or that the rails
are really up, because sysfs reports only the enable bit.

The live vendor kernel's power table for this sensor matches the public source: clock,
reset low, power-down low, then 1.8, 2.8 and 1.2 V, reset high, power-down high. Its
pin states for this socket are GPIO33 and GPIO29. The vendor kernel's own bus selection
is the same as read in the public source.

## T3: clock at the pad, rails, and another chip on the bus

Same boot, module `caa443a8` from commit `74f2fcd2`, script `afc3fb46`, one run of 30 s, as
reported by the custodian.

Observed:

- The AW9120 returned its ID, `b223`, with its enable raised for a moment. So this bus
  and controller do get an ACK from a known chip at `0x2c`.
  The owner saw no LED flash during the run.
- The PMIC's own status: `0x0a12` `da62`, `0x0a40` `c262`, `0x0a58` `c262`, bit 15 set on all
  three, and selectors 3, 6 and 6. So the three rails are up at the vendor's voltages.
- All 60 reads at `0x20` and `0x28` returned `-6`, across the pulse.
- GPIO30, 31, 35 and 36 read input level 0 on every sample, with and without the
  generators on.
- Through the error below, generators 1, 3 and 4 stayed on for about 20 s of the hold. GPIO30
  and GPIO31 were in clock mode, GPIO35 and GPIO36 were not. The sensor stayed silent.

Inference: rail and bus faults are out. The sensor is silent with its rails up, its
reset and power-down high, and its bus working. The clock not reaching the sensor is the
leading candidate, because this class of sensor usually needs it to answer I2C, but it
isn't shown: a level of 0 proves nothing if the pad's input path is off in clock mode.
A wrong generator for CMMCLK0 or CMMCLK1 is unlikely, since all four were on. CMMCLK2 and
CMMCLK3 were not tried, since those pads were not in clock mode. Pad drive strength is also
open: the vendor library sets it (`setMclk2IODrivingCurrent`, bits 3:2 of `0x100020f0`) and
this kernel does not, since its MT6797 pin driver has no drive, pull or input-enable
tables.

### A script error: writes to address 0

`camera-t3.sh` used a shell variable `a` in a helper function and also for the generator
address in its loop, so the restore step ran as `devmem 0 32 VALUE`. Three unrequested
writes went to physical address 0: `0x00000001`, `0x00000000`, `0x00000000`. The readbacks
read address 0 and returned 0, so the generators weren't restored and ran about 20 s beyond the 2 s
asked. The author's error; the custodian found it in the output.

No fault followed: no abort, no Oops, not tainted, pstore empty, uptime continuing. What is at
physical address 0 is not established, and `/proc/iomem` lists nothing there. No effect
was observed, which does not show there was none.

Later scripts share no shell variables across functions, and no `devmem` write uses an
address from a variable. Further tests list literal addresses, read-only unless the
owner has approved a write.

## T4: the pad configuration

Same boot, one read-only run, with the rails and clock off, so these are the pads at rest
and aren't shown to hold during a hold. `0x10002000` read `0xfff`, so input is enabled on all ten
CAM pad bits. `0x10002040` `0x000c381f`, `0x100020b0` `0x400`, `0x100020d0` `0xb80`,
`0x100020f0` `0x05555555`. Bits 3:2 of the last are the drive of the pad the vendor library
calls MCLK2, and read 1.

Inference: GPIO74 and GPIO75 read high in mode 1, so a pad's input level does report in a
non-GPIO mode. With input enabled, GPIO31 reading 0 on all 96 samples under its generator
means it is probably not toggling, rather than that it can't be seen, assuming input
enable stays set while the clock runs. T5's samples are the direct test. So the clock is
probably not reaching the sensor, with its registers all reading as written.

## Offline: the CAMTG mux needs an update write

The vendor kernel's `clk-mt6797.c` selects `MUX_CLR_SET_UPD` for its top muxes, with `0x04` as
the update register and bit 8 for CAMTG, and its enable, disable and set-parent all write
that bit. The live vendor kernel carries those functions. This kernel's `clk-mt6797.c` uses plain
`MUX_GATE` for `camtg_sel` and never writes the update register. The vendor's own mux
therefore applies selection through a step this kernel omits, so `0x10000060` can read as asked
while the hardware still runs the old setting.

Also settled: the live kernel sets bus 3 for this socket, and the library's power-on sets
the master clock's drive, which is an open and separate difference.

T5 tested this on the device and did not support it as the sole cause.

## T5: the mux update write

Same boot, module `caa443a8`, script `ee9e8f6b`, one run of 14 s, as reported by the
custodian. The owner approved the write. `0x10000060` read `0x01010001` and `PWR_STATUS` showed
the ISP domain on, then `0x00000100` was written once to `0x10000004`.

Observed: GPIO31 read 0 on 64 of 64 samples before the write and 64 of 64 after. All 28
chip ID reads returned `-6`, with none after the write differing. No fault. The PMIC and
the AW9120 answered as in T3.

Inference: the omitted update is not, by itself, why the sensor is silent. This is one
write with the gate already open, nothing shows the mux took it, and the timing of the write
against the reads comes only from the script's order. The gap in `clk-mt6797.c` remains a
real difference from the vendor kernel, whether or not it matters here.

Nothing has yet shown GPIO31 toggling under any kernel, so the sampling method itself is
unproved for a pad known to be running.

The custodian repeated T5 once at the owner's request, on the same boot, to watch for an
LED; the update write ran again. GPIO31 again read 0 of 64 before and after. Of the 28 reads,
27 returned `-6` and one returned `-110`, at `0x20` about 3 s after the pulse, with the probe
taking about 2 s longer. The next pair went back to `-6`. No controller message was seen,
and the AW9120 read and the end state were as before.

This is the first timeout on this bus. One event shows only that a transfer stalled once.
Whether the sensor held the bus, which would mean it is alive, or the controller stalled is
not shown, and nothing was sampled at that moment. No more I2C on this bus this boot.

## G1: the stock system driving the sensor

Gemian `3.18.41+`, boot `eb8ddd2f`, one read-only sampler over one `cameraserver` restart, as
reported by the custodian. The owner approved the boot. Nothing was written by this test.

Observed:

- `sp5509 i2c write id: 0x40, ReadOut sensor id: 0x556` at both boot-time probes and after the
  restart. So the module answers on this unit today, at 7-bit `0x20`.
- GPIO31's input level read 1 on 54 % and 56 % of samples while the ISP domain and CAMTG were on
  with reset high, and on 11 % of 23352 with them on before reset rose. It read 0 on all 565255
  samples with them off. So this sampling sees the clock, and the clock runs before reset.
- Order: ISP domain on, CAMTG gate open within 0.2 ms, then about 460 ms later reset high, then
  power-down high 10 ms after it. Each cycle held about 60 ms.
- `0x100020f0` read `0x0555575d` against mainline's `0x05555555` at rest. `0x10000060`'s CAMTG
  byte and GPIO31's mode match mainline. `0x10002040` differs only outside the camera bits.

Inference: mainline's sensor is silent because its master clock is not running at the pad.
The samples on mainline were fewer and slower, 64 to 96 reads, but a toggling pad would not
read 0 on all of them. The hold's pulse ends with power-down low then high, unlike the vendor's
reset first; that is not the cause while there is no clock.

What stops the clock is not known. Mainline's generator and gate registers read as written, and
nothing has read the vendor's. T6 compares the remaining registers and tries the two vendor
differences that a hold can test.

The G2 read of the vendor's CAMSYS and SENINF registers did not run, as Gemian had already shut down.
