# Experiment: a GNSS daemon that turns the DSP's measurements into NMEA

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-10-gemini-gnss-daemon` |
| Status | `running`: the daemon, its unit and package spec pass offline tests against retained captures; it has not run on the device |
| Subsystem | GNSS userspace, `gnss-mt6797`, gpsd |
| Device variant | Gemini PDA (MT6797X), Arch card root |
| Date(s) | 2026-11-10 |
| Investigator(s) | project session; owner request relayed by the device custodian |
| Tracking issue | none |

## Question

The owner asked: "Do we have the gnss userland to produce a fix and position? If not can we write
it and package it for arch on the sdcard?"

Nothing did. With [0636](../../patches/proposals/0636-gnss-mt6797-boot-the-DSP-from-its-firmware-file.patch),
opening `/dev/gnss0` boots the DSP, and
[gnss-minihost.c](../2026-11-01-gemini-gnss-stock-trace/gnss-minihost.c) only feeds it and records
what it sends. Positions came only from offline solvers run on private captures.

## What it is

[gnss-mt6797d](gnss-mt6797d), Python 3 with the standard library only, written from the protocol
facts in [the driver notes](../../docs/hardware/gemini-gnss-driver.md); it contains no vendor code.

- **Host side:** opens `/dev/gnss0`, sends the setup commands, then each second the frames
  `gnss-minihost.c` sends. Time comes from the system clock, as before.
- **Search list:** stock orders it by expected visibility, which depends on place and time, so the
  daemon sends the same satellites in number order. This is the one change from what booted and
  tracked in step 6 and T5.
- **Measurements:** groups each second's valid GPS records between `0xFE28` and `0xFE2C`, forms
  pseudoranges from their transmit times against a common receive time, and solves position and
  clock by least squares, with Earth rotation, satellite clock, relativity and group delay.
- **Orbits:** decodes GPS subframes 1 to 3 from `0xFE2B` with LNAV parity, and keeps an ephemeris
  when its issue numbers agree. It needs no network and no assistance.
- **Output:** NMEA `GGA`, `GSA`, `RMC` and `GSV` once a second, to a pty linked at
  `/run/gnss-mt6797/nmea`. Without a fix it still writes `GGA`, `RMC` and `GSV`, marked invalid.
- **Records:** `--record FILE` keeps both directions in the `frames.log` format; `--replay FILE`
  decodes one and prints NMEA.
- [gnss-mt6797.service](gnss-mt6797.service) loads the module, runs the daemon and hands the pty to a
  running gpsd. It is not enabled: starting it switches the GPS radio on.
- [PKGBUILD](PKGBUILD) packages both, for the Arch root to build next to `gemini-base`.

**Limitations:**
- GPS only: GLONASS and BeiDou records are tracked and listed but not used for position.
- No ionosphere or troposphere correction, and no geoid: `GGA` altitude is height above the
  ellipsoid, with the separation field empty.
- No speed or course: those `RMC` fields are empty.
- Week numbers assume the 2019 to 2038 rollover period.
- A fix needs four GPS satellites with complete orbits, which takes at least the 30 s a satellite
  needs to send subframes 1 to 3 after it is tracked.

## Offline tests

[test-offline.py](test-offline.py) takes two private captures: T5's (`gnss-minihost.c` on
`/dev/gnss0`) and step 6's (stock host, outdoors). It prints counts only. All ten checks pass:

| Check | Result |
| --- | --- |
| Frames round trip, also fed in 3-byte pieces; a bad sum is dropped | Pass |
| Setup and two seconds against the C host's writes in T5, except the time bytes and search list | 24 frames equal |
| Search list holds the same satellites as stock's | Equal |
| Live loop against a fake device playing step 6's DSP bytes | Setup, per-second frames, stop sent last; 568 fixes written to the pty; every checksum right; exit 0 and link removed |

Replays:

| Capture | Epochs | Fixes |
| --- | --- | --- |
| Step 6, stock host outdoors | 636 | 568, first at epoch 69, median 7 satellites, median HDOP 1.3 |
| T5, mainline at a window | 600 | 0: at most two satellites at once |
| T4, mainline indoors | 53 | 0 |

On step 6 the daemon's median position is within 1.6 m horizontally of RTKLIB's GPS and
GPS+GLONASS solutions from the broadcast orbit file, and 10 to 11 m higher, which fits the missing
atmospheric corrections. Its horizontal scatter is 2.8 m at p50, 5.5 m at p90 and 8 m at p99. These
are the same counts as the earlier private solver it was rewritten from.

**gpsd:** step 6's NMEA through a pty into gpsd 3.25 in the dev VM gave 293 TPV reports in mode 3,
with position, and 221 SKY reports. Ubuntu's AppArmor profile stops gpsd opening a pty, so that
test ran a copy of the binary outside the profiled path; Arch has no such profile.

**Not tested:** anything on the device; the card's Python; the search list's effect on acquisition;
gpsd on Arch.

## Device test, when proposed

A run is a radio action and needs the owner's approval and an open-sky placement, proposed through
the custodian. It needs a kernel with 0636, `gnss_dsp_6797.bin` with SHA-256 `a99cacea…` and this
package. Captures and NMEA hold position, so they stay private.
