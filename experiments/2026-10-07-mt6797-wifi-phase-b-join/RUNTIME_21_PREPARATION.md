# Runtime 21 preparation: one boot for handshake, data and teardown (proposals 0164 to 0167)

Status: protocol stated before any boot; compile 25 ([COMPILE_25.md](COMPILE_25.md))
is validated; the candidate and deployment bindings follow their receipts. The custodian reviews this
protocol and every device step; the custodian remains the sole device
custodian.

## What differs from runtime 20

Runtime 20 ended one second after the group key's credit with a refused
second add-key-done event. This boot carries proposals 0163 to 0167 on top of
compile 24's series: both add-key-done windows admitted and required, the
group key under the station's declared broadcast WLAN index 2 with the
supplicant-path removal shapes, the channel privilege released after the
group key, one bounded data phase with protected data in both directions on
the legacy non-QoS association, and the teardown after it. The
association, the EAPOL path and the key commands are otherwise runtime 20's.

## Hypothesis, unique measurement and branches

Hypothesis: with the group key under the declared broadcast entry and the
channel released, the firmware accepts the two key commands with one
add-key-done event each, the station exchanges protected data with the AP
for up to 60 s, busybox `udhcpc` obtains a lease and `ping` to the gateway is
answered, and the reserved deauthentication and teardown complete.

Unique measurements, all from the sanitized driver records and the session's
fixed fields: the two key-done records, `channel released`, `data phase`,
the first `data TX` and `data RX` records, the `data phase end` record with
its reason and counts, the data-phase userspace outcomes (lease obtained,
prefix length, ping replies received; no address printed), the removals and
the three-stage teardown with stage 1 released.

Branches, each ending the lifetime exactly once:

1. Both keys credited, channel released, data phase opened, `udhcpc` bound,
   ping answered, the phase ended by the supplicant's disconnect (the script
   stops the supplicant after its checks) or by the 60 s budget, healthy
   teardown: the handshake and data-path passes and the network outcomes are
   recorded separately.
2. Data phase opened but no lease or no ping reply within their bounds: the
   driver counts stand as firmware-boundary evidence; the network outcome is
   recorded as failed; no retry.
3. The second add-key-done event refused, the channel release refused, a data
   credit overflow, an aggregated or QoS frame, an unknown event or any other
   named refusal: fail-stop as before, seal, reviewed recovery.
4. Eight unacknowledged data frames in a row: the phase ends with reason
   `txfail`; the teardown runs; not a pass.
5. The PID budget: PIDs 1 to 127 are consumed in order by every submitted
   frame; ordinary data stops at 126 and the phase ends with reason
   `pidbudget`, so the reserved deauthentication always has PID 127; the
   teardown runs; not a pass.
6. Owned protected data arriving outside the open phase (between the
   pairwise key command and the channel release, or after the phase ended
   while the deauthentication and teardown run) is dropped undelivered and
   counted, at most 256 per lifetime (`data RX outside` records); the 257th
   is a refusal (fail-stop).

No branch repeats a boot without a decision-changing change. Nothing is
reconnected or rekeyed.

## Finite limits

| Stage | Limit |
| --- | --- |
| Passive scan | one 500 ms dwell on channel 40, as before |
| Join lifetime | 10 s from the scan hand-off until the data phase opens; 9 s channel grant |
| Data phase | 60 s after the group key's credit, or until disconnect or fault |
| Teardown margin | 5 s added to the lifetime deadline when the data phase opens |
| Poller | 20 ms period, at most 4096 polls and 32768 packets per lifetime |
| Receive delivery | at most 16384 data frames; more dropped and counted |
| Transmit queue | 8 frames or 12400 bytes queued; one frame in flight; 8 unacknowledged in a row end the phase |
| PID budget | PIDs 1..127 in order for every frame; data stops at 126 (`pidbudget`), 127 reserved for the deauthentication |
| Outside-phase data | at most 256 owned protected frames dropped and counted; the 257th refused |
| TC4 pool | 26 pages (unchanged); TC1 pool 16 pages, both declared host budgets |
| Session join phase | the device script waits at most 100 ticks of 1 s for the terminal record; `udhcpc` at most 4 tries of 3 s; `ping` 3 requests, 2 s each, 8 s overall |
| Host phase budget | the passive-scan phase budget rises from 45 s to 130 s; the supplicant-log export stays 20 s |
| Wi-Fi SSH check | readiness poll 10..120 s (default 90), one exchange, baseline connect timeout 10 s, exchange at most 25 s |
| Wi-Fi listener | retained Dropbear on wlan0's address only; idle 30 s, 60 s per connection, 2 auth tries, 90 s absolute under busybox timeout; stopped at the terminal and on EXIT |

