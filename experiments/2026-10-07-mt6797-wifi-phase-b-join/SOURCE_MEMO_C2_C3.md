# Source memo: what the reference run 3 settles for Phase C2 completion and the C3 data path

Status: resolved; implemented by proposals 0164 to 0167 (see the README).
Concise resolution of the concrete source questions raised by the
[reference run 3 recommendation](../2026-09-26-gemian-wifi-reference/README.md#run-3-against-mainline-proposal-0163-and-the-remaining-driver-work);
read before the C2/C3 proposal diff. Sources are the pinned public vendor
tree `59e00a91` (`drivers/misc/mediatek/connectivity/wlan/gen3`), the
Debian `wpa` 2.4 upstream tarball the device's supplicant is built from, the
mainline proposals 0153 to 0163 and `include/net/mac80211.h` of the pinned
kernel 7.1.3. The reference ledger carries metadata (command and event
identifiers, sequences, descriptor classes, lengths, flags), never packet
bytes; nothing below rests on packet content.

## 1. The group key's WLAN index (resolved)

The vendor's WLAN table allocators (`privacy.c secPrivacySeekForEntry` and
`secPrivacySeekForBcEntry`) search entries 0 to 30, below
`NIC_TX_DEFAULT_WLAN_INDEX` 31 (`nic_tx.h`, the index for peers without an
entry), lowest free first; the observed 0, 1, 2 are the first three
allocations of this single-peer owner, not a table size. The order the
run-3 ledger shows is exactly the source's:

- BSS activation (`nic.c nicActivateNetwork`) seeks a broadcast entry for the
  BSS's own address while the BSSID is still zero (cipher none, key id
  0xff): entry 0. `BSS_ACTIVATE_CTRL` and the post-association
  `SET_BSS_INFO` carry BMC index 0; the pre-association `SET_BSS_INFO`
  carries 255 (`ais_fsm.c` resets the BSS's index to the reserved entry).
- AP station creation (`cnm_mem.c cnmStaRecAlloc` → `secPrivacySeekForEntry`)
  takes the next free entry as the pairwise entry (entry 1 = the station's
  WLAN index) and, because the station is the AP (`IS_AP_STA`), calls
  `secGetBmcWlanIndex`, which seeks a broadcast entry for the AP's address
  (cipher none, key id 0xff): entry 2. Every `UPDATE_STA_RECORD` therefore
  declares `ucBMCWlanIndex` 2 from the first one on, before any key.
- The group key (`wlan_oid.c wlanoidSetAddKey`, not a TX key, peer the
  BSSID, station record present) calls `secPrivacySeekForBcEntry` with the
  AP's address, CCMP and key id 1; entry 2 matches (same BSS, same address,
  not pairwise, key id 0xff admits any key id) and is reused; the command
  carries WLAN index 2 and `prStaRec->ucBMCWlanIndex` stays 2.

Mainline (0137, 0156) declares BMC index 0 in the station record and
installs the group key under WLAN index 0, that is, under the BSS's own
broadcast entry rather than a distinct entry declared for the AP station.
Whether the firmware accepts that is not shown by any evidence. The
source-backed shape is: allocate a distinct WLAN index for the AP station's
broadcast key (2 when the BSS holds 0 and the station 1), declare it in
every `UPDATE_STA_RECORD` for the AP station, and use it for the group
`ADD_REMOVE_KEY`. This is a C2 change.

## 2. The key removal shape (resolved)

The six index-based removals observed at every stock teardown are not the
vendor driver's own teardown. They are wpa_supplicant's
`wpa_clear_keys` (`wpa_supplicant.c`; six indices with `CONFIG_IEEE80211W`,
address NULL because `wpa_supplicant_mark_disassoc` has already zeroed the
BSSID) reaching `mtk_cfg80211_del_key` with no address and then
`wlanoidSetRemoveKey`: a zeroed `CMD_802_11_KEY` with remove, the key id,
a zero peer, BSS 0, key type 0 and, with no station record for the zero
address and WPA authentication, WLAN index `WTBL_RESERVED_ENTRY` (255). The
firmware accepted all six, including indices never installed. The vendor
driver's disconnect path itself submits no key removal; the BSS
deactivation frees the host-side table entries.

For a removal with the AP's address and the unicast flag,
`wlanoidSetRemoveKey` produces key type 1 and the station's WLAN index; for
a removal with the AP's address and no unicast flag it leaves key type 0
and WLAN index 0 (zeroed), a shape the real supplicant never requests.
Mainline 0156 retires the group key with the AP's address and a zeroed
index, that is, the never-requested shape. The smallest source-backed
behaviour: pairwise removal with the AP's address, unicast type and the
station's WLAN index; group removal with a zero peer, type 0 and WLAN index
255, as the supplicant's path produces and the firmware accepted. Keep the
order (after the deauthentication, pairwise first) and the explicit
retirement on `DISABLE_KEY` or in the cleanup; do not emit six removals for
resemblance.

## 3. Receive block-ack and reorder events (resolved in semantics)

