# First finite monitor-assisted stable PTK — proposal 0191

**Source/test review record; no build or hardware result.** ROOT authorized
authoring, the normal DHCP branch, and subsequently the exact source/profile
below for selection/build. Frozen ND6 and exact [0190 helper](CCMP_RX_CONTRACT_REVIEW.md)
are the foundation; no historical artifacts, series or runtime evidence changed.

- [0191 patch](../../patches/proposals/0191-wifi-mt6797-gate-one-monitor-assisted-stable-ccmp-epoch.patch)
  changes only driver `Kconfig` and `mac.c`.
- Profile proposal (fragment retired 2026-10-24, in the git history)
  originally archived unselected, uses native arm0/CCMP arm1
  and requires the existing ND6 profile's ordered foundation plus exact0190/0191.
  The later approved selection is recorded below; the original fragment's
  proposal/unselected comments describe its pre-review origin.
- Source commit: `9b7bad2ba02513b4f003fa1162e00ea94a502d8d`, parent
  `7e89fa209b4fd9c1ad7f9efcae8210a4d633e11c`.
- Patch SHA256: `0b855aecb02c3fada1a263ad8e7c811b1850a8f56a0255fb37d7532a08251fe4`.
- MAC SHA256: `94319809962acf26f51715225962d3c4b684f3bfe81886d4d25084fa4f7b3ff2`.

## Contract and deliberate limits

The new read-only/default-off `ccmp_stable_epoch` arm rejects simultaneous native
arming. It reuses the admitted monitor enable/disable commands, shared command
sequence/page/credit ledger, prospective all-RX512/1MiB limits, accepted-frame64
limit, wall10s or lower grant, TX fence, bounded owed-TX drain and existing cleanup.
`ccmp_queued` is separately named accepted/queued Ethernet evidence, not native
ciphertext, proven core delivery or hardware replay enforcement. No extra packet
sample, histogram, HIF change or speculative firmware command is added.

Normal non-monitor PN production remains unproved: [Runtime32](../2026-10-07-mt6797-wifi-phase-b-join/RUNTIME_32_RESULT.md)
delivered60 frames with Group4 only, whereas ND6's translated sample had Group1
under monitor. The earlier normal-mode premise is not used here. Monitor can
consume its512-frame window in roughly two seconds, and the unresolved post-CLOSED
HIF80/32 fault remains a risk; this is not a maintained monitor mode or repair.

Host state comes from the source-owned initial station/key setup, never learned
from packet metadata. Logical BSS0's peer/key commands use the existing station
WLAN1 mapping; the expected post-activation RXD tag1 is a measured filter, not
BSS0 arithmetic or proof of firmware ownership. Exact0190 validates the actual
translated descriptor, PTK-only context, current peer/own addresses, complete
G4/G1 and strict seeded PN increase under the MAC mutex. Allocate before PN commit.
No ordinary legacy fallback exists in the new mode; group/GTK RX is withheld.

Initial PTK activation requires its existing submit/returned credit and the first
owned0x24 event before GTK submission. This is **provisional window attribution**,
not typed, command-sequenced or key-generation certification. Initial GTK install
and the existing group-credit/data-open path remain allowed; a later group event
may be a delayed repeat and is not certified GTK completion. No rekey/reinstall,
slot replacement, host re-arm or reuse is supported.

The actual PTK pubsta is retained under RCU and must be that same core-authorized
station. Core decap callback eligibility is respected; no fast_rx/vif flags are
manually forced. Scan/control/data use one serialized, BH-disabled
`ieee80211_rx_napi` family with RCU across handoff, outside the MAC lock. Queue-time
and handoff-time eligibility both apply. Standard CCMP decap flags describe the
provisional decryption contract and the driver's PN validation, not firmware proof.

Firmware-only ordinary TX requires the actual current PTK cookie/index and the
existing checked non-QoS CCMP ToDS shape. Ethernet broadcast still uses AP RA/PTK.
No host IV/MIC generation or double encryption is introduced. Unsupported shapes
and wrong/stale cookies are dropped without keyconf dereference. Existing TX
status and returned-credit attribution is reused, not upgraded to over-air ACK.

Disable invalidates host RX/TX/decap/station/key cookies, discards ordinary queued
work, synchronizes previous receive/status batches and terminates join work before
callback completion. It never permits re-arm. Healthy evidence says only
`removal_command_credit`; poisoned/deadline paths can return0 for **LOCAL DISABLE**
with failstop/recovery required. Neither is hardware-key deletion proof. No extra
removal retry, ACK read or new firmware read manufactures retirement.

