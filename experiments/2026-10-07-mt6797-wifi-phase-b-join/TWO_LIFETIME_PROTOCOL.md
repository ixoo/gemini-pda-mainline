# Finite two-lifetime protocol (proposal 0180, bounded prototype)

The protocol for the next runtime: one healthy join lifetime, a healthy teardown, then a
second healthy join and scan in the same boot, to assess whether the source-supported re-arm
runs. It is a bounded source-supported prototype, not production reusability and not a crypto
result. The crypto/replay boundary stays a separate required condition; the absent group 1 in
runtime 32 does not reduce it.

## What the wrapper does (explicit same-supplicant control; device effects of runtime 32, twice)

The supplicant's natural auto-reconnect is NOT used: it can begin cycle 2's scan during cycle
1's DHCP block, before the wrapper has seen cycle 1's fault or its host SSH receipt, and the
driver's first-effect scan cap cannot stop that (only one scan has occurred). The wrapper
therefore controls the supplicant explicitly, keeping the one vif and the one supplicant alive:

- The network starts **disabled** (`wpa_cli disable_network`, with `ap_scan=1`). `remove_interface`
  and `stop` are never invoked between cycles; the vif and supplicant stay up.
- Cycle 1: one `wpa_cli enable_network`/`select_network` → the one scan, join, data phase and the
  per-cycle DHCP/ping/SSH in cycle 1's own directory with a fresh readiness marker and receipt →
  the driver's bounded teardown → `disable_network` on the terminal.
- A failed control response stops the run before any effect: the control socket must be up and
  `sta_autoconnect 0` must return exact `OK` before any scan, and each cycle's `select_network`
  must return `OK` before its scan.
- The attributable per-cycle receipt is a **host acknowledgment**, not a device log heuristic: the
  host adapter does the Wi-Fi SSH exchange to the cycle's leased address, validates the live boot,
  the cycle ordinal, the command output and the exit status, and writes the exact line
  `host_ack boot=<boot> cycle=<N> ssh_exit=0` to `c<N>/host-ack` over authenticated USB; the device
  only consumes it (an exact `grep -qxF` match on a new non-symlink leaf).
- **Attributability and the one exact cutoff.** The *data exchange* must happen inside this
  cycle's data window: the kernel delivers and transmits station data only during the data phase,
  so a successful Wi-Fi SSH exchange is itself attributable to that window. The host confirms it
  against the device's own per-cycle `ready` block (this boot, this cycle ordinal, the fresh
  listener pid, the leased address), served by the device over Wi-Fi — a device-written marker,
  not an echo of the ordinal the host supplied. The *acknowledgment* is a USB control
  notification, not station data; it may land during the healthy cleanup tail, but only guarded:
  the host's write and the device's `wait_host_ack` both fail closed once this cycle's stage-3
  terminal is reached or any named fault is recorded (the host guard also refuses an existing or
  symlink ack leaf), so a late or post-fault ack cannot gate cycle 2. This is not a claim that
  station data moves outside the data phase. The healthy terminal and re-arm waits are
  deliberately **not** gated on this window: they run after the data phase and cleanup close.
  Because runtime 32's data window was only ~6.2 s, the device waits/blocking-child polls and the
  host probe/ack polling use a short 0.2 s interval (same finite budgets, one Wi-Fi attempt per
  cycle) so the exchange and ack fit the window. The custodian joins and stops the host helper
  before evidence sealing and recovery, so no ack can be written after the return to Gemian.
- Before cycle 2 the wrapper waits for **both** the healthy rendezvous (the `one-shot WLAN join
  rearm` record) **and** the attributable cycle-1 host acknowledgment, and stops on the first fault
  (a named join `stopped:`, a boot change or the wall deadline); only then `select_network` for
  cycle 2. No automatic retry; no second selection if cycle 1 faulted or its ack is absent.
- Every wait (data phase, host ack, terminal, rearm) and every blocking host operation (DHCP,
  listener, ping, via `window_ok`) shares the same fatal/boot/deadline guard, so a cycle's
  lease/listener/ping stay within the live data window and nothing runs after a fault.
