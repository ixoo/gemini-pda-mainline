# GTK handoff: existing mac80211 decap path and driver obligations

Source-only review performed while [C11](CCMP11_PREPARATION.md) awaited owner
physical selection. The [C11 result](CCMP11_RESULT.md) subsequently established
positive group-PN availability; GTK delivery remains withheld. No new candidate, GTK acceptance, frame acquisition or device action.
The [C11 observation](GROUP_PN_SUCCESSOR.md) establishes only sampled availability.
The unchanged C10 baseline and the later [D3 diagnostic](SESSION_0202_PLAN.md#evidence-and-later-work)
are now recorded. The owner adopted group-first preparation after D3; the new-build hold remains. No GTK acceptance code has been added.

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

## Post-D3 reassessment of the group-first proposal

The [C11 source-status clarification](CCMP11_RESULT.md#later-source-status-clarification-no-additional-device-run)
supports the researcher's key observation: 32 received groups passed the clean
translated shape/key-ID/TID/EtherType gates, including mandatory G4 and observed
G1, and were still withheld by the PTK-only checker. Group withholding is a host
policy, not evidence that those group packets were lost before the driver.
Their EtherType breakdown was not retained. It does not yet establish that any
was the laptop's ARP request or caused the earlier SSH failures. Neither blanket
"upstream fault" nor proven driver-caused SSH failure follows from these counts.

D3 authenticated with an absent initial neighbor entry that became complete,
without a ping intervention. This demonstrates successful resolution in that
run, not its mechanism. A's success deliberately prevented B; no extra boot is
justified as an automatic repeat.

The proposed group predicates and separate PN state are a reasonable basis for
reviewing a bounded initial-GTK extension. Mandatory G4 followed by G1 places
G1 at offset 32 in the existing wire order; the PTK accessor already reverses
its six-byte PN. Reusing an accessor does not establish GTK ownership or seeding.
A group context must bind the installed GTK ID, BMC index, station/key lifetime,
real receive-sequence seed and strict monotonic PN independently of PTK. Reject
missing metadata and retain full validation/allocation before advancing PN.
The existing current-station/authorized/RCU handoff gates must still apply.
Passing the AP station pointer enables the Ethernet path; it does **not** ask
mac80211 to select a GTK or check replay. Those remain driver obligations under
the pinned contract above. No rekey, deletion/reuse or stale-frame guarantee is
implied by adding initial group acceptance.

A counters-only withheld-ARP count can use the already validated EtherType
without reading PN or exporting addresses/content. A positive count proves that
ARP-class groups reached and were withheld by the host; without sender/target
attribution it does not uniquely identify the SSH peer's resolution attempt.
Specify this narrower observation and decision before implementation.

The repeated 48-byte difference equals G1+G2+G3 and the opposite signs are
consistent with a format/length-record association race. They are not proof of
that mechanism: associating different FIFO records can also produce either sign.
The current TX-credit quiescence is not an RX-producer fence. Early write-once
0202 remains a bounded comparison, not a proven fix or proof of RX quiescence.
No new register access or deadline extension is authorized by this inference.

The owner explicitly superseded framing-first ordering: prepare initial GTK
first, with 0202 retained as a separate framing comparison. The approved 0203
exception is now selected by independent `CONFIG_MT6797_CCMP_60S_WINDOW` and a
C10-derived profile that excludes 0202. Request/grant/window boundaries pass
locally; Linux validation of this revision is pending. Builds and device work
remain on hold, and the 120/600-second stages are not included in this change.

## Predeclared initial-GTK preparation

The successor starts from C10 plus the independent 60-second window, without
C11's availability observer or 0202's global format change. Retain the C10
mask protocol and reject any RX length mismatch without adjustment. This is
one initial-key compatibility experiment, not maintained normal-mode crypto.

Keep the PTK checker unchanged. Add a separate GTK context with the same strict
shape/error/fragment/TID/aggregation predicates, changing only key class/ID,
BMC index and group destination. Key IDs 0..3 must match the single installed
GTK, WLAN index must be 2, and Ethernet RA must be group-addressed. Require G4
and G1; reverse the six-byte PN at offset 32 and require strict increase over
the real GTK seed. No same-PN exception, QoS expansion or PTK replay-state reuse.

Read the initial GTK sequence with the pinned key API's TID 0 convention before
any GTK acceptance, serialized against receive handoff. Do not acquire the
receive mutex while holding the MAC mutex: the receive path uses the opposite
order. Release it before any firmware-credit wait. Only successful key command
credit and current station/key admission can publish the seeded GTK context;
credit remains buffer retirement, not an independent firmware key-install ACK.

Authorization follows the current AP station. Any existing withdrawal closes
both contexts before synchronizing the receive batch; no queued frame may
escape after key/station teardown. Allocation precedes PN mutation. Retain
permanent poison and prohibit every reinstall, rekey, reuse and reconnect.

Add the requested single withheld-ARP counter using the validated group
EtherType, without a PN read in the classifier or retained frame content.
A one-time first-checked-GTK-queue event is also needed: ARP/SSH already succeed
on C10, so network success alone cannot prove that the new path was exercised.
This event is queue evidence, not independent core delivery or firmware
integrity proof. PTK and GTK together retain the existing 64-frame delivery cap;
other RX/byte/PID/poll/time limits remain unchanged.

Actual-source fixtures must distinguish both PN contexts, GTK IDs, missing or
truncated groups, replay/equality/rollover, wrong status/peer/destination, stale
keys and queued frames, allocation failure, authorization/withdrawal races,
option-off parity and unchanged HIF receive behavior. Synthetic checks prove
host behavior only. No candidate build or radio test follows automatically.