## Evidence and claims

The sealed kernel log's `one-shot WLAN join` records classified by
`classify-join.py`; the session's fixed fields and phrase counts; the private
supplicant log exported and digested. `driver_handshake_path_pass` and
`driver_data_path_pass` describe the driver's bounded behaviour at the
firmware boundary; `wifi_operational` stays false; a lease and ping replies
are the only network-function evidence and are reported as such. No
installed-key, replay-protection or throughput claim follows.

## Session tools (implemented, host-tested, not yet run on the device)

- `join-once.sh` waits up to 100 ticks for the terminal record; when the
  driver records `data phase: budget_ms=`, it runs the data checks once.
  busybox `udhcpc` (foreground, 4 tries of 3 s, under a 20 s busybox timeout)
  runs a hook that admits only `wlan0`, a dotted-quad address and a prefix
  length of 1 to 32 (busybox exports the mask as prefix bits; an absent or odd
  value is the fixed status `prefix`, never a guessed /24), adds the address
  on `wlan0`, tries the default route through the router, and writes the
  private lease and prefix files only after the address operation succeeded
  (`hook_status` records `interface`, `address`, `prefix`, `addr-failed` or
  `bound`). On a bound lease the retained `/bin/dropbear` (digest checked
  against the candidate's `10663dd4…`) starts as a second listener on wlan0's
  leased address only, with the retained host key and the approved
  authorized-key directory, foreground, password and forwarding disabled like
  the USB service, idle 30 s, each connection at most 60 s, two auth tries,
  under the admitted busybox `timeout 90` (which execs Dropbear in place, so
  the owned pid is Dropbear's and the watchdog bounds the whole listener to
  90 s). The readiness marker is written last, after Dropbear's pid file names
  the owned pid and it is alive. Then busybox `ping` to the router (3
  requests, 2 s each, 12 s timeout). The listener is stopped with one signal
  and one wait at the terminal record and unconditionally on EXIT. The framed
  result gains the fixed fields `data_phase_seen`, `tool_udhcpc`, `tool_ping`,
  `dhcp_exit`, `dhcp_bound`, `dhcp_prefix`, `hook_status`, `lease_written`,
  `dropbear_digest_ok`, `wifi_sshd_started`, `wifi_sshd_ready`,
  `wifi_sshd_exit`, `ping_transmitted` and `ping_received`; no address is
  printed, and the private files are removed before the phrases.
- `laptop-wifi-ssh.py` (laptop, custodian-run, in parallel with the join
  phase) takes the retained credential directory (`admin`, `known_hosts`) and
  the launched boot ID. Both hops use the baseline's exact direct SSH options
  (`collect-baseline.py`'s `ssh_command`: no configuration file, no agent, no
  proxy, no multiplexing, Ed25519 only, key only, strict host-key checking
  against the retained `known_hosts`, which pins the fixed USB endpoint's host
  key). It polls the readiness marker over the USB path within a 10 to 120 s
  budget, refuses an address equal to the USB endpoint, loopback, multicast,
  unspecified or broadcast, then opens exactly one SSH session over Wi-Fi to
  the leased address with `HostKeyAlias` set to the USB endpoint, runs one
  read-only command printing the boot identity and requires equality with the
  launched boot. Its receipt (`--receipt`, a new mode-0600 JSON file) holds
  statuses, byte counts, seconds and the boot ID only. One attempt, no retry.
- `passive-host.py` reads that receipt from `GEMINI_WIFI_SSH_RECEIPT` when set,
  binds it to the session result's established `mainline_boot`, and records
  `c3` with `c3_session_pass` (the C2 conjunction, the driver's data-path
  pass, the device's bounded network outcomes with the owned listener, and the
  boot-bound Wi-Fi SSH receipt); the exit code follows that verdict. Without
  the variable the session stays a C2 one. The join phase budget is 130 s.
- `bind-target.py`, `prepare-runtime.py` and the host's inherited scan-tuning
  prepare (its source guard re-pointed through `SCAN.SOURCE_LIMIT`, the
  historic experiment keeping 16384) accept the revised source and its private
  wrapper up to 32768 bytes (the source is about 22.6 KB plus the small
  private prefix); the host fixture runs that prepare chain over the real
  bound source.
- Fixtures: `tests/join-once-test.py` (hook validation and order, one
  listener launch with the exact flags and digest check, readiness after the
  pid file names the owned pid, stop on EXIT and at the terminal, no address
  printed, private files removed), `tests/laptop-wifi-ssh-test.py` (baseline
  options on both hops, HostKeyAlias, address exclusions, one bound exchange,
  mismatch, failure, timeout, private receipt), `tests/c2-session-test.py`,
  `tests/c2-host-test.py` (C3 result over the real session-result shape with
  missing, foreign and malformed receipts), `tests/bind-target-test.py`
  (offline binding of the revised source within the caps),
  `tests/prepare-runtime-test.py`, `tests/host-identity-test.py`,
  `tests/laptop-wrappers-test.py`.

The actual tool execution on the device (busybox applet presence recorded by
`tool_udhcpc` and `tool_ping`, the Dropbear digest, the listener's start) is
verified only by the run itself.

## Candidate 20 and the runtime 21 bindings

The custodian composed and validated candidate 20 privately at 996116d6 with
the compile-25 package `cca46f58…`: candidate 19's RAM root byte-identical
(`449832a3…`), the same board DT `25ab60f4…` and kernel config `975f8703…`,
kernel image `ff95005b…`, boot image `639bbd98…` (12300288 bytes), full padded
boot2 `d01f3304…`. [results/candidate-20.json](results/candidate-20.json)
(SHA-256 `38a4f6b8…`) is the receipt's exact bytes and
`runtime-21/results/candidate.json` its copy. The current boot2 content is the
reviewed Gemian reference v10 predecessor `8d3289a1…` (16 MiB); the custodian
rederives the live GPT and verifies it with the reviewed guard at deployment.

| Adapter | Runtime 21 binding |
| --- | --- |
| `install-passive.py` | predecessor `8d3289a1…`, receipt `mt6797-wifi-phase-b-deployment-20`, `results/candidate-20.json`, slot filled |
| `capture-private.py` | `capture-21`, `session-21/deployment-summary.txt`, `results/candidate-20.json`, slot filled |
| `passive-session.py` | `results/candidate-20.json`; 63-member RAM root with the required supplicant |
| `passive-host.py` | `session-21`, `capture-21`; identity `runtime-21/results/candidate.json`; PSK-bound script required; `GEMINI_WIFI_SSH_RECEIPT` optional |
| `prepare-runtime.py` | `results/candidate-20.json` against the compile-25 input and package, both slots, predecessor `8d3289a1…`, the PSK-bound wrapper (≤ 32768 bytes); creates `wifi-phase-b/session-21` only |

## Device protocol

One boot of the composed candidate, the reviewed session (`passive-host.py`
with the C2 pieces and the data-phase fields), the bound private script with
the PSK, the owner's physical boot2 handoff, the custodian's recovery through
the reviewed path after the sealed log is preserved. No device access from
Buildbox at any point.
