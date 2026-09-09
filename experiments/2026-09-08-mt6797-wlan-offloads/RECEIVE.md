# Receive format and station lifetime follow-up

## Result

Continue the receiver design around **translated data with an explicit
host reorder owner**. The selected source directly implements that path.
Native 802.11 data remains an alternative only after a supported control and
its managed-station semantics are established. Do not use monitor mode or
invent a packet-filter bit to obtain it.

The follow-up also identifies a concrete station-reuse requirement: a host-only
generation counter cannot distinguish a late firmware event for a reused
station index. The inspected removal path provides no response or drain witness.
A receiver cannot be declared ready for reconnect or teardown until the firmware
ordering boundary is established. This is an unresolved protocol requirement,
not an observed failure on Gemini.

The [source receipt](results/receive-sources.json) pins nine public gen3 files
at the same Planet commit used by the [offload review](README.md). Source
objects were read from the existing Buildbox cache. No device command, firmware
inspection, capture, kernel build or driver code was involved.

## Native-data controls are not established

`wlanoidSetPacketFilter()` sends four bytes through command `0x0a`. The declared
normal supported filter mask contains directed, multicast and broadcast
selection; the self-test variant also includes all-multicast. A declared
promiscuous constant is not in either supported mask. These declarations do
not establish an RX header-translation switch.

The source also implements command `0xfc` under `CFG_SUPPORT_SNIFFER`, with
fields for enable, band, primary channel, channel width and secondary channels.
When the local monitor flag is active, the RX dispatcher sends data packets to
`nicRxProcessMonitorPacket()` instead of `nicRxProcessDataPacket()`. This is a
separate monitor path, not a demonstrated native-format control for an existing
managed connection. No monitor transition was issued.

The presence of translated and non-translated packet handling is therefore
insufficient to select native managed data. The inspected fields are positive
source facts; this is not an exhaustive claim that no other firmware control
exists.

## Retained packet-filter handler

A [bounded firmware follow-up](results/firmware-rx-filter.json) identifies the
mapped handler for command `0x0a` in the retained image. It obtains an initial
32-bit value through an unresolved callback, transforms a local copy according
to the command's filter word, and passes the result to a second unresolved
callback. The public filter header matches byte-for-byte between the pinned
Planet source and the inspected Gemian revision.

| Public filter request | Direct transformation of the local callback value |
| --- | --- |
| All multicast (`0x04`) | Clear bits 5 and 7; this branch takes precedence over ordinary multicast. |
| Multicast (`0x02`) without all multicast | Clear bit 5 and set bit 7. |
| Neither multicast request | Set bit 5; preserve bit 7. |
| Broadcast (`0x08`) | Clear bit 6 when requested; set it otherwise. |

The promiscuous (`0x20`) branch selects diagnostic calls but does not directly
change this local value. Directed (`0x01`) and higher request bits have no
explicit transformation in this selected body. These are internal callback
arguments, not identified hardware-register bits or an admitted programming
recipe. The callback implementations and diagnostic side effects remain
unresolved; zero returned by the handler does not validate their success.

This narrows the normal filter command to a concrete multicast/broadcast value
transformation without establishing a native-data selector. It does not prove
that the firmware has no other receive-format control. The 253-instruction
direct-flow walk exhausts with 20 calls, no invalid instructions and no
unresolved non-call transfers; callees are skipped under an assumed return.
No filter command, register access, radio action or firmware execution occurred.

## Receive representation

The base RX descriptor is 16 bytes. Its optional groups are selected by the
validity bitmap and appear in the source parser's order 4, 1, 2, 3:

| Group | Source-defined size | Content relevant to the receiver |
| --- | ---: | --- |
| 4 | 16 bytes | Original frame control, transmitter address, sequence/fragment, QoS and HT control for translated headers |
| 1 | 16 bytes | Packet-number bytes; cipher-specific interpretation remains separate |
| 2 | 8 bytes | Timestamp and CRC fields |
| 3 | 24 bytes | Six receive-vector words |

Those fields can support bounds checking and attribution, but they do not
prove that reconstructing arbitrary native 802.11 frames from Ethernet payloads
is lossless. Address layout, LLC handling, aggregation and cipher/PN semantics
must be established before choosing reconstruction. No reconstruction helper
is added.

## Reorder lifetime: distinct operations

