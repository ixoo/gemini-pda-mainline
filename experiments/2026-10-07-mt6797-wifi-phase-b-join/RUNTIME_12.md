# Twelfth Phase B runtime: Phase C1 passed

Boot identity: mainline `46f8e96e-0220-41a6-a297-c268e08ba66e` from candidate
11 (boot2 `1c491341…`, receipt `08764467…`, compile-16 package `642165d4…`,
input `707e2d71`), laptop session source `1853ce20`, returned to a changed-ID
Gemian boot `2999c7b7-431c-4c8a-980e-df93e8104220` through the reviewed native
recovery, independently verified over the LAN. Sanitized records:
[results/runtime-12.json](results/runtime-12.json) and the laptop's combined,
unchanged [results/runtime-12-session-result.json](results/runtime-12-session-result.json).
The sealed log is 153162 bytes, 2021 records, SHA-256 `f2ba8cbb…`, manifest
`61015310…`. Raw evidence and the AP identity stay private.

## Observations (measured)

- Initialization 285/285, calibration acknowledged, PA rails off, no BT H1
  record, prerequisites in order. One 500 ms channel-40 passive scan succeeded
  (host elapsed 516901 µs, firmware management count 15); the owner's BSS
  matched; NO-IR lifted after the beacon. The sampled tuning is consistent but
  is not atomic RF proof. Connect acknowledged with errno 0, helper exit 0.
- Authentication: TX PID 1, one page, TX done status 0, response status 0,
  mac80211 `authenticated`. Association: TX PID 2, one page, TX done status
  0, response status 0.
- `eapol observed: translated=1 frame=99 activated=0 vector=0 bss=15`: one
  clear frame from the target to this station on channel 40 in the translated
  Ethernet layout, without an RX vector, BSSID tag 15, received after the
  accepted association response and before the local activation, carrying
  99 bytes after the Ethernet header that the 0140 decoder accepts as complete
  EAPOL-Key framing. It was dropped; nothing was delivered or answered.
- mac80211 then processed the response (`RX AssocResp … status=0 aid=9`), the
  BSS and station configuration returned one and two pages, the activation
  arrived (`sequence=24 state=3`) and mac80211 logged `associated`.
- The driver's deauthentication, released by the observation: TX PID 3, one
  page, TX done status 0. Cleanup stages 0, 1 and 2 each returned one page,
  one admitted `bss absence: bss=0 absent=0 quota=0 reserved=0`, then
  `cleanup: stage=3 credits=returned slots=retired deauth=1`; mac80211 logged
  the connection loss. Thirteen pages submitted and thirteen returned.
- Classifier: every accepted-path field true (`bounded_join_pass`,
  `healthy_cleanup_demonstrated`, `stage_and_credit_order_verified`,
  `associated_station_activation_demonstrated`, `management_exchange_demonstrated`,
  `unique_tx_acknowledgements`), one EAPOL framing observation, no refusal, no
  terminal failure, no malformed record, `wifi_operational=false`. A53
  regression and the reviewed recovery passed.

## What this demonstrates, and its limits

Phase C1's hypothesis is confirmed: the protected AP accepts this station's
association when the request carries the RSN element, mac80211 completes the
association and the firmware activates the station, and the AP's first frame
after accepting is a clear, translated, vector-less data frame carrying
complete EAPOL-Key framing, which arrives before the stack's association
completes and before the activation. Its BSSID tag is 15 at that moment. The
driver-owned deauthentication and the three-stage teardown then ran healthily.

It is not a validated handshake message: message 1 identity, nonce, replay
counter and MIC were not checked, nothing was delivered to mac80211, nothing
was answered, no key exists, no data frame was sent or received, and the
radio scope stayed one passive scan, two management exchanges and one
deauthentication. The runtime-10 and runtime-11 refusals are now explained by
measurement: the vector-less layout and the BSSID tag, both admitted by
proposals 0151 and 0152. Phase C2, the key exchange, is designed in
[PHASE_C.md](PHASE_C.md) from this evidence.
