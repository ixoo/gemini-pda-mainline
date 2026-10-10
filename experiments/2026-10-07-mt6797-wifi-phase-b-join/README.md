# Design: MT6797 Wi-Fi Phase B, bounded station authentication and association

| Field | Value |
| --- | --- |
| ID | `2026-10-07-mt6797-wifi-phase-b-join` |
| Status | Runtime 4 ([RUNTIME_4](RUNTIME_4.md)) logged no driver refusal; the reconstructed cause is cfg80211's privacy-sensitive BSS lookup; the reviewed connect helper and proposal 0144 are built as [compile 9](COMPILE_9.md) runtime 5 ([RUNTIME_5](RUNTIME_5.md)) measured the EINVAL at mac80211's station setup: the driver informed cfg80211 directly so mac80211's BSS rate record was empty; proposal 0145 delivers scanned beacons through mac80211, built as [compile 10](COMPILE_10.md) runtime 6 ([RUNTIME_6](RUNTIME_6.md)) demonstrated the first management exchange: authentication accepted, association denied with status 45, cleanup stopped with an unmeasured protocol error; proposal 0146 names the failing branch and ledger terms, built as [compile 11](COMPILE_11.md) runtime 7 ([RUNTIME_7](RUNTIME_7.md)) measured the cleanup's protocol error: an unsolicited BSS absence/presence event refused by the control-event parser; proposal 0147 admits it under a strict teardown contract, reviewed and built as [compile 12](COMPILE_12.md) runtime 8 ([RUNTIME_8](RUNTIME_8.md)) is the first healthy bounded join: authentication accepted, association denied as expected without an RSN element, admitted absence indication, finite teardown with all pages returned; Phase C1 ([PHASE_C](PHASE_C.md)) is reviewed and built as [compile 13](COMPILE_13.md) and [runtime 9](RUNTIME_9.md) on candidate 8 stopped before the association transmission at the driver's own admission predicate, which refused the RSN element; proposal 0149 is reviewed and built as [compile 14](COMPILE_14.md) and [runtime 10](RUNTIME_10.md) on candidate 9 measured the first accepted association (status 0) and then refused the next received packet, a 147-byte vector-less data packet, at the frame gate; proposals 0150 and 0151 are reviewed and built as [compile 15](COMPILE_15.md) and [runtime 11](RUNTIME_11.md) on candidate 10 named the refused packet's header: a translated clear frame from the target with the EAPOL Ethernet type and BSSID tag 15, refused by the decoder's byte-7 check; proposal 0152 is reviewed and built as [compile 16](COMPILE_16.md) and [runtime 12](RUNTIME_12.md) on candidate 11 passed Phase C1: accepted association completed in mac80211, station activated, the AP's first frame observed as clear EAPOL-Key framing (translated, no RX vector, BSSID tag 15, before activation), healthy teardown; Phase C2 (keys) is built as [compile 18](COMPILE_18.md) with proposals 0153 to 0157 and installed as candidate 13 ([deployment 13](results/deployment-13.json)); [runtime 13](RUNTIME_13.md) stopped before any scan because the pinned supplicant does not implement `-f` (usage text, exit 0); [runtime 14](RUNTIME_14.md) with the corrected invocation initialised the supplicant and stopped at the missing packet socket (`CONFIG_PACKET` unset by the usbdiag fragment); the Wi-Fi fragment restores it, built as [compile 19](COMPILE_19.md) and composed as candidate 14; [runtime 15](RUNTIME_15.md), the first handshake measurement, delivered message 1, sent message 2 and refused the next EAPOL-shaped packet at its RXD BSSID tag (1 after activation, never measured before; message 3 inferred, unvalidated); proposal 0158 binds the two measured tags, built as [compile 20](COMPILE_20.md) and composed as candidate 15; [runtime 16](RUNTIME_16.md) delivered both EAPOL frames and sent both replies, then refused a 136-byte software frame the summary could not describe, before any key command; proposal 0159 names such frames and refused keys (diagnostic only), built as [compile 21](COMPILE_21.md) and composed as candidate 16; the diagnostic [runtime 17](RUNTIME_17.md) delivered message 1, sent message 2 and refused a fully named protected group-addressed data frame from the AP before message 3 (the runtime-16 software frame did not recur); proposal 0160 discards exactly that measured class undelivered while the station holds no group key, built as [compile 22](COMPILE_22.md) and composed as candidate 17; [runtime 18](RUNTIME_18.md) demonstrated all four handshake messages on the air (keys offered by the supplicant), then refused the target's directed clear Action frame before any key command; proposal 0161 discards exactly that measured class undelivered, built as [compile 23](COMPILE_23.md) and composed as candidate 18; [runtime 19](RUNTIME_19.md) discarded the Action frame, submitted the pairwise key command and then refused the firmware's unsolicited add-key-done event (id 0x24, consistent with the pinned source, ownership unverified); proposal 0162 admits it once after the pairwise command, built as [compile 24](COMPILE_24.md) for candidate 19; not operational; data and keys remain incomplete |
| Base | Phase A [runtime 3](../2026-10-06-mt6797-wifi-common-init/RUNTIME_3.md), package `3013daa6…` |
| Date | 2026-10-07 |
| Device action | One boot, WMT preparation/negotiation/common-init attempt, evidence sealing, A53 regression and confirmed Gemian recovery; no scan or join |

## Question

Can the mainline driver, after the proven Phase A common init and scan, run
one standard mac80211 Open System authentication and association exchange
with one owner-designated access point, using only the existing PIO command
port and polled receive? No DMA, no new interrupt, no AP credentials and no
data frames.

The Phase A artifacts and protocol stay unchanged. Phase B starts from a
separate profile and candidate.

The [first runtime](RUNTIME_1.md) failed common init at step 5 before any WLAN
initialization or management TX. Its log is sealed and Gemian recovery is
confirmed. The next candidate needs a diagnosis or a decision-changing
measurement of that early transport failure.

## Next-stage EAPOL receive preparation

Proposal [0140](../../patches/proposals/0140-wifi-mt6797-decode-clear-EAPOL-receive-layouts.patch)
adds an original, unlinked decoder needed for the first WPA2 EAPOL-Key receive.
The management-only parser cannot handle ordinary RX-data packets. The public
gen3 [RXD definitions](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic/nic_rx.h)
and [RFB parser](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_rx.c)
describe native and Ethernet-translated layouts. Translation needs group 4's
AP and sequence metadata to reconstruct the native header for mac80211.

The helper accepts only clear, nonaggregated, non-QoS From-DS unicast
WPA2-PSK EAPOL-Key frames with a 16-byte MIC field. It validates channel,
BSS/WLAN index, copied peer identity,
RX error flags, complete group/padding bounds, exact declared body and key-data
lengths before returning spans and a reconstructed prefix. It does not validate
handshake state, nonce, replay or MIC; those belong to the supplicant. It has no
transport, key installation or radio effect, and no call site. Admission and
associated-peer lifetime checks remain the caller's responsibility.