| Edge | Inspected source behavior | Requirement for the future receiver |
| --- | --- | --- |
| BA creation/replacement | `qmAddRxBaEntry()` may flush a previous entry to the host before creating the replacement. It records station index, TID and a 12-bit sequence window. | Validate the negotiated window and tie the entry to the current station and firmware lifetime; replacement is not station destruction. |
| Firmware DELBA | `qmHandleEventRxDelBa()` calls deletion with `fgFlushToHost=TRUE`. | A normal agreement end may release queued packets only while the station remains valid and ordering is resolved. |
| Station deactivation | `qmDeactivateStaRec()` deletes all BA entries with `fgFlushToHost=FALSE`, returning retained RX buffers rather than delivering them. | Stop delivery, discard station queues and join timers/work before freeing the station. Do not reuse the DELBA delivery policy for station removal. |
| Missing-packet timeout | The timer constructs `EVENT_ID_CHECK_REORDER_BUBBLE` **locally** and queues it into the RX path using station index/TID. | Treat this as local work with cancellable lifetime, not a firmware stop/acknowledgement. A copied event without station incarnation is insufficient. |
| Firmware drop bitmap | The handler identifies a station/TID queue and marks sequence numbers that need not be awaited. | Validate bitmap extent, modular sequence arithmetic and agreement identity before advancing the queue. It is not a station-removal barrier. |
| Station removal | `cnmStaRecFree()` aborts local state, makes its index locally free, then sends command `0x14` with no requested response, completion callback or timeout callback. | Local cleanup proves neither that firmware has stopped using the index nor that all old RX/events have drained. |

The ordinary reorder window uses modulo 4096. A timeout decides how to handle a
missing packet inside an existing agreement; it does not prove firmware
quiescence or authorize station-index reuse. The source's extra window margin
is an implementation detail, not a negotiated capability to copy by default.

## Why a local generation alone is insufficient

The firmware ADDBA/DELBA and drop-event records name a station index and TID.
The inspected handlers do not validate their outer event sequence as a station
incarnation. The local allocator reuses the first entry marked not in use.
Consider two hypothetical histories at the point an identical DELBA arrives:

| History | Event meaning | Correct action |
| --- | --- | --- |
| Station index S belongs to a current connection; DELBA is from that connection | Current BA agreement ends | Close that agreement under its delivery policy |
| Old connection used S; S was reused; DELBA belongs to the old connection | Stale event | Do not close the new agreement |

If the event bytes and current host state are identical, attaching the current
host generation at receive time cannot distinguish these histories. This is a
protocol ambiguity demonstration, not evidence that the second history occurs
in the installed firmware. A proved ordering/drain rule could exclude it; the
inspected host removal call does not supply that proof.

Before index reuse, establish an attributable firmware completion and RX/event
ordering boundary, or another documented protocol distinction that excludes
old events. Do not invent a removal ACK, assume an unrelated query is a barrier,
or turn an arbitrary delay into proof. Keeping a table entry allocated forever
would postpone reuse, not satisfy the roadmap's reconnect requirement.

The command-completion follow-up narrows this further:

- In the multithreaded command path, no-response set commands enter the local
  done queue after `nicTxCmd()`. Response-bearing commands enter the pending
  command queue instead (`common/wlan_lib.c:1493–1507`). Local done is not a
  firmware event-drain acknowledgement.
- The station activation callback validates the current state and peer address
  before activating its queue (`mgmt/cnm_mem.c:790–804`). The active generic RX
  response path dispatches by pending command sequence
  (`nic/nic_rx.c:2431–2448`). The similarly named direct activation/deactivation
  cases at `1934–1965` are inside `#if 0`; they are not a removal witness.
  A valid activation reply still does not specify ordering of older data or
  unsolicited BA events.
- `EVENT_ID_RX_FLUSH=0x0e` exists as an unsolicited enum value. An exact gen3
  symbol search found only that declaration, with no selected handler or
  trigger. Its name alone supplies neither a wire layout nor barrier semantics.

The host source therefore does not establish the required fence. The next
useful evidence must attribute firmware-side ordering or an otherwise admitted
removal/reactivation observation to the exact image and event stream. The
question is specifically whether old data and BA events are excluded after a
positive boundary, not merely whether a new station can transmit. This record
admits no radio or firmware action.

The [retained firmware follow-up](FIRMWARE_STATION_LIFETIME.md) now separates
removal cleanup and command-object recycling from the optional activation
response. Its output callback remains unresolved, so the reply is not yet a
proved drain boundary for older station data or BA events.

## Encrypted translated data: replay ownership

The security follow-up keeps translated data as the design direction, but it
cannot rely on mac80211 to supply a missing replay check after Ethernet
handoff. The [security source receipt](results/security-sources.json) pins the
inspected files and ranges; this is public-source analysis, not a finding about
replay acceptance by the installed firmware.

