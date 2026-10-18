# Fixed RX format prototype — UNBUILT, no runtime admission

[Predeclared hypothesis/branches](RX_FORMAT_OWNERSHIP_SUCCESSOR.md) follow the
[D2 enable-time refusal](SSH_D2_RESULT.md). [Proposal 0202](../../patches/proposals/0202-wifi-mt6797-compare-firmware-lifetime-fixed-RX-format.patch)
is one logical ownership comparison on C10, excluding C11's observer. It is
not a proven firmware fix. No candidate or kernel build; the owner's hold remains.

## Implementation

The CONSYS bootstrap calls the new preparation operation after its initial
TC4 accounting pair and before scan-ready, within the existing RTNL interval.
The MAC also holds its mutex, rejects a second attempt or any started/vif/scan
state, and never publishes scan-ready after failure. The initial pair is not
assumed idle: D2 retained free 14, pending CPU 0 and pending FFA 12.

The HIF binds one attempt to its instance and requires the established normal
accounting owner. It first reconciles prior configuration debt to idle, then
submits exactly the existing eight-byte CID 0xc0/target/value-7 payload through
a narrowly validated normal configuration kind. It retires the one-page debit
using the existing credit acquisition/cadence. Both stages share one absolute
100 ms deadline. No new register, counter reset, speculative credit or retry.
Transport/deadline/accounting faults poison; admission refusals publish no
readiness. This owner performs no further I/O after failure.
Credit still proves command-buffer retirement, not firmware application.

Fixed-mode data-window transitions are local IDLE/ACTIVE/CLOSED. Both-key/data
and quiescence gates, sample clock, ceilings and owed-TX fence remain. Unexpected
pending states or actions fail closed before the worker can select another TX
or RX. The join-command validator rejects all mask writes in this mode; only the
initialization owner may configure it. No station arm/close/disconnect changes
the descriptor format. Configuration remains owned by the HIF/firmware instance;
local CLOSED does not certify firmware queue/key retirement or configuration release.

RX equality/complete transfer/poison/no-copy, channel/data deadlines, EAPOL,
strict PTK PN/status checks and key ownership code are unchanged. Ordinary legacy
data is still withheld by the existing CCMP dispatch before ACTIVE. GTK delivery,
rekey, reuse and reconnect stay disabled. Global configuration ownership and
station cleanup must be reported separately in any later admitted trial.

## Inputs and current checks

The bounded source commit in the patch header is an integration fixture, not a
full Linux revision. Selected profile
`mt6797-a53-wifi-ccmp-fixed-rx-format` inherits C10 and adds only 0202 and
`CONFIG_MT6797_CCMP_FIXED_RX_FORMAT=y`. The separately approved 60-second
[budget patch](../../patches/proposals/0203-wifi-mt6797-bound-first-fixed-format-window-to-60s.patch)
is selected after 0202; it changes only the exact request and observation
admission described in the [session plan](SESSION_0202_PLAN.md). Series preserve canonical order and skip
the unrelated C11 observer. All 34 prior manifest profile definitions are unchanged.
Patch applicability passed on retained C10 and the canonical C11 source successor.

The [actual-source fixture](tests/run-fixed-format-test.py) and
[C cases](tests/fixed-format-test.c) passed locally with ASan/UBSan:

- 1482 focused cases: exact wire/payload, one-page accounting, split credits,
  every injected I/O/deadline failure in old-debt and mask phases, the real D2
  initial credit state, shared-budget exhaustion, no readiness on failure,
  duplicate/invalid owner refusal and no second I/O after poison.
- Local window/key gates, all sample ceilings, CLOSED non-rearm and owed-TX
  cleanup fencing; no sequence/debt mutation or runtime mode I/O.
- Mandatory rejection of runtime join-owned mask writes and initialization
  value 0; malformed/changed addresses, values and lengths remain rejected.
- Option-off HIF/MAC preprocessing is byte-identical to C10; original control
  cases pass. Actual runtime/selected RX I/O/publication tables remain equal
  on both ports, including all six observed length mismatches and faults.

These establish host behavior only. A missing mutex stub and a whitespace-only
option-off comparison failure were corrected in fixture/prototype preparation;
logs are retained. The historical exact-C10 runner correctly refused the extra
prototype changes and was not weakened. Linux host fixtures passed from clean
pushed input `8fa3951a`, including all 1,482 cases, window boundaries and the
combined-source scan/group fixture. Strict patch review found alignment and
description-wrapping issues; these were corrected and local fixtures reran.
The archives intentionally lack DCO certification; do not label checkpatch green.
Final strict review of the formatting correction is pending from pushed inputs. No kernel compilation, DT/schema check,
firmware enforcement, healthy resource lifetime or Wi-Fi runtime success is claimed.

## Remaining boundary

Complete Linux host validation, patch/profile review and the repository checks
before requesting release of the owner's explicit new-candidate build hold.
Only a later authorized standard Buildbox build/package and reviewed real
composition/install can lead to a physical boot2 handoff. No device run or
unchanged D2 retry is admitted by this prototype. Full Wi-Fi acceptance remains
incomplete, including the separate intermittent SSH failure and sustained operation.

## Approved first sustained-window preparation

The owner approved preparation of the narrowly bounded 60-second change while
keeping kernel builds on hold. Separate 0203 permits exactly 65,000 ms in addition
to the previous short channel requests, requests that interval only in the fixed
format profile, and refuses data opening with `-ERANGE` before changing state
unless at least 62,500 ms remains on the actual granted ownership. A bounded
software-only refusal log reports remaining/required time. No presumed firmware
grant, renewal or changed transport timeout. Data duration remains 60,000 ms,
its observation wall becomes 60,000 ms, and the 2,500 ms tail / 5,000 ms teardown
margin and every resource/PN/key limit remain unchanged.

The [actual-source window fixture](tests/run-fixed-window-test.py) passes locally
with ASan/UBSan. It exhausts request/grant intervals 0..70,000 ms, verifies
62500 ms +/-1 ns opening boundaries, no state publication on rejection, a full
60-second data deadline and unchanged cleanup/resource stops. Option-off encoder,
request, opening function and budget preprocessing match the parent exactly.
An initial option-off textual comparison exposed redundant parentheses; those
were removed without weakening the check. Linux host validation passed from
clean pushed input `8fa3951a`; the updated source fixtures also passed locally
after the strict-review formatting correction.
The format fixture still passes all 1,482 cases after refreshing the existing
software-ledger error report. These are partial-source fixtures, not kernels.
Runtime A/B binding and full-window authenticated SSH operation remain pending;
no candidate may be built under the hold. Subsequent 120/600-second limits are
not included in the owner's first-stage approval.
