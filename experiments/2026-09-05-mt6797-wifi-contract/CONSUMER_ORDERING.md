# CONSYS consumer attachment and resource ordering

This bounded source item follows `e47791426ce286146b9b88a5b2abda8bb8d9b29e`.
The [passive provider proposal](DEFERRED_REGISTRATION.md) suppresses provider
registration-time activation. **An ordinary single-domain platform consumer
still powers CONN before its driver probe.** The existing multi-domain API can
separate attachment from activation, but it does not bypass that earlier bus
attachment for the currently established single CONN island.

A second independent limit prevents a complete parent teardown: successful
runtime suspend is not confirmation that the island powered off. Consequently
no driver skeleton, new domain reference, mapping or consumer is added here.
This record identifies the actual usable calls and the missing integration
conditions; it does not replace missing preparation or rollback with stubs.

## Exact pre-probe path

At the pinned upstream revision, `platform_probe()` first applies assigned
clock defaults, then calls `dev_pm_domain_attach()` with attach-on/detach-off
flags, and only afterward calls the platform driver's probe. The OF backend
counts `power-domains`: exactly one reference invokes
`__genpd_dev_pm_attach(..., true)`, which calls `genpd_power_on()` before
returning. The parent cannot assert external reset or prepare rails in its own
probe before this activation.
[Platform entry](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/base/platform.c#L1497),
[single-domain selection](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/core.c#L3448).

Calling `dev_pm_domain_attach_by_name()` inside that probe cannot undo the
activation: it returns `-EEXIST` when `dev->pm_domain` is already populated.
Neither a domain name nor `PD_FLAG_NO_DEV_LINK` changes the earlier count.
Passing zero attach flags is also not an OF no-power escape at this pin:
`dev_pm_domain_attach()` forwards the attach-on flag to ACPI, but calls
`genpd_dev_pm_attach(dev)` without such a parameter.
[Public wrappers](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/base/power/common.c#L103).

With multiple genuine domain references, the automatic OF attachment returns
without attaching and the driver's probe can perform explicit attachment.
The selected hardware contract establishes the CONN island, not a second
parent power domain that could justify this topology. A duplicate, dummy or
unrelated domain added merely to change the count is not a solution. A bare
node without a power-domain reference cannot use by-ID attachment either.
Assigned clock defaults must likewise not perform an unreviewed preparation
step before probe.

## Smallest existing explicit-attachment path

Where the bus has legitimately left the device unattached, the smallest
interface is `dev_pm_domain_attach_by_name(parent, "conn")`. The name is a
prospective binding role, not an added binding or existing board declaration.
Its actual order is:

1. Refuse an already-attached parent; resolve the named index.
2. Allocate/register a virtual device on the genpd bus.
3. Add that virtual device to the selected domain through
   `__genpd_dev_pm_attach(..., false)`; skip its power-on block.
4. Enable runtime PM on the virtual device and queue an unused-domain OFF
   check. The passive provider's owned, initially-OFF prerequisite matters:
   this helper is not a promise of zero transitions for an arbitrary ON domain.

The returned pointer is the device on which explicit runtime-PM references
would be taken. Treat both ERR_PTR and NULL as failure for a required CONN
domain; no missing-domain success is acceptable. Attachment also processes
required OPPs before its power-on block. No CONN OPP/performance-state contract
is established here, so no such property or effect is assumed away or added.
[By-name/by-ID implementation](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/core.c#L3481),
[attachment and OPP ordering](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/core.c#L3387).

The list API is unnecessary for one explicitly managed handle. If a genuine
multi-domain consumer uses it, `PD_FLAG_NO_DEV_LINK` suppresses automatic
runtime-PM device links. Omitting only `PD_FLAG_DEV_LINK_ON` avoids the explicit
activation request when creating the link; it still creates a PM-runtime
supplier dependency. Runtime PM resumes those suppliers before calling the
consumer's resume callback, so preparation in that callback would again be too
late. Plain by-name attachment creates no such parent-to-virtual-device link.
[List flags](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/base/power/common.c#L193),
[supplier-before-callback order](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/base/power/runtime.c#L374).

## Resource operations before explicit activation

The following is an interface boundary, not an executable board sequence:

| Stage | Existing operation | Required interpretation |
| --- | --- | --- |
| Obtain external reset | `devm_reset_control_get_exclusive()` | Require the real CONMCU reset owner and a nonoptional handle; do not use the variant that deasserts during acquisition. |
| Prepare rails | Individual regulator operations in the reviewed order | The existing WMT delay, conditional rail and hardware-control selection remain requirements, not implicit bulk-regulator behavior. |
| Hold reset | `reset_control_assert()` | Check the provider result. A shared or optional reset is not equivalent to holding an exclusive line. |
| Request island activation | `pm_runtime_resume_and_get(pd_dev)` | Only after all outer preparation and provider transition prerequisites are implemented. Hold the successful usage reference throughout dependent activity. |
| Release external reset | `reset_control_deassert()` | Only after successful island activation and the subsequent reviewed MCU preparation; this is not implied by obtaining a PM reference. |

This does not prescribe moving reset assertion ahead of the retained WMT rail
order. The exact hardware ordering remains in [POWER_DOMAIN.md](POWER_DOMAIN.md).
`regulator_bulk_enable()` schedules individual enables asynchronously and
unwinds successful entries after another entry fails. It cannot encode the
observed inter-rail delay or the missing VCN28 hardware-control selection.
[Reset acquisition](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/include/linux/reset.h#L616),
[reset assertion](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/reset/core.c#L493),
[bulk enable](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/regulator/core.c#L5409).

`pm_runtime_resume_and_get()` repairs the runtime-PM usage count on a failed
resume; it does not reconstruct partially changed hardware. No rail-drop,
reset-release or automatic retry path can be inferred from that error.
[Runtime-PM reference handling](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/include/linux/pm_runtime.h#L516).

## Teardown cannot use runtime-suspend success as an OFF receipt

`pm_runtime_put_sync_suspend(pd_dev)` requests device runtime suspend. In the
genpd backend, `genpd_runtime_suspend()` calls `genpd_power_off()` and returns
zero afterward. `genpd_power_off()` is void: it can decline the transition for
active users, policy or subdomains, and can return after a provider power-off
error without marking the domain OFF. The caller therefore cannot treat
successful runtime suspend as permission to remove outer rails.
[Runtime suspend](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/core.c#L1269),
[domain OFF decisions](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/core.c#L951).

`dev_pm_domain_detach(pd_dev, false)` does not repair this: the genpd detach
callback ignores its `power_off` argument and queues a power-off work item
after removing the device. It does not return an attributable completed OFF
transition. Managed list detach also uses this backend. Thus an error label
that detaches and immediately drops rails would invent an unproved unwind.
[Detach implementation](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/core.c#L3256).

## Bounded implementation decision

No current driver-only skeleton satisfies the established ordinary platform
topology and failure contract. The smallest missing entry-point capability is
a reviewed way for that bus to leave a real single-domain consumer unattached
until its driver deliberately invokes the existing by-name/by-ID API. This
is a bus/framework integration question, not a new domain, clock alias or SPM
mapping. No invented driver flag or custom PM-domain wrapper is implemented.

Explicit runtime-PM ordering alone would also not establish system-sleep
ordering for the parent and virtual device. No system-suspend/resume callbacks
or unproved device hierarchy are proposed here.

Even with that entry point, safe outer-rail release needs provider-owned
sequencing or an explicit completed-OFF/error contract. A generic successful
runtime-PM put supplies neither. The unresolved reset/rail/sleep-mask/SPM-key
and transition-recovery owners still prohibit activation; this source result
does not change the passive proposal's compilation or physical admission.
The [roadmap](../../docs/ROADMAP.md) alone orders follow-up work.

## Evidence and limits

[Source identities](results/consumer-ordering-sources.json) pin the current
upstream and maintained v7.1.3 inputs. Ten relevant function bodies compare
byte-identical; the common attachment file and runtime-PM header also match
in full. Other whole files differ, so no whole-kernel equivalence is claimed.
[Validation](results/consumer-ordering-validation.txt) records the comparison
and repository checks. No new executable fixture, source tree, driver, kernel
build, device operation or private acquisition was needed for this interface
finding. No shared integration files changed.

The earlier passive-registration fixture remains limited: source fetching has
per-request timeouts but no strict aggregate deadline or response-byte cap;
captured subprocess output has no strict byte cap; subprocess timeouts do not
provide process-group containment. Pinned digests and passing selected cases
do not establish those bounds. That runner is unchanged in this item.
