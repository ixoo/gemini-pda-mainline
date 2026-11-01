# Experiment: Wi-Fi on any network and channel (daily-use plan, phase 3)

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-mt6797-wifi-any-channel` |
| Status | `running`: passive and active scan work, including named SSIDs and a supplicant join. 0414 joins channels 40 and 161, and 0443 recovers from faults by itself. Channel 11 transmits poorly, channel 6 failed, and faults at disconnect under traffic are open |
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

By module swap on station 29. Buildbox at a4851e47, 581 patches, package
inventory `c362711b…`: `Image.gz` (`8ef83b55…`), CONSYS and core are
byte-identical to station 29's, and only `mac` differs (`a0bcb958…`, was
`d5a41fb1…`). Copy `mac.ko` to the RAM root, `rmmod mac`, `insmod` it.

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

## Observations

Run by the device custodian on station 29, boot `c08cf8d4`, `mac` `a0bcb958…`
swapped in with `rmmod mac` and `insmod` (2026-11-01).

| Step | Result |
| --- | --- |
| 1. Three full scans | Exit status 0, 1.53-1.55 s each, no BSS listed. One admitted and one completed scan each, `complete=1 frame=1 beacon=1` |
| 2. Subset scans | Did not run: the test script had `passive` before `freq`, a usage error |
| 3. Join after the scans | Failed. Authentication, association and the first EAPOL frame went through, then `join stopped: status=-125 ... branch=9` right after `associated`. Later scans were refused with `-EOPNOTSUPP` |
| 3b. Full module reload, keeping 0410, no scans first (the custodian's addition) | `COMPLETED` on 5200 MHz, a lease, gateway 3/3. Ping 10/10, ten reconnects 10/10. Receive 45 and 43, transmit 21 and 23 Mbit/s |
| 4. Kernel log | No Oops, warning or call trace; not tainted |

## Analysis

These explanations come from the log and a source read; neither has been run.

- **The empty scans.** mac80211 calls `hw_scan` once per band unless the driver
  sets `SINGLE_SCAN_ON_ALL_BANDS`. The first call covered 2.4 GHz: 11 channels
  at 130 ms is 1.43 s, against the 1.53 s measured. The second call, for 5 GHz,
  got `-EBUSY`, since a lifetime takes one scan, so mac80211 reported the scan
  aborted. `iw` then prints "scan aborted!", lists nothing and exits 0. So
  `bss=0` does not show an empty scan table. `beacon=1` suggests 2.4 GHz frames
  did arrive, but no per-frequency count exists yet, and 5 GHz sweeps have not run.
- **The failed join.** Branch 9 is a regulatory update during a lifetime, not
  a scan effect. A `mac` re-attach never records what the firmware was sent
  (`reg_sent_valid` stays false), so 0405's comparison cannot run and the access
  point's country element ends the lifetime. A full reload sends the record,
  which sets it, so step 3b differs from step 3 in the reload as well as in the
  scans. This predicts that the failure follows the `mac`-only reload and needs
  no scan, and that older `mac` builds with 0405 fail the same way.
- **The dwell.** The firmware appears to honour it: 500 ms for one channel took
  0.53 s, and the 2.4 GHz sweep fits 130 ms per channel.

## Second test

Patches:
- [0412](../../patches/proposals/0412-wifi-mt6797-scan-both-bands-in-one-hardware-scan.patch) sets `SINGLE_SCAN_ON_ALL_BANDS`.
- [0413](../../patches/proposals/0413-wifi-mt6797-send-the-regulatory-state-on-a-re-attach.patch) sends the domain and power on a re-attach and records them.

Hypothesis: a full scan takes about 5 s and lists BSSes on both bands, and a
join after a `mac`-only reload and idle scans completes.

The procedure is unchanged, with the script fixed, and swaps `mac` only, so
step 3 tests 0413 directly.

| Observation | Decision |
| --- | --- |
| Full scan near 5 s with BSSes on both bands, join and reconnects pass | Multi-channel scan works; ask the owner about the transmit protocol, then unpin join |
| Scan near 5 s, one band empty | Ask the owner what a phone sees there, then compare the firmware's regulatory lists with the request |
| Second firmware request never completes, or its count differs | Read the event; stop and recover with a full reload, no retry |
| Fewer BSSes on 5200 in the sweep than in the 500 ms scan | Raise the sweep dwell |
| Join still ends with branch 9 after the `mac`-only reload | The analysis is wrong; read the notifier's inputs before any change |
| Join fails only after idle scans, in some other way | Read the post-scan path |

### Result: second test, boot `c08cf8d4` (2026-11-01)

Run by the device custodian. Buildbox at a70416e3, package inventory
`ee5fc0dd…`, `mac` `a2b6fd46…`, `Image.gz` `8ef83b55…`. Swapped with `rmmod mac`
and `insmod`, with no full reload.

| Step | Result |
| --- | --- |
| 1. Three full scans | Exit status 0 in 5.97, 5.30 and 5.30 s. 23, 24 and 22 BSSes: 2412 MHz 3, 2437 7-9, 2462 2, 5200 3, 5240 3, 5745 1, 5805 3 |
| 2. Subset scans | 2412/2437/2462 in 0.48 s; 5200 in 0.55 s; both with frames. 5260/5500 in 0.33 s, nothing heard |
| 3. Join after the scans | `COMPLETED` on 5200 MHz WPA2-PSK/CCMP, a lease, gateway 3/3. Ping 10/10 (8.5 ms average), ten reconnects 10/10. Receive 38 and 39, transmit 22 and 23 Mbit/s |
| 4. Kernel log | No Oops, warning or call trace; no branch 9 or "submission stopped"; not tainted |

The first decision row holds:
- **Both fixes.** The full scan lists both bands, and a join after a `mac`-only
  reload and idle scans completes, so both explanations in the analysis fit.
- **The second firmware request.** The log has one line per scan, not one per
  request. Still, in the US list the first request ends at channel 149, so
  5805 MHz (channel 161) can only come from the second.
- **Dwell.** The sweep found the same three BSSes on 5200 MHz each time, so
  nothing shows it losing any. The subset counts can't compare dwells, because
  `iw` lists the kernel's cached results.
- **Throughput.** Receive here is at the low end of the range since station 24
  (37-47 Mbit/s), and the same module read 38 and 39 only; 0410's run read 43
  and 45. These few samples do not separate that from the air.

Not shown:
- reception on a DFS channel: nothing was heard on any, and whether an access
  point is there is unknown;
- that no frame was transmitted during the scans, since nothing measures the air;
- a hidden network, since these scans send no probes.

## Radio protocol (approved by the owner, 2026-11-01)

Everything before this section transmits only on channel 40. This is the
protocol for transmitting elsewhere.

Scope, in order, each stage on its own driver patch and hypothesis:
1. **Join on another 5 GHz channel**, non-DFS (36-48 or 149-165), on the owner's
   own access point: 20 MHz, then HT40.
2. **Join on 2.4 GHz** channels 1, 6 and 11, on the owner's own access point or
   phone hotspot, 20 MHz only.
3. **Active scan:** probe requests on channels cfg80211 marks usable, naming only
   the requested SSIDs. DFS and other no-IR channels stay passive.

Limits:
- **Networks.** Only access points the owner names. Others are heard in scans
  and never contacted.
- **Country.** US, the station's setting. Channels and power come from
  `regulatory.db` through cfg80211; 12 and 13 stay disabled. The driver has
  no way to raise them.
- **Power.** The firmware's existing limits with the device's own calibration
  record, as on channel 40. Output is not measured by any instrument here.
- **Excluded.** Joining a DFS channel, access-point mode, monitor mode and
  injection, which each need their own approval.
- **Budget per channel.** One join, DHCP, a gateway ping, ten reconnects and a
  60 s transfer each way. Active scan: at most ten scans in a session.
- **Stop conditions.** Those of [safety](../../docs/SAFETY.md#stop-conditions),
  plus any firmware fault or a join that fails twice: stop, recover with a full
  module reload, and read the log before any retry.

Known limit: an access point advertising a country other than US still ends
the lifetime until a module reload, so test access points should advertise US.

## Stage 1: join on other 5 GHz channels

[0414](../../patches/proposals/0414-wifi-mt6797-join-any-non-DFS-5-GHz-channel.patch) takes the channel from mac80211's
operating channel in the join commands and on every receive path, and adds HT40
with the secondary channel above. `mac` still refuses 2.4 GHz and channels
marked no-IR or radar, before any command reaches the firmware.
[`wifi-up.sh`](../2026-10-30-mainline-dev-station/wifi-up.sh) no longer pins the
frequency, and pins the BSSID only if the private file names one.

The core module's exported join call changes, so this needs a full module
reload. A join now starts from a full scan of about 5 s unless `TARGET_FREQ`
is set.

**Control on channel 40**, on the owner's access point, no new transmission.
Hypothesis: `grant: channel=40 sco=3`, with join, ten reconnects and throughput
as before.

| Observation | Decision |
| --- | --- |
| Join, reconnects and throughput as before | The change kept channel 40; go to another channel when the owner's access point is ready |
| Grant refused or join fails on channel 40 | Stop and read the log; compare the commands with 0413's |
| Reconnects fail with the full scan but pass with `TARGET_FREQ=5200` | Read the post-scan path: the join must start inside the 10 s after the scan |

**Other channels**, within the protocol's budget. First a non-DFS 5 GHz channel on
an access point the owner names, with a private file pinning its BSSID and
frequency. Hypothesis: `grant: channel=N` with the matching `sco`, `COMPLETED`, a
lease, gateway ping, ten reconnects, 60 s transfer each way.

| Observation | Decision |
| --- | --- |
| All pass at 20 and 40 MHz | Stage 1 is done for that channel. Repeat on one UNII-3 channel if the owner has one, then stage 2 |
| The firmware refuses the grant | Stop. Compare the channel with the firmware's domain list |
| Join passes, data fails | Stop. Read the receive status lines for the descriptor's channel |
| HT40 fails, 20 MHz passes | Keep 20 MHz for that secondary offset and read the secondary channel path |

### Result: channel 40 control, boot `c08cf8d4` (2026-11-01)

Run by the device custodian. Buildbox at beef6040, package inventory `de177d6b…`,
`mac` `1b64ede6…`, core `e37a1686…`, `Image.gz` `8ef83b55…`, full module reload.
The private file pins the BSSID, not the frequency. The audio modules were loaded,
and no audio ran.

| Check | Result |
| --- | --- |
| Join | `COMPLETED` on 5200 MHz WPA2-PSK/CCMP, a lease, gateway 3/3; `join grant: channel=40 sco=3` on all 11 joins |
| Ping | 10/10, 8.2 ms average |
| Ten reconnects | 10/10, each 2/2. The first took 5.70 s, the rest 1.36-1.47 s |
| Throughput | Receive 40 and 42, transmit 22 and 23 Mbit/s |
| Kernel log | No Oops, warning, call trace, branch 9 or "submission stopped"; not tainted |

The first decision row holds. The prediction of 6-7 s per reconnect was wrong:
only the first reconnect took about 5 s. Every reconnect still scanned, and the
later scans lasted about 0.88 s, which fits about seven channels at 130 ms.
`wpa_supplicant` probably narrows the list to channels it has recently seen
networks on (inferred, since the request's list isn't logged). That accounts for
the extra 0.3-0.4 s over a 500 ms one-channel scan.

This shows 0414 keeps channel 40. It does not test another channel, HT40 with the
secondary channel above, or a join by name without a BSSID.

### Channel 161: predeclared (2026-11-01)

A passive scan heard the owner's network name on other channels, and the owner
confirmed those access points are theirs and named channel 161 (5805 MHz) for this
test, so it needs no router change. The RAM copy of the private file sets
`TARGET_FREQ=5805` and drops the BSSID pin, so this is also the first join by name.

Hypothesis: the operating channel is 161 and `join grant: channel=161` appears
with `sco=3` at HT40 (secondary channel 157) or `sco=0` at 20 MHz. Then `COMPLETED`, a
lease, a gateway ping, ten reconnects and a 60 s transfer each way. The decision
table above applies. This does not test a secondary channel above; that needs
a channel such as 149 at a usable signal.

### Result: channel 161, boot `c08cf8d4` (2026-11-01)

Run by the device custodian, on the 0414 modules, within the protocol's budget.

| Check | Result |
| --- | --- |
| Join by name, no BSSID pin | `COMPLETED` on 5805 MHz, WPA2-PSK/CCMP, a lease, gateway 3/3, 40 MHz, -60 dBm |
| Grant | `join grant: channel=161 sco=3` on all 11 joins |
| Ping | 10/10, 9.9 ms average |
| Ten reconnects | 10/10 in 1.00-1.13 s, each 2/2, all on 5805 MHz |
| 60 s each way | Receive 56, transmit 22 Mbit/s |
| Temperature | SoC 30.7 to 31.4 C, battery 24.1 C throughout |
| Kernel log | No Oops, warning, call trace, branch 9, "submission stopped", "channel refused" or "join stopped"; not tainted |
| Back on channel 40 | With the unchanged private file: `COMPLETED`, a lease, gateway 3/3 |

The first decision row holds: the station joined a channel other than 40 for the
first time, in the other UNII group, and carried data both ways.

- **Reconnect time.** 1.00-1.13 s matches the earlier pinned runs. `TARGET_FREQ`
  gives a one-channel scan, against about seven channels in the channel 40
  control, so the difference comes from the private file (inferred).
- **Throughput.** Receive is above channel 40's range and transmit is the same.
  The access point differs, so this says nothing about the driver.

Not tested: a secondary channel above (`sco=1`), channel 149 or 48, 2.4 GHz, and
a join with no frequency pin that picks among access points of one name.

## Stage 2: join on 2.4 GHz

[0420](../../patches/proposals/0420-wifi-mt6797-join-2.4-GHz-channels-at-20-MHz.patch) admits 2.4 GHz channels at 20 MHz. Channel
and BSS records carry the band, the records carry the ERP PHY type, and the CCK
rates map to the firmware's own positions, following the public vendor source.
`mac` still refuses no-IR and radar channels.

Limits by design: every frame goes at OFDM 6 Mbit/s or the fixed MCS 5, so an
802.11b network is refused. ERP protection stays off, so a transfer beside 802.11b
stations may suffer. Receive and data descriptor gates were read against 5 GHz
frames only; a 2.4 GHz frame may need changes there.

**Control on channel 40**, no new channel, since the budget allows no
repeat on 161.
Hypothesis: `grant: channel=40 sco=3`, with join, ten reconnects and throughput
as before.

| Observation | Decision |
| --- | --- |
| As before | Go to a 2.4 GHz channel the owner names |
| Grant refused or join fails | Stop, read the log, compare with 0414's commands |

**A 2.4 GHz channel**, within the protocol's budget, on channel 6 of the owner's
network, as the owner named on 2026-11-01. Hypothesis: `grant: channel=N sco=0`, `COMPLETED`, a lease, gateway ping,
ten reconnects, 60 s transfer each way.

| Observation | Decision |
| --- | --- |
| All pass | Stage 2 passes on that channel; try the others in the protocol |
| The firmware refuses the grant or the join | Stop. Compare with the firmware's domain list and the records |
| Association passes, handshake or data fails | Stop. Read the receive refusal lines for what differs on 2.4 GHz |
| Works with poor throughput | Record it. Check the rate first: the fixed rate may not suit the access point |

## Stage 3: active scan

[0423](../../patches/proposals/0423-wifi-mt6797-scan-actively-with-SSIDs-where-probing-i.patch) sends probe requests on channels cfg80211
marks usable, for the wildcard or up to four named SSIDs. Channels marked no-IR or
radar stay in passive requests of their own, enforced in `mac`.

Runs after stages 1 and 2, within the protocol's budget of ten scans in a session.

Hypothesis, by `iw`, with `wpa_supplicant` stopped:
- `iw dev wlan0 scan` reports `probing=N` with N below `channels`, and lists at
  least the BSSes of a passive scan, in less time or about the same;
- `iw dev wlan0 scan ssid <owner's network>` finds that network;
- with `passive_scan=1` removed from the supplicant's configuration, a join works.

