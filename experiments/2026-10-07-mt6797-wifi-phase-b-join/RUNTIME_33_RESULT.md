# Runtime 33 result — C2/C3 two-lifetime re-arm on candidate 32

One bounded run on candidate 32 (mainline boot `626e02e3-2c12-4cfa-9055-858dbd563ee6`,
`7.1.3-gemini-a53-wifi-phase-b-compile` aarch64), from the pinned 7b2 tools, with the
reviewed evidence / regression / recovery. Sanitized from the custodian's handoff (no
PSK, AP identifiers, addresses, personal paths or raw captures). Overall
**two_lifetime_pass = false**: cycle 1 healthy, cycle 2's second scan refused early.

## Outcome

- Regression **PASS**, kernel log complete, 52 pre-recovery files verified; one reviewed
  recovery to fresh Gemian `c0534bf5-7403-4061-bf3c-e42c2eb794a4` (3.18.41+); helper group
  quiesced (owned, safe, group_quiescent); no retry.
- **Cycle 1 healthy:** one scan (status 0, one frame, one beacon, ~526 ms dwell),
  association/keys, data phase 6132 ms (RX 34 unicast / 31 group, TX 27 status-0 / 0
  failures / 58 credits), healthy stage-3 cleanup, one re-arm. Fresh **Wi-Fi SSH exit 0**,
  boot match, host_ack written; helper elapsed 5.4 s.
- **Cycle 2 failed:** second scan admitted, refused ~26 ms later; no auth/association, no
  data phase, no ready marker; SSH not attempted; helper poll expired at 90 s.

## Second-scan diagnosis (from source + the kmsg)

The kmsg records the cause (scan-event-metadata, custodian SHA
`883d8e1ece628110a35e8657ce675293cd9d803fafcd224bce15f9b68071546b`):

```
182024934  scan admitted (cycle 1)
182546517  firmware scan count version=3 management=12 pno=0
182550812  scan status=0 complete=1 frame=1 beacon=1 credit=1 retired=1   (cycle 1 OK)
189457687  join rearm lifetime=1 token=2 sta_seq=25 sequence=32            (healthy)
189779634  scan admitted (cycle 2)
189801285  unknown event: len=12 id=0x11 seq=0                             (the cause)
189805431  scan status=-71 complete=0 frame=0 beacon=0 credit=1 retired=1  (EPROTO)
194837380  passive submission stopped status=-95
```

The firmware emitted **event id 0x11 — EVENT_ID_BSS_ABSENCE_PRESENCE** (12 bytes,
unsolicited seq 0; grounded in the event definition / que_mgt.h and the existing join
event parser `mt6797_join_event(.., 0x11, 4)`, not the like-numbered command
`MT6797_NORMAL_BSS_ACTIVE` — command and event ids are separate namespaces). It is an
asynchronous notification about the BSS cycle 1 associated with. The scan event handler
had no case for id 0x11, so it hit the default unknown-event refusal and returned
`-EPROTO`; the submission then stopped with `-95`. The 0x11 **body fields were not
recorded**, so nothing is claimed about absent vs present / fresh vs stale. This is an
early second-scan event refusal, **not** an association timeout, and (no refused packet
header otherwise) not a demonstrated stale BSS/key cause.

The first scan's firmware tuning summary was 4/4 pending 0; the second's was also 4/4 with
no new samples — so the completion gate's tuning balance was not the trigger this run, but
the tuning counters are not reset per scan in the source (they carry across lifetimes while
the gate requires balance), a latent gate fragility.

## Fixes

- **Scan handler (proposals 0182 + 0183, C2/C3 base):** 0182 is a narrow, source-grounded
  logged tested-predicate discard of the 0x11 owned-BSS absence/presence notification during a
  later lifetime's scan — shape
  validated against the same event the join parser admits, discarded with no credit/state/
  ownership inference and no interpretation of absent/present; the body is logged before the
  accept/refuse decision so a refused known event is visible; any other shape stays `-EPROTO`
  and the default refusal is unchanged (not a blanket bypass). 0183 resets the
  SCAN_TUNING_SAMPLE counters per scan. In the phase-b profile series for a
  future runtime 34 re-run; **not** in the native-delivery package (that diagnostic is one
  lifetime and never reaches a later-scan 0x11, so its validated package d104 is unchanged).
- **Evidence exporter (repo commit 13141cc3):** the two-cycle exporter lost the per-cycle RAM
  evidence because `cycles_export_script` returned str while the invoke contract requires
  bytes (empty command.sh, TypeError before capture). Fixed to bytes, the test corrected to
  the right contract, and the cleanup failure path hardened. **The cycle-specific RAM archive
  was lost on this run** because of that bug, and the supplicant-log export was partial (27021
  bytes, boot match, but one supplicant process remained so completeness was false); the
  unique kernel log and regression evidence were preserved before recovery.

## Boundary

Cycle 1 is one healthy maintained-join lifetime with a real Wi-Fi SSH exchange; it is **not**
full-driver completion (ordinary WPA2/DHCP/ping/sustained SSH, IRQ/DMA, stop/unbind/restart).
Cycle 2's refusal is a single, now-diagnosed event-handling gap; a re-run requires the 0182
image, not an unchanged-image retry.
