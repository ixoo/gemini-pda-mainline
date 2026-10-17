# CCMP6: DHCP, then pending monitor-disable credit; incomplete

Consumed once, 2026-10-17. No unchanged C6 repetition or next device candidate
is selected. Maintained Wi-Fi, healthy cleanup and full compatibility remain
false. Device returned through the reviewed path to confirmed changed-boot
Gemian; C6 remains installed in boot2, not awaiting a new selection.

## Identity and execution

[Preparation](CCMP6_PREPARATION.md) pins the kernel input `6a34397c`, profile,
package, source, config, real candidate receipt and full partition checksum.
Deployment full-readback SHA-256 was
`fbb5eb729638bec7afb435782b1dbb73219ff3e52469b0aa946ca26073ff3091`.
The new terminal symbol, release and architecture were independently checked
on mainline boot `71a631b3-5628-459b-a040-f4ea698baca5`.

Exactly one capture completed (exit 0, Phase A ready). An initial session CLI
refused in host source preflight (exit 2), before `HOST.prepare`, helper spawn,
session claim or device commands. The [source-routing correction](results/ccmp6-session-source-review.json)
preserved every historical source hash and recovery behavior; full actual
offline preparation and local/Linux binding tests passed. No second capture,
boot, scan or join was used to repair that host preparation.

One actual device session then executed with tooling
`0c706a34ae5cf5a179bd25b1d22a058c40c59801` and returned exit 1. The original
preflight-refusal log remains separate from the actual execution log. No
driver, budget, candidate or acceptance predicate changed between capture
and session.

## Positive observations and network limits

- AUTH/ASSOC and the initial WPA2 messages 1-4/key negotiation completed.
  Initial PTK/GTK submission and credit observations are not proof of key
  deletion, rekey safety, firmware integrity or replay enforcement.
- Two checked firmware-decrypted CCMP Ethernet frames were queued through the
  selected initial-PTK/host-PN/standard-decap path. Native ciphertext queued 0.
  Both ordinary TX frames received firmware status-0 completion records.
  Status 0 is not an independent over-air ACK measurement.
- DHCP completed (exit 0, bound/lease-written 1, prefix 24). A real 194-byte
  DHCP log was retained. The SSH listener started and passed its readiness/
  binary-digest checks, but the laptop helper saw a named fault before it
  admitted a Wi-Fi SSH exchange. No SSH attempt or fresh authenticated ACK.
- Cycle export is incomplete and contains no ping transcript. Leaf ping 0/0
  are absent-proof defaults, not a measured zero-traffic or three-loss result.
  The legacy footer's RX-unicast 0 also does not negate the two checked CCMP
  deliveries, which use the separate decap counter.

Classifier `authenticated=false` means missing fresh SSH proof; it does not
deny the observed WPA2 negotiation. `eligible_ccmp_queue=false` folds in fault
and healthy-cleanup conditions; it does not mean no checked Ethernet arrived.

## Numeric chronology and terminal history

The [chronology](results/ccmp6-numeric-chronology.txt) and
[scalars](results/ccmp6-runtime-scalars.json) contain only whitelisted numeric
fields from the hash-verified log. Times below are microseconds since boot.

| Boundary | Time | Observation |
| --- | ---: | --- |
| Data phase begins | 450520331 | budget 6196 ms, teardown margin 5000 ms |
| ACTIVE | 450565942 | sample counters initially zero |
| First data submit / completion | 450988896 / 451014096 | PID 5; 25200 us between host log records |
| PID 6 completion | 451164940 | status 0; its earlier C5 missing-completion outcome did not recur |
| DISABLE_PENDING | 452252839 | all-RX cap 512, bytes 52125, two checked Ethernet deliveries |
| Stop | 452360499 | -110, first 0, branch 1, shared debt 1, cleanup 0 |
| Data footer | 452384846 | reason disconnect, elapsed 1864 ms, TX queued/done 2/2, failed 0 |