Nothing measures the air, so the absence of probes on a no-IR channel rests on the
request list in the kernel log and the firmware honouring the passive type.

| Observation | Decision |
| --- | --- |
| All pass | `wifi-up.sh` drops `passive_scan=1`; go to a hidden network if the owner has one |
| Scan rejected or never completes | Stop. Read the request's bytes against the vendor's |
| Wildcard works, a named SSID finds nothing | Try the SSID count byte set, since the vendor leaves it zero |
| Finds fewer BSSes than passive | Compare the firmware's default dwell with passive's 130 ms |

## Scan while connected (phase 4, predeclared)

[0430](../../patches/proposals/0430-wifi-mt6797-scan-while-connected.patch) lets a scan run during a connection. This is the
first half of roaming; reassociation is not written. Compile-checked only. It
follows stage 3, and a scan counts against that stage's budget.

Hypothesis: with a connection up and a ping running, `iw dev wlan0 scan` and
`iw dev wlan0 scan passive` complete, list both bands, and the connection stays,
with some ping delay during the scan. Measured:
- the scan's duration and the longest ping gap;
- that a 10 s transfer continues, at lower throughput, through a scan;
- that 300 scans in a row cross the command sequence recycling. That many active
  scans exceed the protocol's budget, so this count runs with passive scans.

