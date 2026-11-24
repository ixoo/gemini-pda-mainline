# Wi-Fi for daily use, for anyone: plan

Status: plan, updated 2026-11-01.
- Phase 1 (one clean driver) passed on station 24
  ([record](../experiments/2026-10-31-mt6797-wifi-clean-driver/README.md));
  its 2.5 h hold was not repeated.
- Phase 2's code passed on station 28
  ([record](../experiments/2026-11-01-mt6797-wifi-self-start/README.md)): the
  driver starts by itself and follows the US country. Its `nmcli` exit test
  needs phase 3.
- Phase 3 is partly done ([record](../experiments/2026-11-01-mt6797-wifi-any-channel/README.md)):
  scan and 5 GHz joins work; 2.4 GHz does not yet carry usable transmit, and security modes are
  not started. Phase 4 has its recovery restart and an untested scan while connected. The
  owner parked this testing on 2026-11-01.
- The owner reopened Wi-Fi on 2026-11-01 for a
  [baseline on a booted image](../experiments/2026-11-01-mt6797-wifi-booted-baseline/README.md):
  planned, not yet run.
- [Roaming](../experiments/2026-11-01-mt6797-wifi-roaming/README.md) on request works on one boot:
  21 clean at the driver between channels 40 and 161. Under a download one TCP connection stalled in 12
  roams, not explained. The owner closed this as a success for now after three walks. Weak links now carry
  data, down to MCS0 (0471), with gaps up to about 27 s and little actual roaming on the third walk. One access
  point refuses the handshake, channel 149 is not settled, and 0473 has run on a strong link only. The fixes are
  in boot2, booted once with a working link, and that image pins one access point with no `bgscan`, so it won't roam by itself.
- iwd installs the group key before the pairwise key, which the driver refused, ending each join in a
  firmware restart (custodian, boot `0993c976`). 0637 holds such a group key until the pairwise key is in.
  On that boot, as the custodian reports, with `mac` 5c5b7083 from `5e4cffbc` swapped in: iwd 3.12 joined
  5200 (held group key, then pairwise, then group), got a lease and 5 of 5 gateway pings, with no restart.
  `wifi-up.sh` with wpa_supplicant then joined in its usual order, with no hold, a lease and 3 of 3. One join
  each. Two `cipher-mismatch` refusals after the iwd join didn't affect the ping. iwd renames the interface
  (`wlan3` here), and `wifi-up.sh` needed `DOWN=1` and a reload after iwd had used the phy.
- A join that starts late in the 10 s after a scan was refused at authentication, which needs 850 ms left,
  and the lifetime ended in a firmware restart (`-95`, branch 1). iwd hit it on the Arch card's first join,
  9.2 s after its scan (custodian, R5). 0638 gives each join its own 10 s. Compiled only.
- iwd stayed in "connecting" with nothing sent (card-18, custodian): it had asked for a scan inside the
  10 s join window of the previous one, which the driver refused as busy, and iwd waits for another scan to
  finish before retrying, which never happened. 0669 retires that idle window at once for the new scan.
  On the first boot of station-work-92 (D1, from `980309cf`, with 0669 and 0670) and card-23, the owner joined
  with iwd: "wifi works!!!" (relayed by the custodian). One join on one boot, without logs yet, and the stall
  was never reproducible on demand, so this fits 0669 without proving it. A second boot, `d4a5ac06`, logged the
  join: no `scan busy` in the whole boot, and iwd's connect scan was admitted and joined. Whether it fell in an
  idle window, which is what 0669 changes, is not clear from the lines.
