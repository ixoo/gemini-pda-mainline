# MT6797 gen3 WLAN host and firmware responsibilities

## Decision

Use **mac80211 as the preferred design target**, with a generation-specific
MT6797 HIF/firmware backend. The inspected gen3 source implements authentication,
association, their retries and receive reordering on the host. A direct
cfg80211 wrapper would have to replace that host work; the existing `.connect`
entry point does not demonstrate that the firmware performs it.

This is a source-supported design choice, not driver admission. No mac80211
capability flags, driver registration or firmware command are added. In
particular, the receive path needs an explicit reordering owner: device-side
header translation does **not** imply firmware reordering. Upstream mac80211
can accommodate a driver-owned reorder buffer, but that buffer's correctness,
station lifetime, event identity and teardown still need a concrete contract.
The [shared HIF lifetime stop](../2026-09-07-mt6797-hif-upstream-architecture/README.md)
remains in force.

This advances the independent command/offload investigation called for in the
[Wi-Fi handoff](../2026-09-05-mt6797-wifi-contract/HANDOFF.md#resume-point).
It does not replace or renew the selected normal-cycle ownership observation.

## Source boundary

The review reads thirteen individual gen3 files from Planet commit
`c5b0be85017ad0c599725e8273842efdbecdd88a`, already selected by the
[transport contract](../2026-09-05-mt6797-wifi-contract/README.md). Exact objects
were available in Buildbox's existing public Git cache after two raw-URL
requests failed. No Linux source tree was transferred.

The comparison uses `include/net/mac80211.h` and `net/mac80211/rx.c` from
upstream `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`. Each cached file was
byte-compared to its member in the existing source archive, whose complete
SHA-256 was verified against the manifest pin. This is a pinned-baseline
comparison, not a fresh upstream-HEAD claim. The exact hashes, source URLs and
line ranges are in [the source receipt](results/sources.json).

Only public source semantics were inspected. The source's presence does not
prove that the installed WLAN firmware accepts every path or that every
conditional feature is active. No retained binary, capture, calibration, key
or live network state was opened. No vendor implementation is copied into a
new driver by this result.

## Responsibility map

Paths and line numbers below are relative to the selected `gen3/` directory.
They identify actual call sites, not only declarations or comments.

| Work | Host/source evidence | Firmware boundary and implication |
| --- | --- | --- |
| Scan | `mgmt/scan_fsm.c:283–356` builds V2 scan parameters and sends command `0x03`. `693–745` accepts completion only for the active scan and matching **payload scan sequence**. | Firmware performs the requested scan. Event `0x0d` has version-dependent length handling in `nic/nic_rx.c:1967–1971`. The scan sequence must not be confused with the outer command/event sequence. A mac80211 `hw_scan` adapter needs cancellation, regulatory limits and exactly one terminal completion. |
| Authenticate and associate | `mgmt/saa_fsm.c:159–194,242–269` sends authentication and association frames, counts retries and starts timers. `865–929` checks the association response and transitions host state. AIS starts that host state machine at `mgmt/ais_fsm.c:525`. | This is host MLME work. Prefer mac80211's managed-station state machine rather than porting AIS/SAA behind cfg80211. Sending a firmware scan request does not offload association. |
| BSS and station state | Command IDs `0x11–0x14` describe BSS activation/configuration and station update/removal. `mgmt/cnm_mem.c:720–760,850–880,953–963` synchronizes host station state, rates and capabilities to firmware; entry into state 3 can request a response. | A future `sta_state`/BSS adapter must map these semantics, not cast Linux state numbers to vendor state numbers. Firmware station identity and pending callbacks must outlive neither the station nor its generation. |
| Transmit frames | `nic/nic_tx.c:1072–1107` selects ordinary 802.11 or non-802.11 header format. `include/nic/nic_tx.h:115–124` defines 28-byte long and 8-byte short descriptors, before separate padding. | Raw management-frame submission exists in the source. The normal eight-byte command header is not a data descriptor. Data lengths, descriptor form, queue credit and HIF padding require separate accounting. |
| Transmit completion | `nic/nic_tx.c:1120–1124` requests a status/PID when a completion callback exists. `2377–2414` finds pending work using **WLAN index plus packet PID**, then dispatches the status. Event `0x0f` carries status, sequence number and optional advanced rate/count information. | Bus-write completion, page-credit return and over-air TX completion are different events. Do not assume every data frame requests TX status, match it using the outer command sequence, or assume advanced rate fields are always valid. |
| Receive framing | `nic/nic_rx.c:285–336` locates optional status groups in order **4, 1, 2, 3**, then applies the reported header offset. Management frames are separately dispatched at `2473–2538`. | Parse reported byte count, group sizes and header offset before taking any pointer or subtracting lengths. Header-translated data and native management frames must not share an assumed payload layout. The source's unchecked arithmetic is not a validation rule to reproduce. |
| Aggregated receive ordering | `nic/nic_rx.c:1340–1342` marks BA-session data for reorder. `nic/que_mgt.c:2577–2584,2608–2609` feeds applicable frames, including translated data, to the **host** reorder queue. Events `0x0a/0x0b` create/delete BA state; `3414–3457` extracts station, TID, start sequence and window size. | Firmware BA events do not prove that frames arrive ordered. `CFG_RX_REORDERING_ENABLED=1` in the selected source also does not establish the live configuration. The future backend must establish either native 802.11 delivery into mac80211 reorder or correct driver-owned reordering before decapsulated delivery. |
| Keys | `common/wlan_oid.c:2316–2355,2649–2655` builds key command `0x07`, selects no generic response, queues it and returns pending. The [retained key-lifetime follow-up](FIRMWARE_KEY_LIFETIME.md) identifies a distinct unsolicited `0x24` event and its host TX gate. | Queue completion, firmware key readiness and replay validation are separate. Event correlation/reliability, cipher applicability, PN/replay ownership and station-index reuse remain unresolved; no `set_key` implementation or crypto-offload flag follows from this review. |
| Rate control | `nic/nic_tx.c:1141–1154` selects automatic or manual descriptor/control-register rate modes; station updates supply rate capabilities. | Automatic mode is not enough to set `IEEE80211_HW_HAS_RATE_CONTROL`. Upstream's flag requires the hardware/firmware rate-control contract and related protection callbacks. No rate-control policy is selected here. |

The existing [normal capability/NVRAM helpers](../2026-09-05-mt6797-wifi-contract/NORMAL_COMMAND.md)
remain narrowly scoped. Their one-command state and sequence bitmap must not
be expanded into a fake universal event dispatcher: scan completion, station
updates, BA events and TX status have distinct identities and lifetimes.

## The mac80211 receive constraint

In the pinned upstream `net/mac80211/rx.c:5704–5721`, `RX_FLAG_8023` selects
`__ieee80211_rx_handle_8023()` rather than the ordinary 802.11 packet handler.
That function (`5258–5305`) requires a usable station/fast-RX context and calls
`ieee80211_rx_8023()` directly. It does not pass through the ordinary AMPDU
reorder call at `4312`.

Therefore simply setting `RX_FLAG_8023` on the vendor's translated packets
would discard the host reordering responsibility seen above. The standard
`IEEE80211_HW_SUPPORTS_REORDERING_BUFFER` contract explicitly permits either
hardware **or the driver** to manage the reorder buffer, provided mac80211
receives ordered frames and need not manage BA timeout itself. Driver-side
reordering is thus a possible standard integration, not evidence that firmware
already supplies it. Do not advertise that flag before the implementation
meets the contract.

Two possible receive implementations remain open:

1. Establish a supported native-802.11 data mode, including cipher/PN metadata,
   and use mac80211's normal receive/reorder path.
2. Preserve a generation- and station-bound private reorder owner for translated
   data, with BA creation/deletion, window advancement, holes/timeouts and
   teardown defined, before passing ordered Ethernet frames to mac80211.

The inspected source shows both frame-format handling and a translation flag;
it does not freeze a supported control for selecting native data delivery.
No firmware command or register bit is invented to obtain that mode. The next
independent source question is that RX-format/control and BA-lifetime boundary,
not another stand-alone parser without a real receiver.

The [receive follow-up](RECEIVE.md) retains the source-supported translated
path and distinguishes normal DELBA delivery from station-removal discard. It
also identifies the missing firmware ordering boundary before station-index
reuse; a host-only generation does not authenticate a late wire event.

The existing `mt76` hardware/transport mismatch is unchanged. A plausible
mac80211 integration does not make this an MT7603, MT7628 or SDIO device, and
similar descriptor vocabulary is not a compatibility proof.

## Observation-path check

Before the offload review, the public Gemian comparator
`59e00a9144d782e148332009a835b99c43382467` was checked for a standard perf
alternative to the already-unavailable kprobe/ftrace path. Its perf UAPI has
`PERF_SAMPLE_REGS_USER` but no `PERF_SAMPLE_REGS_INTR`.
`kernel/events/core.c:4672` substitutes saved **user** registers when the
interrupt occurred in kernel context (or supplies none for a kernel thread).
`perf_bp_event()` at `6449` supplies the breakpoint address and count to the
normal sample path; it does not expose the arbitrary kernel argument/MMIO
values required by the five-predicate lifetime capture.

The prepared cached `core.c` is locally patched and did not match the complete
public blob; the two relevant function bodies were consequently read directly
from the pinned public Git object. This result is about that source ABI, not
fresh live-kernel identity or a test of perf on the device. No perf event,
breakpoint, module, trace, radio action or device command was issued. A custom
kernel callback would be new instrumentation, not this standard read path,
and is not selected. The owner-closed retained-instruction observer remains
closed.

## Validation and limits

Source objects and cited call paths were reviewed directly. The two upstream
files matched the checksum-verified pinned archive. This is documentation and
source analysis only: repository checks apply; no kernel build, synthetic
protocol suite, device session or hardware-support result is claimed.

The preferred stack choice resolves one design uncertainty while preserving
real blockers: CONSYS/EMI/AP-DMA lifetime, firmware load/stop, calibration,
regulatory applicability, exact live RX/event behavior and failure teardown.
Mainline scanning, association and traffic remain unimplemented/unproved.
