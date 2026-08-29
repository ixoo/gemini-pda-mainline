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
symbol maps and output hashes plus all observer stack-usage reports. The Linux
stack-report tree is nested in a checksum-covered tar archive with NUL-safe and
readable member manifests so case-distinct filenames survive extraction on a
case-insensitive host. These are compiler and timing-review inputs only;
neither output is a boot candidate.

## Mainline Gate-6 patch-generation lanes

The mainline I2C6 short-write transport and DA921x same-value-write experiments
have separate patch-review lanes:

```sh
./scripts/buildbox generate-i2c6-write-transport-patches
./scripts/buildbox fetch-i2c6-write-transport-patches
./scripts/buildbox generate-da921x-same-value-write-patches
./scripts/buildbox fetch-da921x-same-value-write-patches
```

Each lane requires an exact clean pushed project commit, validates the managed
Linux source state and parent-file checksums, generates normal format-patches
with a synthetic non-certifying identity, replays them, and runs source and
strict style gates. Fetch transfers only the checksum-covered patch review and
provenance. These lanes do not compile a kernel, create a boot candidate,
access the Gemini, or authorize a physical I2C transaction.

## Mainline Gate-7 A34 evaluator patch-generation lane

The hardware-free A34 eligibility evaluator is generated only from the exact
clean, pushed project commit:

```sh
./scripts/buildbox generate-a72-a34-eligibility-patch
./scripts/buildbox fetch-a72-a34-eligibility-patch
```

The raw MediaTek watchdog boot-status capture uses the same clean, pushed,
Git-pinned generation contract:

```sh
./scripts/buildbox generate-mtk-wdt-boot-status-patch
./scripts/buildbox fetch-mtk-wdt-boot-status-patch
```

The pure retained ram-console parser also uses that contract and produces one
parser-only patch review:

```sh
./scripts/buildbox generate-mtk-ram-console-parser-patch
./scripts/buildbox fetch-mtk-ram-console-parser-patch
```

It returns one checksum-validated patch review and never copies a kernel source
tree between the host and Buildbox.

The MT6797 A72 platform-state source uses the same contract and generates four
logically separated patches: the locked TOPRGU reset-status accessor, binding,
default-off capture source, and disabled DT description:

```sh
./scripts/buildbox generate-mt6797-a72-platform-state-patches
./scripts/buildbox fetch-mt6797-a72-platform-state-patches
```

The lane verifies the exact canonical source through patch `0307`, replays the
four generated patches, and rejects polling, hardware writes, A34 callers, CPU
operations, and DT enablement.

The DA921x provider-state export follows the platform-state source and
generates three logically separated patches for the platform-private registry
ABI, the stable read-only DA921x callback, and its hardware-free KUnit proof:

```sh
./scripts/buildbox generate-da921x-provider-state-patches
./scripts/buildbox fetch-da921x-provider-state-patches
```

The lane pins every edited file, takes two immediate five-register samples
under one root-adapter lock with retries disabled, and rejects writes, delays,
loops, A34 callers, CPU operations, or device actions. Generation does not
contact the Gemini.

The follow-up read-only snapshot separation uses the canonical through-`0347`
tree and generates only the provider factoring patch plus its isolated test:

```sh
./scripts/buildbox generate-da921x-readonly-snapshot-patches
./scripts/buildbox fetch-da921x-readonly-snapshot-patches
```

This lane requires the positive provider transaction and firmware-writer
transaction window to remain unselected. It validates all ten negative and
short read ordinals and all five second-sample mismatches without a physical
adapter, build candidate, or device action.

The staged Phase B physical-source observer follows canonical patch `0349` and
generates five logical changes for retained attribution, the temporary direct
source, its binding, a separate candidate DT, and injected tests:

```sh
./scripts/buildbox generate-a72-physical-source-patches
./scripts/buildbox fetch-a72-physical-source-patches
```

