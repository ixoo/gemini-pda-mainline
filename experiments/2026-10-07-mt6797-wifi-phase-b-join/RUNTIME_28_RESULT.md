# Runtime 28 result: negative lifetime; the first network milestone (lease, ping replies, one SSH exchange), then a local disconnect and an unrecorded end

Boot: mainline `e6f9c3b6-cd84-4161-8d87-60bfde19270d` on candidate 27 (compile 32,
package `e9610ba5…`, built input 5ee1f55f, boot2 `c45503fa…`), session tools at
32482fc4, consumed once by the custodian after deployment 27 (predecessor candidate 26
`e322e068…`, stock boot `57c5ae6e…`). Evidence: the custodian's fourteen sanitized
uploads (join records, body, host-wait and disconnect fields, the audit follow-up, the
host results, the Wi-Fi SSH receipt); kernel log sealed complete (164882 bytes, 2087
records 0 to 2086, SHA-256 `5bb65945…`); supplicant log complete (26880 bytes, SHA-256
`c23f82c2…`, no per-line timestamps). The logger ran 192953 ms; the host wait emitted
its five keepalive ticks and ended normally (join lifecycle none, exit 0). The last
kernel record's timestamp is not the end of coverage. No raw capture, packet content,
address, credential or image is published.

## Observed (kernel records, µs since boot)

- Handshake: auth TX 81878362, auth RX 81904640 (status 0), association TX 81926356,
  association RX 81952690 (status 0), activation 82003378; pairwise key command and
  credit, first add-key-done window; group key command and credit, second window;
  `data phase: budget_ms=6184 teardown_margin_ms=5000 inside_grant=1` at 82145721.
- The 0168 class: eight discards recorded across the lifetime, which demonstrates the
  class as runtime 27 did. 0174's behaviour beyond eight is unmeasured: no ninth
  arrival is recorded (the total record is written at stage 3, which was not reached)
  and no refusal of the class occurred, so nothing is claimed about arrivals beyond
  eight. 0173 observed: four keyed beacons skipped and recorded.
- Data: `data TX: first pid=5 pages=3 bytes=342` at 82322389; `TX done: pid=5
  status=0` at 82323635 (+1246 µs after the submission); first unicast protected data
  frame delivered at 82324912; `data credit: pages=3 debt=0 count=1` at 82346337
  (+23948 µs after the submission). Twenty-eight consecutive completions, PIDs 5 to
  32, all status 0, none failed (a completion is not an acknowledgement or a delivery
  claim). `data phase end: reason=disconnect elapsed_ms=5256 rx_unicast=32 rx_group=22
  rx_dropped=0 tx_queued=28 tx_done=28 tx_failed=0 tx_credits=57` at 87402363.
- Host, separately: `udhcpc` exit 0, lease written, bound, prefix length 24; the
  retained Dropbear's digest matched, started, ready; `ping` 3 sent, 3 received. The
  laptop helper saw the readiness marker after 4.5 s and completed its one SSH exchange:
  exit 0, 37 bytes of output, boot match true, elapsed 5.9 s, bound to this boot. These
  are the first positive network observations of the series. They are not a Wi-Fi
  operational, reliability or replay-protection claim; `wifi_operational` stays false.