The 95-byte fixed key body uses the standard 32-byte nonce and 16-byte MIC.
This was checked against the pinned supplicant
[common definitions](https://android.googlesource.com/platform/external/wpa_supplicant_8/+/073b9ad1b7e6876417fe0927c6364245ecf26d8b/src/common/wpa_common.h)
(source SHA-256 `319284b9b06f01686a2aa93ba496fad49f49aaf07c88e1492bc3702ecb8e0f1c`).
The public vendor `privacy.h` structure declares a 16-byte nonce; that
inconsistent structure was not used to derive the EAPOL framing offsets.

The [fixture](tests/eapol-rx-test.c) passed ASan/UBSan on a Buildbox across 24
native/translated group and padding combinations, every truncated allocation,
malformed metadata, peer mismatch and the 2048-byte body bound. Header-file
Checkpatch found no errors or warnings. The format-patch check has one reminder
about MAINTAINERS for a new file; this unlinked internal experiment has no
upstream maintainer entry or DCO certification. Reproduce with
[run-eapol-test.py](tests/run-eapol-test.py)
against a Phase B tree with proposal 0140 applied. No profile selects this
patch, no kernel build changed, and the installed management-test candidate and
its protocol remain unchanged. These fixtures do not establish the device's
actual RX layout or demonstrate an EAPOL exchange. Runtime integration follows
the first management-test result and a separate data/key protocol.

## What the Phase A baseline could do

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
| 5 | Channel privilege REQ for JOIN on the target channel | new command and event | no grant within the budget |
| 6 | STA record pre-auth for the AP | new command | no credit return |
| 7 | TX Open System authentication, sequence 1 | **first RF TX** | no TX done, or TX status not success |
| 8 | RX authentication response, delivered to mac80211 | new parser | none within the budget |
| 9 | TX association request | RF TX | no TX done |
| 10 | RX association response, any status | new parser | none within the budget |
| 11 | If accepted: BSS/RLM, STA record state 3, then immediate deauthentication | new command, RF TX | no 0x0c event or no TX done |
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

The first concrete candidate and bounded execution are pinned in
[PROTOCOL.md](PROTOCOL.md), with the full build in [COMPILE_6.md](COMPILE_6.md).

## Gate before any air test

No authentication or association attempt runs until the candidate, this
protocol, the effect review and the owner's private AP target are all concrete
and reviewed.

## After this admission

Bounded PIO data TX and RX come only after association evidence, in a separate
admission. DMA and interrupts stay out of scope until then.

The current [offline implementation checkpoint](OFFLINE_IMPLEMENTATION.md)
records selected preparation patches, validation and missing join callbacks.

## Runtime 1 review and fixes (2026-10-06)

[RUNTIME_1.md](RUNTIME_1.md) records the first boot, which failed WMT common
init at step 5 before any WLAN initialization. [REVIEW_1.md](REVIEW_1.md)
records the read-only code review that followed. Two patches came out of it:

- [0141](../../patches/proposals/0141-soc-mediatek-tolerate-a-no-source-BTIF-interrupt-during-a-WMT-exchange.patch):
  the WMT full I/O treats a non-initial BTIF interrupt whose IIR shows "no
  interrupt pending" (bit 0 set, bits 1, 2 and 6 clear) as benign. It counts
  it against the unchanged service and deadline budgets, touches no FIFO or
  register and makes no protocol transition. Every other unexpected cause
  still fails stop. The last IIR and the no-source count are stored and
  printed in the existing common-init failure footer.
- [0142](../../patches/proposals/0142-wifi-mt6797-release-the-driver-owned-deauthentication-frame-on-teardown.patch):
  `join_close` and the worker's failure path clear `join_internal` under the
  MAC mutex and free the driver-built deauthentication frame with
  `dev_kfree_skb`, returning only mac80211's own frames with
  `ieee80211_free_txskb`.

Both are selected only in `mt6797-a53-wifi-phase-b-compile`; the resulting
package is [compile 7](COMPILE_7.md).

**First-admission policy, stated explicitly.** In this admission any
`mgd_prepare_tx` the driver does not admit, including a mac80211
authentication retry and an unexpected disconnect between authentication and
association, fails stop: the session records an error and closes without a
deauthentication frame. That is deliberate for one bounded attempt. Normal
product disconnect and retry handling remains incomplete and is a later step.

New fixtures, run with the production headers and functions (no mirrored
copies, no stubbed close):

- `tests/run-wmt-irq-test.py` with `wmt-full-irq-test.c`: partial TX then a
  no-source interrupt then valid completion; a fully submitted command then a
  no-source interrupt then the reply; a no-source storm against the service
  budget and the deadline; and an unsupported pending cause, which still
  refuses.
- `tests/run-ownership-test.py` with `join-ownership-test.c`: it extracts
  `struct mt6797_mac` and the production worker, close and wait functions from
  the selected `mac.c`. It covers an internal deauthentication TX done with
  NACK, an unknown event with the internal frame in flight, the same with a
  mac80211 frame in flight and the internal frame queued, a close during the
  management wait, and a close with only mac80211 frames. Every frame is
  released exactly once by the owner's function. It fails on the pre-0142
  `mac.c`.

## Compile 24 and candidate 19 (2026-10-10)

[Compile 24](COMPILE_24.md) (input `4be81db8`, package `295e881b…`, image
`7b3a1dad…`, config `975f8703…` and DT unchanged, 661 patches, the two
baseline warnings, zero driver warnings) built proposal 0162.
`build-candidate.py` and `prepare-runtime.py` pin the input and package; the
owner composes candidate 19 with candidate 18's RAM root unchanged, and the
deployment-19 and runtime-20 bindings wait for its receipt.

## Runtime 19 result and proposal 0162 (2026-10-10)

[Runtime 19](RUNTIME_19.md): both EAPOL frames delivered, messages 2 and 4
sent, the target's Action frame discarded once as 0161 intended, the pairwise
key command submitted and its page credit returned; then the control event
dispatcher refused an unsolicited 16-byte event with id `0x24`, which the
pinned gen3 source defines as `EVENT_ID_ADD_PKEY_DONE` with an 8-byte payload
of BSS index, reserved byte and station address. The payload was not
recorded, so the event is consistent with the completion of the submitted
command and its ownership is unverified. Proposal 0162 admits it exactly
once after a pairwise key command while the station is active and before
the teardown, comparing (never logging) the BSS index and the target's
address, and records `key done: pairwise bss=0 peer=1`; the classifier
requires that record for the handshake-path pass. No key is proven installed.

## Runtime 19 bindings (2026-10-10)

Candidate 18 pairs the [compile 23](COMPILE_23.md) package `4f07d571…` (input
`f5477df6`, proposal 0161) with candidate 17's RAM root byte-identical
(`449832a3…`, 63 members), the same board DT `25ab60f4…` and kernel config
`975f8703…`; kernel image `104cec2a…` (6643164 bytes), boot image
`1de73be9…` (12296192 bytes), full padded boot2 `dfdf6bcb…`. The owner composed
and validated it privately with the reviewed composer; the committed receipt
[results/candidate-18.json](results/candidate-18.json) (SHA-256 `b0d577ba…`)
is that receipt's exact bytes and `runtime-19/results/candidate.json` its
copy. [Deployment 18](results/deployment-18.json) wrote it over the installed
candidate 17 (`5135b2f8…`) with the full readback matching; the device is
powered off awaiting the owner's boot2 start, and nothing about Wi-Fi is
measured by that. [RUNTIME_19_PREPARATION](RUNTIME_19_PREPARATION.md) states
the hypothesis. Bindings, with every prior receipt, copy and piece of
evidence untouched:

| Adapter | Runtime 19 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT f5477df6…`, `PACKAGE 4f07d571…`, exact packet-socket config delta, `--helper` `bc499f28…`, `--supplicant` `0487b710…` |
| `install-passive.py` | predecessor `5135b2f8…` (installed candidate 17), receipt `mt6797-wifi-phase-b-deployment-18`, `results/candidate-18.json`, slot filled |
| `capture-private.py` | `capture-19`, `session-19/deployment-summary.txt`, `results/candidate-18.json`, slot filled |
| `passive-session.py` | `results/candidate-18.json`; 63-member RAM root with the required supplicant |
| `passive-host.py` | `session-19`, `capture-19`; identity `runtime-19/results/candidate.json`; PSK-bound script required; C2 session pieces at `4983499e` |
| `prepare-runtime.py` | `results/candidate-18.json` against the compile-23 input and package, both slots, predecessor `5135b2f8…`, the PSK-bound script; creates `wifi-phase-b/session-19` only and leaves `capture-19` absent |
| `join-once.sh` | unchanged since `4983499e` |

## Compile 23 and candidate 18 (2026-10-10)

[Compile 23](COMPILE_23.md) (input `f5477df6`, package `4f07d571…`, image
`104cec2a…`, config `975f8703…` and DT unchanged, 660 patches, the two
baseline warnings, zero driver warnings) built proposal 0161.
`build-candidate.py` and `prepare-runtime.py` pin the input and package; the
owner composes candidate 18 with candidate 17's RAM root unchanged, and the
deployment-18 and runtime-19 bindings wait for its receipt.

## Runtime 18 result and proposal 0161 (2026-10-10)

[Runtime 18](RUNTIME_18.md): both EAPOL frames delivered, messages 2 and 4
sent, the supplicant completed its handshake and offered both keys; then the
gate refused a 136-byte software frame now named in full: match `0x02`
(unicast-to-me only), header 24 unpadded, BSSID field 1, WLAN index 1, TID
and security mode 0, status `0xe000`, frame control `0x00d0` (Action, no
flags, unprotected), receiver this station, transmitter the target; body and
category unrecorded. The pairwise key install was waiting on the ledger when
the worker stopped (-71) and the group install met the stopped lifetime
(-95); no firmware key command exists. Proposal 0161 discards exactly that
measured class undelivered while the station is active, each recorded, at
most eight; everything else stays refused; no new host submission is made.
Runtime 16's unclassified 136-byte frame is consistent with this class, an
inference. The 0160 group-data discard was not exercised (no group frame
arrived before the stop).

## Runtime 18 bindings (2026-10-10)

Candidate 17 pairs the [compile 22](COMPILE_22.md) package `096b50b5…` (input
`6a3b000d`, proposal 0160) with candidate 16's RAM root byte-identical
(`449832a3…`, 63 members), the same board DT `25ab60f4…` and kernel config
`975f8703…`; kernel image `13dbdeb6…` (6642715 bytes), boot image `59a2c509…`
(12296192 bytes), full padded boot2 `5135b2f8…`. The owner composed and
validated it privately with the reviewed composer; the committed receipt
[results/candidate-17.json](results/candidate-17.json) (SHA-256 `cf5958f2…`)
is that receipt's exact bytes and `runtime-18/results/candidate.json` its
copy. [Deployment 17](results/deployment-17.json) wrote it over the installed
candidate 16 (`c773902c…`) with the full readback matching; the device is
powered off awaiting the owner's boot2 start, and nothing about Wi-Fi is
measured by that. [RUNTIME_18_PREPARATION](RUNTIME_18_PREPARATION.md) states
the hypothesis. Bindings, with every prior receipt, copy and piece of
evidence untouched:

| Adapter | Runtime 18 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT 6a3b000d…`, `PACKAGE 096b50b5…`, exact packet-socket config delta, `--helper` `bc499f28…`, `--supplicant` `0487b710…` |
| `install-passive.py` | predecessor `c773902c…` (installed candidate 16), receipt `mt6797-wifi-phase-b-deployment-17`, `results/candidate-17.json`, slot filled |
| `capture-private.py` | `capture-18`, `session-18/deployment-summary.txt`, `results/candidate-17.json`, slot filled |
| `passive-session.py` | `results/candidate-17.json`; 63-member RAM root with the required supplicant |
| `passive-host.py` | `session-18`, `capture-18`; identity `runtime-18/results/candidate.json`; PSK-bound script required; C2 session pieces at `4983499e` |
| `prepare-runtime.py` | `results/candidate-17.json` against the compile-22 input and package, both slots, predecessor `c773902c…`, the PSK-bound script; creates `wifi-phase-b/session-18` only and leaves `capture-18` absent |
| `join-once.sh` | unchanged since `4983499e` |

## Compile 22 and candidate 17 (2026-10-10)

[Compile 22](COMPILE_22.md) (input `6a3b000d`, package `096b50b5…`, image
`13dbdeb6…`, config `975f8703…` and DT unchanged, 659 patches, the two
baseline warnings, zero driver warnings) built proposal 0160.
`build-candidate.py` and `prepare-runtime.py` pin the input and package; the
owner composes candidate 17 with candidate 16's RAM root unchanged, and the
deployment-17 and runtime-18 bindings wait for its receipt.

## Runtime 17 result and proposal 0160 (2026-10-10)

[Runtime 17](RUNTIME_17.md), the diagnostic boot: message 1 delivered, message
2 sent, then the gate refused a 110-byte native data RXD now fully named by
proposal 0159: broadcast match bit without unicast-to-me, BSSID field 1, WLAN
index 0, security mode 0, status `0xc004` (cipher mismatch, no error flag),
frame control `0x6208` (data, FromDS, More Data, Protected), transmitter the
target, receiver not this station; body and receiver address unrecorded. The
AP's ordinary group-addressed traffic, encrypted with a group key the station
does not hold before message 3, can end the join at random. Proposal 0160
discards exactly that measured class undelivered and uninterpreted while the
station is active and before a group key command has returned its credit,
records the first eight, caps at sixty-four, and leaves every other refusal
(unicast protected, decrypted, other status, the runtime-16 software frame)
unchanged. The channel-40 flag was measured clear during the join.

## Runtime 17 bindings (2026-10-10)

Candidate 16 pairs the [compile 21](COMPILE_21.md) package `f429ebe9…` (input
`4983499e`, diagnostic proposal 0159) with candidate 15's RAM root
byte-identical (`449832a3…`, 63 members), the same board DT `25ab60f4…` and
kernel config `975f8703…`; kernel image `4429011b…` (6642539 bytes), boot
image `41699010…` (12296192 bytes), full padded boot2 `c773902c…`. The owner
composed and validated it privately with the reviewed composer; the committed
receipt [results/candidate-16.json](results/candidate-16.json) (SHA-256
`1aaf85ea…`) is that receipt's exact bytes and `runtime-17/results/candidate.json`
its copy. [Deployment 16](results/deployment-16.json) wrote it over the
installed candidate 15 (`eb43ddef…`) with the full readback matching; the
device is powered off awaiting the owner's boot2 start. [RUNTIME_17_PREPARATION](RUNTIME_17_PREPARATION.md) states
the diagnostic hypothesis. Bindings, with every prior receipt, copy and piece
of evidence untouched:

| Adapter | Runtime 17 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT 4983499e…`, `PACKAGE f429ebe9…`, exact packet-socket config delta, `--helper` `bc499f28…`, `--supplicant` `0487b710…` |
| `install-passive.py` | predecessor `eb43ddef…` (installed candidate 15), receipt `mt6797-wifi-phase-b-deployment-16`, `results/candidate-16.json`, slot filled |
| `capture-private.py` | `capture-17`, `session-17/deployment-summary.txt`, `results/candidate-16.json`, slot filled |
| `passive-session.py` | `results/candidate-16.json`; 63-member RAM root with the required supplicant |
| `passive-host.py` | `session-17`, `capture-17`; identity `runtime-17/results/candidate.json`; PSK-bound script required; C2 session pieces at `4983499e` |
| `prepare-runtime.py` | `results/candidate-16.json` against the compile-21 input and package, both slots, predecessor `eb43ddef…`, the PSK-bound script; creates `wifi-phase-b/session-17` only and leaves `capture-17` absent |
| `join-once.sh` | the `4983499e` version (prefix-free message-3 phrase, key-install counts, channel-40 state sampled during the join) |

## Compile 21 and candidate 16 (2026-10-10)

[Compile 21](COMPILE_21.md) (input `4983499e`, package `f429ebe9…`, image
`4429011b…`, config `975f8703…` and DT unchanged, 658 patches, the two
baseline warnings, zero driver warnings) built the diagnostic proposal 0159.
`build-candidate.py` and `prepare-runtime.py` pin the input and package; the
owner composes candidate 16 with candidate 15's RAM root unchanged, and
deployment 16 and runtime 17 bindings follow its receipt.

## Runtime 16 result and proposal 0159 (2026-10-10)

[Runtime 16](RUNTIME_16.md): both EAPOL frames delivered (tags 15 then 1),
messages 2 and 4 sent with their credits, the supplicant completed its
handshake and offered both keys; then the frame gate refused a 136-byte
software-defined frame (type `0xee01`, the vendor's management-processing
layout) whose fields the summary could not interpret, and the join
fail-stopped before any key command. Proposal 0159 is diagnostic only: the
refusal summary interprets software frames and adds the security mode and
receiver/transmitter flags, and refused key commands are named; no receive
admission changes. The tooling corrects the message-3 phrase (`RSN:` prefix
on the WPA2 path), counts the key installs, and gates the channel-40 flag on
the state sampled during the join, because cfg80211 restores the world-domain
no-IR flag once every interface is idle after the disconnection.

## Runtime 16 bindings (2026-10-10)

Candidate 15 pairs the [compile 20](COMPILE_20.md) package `ee32128d…` (input
`67a37ca1`, proposal 0158) with candidate 14's RAM root byte-identical
(`449832a3…`, 63 members), the same board DT `25ab60f4…` and kernel config
`975f8703…`; kernel image `6aba6108…`, boot image `b0c1ff8d…` (12296192
bytes), full padded boot2 `eb43ddef…`. The owner composed and validated it
privately with the reviewed composer; the committed receipt
[results/candidate-15.json](results/candidate-15.json) (SHA-256 `a99fc4f9…`)
is that receipt's exact bytes and `runtime-16/results/candidate.json` its copy.
[Deployment 15](results/deployment-15.json) wrote it over the installed
candidate 14 (`911e3d67…`) with the full readback matching; the device is
powered off awaiting the owner's boot2 start. [RUNTIME_16_PREPARATION](RUNTIME_16_PREPARATION.md) states the
measured change and the C2 hypothesis. Bindings, with every prior receipt,
copy and piece of evidence untouched:

| Adapter | Runtime 16 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT 67a37ca1…`, `PACKAGE ee32128d…`, exact packet-socket config delta, `--helper` `bc499f28…`, `--supplicant` `0487b710…` |
| `install-passive.py` | predecessor `911e3d67…` (installed candidate 14), receipt `mt6797-wifi-phase-b-deployment-15`, `results/candidate-15.json`, slot filled |
| `capture-private.py` | `capture-16`, `session-16/deployment-summary.txt`, `results/candidate-15.json`, slot filled |
| `passive-session.py` | `results/candidate-15.json`; 63-member RAM root with the required supplicant |
| `passive-host.py` | `session-16`, `capture-16`; identity `runtime-16/results/candidate.json`; PSK-bound script required; C2 session pieces with the corrected phrase and channel-40 fields |
| `prepare-runtime.py` | `results/candidate-15.json` against the compile-20 input and package, both slots, predecessor `911e3d67…`, the PSK-bound script; creates `wifi-phase-b/session-16` only and leaves `capture-16` absent |
| `join-once.sh` | the `67a37ca1` version (printed phrases, channel-40 diagnostics, no `-f`) |

## Compile 20 and candidate 15 (2026-10-10)

[Compile 20](COMPILE_20.md) (input `67a37ca1`, package `ee32128d…`, image
`6aba6108…`, config `975f8703…` and DT unchanged, 657 patches, the two
baseline warnings, zero driver warnings) built proposal 0158.
`build-candidate.py` and `prepare-runtime.py` pin the input and package; the
owner composes candidate 15 with candidate 14's RAM root unchanged, and
deployment 15 and runtime 16 bindings follow its receipt.

## Runtime 15 result and proposal 0158 (2026-10-10)

[Runtime 15](RUNTIME_15.md): accepted association, message 1 delivered (tag
15, before activation), message 2 sent with its credit, then the next clear
translated EAPOL-shaped packet refused at the frame gate: RXD byte 7 `0x04`,
BSSID tag 1, where 0152 admitted 0 and 15 only (consistent with message 3,
not validated; only the RXD, header and Ethernet type were recorded);
fail-stop, no key command. Proposal 0158 admits exactly the two
measured values, 15 until the BSS command's credit completion and 1 while the
station is active; tag 0 (never measured) is now refused and named. The
session tooling counts the one scan by the nl80211 driver's debug line
(`CTRL-EVENT-SCAN-RESULTS` goes only to attached control-interface monitors,
never to the debug log), counts the four handshake messages, and records the
channel-40 query status, line count and flag words behind the IR flag. A new
compile and candidate follow the review.

## Runtime 15 bindings (2026-10-10)

Candidate 14 pairs the [compile 19](COMPILE_19.md) package `46f3682f…` (input
`9aa567d7`, `CONFIG_PACKET=y`) with candidate 13's RAM root byte-identical
(`449832a3…`, 63 members with the helper and the supplicant) and the same
board DT `25ab60f4…`; kernel config `975f8703…`, image `ce526e77…`, boot image
`223f886e…` (12296192 bytes), full padded boot2 `911e3d67…`. The owner
composed and validated it privately with the reviewed composer; the committed
receipt [results/candidate-14.json](results/candidate-14.json) (SHA-256
`889b101f…`) is that receipt's exact bytes, and `runtime-15/results/candidate.json`
is its copy. [Deployment 14](results/deployment-14.json) wrote it over the
installed candidate 13 (`ec412ce9…`) with the full readback matching; the
device is powered off awaiting the owner's boot2 start. [RUNTIME_15_PREPARATION](RUNTIME_15_PREPARATION.md)
states the measured dependency change and the C2 hypothesis. Bindings, with
every prior receipt, copy and piece of evidence untouched:

| Adapter | Runtime 15 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT 9aa567d7…`, `PACKAGE 46f3682f…`, exact packet-socket config delta, `--helper` `bc499f28…`, `--supplicant` `0487b710…` |
| `install-passive.py` | predecessor `ec412ce9…` (installed candidate 13), receipt `mt6797-wifi-phase-b-deployment-14`, `results/candidate-14.json`, slot filled |
| `capture-private.py` | `capture-15`, `session-15/deployment-summary.txt`, `results/candidate-14.json`, slot filled |
| `passive-session.py` | `results/candidate-14.json`; 63-member RAM root with the required supplicant |
| `passive-host.py` | `session-15`, `capture-15`; identity `runtime-15/results/candidate.json`; PSK-bound script required; C2 session pieces and private supplicant-log export |
| `prepare-runtime.py` | `results/candidate-14.json` against the compile-19 input and package, both slots, predecessor `ec412ce9…`, the PSK-bound script; creates `wifi-phase-b/session-15` only and leaves `capture-15` absent |
| `join-once.sh` | unchanged since `e7bcb6e5` (no `-f`, redirected private log) |

## Compile 19 and candidate 14 (2026-10-10)

[Compile 19](COMPILE_19.md) (input `9aa567d7`, package `46f3682f…`, config
`975f8703…` = the compile-18 configuration plus `CONFIG_PACKET=y` and the
visible `PACKET_DIAG` prompt left off, image `ce526e77…`, 656 patches, zero
driver warnings) is validated. `build-candidate.py` permits exactly that
configuration delta and `prepare-runtime.py` pins the input and package; the
owner composes candidate 14 with the unchanged RAM root. Deployment 14 and
runtime 15 bindings follow the candidate-14 receipt. Runtime 14's roots and
receipts are consumed and immutable.

## Runtime 14 result and the packet-socket dependency (2026-10-10)

[Runtime 14](RUNTIME_14.md) on candidate 13 with the corrected invocation:
the supplicant initialised and then failed to add `wlan0` because the kernel
has no packet sockets (`# CONFIG_PACKET is not set`, from the usbdiag
fragment); it opens one `PF_PACKET` socket per interface for its own address
even with the nl80211 control port. `configs/gemini-a53-wifi-phase-b-compile.fragment`
now restores `CONFIG_PACKET=y` (the defconfig value, applied after the usbdiag
fragment); only the Wi-Fi Phase B profile uses that fragment. Compile 19,
candidate 14 and a new deployment follow the review. No handshake has been
measured yet.

