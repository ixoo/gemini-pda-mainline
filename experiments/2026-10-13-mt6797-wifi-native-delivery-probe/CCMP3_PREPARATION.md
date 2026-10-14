# CCMP3 — strict management RX repair, fresh runtime only

ROOT materially reviewed and approved the exact [0193 patch](../../patches/proposals/0193-wifi-mt6797-retain-strict-management-rx-in-ccmp-mode.patch),
SHA256 `0297b9ee121ad5bff43fcca7f44ad0435cb588c89cc7032479da4d3e22a7d075`;
source `e1ecfcd967a246ad72627b9fd2d92caaa31c59a0`, parent0fcdc1;
MAC `261a159513497d6e541831f1db442ddbd4974f781173fac4d3c718d095cc6139`.
The exact13-addition/2-deletion body and unchanged strict management decoder/
state/queue/negative tests were reviewed. No additional fix or observer admitted.
See [CCMP2 result and source diagnosis](CCMP2_RESULT.md) for the concrete need
and observation/inference distinction; its completed tooling remains frozen.

Independent bounded source advisory corroborates the exact routing patch.
Repeated AUTH preparation stores-EOPNOTSUPP, subsequently reported by branch1;
a duplicate AUTH response within an allowed window returns-EPROTO. The inferred
retry is mac80211's internal timer, not a second observed supplicant request.
The drop bypassed strict management, not every RX class: beacon/EAPOL paths were
retained. The repair handles current-state-permitted management even when keys
exist, not exclusively pre-key. Disarmed source/semantics are unchanged, with no
claim of identical compiled binaries. Raw response arrival and callback entry
remain unobserved. Supplemental sanitized scalar counts show one userspace
Authenticate request, zero Associate/response phrases; they do not count internal
kernel retries. The exact approved source/patch identities remain unchanged.

New profile `mt6797-a53-wifi-ccmp-management-rx` selects
`patches/series-a53-wifi-ccmp-management-rx`: CCMP2's687 ordered patches plus0193,
exact688. Series SHA256
`71661717247d88a93d18c7a1981eb0838f286c902f3f2c8e9cfe1612eacd0baf`.
All26 ordered fragments and release are identical to CCMP2. Against2e8ad9aa,
all25 existing profiles,19 existing named series and48 config/DT paths are
byte/structure-identical. Canonical appends0193; four historical implicit
consumers full/handoff/usbdiag/usbdiag-clkignore inherit it and are **not** new
build foundations. Named CCMP1/CCMP2 series, receipts and runtime remain intact.

Actual parent/child dispatch and callback ASan/UBSan tests pass, exact delta
reversal/all other driver files equal, apply-check at immutable0f passes. Strict
checkpatch has only the missing truthful DCO error (zero warnings/checks): internal
synthetic non-certifying archive, not upstream-ready. Mandatory repository gates
are required before publication; kernel/DT build and hardware results are not
claimed by these host checks.

Ordinary BB1 build only from clean pushed intended inputs,32jobs/modulesfalse,
experiment selector unset. Actual preflight:48-CPU cgroup quota,128GiB memory
limit, about6GiB current use,420GiB workspace free, managed lock available, no
heavy build processes, all56 retained job records validated. Doctor verifies
toolchain/repository access; recheck live capacity/lock before submission.

After validated package/fetch, proactively pin a fresh compositor to the real
package using the unchanged private C32/RAM/DT/config/container gates. ROOT owns
the private composition and returns its real receipt; do not copy private image/
RAM/key or use placeholder identities. Fresh capture-ccmp3/session-ccmp3/
runtime-ccmp3 receipt/install/private-binder identities then bind that receipt.
Expected installed predecessor is CCMP2 full7b2b, freshly verified by ROOT's
live guard. No assembly permission turn, binding-only rebuild or worker device
access. Optional source advisory does not hold the approved exact-body build.

Hypothesis: strict existing AUTH/ASSOC response routing can progress beyond the
pre-association starvation while keeping ordinary legacy data withheld. Unique
evidence is existing management-response/status/association chronology on the
new candidate; no new telemetry or radio effect. Absent AUTH response remains
negative, not retry authorization; malformed/unknown/data still withheld.
Ready -> one finite initial PTK/normal DHCP real lease/ping3/ACTIVE-bound SSH with
full attributable leaf/process/cycle/ACK/healthy-cleanup/seal/regression/return
proof. Refused startup -> reviewed no-scan preservation/one-return route.
Partial queue/SSH or missing proof stays partial; no GTK RX, rekey/reuse, PN/HIF
relaxation, added budget or key-deletion claim. Full owner Wi-Fi goal remains unmet.

## Validated package and real-pin composition handoff

Kernel input `47a23e6aea65be56246ca2b0fce023cf17028698` completed ordinary BB1
build/validation at2026-10-14T21:16:40Z. Normal fetch passed exact inventory and
clean/profile/modules provenance. Package inventory:
`f811ca7f261927cb5e953abbddeb474915bf5fa88607e6496c01a7eff9a02316`;
Image.gz `5268f9f4e84b0715420e320d0a49336418170ee7a48e03d75b97162453604326`.
Resolved config `483e0165368ce521f7f6e082e5acbc612c26badab7cacdc1e1cd60166f15c350`
is byte-identical to CCMP2. Patchset
`e0ee3ecfc597639c4c4e00dd58eba5bfa17cb4b33fe413710f6f7e989beff5b3`,
config-input `147330a1ffa587495babe41f72979778806847544c781e5cb93bbc8ba645ead1`.
All actual built driver files equal approved sourcee1ecfcd9/MAC261a1595.
Compilation/validation do not prove management response arrival or Wi-Fi support.

[CCMP3 compositor](build-ccmp-candidate-3.py) is CCMP2's reviewed compositor with
only real package/input/profile/series/source/patch pins changed. C32 parent,
private64 RAM inventory/release substitution, config oracle, DT/PSCI/clock,
container/header/padding and disk gates remain unchanged. No private image/RAM
was copied to the worker. ROOT executes:

```sh
python3 experiments/2026-10-13-mt6797-wifi-native-delivery-probe/build-ccmp-candidate-3.py --kernel-package <validated-f811-package> --parent <verified-private-C32> --output <fresh-private-CCMP3-output>
```

ROOT verifies the six-file inventory and returns the actual receipt bytes/raw/
full identities for fresh CCMP3 installer/prepare/capture/session/runtime binding.
No placeholder receipt, device action or source/kernel rebuild.

[Fresh host](passive-host-ccmp3.py) uses capture-ccmp3/session-ccmp3/runtime-ccmp3
through all underlying namespaces and the unchanged genuine-no-scan function.
[Actual failure-main fixture](tests/ccmp3-no-scan-host-test.py) passes never-started
helper failure, keeps failed compatibility false, and refuses started-child
bypass. Private executor is mocked; final real-receipt wiring remains pending.
[Composition oracle](tests/ccmp3-composition-test.py) reuses exact C32 config/
negative gates. Optional [actual management fixture](tests/ccmp-management-path-test.py)
also compares whole state on decoder-false and old-mode/new-goto queued content/
status/state/strict parsed offset from identical synthetic input; ASan/UBSan pass.
These tooling-only tests do not change approved0193 or require a binding rebuild.
