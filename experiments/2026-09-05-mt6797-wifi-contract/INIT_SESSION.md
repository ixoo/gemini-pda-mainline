# One pending gen3 INIT command per owner session

This offline slice follows `99b6af9fe44dca1a0ebc057bfcd881ebc3f3183c`.
It resolves one host implementation dependency: how an outstanding
DOWNLOAD_CONFIG/CMD_RESULT exchange is kept within one bounded, attributed
owner session. It composes the unchanged [logical-record decoder](INIT_PROTOCOL.md)
with a pure lifecycle model and fake-clock/fake-owner tests. It does not
construct or select a kernel, access hardware, or start a radio.

The implementation owner is the Wi-Fi workstream; integration and shared
documents belong to Orchestrator. Scope is this record, its validation receipt
and two new Python files. The topic remains `codex/mt6797-wifi-contract`, with
no Linux tree. The eventual consumer is an upstream wireless driver under a
shared MT6797 connectivity provider. This model is an internal reference,
not a kernel patch or submission-ready topic; there is no DCO certification
or upstream submission in this slice.

## The gap and its boundary

The earlier decoder validates one supplied command/result pair. It cannot
know whether another request is outstanding, a deadline expired, ownership
was lost, or the same sequence was already consumed. A matching eight-bit
sequence alone supplies none of that context.

[`wifi_init_session.py`](scripts/wifi_init_session.py) keeps that context for
one session. A future common provider must own the session object and
serialize every call under the same lifecycle lock used for command admission.
Multiple independently constructed objects would not serialize multiple
drivers. This sequential reference model supplies no lock, interrupt handler,
shared-register lease, memory barrier or transport cancellation mechanism.

The [shared ownership audit](OWNERSHIP.md) identifies why this must belong to
one provider: WMT and WLAN share remap/protection resources, and a local WLAN
success cannot establish their ownership. The session accepts an independently
supplied owner generation and readiness observation; it does not read HIF
registers, obtain driver ownership, arbitrate shared memory or validate power.
Those observations are assertions to check for consistency, not proof that
hardware is ready or that stale receive data has been drained.

## Session policy

The constructor fixes an unsigned 64-bit owner generation and a positive
unsigned 64-bit timeout interval. Time is expressed in abstract monotonic
ticks supplied by the caller. No wall-clock or hardware timer is read, and
no source-specific millisecond timeout is inferred from this interval.

| Condition | Modeled effect |
| --- | --- |
| Valid command in an idle session | Consume the expected sequence and establish one deadline; retain only scalar bookkeeping and a bounded sequence set |
| Another begin while pending | Refuse without replacing the outstanding exchange; first consider valid ownership/clock observations and pending expiry |
| Matching success before the deadline | Complete the command and return to idle; the sequence stays consumed |
| Reuse of any consumed sequence | Refuse; the session has at most 256 accepted commands and never wraps its identity space |
| Matching nonzero firmware status | Terminal firmware rejection, distinct from malformed protocol input |
| Malformed or mismatched result while pending | Terminal protocol failure; no resynchronization search or alternate event acceptance |
| Current tick at or after the pending deadline | Terminal timeout, including an otherwise matching late ACK |
| Clock regression, owner-generation change or lost readiness | Terminal session failure; do not accept a result using the old context |
| Transport error or closing with work pending | Stop the exchange; recovery remains required |
| Invalid API argument type/range | Fixed refusal with no mutation or private value in the error |

There is no retry, reset, rearm or automatic new generation. A failed session
cannot begin another exchange. Teardown records the unresolved state; it does
not release a physical resource or perform rollback. Creating another object
after failure is outside this model's recovery proof: the provider must first
establish the required reset/transport quiescence and fresh ownership context.

Deadlines are checked only when an observation is supplied through the API.
Production code still needs a bounded timer/wait and a cancellation path.
Passing a later generation label does not authenticate a packet. In
particular, a caller that relabels old bytes can defeat any association based
only on these observations. Avoiding sequence reuse inside one object removes
that local ambiguity; it does not prove freshness across object lifetimes.

## API and fake observations

The class exposes `begin`, `receive`, `poll`, `transport_error`, `close` and
`snapshot`. Begin and receive take already-delimited immutable records.
Context-bearing methods require `now_tick`, `owner_epoch` and `owner_ready`;
begin also requires the independently expected sequence. No method sends,
reads or constructs a packet. All terminal outcomes and refusals use fixed
classification codes.

The object retains no raw command or reply bytes. Snapshots contain bounded
status/counter metadata, without owner-generation values, sequence values,
addresses, diagnostic data or input bytes. They continue to deny hardware
access and loading/transmission authorization. A successful model transition
does not prove firmware download or radio support.

Terminal observations return a snapshot with the failure classification.
Ordinary refusals raise `Refusal` without changing any state, including the
last accepted clock observation. Accepted begin/receive/poll calls advance
that clock floor. Closing a failed session changes its state to closed while
preserving its original failure classification and recovery requirement.

The [tests](scripts/test_wifi_init_session.py) supply synthetic logical
records, a fake monotonic clock and fake shared-owner observations. They can
change time or revoke ownership between begin and receive without waiting or
touching a device. They exercise overlap, exact deadline boundaries, late and
duplicate results, clock regression, ownership loss, sequence exhaustion,
terminal-state behavior, refusal order and privacy. Real IRQ/DMA ordering,
clock behavior and recovery remain untested.

