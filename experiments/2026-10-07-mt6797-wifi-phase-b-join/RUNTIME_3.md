# Third Phase B runtime: scan demonstrated, join refused before any frame

Boot identity: mainline `2cd8d3d1-5fdd-4cf5-8015-9aae155bfd2b` from candidate
2 (boot2 `03a6d78c…`, receipt `f19dffdb…`, package `47addc13…`), host
revision `05aa8e4b`, returned to a changed-ID Gemian boot
`1b7e766a-ab22-47ec-a0a5-6b3efe7bc34d` through the reviewed native recovery.
Sanitized records: [results/runtime-3.json](results/runtime-3.json) and the
laptop's combined [results/runtime-3-session-result.json](results/runtime-3-session-result.json).
Raw capture, session, AP input and calibration bytes stay private on the
laptop; the sealed log is 151009 bytes, SHA-256 `97279e39…`, manifest
`6807d77b…`.

## Observations

- Common init completed 285/285 with result 0 again, with a calibration ack,
  PA rails off and the firmware not stopped. Readiness markers were unique and
  the wiphy probe registered one phy, index 0, bound.
- The corrected script passed every prerequisite: no stage marker was printed.
  The passive scan was admitted once, the done header matched, the scan
  reported status 0 with one frame, one beacon, credit returned and the wire
  retired; the host saw a standard BSS on 5200 MHz, the owner's BSS matched,
  and `channel40_ir_after_beacon=1` appeared, so the found beacon lifted NO-IR
  as the regulatory inference in [RUNTIME_2.md](RUNTIME_2.md) expected.
- `iw dev wlan0 connect` returned `command failed: Operation not supported
  (-95)` synchronously, exit 161. The driver printed one footer at
  58.28 s: `one-shot WLAN join stopped: status=-110 first=0 submitted=0x0
  debt=0 cleanup=0`. The log holds zero management TX, RX, acknowledgement or
  submission records. The script saw that terminal footer and exited 0.
- The inherited scan classifier reported `standard_scan_succeeded=false` and
  `passive_scan_demonstrated=false` only because the connect's error text was
  on stderr; every scan-specific flag passed. The combined result is
  `session_verified=true`, `bounded_join_pass=false`. A53 regression passed,
  the log was complete, recovery was confirmed.

## Control path, verified against the selected sources

The laptop's hypothesis was that `iw connect` is unsupported because mac80211
exposes authenticate and associate rather than connect. In the selected tree
mac80211 registers `.auth`, `.assoc`, `.deauth` and `.disassoc`
(`net/mac80211/cfg.c`) and no `.connect`; `cfg80211_connect`
(`net/wireless/sme.c`) then runs cfg80211's own station management entity,
which requires exactly those operations, resolves the default automatic
authentication type to open system, and calls `cfg80211_mlme_auth`
synchronously when the BSS is already in the scan results. So the connect
command is supported, and an explicit `iw auth` followed by `iw assoc` would
enter the same `ieee80211_mgd_auth` path. The script therefore keeps the
single connect; no control-path change is justified by the evidence.

In `ieee80211_prep_connection` (`net/mac80211/mlme.c`) mac80211 derives the
peer's supported and basic rates from the BSS, copies the beacon interval,
prepares the channel through the driver's `.config` (legacy 20 MHz, because
the driver advertises no HT), notifies the driver of BSSID, basic rates and
beacon interval, and only then inserts the station, which calls the driver's
`sta_state` for the NOTEXIST to NONE transition. Nothing on that path returns
-95 for an open legacy join except the driver itself.

## Diagnosis (inference; the refused condition was not measured)

The driver's `mt6797_mac_join_add_peer` refuses with -EOPNOTSUPP, without
setting a first error, when any of nineteen preconditions fails: scan state,
interface and MLO identity, started and configured state, active BSS, running
join, valid BSS and channel bindings, the one-peer reservation, retirement,
debt, the 10 s join deadline measured from scan completion, the command
sequence budget, HIF idleness, the BSSID match and the legacy rate rule. That
early refusal matches every observation: a synchronous -95 to userspace, no
first error, nothing submitted, and the worker stopping at its deadline about
10 s after the scan. Which condition refused cannot be read from the sealed
evidence; the candidates that depend on runtime state are the channel binding
(the exact chandef `.config` saw), the BSS binding, HIF idleness and the rate
rule. The driver footer's timing is consistent with the connect having been
issued within the deadline, but that is not measured either.

## Correction and the measurement that decides

Proposal 0143 evaluates every precondition into a bitmask and prints, once
per MAC lifetime, `one-shot WLAN join peer refused: reasons=0x… supported=0x…
basic=0x… sequence=…`, and prints once the first rejected 5 GHz chandef
(`one-shot WLAN join channel refused: hw=… center=… width=… freq1=… freq2=…
flags=0x… config=…`). Bits: 0 scan active, 1 scan not ready, 2 foreign
interface, 3 MLO, 4 not started, 5 not configured, 6 BSS inactive, 7 join not
running, 8 BSS binding invalid, 9 channel binding invalid, 10 peer already
used, 11 retired or closing, 12 first error, 13 page debt, 14 deadline passed,
15 sequence budget, 16 HIF busy, 17 BSSID mismatch, 18 rate rule. Behaviour,
return values and the one-peer reservation are unchanged;
[tests/join-peer-test.c](tests/join-peer-test.c) asserts the exact bits for a
second peer with a foreign address, for a busy HIF, and that the line is
printed once. The script change is to framing only: the connect's diagnostics
now go into the framed stdout body so the inherited scan classifier no longer
reads a refused join as a failed scan.

The next boot needs a compile-8 candidate with 0143 and is justified by that
measurement alone: the reasons word names the refused condition on the first
attempt without any retry of the join.
