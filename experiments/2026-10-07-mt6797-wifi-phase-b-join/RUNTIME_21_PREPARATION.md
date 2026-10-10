# Runtime 21 preparation: one boot for handshake, data and teardown (proposals 0164 to 0167)

Status: protocol stated before any build or boot; the compile, candidate and
deployment bindings follow their receipts. The custodian reviews this
protocol and every device step; the custodian remains the sole device
custodian.

## What differs from runtime 20

Runtime 20 ended one second after the group key's credit with a refused
second add-key-done event. This boot carries proposals 0163 to 0167 on top of
compile 24's series: both add-key-done windows admitted and required, the
group key under the station's declared broadcast WLAN index 2 with the
supplicant-path removal shapes, the channel privilege released after the
group key, one bounded data phase with protected data in both directions on
the legacy non-QoS association, and the teardown after it. The
association, the EAPOL path and the key commands are otherwise runtime 20's.

## Hypothesis, unique measurement and branches

Hypothesis: with the group key under the declared broadcast entry and the
channel released, the firmware accepts the two key commands with one
add-key-done event each, the station exchanges protected data with the AP
for up to 60 s, busybox `udhcpc` obtains a lease and `ping` to the gateway is
answered, and the reserved deauthentication and teardown complete.

Unique measurements, all from the sanitized driver records and the session's
fixed fields: the two key-done records, `channel released`, `data phase`,
the first `data TX` and `data RX` records, the `data phase end` record with
its reason and counts, the data-phase userspace outcomes (lease obtained,
prefix length, ping replies received; no address printed), the removals and
the three-stage teardown with stage 1 released.

Branches, each ending the lifetime exactly once:

1. Both keys credited, channel released, data phase opened, `udhcpc` bound,
   ping answered, the phase ended by the supplicant's disconnect (the script
   stops the supplicant after its checks) or by the 60 s budget, healthy
   teardown: the handshake and data-path passes and the network outcomes are
   recorded separately.
2. Data phase opened but no lease or no ping reply within their bounds: the
   driver counts stand as firmware-boundary evidence; the network outcome is
   recorded as failed; no retry.
3. The second add-key-done event refused, the channel release refused, a data
   credit overflow, an aggregated or QoS frame, an unknown event or any other
   named refusal: fail-stop as before, seal, reviewed recovery.
4. Eight unacknowledged data frames in a row: the phase ends with reason
   `txfail`; the teardown runs; not a pass.

No branch repeats a boot without a decision-changing change. Nothing is
reconnected or rekeyed.

## Finite limits

| Stage | Limit |
| --- | --- |
| Passive scan | one 500 ms dwell on channel 40, as before |
| Join lifetime | 10 s from the scan hand-off until the data phase opens; 9 s channel grant |
| Data phase | 60 s after the group key's credit, or until disconnect or fault |
| Teardown margin | 5 s added to the lifetime deadline when the data phase opens |
| Poller | 20 ms period, at most 4096 polls and 32768 packets per lifetime |
| Receive delivery | at most 16384 data frames; more dropped and counted |
| Transmit queue | 8 frames or 12400 bytes queued; one frame in flight; 8 unacknowledged in a row end the phase |
| TC4 pool | 26 pages (unchanged); TC1 pool 16 pages, both declared host budgets |
| Session join phase | the device script waits at most 100 ticks of 1 s for the terminal record; `udhcpc` at most 4 tries of 3 s; `ping` 3 requests, 2 s each, 8 s overall |
| Host phase budget | the passive-scan phase budget rises from 45 s to 130 s; the supplicant-log export stays 20 s |

## Evidence and claims

The sealed kernel log's `one-shot WLAN join` records classified by
`classify-join.py`; the session's fixed fields and phrase counts; the private
supplicant log exported and digested. `driver_handshake_path_pass` and
`driver_data_path_pass` describe the driver's bounded behaviour at the
firmware boundary; `wifi_operational` stays false; a lease and ping replies
are the only network-function evidence and are reported as such. No
installed-key, replay-protection or throughput claim follows.

## Device protocol

One boot of the composed candidate, the reviewed session (`passive-host.py`
with the C2 pieces and the data-phase fields), the bound private script with
the PSK, the owner's physical boot2 handoff, the custodian's recovery through
the reviewed path after the sealed log is preserved. No device access from
Buildbox at any point.
