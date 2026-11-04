# Experiment: the front camera's CSI-2 receiver on the station

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-04-gemini-camera-receiver` |
| Status | `running`: receiver written, compile-checked, not run |
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

None yet.

## Inference

None yet.

## Negative results

None yet.

## Limitations

- Compile-tested only.
- 437 MHz is not known to be the link rate at 24 MHz.

## R1: the first stream

Not run.
