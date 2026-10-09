# Eleventh Phase B runtime: the refused packet's header, named

Boot identity: mainline `e2aca773-11b9-42eb-8c16-fa30f98c5da6` from candidate
10 (boot2 `57f9e65c…`, receipt `37fc49ad…`, compile-15 package `efb0b28a…`,
input `89d60283`), laptop session source `b8b00aeb`, returned to a changed-ID
Gemian boot `5c61cd3e-f267-4b28-8dcf-0030f632b057` through the reviewed native
recovery, independently verified over the LAN. Sanitized records:
[results/runtime-11.json](results/runtime-11.json) and the laptop's combined,
unchanged [results/runtime-11-session-result.json](results/runtime-11-session-result.json).
The sealed log is 151176 bytes, 2007 records, SHA-256 `f4494071…`, manifest
`1ff84a18…`. Raw evidence and the AP identity stay private.

## Observations (measured)

- Initialization 285/285, calibration acknowledged, PA rails off, no BT H1
  record. One 500 ms channel-40 passive scan succeeded (host elapsed
  534726 µs, firmware management count 15); the owner's BSS matched; NO-IR
  lifted after the beacon. Connect acknowledged with errno 0, helper exit 0.
- Authentication: TX PID 1, one page, TX done status 0, response status 0.
  Association: TX PID 2, one page, TX done status 0, response **status 0**,
  the second accepted association. As in runtime 10 the accepted response was
  validated and logged by the driver, queued for mac80211 and discarded with
  the lifetime in the same tick; mac80211's association did not complete.
- The next packet was refused with proposal 0150's record: `bytes=147
  type=0x51af allowed=0x1402 hdr=0228ce3c010000c0 groups=0x8 at=34
  g4fc=0x208 g4seq=0x0 g4ta=1 translated=1 first=0x888e`, then `stopped:
  status=-71 … branch=7`. No activation, EAPOL observation, deauthentication
  or cleanup followed; two host submissions in total. A53 regression and the
  reviewed recovery passed.

## What the header establishes, by the pinned gen3 layout

Byte 4 `0x02`: unicast to this station. Byte 5: channel 40. Byte 6 `0xce`:
header translation, header padding, header length 14. Byte 7 `0x3c`: payload
format 0 (an MSDU, not A-MSDU) and BSSID field 15. Byte 8: WLAN index 1, the
station record this driver owns for the AP. Byte 9 `0x00`: TID 0, security
mode 0 (clear). Status `0xc000`. Groups `0x8`: group 4 only, no RX vector.
Group 4: frame control `0x0208` (data, From-DS), sequence 0, transmitter is
the target. The first word after the groups, at offset 34, is the Ethernet
type `0x888e`.

So the packet is a translated Ethernet frame from the target to this station
on the join channel, clear and non-aggregated, carrying the EAPOL Ethernet
type. It is **not** established that it is an EAPOL-Key frame or message 1:
the decoder never reached the body, and no body field is known.

## Which check refused it (source)

The clear-EAPOL decoder at this revision requires byte 7 to be 0 before it
reaches the group and vector stage. Every other base-header check it makes
(match, channel, translation flags and header length, WLAN index 1, TID and
security 0, status `0xc000`) is satisfied by the measured bytes. Proposal
0151's optional-vector relaxation is still in the source and still correct for
this packet's group set, but it was not reached.

The pinned gen3 receive path never reads the RXD BSSID field: the accessor is
defined and unused, and received data is routed by the WLAN index to the
station record and its BSS. Payload format 0 is its MSDU case. The value 15 in
a six-bit field, on a part with four hardware BSS slots, reads as no hardware
BSSID match, consistent with the station not yet being activated; that
reading is inference, the source defines no such sentinel.

## Fix for review: proposal 0152

The decoder requires the MSDU payload format and reports the BSSID field,
admitting only 0 and 15. The worker admits 15 only until the associated BSS
has been configured in the firmware, which precedes the station activation,
and 0 at any point in the window; the observation record gains `bss=`. Every other
bound is unchanged: accepted association, owned WLAN index 1, exact AP, own
address and channel, clear non-QoS non-aggregated From-DS frame control,
complete EAPOL-Key framing, at most two observations, the hold and the
single deauthentication. This is not blanket BSS acceptance and nothing
pretends the station is activated.

Decision branches of the next boot: the packet is observed (`eapol observed
… vector=0 bss=15 activated=0`), then hold, deauthentication and teardown;
or it is refused again with its header named, which decides the next step
without a further repeat of this artifact; or the AP's behaviour differs.

## What this demonstrates, and its limits

Nothing beyond runtime 10 in support terms: the accepted association at the
driver, no mac80211 association, no activation, no EAPOL-Key framing
observed, no key, no data frame delivered, nothing transmitted beyond the two
management frames. What is new is the measured header of the first frame the
AP sends after accepting, which is now sufficient to decide the fix. Wi-Fi
remains incomplete.