- On an idle connected link the join worker ran about 4,100 times a second, near a fifth of a CPU (card-31,
  custodian's trace): work stayed pending without progress, and the pump polled at once 32 times, waited one
  tick and started over. 0709 backs it off to the idle interval after 200 such passes and logs the pending
  state once. On card-32, boot `a71d4762`, as the custodian reports: at most 74 workqueue items a second
  in all, load 0.01, and one `pump stalled: queued=1` with nothing else pending. That one frame is the reserved
  deauthentication, held in the queue for the whole data phase; 0714 leaves it out of the pending test.
  On station-work-103, boot `b8fb3cbf`, as the custodian reports: the join worker ran 45 times a second on an
  idle link, the idle interval, with no `pump stalled` line. A disconnect, and so the held frame's release,
  was not exercised.
- Receive is polled, with no interrupt in this driver, so the 20 ms idle interval was the largest wakeup source
  on an idle station: about 52 a second (card-32 census). 0760 polls every 100 ms after 1 s with nothing either
  way, nothing pending and no frame held for reordering; any frame brings back 20 ms. The first frame after a
  quiet spell can wait up to 100 ms longer. An interrupt-driven receive would remove the polling, but is not
  started. On card-32 (boot `e7e3b009`, custodian) it changed nothing, 54 a second: about 6 broadcast or
  multicast frames a second kept the link from counting as quiet. 0767 counts only frames under the pairwise
  key and the station's own. On the same boot with 0767 swapped in, idle with the screen blanked and nothing
  streaming over SSH: 10.6 join work runs a second over 120 s (was 54), timer interrupts 47.6 a second (was
  about 113), with about 2.3 broadcast or multicast frames a second still arriving. SSH stayed usable. One run.
- The Wi-Fi stack held the AP-DMA clock on whenever Wi-Fi was up, which blocks SODI and deep idle (cpuidle,
  image 124): the HIF from attach to free, and the WMT setup from its first check to CONSYS unload. 0782 enables
  it only around each HIF DMA transfer, and 0783 only for the WMT check. On station-work-125, boot `0da78fe9`,
  as the custodian reports: enable count 0 at idle while joined and after a download, the gate closed in 199 of
  200 samples, and AP_DMA gone from the SODI and deep idle blockers. Three 64 MiB downloads ran at about 39.5
  Mbit/s against about 40 before, with no new errors. CONSYS and Bluetooth started; FM was not checked.
- Receive was only polled, so a frame arriving during SODI waited for the next poll (cpuidle D4: ping round
  trips up to 2 s), and an idle link still woke about ten times a second. At the owner's request ("interrupt
  driven wifi"), 0807 serves receive from the WLAN interrupt that 0808 adds to the device tree (GIC SPI 283,
  active low, as on the vendor kernel): WHIER gets the vendor's default sources, WHLPCR's host interrupt is
  enabled once a link is up, and a quiet link is polled once a second. A line that keeps waking the worker
  with nothing to read is given up. On image 136 (custodian) the interrupt never fired: the GIC had SPI 283
  enabled, level and inverted for active low, but never pending, and 0809's read-back showed WHLPCR 0x101 and
  WHIER 0, so the WHIER write did not take. The vendor's AHB bus driver also sets CCCR IENx (function 0,
  register 4) when it claims the interrupt; 0810 does too. On the device it read back 0 (`ienx=0x00`), with
  WHIER still 0. The same CMD52 path does take at CONSYS probe, where IOEx reads back set, and the vendor
  writes IENx before the firmware starts, so 0811 sets it there. On boot `2d4dcc57` with 0811's CONSYS and
  0810's `mac` swapped in, as the custodian reports: probe read IENx back as 0x03, and the WLAN interrupt fired
  and served receive. A 25-ping flood took 24.5 to 33.9 ms (was 33 to 65 ms polled). A 60 s download ran at
  33.8 Mbit/s with about 4,290 interrupts a second and no storm. In the cpuidle D4c window C, all 60 SODI periods
  ended early on the WLAN line and laptop pings took 3.4 to 266.7 ms (was up to 2.6 s). The arming read-back
  still shows IENx and WHIER as 0 after the firmware starts, so whether the later writes do anything is not
  known; the probe-time IENx is what made the difference. At idle with an SSH session open, the join worker ran
  about 7 times a second, from about 2.5 interrupts a second, against a target of about 1. One boot, one run.
- `ip link set wlan0 down` is one-way today: a later `up` fails with `Operation not supported` (boot `64622312`) until
  `mac` is reloaded. networkd and iwd hit it on card-18: networkd took a fresh `wlan0` up and down, then iwd's own
  interface could never start. 0670 makes such an `up` request a WLAN restart, which brings back a new phy; the
  first `up` still fails. On D1, boot `d4a5ac06`, as the custodian reports: one `systemctl restart iwd` gave that
  failure, one `WLAN restart` 6 ms later, and iwd's new interface was connected with an address 3 s after the
  restart. Bluetooth and FM re-probed and their devices were present afterwards; neither was exercised. It's by design so far: `remove_interface` sets `closing` and `stop` closes the join, so that a
  firmware BSS slot is never reused. Fixing it means re-arming after a close, which needs device tests. Not started.