## Runtime 14 bindings (2026-10-10)

[Runtime 13](RUNTIME_13.md) on candidate 13 stopped before any scan: the
pinned static supplicant implements no `-f` (no `CONFIG_DEBUG_FILE`), printed
its usage text and exited 0. The corrected `join-once.sh` starts it without
`-f` and redirects its debug stream and stderr into the private RAM log;
nothing else changes. [RUNTIME_14_PREPARATION](RUNTIME_14_PREPARATION.md)
holds the bindings (fresh `capture-14` and `session-14`, identity
`runtime-14/results/candidate.json`, the same installed candidate 13 and
deployment 13) and the hypothesis.

## Runtime 13 bindings (2026-10-09)

Candidate 13 pairs the [compile 18](COMPILE_18.md) package `49afb45d…` (input
`eba4baa4`, proposals 0153 to 0157, config and DT unchanged) with the RAM
root of the unused candidate 12, byte-identical (`449832a3…`, 5621445 bytes:
the parent's 61 members, the release gate, the Phase C1 helper `bc499f28…`
and the pinned supplicant `0487b710…` as the 63rd member); board DT
`25ab60f4…` and kernel config `153ea2d0…` are byte-identical to candidates 8
to 12. The owner composed and validated it privately with the reviewed
composer; the committed receipt
[results/candidate-13.json](results/candidate-13.json) (SHA-256 `adc7a4a5…`)
is that receipt's exact bytes, and `runtime-13/results/candidate.json` is its
copy. Candidate 12 (receipt `e8d9900f…`) is preserved unused; deployment 12
never happened. The bound join script is the owner's fresh PSK-bound C2
script from the corrected source, which the preparation tool and the host
require. The runtime-13 protocol, hypothesis and branches are those of
[Phase C2](PHASE_C.md#device-protocol-stated-in-advance), recorded in
[RUNTIME_13_PREPARATION](RUNTIME_13_PREPARATION.md). Bindings, with every
prior receipt, copy and piece of evidence untouched:

| Adapter | Runtime 13 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT eba4baa4…`, `PACKAGE 49afb45d…`, `--helper` pinned to `bc499f28…` (665552 bytes), `--supplicant` pinned to `0487b710…` (1719888 bytes) |
| `install-passive.py` | predecessor `1c491341…` (installed candidate 11), receipt `mt6797-wifi-phase-b-deployment-13`, `results/candidate-13.json`, slot filled |
| `capture-private.py` | `capture-13`, `session-13/deployment-summary.txt`, `results/candidate-13.json`, slot filled |
| `passive-session.py` | `results/candidate-13.json`; RAM root of 63 members with the C1 `bin/join-connect` and the required C2 `bin/wpa_supplicant` verified |
| `passive-host.py` | `session-13`, `capture-13`; the WMT host identity reads `runtime-13/results/candidate.json`, a byte copy of the committed receipt; refuses a join script without the PSK binding; the C2 session pieces and the private supplicant-log export |
| `prepare-runtime.py` | checks `results/candidate-13.json` against the compile-18 input and package, both slots, predecessor `1c491341…`, the PSK-bound script; creates `wifi-phase-b/session-13` only and leaves `capture-13` absent |

## Runtime 12 bindings (2026-10-09)

Candidate 11 pairs the [compile 16](COMPILE_16.md) package `642165d4…` (input
`707e2d71`, proposal 0152 added, config and DT unchanged) with candidate
10's RAM root unchanged: the same parent members, release gate and Phase C1
helper `bc499f28…`, so the initramfs digest `dc8a4479…`, board DT `25ab60f4…`
and kernel config `153ea2d0…` are expected byte-identical to candidates 8 to
10 and only the kernel image changes. The bound join script is the
candidate-8 one. The runtime-12 protocol, hypothesis and branches are those of
runtime 11, with BSSID tag 15 admitted until the BSS command credit completion
is recorded. Bindings, with every prior receipt, copy and piece of evidence
untouched:

| Adapter | Runtime 12 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT 707e2d71…`, `PACKAGE 642165d4…`, `--helper` pinned to `bc499f28…` (665552 bytes) |
| `install-passive.py` | predecessor `57f9e65c…` (installed candidate 10), receipt `mt6797-wifi-phase-b-deployment-11`, `results/candidate-11.json`, slot filled |
| `capture-private.py` | `capture-11`, `session-11/deployment-summary.txt`, `results/candidate-11.json`, slot filled |
| `passive-session.py` | `results/candidate-11.json`; RAM root of 62 members with the C1 `bin/join-connect` verified |
| `passive-host.py` | `session-11`, `capture-11`; the WMT host identity reads `runtime-12/results/candidate.json`, a byte copy of the committed receipt |
| `prepare-runtime.py` | checks `results/candidate-11.json`, both slots, predecessor `57f9e65c…`; creates `wifi-phase-b/session-11` only and leaves `capture-11` absent |

## Runtime 11 bindings (2026-10-09)

Candidate 10 pairs the [compile 15](COMPILE_15.md) package `efb0b28a…` (input
`89d60283`, proposals 0150 and 0151 added, config and DT unchanged) with
candidate 9's RAM root unchanged: the same parent members, release gate and
Phase C1 helper `bc499f28…`, so the initramfs digest `dc8a4479…`, board DT
`25ab60f4…` and kernel config `153ea2d0…` are expected byte-identical to
candidates 8 and 9 and only the kernel image changes. The bound join script is
the candidate-8 one. The runtime-11 protocol, hypothesis and branches are
those of runtime 10, with the optional-vector observation and the single
bounded refusal header record added. Bindings, with every prior receipt, copy
and piece of evidence untouched:

| Adapter | Runtime 11 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT 89d60283…`, `PACKAGE efb0b28a…`, `--helper` pinned to `bc499f28…` (665552 bytes) |
| `install-passive.py` | predecessor `8d2c87f9…` (installed candidate 9), receipt `mt6797-wifi-phase-b-deployment-10`, `results/candidate-10.json`, slot filled |
| `capture-private.py` | `capture-10`, `session-10/deployment-summary.txt`, `results/candidate-10.json`, slot filled |
| `passive-session.py` | `results/candidate-10.json`; RAM root of 62 members with the C1 `bin/join-connect` verified |
| `passive-host.py` | `session-10`, `capture-10`; the WMT host identity reads `runtime-11/results/candidate.json`, a byte copy of the committed receipt |
| `prepare-runtime.py` | checks `results/candidate-10.json`, both slots, predecessor `8d2c87f9…`; creates `wifi-phase-b/session-10` only and leaves `capture-10` absent |

## Runtime 10 bindings (2026-10-09)

Candidate 9 pairs the [compile 14](COMPILE_14.md) package `3ecfdecb…` (input
`9ce81bc3`, proposal 0149 added, config and DT unchanged) with candidate 8's
RAM root unchanged: the same parent members, release gate and Phase C1 helper
`bc499f28…`, so the initramfs digest `dc8a4479…`, board DT `25ab60f4…` and
kernel config `153ea2d0…` are expected byte-identical to candidate 8 and only
the kernel image changes. The bound join script is the candidate-8 one. The
runtime-10 protocol, hypothesis and branches are those of runtime 9. Bindings,
with every prior receipt, copy and piece of evidence untouched:

| Adapter | Runtime 10 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT 9ce81bc3…`, `PACKAGE 3ecfdecb…`, `--helper` pinned to `bc499f28…` (665552 bytes) |
| `install-passive.py` | predecessor `1eed3948…` (installed candidate 8), receipt `mt6797-wifi-phase-b-deployment-9`, `results/candidate-9.json`, slot filled |
| `capture-private.py` | `capture-9`, `session-9/deployment-summary.txt`, `results/candidate-9.json`, slot filled |
| `passive-session.py` | `results/candidate-9.json`; RAM root of 62 members with the C1 `bin/join-connect` verified |
| `passive-host.py` | `session-9`, `capture-9`; the WMT host identity reads `runtime-10/results/candidate.json`, a byte copy of the committed receipt |
| `prepare-runtime.py` | checks `results/candidate-9.json`, both slots, predecessor `1eed3948…`; creates `wifi-phase-b/session-9` only and leaves `capture-9` absent |

## Runtime 9 bindings (2026-10-09)

Candidate 8 pairs the [compile 13](COMPILE_13.md) package `07caf6b5…` (input
`8efe639e`, proposals 0140 and 0148 added, config and DT unchanged) with a
new RAM root: the parent members as before plus the Phase C1 helper
`bc499f28…` (665552 bytes) in place of the Phase B helper, so the initramfs
digest differs from candidates 4 to 7. The join script is unchanged apart from
the pinned helper digest, so a new bound script is required. Bindings, with
every prior receipt, copy and piece of evidence untouched:

| Adapter | Runtime 9 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT 8efe639e…`, `PACKAGE 07caf6b5…`, `--helper` pinned to `bc499f28…` (665552 bytes) |
| `install-passive.py` | predecessor `820657ed…` (installed candidate 7), receipt `mt6797-wifi-phase-b-deployment-8`, `results/candidate-8.json`, slot filled |
| `capture-private.py` | `capture-8`, `session-8/deployment-summary.txt`, `results/candidate-8.json`, slot filled |
| `passive-session.py` | `results/candidate-8.json`; RAM root of 62 members with the C1 `bin/join-connect` verified |
| `passive-host.py` | `session-8`, `capture-8`; the WMT host identity reads `runtime-9/results/candidate.json`, a byte copy of the committed receipt |
| `prepare-runtime.py` | checks `results/candidate-8.json`, both slots, predecessor `820657ed…`; creates `wifi-phase-b/session-8` only and leaves `capture-8` absent |

## Runtime 8 bindings (2026-10-09)

Candidate 7 pairs the [compile 12](COMPILE_12.md) package `784aef75…` (input
`65c2fa81`, proposal 0147 added, config and DT unchanged) with the same RAM
root and helper as candidates 4 to 6; no host-side protocol change. Bindings,
with every prior receipt, copy and piece of evidence untouched:

| Adapter | Runtime 8 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT 65c2fa81…`, `PACKAGE 784aef75…`, `--helper` pinned to `b3851a4b…` (665552 bytes) |
| `install-passive.py` | predecessor `e6b7dd4e…` (installed candidate 6), receipt `mt6797-wifi-phase-b-deployment-7`, `results/candidate-7.json` (SHA-256 `e3134657…`, boot.img `1fb75cff…`, padded boot2 `820657ed…`), both slots filled |
| `capture-private.py` | `capture-7`, `session-7/deployment-summary.txt`, `results/candidate-7.json`, slot filled |
| `passive-session.py` | `results/candidate-7.json`; RAM root of 62 members with `bin/join-connect` verified |
| `passive-host.py` | `session-7`, `capture-7`; the WMT host identity reads `runtime-8/results/candidate.json`, a byte copy of the candidate-7 receipt |
| `prepare-runtime.py` | checks `results/candidate-7.json`, both slots, predecessor `e6b7dd4e…`; creates `wifi-phase-b/session-7` only and leaves `capture-7` absent |

## Runtime 7 bindings (2026-10-08)

Candidate 6 pairs the [compile 11](COMPILE_11.md) package `86b0a208…` (input
`d88d6e22`, proposal 0146 added, config and DT unchanged) with the same RAM
root and helper as candidates 4 and 5; no host-side change. Bindings, with
every prior receipt, copy and piece of evidence untouched:

| Adapter | Runtime 7 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT d88d6e22…`, `PACKAGE 86b0a208…`, `--helper` pinned to `b3851a4b…` (665552 bytes) |
| `install-passive.py` | predecessor `e6fe0e8d…` (installed candidate 5), receipt `mt6797-wifi-phase-b-deployment-6`, `results/candidate-6.json` (SHA-256 `e4fbd0e2…`, boot.img `59d1ee6f…`, padded boot2 `e6b7dd4e…`), both slots filled |
| `capture-private.py` | `capture-6`, `session-6/deployment-summary.txt`, `results/candidate-6.json`, slot filled |
| `passive-session.py` | `results/candidate-6.json`; RAM root of 62 members with `bin/join-connect` verified |
| `passive-host.py` | `session-6`, `capture-6`; the WMT host identity reads `runtime-7/results/candidate.json`, a byte copy of the candidate-6 receipt |
| `prepare-runtime.py` | checks `results/candidate-6.json`, both slots, predecessor `e6fe0e8d…`; creates `wifi-phase-b/session-6` only and leaves `capture-6` absent |

## Runtime 6 bindings (2026-10-08)

Candidate 5 pairs the [compile 10](COMPILE_10.md) package `7ee0f058…` (input
`00dc3c7a`, proposal 0145 added, config and DT unchanged) with the same RAM
root and helper as candidate 4; no host-side change. Bindings, with every
prior receipt, copy and piece of evidence untouched:

| Adapter | Runtime 6 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT 00dc3c7a…`, `PACKAGE 7ee0f058…`, `--helper` pinned to `b3851a4b…` (665552 bytes) |
| `install-passive.py` | predecessor `eeb2ce9b…` (installed candidate 4), receipt `mt6797-wifi-phase-b-deployment-5`, `results/candidate-5.json` (SHA-256 `c7a93e94…`, boot.img `ad91f738…`, padded boot2 `e6fe0e8d…`), both slots filled |
| `capture-private.py` | `capture-5`, `session-5/deployment-summary.txt`, `results/candidate-5.json`, slot filled |
| `passive-session.py` | `results/candidate-5.json`; RAM root of 62 members with `bin/join-connect` verified |
| `passive-host.py` | `session-5`, `capture-5`; the WMT host identity reads `runtime-6/results/candidate.json`, a byte copy of the candidate-5 receipt |
| `prepare-runtime.py` | checks `results/candidate-5.json`, both slots, predecessor `eeb2ce9b…`; creates `wifi-phase-b/session-5` only and leaves `capture-5` absent |

## Runtime 5 bindings (2026-10-07)

Two corrections follow runtime 4, both reviewed offline and neither yet
booted:

- **Host side.** `helper/join-connect.c` is a static, dependency-free program
  that sends one `NL80211_CMD_CONNECT` with the interface, SSID, 5200 MHz,
  the owner's BSSID, `NL80211_ATTR_PRIVACY` and open-system authentication,
  and nothing else: no key, cipher, information element or scan attribute.
  With the privacy flag set, cfg80211's station management entity finds the
  already scanned protected BSS and proceeds to authenticate and associate
  without issuing the directed scan that the one-shot `hw_scan` refuses. The
  transport uses distinct sequence numbers for the family lookup and the
  connect, consumes the lookup's acknowledgement before sending the connect,
  accepts only kernel-origin replies carrying the matching sequence, bounds
  every receive and the whole exchange, and never retries; the message and
  reply buffers are aligned for the netlink headers. `join-once.sh` runs it in
  place of `iw connect`, under the same `timeout 3`, after the same scan and
  NO-IR gates, with its output inside the framed body. The reproducible static
  aarch64 build is `helper/build-join-connect.sh` (SHA-256 `bc499f28…` for the
  Phase C1 helper with the WPA2-PSK parameters and RSN element, `b3851a4b…`
  for the Phase B helper; 665552 bytes each, pinned in the script's tool digests). The kernel is identified
  by the sender port 0; reply headers carry the requester's port ID, as
  `netlink_ack` and `genlmsg_put_reply` stamp it, and are not checked. The
  family reply, which for nl80211 exceeds 512 bytes with its operation list,
  is parsed from a reply-sized buffer and a truncated datagram is refused.
- **Phase C2 preparation (design under review, nothing built).**
  `helper/wpa_supplicant.conf.template` is the supplicant configuration the
  private binding step fills (passive single-channel scan, one RSN network,
  PSK placeholder). `helper/extract-gemian-credential.py` copies the existing
  Gemian credential for the exact private target into fresh mode-0600 input
  files on the laptop, read-only on the device, with identity and uniqueness
  gates and no secret on any output; `tests/credential-tool-test.py` drives it
  against a fake remote helper. The C2 design findings are in
  [PHASE_C](PHASE_C.md).
- **Phase C2 implementation (compile 18 with proposal 0157 built; candidate 13 to be composed by the owner; candidate 12 unused).** Proposals 0153 to
  0156 (bounded scan-element limit; EAPOL delivery to mac80211; control-port
  EAPOL transmit as the vendor security frame on TC4 through the one queue;
  firmware keys with the WPA2 BSS declaration, ledger-serialized `set_key` and
  explicit removals after the deauthentication). Tooling: `build-candidate.py
  --supplicant` adds `bin/wpa_supplicant` as a 63rd member that
  `passive-session.py` checks; `bind-target.py --psk-file` binds the private
  PSK; `join-once.sh` runs the supplicant-owned scan, join and handshake when
  a PSK is bound, prints fixed phrase counts only and leaves the complete
  supplicant log in RAM for private preservation; `classify-join.py` admits
  the `eapol delivered`, `eapol sent`, key command, credit and removal records
  with exact page and sequence ownership and reports
  `driver_handshake_path_pass` without any installed-key or operational claim.
  `c2-session.py` and the `passive-host.py` hooks (checked by
  `tests/c2-session-test.py` and `tests/c2-host-test.py`): a PSK-bound script
  selects the C2 pieces; the join phase budget is 45 s for the bounded 24 s
  loop; one bounded read-only `supplicant-log` phase exports the complete
  supplicant log into the private runtime root between the join script and
  the log seal, with boot identity, size before and after, supplicant process
  count and transport completeness; the sanitized result carries fixed-phrase
  counts, the export's byte count and digest and the session conjunction
  (`c2_session_pass`: the join phase's complete process under the
  authenticated boot with an empty stderr, clean supplicant and connect
  exits, exactly one scan result set, key negotiation completed and
  connected phrases, the channel-40 IR flag, the terminal record, the driver
  handshake path, the complete bounded export with the reported byte count
  and the same phrase counts, and the sealed, regression-passed, recovered
  session), and no digest of the PSK-bound script. The inherited exit
  condition keeps every phase and process error; only the standard iw
  demonstration is replaced by the join phase's completeness. Compile 17 (job
  `0e333617…-mt6797-a53-wifi-phase-b-compile-m0`, image gzip
  `0c24f88f…`, config `153ea2d0…`, 655 patches, no driver warnings) exists
  and was composed as candidate 12, held unused: proposal 0157 admits the
  pinned supplicant's RSN capabilities 0x000c (its 16-replay-counter
  declaration on a WMM-advertising AP, from the public source) next to 0,
  with everything else in the admission unchanged and no WMM support
  claimed; the ownership fixture admits the 0x000c variant and refuses six
  other capability patterns. [Compile 18](COMPILE_18.md) (input `eba4baa4`,
  package `49afb45d…`, image `bea14180…`, config and DT unchanged, 656
  patches, no driver warnings) built it; `build-candidate.py` and
  `prepare-runtime.py` pin that input and package for candidate 13, which
  the owner composes from the same private parent, helper and supplicant.
  Deployment 12 never happened; the candidate-12 receipt and the runtime-13
  bindings below are preserved until the candidate-13 receipt exists.
  Fixtures: `tests/run-security-test.py` (descriptor and preparation),
  `tests/run-key-test.py` (key payloads and the WPA2 bytes), the ownership
  harness end-to-end one-queue sequence, and the peer harness `set_key` with
  message 4 in flight or queued, refusals and the removal order.
