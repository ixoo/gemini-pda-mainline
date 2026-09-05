# Exact upstream KUnit profile proposal

## Admission boundary and inputs

[profile-proposal.json](profile-proposal.json) supplies the complete proposed
manifest entry, ordered six-patch inventory, fragment identity, preservation
oracle, QEMU contract and cache destination. It is a proposal inside this
experiment. Nothing here edits the manifest, `configs/`, `patches/`, a cache,
or device state. Project Planning retains admission and integration ownership.

The source tuple selects upstream commit
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c`, the existing verified gzip snapshot,
and archive root `linux-4d7d9486c04d917265f64c55bd23b2cc4fe7749c`. The source
version is `7.3-rc1`; `released=2026-09-05` records the snapshot commit date,
not a claim that the release-candidate tag was published that day. The global
7.1.3 tuple remains unchanged. The [archive receipt](results/upstream-archive.json)
and [generation receipt](results/coherent-topic-generation.json) remain the
identity authorities; no placeholder checksum or timestamp-selected file is used.

Proposed profile: `mt6797-infracfg-upstream-kunit`, base `allnoconfig`, with only
the proposed [fragment](upstream-kunit.fragment) copied into its named `configs/`
path after review. Its series selects only the six exact generated patches,
under the proposed `patches/upstream-4d7d9486/` directory. Preserve every patch
byte and its recorded digest, including the unsigned internal-review metadata.
They remain not submission-ready; this proposal invents no authorship or DCO.

| Order | Logical change |
| --- | --- |
| 1 | Generic SET/CLEAR reset bank/index refusal |
| 2 | Generic pure reset-translation KUnit tests |
| 3 | MT6797 reset IDs and infracfg binding requirement |
| 4 | Production MT6797 reset descriptor and provider registration |
| 5 | MT6797 pure descriptor/mapping KUnit tests |
| 6 | Existing MT6797 infracfg node exposes one reset argument cell |

Exact filenames and SHA-256 values are in the JSON, derived directly from the
six-patch generation receipt. Do not mix these patches with historical 7.1.3
integration repairs. No new Gemini DT or boot container is part of this profile.

## Minimal requested configuration and source evidence

The fragment requests serial output, MT6797 clock/reset production compilation,
and exactly the two KUnit suites. It excludes unrelated test suites, modules,
network, storage, USB, regulator, thermal, cpufreq, idle and suspend policy.
It has no initramfs; KUnit must finish and power off the virtual machine before
normal userspace startup. Configuration resolution and compilation remain
untested. Every explicit requested value must survive the normal builder's
`olddefconfig` and fragment validator; a dropped symbol blocks the build result.

Pinned source inspection establishes the following dependencies:

- `arch/arm64/Kconfig` selects AMBA, architectural timer, GIC, PSCI, common
  clocks and OF. There is no `ARCH_VIRT` option in this source's platform menu.
- MediaTek clock configuration depends on `ARCH_MEDIATEK || COMPILE_TEST`.
  `COMMON_CLK_MT6797` selects `COMMON_CLK_MEDIATEK`, which selects the reset
  framework. `MFD_SYSCON` selects MMIO regmap support. Both added tests depend
  on KUnit and remain behind that existing MediaTek menu dependency.
- `ARCH_MEDIATEK=y` is retained so the unmodified production `dtbs`/package path
  produces MediaTek DTBs, including `mt6797-evb.dtb` and `mt6797-x20-dev.dtb`.
  A `COMPILE_TEST`-only image would not supply that package inventory.
- PL011 console selects serial core console and earlycon; arm64 supplies AMBA.
  The upstream arm64 KUnit QEMU recipe uses `console=ttyAMA0`, `virt`, CPU `max`
  and `Image.gz`. PL010 is unnecessary for this proposed PL011 console.
- The executor accepts `kunit_shutdown=poweroff`, not `kunit.shutdown=poweroff`.
  This source also provides KUnit default-enabled, autorun and timeout settings.

The required architecture-selected symbols are listed separately in the JSON
and must be checked in the resolved config. `allnoconfig` plus these requests is
not a proof of a globally minimum config: platform defaults may add other clock
or pinctrl drivers. Review the complete resolved delta and all enabled KUnit
symbols before execution; do not silently broaden the two-suite test claim.
The source-read hashes are recorded in [the audit](results/profile-source-audit.json).
No source file was extracted to a persistent source tree during this inspection.

## Build and QEMU contract after admission

Only after reviewed source tooling, V4 freeze, exact patch/profile admission and
clean publication, use the normal explicit Buildbox workflow:

```sh
KERNEL_PROFILE=mt6797-infracfg-upstream-kunit ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-infracfg-upstream-kunit ./scripts/buildbox fetch-package
```

Freeze the exact revision through validated fetch. Require full package/source
provenance, both production object files and both test object files, all fragment
requests and required selected symbols. Derive and pin the actual release and
Image identity from that exact validated package before the runtime classifier
exists. Expected source version is 7.3-rc1; never substitute a local 7.1.3 compile.

The JSON proposes one QEMU run: TCG, `virt`, CPU `max`, two vCPUs, 512 MiB,
`Image.gz`, no network, disks, initramfs, or supplied MT6797 DTB. Use explicit
serial output and no monitor/display, a 45-second wall limit with five-second
TERM-to-KILL grace, and the pinned command line. QEMU generates its virtual DT.
No physical MT6797 device exists there; these suites test pure arithmetic and
descriptors, not live reset registration, reset pulses or hardware error paths.

Acceptance requires both exact suite names and all eight named cases once,
complete KTAP plans, no failure, skip, bailout, panic, oops or unexpected suite,
and successful QEMU exit from requested power-off. Timeout is a refusal even if
some tests printed success. Preserve the exact log and classify before any retry.
Implement the exact-package runner/classifier with refusal fixtures after the
package exists; this proposal is not an executable runner or test pass.

## Binding and DT validation targets

On the same managed source/build state, run `dt_binding_check` with
`DT_SCHEMA_FILES=clock/mediatek,infracfg.yaml`, then `dtbs_check` with the same
schema filter. Record the dtschema/tool identities and full relevant diagnostics;
exit status alone is insufficient because binding recipes can retain diagnostics
while continuing. Missing tools or output is a refusal, not a skipped pass.

Require both affected targets, `mediatek/mt6797-evb.dtb` and
`mediatek/mt6797-x20-dev.dtb`, to be built and validated. Both include
`mt6797.dtsi`. In each resulting DTB, find the unique node compatible with
`mediatek,mt6797-infracfg` and require `#reset-cells = <1>`. Check the new public
reset header exposes only the intended IDs, thermal 0 and PMIC-wrapper 1.
Distinguish unrelated existing diagnostics from new errors, with explicit
baseline evidence before any exclusion. No schema check has run yet.

