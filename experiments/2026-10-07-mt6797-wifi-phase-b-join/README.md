# Design: MT6797 Wi-Fi Phase B, bounded station authentication and association

| Field | Value |
| --- | --- |
| ID | `2026-10-07-mt6797-wifi-phase-b-join` |
| Status | Incomplete offline implementation pinned in a compile-only profile; MAC build and runtime gates remain open; no air test |
| Base | Phase A [runtime 3](../2026-10-06-mt6797-wifi-common-init/RUNTIME_3.md), package `3013daa6…` |
| Date | 2026-10-07 |
| Device action | None |

## Question

Can the mainline driver, after the proven Phase A common init and scan, run
one standard mac80211 Open System authentication and association exchange
with one owner-designated access point, using only the existing PIO command
port and polled receive? No DMA, no new interrupt, no AP credentials and no
data frames.

The Phase A artifacts and protocol stay unchanged. Phase B starts from a
separate profile and candidate.

## What the driver can do today

Audited offline against the Phase A tree (series `mt6797-a53-wifi-phase-a-compile`)
and the pinned vendor gen3 driver, which the vendor wlan Makefile selects for
`CONSYS_6797`.

| Area | Today | Source |
| --- | --- | --- |
| Host frame TX | None. `.tx` frees every frame without status | `mac.c` `mt6797_mac_tx` |
| Station state | `sta_state` returns `-EOPNOTSUPP`, so mac80211 cannot insert the AP station | `mac.c` `mt6797_mac_sta_state` |
| Firmware commands | TC4 PIO normal commands on WTDR1, a CID whitelist with fixed payloads, 256 single-use sequence numbers per firmware session | `normal_command.h`, `hif_command.h` |
| BSS activation | `BSS_ACTIVATE_CTRL` 0x11 sent for the scan, deactivated after it; the slot is never reused | `scan-wire.h`, `mac.c` |
| RX filter | `SET_RX_FILTER` 0x0a with BROADCAST only; vendor default adds DIRECTED and MULTICAST | `normal_command.h`; vendor [`wlan_oid.h`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/wlan_oid.h) |
| RX | Polled WRDR0/1 only while a scan is active; bounded per tick and in total | `mac.c` `mt6797_mac_scan_work`, `hif.c` |
| RX parsing | Firmware SW frames (type `0xe001`); only beacon and probe response, delivered to cfg80211 BSS inform, not to `ieee80211_rx` | `scan-wire.h`, `mac.c` |
| Events | Any unknown event fails the session, including TX done 0x0f, channel privilege 0x10 and STA activation 0x0c | `mac.c` |
| Scan | hw_scan, one-shot per boot, one channel, passive | `mac.c` |
| HW flags | `SIGNAL_DBM`, `NO_AUTO_VIF`; no TX ACK status | `mac.c` |

No host-built 802.11 frame has ever been transmitted by a mainline kernel on
this device. Phase B is the first host RF transmission.

## What the vendor join needs

Observation from the vendor source:

- The host builds every authentication and association frame
  ([`auth.c`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/mgmt/auth.c), [`saa_fsm.c`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/mgmt/saa_fsm.c)). The
  firmware does not run the join.
- Management frames go to TC4 through the command path as
  `COMMAND_TYPE_MANAGEMENT_FRAME`. Each frame is preceded by a 28-byte long
  `HW_MAC_TX_DESC_T` and written to the same WTDR1 port as commands
  ([`nic_tx.c`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_tx.c), [`nic_tx.h`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic/nic_tx.h)).
  The page count includes the descriptor. The vendor AHB write path has a PIO
  fallback ([`ahb.c`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/ahb.c)).
- Join order ([`ais_fsm.c`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/mgmt/ais_fsm.c)): activate the network, request
  the channel for JOIN, wait for the grant, create the STA record, run SAA,
  then update the BSS information after the association response.

| Purpose | Command or event | Response that proves it |
| --- | --- | --- |
| Activate BSS | `CMD_ID_BSS_ACTIVATE_CTRL` 0x11 | credit return only |
| STA record, pre-auth | `CMD_ID_UPDATE_STA_RECORD` 0x13, state 1, no response | credit return only |
| Channel for JOIN | `CMD_ID_CH_PRIVILEGE` 0x1c, REQ | `EVENT_ID_CH_PRIVILEGE` 0x10, status GRANT |
| Frame sent | management frame, PID with TX status to MCU | `EVENT_ID_TX_DONE` 0x0f, matching WLAN index and PID |
| STA record, associated | 0x13, state 3, response requested | `EVENT_ID_ACTIVATE_STA_REC` 0x0c as the command's response: same sequence number, STA index and AP address |
| BSS information | `CMD_ID_SET_BSS_INFO` 0x12, after association | credit return only |
| Teardown | 0x13 state 1 or `REMOVE_STA_RECORD` 0x14; 0x1c ABORT; 0x11 off | credit return; TX done for the deauthentication |