- **Phase C2 supplicant, pinned, not yet admitted.** `helper/build-wpa-supplicant.sh`
  with `helper/wpa_supplicant.config` builds upstream wpa_supplicant 2.11
  with libnl 3.11.0 as one static aarch64 binary (SHA-256 `0487b710…`,
  1719888 bytes, reproducible; source digests and release-signature
  fingerprints in [PHASE_C](PHASE_C.md)). It is research for Phase C2 and is
  not part of any candidate until the runtime-9 evidence is in.
  Tests: [tests/join-connect-test.py](tests/join-connect-test.py) parses the
  exact attribute set from the helper's dump mode, refuses the argument
  boundaries, runs [tests/join-connect-transport-test.c](tests/join-connect-transport-test.c),
  the production transport against a scripted kernel (happy path, kernel -95
  retained as exit 3, a late or stale family acknowledgement never
  acknowledging the connect, non-kernel origin ignored, reply headers with a
  non-zero port ID, data and acknowledgement in one datagram, a family reply
  with the id beyond 2 KiB of operations, a reply longer than the buffer
  refused before any connect, an unacknowledged or failed lookup never
  sending the connect, and the deadline with one request), and performs a
  real, connect-free generic netlink lookup against the host kernel through
  the helper's `--family-lookup` mode: `nlctrl` must resolve to 16, `nl80211`
  must resolve when cfg80211 is present, and an unknown name must fail.
