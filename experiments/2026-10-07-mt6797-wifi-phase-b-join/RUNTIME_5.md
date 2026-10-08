# Fifth Phase B runtime: the privacy-flagged connect is refused with EINVAL

Boot identity: mainline `8f9d400a-828d-4624-9d12-a1ac43b6b8a7` from candidate
4 (boot2 `eeb2ce9b…`, receipt `0d8bf089…`, compile-9 package `bb1659e0…`,
input `68e3a3c8`, helper `b3851a4b…`), laptop session source `238cb255`,
returned to a changed-ID Gemian boot `41113925-3f02-41e3-af9c-6e5225bb1a32`
through the reviewed native recovery. Sanitized records:
[results/runtime-5.json](results/runtime-5.json) and the laptop's combined
[results/runtime-5-session-result.json](results/runtime-5-session-result.json).
The sealed log is 148616 bytes, 1988 records, SHA-256 `8d27aa49…`, manifest
`a66315d1…`. Raw evidence and the AP identity stay private.

## Observations

- Initialization completed 285/285 with result 0, a calibration ack, PA rails
  off; one passive scan passed, the owner's BSS matched, and
  `channel40_ir_after_beacon=1` appeared.
- The helper's framed body reads `connect_request=refused errno=22`, exit 3:
  the kernel acknowledged the sequence-2 connect request itself with EINVAL.
  This differs from runtimes 3 and 4 (EOPNOTSUPP from the refused directed
  scan): the privacy flag made cfg80211's station management entity find the
  protected BSS, and the request then failed further along.
- The driver printed only `one-shot WLAN join stopped: status=-110 first=0
  submitted=0x0 debt=0 cleanup=0`; no `peer refused` or `channel refused`
  line. Those diagnostics log refusals only, so their absence excludes a
  logged driver refusal and nothing more.
- Zero management records; A53 regression passed, the log was complete,
  recovery was confirmed; `session_verified=true`, `bounded_join_pass=false`.

## Source review of the EINVAL path (selected tree)

With the privacy flag set, `cfg80211_sme_connect` finds the BSS and calls
`cfg80211_mlme_auth` synchronously, which calls mac80211's
`ieee80211_mgd_auth`. The EINVAL returns remaining on that path for an
open-system, legacy, non-MLO request on channel 40 are:

- `nl80211_connect` and `cfg80211_connect`: only for attributes this request
  does not carry (RRM, BSS selection, FILS, external authentication, HT or
  VHT capability masks, keys) or for an unknown or disabled frequency; 5200 MHz
  is present and enabled.
- `cfg80211_mlme_auth`: only for a link ID without MLO support, shared-key
  parameters, or a BSSID equal to our own address.
- `ieee80211_mgd_auth`: a channel switch in progress at the AP.
- `ieee80211_prep_connection` through `ieee80211_mgd_setup_link_sta`: no
  legacy rate of the AP matches the station's band rates, logged as
  `wlan0: No legacy rates in association response`.
- `ieee80211_determine_chan_mode`, reached from `ieee80211_prep_channel`:
  the AP's basic rates carry a BSS membership selector the station does not
  support, logged as `wlan0: required basic rate or BSS membership selectors
  not supported or disabled, rejecting connection`; or the operating channel
  is unusable even at 20 MHz, logged as `wlan0: unusable channel (5200 MHz)
  for connection`.

Two facts narrow this. First, a connect request carries no supported
selectors: `NL80211_ATTR_SUPPORTED_SELECTORS` is read only by the explicit
authenticate and associate requests, so mac80211 assumes only the SAE-H2E
selector for a connect and adds the HT, VHT, HE and EHT PHY selectors solely
from the connection mode. Second, this driver advertises no HT capability, so
the connection mode is legacy and no PHY selector is added. An AP whose basic
rate set includes an HT, VHT or HE PHY membership selector is therefore
rejected at the selector check with EINVAL, before `ieee80211_prep_channel`
asks for the channel and before the station insert, which matches the absent
0143 lines. Whether the owner's AP advertises such a selector is not yet
known: it is visible in the retained scan output's supported-rates lines.

Every candidate site above prints a `wlan0:` kernel message that the join
filter does not match. Those lines, requested from the retained sealed log,
identify the site exactly without any device action. Until they are read the
cause remains a source-review inference.

## Next

If the selector rejection is confirmed, the fix is host-side: the station
must either declare the selector (only the explicit authenticate and associate
requests accept supported selectors) or the exchange must use those explicit
requests. Either is a protocol change for the owner to approve; no driver
change is indicated by this result and no kernel build is needed for it.
