# Pinned kernel patch workflow

This repository stores the ordered inputs needed to build an upstream-derived
Gemini kernel. It does not store a Linux source tree or generated build output.
Exact candidate construction and runtime history belong in the associated
[`experiments/`](../experiments/README.md) directory.

Read [SAFETY.md](SAFETY.md) before creating a device artifact or writing a
partition.

## One-command build

Use the explicit Buildbox entry point:

```sh
./scripts/build-kernel --backend buildbox
```

The default also selects Buildbox. An unavailable Buildbox stops the build;
`auto` never falls back to a VM. A native VM build requires an explicit owner
request for that build and explicit `--backend vm` or `GEMINI_BUILD_BACKEND=vm`.

Buildbox accepts only a clean, pushed commit and fetches it directly from the
project repository. See [Buildbox kernel builds](BUILDBOX.md) for the commit,
storage, immutable-package, fetch and provenance contract. Independent task
worktrees contain only this small patch repository, never Linux source copies.

Repository commit signing is not a Buildbox prerequisite. When the signing
agent or owner is unavailable, create the repository commit with
`git commit --no-gpg-sign`, push it, and continue the workflow instead of
waiting for signing. This unsigned repository commit does not create or waive
the separate DCO sign-off required for an upstream submission.

Both backends perform the same pinned workflow:

1. read `kernel/manifest.json`;
2. download the pinned kernel.org source archive into the guest cache;
3. verify the source SHA-256 before extraction;
4. reuse or prepare a guest-ext4 source tree keyed by the effective patch
   series;
5. apply the selected patches in canonical order;
6. start from the profile's arm64 base configuration and merge its fragments;
7. build `Image`, LK-compatible `Image.gz`, and arm64 DTBs out of tree;
8. package kernel forms, MediaTek DTBs, configuration, provenance, and
   checksums under `~/artifacts/gemini-pda/`.

The download, source, build, and package directories never live in the macOS
checkout. Print the VM paths with:

```sh
./scripts/dev-vm kernel paths
```

## Pinned inputs

`kernel/manifest.json` is the build authority for:

- kernel version, source URL, and source SHA-256;
- default configuration profile;
- each profile's base configuration and ordered fragments;
- an optional named patch-series subsequence for an experiment.

The manifest stays pinned until reviewed and changed in Git. Checking for a
newer kernel never changes build inputs:

```sh
./scripts/dev-vm kernel check-latest
```

In this project, “latest kernel” means the candidate explicitly selected for
the active experiment after source, patch, configuration, package, checksum,
LK-container, and experiment-specific validation. It never means the newest
file by timestamp or a compile-only package.

## Patch series

Author logical commits in a disposable Linux clone and export them with
`git format-patch`. Store patches below the pinned baseline:

```text
patches/
  series
  series-<named-experiment>
  v7.1.3/
    0001-arm64-dts-mediatek-add-gemini-pda.patch
    0002-clk-mediatek-add-required-clock.patch
```

`patches/series` is the canonical superset and ordering authority:

```text
v7.1.3/0001-arm64-dts-mediatek-add-gemini-pda.patch
v7.1.3/0002-clk-mediatek-add-required-clock.patch
```

Blank lines and lines beginning with `#` are ignored. The build rejects:

- missing or symlinked patch files;
- absolute, empty, `.` or `..` path components;
- whitespace in patch paths;
- a patch that does not apply cleanly.

A manifest profile may select a named canonical-order subsequence through
`patch_series`. This isolates an experiment without creating a second patch
history. Every selected patch must also appear in `patches/series` in the same
relative order.

