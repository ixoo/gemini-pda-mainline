# A53 modern CONN provider integration gate

The isolated modern MT6797 CONN child-domain proposals compile, but they have
not been linked with the accepted A53 service foundation. This profile checks
that exact integration before a shared CONSYS owner or effect-bearing DT child
is added. It keeps the frozen A53 fragments and patch bytes, then selects the
nine modern provider proposals in canonical series order. Only the modern
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
applied all 514 selected patches and linked a full A53 kernel on Buildbox.
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
The next implementation must select a reviewable DT relationship and prove
that explicit attachment, runtime activation, fault queries and retained
cleanup preserve the rail/reset-before-domain order. This finding changes
the planned binding and activation path; it does not justify a device boot
or CONN transition yet.
