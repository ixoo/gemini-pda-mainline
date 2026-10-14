# ND6 result — translated descriptor metadata, ordinary native zero, terminal HIF fault

One completed one-shot run. The native-beacon hook queued18 beacons, and the
retargeted sample captured one translated reported-index1 descriptor with
available Group4 FC/TA metadata. No ordinary native frame was eligible or
delivered. The native command sequence reached CLOSED at the frame ceiling,
but a subsequent HIF header-length refusal stopped the join before demonstrated
healthy cleanup. This is a negative/partial result, not authenticated ordinary native delivery,
firmware-mode acceptance, replay safety or maintained-driver support. No retry.

## Identity and preserved evidence

- Kernel input `6e29f38a0b8ba314f08331906c4d0703579a3343`, native diagnostic
  profile; [reviewed0189](../../patches/proposals/0189-wifi-mt6797-retarget-native-metadata-to-translated-index1.patch).
- Tooling `1b9b707246209cf2e648e24dd3407b8c39b0eb57`, package inventory
  `ace5aad38afdc9374f2a26964bd68b02c130dd07f9ba84597654d7fc22acab7e`,
  Image.gz `7f73a6202a8cb7faf5136d7079e179ee877e3798e3d40a136a70cb33d197dc9b`.
- [Real receipt](results/native-delivery-candidate-6.json), byte-exact
  [runtime identity](runtime-nd6/results/candidate.json):
  `a8e76bedb11e5b2c0023731611c11934bb431ef0764cb42df8d76975af8a26ee`.
  Raw boot `98c4606ef5792da7db0b4982ffad59d576100bf34e8f926a4bb8db1d720da604`,
  12668928B; full boot2
  `bf49d91c73689e479c7865ab15e298a72e859b95dfe5cfe449bae1e7c45791ef`,16777216B.
- Custodian reports guarded installation/full readback, clean shutdown and owner
  physical selection. Fresh mainline boot
  `7bde0e93-4364-43b3-bacd-b50b81116e03`, native release/aarch64 verified;
  Phase A285 PASS, ready_for_scan true. These are supplied device facts, not
  worker device actions or a newly imported deployment receipt.
- All16 sanitized bundle payload hashes independently verified by the author;
  inventory manifest
  `0033721cf3ecf614da9e3498632a2b38db546bea4736fce6e52a5944fbb56370`.
- Complete sealed kernel log2063 records/161636B:
  `971c1b7adab4379122cc1f0caf9bfc7db98112600265f25c2279b35f639ba235`.
  Coverage is sequence-zero-through-explicit-seal. No raw packets, addresses,
  keys/IV/PN, private images or personal paths are published here.

Actual built-source SHA256 pins:

| File, under drivers/net/wireless/mediatek/mt6797 | SHA256 |
| --- | --- |
| mac.c | 046012d7448d6a00c2e52ec64e48633d521045e4bda5f6c79b673a2a2959f462 |
| hif.c | 07763b3ba8f48ae71c2a629dcbe558c06a59b675d1fb7f57615ed148286e3769 |
| data-rx.h | 02179812099659607a99e0d092c58c031960375f64d502a566274c413106134a |
| native-diag.h | 905b6763ac1a15cbdca1ef0643db70585dfa443d2fdd36af223b349d157ccae0 |
| native-beacon.h | 86800ed1163078ad2c4195d8508b230c96614ae19f77bd2f55bda917374d9303 |

## Chronology and exact accounting

| Kernel sequence | Boot microseconds | Observation |
| --- | --- | --- |
| 2035 | 389225378 | DATA opens, budget6196ms/teardown margin5000ms |
| 2036/2038 | 389245977/389271040 | ENABLE_PENDING/ACTIVE, total0 |
| 2041/2042 | 389418164/389419531 | DATA PID5/pages3/bytes342, TX-done status0 |
| 2043 | 389420842 | Sole translated reported-index1 descriptor sample |
| 2044 | 389445984 | DATA credit pages3/debt0 |
| 2045 | 391413964 | DISABLE_PENDING, total512/native0/67772B |
| 2047 | 391439000 | DATA ends native-diag at2213ms; TX queued/done1, failed0, credits3 |
| 2049 | 391443021 | CLOSED, same sample counters |
| 2052/2053 | 391467137/391469810 | HIF header-length refusal, join stopped -71/branch4 |
| 2054..2061 | 391471401..391488899 | Eight terminal phase report lines |

