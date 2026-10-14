# CCMP2 — explicit cipher admission correction, fresh runtime only

ROOT approved exact three-addition successor source, parent9b7bad2, MAC SHA256
`a140b36a170a8608f48ca1dbb014b98181e337a2df58c768c37239b5f3ada746`:
static CCMP-only suite array and pointer/count in the new-mode branch. Source
commit `0fcdc1ee65d588a2fc9cdbfc61cd39761cb71e01`; [0192 patch](../../patches/proposals/0192-wifi-mt6797-declare-ccmp-suite-for-stable-monitor-registration.patch)
SHA256 `b9c1c1d99ebc43856c6098dce3e07e5ca8e38fe390d40a3ec1369a9b284da470`.
The observed need is [CCMP1's core registration refusal](CCMP1_RESULT.md), not a
parser/crypto result. No protocol/API executable change beyond those3 additions.

Keep SW_CRYPTO_CONTROL and the actual key/TX/no-fallback gates; no broad assertion
that the flag alone prevents software crypto in every path. Initial PTK and GTK
install still use the same CCMP suite; GTK RX/rekey/reuse remain excluded. Core
decap/pubsta/BH/RCU/PN, HIF/no-copy/credits, finite monitor commands/budgets and
cleanup contracts are unchanged. No DT or requested configuration changes.

## Isolated selected inputs

New profile `mt6797-a53-wifi-ccmp-cipher-admission` selects
`patches/series-a53-wifi-ccmp-cipher-admission`: exact ND6 ordered684 plus unchanged
0190/final0191 plus0192 =687. Ordered26 fragments are identical to CCMP1, including
native arm0/CCMP arm1 and clock/PSCI constraints. Kernel release remains
`7.1.3-gemini-a53-wifi-ccmp-stable-monitor`; candidate/receipt/input/boot identities
and fresh CCMP2 roots, not a cosmetic release change, distinguish this runtime.

Against frozen ca7ee96b, all18 existing named explicit series files (historical17
plus CCMP1), all24 manifest profile entries and all48 configuration/DT paths are
unchanged. Canonical only appends0192, affecting the same four historical implicit
consumers full/handoff/usbdiag/usbdiag-clkignore; they are not build foundations.
New series SHA256 `7e6455e7e2532ecd67b7b88a001e068de9aebf3979e116c1f86973d373eed497`.
Old CCMP1 input83/source9b/toolsca7/receipt725/raw94a/full418 and consumed claims
remain reproducible and immutable. Do not rebuild or repeat CCMP1.

[Cipher-admission host fixture](tests/ccmp-cipher-admission-test.py) extracts exact
7.1.3 `ieee80211_init_cipher_suites` and actual parent/fixed registration blocks:
parent-EINVAL reproduced, static CCMP-only list admitted, both hardware flags
unchanged, normal-mode defaults and FIPS refusal preserved. ASan/UBSan PASS.
Strict checkpatch reports only the intentionally missing truthful DCO error,
zero warnings/checks; internal synthetic non-certifying archive, not submission-ready.

## Future no-scan correction and next boundary

[No-scan function](ccmp-no-scan.py) uses the existing underlying WIPHY/private/A53
preparation for a genuinely never-started helper, rather than installing C2 leaf
export prerequisites. It neither starts a helper nor fabricates safe/quiescent
state; started/uncertain child state refuses this shortcut, leaving the real
child-group guards unchanged. [Actual function host tests](tests/ccmp-no-scan-test.py)
cover that failure route and all started/proc/PGID/unknown-start refusals. Fresh
CCMP2 host binding must route its no-scan branch here; these isolated tests are
not a private64/device execution or a completed runtime-binding receipt.

The [fresh host binding](passive-host-ccmp2.py) now routes its actual failure main
through that function and rebinds every evidence namespace to capture-ccmp2/
session-ccmp2/runtime-ccmp2. [Actual host-main tests](tests/ccmp2-no-scan-host-test.py)
pass the enabled-but-never-started helper case without phantom exports, keep
recovered failed compatibility false and reject a real started-helper shortcut.
Only the underlying private preparation/executor is mocked; no device action.

Build only clean pushed intended inputs with ordinary BB1 provenance,32 jobs,
modulesfalse, experimentselectorunset, one heavy job after actual capacity/locks
checks. After validated real package pins, reuse the reviewed private C32/RAM
compositor constraints, bind only a REAL new receipt, and create fresh capture-
ccmp2/session-ccmp2/runtime-ccmp2 identities. No binding-only rebuild or separate
assembly permission turn. ROOT alone fetches/composes/validates/installs/readbacks/
shuts down, then owner physically selects boot2. No worker device access.

First test remains normal DHCP only, helpers before ACTIVE, real lease, WLAN-bound
ping3/3 and boot/mode-bound SSH within actual finite ACTIVE; full leaf/export/process
proof required, partial evidence retained honestly. Full normal producer/GTK/
rekey/reuse/IRQ-DMA/clean-profile ten-minute Wi-Fi remains incomplete. No new
descriptor sample/observer/radio effect, crypto/HIF relaxation or unreviewed retry.

## Validated real package and offline compositor

Clean pushed kernel input `5c5a7b10932b506c87e4ef624d018330bbf6490e` completed ordinary
BB1 build/validator at2026-10-14T11:01:56Z,32jobs/modulesfalse/experimentselectorunset.
The agent fetched the validated exact inventory/provenance; ROOT independently
verified the actual job and initiated its own fetch at that input. Package inventory:
`0304e09eaa435e8faa37113564f2f5c340ffac9d84a601772eefbea40cf26d7b`.
Image.gz SHA256 `451e46da9fe257eb42c135c85253484ea9fc96608655569a6ee2b145702d4ecf`;
resolved config `483e0165368ce521f7f6e082e5acbc612c26badab7cacdc1e1cd60166f15c350`
is byte-identical to CCMP1. Patchset digest:
`274b8e45e9d1c5eedb6edeef5ee12051edbe32d1391b9af86fd0839a651e2197`;
config-input digest `9fb8d1761ad9acf158e03da36a294af72f878e803ca83594c2fa1ffba117cec6`.
All actual built driver files equal exact approved source0fcdc1; MACa140b36a.
Compilation/fetch is not registration/runtime success.

[CCMP2 compositor](build-ccmp-candidate-2.py) reuses frozen CCMP1/C32 whole-parent/
64-member RAM/config/board/clock/PSCI/container/padding gates. Only real kernel/
profile/source/patchset/image/687-series pins differ; expected config/RAM release
gate change from C32 remains the same. [Focused oracle](tests/ccmp2-composition-test.py)
reuses the actual C32-hash/real resolved-config and mutation refusals, PASS.
ROOT may compose directly, no extra assembly permission or binding-only rebuild:

```sh
python3 experiments/2026-10-13-mt6797-wifi-native-delivery-probe/build-ccmp-candidate-2.py --kernel-package <validated-0304-package-at-input5c5> --parent <existing-private-C32-parent> --output <fresh-private-CCMP2-output>
```

Actual receipt/new raw/full boot2 hashes remain pending ROOT's real composition,
never placeholders. After that receipt, finalize only fresh CCMP2 prepare/capture/
session/installer identities; predecessor expected full418 from CCMP1, freshly
verified by ROOT's live guard. Frozen CCMP1 files/roots/claims stay untouched.