Run the new suite and the unchanged 36 decoder tests with:

```sh
python3 -B experiments/2026-09-05-mt6797-wifi-contract/scripts/test_wifi_init_session.py
python3 -B experiments/2026-09-05-mt6797-wifi-contract/scripts/test_wifi_init_protocol.py
```

[Validation](results/init-session-validation.txt) records exact helper
identities, executed checks and review outcomes. The public source facts and
stricter session policies are distinguished in the source review below.

## Source review and remaining dependencies

All source references below use Planet commit
`c5b0be85017ad0c599725e8273842efdbecdd88a`, beneath
`drivers/misc/mediatek/connectivity/wlan/gen3/`. These are independently
described facts from the selected GPLv2 source. No vendor implementation,
binary, private capture, calibration value or firmware is added.

| Selected source behavior | Consequence for this model |
| --- | --- |
| Startup processes sections synchronously and waits for CONFIG success before PDA transfer. The sequence allocator locks only an increment of an eight-bit field, which wraps through zero. | Global transaction serialization and refusal to reuse sequences are added policy, not demonstrated vendor guarantees. [Startup ordering](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L716), [allocator](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic.c#L1025) |
| The ACK verifier consumes one port-0 response and fails the first event/sequence/status mismatch. It neither searches past another event nor checks returned logical length/type. | The existing strict decoder is retained; no drain, alternate event or retry is inferred. [Verifier](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L2769) |
| RX has a nominal 1000 ms wait while reported length is zero, with no deadline check after a nonzero length or around the port transfer. TX resource polling has a separate 256-iteration, 50 ms sleep policy. | One absolute pending deadline is added policy; the model does not inherit an end-to-end bound from these loops. [RX wait](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_rx.c#L3615), [TX resource wait](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_tx.c#L322) |
| The selected non-`_HIF_SDIO` macros discard port-read/write return values; `nicTxInitCmd` returns success after its write. Configuration also replaces an earlier error with the ACK result. | Positive transport completion is still an external obligation. The model's `transport_error` represents a reported failure, not proof every failure can be observed. [Selected macros](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic/hal.h#L263), [TX return](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_tx.c#L2259), [configuration result](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L2472) |
| AHB guards refuse writes during DMA-fatal/reset/firmware-owned state, while the corresponding read guard returns true without reading. Reset notifications change a flag, but the ACK verifier has no owner-generation check. | Stale-buffer acceptance is a source-based possibility, not a device observation. Ownership loss and transport uncertainty must stop a future transaction. [AHB read guard](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/ahb.c#L778), [write guard](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/ahb.c#L1068), [reset notification](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/gl_rst.c#L130) |
| Startup requires driver ownership. The ownership helper can return immediately from its software flag, and the ACK verifier does not revalidate ownership. | A startup flag is not the shared-provider lease required here. Current ownership, cancellation and reset exclusion still need implementation. [Startup prerequisite](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L358), [ownership helper](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_pwr_mgt.c#L147) |

Begin is logical admission, not a separate positive TX-completion receipt.
A matching receive is therefore still only a model result. A production
transport must propagate transfer errors and establish actual completion;
that path is outside this lifecycle slice.

The [earlier INIT](INIT_PROTOCOL.md#immutable-source-identities),
[calibration](CALIBRATION.md#exact-source-identities) and
[firmware](FIRMWARE_FORMAT.md) records pin reused files. Additional raw-file
SHA-256 identities verified for this audit are:

| Path below gen3 | SHA-256 |
| --- | --- |
| `nic/nic.c` | `6ccae6fbbd21287df1247720f2056c3961a5d1cdeeba5bcc2246a6e8de4b0ce4` |
| `include/nic/adapter.h` | `2d4b9dbb18af3de48d369a0c232266de3f3840a23ea0175ef8000fdf7bc4cab6` |
| `include/nic/nic_tx.h` | `a51b8357b2a5fc0fdff095866d693194274f552cb2e722016bb1ce7c81612db7` |
| `include/nic/hal.h` | `24b9bce2fc8b331d75a330cae8c9291816bb90cff8078200cd7ecb719f180ee0` |
| `nic/nic_pwr_mgt.c` | `413f7b153029a34c3c326fa59ae44b6eace685ae1d53cde9b9cc2b48728ea039` |
| `include/pwr_mgt.h` | `fc2d5dec5960775b05c235ee05544f5f7bd41fa63065dfdd4293f3638ce4b06e` |
| `os/linux/include/gl_kal.h` | `090ba29f6e64d9bc527fc018277a4301e033f0c3e9c52e745b5058b4de653eb0` |
| `os/linux/gl_rst.c` | `8240d06a875947afca6c28a12a2f49efb85ee3b25f4127b35dc17f463449309a` |

The remaining runtime boundary is an actual provider/transport implementation
that supplies truthful ownership observations, extracts and attributes each
logical record, runs the deadline, stops transfers and proves recovery.
Calibration production history remains a separate dependency; it does not
block this offline command/resource model. No device action budget or new
readiness claim is created. The [roadmap](../../docs/ROADMAP.md) remains the
only owner of ordered work.
