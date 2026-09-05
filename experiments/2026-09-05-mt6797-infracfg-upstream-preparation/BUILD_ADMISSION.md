# Exact upstream reset test build admission

The integrator admits `mt6797-infracfg-upstream-kunit` for the explicit Buildbox
build after publication and verified archive adoption. It selects the complete
source tuple and six patch identities in [the proposal](profile-proposal.json).
This is a compile and virtual-test profile, not a Gemini boot candidate. No
device, boot2, upstream submission or hardware-support claim follows.

## Input review and preservation

Proposal `95ddbf35b62972bd3f5629594635fbaa5d16e022` passed coordinator and
independent review. The six retained format-patches match the generation
receipt byte-for-byte and retain clearly synthetic, non-certifying experiment
metadata with no sign-offs. Thirteen independently retrieved pinned upstream
files match the source audit and support the requested Kconfig dependencies,
two KUnit suites/eight named cases, QEMU poweroff parameter and both MT6797 DTBs.
Actual configuration resolution and compilation remain separate evidence.

The previously sole canonical consumer, `gemini-thermal-v4-corrected`, now
selects a byte-identical copy of its old series under
`patches/series-gemini-thermal-v4-corrected`. Its 531 patches and 34 fragments,
and all 189 existing profiles' effective inputs and default selection, remain
unchanged. The six upstream patches are appended to the canonical series and
selected only by the new profile. The all-profile invariant audit covers 190
profiles. This metadata freeze does not rebuild V4 or reopen its consumed gate.

The named configuration preserves every proposal request. Only its introductory
comment changes to identify an admitted Buildbox/QEMU test input. The proposal
fragment remains immutable; actual configuration and source/patch identities
are recorded by the normal package provenance.

## Cache and build boundary

Buildbox preflight passed. Host and running RE-VM storage each had approximately
87 GiB free; Buildbox reported 9.8 GiB available in its home filesystem and
268 GiB in the source/build workspace. No VM kernel build is requested or used.
The verified upstream archive is retained on Buildbox; the reviewed
[adoption helper](scripts/adopt-upstream-archive.py) performs the bounded
cross-filesystem migration under both locks before any source preparation.
It preserves a durable receipt before deleting the old public, regenerable copy.
Raw sources and archive bytes are never transferred to the host.

After the exact clean revision is committed and pushed, keep this checkout
frozen through the following build and validated fetch:

```sh
KERNEL_PROFILE=mt6797-infracfg-upstream-kunit ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-infracfg-upstream-kunit ./scripts/buildbox fetch-package
```

Retain package identity and failures in this experiment. Refuse unresolved
configuration requests or changed source/patch inputs. Reuse the managed
prepared source and profile build directory; do not create another source copy
for schema or QEMU work. A package is not a device candidate.

## Execution and upstream limits

The [proposal](PROFILE_PROPOSAL.md) owns the precise two-suite/eight-case QEMU
acceptance and both DT/schema targets. Implement and review the exact-package
runner/classifier with refusal fixtures before QEMU execution; enforce complete
KTAP, bounded runtime, successful poweroff and no unexpected suite or failure.
Record full schema diagnostics and tool versions; exit status alone is
insufficient. These pure tests do not exercise physical MT6797 reset pulses,
provider registration, unbind/rebind or a Gemini boot.

Status at admission: source/profile/series review complete; archive migration,
resolved config, kernel build, validated package, QEMU and schema results pending.
Actual author certification and upstream submission remain separate gates.

## Preparation validation

The common publication gate passed all 22 changed files and 190 manifest
profiles; the separate preservation oracle retained all 189 existing profiles.
The exact six-patch review package's complete inventory and hashes passed before
copying its patches into the canonical inputs. No author/sign-off bytes changed.

Independent review found no blocking defect in the fixed-path archive helper
(`17979a24f33f107f7f51d8ed3bc29655e0313d0f0b0b49c02333d47b4fc0896b`)
and its fixtures (`a59390515dac1a47761d97d12afe5674249e33d6e39c94ecdc3abaf97af2d97c`).
The final suite has 26 tests: 25 pass on macOS and one real cross-filesystem
fixture requires Linux. Ten real SIGTERM/SIGKILL interruption/recovery combinations
passed. Exact Linux fixtures and the production read-only check are required
before migration. These results do not claim actual archive movement or a build.

## Completed build and fetch

The exact clean, pushed revision
`4ec63076aeb6388ba24b33ee20afcf19ced541e1` completed the explicit Buildbox build
and validated package fetch. CI run `33965544268` also passed. The
[build receipt](results/upstream-build-4ec63076.json) records the full source,
toolchain, configuration, image and inventory identities. The checkout remained
frozen through fetch; no VM kernel build or device action occurred.

All 26 archive-adoption fixtures passed on Buildbox, including the real
cross-filesystem case. The production read-only check passed, followed by
successful migration of the 269,814,253-byte archive to the production
checksum-keyed cache. The helper verified the destination and wrote a durable
receipt before removing the old public archive. The
[sanitized result](results/archive-adoption-4ec63076.json) records one retained
copy, no stale partial and no source/archive transfer to the host. The retained
durable receipt was independently reread afterward.

The built release is `7.3.0-rc1-mt6797-infracfg-upstream-kunit`. All requested
configuration settings and all required dependency symbols survived resolution.
Both reset test suites are built in; their four production/test object files
were checked in the managed build directory. The package contains 118 MediaTek
DTBs, including both proposed MT6797 targets. These are compilation facts;
neither suite has executed and neither schema target has run at this point.

The validated inventory identity is
`8393a89ef3dbdb3bbae967d6adc78cf5a1cd907c21f21e9ba2efc015ba041917`.
The immutable package directory begins `linux-7.1.3-gemini-` because the publisher
used the global manifest version for its label. Its checked source tuple,
configuration and release correctly identify the admitted upstream build.
Preserve this original package and identity; correct future publication naming
without renaming or rebuilding this evidence. Consumers must verify provenance
and checksums rather than infer the kernel from that directory label.

Focused QEMU execution and DT/schema checks remain open under the protocol above.
The provider-failure follow-up and independent TOPRGU readiness assessment do
not alter this compiled six-patch input or select a device session.

## Post-build review and publication correction

The publisher now resolves the packaged build's selected source through the
shared source-provenance contract. The defect reproduces with the old publisher;
the corrected publication suite passes 21 cases, including the selected override,
legacy global and unprofiled inputs, malformed provenance refusals and unchanged
fetchability of the original mislabeled package. No existing artifact is renamed,
republished or rebuilt. Full Linux validator fixtures remain a CI check for this
tooling correction; the original kernel package already passed its Linux validator.

The [provider review](PROVIDER_FAILURE_REVIEW.md), adopted from `a5a3acf0`, passed
independent verification of all five pinned upstream files and all six patch
identities. Its probe/devres and retained-handle reasoning is source evidence;
no fault-injection, concurrent detach or full clock-driver lifetime test ran.
The separate [TOPRGU assessment](../2026-09-05-mt6797-toprgu-upstream-preparation/README.md),
adopted from `df489707`, likewise passed independent source/evidence review and
remains unready for submission. Neither changes the build's inputs.
