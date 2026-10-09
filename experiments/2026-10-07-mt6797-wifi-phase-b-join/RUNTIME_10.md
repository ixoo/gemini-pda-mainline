# Tenth Phase B runtime: the first accepted association, then a refused receive

Boot identity: mainline `084bf978-f3e9-4afe-b4f4-09be8e44cb11` from candidate
9 (boot2 `8d2c87f9…`, receipt `d6857436…`, compile-14 package `3ecfdecb…`,
input `9ce81bc3`), laptop session source `baaac9f5`, returned to a changed-ID
Gemian boot `a51fe04d-b674-4e6a-bcab-567a545f878f` through the reviewed native
recovery, independently verified over the LAN. Sanitized records:
[results/runtime-10.json](results/runtime-10.json) and the laptop's combined,
unchanged [results/runtime-10-session-result.json](results/runtime-10-session-result.json).
The sealed log is 151666 bytes, 2010 records, SHA-256 `449f497b…`, manifest
`a4a9ae02…`. Raw evidence and the AP identity stay private.

## Observations (measured)

- Initialization 285/285 with status 0, calibration acknowledged, PA rails
  off, no BT H1 record. One 500 ms channel-40 passive scan succeeded (host
  elapsed 537375 µs, firmware management count 15); the owner's BSS matched;
  NO-IR lifted after the beacon.
- The Phase C1 connect request was acknowledged with errno 0, helper exit 0.
- Authentication: TX PID 1, one page, TX done status 0 (count 2), response
  status 0, mac80211 `authenticated`.
- Association: TX subtype 0, PID 2, one page, TX done status 0 (count 1),
  response subtype 1 **status 0**. This is the first accepted association of
  the project; proposal 0149 admitted the RSN-bearing request as intended. The
  AP's accepted response was validated and logged by the driver and queued for
  mac80211, but the worker stopped on the next packet in the same tick and the
  queued response was discarded with the lifetime, so mac80211's association
  did not complete (it retried twice against the closed queue).
- Immediately after that response the driver logged `frame refused: bytes=147
  type=0x51af allowed=0x1402` and `join stopped: status=-71 first=0
  submitted=0x801 debt=0 cleanup=0 branch=7`. No activation, no EAPOL
  observation, no deauthentication and no cleanup record followed; mac80211's
  second and third association tries reached the closed queue, two host
  submissions in total. A53 regression passed and the reviewed recovery passed.
- Classifier: `association_response_status=0`, `refusal_recorded=true`,
  `unique_tx_acknowledgements=true`, `host_management_submissions=2`,
  `diagnostic_records=["frame refused"]`, `bounded_join_pass=false`.
  `management_exchange_demonstrated=false` records only that the lifetime
  ended without the deauthentication and teardown the accepted-path grammar
  requires; it does not contradict the accepted association.

## The refused packet: what is measured, derived and inferred

Measured: 147 bytes, RXD type word `0x51af`, permitted management subtype
mask `0x1402`, received as the very next packet after the association
response, refused by the frame gate in the worker's branch 7.

Derived from the type word alone, by the pinned gen3 word-0 layout: packet
type 2 (data), group-valid bits `0x8` (group 4 only, so no groups 1, 2 or 3
and no RX vector), low bits `0x1af` (ethertype-offset field 47, both
checksum bits set). Nothing else about the packet is known: the base header
bytes 4 to 11, the group-4 contents and the payload were not recorded.

Source facts at this revision: the 0140 clear-EAPOL decoder refuses any
packet without RX vector group 3 before it looks at anything else, and so
does the management frame gate; the pinned gen3 receive path locates every
status group from the group-valid bits and treats group 3 as optional
(`nicRxFillRFB`, a null-checked group-3 pointer). A vector-less packet
therefore cannot be observed by the C1 build whatever it is.

Inference, not measured: 16 base + 16 group 4 + 2 header padding + 14
Ethernet + 99 EAPOL-Key bytes is exactly 147, the length of a translated
EAPOL-Key message 1 with an empty key-data field. The packet is not labelled
EAPOL, native or translated by this record; no capture of it exists. The
147-byte, group-4, padding, Ethernet and EAPOL fields that the fixtures build
are hypothetical source-valid cases of that arithmetic, not fields of the
captured packet, which has none.

## Fix for review: proposals 0150 and 0151

- 0150 names the header of any packet the frame gate refuses: RXD base bytes
  4 to 11, the group set, the computed header offset, the group-4 frame
  control, sequence and whether its transmitter is the target, and the first
  wire word after the groups (the Ethernet type of a translated packet, the
  frame control of a native one); lengths and flags only, no address, no
  payload byte. With it, a refused packet is decision-changing metadata.
- 0151 makes RX vector group 3 optional in the clear-EAPOL decoder, as the
  pinned receive path has it, reporting the signal invalid without it; every
  other check (peer, channel, non-QoS non-aggregated clear From-DS frame
  control, layout bounds, complete EAPOL-Key framing) keeps its exact form,
  and the observation record gains a `vector` flag.

Decision branches of the next boot, stated in advance: the packet decodes as
a clear EAPOL-Key frame from the target and is observed (`eapol observed`
with `vector=0`), after which the hold, deauthentication and teardown run as
designed; or it is refused again, now with its header named, and the record
decides the next step without a further repeat; or the AP's behaviour
differs (denial, no packet) and the existing branches apply.

## What this demonstrates, and its limits

The protected AP accepts this station's association when the request carries
the RSN element: management transmit and receive through the accepted
exchange are demonstrated at the driver. mac80211's association and the
firmware station activation were not completed: the accepted response was
discarded with the lifetime before mac80211 processed it, and no activation
was requested. One data-type packet was received from the firmware and
refused unidentified; no data frame was delivered to mac80211, no usable data
exchange or EAPOL identity was established, no EAPOL frame was observed, no
key exists and nothing but the two management frames was transmitted. The
radio scope stayed one passive scan and two management exchanges. Wi-Fi
remains incomplete.