| Observation | Decision |
| --- | --- |
| All pass | Scan while connected works; reassociation is next |
| The connection ends during a scan | Read which notice ended it, then the firmware's absence events |
| Scan never completes, aborted at its deadline | Read the done events the worker saw |
| Data stalls past the scan | Stop. Read the ledger lines: the scan's pages may not be returning |
| Recycling refused under load | Scans are refused past 230 by design; check they resume when idle |

### Result: channel 40 control for 0420 and 0423, boot `4ac95e75` (2026-11-01)

Run by the device custodian on station 30 by full module reload: Buildbox at 799b873d,
package inventory `56673cc5…`, `mac` `79808dd7…`, CONSYS `c944a664…`, core `425b8add…`,
`Image.gz` `ee620135…`. This boot had a failed GNSS start before it, cleared
by a GNSS diagnostic module. Audio modules were loaded and idle.

| Check | Result |
| --- | --- |
| Join | `COMPLETED` on 5200 MHz WPA2-PSK/CCMP, a lease, gateway 3/3; grants `channel=40 sco=3` |
| Ping | 10/10, 3.5 ms average |
| Ten reconnects | 10/10, each 2/2: 5.71 s, then 1.34-1.46 s |
| Throughput | Receive 39 and 41, transmit 21 and 23 Mbit/s |
| Scan lines | All 11 show `probing=0 ssids=0`: 2 with `channels=36`, 9 with `channels=6` |
| Kernel log | No Oops, warning, call trace, branch 9 or "submission stopped"; not tainted |

