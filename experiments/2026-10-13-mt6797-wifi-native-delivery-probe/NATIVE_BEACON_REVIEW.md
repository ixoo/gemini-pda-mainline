# Native beacon proposal — offline source review, not a runtime result

[0188](../../patches/proposals/0188-wifi-mt6797-admit-intact-native-beacons-in-active-diagnostic.patch)
SHA256 `f2d5c61673b278eb1c57dee731a18ea2258e9915896cfbe4fb9710f5b3a09ad1`.
Reviewed proposal on the exact ND4 built driver, mac.c
`47dbe9567a216aef6ae2703ee13204c49eb9594c1015c64f369e45598dd4c751`.
Two driver files only: new native-beacon.h and MAC dispatch/one report field,
86 insertions /3 deletions. Coordinator exact-source review approved immutable
source commit `16cb97670534dbe184a91c73ccc99a9d2c8af40a`, a reviewed
formatting-only successor to67d. Replay equals new
native-beacon.h `86800ed1163078ad2c4195d8508b230c96614ae19f77bd2f55bda917374d9303`
and mac.c `0327fcd9ddddae40dff6575296da9cff496adbb691141dc8c56c557799555e28`.
Selected only in the explicit native profile series and canonical order;
manifest/configuration and18 other explicit profile series remain unchanged.
The four historical global-series consumers inherit the archive append under
existing approval, not new foundation/build admission. No runtime change or
kernel build result is claimed here.
[ND4](ND4_RESULT.md) remains negative;
actual ACTIVE native-beacon presence is **unproved**.

## Source contract and hypothesis

