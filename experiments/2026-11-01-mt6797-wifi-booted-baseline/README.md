# Experiment: the Wi-Fi driver's baseline on a booted image

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-mt6797-wifi-booted-baseline` |
| Status | `planned`: protocol written and requested; the owner said "Not now" to running it |
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
| `5895e1f1` | 36 | 626 | not counted | not counted | 0 |
| `6b3acef8` | 36 | not counted | not counted | not counted | 1 |

These boots ran for other tests, so they show a working join and not a measured hold. Their logs
do not show whether the link carried traffic throughout.

The last two rows are the custodian's reports on one image (`mac` `773e1694…`, boot2 `d1a882db`): a
clean first join with no restart through 626 s, then a fault on the next boot.

**New finding, first-join fault.** In 3 of these 7 boots the first join after boot failed: mac80211
reports `authenticated`, then about 0.74 s later `join stopped: status=-110 first=0 submitted=0x800
debt=0 cleanup=0 branch=1`, before association.

Read from the retained logs, every faulted boot lacks the `join TX status: pid=1` line, and all four
clean boots have it about 30 µs before the authentication response:

- The access point answered, so the frame went out, and `debt=0` shows its pages came back.
- The 0.74 s fits the 750 ms wait for that status, from the frame's submission.

So the status for the first authentication frame did not reach the join path. Either the firmware did not send
it or the driver discarded it: the worker skips an event with another PID without logging it. This
log cannot tell which. The same image both joined and faulted, so the image does not decide it.

Recovery is not always hands-free. The firmware restart returned `status=0` each time, and station
35 then associated within about 6 s. On `6b3acef8` the supplicant reached `COMPLETED` but there was no
lease after 60 s, and rerunning `wifi-up.sh` leased at once. The restart recreates `wlan0`, so `udhcpc`
may have stayed on the old interface; that is not checked.

[0460](../../patches/proposals/0460-wifi-mt6797-take-a-management-frame-s-answer-as-its-.patch) takes
the answer as the frame's status and logs the status events the worker skipped; it has not run. A boot count has
to measure it, since this test stays on one boot.

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