The first decision row holds. The reconnect scans' `channels=6` confirms that
`wpa_supplicant` narrows later scans, which the channel 40 control could only infer.

Stage 3's test script prints no names: one passive baseline, two wildcard and two named
scans, so five scans plus one join and one reconnect, inside the budget of ten.

### Result: channel 6, boot `4ac95e75` (2026-11-01)

Run by the device custodian, on the 0423 modules, one attempt within the budget. Part B,
active scan, did not run.

| Check | Result |
| --- | --- |
| Scan, grant, join | One-channel passive scan, `join grant: channel=6 sco=0`, authentication and association status 0 |
| Handshake | Failed. EAPOL message 1 arrived four times about 1 s apart, then the access point deauthenticated with reason 15 (4-way handshake timeout) |
| Stop | `join stopped: status=-67` (`-ENOLINK`) 24 ms after that deauthentication; later scans refused until a full reload |
| Kernel log | No Oops, warning or call trace; not tainted. Temperatures unremarkable |
| Back on channel 40 | After a full reload: `COMPLETED`, a lease, gateway 5/5 |

The decision table's row "association passes, handshake or data fails" applies.

Analysis, from the log and source:
- 2.4 GHz scan, grant, authentication, association and receive all work. So do the
  firmware's band and record changes, as far as association.
