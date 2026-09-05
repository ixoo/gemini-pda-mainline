# Isolated provider lifecycle compilation

The integrator selects `mt6797-provider-compile` for one explicit Buildbox
compile and validated package fetch after this exact input revision is checked,
committed and pushed. It combines two disjoint, independently reviewed changes:

- [Common clock cleanup](cleanup-proposal/GENERATION_RESULT.md), patch SHA-256
  `eabc1a33c23b4511a285bb2660376585f4e8332f2bca124ffab606e308ee9a62`.
- [Passive SCPSYS registration](../2026-09-05-mt6797-wifi-contract/DEFERRED_REGISTRATION.md),
  patch SHA-256 `e2338d566150a9e5a929b6a37e1bf76e356c4989391dd8549ed36b8e7554bc7f`.

No SoC selects the passive capability. There is no device candidate, new node,
QEMU invocation, physical admission or submission certification. The original
generation/host-test receipts retain their scopes; this profile supplies the
previously missing compiler and linkage check, not kernel execution evidence.

## Exact source and profile

The [manifest](../../kernel/manifest.json) reuses the existing complete source
tuple for upstream `4d7d9486c04d917265f64c55bd23b2cc4fe7749c` (7.3-rc1),
archive SHA-256 `45590c057805bc9cf7281ce04d5dbde5316b7c8b017998cafac301f67e92682d`.
The [two-patch series](../../patches/series-mt6797-provider-compile) contains only
the proposals above, in canonical order. The validated six-patch infracfg topic
is independent and is not needed for this compilation.

The [allnoconfig fragment](../../configs/mt6797-provider-compile.fragment)
selects the real legacy SCPSYS, common clock, syscon, regulator and PM paths.
An independent review of the pinned upstream Kconfig/Makefiles confirms that
legacy `MTK_SCPSYS` selects `PM_GENERIC_DOMAINS` only with `PM=y`; the newer
`MTK_SCPSYS_PM_DOMAINS` provider remains disabled. Common MediaTek clocks select
the reset-controller core. No new toolchain or test framework is required.

All 190 existing effective inputs were compared before/after admission: source
tuple, base configuration, every fragment byte and ordered patch bytes remain
unchanged. The default profile and historical default series also remain fixed.
Only the new profile selects these appended canonical entries. The invariant
audit must cover all 191 profiles before publication.

## Build window and storage

Buildbox doctor passed: about 266 GiB workspace and 9.5 GiB home free; host
space was about 87 GiB. Reuse the retained verified archive. The existing
six-patch prepared tree is a different source state and must not be relabelled
or mutated. The normal builder owns one managed tree for this new two-patch
state and reuses it when its recorded state matches; no second copy of that
state or host source export is allowed. The normal shared lock serializes work.

Keep the integrator checkout frozen from submission through validated fetch:

```sh
KERNEL_PROFILE=mt6797-provider-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-provider-compile ./scripts/buildbox fetch-package
```

No other worker has a backend mutation window during this build. A build or
configuration failure requires review of the actual failure before any retry.
There is no VM fallback. Retain the validated package and decision-relevant
compiler/provenance evidence; no boot container is constructed.

## Acceptance and limits

Require a clean exact published project revision, successful final ARM64 link,
normal package validation and complete fetched inventory/checksum/provenance
checks. Expected release is `7.3.0-rc1-mt6797-provider-compile`. The resolved
configuration must enable ARM64, ARCH_MEDIATEK, COMMON_CLK, COMMON_CLK_MT6797,
COMMON_CLK_MEDIATEK, OF, HAS_IOMEM, MFD_SYSCON, REGMAP, REGMAP_MMIO, MTK_SCPSYS,
MTK_INFRACFG, PM, PM_GENERIC_DOMAINS, REGULATOR and RESET_CONTROLLER. Require
every explicit negative fragment setting to remain disabled.

The complete patched source hashes must be:

- `drivers/clk/mediatek/clk-mtk.c`: `01f33c475e9bbe6ffef504d8247acd618bd53cc563de42abef4ada96b8344646`.
- `drivers/pmdomain/mediatek/mtk-scpsys.c`: `216b022e433b2a55b255d30933e313e296415c624306dd6b0c4f76ac65a51f54`.

Inspect real object/command records for `clk-mtk`, `clk-mt6797`, MediaTek reset,
legacy `mtk-scpsys`, genpd core, MediaTek infracfg, regulator core/devres, reset
core, syscon and regmap-mmio. Review linkage to real genpd/regulator/reset
functions rather than disabled stubs. Do not require static helper symbols that
the compiler may inline, or confuse symbol presence with exercising an error
path. Record only bounded metadata from the builder; fetch no raw source/object
tree. Host control-flow fixtures retain their separate scope.

Status at admission: source/profile review complete; compilation, resolved
configuration, object/linkage review and validated fetch pending. Actual driver
lifecycle execution, CONN ownership/activation and Wi-Fi usability remain open.

## Completed build and package review

The exact admitted revision `7029b1368134eef359dc43997bad84b73f426578`
built successfully with `BUILD_MODULES=0` and `KERNEL_JOBS=64`. A first local
invocation could not refresh Git's `FETCH_HEAD` under the filesystem sandbox;
it stopped before remote submission. Retrying that local preflight with the
authorized Git access submitted one kernel build. No input was changed or
failed kernel build repeated. Publication CI passed for the input revision.

The normal builder applied exactly the two patches, resolved every requested
configuration option, linked the ARM64 kernel and validated its package. The
checkout remained clean and frozen through the standard validated fetch. The
[build provenance](results/provider-compile-7029b136/build.json) records GCC
12.2.0, binutils 2.40, exact tool hashes, source, patchset and configuration.

| Identity | Result |
| --- | --- |
| Release | `7.3.0-rc1-mt6797-provider-compile` |
| Package inventory SHA-256 | `600e586a6a4559dac20ecd807c1dbb7348aff31576ab83d4741a046f9ffeea5e` |
| Ordered patchset SHA-256 | `60359786b91f96abde693f4397e95af3930ed22e2641c04a1a28897767b4dafb` |
| Resolved configuration SHA-256 | `3910887ce880cc55ab561819ec368756aaecf032663464d009ebea484b9af06d` |
| Image.gz SHA-256 | `675a5eaa9cbdcbbd02cff62f09678dbc9e7cc73e668001009c6e3060098cf9d4` |

The [package review](results/provider-compile-7029b136/package-review.json)
verified all 128 original [inventory members](results/provider-compile-7029b136/SHA256SUMS)
and all enabled/disabled configuration predicates. The inventory is package-relative,
not relative to this review directory; the kernel package remains ignored.

A separate [backend metadata review](results/provider-compile-7029b136/backend-review.json)
held the existing shared lock and verified the prepared source-tree integrity,
both exact patched-file hashes, all eleven ARM64 relocatable objects and their
command-record hashes. The two modified objects reference real genpd, regulator
and reset/provider functions, and those functions are defined in the linked
kernel. No warning/error diagnostics were found in the bounded build log.
Only metadata was returned; no source/object tree was fetched.

This establishes compilation and linkage on the selected source/configuration.
It does not execute provider registration, reset-failure cleanup, domain
withholding or CONN transitions in a kernel. Prior actual-C host fixtures retain
their narrower scope. No device access, QEMU run, new schema execution, boot
container or hardware-support promotion occurred. The one source state, build
and validated package remain retained for open provider review; the older
six-patch source and package are unchanged.
