# Second Phase B runtime: initialization passes, join script stops before output

Boot identity: mainline `eee023ca-9184-47cf-9a09-bc1c7e6a21a9` from candidate
2 (boot2 `03a6d78c…`, receipt `f19dffdb…`, package `47addc13…`), host revision
`103116ac`, returned to a changed-ID Gemian boot
`695a19a9-7cf3-40a0-b0db-b686a6e37963` through the reviewed native recovery.
Sanitized record: [results/runtime-2.json](results/runtime-2.json). Raw
capture, session, AP input and calibration bytes stay private on the laptop.

## Observations

- Common init completed all 285 steps with result 0, a calibration ack
  arrived, PA rails were off afterwards and the firmware was not stopped. The
  runtime-1 step-5 failure did not recur under fix 0141.
- TC4 reconciliation, regulatory configuration and private record prepare each
  appeared once; the wiphy probe registered one phy, index 0, bound.
- The bound join script was invoked once and exited 1 after about 0.5 s with
  zero bytes on stdout and stderr, stdin complete, no reason. The sealed log
  holds no `one-shot passive WLAN scan` or `done` record, no `one-shot WLAN
  join` record and zero host management submissions. No RF request was
  demonstrated. The combined result's `scan_attempted` means invocation only
  and `channel40_permitted=false` is the unobserved default.
- A53 regression passed, the log was complete (146383 bytes) and recovery was
  confirmed; `session_verified` is true, `bounded_join_pass` false.

## Diagnosis (source inference, not yet measured)

Everything the script does before its first print is a chain of `set -eu`
tests. Against the script that passed in Phase A runtime 3 (`phase-a-scan.sh`,
same initramfs tool digests, same CONSYS device path, same readiness markers)
the join script differed in that region only by the bound target inputs, the
kernel release string, the scratch directory name and one gate: it refused
channel 40 when `iw phy phy0 info` reported `no IR` or `radar detection`,
where Phase A refused only `disabled`.

In the selected tree the world regulatory domain rule for 5170 to 5250 MHz
carries `NL80211_RRF_NO_IR` (`net/wireless/reg.c`, `world_regdom`), and the
driver sets no country hint, regulatory flags or self-managed domain
(`mac.c`, registration). cfg80211 lifts NO-IR on a channel only after a scan
finds an ESS beacon there (`regulatory_hint_found_beacon` from
`net/wireless/scan.c`, applied by `handle_reg_beacon` for world-roaming
wiphys without `REGULATORY_DISABLE_BEACON_HINTS`). Before the first scan,
channel 40 is therefore NO-IR, which is permitted for a passive scan, exactly
the state in which Phase A succeeded. The join script's pre-scan `no IR`
refusal exits 1 before any output, matching the observed half-second,
zero-byte failure. The sealed evidence cannot distinguish this from the other
pre-print gates, so it remains an inference.

The laptop's hypothesis that mac80211 auto-created `wlan0` is refuted by
source: the driver sets `IEEE80211_HW_NO_AUTO_VIF`, and
`ieee80211_register_hw` adds the default station interface only when that flag
is absent (`net/mac80211/main.c`).

## Decision-changing measurement before any boot

The retained Phase A runtime-3 passive-scan stdout holds the `__PHY_INFO__`
block. Its `* 5200 MHz [40]` line showing `(no IR)` confirms that Phase A
scanned in the NO-IR state and that the join script's pre-scan gate was the
first failing prerequisite. That line carries no identifier and no secret. If
it shows no `(no IR)`, the diagnosis is wrong and the stage marker below
identifies the real gate on the next run.

## Correction

`join-once.sh` now refuses channel 40 before the scan only when it is
`disabled` or needs `radar detection`, as Phase A did, and adds a second gate
after the scan accepted the target BSS: it re-queries the phy and requires the
channel-40 line to be free of `no IR` before the connect, so this host never
transmits on a channel the found beacon did not open. Every other gate is
unchanged. The script also records the current prerequisite in a `stage`
variable and, only on a non-zero exit, prints one `__STAGE_FAIL__ stage=…
rc=…` line to stderr; the success path's stdout and empty stderr are
byte-identical to before, which the host's parser requires.
[tests/join-once-test.py](tests/join-once-test.py) runs a copy under busybox
ash with a stub to fail the first gates in turn and asserts the marker, and
statically asserts the NO-IR gate's position. This is a script correction,
not a kernel change: no new build is needed and candidate 2 stays installed.

## Next run

Another boot of the identical candidate is justified only after the Phase A
phy-info line is read. The next run needs a fresh runtime root (new
`session-2` from `prepare-runtime-2.py`, capture on the new boot) and a bound
script regenerated from this revision with `bind-target.py`; the stage marker
in the private `passive-scan/stderr.txt` names any further refusal.
