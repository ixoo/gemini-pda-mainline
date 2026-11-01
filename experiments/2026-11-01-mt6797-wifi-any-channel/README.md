# Experiment: Wi-Fi on any network and channel (daily-use plan, phase 3)

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-mt6797-wifi-any-channel` |
| Status | `running`: multi-channel passive scan passes (0410, 0412, 0413). The owner approved the radio protocol on 2026-11-01. 0414 joins channel 40 and channel 161 with data both ways. A secondary channel above and 2.4 GHz are not tested |
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
