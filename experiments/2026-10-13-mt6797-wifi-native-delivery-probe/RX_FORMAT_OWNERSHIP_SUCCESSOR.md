# Before implementation: fixed receive format for one firmware lifetime

Source-review proposal after [D2](SSH_D2_RESULT.md), not an implemented fix,
candidate build, runtime admission or permission to repeat D2. The owner's hold
on new candidate builds remains. No device operation occurred in this review.

## Questions resolved and limits

The [source-review scalars](results/d2-format-source-review.json) pin exact C10
headers, the existing fixture and the clean pushed Linux test input.

| Question | Established from source/tests | Limit |
| --- | --- | --- |
| Does metadata require weakening EAPOL parsing? | C10 `eapol-rx.h` already accounts for groups 1/2/3/4 before locating the frame. The existing actual-source fixture passed 48 layout/padding cases, all truncations and malformed metadata on Linux with ASan/UBSan. | Host decoder behavior only. Firmware may emit a different shape; it must still be refused. |
| Can WHCR bit 3 be selected as a fix from its name? | The public header names it, but the inspected HAL helpers and `nicSDIOInit` do not select it. Their visible writes concern enhanced-mode and length-count configuration. | This bounded public-code review is not whole-tree absence, AHB equivalence or proof of that bit's complete semantics. No bit-3 write is justified or proposed. |
| Is there a host initialization boundary before scan/station setup? | `mt6797_mac_register` holds RTNL/MAC serialization while loading record/configuration. `configured` becomes true only on success; `scan_ready` is set later. Start/add-interface/hw-scan gates require readiness. | No claim of a firmware RX queue fence, FIFO emptiness or no autonomous firmware traffic. |
| Does the current mask helper own initialization completion? | It submits through the shared join-command path, which requires NVRAM-submitted normal state and full TC4 availability. The current join worker owns its pending page/deadline. | Moving that call alone would lose the correct completion owner. Initialization must use the normal configuration owner and prove its credit accounting. |

Public comparison input is kernel/mediatek commit
`4f43e6b499c6d194030df8d2506485db9d5165bd`:
[HAL helpers](https://android.googlesource.com/kernel/mediatek/+/4f43e6b499c6d194030df8d2506485db9d5165bd/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic/hal.h),
[`nicSDIOInit`](https://android.googlesource.com/kernel/mediatek/+/4f43e6b499c6d194030df8d2506485db9d5165bd/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic.c).
No vendor implementation is copied into the proposed driver change.

The Linux test reused prepared C10 sources and existing clean, pushed tooling
`003519224de8ddc9d525971b3d3c9028b55aae05`. Its fixture is byte-identical to the
current repository fixture. No source tree or credentials were copied, no kernel
was compiled and no device accessor or other agent was started.

## One logical comparison

Hypothesis: keeping the descriptor metadata format stable while ordinary station
RX can be queued/acquired avoids the enable-time +48 and close-time -48 failures.
D2's pre-arm RX indication and TX-only quiescence motivate this comparison; they
do not prove the firmware producer mechanism or an already-correct replacement.

Propose one default-off child of C10, without the C11 observer: configure the same
fixed mask value 7 once during initial normal configuration, before `configured`
and `scan_ready` can admit scan/station activity. Keep that format for the HIF /
firmware instance. Do not toggle it at data-window arm/close or station teardown.
The mask becomes device configuration owned by the firmware/HIF lifetime, rather
than a station-scoped borrowed mode. This ownership change must be explicit;
merely suppressing the close write or stopping reads is not the proposal.

Use the existing normal configuration transaction for the exact eight-byte
CID 0xc0 payload, target/value unchanged. Add only the narrowly validated named
configuration kind needed by this default-off mode. Require full TC4 availability,
account its one page, return to the normal idle phase only on actual credit and
keep the 100 ms command limit. No scan-ready publication on failure, no retry,
credit forgiveness, new register, readback or claimed firmware acknowledgement.
Do not call the current join submitter and pretend another worker retires it.

Keep the bounded data-window state machine separate from this fixed hardware
configuration. It must still gate initial-PTK traffic on both keys/authorization,
start the same sample clock, enforce the same RX/frame/byte/grant/wall limits,
withhold GTK, preserve sticky plaintext withholding, end data, fence owed TX and
then permit the existing station cleanup. Its local state changes must not fake
an enable/disable firmware completion or charge/refund a nonexistent command.
No 0-to-7 or 7-to-0 format change is permitted while this firmware instance's
station RX is used. Firmware/HIF teardown owns eventual configuration release;
that is not proof of key/queued-frame retirement or permission to reuse slots.

This is a compatibility experiment toward an ordinary stable receive contract,
not maintained ownership or integrity certification. Command credit alone does
not prove an applied mask; required per-frame PN/status metadata must still be
checked, with mandatory rejection if missing. Do not claim queue emptiness or
normal hardware cleanup merely from avoiding a refused acquisition.

## Unique observation and decision branches

One future admitted boot would retain:

- Exactly one initialization mask submission/credit outcome before scan-ready;
  no mask command from data-window entry, close, disconnect or station cleanup.
- Existing complete-transfer/equality/poison/no-copy evidence across scan,
  EAPOL, initial PTK, window end, deauthentication and cleanup.
- Actual DHCP, three individual pings, fresh boot-bound SSH and its failure stage,
  including the already tested D2 host-output/local-state observations.
- Transport, network, station cleanup and global configuration ownership verdicts
  separately, actual versus planned duration and the first failure point.

Branches: a length refusal without a runtime format transition weakens/refutes
the transition-only explanation; preserve it and stop, never adjust length. An
EAPOL/management shape failure is separate and cannot weaken the decoder. Missing
PN/status metadata remains rejected. An initialization credit/guard failure stops
before scan-ready without a longer deadline. Healthy finite traffic supports only
this one lifetime, not sustained operation or safe key reuse. An SSH failure with
healthy transport selects its retained client/server/neighbor stage. Success does
not classify earlier failures or admit an unchanged retry automatically.

## Before any build or execution

First implement and review only this logical ownership change, reusing actual
source fixtures. Prove exact payload/one-page initialization accounting, finite
failure/poison behavior, no readiness on failure, no runtime mode writes, unchanged
crypto rejection/ACK gates and all observed RX mismatches on both ports. Test the
local data-window state transitions and owed-completion fence without assuming
firmware queue enforcement. Audit canonical series/profile selection; option-off
must recover C10 and leave existing profiles unchanged.

No code is implemented by this document. Do not build under the owner's current
hold. A later build needs the reviewable patch/tests and the owner's release of
that hold, clean pushed inputs, the standard Buildbox backend and package validation.
Only then can a separately reviewed real candidate/composition/install/protocol
lead to an owner physical boot2 handoff. No automatic device run follows this plan.

Keep GTK delivery, rekey, reuse and reconnect disabled. No -48 adjustment, longer
transport deadline, unrelated callback reverse engineering or new userspace API.
Staged 60 s / 2 min / 10 min operation and the full acceptance test remain open.
