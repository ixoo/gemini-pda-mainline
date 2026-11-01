# Experiment: one clean MT6797 Wi-Fi driver (daily-use plan, phase 1)

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-31-mt6797-wifi-clean-driver` |
| Status | `running`: checkpoint 0389 (configuration folded, test surface removed) passed on the device by module swap; the structural steps follow |
| Subsystem | Wi-Fi: `mt6797-consys`, `mt6797-wlan-core`, `mac` |
| Device variant | named Gemini PDA (MT6797X), boot2 station |
| Date(s) | 2026-10-31 |
| Investigator(s) | project custodian |
| Tracking issue | none |

## Question or hypothesis

Phase 1 of the [daily-use plan](../../docs/WIFI_DAILY_USE_PLAN.md#1-one-clean-driver-no-new-behaviour)
turns the station's Wi-Fi patches into one driver a reviewer can read,
without changing behaviour. The station series carries about 290 patches
that touch CONSYS, WMT and WLAN. In the source they build, 48 Kconfig
switches select the working configuration, and test schedules, records and
dead branches sit beside it.

Hypothesis for checkpoint 0389: folding the switches to the station's
values and removing the measurement surface keeps the station's Wi-Fi
behaviour. That covers join, DHCP, reconnects and throughput.

## Provenance and environment

- **Source.** The station series (`patches/series-a53-station`) applied
  with `git apply --unidiff-zero` to Linux 7.1.3, as the build does. The
  Wi-Fi files are about 24,700 lines across the three modules.
- **Inventory.** A read-only classification of every switch, runtime
  surface, log and pin. It was kept private to the session; its
  conclusions are below.
- **Owner decisions.** Fixed HT MCS5 stays the default and minstrel becomes
  an option. The measurement code becomes one optional patch outside the
  clean series. Compile-only iteration may run in the dev VM; booted
  images still come from Buildbox.

## Safety assessment

Same radio use as the station boots: the owner's access point on channel
40, WPA2-PSK. There is no new channel, power or firmware command, and no
change to the CONSYS power, reset or EMI path. A boot that fails to join
returns to the previous station image through boot2.

## Associated code

[0389](../../patches/proposals/0389-wifi-mt6797-fold-the-station-configuration-and-remov.patch),
the last patch of the station series. It is a checkpoint that the clean
series replaces later.

What the inventory showed, and how 0389 handles it:
- **The working configuration is not one configuration.** A built-in test
  schedule set each `mac` load's associations. Associations 1 and 5 onward
  used the build settings: fixed `0x85`, HT40 and receive A-MPDU.
  Associations 2 to 4 used minstrel, minstrel at 20 MHz, and a fixed rate
  at 20 MHz. 0389 gives every association the build settings, so the
  comparison is with associations 1 and 5 onward.
- **Not all "diagnostic" code is diagnostic.** The `NATIVE_DELIVERY_DIAG`
  state machine writes the firmware mask at `0x800c0068` that admits
  protected receive. It stays.
- **Some defaults are not the working values.** Three Kconfig defaults
  differ from the station's: transmit depth 12 (default 4), rate `0x85`
  (default `0x4b`) and a status report on 1 frame in 64 (default 0). They
  are folded at the station values.
- **Startup reads log text.** `wifi-cycles.sh` matches kernel messages to
  find firmware readiness. Every matching message is unchanged.
- **New option.** `rate_control`, a `mac` module parameter, read once per
  association. Off is the fixed rate, on is minstrel.
- **Size.** 31 files change: 246 lines added and 6,382 removed. W=1 builds
  each step with no warnings.

## Procedure

Station 24: the station 23 image with 0389, through the usual boot2 path.
(Run instead as a module swap on station 23 at the owner's prompt; see
Observations.) Then, over USB SSH:
1. `wifi-up.sh`: firmware start, `mac` load, join, DHCP.
2. Gateway ping, 10 at 1 s.
3. Ten reconnects (`wpa_cli disconnect`, then `reconnect`). Each must
   reach `COMPLETED` and answer a gateway ping.
4. Throughput, if the station's tools allow, each way against the
   previous station's figures on the same access point.
5. `rate_control=1`, then one reconnect: the join completes and the
   transmit rate words change.
6. Kernel log: no Oops, warning or call trace, and no refusal beyond the
   known ones.

| Observation | Decision |
| --- | --- |
| Steps 1-3 and 6 pass, and throughput is within the earlier band | 0389 holds. Continue with the structural steps (file layout, Kconfig, DT binding, series) |
| The join or the data phase fails | Bisect the five cleanup steps (snapshot, test configuration, dead branches, records, CONSYS modes) in the dev VM by diff. Then rebuild |
| Reconnects fail after a few | Compare with station 9's 26 reconnects. The test schedule's associations 2-4 were the variable |

## Observations

**Module swap on station 23, boot `f9097bd5` (2026-10-31).** The owner
asked why a reboot was needed when Wi-Fi is modular. None was needed.
- **The package.** Built at e977755c (inventory `95b7a67f`). Its
  `Image.gz` (`b3d5757e…`) is byte-identical to the running station 23
  kernel's, and the vermagic matches.
- **The new modules** were copied over USB SSH into the RAM root's module
  directory: `mac` `21bd162f…`, core `5ee46803…`, CONSYS `fb4ea795…`.
  Station 23's own modules were kept in `/run`.

| Step | Result |
| --- | --- |
| 1. `wifi-up.sh` | Common init `completed=285/285`; firmware ready; `mac` insmod 0; `COMPLETED` on 5200 MHz, WPA2-PSK/CCMP; a lease; gateway 3/3 |
| 2. Gateway ping, 10 at 1 s | 10/10, 0 % loss, average 13.8 ms |
| 3. Ten reconnects | 10/10 `COMPLETED` in 0.88-1.12 s, each answering a 2/2 gateway ping |
| 4. Throughput, 10 s each, interface counters | Device receive (HTTP download from the laptop) 41 and 38 Mbit/s. Device transmit (`nc` to the laptop) 22 and 23 Mbit/s |
| 4b. Control: station 23's modules, same harness, same air, minutes later | Receive 40 and 45, transmit 18 and 22 Mbit/s |
| 5. `rate_control=1`, then a reconnect | `COMPLETED`, gateway 3/3. The transmit bitrate went from MCS1 to MCS7 at 40 MHz, and transmit was 23 Mbit/s. Reset to 0 afterwards |
| 6. Kernel log | No Oops, warning or call trace, and the kernel is not tainted. The only refusals are the known EAPOL-trace and early data-layout lines at the join |

The swap used the R2 reload: `rmmod` of `mac`, then CONSYS (CONN powered
off), then the core, followed by a normal start. One harness detail: after
a manual unload, `wifi-cycles.sh` keeps its `/run/station/firmware-started`
marker. It then skips the start, and `mac` refuses with `-ENODEV`. Removing
the marker fixed that. The script's own `RESTARTS` path clears it.

## Analysis

- **Behaviour holds.** 0389 joins, renews and reconnects like the station
  modules, with reconnects in about 1 s.
- **Throughput.** It is within the control's band in both directions under
  the same harness. This `nc` and `wget` harness reads lower for transmit
  than the [boot AV](../2026-10-13-mt6797-wifi-native-delivery-probe/THROUGHPUT_SERIES_RESULT.md#rate-control-against-the-fixed-rate-2026-10-27-boot-av)
  figures (29.7-30.9 Mbit/s). The same-session control shows that the gap
  comes from the harness and the air, not from 0389.
- **The new parameter works.** `rate_control` hands transmit to minstrel.
- **Every association now uses the build configuration.** Before 0389,
  associations 2-4 used the test schedule's settings. That made no
  difference to the joins here.

## Conclusion

Checkpoint 0389 passes the predeclared first row: folding the
configuration and removing the measurement surface kept the station's
Wi-Fi behaviour. That covers join, DHCP, ten reconnects, throughput within
the same-session control, and the minstrel option. Only 0389's module
files ran, under station 23's kernel, which the package matches byte for
byte.

## Follow-up

The rest of phase 1:
- the file layout, splitting `mac.c` and merging the small headers;
- three Kconfig tristates;
- a CONSYS binding without the `one-shot-*` staging;
- the clean series replacing the station's Wi-Fi patches;
- the debug patch.