Original classifier replay on supplied chronology and Wi-Fi SSH receipt exactly
matches the supplied verdict: sequence_ok/counts_ok true, fault true,
malformed_records0, native0, eligible_delivery/authenticated/native_delivery_pass
false. No first queued ordinary MPDU/crypto-flag sample exists; the classifier's
bypass_flags_clear false is absence of positive evidence, not observed bypass.

| Phase | Classes | Native-beacon queues | Ordinary calls | Blocked ordinary hooks |
| --- | --- | ---: | ---: | ---: |
| Pending | 0 | 0 | 0 | 0 |
| ACTIVE | class2=510, class7=2 | 18 | 491 | 1 |
| Owed drain | 0 | 0 | 0 | 0 |
| CLOSED inherited dispatch | class2=12 | 0 | 0 | 12 |

`510 + 2 = 512`; `18 + 491 + 1 = 510`. First gates are mutually exclusive:
`16 translated + 30 fcs + 391 header + 12 span + 42 frame_type = 491`.
Every ordinary call failed before Protected/peer checks in that decoder;42 did
evaluate FC for its frame-type gate. New Group4 sample FC is separately examined
metadata. HEADER391 and other rejection populations remain unidentified.
reported_idx1_translated1/untranslated0 counts only actual admitted ordinary
class2 calls with bounded reported index1, not successful beacons, blocked calls
or CLOSED traffic. It cannot describe all native or translated traffic or prove
a route universally alive/dead. CLOSED12 were separately consumed and blocked;
none reopened ordinary/legacy RX. TX completion/credit does not prove AP processing.

## Selected descriptor: available metadata, not native ciphertext

```text
phase=1 bytes=429 fields_valid=1 type=0x5faf channel=40 header=0xce groups=0xf msdu=0 status=0xc000 reported_index=1 security_mode=4 group4_valid=1 fc=0x4208 ta_ap_equal=1
```

The actual-source selector runs only after an admitted ordinary decoder call,
and selects once on its TRANSLATED rejection, class2 and reported index1.
The full16-byte RXD supplies index/security. Group4 bit8 plus at least32 bytes
permits FC at16 and TA at18. The sample's429 bytes satisfy those bounds. FC is
from Group4, **not translated Ethernet destination bytes**.