- Cycle 2: the same finite bounds; `disable_network` on its terminal.
- Control client: a pinned same-version `wpa_cli`, built from the SAME wpa_supplicant 2.11 and
  libnl 3.11.0 sources, `.config`, toolchain and flags as the pinned supplicant (the reproducible
  `build-wpa-cli.sh`; static aarch64, SHA-256 `04fdf3ae…`), added to the private RAM root as a
  composition input with that checksum. Source-verified control contract (wpa_supplicant-2.11):
  `STA_AUTOCONNECT 0` sets `wpa_s->auto_reconnect_disabled`, which `events.c` gates the
  post-disconnect auto-reconnect on, so a cycle's driver teardown leaves the supplicant idle and
  the wrapper drives each cycle with `select_network`/`reconnect` over the one live vif — no
  reliance on `disable_network` timing. The host two-cycle adapter and the composition input are
  the remaining sub-project.

## Exact budgets and counts (per lifetime, as runtime 32)

- Scan: exactly one admitted `hw_scan` per cycle (`scan_used` reset only on the healthy scan
  completion), channel 40, the one broadcast filter; no probe requests.
  The supplicant config sets `scan_res_valid_for_connect=0`, so each `select_network` forces a
  fresh scan (2.11 `fast_associate`'s age check is always expired) rather than a cached
  fast-associate; the exactly-two-scan bound does not depend on the data-phase duration. The
  classifier requires each lifetime segment to show exactly one kernel scan admission.
- Channel: one grant per cycle, held through the data phase, returned at cleanup stage 1; the
  grant-tail and the reserved deauthentication margin preserved.
- Keys: the two WPA2 key commands (pairwise, group) submitted and credited, then removed at
  cleanup; no rekey.
- Management: 3 management transmits per cycle — authentication (subtype 11), association
  (subtype 0) and the reserved deauthentication (subtype 12) — plus 2 EAPOL frames; the keys
  are 2 adds and 2 removes, each a command with a 100 ms credit deadline.
- Data phase: budget = min(`MT6797_JOIN_DATA_BUDGET_MS` 60000 ms, grant deadline −
  `MT6797_JOIN_GRANT_TAIL_MS` 2500 ms); teardown margin `MT6797_JOIN_TEARDOWN_MARGIN_MS` 5000 ms;
  worker poll cap `MT6797_JOIN_MAX_POLLS` 4096; RX delivery cap `MT6797_JOIN_DATA_RX_MAX` 16384;
  a TX queue of up to `MT6797_JOIN_DATA_TX_QUEUE` 8 slots with one frame in flight at a time; TX-failure cap `MT6797_JOIN_DATA_TX_FAILURES`
  8; credit records `MT6797_JOIN_DATA_CREDIT_RECORDS` 8.
- Host per cycle: `udhcpc` ≤ 20 s (4 tries × 3 s, one lease), the Dropbear listener ≤ 90 s,
  `ping` 3 × 2 s ≤ 12 s, the SSH readiness wait ≤ 6 × 0.5 s.
- Command sequence: the u8 `mac->sequence` is monotonic across both cycles (refused > 248 at
  add_peer, > 253 at cleanup); the TX pids `join_next_pid` are monotonic across both cycles,
  capped at `MT6797_JOIN_DATA_LAST_PID` 126, and a re-arm is refused if `join_next_pid` > 63 so
  the second cycle has fresh pids and never reuses them.
- Aggregate over the two cycles: ≤ 2 scans, ≤ 2 channel grants, 4 key adds + 4 key removes,
  6 management transmits + 4 EAPOL, two data phases, all pids and sequences within the single
  monotonic u8 spaces above; a third cycle's first-effect scan is refused. After lifetime 2's healthy cleanup the
  driver does not schedule a re-arm (the cap is reached), so the stage-3 cleanup record is the
  expected terminal; no "rearm refused lifetimes=2" record is emitted, and the wrapper treats
  the two-cycle completion, not a refusal, as success.
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
event is a named refusal; a wire-identity wrap emits the named `rearm wrap` record and
poisons via first_error+closing (no automatic retry). `classify-join.py`'s
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
