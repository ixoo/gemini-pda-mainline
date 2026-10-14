# Unwired stable-PTK CCMP decision helper — proposal 0190

This [proposal](../../patches/proposals/0190-wifi-mt6797-add-unwired-stable-ptk-rx-decision-helper.patch)
is the first **offline code unit**, not receive delivery, a selected kernel
input or hardware support. Parent is exact ND6 MAC046012/data021798/native-diag905b;
all existing driver files remain byte-identical. The patch only adds `ccmp-rx.h`,
with no production include/Makefile/flags/logging/MMIO changes. ND6 and older
artifacts/results/bindings are immutable.

## Provisional source contract and rights

Original independently written GPL-2.0-only implementation of public field and
API facts, not a vendor driver copy. Public gen3 source at
[gemian commit59e00a9](https://github.com/gemian/gemini-linux-kernel-3.18/tree/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3):

| File | SHA256 | Relevant facts |
| --- | --- | --- |
| include/nic/nic_rx.h | 0645985217a887e6c2d367955fa656b45f716a6aeeee13a29a2b462eb8dea5cb | lines105..156/455..484/673..694/760..767: RXD/group layout, status, keyID/TID, Group1 first6 RSC |
| nic/nic_rx.c | a844bdf75065a152e78d30c789aabb398b0d0f336d30d6ffd028793bf091412b | lines302..336 group4/1/2/3 walk;1313..1414 error/drop then Ethernet data handling |
| nic/que_mgt.c | 03fd22064c8bd56de4a895fde769264679c89cc05645be9e6395ecd545176a96 | lines2462..2515 translated G4/station checks;2577..2615 separate BA/reorder/class behavior |
| mgmt/privacy.c | cd644912f4351756de2e145784fd611e20165a1f75e1299c18e02f1565b8407d | lines191..244 class-error rejection;1072..1116 live WTBL station/BSS mapping |

The pinned7.1.3 upstream `mt76/mt7603/mac.h:6..59` correlates these base descriptor
bit positions. `mt7603/mac.c:539..547` handles ICV/CCMP-MIC error and hardware
decryption;564..585 converts Group1 first6 LE bytes to most-significant-first PN.
This is the **provisionally accepted layout-correlated contract**, not proof of
MT6797 firmware enforcement or interchangeable drivers/resources. Existing
7.1.3 `mt76/mac80211.c:1179..1204,1296..1351` supplies the standard seeded PN API/
strict comparison model. `include/net/mac80211.h:1508..1517` makes hardware
decryption and driver/hardware replay obligations explicit.

Actual upstream file pins: mt7603/mac.c
`59ff45dae421449647e44e7d51e6234834cda49653c34005de1cfa3937c1f1f7`;
mt7603/mac.h `61a6ccc374dc30c688c1e9809f7c506b05ab1c6d59283ef401f103042e24d13a`;
mt76/mac80211.c `df360fa98cb15603168e09cbc5798d4651d797e3457b20ed56533f15e434519f`.
Patch author identity is explicitly synthetic/non-certifying for this internal
archive; no invented DCO. Not submission-ready.

Strict checkpatch reports one error (missing truthful DCO sign-off, intentionally
withheld for the internal non-certifying archive), one warning (new-file
MAINTAINERS notice), and zero checks. No speculative maintainer identity was
added to suppress that notice; this is not a zero-warning result.

## Smallest supported scope and decision

- One current authorized station, **initial stable PTK only**, WLAN index1,
  keyID0, WLAN_CIPHER_SUITE_CCMP/16-byte key, caller-seeded PN. GTK/group,
  reinstall/rekey/slot replacement are outside admission.
- Caller context is trusted, serialized host state established by future
  activation code, never populated from a packet. `rxd_bssid` is the expected
  descriptor code, not proof it equals a command's BSS index. Own/AP must be
  nonzero unicast addresses; packet channel/BSSID/index/key/match must agree.
- Complete type2 RXD/declared length, HDR_TRAN/header14, MSDU0, security4 and
  exact status0xc000. Exact non-aggregated status excludes error/class/FCS/
  cipher-mismatch/length/LLC/null/fragment flags and either BA indicator clear.
- Mandatory complete G4/G1; checked optional G2/G3 and pad. G4 FC permits only
  Data/subtype0/Protected/FromDS, optional Retry/MoreData; no QoS/fragment/Order/
  PowerManagement. Fragment number/QoS/HTC metadata zero. RXD TID0 is an explicit
  conservative non-QoS policy; other TIDs are unsupported, not malformed firmware.
- G4 TA matches current AP; Ethernet DA matches station, SA nonzero unicast;
  Ethernet-II with a body, no length frames/EAPOL. No Ethernet bytes read as FC.
- Group1 first6 LE PN converted to standard most-significant-first order and
  compared strictly to seeded highwater. Equal/decreasing/wrapped PN rejected.
- Failure leaves **every context and output byte unchanged**. Success changes
  only highwater and returns an Ethernet offset/length. It neither delivers nor
  asserts DECRYPTED/PN_VALIDATED or any other flag. Caller serialization is
  required; future code must not use this return as firmware-authentication proof.

There is deliberately no generation field or key framework. Caller `active`
cannot detect old plaintext queued in firmware before a slot replacement. Host
removal/re-enable tests only test eligibility and seed preservation for the same
unchanged context, **not** firmware key retirement/reinstall safety. A new stable
epoch cannot be fabricated by resetting PN or toggling active. Slot reuse/rekey
requires a separately reviewed retirement/ownership contract.

## Focused checks and next review boundary

[C fixture](tests/ccmp-rx-test.c) reuses the actual existing translated-data
fixture and baseline tests with neutral synthetic addresses/PN; no real keys or
packet capture. [Runner](tests/run-ccmp-rx-test.py) pins ND6 and verifies every
existing source byte/file is unchanged and the added header is unwired.

```sh
python3 experiments/2026-10-13-mt6797-wifi-native-delivery-probe/tests/run-ccmp-rx-test.py <exact-ND6-parent-tree> <proposal-child-tree>
```

Host ASan/UBSan checks:16 masks/pad combinations, every truncation at an actual
allocation boundary (valid shortened payloads distinguished from missing fields),
every status/FC bit, wrong context/match/BSS/index/keyID/security/peer/destination,
GTK/PTK exclusion, EAPOL/length/missing PN, all PN byte carries/equality/decrease/
zero/max/wrap, unseeded/removal/re-enable host gates. False preserves state/output;
true Ethernet view matches the unchanged actual legacy decoder's span, without
using its reconstructed header. No delivery API exists in the helper.

Synthetic negatives demonstrate host rejection/state behavior, not firmware
MIC detection or negative on-wire replay tests. No injection hardware is required
for this unit; a later reviewed finite positive-hardware test can check the
provisional contract using normal traffic, with honest negative-hardware limits.

ROOT reviews immutable patch/helper/tests before publication/selection/wiring or
kernel build. Next stage is actual standard mac80211 sta/decap/key activation/
removal for one finite stable epoch, preserving HIF/credit/cleanup guards. Neither
this unit nor that first epoch establishes full maintained rekey/reuse/IRQ-DMA/
clean-profile WPA2/DHCP/ping/ten-minuteSSH. Native producer control remains
unresolved; there is no speculative mode write, retarget boot or HIF repair.