- Before 0434, an unacknowledged EAPOL frame ended the lifetime at once with `-ENOLINK`.
  That came only after the deauthentication, so any message 2 the driver submitted was
  acknowledged. Either the driver never submitted one, or the access point heard it and
  rejected it. A message 2 with a wrong MIC gives exactly this pattern. The same key
  works on channels 40 and 161, but those are other access points.
- The log has no line for message 2 at all. [0433](../../patches/proposals/0433-wifi-mt6797-log-the-transmit-status-of-join-frames.patch)
  adds its status, attempts and rate.
- [0434](../../patches/proposals/0434-wifi-mt6797-survive-a-frame-the-air-lost.patch)
  stops a lost frame from ending the lifetime, the cause of the `-ENOLINK` here.

Next: one join on channel 11, the access point the owner chose on 2026-11-01, with
0433 and 0434 loaded, then active scan.

| Observation | Decision |
| --- | --- |
| Another 2.4 GHz access point joins | The band works; the channel 6 access point differs. Ask the owner about its settings |
| Message 2 logged with status 0, and the same failure | The firmware's frame or the access point's check. Compare the frame with channel 40's, by capture if possible |
| Message 2 logged unacknowledged | Radio or rate on 2.4 GHz after activation. Read the station and BSS records against the vendor's |
| No message 2 logged | The supplicant or the driver's EAPOL admission. Read the admission path |

### Separate finding: a lost deauthentication closes the lifetime

On channel 40 on the same boot, stopping `wpa_supplicant` after 163 s and 64246 transmitted
frames gave `deauth completion missing: pid=127`, then `join stopped: status=-110
... debt=2 branch=8`. Scans then failed with `-EOPNOTSUPP` until a full reload.
The missing completion has a retire path by design. Something later in the
cleanup returned `-ETIMEDOUT` in the same pass. Not understood and not fixed. Which
command failed and whether the firmware had stopped responding remain open. It has been
seen once. Recovery without a reload belongs to phase 4.

The driver's scan refusal after a closed lifetime reads as "unsupported" (`-95`). It
means the lifetime is closed.

### Result: channel 11 and active scan, boot `4ac95e75` (2026-11-01)

Run by the device custodian on station 30: Buildbox at cde254b1, package inventory
`2115826b…`, `mac` `4218fbd8…`, CONSYS `7a1bb9db…`, core `425b8add…`.

| Part | Result |
| --- | --- |
| Channel 40 control | Ping 10/10, reconnects 10/10 (5.76 s, then 1.41-1.49 s), receive 45 Mbit/s. Transmit 1.3 Mbit/s on a first run, 21 on a repeat: the first run used a new script, and the low figure is unexplained and not repeated. Join frames all status 0, one attempt |
| Channel 11, first join | `join grant: channel=11 sco=0`, `COMPLETED`, a lease, ping 3/3, -65 dBm. The first message 2 failed with status 3 after 3 attempts; a resend 0.86 s later went through. Ping 9/10 |
| Channel 11, first reconnect | Disconnect clean. Authentication acknowledged. Two association requests failed with status 3 after 3 attempts each. The third try ended the lifetime with `-EOPNOTSUPP` |
| Channel 11, the rest | Scans refused until a full reload. No transfer ran |
| Active scan | Not run: `iw` got `-EINVAL`, because `max_scan_ssids` was still 0 |
| Passive baseline | 5.16 s, 20 BSSes on both bands, 36 channels |

Status 3 is taken to mean the MPDU retry limit was reached, per the vendor's result
codes; its name was not checked against the header.

Analysis:
- **The 2.4 GHz band works.** Authentication, association and data all ran.
- **The driver allowed 3 transmit attempts; the vendor's limit is 30**
  ([`nic_tx.h`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic/nic_tx.h)).
  On a busy channel three attempts can fail within tens of milliseconds. That fits
  every lost frame here, and may fit channel 6 too, although channel 6's message 2
  frames were not seen. [0436](../../patches/proposals/0436-wifi-mt6797-retry-frames-as-the-vendor-does.patch)
  raises it, also for data at the fixed rate, so channel 40's throughput
  needs a fresh control. This is inference until tested.