## Focused host checks

[Runner](tests/run-ccmp-monitor-test.py) reuses existing native fixture extractors,
translated/CCMP and native-layout fixtures; [C fixture](tests/ccmp-monitor-state-test.c)
extracts actual callbacks, dispatch, pre-read, TX, monitor step and the unchanged
parent monitor step. It uses ASan/UBSan and bounded pthread barriers, not a device.

```sh
python3 experiments/2026-10-13-mt6797-wifi-native-delivery-probe/tests/run-ccmp-monitor-test.py <exact-0190-parent-tree> <0191-child-tree>
```

PASS coverage includes initial activation/seed, missing/wrong/withdrawn event,
submit failure, authorized pubsta identity, decap withdrawal, actual RX API/BH/RCU
mock assertions, strict PN rejection, G1 absence/no fallback, allocation-before-PN,
current PTK vs GTK/dangling TX cookies, software-IV shape rejection, local-disable
poison evidence, queue discard and an already-started RX/withdrawal barrier.

Actual parent/child native engine traces compare the unchanged encoder's call
interface, enable/disable arguments, sequence, shared pages/pending-credit,
state/counters/deadlines. CCMP-only arm tests63 versus64 with native counter0, allRX,
prospective bytes, wall/lower deadline, owed-TX retirement/fence, ambiguity and
no-radio tail. Original-native dispatch verifies preserved MPDU flags/counters;
CONFIG-block exclusion additionally proves existing native source unchanged.
The existing native decision, loop/control-order and actual-HIF mocked fixtures
also passed before final style cleanup; their implementation inputs were unchanged.

All results are **host simulations**, not live kernel RCU/core correctness,
firmware MIC/replay negatives, WLAN delivery, DHCP or hardware support. Strict
checkpatch has exactly one missing truthful DCO error, zero warnings/checks. The
internal synthetic non-certifying archive intentionally has no fabricated signoff
and is not upstream-submission-ready. Source and test licenses are GPL-2.0-only.

## Next boundary

ROOT approved exact `9b7bad2`/patch0b855aec/MAC94319809/profile8lines. Select a separate
profile with canonical-order ND6+0190+0191 inputs, commit/push clean inputs and build on Buildbox-1 with32 jobs,
modulesfalse and ordinary provenance. Prepare compositor/runtime/installer/real
receipt bindings with that admitted build; composition needs no new assembly
permission. Private parent/RAM remain outside Git; ROOT alone operates hardware.

First runtime is **normal DHCP only**: helpers ready before ACTIVE, a real lease,
then WLAN-bound unicast ping/boot-mode SSH within the available finite window.
No static address fallback, fabricated lease/READY, or USB-as-WLAN claim. Short
window/failure is a truthful partial result. Full normal producer, GTK RX,
retirement/rekey/reuse, IRQ-DMA reliability and clean-profile ten-minute SSH remain
unresolved. Selection below supplies no validated package, compositor or device
receipt; none is claimed by this source-only record.

## Approved selection audit

`mt6797-a53-wifi-ccmp-stable-monitor` selects
`patches/series-a53-wifi-ccmp-stable-monitor`: exactly the frozen ND6 ordered684
patches followed by unchanged0190 and approved0191, total686. The manifest adds
only this profile, cloning ND6's complete base/ordered25 fragments and appending
the reviewed CCMP fragment. No DT patch or other source tuple changes.

Against published `904e703c`, all existing manifest entries and all47 tracked
configuration/DT paths remain identical. The checkout contains **17 existing
named explicit series files**, all byte-identical (18 existing series files if
the canonical file is counted). These measured counts replace an assumed18
explicit-file count; no existing named series is altered. Canonical series only
appends0190/0191. Four historical implicit consumers (`full`, `handoff`, `usbdiag`,
`usbdiag-clkignore`) consequently inherit those additions; that is not evidence
they apply cleanly or are admitted new build foundations. Only the exact ND6-based
new profile is authorized for this build.

Selected series SHA256:
`7b9066cee939342b84b43baf0db9cab7d29b8d15fa80fda5600fe7f95a9a1663`.
Resolved configuration, compiler outputs and package identities are pending the
ordinary build/validation; requested fragments alone are not a resolved-config
receipt. ROOT independently reviewed and approved the one-comment clarification
from `da480f1` to `9b7bad2` (`set_key` versus `DISABLE_KEY` returns), with no executable
change. Selection keeps published archive45a3ec43's exact patch0b855aec and the
more precise comment; all source/build/compositor pins must use that final source.
