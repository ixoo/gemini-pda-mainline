# Finite two-lifetime protocol (proposal 0180, bounded prototype)

The protocol for the next runtime: one healthy join lifetime, a healthy teardown, then a
second healthy join and scan in the same boot, to assess whether the source-supported re-arm
runs. It is a bounded source-supported prototype, not production reusability and not a crypto
result. The crypto/replay boundary stays a separate required condition; the absent group 1 in
runtime 32 does not reduce it.

## What the wrapper does (identical device effects to runtime 32, twice)

- Keeps the vif alive between the two disconnect/connect cycles: `remove_interface` and `stop`
  remain separate from a disconnect, and are not invoked between the cycles.
- Lifetime 1 is the runtime-31/32 healthy C2+C3 exactly. Then a healthy disconnect that drives
  mac80211's `sta_state` down to `NOTEXIST`.
- Waits for the attributable first healthy terminal **and** the completed station teardown
  before the second connect: the driver re-arms only when the worker's healthy stage-3 cleanup
  and the `NOTEXIST` teardown have both been observed (either order), the lifetime is quiescent
  (empty queue, no debt, no credit pending, no in-flight frame), exactly the two expected key
  removals are credited with both key-done windows and no third, and the two-lifetime cap is
  unreached. The wrapper does not start the second connect until the `one-shot WLAN join rearm`
  record is observed.
- Lifetime 2 is a second connect and its scan, same finite bounds as lifetime 1.
- No automatic retry: a re-arm that does not occur (any gate unmet, or a wire-identity wrap) is
  a named terminal, not a retried cycle.

## Exact budgets and counts (per lifetime, as runtime 32)

- Scan: exactly one admitted `hw_scan` per cycle (`scan_used` reset only on the healthy scan
  completion), channel 40, the one broadcast filter; no probe requests.
- Channel: one grant per cycle, held through the data phase, returned at cleanup stage 1; the
  grant-tail and the reserved deauthentication margin preserved.
- Keys: the two WPA2 key commands (pairwise, group) submitted and credited, then removed at
  cleanup; no rekey.
- Management/data: the runtime-32 budgets — the bounded data phase (`MT6797_JOIN_DATA_BUDGET_MS`
  inside the grant), the data delivery and TX caps, the ping and SSH exchanges.
- Wire identities: `join_channel_token` and `join_sta_sequence` advance by one per re-arm and the
  monotonic command `sequence` continues; a u8 wrap or an exhausted `sequence` (> 248) refuses the
  re-arm. Scan counters and observers reset per completed cycle; wire identities stay fresh.
- At most **two** lifetimes are admitted, enforced at the **first effectful submission**:
  `hw_scan` counts the lifetime where it admits the scan and refuses a third scan before any
  peer, channel or key write, so no third cycle reaches a command; a re-arm is likewise refused
  once two lifetimes have started, and only a healthy terminal re-arms (a fault re-arms nothing and
  stops the run). The wrapper issues exactly two expected supplicant cycles and does not rely on
  the activation cap or on a host kill.

## Stop conditions and classification

The runtime-32 refusal grammar and the single native recovery are unchanged, plus: a re-arm
refused (any gate unmet) is a named terminal, not a silent close; a third or out-of-order key
event is a named refusal; a wire-identity wrap poisons (footer branch 10). `classify-join.py`'s
`classify_lifetimes()` splits the sealed log at each `rearm` record and classifies each lifetime
segment; a single-lifetime log (the pre-0180 shape, no re-arm record) returns one segment, so old
evidence stays valid.

## The explicit residual (not settled by a passing run)

The lifetime-2 `ACTIVATE_STA_REC` response authenticates activation only; it is **not** proof that
lifetime 1's generationless key events were drained. `EVENT_ID_ADD_PKEY_DONE` carries only
`{bss, addr}` — no sequence or generation — so a late lifetime-1 key-done could substitute for a
delayed or lost lifetime-2 one and still total two. Matching counts and station liveness **bound**;
they do not **authenticate**. A passing two-lifetime run shows the source-supported lifecycle runs;
it does not settle this firmware key-event incarnation contract or establish production reuse. The
connection-monitor (nullfunc/beacon, the reason-4 idle disconnect) is in scope only so lifetime 2
starts from a clean monitor state; no sustained-operation claim follows.

## Checks (this input)

Host-testable: `tests/join-rearm-test.c` (the re-arm decision — the rendezvous in both orders, the
two-lifetime cap, the poison short-circuit, each quiescent/obligation gate, and the token/station/
sequence wrap, ASan/UBSan); `tests/host-test.py` (the two-lifetime segmentation into two healthy
verdicts, the single-lifetime one-segment case, and the re-arm and lifetime-tagged activation records
recognized not malformed); `./scripts/check-repository`; and the pinned `scripts/checkpatch.pl` on
the 0180 patch (one standing missing-Signed-off-by as every archive proposal, one commit-description
line-length warning, a new-file MAINTAINERS note, and the advisory multiple-assignment style of the
mechanical reset block — none a material defect). The re-arm's concurrency and the field reset live
in `mac.c`, which is not host-compilable; their compile is the managed Buildbox build (after review)
and their behaviour is the runtime's. No build, device or crypto step is part of authoring 0180.
