# Experiment: Wi-Fi comes up by itself (daily-use plan, phase 2)

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-mt6797-wifi-self-start` |
| Status | `running`: station 25 is on boot2 and awaits its boot |
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
