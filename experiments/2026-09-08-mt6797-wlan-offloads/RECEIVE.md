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
