# A53 modern CONN provider integration gate

The isolated modern MT6797 CONN child-domain proposals compile, but they have
not been linked with the accepted A53 service foundation. This profile checks
that exact integration before a shared CONSYS owner or effect-bearing DT child
is added. It keeps the frozen A53 fragments and patch bytes, then selects the
modern provider proposals in canonical series order. Only the modern
provider is enabled; the legacy SCPSYS provider remains disabled.

The hypothesis is that the combined kernel links with the modern provider and
MT6797 CONN data, while the resulting Gemini DTB contains no modern controller
compatible, CONN child or consumer. The unique evidence is the clean pushed
project commit, validated Buildbox package, resolved config, linked symbols and
DTB inspection. A patch conflict or link failure must be repaired at the
specific integration boundary. A DTB containing an enabled modern CONN child
would invalidate this compile-only gate and require a separate effect review.

This profile is not a boot2 image or device candidate. No new CONN power,
rail, reset, remap, EMI, firmware, radio or DMA action is requested. A later
active candidate still needs one shared owner, external VCN/CONMCU sequencing,
retained-writer exclusion, remap/EMI policy and failure retention. Build success
alone will not prove those contracts or Wi-Fi support.

## Build result

The clean pushed commit `2f5f79c1d290e520ceee9d88010979df73f3b31d`
applied its 514 selected patches and linked a full A53 kernel on Buildbox.
The fetched package passed its checksum inventory. The
[build receipt](results/build-a53-integration.json) pins the package and
source/config identities. Relative to the accepted A53 service build, the
resolved config changes only the release suffix and enables
`MTK_SCPSYS_PM_DOMAINS`; the legacy provider remains disabled. The linked
image contains MT6797 CONN domain data, the retained-fault query and the
modern provider initcall. All five Gemini DTBs are byte-identical to the
A53 service package and contain no modern CONN controller compatible.

This passes the source-integration gate. It does not exercise provider probe,
initial-OFF admission, a domain transition or any Wi-Fi operation on the PDA.
The next code slice must add a real shared owner and its dependency/retention
contract before an effect-bearing DT child or boot is considered.

The profile later selected a [checked OFF query](../2026-09-26-mt6797-modern-provider-off-query/README.md)
as an additional provider proposal. The build above predates that selection;
the [later A53 build](../2026-09-26-mt6797-modern-provider-off-query/results/build-a53.json)
validates its source integration without adding an active DT child.

## Domain attachment order found in the built source

The exact prepared 7.1.3 source exposes an owner-ordering constraint.
`drivers/base/platform.c` calls `dev_pm_domain_attach()` with
`PD_FLAG_ATTACH_POWER_ON` before invoking a platform driver's probe.
`drivers/pmdomain/core.c` attaches a device with exactly one
`power-domains` entry through `__genpd_dev_pm_attach(..., true)`, which calls
`genpd_power_on()`. A CONSYS owner node with a single ordinary
`power-domains` reference would therefore request CONN power before its probe
could assert independent CONMCU reset or prepare the VCN rails. Do not add
that binding to an active candidate.

The same source offers a separate non-powering attachment mechanism:
`of_genpd_add_device()` calls `genpd_add_device()` without a power-on call;
`dev_pm_domain_attach_by_id()` likewise passes `false` to the attachment
helper. These are source-level options, not an implemented owner contract.
The staged-child topology below uses the ordinary child attachment instead,
after parent preparation. Runtime activation, fault queries and retained
cleanup still need proof. This finding changes the planned binding and
activation path; it does not justify a device boot or CONN transition yet.

## Staged child population in the pinned source

A parent/child topology provides the needed ordering without a new generic
power-domain attach flag. In the exact prepared 7.1.3 source, the default OF
population walk creates a device for a custom-compatible parent but recurses
only into `simple-bus`, `simple-mfd`, `isa` and AMBA buses. A CONSYS manager
parent without `power-domains` can therefore bind while its WLAN child remains
uncreated. After the manager has established the real shared-resource handoff,
asserted CONMCU reset and prepared the VCN rails, it can call
`of_platform_populate()` on its own node. The child may then use the ordinary
single CONN `power-domains` reference: the platform bus attaches and requests
CONN power when that child's driver probes, after parent preparation. The
child must leave MCU preparation and reset release under the manager's
ordered control. This refines the earlier [direct-consumer audit](../2026-09-05-mt6797-wifi-contract/CONSUMER_ORDERING.md), which correctly rejects a
single-domain reference on the *parent*.

This is an ordering mechanism, not a completed ownership contract.
`of_platform_populate()` creates devices rather than waiting for successful
child probes, and its loop does not report a child probe failure. The parent
must retain prerequisites while child binding is absent, deferred or failed,
query the provider's retained fault before hardware use, and never infer a
completed OFF transition from child unbind or runtime-PM suspend. In
particular, automatic `devm_of_platform_populate()` teardown cannot be paired
with unconditional rail cleanup: its release depopulates children without an
attributable successful CONN OFF receipt. The manager's permanent lifetime,
explicit client quiescence and fault-held cleanup remain required. No child
DT node or hardware action is admitted by this source audit.
