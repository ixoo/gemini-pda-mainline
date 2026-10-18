# C9: untranslated framing hint at the length refusal

Consumed once, 2026-10-18 UTC (2026-10-17 local). WPA2 and DHCP completed;
no individual ping reply or authenticated SSH was retained. After twelve CLOSED
length-equal type-2 transfers, the completed receive refused advertised/header
427/379. The new bounded hints are header-control `0x18`, status `0xe000`.
No healthy cleanup or maintained Wi-Fi. Preserved evidence and independently
confirmed changed-boot Gemian; no unchanged retry or next boot selected.

## Identity and execution

[Preparation](CCMP9_PREPARATION.md) pins kernel input
`79a2c883f2feaff6f5ed4583d05998fe73924ab6`, profile, validated 850-member
package, receipt, sources and guarded installation. Full boot2 readback matched
`851a465efddff08895b726767b95d74a59a690ab648222c2dc67a936a06f6f61`.
After owner selection, strict USB SSH verified aarch64, expected stable-monitor
release and fresh boot `05aafcdf-751b-4cf1-9cf8-34e484389528`.
The selected-reader symbol corroborates the C8 base; it does not uniquely
identify C9. Installation/source provenance and the new failure line bind C9.

Tooling `627cf81b741c2869a104f024ed21b96bd42a1690` ran one Phase-A capture
(exit 0, ready), then one actual session (exit 1). No second capture, retry or
alternate candidate. The [predeclared observation](REFUSED_RXD_FRAMING_SUCCESSOR.md)
added only retained failure hints; equality, complete transfer, poison/no-copy,
arbitration, crypto, key, credit and diagnostic limits remained unchanged.

## Independent verdicts

| Area | Established evidence | Limit / decision |
| --- | --- | --- |
| Transport | Twelve CLOSED length-equal type-2 transfers; then port 0 advertised/header 427/379, complete staged span 432, type word `0x4000`. Stop -71, branch 4. | Fatal refusal preserved. No subtraction, prefix copy, short read or 48-byte exception. |
| Framing hints | Bounds flag 1, header-control `0x18`, status `0xe000`. | Untrusted staged bytes, not a valid packet or producer identity. Matches the predeclared untranslated branch. |
| Network | Initial WPA2 negotiation, two checked CCMP Ethernet deliveries, DHCP exit/bound/lease-written 0/1/1. | No ping log or individual reply; interrupted leaf 0/0 is not a measured send/loss count. SSH attempted, exit 255, no authenticated boot match or ACK. |
| Cleanup | Monitor disable credit returned; CLOSED. Deauthentication PID 7 submitted. Terminal shared debt 0, cleanup stage 0, deauthentication still in flight. | No TX-done for PID 7, full cleanup, resource/key retirement or healthy re-arm proof. |
| Timeout/credit | Branch-1 site 0, pending 0; cached WTQCR7 one CPU/FFA pair, TC4/TC1 free 26/16, pending remainders 0. | This is a receive refusal, not a C5/C6 timeout. Cached values are not fault-time samples or proof of firmware key deletion. |
| Security | Existing monitor-assisted initial stable-PTK host-PN/checked-decap path. | Ordinary integrity/PN, GTK attribution, rekey, deletion and safe key-slot reuse remain unresolved. |

Two ordinary data submissions, PIDs 5-6, received status-0 completion and
returned pages. Firmware completion is not an independent over-air ACK.
Native ciphertext queued 0. The SSH listener passed binary/readiness checks;
the helper saw the fresh after-ACTIVE marker and attempted SSH. Readiness is
not authentication. No three-ping, ten-minute SSH or complete-cycle claim.

## Chronology and new distinction

[Numeric chronology](results/ccmp9-numeric-chronology.txt) and
[scalars](results/ccmp9-runtime-scalars.json) retain only fixed-prefix scalars.
Times below are host log microseconds since boot, not firmware arrival times.

| Boundary | Time | Observation |
| --- | ---: | --- |
| Data phase begins | 118974102 | 6152 ms budget, 5000 ms teardown margin |
| ACTIVE | 119019741 | total 0 from enable-pending |
| First ordinary submit / completion | 119378801 / 119403889 | PID 5 |
| Second ordinary completion | 119456098 | PID 6 |
| DISABLE_PENDING | 120670601 | all-RX 512, bytes 61220 |
| CLOSED | 120700891 | disable credit reconciled |
| Deauthentication submitted | 120702226 | PID 7, one page |
| Length refusal / framing hint | 120727779 / 120731014 | 427/379, `0x18`, `0xe000` |
| Stop | 120744990 | -EPROTO, branch 4, debt 0, cleanup 0 |

