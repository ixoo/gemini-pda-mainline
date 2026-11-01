# Experiment: Wi-Fi comes up by itself (daily-use plan, phase 2)

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-mt6797-wifi-self-start` |
| Status | `complete`: station 25 starts Wi-Fi by itself with the record read from `nvdata`; regulatory remains for phase 2 |
| Subsystem | Wi-Fi: `mt6797-consys`, `mac`; station init |
| Device variant | named Gemini PDA (MT6797X), boot2 station |
| Date(s) | 2026-11-01 |
| Investigator(s) | project custodian |
| Tracking issue | none |

## Question or hypothesis

Phase 2 of the [daily-use plan](../../docs/WIFI_DAILY_USE_PLAN.md#2-comes-up-by-itself-from-files-anyone-can-get)
makes Wi-Fi start without SSH steps, from files any owner has. The first
step covers the start and the calibration record:
- [0400](../../patches/proposals/0400-soc-mediatek-mt6797-consys-start-the-subsystem-after.patch)
  runs the CONSYS start chain from a work item queued at probe, replacing
  the root writes to `region19_prepare` and `wmt_negotiate`. A `mac`
  module loaded before the firmware is ready is held and attached when
  it is. (The commit that added it, e8c1bf5a, calls it 0399; the number
  moved to 0400 when an audio patch took 0399.)
- The station init mounts `nvdata` read-only with `noload`, found by its
  partition label, and links `APCFG/APRDEB/WIFI` as the firmware loader's
  `mediatek/mt6797/WIFI.storage`, as the
  [firmware page](../../docs/hardware/firmware.md#files-the-mainline-wi-fi-driver-loads)
  describes. The RAM root no longer carries a copy. Init then loads the
  core, CONSYS and `mac`.

The permanent MAC address already comes from the record (bytes 4-9), so
it needs no change. Regulatory is a later step.

Hypothesis: on station 25, `wlan0`'s phy exists after boot without any
SSH step, with the MAC address and calibration from `nvdata`, and Wi-Fi
behaves as on station 24.

## Safety assessment

The start chain is the station's reviewed one; only its trigger moves
from two root writes to probe time, so it now runs at every boot. The
radio use is unchanged: calibration at start, then the owner's access
point on channel 40. `nvdata` is mounted read-only with `noload`, so no
journal replay writes to the partition. A boot that fails returns to the
previous image through boot2.

## Build

Buildbox at e8c1bf5a: 566 patches, package inventory `c24903eb…`.
`Image.gz` is `0d4d6d74…`, byte-identical to station 24's; only the
modules and the RAM root change. Composed as boot2 `561100cf…`, written
by `flash-boot2` over station 24 (`f7761f02…`) with a matching readback.

## Procedure

Station 25 through the usual boot2 path. Then, over USB SSH:
1. `/run/station/status`: `nvdata=mounted`, three `wifi=` lines without
   `-failed`. The kernel log shows the start chain's lines in order,
   ending with the firmware ready line and the mac attach, with no root
   write. `/sys/class/ieee80211/phy0` exists, and its address equals
   bytes 4-9 of `/nvdata/APCFG/APRDEB/WIFI`.
2. `/lib/firmware/mediatek/mt6797/WIFI.storage` is the link to the
   record, and the record is byte-identical to station 24's copy.
3. `wifi-up.sh`, then station 24's checks: gateway ping, ten reconnects,
   throughput.
4. `wifi-cycles.sh` with `CYCLES=1 RESTARTS=1`: a `mac` reload, then a
   CONSYS reload that starts the firmware again by itself.
5. Kernel log: no Oops, warning or call trace.

| Observation | Decision |
| --- | --- |
| Steps 1-5 pass | The start and record parts of phase 2 are done; regulatory next |
| `nvdata` does not mount | Keep the copied record for the station, investigate the partition offline |
| The start stops or `mac` does not attach | Compare the log with station 24's; the chain itself is unchanged, so look at the trigger and attach ordering first |

## Observations

Station 25, boot `2c826ce3` (2026-11-01).

| Step | Result |
| --- | --- |
| 1. Boot | Status: `nvdata=mounted device=/dev/mmcblk0p6` and `wifi=` for all three modules. `/nvdata` is mounted `ro,norecovery`. In the log, with no root write: WMT window prepared at 2.33 s, common init `completed=285/285` at 3.68 s, EMI final policy, firmware ready and the `mac` attach (record prepare 0, regulatory 0) at 3.76 s. `phy0`'s address equals bytes 4-9 of the record |
| 2. Record | `WIFI.storage` is the link to `/nvdata/APCFG/APRDEB/WIFI`; the record's SHA-256 equals the copy station 24 carried |
| 3. Wi-Fi | `wifi-up.sh`: phy present at once, `COMPLETED` on 5200 MHz WPA2-PSK/CCMP, a lease, gateway 3/3. Ping 10/10 (12.9 ms average). Ten reconnects 10/10 in 1.00-1.11 s, each 2/2. Receive 42 and 43 Mbit/s, transmit 22, 22 and 22 Mbit/s at -61 dBm |
| 4. Reload | `CYCLES=1 RESTARTS=1`: a `mac` cycle (re-attach kept the configuration, passive scan 3 BSS). Then CONSYS and core unloaded (WLAN stopped, CONN off) and reloaded: CONSYS started again by itself, common init 285/285, firmware ready 2 s after the load, a second cycle passed |
| 5. Kernel log | No Oops, warning or call trace; not tainted |

## Analysis

- The start chain is unchanged and now runs from probe. It finishes
  about 1.4 s after the WMT window is prepared, so Wi-Fi is ready about
  4 s into boot.
- The record is read in place: the link, the read-only mount and the
  unchanged hash show the firmware loader reads the device's own
  `nvdata`. `norecovery` confirms `noload` took effect.
- Throughput is at or above station 24's (receive 37-38, transmit
  20-22), at a stronger signal.

## Conclusion

The predeclared first row holds: Wi-Fi comes up by itself at boot, with
the calibration record and the MAC address from `nvdata`, and behaves as
before across reconnects and module reloads. Joining still needs
`wifi-up.sh` (the pinned network and supplicant configuration).

## Follow-up

- Regulatory: follow the country through cfg80211 and `regulatory.db`,
  dropping the fixed channel set (phase 2's last part).
- The phase 2 exit test, `nmcli` on a full system, once the channel pin
  goes in phase 3.
