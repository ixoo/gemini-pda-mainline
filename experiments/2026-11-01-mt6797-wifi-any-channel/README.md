# Experiment: Wi-Fi on any network and channel (daily-use plan, phase 3)

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-mt6797-wifi-any-channel` |
| Status | `running`: 0410's first device test failed for two identified reasons; fixes built, repeat requested from the custodian |
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
