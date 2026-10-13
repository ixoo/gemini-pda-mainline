# ND4 diagnostic successor — source review only

Proposal [0187](../../patches/proposals/0187-wifi-mt6797-count-native-rx-eligibility-and-name-hif-refusals.patch)
SHA256 `dd6a6d3dea6d1c78296710c1d443436e4d0f4dee68d17ffd382ad97217188da5`.
Coordinator final review approved this exact proposal and its seven-path
source/test cohort. Selected only in the native diagnostic series, in canonical
order, against the exact [ND3 source/result](ND3_RESULT.md), not phase-b 0184/0186.
Other profile series, manifest/configuration, frozen runtime and READY remain
unchanged. The reviewed build and ND4 preparation are admitted; no candidate,
installation or runtime result is claimed here. C35/R36 remain uninstalled;
last verified boot2 remains ND3, pending fresh custodian identity checks.

Selection audit: manifest/configuration and all 18 explicit nonnative profile
series remain byte-identical. The canonical append naturally also adds 0187 to
the effective inventories of `full`, `handoff`, `usbdiag` and `usbdiag-clkignore`,
which inherit the global series. The coordinator explicitly admitted that archive
inheritance; their explicit files and historical inputs are not rewritten. They
are not build/boot foundations for this task. Existing full/canonical foundation
limitations remain; no all-23-inputs-unchanged or full-profile support claim.

## New ND3 chronology: observation, not packet-shape inference

The custodian's fourteen sanitized files passed `CHRONOLOGY_SHA256SUMS`.
Records below use the same complete log
`b7e1d741b6385931e3643d473cd4d079fc8b0da0be14b7d4a2551da5903ea73b`.

| Log sequence | Boot microseconds | Observation |
| --- | --- | --- |
| 2031 | 193760708 | DATA opened, budget6196 ms / teardown margin5000 ms |
| 2035 | 193806331 | ACTIVE; cumulative total1 / 442B / native0 |
| 2036 | 194249383 | DATA TX PID5 / pages3 / bytes342 |
| 2037 | 194250862 | PID5 TX-done status0 |
| 2038 | 194273211 | DATA credits3 returned, debt0 |
| 2039 | 195381244 | DATA ended: disconnect, elapsed1620 ms; TX queued/done1, failed0, RX unicast/group/dropped0 |
| 2041 | 195397219 | Disable pending, total200 / 40338B / native0 |
| 2043 | 195422340 | CLOSED after disable credit retirement |
| 2044 | 195423679 | Deauth subtype12 / PID6 / page1 submitted |
| 2045 | 195424964 | HIF receive boundary refused: -EPROTO, debt1, cleanup0, branch4 |

Leaf selection succeeded; DATA checks started. udhcpc reported starting and
broadcasting discover; exit137, bound0, lease0, listener0, READY0 and
`data_checks_failed=1`. This explains the absent READY without bypassing its
DHCP/listener/window contract. Disconnect ended DATA before its configured
budget. The available log does not establish the disconnect's initiating cause.
No delivered lease is **not** proof that no reply arrived on wire or was rejected.

The 442B cumulative count at ACTIVE can include ENABLE_PENDING accounting; it
proves neither protected EAPOL, descriptor type nor decoder invocation. Likewise
RX unicast/group/dropped0 are inherited translated-path counters, not native
decoder-call counts. No existing HIF refusal-stage or native gate/class metadata
was captured. These two missing discriminators justify measurement, not repair.

## HIF failure-only metadata

At exactly the two existing protocol-refusal sites, the result gains a named
reason and the already-read selected length. Header mismatch also records the
already-buffered header length and `header_valid=1`. At advertised-length
refusal, header fields stay zero/absent and RX setup/completion remain false.
Post-WRPLR was not read at either refusal: `post_valid=0`, value0. `pre_valid`
attests the completed pre-WRPLR read; selected length is present only when the
protocol-refusal enum is nonzero. Other errors leave new fields absent.

The native worker logs one `native HIF refused` line before the unchanged
fail-stop. It cannot copy refused packet data or continue/replenish credit.
There are no new MMIO/FW/radio accesses; the length/header comparisons and
poison calls remain at their original sites. This identifies the refusal gate,
not the root cause of an unexpected device length.

## Native counts: consumed class versus actual decoder call

