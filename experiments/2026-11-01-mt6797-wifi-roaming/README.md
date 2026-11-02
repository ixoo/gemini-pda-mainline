# Experiment: roaming between access points of one network

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-mt6797-wifi-roaming` |
| Status | `running`: stage A passed on one boot; stage B's roams reach the second access point and authenticate; 0464 addresses the next stops, not yet rerun |
| Subsystem | Wi-Fi: `mac` |
| Device variant | named Gemini PDA (MT6797X), boot2 station |
| Date(s) | 2026-11-01 |
| Investigator(s) | project custodian |
| Tracking issue | none |

## Question or hypothesis

Can the station move between access points of the owner's network, on request and then by itself,
without a firmware restart? This is the roaming part of the
[daily-use plan's phase 4](../../docs/WIFI_DAILY_USE_PLAN.md#4-a-full-day-anywhere). The owner asked
for it on 2026-11-01 ("Yes, start roaming").

The supplicant decides when to roam and mac80211 runs the switch. Reading the code showed four gaps
in the driver:

| Gap | Change | State |
| --- | --- | --- |
| Scan while connected | [0430](../../patches/proposals/0430-wifi-mt6797-scan-while-connected.patch) | Already in station images, never run |
| A reassociation request closed the lifetime | [0456](../../patches/proposals/0456-wifi-mt6797-accept-reassociation.patch) | Compiled |
| A lifetime only opened after a scan, and the channel changed under the old link's teardown | [0457](../../patches/proposals/0457-wifi-mt6797-join-without-a-scan-once-the-old-link-is.patch) | Compiled |
| mac80211 refuses a signal threshold on a beacon-filtering interface unless the driver reports it | [0458](../../patches/proposals/0458-wifi-mt6797-report-the-signal-threshold.patch) | Compiled |

All of this is read from the code, not observed on the device. In 0458, how often beacons reach the
driver on an idle link is unknown, so its events may be slow; its log line carries a sample count.

Out of scope: 802.11r, k and v, DFS joins and 2.4 GHz until its transmit is fixed.

## Safety assessment

**Stage A** sweeps both bands while connected, so the radio leaves the operating channel. The scans
are passive, so the driver asks for no probe requests. Read from the code, the driver adds no new
frame type; what the firmware sends when it leaves the channel, such as a power-save frame to the
access point, is not measured.
**Stages B to D** move the link between the owner's access points, which the
[radio protocol](../2026-11-01-mt6797-wifi-any-channel/README.md#radio-protocol-approved-by-the-owner-2026-11-01)
budgets at one join and ten reconnects per channel, and channels 40 and 161 have already used theirs.

**Roam budget, approved by the owner on 2026-11-01** ("Approve budget"), replacing that limit for these
tests only: only access points of the owner's network on non-DFS 5 GHz channels, at most 40 roams a
session, US country, its other limits and stop conditions unchanged. Two failed roams in a row stop
the test.

## Stage A: map and scan while connected

On any station carrying 0430, connected, with [`wifi-roam.sh`](wifi-roam.sh):

1. `map`: frequency and signal of each access point of the network. Addresses stay private on the
   device.
2. `scans 70`: 70 passive scans with a 5 pings/s ping running, enough to cross the command
   sequence recycling at 200.

| Observation | Next |
| --- | --- |
| Scans complete, list both bands, the link stays, the ping recovers | Stage B |
| Two or more access points on non-DFS 5 GHz | Stage B between them |
| Only one in reach, or others on DFS or 2.4 GHz only | Ask the owner where to test; DFS needs its own approval |
| The link ends during a scan | Read which notice ended it, then the firmware's absence events |
| A scan never completes | Read the done events the worker saw |
| Data stalls past the scan | Stop; read the ledger lines, the scan's pages may not be returning |
| Refused past 230 under load | By design; check scans resume when idle |

## Stage B: roam on request, at the desk

Package: to be recorded, from the build carrying 0464.

USB connected, between channels 40 and 161, the two strongest 5 GHz access points in the map.
Hypothesis: `wpa_cli roam` moves the link with one `join without a scan` line per roam, a reassociation
response, and no firmware restart. `scans 100` first, for the recycle line; then `roams 10`, then the
same with a transfer running.

| Observation | Next |
| --- | --- |
| 10/10 at the target, no restart, a gap near today's 1.5 s reconnect | Stage C |
| Roams work with a restart each | Read `join stopped` and the first error; 0457 is the suspect |
| Station refused | The `refused` bits in the log name the failed precondition |
| Falls back to a scan and then joins | The wait bound or re-arm ran late; read the times |
| Fails twice | Stop, keep the log, full module reload, no retry before reading it |

## Stage C: roam by itself

`bgscan` in `wpa_supplicant`, if the RAM root's build has it, with the owner moving the device on USB
or a far access point. Hypothesis: `signal threshold` lines appear at a usable rate, a connected
scan follows, and the supplicant moves to the stronger access point.

| Observation | Next |
| --- | --- |
| Roams by itself | Stage D |
| Sample count too low on an idle link | Feed the average from data frames as well |
| `bgscan` absent from the build | Rebuild the tool or drive roams with a small script |

## Stage D: the walk

The owner carries the device between access points with no USB, logging to the data partition, read
afterwards. Protocol to be written after stage C.

## Observations

**Stage A, first try: boot `6b3acef8`, image `d1a882db`, `mac` `773e1694…`, run by the custodian at
the owner's choice.** That boot had the first-join restart, a `wifi-up.sh` rerun and a GNSS test, and
`gnss-mt6797` stayed loaded.

- `map` at about 440 s: `iw` returned `-EBUSY` (rc 240), no access point was listed, and the link
  stayed `COMPLETED` on 5200 MHz. A manual passive scan gave the same.
- No `connected scan` line in the log. `scans 70` did not run.
- Outside the steps, the custodian ran `wpa_cli scan` once at about 476 s: it returned `OK`, with no
  scan line and `wpa_state` unchanged. Whether it was admitted is not proven. That supplicant was not
  in passive mode, so it could have sent probes had it run.
- The link stayed up, with gateway pings 3/3 before and after, not tainted, no new restart.

**Analysis, from the code, first reading: wrong.** I judged the driver's busy path unlikely and suspected a
scan held above it. The retest below disproved that.

Retest package: Buildbox at `234bf3ec`, inventory `4e074191…`, `mac` `584cbe76…`, CONSYS `28b5435c…`,
core `425b8add…`, `Image.gz` `e9bad6fb…`. Only `mac` needed swapping. A swap is not a first join after
boot, so it did not test 0460's fault.

Reads on the same boot at 704 s, by the custodian: the newest scan results date from about 59 s, one
`wpa_supplicant`, one `udhcpc`, and one `CTRL-EVENT-SCAN-FAILED ret=-16` in its log, which has no
times. That line is probably the `wpa_cli scan` above, so that scan was probably refused and sent
nothing. None of this shows a scan pending inside mac80211 or cfg80211, which has no view here.

**Stage A, second try: same boot, fresh `mac` `584cbe76…`, run by the custodian.** It loaded cleanly,
reached `COMPLETED` on 5200 MHz with a lease and `passive_scan=1`, and `map` ran about 10 s after the
channel release. One attempt, refused:

```
one-shot WLAN scan busy: used=1 data=1 ended=0 released=1 sta=1 cleanup=1 online=0 cancel=0
```

The driver refused it. `mt6797_mac_mgd_complete_tx()` requests the cleanup when the association
request completes, so `join_cleanup_requested` is set all through the data phase, and 0430's condition
could never hold. Every connected scan since 0430 would refuse, on any boot, so 0430's code past that
check has still never run.
[0461](../../patches/proposals/0461-wifi-mt6797-admit-a-connected-scan-while-cleanup-is-.patch)
tests `join_cleanup_done` instead. The link stayed up, with no restart and no `TX status` lines.

**Stage A, third try: same boot, fresh `mac` `977c2ea5…` (0461), package `c9bd5a47…`, passive scan,
run by the custodian.** Passed:

- `map`: rc 0, the link stayed. Nine access points of the network were heard: channels 40 (-62 dBm,
  current), 48 (-81), 149 (-79), 161 (-58) on 5 GHz, none on a DFS channel, and five on 2.4 GHz (1, 6
  and 11).
- `scans 70`: 70/70 rc 0, `COMPLETED` on every line, 5.76 s mean and 5.78 s max, 19-23 BSS. 71 scans admitted
  and ended on this `mac`, none aborted, no new restart, not tainted.
- Ping at 5/s through the run: 2720 replies, no gap in the sequence numbers. The custodian's figures:
  median 40 ms, 99th percentile 404 ms, maximum 496 ms. There is no baseline without scans on this boot.

The script's summary printed `replies=0`, because busybox ping writes `seq=`. That is fixed; the
figures above come from the raw file, recomputed here for replies and gap.

Not shown:
- Sequence recycling. The README expected 70 scans to cross it, but no line logs it, and at 2
  commands a scan from 84 the sequence stays under the 230 refusal with or without a recycle.
  [0462](../../patches/proposals/0462-wifi-mt6797-log-the-connected-scan-s-command-sequenc.patch)
  logs it, so stage B repeats 100 scans.
- What the firmware sends when it leaves the channel.
- A clean first join: this is the boot of the first-join restart.

**Stage B, first try: same boot, `mac` `a8c1a778…`, package `a5392104…`, passive scan, run by the
custodian.** The 100 scans passed and both roams failed, which is the stop rule. 2 of the 40 roams used.

- `scans 100`: 100/100 rc 0, `COMPLETED`, 5.76 s mean, 3885 ping replies with no gap. The sequence
  recycled twice, 201 to 110 and 202 to 110. No `scan busy`, none aborted, no restart. That settles
  recycling on this boot.
- `roams 2`: neither reached channel 161. Each cost a firmware restart, then a normal scan and a rejoin on
  channel 40 about 7.5 s later. No `join without a scan` line.

The first roam's log, in order:

```
4863.735 join data phase end: reason=disconnect
4863.807 join cleanup: stage=3 ... deauth=1 delivery=transmitted
4863.807 connection loss report: source=cleanup
4863.831 wlan0: Connection to AP lost
4863.848018 join rearm: lifetime=1 token=2 sta_seq=120 sequence=149
4863.848382 mask-control submission: enable=0 status=-16
4863.848409 join peer refused: reasons=0x00002 ... sequence=156
4863.848562 wlan0: failed to insert STA entry for the AP (error -95)
4863.848583 join channel refused: hw=1 center=2412 ... config=-95
4863.949 passive WLAN submission stopped: status=-95
4863.950 WLAN restart: begin
```

The scanless join ran, as far as its first command, under a millisecond after the re-arm. That command
returned -EBUSY and ended the lifetime. Read from the code, the command path returns -EBUSY when
its mutex is busy or, it seems, when the ledger still owes pages; which one is not shown. The re-arm's own
comment says its last pages may be unreconciled.
[0463](../../patches/proposals/0463-wifi-mt6797-wait-for-the-ledger-before-a-scanless-jo.patch) waits for the ledger first.

Read from these lines:
- The link went down before mac80211's `disconnect from AP ... for new auth` could print, and there is no
  `deauthenticating` line. The data phase ended by another route, probably the supplicant unauthorizing
  the port, which the driver treats as a disconnect. Inferred, not traced. It reports a connection loss, so
  the supplicant may also see a disconnect mid-roam.
- `hw=1 center=2412` is `.config` refusing after the error; the join never tried it, and the log shows no join
  frame on it. The same line after the first-join fault is the same teardown path.
- The jump in `sequence` from 149 to 156 fits six commands from cfg80211's regulatory restore plus the mask
  itself: the supplicant reports a change to WORLD and back to US around each disconnect. Inferred.

**Stage B, second try: same boot, `mac` `a7045e3a…` (0463), package `b38b95ee…`, run by the custodian.**
4 of the 40 roams used so far.

- Roam 1 ran `join without a scan`, got `join grant: channel=161`, sent its authentication frame on
  channel 161 and got the answer, 280 ms after the disconnect. 20 ms after `associate`, it stopped with
  `status=-22 branch=3`, no association frame submitted.
- Roam 2 stopped on `mask-control submission: enable=0 status=-16`, 416 µs after the re-arm, then a restart.
  Rejoins on channel 40 took about 3 s and 7 s.
- The supplicant logged no `CTRL-EVENT-DISCONNECTED`, and it did carry on with the roam. So the earlier
  worry about a disconnect mid-roam did not stop this one.

Causes, from the code:
- `mt6797_join_tx_descriptor()` keeps its own list of frame types, and 0456 did not add reassociation
  to it, so the frame was refused as invalid. That is certain from the code.
- The -16 is less clear. The first try's sequence numbers put the regulatory commands between the re-arm
  and the mask. In roam 2 the mask has no `failed to insert` line after it, so it probably came from a scan,
  which 0463's wait did not cover, rather than the scanless join. Not proven.
[0464](../../patches/proposals/0464-wifi-mt6797-send-a-reassociation-and-wait-for-idle-b.patch) fixes the first and moves the wait to the start
shared by scans and scanless joins.

Also in the first try's log, and again in this run up to 1776.66 s, not investigated: 64 `data rx refused` lines (`field=packet-type`), the first at
64.87 s and the rest from 259.86 s.
