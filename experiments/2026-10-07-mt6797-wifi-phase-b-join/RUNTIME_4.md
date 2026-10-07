# Fourth Phase B runtime: the connect never reaches the driver's join callbacks

Boot identity: mainline `bc5796ca-13a1-47e8-8cfc-5b4dab6ef7ba` from candidate 3
(boot2 `84f65eae…`, receipt `00f6c619…`, compile-8 package `9c5a7300…`, input
`a5951349`), laptop session source `75c850d9` (the later documentation
commit was not pulled during the hardware run), returned to a changed-ID Gemian boot
`7339537d-9f66-4b20-8e9f-69ae4ec37290` through the reviewed native recovery.
Sanitized records: [results/runtime-4.json](results/runtime-4.json) and the
laptop's combined [results/runtime-4-session-result.json](results/runtime-4-session-result.json).
The sealed log is 150996 bytes, SHA-256 `e2a60042…`, manifest `addc6410…`.
Raw evidence and the AP identity stay private.

## Observations

- Initialization completed 285/285 with result 0; the passive scan passed with
  the classifier now independent of the join; the owner's BSS matched and
  `channel40_ir_after_beacon=1` appeared.
- `iw dev wlan0 connect` returned `command failed: Operation not supported
  (-95)` inside the framed body, exit 161; the driver printed only `one-shot
  WLAN join stopped: status=-110 first=0 submitted=0x0 debt=0 cleanup=0`; zero
  management records.
- The complete sealed log contains neither `one-shot WLAN join peer refused`
  nor `one-shot WLAN join channel refused`. Both format strings are present
  once each in the decompressed validated compile-8 image, verified
  independently by the laptop and on Buildbox-1 against the fetched package.
- A53 regression passed, the log was complete, recovery was confirmed.

## What the negative result establishes, and what it does not

Proposal 0143 logs refusals, not entries: a valid 5 GHz configuration or an
admitted peer runs without any line. The absent lines therefore prove that
neither the channel binding nor the peer precondition logged a refusal; they
do not by themselves prove that those callbacks never ran. What the sealed
evidence does exclude is the runtime-3 inference as stated: a refusal by the
driver's peer precondition would have printed. The failure must lie either on
the host side before the driver's join callbacks, or in a driver path that
refuses without logging; the source review below finds the former and no
instance of the latter on this request.

## Source review of the host path (selected tree, read-only)

- `nl80211_connect` accepts the request and calls `cfg80211_connect`
  (`net/wireless/sme.c`), which, because mac80211 has no `.connect`, runs
  `cfg80211_sme_connect`.
- `cfg80211_sme_connect` first looks the target up with
  `cfg80211_get_conn_bss`, which calls `cfg80211_get_bss` with
  `IEEE80211_PRIVACY(params.privacy)`. `iw connect` without a key does not set
  the privacy attribute, so the lookup demands a BSS whose capability has the
  Privacy bit clear; `cfg80211_get_bss` (`net/wireless/scan.c`) skips any BSS
  whose Privacy bit is set.
- When the lookup misses, `cfg80211_sme_connect` does not fail: it calls
  `cfg80211_conn_scan`, which builds a one-channel scan request with
  `n_ssids = 1` (a directed probe, so an active scan) and submits it through
  `rdev_scan` to mac80211.
- mac80211's `__ieee80211_start_scan` (`net/mac80211/scan.c`) hands it to the
  driver's `hw_scan`. The Phase B `mt6797_mac_hw_scan` admits exactly one
  passive scan per lifetime and refuses any request with `n_ssids`, or any
  second request (`scan_used`), with -EOPNOTSUPP and no log line. mac80211
  falls back to a software scan only when the driver returns 1; any other
  error is returned unchanged, so -95 propagates through `cfg80211_conn_scan`
  and `cfg80211_sme_connect` to userspace synchronously.
- This path never calls the driver's `.config` with the operating channel,
  `.bss_info_changed` or `.sta_state`, which is consistent with the absent
  0143 lines. It leaves the join worker idle until its 10 s deadline, which
  is the observed footer. No host function trace was captured, so this is a
  statically reconstructed path, not a measured one.
- By contrast, `nl80211_authenticate` and `nl80211_associate` look the BSS up
  with `IEEE80211_PRIVACY_ANY` and call mac80211 directly without any scan.

The earlier statement in [RUNTIME_3.md](RUNTIME_3.md) that an explicit
authenticate request would behave identically to the connect was wrong: the
two paths differ precisely in the BSS lookup and the fallback scan. The
coordinator's runtime-3 hypothesis that the connect path itself was the
problem was correct in effect, for this reason rather than for a missing
connect operation.

## Confirming observation, and limits

The path requires the owner's AP to advertise the Privacy capability. The
laptop verified privately in the retained runtime-4 output that the target
block has the Privacy bit set and an RSN element present, with no identifier
disclosed. With that bit verified, the selected SME lookup and the refused
directed scan are a strong source-backed explanation of the -95; it remains a
static reconstruction because no host function trace exists. No other
host-side -EOPNOTSUPP return was found on the connect path before the driver
callbacks for an open-system legacy request on a non-MLO station interface.

## Options for the next step (not implemented here)

1. Userspace: authenticate explicitly instead of connecting. `iw` has an
   `auth` command (`NL80211_CMD_AUTHENTICATE`, open system, fixed frequency
   and BSSID) whose lookup is privacy-agnostic, so it reaches the driver's
   join callbacks through `ieee80211_mgd_auth` without a scan. `iw` has no
   association command, so the bounded authenticate-then-associate exchange
   would need a small additional nl80211 client in the initramfs, or the
   first management milestone would be redefined as authentication only.
2. Driver: admitting the SME's directed scan would mean an active probe on
   air, outside the admitted passive budget, and is not proposed.
3. Any choice changes the reviewed join script and its classifier and needs
   the owner's decision on scope before implementation.
