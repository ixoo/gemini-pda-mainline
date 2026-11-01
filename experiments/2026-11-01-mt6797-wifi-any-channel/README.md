# Experiment: Wi-Fi on any network and channel (daily-use plan, phase 3)

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-mt6797-wifi-any-channel` |
| Status | `running`: 0410 (multi-channel passive scan) built, device test predeclared |
| Subsystem | Wi-Fi: `mac` |
| Device variant | named Gemini PDA (MT6797X), boot2 station |
| Date(s) | 2026-11-01 |
| Investigator(s) | project custodian |
| Tracking issue | none |

## Question or hypothesis

Phase 3 of the [daily-use plan](../../docs/WIFI_DAILY_USE_PLAN.md#3-any-network-any-channel)
removes the channel 40 pins. The first step listens only:
[0410](../../patches/proposals/0410-wifi-mt6797-scan-many-channels-in-one-request.patch)
lets one scan cover every channel the request lists, in as many firmware
requests as it takes (at most 32 channels each), with 130 ms per channel.

Hypothesis: `iw dev wlan0 scan passive` with no frequency list reports
access points on both bands, including channels the driver has never tuned
to on this kernel. The firmware's done event counts each request's channels.
The owner's access point on channel 40 is found as before, and join,
reconnect and throughput on channel 40 do not change.

## Safety assessment

The scan command's type stays passive with no SSIDs, as on every station so
far, so no probe request is requested on any channel. The channels are those
cfg80211 enables under the US domain, DFS ones included: listening needs no
radar clearance. Join stays pinned to channel 40 in `mac`, which refuses
any other channel before a command reaches the firmware.

This step rests on the firmware honouring the passive type; nothing here
measures the air. Transmitting on another channel needs the owner's approval
of a radio protocol, and is not part of this step.

## Procedure

By module swap, if the 0410 package's `Image.gz` is byte-identical to station
28's: copy `mac.ko` to the RAM root, `rmmod mac`, `mt6797_consys` and
`mt6797_wlan_core`, reload. Otherwise a new station image.

Scan output is reduced to counts per frequency; no network name or address
leaves the device.

1. Stop `wpa_supplicant`. `iw dev wlan0 scan passive`, three times, at least
   12 s apart (a scan with no join holds its lifetime for 10 s). Record the
   duration, the BSS count per frequency and the kernel's scan lines.
2. `iw dev wlan0 scan passive freq 2412 2437 2462`, and the same with `freq
   5200`.
3. `wifi-up.sh`: join on channel 40 with its pins in place. Ping, ten
   reconnects, throughput as on station 28.
4. Kernel log: no Oops, warning or call trace.

| Observation | Decision |
| --- | --- |
| Steps 1-4 pass, with BSSes on both bands | Multi-channel scan works; ask the owner about the transmit protocol, then unpin join |
| One band or some channels never report, while other devices see networks there | Compare the firmware's regulatory lists with the request before any change to dwell |
| The second request's done event does not arrive, or its count differs | Split no further: read the event, then decide between one request per band and a shorter list |
| Few BSSes compared with a 500 ms one-channel scan on the same channel | Raise the sweep dwell and repeat |
| Join or reconnect regresses on channel 40 | Stop; a scan must leave no state behind. Read the post-scan path |
