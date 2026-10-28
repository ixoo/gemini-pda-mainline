# Wi-Fi for daily use — the driver's gaps

Scope record, 2026-10-28. Written from a source read of the lifecycle
tree (0333) while device boots were unavailable. Nothing here was booted.
Each item is its own reviewable change; the ones that need the device get
their own predeclared boot.

Daily use here means: the station stays associated for a working day on
the owner's access point, reconnects by itself whenever the link drops,
survives the access point's key schedule, and carries ordinary traffic,
idle or busy. The demonstrated base is in
[HARDWARE_SUPPORT](../../docs/HARDWARE_SUPPORT.md) and the
[lifecycle result](LIFECYCLE_RESULT.md): repeated WPA2-PSK lifetimes on one
boot, reconnection after the access point's own loss, and the
[boot AV](THROUGHPUT_SERIES_RESULT.md#rate-control-against-the-fixed-rate-2026-10-27-boot-av)
throughput.

## Found and changed (source and host tests only)

1. **The driver died after the eleventh connection.** Every firmware
   command takes a single-use sequence number, and none was ever released.
   One lifetime uses 22 (boot AV's log: lifetime 1 starts at 10, each
   re-arm adds 22), so the re-arm gate met its exhausted-sequence refusal
   after lifetime 11 and poisoned the driver until reboot. An idle link is
   lost after about six minutes, so that was about an hour of idle use.
   Proposal 0334 recycles the sequences at the quiescent re-arm barrier.
   Join completions are matched by credit and channel token, never by
   command sequence. Lifetimes 1–9 are unchanged.
2. **A connected lifetime failed after about two hours.** It failed once
   it read 65536 HIF packets, and beacons and group frames alone arrive at
   about 8–11 a second. Proposal 0335 makes that a count, not a fence,
   for the connected lifetime only. The diagnostic counts already
   saturate rather than stop.

Tested: the re-arm gate's host test (updated: it already failed on the
current tree, since the two-lifetime cap and the PID wrap it asserted were
removed by later patches), a W=1 build of the driver and checkpatch. Not
tested: a build of the profile on Buildbox and any device run.

## Open, in order

1. **Group-key rekey.** A rekey's first message arrives PTK-protected with
   the EAPOL type. The CCMP receive classifier excludes that type and the
   clear-EAPOL path admits two frames per lifetime, so the message is
   dropped. The data transmit descriptor refuses EAPOL as well, and the
   driver refuses a second group key. The expected outcome is that the
   access point deauthenticates the station after its retries, and the
   station reconnects (now without a limit). That is a disconnect per
   rekey interval, not support. Support needs:
   - protected EAPOL receive, PN-checked;
   - protected EAPOL transmit;
   - a second group key installed under a new index while the old one is
     still current;
   - removal of the old key without closing the receive path.

   Two questions are open before implementation:
   - Which firmware entry a new group key index lands in. The receive path
     assumes one broadcast WLAN index.
   - Whether the firmware's key command needs anything beyond the index.

   Read the pinned public gen3 key path first. Then make one boot against
   an access point that rekeys on a short interval.
2. **Idle loss at about six minutes.** The access point disassociates an
   idle station with reason 4 (inactivity), while light periodic traffic
   holds the link. The cause is not identified: an unanswered keep-alive
   poll from the access point, or the firmware's power-save state, are the
   candidates. The [soak](HIF_TRANSPORT_ANALYSIS.md#69-the-soak-one-hour-on-avs-kernel-predeclared-2026-10-28) measures the idle end
   once more. Reconnection makes this a drop, not a failure.
3. **One channel.** Scan, join and every receive status are pinned to
   channel 40 (5200 MHz), the owner's access point. Elsewhere the station
   cannot join. A multi-channel scan and a per-join channel need the
   descriptor's channel field read rather than compared with 40, and need
   a 2.4 GHz join tested.
4. **The remaining per-boot identities.** The channel token and the
   station sequence still refuse at 255. Neither moves per lifetime today
   (boot AV's log), so this bound is not reached in practice.
5. **A clean profile.** The lifecycle profile carries the measurement
   surface (test schedule, records, debugfs). Daily use wants the same
   station path without them. That is the roadmap's one CONSYS/WMT owner,
   one WLAN driver and one profile.

PTK rekey, roaming between access points, power saving and transmit
aggregation are later work. None of them blocks a day on the owner's
access point.
