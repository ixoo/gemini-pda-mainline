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

## Diagnosis (inference; the failed predicate was not measured)

The script printed nothing and the channel flags were not captured, so the
exact failing predicate on runtime 2 is unmeasured. What follows is source
inference about the most likely gate, kept distinct from the observations
above and in [results/runtime-2.json](results/runtime-2.json).

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

## Supporting evidence and the measurement that decides

The retained Phase A runtime-3 passive-scan stdout holds a `__PHY_INFO__`
block whose `* 5200 MHz [40]` line, if it shows `(no IR)`, supports the
inference that the pre-scan state is NO-IR; it carries no identifier. A prior
boot cannot establish which gate failed silently on runtime 2, so that line is
supporting evidence only, never confirmation, and its absence is not a blocker.
The decision-changing measurement is the explicit stage marker the corrected
script now emits on refusal: the next boot is justified by that measurement
alone, and it names the real gate if the inference is wrong.

## Correction

`join-once.sh` now refuses channel 40 before the scan only when it is
`disabled` or needs `radar detection`, as Phase A did, and adds a second gate
after the scan accepted the target BSS: it re-queries the phy and requires the
channel-40 line to be free of `no IR` before the connect, so this host never
transmits on a channel the found beacon did not open, and prints one
`channel40_ir_after_beacon=1` line inside the scan body when it passes. Every
other gate is unchanged. The script also records the current prerequisite in a
`stage` variable, with `bss_match` set before the target check so an absent
target is reported distinctly from a failed passive scan, and, only on a
non-zero exit, prints one `__STAGE_FAIL__ stage=… rc=…` line to stderr. The
success path keeps the stdout prefix and framing the host's parser requires
and leaves stderr empty, which the parser also requires; the new body line is
ignored by its BSS scan.
[tests/join-once-test.py](tests/join-once-test.py) runs a copy under busybox
ash with a stub to fail the first gates in turn and asserts the marker, and
statically asserts the NO-IR gate's position. This is a script correction,
not a kernel change: no new build is needed and candidate 2 stays installed.

## Next run

Another boot of the identical candidate is justified by the corrected
script's explicit stage measurement. The next run needs a fresh runtime root (new
`session-2` from `prepare-runtime-2.py`, capture on the new boot) and a bound
script regenerated from this revision with `bind-target.py`; the stage marker
in the private `passive-scan/stderr.txt` names any further refusal.
