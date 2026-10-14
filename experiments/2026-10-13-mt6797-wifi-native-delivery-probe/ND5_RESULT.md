# ND5 result — native-beacon hook demonstrated, ordinary crypto remains negative

One completed device run. The new native-beacon hook successfully queued26
strictly matched unprotected beacons through the normal helper. The diagnostic
completed its healthy owned sequence/cleanup at the existing frame ceiling.
Ordinary native eligibility/delivery and authenticated Wi-Fi exchange remained
zero. This is not firmware-mode acceptance, replay/crypto, throughput or full
maintained-driver support.

## Exact identity and evidence

- Kernel `eaafab2fa0d6f886768c7d0aa6f5c586d1f163cf`, native diagnostic profile;
  [reviewed source](NATIVE_BEACON_REVIEW.md), [build/preparation](ND5_PREPARATION.md).
- Tooling `7c50003480a5f0d67fe5a96d5eac1b39a21951e0`, package inventory
  `3f6754e02895ea3b12094d8520c79e8eac743180e454a89d64a3ef483a39d919`,
  Image.gz `759f12a22a9a6ea7927437eeff05cddc256f03dea46df3c7773e6fe4d137550e`.
- [Real receipt](results/native-delivery-candidate-5.json)
  `25893fa2bf4b67364e0821e635c0105c212f110d37156748d8e5a9338a612ef8`;
  raw boot `f6b3a0d30d4955655c9c7d0fdcc3b7ef8aef880655e976fdc517ae5aa574fe50`,
  12668928 bytes; full boot2
  `6fec5cf5227f58deef91c0c1b0213956ab6c88f61292961d2817a6e6ec273ae0`,16777216 bytes.
- Custodian-validated installation receipt metadata:
  `062b94754b42d0771531176590078220982a8ccdded02159662e72f694b8c201`,
  full readback matched, guarded inactive boot2 distinct from root, actual ND4
  predecessor/power verified, clean shutdown and owner physical selection.
  These supplied installation facts do not constitute a new worker device call
  or newly rehashed deployment-receipt import.
- Mainline boot `a8b2d6e2-34c8-4090-8684-c4d6210607ed`, strict native release/
  aarch64/wpa_cli pin verified. Phase A285 PASS, `ready_for_scan=true`.
- Complete log `0e72440793b3487df29e83a072a99ca2ea4153ad830b188fa4f3439e58f0e3ea`,
  162627 bytes /2074 records, sequence-zero-through-explicit-seal coverage.

All17 payload hashes in the sanitized18-file bundle were independently checked
by the author. Raw payloads, addresses, PSK/keys/IV/PN, personal paths and private
images remain with the sole laptop custodian. Boot/evidence/deployment digests
are published under project policy. No new kernel build or hardware action for
this source/metadata reassessment.

## Observed chronology and accounting

| Sequence | Boot microseconds | Observation |
| --- | --- | --- |
| 2033 | 79352599 | DATA opens: budget6168ms / teardown margin5000ms |
| 2034 | 79373115 | Enable pending, state1/action1, total0 |
| 2035 | 79374476 | Existing class7 keyed beacon delivery, generic count3 |
| 2037 | 79398156 | ACTIVE, state2/action0, total1 /442B /native0 |
| 2038 | 79421175 | Sole ordinary-call descriptor sample, below |
| 2039 | 79521933 | Generic beacon delivery count4; native attribution comes from separate terminal counter |
| 2040/2041 | 79869160/79870411 | DATA PID5/pages3/bytes342, TX-done status0 |
| 2043 | 82069114 | Disable submitted, state3/action2, total512 /82418B /native0 |
| 2045 | 82094140 | DATA ends: native-diag, elapsed2741ms; TX queued/done1, failed0, credits3; inherited RX unicast/group/dropped0 |
| 2047 | 82098164 | CLOSED, state4/action0, same counters |
| 2049 | 82100679 | Deauth PID6 TX-done status0 |
| 2063 | 82256728 | Healthy cleanup stage3, credits returned/slots retired/deauth1 |

The original classifier replay on the supplied numeric chronology/SSH receipt
exactly reproduces the provided native verdict: `sequence_ok=true`,
`counts_ok=true`, `fault=false`, `malformed_records=0`, ordinary native0,
`eligible_delivery=false`, `authenticated=false`, `native_delivery_pass=false`.
There is no HIF refusal or join-stopped footer. No first queued ordinary MPDU/
crypto flag sample exists; absent samples do not demonstrate bypass flags set.

| Phase | Consumed descriptor classes | New native beacons | Ordinary calls | Blocked at ordinary hook |
| --- | --- | ---: | ---: | ---: |
| Pending | class7=1 | 0 | 0 | 0 |
| ACTIVE | class2=508, class7=3 | 26 | 481 | 1 |
| Owed drain | 0 | 0 | 0 | 0 |
| CLOSED inherited cleanup | class2=5, class7=10 | 0 | 0 | 5 |

Exact sample accounting is `1 pending + 511 ACTIVE = 512`. ACTIVE class2 is
`26 native beacons + 481 actual ordinary decoder calls + 1 blocked = 508`.
First-failure totals are:

| First gate | Calls |
| --- | ---: |
| Translated header | 27 |
| Conservative FCS metadata filter | 22 |
| Reported header length not24/26 | 330 |
| MPDU span under current source walk | 34 |
| Version/frame-type check | 68 |
| **Sum** | **481** |