- **mac80211 makes three association tries; the driver admitted two.** The third
  closed the lifetime. 0436 admits three.
- **`max_scan_ssids`.** 0423 did not raise it, so its active path has never run.
  [0437](../../patches/proposals/0437-wifi-mt6797-advertise-the-scan-SSIDs.patch)
  does. My earlier belief that mac80211 sets it was wrong.

Still open: a lifetime that does end this way needs a module reload.

Next, each within the protocol's budget, on channels the owner names:

| Observation | Decision |
| --- | --- |
| Channel 11 passes with one or two attempts per frame | Lost frames were the problem; go on to channel 1 and active scan |
| Frames still need most of 30 attempts | Check coexistence and the transmit power on 2.4 GHz |
| Channel 40's throughput falls with the higher limit | Keep the limit for management and EAPOL only |

### Result: channel 40 control for 0436 and 0437, boot `4ac95e75` (2026-11-01)

Run by the device custodian, `mac` `6ecb54a7…`. Channel 11 and active scan did not run.

Ping 10/10, reconnects 10/10 (5.71 s, then 1.24-1.33 s), receive 37.7 Mbit/s, every
join frame `status=0 count=1`, `max # scan SSIDs: 4`, not tainted. Transmit read 0.5, 0.6
and 9.5 Mbit/s. That hit the predeclared stop, under about 15 Mbit/s. The harness
and spacing are newer than station 24's and not yet separated from the driver: `mac`
`4218fbd8…`, with data at 3 attempts, read 1.3 and then 21.4 on a first use of it.

[0438](../../patches/proposals/0438-wifi-mt6797-keep-data-at-three-transmit-attempts.patch) takes the predeclared fallback: 30 attempts for
management and EAPOL, 3 for data. A same-harness run of `4218fbd8…` is requested as the
control for that.

### Result: transmit comparison, boot `4ac95e75` (2026-11-01)

Same tool and spacing on channel 40: a 10 s receive, then three 10 s transmits counted at
the laptop.

| `mac` | Data attempts | Receive | Transmit 1 | Transmit 2 | Transmit 3 |
| --- | --- | --- | --- | --- | --- |
| `6ecb54a7…` (0436) | 30 | 37.7 | 0.5 | 0.6 | 9.5 |
| `4218fbd8…` | 3 | 38.7 | 1.2 | 0.6 | 21.7 |

One sequence each, in Mbit/s. A slow first 20 s or so predates 0436. The earlier figures
of 21-23 Mbit/s came from 60 s runs or runs with no receive transfer first, so they don't
compare with these. Run 3 suggests 30 attempts for data costs throughput, without proving it.

Hypothesis, untested: after a receive transfer, the receive reorder state holds the
acknowledgements of the sending TCP connection for its 200 ms timeout.

Predeclared next test, `mac` with 0438, on channel 40, no new channel: 60 s transmits
counted every 10 s, with a gateway ping alongside, with and without a receive transfer
first.

| Observation | Decision |
| --- | --- |
| Slow only after a receive transfer, ping delayed by about 200 ms | Read the reorder state at the end of a receive transfer |
| Slow in both cases | Rate or TCP start, not the reorder; read rate and data status |
| Slow in neither | The earlier sequence's spacing or the tool; record it and go on |

### Result: the slow transmit test, boot `4ac95e75` (2026-11-01)

Run by the device custodian on channel 40, `mac` `ba28eb81…` (0438), with a gateway ping
at 1 s. Throughput per 10 s, in Mbit/s:

| Run | Before | Throughput | Ping min/avg/max, ms | `tx failed` |
| --- | --- | --- | --- | --- |
| 1. Transmit 60 s | Fresh reconnect, 30 s idle | 20.7 21.1 20.8 20.6 20.4 20.4 | 13.7/32.2/209.8 | 0 |
| 2. Transmit 60 s | 10 s receive at 19.4 | 3.1 3.2 3.2 3.1 2.6 2.3 | 245.8/360.9/468.3 | 0 |
| 3. Receive 60 s | 10 s receive at 22.0 | 21.2 21.1 21.9 21.6 22.8 20.1 | 198.0/308.5/408.4 | 0 |

No new ADDBA in runs 2 and 3. Few PN refusals.

- **Transmit itself is fine.** Run 1 holds 21 Mbit/s with data at 3 attempts, so
  0438's data limit is good.
- **The stall lasts past 60 s,** not the 20 s the shorter runs suggested.
- **Latency is high in runs 2 and 3,** a floor near 200 ms. That fits frames waiting on
  the reorder timeout, but doesn't prove it. Receive also ran at about half its fresh-join
  rate here. So the condition may belong to the receive path, not to transmit.

The two predeclared rows conflicted: "slow only after a receive" and "settled below
15 Mbit/s". Run 1 shows the second was not its intended case, so channel 11 and active
scan went ahead.