Independently public source at
[gemian/gemini-linux-kernel-3.18, commit59e00a9](https://github.com/gemian/gemini-linux-kernel-3.18/tree/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3)
corroborates the existing byte-layout contract:

- [nic_rx.h](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic/nic_rx.h),
  SHA `0645985217a887e6c2d367955fa656b45f716a6aeeee13a29a2b462eb8dea5cb`:
  base16, groups4/1/2/3 sizes16/16/8/24, header low6 directly in bytes,
  BIT6 pad2, BIT7 translation; FCS bit1/ICV bit4.
- [nic_rx.c](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_rx.c),
  SHA `a844bdf75065a152e78d30c789aabb398b0d0f336d30d6ffd028793bf091412b`:
  nicRxFillRFB walks4/1/2/3 then pad, returns original header/remaining span;
  class2 uses the monitor consumer when enabled, separate from class7 management.

Public source bytes were independently verified by the coordinator; local bytes
match those pins. The new implementation is independently expressed, not a
vendor-code copy. There is no supported units/group-offset repair to the ordinary
decoder. The hypothesis is that accepting a correctly formed raw native class2
beacon through normal MLME may avoid the observed local beacon-monitor loss.
No ACTIVE beacon FC/AP/content was captured in ND4. The442-minus64=378 length
correspondence, missing delivery logs and first-gate counts do not establish
beacon arrival, matcher failure on all frames, correct non-data classification
or firmware-monitor acceptance.

## Exact delivery delta

The new pure decoder requires matching declared count, bounded buffer, class2,
channel40 at the call site, translation off, reported24-byte header and MSDU0.
It independently walks optional groups/pad, requires group3 for the existing
signal helper, validates full group/vector span and at least36 MPDU bytes
(header24 + fixed beacon fields12). RCPI must be at most220. FCS/ICV errors are
conservatively withheld. Information-element semantics remain with mac80211.

It validates actual version0 management beacon subtype, no DS/Protected/
MoreFrag/Order, fragment number0, broadcast destination, and both TA/BSSID equal
the joined AP. Group4 never substitutes header/address fields; the actual raw
MPDU is checked. Probe responses, data, other AP/destination, protected/translated
or malformed shapes are not delivered. Successful output is only original
offset/length/signal, with input and failed outputs unchanged. No reconstruction,
FCS stripping, fabricated beacon or new read.

Dispatch is inside the existing native-engaged ordinary hook, immediately after
its existing `mt6797_native_diag_admit` evaluation and before the unchanged
ordinary-data decoder call. Successful association, no cleanup completion and no
deauth completion are required. Central all-class count/byte accounting and the
post-window owed-only gate already ran. Only ACTIVE below existing ceilings can
reach new delivery; pending/disable/CLOSED/off/over-ceiling cannot. The exact
existing helper queues the untouched MPDU with normal mac80211 RX status and
crypto bypass flags0; allocation failure takes the existing failed terminal.

Both earlier class7 beacon selectors and delivery paths remain unchanged.
They retain their historical semantics, including delivery outside native ACTIVE.
This proposal does not disable beacon monitoring, forge READY, suppress regulatory
stop, refund credit, re-arm, expand budgets or change ordinary-data eligibility.

## Attribution and accounting

Only after new admitted class2 decode **and successful normal helper delivery**
does `native_diag_rx[phase].beacons` increment. Failed allocation/no admission/
other AP/other class do not increment it. It appears as `beacons=` in the existing
once-per-terminal `native RX classes` line: same eight phase report lines,
same one existing descriptor sample, no new output line or payload sample.
Existing generic beacon logs alone do not identify the new hook.

These frames consume the existing total RX/byte ceilings, never the ordinary
protected-native64/eligibility/crypto counter. They return before the ordinary
decoder, so class-minus-gate/blocked accounting now also includes successfully
delivered native beacons. First-gate sums still equal actual ordinary calls.
Neither `beacons=` nor generic MLME delivery is a native crypto/data PASS.

## Focused evidence, synthetic only

[run-native-beacon-test.py](tests/run-native-beacon-test.py) pins the ND4 parent,
checks exact two-file scope and reverses only the added dispatch/counter/report
field to obtain byte-identical MAC source. All other driver files, ordinary
decoder, flags/budget header, stop/drain/regulatory/credit functions remain
byte-identical. It compiles the actual helper, actual class7 selection, central
accounting and complete native dispatch bodies with explicit allocation/queue/
clock/log stubs under strict compiler warnings and ASan/UBSan.

- Same synthetic source-defined class2 beacon: exact ND4 parent withholds and
  fails the positive assertion; child queues it verbatim, flags0 and no ordinary
  data eligibility/sample increment. Parent is a real runtime assertion oracle,
  not a compile failure.
- All16 group masks and both pads; group3-present positives, absent-vector
  negatives; count/channel/header/translation/MSDU/FCS/ICV/RCPI/full fixed-bound
  checks, every address byte, FC/fragment/subtype negatives and one-bit mutations.
- ACTIVE-only native dispatch, off/pending/disable/CLOSED/drain and each existing
  ceiling; joined-AP/association/cleanup/deauth failures; allocation failure;
  central sample/drain count/bytes retained; successful native-only scalar counter
  and once-only eight-line report, class7 counter exclusion.
- Actual ordinary protected-data positive still queues original bytes with
  unchanged eligibility/native/data sample accounting and crypto bypass0.
  Existing paired actual-HIF/ordinary decoder20000-mutation/phase/classifier,
  native-loop and native-diag flags/ceiling fixtures also pass on replay.

These are not kernel concurrency, actual native-beacon traffic, on-device MLME,
firmware, authentication/replay or sustained-support evidence. Strict checkpatch
on the exact approved16cb export reports only the acknowledged archive exceptions:
one missing-signoff error and one new-file MAINTAINERS warning, with zero style
warnings/checks. These are reported, not described as an unqualified clean checker
result. The archive has no DCO certification and is not submission-ready.
The exact production source/replay hashes above replace the earlier67d export;
no stale patch/source pin mix. No fabricated DCO or kernel build result.
ND3/C35 inputs/evidence remain unchanged.
