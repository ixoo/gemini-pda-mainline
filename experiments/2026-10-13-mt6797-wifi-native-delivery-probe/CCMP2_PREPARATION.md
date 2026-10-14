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

ROOT actually composed with toolingd3da89da/compositor4dc1290f, verified private
C32, package0304 and all6 output identities/padding/config/private64/board gates.
The [REAL receipt](results/ccmp-stable-monitor-candidate-2.json) is SHA256
`ba8078a0be1673a81a8159b5166769aeb226785eb0ee29ba682c3db3e50dc93d`;
[runtime identity copy](runtime-ccmp2/results/candidate.json) is byte-identical.
No private image/RAM/key was transferred to the agent. Raw boot12670976B:
`e7e7e433bdc6f5ace8cede9236c6fe48fbfd39d9727a33953457c6d5a86e0ec4`;
full16777216B `7b2b881b74b958502cd9c148f10b23c58949ea221f75281c9d97721d8b3bd60e`.
RAM0b89/board25ab/config483 are identical to CCMP1; only the kernel changes relative
to CCMP1. Expected predecessor full418 from CCMP1 is freshly verified by ROOT's
live guard, not taken as a current Gemian identity. Frozen CCMP1 stays untouched.

## Fresh receipt-bound installation and runtime handoff

[Prepare](prepare-ccmp2.py), [installer](install-ccmp2.py),
[capture](laptop-capture-ccmp2.py) and [session](laptop-session-ccmp2.py) bind the
real receipt/program/source/predecessor and fresh capture-ccmp2/session-ccmp2/
runtime-ccmp2 roots. Existing private64/source/calibration/supplicant/CLI/credential,
device guard, seal/regression/one-recovery and started-child quiescence rules
remain. Shared reviewed `join-ccmp.sh`, ACTIVE-only Wi-Fi helper and corrected
full leaf/export/process classifier remain byte-identical; the private binder
must wrap that exact leaf at mode0600/one link. No static-IP fallback.

ROOT sets its existing private paths and fresh verified Gemian boot identity:

```sh
P=experiments/2026-10-13-mt6797-wifi-native-delivery-probe
export GEMINI_PRIVATE_REPO=<existing-private-checkout>
export GEMINI_RUNTIME_ROOT=<private-runtime-root>
export GEMINI_JOIN_SCRIPT=<mode-0600-private-CCMP-binder>
CANDIDATE=<private-path>/candidate-e7e7e433bdc6f5ace8cede9236c6fe48fbfd39d9727a33953457c6d5a86e0ec4
python3 "$P/prepare-ccmp2.py"
python3 "$P/install-ccmp2.py" validate --candidate "$CANDIDATE" --previous-gemian-boot "$PREVIOUS_GEMIAN_BOOT"
python3 "$P/install-ccmp2.py" prepare --candidate "$CANDIDATE" --previous-gemian-boot "$PREVIOUS_GEMIAN_BOOT" --output "$INSTALL_OUTPUT"
```

ROOT performs actual private64/full-host preflights, reviews/executes the derived
guarded shell with fresh OS/boot/GPT/root/power/predecessor, requires full readback
7b2b881b and clean shutdown, then owner physically selects boot2. Do not create a
fresh backup merely per write, invent a deployment summary or substitute reboot.
Retain the actual deployment-summary under
`$GEMINI_RUNTIME_ROOT/ccmp-stable-monitor/session-ccmp2/`. After physical boot,
ROOT authenticates the fresh expected release/candidate and supplies that boot:

```sh
export GEMINI_WIFI_SSH_KEYS=<existing-private-key-root>
export GEMINI_WIFI_SSH_BOOT=<fresh-authenticated-CCMP2-boot-UUID>
python3 "$P/laptop-capture-ccmp2.py" --candidate "$CANDIDATE" --execute
python3 "$P/laptop-session-ccmp2.py" --candidate "$CANDIDATE" --execute
```

Exactly one fresh capture/session; no CCMP1 repeat or namespace reuse. Genuine
not-ready Phase A now uses the underlying no-leaf/A53 route: no never-started
helper/C2 export prerequisites, no safe/quiescence fabrication. Started or
uncertain children retain/refuse bypass of their real guards. Original ordinary
recovery requires complete **available** evidence; logger deadline-limited logs
must still be labelled incomplete with false regression/compatibility, not fake
full-log success or an emergency RAM-loss premise.

## Scalar hypothesis, unique evidence and decision branches

The sole source-fix hypothesis is that the explicit supported CCMP suite clears
the exact core registration predicate (`main.c:1076`) while both hardware flags,
key/TX/fallback guards and finite monitor/PTK behavior stay unchanged. Unique
scalar evidence is this candidate's registration/regulatory status and wiphy/
TC4 startup result. No added observer, histogram, descriptor sample or firmware
command is authorized by this fix; existing protocol evidence suffices.

- Registration still refuses: preserve exact status/boot/trace, withhold scan,
  use corrected no-scan seal/available-preservation/one-reviewed-return path;
  no unchanged retry, cipher/fallback relaxation or PHY success claim.
- Startup ready but no CCMP queue/lease: preserve normal finite monitor/key/
  credit/queue and leaf evidence; partial, not authentication/support. Initial
  GTK RX stays withheld, so broadcast DHCP/ARP responses can block completion.
- Queue/SSH but missing ping3/3, leaf host-ack consumption or complete sameboot/
  cycle export/process proof: retain separately named partial fields, no full
  provisional pass. Missing/unexported/truncated evidence remains absent.
- All admitted DHCP/lease/listener/ping/SSH/leaf/healthy-cleanup and sealed boot/
  regression/recovery evidence: first finite provisional compatibility only.
- HIF poison/deadline/cleanup ambiguity: no retry or claimed hardware key
  deletion; preserve unique available evidence and use the unchanged finite
  stop/quiescence/seal/identity/tool-bound one-recovery rules.

Focused actual binding/refusal/namespace/private64-requirement/helper ownership
tests and actual future failure-main tests are host-only; no worker device or
private64 execution is claimed. ROOT's real preflights remain required. Full
normal producer/GTK/rekey/reuse/IRQ-DMA/clean-profile ten-minute support is unproved.
