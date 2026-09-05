# Reset-provider failure and lifetime follow-up

## New review evidence

This follows the existing [routing/resource review](REVIEW_NOTES.md) without
changing the six-patch topic or its profile proposal. The new observation is
the concrete probe-failure/unregister chain in pinned upstream commit
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c`. Selected source files were read from
the retained archive; no persistent source extraction, build, cache mutation,
probe, reset operation or device access occurred.

The added reset registration has a narrower lifetime contract than the entire
MT6797 clock driver. It uses managed registration, and driver-core probe failure
releases that registration. Existing unmanaged clock-provider state does not
thereby gain complete rollback or unbind support. The pure eight-case KUnit
proposal must not be described as testing these framework/lifetime paths.

## Failure matrix from the exact source

| Point | Reset-controller state | Clock state and review consequence |
| --- | --- | --- |
| Added registration returns an error | No successful managed reset registration remains after failed probe cleanup | Patch 4 returns before this platform invocation allocates/rewrites `infra_clk_data` or registers gates/factors. Already-existing early clock state is not rolled back. |
| Registration succeeds, then absent `infra_clk_data` allocation fails | `really_probe()` follows `probe_failed` to `device_unbind_cleanup()`, which calls `devres_release_all()`; managed reset registration unregisters | No new successful allocation exists in this branch. This source chain is not an allocation-fault injection test. |
| Gate registration fails | Reset registration has already succeeded; the top-level MT6797 initializer does not test the gate helper's returned error | The gate helper returns an error and has its own unwind loop, but the caller continues to factor/provider registration. This behavior predates patch 4. A top-level probe success is not proof that every gate registered. |
| `of_clk_add_hw_provider()` fails | Failed-probe devres cleanup unregisters the reset controller | The existing MT6797 initializer has no explicit gate/factor/`infra_clk_data` rollback before returning this error. Managed reset cleanup does not repair that separate existing clock path. |
| Successful driver is later detached | Managed reset registration calls the reset core's unregister path | The driver has no remove callback or explicit `suppress_bind_attrs` setting. Whole-driver detach/rebind support is not established by the new reset lifetime. |

The source evidence for the driver-core error edge is
`call_driver_probe()` -> `probe_failed` -> `device_unbind_cleanup()` ->
`devres_release_all()`. Reset devres invokes `devm_reset_controller_release()`
which calls `reset_controller_unregister()`. None of these observations is a
runtime result on the Gemini or a proof about every possible concurrent consumer.

## Outstanding reset consumers after unregister

This upstream reset core removes the controller from its discovery list, then
walks remaining reset handles under the controller lock. It nulls each handle's
controller pointer and waits for its SRCU readers before removing that handle
from the controller. The handle is not simply freed out from under its consumer.
The checked `reset_control_assert()` and `reset_control_deassert()` paths obtain
the pointer under SRCU and return `-ENODEV` when it is null.

This resolves the specific source-level concern that a managed provider detach
necessarily leaves those two APIs dereferencing freed controller memory. It
also establishes an observable loss-of-provider error for retained handles;
it does not promise transparent reattachment after reprobe or validate consumer
recovery policy. No concurrent unregister test or whole-driver unbind test ran.

## Syscon dependency and changed error propagation

The existing `mtk_clk_register_gates()` already calls
`device_node_to_regmap()`. When `CONFIG_MFD_SYSCON` is absent, the header's stub
returns `-ENOTSUPP`. Thus shared-syscon availability was already needed for these
gates; the reset addition is not the first use of that interface in the driver.

The behavior nevertheless changes on failure: the new reset-registration error
is returned immediately, whereas the old initializer ignored the gate helper's
returned error. Review the explicit fail-early behavior as part of patch 4;
do not claim that every failure outcome is identical to the old driver. The
proposed test config explicitly enables `MFD_SYSCON`, but configuration intent
is not a substitute for eventual resolved-config or runtime evidence.

## Binding compatibility rationale, with limits

The existing compatible and clock namespace are retained. The new two-entry
reset namespace and `#reset-cells = <1>` describe an additional capability of the
same infracfg node, with no new consumer introduced by this topic. Registration
does not require the property itself; reset consumer phandle parsing is a later
operation. An older upstream DT without reset consumers therefore does not fail
registration solely because that property is absent. New allocation/regmap
failure paths above still matter, so this is not a blanket old-DTB boot claim.

The stricter schema intentionally rejects old DT source lacking the new required
property. That schema compatibility decision needs binding-maintainer agreement;
source-level runtime reasoning cannot waive it. Likewise, a new DT's property
alone does not make an older driver implement resets. Historical project-local
reset IDs remain outside the upstream ABI being proposed.

## Review disposition

These findings support keeping the reset-registration ordering and its narrow
managed-lifetime explanation. They do not require changing the reviewed six
patch bytes for the proposed compile/pure-KUnit gate. They identify separate
existing clock error/cleanup debt and prevent stronger probe-success or unbind
claims. Any future consumer or physical lifecycle test must define its own
error-handling and recovery contract. No new runtime test is selected here.

[The source receipt](results/provider-failure-review.json) pins the inspected
files and exact provider patch. This review supplements, and does not supersede,
the pending binding, build, KUnit and maintainer acceptance requirements.
