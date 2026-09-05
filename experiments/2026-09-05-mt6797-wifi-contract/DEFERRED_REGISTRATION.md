# Legacy MediaTek deferred domain registration proposal

This work follows `df61a2356023d7db4f74901624ae95ba28f2fc8a` and implements
the provider-registration operation identified in [POWER_DOMAIN.md](POWER_DOMAIN.md).
The [kernel proposal](../../patches/proposals/0001-pmdomain-mediatek-defer-initial-activation.patch)
adds an explicit capability for an initially-off standalone domain to register
without an initial power callback. A refused domain occupies a NULL onecell
slot; other domains keep their indices and normal registration behavior.
No kernel-core interface change is needed.

No SoC data selects the capability. There is no CONN binding identifier,
consumer, board node, new register mapping, manifest/profile/series change,
build candidate or hardware admission. Orchestrator owns integration and the
Buildbox window. This is one provider implementation proposal, with a host
fixture for its actual C functions, not a new session abstraction.

## Source and patch identity

The upstream audit baseline remains Linux
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c`. Its legacy provider source digest
is `9ce2b2c95a38bc4c7b801aff9b7c26da2dc8ec2e3fd34199adaedf1db3007226`.
The proposal is a `git format-patch` export from a disposable, single-file
public-source snapshot, not a vendored Linux checkout. The source and temporary
Git state were removed after export. The patch message names the real upstream
source pin; its temporary Git parent is not represented as an upstream commit.

The maintained [v7.1.3 provider](https://github.com/gregkh/linux/blob/199c9959d3a9b53f346c221757fc7ac507fbac50/drivers/pmdomain/mediatek/mtk-scpsys.c)
is byte-identical to this audit baseline.
Provider-file application after local MFG patches 0047 and 0050 is checked
separately from application to raw upstream. This is not a full-stack apply,
configuration or kernel-build result. The existing repository manifest remains
the build authority; this unselected proposal is not added to canonical series
by the Wi-Fi worker.

The relevant v7.1.3 genpd initialization, translation, attachment, late-OFF and
disabled-interface functions also match the current audit. The whole core
files differ: onecell registration assigns the provider-device parent at a
different stage, while NULL skipping, membership checks and unwind semantics
match. The validation record pins both versions without claiming whole-file
identity for the core.

The patch has a clearly synthetic, non-certifying experiment author and no
`Signed-off-by`. It is **not submission-ready**. The implementation is
independently authored with AI assistance; no vendor implementation is copied.
Future upstream submission requires actual author attribution, truthful DCO
certification, a reviewed user of the capability, and the missing kernel checks.

## Implemented behavior

`MTK_SCPD_KEEP_DEFAULT_OFF` is an opt-in legacy-provider capability. Existing
domain data has no such bit and retains its prior behavior. The implementation
does the following only for a flagged domain:

1. Refuse when generic power domains are unavailable or the status mask is
   zero. Neither refusal reads status or invokes a power callback.
2. Check both existing power-status registers before acquiring that domain's
   optional regulator. Only both masked words clear passes. Both set returns
   `-EBUSY`; a mixed result returns `-EINVAL`. No state is normalized.
3. Isolate that domain's regulator or clock acquisition error in its NULL
   slot. Normal-domain resource errors retain the existing provider-wide
   failure behavior. The common clock lookup still acquires handles for the
   existing provider; it does not enable clocks.
4. Recheck both ACKs immediately before registration, after resource setup.
   On success call `pm_genpd_init(..., true)` without either power callback.
   An initialization failure also leaves a NULL slot. Publish a pointer only
   after this domain's successful initialization.

Missing optional supply still means optional: `-ENODEV` is accepted just as
before. This is not a supply-preparation gate. A refused resource handle may
remain managed by the provider's device lifetime; the proposal does not enable
it or add a resource retry worker.

For normal domains, the provider still calls `power_on()`, warns on failure,
initializes software state from that result and retains its previous treatment
of initialization/provider-publication errors. In particular, the explicit
normal-domain activation under `CONFIG_PM=n` remains. This focused change does
not repair the legacy provider's unrelated error handling.

The new capability is restricted to domains absent from the SoC subdomain
table. A linked flagged entry is invalid static configuration and rejects the
whole probe **before resource allocation or power operations**. Silently
withholding a parent would strip an existing child's dependency; silently
activating the parent would violate the capability. The future CONN proposal
must therefore remain standalone. Runtime status/resource refusal of a valid
standalone entry withholds only that entry; ordinary multimedia relationships
still register.

## Why NULL is required, and what a refused consumer sees

The existing core provider loop explicitly skips NULL slots. Error pointers
are unsuitable: they fail the registered-domain membership check and can
unwind publication of previously added domain devices. The default onecell
translator returns `-ENOENT` for an in-range NULL slot and `-EINVAL` for invalid
arguments or indices. Keeping `num_domains` and the original array positions
preserves the existing power-domain ABI.
[Core registration](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/core.c#L2750),
[core translation](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/core.c#L2599).

Ordinary consumer attachment converts failed lookup through
`driver_deferred_probe_check_state()`. The result can be `-EPROBE_DEFER`,
`-ENODEV` after initialization without modules, or `-ETIMEDOUT` after the
deferred-probe timeout. This proposal does not promise perpetual probe
deferral. Withholding is static for that provider instance: later ACK changes
or consumer reprobes do not reacquire resources, rerun admission or publish the
slot. No asynchronous retry is added.
[Attachment lookup](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/core.c#L3375),
[deferred-probe policy](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/base/dd.c#L285).

## Limits on what registration establishes

`pm_genpd_init(..., true)` sets software OFF without calling `power_on()`.
Provider-device probe is a no-op, and late unused-domain/sync-state work skips
a software-OFF domain. These paths do not defeat suppression of provider-probe
activation. With generic domains unavailable, the new path refuses; it does
not fall back to powering the domain.
[Initialization](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/core.c#L2395),
[unused-domain handling](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/core.c#L951),
[disabled interfaces](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/include/linux/pm_domain.h#L340).

Two sequential ACK reads are not an atomic ownership lease. An OFF result
does not establish firmware relinquishment, independent CONMCU reset,
protection, rails, SPM key authority or recovery from a partial transition.
The second check catches an observed change during setup; it cannot exclude a
later change by another owner. Linux ownership remains a prerequisite for
selecting this capability, not something the bit or ACKs can certify.

Normal single-domain attachment may call `power_on()` **before the consumer's
own probe**; runtime resume also powers the domain before the consumer's resume
callback. The multi-domain attachment interface avoids initial activation but
still requires deliberate sequencing. Therefore this proposal establishes
only provider-probe callback suppression. A future CONN consumer must arrange
outer preparation before any path that can activate the island, using reviewed
standard subsystem interfaces. No consumer is enabled here.
[Attachment power-on](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/core.c#L3411),
[multi-domain attachment](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/core.c#L3517),
[runtime resume](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/core.c#L1308).

The exact remaining rail/reset/SPM-control/order/rollback prerequisites stay
in [the power-domain contract](POWER_DOMAIN.md). Passive registration is not
Wi-Fi support, a safe power transition or authorization for a device action.
The [roadmap](../../docs/ROADMAP.md) alone orders subsequent work.

## Reproduction and validation

Run the bounded public-source fixture from the repository root:

```sh
python3 -B experiments/2026-09-05-mt6797-wifi-contract/scripts/test_deferred_genpd.py --checkpatch
```

The [runner](scripts/test_deferred_genpd.py) verifies pinned source and patch
digests, applies the patch to that exact provider file and extracts the actual
C functions into temporary state. The [host fixture](src/deferred_genpd_test.c)
replaces only kernel boundary types and operations with synthetic registers,
resource results and ordered-call spies. It also compiles the actual core
onecell translator. It does not reproduce the decision logic in a separate
model, access hardware, or claim to emulate kernel concurrency or firmware.

Coverage includes OFF/ON/both mixed ACK cases, unrelated status bits, first
through last array positions, multiple deferred entries, changed state after
setup, zero mask, optional supply absence, regulator/clock errors, genpd
initialization failure, generic PM disabled, existing callback order, original
lookup indices and invalid linked use before provider side effects. Deliberate
unsafe mutations must fail explicit fixture assertions. Address/undefined
behavior sanitizers cover the host fixture, not the Linux driver in a kernel.

The runner locks a private managed temporary root, verifies its marker before
removing stale regenerable state, and removes source/binaries on success,
failure and handled interruption. It retains only the empty managed root,
marker and lock. No Linux tree or generated binary is committed.

[Validation](results/deferred-genpd-validation.txt) records exact source,
patch and fixture identities, counts, independent review and publication
checks. Checkpatch is run with only the deliberate missing-DCO exemption;
that result is not submission readiness. Full kernel compilation remains
pending the integrator's explicit Buildbox admission/window after commit,
push and canonical input selection. No VM kernel build is permitted or used.

The eventual destination is the upstream MediaTek power-domain provider,
reviewed through [GENERIC PM DOMAINS](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/MAINTAINERS#L11014)
and [ARM/Mediatek SoC support](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/MAINTAINERS#L3158).
Delete this proposal once an accepted upstream change supplies the required
behavior, or when maintainers select a different provider architecture. Shared
documentation and manifest/series integration remain with Orchestrator.