At the existing successful receive/window hook, one descriptor-type bucket
(`packet_type >> 13`, bounded0..7 by the HIF le16 result) is incremented before
class dispatch. It does not imply protection, EAPOL, peer identity or eligibility.

| Phase | Meaning at successful consumption |
| --- | --- |
| 0 | ENABLE_PENDING sample |
| 1 | ACTIVE sample |
| 2 | Post-window owed-completion drain, pending or active |
| 3 | Inherited reception after CLOSED |

The phase is frozen before dispatch. An ACTIVE transition later cannot relabel a
pending packet. IDLE/disable-pending have no native sample bucket. Existing
control/EAPOL/management dispatch still precedes the ordinary-native hook;
counts consumed there must not be called decoder rejections.

At the ordinary-native hook, the existing admission predicate is evaluated once.
If false, only `blocked` increments: **no decoder call**. If true, the original
ordered decoder returns its first failing eligibility gate (or eligibility0),
and exactly one corresponding bucket increments. Sum of gate buckets equals
actual decoder calls; `blocked` is excluded. For each phase, gates+blocked are
at most consumed type counts; the remainder never reached this hook. Eligibility
counts include any later allocation failure and are not delivered/authenticated
counts. Existing `native=` still counts queued delivery exactly as before.

Gate labels in order: input pointers/size/channel argument, declared length,
descriptor type, observed channel, header translation, MSDU/aggregation, FCS,
reported header length, MPDU span, version/frame type, Protected, DS direction,
remaining frame shape/fragmentation, peer, destination, CCMP shape. Only the first
failure is counted; later gates may be unevaluated. The existing boolean wrapper
is retained, with the same admission decisions and returned offsets/lengths.

One scalar descriptor sample at the **first actual admitted decoder call** names
phase/length and descriptor type/channel/header/group mask/MSDU/status. Fields
are present only with at least16 buffered bytes; otherwise `fields_valid=0` and
all descriptor values0. This bit attests byte availability, not correctness of
the assumed RXD interpretation. No MPDU FC, addresses, payload, IV, PN or keys are
logged. A single sample must not be extrapolated to the other calls.

At the healthy or failed terminal, at most eight aggregate lines (two per phase)
are emitted once. Including one first-call sample and one HIF refusal, added
output is at most ten lines for this one-lifetime diagnostic. Counters are bounded
by existing successful-packet/sample/drain/lifetime caps, never used to admit
traffic or expand a limit. Crypto bypass/strip flags remain0.

Telemetry uses separate `one-shot WLAN native RX` / `native HIF refused` prefixes.
The old classifier remains unchanged; its strict state/RX/fault grammar and all
positive requirements remain mandatory. These diagnostics cannot force PASS.

## Focused validation and review boundary

[run-native-metadata-test.py](tests/run-native-metadata-test.py) accepts the pinned
parent tree and a replayed child tree. It reuses existing actual-HIF/native-RX
fixtures and compiles under `-Wall -Wextra -Werror -Wformat=2`, ASan and UBSan:

- both HIF refusal gates/ports, empty and valid reads, every injected transport
  fault, valid/absent fields, actual refusal logging, full no-copy sentinels and
  unchanged poison; parent/child outcome and transport-call tables identical;
- every first decoder gate, multiple simultaneous failures and20000 deterministic
  synthetic mutations: boolean decisions, MPDU offsets/lengths identical to the
  actual parent; original group/pad/QoS tests retained;
- extracted real phase/count/report/sample hooks: pending versus active versus
  drain/closed; blocked does not call decoder, gate sums equal calls, descriptor
  absence zeroes values, eight terminal lines once plus one first-call sample;
- original classifier fixtures plus actual extracted telemetry output: positive,
  fault and malformed original state/RX/fault verdicts unchanged;
- original prospective pre-read/state-action functions and native budget/flags
  header byte-unchanged, plus existing native-loop/budget tests.

Patch replay and focused tests pass. Strict checkpatch reports zero warnings or
checks, with only the explicit missing-signoff error: this synthetic internal
archive has no DCO certification and is not submission-ready. No full kernel
compile, DT test, device test or crypto result is claimed. Final exact proposal
and test paths received coordinator final approval before canonical selection
and build. No new advisor work, candidate substitution or unchanged retry.
