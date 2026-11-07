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
  Compiled only; not yet run with iwd.
- `ip link set wlan0 down` is one-way today: a later `up` fails with `Operation not supported` (boot `64622312`) until
  `mac` is reloaded. It's by design so far: `remove_interface` sets `closing` and `stop` closes the join, so that a
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
