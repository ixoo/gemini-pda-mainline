# Sixth Phase B runtime: the first management exchange

Boot identity: mainline `6646bc4a-015c-4410-976e-d2bed86ae4c5` from candidate
5 (boot2 `e6fe0e8d…`, receipt `c7a93e94…`, compile-10 package `7ee0f058…`,
input `00dc3c7a`, helper `b3851a4b…`), laptop session source `d3b678ea`,
returned to a changed-ID Gemian boot `e128be1a-a40b-4d63-a7f4-892a1293c2bf`
through the reviewed native recovery. Sanitized records:
[results/runtime-6.json](results/runtime-6.json) and the laptop's combined
[results/runtime-6-session-result.json](results/runtime-6-session-result.json).
The sealed log is 151868 bytes, 2012 records, SHA-256 `ac8800e3…`, manifest
`fdca1ca5…`. Raw evidence and the AP identity stay private.

This is the first demonstrated management exchange between this driver and
the owner's access point. It is not operational Wi-Fi: no association was
granted, no key was exchanged and no data frame existed.

## Observations (measured)

- Initialization 285/285 with result 0, a calibration ack and PA rails off;
  one passive scan passed; the owner's BSS matched; NO-IR lifted after the
  beacon. The helper's connect request was acknowledged with errno 0.
- Peer setup: filter and channel commands each returned one credit page, the
  channel grant arrived (channel 40, 9000 ms), the station command returned
  two pages, and the peer became ready at command sequence 23.
- Authentication: mac80211 sent one authentication frame; the driver's TX
  record (subtype 11, PID 1, one page) was followed by a credit page, a TX
  done with status 0 and the response (subtype 11, status 0); mac80211 logged
  `authenticated`.
- Association: mac80211 sent one association request (subtype 0, PID 2, one
  page), a credit page and a TX done with status 0 followed, and the response
  carried status 45 with an AID; mac80211 logged `denied association
  (code=45)`. In the selected header, status 45 is
  `WLAN_STATUS_INVALID_RSN_IE_CAP`.
- Cleanup: submissions for stages 0, 1 and 2 each returned one credit page.
  The final cleanup line (stage 3) did not appear; the worker stopped with
  `status=-71 first=0 submitted=0x801 debt=0 cleanup=3`. Nine credit pages
  were logged in total: four for peer setup, two for management, three for
  cleanup, matching the pages submitted.
- Zero host management submissions beyond the two frames; unique TX
  acknowledgements; A53 regression passed; the log was complete; recovery was
  confirmed. The classifier reports `management_exchange_demonstrated=true`
  and, because the stage-3 line is absent, `healthy_cleanup_demonstrated=false`
  and `bounded_join_pass=false`.

## Inference (source review, not measured)

- The association request carried no RSN element by construction: the helper
  sends no information element and no cipher, `nl80211_connect` copies
  elements only from the request, and mac80211 builds the association request's
  elements from what the request supplied. The AP's own reason for status 45 is
  not observable; the status name is the standard's, not a measurement of the
  AP's policy.
- The protocol error's origin is unmeasured. `cleanup=3` is the submission
  counter, not a location: within one worker tick the credit guard's
  reconciliation, the TX-done, control-event and frame parsers, and the cleanup
  step's HIF-idle gate each return EPROTO without a log. The nine returned
  pages match the submissions but do not by themselves establish that the
  HIF's own ledger was idle, since that predicate also requires balanced
  CPU and FFA release counters, recorded sequences, the post-NVRAM phase and
  an unlocked mutex.

## Diagnostic for the next boot (proposal 0146)

No behaviour, budget or retire path changes. The join footer gains
`branch=`, the phase of the tick that stopped the lifetime (1 deadline, 2
guard, 3 TX submission, 4 receive, 5 TX done, 6 control event, 7 frame, 8
cleanup). A refused control event prints its logical length, wire type, event
id and sequence; a refused frame prints its length, wire type and the allowed
mask; no body bytes or addresses. When the cleanup step's idle gate refuses,
a read-only accessor prints the HIF ledger terms (phase, free and limit pages,
pending CPU and FFA counts, sequences recorded, mutex busy) as a snapshot
taken after the failed check, which describes the ledger just after the
refusal rather than proving the failed predicate atomically. A credit
release beyond the outstanding debt is also named. The peer fixture asserts
that the cleanup refusal still returns EPROTO, completes nothing and logs
once, and that the overflow is logged and refused.

## Next

Candidate 6 pairs a compile-11 kernel (0146) with the candidate-4 RAM root
and helper; the radio scope stays one passive scan and one open-system
authenticate-and-associate attempt with no keys and no data. The next boot's
decision-changing observation is the footer's branch and the accompanying
refusal line.

The standing goal remains complete Wi-Fi. Once the cleanup termination is
resolved, the next development stage is the protected association, the key
exchange and the data path, each implemented and reviewed under its own
concrete bounded protocol with the project's tests, as the owner has already
authorized for this driver. Owner input is needed only where it is genuinely
required, such as the private access-point credential and the physical boot.
