# Terminal retention after failed WLAN startup

The unselected [patch](patches/probe-retain/0001-wlan-retain-failed-startup-resources-until-recovery.patch)
addresses the [startup-failure caller gap](REMOVE_RETENTION.md#startup-failure-follow-up-unresolved-containment)
after the 29-patch removal-retention composition. It is an incomplete
experiment checkpoint: lower DMA failure cleanup, concurrent reset, full
resource isolation and independent recovery remain unresolved. No canonical
profile selects it, and it has no device result or boot candidate.

The [source receipt](results/probe-retain-sources.json) pins five parent and
output files. The reconstructed `wlan_lib.c` parent also matches the
[previous native compilation receipt](results/remove-retain-object-compile.json).
The patch archive uses a synthetic identity without DCO certification.

## Why failed startup cannot use ordinary teardown

`wlanAdapterStop()` always returns its initially successful status. It can
reach that return after a skipped firmware command, firmware-stop timeout or
reset request, and releases adapter allocations regardless. Its return is not
an idle or isolation certificate. The existing [stop evidence](STOP_HOOKS.md)
records these distinctions without repairing them.

The selected [DMA failure paths](DMA_HOOKS.md#selected-deadline-and-idle-exits)
likewise do not promise release safety: a deadline can return with the HIF lock
and mapping retained; an idle-count escape can unmap without observing idle.
An additional outer worker wait cannot establish hardware quiescence. A
startup failure must not initiate ordinary cleanup merely because it returned
to the caller.

## Implemented path

`wlanProbe()` marks the retention boundary immediately before firmware
mapping and adapter startup, after successful IRQ setup. Every later nonzero
startup result reaches `wlanProbeRetain()` before the old cleanup switch,
including firmware mapping, adapter startup, partial worker creation, netdev
registration and later proc setup failures. Earlier bus/netdev/IRQ setup
failures retain their previous behavior.

The helper aborts capture, clears readiness, requests halt and wakes the three
initialized wait queues. It does not wait, clear valid task pointers, unregister
or free the netdev, stop the adapter, release IRQs or change power. These are
halt requests, not observed completions. Workers may still be active or stuck;
resources remain occupied until independent recovery. Each failed
`kthread_run()` is checked before scheduling or creating the next worker, and
its error pointer is replaced with null.

`wlanAdapterStart()` keeps its acquisition code and failure-stage assignments,
but replaces its outer failure-release switch with a stage diagnostic. It
retains allocations that the outer switch would have released. Native helper
cleanup that already occurred deeper in startup is not undone or repaired.
The firmware mapping caller still performs its existing image unmapping.

The private `-EUCLEAN` result means that startup resources were retained. AHB
preserves it, skips the second removal call and latches failure. Later AHB
probe/removal requests return the same error before callbacks or power calls.
`wmt_func_wifi_on()` preserves this one result while keeping the previous
normalization of other errors. WMT keeps the Wi-Fi occupancy state at
`FUNC_ON`, skips SDIO/common power-off and latches the retained failure. That
state means occupied resources, not successful networking: the Wi-Fi-on bit
is not set on this failure, and the WMT operation dispatcher rejects all later
operations before their handlers. The latches have no reset API; fixture
resets model a new boot. They do not cancel a request already executing or
protect against out-of-band reset, direct control, unregistration or unload.

The controller must treat the first error as terminal. No second ON/OFF,
cleanup retry, continued networking or WMT reinitialization is selected.
The future independent recovery owner must be armed before the first native
effect. This patch neither implements nor authorizes that recovery.

## Verification

The [focused fixture](test-probe-retain.py) compiles the actual AHB probe/remove,
WMT Wi-Fi-on, function-on, common power-off and operation-dispatch bodies.
It injects the probe result, hardware and other dependencies. It separately
executes the exact native worker-creation block, probe error tail, retention
helper and adapter-start result tail; it does not execute complete probe or
adapter initialization.

All 29 cases pass. They cover ordinary success/error behavior, both common
transport branches, another active subsystem, retained failure, subsequent
AHB and WMT requests, failure of each worker creation, late startup failure,
failure before worker creation, earlier setup cleanup and all five adapter
failure stages. Parent/child ordinary caller effects match; retained paths
skip the modeled cleanup and power effects. Compilation uses strict warnings
with explicit unused-code exceptions for native bodies and injected stubs.
The extracted startup fragments also allow the original cleanup switch's
intentional implicit fall-through. The first Buildbox attempt stopped on that
GCC warning in the host fixture before native compilation; no kernel failure
is inferred from it.
Patch replay/reversal and strict Checkpatch pass with the established legacy
`CAMELCASE` and synthetic `MISSING_SIGN_OFF` exceptions.

`check-startup-objects.py COMMIT --probe-retain` selects 30 patches and the
same 19 native translation units as removal retention, verifies five source
pairs and runs the focused fixture. Native compilation is pending. A passing
compile will not establish runtime retention, DMA safety, concurrency or
recovery. Full linking, resource isolation, controller/recovery integration
and a separately admitted device protocol remain necessary.