The lane pins the exact prepared source, replays the generated series, and
rejects provider transactions, publisher calls, owner mutation, CPU requests,
and synthetic sign-offs. It creates only a patch review; compilation and the
no-network KUnit run occur after canonical admission, and device deployment is
a later separately gated step.

If that KUnit run exposes a stack-only fixture defect, its pinned test-only
follow-up is generated and fetched with:

```sh
./scripts/buildbox generate-a72-physical-source-stack-fix
./scripts/buildbox fetch-a72-physical-source-stack-fix
```

This lane accepts only the exact managed source through `0354`, changes only
the physical-source KUnit file, and proves that the two large direct-state
fixtures use KUnit-managed allocation. It changes no production source and
performs no hardware or device action.

Candidate admission subsequently found the corresponding large production
probe result still declared on the kernel stack. Generate and fetch its pinned
one-file repair with:

```sh
./scripts/buildbox generate-a72-physical-source-production-stack-fix
./scripts/buildbox fetch-a72-physical-source-production-stack-fix
```

This lane accepts only the exact managed source through `0355`, changes only
the physical-source production observer, requires one `kvzalloc_obj`/`kvfree`
pair around the existing transaction, and adds no hardware or device action.

The runtime-rejected physical-source path has two later retained-boundary
generation lanes. The historical pre-capture lane generated canonical patches
`0357`--`0359`; its current successor pins the exact managed source through
`0359` and moves the two records to built-in init before registration and first
probe entry:

```sh
./scripts/buildbox generate-a72-physical-source-init-probe-ledger
./scripts/buildbox fetch-a72-physical-source-init-probe-ledger
```

The successor changes only Kconfig help, the two record identities, and the
observer init/probe call sites. Its enabled path returns before allocation or
source lookup and performs no physical snapshot, provider transaction,
publication, owner mutation, CPU request, candidate construction, or device
action.

The later global-initcall and early-initcall successors each have their own
one-patch generation lane:

```sh
./scripts/buildbox generate-a72-global-initcall-ledger
./scripts/buildbox fetch-a72-global-initcall-ledger
./scripts/buildbox generate-a72-early-initcall-ledger
./scripts/buildbox fetch-a72-early-initcall-ledger
```

The early lane pins the exact managed source through `0361`, moves the primary
records to pure and core initcalls, and permits one separately gated record-2
refusal marker only after the pure checkpoint fails. Both lanes suppress
observer registration and add no source, provider, owner, CPU, candidate, or
device action.

The first physical-read discriminator has a separate four-patch generation
lane:

```sh
./scripts/buildbox generate-a72-platform-snapshot-patches
./scripts/buildbox fetch-a72-platform-snapshot-patches
```

It pins the exact managed source through canonical patch `0362`, brackets one
platform-state snapshot with two retained records, and generates the one-shot
observer, binding, and four injected tests. The admitted runtime path performs
exactly one fixed two-sample snapshot (26 read-only register observations), no
retry, and no DA921x, protected-clock, BigiDVFS, publisher, owner, or CPU
operation. Patch generation itself compiles no kernel, constructs no boot
candidate, and performs no device action.

The protected-clock first-dmesg call discriminator also has a source-review
lane:

```sh
./scripts/buildbox generate-protected-clock-first-dmesg-call
./scripts/buildbox fetch-protected-clock-first-dmesg-call
```

It pins the exact prepared source through canonical patch `0335`, relocates the
existing clock-only observer's two retained call checkpoints to first-dmesg
records 1 and 2, replays the resulting format-patch, and runs source and strict
style validation. The lane adds no writer or call site, compiles no kernel,
constructs no candidate, and performs no device action.

The closed A72 direct-state compositor has a separate hardware-free review
lane:

```sh
./scripts/buildbox generate-a72-direct-state-compositor
./scripts/buildbox fetch-a72-direct-state-compositor
```