- **Driver side.** Proposal 0144: mac80211 calls the config operation with
  radio index -1 for this single-radio wiphy, including the emulated channel
  context that sets the operating channel before authentication; the
  operation refused any non-zero index, so the channel binding could never
  become valid and the emulated context would have failed the connect with
  -95 after the host-side fix. It now accepts exactly -1.
  [tests/run-config-test.py](tests/run-config-test.py) runs the production
  function: -1 accepted and binding channel 40, 0 and 1 refused with the
  refusal logged once, NO-IR or an HT width breaking the binding without an
  error, flags and not-ready refusals, a 2.4 GHz channel and no channel. The
  same fixture fails on the pre-0144 source.

Candidate 4 pairs the [compile 9](COMPILE_9.md) package `bb1659e0…` (input
`68e3a3c8`, 0143 and 0144, config and DT unchanged) with a RAM root that
carries `bin/join-connect` next to the pinned `iw` tools. The adapters are
bound as for the earlier runtimes, with every prior receipt and copy untouched:

| Adapter | Runtime 5 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT 68e3a3c8…`, `PACKAGE bb1659e0…`, `--helper` pinned to `b3851a4b…` (665552 bytes) |
| `install-passive.py` | predecessor `84f65eae…` (installed candidate 3), receipt `mt6797-wifi-phase-b-deployment-4`, `results/candidate-4.json` (SHA-256 `0d8bf089…`, boot.img `6bc99a30…`, padded boot2 `eeb2ce9b…`), both slots filled |
| `capture-private.py` | `capture-4`, `session-4/deployment-summary.txt`, `results/candidate-4.json`, slot filled |
| `passive-session.py` | `results/candidate-4.json`; RAM root of 62 members with `bin/join-connect` verified by size, digest, mode and ownership |
| `passive-host.py` | `session-4`, `capture-4`; the WMT host identity reads `runtime-5/results/candidate.json`, a byte copy of the candidate-4 receipt |
| `prepare-runtime.py` | checks `results/candidate-4.json`, both slots, predecessor `84f65eae…`; creates `wifi-phase-b/session-4` only and leaves `capture-4` absent |

The composer `build-candidate.py` takes a `--helper` input pinned to the
digest and size above and, through `add_helper()`, inserts that one member
(mode 0755, root-owned, one link, like `bin/iw`) into the otherwise unchanged
parent RAM root, re-parses the archive with one more member and records the
helper in the receipt. An earlier attempt to apply this edit was denied by the
auto-mode classifier; the owner then approved it explicitly and it was applied.
[tests/composer-helper-test.py](tests/composer-helper-test.py) exercises the
insertion on a synthetic RAM root, including the refusals of a wrong digest or
size, a missing or re-owned `bin/iw` and an already present helper. The staged
binary for composition is published on Buildbox-1 under the artifacts helpers
directory named by its digest, with a `SHA256SUMS` file.

## Runtime 4 bindings (2026-10-07)

Candidate 3 is the [compile 8](COMPILE_8.md) package `9c5a7300…` from input
`a5951349`, differing from candidate 2 only by proposal 0143 in the image.
The adapters now bind runtime 4 the way runtime 2 was bound, with the
runtime-2 and runtime-3 evidence and receipts untouched:

| Adapter | Runtime 4 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT a5951349…`, `PACKAGE 9c5a7300…` |
| `install-passive.py` | predecessor `03a6d78c…` (installed candidate 2), receipt `mt6797-wifi-phase-b-deployment-3`, `results/candidate-3.json` (SHA-256 `00f6c619…`, boot.img `d98cca07…`, padded boot2 `84f65eae…`), both `MANIFEST_SHA` slots filled |
| `capture-private.py` | `capture-3`, `session-3/deployment-summary.txt`, `results/candidate-3.json`, slot filled |
| `passive-session.py` | `results/candidate-3.json` |
| `passive-host.py` | `session-3`, `capture-3`; the WMT host identity reads `runtime-4/results/candidate.json`, a byte copy of the candidate-3 receipt |
| `prepare-runtime.py` (was `prepare-runtime-2.py`) | checks `results/candidate-3.json`, both slots, predecessor `03a6d78c…`; creates `wifi-phase-b/session-3` only and leaves `capture-3` absent |
| `laptop-capture.py`, `laptop-session.py` | unchanged; they follow the adapters |

