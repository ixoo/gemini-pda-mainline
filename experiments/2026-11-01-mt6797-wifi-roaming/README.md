# Experiment: roaming between access points of one network

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-mt6797-wifi-roaming` |
| Status | `running`: stage A passed on one boot; `wpa_cli roam` works both ways on one boot, 21 clean at the driver; under a download one TCP stall in 12 roams, unexplained; roams by itself both ways on one walk, no restarts; one access point refuses the handshake, and weak links pass no received data |
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

Package: Buildbox at `5182bab9`, inventory `307052cd…`, `mac` `a70b0c88…`, CONSYS `28b5435c…`, core `2542c418…`.

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

`bgscan` in `wpa_supplicant`, from [the rebuild](build-wpa-supplicant.sh), with the owner moving the device on USB
or a far access point. Hypothesis: `signal threshold` lines appear at a usable rate, a connected
scan follows, and the supplicant moves to the stronger access point.

| Observation | Next |
| --- | --- |
| Roams by itself | Stage D |
| Sample count too low on an idle link | Feed the average from data frames as well |

## Stage D: the walk

The owner carries the device between access points with no USB, logging to the data partition, read
afterwards.

Hypothesis: with `bgscan="simple:30:-70:300"`, the rebuilt supplicant and 0470, the device changes access point by itself on the way
out and back, with a gap near the desk's and no firmware restart, and TCP mostly survives.

- **Setup, at the desk on USB:** a new `walk` mode in [`wifi-roam.sh`](wifi-roam.sh) starts the supplicant unpinned, `scan_freq` and
  `freq_list` set to the access points' non-DFS channels from the map, then runs a repeating download from the laptop and a 5/s ping
  to the gateway, as at the desk, logging all of it to the data partition. The laptop captures its end of the download.
- **Walk:** unplug, go to the farthest access point, wait 2 minutes, come back the same way, wait 2 minutes, plug in. 20 minutes at most.
- **Budget, approved by the owner on 2026-11-02** ("Approve budget"), for this walk only: 20 roams and 60 active scans, on those channels.
- **Limits, enforced by the script since nobody can reach the device:** it stops at 20 minutes, 20 roams, 60 active scans, 2 firmware
  restarts or 2 `join stopped`, then restores the normal pinned link. It counts every data phase after the first as a roam, reconnects
  included. No reboot is needed, and a failure leaves the logs for afterwards.

| Observation | Next |
| --- | --- |
| Moves both ways, no restart, gaps under 1 s, TCP survives | Roaming shown on one walk. A second route or a real network manager next |
| Stays on a far access point until the link is lost | Read the threshold events and decisions; the threshold or the sample rate is the question |
| Moves, but too often | The hysteresis and the swing; a lower threshold, or `bgscan`'s intervals |
| TCP stalls again | The capture says whether the laptop kept sending, which separates the network from the station |
| Firmware restarts | Read `join stopped`; the driver's fault under real movement |

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
- The supplicant logged no `CTRL-EVENT-DISCONNECTED`, and it did carry on with the roam. The third try
  shows the disconnect did matter.

Causes, from the code:
- `mt6797_join_tx_descriptor()` keeps its own list of frame types, and 0456 did not add reassociation
  to it, so the frame was refused as invalid. That is certain from the code.
- The -16 is less clear. The first try's sequence numbers put the regulatory commands between the re-arm
  and the mask. In roam 2 the mask has no `failed to insert` line after it, so it probably came from a scan,
  which 0463's wait did not cover, rather than the scanless join. Not proven.
[0464](../../patches/proposals/0464-wifi-mt6797-send-a-reassociation-and-wait-for-idle-b.patch) fixes the first and moves the wait to the start
shared by scans and scanless joins.

**Stage B, third try: same boot, core `2542c418…`, `mac` `431e5560…` (0464), package `c0ce36aa…`, run by
the custodian.** 6 of the 40 roams used. Both roams reassociated on channel 161 with no firmware restart,
and neither held:

- `join without a scan`, grant on channel 161, authentication, then `join TX status: pid=2 fc=0x0020
  status=0`, `join RX: subtype=3 status=0`, about 320 ms after the disconnect. Reassociation works, on one
  access point and one boot.
- The access point's first handshake message arrived and reached the supplicant, four times about 1 s
  apart. The supplicant logged `WPA: No SSID info found (msg 1 of 4)` each time and did not answer. The access
  point deauthenticated with reason 15 about 4 s later.
- The supplicant then rejoined channel 40 by itself, with no restart. Gateway 3/3, not tainted. No -16.

Reading of the cause, from the log and the code, not traced on the device: the link goes down within about
35 ms of the roam request, with no mac80211 `disconnect from AP` line, and the driver reports a
connection loss. The supplicant closes the port when it starts a roam, which reaches the driver as
`AUTHORIZED` to `ASSOC`, and the driver took any downward step as the end of the link. The loss then
cleared the supplicant's network. [0465](../../patches/proposals/0465-wifi-mt6797-keep-the-link-when-the-supplicant-closes.patch) only stops the data on that step.

**Stage B, fourth try: same boot, `mac` `1bd1c32b…` (0465), run by the custodian.** 7 of the 40 roams used; one
roam, and one plain disconnect and reconnect. The roam failed the same way, with `No SSID info found` four
times, so 0465 alone was not enough.

- The data phase now ends with `reason=key-disable`, about 60 ms after the roam request, so the port
  close was not the only trigger. The same teardown, deauthentication and connection loss report follow.
- `disconnect from AP ... for new auth` still does not appear: by the time the authentication arrives,
  mac80211 is no longer associated.
- The plain `wpa_cli` disconnect and reconnect still works: `COMPLETED` on channel 40, gateway 3/3.

Reading: the supplicant removes the keys at the start of a roam too, and the driver's teardown after that
ends in the loss report. The teardown is needed, but the report need not come so soon.
[0466](../../patches/proposals/0466-wifi-mt6797-hold-the-loss-report-when-the-keys-are-r.patch) holds it for 2 s. If a roam's authentication arrives,
mac80211 takes the link down itself and the report is dropped. Otherwise it goes out late.

**Stage B, fifth try: same boot, `mac` `96c7d1f4…` (0466), run by the custodian.** 8 of the 40 roams used; one
roam. The order predicted for 0466 held: `disconnect from AP ... for new auth` appeared for the first time,
and neither `connection loss report` nor `Connection to AP lost` came before it. The join then stopped
earlier than on the third and fourth tries, so `No SSID` is not yet tested:

```
7588.132006 wlan0: disconnect from AP for new auth
7588.164044 join rearm: lifetime=1 token=2 sta_seq=240 sequence=237
7588.179631 join without a scan: lifetime=2 sequence=240
7588.179656 join peer refused: reasons=0x00100 supported=0xff basic=0x15 sequence=240
7588.179941 join stopped: status=-125 first=0 submitted=0x0 debt=0 cleanup=0 branch=9
```

Bit 8 is `join_bss_valid`. mac80211 now sets up the new access point before the re-arm ends, and the re-arm
clears the record, and would have cleared the secondary channel offset too. [0467](../../patches/proposals/0467-wifi-mt6797-read-the-new-access-point-s-BSS-after-th.patch) reads the record again from mac80211's state and keeps the offset. Nothing was transmitted on channel 161.

`sta_seq` above `sequence` is not a fault: the station sequence takes the next command sequence, and the
sequence had recycled since. Module swaps do keep the sequence high on this boot, and a `sequence_base`
above 128 is not recycled at a re-arm, which matters only for repeated swaps. Not changed.

**A gap for daily use, seen here by the custodian.** After a firmware restart, the supplicant reached `COMPLETED`
with no IPv4 address on `wlan0` and no route, while `udhcpc` was still running. A `wifi-up.sh` rerun then
printed `lease after 0s` over an empty gateway ping; only killing `udhcpc` first brought it back. That fits
the earlier `no lease after 60s`, and shows the script's lease check can pass with no address. A real network
manager may handle a recreated `wlan0` differently; that is not tested.

**Stage B, sixth try: same boot, `mac` `239ea341…` (0467), run by the custodian.** 9 of the 40 roams used; one
roam. 0467 worked as far as `join grant: channel=161 sco=3` and `join peer: ready=1`. Then:

```
8147.459735 wlan0: send auth (try 1/3)
8147.459858 join stopped: status=-125 first=0 submitted=0x0 debt=0 cleanup=0 branch=9
```

Branch 9 has one source, the regulatory stop. mac80211's disconnect for the new authentication makes cfg80211
restore its regulatory settings, from world back to the country. Its work needs RTNL, which the request
holds, so it most likely ran as the request returned, which fits the 123 µs. That also fits try 5's
`status=-125 branch=9`, whose visible cause was the peer refusal.
[0468](../../patches/proposals/0468-wifi-mt6797-let-a-join-run-while-the-regulatory-doma.patch) lets a starting join run while the domain settles, and a change
still unsettled at the data phase ends the lifetime as before. The firmware stays on its domain throughout.

The plain `wpa_cli` disconnect and reconnect still works on this `mac`: `COMPLETED`, gateway 3/3. `No SSID` is
still untested. After the restart the lease was lost again, as recorded above.

**Stage B, seventh try: same boot, `mac` `a70b0c88…` (0468), run by the custodian.** 10 of the 40 roams used; one
roam. The driver side now runs through: `disconnect from AP ... for new auth`, re-arm, `join without a
scan`, `join grant: channel=161 sco=3`, `join RX: subtype=11`, `join TX status: pid=2 fc=0x0020 status=0`,
`join RX: subtype=3`, about 340 ms after the disconnect, with no loss report before it and no restart. The
handshake's first message arrived four times, and the supplicant again logged `WPA: No SSID info found
(msg 1 of 4)` each time. Then it deauthenticated itself (`reason=4 locally_generated=1`), returned to channel
40, and kept its address and route without help.

So my reading was wrong, or at least incomplete: the early loss report was not what cleared the supplicant's network,
since it is gone and the message remains. No `CTRL-EVENT-DISCONNECTED` is logged before `Trying to associate`.
A plain `wpa_cli` disconnect and reconnect still works on this `mac`. Next: one roam with the supplicant at
`-dd -t`, which should name what cleared its state.

**Debug roam: same boot and `mac`, supplicant at `-dd -t`, run by the custodian.** 11 of the 40 roams used. The
log explains `No SSID info found`, and it is the test, not the driver:

- The network block in the private `wpa.conf` carries `bssid=`, the channel 40 access point, as the
  channel tests' private file set it. The log shows it at parsing, and `skip - BSSID mismatch` in its scans.
- As far as I recall the v2.11 source, not checked against it, the handshake's `get_network_ctx` looks the network up
  again by SSID and pinned BSSID, so at the second access point it finds none. `wpa_cli roam` itself does not check the pin.
- Everything else in the log is as a roam should be: the port closes and the keys go, `Authenticate`,
  `Ignore disconnect event when using userspace SME`, `Associate` with `prev_bSSID`, and the frame reaching
  the state machine.

So on the third, fourth, seventh and this try, `No SSID` said nothing about the driver, and my readings of it
were wrong. It follows that 0465 and 0466 were not fixing what I said they fixed, and 0467 and 0468 only
exist for the order 0466 made. They may still be the better behaviour, but that is not shown, and once a roam
completes they should be reviewed for removal.

**Stage B, first roam without the pin: same boot and `mac` `a70b0c88…`, the network block limited to 5200 and
5805 MHz, run by the custodian.** 13 of the 40 roams used. The first complete roam on this driver:

- The supplicant first chose channel 161 by itself, a first join there on this path.
- Channel 161 to 40: `at=target`, `COMPLETED` in about 1 s, with the 5/s ping keeping its sequence throughout
  (56 replies, no gap), no restart, same `udhcpc`, same address and route, gateway 3/3. One roam, in one direction.
  ```
  9102.788059 disconnect from AP for new auth
  9102.827627 join without a scan: lifetime=10 sequence=115
  9102.899698 join grant: channel=40 sco=3 interval_ms=9000
  9102.955701 join RX: subtype=11 status=0
  9102.987690 join RX: subtype=3 status=0
  9103.107994 associated
  ```
- No `No SSID` once the pin was gone, which supports the pin reading.
- The roam back, 36 s later, failed differently: `MLME command failed (auth): ret=-2`, the supplicant's refresh scan refused
  with -16, and the 2 s loss report then fired as designed. It rejoined channel 40 with no restart, a 2 s ping gap.

The custodian's reading of that failure, which fits but is not checked: cfg80211 had aged out the target's entry, 53 s after the
last scan that saw it, against 17 s for the roam that worked. So `roams` now scans the two channels first.

A real limit stays in the driver: if the target's entry is stale the keys are already gone, the link goes down, and the
refresh scan is refused during the teardown, which costs about 2.5 s. `bgscan` should keep results fresh, so this
may be rare. Not changed.

**Stage B, repeats with a scan before each roam: same boot and `mac`, run by the custodian.** 25 of the 40 roams used.

- No traffic, one at a time: 9 of 9 at target, both directions, including the first roams to channel 161. No
  ping gap at 5/s, gateway 3/3 after each, same `udhcpc`, no restart. From the log, `disconnect from AP` to
  `connected data phase` took 0.37-0.49 s across 11 roams. Both channels ran at 40 MHz.
- Under a download: 2 of 3. A TCP download survived both of those roams, the longest ping gap 0.6 s.
- The third stopped with `join stopped: status=-110 submitted=0x804 branch=5`, 7 ms after `data phase end:
  reason=key-disable`, with 11 frames still owed, and restarted the firmware.

That is the `-110` from [stopping during a download](../2026-11-01-mt6797-wifi-any-channel/README.md), not understood
there. `branch` is left over from the previous packet: the source is `mt6797_native_diag_pre_read()`, which runs before
`branch = 4` and allows 64 reads to drain the frames owed after the data phase. A download spends them in milliseconds,
and a transmit alone does not. That is read from the code, and fits both records.
[0469](../../patches/proposals/0469-wifi-mt6797-let-the-time-bound-end-the-drain-after-t.patch) lets its existing 750 ms bound decide. Package: Buildbox at `310d4d1a`, inventory `22144aa6…`, `mac` `3ba824b1…`,
with CONSYS `28b5435c…` and core `2542c418…` unchanged. Not run yet.

**Review of 0465-0468, from the code, nothing run.** They were written on the wrong reading of `No SSID`, so the
question was whether to remove them. Kept, because each still has a reason of its own:

- 0465: without it the link ends at the port closing, with mac80211 still associated.
- 0466: without it the loss report reaches `__ieee80211_disconnect()` while associated. That disconnects and, for a
  loss, removes the old access point's entry, ahead of the roam's own disconnect. If the report landed after the new
  association it would end that link. The hold is also what recovers the stale-target failure above.
- 0467: follows from that order, and keeping `join_sco` across a re-arm is needed in any order, or a 40 MHz access
  point joins at 20 MHz. Its refusal (`reasons=0x00100`) was observed.
- 0468: follows from that order; its `-ECANCELED` was observed.

Whether roams would work without 0465 and 0466 is not shown. What the supplicant does with a deauthentication mid-roam
is not checked here. Finding out needs a package and roams for each removal, and the 15 left are better spent
on the rerun and on stage C. The messages of 0465 and 0466 no longer give `No SSID` as the cause; the code is unchanged.

**Stage B, 0469 under a download: same boot, `mac` `3ba824b1…`, run by the custodian.** 10 roams and one reconnect, so
36 of the 40 used, counting that reconnect because the radio protocol's reconnect limit on these channels is spent and
the owner's replacement speaks only of roams. Supplicant starts during setup and restore were not counted, in this run
or earlier ones, which the owner should know.

- 10 of 10 at target, 0.35-0.46 s from disconnect to data phase, longest ping gap 5 pings on one roam and at most 2 on
  the rest. No new `join stopped`, no restart, same `udhcpc`, gateway 3/3 after each. Addresses were not compared, only
  that one was present.
- The stop during a 53 Mbit/s download: cleanup in 74 ms, no `join stopped`, no restart, reconnected in about 1 s.
- So the `-110` did not recur, against 4 of 5 stops and 1 of 3 roams before, on this small sample.
- From `data phase end` to `cleanup: stage=3`: 55-156 ms on nine roams, 680 ms on the first. There, 622 ms pass between
  `PM abort` and the deauthentication's status. The log has no line for the end of the drain, so whether that time counts
  against the 750 ms bound is open. If it does, that roam was close to a restart.

**One download stalled after roam 7, not explained.** `wget` timed out 20 s after that roam, and the phase after
it carried almost nothing:

```
join data phase end: reason=key-disable elapsed_ms=14699 rx_delivered=132 tx_queued=62 tx_done=62 tx_failed=0
data qos: tx_qos=62 rx_qos=62 rx_nonqos=34 rx_refused=2
RX reorder: tid=0 holes=0 expiries=0 duplicates=0 behind=0 held=0
```

Other phases under the download delivered 30-65k frames, one 9.6k. What this shows:

- The driver dropped nothing: no reorder drops and 2 refusals. The TCP frames never reached it, and the station sent
  none, as a receiver with nothing arriving would not.
- Pings kept working, but only to the gateway, so the path from the laptop was not measured.
- A new connection 21 s later, one roam on, ran normally. Roam 8 came only 5 s before the timeout, so it says little
  about the old connection.

Candidates, none measured: the network still forwarding the laptop's frames toward the old access point, with nothing
from the station to correct it while TCP waits; the firmware dropping large or aggregated frames on that one
lifetime; or either end. The previous phase's `behind=26` was the run's highest, a correlation only.

One stall in 12 roams means the 4 roams left would catch another only about a quarter of the time, so a retest with a
laptop capture is not worth them. It belongs with the next budget.

**Stage C, first step: no `bgscan` in the RAM root.** The custodian read the binary: `wpa_supplicant` v2.11 here has the
config field and no `simple` or `learn` module. Nothing ran, and no roam or scan was spent. `bgscan_simple` in the 2.11 source
scans with the network's SSID, and the driver turns any scan with an SSID into probing on channels that allow it. At a 15 s
interval that would use the radio protocol's ten active scans in about 3 minutes. Signal thresholds do not need `bgscan`, so
0458 is tested first with `iw`, which sends no frames.

**0458 alone produced nothing.** `mac` `3ba824b1…`, signal -60: `iw dev wlan0 cqm rssi -40 2` returned 0, and in 30 s there was
no `signal threshold` line and no `iw event`. No roam or scan was spent, and the link was unharmed. This image can't say why.
The likely reason, from the [firmware contract](../../docs/hardware/mt6797-wifi-firmware-contract.md#monitoring-ownership) and
not measured, is that beacons stop reaching the host once connected. Data frames had no signal reported at all, so
`-60` above is probably left from earlier frames.
[0470](../../patches/proposals/0470-wifi-mt6797-take-the-signal-from-data-frames.patch) takes the signal from data frames as well, for the average and for mac80211, and logs
the threshold with the sample and beacon counts, and the end of the drain. Package: Buildbox at `660a1d87`, inventory `748f64a2…`,
`mac` `3a6ef88d…`, with CONSYS and core unchanged. Whether data frames carry a usable value is for the run to show.

**Signal thresholds work at the desk: same boot, `mac` `3a6ef88d…` (0470), run by the custodian.** No roams or scans spent,
36 of 40 still. The rejoin after the swap was one more uncounted supplicant start.

- A threshold 20 dB above the signal gave `event=0` 6 ms after it was set, and 20 dB below gave `event=1`. All 134 events matched
  `iw event` in count and direction, and the first 30 in value.
- Samples: 8.0-8.7/s with a 5/s ping, 3.3/s over an idle minute. The idle figure depends on what the access point sends,
  probably broadcasts, on this network. A quieter one gives fewer.
- `beacons=` stayed at 20 for the 428 s logged, so beacons do stop reaching the host early in a connection. The samples are data frames.
- The average moves between about -60 and -66 with the device still, around -65 with the ping and -60 idle. At a 1 dB
  hysteresis that gave an event every 2.4 s; at 2 dB, idle, none in a minute. What the swing follows, such as frame type or rate,
  is not known. A trigger needs a hysteresis above it, and repeated events in one direction are the rule's normal behaviour.
- No taint, restart or `join stopped`, and no ping gap.

This shows the events reach userspace. It doesn't show roaming by itself, which needs a trigger and the device moving.

**A supplicant with `bgscan`.** The owner chose a rebuild over a script on 2026-11-02 ("Rebuild with bgscan"), the real
behaviour over a test-only one. [`build-wpa-supplicant.sh`](build-wpa-supplicant.sh) builds 2.11 statically in the dev VM, as the
station's other tools are, `wpa_supplicant` `ff292b2a…` and `wpa_cli` `60a415c8…`. It has no EAP or SAE, which this network does not use.

Reading the 2.11 source: a roam decision takes the current level from a signal poll, using the beacon average if the driver
reports one and otherwise the station's average. mac80211 reports no beacon average with beacon filtering, so the level comes
from the data-frame signal that 0470 added; before it there was none. A roam then needs the target about 5 dB stronger at -70 dBm and
above, 1 dB at -86 and below, adjusted by estimated throughput. `bgscan_simple` asks for a 4 dB hysteresis, smaller than the
6 dB swing seen at the desk, so the threshold should sit well below a healthy signal.

**`bgscan` at the desk: same boot, `mac` `3a6ef88d…`, the rebuilt supplicant, run by the custodian.** No roams spent; 8 active
scans on this boot, counting 2 earlier ones it cannot place in another session.

- It associated first try, with its own connect scan passive.
- 6 connected scans at 60 s intervals, each `probing=2 ssids=1`, about 0.41 s, none refused, then the back-off to the long
  interval. A 5/s ping lost at most one reply in 600 s. No restart, `join stopped` or taint.
- The threshold set from the supplicant arrived with `hyst=4`, and one event followed, with its `bgscan simple: signal level changed`.
- Each scan selected the current access point, the stronger by about 9 dB, and `wpa_supplicant_need_to_roam()` returns on that before
  it compares levels. So the live level in a roam decision has not been seen.
- `iw dev wlan0 link` read 2-5 dB below the scan results for the same access point; which is nearer is not known.

**The first roam by itself: same boot, `mac` `3a6ef88d…`, the rebuilt supplicant, run by the custodian.** Started on channel 40 by
limiting the network block to it, then widened with `set_network`, with no reconnect. 37 of 40 roams, 9 active scans.

```
signal threshold: event=0 average=-66 samples=201
connected scan: admitted=1 channels=2 probing=2 ssids=1
Using signal poll values for the current BSS: level=-65 snr=27 est_throughput=132300
Allow reassociation due to difference in signal level (12 >= 4)
disconnect from AP for new auth
connected data phase
```

- From threshold event to data phase took 0.88 s, 0.38 s of it from disconnect to data phase. No ping gap, same `udhcpc` and address, no
  restart, `join stopped` or taint.
- The level was live: -65 from the poll against a driver average of -66 and -63 in the scan. This is the path 0470 feeds.
- The scan came 22 s after association, not at 60 s. Below the threshold, a further 4 dB drop starts a scan at once if the last was
  over 10 s ago, and here the threshold was set above the signal on purpose. So the desk's swing can start scans once a walking device
  is under the threshold.
- The `drain end:` line only appears when frames were owed; there was none here, with only a ping running.

One roam, between two access points, device still. It shows the chain, not roaming on the move.

**The walk's first start stopped before anyone moved.** 0 roams, 0 active scans. Stopping the old supplicant at the script's start
ended that lifetime at sequence 255, past the wrap limit of 248, which restarts the firmware on purpose. It rejoined in about 3 s, with no
address, the known lease gap, and `progress.txt` showed `COMPLETED` regardless. The custodian held the owner back.

The cause is this boot's module swaps, from the code and log. `sequence_base` is taken from the first lifetime after a module
load, so a swap inherits a high one, here 146, and a re-arm only recycles when the base is at most 128. A connected scan recycles with no such check,
which is why it went unseen. Booted images and the state after this restart start low, at `sequence=37` here, so the wrap is
not expected on the walk unless `mac` is swapped again. Not changed in the driver.

The script now restarts `udhcpc` when connected with no address and logs `inet=` in its progress. That branch has not run.

**Stage D, the walk: same boot, `mac` `3a6ef88d…`, the rebuilt supplicant, 20 minutes, two trips, run by the custodian and walked by
the owner.** The owner allowed the rerun ("Yes, allow a rerun") and offered the second trip. `end=time roams=7 scans=28 restarts=0
stopped=0`, of the budget's 20 and 60. No firmware restart, no `join stopped`, no taint. Sequence recycling worked (`from=208 to=13`), which
supports the reading of the aborted start above. The `udhcpc` branch did not run.

| Uptime | Move | Disconnect to data phase | Current vs selected level | Result | `rx_qos` in the phase after |
| --- | --- | --- | --- | --- | --- |
| 48001 | 5805 to 5745 | 0.47 s | -75 vs -74 | Moved | 0 |
| 48014 | 5745 to 5240 | | -92 vs -52 | Handshake failed | |
| 48031 | to 5240, fresh join, after an authentication timeout on 5200 | | | Handshake failed; joined 5200 at 48056 | 31736 |
| 48089 | 5200 to 5805 | 0.40 s | -72 vs -59 | Moved | 1143386 |
| 48325 | 5805 to 5745 | 0.46 s | -72 vs -66 | Moved | 0 |
| 48357 | 5745 to 5240 | | -81 vs -53 | Handshake failed; joined 5200 at 48373 | 0 |
| 48496 | 5200 to 5240 | | -78 vs -53 | Handshake failed; joined 5200 at 48512 | 0 |
| 48846 | 5200 to 5805 | 0.53 s | | Moved | 746162 |

So the device changes access point by itself in both directions, with the handover near the desk's. The walk's other two rows did not
hold: gaps were not under 1 s, the longest 57 s and 521 s of ping, and downloads failed from 48325 to 48828.

**Every handshake on 5240 failed, 4 of 4, with that access point the strongest at -52 to -53.** Authentication and association pass, by
reassociation or fresh, so it isn't the roam. Message 2 is sent for each message 1 and acknowledged, with a new status each time, the access point keeps
sending message 1 about once a second, and deauthenticates with reason 2 after about 4 s. The other three access points complete with the
same key and supplicant, the same 2/4 handling and the same cipher and key management. So it looks like that access point not accepting message 2, but why is
not known; a different key on it, or something in our frame that only it checks, would both look like this. It is also the first time this
device has been on that channel. Not tested with the original supplicant.

**The link stayed up with no received data in all four phases at about -78 or below.** `rx_qos=0`, no block-ack start, ping and TCP dead, while broadcasts and
beacons arrived and transmits were reported done, which turned out not to mean acknowledged, as below. Average signal in those phases: -83, -78, -79, -80. Every other phase averaged -58 to -70.

- The driver didn't drop these frames: `rx_refused_qos=0` throughout. The `data rx refused` lines are mostly 690-byte frames with `wlan=255`, not from this
  link's station entry, and a good phase had 965 refusals. This also answers the earlier question about those lines, at least for this shape.
- From this log alone the unicast frames could be undelivered either way: not sent by the access point because our uplink isn't heard or decrypted, or
  sent and not received. Weak signal correlates, and doesn't obviously explain none at all in 334 s. That is the part to find out.
- The device was in that state because 5240 had refused it and the supplicant returned to the weak access point, so the two faults compound.
- `-75 vs -74` moved on estimated throughput, to a worse link than it was leaving.
- Before the walk, the [channel tests](../2026-11-01-mt6797-wifi-any-channel/README.md) had not run a secondary channel above (`sco=1`), or channels 149 or 48. Both phases on 149 were `sco=1` and had `rx_qos=0`, so those two may be that rather than the signal. The two on 5200 at `sco=3` can't be, since other phases on it worked.

The owner says the access point on 5240 has the same setup as the others ("It's the same setup"), so a different key on it is unlikely. Something in our frame or the supplicant remains.

A correction for the earlier stall too: the laptop was on Wi-Fi then as well, so its own link is another candidate. The laptop's sampler shows no TCP connection
for 495 s from about 48354, so nothing reached it through this outage.

The owner went to sleep and, as the custodian relays, told it: "keep going on the roaming progress". The
limits stay: 40 roams, the owner's non-DFS 5 GHz access points, no boot2 flash or reboot on this boot.

Refused `rxd-byte4` frames with `fc=0x6208` also appear in this window; they look like protected data
arriving with no key installed, not investigated.

Also in the first try's log, and again in this run up to 1776.66 s, not investigated: 64 `data rx refused` lines (`field=packet-type`), the first at
64.87 s and the rest from 259.86 s.

### Two desk tests of the faults

[`wifi-desk-join.sh`](wifi-desk-join.sh) joins one access point with the original supplicant, passive scan and no bgscan, pinned, pings the gateway for 60 s where the handshake completes, and returns to the normal link. This needs no walking and uses no roams or active scans. Each is one join within that channel's [radio protocol](../2026-11-01-mt6797-wifi-any-channel/README.md).

| Test | Observation | Next |
| --- | --- | --- |
| 5240 | Handshake fails as on the walk | Not the rebuilt supplicant; compare that access point's beacon and message 1 with the others', then message 2 |
| 5240 | Handshake completes, ping works | Rebuilt supplicant or the roam's state; repeat with the rebuilt one, no bgscan |
| 5745, `sco=1` | `rx_qos=0`, no replies | The `sco=1` setting at any signal, not weakness; read the channel request for that case |
| 5745, `sco=1` | Replies, `rx_qos` above 0 | `sco=1` works at this signal; Fault 2 follows signal, and the question is what fails below it |
| Either | Firmware restart at the join | The sequence wrap after a module swap, as at the walk's start; not this test's answer, rerun once |

**5745 at the desk, boot `6b3acef8`:** the original supplicant completed in 2 s, then 0 of 300 pings came back with `tx_done=326`, `tx_failed=5`, `rx_qos=0`, `rx_nonqos=219` and `rx_refused_qos=0`. The join's average was -79, not the -75 I expected, so this repeats the walk's two phases and rules the rebuilt supplicant and bgscan out of them. It doesn't separate `sco=1` from signal. No restart, and the normal link came back with gateway 3/3.

5240 did not run. At the desk it now reads -83, against -52 on the walk, so a failure there would say little, and its failed joins hit the protocol's stop condition. That test needs a position near that access point.

Next, the same access point and signal at 20 MHz: `wifi-desk-join.sh 5745 ht20` sets `disable_ht40`, and mac80211 then limits the link to 20 MHz, as `net/mac80211/mlme.c` does from the overridden capability. The supplicant differs too, but the rebuilt one showed the same fault on the walk.

| Observation at 20 MHz, `sco=0` | Next |
| --- | --- |
| Join is not `sco=0` | The override didn't take; read the supplicant log |
| Replies, `rx_qos` above 0 | The 40 MHz link is what fails here, as a setting or at this signal; a weak `sco=3` link separates those |
| No replies, `rx_qos=0` | Not width: signal, or this access point or channel, at any width |

**5745 with `ht20`:** the supplicant reported `WIDTH=20 MHz`, `LINKSPEED=13` and `AVG_RSSI=-76`, and 2 of 300 pings came back, with `tx_done=288`, `tx_failed=4` and `rx_qos=4`. It isn't a clean 20 MHz test: the channel grant still read `sco=1`. mac80211 takes the override at association (`ifmgd->ht_capa`, `net/mac80211/mlme.c`), and the driver had already asked for its channel with the 40 MHz definition used for authentication. So my row for that case, "the override didn't take", was wrong: it took for the link and not for the grant. Lowering the negotiated width did not bring the link back, which makes width less likely but doesn't exclude the radio's 40 MHz setting.

Inference, not yet observed: the access point may not be sending these replies at all, which would put the loss above the acknowledgement on our uplink.

- Across this boot's log, tid 0 block-ack sessions open within about a second of a working link, and tid 6 too. None opened on tid 0 in this run or in the walk's dead phases, though action frames do arrive, as the two on tid 5 and one on tid 6 here show.
- The two tid 5 sessions opened with start sequence 0 and then 1, about when the two replies arrived. The first reply came about 50 s into the ping. If those replies are tid 5, the access point numbered only those two frames there. Which tid they used isn't logged.

This paragraph's first reading, that the access point acknowledged our frames, was wrong; see the fixed-rate result below.

Next, the same join with `PEER` set to the laptop's address on this LAN, reading the laptop's ICMP input counter with `netstat -s -p icmp` before and after, which needs no capture rights.

| Echo requests at the laptop, of 300 | Device replies | Reading |
| --- | --- | --- |
| About 300 | About 0 | Uplink works; the replies don't reach the device. Back to the receive path |
| About 300 | About 300 | The fault is on the path to the gateway; the device and access point work |
| About 0 | About 0 | The frames do not get past the access point, for example not decrypted by that access point. Read the key installation and transmit descriptor |

**That run, `PEER` at 40 MHz:** the laptop's echo count rose by 3, the control pings, and 0 of 300 came back. This does not show that the access point fails to forward. The driver queued only 57 frames in 70.8 s, against 331 to the gateway, as the custodian noticed. Losing carrier flushes the neighbour table (`net/ipv4/arp.c`), so the pings waited on an address, and those frames are most likely ARP requests at about 1 a second. No capture confirms that. So my "about 3" row can't be read from this run. It does add something: if those were ARP requests, no unicast reply reached the device in 60 s, with `rx_qos=0`. The gateway's address probably resolved from its own broadcast request, though that isn't observed either. The script's mark also matched the previous run, so its counts spanned both, all zero.

The script now holds the peer's entry static for the test, which the flush leaves alone, reports it after the ping, removes it afterwards and prints `data phase end`, so the rerun can show the frames were sent. The table above applies only if `tx_queued` is about 300 or more and `peer_flags` is `0x6`.

**The rerun, with the entry static:** `tx_queued=300`, `tx_done=296`, `tx_failed=4`, `peer_flags=0x6`. The laptop counted only the 3 control echoes and 0 of 300 came back. So the frames left the device and did not reach the laptop. `tx_done` is the firmware's status 0, taken as acknowledged, and nothing on the air has confirmed that.

**A candidate cause, which I should have checked first:** `rate_control` defaults to off, so ordinary data goes at a fixed HT MCS5, at 40 MHz on a 40 MHz link, with three attempts and no fallback. Management and EAPOL frames go at OFDM 6 Mbit/s. That would fit the fault's shape: the join completes and broadcasts arrive, then no data at about -78 or weaker. It would cover 5200 as well as 5745, with no `sco=1` fault needed. What does not fit is the acknowledgements, since an access point that can't decode a frame shouldn't acknowledge it. The value on this boot is not in my records. `LINKSPEED=13` is not the sent rate, since a fixed-rate status names none.

Next, the same join with `rate_control` on for that join only, with the script mode `rc`. No module swap is needed, since the driver reads it at each association.

| Observation | Next |
| --- | --- |
| `rate_control` was already on | This candidate is wrong; a fixed 6 Mbit/s mask is the next separation |
| Replies, laptop count near 303 | Fixed MCS5 is Fault 2 on this link. Compare throughput, then make rate control the default |
| Still none, `tx bitrate` stays high | The status misleads minstrel; try a fixed 6 Mbit/s mask |
| Still none, `tx bitrate` low | Not the rate; encryption or that access point. Read key installation and the descriptor |

**The result, Fault 2: ordinary data at the fixed rate is not getting through, and the counters hid it.** With `rate_control` on for one join on 5745 at -77, data flowed for the first time: 105 of 300 replies, and the laptop counted 108 echoes, the 3 control pings and those 105.

The "acknowledged" puzzle above was my misreading. `tx_done` does not mean acknowledged. At the fixed rate, one frame in 64 asks for a status (0281) and the rest are retired when their credit returns, counted as done. `tx_failed` therefore counts only the sampled frames, and in the dead phases it is about all of them:

| Phase | `tx_queued` | Queued / 64 | `tx_failed` | `rx_qos` |
| --- | --- | --- | --- | --- |
| Walk, 149 | 174 | 2.7 | 2 | 0 |
| Walk, 5200, weak | 754 | 11.8 | 11 | 0 |
| Walk, 5200, weak | 2026 | 31.7 | 31 | 0 |
| Desk, 149 | 300 | 4.7 | 4 | 0 |
| Desk, 149, `ht20` | 292 | 4.6 | 4 | 4 |
| Walk, 161, strong | 258513 | 4039 | 0 | 1143386 |
| Before the walk, strong | 223547 | 3493 | 1 | 859029 |

So the sampled frames at the fixed HT MCS5 all failed in those phases and almost none failed on strong links. Management and EAPOL frames go at 6 Mbit/s, and each asks for a status, which is why joins complete. This is one fault across channels. It removes the need for a separate `sco=1` fault, for these results, and it means no evidence remains of frames reaching the access point undelivered. No capture confirms what was on the air, and the rate sent during the rate control run was not read.

**Rate control has its own fault here.** The link dropped every 3 to 4 s with `reason=txfail`, usually after 7 done and 8 failed. Eight failures in a row end the data phase, and with rate control every probe frame reports, while most others are counted done on credit. So I think failing probes of higher rates end a link that is otherwise carrying data; that is from the code and these counts, since the rates were not logged.

**A budget breach, caused by my script.** The supplicant rejoined by itself after each drop, so this run made 15 joins on 149 where I had counted one, taking that channel to 21 against a limit of 10. The script had no cap and my request didn't consider it. The script now ends the test at the first disconnect. The custodian has told the owner, and 149 stays closed until the owner rules.

**A second driver stop, not explained.** The 15th join stopped with `status=-95 first=-95` at `sequence=195`, followed by a firmware restart. It is not the known wrap, which sets `-EOWNERDEAD` at a higher sequence. The normal link was recovered by the custodian with its usual steps, without a module reload.

**The fix, 0471, approved by the owner on 2026-11-02 ("Yes, write the fix"):** rate control on by default, probe failures not counted toward the eight, at most one frame in 16 a probe, and at least one report each 100 ms. The code supports the reading above: frames that don't report are counted done on credit, which resets the count of failures in a row, so eight in a row had to be frames that report, nearly all probes. `minstrel_ht` may probe every 20 ms, so at 5 frames a second most frames are probes, and with one rate per frame a failed probe loses its frame. That would also explain why only about half the frames were delivered, on top of the drops. Compiled with `W=1`; not yet run. The earlier [comparison](../2026-10-13-mt6797-wifi-native-delivery-probe/THROUGHPUT_SERIES_RESULT.md#rate-control-against-the-fixed-rate-2026-10-27-boot-av) measured rate control at 0.83x the fixed rate's transmit at 40 MHz on a strong link.

### Testing 0471

A strong channel first, since 149 is closed until the owner rules, with `tx_probe_failed` in the phase end line to read.

Hypothesis: on a strong link 0471 keeps the link, with no `txfail`, ramps as before and transmits at about 0.83x the fixed rate or better. The weak-link claim needs a weak link, so this does not test it.

| Observation | Next |
| --- | --- |
| No `txfail`, ping clean, throughput near the earlier rate control figures | Ask the owner for a weak link: 149 if allowed, or a walk |
| `txfail` on a strong link | The reading above is wrong or incomplete; read the failures |
| Throughput far below those figures | The probe limit or the reports cost more than planned; tune or reconsider |

**Result on 5200, boot `6b3acef8`, `mac` 33fdc4ec, one single run of each:** `rate_control=Y`, no `txfail`, no restart and no active scans. 0 of 300 pings lost at -64 to -66, `tx_failed=2`, `tx_probe_failed=0`, and the rate reached MCS7 at 40 MHz. Receive was 49.1 Mbit/s and transmit 23.6, or 22.2 at the laptop's end. The earlier figures may have used another method, so these are comparable only roughly: transmit is close to the earlier rate control figures, and receive is above them, which this run doesn't explain. So the first row holds, and 0471 stays loaded. The weak-link claim is still untested.

### Second walk: 0471 on a weak link

The owner chose a walk over another join on 149 ("Another walk instead"). Same route, setup and limits as Stage D, with `mac` 33fdc4ec.

Hypothesis: weak phases now carry data. Where the first walk had `rx_qos=0` at about -78 or weaker, data now flows at a lower rate, and the link stays up or moves on without `txfail` repeating.

- **Channels:** only 5200 and 5805, in `scan_freq` and `freq_list`. 149 is closed until the owner rules, and 48 refused every handshake, so a failed join there would hit the protocol's stop condition and hide this result. The device has to reach further on these two, which suits this test, and this walk can't test those two channels.
- **Before it:** a full module reload, so the sequence starts low and the earlier stops are cleared as the protocol asks.
- **Logging:** the script's progress line now has the average signal and transmit rate every 5 s, which the last test lacked.
- **Budget, approved by the owner on 2026-11-02** ("Approve budget"), for this walk only: 20 roams and 60 active scans, the script's limits, on those two channels.

| Observation | Next |
| --- | --- |
| Data flows in weak phases, no repeated `txfail`, gaps near 1 s | The fix holds on a weak link. Then channel 48's handshake, and a real network manager |
| Data flows, but repeated `txfail` | The eight failures are too few when the rate has to fall; read which frames failed |
| `rx_qos=0` again at low rate | Not only the rate; read the phase and reconsider a capture |
| Low rate is reached, but the link is too slow to use | The threshold should move earlier; tune `bgscan` |
| Stays on one access point throughout | Not a test of roaming; read the threshold events |
