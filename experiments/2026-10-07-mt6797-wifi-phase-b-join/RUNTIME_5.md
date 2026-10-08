# Fifth Phase B runtime: the connect is refused for an empty rate record

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

## The rejection site, observed

The laptop read the retained sealed log: the only `wlan0:` record is
`wlan0: No legacy rates in association response`, logged 0.17 s after the
scan completion record and before the join footer. That is mac80211's
`ieee80211_mgd_setup_link_sta`, called from `ieee80211_prep_connection` during
`ieee80211_mgd_auth`, returning -EINVAL when none of the AP's rates matches
the station band's bitrates. The wording is historical: nothing was sent or
received on air (zero management records); the function runs before the
channel is prepared and before the station is inserted, which is consistent
with the absent 0143 lines.

The owner AP's block in the retained scan output lists `Supported rates:
6.0* 9.0 12.0* 18.0 24.0* 36.0 48.0 54.0`, no extended rates and no membership
selector; its capability is ESS, Privacy, spectrum management, short slot time
and radio measurement. The driver registers exactly those eight OFDM rates on
5 GHz. [tests/scan-rates-test.c](tests/scan-rates-test.c) runs mac80211's own
`ieee80211_get_rates`, extracted from the selected tree, over the driver's
registered bitrate table with those rate bytes: all eight match, the basic set
is 6, 12 and 24 Mbit/s, and the minimum-rate index is 0. So the rates are
compatible, and the only way the match is empty is an empty rate record.

## Cause (source, consistent with every observation)

`ieee80211_mgd_setup_link_sta` reads the rates from mac80211's private
per-BSS record (`struct ieee80211_bss`, the cfg80211 entry's private area),
which mac80211 fills only when it receives the beacon itself through
`ieee80211_rx` and `ieee80211_bss_info_update`. The Phase A and Phase B
driver reported each scanned beacon to cfg80211 directly with
`cfg80211_inform_bss_frame_data`, so the cfg80211 entry existed (the scan
dump and the privacy-flagged lookup both found it) while mac80211's record
stayed zeroed. The same fixture reproduces the exact condition with an empty
record: no minimum-rate index, the logged message's test. This also explains
why no earlier runtime could have reached a management frame through the
connect path regardless of the privacy fix.

## Correction

Proposal 0145 queues each validated beacon or probe response as a received
mac80211 frame (band, frequency, dBm signal from RCPI, and a zeroed rate index
that is a placeholder mac80211 requires, not a PHY rate observation) and hands
the queue to mac80211 outside the MAC lock before completing
the hardware scan, so mac80211 creates the cfg80211 entry itself, including
the regulatory beacon hint, and fills its own record. Frames of a failed scan
lifetime are dropped. Scan admission, budgets and radio behaviour are
unchanged. [tests/scan-report-test.c](tests/scan-report-test.c) drives the
production handler with a synthetic beacon through the frame parser and
checks the queued frame's status fields, the probe-response acceptance, and
the refusals of a non-scan frame, a foreign or disabled channel and an
allocation failure. The runner also fails if the handler still informs
cfg80211 directly.

## Next

Candidate 5 pairs a compile-10 kernel (0145) with the candidate-4 RAM root and
helper; no host-side change is needed. The boot's decision-changing
observation is the first management frame: join TX, RX and acknowledgement
records with an authentication or association status, or a new specific
failure.
