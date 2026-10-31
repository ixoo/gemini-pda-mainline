# R2 calibration protocol

Status: admitted by the owner on 2026-10-31, with the restart implemented as
a module reload ([R2](README.md#r2-as-a-module-reload-2026-10-31)). Not yet
run.

**Amendment on admission.** The owner chose the full module split, so that
any Wi-Fi change is tested by reloading modules. That needs more than one
restart per boot, so the "at most one R2 per boot" precondition below is
replaced:
- Each restart follows a completed unload: CONN powered off, its domain
  confirmed off and every vote returned.
- A failed step ends restarts for that boot.
- Every other bound and precondition stands.

The checks map onto the module form as follows:
- The unload performs R1 and the power-off.
- The next load's existing checks refuse a CONN that is not confirmed off,
  VCN18, VCN28 or either VCN33 still active, or an EMI state other than
  boot-clear or the earlier start's own.

R2 restarts the CONN subsystem within one boot. Its start half reruns the WMT
common initialization: ROM patches, MCU clock, LTE coexistence, PA rails,
**RF calibration**, PA rails off and antenna mode. The restart
[design](README.md#proposed-design) left this repeated calibration to its own
protocol, as [SAFETY](../../docs/SAFETY.md) requires for calibration and radio
actions. This is that protocol.

## What is already admitted

- **The common init itself.** The Phase A
  [effect review](../2026-10-06-mt6797-wifi-common-init/EFFECT_REVIEW.md)
  admitted every step, calibration included, once per boot.
  - Calibration is one firmware-internal run of `01 14 01 00 01`, with no
    host transmit, association or scan around it.
  - Every WMT write targets the CONSYS MCU or firmware. The PA rails, through
    the regulator API at 3.3 V, are the only AP-side effect.
  - Nothing is written to storage, NVRAM or calibration partitions. All the
    effects live in CONSYS and end with a reboot.
- **On the device:** every station and soak boot since then has run it
  (285/285 steps).
- **Repetition is routine on this unit under Gemian.** The vendor reruns the
  full common init at every CONN power-on (`stp_init`). One Gemian
  last-client cycle on this unit was observed:
  - WLAN off powered CONN off (CONN bit 1 cleared);
  - the next power-on restored WLAN and BT
    ([trace receipt](../2026-09-26-gemian-wifi-reference/results/trace-shared-off-v8-1.json),
    [hardware facts](../../docs/hardware/mt6797-wifi.md)).

  So a second calibration in one boot is the vendor's normal behaviour, not a
  new kind of operation.

## What is new under R2

1. A second common init in the same boot, after the R1 stop and a full CONN
   power-off and power-on (CONMCU reset held, then released).
2. The ROM patches are downloaded again into a freshly reset CONN MCU.
3. A second RF calibration and a second PA rail on/off pair in the same boot.
4. The vendor's whole-chip-reset retry loop (up to 10 attempts) is **not**
   copied: each step runs once.

## Preconditions

The R2 code checks each of these and refuses before any power change if one
fails:
- **R1 completed this boot:** `WLAN stopped` was logged, WLAN_READY was
  clear, and VCN33-WIFI was disabled.
- **The mac layer is detached,** and no WLAN attach is in progress.
- **No other CONN client:** the PMIC control registers show VCN33-BT and
  VCN33-WIFI both inactive, the same check as the existing HIF probe. A
  held BT vote refuses.
- **CONN is off before power-on:** the domain was confirmed off after the
  stop, with CONMCU reset asserted.
- **At most one R2 per boot** (replaced on admission; see the amendment
  above).

The custodian also checks these before triggering it:
- the session is attended by the owner, and the lid is open;
- the station has been up for under an hour, with no thermal warning in the
  kernel log. There is no thermal driver, so the custodian keeps the session
  short.

## Bounds

These are the same as Phase A:
- each step runs once;
- each WMT exchange waits at most 2 s for its exact event;
- the whole common init is capped at 60 s;
- the first failed step stops the sequence, with no retry or cleanup write.

The calibration event is accepted on its `02 14` prefix and a length field
that matches, as in Phase A. Its content is recorded, not judged: what
counts as calibration success is still unknown.

## Stop handling

- **A failure before PA-on:** the station stays up with Wi-Fi off. The
  custodian saves the kernel log; the next boot restores everything.
- **A failure between PA-on and PA-off:** one or both PA rails may stay on.
  The custodian saves the kernel log and powers the station off with an
  orderly `poweroff` within five minutes. Rails must not stay on through an
  unattended or long session.
- **A hang:** the watchdog or a reboot by the owner recovers it, as for any
  station boot.
- Never retried in the same boot, and never followed by a different reset
  path.

## Records

- **Public:**
  - each step's result and the steps completed (for example 285/285);
  - the calibration event's length;
  - whether its bytes equal the first run's in the same boot (`same` or
    `different`);
  - both rails' states after PA-off;
  - the elapsed time since the first calibration.
- **Private:** the calibration event bytes themselves, kept in the ignored
  station evidence and never committed.

## Readings (predeclared)

| Observation | Reading |
|---|---|
| Common init 285/285 again, calibration event of the same length, rails off, then START, firmware ready and a scan with BSS | A full restart works within one boot; CONSYS as a module becomes possible |
| Calibration bytes `different` but the scan finds BSS | Calibration output varies between runs, as on every Gemian power-on; not a fault |
| A ROM patch step fails | The patch does not reapply to a reset MCU this way; stop and record the step |
| The calibration event times out or is malformed | The second calibration is not admitted by this firmware state; stop, rails per the rule above |
| START or WLAN_READY fails after a clean common init | The common init survives a restart, but region 18 or the HIF start does not; that step names it |