Order: the laptop composes candidate 3 with `build-candidate.py` from the
fetched compile-8 package and returns the sanitized receipt; this checkout
commits it as `results/candidate-3.json`, fills both slots and the runtime-4
copy; then the guarded `install-passive.py prepare` (deployment-3) over the
installed candidate 2, the owner's boot2 selection, and the runtime-4 steps
with a fresh runtime root as in [RUNTIME_3.md](RUNTIME_3.md). The decision
the boot answers is the refused-condition bitmask printed by 0143. Deployment 3
is recorded in [results/deployment-3.json](results/deployment-3.json) and
[RUNTIME_4_PREPARATION.md](RUNTIME_4_PREPARATION.md).
Runtime 4 ([RUNTIME_4.md](RUNTIME_4.md), [results/runtime-4.json](results/runtime-4.json))
booted candidate 3: initialization and the scan passed, the connect failed
with -95 again, and neither 0143 diagnostic line appeared although both
strings are in the image, so no driver refusal was logged. The source review
there reconstructs the failure in cfg80211's connect path.

## Runtime 2 bindings (2026-10-06)

Runtime 2 uses the [compile 7](COMPILE_7.md) package: commit
`db1b2aeae59b5bc117893b752f73e892efd78b10`, inventory
`47addc1327b7c843d530cded614b86b1baab504dd87557dbfec3212fc80421ae`, release
`7.1.3-gemini-a53-wifi-phase-b-compile`. The parent is still the booted Phase A
runtime-3 candidate (`827a6582…`), so the board DT is byte-identical, the
private RAM root keeps all 61 members with only the release gate changed, the
config differs only in release and `CONFIG_MT6797_STATION_JOIN=y`, and PSCI
power-off and `clk_ignore_unused` are unchanged. The release string is the same
as runtime 1, so every live admissibility check binds to the candidate-2 receipt
digest, the package inventory and the full boot2 hash, never to the release.

