# Experiment: a GNSS daemon that turns the DSP's measurements into NMEA

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-10-gemini-gnss-daemon` |
| Status | `running`: the daemon feeds gpsd and GeoClue with standard NMEA, and Noctalia switches it on and off; it passes offline tests against retained captures, with real gpsd and GeoClue in the dev VM; it has not run on the device |
| Subsystem | GNSS userspace, `gnss-mt6797`, gpsd |
| Device variant | Gemini PDA (MT6797X), Arch card root |
| Date(s) | 2026-11-10 |
| Investigator(s) | project session; owner request relayed by the device custodian |
| Tracking issue | none |

## Question

The owner asked: "Do we have the gnss userland to produce a fix and position? If not can we write
it and package it for arch on the sdcard?"

A later requirement, also in the owner's words: "It needs to be done in a standard way for all
software that require a position to be able to use it." So the daemon produces only standard NMEA
0183, and applications reach it through gpsd (libgps clients) and GeoClue (desktop applications and
browsers). There is no Gemini-specific client interface.

And on switching it: "I don't want the gnss to be up by default, only when activated in noctalia
(if possible)".

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
- **Output:** NMEA `GGA`, `GSA`, `RMC` and `GSV` once a second, to two places. Without a fix it
  still writes `GGA`, `RMC` and `GSV`, marked invalid.
  - `/run/gnss-mt6797/nmea`, a link to a pty, for gpsd. gpsd drops root before it opens a device
    added later, so the pty goes to gpsd's group, `uucp` on Arch, mode 0660.
  - `/run/gnss-mt6797/nmea.sock`, a Unix socket that sends every client the same sentences, for
    GeoClue's NMEA source. It goes to group `geoclue`, which GeoClue runs as, mode 0660.
- **Records:** `--record FILE` keeps both directions in the `frames.log` format; `--replay FILE`
  decodes one and prints NMEA.
- [gnss-mt6797.service](gnss-mt6797.service) loads the module, runs the daemon and adds the pty to
  gpsd with `gpsdctl` through `/run/gpsd.sock`, which `gpsd.socket` provides. It is not enabled:
  starting it switches the GPS radio on.
- [geoclue-gnss-mt6797.conf](geoclue-gnss-mt6797.conf), installed as
  `/etc/geoclue/conf.d/90-gnss-mt6797.conf`, points GeoClue's `[network-nmea]` source at the socket.
- [noctalia-gnss](noctalia-gnss), the Noctalia 5 plugin `gemini/gnss`: a control-center tile
  (`gemini/gnss:toggle`) and a bar indicator (`gemini/gnss:indicator`). Each polls
  `systemctl is-active gnss-mt6797.service` every 2 s, shows on or off, and starts or stops the
  service on click, with a notification if that fails. Nothing else starts the GPS.
- [gnss-mt6797.rules](gnss-mt6797.rules), a polkit rule: the user at the device's active local
  session may start, stop and restart `gnss-mt6797.service` without a password. Every other unit
  and action keeps polkit's normal rules.
- [PKGBUILD](PKGBUILD) packages all of it, depending on `gpsd`, `geoclue` and `polkit`, for the
  Arch root to build next to `gemini-base`. The plugin goes to `/usr/share/noctalia/plugins/gnss/`.

## Noctalia

From the Noctalia 5.4.1 documentation and its official example plugins:
- **No built-in location toggle:** shortcut tiles are built-in types, and `custom_button` runs a
  command but shows no state. A Luau plugin can declare a `[[shortcut]]` tile, with `setActive`
  for its state, and a `[[widget]]` for the bar, and run commands with `noctalia.runAsync`.
- **Plugin API level:** 24, for `runAsync` with an argument list; 5.4.1 accepts 3 to 43.
- **Loading:** plugins load from the user's data directory or a configured source. A
  `[[plugins.source]]` with `kind = "path"` and `location = "/usr/share/noctalia/plugins"` should
  find `gnss/`, and `[plugins] enabled = ["gemini/gnss"]` turns it on. A bar widget is placed with
  `type = "gemini/gnss:indicator"`. The tile is added from Noctalia's control-center settings; a
  TOML form for plugin tiles is not documented. These belong in the root's `noctalia.toml`.
- **Commands run as the session user,** by inference: the docs' examples use `systemctl --user`.
  Hence the polkit rule.

## gpsd and GeoClue on Arch

Read from GeoClue 2.8.2's source and Arch's gpsd 3.27.5 packaging; Arch Linux ARM ships the same
GeoClue version.

- **GeoClue:** `nmea-socket=PATH` in `[network-nmea]`, with `enable=true`, adds a local socket as
  an NMEA service next to any found through Avahi. Drop-in files in `/etc/geoclue/conf.d/` override
  `geoclue.conf`, in name order. GeoClue connects as a client; when the socket is absent or closes,
  it marks the service broken and retries all of them every 5 s. It reads `GGA` (ignored without a
  fix; accuracy from HDOP) and `RMC` (ignored unless status `A`), and reports this source at
  accuracy level `EXACT`.
- **GeoClue agent:** GeoClue answers an application only after an agent in the user's session
  authorises it; with no agent, a client waits. The Arch package installs its demo agent as an XDG
  autostart entry, so the card's session has to start XDG autostart entries or the agent itself.
- **gpsd:** Arch builds it with group `uucp`, installs `gpsd.socket`, `gpsd.service` and
  `/etc/default/gpsd` with no devices, and `gpsdctl` adds a device through the control socket.
  `gpsd.socket` has to be enabled.

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

The live-loop check also confirms the socket carries exactly the bytes the pty does.

**gpsd:** step 6's NMEA through a pty into gpsd 3.25 in the dev VM gave 293 TPV reports in mode 3,
with position, and 221 SKY reports. Ubuntu's AppArmor profile stops gpsd opening a pty, so that
test ran a copy of the binary outside the profiled path; Arch has no such profile.

**GeoClue:** in the dev VM, GeoClue 2.7.0 with this drop-in, the daemon driven by a fake device
playing step 6, and GeoClue's demo agent and `where-am-i` client (accuracy level 8): 406 locations,
each described "GPS GGA" with an accuracy from HDOP. Socket and pty were created with the
intended groups and modes. Without an agent, `where-am-i` waited and timed out, as above.

**polkit:** in the dev VM with dummy units, the rule without its session condition let a normal user
start and stop `gnss-mt6797.service` and refused another unit and `enable`. The real rule refused the
same start from an SSH session, which is not an active local session. polkit logged no rule error.

**Not tested:** anything on the device; the card's Python, gpsd and GeoClue; `gpsdctl` through
`gpsd.socket`; the search list's effect on acquisition; the Noctalia plugin, which has no Luau
interpreter here and has not been loaded by Noctalia; the polkit rule from a real seat session.

## How each path gets tested on the device

Once the card has the package, in the one approved open-sky run:
- **gpsd:** with `gpsd.socket` enabled, start `gnss-mt6797.service`; `gpspipe -w` must show the
  device added and `TPV` in mode 3, and `cgps` must show the same satellites as the daemon's `GSV`.
- **GeoClue:** in the same run, a GeoClue client in the owner's session, `where-am-i` or GNOME Maps
  or Firefox's location prompt, must get a location described "GPS GGA" with accuracy of a few
  metres, while Wi-Fi location is unavailable or worse.
- Record only counts, modes, accuracies and descriptions; positions stay private.

## Device test, when proposed

A run is a radio action and needs the owner's approval and an open-sky placement, proposed through
the custodian. It needs a kernel with 0636, `gnss_dsp_6797.bin` with SHA-256 `a99cacea…` and this
package. Captures and NMEA hold position, so they stay private.
