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