- Disconnect: the supplicant's one `CTRL-EVENT-DISCONNECTED` carries reason 4 with
  `locally_generated=1` (line 383 of its log); the driver's data phase ended with
  reason `disconnect` 5256 ms after it opened. The reserved deauthentication was
  dequeued: `TX: subtype=12 pid=33 pages=1` at 87406362 (3999 µs after the phase-end
  record). No further join record followed in the sealed log: no completion, cleanup
  stage, key removal or footer. The only later kernel record is 2086 at 87510973
  (104611 µs after the deauthentication's submission): the one-shot passive scan gate
  refusing a scan
  (status -95, the published 0075 format), matching the supplicant's single
  `State: DISCONNECTED -> SCANNING` (51 lines after the disconnect; no scan started, no
  association attempt, no reconnection). The session script issued no interface,
  disconnect or supplicant action until the wait ended.
- Verdicts as computed (preserved): bounded join false; `malformed_stage_record`
  true; refusal false; terminal failure false; `unique_tx_acknowledgements` false
  (the deauthentication has no completion); handshake and data-path passes false;
  healthy cleanup false; C2 false; C3 false.

## Why the classifier says malformed

Two rules fired, both about the missing end, neither about firmware framing: the keys
were submitted and never removed while no footer exists (a healthy lifetime removes
each key; a fail-stopped one has the footer), and the deauthentication's window has no
end (no completion and no footer). The flag therefore says that the lifetime ended with
no terminal record; it is not evidence of malformed firmware records, and the original
verdict is kept as computed.

## Source audit (the pinned 7.1.3 source and the authoring tree; inference, not hardware proof)

1. The disconnect. The driver declares `REPORTS_TX_ACK_STATUS` and never delivers a
   beacon to mac80211 (the target's clear beacons are consumed by the scan decoder and
   skipped; the keyed variant is skipped by 0173). mac80211 arms its beacon monitor at
   association (`ieee80211_sta_reset_beacon_monitor`, `beacon_loss_count` 7 beacon
   intervals) and nothing re-arms it; on expiry `ieee80211_beacon_connection_loss_work`
   calls `ieee80211_mgd_probe_ap(beacon=true)`, which with ACK-status reporting sends a
   nullfunc (`ieee80211_mgd_probe_ap_send`). That nullfunc (unprotected To-DS data,
   frame control 0x0148) is admitted by neither of the driver's TX gates and is freed
   unsent through `ieee80211_free_txskb`, which reports it dropped and not acknowledged
   (`ieee80211_report_used_skb`, `ieee80211_sta_tx_notify`); mac80211 then retries up
   to `max_nullfunc_tries` (2) and declares the connection lost
   (`ieee80211_sta_connection_lost`, reason 4, `tx=false`, locally generated). A
   unicast frame from the AP during the poll clears `probe_send_count`
   (`ieee80211_sta_reset_conn_monitor`), after which `ieee80211_reset_ap_probe`
   re-arms the beacon monitor; the poll is therefore cancelled while unicast traffic
   flows and succeeds when it idles. This chain fits the observation: the disconnect
   followed the SSH exchange, 5.3 s into the data phase. The driver recorded nothing
   of it because the nullfunc is freed on a path without a record.
2. The end of the lifetime. `ieee80211_sta_connection_lost` disassociates without
   transmitting (no prepare-tx call, no mac80211 deauthentication frame); the first
   driver callback is `sta_state` (downward), which ended the data phase with reason
   `disconnect` and requested the cleanup; the worker dequeued the reserved
   deauthentication 4 ms later. cfg80211 then reports the disconnect and, once every
   interface is idle, restores its regulatory settings (`sme.c disconnect_work` →
   `regulatory_hint_disconnect` → `restore_regulatory_settings` →
   `update_all_wiphy_regulatory` → `reg_call_notifier`). The driver's regulatory
   notifier retired a used lifetime by clearing its running state and setting the
   first error without any record; the worker's next tick then exited at its first
   check without the footer and did not re-arm. The notifier is uninstrumented, so its
   involvement is an inference consistent with the records: the deauthentication's
   completion, the frame-deadline footer (750 ms) and the cleanup stages are all
   absent, the supplicant's reconnect scan was refused 104 ms later, and no other path
   in the source ends a running lifetime without a footer except the close paths
   (interface removal, stop, scan cancellation), none of which the session exercised.
3. The classifier. Its rules were right to refuse a pass; the terminal treatment lacked
   a name for a lifetime that ends after the deauthentication's submission without a
   completion. With a footer there (0175) the window closes at the footer; without one
   the shape stays malformed.

## Proposals

- 0175 (`patches/proposals/0175-…`): the regulatory notifier ends a running lifetime
  through the one terminal path (branch 9, status -ECANCELED) with the footer and frees
  its frames exactly once; an already-ended lifetime is retired as before. The footer
  makes the notifier's involvement observable in the next runtime. No decoder, radio,
  TX or time budget changes.
- 0176 (`patches/proposals/0176-…`): the target's beacons are delivered to mac80211
  after an accepted association, both the clear class the scan decoder already accepts
  (on the join channel, beacon subtype, the target as transmitter and BSSID) and the
  keyed variant 0173 already decodes (the vendor's management path delivers frames
  regardless of the cipher-mismatch flag and drops only ICV errors under MFP), handed
  over as the passive scan hands beacons over (native frame, join channel, RCPI as the
  signal). The decoders are unchanged; the keyed decoder gains an RCPI output. The
  first four deliveries are recorded and the total with its keyed part before the stage
  3 record; the lifetime's 32768-packet budget bounds the class. mac80211's beacon and
  connection monitors are then fed by the beacons themselves; the driver's BSS-change
  handler ignores the beacon-derived change bits (it reacts to BSSID, basic rates and
  beacon interval only), cfg80211 takes its country hint at connect time, not from
  beacons, and no probe or nullfunc is needed.
- Rejected: `IEEE80211_HW_CONNECTION_MONITOR`. The flag declares that the driver owns
  connection health, including keep-alives and probing on beacon loss. This worker owns
  only its own bounds: a 750 ms completion deadline per submission, the data phase's
  budget, the lifetime deadline, the packet and poll budgets, and the stage-3
  `ieee80211_connection_loss` report when the lifetime ends. It sends no keep-alive and
  detects no beacon loss, so a silent AP would end the lifetime by its budget alone. The
  flag would only bypass mac80211's monitor; it is not claimed.
- Deferred, named: mac80211's own transmitted deauthentication during a lifetime (a
  supplicant exit while the data phase runs) reaches the prepare-tx hook's refusal
  path, which sets the first error without a record; the session's supplicant stop
  comes after the lifetime, so it was not exercised here.

## Proposed runtime 29 protocol (bounded, one test)

Candidate 28 from the next compile (0163 to 0176) with candidate 27's RAM root, DT and
config; runtime 28's protocol otherwise unchanged (same wrapper, budgets, wait, helper,
one SSH exchange). Hypothesis: the delivered beacons keep mac80211's monitors satisfied,
no nullfunc poll occurs, the data phase runs to its budget inside the grant and the
driver's own cleanup follows (deauthentication completed, keys removed, the three
recorded cleanup stages 1 to 3, no footer); the lease, ping replies and the SSH exchange are observed again and
reported apart. Unique measurements: the `beacon delivered` records and the total with
its keyed part; the data phase end reason; the completions by PID; the stages; the
network terms. Branches: (1) budget end and healthy cleanup: 0176 observed, the first
healthy C3 lifetime; (2) a disconnect again with a branch-9 footer: the regulatory
notifier's involvement in that boot is observed, and the disconnect's cause is re-read
from the supplicant fields; (3) a disconnect again without any footer: that boot's stop
is unresolved and the other close paths (interface removal, stop, scan cancellation,
the prepare-tx refusal) are the next audit; it does not refute the historical runtime
28 inference, which stays an inference; (4) any named refusal or
fault (a beacon-derived mac80211 change the driver refuses, a fail-stop, a timeout):
fail-stop, seal, native recovery once. No repeat of candidate 27 without this change;
no operational or replay-protection claim.
