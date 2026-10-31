# Wi-Fi for daily use — the driver's gaps

Scope record, 2026-10-28. Written from a source read of the lifecycle
tree (0333) while device boots were unavailable. Nothing here was booted.
Each item is its own reviewable change. The ones that need the device get
their own predeclared boot.

Daily use here means the station:
- stays associated for a working day on the owner's access point;
- reconnects by itself whenever the link drops;
- survives the access point's key schedule;
- carries ordinary traffic, idle or busy.

The demonstrated base is in
[HARDWARE_SUPPORT](../../docs/HARDWARE_SUPPORT.md) and the
[lifecycle result](LIFECYCLE_RESULT.md): repeated WPA2-PSK lifetimes on one
boot, reconnection after the access point's own loss, and the
[boot AV](THROUGHPUT_SERIES_RESULT.md#rate-control-against-the-fixed-rate-2026-10-27-boot-av)
throughput.

## Blockers found by source reading

Both were found by reading the source, not by a test. A daily driver meets
both within a morning. Each is tested on its own boot, on the kernel that
carries exactly these two over AV (`f2a97fb1`). They ride with no other
change: they are structural, and their failure mode, a poisoned driver or
a failed lifetime, would contaminate anything beside them. The
predeclarations are in
[§70](HIF_TRANSPORT_ANALYSIS.md#70-the-daily-use-fixes-and-the-soaks-idle-record-predeclared-2026-10-28).

### The driver died at the twelfth connection (0334)

**What happened.** Every firmware command takes a single-use sequence
number, and none was ever released. One lifetime uses 22 (boot AV's log:
lifetime 1 starts at 10, and each re-arm adds 22). After lifetime 11 the
sequence is 252. The re-arm gate refused the next lifetime as exhausted
and poisoned the driver until reboot.

The link is lost after about six minutes, idle or not, so that is about
an hour of use.

**The fix.** 0334 recycles the sequences at the quiescent re-arm barrier,
before lifetime 10. Join completions are matched by credit and channel
token, never by command sequence. Lifetimes 1–9 are unchanged.

**Why no test caught it.** No boot ever ran more than six lifetimes: the
lifecycle harness allows two to six cycles inside one 720 s wall.

**Evidence.** One boot cycling twelve lifetimes, predeclared in
[§70.2](HIF_TRANSPORT_ANALYSIS.md#702-the-0334-boot-twelve-lifetimes-on-one-boot-predeclared).
It passes if the twelfth lifetime joins and carries traffic like the
first, with no exhausted-sequence refusal.

### A connected lifetime failed after about two hours (0335)

**What happened.** A lifetime failed once it read 65536 HIF packets.
Beacons and group frames alone arrive at 8–11 a second, so it was reached
after 1.7–2.3 hours (about 1.8 at 10 a second), however light the use.

**The fix.** 0335 makes that a count, not a fence, for the connected
lifetime only. The diagnostic counts already saturate rather than stop.

**Why no test caught it.** No connected lifetime ever ran past about
15 minutes. Every session ended at 900 s of uptime, and the coming soak is
an hour, under the bound (about 40000 packets).

**Evidence.** One connected run past 2.5 hours, in its own session,
predeclared in
[§70.3](HIF_TRANSPORT_ANALYSIS.md#703-the-0335-boot-one-connected-lifetime-past-25-hours-predeclared).
It passes if there is no packet-budget failure and the ledger is intact at
the end.

Tested so far:
- The re-arm gate's host test, updated. It already failed on the current
  tree, since the two-lifetime cap and the PID wrap it asserted were
  removed by later patches.
- A W=1 build of the driver, and checkpatch.
- The lifecycle profile's Buildbox build at `f2a97fb1`.

Not tested: any device run.

**Device result (2026-10-31, station 9):** both blockers are closed.
- With 0334 and its fix 0352, 25 reconnects in a row passed: 26 lifetimes
  on one firmware start.
- With 0335, one connected lifetime ran 2.79 h with 307 reason-4 notices
  consumed and no loss
  ([station record](../2026-10-30-mainline-dev-station/README.md#observations)).

## Open, in order

Two of these hit the owner at home every day:
- the six-minute loss, with or without traffic (fixed by 0337);
- the group-key rekey, hourly if the access point rekeys.

The single channel only matters when joining a different network.

1. **The six-minute loss (fixed by 0337).** The firmware reports a
   reason-4 BSS timeout about six minutes after the join, whether or not
   there is traffic. Before 0337 the driver ended the connection on it.
   - **It is not inactivity.** In the soak, a ping every 10 s was
     answered throughout, and the last unicast frame each way was under
     a second before the loss at 361 s
     ([§70.5](HIF_TRANSPORT_ANALYSIS.md#705-soak-result-2026-10-29-the-link-was-lost-at-361-s-under-traffic-nothing-measured)).
     Lifecycle boot 10, with no traffic, was lost at 367 s. So a
     keep-alive is not the fix.
   - **It was the driver's choice.** The firmware's event is a notice
     to the host. The vendor driver ignores it when a packet reached the
     host within 2 s, which held for all seven reason-4 events we have.
     0337 applies that rule to reason 4. On the soak rerun the notice came
     at 361 s and repeated, 97 times in all, each on a fresh clock;
     the link carried 45 minutes of traffic and 15 idle without a loss
     ([§71.3](HIF_TRANSPORT_ANALYSIS.md#713-soak-rerun-result-2026-10-30-the-link-held-the-hour-the-notice-repeats-and-is-benign)).
     0337 is in the daily-use set. Open: what reason 4 means, and a
     daily-length run with idle stretches.
2. **Group-key rekey.** A rekey's first message arrives PTK-protected with
   the EAPOL type, and today it is dropped:
   - the CCMP receive classifier excludes that type;
   - the clear-EAPOL path admits only two frames per lifetime;
   - the data transmit descriptor refuses EAPOL;
   - the driver refuses a second group key.

   The expected outcome is that the access point deauthenticates the
   station after its retries, and the station reconnects (with 0334,
   without a limit). That is a disconnect per rekey interval, not support.

   Support needs:
   - protected EAPOL receive, PN-checked;
   - protected EAPOL transmit;
   - a second group key installed under a new index while the old one is
     still current;
   - removal of the old key without closing the receive path.

   Two questions are open before implementation. The pinned public gen3
   key path can answer both offline:
   - Which firmware WLAN index a new group-key index lands in. The receive
     path assumes one broadcast WLAN index.
   - What the firmware's key command needs beyond the index.

   After that, one boot against an access point that rekeys on a short
   interval.
3. **Channel and band reach.** Scan, join and every receive status are
   pinned to channel 40 (5200 MHz), the owner's access point, so the
   station cannot join elsewhere. A multi-channel scan and a per-join
   channel need two things:
   - the descriptor's channel field read rather than compared with 40;
   - a 2.4 GHz join tested.
4. **A clean profile.** The lifecycle profile carries the measurement
   surface: test schedule, records and debugfs. Daily use wants the same
   station path without them. That is the roadmap's one CONSYS/WMT owner,
   one WLAN driver and one profile.

**Not blocking.** The channel token and the station sequence still refuse
at 255. Neither moves per lifetime today (boot AV's log), so the bound is
not reached in practice. PTK rekey, roaming between access points, power
saving and transmit aggregation are later work. None of them blocks a day
on the owner's access point.
