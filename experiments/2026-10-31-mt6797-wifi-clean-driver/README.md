# Experiment: one clean MT6797 Wi-Fi driver (daily-use plan, phase 1)

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-31-mt6797-wifi-clean-driver` |
| Status | `running`: the clean series 0390-0394 passed on station 24; the station 9 hold and reconnect counts remain |
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
the marker fixed that. The script's own `RESTARTS` path clears it, and
the script now also clears it whenever it loads CONSYS itself.

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

## Clean series 0390-0394

The structural steps, built on 0389 and compile-checked with W=1 in the
dev VM after each step. The station series drops the 300 patches that
touch the Wi-Fi stack, 0389 included, and ends with five patches:

| Patch | Content |
| --- | --- |
| [0390](../../patches/proposals/0390-dt-bindings-power-mediatek-mt6797-scpsys-describe-th.patch) | The SCPSYS binding's CONN power-controller child, unchanged from the station |
| [0391](../../patches/proposals/0391-dt-bindings-soc-mediatek-add-the-MT6797-CONSYS-owner.patch) | The CONSYS binding without the `one-shot-*` and `deferred-*` properties |
| [0392](../../patches/proposals/0392-wifi-mediatek-add-the-MT6797-WLAN-driver.patch) | The WLAN driver: `mt6797-wlan-core` and `mac` |
| [0393](../../patches/proposals/0393-soc-mediatek-add-the-MT6797-CONSYS-owner.patch) | The CONSYS owner, with the start chain fixed |
| [0394](../../patches/proposals/0394-arm64-dts-mediatek-gemini-pda-describe-the-connectiv.patch) | The board's CONN domain, regulators and CONSYS node |

What changed after 0389:
- **Kconfig.** Three options remain: `MTK_MT6797_CONSYS`,
  `MT6797_HIF_CORE` and `MT6797_MAC80211`.
- **CONSYS.** The driver no longer reads the eleven start-mode
  properties; it always runs the chain the station selected. The
  station's device tree differs from the old one only by those
  properties, and it passes the new schema.
- **Dead code.** The image-binding and EMI helper layers had no caller
  and are gone, with a few unused functions. The host-test shims are
  gone. The transmit data depth is folded at 12. The channel token and
  station sequence no longer refuse at 255: every join assigns them
  afresh, so the refusal could not trigger.
- **Layout.** `mt6797-wlan-core` is four files (`hif.c`, `firmware.c`,
  `ordinary-transfer.c`, `record-prepare.c`) with two wire-format
  headers, down from thirteen objects and twenty headers. `mac` is
  `main.c`, `join.c` and `data.c` with `mac-priv.h`; a comparison of all
  224 definitions shows the move changed none of them. CONSYS has one
  WMT header instead of fourteen.
- **Style.** checkpatch reports no errors or warnings; `--strict` leaves
  nine notes, mostly long lines in the join worker.
- **Series.** All 565 patches of the new station series apply to Linux
  7.1.3. The resulting Wi-Fi files match the edited source byte for byte.

Not done: the separate debug patch. Nothing needs it yet; the station
series keeps the measurement code's history.

Hypothesis: the clean modules behave like 0389 on station 23. Test by
module swap if the package's `Image.gz` matches station 23's, with
0389's procedure (steps 1-6) and 0389's figures as the control.

| Observation | Decision |
| --- | --- |
| Steps 1-3 and 6 pass, throughput within 0389's band | Phase 1's code is done; the station 9 hold and reconnect counts come next on a booted image |
| Join or data fails | Bisect the post-0389 steps in the dev VM by diff, then rebuild |
| `Image.gz` differs from station 23's | Boot a new station image instead of swapping modules |

### Result: station 24, boot `46c10546` (2026-11-01)

The keyboard cleanup (c0758ae6) changes built-in code, so `Image.gz`
(`0d4d6d74…`) differs from station 23's and the test ran on a booted
image. Built on Buildbox at 6fea0382 (565 patches, package inventory
`98dfb5e8…`), composed as boot2 `f7761f02…`, written by
`flash-boot2` with a matching readback. Modules: `mac` `6a331fc3…`,
CONSYS `832cfcdb…`, core `e4072f87…`. The CONSYS node carries none of the
`one-shot-*` properties.

| Step | Result |
| --- | --- |
| 1. `wifi-up.sh` | Common init `completed=285/285`; firmware ready; `mac` insmod 0; `COMPLETED` on 5200 MHz, WPA2-PSK/CCMP; a lease; gateway 3/3 |
| 2. Gateway ping, 10 at 1 s | 10/10, 0 % loss, average 5.5 ms |
| 3. Ten reconnects | 10/10 `COMPLETED` in 0.98-1.15 s, each answering a 2/2 gateway ping |
| 4. Throughput, 10 s each | Receive 38 and 37 Mbit/s. Transmit 14, 19, 20, 22 and 20 Mbit/s; signal -67 dBm |
| 5. `rate_control=1`, then a reconnect | `COMPLETED`, gateway 3/3; the transmit rate rose to MCS7 at 40 MHz; one transmit run gave 13 Mbit/s. Reset to 0 |
| 6. Kernel log | No Oops, warning or call trace; not tainted |

The first decision row holds. Receive matches 0389 (38-41) and the old
station modules (40-45). Transmit after the first run (20-22) lies in
the old modules' band (18-22), slightly below 0389's 22-23. The 14 Mbit/s
first run and the single minstrel run are not separated from the air by
these few samples. The start chain ran from the device tree without
any staging property.

## Follow-up

The rest of phase 1:
- the station 9 repeat: 26 reconnects and a 2.5 h hold;
- the debug patch, if a measurement needs it.