FC0x4208 reports version0, Data/subtype0, FromDS1/ToDS0, Protected1, not unicast
or destination. TA equality reports comparison with the host's joined-AP value.
The independently public-verified gen3
[nic_rx.h:82](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic/nic_rx.h#L82)
defines CIPHER_SUITE_CCMP4 (file SHA256
`0645985217a887e6c2d367955fa656b45f716a6aeeee13a29a2b462eb8dea5cb`).
Thus security mode4 reports that source's CCMP encoding, not measured decryption;
index1 is the programmed pairwise-record index. Together these narrow the
representation question beyond ND5's absent FC capture, but do not prove whole
packet ownership/authentication, firmware key acceptance, ciphertext/IV/PN/MIC
preservation or producer policy. Field availability is not packet validity.
Status0xc000 is not a transport-authentication or cipher-success certification.

Source layout arithmetic gives low6 header14, BIT6 pad2 and group4/1/2/3 sizes
16/16/8/24 after base16: derived offset82, remaining347 bytes. This is consistent
with the source-defined translated/Ethernet header-length report, not a captured
Ethernet body or DHCP identification. The unchanged ordinary decoder rejects
translation before any MPDU/header/crypto admission; no header reconstruction,
CRC strip, flags change or predicate relaxation is justified.

## Specific terminal HIF fault, separate from the ACTIVE data gap

```text
gate=header-length port=0 pre_valid=1 pre_wrplr=0x00000050 selected=80 header_valid=1 header=32 setup=1 complete=1 staging=84 post_valid=0 post_wrplr=0x00000000
status=-71 first=0 submitted=0x1801 debt=0 cleanup=0 branch=4
```

Actual `hif.c:1079..1161` selects the port0 low16 WRPLR length80, stages
logical+4=84 bytes, then requires the staged first little-endian16-bit length to
equal80. At1140..1146 it instead reads32, records HEADER refusal and returns
`-EPROTO` through `mt6797_hif_fail`/transaction-normal abort. This is **not** the
WRPLR range refusal, ordinary HEADER gate, FCS/crypto gate or a PIO return error.
setup/complete report the transfer helper completed; they do not prove correct
packet framing. No caller payload copy or packet-type publication occurs on this
branch. post_valid0 means the later WRPLR read was not reached, not an observed
post-register value of zero or proof of FIFO state.

`mac.c:1474..1485` intentionally leaves CLOSED on inherited bounded dispatch.
At2115..2133 receive branch4 logs the refusal and takes fail-stop;
`mac.c:1688..1701` prints the footer and phase reports. footer first0 is the MAC
first-error field at that point, not a successful HIF transaction; debt0 does not
establish cleanup. The supplied sequence places refusal after CLOSED, so it did
not cause the earlier ACTIVE native0/TRANSLATED/HEADER failures. Conversely a
healthy native state sequence does not negate this later join fault.

No cleanup-stage3 success is present; cleanup0/submitted0x1801 does not establish
successful deauthentication/key/channel retirement. Source stage3's
connection_loss callback at1373..1381 cannot be claimed as observed cleanup here.
Length80 versus32 is established; stale length, framing/port/producer effects or
a control packet are hypotheses only. The refusal does not export header type or
packet body, so it cannot select among them. The public gen3 caller also checks
WRPLR versus descriptor byte count (`nic/nic_rx.c:2854..2889` at
`gemian/gemini-linux-kernel-3.18` commit
`59e00a9144d782e148332009a835b99c43382467`); it is not evidence for relaxing equality.

## Readiness, incomplete leaf evidence and recovery

Helper named join fault, no READY, no SSH attempt, all_pass false. It exited1
owned/safe/group-quiescent, no timeout/kill/probe error. Cycle export is transport
OK/truncated false but **complete false**, with only80B udhcpc log; leaf numeric
status is an empty list. DHCP exit/bound/lease/listener/READY/data-check numeric
fields are **not captured**, not zeros and not an inferred DHCP failure code.

Complete supplicant export24654B reports key negotiation/connection followed by
one locally generated reason3 disconnect, not ND5's reason4. The custodian's
case-insensitive search of the complete export finds no beacon-loss-related
text; this is not a source diagnosis of disconnect. Its line order is not kernel-time
aligned; this does not prove a cause, AP fault or authenticated ordinary delivery.
Its supplied complete-export SHA256 is
`f23b91b383999a49af5cb42cad5345bcecabd62b6d78e0ae3a46ed9763ec6073`.

Device quiescence empty faults and service regression PASS. All63 pre-recovery
seals independently match manifest
`19672fbce3e67610aec1adead54829b22ecc6efe23a01b7eacb26a281502370d`.
Exactly one reviewed native recovery request and confirmed changed-boot return;
two return connection attempts are not two recovery requests. Independently
strict known-good Gemian `929b50a1-229e-434a-8c54-83dd6c3b7db1`, kernel3.18.41+/
aarch64 confirmed. Recovery success is not healthy join cleanup.

## Next decision: source-grounded representation work, not another identical probe

The measurement has answered its narrow question: the sampled translated
reported-index1 descriptor contains available Data/Protected/FromDS/AP-equality
metadata, while no such untranslated ordinary call was counted in this window.
It has not supplied an intact protected native MPDU or proof of producer policy.
Another decoder offset/units adjustment or admitting reconstructed Ethernet
cannot create the missing authentication/replay material.

The lowest-change next step is hardware-free producer/command-policy diagnosis:
use this sample to focus on the actual native monitor command and programmed
station/key record, trace independently verified caller wire fields and their
translation-selection semantics, then compare any source-grounded producer
interpretation forwarded by ROOT. Public gen3 names an eight-byte
CMD_BASIC_CONFIG_T whose first byte is ucNative80211, CID0x02/Set;
[definition](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic_cmd_event.h#L422),
[initial sender](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L3218)
and [OID sender](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_oid.c#L7070)
independently verified at that public commit. Both callers set the byte to0;
neither proves firmware consumption, supported nonzero values, untranslated
ciphertext or replay-material preservation. Do not assume monitor redispatch implies
untranslated ordinary delivery. A concrete producer control preserving native
crypto material must be established before proposing an implementation; absent
that evidence, record the missing contract rather than invent a firmware/IRQ fix.

Treat the post-CLOSED HIF mismatch as a separate framing/control-lifecycle issue.
First use retained source/evidence; it cannot be repaired by ignoring the length
check, copying32/80 guessed bytes, an extra read/retry or skipping cleanup traffic.
Any further failure-only metadata proposal must identify a decision-changing
bounded scalar absent from current records and retain poison/no-copy semantics.

No successor implementation/test authoring or build is admitted by this result.
ROOT reviews the concrete proposal first. Preserve ND6/ND5/older artifacts and
the strict classifier/crypto/radio/sample/drain/credit/cleanup contracts. Full
maintained lifecycle/reuse/rekey/replay/IRQ/DMA/clean-profile Wi-Fi is incomplete.