Struct layouts are in the vendor [`nic_cmd_event.h`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic_cmd_event.h).
None of these steps needs DMA or a HIF interrupt in the vendor design.

## Proposed first admission

One boot, one attempt, one access point. The steps run in this order. The
first failure stops the join. Teardown follows only while boot identity,
firmware health and link health remain verified; otherwise the driver fails
stop without further commands (see Bounds).

| # | Step | Kind | Stop condition |
| --- | --- | --- | --- |
| 1 | Phase A common init and readiness, unchanged | existing | any Phase A gate |
| 2 | One channel scan of the target's channel, then connect within the cfg80211 BSS lifetime | existing scan, new caller | target BSS absent |
| 3 | RX filter DIRECTED and BROADCAST | changed payload | no credit return |
| 4 | Retain the active AIS BSS from the completed scan: BSS 0, own-MAC 1, BMC 0 | new Phase B lifetime | incomplete/failed scan or ownership fence not met |
| 5 | STA record pre-auth for the AP | new command | no credit return |
| 6 | Channel privilege REQ for JOIN on the target channel | new command and event | no grant within the budget |
| 7 | TX Open System authentication, sequence 1 | **first RF TX** | no TX done, or TX status not success |
| 8 | RX authentication response, delivered to mac80211 | new parser | none within the budget |
| 9 | TX association request | RF TX | no TX done |
| 10 | RX association response, any status | new parser | none within the budget |
| 11 | If accepted: STA record state 3, then immediate deauthentication | new command, RF TX | no 0x0c event or no TX done |
| 12 | Teardown: STA record removal, channel ABORT, BSS off, stop polling | new and existing | only while identity and firmware and link health remain verified |

The decision is the association response. Any status, accepted or refused,
proves host TX, firmware TX done and directed management RX. An accepted
association with a correct STA activation event proves the join. No data frame,
EAPOL exchange or key is part of this admission.

### Bounds

- **Host submissions are not RF frames.** The host submits at most one
  authentication, one association request and one deauthentication. Each
  submission can produce several RF transmissions: firmware retries up to the
  descriptor's retry limit within its lifetime, plus the hardware's automatic
  ACK frames for frames it receives. The descriptor pins a fixed retry limit
  and lifetime, taken from the vendor values and stated in the candidate, and
  the record keeps host submissions, firmware retries and automatic MAC ACKs
  apart.
- **Duplicates.** The driver refuses a second submission of the same subtype
  in the same join state, mac80211 retries included, not merely a fourth frame.
  TX ACK status comes from the TX-done event, so mac80211 sees real status.
- **Frame types.** `.tx` accepts only authentication, association request
  and deauthentication frames addressed to the designated BSSID. It drops and
  counts every data, null or other management frame.
- **RX.** Polled only inside a join window of at most 10 s, with the existing
  per-tick and total packet bounds. Only authentication, association response,
  deauthentication and disassociation frames from the designated BSSID go to
  mac80211; beacons stay with cfg80211 as now.
- **Channel.** Only the scanned channel, which must be non-DFS and not NO_IR.
  The first proposal uses channel 40 again if the designated AP is there.
- **Budgets.** Firmware sequence numbers and TC4 pages are counted before the
  run; Phase B uses fewer than 20 more commands and frames.
- **Firmware health and teardown.** Teardown commands run only while the boot
  identity, firmware health and link health are still verified. A WHISR
  firmware-abort bit, a stopped firmware line, or any unknown, unparsed or
  unmatched event makes the firmware's effects unknown. The driver then sends
  no further command, preserves the evidence, fails stop, and leaves recovery
  to the reviewed SoC recovery path. It sends no speculative teardown command.
- **Partial states and asynchronous input.** The record accounts for every
  partial success: BSS active, STA record created, channel granted,
  authenticated, associated. It also counts asynchronous beacons, credit
  returns and expected unsolicited events, including a TX done for each
  submission, separately from the awaited responses. Budgets cover these too.

### Access point and credentials

- The owner designates one owner-controlled AP by a private input file holding
  its SSID, BSSID and channel. These identities stay out of the repository, and
  the driver and tools assume no SSID or BSSID.
- No credentials are used or needed. Open System authentication precedes RSN
  on WPA2 networks. Without an RSN element, a WPA2 AP may refuse the
  association; that refusal still answers the question.
- An open test network accepted by the owner would also prove an accepted
  association. That choice is the owner's.

## Open gaps to resolve before implementation

1. **TX descriptor.** The 28-byte layout, WLAN index, own-MAC index, queue
   index (inference: `0x88` against `0x80` for commands), header format,
   PID and TXS-to-MCU bits, lifetime, retry limit and fixed rate must be
   derived from the vendor encoder and checked by a fixture against vendor
   vectors.
