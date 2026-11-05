# Experiment: the front camera's CSI-2 receiver on the station

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-04-gemini-camera-receiver` |
| Status | `running`: the owner saw the front camera on the panel through a diagnostic path, with no capture node |
| Subsystem | SENINF second interface, MIPI RX analog, CSI-2, Hi-556 streaming |
| Device variant | Planet Computers Gemini PDA, MT6797X, boot2 station |
| Date(s) | 2026-11-04 |
| Investigator(s) | project session, device custody with the custodian session |
| Tracking issue | none |

## Question or hypothesis

With the vendor library's receiver setup, does the sensor's test pattern reach the second interface's
mux at the right size, without CSI-2 errors?

Hypothesis: with colour bars on, `+0x1d0c` reports 2592 by 1944, the frame and line register at `+0x1730`
changes between reads, and `+0x1714` shows no error bits.

This proves a link. It needs no DMA and produces no image: the data stops at the mux.

## Provenance and environment

- Linux 7.1.3 with the station series, profile `mt6797-a53-station-a72`.
- The vendor camera library `libcam.halsensor.so`, SHA-256 prefix `6faba2ed96b8`, decompiled in the
  development VM. Only the register use below is recorded.
- Prior records: [the sensor from modules](../2026-11-04-gemini-camera/README.md) and
  [the Gemian driver split](../2026-11-04-gemian-camera-driver-re/README.md).

## Design

`mt6797-seninf` gains the receiver for the second interface
([0555](../../patches/proposals/0555-media-mediatek-mt6797-seninf-add-the-CSI-2-receiver.patch)): analog
block at `0x10217400` and `+0x200`, NCSI2 at `+0x1700`, calibration at `+0x1838`, mux at `+0x1d00`. It binds
the sensor through the graph, which also creates the sensor's sub-device node. The graph needs a new DTB
([0554](../../patches/proposals/0554-arm64-dts-mediatek-mt6797-describe-the-sensor-interf.patch)), so this
takes one boot.

With no capture node to start a stream, a debugfs file does it and reads the status
([0556](../../patches/proposals/0556-media-mediatek-mt6797-seninf-DIAGNOSTIC-debugfs-to-s.patch)), to be dropped
later.

Choices that may need revisiting, each adjustable with no build except the first:

- The per-unit trim the library writes to the analog block from fuses is left out.
- The settle count is computed from the vendor's 14 ns at the 325 MHz this kernel runs `mm_sel` at, giving 5.
  The vendor's clock may differ. Debugfs `settle` sets it.
- `hsrx_delay` is on by assumption. Debugfs sets it.

## Safety assessment

- No calibration data, no protected partition. Sensor register writes are the driver's tables, to RAM.
- The analog and NCSI2 writes run only from the stream path, with the ISP domain held by runtime PM.
- A stream is short and bounded in each test.
- A new image goes to boot2 through `flash-boot2`.

## Associated code

Patches 0554 to 0556.

## Procedure

R1 below.

## Observations

See R1 below.

## Inference

See R1 below.

## Negative results

None yet.

## Limitations

- No frame has been captured, so pixel content is unknown.
- 437 MHz is not known to be the link rate at 24 MHz.

## R1: the first stream

Image `da1894c0`, package `e3799238`, commit `7d5269ff`, boot `c1ab6349`, one run, as reported by the
custodian. The owner approved the image write, the boot and the stream's effects. Colour bars selected,
stream on for 3 s, status read once a second.

Observed:

- `/dev/v4l-subdev0` appeared, and the sensor bound to the receiver.
- The stream started and stopped cleanly, with no fault, rails off and the ISP domain off afterwards.
- `+0x1d10`, the mux's first debug word, read `7690c01e`, `8690c03c`, `7690c05a`: its low byte moved by 30 a
  second.
- `+0x1d14` and `+0x1d18` read `0a200798` on all three reads. These are 2592 and 1944.
- `+0x1714` read `0x00001014` and `+0x1d08` read `0x00000058`, unchanged on all three, cleared by each read.
- `+0x1d0c`, where the size was expected, and `+0x1730`, where a frame number was expected, read 0.
- The calibration status words read 0. The vendor library treats 0 as a failed calibration and carries on.
- `+0x172c` moved between `01011010` and `01010101`.

Inference:

- The sensor's CSI-2 data is reaching the mux, and 2592 by 1944 is being measured there, at about 30 frames a
  second. This holds with the receiver's analog setup from the library and no per-unit trim.
- The hypothesis's register choice was wrong for size and frame number. The size is seen elsewhere.
- Status bits remain to explain, so "no errors" is not shown. Bit 4 of `+0x1714` looks like a header error
  flag, and three bits of `+0x1d08` look like size checks, which may just be against a configured size that
  is still 0. R2 varies the settle count to separate them.
- Nothing shows the pixels are correct. Nothing has been captured.

## R2: the settle count

Same boot, script `5361e336`, ten streams of about 3 s, as reported by the custodian, under the approval for
R1.

Observed: settle counts 5, 10, 14, 24 and 40, each with the HSRX delay on and off, gave the same picture.
`+0x1714` read `0x00001014`, `+0x1d08` read `0x00000058`, `+0x1d14` and `+0x1d18` read `0a200798`, the low byte of
`+0x1d10` read `3c` after 2 s, and calibration read 0, every time. The top bytes of `+0x1d10` varied, and its second
byte fell to `00` at the last setting, which is not interpreted.

Inference: the receiver takes the link across this whole range, so settle is not critical here and is not
what sets those bits. Whether they are errors stays open. Capturing a frame would answer more than further
status reads.

## C1: one frame to memory

Image `b7b2cbbe`, package `490eea01`, commit `a2462905`, boot `5e582d21`, one run, as reported by the custodian.
The owner approved the write, the boot and the DMA. Before the run the custodian unmounted the data partitions
and set the eMMC read-only, as a precaution against corruption, and treats this boot as suspect.

[`0558`](../../patches/proposals/0558-media-mediatek-mt6797-seninf-DIAGNOSTIC-capture-one-.patch) ran the first CAMSV into a
coherent buffer at `0xfeb00000`, with `larb2` in its reset state and no M4U.

Observed: the capture returned 0 with no fault. All 6298560 bytes kept their fill value, and no guard byte
changed. The generator read enabled, and `CAMSV_INT_STATUS` read 0 with its enable written 0.

Inference: nothing landed in the buffer, and this does not show that nothing was written elsewhere. A likely cause
is in the code: the vendor library gates this DMA behind frame buffer control, which this test left off.
Whether the sensor's data reached the first CAMSV at all was not logged.

## C2: through frame buffer control

Module `5fe9b698`, fresh boot `89e2dfe5`, one run, as reported by the custodian. The owner approved it, and the eMMC was
set read-only first. [`0559`](../../patches/proposals/0559-media-mediatek-mt6797-seninf-DIAGNOSTIC-capture-thro.patch)
added frame buffer control with one buffer.

Observed, with register names from the vendor kernel:

- `CAMSV_TG_DAT_NO` reached `0x4ce2ff`, one short of 2592 by 1944 pixels, and `CAMSV_TG_FRMSIZE_ST` read `0a200799`.
- `CAMSV_INT_STATUS` went through `0x87` to `0x0010040f`: vertical sync, the two generator states, the start of frame,
  and both pass-done bits. `SV_TG_ERR`, `SV_TG_GBERR`, `SV_IMGO_ERR` and `SV_IMGO_OVERRUN` stayed clear.
- `CAMSV_FBC_IMGO_CTL1` read `01408000` on every line, `CTL2` and `CUR_ADDR` read 0, and the CAM mux read `11111110`.
- All 6298560 bytes kept their fill value. No guard byte changed. No fault.

Inference: this shows the sensor's data reaching CAMSV as a full frame with this CAM mux. Which entry matters is still
not separated. The DMA did not write the buffer. The registers are double-buffered, so one frame in single mode may
run before they load, which is what C3 tests. Writes elsewhere are not ruled out.

## C3: continuous

Module `14ebc561`, script `ac9d99a1`, fresh boot `4d00c1ce`, one run, as reported by the custodian. The owner approved it,
and the eMMC was set read-only first. [`0560`](../../patches/proposals/0560-media-mediatek-mt6797-seninf-DIAGNOSTIC-capture-with.patch)
ran the generator continuously for about 264 ms.

Observed:

- All 6298560 bytes kept their fill value. No guard byte changed. No fault, no taint.
- `CAMSV_FBC_IMGO_CTL2` went from 0 to `04000000`. Only its top byte moved. `CUR_ADDR` read 0 on every line.
- The top bytes of `CAMSV_TG_INTER` reached 8, about one step per 33 ms.
- `CAMSV_INT_STATUS` bit 19 was set on exactly the four lines where the top byte of `CTL2` stepped, and clear on the two
  where it did not. The vendor header does not name bit 19.
- `SV_IMGO_ERR` and `SV_IMGO_OVERRUN` stayed clear. `SV_SW_PASS1_DON_ST` appeared only on the first line.

Reading the public vendor kernel's layout for these registers, on the CAM block at the same offsets:

- The top byte of `CTL2` is `DROP_CNT`. `FBC_CNT`, `RCNT` and `WCNT` below it stayed 0.
- In `CTL1`, bit 16 is `FBC_MODE`, which the same kernel reads as queue mode, and the top byte is `SUB_RATIO`. The vendor
  library logs the value it writes there as the subsample.

Inference: the block counted these frames as dropped, and it counted no write. Four drops in eight frames fits a
subsample ratio of 1 skipping every other frame. That is a correction to `0559`, which is wrong in two places: it named
bit 16 a flush and cleared it, where the vendor library sets it and leaves it set, and it wrote 1 to the top byte as a
buffer count. With queue mode off and `FBC_NUM` 0, no buffer was ever available. This also replaces the double-buffer
idea from C2, which C3 does not support. The evidence for no stray writes is these counters, not a check of memory:
the layout comes from the CAM block, and nothing read the rest of memory.

## C4: queue mode and larb2

[`0561`](../../patches/proposals/0561-media-mediatek-mt6797-seninf-DIAGNOSTIC-queue-mode-a.patch) sets `CTL1` the way the
vendor library does. This should make the DMA write for the first time, so it first reads larb2 and refuses to start
CAMSV if `0x380-0x3fc` or `0xf00-0xffc` is non-zero, the check the display path made on larb0 and larb5.

Read step: module `fad7c14c`, script `1e788988`, fresh boot `d9722def`, one run, as reported by the custodian. No DMA ran.

Observed: `0xfc0` read `00003fff`, and nothing else in either window was set. The check refused, as designed, and no
capture ran. No fault.

Inference: `0xfc0` is the larb's MMU enable, per the [M4U and SMI record](../2026-07-12-mt6797-m4u-smi-recovery/results/mt6797-m4u-smi-mainline-design.md)
and the mainline SMI driver. The vendor kernel writes one bit per port, and larb2 has 14 ports, which are the 14 bits
set. So every larb2 port, CAMSV0's among them, goes through an M4U that nothing here has set up. A physical address
would be wrong on this path, and the earlier check would not have made it right. This differs from display: larb0 and
larb5 read zero. Not known: whether `0x3fff` is the reset value or set by earlier firmware, and what the hardware does
with such a write while M4U is off.

C1 to C3 are not explained by this: C3's counters show drops before any write was attempted.

## The display timeouts after C3 and C4

Observed, as reported by the custodian: on the C4 read boot `d9722def`, "vblank wait timed out on crtc 0" and a warning in
`mtk_crtc_atomic_disable` at the first blank after the read, 27 s later, tainting the kernel. Blanks before the read on
the same boot gave none. C3's boot has the same timeout. `mm_smi_common` read `en=0 prep=0` afterwards. The earlier "no
fault" reports for C1 to C4 checked straight after the capture, before any blank, so they did not cover the display.
The C1 and C2 boots were powered off before a blank, so they neither show it nor clear it.

Inference, from the code rather than a read of the gate: my capture path caused this.
[`0558`](../../patches/proposals/0558-media-mediatek-mt6797-seninf-DIAGNOSTIC-capture-one-.patch) enabled and disabled
`CLK_MM_SMI_COMMON`, bit 0 of the MMSYS gate at `0x14000100`. The station has no SMI driver, so nothing counts that
clock while the display relies on the gate the loader left open. The count went from 1 to 0 and closed it.

Other clocks on this path: `cam_*` gates are in CAMSYS, in the ISP domain, so the display does not use them. `mm_sel`, the
parent of most of them, is a plain mux with no gate, and `camtg_sel`'s gate belongs to the sensor clock.

[`0563`](../../patches/proposals/0563-media-mediatek-mt6797-seninf-DIAGNOSTIC-leave-the-sh.patch) stops touching the clock,
reads the gate, and refuses to capture if it is closed. Holding the clock from here instead would close the gate at
unload. A real driver needs a proper owner for this clock.

## C5: CAMSV0 bypasses M4U

Module `edd4aa70`, scripts `ca621f8a` then `2b1d42b8`, fresh boot `be93adeb`, one run each, as reported by the custodian.
The owner approved each step and checked the screen after the first. The eMMC was read-only throughout.
[`0562`](../../patches/proposals/0562-media-mediatek-mt6797-seninf-DIAGNOSTIC-bypass-M4U-o.patch) clears bit 6 of `0xfc0`,
port 6 being `M4U_PORT_CAM_SV0` in the mainline port header, and leaves the other ports alone.
[`0563`](../../patches/proposals/0563-media-mediatek-mt6797-seninf-DIAGNOSTIC-leave-the-sh.patch) leaves the shared gate
alone.

Observed:

- `0xfc0` went from `00003fff` to `00003fbf`, and nothing else in either window was set.
- MMSYS `CG0` read `00110000` at every read, so the SMI common bit stayed clear. Blank and unblank returned 0, with no
  timeouts and tainted 0, before the load, after the set and after the capture. The screen was asked about after the set
  only.
- "0 of 6298560 bytes still fill, 0 guard bytes changed". No fault.
- `CAMSV_FBC_IMGO_CTL2` started at `00000101` (`FBC_CNT` 1, `RCNT` 1) and moved to `01010100`, then `WCNT` stayed 1 and
  `DROP_CNT` rose to 7. `CUR_ADDR` read `feb00000` and then 0.

Decoding the frame, which stays private:

- The whole frame holds two distinct lines, one for the even rows and one for the odd, so no line was corrupted.
- Packing: 10-bit little-endian, 4 pixels in each 5 bytes, stride 3240.
- Eight bars of about 324 pixels, plus 4 pixels at the right edge that differ. Read as the usual white, yellow, cyan, green,
  magenta, red, blue, black, the cell is Gr, R on even rows and B, Gb on odd. That agrees with the vendor driver's Gr first
  pixel. The order of the bars is assumed.

Inference: this is the first frame in memory on mainline. CAMSV wrote one frame and dropped the rest, as queue mode
with one buffer should, and the two faults above were the blockers. Bypass is shown to reach the buffer. Stray writes
elsewhere are not ruled out by this, and the display check is the only evidence on that.

## D1 and D2: the camera on the panel

Module `3e157761`, boot `6a422120`, fresh, no image write, as reported by the custodian. The owner approved each step, and
the eMMC stayed read-only. [`0564`](../../patches/proposals/0564-media-mediatek-mt6797-seninf-DIAGNOSTIC-a-rough-pict.patch)
builds a panel-sized picture from each frame, and a script copies it to the framebuffer: one RGB pixel per Bayer cell, black
level off, a square-root curve, no colour balance or shading correction, and no auto exposure.

D1, colour bars, script `ea49f4bc`, once: all return codes 0, 0 guard bytes changed, no timeouts, tainted 0. The owner: "it
works yes I see the bars". Colour wasn't judged by eye, and the edges were not reported.

D2, the real view, script `8d95fc84`, five stills at default exposure and gain, about 3.8 s each: every capture and copy
returned 0, 0 guard bytes changed each time, and 70 to 130 bytes matched the fill value, which real data would do by
chance. Blank and unblank returned 0, with no timeouts, tainted 0, rails disabled, and MMSYS `CG0` `00110000`. The owner:
"it all worked!!!!". Colour wasn't judged by eye. Orientation, mirroring and exposure were not reported, so nothing here
says the picture was upright or well exposed. No frame was saved.

Limits of this result:

- Debugfs and a script, not a V4L2 capture node. Stills only, with the sensor powered up and down around each.
- CAMSV0 bypasses M4U through a larb2 bit cleared by hand. The other 13 larb2 ports still have MMU enabled.
- Stray writes elsewhere are not ruled out. The evidence is the guard, the counters and a clean display check.
- The SMI common clock has no owner. The capture relies on the loader leaving it open.
- One boot on one unit, with the diagnostics of `0556` and `0558` to `0564` in the module. Status bit 4, the mux status,
  the CAM mux entry and the receiver calibration reading zero remain unexplained.

## N1 and N2: the capture node

- [`0568`](../../patches/proposals/0568-media-mediatek-mt6797-seninf-add-a-capture-node.patch) replaces the debugfs capture with
  a video node and a media graph from sensor to receiver to CAMSV0. It uses vb2-dma-contig and keeps one buffer in frame
  buffer control at a time, because whether the hardware holds more than one address has not been tested. The interrupt
  completes a buffer when the write count moves.
- [`0566`](../../patches/proposals/0566-media-v4l-add-the-MediaTek-packed-10-bit-Bayer-forma.patch) adds a local format code for
  this packing, which is not the MIPI one. The vendor library sets no unpacked mode. The fourcc is not settled upstream, and
  libcamera support for it has not been checked.
- [`0565`](../../patches/proposals/0565-clk-mediatek-mt6797-mm-keep-the-SMI-common-gate-open.patch) marks the SMI common gate
  critical, so a camera consumer can no longer close it behind the display. An SMI driver should own it instead.
- [`0569`](../../patches/proposals/0569-media-i2c-hi556-add-red-and-blue-balance-controls.patch) adds standard red and blue
  balance controls on the sensor's separate gains, for the owner's request that userspace can control colour.
- [`0570`](../../patches/proposals/0570-media-i2c-hi556-write-the-analogue-gain-to-its-own-r.patch) writes the analogue gain at
  `0x0076`. From the source, not yet observed: upstream's 16-bit write at `0x0077` puts the value in the Gr gain's high
  byte, so analogue gain never applies. The vendor driver for this register map uses `0x0076`.
- [`0567`](../../patches/proposals/0567-arm64-dts-mediatek-mt6797-give-the-sensor-interface-.patch) adds SPI 252 and larb2's
  window to the sensor interface node. CAMSV0 still bypasses M4U.

[`cam-view.c`](cam-view.c) streams from the node, checks colour bars line by line, and shows a rough picture on the panel.

N1, boot `68f2ec68`, combined image `c894320e` from `01bbd719` with the camera modules byte-identical to `aae632bb`, script
`aaa10cca`, as reported by the custodian. The owner approved the image write and the eMMC was read-only.

- `/dev/video0`, `/dev/media0`, `v4l-subdev0` the receiver and `v4l-subdev1` the sensor. Format `MBgA` 2592x1944, stride 3240.
- Colour bars: 60 of 60 frames, none with a bad line. Sequence reached 220, so 161 frames were skipped while the tool drew,
  at 7.82 delivered per second.
- SMI count 1 before and after, blank and unblank clean, no timeouts, tainted 0, no fault, no interrupt storm, 232 interrupts.

N2, same boot, five-second runs of a real scene on the panel, all 150 of 150, no fault, tainted 0:

- Default: ran. Which way up was not reported.
- `-g 60`: brighter, by the owner's eye. So the analogue gain has an effect, which fits `0570`.
- `-e 500`: darker, by the owner's eye. The tool's `-f 1` mirror worked.
- `-R 512`: ran, 9.36 delivered per second.

Colour wasn't judged by eye; a measurement from the tool's `-m` follows. Until then the Bayer order of a real scene is open:
the vendor driver's notes for `0x000e` suggest Gb first at upstream's `0x0100`, while upstream and this view assume Gr first,
and the test pattern may ignore that register. There are no guard bytes around these buffers, and stray writes are not
ruled out.
