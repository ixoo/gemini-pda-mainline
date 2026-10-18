# Before implementation: observe GTK PN availability without delivery

C10 passed one finite mask-only initial-PTK lifetime. Its checked receive path
accepts only unicast PTK frames and bypasses the older per-class PN counters.
Consequently its 36 deliveries prove no GTK PN availability. No raw RX capture
exists from which to reconstruct that missing scalar. The earlier legacy
runtime 32 observed group 4 only, before the mask-only comparison.

The pinned same-chip gen3 source at commit `59e00a9144d782e148332009a835b99c43382467`
defines group match bits, key ID, WLAN index, G4/G1 layout and error status in
`include/nic/nic_rx.h` (SHA-256 `0645985217a887e6c2d367955fa656b45f716a6aeeee13a29a2b462eb8dea5cb`).
`mgmt/privacy.c` (SHA-256 `cd644912f4351756de2e145784fd611e20165a1f75e1299c18e02f1565b8407d`)
keeps distinct pairwise/group table assignments and checks group key ID.
`nic/que_mgt.c` (SHA-256 `03fd22064c8bd56de4a895fde769264679c89cc05645be9e6395ecd545176a96`)
requires G4 for translated frames and separately attributes the station/BSS.
The current encoder declares PTK index 1 and broadcast index 2; prior measured
broadcast index changes and the existing `data-rx.h` retain their scope. None
of these facts supplies a key-incarnation tag or safe slot-reuse contract.

## Hypothesis and unique observation

Hypothesis: the same mask that supplied mandatory PN metadata for C10 PTK
frames also supplies G1 for the source-supported initial GTK receive shape.
Observe metadata from existing complete acquisitions in the admitted ACTIVE,
authorized initial-key window, under the MAC mutex. No new HIF acquisition,
firmware command, address access, packet acceptance or userspace API.

Use the existing actual `mt6797_data_rx` decoder only as a metadata classifier.
Count reported group frames, source-supported group shapes, shapes matching the
current installed group key ID with TID 0 and an Ethernet-II body excluding
EAPOL, and those with/without G1. The numeric `eligible` counter means only
this observation policy, never authentication or packet admission. Retain a
16-mask bitmap for that final class. No PN value, key material, address or body
is logged. The old decoder's reconstruction stays local and is never queued.
Its success does not authenticate a GTK frame or advance any replay state.
Only the existing strict PTK checker may deliver; GTK remains withheld.

One default-off option depends on the mask-control comparison. Add only counters,
a small observer call at the existing ready checked-RX site, and one terminal
numeric line. Option-off source preprocessing must match C10 byte-for-byte.
Do not reuse counters labeled as delivered data for these dropped observations.
The existing all-RX512/1MiB, checked64, wall10s-or-lower, channel/frame/100ms
command deadlines, cleanup and fatal poison remain unchanged.

## Decision branches, before code or boot

1. Matching initial GTK shapes carry G1: preserve count/mask evidence; review a
   separate seeded GTK checker and key attribution before enabling delivery.
   Availability is not firmware MIC enforcement or key-retirement proof.
2. Matching GTK shapes lack G1: retain mandatory rejection. Document that
   precise group-PN capability gap before selecting another crypto route.
3. Reported group traffic exists but no matching shape/key: use those distinct
   counts to locate the unsupported contract; do not relabel it as missing PN.
4. No reported group exposure: absence is inconclusive; no unchanged retry or
   arbitrary group traffic generator is admitted by this result.
5. Earlier/different transport or network failure: record independently; no
   timeout extension, RX-length exception, credit refund or global-monitor fallback.

## Validation and admission

One logical proposal with focused actual-source fixtures. Cover all 16 group
masks and padding, exact allocation/truncation bounds, status/identity/index/key/
TID mismatches, no PN reads and no input/context/key/PN/queue mutation. Reuse the
existing translated fixtures. Verify observer placement, single terminal report,
option-off parity and unchanged RX/crypto/key/lifetime source. Synthetic tests
establish host observation behavior, not firmware integrity.

Select a named profile preserving canonical patch order, all C10 fragments and
one flag. Audit every other profile unchanged. Commit/push reviewed inputs,
run Linux-only checks and the standard Buildbox kernel/package workflow from a
clean checkout, validate composition/tool bindings and guarded boot2/readback.
Then one custodian, fresh identity, one admitted capture/session, original
preservation/quiescence/regression/recovery gates and owner physical selection.
No device action is selected before those gates. No C10 unchanged repetition,
GTK delivery, rekey, key-slot reuse, re-arm or maintained support is implemented
by this diagnostic. The full ordinary-crypto/reconnect/ten-minute goal remains.

## Authored source and local validation

[Proposal 0201](../../patches/proposals/0201-wifi-mt6797-observe-initial-GTK-PN-metadata.patch),
SHA-256 `c14244306eeaab5b6749fb68dc039b312c920f5202d1a619f40d018d6dac4193`,
changes only `Kconfig` and `mac.c`. Bounded driver snapshot
`70f1b9a3484139b35dfdb894cbbcb56f21b33218` is an authoring identity, not a Linux
revision. It adds six counters and the existing report site's single numeric
line. The observer runs only after the unchanged ready/authorized ACTIVE and
checked-delivery-cap gate, before the unchanged PTK allocation/check path.

The [actual-source runner](tests/run-group-pn-observe-test.py) passes locally
with ASan/UBSan: 2716 exact-allocation observations, all masks/padding and
truncations, field/key/TID/status/address/shape refusals, Ethernet-II/EAPOL and
empty-body policy, single-report/512-acquisition behavior. Poisoning the actual
G1 allocation proves no PN read; full input/MAC state comparison permits only
the six observation counters to change. The real unchanged PTK decision tests
also pass strict seeded-PN rejection. Reversing 0201 restores every C10 driver
file byte-for-byte. Complete option-off MAC preprocessing matches C10 for both
normal and diagnostic configurations. HIF, RX, crypto, key and lifecycle inputs
are unchanged. These tests establish host behavior only.

The new `mt6797-a53-wifi-ccmp-group-pn-observe` profile selects the 696-patch
ordered series and all 27 C10 fragments plus one option fragment. All 33 existing
profile definitions remain identical. Linux validation, strict checkpatch,
clean pushed Buildbox build/package and actual candidate/tool/device gates are
still pending at this source checkpoint. No GTK delivery or device test yet.

Linux actual-source ASan/UBSan passed on the first pushed input. Strict checkpatch
then found the new Kconfig help paragraph one line short and stopped before any
kernel build. The help paragraph is now complete; observer MAC code is unchanged.
The failed pre-build log remains retained, and corrected-input validation is pending.
