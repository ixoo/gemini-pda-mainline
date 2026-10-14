# CCMP2: registration corrected; authentication blocked before CCMP

## Completed run and identities

ROOT executed exactly one capture/session on boot
`271cca5e-f3ba-4a27-9939-c8d47d498afd`. Kernel input commit remains
`5c5a7b10932b506c87e4ef624d018330bbf6490e`, approved source
`0fcdc1ee65d588a2fc9cdbfc61cd39761cb71e01`, driver MAC SHA256
`a140b36a170a8608f48ca1dbb014b98181e337a2df58c768c37239b5f3ada746`,
package inventory `0304e09eaa435e8faa37113564f2f5c340ffac9d84a601772eefbea40cf26d7b`.
Completed tooling is frozen at `b1160d90a8033de79be769713166ac8081ec23dd`.
The [real candidate receipt](results/ccmp-stable-monitor-candidate-2.json)
binds raw e7e7e433/full
`7b2b881b74b958502cd9c148f10b23c58949ea221f75281c9d97721d8b3bd60e`.
Source, tooling, package and installed full-partition identities are distinct.

ROOT reported one guarded write, verified predecessor418 and full16MiB7b2b
readback, sync/flush and clean shutdown. A missing private-environment variable
caused the installer to exit2 at its final local receipt validation **after**
the completed write/shutdown. The operator corrected only local receipt
validation; no repeated device write/action. Actual deployment-summary SHA256:
`826a2658e0df9307fe97440932d38a64f009dd82b808d85b69734a7db626fe91`.

## Observations, absent evidence and return

The explicit CCMP suite fixed the observed registration failure: Phase A ready,
common285/calibration pass, regulatory0, TC4 snapshot2=0, wiphy count1/index0/
bound1. One scan-result phrase; no association, message1/3, PTK or GTK install,
key-negotiation/connected phrase, CCMP queue or monitor ACTIVE evidence.

Numeric kmsg chronology (microseconds from boot):

| Event | Time | Observed fields |
|---|---:|---|
| Passive scan complete | 79151877 | status0/frame1/beacon1/credit1/retired1 |
| Channel grant | 79346281 | channel40/interval9000ms |
| Peer ready | 79371477 | sequence23 |
| AUTH TX | 79394278 | subtype11/pid1/pages1 |
| AUTH TX-done | 79419331 | pid1/status0/advanced1/count1 |
| Join stopped | 79538195 | status=-95/first=-95/submitted0x800/debt0/cleanup0/branch1 |

The helper terminated as joinfault, with no READY or SSH proof. The122-byte cycle
export was intact, untruncated and empty. DHCP numeric fields are **absent**, not
zero; zero observed cycles/association/key phrases do not manufacture DHCP
measurements. Compatibility/provisional/full maintained support remain false.

Full sealed log complete:150352B, SHA256
`76969a48cc799d09f98b5cd4c1663d4be19e787b6db019806e6edf0da4774e7d`.
ROOT independently verified63 PRE hashes against seal manifest
`0056ad93d7a3ee522d2078b8aa10fb229a7efc1d8102d6d58cebad412b5db314`;
helper group safe/quiescent and device child quiesced. A53 regression passed.
Exactly one reviewed recovery, two LAN connection attempts, changed Gemian boot
`fffd9a0b-ecee-4f7c-b821-84eed7ffbac8`, independently verified3.18.41+/aarch64.
Device remains ROOT-owned in Gemian; no worker device access or repeat run.

All14 supplied sanitized final payloads independently hash-verified, manifest
SHA256 `466ba3499067febca35aaeb24b3afc83fe3388d62a5d1a2d2ab878fb70e93790`.
The raw supplicant log remains private; its supplied sanitized counts report
13817B/complete and no association/handshake. No raw AP/key evidence is published.

## Pinned source diagnosis: management starvation, not CCMP decoding

Line numbers below refer to approved0f source, not a subsequently edited tree.

1. `mac.c:2593–2594` executes an unconditional CCMP-mode `continue` outside
   native engagement. It sits **before** the unchanged strict directed management
   decoder at2818 and AUTH/ASSOC state updates at2827/2837. Thus even an otherwise
   valid AUTH response is silently withheld before `join_auth_received` and
   mac80211 RX delivery. The earlier clear EAPOL path remains unchanged, but is
   association-gated and cannot replace management authentication.
