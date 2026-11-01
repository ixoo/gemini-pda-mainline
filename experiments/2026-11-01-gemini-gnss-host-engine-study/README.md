# Experiment: can an open GNSS stack be built from what `libmnl` shows?

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-gemini-gnss-host-engine-study` |
| Status | `completed`: offline study, conditional go; no device access, no code |
| Subsystem | MT6797 CONSYS GNSS: host engine path on STP task 2 |
| Device variant | Gemini PDA (MT6797X) |
| Date(s) | 2026-11-01 |
| Investigator(s) | project session |
| Tracking issue | none |

## Question

The [link record](../2026-11-01-gemini-gnss-link/README.md) parked the offload path because
`MNL.bin` does not exist. If stock runs its engine on the application processor, could we
replace that engine with an open one? That depends on the level of data the receiver DSP
sends: measurements, which an open solver can use, or something much lower.

## Method

Static reading of the retained `libmnl.so`, SHA-256 `a2e3fe69…` (see the
[reverse-engineering record](../2026-11-01-gemini-gnss-re/README.md)), using the existing Ghidra
decompile, in the RE VM. Nothing ran. Exact offsets and image details are private, under
`artifacts/gnss-host-engine-study/`. No vendor code or firmware bytes are copied here.

## Findings

**Read from the decompile:**
- **The host boots the DSP.** `mtk_gps_dsp_init` runs a boot routine that picks a DSP image
  embedded in `libmnl` by chip, and it has an MT6797 entry selected by the same chip words as
  [0439](../../patches/proposals/0439-gnss-mt6797-send-the-vendor-s-start-configuration.patch).
  The image has a size, load and execute addresses, and a cipher key field, and goes in
  1400-byte fragments.
- **The frames are not GFNS.** They run `AA F0`, a length with flags, a packet ID, a 32-bit
  address, payload, a checksum, then `AA 0F`.
- **About 30 packet types** arrive from the DSP, including per-channel records with a channel
  number and a fixed record size. A first-message packet triggers `$PMTK010,001`.
- **The engine logs per-satellite measurements:** code phase, carrier-related values and a 20 ms
  count, with arithmetic on the 1023-chip code length.

**Inferred:**
- The DSP does the tracking, and the host works from measurements. This is the feasible row of
  the study's table. The evidence is the measurement fields, plus no sign of host-side tracking
  loops in the strings. Stripped logs make that absence weak.
- T3's A1 fits this path: after function-on with no boot, task 2 stayed silent for 60 s.
- With F16 of the [source review](../2026-10-04-gemini-gps-re/README.md), this supports stock
  using this path, which stays an inference until a stock trace confirms it.

**Unknown, and able to stop the work:**
- Whether the MT6797 boot actually runs over STP. The routine's logs name UART, and the boot was
  never observed. Whether the firmware accepts these frames on task 2 is also unknown.
- Whether the image is ciphered in `libmnl`, and whether the DSP needs anything else first.
- What the host must send to run the DSP: channel assignment, search control, assistance. If the
  host has to steer acquisition, the open stack must implement that too.
- Whether navigation bits reach the host in a usable form. Without them there is no ephemeris
  and no fix without assistance.
- Field layouts of the packets. They are known only through engine use, and a trace would be
  the fastest way to confirm them.
- Whether GNSS has ever worked on this device under either kernel.

## Verdict: conditional go

Nothing found rules it out, and the most likely level of data is the workable one. But the size
stays uncertain: a protocol client, DSP control and an open solver are weeks to months, with
accuracy below the vendor's at first.

**What it would be:** a small kernel change, a raw task 2 pipe with GPS function-on and GPIO 69,
because the kernel only carries bytes; an open userspace daemon; and a DSP image the owner extracts
from their own `libmnl`, never distributed by this repository. It would be written independently
from protocol facts, and would not be a standard NMEA `gnss` device at the kernel boundary.

**Update:** the [stock trace](../2026-11-01-gemini-gnss-stock-trace/README.md) observed the DSP boot over STP
with these frames. It stopped before any measurement packet.

## Next gate

A stock trace is the most informative next step: `/dev/stpgps` traffic from a Gemian GNSS
session would show the boot, the transport, the commands and real packets, and whether stock works
at all. Booting the DSP from mainline is the alternative, but it tests more unknowns at once and
would have nothing to compare with. Either is a radio action needing its own protocol and the
owner's approval. Neither has been started.