The inherited WMT host main compares the capture identity against
`HERE/results/candidate.json`, which is the runtime-1 receipt here; the first
runtime-2 session was refused offline for that reason before any device action
("capture identity or one-shot evidence changed"). `passive-host.py` now binds
that one module's `HERE` to [runtime-2/](runtime-2/results/candidate.json),
whose `results/candidate.json` is a byte copy of `results/candidate-2.json`;
every equality, boot and one-shot check is unchanged and
[tests/host-identity-test.py](tests/host-identity-test.py) asserts the binding
and the predicate's positive and negative cases.

Deployment 2 is recorded in [results/deployment-2.json](results/deployment-2.json)
and [RUNTIME_2_PREPARATION.md](RUNTIME_2_PREPARATION.md). The runtime itself is
recorded in [RUNTIME_2.md](RUNTIME_2.md) and
[results/runtime-2.json](results/runtime-2.json): initialization and WLAN
readiness passed, the join script exited before its first output, no scan or
RF occurred, and recovery was confirmed. The inferred, unmeasured cause is the
script's pre-scan `no IR` refusal under the world regulatory domain;
`join-once.sh` is corrected and now names a failing prerequisite on stderr.

Runtime 3 ([RUNTIME_3.md](RUNTIME_3.md), [results/runtime-3.json](results/runtime-3.json))
passed every script prerequisite, demonstrated the passive scan on the owner's
BSS with NO-IR lifted by the found beacon, and then saw `iw connect` refused
with -95 before any management frame while the driver stopped at its deadline
with nothing submitted. The connect path is supported (cfg80211's own station
management entity over mac80211's auth and assoc); the refusal is inferred to
come from the driver's peer precondition. Proposal 0143 prints the refused
condition bitmask once; the script now keeps the connect's diagnostics inside
the framed stdout so the inherited scan classification stays independent.

Runtime-1 evidence is untouched: [results/candidate.json](results/candidate.json),
[results/deployment-1.json](results/deployment-1.json) and
[results/runtime-1.json](results/runtime-1.json) stay as consumed, and the
runtime-1 adapter bindings are reproducible at revision `bd76eb67`.

Runtime-2 bindings, each the smallest parameter change to an existing adapter:

| Adapter | Runtime 2 |
| --- | --- |
| `build-candidate.py` | `COMMIT` and `PACKAGE` pinned to the compile-7 package |
| `install-passive.py` | receipt `results/candidate-2.json`; installer receipt `mt6797-wifi-phase-b-deployment-2`; boot2 predecessor `6ecc057c…` (the installed runtime-1 candidate) |
| `capture-private.py` | receipt `results/candidate-2.json`; evidence `wifi-phase-b/capture-2`; deployment summary `wifi-phase-b/session-2/deployment-summary.txt` |
| `passive-host.py` | evidence `wifi-phase-b/session-2` and `capture-2` |
| `passive-session.py` | receipt `results/candidate-2.json` |
| `bind-target.py`, `join-once.sh`, `classify-join.py` | unchanged |

The composed candidate-2 receipt is committed unchanged as
[results/candidate-2.json](results/candidate-2.json), SHA-256
`f19dffdb622643e7dd486a2b6b3b4e752c993b5908ecc91929c0b4a0972ee896`, and both
`MANIFEST_SHA` slots carry that digest. Its boot image is `9374ff09…`, its full
padded boot2 `03a6d78c…`; kernel.config, board DT and initramfs are
byte-identical to runtime 1 and only `Image.gz` changed.

[prepare-runtime.py](prepare-runtime.py) (named `prepare-runtime-2.py` for runtimes 2 and 3) is the offline preparation entry
point for the laptop. Driven only by `GEMINI_PRIVATE_REPO`,
`GEMINI_RUNTIME_ROOT` and `GEMINI_JOIN_SCRIPT`, it checks that the private
repository holds credentials, that the bound join script is one mode-0600 file
wrapping the reviewed `join-once.sh`, that `results/candidate-2.json` names the
compile-7 package and that both slots equal its digest. It then creates the
mode-0700 evidence root and `wifi-phase-b/session-2`, refusing if the session
or capture directory exists. It leaves `capture-2` absent on purpose: the
inherited capture claims that directory itself and refuses an existing one, so
the one-attempt guard stays with the capture
([tests/prepare-runtime-test.py](tests/prepare-runtime-test.py) asserts
exactly that precondition). It performs no device action.

Two env-driven wrappers replace the laptop's private reference wrappers for a
checkout that lacks the private artifacts:

- [laptop-capture.py](laptop-capture.py) runs `capture-private.py` with the
  baseline collector loaded from the private checkout's copy, so the
  collector's own repository root resolves to the credentials.
- [laptop-session.py](laptop-session.py) runs `passive-host.py` with the pinned
  return workflow, the service scripts and the baseline scripts loaded from the
  private checkout's copies, and rebinds `BASELINE` and `SERVICE` through the
  session module tree when the host loads `passive-session.py`. The installer is
  the public `install-passive.py`, used directly and by the host's `run_path`.
  Run the session only through `laptop-session.py`: invoking `passive-host.py`
  directly reads the public copies of the frozen return workflow
  (`a53-ram-return-v2.py`, `a53-ram-return.py`) and `finish-baseline.py`, which
  the 2026-10-05 hygiene commit changed, and the exact pins refuse them
  (first as "Gemian return v2 source changed"); the private checkout's
  retained copies are the pinned bytes. The pins themselves are unchanged.

Pinned digests still apply to every remapped file, so the private copies must
be identical to this checkout's. The wrappers contain no host-specific path;
[tests/laptop-wrappers-test.py](tests/laptop-wrappers-test.py) asserts each
remapped root and that nothing else moves.

**Installer pinned inputs.** The first runtime-2 `install-passive.py prepare`
on the laptop refused: `reviewed installer input changed:
experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/install-boot2.sh`.
The baseline installer's `pinned_sources()` captures this checkout as its
default root, and this checkout's `install-boot2.sh` (`ba6ffd55…`) no longer
matches the reviewed pin `deaa0e88…`: commit a0887d2c changed the script after
it was pinned at cac47380, while the retained private checkout still holds the
pinned bytes. The laptop's private installer wrapper had supplied the private
`pinned_sources`, so the earlier statement here that it was fully redundant was
wrong. The Phase B `install-passive.py` now binds that one input root to
`GEMINI_PRIVATE_REPO`; every pin, digest, derive and guard check is the
reviewed original, and a mismatching private copy still refuses.
[tests/installer-sources-test.py](tests/installer-sources-test.py) asserts the
binding, the unchanged checks, acceptance of the pinned bytes and refusal of the
modified script. The pin itself is not updated here; whether a0887d2c's change
deserves a reviewed re-pin is a separate decision.

Order for runtime 2, with the laptop's private wrappers supplying only the
private-repository module remaps and the runtime root:

1. Laptop: `build-candidate.py --kernel-package <package 47addc13…> --parent
   <Phase A runtime-3 candidate> --output <candidate-2 directory>`; send the
   sanitized `candidate.json`.
2. Buildbox: commit it as `results/candidate-2.json` and fill both slots.
3. Laptop, with `GEMINI_PRIVATE_REPO`, `GEMINI_RUNTIME_ROOT` (fresh) and
   `GEMINI_JOIN_SCRIPT` exported, and `<previous>` the live Gemian boot ID:
   1. `python3 bind-target.py --target <private AP input> --output
      $GEMINI_JOIN_SCRIPT`
   2. `python3 prepare-runtime.py`
   3. `python3 install-passive.py prepare --candidate <candidate-2 dir>
      --previous-gemian-boot <previous> --output <installer dir>`, then the
      guarded installer it generates (deployment-2); the owner selects boot2.
   4. After the mainline boot: `python3 laptop-capture.py --candidate
      <candidate-2 dir>` for the offline preparation and the same with
      `--execute` for the single `wmt_negotiate` trigger; then `python3
      laptop-session.py --candidate <candidate-2 dir>` for the offline
      preparation and the same with `--execute` for the one attempt, exactly as
      in [PROTOCOL.md](PROTOCOL.md). Both wrappers take the public adapters'
      own arguments.