There was no CLOSED transition, post-CLOSED receive, HIF length-refusal line
or data-frame-timeout line. The ACTIVE phase accounts for 508 type-2 and four
type-7 packets; seven delivered beacons are a separate counter, not seven
additional reads. The sample ceiling was respected; no drain reads followed.

The once-only terminal report records no frame in flight, PID/last-submit
PID 6, submit-return boundary `451020155334` ns and stored frame deadline
`451770155334` ns. Thus an expired stored deadline alone is not the C5
in-flight predicate. The last successful guard returned at `452284049719` ns,
with cached WHCR 0 / WHISR 2. The report's embedded time was
`452308059334` ns: 24.010 ms after that guard return. The actual register reads
preceded the return; these are not fault-time values or exact sample ages.

| Port | Attempts | HIF successes | Type 7 | Opposite half nonzero | Last status / pre-WRPLR |
| --- | ---: | ---: | ---: | ---: | --- |
| 0 | 518 | 512 | 4 | 0 | 0 / `0x0000005c` |
| 1 | 517 | 0 | 0 | 508 | -EAGAIN / `0x0000005c` |

Last return times were `452184248796` / `452184234180` ns respectively,
before the monitor-disable wait. These observations prove neither an
opposite-port packet was lost nor that WRPLR reads advance a FIFO. Port 1
reported no selected length; its opposite-half count describes advertised
port-0 work only. A reported type class is not a producer or crypto guarantee.

## Source-supported reading and remaining uncertainty

After the all-RX ceiling, the unchanged state machine submits monitor disable
only when its shared ledger is quiescent, charges one shared page and marks
`join_credit_pending`. DISABLE_PENDING admits no generic RX; only the existing
register guard can retire that command's page. In the reviewed source the
command's credit deadline is 100 ms from the step's pre-submit timestamp.
The worker tests pending-credit expiry under branch 1 before the next guard.

The observed pending disable, remaining shared page and absence of a later
credit/closed record are consistent with that credit-expiry path. This is a
different unresolved obligation from C5's in-flight data completion. The
combined branch-1 predicates and exact credit-deadline value were not logged,
so the label does not independently identify every condition true at the tick.
Missing page return is not proof the firmware never processed the command.

Source inspection found no hidden credit reconciliation inside monitor
submission: it uses the existing serialized join-command PIO path. Host
locking, header equality and poison/no-copy behavior remain unchanged.
The pre-submit deadline origin is a source fact, not proof it caused this
timeout; no extension or timer-origin repair is selected from these records.

Neither this run nor C5 reached the earlier post-CLOSED gap-48 comparison
point. No FIFO-pop fix, aggregate decoder, length subtraction, unchecked RX,
extra drain, synthetic credit retirement or successful 0195 repair is proved.
The next source question is the monitor-disable command/page-return contract
and its relation to pending RX, considered separately from the RXD/advertised-
length producer contract. A later candidate needs a concrete supported
correction or a distinct bounded measurement; no repeat or broad firmware
search follows merely from this failure.

## Preservation, quiescence and reviewed return

The complete 161208-byte log has SHA-256
`7ba0f4628cc50e7c72b29ff34996a12c436987da0cd5c6c5c11a5fcf056c8df8`:
2061 contiguous records 0-2060, classified complete through seal. All 63
pre-recovery seal entries were independently rehashed and matched manifest
`34f689046bb6b239959f6d51b419f041b8806567b74ed85f64148c2182e4e9a0`.
Raw logs, network exports, source snapshots, firmware and private paths remain
private; only their bounded scalar observations and identities are published.

Owned helper SAFE/group-quiescent and device-child quiescence passed; no
helper timeout, probe error or kill error. A53 regression passed. One reviewed
native recovery request and two recovery-watch connection attempts confirmed
changed-boot Gemian `29fa9106-1c76-408e-b735-42cc2bc183ae`. A separate bounded
read-only confirmation matched `3.18.41+` / aarch64 and that boot identity.
No second recovery, automatic boot2 selection or additional radio trial.