- Phases 5-6 are not started.
Priorities stay in the [roadmap](ROADMAP.md#phase-b-usable-wi-fi). Demonstrated support stays in
[HARDWARE_SUPPORT](HARDWARE_SUPPORT.md). This page orders the work and
states what "done" means at each step.

## The goal

Any Gemini PDA owner installs a kernel built from this repository, runs
one documented step to fetch the firmware, and from then on uses Wi-Fi
like on any Linux laptop:
- `wlan0` appears at boot with the device's own MAC address;
- NetworkManager, iwd or a plain `wpa_supplicant` lists the networks
  around it on 2.4 and 5 GHz, including hidden ones once named;
- it joins the chosen open, WPA2-PSK or WPA3-SAE network on any channel the
  country allows, and picks the strongest access point for that SSID;
- it stays connected through a working day: key rekeys, access-point
  restarts, moving between access points of one network, idle periods;
- it costs little battery when idle, and survives `ip link down`/`up`,
  module reload and rfkill.

## Where it stands

Measured on the owner's access point only, on the development-station
kernel ([status](HARDWARE_SUPPORT.md), [gaps record](../experiments/2026-10-13-mt6797-wifi-native-delivery-probe/DAILY_USE_GAPS.md)):
- **Connection:** WPA2-PSK/CCMP, DHCP and automatic reconnects. 26 joins
  ran on one firmware start, and one connection held 2.8 h.
- **Throughput:** about 22 Mbit/s transmit and 40-50 Mbit/s receive on channel 40, with
  HT40, receive A-MPDU and a fixed transmit rate of MCS5, through a laptop on Wi-Fi on the
  same channel.
- **Reloading:** every layer reloads as a module.

What keeps it from being anyone's Wi-Fi:

| Gap | Today |
| --- | --- |
| Channel | Joins any non-DFS channel in code; 40 and 161 tested. On 2.4 GHz, channel 11 joins and receives well but transmits about 2 Mbit/s, and channel 6 failed its handshake. DFS joins are refused. The channel list follows the regulatory domain |
| Recovery | A fault ends the lifetime and the driver restarts the firmware (0443), tested on faults at disconnect under traffic. `wlan0` is recreated |
| Network choice | `wifi-up.sh` joins by name, from a private file sent over SSH, with an optional BSSID or frequency pin. No NetworkManager test yet |
| Scan | Passive on all channels of both bands, about 5 s. Wildcard active scan has run once; a named SSID has not |
| Security | WPA2-PSK only. No PMF (`ieee80211w=0`), so no WPA3. No group-key or PTK rekey: EAPOL after the 4-way handshake is dropped. No 802.1X |
| Roaming | Scan while associated (0430, 0461) ran 171 times on one boot, link kept. `wpa_cli roam` works on one boot, 21 clean at the driver, one TCP stall under a download (0456-0457, 0463-0469). Signal threshold events work at the desk, from data frames (0458, 0470). Three walks on one boot: moved by itself both ways on the first, weak links carry data with rate control (0471) on the third, gaps up to about 27 s. Closed as a success for now by the owner. Open: one access point refuses the handshake; channel 149 not settled; 0473 on a strong link only; fixes in boot2, booted once, no `bgscan` there; no network manager tried |
| Regulatory | An update that really changes the domain during a lifetime, such as an access point advertising another country than the one set, ends the lifetime until a module reload |
| Battery | Receive is polled, since the HIF interrupt line never asserted. No 802.11 power save, and no system suspend on this kernel |

## Phases

Each phase ends in a test that someone other than the developer could
repeat. Every boot keeps the project's rules: a stated hypothesis, then
evidence. Radio work beyond the owner's access point needs its own
admitted protocol (see [safety](SAFETY.md)).

### 1. One clean driver (no new behaviour)

Collapse the series into what a reviewer would read:
- one CONSYS/WMT owner, one HIF core and one mac80211 driver, built as
  modules;
- the measurement surface goes into a separate debug profile or leaves:
  the test schedule, `testcfg.c`, the snapshots, `native-diag`, the
  per-boot records and the lifecycle classifier hooks;
- the Kconfig experiment switches (HT records, HT40, fixed MCS5, rate
  control) become the driver's normal behaviour or a module parameter;
- fix the bounded counters that still refuse at 255 (the channel token and
  the station sequence) now, while the code is being reorganised.

**Exit:** the clean profile repeats the station 9 results (26 reconnects,
a 2.5 h hold) and boot AV's throughput within its control band. The
series is W=1- and checkpatch-clean. The old station profile retires.

### 2. Comes up by itself, from files anyone can get

- **Firmware and calibration.** The driver already loads all four files
  from `/lib/firmware/mediatek/mt6797/`. The
  [firmware page](hardware/firmware.md#files-the-mainline-wi-fi-driver-loads)
  lists them, their Gemian source paths and how they are checked. Owners
  copy the three firmware files from their own device; the repository
  cannot ship them (`required-nonfree`, no redistribution right).
  `WIFI.storage` is not copied: the system mounts the `nvdata` partition
  read-only at `/nvdata` and links the record into the firmware directory.
  The station's RAM root does the same. Take the permanent MAC address
  from that record rather than a fixed value.
- **Start.** Power and firmware start happen in the driver: at probe, or
  on the first `ifup` with an idle power-off. The two userspace writes go.
- **Regulatory.** Ship with `regulatory.db` and follow the country
  through cfg80211, using the existing country-power encoder. Remove the
  fixed channel set.

**Exit:** on a freshly installed system, the three documented firmware
files, the `nvdata` mount and link, a reboot and `nmcli device wifi connect <owner AP>` work without SSH or a
custom `wpa_supplicant.conf`.

### 3. Any network, any channel

- **Channels.** Read the receive descriptor's channel field instead of
  comparing it with 40. Advertise every 2.4 and 5 GHz channel the firmware
  supports and mark them as the regulatory domain says: no-IR and DFS
  channels are passive scan only.
- **Scan.** Scan many channels in one request, with a proper dwell. Do
  active scans with probe requests and the requested SSIDs, so hidden
  networks can be found. Report every BSS with its signal strength.
- **Bandwidth.** Use HT20 and HT40 per access point. 2.4 GHz stays 20 MHz
  under 20/40 coexistence. VHT later.
- **Security.** Add PMF (802.11w, BIP) and WPA3-SAE. The host already
  builds authentication frames, so SAE should fit mac80211's SME path.
  Then WPA2-Enterprise (802.1X), whose EAPOL goes on AC_VO on some access
  points.

**Exit:** a test matrix of at least three access points (two makes),
covering:
- channels 1, 6 and 11;
- 36–48, a DFS channel (52–64 or 100–140) and 149–165;
- open, WPA2-PSK, WPA3-SAE and transition mode;
- one hidden SSID;
- a phone hotspot.

Each one joins, gets DHCP and carries a 60 s transfer.

### 4. A full day, anywhere

- **Group-key rekey.** Protected EAPOL receive with a PN check, and
  protected EAPOL transmit. A second group key under a new index while the
  old one is still current, then its removal without closing receive.
  This is item 2 of the gaps record, with its two offline questions first.
- **PTK rekey** with the same machinery.
- **Roaming.** Scan while associated: firmware off-channel scan or
  mac80211 software scan, with a bounded absence. Then reassociation to
  another BSS of the same SSID. `wpa_supplicant` and iwd pick the access
  point and decide when to roam. The driver only has to scan, report and
  reassociate. 802.11r/k/v later.
- **Recovery.** A firmware or HIF fault ends in a driver-owned restart
  (WMT off and on, then rejoin), never in a poisoned driver that needs a
  reboot. Wire rfkill.

**Exit:**
- 24 h connected on an access point that rekeys the group key every
  10 minutes, with no disconnect at a rekey;
- an 8 h day that moves between two access points of one SSID, with
  every handover logged and no manual action;
  the owner can carry the device between access points once roaming is in
  the driver. USB is then unavailable, so the device logs to its data
  partition and the log is read afterwards;
- 20 forced firmware faults, each recovered without a reboot.

### 5. Battery

- **802.11 power save.** Firmware PS-Poll or U-APSD, as the vendor's
  power-management path does. DTIM-based wake while idle.

  **Scope, at the owner's request ("Scope power save", 2026-11-16); nothing below is admitted or built.**
  On a quiet joined link the WLAN interrupt matches received frames (about 3 a second), but SODI periods end
  every 56 ms at the median, which fits the 102.4 ms beacon interval: the firmware runs with power save off
  (`IEEE80211_CONF_PS` is refused) and wakes for every beacon. Two separate mechanisms, from the vendor's gen3
  driver:

  - *802.11 power save.* `CMD_ID_POWER_SAVE_MODE` (0x05), `{ bss_index, ps_profile, 2 reserved }`; the
    profile values (constant awake, fast PS, maximum PS) are still to be confirmed from the vendor's OID code.
    The firmware then sets the PM bit, sleeps between DTIMs and fetches buffered frames itself; the driver
    already sends `CMD_ID_INDICATE_PM_BSS_CONNECTED` (0x16) with the DTIM period, AID and beacon interval. In
    the driver: accept `IEEE80211_CONF_PS` and send the profile from `config`, advertise `SUPPORTS_PS` and
    `SUPPORTS_DYNAMIC_PS` so mac80211 leaves the null frames to the firmware, and gate it behind a module
    parameter first, since `CONFIG_CFG80211_DEFAULT_PS=y` would otherwise turn it on at every join.
  - *Low-power ownership.* The driver holds driver own (WHLPCR bit 8) for good. The vendor hands ownership
    back with `WHLPCR_FW_OWN_REQ_SET` and reclaims it with `FW_OWN_REQ_CLR`, polling up to 2048 ms, before HIF
    access. Without it CONSYS likely cannot sleep. It touches every HIF access path, so it is a later stage.

  Risks: access points that buffer badly or drop the PM state; broadcast and ARP delivered only at DTIM; added
  latency up to the DTIM interval for the first frame after a quiet spell; an untested firmware command ending
  in a fail-stop; and, for ownership, a HIF access while the firmware owns the bus, which would stall or
  restart the WLAN.

  Staged plan, each stage needing its own admission:
  1. *Baseline, read only:* battery current averaged over 10 min on a quiet joined link with the screen
     blanked and no SSH, and the cpuidle SODI wake distribution in the same state.
  2. *Fast PS by module parameter:* one join, then 10 min quiet, a laptop ping at 1 s, a 60 s download and one
     reconnect. Stop at any restart, `join stopped`, `txfail`, disconnect, or ping loss above 1 %.
  3. *Maximum PS*, the same test, only if 2 holds.
  4. *Ownership handoff*, designed after 2.

  The gain to measure, against stage 1: SODI wakes on a quiet link moving from beacon pace to DTIM pace or
  slower, and the battery current falling, both on the same boot by toggling the parameter.

  Stage 2's code is 0812, written at the owner's request ("Stage 1 + write 2"): `mac.power_save=1` (maximum) or
  `2` (fast) offers firmware-managed power save, and `iw dev <if> set power_save on/off` switches between that
  profile and constantly awake. The default sends nothing. Compiled only; not admitted to run.

  Stage 1 baseline (custodian, boot `2d4dcc57`, power save off, screen blanked, no SSH, all CPUs online, no
  SODI): battery discharge averaged 153.6 mA over 602 s (median 152.7), with 3.2 WLAN interrupts and 3.3
  received frames a second, 1.4 of them dropped, and nothing sent. With all CPUs online and no SODI, the radio's
  share of that may be small, so stage 2 compares power save on and off on one boot in the same state, plus
  SODI windows.

  Stage 2, as the custodian reports (boot `2d4dcc57`, `power_save=2`): 0812 never sent the command (mac80211
  reports power save through `BSS_CHANGED_PS`, fixed in 0813), and 0813's was refused locally (the encoder did
  not admit command 0x05, fixed in 0814). With 0814 the first join sent fast power save with status 0; 180
  pings at 1 s lost none, at 39.9/95.4/206.4 ms against 3.4/29.5/266.7 with power save off, and a 60 s download
  ran at 4.69 MB/s. After `ip link down` and `up`, which restarts the WLAN by design (0670), the resend came back
  `-ETIMEDOUT`, having lost its credit to the mask-control submission, and a page stayed owed. 0815 holds the
  profile until the data phase settles.

  With 0815 (`mac` e989cbc1), as the custodian reports on the same boot, on battery with the screen off, three
  10 min phases toggled with `iw`: fast power save drew 86.3 mA, then 142.7 mA with it off, then 92.6 mA
  (median 83.4; about 160 mA for the first 50 s after switching it back on). That is about 57 mA less on a quiet
  link. Every toggle sent its profile with status 0, an iwctl reconnect re-sent it about 6 s after the join,
  and nothing restarted. With power save on, WLAN interrupts rose to about 5.6 a second, from 3.8, for the same
  received frames. Cable-in checks: 180 pings, no loss, median 97 ms; a download at 4.69 MB/s. Each power-save
  log line appears twice, not yet explained. One boot. The owner chose it on by default ("Yes, on by default"):
  `0818` sets `power_save=2` as the default. Compiled only; it reaches the device with the next image.
- On an idle, connected station with power save on, the join worker still ran about 32 times a second against
  12 WLAN interrupts (custodian, image 138): after each frame it polled at once while work was owed, and every
  20 ms for a second after any unicast frame. 0857 lets the interrupt pace it, and 0861 allows 8 immediate passes
  after progress while work is owed. On card-32, idle and blanked: about 4.9 runs a second with 0861 (5.5 with
  0857), WLAN interrupts 287 a minute (723 before), the DA9214 I2C bus 416 (1545). Transmit measured 2.40 to 2.47
  MB/s with 0861 and 2.45 with 0857 on the same boot, against 2.68 for the old module on an earlier boot; receive
  4.84 to 5.33. Whether that transmit gap is the change or the boot is not settled.
- After an rfkill block and unblock on card-32 (boot `0dad538a`, custodian), Wi-Fi did not come back. From the
  kernel log: the unblock's `up` hit the closed instance and its restart (0670) completed with a new phy, a scan
  was cancelled 0.3 s later, and nothing followed for 640 s until a manual unblock restarted it again. A restart
  request less than 30 s after the last one was dropped, so an interface closed again just after a restart
  stayed down. 0862 defers such a request to the end of the spacing instead. iwd's log then showed why it
  closed again: networkd brought the new `wlan0` up at once, and iwd, keeping the default interface, toggled
  it down and up during its setup. At boot that toggle is harmless because the earlier `up` fails before the
  firmware is ready. Without a config change each restart could be closed the same way, so 0862 is not to be
  tested alone; the suggested change is `[Link] ActivationPolicy=manual` in `50-gemini-wlan.network`, leaving
  link-up to iwd. A reversible down/up in the driver remains the real fix and is not started. Compiled only.
- The retest with 0862 and gemini-base 69 (image 139, boot `b83b8049`, custodian) had one restart, status 0,
  yet the new phy came up soft-blocked, and the block was restored on the next boot. Cause, from systemd's
  rfkill source: it writes a change only on exit, 5 s after the last event, drops the queued write of a
  device that goes away, and applies the saved state to a device that appears. The unblock was lost with the
  old phy and the stale block applied to the new one. Inference: the log does not show the dropped write, but
  the timings and a second boot fit it. gemini-base 70 masks systemd-rfkill. 0866 and 0867 keep the phy
  instead: the restart halts the mac layer (disconnecting first), CONSYS reprobes, and the kept phy gets the
  new lifetime with its state group cleared under the wiphy lock. An `up` of a closed interface now succeeds
  at once; scans are refused until the new lifetime is ready. The mac and CONSYS modules go together, since
  the ops structure gains the halt. Compiled only.
- 0867's first test (boot `2de14aa4`, custodian) failed in cycle 1: the restart registered phy2 and `wlan1` beside
  the halted phy1, and `wlan0` got no address. CONSYS's remove clears its whole owner, the kept phy pointer
  with it, so the attach after the reprobe registered a new phy; it also loads the configuration record again,
  as the owner's configured flag is cleared too. The orphaned phy1 stayed registered after the rollback
  unloaded the mac module, and the station switched itself off about 5 minutes later; that the orphan caused
  it is an inference awaiting the journal. 0869 holds the phy outside the owner. Compiled only.
  The journal then showed two more things. At the unblock, the open's configuration was refused because the
  lifetime was closed, and `ieee80211_hw_conf_init()` warned; 0870 accepts it while a restart is pending and
  has the resume take the join channel from mac80211's current configuration. After the rollback, a regulatory
  update oopsed in the mac module's code through a dead device, and the station hung and powered off: consistent
  with the orphaned phy, whose callbacks pointed into the unloaded module. Compiled only.
  The rollback's `WLAN stop: power-off status=-95` is a separate, older teardown case: unloading the mac module
  while associated, the deauthentication's completion went missing and was retired late without credit, so its
  page stayed retained, and with a retained cleanup page only removal and abort commands are encoded. The stop
  refused as designed and CONN was powered off anyway. The fixed pair is package `f3d8d336` (mac `f8f0274e`,
  CONSYS `d9f7a1d9`).
- That pair passed on card-32 (image 139, boot `0d12a9a2`, custodian, swapped onto the running station): two
  rfkill block and unblock cycles three minutes apart each gave one restart, "lifetime halted; phy kept", then
  "lifetime resumed on the kept phy: status=0" about 2 s after the unblock; the phy, its rfkill ID and `wlan0`'s
  ifindex stayed the same, one wlan interface, the soft block stayed off at +10 s and +120 s, no warning, and
  IPv4 returned 14 s after the unblock with 5 of 5 pings. Not exercised: unloading the pair, a fault while
  associated (the halt's disconnect path) and iwd's Powered toggle.
- **Polling.** The receive interrupt line never asserted, so make the poll
  adaptive: fast while traffic flows, backing off to the DTIM interval
  while idle. Before that, look once more for the interrupt route, the
  WHIER source or EINT, now that the EINT pad-mode fix (0377) explained
  two other silent lines.
- **System suspend** (a platform gap, not a Wi-Fi one) with Wi-Fi off
  across it. Wake-on-WLAN later.

**Exit:** the idle connected power draw, measured at the battery with
charge-guard holding the charger off, is within an agreed margin of
Gemian's on the same access point. The CPU stays mostly idle while the
link is idle.

### 6. Hand-over to users and upstream

- **Docs.** A page in `docs/` for owners: the firmware files to copy,
  the supported security modes and bands, and the known limits.
- **Distribution.** A kernel config fragment for distributions
  (postmarketOS, Mobian, Gemian successors), with the driver as modules.
- **Upstream.** DT bindings for the CONSYS owner and WMT, the STP and BTIF
  transport, and the WLAN driver, each with a real author and a truthful
  certification (see the [upstream gate](ROADMAP.md#upstream-delivery-gate)).
- **Firmware rights.** Ask MediaTek, or linux-firmware, about
  redistributing the firmware, so that owners no longer copy it.

## Order and size

Phases 1 and 2 come first. Every later test is cheaper on a clean driver
that starts by itself, and 2 is what makes the driver usable by someone
else at all. Phase 3's channel work is next, because it unlocks every
other network. The phases run in this order:

1. Phase 1: mostly reorganisation. Two or three boots to confirm nothing
   regressed.
2. Phase 2: moderate. One boot per change (firmware path, start,
   regulatory).
3. Phase 3: channels and scan first, a few boots on the owner's access
   point and a second one. Security modes after: new code, one boot each.
4. Phase 4: the largest. Rekey alone needs offline answers, then a boot
   against a rekeying access point. Roaming needs a second access point.
5. Phase 5 can start in parallel with 4.

## What the owner provides

- A second access point, or the router's guest network on another
  channel and band, and a phone hotspot, for phases 3 and 4.
- An access point setting with a short group-rekey interval, or a
  `hostapd` configured to rekey every few minutes.
- A decision on the security modes that matter (WPA3, Enterprise).
- Approval of the radio test protocol for channels and power beyond the
  current single channel.