These are mutually exclusive **first evaluated failures**, not all failed
predicates. The68 FRAME_TYPE calls did evaluate FC, and the beacon hook validates
FC; **no FC value was captured**. Every ordinary call failed before Protected evaluation and before
AP/address checks in the ordinary decoder. Protection and target ownership
therefore remain unobserved in its reported rejection counters
for those calls, not proven absent. HEADER/TRANSLATED totals alone cannot identify
target-AP data versus other air traffic. Inherited translated RX counters0 do
not measure these calls. CLOSED packets were separately consumed for inherited
cleanup; five blocked ordinary hooks did not decode or reopen legacy data.

The new native-beacon counter increments only after admitted class2 decoding
and successful normal helper queueing. Its26 proves that hook ran, unlike
generic beacon logs that can originate from unchanged class7 paths. It does not
prove every queued frame was accepted by MLME or the AP authenticated. Ordinary
eligible/native counters remain separate and zero.

## Sole ordinary sample: bounds observation, not packet identity

```text
one-shot WLAN native RX descriptor: phase=1 bytes=92 fields_valid=1 type=0x4e00 channel=40 header=0x5a groups=0x7 msdu=0 status=0xd000
```

Verified byte-layout arithmetic gives groups1/2/3 offset64 plus BIT6 pad2 =66;
reported low6 header length26 leaves26 bytes. Under the unchanged strict data
decoder that span is less than the required26+CCMP8+MIC8=42 bytes, before any FC
or protection check. There is no FC/body/address sample. This is not proof of
QoS-null, data subtype, Protected value, AP identity, ciphertext stripping or
the composition of the330 HEADER/27 TRANSLATED failures. No units/offset repair
or payload reconstruction follows from it.

No eligible protected ordinary MPDU was observed; there is no basis for a guessed
CRC strip or crypto/predicate relaxation. Producer FCS trailer semantics remain
unknown. Per-frame crypto flags0 are distinct from mac80211's hardware
`IEEE80211_HW_RX_INCLUDES_FCS` contract; neither establishes producer framing.

## Window, readiness, disconnect and final recovery

The window reached the unchanged512-frame limit, not ND4's early disconnect.
No all-RX ceiling was expanded; the last counted packet was withheld by the
existing post-count admission ceiling. Healthy disable/credit retirement,
CLOSED and cleanup were observed. No claim of arbitrary lifecycle reuse/rekey.

Helper: READY absent/SSH not attempted because this cycle's window closed at
stage3, not a named join fault. Leaf DHCP exit137/bound0/lease0/listener0/READY0/
data_checks_failed1; udhcpc log110B. No delivered lease is not proof that no
response arrived on wire or was withheld. The readiness contract was not bypassed.

The complete supplicant export contains locally generated reason4 disconnect,
but no beacon-loss-related text. Line order is not aligned to kernel monotonic
times; the existing stage3 connection_loss callback can explain a terminal
disconnect, but exact attribution is not established by this export. Do not
claim AP fault or renewed monitor loss, or that beacons alone authenticated data.

Device quiesced with empty faults; helper group safe/quiescent. Independently
all63 seals matched manifest
`10af9923e4f91fb9aa3145a7d6aacb87862c86c751f5a08bc2a836e0e3c26871`.
Final deferred result confirms service regression PASS and exactly one reviewed
recovery request/confirmation. Two return-collector connection attempts are not
two recovery requests. Independent strict Gemian verification: kernel3.18.41+,
aarch64, changed boot `7cadd2e1-b727-46bd-ad27-6390a2244a99`.

## Ordinary-data gap and next decision

No evidence-grounded decoder/crypto correction is established. Current exported
records do not supply RXD index/security or group4 FC/TA for the27 translated
calls. First check any already retained scalar records for those fields; absence
does not admit an identical retry. A smallest source-grounded observation proposal
is to retarget the existing ONE descriptor sample to the first actually admitted
ordinary class2 translated call reporting the programmed pairwise index1. Add
only bounded RXD index/security and valid/absent group4 FC plus TA-to-joined-AP
equality. Translation payload is Ethernet: its first destination bytes must
never be read as FC. If group4 is absent/short, FC/TA stay explicitly absent,
not non-data/non-peer/unprotected. No MAC bytes, payload, IV, PN or key output.

Two ACTIVE admitted-call counters can give context: reported index1 with and
without translation. They describe a programmed-index descriptor split, not
ordinary/protected/target-AP traffic, firmware key/peer acceptance or a route
universally alive/dead. In this scope already accepted native beacons are excluded;
late blocked/CLOSED calls are not counted. Keep eight terminal phase lines and
the single sample. No per-gate sample expansion or header histogram is proposed.
Even FC/TA scalar matches would be metadata observations, not authentication or
permission to admit a translated/otherwise rejected frame. HEADER330 remains an
unresolved separate population unless source-valid additional evidence exists.

This is a proposal for coordinator source review, not implementation authority.
Keep existing calls/decisions/offsets/crypto0/no-radio/credit/cleanup/one sample/
terminal-line and all-RX budgets unchanged. No source/test authoring or build has
begun; await materially resolved diagnosis and coordinator decision, including
its independently initiated advisor interpretation. No identical retry.

ND5/ND4/ND3/C35 artifacts and inputs remain immutable. Full maintained lifecycle/
reuse/rekey/replay/IRQ/DMA/clean-profile Wi-Fi objective remains incomplete.
