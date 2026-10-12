# RX replay boundary: what the pinned RXD layout exposes, what the driver uses, and the next measurable step

Hardware-free source review after runtime 31 (the first complete bounded C2+C3 pass).
No device, build, radio or replay action is part of this review. It reads the pinned
gen3 receive layout (`nic_rx.h`, the same layout the driver's `data-rx.h` already decodes)
and the current driver's receive path, and states one decision-changing measurement and
the dependency chain it sits on. Driver completion is unproven; nothing here claims it.

## Source findings

1. **The layout defines a received packet number.** The pinned RXD groups carry a
   16-byte PN in receive status **group 1**, present only when its GROUP_VLD bit is set
   (the GROUP_VLD field selects which of groups 1–4 follow the fixed descriptor; group 3
   is the RX vector, group 4 is the translated frame control and addresses). Accessors to
   copy the PN (16 bytes) and the RSC (its first 6 bytes) are defined in the layout.

2. **The current driver parses the group mask but exposes only groups 3 and 4.** Its
   decoder (`data-rx.h`, `mt6797_data_rx`) reads the GROUP_VLD mask to walk the
   variable groups' offsets — it already steps over group 1 when present — but the decoded
   struct surfaces only group 4 (frame control, used to rebuild the header) and group 3
   (the RX vector → `signal_valid`). It does **not** surface group-1 presence or the PN.
   The delivered frame is handed to mac80211 with `RX_FLAG_DECRYPTED | RX_FLAG_IV_STRIPPED
   | RX_FLAG_MMIC_STRIPPED` and the record states no PN is available, so no replay
   protection is claimed.

3. **Nothing on the host consumes the received PN for replay.** The vendor receive path
   makes its delivery and drop decisions from the DW2 status-flag error bitmaps and the
   specific error flags (ICV, TKIP-MIC, LLC mismatch), and reads the security mode only to
   time the EAPOL message-3 key-install action; the group-1 PN pointer is located for
   offset accounting and read nowhere, and the PN/RSC accessors have no callers. The only
   "replay counter" state is the EAPOL-Key handshake field and the GTK-rekey offload
   command — handshake and firmware-offload state, not the received-frame PN. So received
   CCMP replay is not enforced on the host in this layout; it is the firmware's, or it is
   not enforced at all. (This negative is scoped to the retained primary tree searched in
   full; it is a source-coverage statement, not proof about the firmware.)

4. **For runtime 31's delivered traffic, group-1/PN wire presence is UNKNOWN.** The data
   RX record reports `vector=` which is group-3 (RX vector) presence only; it says nothing
   about group 1. The "group-4-only" (GROUP_VLD `0x8`) fact belongs to runtime 30's
   *refused* 94-byte descriptor, not to the frames runtime 31 delivered. Whether the
   firmware sets the group-1 bit (and a PN) on the delivered, decrypted, header-translated
   data class is not in any retained record. Present-in-layout is not present-on-wire.

## The one decision-changing measurement

Record, for the already-admitted delivered unicast and group data classes, bounded
**aggregate counts over the data phase**: the GROUP_VLD mask values seen (as the decoder
reads them) and, per class, how many frames had group 1 present versus absent. The existing
first-frame record pair stays if useful. No PN bytes, no payload, no addresses, no timing
budget and no new effect: the decoder already computes the group mask to walk offsets, so
this reports a value it already derives. It is the smallest exact decoder + record +
classifier change, with the group offsets and bounds verified and the applicable C, Python
and build checks run. It is not a generic replay floor and surfaces nothing to the crypto
path.

What it does and does not settle. It settles exactly one thing: **whether group 1 is
available on the sampled delivered classes** — because that availability is currently
UNKNOWN (finding 4), not because of any supposed mode or reference contrast. It does **not**
settle replay ownership and does **not** prove firmware enforcement or its absence: a group
mask is descriptor metadata, and the firmware's actual replay behaviour is not observable
from it.

How standard mac80211 CCMP replay actually works (pinned `net/mac80211`,
`ieee80211_crypto_ccmp_decrypt`): mac80211 reads the PN from the **in-frame CCMP header**
(`ccmp_hdr2pn` at the 802.11 header length) and compares it against `key->u.ccmp.rx_pn[queue]`,
only when `RX_FLAG_PN_VALIDATED` is clear; a decrypted frame must still carry the 8-byte
CCMP header (`pskb_may_pull(hdrlen + IEEE80211_CCMP_HDR_LEN)`). The current path sets
`RX_FLAG_IV_STRIPPED`, which removes that header, so mac80211 performs **no** replay check
and there is no interface to hand it a raw descriptor PN out of band. Standard replay would
therefore require either delivering the frame with its CCMP header intact (IV not stripped)
so mac80211's own path runs, or the driver maintaining `rx_pn` state itself and setting
`RX_FLAG_PN_VALIDATED` — both needing authenticated metadata (key, TID, security queue, key
incarnation and ordering), none of which a raw group-1 PN supplies. This measurement
establishes none of that; it only tells whether group 1 is even present to consider those
options.

## Dependency chain to a usable mac80211/cfg80211 station (not a work plan, the ordering)

A complete Wi-Fi driver is a usable, maintained standard mac80211/cfg80211 station, not
this one bounded lifetime. The concrete dependencies, in order, each resting on the prior:

1. **Crypto/replay boundary** — the measurement above establishes only group-1 availability
   on the delivered classes, the first fact needed before any replay design. Who enforces
   replay (firmware, a host rx_pn with `RX_FLAG_PN_VALIDATED`, or nobody) and whether the
   CCMP header can be delivered intact for mac80211's own path are separate questions it does
   not answer. Everything data-plane rests on resolving this boundary.
2. **Packet DMA / IRQ / resource ownership, assessed from source.** The present path is the
   observed PIO fallback; whether ordinary operation needs packet DMA and the receive IRQ,
   and who owns those resources, is the next source assessment. PIO may remain a fallback;
   no unsupported hardware effect is assumed.
3. **Ordinary station lifecycle** — reusable connect/disconnect/scan, ongoing TX/RX
   ownership beyond a single bounded phase, and correct station/key/channel teardown,
   restart and unbind, replacing the one-shot join.
4. **Regression and consolidation** across the earlier phases once traffic is ordinary.

The existing audit already names DMA/IRQ and then the ordinary lifecycle and consolidation
as the main body after traffic; this review does not restate it as a plan. No upstream
submission or DCO is promised; that requires truthful certification and the subsystem's
own review when real code is ready.
