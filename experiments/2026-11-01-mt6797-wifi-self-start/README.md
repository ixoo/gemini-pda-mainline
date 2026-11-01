# Experiment: Wi-Fi comes up by itself (daily-use plan, phase 2)

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-mt6797-wifi-self-start` |
| Status | `running`: Wi-Fi starts by itself and follows the US country (stations 25-27); station 28 passes from a clean boot: self-start, US country, join and 26 reconnects |
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

## Regulatory (station 26)

[0402](../../patches/proposals/0402-wifi-mt6797-advertise-UNII-2A-UNII-2C-and-UNII-3.patch)
advertises 52-64, 100-144 and 149-165 besides 1-13 and 36-48. The
firmware domain is encoded by operating class (81, 115, 118, 121, 125),
as the vendor's domain table does, with DFS channels in the passive list,
and CID 0x38 carries one limit per UNII group. A host check of the
encoder with a US channel set gave the classes, ranges and limits
expected. The station RAM root carries wireless-regdb 2026.09.03's
signed `regulatory.db` (release hash checked against kernel.org's signed
list), and init runs `iw reg set US`. Scan and join stay on channel 40,
so transmission is unchanged.

Build: Buildbox at 82106b72, 567 patches, package inventory `bccf6f69…`;
`Image.gz` unchanged (`0d4d6d74…`). `regulatory.db` `7e236cae…`. boot2
`c8cf0aaf…`, written over station 25 with a matching readback.

Hypothesis: on station 26, cfg80211 loads the database, the country is
US, the driver submits US's domain and power without error, and Wi-Fi
behaves as on station 25.

Procedure:
1. Kernel log: `regulatory.db` loaded and no "regulatory submission
   stopped". Status `reg=US`. `iw reg get` shows `country US` for the
   phy as well as globally.
2. `iw phy phy0 channels`: 1-11 enabled, 12-13 disabled, 36-165 listed
   with 52-144 marked radar detection.
3. `wifi-up.sh`, ping, ten reconnects, throughput, as on station 25.
4. Kernel log: no Oops, warning or call trace.

| Observation | Decision |
| --- | --- |
| Steps 1-4 pass | Phase 2's code is done; the exit test on a full system follows phase 3's channel unpinning |
| The database does not load | Check the signature keys; the station can fall back to the world domain meanwhile |
| The domain or power submission fails | Compare the payloads with the host check; return to station 25's channel set if the firmware refuses the new classes |

### Result: station 26, boot `6b0273db` (2026-11-01)

| Step | Result |
| --- | --- |
| 1. Regulatory | `regulatory.db` loaded (no "failed to load"); status `reg=US`; `iw reg get` shows `country US: DFS-FCC`; the firmware accepted the domain and power at attach (`regulatory configuration: status=0`) and no submission stopped |
| 2. Channels | 1-11 enabled, 12-13 disabled; 36-165 listed, 52-144 with radar detection |
| 3. Wi-Fi (0402's `mac`) | Failed. The join reached association, then stopped with `-ECANCELED`, branch 9 (a regulatory update during the lifetime): the access point's country element (US, the country already set) reached the notifier. Later scans were refused (`-EOPNOTSUPP`). Without `regulatory.db`, cfg80211 never acted on that element |
| 3b. Wi-Fi with [0405](../../patches/proposals/0405-wifi-mt6797-ignore-regulatory-updates-that-change-no.patch) | `mac` swapped from the b7774d77 package (`27cc2ea3…`; `Image.gz` and the other modules unchanged), after a full reload that powered CONN off and started the firmware afresh. Join `COMPLETED`, a lease, ping 10/10 (6.4 ms average), ten reconnects 10/10 in 0.97-1.14 s, each 2/2. The country element arrived at each of the 11 associations and ended none. Receive 47 and 43 Mbit/s, transmit 21, 23 and 23 Mbit/s at -58 dBm |
| 4. Kernel log | No Oops, warning or call trace after the reload; not tainted |

A swap without the reload first failed (scan `-71`, channel refused):
the poisoned first lifetime had left firmware state behind, which the
reload cleared.

0405 skips an update whose domain and power payloads equal those last
sent. An update that changes them during a lifetime, for example an
access point advertising another country than the one set, still ends
the lifetime as before; recovering from that belongs to phase 4.

Station 27, from the b7774d77 package with 0405's `mac` (`27cc2ea3…`)
and otherwise station 26's inputs, is on boot2 (`6af3c678…`, written over
station 26 with a matching readback).

### Result: station 27, boot `778ff91c` (2026-11-01)

The b7774d77 image booted as composed: 0405's `mac` (`27cc2ea3…`),
`reg=US`, `country US: DFS-FCC`, the firmware ready at 3.9 s.
`wifi-up.sh` joined (WPA2-PSK/CCMP, a lease, gateway 3/3), ping 10/10.
Reconnects 1-7 completed in 0.97-1.12 s; 8-10 did not.

Lifetime 9 (the eighth reconnect), traced in the kernel log:
- it followed a command-sequence recycle (213 to 13), as station 9's
  long runs did;
- association succeeded and the access point's country element ended
  nothing (0405);
- only two EAPOL frames reached the supplicant. Later EAPOL frames from
  the access point were refused by the driver's per-lifetime delivery
  cap ("delivery-cap"), and the supplicant reported a 4-way handshake
  failure. The frame pattern fits a lost handshake frame that the
  access point retransmitted;
- the lifetime ended without keys, so the re-arm, which waits for
  exactly two key removals, stayed deferred (`key_removals=0`). Every
  scan after that was refused with `-EBUSY` until a full module reload,
  which restored Wi-Fi.

In stations 25 and 26 the first EAPOL frame also arrived before the
lifetime's activation; that ordering is normal and not the cause. Nothing
in this path depends on the regulatory change: the cap and the re-arm gate
predate it. Two driver gaps are exposed:
- a single lost handshake frame ends the lifetime, because the cap does
  not admit the access point's retransmissions;
- a lifetime that never installs keys can never re-arm.

### Result: 0406 by module swap on station 27 (2026-11-01)

[0406](../../patches/proposals/0406-wifi-mt6797-survive-a-lost-handshake-frame.patch)
admits up to four EAPOL frames each way until the pairwise key is
submitted (two after that, as before), and lets a lifetime that never
submitted a key re-arm. `mac` `d5a41fb1…` from the 2170f1ce package
(`Image.gz` and the other modules unchanged), loaded after a full reload,
boot `778ff91c`.

| Check | Result |
| --- | --- |
| 26 reconnects | 26/26 `COMPLETED` in 0.96-1.20 s, each 2/2 gateway pings, through three command-sequence recycles. No handshake failure, no deferred re-arm, no delivery-cap refusal: no frame was lost in this run, so neither new path ran here |
| One attempt with a deliberately wrong PSK on the owner's access point | Both new paths ran. Six EAPOL frames were admitted across that attempt and the following good join, none refused by the cap. The supplicant reported the handshake failure, the lifetime ended without keys, and `join rearm: lifetime=28` followed with no deferral. With the real key restored, `COMPLETED` in 2 s and gateway 3/3, with no reload |
| Kernel log | No Oops, warning or call trace; not tainted |

Not measured: throughput with 0406, and a real lost frame followed by a
successful handshake (the wrong key exercises the retransmissions and the
re-arm, not message 3 arriving after them).

Station 28, from the 2170f1ce package with 0406's `mac` (`d5a41fb1…`) and
otherwise station 27's inputs, is on boot2 (`83fd0f91…`, written over
station 27 with a matching readback).

### Result: station 28, boot `a4079e78` (2026-11-01)

No module swap. `mac` `d5a41fb1…` as composed; status `nvdata=mounted`,
all three `wifi=` lines, `reg=US`; `country US: DFS-FCC`; firmware ready at
3.9 s and `phy0` present with no SSH step; `WIFI.storage` the link to
`nvdata`. `wifi-up.sh`: `COMPLETED` on 5200 MHz WPA2-PSK/CCMP, a lease,
gateway 3/3. Ping 10/10 (6.5 ms average). 26 reconnects 26/26 in 0.99-1.17 s,
each 2/2, through three command-sequence recycles: 26 re-arms, none
deferred, no delivery-cap refusal, no handshake failure. No Oops, warning
or call trace; not tainted.

## Follow-up

- Station 9's 2.5 h hold, not yet repeated on the clean driver.
- The phase 2 exit test, `nmcli` on a full system, once the channel pin
  goes in phase 3.
- A country change during a lifetime still ends it (phase 4, recovery).
