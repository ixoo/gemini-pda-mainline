# Ninth Phase B runtime: the RSN-bearing request stopped at the admission predicate

Boot identity: mainline `91d109d5-3770-47b4-bfff-dac791376408` from candidate
8 (boot2 `1eed3948…`, receipt `6d5183ec…`, compile-13 package `07caf6b5…`,
input `8efe639e`), laptop session source `b625a864`, returned to a changed-ID
Gemian boot `61bf9a0c-d181-48ff-af1e-775aa32ec34e` through the reviewed native
recovery, independently verified over the LAN. Sanitized records:
[results/runtime-9.json](results/runtime-9.json) and the laptop's combined,
unchanged [results/runtime-9-session-result.json](results/runtime-9-session-result.json).
The sealed log is 150823 bytes, 2004 records, SHA-256 `dcde9306…`, manifest
`04854e3a…`. Raw evidence and the AP identity stay private.

## Observations (measured)

- Initialization 285/285 with status 0, PA rails off, no BT H1 record. One
  500 ms channel-40 passive scan succeeded (host elapsed 533274 µs, firmware
  management count 15); the owner's BSS matched; NO-IR lifted after the beacon.
- The Phase C1 connect request (WPA2-PSK CCMP parameters and the fixed RSN
  element) was acknowledged with errno 0 and the helper exited 0.
- Authentication: TX PID 1, one page, TX done status 0, response status 0,
  mac80211 `authenticated`.
- mac80211 logged `associate with … (try 1/3)`; 12 ms later the driver logged
  `join stopped: status=-22 first=0 submitted=0x800 debt=0 cleanup=0 branch=3`.
  No association TX record, no TX done, no response, no activation, no EAPOL
  observation, no deauthentication and no cleanup submission followed; the
  only submitted subtype was authentication (`0x800`). mac80211's `try 2/3`
  came 1.1 s later, after the lifetime had ended; no second host submission.
- Classifier: `terminal_failure_recorded=true`, `host_management_submissions=1`,
  `unique_tx_acknowledgements=true`, `refusal_recorded=false` (no refusal
  record exists for this branch at the booted revision), `bounded_join_pass=false`.
  A53 regression passed and the reviewed recovery passed.

## Cause (source-derived; the boot carries no predicate-specific record)

Branch 3 is the worker's submission step; its `-EINVAL` covers five
conditions: linearization, the frame admission predicate
`mt6797_mac_join_frame`, the PID budget, the channel grant and the grant
margin. The source proves that the C1 request fails the old predicate
deterministically: at the booted revision it refuses any association request
that carries an RSN element (`WLAN_EID_RSN`), with the comment "No RSN, HT/VHT
or fast-transition negotiation in this admission"; the C1 helper adds the RSN
element to the connect request by construction, and mac80211 copies the
request's elements into the association request (`ieee80211_send_assoc`, the
before-HT element order). Runtime 8's request, identical except for the absent
RSN element, passed this predicate and was transmitted, and the driver
declares one hardware queue and no HT or VHT capability, so the RSN element is
the only new element on this path. The other conditions are not observed by
this boot: the PID budget (PID 2 of 127), the channel grant and its margin
(12 ms after a successful authentication under the same 9 s grant) are
strongly supported by the surrounding records, while linearization has no
record at all. The booted revision logs nothing for any of the five
conditions, so the boot does not single out the predicate by measurement;
the source does. Proposal 0149 adds a one-line element record to the
predicate so that this branch is no longer silent.

## Fix: proposal 0149

The predicate admits exactly one RSN element whose 20-byte body is the fixed
WPA2-PSK CCMP shape the reviewed helper sends (version 1, group CCMP, one
pairwise CCMP, one AKM PSK, capabilities 0); a second RSN element, any other
body, or the still-excluded HT, VHT, mobility-domain, fast-transition and WMM
elements are refused as before, now with one `frame element refused:
subtype=… id=… len=… count=…` record. Nothing else changes: peer, channel,
credit, deadline and the single-submission bounds are untouched, and an
RSN-free request (the runtime-8 shape) is still admitted. The ownership
fixture builds the association request as mac80211 does for this connect and
checks the admitted and the refused shapes; the runner checks that the helper's
RSN constant and the driver's expected body are the same bytes.

## What this demonstrates, and its limits

Nothing new about the AP or the firmware: the Phase C1 hypothesis was not
tested because the request never left the host. The RF scope stayed one
passive scan and one authentication exchange. Wi-Fi remains incomplete.