`EVENT_ID_RX_ADDBA` (`que_mgt.c qmHandleEventRxAddBa`) names a station record
index, a BA parameter set (TID and buffer size) and a starting sequence
control; the firmware has completed the ADDBA exchange itself and the host
creates a reorder queue for that station and TID (`qmAddRxBaEntry`).
`EVENT_ID_CHECK_REORDER_BUBBLE` (`qmHandleEventCheckReorderBubble`) names a
station record and TID; when the host's reorder queue has a hole at its
window start, the host advances the window past the first missing sequence
and releases what it holds. `EVENT_ID_RX_DELBA` removes the entry. The
run-3 ledger shows three ADDBA events (TIDs 6 and 0) and six bubble checks
during ordinary traffic. A host that does not reorder delivers frames in
arrival order; no vendor code path refuses data without a reorder queue.
For mainline this means: accept and record both events (station index, TID,
window size, no addresses), either implement a bounded per-TID reorder
window with the vendor's bubble semantics or deliver in arrival order and
say so; never derive a traffic claim from either.

## 4. Data framing toward mac80211 (API facts and the observed classes)

The reference shows data in both directions in translated Ethernet form at
the firmware boundary. The two accepted protected receive classes are
distinct and must stay distinct: 962 unicast descriptors (destination not a
group address, unicast-to-me set, broadcast and multicast clear, security
mode 4, translation set, WLAN index 1, the station's pairwise entry, raw
status word 0) and 131 group descriptors (destination group bit set,
broadcast set, security mode 4, translation set, WLAN index 2, the group
key's entry, raw status word `0xc000`). In the source's bit names
(`nic_rx.h`) `0xc000` is the A-MPDU sub-frame and A-MPDU format flags, not
an error and not a requirement for unicast; the error mask is bits 1 to 10;
the management frames before the keys carried `0xe000`, whose bit 13 is the
source's non-data test. The observer's `grp` field is the destination
address's group bit read from the delivered header (translated byte 0,
native byte 4), not the descriptor's status-group presence word; what
extension groups a descriptor carries, and with them the sequence control,
frame control and any PN, must come from the RXD decoder and the source,
never from these counts. For translated frames the vendor takes frame
control and the sequence number from status group 4
(`nic_rx.c` `rxmDefragMPDU`, `que_mgt.c` reorder: `HAL_RX_STATUS_GET_SEQFrag_NUM(prRxStatusGroup4)`),
so a receiver that owns reordering reads group 4. Transmit descriptors were
format 0 (Ethernet), not 802.11, with the protected flag, on traffic
classes 1 and 3.

The pinned kernel's mac80211 offers: `RX_FLAG_8023` with
`IEEE80211_OFFLOAD_DECAP_ENABLED` for 802.3 receive (no reordering by
mac80211), `RX_FLAG_DECRYPTED` with `RX_FLAG_IV_STRIPPED` and
`RX_FLAG_MMIC_STRIPPED` for frames the firmware decrypted (without
`RX_FLAG_PN_VALIDATED` mac80211 cannot check replays, and the firmware's
PN handling is not shown by the reference: replay protection is not
established by security mode 4), `IEEE80211_OFFLOAD_ENCAP_ENABLED` for
802.3 transmit, `ieee80211_start_rx_ba_session_offl` for block-ack
sessions the firmware negotiated, and `IEEE80211_HW_SUPPORTS_REORDERING_BUFFER`
only for a driver that really reorders. Decision taken for the C3
proposals (0165 to 0167): the association stays legacy and non-WMM (the
join gate refuses HT, VHT and WMM elements, so the AP negotiates no
block-ack with this station), there is no reorder engine and no reordering
buffer is declared; aggregated descriptors (either A-MPDU bit clear in the
inverse pinned macros), QoS data and the ADDBA, DELBA and bubble events are
refused. Receive rebuilds the 802.11 header from the translated header plus
group 4's frame and sequence control and delivers through `ieee80211_rx`
with the decrypted and stripped flags. Transmit converts mac80211's 802.11
data to Ethernet II in the driver (the observed firmware format) without
encapsulation offload, with finite traffic-class, page and PID accounting. Which post-association commands
(`INDICATE_PM_BSS_CONNECTED`, `SET_RX_FILTER`, `MAC_MCAST_ADDR`,
`UPDATE_WMM_PARMS`, `SET_BSS_RLM_PARAM`) the firmware needs for data is not
shown by the reference and is decided from source per command, smallest
first.

## 4b. Channel privilege after the join (reference fact)

The run-3 ledger holds two `CH_PRIVILEGE` commands: the request before the
authentication (grant 4000 ms) and a second one about four seconds later,
after both key commands and after protected data had already started inside
the grant; protected data keeps arriving after it. The vendor therefore
releases the privilege once the join is complete and passes data on the
connected BSS without one. The mainline lifetime releases it right after the
group key's credit and runs its whole data phase without a grant.

## 5. What the offline replay can and cannot do

The reference ledgers (runs 1 to 3) give command and event order, key
command fields, event classes and descriptor classes, so a replay can check
the mainline classifier and the driver's sequence logic against that order.
They carry no packet bytes, so decoder, sequence and reorder logic is
covered by focused synthetic boundary and malformed cases, not by replay,
and no network function is validated from metadata counts.
