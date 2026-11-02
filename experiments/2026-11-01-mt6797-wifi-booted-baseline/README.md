# Experiment: the Wi-Fi driver's baseline on a booted image

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-mt6797-wifi-booted-baseline` |
| Status | `planned`: protocol written, device run requested from the custodian |
| Subsystem | Wi-Fi: `mac`, CONSYS |
| Device variant | named Gemini PDA (MT6797X), boot2 station |
| Date(s) | 2026-11-01 |
| Investigator(s) | project custodian |
| Tracking issue | none |

## Question or hypothesis

Does the current driver repeat the
[station 9 counts](../2026-10-31-mt6797-wifi-clean-driver/README.md), 26 reconnects and a 2.5 h
hold, and the clean channel 40 throughput, on a booted station image?

The owner reopened Wi-Fi for this test on 2026-11-01 ("Yes, start baseline").

**Hypothesis.** All three hold, with no manual action. It is falsified by a disconnect during the
hold, a reconnect that does not complete by itself, or throughput below the band in the decision
table.

The unique observation is the hold: the clean driver has never been held this long, and it drops
EAPOL after the 4-way handshake, so a rekey by the access point during the hold would show here.

## What retained boots already show

The [any-channel record](../2026-11-01-mt6797-wifi-any-channel/README.md#where-this-stopped) says
the later patches had only run by module swap. That is no longer true. Station images 31 to 35
carry `mac` `773e1694…` in the RAM root and load it at boot. Read from the retained kernel logs:

| Boot | Station | Log length (s) | Associations | Local disconnects | Join faults |
| --- | --- | --- | --- | --- | --- |
| `24465562` | 31 | 4370 | 3 | 2 | 0 |
| `7dd24578` | 32 | 919 | 1 | 0 | 1 |
| `a4984df3` | 33 | 1536 | 1 | 0 | 0 |
| `e1706072` | 34 | 638 | 1 | 0 | 0 |
| `c09fb418` | 35 | 3827 | 1 | 0 | 1 |

These boots ran for other tests, so they show a working join and not a measured hold. Their logs
do not show whether the link carried traffic throughout.

**New finding, first-join fault.** In 2 of these 5 boots the first join after boot failed: mac80211
reports `authenticated`, then about 0.7 s later `join stopped: status=-110 ... branch=1`, before
association. The restart from 0443 recovered it in about 6 s on station 35, with no manual action.
The cause is not known. It may not recur in this test, which stays on one boot, so a later boot
count has to measure it.

## Safety assessment

No new code and no new image. The owner's access point on channel 40 only, where the station has
always transmitted; the
[radio protocol's budgets](../2026-11-01-mt6797-wifi-any-channel/README.md#radio-protocol-approved-by-the-owner-2026-11-01)
cover other channels, so a link on any other channel stops the test. No module reload, no flash. The check for NetworkManager only lists files on the mounted partition.

## Procedure

Run by the custodian on a station whose `mac` is `773e1694…` or built from the same Wi-Fi patches
(none has changed since `b36b2f7f`), with [`wifi-baseline.sh`](wifi-baseline.sh). Record the boot
ID and the three Wi-Fi module hashes. No CONSYS reload or GNSS test may run during steps 2 to 5;
audio may.

1. Check `iw dev wlan0 link` reports 5200 MHz, and `busybox --list` has `killall`, `pidof`, `nc`
   and `wget`.
2. `tput`, against the laptop on Wi-Fi on the same channel, as for the clean figures.
3. `reconnects`: 26 `wpa_cli` disconnect and reconnect pairs, each with a 2/2 gateway ping.
4. `hold`: 9000 s idle, one gateway ping and a counters line every 60 s.
5. `tput` again.
6. List `/mnt/data/usr/sbin/NetworkManager` and `/mnt/data/usr/bin/nmcli`, to plan the `nmcli` test.
7. Keep the kernel log from the boot's start.

Steps 2-3 and steps 4-5 may run in separate slots on one boot. Keep private: network name, peer
address and the logs themselves, which carry them.

## Decisions

| Observation | Next |
| --- | --- |
| No disconnect, 26/26 reconnects, transmit about 22 and receive 40-55 Mbit/s | The counts hold; go to the `nmcli` test, then channel 11's transmit |
| Disconnect during the hold | Read the reason and the time in the log; a regular interval points at a rekey, and the rekey work comes first |
| Reconnect fails, restart recovers it | Not a pass; record the branch, and compare with the first-join fault |
| Reconnect needs manual action | Stop, keep the log, read the failing branch before any repeat |
| Throughput below the band twice, signal unchanged | Compare with the last clean figures before anything else |
| NetworkManager present or absent on the partition | Decides how the `nmcli` test gets its userspace; no write is admitted here |

## Observations

None yet.