It pins the prepared source through canonical patch `0336` and generates a
core patch plus its focused injected KUnit suite. The core holds the Linux
CPU-hotplug read lock and the A72 transition lock around one complete source
record, rejects every partial record with an all-zero result, and requires the
owner to remain pristine `CLOSED / UNINITIALIZED`. It calls no physical reader,
opens no lifecycle, and performs no hardware or CPU operation.

The audit-selected A34-v2/P30-interlock successor is also generated only from
the exact clean pushed repository commit and the managed source through patch
`0341`:

```sh
./scripts/buildbox generate-a34-v2-interlock
./scripts/buildbox fetch-a34-v2-interlock
./scripts/buildbox generate-a72-atomic-publication
./scripts/buildbox fetch-a72-atomic-publication
```

That lane creates three normal patches for the pristine P30 claim,
direct-state ABI 2 target identity, and the pure A34-v2 evaluator. It requires
exact replay and strict checkpatch, and transfers only the checksum-covered
review package. It adds no production caller, physical source binding,
lifecycle publication, CPU request, boot candidate, or device action.

If the exact compile exposes the known C tag-namespace collision in the first
admission, generate and fetch the single mechanical record-tag correction from
the prepared source through patch `0314` with:

```sh
./scripts/buildbox generate-da921x-provider-state-tag-fix
./scripts/buildbox fetch-da921x-provider-state-tag-fix
```

That lane permits only the thirteen `struct` tag renames across the public
record, registry, provider, and KUnit source. It preserves the existing
lifecycle enum and changes no behavior.

After canonical admission, compile and fetch the isolated focused profile with:

```sh
KERNEL_PROFILE=mt6797-a72-platform-state-source ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-a72-platform-state-source ./scripts/buildbox fetch-package
```

The corresponding parser-only compile and fetch commands are:

```sh
KERNEL_PROFILE=mtk-ram-console-parser-kunit ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mtk-ram-console-parser-kunit ./scripts/buildbox fetch-package
```

Each lane verifies the managed Linux source state and every edited parent file,
generates one normal `git format-patch` with an explicitly synthetic,
non-certifying experiment author, replays it, runs source and strict style
validation, and exports only its checksum-covered patch review and provenance.
The generation lanes do not compile a kernel, install a boot candidate, access
the Gemini, open the A72 lifecycle owner, perform a hardware action, or issue
`CPU_ON`/`CPU_OFF`.

## Gemian pre-isolation rollback patch-generation lane

The first Gate 4 rollback discriminator has a separate source-preparation lane:

```sh
./scripts/buildbox generate-gemian-rollback-patches
./scripts/buildbox fetch-gemian-rollback-patches
```

Like every Buildbox workflow, it requires a clean pushed commit and fetches that
exact revision. It applies the seven validated observer patches to the pinned
public Gemian source, performs three deterministic and source-drift-checked
logical edits, commits them with a clearly synthetic non-certifying experiment
identity, and generates real `git format-patch` output on Buildbox. Static and
mutation validation must pass before the patch-review package is fetchable.

The lane transfers only the generated patches, provenance and checksums. Its
temporary vendor source is removed after generation; it does not compile a
kernel, construct a boot image, access the device, or authorize deployment.

## Gemian pre-isolation rollback compile-review lane

After the exact generated patch series is reviewed and tracked, its separate
compile-only comparison runs with:

```sh
./scripts/buildbox build-gemian-rollback-compile
./scripts/buildbox fetch-gemian-rollback-compile
```

The rollback tree is the seven-patch parent observer plus the three reviewed
rollback patches. Its baseline is the same seven-patch observer tree without
the rollback series. Both use the pinned live configuration, compiler, DCT
oracle, host compatibility flag, and target `-fstack-usage` flag. Validation
requires exact configuration deltas, byte-identical extracted diagnostics,
rollback-symbol presence only in the changed tree, and checksum-covered
case-preserving stack archives for both builds.

