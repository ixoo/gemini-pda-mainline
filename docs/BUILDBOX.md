# Buildbox kernel builds

The x86_64 buildbox is the preferred kernel-build backend when it is reachable.
It fetches committed project inputs from the public repository, maintains its
own pinned Linux source archive and prepared tree, cross-compiles arm64 outputs,
and retains validated packages until an explicit fetch. No project checkout,
Linux source tree, build directory, cache, credential, or device evidence is
synchronized from the development Mac.

The local ARM64 VM remains an explicit supported backend and the independent
native-build reference.

## Selecting a backend

The normal entry point selects buildbox when its SSH endpoint, required tools,
writable workspace, and repository access are available. It falls back to the
local VM only when that availability probe fails:

```sh
./scripts/build-kernel
```

Select either backend explicitly when the distinction is part of an experiment:

```sh
./scripts/build-kernel --backend buildbox
./scripts/build-kernel --backend vm
```

`GEMINI_BUILD_BACKEND=auto|buildbox|vm` provides the equivalent environment
control. `KERNEL_PROFILE`, `BUILD_MODULES`, and `KERNEL_JOBS` retain their usual
meanings.

An available buildbox does not cause an uncommitted or unpushed checkout to fall
back silently to the VM. The remote build fails before submission so it cannot
test inputs different from the local worktree. Use the explicit VM backend when
an intentionally uncommitted compile check is required.

## Commit-based build contract

The buildbox backend requires:

1. a clean local worktree, including no untracked non-ignored files;
2. a checked-out branch with an upstream at the exact project `origin` URL;
3. local `HEAD` pushed to that upstream branch; and
4. a valid manifest profile and build controls.

The backend records the immutable commit before submission. Buildbox fetches
that branch into a persistent bare mirror, proves the fetched branch resolves to
the requested commit, and builds a detached clean checkout of that commit. The
branch name is transport information; the commit is the artifact identity.

Typical use is:

```sh
git commit
git push origin HEAD
KERNEL_PROFILE=PROFILE_NAME ./scripts/build-kernel
KERNEL_PROFILE=PROFILE_NAME ./scripts/buildbox fetch-package
```

The fetched package is written below the ignored path:

```text
artifacts/buildbox/COMMIT/PACKAGE/
```

Fetching refuses to overwrite an existing package and verifies the complete
packaged `SHA256SUMS` after transfer. Only the validated package is transferred;
remote sources, builds, caches, and checkouts remain remote and regenerable.

## Gemian observer compile-review lane

The fixed MT6797 A72 owner-observer experiment has a separate compile-only
Buildbox lane because its public Gemian 3.18 source and pinned Stretch
cross-toolchain are not inputs to the upstream 7.1.3 manifest:

```sh
./scripts/buildbox build-gemian-observer
./scripts/buildbox fetch-gemian-observer
```

It retains the same clean, pushed-commit and exact-origin gate. Buildbox fetches
the fixed public vendor commit, verifies the experiment's 39 exact Debian
snapshot packages by SHA-256, constructs an unprivileged relocatable GCC 6.3/
binutils 2.28 plus Python 2.7.13 environment, verifies the tracked DCT generator
produces a `cust.dtsi` whose sole wall-clock comment is normalized to the fixed
epoch text and whose remaining complete content matches the pinned checksum,
imports the hash-pinned live configuration, and permits
only `CONFIG_MTK_A72_TRANSITION_OBSERVER` absent-to-`y` plus the semantically
disabled `CONFIG_ANBOX` absent-to-explicit-`n` serialization to change. Its
fetched bundle is for
compiler, configuration, symbol, warning, and timing review. Provenance marks
`boot_candidate=false`; this lane does not construct an Android boot image,
write `boot2`, access the device, or authorize an A72 request.

Legacy host tools are built by the Buildbox system compiler with the sole
additional environment flag `HOST_EXTRACFLAGS=-fcommon`, reproducing GCC 6's
tentative-definition behavior required by the pinned DTC sources while still
allowing sub-Makefiles to append their local include flags. This flag never
enters target ARM64 compilation. The bundle records the host compiler identity
and the compatibility flag separately from the pinned target compiler.

The compile-review bundle also builds the exact unpatched vendor commit with
the same normalized live configuration, pinned toolchain, DCT oracle, host
compatibility flag, and target `-fstack-usage` diagnostic flag. Validation
requires byte-identical extracted warning/error sets and absence of observer
symbols from the baseline. It retains both configs, build logs, diagnostics,
symbol maps and output hashes plus all observer stack-usage reports. These are
compiler and timing-review inputs only; neither output is a boot candidate.

## Remote storage and concurrency

Buildbox uses its persistent home volume for the Git mirror, verified kernel
archive, and a bounded compressed 5 GiB ccache. It uses `/workspace` for
detached project checkouts, prepared Linux sources, out-of-tree builds, job
records, logs, and packages. Loss of `/workspace` therefore loses only
regenerable state.

A remote lock serializes kernel builds that share the managed source and build
roots. The default is 64 jobs; set `KERNEL_JOBS` explicitly for a recorded
benchmark or a deliberately different resource policy.

Inspect readiness without changing project or device state:

```sh
./scripts/buildbox doctor
```

## Toolchain and provenance

The shared kernel driver supports native arm64 builds and x86_64 builds using
an arm64 cross-toolchain. Every `make` stage receives the same resolved target
compiler and linker. The build-state identity includes builder architecture,
native-versus-cross mode, compiler target and version, and compiler/linker
binary hashes, so a toolchain change invalidates the out-of-tree build.

Packaged provenance additionally records the repository commit, clean-worktree
state, target and build architectures, ccache state, and exact compiler/linker
identities. A buildbox package still requires the ordinary package validator;
neither compilation nor validation is hardware evidence.

For a decision-critical candidate, retain the experiment's required independent
build or reproducibility oracle. The native VM remains available for that lane:

```sh
KERNEL_PROFILE=PROFILE_NAME ./scripts/build-kernel --backend vm
```

## Safety boundary

Buildbox has no device credentials and performs no candidate installation or
hardware writes. Candidate construction, pre-boot hypotheses, runtime evidence,
and guarded `boot2` deployment remain separate experiment-owned steps governed
by the existing safety policy.
