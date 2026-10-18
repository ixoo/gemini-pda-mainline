# GTK handoff: existing mac80211 decap path and driver obligations

Source-only review while [C11](CCMP11_PREPARATION.md) awaits owner physical
selection. No new candidate, GTK acceptance, frame acquisition or device action.
The [C11 observation](GROUP_PN_SUCCESSOR.md) must establish its missing metadata
availability before selecting a strict initial-GTK checker.

Input: the actual prepared Linux 7.1.3 source for kernel commit
`774e08aa5570f96986acc1fd2a40afa0c226777d`, using the
[manifest-pinned archive](../../kernel/manifest.json). Exact files:

| File | SHA-256 |
| --- | --- |
| `net/mac80211/rx.c` | `d2db151ef96e779c8bb3844a53d7742b0c9d0c1868f76929bf278b0a4de1648b` |
| `include/net/mac80211.h` | `bc2cfea5976ba788e437b3293b324cd156471c6dcd1df17d43519215c7b0f6fd` |

The inspected receive windows were `rx.c:4864-4978`, `5120-5265` and
`5615-5652`; flag obligations are in `mac80211.h:1511-1517,1603-1604`.
These are source contracts for this pinned core, not firmware enforcement tests.

| Boundary | Source behavior | Driver obligation |
| --- | --- | --- |
| RX_FLAG_8023 dispatch | Routes directly to `__ieee80211_rx_handle_8023`. | Deliver an actual complete Ethernet frame with already checked security metadata. |
| Station/core eligibility | Requires an Ethernet header, non-null current station, successful RX station/link setup and a current `fast_rx` object. | Preserve the core decap callback and authorized-station/RCU/handoff eligibility gates. |
| `ieee80211_rx_8023` | Updates statistics and delivers to the local stack. Its forwarding branch explicitly handles multicast; no unicast-only destination restriction appears in the station delivery path. | Source-check multicast ownership before queueing; do not infer key ownership from successful core delivery. |
| Crypto/key/replay | This direct path does not perform the 802.11 decrypt handlers, choose a GTK or compare the packet's PN. Stripped IV prevents core replay detection; PN_VALIDATED describes an actual completed replay check and requires decryption. | Check the current trusted key class/index/ID, per-frame integrity status, mandatory G1 and a strictly increasing correctly seeded PN before asserting those flags. |

Consequently the existing Ethernet decap handoff can remain the basis for an
initial GTK implementation if its independent source/metadata contract is
supported. C11's observation-policy eligibility is not that check: it reads no
PN value, authenticates no frame and still withholds group delivery.

A future positive availability result would justify reviewing a separately seeded
GTK context alongside the unchanged initial PTK context, with unambiguous packet
class/key attribution, mutation only after full validation and allocation, and
withdrawal before key/station pointers can be freed. This review changes no
callback, context or acceptance code and does not select that implementation.
Missing required metadata must continue to reject. Firmware integrity attribution,
rekey/deletion and queued-frame retirement remain obligations before key reuse;
the [lifecycle barriers](../2026-10-07-mt6797-wifi-phase-b-join/REUSABLE_LIFECYCLE_DESIGN.md)
and two-lifetime/ten-minute acceptance remain unproved.