Prepared source trees are keyed by their recorded patchset identities. Reuse
requires both the input-identity marker and a recursively computed source-tree
integrity digest to match. The latter covers paths, file and directory modes,
regular-file contents, additions/removals, and symbolic-link targets while
excluding only the private Git metadata and the two root markers. Any mismatch
reconstructs the prepared tree from the pinned archive and ordered patches.
Out-of-tree build directories are removed after packaging. Provenance marks
the result `rollback-compile-review-only` and `boot_candidate=false`; neither
compiled output is a deployment artifact or permission to access the device.

## Gemian recovery-only patch-generation lane

The no-A72 watchdog/pstore prerequisite begins with a separate source-review
lane:

```sh
./scripts/buildbox generate-gemian-recovery-patches
./scripts/buildbox fetch-gemian-recovery-patches
```

It fetches the clean pushed project commit and pinned public Gemian source,
generates three deterministic commits with a synthetic non-certifying
experiment identity, and validates the exact CPU8/9 rejection, kicker-lock
handoff, TOPRGU reset-only owner, fixed timeout, terminal marker, and absence
of A72 operations or userspace controls. The fetched package contains only
patches, provenance, and checksums. It does not compile a kernel, construct a
boot image, access the device, or authorize deployment.

After the generated patches are reviewed and tracked, compile them against an
unpatched source baseline with:

```sh
./scripts/buildbox build-gemian-recovery-compile
./scripts/buildbox fetch-gemian-recovery-compile
```

This lane reuses the already validated pinned Gemian toolchain, performs two
full out-of-tree `Image.gz-dtb` builds, and requires exact configuration deltas,
identical extracted diagnostics, recovery symbols only in the changed build,
and checksum-covered stack-usage archives. Its package is compile-review-only
and is not yet a boot candidate.

## Gemian pair-v6 parallel-load compile-review lane

The bounded parallel disjoint-load child is compiled only after its generated
patch is reviewed and tracked:

```sh
./scripts/buildbox build-gemian-cpu9-parallel-compile
./scripts/buildbox fetch-gemian-cpu9-parallel-compile
```

This lane compares pair-v6 against the exact pair-v5 multiline parent with the
same pinned Gemian source, Stretch toolchain, normalized configuration, DCT
oracle, target stack instrumentation, and extracted diagnostics. Validation
requires the complete inherited symbol inventory in both builds; new parallel
callback and 64 KiB static working-set symbols only in the child; linked pair-v6
pass and fault terminals; emitted acquire/release barriers; non-identical
integration code; and bounded static stack reports (512 bytes for the callback
and coherency worker, 1,024 bytes for the complete terminal worker). Its
package is compile-review-only, never a boot candidate, and performs no device
action.

## Gemian scheduler-context patch-generation lane

The current scheduler-context successor is generated from the exact rejected
phase-attribution source only from a clean pushed commit:

```sh
./scripts/buildbox generate-gemian-scheduler-patches
./scripts/buildbox fetch-gemian-scheduler-patches
```

The lane reconstructs and validates the unchanged task-context and
phase-attribution patches, then changes only the parked-thread activation
contract from `wake_up_process()` to `kthread_unpark()`. It revises the
void-operation result and marker schema, validates the exact kernel kthread
lifecycle, rejects the fixed mutation set, proves byte equality after reverse
normalization, and exports one checksum-covered `0003` format-patch review.
After admission, regeneration additionally requires the exact tracked
three-patch series and byte-compares the regenerated `0003` with the admitted
patch. It performs no kernel compile, container construction, device access, or
partition action.

After the generated patch is reviewed and tracked, compile it against the exact
rejected phase-attribution parent with:

```sh
./scripts/buildbox build-gemian-scheduler-compile
./scripts/buildbox fetch-gemian-scheduler-compile
```

The compile lane reuses the pinned Gemian source, Stretch toolchain, normalized
configuration, DCT oracle, diagnostics comparison, and stack instrumentation.
It requires exact parent-versus-child create, park, unpark, wake, and stop call
targets; identical lifecycle-core, startup, and HPS sources; the revised
terminal and phase strings only in the child; and bounded task/coherency/
terminal stack use. The package is compile-review-only, never a boot candidate,
and performs no device action.