[0440](../../patches/proposals/0440-wifi-mt6797-log-the-receive-reorder-counters.patch) logs each TID's holes, expiries, duplicates and frames
behind the window. Next, once it is loaded: the same runs, each ended by a reconnect so the
counters print.

| Observation | Decision |
| --- | --- |
| Expiries near one per 200 ms in runs 2 and 3, few in run 1 | The reorder window has a recurring hole: find which frames leave it |
| Few expiries, with latency unchanged | Not the reorder; read the worker's polling and the receive batching |

### Result: channel 11 retest and active scan, boot `4ac95e75` (2026-11-01)

Run by the device custodian, `mac` `ba28eb81…`, full reload between parts, within the
owner's budget.

Channel 11, `join grant: channel=11 sco=0`, -63 dBm:

| Check | Result |
| --- | --- |
| First join | `COMPLETED` but no lease: message 4 failed all 30 attempts, and neither side recovered for about 90 s. A reconnect then worked |
| Ten reconnects | Nine after that: 8 answered ping, in 0.90-2.73 s, and the slower ones include authentication timeouts |
| Transmit 60 s, from idle | 3.2 0.9 2.2 1.3 2.3 1.9 Mbit/s; ping 52/60, 12.3 ms average |
| Receive 60 s | 32.1 37.8 40.1 40.1 35.0 33.9 Mbit/s |
| Lifetime | Stayed open throughout |

Of 60 join frames at 6 Mbit/s, most took one attempt. Six authentication frames and two
message 4 frames failed all 30 attempts, and some took 6 or 12. 30 attempts took at most
about 150 ms, and failures come in bursts lasting seconds. Channel 40 frames on the same
module took one attempt.

So 2.4 GHz works, and the higher retry limit keeps the lifetime alive, but transmit on
this channel is poor while receive is good. This fits something that blocks transmit in
bursts: interference, or coexistence or power on this radio. Which is unknown. Rate
control has not been tried here.

Active scan, wildcard: exit 0 in 3.91 s, `channels=36 probing=20 ssids=1`, 24 BSSes
against 20 for the passive scan. This is the first active scan on this driver. A second
scan-done event 24 ms later (`-EPROTO`) then closed the lifetime, so the two named scans
and the supplicant join did not run. [0441](../../patches/proposals/0441-wifi-mt6797-ignore-a-scan-done-event-nothing-waits-f.patch)
ignores that event.

### Teardown faults after heavy traffic

Three of four disconnects after heavy traffic on this boot closed the lifetime:

| When | Log |
| --- | --- |
| Channel 40, 163 s, 64246 frames | Deauthentication completion missing, then `-ETIMEDOUT`, branch 8 |
| Channel 40, 303 s, 242407 frames | `join guard failed: ret=-5`, `whisr=0x00000042`, 1 ms after the PM abort |
| Channel 11, 184 s, 52022 frames, 172 not done at the end | `-ETIMEDOUT`, branch 5 |