CLOSED class count type-2 12 means twelve transfers passed HIF equality;
it does not prove packet security or delivery. No individual accepted-transfer
length/timestamp records exist. Port 0 history: 533 attempts, 524 successful
transfers, four type-7 records, final -71 and WRPLR `0x000001ab`. Port 1:
519 attempts, no successful transfers, 505 opposite-half advertisements,
-EAGAIN and older WRPLR `0x00000050`. Attempt counts are not FIFO-read counts.

Under the pinned public [RXD layout](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic/nic_rx.h#L121-L156),
`0x18` decodes to header-length 24, offset bit clear and translation bit clear.
`0xe000` has DATA and both AMPDU bits set, NULL and the low error flags clear.
The type/group hint reports class 2 and no groups. These are conditional layout
interpretations of refused bytes. They do not establish authenticated data,
firmware integrity enforcement, a valid null frame, group removal, queued-frame
conversion or correspondence to the advertised FIFO entry. This is not the
24+16 header-only arithmetic example: the declared length here is 379.

The last successful guard returned at `120680043237` ns, WHCR 0 / WHISR 3;
terminal worker timestamp is `120686034699` ns. Port-return boundaries are
`120681257314` / `120600083545` ns. Current in-flight PID 7 deadline is
`121406815545` ns; last ordinary submit PID 6 return is `119384092468` ns.
These cached acquisition boundaries do not time firmware arrival/conversion.

## Source decision

C9 supplied the missing native-versus-translated hint without additional I/O.
It narrows review to the untranslated/group-free receive shape around monitor
disable. It does not distinguish stale length/pairing from a changed queued
representation. The repeated 48 remains unexplained. Earlier unchanged
ACTIVE/scan/boot acquisition patterns remain possible contributors; the C8
CLOSED-only selection comparison does not exclude them.

A bounded retained-source review after the run checked four files at public
commit `59e00a9144d782e148332009a835b99c43382467`:

| Source | SHA-256 | Boundary established |
| --- | --- | --- |
| `nic/nic_rx.c` | `a844bdf75065a152e78d30c789aabb398b0d0f336d30d6ffd028793bf091412b` | Lines 285-336 walk existing group bits and derive the payload from descriptor length; 2826-2908 select from one WRPLR word and assert equality after a complete transfer. Neither produces FIFO lengths. |
| `common/wlan_oid.c` | `ebfc83d78f86c4cee23207901d8cefbbdaa7b6939c8e078c28e46e703932f5d3` | Lines 10680-10717 encode SET_MONITOR with `fgNeedResp=FALSE`; no pending-RX drain or format-transition acknowledgement in this function. |
| `include/nic_cmd_event.h` | `93c8d67b1bc039a8db5b635e5a00975f2b9e408f4ab1bc8a384f5db49bf00a3a` | Lines 1643-1652 define the enable/channel payload, not a per-packet generation or length ownership contract. |
| `os/linux/gl_wext_priv.c` | `1ac3bc88c1ec9de94887ec077bf69db68f43e47b40bb7948614516489919e737` | Lines 2984-3001 change the local monitor flag/schedule work and issue the OID. This call site supplies no queued-frame retirement barrier. |

These consumer/control boundaries do not prove that firmware changes pending
frames or that command-credit return orders such a change. The precise missing
contract is the producer's relationship between FIFO advertisement, final RXD
length/group layout and monitor transition for already queued entries. Host
source inspected here cannot establish it. No supported defect correction or
new boot follows from this review. A further retained-firmware investigation
needs a separately bounded dataflow question across the prior indirect-call
boundary; do not repeat the exhausted scan or relabel a consumer as a producer.

Keep the next investigation hardware-free. Do not expand live reads, parse
refused payload, repeat C9, adjust deadlines, refund credits or weaken equality.
Ordinary crypto and healthy reusable lifetimes
remain required; the refreshed [lifecycle design](../2026-10-07-mt6797-wifi-phase-b-join/REUSABLE_LIFECYCLE_DESIGN.md)
records separate key-retirement and mac80211 teardown barriers.

## Preservation and return

Complete log: 163397 bytes, SHA-256
`3d5713a6185e0e5c897ce8c6c1477ac266bce413d1fc8efb92896d5366d545a9`,
2071 contiguous records 0-2070. Classification is complete through explicit seal.
All 63 pre-recovery entries independently match seal SHA-256
`ecc1156ade9a90ba34bc3cccc33cfa7b7c113f9aa076daa06d14bafd7e431ef1`.
Raw network/capture data and credentials remain private ignored evidence.

Owned helper safe/group-quiescent, boot-matched device-child quiescence and
A53 regression passed. No helper timeout/probe/kill error. One reviewed native
recovery request and three finite watcher connections confirmed changed-boot
Gemian `770cff12-273b-4465-899f-f9ad54d0078a`. Separate strict read-only LAN SSH
confirmed `3.18.41+` / aarch64 and the same boot. C9 remains installed but
consumed; no physical selection is pending.