2. `.tx` records `join_seen |= BIT(11)` on accepting the first AUTH at4329.
   The observed submitted0x800 confirms the corresponding first AUTH submission.
3. In pinned7.1.3 `net/mac80211/mlme.c`, `ieee80211_sta_work` handles ACKed AUTH
   TX status at8657–8668 by setting `IEEE80211_AUTH_TIMEOUT_SHORT` (`HZ/10`, line38).
   At8697–8705, absent successful AUTH completion, its timeout calls
   `ieee80211_auth`; that calls `drv_mgd_prepare_tx` at8540 before another AUTH.
4. `mt6797_mac_mgd_prepare_tx` at3742 rejects a subtype already in `join_seen`.
   At3751 it **stores** `first_error=-EOPNOTSUPP` and closes admission; this is a
   void callback, not a firmware error return. The unchanged one-shot refusal is
   intentional. At2024–2027 worker branch1 observes that stored error and calls
   `mt6797_mac_join_fail_stop` through the failed label at2902.

The observed TX-done-to-stop118.864ms is consistent with the100ms AUTH retry
timeout plus worker scheduling. This identifies a concrete source call path
and reproduces its exact stored errno with actual callback fragments. However,
the sanitized chronology has no callback-entry record or accepted/raw AUTH RX:
the retry attribution is source-and-timing inference, **not directly observed
callback tracing**, and AP response arrival is unproved. Branch1 means stored
error propagation, not a crypto parser or firmware failure. Core cipher
registration and later set-key/software-crypto policy do not explain this
pre-association obstruction. No software-crypto flag change is proposed.

## Minimal review candidate, not selected or built

[Review patch](review/0193-ccmp-management-path.patch), SHA256
`0297b9ee121ad5bff43fcca7f44ad0435cb588c89cc7032479da4d3e22a7d075`,
author source `e1ecfcd967a246ad72627b9fd2d92caaa31c59a0`, parent0f,
child MAC SHA256 `261a159513497d6e541831f1db442ddbd4974f781173fac4d3c718d095cc6139`.
Only13 additions/2 deletions in MAC: run the existing strict management decoder
before withholding and route **only its accepted result** to the unchanged
management state/update/queue block. Nonmanagement and malformed packets stay
withheld. This does not route through any legacy ordinary-data decoder.

All addresses/channel/framing/status/subtype/transaction/fragment/IE gates,
submission/duplicate checks, RX signal/queue behavior, callback refusal, initial
PTK/GTK installation, PTK-only RX, HIF poison/no-copy, credits/TX-done, finite
monitor/cleanup/seal/recovery contracts remain unchanged. No AUTH retry, GTK RX,
rekey, reuse, observer/sample, radio command, budget or software fallback added.
Management acceptance does not prove firmware integrity or hardware key deletion.

[Focused test](tests/ccmp-management-path-test.py) extracts and compiles actual
parent/child dispatch and `mgd_prepare_tx` fragments with the unchanged parser.
ASan/UBSan PASS: parent valid-AUTH starvation and next-preparation-EOPNOTSUPP;
child AUTH/ASSOC/deauth/disassoc paths, status handling, duplicate-response
refusal; unchanged repeated-AUTH refusal and old-mode management; ten invalid/
ordinary-data mutations and truncated association IE withheld. Exact MAC delta
reversal and all other driver-file equality pass. These are synthetic host
tests; the station-authenticated premise is explicitly injected, not a full
mac80211 state-machine/hardware execution claim. Checkpatch's only remaining
error is the honest missing DCO; internal synthetic archive, not upstream-ready.

Material review precedes selection/build. Existing series/profiles/config/DT,
CCMP2 tooling and receipts are unchanged. No unchanged artifact retry. After
review, a new candidate must test whether the existing strict AUTH/ASSOC path is
actually exercised, retaining the same finite DHCP/ping/SSH and complete proof
requirements. Continued absent AUTH response remains a negative result, not
permission to admit retries or relax framing. Full Wi-Fi lifecycle/producer/
GTK/rekey/reuse/IRQ-DMA/ten-minute acceptance remains incomplete.
