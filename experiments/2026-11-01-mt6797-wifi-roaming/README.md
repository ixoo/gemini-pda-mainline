# Experiment: roaming between access points of one network

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-mt6797-wifi-roaming` |
| Status | `planned`: patches 0456-0458 compile; nothing has run on the device |
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

**Stage A** scans passively while connected, on the channel in use, and sends no new frame type.
**Stages B to D** move the link between the owner's access points, which the
[radio protocol](../2026-11-01-mt6797-wifi-any-channel/README.md#radio-protocol-approved-by-the-owner-2026-11-01)
budgets at one join and ten reconnects per channel. They need a new budget from the owner first:
proposed, only access points of the owner's network on non-DFS 5 GHz channels, at most 40 roams a
session, US country, its other limits and stop conditions unchanged. Not approved yet.

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

USB connected. Hypothesis: `wpa_cli roam` moves the link with one `join without a scan` line per roam,
a reassociation response, and no firmware restart. `roams 10`, then the same with a transfer running.

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

None yet.
