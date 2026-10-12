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

Extend the receive decoder's output and the first-frame record to report, for the
delivered keyed data class, the **GROUP_VLD mask and whether group 1 (PN) is present** (and,
when present, that a PN was attached). This reads a field the layout already defines and
the decoder already walks for offsets; it adds no decryption, no replay check, no radio or
TX behaviour, and changes one struct field and one record line. It converts finding 4 from
UNKNOWN to known on real delivered traffic, which decides the replay/crypto branch below.
It is a bounded, reviewable driver change with a direct source basis, not a diagnostic
detour and not a generic replay floor.

The branch it decides:

- **If the firmware emits group-1/PN on the delivered class**, the driver can surface that
  PN to mac80211 on the existing decrypted, IV-stripped path so mac80211 performs standard
  CCMP replay detection — a correctness gain for a usable station, with no new radio
  behaviour. Even then the host must still establish the exact key, TID, key incarnation,
  authenticity and ordering semantics before relying on it; a present PN proves none of
  those on its own.
- **If it does not**, received replay enforcement must be shown to live in the firmware or
  be declared absent, and native-format software CCMP (a separate approach needing intact
  ciphertext, the CCMP header and MIC, authentication, and its own evidence that the
  hardware can deliver such frames) is the only host-side alternative — none of which this
  field check requires or assumes.

## Dependency chain to a usable mac80211/cfg80211 station (not a work plan, the ordering)

A complete Wi-Fi driver is a usable, maintained standard mac80211/cfg80211 station, not
this one bounded lifetime. The concrete dependencies, in order, each resting on the prior:

1. **Crypto/replay boundary** — the measurement above settles whether received replay can
   be mac80211's on the existing path, is the firmware's, or is absent. Everything data-plane
   depends on knowing this.
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