In the second, WHISR bit 6 is the abnormal interrupt; the vendor
([`nic.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic.c))
reads WASR and resets the chip on it. The causes of these faults are not understood.

[0443](../../patches/proposals/0443-wifi-mt6797-restart-the-firmware-after-a-fault.patch)
does what the reload did, from inside the driver, without explaining them. It covers every
fault that reaches the join's stop path, or any scan on a closed lifetime.
[0442](../../patches/proposals/0442-wifi-mt6797-create-wlan0-by-itself.patch) makes `wlan0`
appear by itself, which the restart and any plain system need.

Next, compile-checked only, predeclared:

| Test | Hypothesis |
| --- | --- |
| Stall, with reorder counters | As in "the slow transmit test" |
| Heavy traffic, then stop the supplicant, a few times | Faults may recur. Each ends in `WLAN restart: status=0` and `wlan0` back within about 5 s, with `wifi-up.sh` joining again without a manual reload |
| Active scan, two wildcard, two named, then a supplicant join with `PASSIVE_SCAN=0` | Named scans find the network; no lifetime closure |

| Observation | Decision |
| --- | --- |
| Restart works | Phase 4's recovery is started; count 20 forced faults later |
| Restart fails: CONSYS will not stop or start cleanly, or the attach fails | Stop, read the log; reboot if needed. Keep the reload as the manual path |

### Result: the stall with reorder counters, boot `4ac95e75` (2026-11-01)

Run by the device custodian on channel 40, `mac` `72e50e13…`, -61 dBm.

| Run | Before | Throughput per 10 s, Mbit/s | Ping avg, ms | Reorder, TID 0 |
| --- | --- | --- | --- | --- |
| 1. Transmit 60 s | Reconnect, 30 s idle | 22.0 22.3 22.2 22.4 22.1 21.9 | 29.5 | No holes, expiries or frames behind |
| 2. Transmit 60 s | 10 s receive at 41.9 | 0.6 0.5 2.3 22.1 22.0 21.8 | 54.7 | 14 behind |
| 3. Receive 60 s | 10 s receive at 37.4 | 46.7 50.6 49.8 45.6 43.5 42.2 | 86.2 | 568 behind |
| Transmit 60 s | 70 s receive, then 30 s idle | 21.5 21.6 21.6 21.7 21.9 21.7 | 29.3 | Not read |

The reorder hypothesis is rejected: no holes or expiries in any run. The stall itself is
real but varies: about 25 s here, over 60 s in the earlier run, with receive rates of 42 and
19 Mbit/s before them. A 30 s idle cured it on the one sample. Whether the laptop's own TCP,
the air or this driver causes it is not separated.

Run 3's disconnect closed the lifetime with `status=-5`, branch 2, as in the
table above: the fourth such closure after heavy traffic.

### Result: restart and active scan, boot `4ac95e75` (2026-11-01)

Run by the device custodian: Buildbox at ed4992be, inventory `8a88b356…`, `mac` `949602c4…`,
CONSYS `28b5435c…`, core `425b8add…`. Not tainted throughout, temperatures unremarkable.

**Restart.** Five cycles of 60 s transmit, 60 s receive and stopping the supplicant. Four
faulted: `status=-5` at branch 2 twice, `-110` at branch 5, `-5` at branch 8. Each ended in
`WLAN restart: status=0` about 0.2 s after it began, with negotiation result 0 at about
0.3 s and `wlan0` back; `wifi-up.sh` then joined, ping 3/3, with no reload. The fifth cycle had
no fault. The predeclared first row holds: recovery works for these faults.

**Active scan.** One passive scan and two wildcard and two named scans, all exit 0 in
about 4 s with `channels=36 probing=20`, no closure. The second done event did not recur
as a fault. Against the passive scan's 21 BSSes they found 20-22; no gain is visible, and
no hidden network exists here to test. `wpa_supplicant` with active scan joined by name
on channel 161, ping 3/3; one reconnect in 1.08 s. `wifi-up.sh` now scans actively by default.

**Budget overrun.** That join and reconnect went past channel 161's budget, which was spent.
The cause is my request: its frequency list included 5805 MHz. All frames took one attempt.
The owner has been told.

**Throughput figures on channel 40.** The laptop is on Wi-Fi on the same channel, so every
transfer there crosses that channel twice. These figures describe that shared path, not the
device's link. Channels 161 and 11 share less.

**Stall.** Device to gateway, 1400-byte ping at 20 ms, no laptop in the path: straight after
a 10 s receive 835/1000 with 122 ms average; after a 30 s idle 1000/1000 with 11.7 ms. So
the stall is not the laptop's hop, or at least not only that. Open question: whether receive
actually stops when the test kills `wget`. Queued data may still arrive.

### Teardown faults: predeclared test of 0444

On the two evidence logs read, a `status=-5` stop came 1-16 ms after `mask-control
submission: enable=0`, with WHISR's abnormal bit set. The log's order is mask off, PM abort,
fault, all before the deauthentication goes out, so the access point is still sending.
[0444](../../patches/proposals/0444-wifi-mt6797-leave-the-monitor-mask-until-the-next-sc.patch) leaves the mask until the next scan. This is a correlation
in a few samples, not an explanation.

Hypothesis: 5 of the same cycles (60 s transmit, 60 s receive, stop) give few or no
`status=-5`; later scans and joins still work with the mask turned off before the scan.

| Observation | Decision |
| --- | --- |
| `-5` gone, scans and reconnects unchanged | The abnormal fault was the mask; look at the `-110` next |
| `-5` remains, with no mask line before it | The mask was incidental; look at the receive batch next |
| Scans find nothing or reconnects fail | The mask matters to the next lifetime's setup; revert 0444 |

### Correction: there was no stall (2026-11-01)

The device custodian found the cause. `timeout` killed the test's shell loop and left its
`wget` running, so a "10 s receive" went on until the 200 MB file finished. `rx_bytes`
kept climbing at 50-60 Mbit/s for 25 s after the "end" of the receive. Killing `wget`
outright stopped traffic within a second. A 30 MB fetch run to completion, followed at once
by the 1400-byte ping, gave 1000/1000 at 11.7 ms average, the same as idle.

Invalid, because a download was running during them:
- every "transmit after receive" figure above, in the transmit comparison, the slow
  transmit test and the stall with counters;
- the ping with 16% loss;
- the reasoning that followed: the reorder hypothesis had no real basis, and the
  restart cycles' first transmit windows may overlap a download.

[0438](../../patches/proposals/0438-wifi-mt6797-keep-data-at-three-transmit-attempts.patch)
rested on those figures, so its commit message overstates the case. Whether data should
keep 3 attempts or take 30 is open and needs a clean comparison.

Still valid: transmit from idle at 21-22 Mbit/s, channel 11's poor transmit and its frame
counts, the restart results, the active scans.

The faults at disconnect probably happened with a download running, which fits light
use not faulting. So they are faults under traffic, not after it. That gives a repeatable
trigger: stop the supplicant during a download.