Every manifest profile must be checked against this invariant, not merely
checked for an existing series file and applicable patches. The active
[profile-series invariant audit](../experiments/2026-07-28-profile-series-invariant-audit/README.md)
records the point-in-time result; do not select a profile it rejects.
Remediation order and exit criteria are owned by
[Roadmap gate 0](ROADMAP.md#0-repair-the-profile-series-invariant).

When the effective series changes, the next preparation replaces only its
generated guest source tree. Never make unique edits there. Export reviewable
patches from a separate clone and add them to this repository.

The source-state marker is the reuse contract. If it matches, use that prepared
tree for every compatible profile and build; do not copy it into a dated or
experiment-named source root. If a clean-room claim specifically includes
source extraction, create the extra tree explicitly, record why it is needed,
and remove it after the comparison.

## Kernel configuration

The default `full` profile uses `configs/gemini.fragment`. Put reusable board
options there with the patch that requires them.

Experiment-only policy belongs in a focused fragment and a named manifest
profile. Examples include probe-minimal handoff, USB gadget diagnostics,
observability, framebuffer rotation, keyboard, SMP-8, DVFSP/I2C6 ownership,
and the fixed board-contract diagnostic. A successful experiment profile does
not silently become the default profile.

Fragments are merged in listed order. A later fragment may intentionally
override an earlier diagnostic baseline, but the reason must be documented in
the experiment. `merge_config.sh` reports redundant or overridden values;
`olddefconfig` resolves dependencies; the repository validator checks the
requested values in the final resolved configuration.

The Gemini profiles intentionally omit unrelated host-oriented stacks when
needed to stay within the retained LK platform's fixed decompression budget.
That is a packaging constraint, not an arm64 upstream default.

Select a non-default profile explicitly:

```sh
KERNEL_PROFILE=PROFILE_NAME ./scripts/build-kernel --backend buildbox
```

Use the exact profile recorded by the experiment. Do not guess a similarly
named profile or edit a built package in place.

## Individual build stages

Use `./scripts/buildbox doctor` and the build log for normal diagnosis. Source
preparation, configuration and compilation use the managed Buildbox workflow.
The legacy `dev-vm kernel prepare/configure/build` and VM build shortcuts are
only for a specifically owner-requested native VM build; they are not a fallback
for an unavailable Buildbox or an intentionally dirty worktree.

## Storage lifecycle

The VM is a reusable tool, not an artifact archive. Keep it provisioned, along
with the verified download cache and prepared source states that are still in
active use. Before a large build or reproduction run, inspect free space and
the sizes of `~/src`, `~/build`, and `~/artifacts`.

Use these retention rules:

- reuse the prepared source selected by `./scripts/dev-vm kernel paths`;
- use an out-of-tree build directory for profile isolation or an independent
  build, rather than another source extraction;
- retain only build directories that are active, needed for a near-term
  incremental rebuild, or required by an unfinished comparison;
- retain the exact validated package and boot candidate named by each open
  experiment, not every intermediate or superseded timestamped directory;
- after recording provenance, checksums, and the comparison result, remove
  disposable reproduction trees, failed staging directories, superseded
  packages, and redundant guest/host exports; and
- keep the single verified source archive cache while its pinned version is in
  use, because redownloading it saves little space relative to repeated source
  extractions.

Independent builds require independent build outputs. They do not require
independent source copies unless the experiment explicitly tests extraction or
source preparation. Evidence needed to reproduce a result is normally the
pinned manifest, patch series, configuration, toolchain identity, provenance,
checksums, and focused runtime output—not a permanent copy of every generated
file.

Temporary paths created by kernel or candidate tooling must be cleaned on
success and failure. Install the cleanup trap immediately after creating the
path, reject unsafe cleanup targets, remove stale partial downloads or staging
directories on the next invocation, and never use a broad home, workspace, or
artifact root as a cleanup target.

Private device backups and unique hardware evidence follow a different
retention policy. Do not delete partition captures, credentials,
calibration-bearing data, or the only copy of runtime evidence as routine
space reclamation. Review their identity and backup status separately.

Set `BUILD_MODULES=1` inside a guest shell only when an experiment requires
modules. The package then stores them below
`modules/lib/modules/<release>/` and records `modules_built=true` in
`provenance/build.json`.

Linux builds both:

- `Image`, retained for inspection and standard loaders;
- `Image.gz`, required by the retained Planet LK 64-bit path.

The retained LK selects its 64-bit path from `bootopt`, scans the compressed
kernel payload for the appended DTB, decompresses the kernel, applies its DT
fixups, and enters Linux. A raw `Image` is not a valid payload for this
development LK contract.

## Package validation

Buildbox validates the selected package before publication. Fetch only its
validated package with the same explicit profile:

```sh
KERNEL_PROFILE=PROFILE_NAME ./scripts/buildbox fetch-package
```

For an explicit package inspection on a supported Linux builder, use
`./scripts/validate-kernel-artifact PATH` with the appropriate artifact root.
On macOS, the Buildbox fetch helper verifies the transferred inventory and
provenance; it does not run the Linux-only validator locally.

The validator checks:

- the complete `SHA256SUMS` inventory;
- required `Image`, `Image.gz`, DTBs, configuration, and provenance files;
- the manifest-selected effective series and exact patch inventory;
- source, patchset, profile, fragment, and resolved-configuration identities.

This is an integrity check. It does not prove that Linux boots or that hardware
works.

For high-risk or decision-critical candidates, the experiment must add:

- two independent builds or an equivalent reproducibility oracle;
- focused source, configuration, DTB, binary, and container checks;
- negative mutation tests for the safety boundary;
- a classifier for the exact runtime result;
- a pre-boot statement of hypothesis, unique evidence, and decision branches.

Timestamp-bearing provenance may differ only where the experiment explicitly
normalizes it. Substantive package, binary, DTB, initramfs, and container
content must match the experiment's declared reproducibility contract.

## Building an LK boot candidate

A kernel package is not a boot candidate. The retained LK requires an
Android-v0 container with pinned load addresses, a deterministic initramfs,
the selected DTB, and LK-specific validation.

Early reusable builders live with the handoff experiments:

- [LK handoff alignment](../experiments/2026-07-16-lk-handoff-alignment/README.md);
- [USB gadget diagnostic](../experiments/2026-07-16-usb-gadget-diagnostic/README.md).

Later candidates have purpose-built constructors and validators in their own
experiment directories. The experiment README is the authority for:

- exact baseline package and artifact identities;
- permitted kernel, DTB, initramfs, and header deltas;
- build command and output inventory;
- prohibited devices, subsystems, and hardware actions;
- mutation and result validators;
- whether the candidate is current, superseded, rejected, or closed.

Do not reproduce a candidate from prose in a general documentation file. Do not
boot an artifact whose experiment says it is superseded, rejected, unvalidated,
or closed to repetition.

The [experiment index](../experiments/README.md) identifies the latest
decisive result and owns all candidate-attribution details.

## Boot selection and device installation

Building and validating do not select a slot or write hardware.

Static analysis of the retained LK associates `boot2` and `boot3` with hardware
key paths and found no supported Gemian software destination for either. The
owner therefore selects `boot2` physically. Do not substitute kexec; it would
bypass required LK DT and reserved-memory fixups. See the
[boot-selection audit](../experiments/2026-07-12-boot-contract-recovery/results/lk-boot2-software-selection-audit-20260718.txt).

Any installation must follow [SAFETY.md](SAFETY.md) and the repository's
guarded `boot2` policy:

- resolve the logical label from the live GPT every time;
- prove the target is inactive, unmounted, writable, correctly sized, and not
  the active root;
- record the predecessor checksum, but do not create a fresh partition backup
  solely for the write; rely on the verified project-wide device backup
  captured at project start;
- pad only to the exact partition size;
- write, synchronize, flush, and require a full-partition readback match;
- never substitute `boot`, `boot3`, preloader, NVRAM, GPT, or a whole device;
- after a verified write, shut down cleanly so the owner can physically select
  `boot2`; never reboot automatically.

A partition checksum proves stored bytes, not selection or runtime execution.

## Runtime evidence

Before a device boot, the experiment must state:

1. the kernel, DT, configuration, and hardware hypothesis;
2. the unique evidence attributable to that candidate;
3. how each possible result changes the next action.

Do not spend a boot on a kernel/DT/config-identical derivative unless it adds a
durable independent observation path with a decision-changing result. Marker
text alone is insufficient.

Runtime claims must identify:

- named hardware and exact candidate;
- boot-selection and serviceability evidence;
- repetition count;
- observations versus inference;
- negative space;
- recovery outcome and post-cycle integrity where relevant.

Record those details under `experiments/<date>-<name>/`. Promote only the
bounded current conclusion to [HARDWARE_SUPPORT.md](HARDWARE_SUPPORT.md) or a
focused hardware document.

## Patch review

Run the pinned tree's review checker before treating patches as
submission-ready:

```sh
./scripts/dev-vm run \
  experiments/2026-07-14-patch-quality-audit/scripts/audit-checkpatch.sh
```

This is a review gate, not a build or hardware gate. Resolve Checkpatch, binding, provenance, authorship and sign-off issues in the
coherent upstream preparation series. Preserve historical experiment patch bytes
and their receipts; do not rewrite old evidence or mechanically replace an
author identity. Before upstream submission, author metadata must identify
the actual author and every sign-off must be a truthful DCO certification.
Never fabricate a certifying identity or sign-off. A clearly synthetic
`From:` identity is acceptable only for an unsigned internal experiment
archive that remains explicitly not submission-ready. The
[patch-quality experiment](../experiments/2026-07-14-patch-quality-audit/README.md)
contains detailed audit results.

## Local validation dependencies

The common gate requires Python 3, Git, Bash, jq, ShellCheck and PyYAML. Use an
ignored reusable environment rather than changing the system Python:

```sh
python3 -m venv artifacts/tooling/repository-checks
artifacts/tooling/repository-checks/bin/python3 -m pip install PyYAML==6.0.3
artifacts/tooling/repository-checks/bin/python3 scripts/check-repository
```

With those dependencies already installed, `./scripts/check-repository` is
equivalent. Linux CI supplies its own environment and runs the Linux-only
artifact-provenance fixtures. The gate reports any local skips explicitly.

## Repository publication gate

Before committing or pushing any repository change, including documentation:

Run `./scripts/check-repository` for the common offline gate; Linux CI also
executes the provenance fixtures that cannot run on macOS. This does not replace
experiment-specific tests, kernel/DT checks, Buildbox compilation or hardware
acceptance. Documentation-only changes do not need a kernel rebuild.

1. stage the intended scope and inspect the complete staged name/status and
   diffstat, including newly added files;
2. run `git diff --cached --check`;
3. validate every manifest-selected series as a canonical-order subsequence of
   `patches/series` with `./scripts/validate-manifest-series`, then run its
   focused mutation test with `./scripts/test-manifest-series-invariant`;
4. run Bash syntax and ShellCheck for every staged shell script, plus the
   applicable Python, C, binding, Device Tree, patch, link, and experiment
   contract checks;
5. scan staged text for credentials, private identifiers, proprietary material,
   and personal absolute host paths; use repository-relative paths or neutral
   role placeholders in published instructions; and
6. verify that no generated kernel package, boot image, partition capture,
   firmware, or path below `artifacts/` is staged.

Point-in-time validation output belongs in the associated experiment. Durable
documents retain only the current conclusion or invariant and link to that
record; ordered follow-up remains in the roadmap.

## Exporting artifacts

After reviewing the guest package or candidate:

```sh
./scripts/dev-vm export-artifacts
./scripts/dev-vm export-artifact boot-candidates/EXACT-DIRECTORY
```

The first command creates a timestamped, Git-ignored host copy of guest
artifacts. The second copies one exact path to `artifacts/vm-export/` and
refuses to overwrite it.

Verify checksums and provenance before any transfer or installation. Generated
kernel trees, packages, private device captures, credentials, raw partition
images, and proprietary firmware remain outside Git.