## Preserve the sole V4 canonical consumer

Before appending the new six patches, freeze the existing complete canonical
series bytes into the proposed V4-specific series path and select it only for
`gemini-thermal-v4-corrected`. The JSON pins the old canonical-file checksum,
531 selected patches, 34 fragments and V4 effective-input fingerprint. This
series migration must precede the canonical append in the reviewed delta.

Use the existing 189-profile oracle before and after admission. Every old
profile, ordered patch path/byte sequence, fragment, base config, architecture,
source and default selection must remain identical. Only the new six-patch
profile is added. Validate every manifest-selected series against canonical
order. Keep the known V4 candidate and its completed runtime gate unchanged;
metadata freezing neither rebuilds it nor authorizes a repeat.

## One retained archive: read-only checks and proposed migration

The archive-adoption fields in the JSON pin the existing workspace-relative
source, normal builder-cache destination, byte count and complete digest. A
read-only metadata check found a regular source with one link, a real destination
cache directory, an absent destination, and **different filesystems**. No cache
was changed. A hard link or same-filesystem atomic rename cannot perform this
observed migration; do not let an unreviewed `mv` conceal a copy-and-delete.

At admission, the integrator should first revalidate those observations while
holding the normal Buildbox `build.lock` and the acquisition helper's
`.acquire.lock`, in that order. Verify source no-follow regular-file identity,
size and full digest; resolve the destination parent; inspect available space;
refuse symlinks, unexpected files, changed identities or an active build. A
matching destination can be reused only after a full digest/size check.

For the observed cross-filesystem case, the proposed single migration uses one
exclusive managed partial file in the destination cache. Budget one archive's
size plus headroom for the temporary second copy; do not redownload. Copy from
the verified source descriptor, hash the complete destination, flush/fsync it,
and publish without replacing an existing path. Reopen and rehash the published
file, record the new canonical location and both identities, and only then
remove the old public, regenerable archive. Fsync the affected directories and
verify the final state: one retained full archive, expected digest and size,
no partial, no old source copy. Preserve the historical acquisition receipt;
publish a separate migration receipt rather than rewriting its old path.

Any failure before destination verification preserves the original. A failure
after publication preserves both copies until the integrator reconciles their
identities; never delete a sole verified copy to satisfy a space target. A
subsequent run must classify its exact partial/published state before cleanup.
This protocol avoids permanent duplicate retention but necessarily has a bounded
transient second copy across filesystems. No migration helper or mutation is
admitted by this document alone.