2. **WLAN and STA index allocation.** The vendor host picks the WLAN index.
   The design needs one fixed index for the AP and the broadcast index already
   used for the BSS.
3. **Unicast forwarding.** Whether the firmware forwards directed management
   frames to the host depends on the DIRECTED filter bit; it is unproven.
4. **RX port.** The runtime-3 sealed log records the first frame (length 442,
   type `0xee01`) and the count of 15, but no RX port marker. WRDR0 versus
   WRDR1 cannot be inferred, so the join poller keeps both ports, each bounded.
5. **Slot reuse.** Resolved by the Phase B slot-lifetime delta below. It is a
   continuous ownership of the same slots, not a release/reallocation.
6. **One-shot scan.** cfg80211 rescans when its BSS entry has expired. The
   connect must follow the single scan quickly, or the connect path must not
   trigger a second scan.
7. **Event handling.** Events 0x0f, 0x10 and 0x0c need parsers. The vendor's
   standalone 0x0c handler is compiled out; the event arrives as the response
   to the state-3 STA record command and is matched by the pending command's
   sequence number, then checked against the STA index and AP address. The
   parser matches event ID, expected sequence and exact payload, never the
   event ID alone. TX done is asynchronous and matches the frame's PID and WLAN
   index. Unknown events still fail the session.
8. **mac80211 hooks.** `sta_state`, `mgd_prepare_tx`, `mgd_complete_tx`,
   `tx` and `ieee80211_rx_ni` delivery are new. `vif_cfg_changed` and
   `link_info_changed` can stay empty for this admission.
9. **Connection monitoring.** After association, mac80211 expects beacons. The
   immediate deauthentication avoids a persistent poller.
10. **Credit deadline.** Whether the firmware needs credit returned within a
    deadline while frames are pending is not known; the poller reconciles
    credit after each step.

## Phase B delta: slot ownership and lifetime

Phase A's `scan-wire.h` reserves AIS BSS 0, own-MAC index 1 and unencrypted
BMC WLAN index 0 until the retained firmware session ends. It records the scan
as used, and treats BSS deactivation as a credit return, not as an activation
or drain acknowledgement. Phase A's code and protocol stay unchanged. Phase B
needs those slots and states its own rule instead of reusing them silently.

**Correction under implementation review: retain one AIS owner.** The earlier
500 ms quiet-window transfer rule is withdrawn: silence is not a firmware
FIFO drain, and a beacon carries no scan-versus-join epoch. The separate
Phase B profile will retain the same BSS 0, own-MAC 1 and BMC 0 continuously
from activation through one successful scan, one join and terminal teardown
or recovery. It will omit scan-end deactivation and a second activation.
Phase A profiles and artifacts retain their existing behavior.

The [lifetime review](BSS_LIFETIME_REVIEW.md) records the public vendor
connection-path evidence and required ownership gates. Its direction was
reviewed as sound; this is implementation planning, not candidate admission.
A cancelled, failed or partial scan never admits a join. The scan consumer
must be quiesced safely before the join becomes the sole FIFO consumer; host
work completion does not prove firmware silence. One vif/MAC owner and the
consumed scan sequence remain retired against replacement or reuse.

Any late/duplicate scan completion fails stop, with no second completion
notification. Parseable beacons are asynchronous frames filtered by current
identity/channel policy and finite budgets; they cannot be labeled scan-owned
solely from arrival time. Directed responses and firmware events still need
the current protocol stage and single-use pending token/command ledger.

**Ownership after the join.** The join owns BSS 0, own-MAC 1, BMC 0 and AP
pairwise WLAN index 1 until its teardown completes under the health rule, or
until the firmware session ends. WLAN index 1 is a project reservation, not a
vendor-fixed assignment: the vendor allocates the first free entry from 0 to
30. Once claimed, no slot returns to the scan. A second scan in the same
firmware session stays refused, as in Phase A. PIDs are per WLAN index, fresh
and unique within the attempt, from 1 to 127 with no wrap or reuse.

## Effects to review

- First host RF transmission: three host submissions at most, on one permitted
  channel, each with the pinned firmware retry limit and lifetime.
- New firmware state: one BSS activation, one STA record and one channel grant,
  removed in teardown only while health remains verified.
- Phase A common init already applies radio configuration: coexistence, PA
  rails, RF calibration and antenna mode. Phase B adds no new radio
  configuration beyond the effects listed here. It writes no storage, NVRAM or
  calibration data, and enables no DMA or interrupt.

## Gate before any air test

No authentication or association attempt runs until the candidate, this
protocol, the effect review and the owner's private AP target are all concrete
and reviewed.

## After this admission

Bounded PIO data TX and RX come only after association evidence, in a separate
admission. DMA and interrupts stay out of scope until then.

The current [offline implementation checkpoint](OFFLINE_IMPLEMENTATION.md)
records selected preparation patches, validation and missing join callbacks.