At the pinned upstream revision, `__ieee80211_rx_handle_8023()` requires a
station and its eligible `fast_rx` state, then calls `ieee80211_rx_8023()`.
That delivery function performs accounting and forwarding; it does not run the
normal 802.11 decrypt/replay handlers. The **native-header** fast RX helper
separately tests `RX_FLAG_PN_VALIDATED | RX_FLAG_DECRYPTED` when a key is present.
Those tests must not be mistaken for checks on the direct Ethernet entry.
Fast-RX eligibility also excludes TKIP, WEP and unsupported ciphers; the
existence of a translated vendor path does not make every vendor cipher
eligible for this upstream interface.

The upstream status documentation assigns replay detection to the driver or
hardware when IV/ICV have been stripped. `RX_FLAG_PN_VALIDATED` asserts that
CCMP/GCMP replay protection already happened; it does not request that work.
Likewise, a decrypted flag is not evidence of replay protection.

The selected gen3 source provides narrower positive facts:

| Boundary | Inspected behavior | What remains unproved |
| --- | --- | --- |
| RX metadata | Optional group 1 contains 16 PN bytes. `HAL_RX_STATUS_GET_RSC` copies its first six bytes; `HAL_RX_STATUS_GET_PN` copies all 16. An exact gen3 symbol search finds only the two macro definitions. | Cipher-specific byte order, presence guarantees, replay owner and key incarnation cannot be inferred from the field or unused accessors. This search is not proof that firmware lacks replay protection. |
| RX acceptance | `nicRxProcessDataPacket()` uses the separate AMPDU/non-AMPDU acceptance masks, drops the error branch and reports qualifying TKIP MIC failures. | Passing these descriptor tests does not by itself prove monotonically valid PN, correct key generation or all cipher integrity semantics. |
| Normal Linux key addition | `mtk_cfg80211_add_key()` zeroes its parameter structure and copies the key and peer/index fields, but does not consume `params->seq` or `seq_len`. `wlanoidSetAddKey()` zeroes `CMD_802_11_KEY` and does not populate its `aucKeyRsc` field. | This ordinary path does not transfer a supplied nonzero receive-sequence floor to that command. It does not establish how firmware initializes or retains replay state. |
| Separate WAPI path | `wlanoidSetWapiKey()` explicitly copies 16 PN bytes into `aucKeyRsc`. | That cipher-specific assignment does not establish CCMP sequence semantics or repair the ordinary key path. |
| Key completion | The ordinary add-key command requests no generic response and returns pending after local enqueue. A distinct unsolicited `0x24` event matches BSS/peer and enables protected host TX. | Local completion and that event are different boundaries; neither establishes the exclusion of older queued RX or key incarnation. See the [firmware key-lifetime follow-up](FIRMWARE_KEY_LIFETIME.md). |

Implementation consequence: retain the PN and security metadata with **each
buffer across reordering**, and establish replay validation before encrypted
Ethernet delivery. A driver-owned validator needs an attributable key lifetime,
cipher-specific PN interpretation, the initial receive sequence, and the
appropriate peer/key/TID domains. Its ordering must account for legitimate
out-of-order arrivals and multiple MSDUs from one protected MPDU; a scalar PN
comparison at raw arrival is not sufficient. If firmware owns validation,
establish its equivalent guarantees and the error/completion observations that
let the driver rely on them. Neither choice is proved by this review.

Do not copy the ordinary vendor key-add path as the upstream sequence contract,
or advertise validated replay merely because a packet passed its RX masks.
The next decision-changing evidence is the CCMP group-1 interpretation and
replay/key-switch behavior for the exact firmware, including rekey and queued
old frames. The station reuse boundary above remains independently necessary.
No standalone replay helper is added before a real receiver and these inputs
exist; no radio test or firmware operation is admitted by this source review.

## Validation and scope

The cited public call sites, event layouts and command arguments were inspected
and their complete source hashes recorded. The six files already present in the
parent audit have unchanged hashes; two additional header identities and the
command-queue source are recorded here. The existing upstream mac80211 receive/reorder analysis remains
unchanged. Repository publication checks apply; there is no implementation to
compile or protocol fixture to call a runtime proof.

The preferred mac80211 direction is unchanged. Shared CONSYS/EMI/AP-DMA and
firmware load/stop requirements remain separate unresolved dependencies. No
mainline scanning, association, reconnect or traffic support is claimed.