## Gemian same-version pmsg-witness generation lane

The observation-only child of the exact register-capsule source is generated
only from a clean pushed commit:

```sh
./scripts/buildbox generate-gemian-pmsg-witness-patch
./scripts/buildbox fetch-gemian-pmsg-witness-patch
```

It reconstructs the complete register-capsule parent, verifies four pinned
parent files, applies the bounded ramoops-only pmsg helper and three fixed call
sites, runs exact-reversal and negative-mutation validation, and returns one
checksum-validated patch review. It compiles no kernel, builds no boot image,
and performs no device action. The retained pmsg contract is valid only for the
same-layout Gemian-derived candidate and Gemian recovery pair, not for the
differently aligned mainline pmsg region.

## A72 platform/provider readiness repair generation

The deferred-bind repair is generated only from a clean pushed project commit
and the managed Linux 7.1.3 source pinned through canonical patch `0370`:

```sh
./scripts/buildbox generate-a72-platform-provider-ready-patches
./scripts/buildbox fetch-a72-platform-provider-ready-patches
```

The isolated lane verifies the exact prepared-source state and integrity plus
the four edited parent files. It emits three experiment-only format patches:
the production provider-ready gate, its required DT phandle, and the injected
not-ready test. Exact replay, source invariants, strict checkpatch, and package
checksums must pass before fetch. The lane performs no kernel compile, device
access, retained-RAM access, candidate construction, or partition action.

## A72 protected-clock third-reader generation

The isolated third reader is generated only from a clean pushed project commit
and the managed Linux 7.1.3 source pinned through canonical patch `0373`:

```sh
./scripts/buildbox generate-a72-platform-provider-clock-patches
./scripts/buildbox fetch-a72-platform-provider-clock-patches
```

The lane pins the exact platform, provider, clock, handoff, retained-ledger,
and public-interface inputs. It emits four experiment-only patches for the
two-record ledger, three-phandle binding, one-shot observer, and eight-case
hardware-free KUnit suite. Validation requires terminal no-retry behavior.
It also requires exact source order after the protected-clock call, exact
replay, strict checkpatch, and package checksums. It performs no kernel compile, device access,
retained-RAM access, candidate construction, or partition action.

## A72 CPU8 transition-executor generation

The first active CPU8 coordinator is generated only from a clean pushed project
commit and the exact managed Linux source through canonical patch `0383`:

```sh
./scripts/buildbox generate-a72-transition-executor-patches
./scripts/buildbox fetch-a72-transition-executor-patches
```

After the generated patches are reviewed and admitted to the canonical series,
compile and fetch the hardware-free focused profile with:

```sh
KERNEL_PROFILE=a72-transition-executor-kunit ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=a72-transition-executor-kunit ./scripts/buildbox fetch-package
```

This lane emits two experiment-only format patches: a default-off coordinator
whose operations are all injected, and its hardware-free KUnit suite. It
requires watchdog-first ordering, one CPU8 request, no CPU_OFF or retry, exact
pre-isolation rollback, and post-isolation power retention. Generation replays
the patches and runs strict Checkpatch, but does not compile a kernel, connect
any physical backend, access the Gemini, create a candidate, or write retained
memory.

## Gemini retained transition-ledger generation

The compact last-stage ledger follows the watchdog owner and is generated from
the exact clean, pushed tree through canonical patch `0387`:

```sh
./scripts/buildbox generate-gemini-transition-ledger-patches
./scripts/buildbox fetch-gemini-transition-ledger-patches
```

The lane emits one production-owner patch and one hardware-free KUnit patch.
It pins the exact pstore Kconfig, Makefile, and ramoops source, replays both
patches, and runs strict Checkpatch. Validation requires one retained zone,
two alternating CRC-committed copies, 19 updates for a complete nine-stage run
plus terminal state, zero production callers, and no physical retained-memory
access or device action.

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
