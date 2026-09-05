# Repository instructions

## Purpose

This repository is the reproducibility and patch layer for bringing the Gemini
PDA to upstream Linux. Do not vendor a Linux tree here. Store reviewable patches,
configuration, safe tooling, hardware knowledge, and reproducible evidence.

## Before changing anything

- Read `docs/SAFETY.md`, `CONTRIBUTING.md`, and `docs/ARCHITECTURE.md`.
- For kernel work, also read `docs/KERNEL_WORKFLOW.md`.
- Preserve unrelated user changes; the worktree may be intentionally dirty.
- Treat historical or vendor material as evidence, not code to copy.

## Required workflow

- Pin upstream inputs in `kernel/manifest.json`.
- Store `git format-patch` files below `patches/` and order them in
  `patches/series`; keep one logical upstream change per patch.
- Treat every manifest-selected `patch_series` as requiring a canonical-order
  subsequence of `patches/series`. Audit all profiles whenever the manifest or
  any series changes; do not introduce a new violation. Profiles already
  quarantined by the active invariant audit remain historical-only and cannot
  be used as a new foundation while Roadmap gate 0 removes or repairs them.
- Add reusable board options to `configs/gemini.fragment`; keep intentionally
  isolated experiment policy in a named profile fragment and pin that profile
  in `kernel/manifest.json`.
- Keep document ownership strict: experiments own exact chronology, candidate
  identities, audit counts, and rejected branches; `docs/hardware/` owns
  durable facts; `docs/HARDWARE_SUPPORT.md` owns concise current support; and
  `docs/ROADMAP.md` alone owns ordered next steps. Link across those boundaries
  instead of copying point-in-time findings or remediation checklists.
- Build kernels with `./scripts/build-kernel --backend buildbox`. Do not use
  the native VM kernel-build backend unless the owner explicitly requests that
  specific build. If buildbox is unavailable, defer the build and report it;
  do not allow the `auto` backend to fall back to the VM. `GEMINI_BUILD_BACKEND`
  remains available for an explicitly owner-requested override.
- The buildbox workflow is Git-based. Before submitting a buildbox build,
  commit the intended changes, push that commit to `origin`, and leave the
  worktree clean. Buildbox fetches and builds that exact commit in its own
  managed kernel checkout. Never copy or synchronize a source tree to or from
  buildbox with `scp`, `rsync`, shared mounts, archives, or similar mechanisms.
- Repository commit signing is not a Buildbox gate. If signing is unavailable,
  create the required commit with `--no-gpg-sign`, push it, and continue; do not
  pause for a signing prompt or signing-agent recovery. This does not add or
  waive an upstream DCO `Signed-off-by`, which remains governed separately by
  the authorship rule below.
- After a successful buildbox build, fetch only its validated package with
  `./scripts/buildbox fetch-package`. Local exports belong below the ignored
  `artifacts/buildbox/<commit>/` tree. See `docs/BUILDBOX.md` for setup,
  diagnostics, backend selection, and recovery commands.
- Generated Linux sources and build directories belong on the selected build
  backend, not in this repository. Do not use `./scripts/dev-vm build-kernel`
  or `./scripts/build-kernel --backend vm` without an explicit owner request.
  Normal builds use the explicit buildbox backend so its provenance checks are
  retained and no automatic native fallback occurs.
- Reuse the managed prepared kernel tree whenever its recorded source state
  matches. Do not create experiment-specific source-root copies merely to get a
  fresh build; use a separate out-of-tree build directory when independence
  requires it, and remove that build directory after its result is recorded.
- “Latest kernel” means the boot candidate explicitly selected for the active
  experiment after package, checksum, LK-container, and experiment-specific
  validation—not the newest file by timestamp or a compile-only artifact.
- Before any device boot, state the kernel/DT/configuration hypothesis, the
  unique attributable evidence, and how each result changes the next action.
  Do not repeat an identical artifact unless repeatability is itself the
  hypothesis and a new measurement can distinguish the outcomes.
- Do not spend a device boot on a kernel/DT/config-identical derivative unless
  it adds a durable independent observation path with a decision-changing
  result; marker text alone is insufficient.
- A compile result is not hardware support. Update `docs/HARDWARE_SUPPORT.md`
  only from reproducible evidence on a named device and exact revision.
- Before upstream submission, patch author metadata must identify the actual
  author. Add a DCO `Signed-off-by` only when that person can truthfully make
  the certification; never invent a certifying identity or sign-off. An
  experiment-only archive may retain a clearly synthetic, non-certifying
  `From:` identity only when it has no synthetic sign-off and remains
  explicitly not submission-ready.

## Progress while the owner is unavailable

- Owner absence blocks physical boot selection, not independent research,
  implementation, review, host tests or authorized Buildbox work. Finish a
  bounded handoff for a waiting item and take the next ready offline item from
  `docs/ROADMAP.md`; do not leave every worker waiting for the same device.
- Prepare experiments through reproducible candidate construction, validators,
  refusal fixtures, evidence capture, classification and recovery instructions
  before requesting an owner session. Keep preparation readiness separate from
  physical admission in `project/experiment-queue.json`.
- Exact candidate identities, dependencies, action budgets, owner instructions
  and pass/fail/inconclusive branches belong in the owning experiment. The
  queue links to those records; the roadmap alone orders work.
- Several experiments may be prepared, but only one candidate may be selected
  for deployment at a time. Existing standing boot2 authorization is unchanged;
  physical selection remains the owner's action and never becomes an automatic
  reboot or a blind batch of queued tests.
- A candidate or protocol change, withdrawn prerequisite, consumed observation
  budget or superseding result invalidates the affected readiness claim. Review
  each result before admitting dependent work; independent offline work continues.
- On the owner's return, provide one concise session plan with the next exact
  physical action, expected behavior, required interaction and stop conditions.
  Reuse a boot for compatible tests only when their combined effects and budgets
  were reviewed in advance. See `docs/ROADMAP.md#owner-away-progress`.

## Storage stewardship

- Treat SSD space as a shared, finite development resource. Check host and VM
  free space before work that will extract a source tree, create a clean build,
  reproduce a package, or capture a device partition.
- Keep the VM provisioned and ready, but lean: normally retain one prepared
  copy of each source state still in use, the active build directories, and the
  exact packages or candidates still needed by an open experiment.
- Prefer reconstruction from pinned inputs over retaining regenerable copies.
  Once checksums, provenance, and decision-relevant evidence are recorded,
  remove superseded source trees, build directories, packages, exports, and
  failed candidate staging directories from both guest and host.
- A reproducibility run does not automatically require another source
  extraction. Share the verified prepared source and use an independent
  out-of-tree build directory unless source extraction itself is part of the
  claim. Remove temporary independent trees after the comparison.
- Do not duplicate a retained artifact between the VM and host without a
  concrete transfer, recovery, or test need. Prefer the bounded
  `export-artifact` workflow over exporting the complete guest artifact tree.
- Temporary files and directories must be created below an explicit managed
  root and removed on both success and failure. Scripts must install cleanup
  traps immediately after creating temporary state and must clear stale
  partial state safely on the next run.
- Distinguish regenerable build data from irreplaceable private evidence.
  Partition backups, calibration-bearing captures, credentials, and unique
  runtime evidence are never opportunistic cleanup targets. Remove them only
  after their identity, required retention, and verified replacement or
  independent backup have been reviewed.
- Be proportionate: avoid duplicate multi-gigabyte trees and unbounded
  timestamped outputs, but do not spend engineering time shaving small caches
  or deleting useful active state without a meaningful storage benefit.

## Hardware and reverse engineering

- Record durable hardware facts in `docs/hardware/` with variant, source,
  confidence, method, contradictions, and links to supporting experiments.
- Put each investigation in `experiments/<date>-<name>/`; start from
  `experiments/TEMPLATE.md` and keep its scripts/source beside the write-up.
- Distinguish observation from inference. Record negative and inconclusive
  results; never silently promote a guess to a fact.
- Reuse an upstream driver only when the observed chip identity, register
  protocol, transport, and resource contract match. If the chipset differs,
  select another matching family driver or add a new driver/binding; do not
  make the closest driver emulate the vendor ABI.
- Redact serials, IMEI values, keys, calibration data, credentials, and personal
  identifiers. Do not commit firmware, partition dumps, proprietary source or
  documents, or other material without verified redistribution rights.
- Use `scripts/extract-device-userspace --target USER@HOST` only for private
  local analysis. Its output must remain under a Git-ignored, access-restricted
  path and must never be staged without a file-by-file license review.
- Use `scripts/backup-device-mmc --target USER@HOST --dry-run` to inventory
  partition labels. Pass `--layout-config FILE` to reuse a MediaTek flash
  layout's logical names. A real all-partition read requires explicit
  `--all --confirm-read`; keep its raw output under the Git-ignored,
  access-restricted `artifacts/device-partitions/` path and never stage it.
  `scripts/rename-device-mmc` migrates older captures whose filenames lack
  logical names.
- For device access, prefer the mode-0600, Git-ignored local key at
  `artifacts/credentials/gemini_ed25519`. Its recovery source is the 1Password
  item `codex-gemini-192.168.1.50`; use `IdentitiesOnly=yes` and
  `IdentityAgent=none` to avoid transient agent failures. Never print or commit
  the private key.
- Treat Gemian LAN SSH and mainline USB SSH as separate access paths. A missing
  USB network interface or route does not establish that Gemian SSH is unavailable.
  When the owner asks to check SSH, use the usual known-good Gemian endpoint for
  a bounded authenticated OS/boot-identity check before requesting a physical
  action. Choose subsequent probes from the observed live OS; do not infer boot2
  identity from a relayed screen/boot report or retry an observer blindly.
- Run `./scripts/dev-vm re-shell` for binary analysis. Treat
  `~/reverse-engineering/gemini-vendor` as immutable evidence and store Ghidra,
  Radare2, and other analysis databases in guest-owned work directories.

## Standing Gemian inspection and private reverse engineering

- The owner authorizes analysis of the existing private firmware, partition and
  userspace captures and read-only inspection of the running known-good Gemian
  Linux system. Reuse the retained captures; keep raw bytes, analysis databases,
  credentials and calibration private under the existing storage/redaction rules.
  Use the RE VM for binary analysis, never as an automatic kernel-build fallback.
- The owner accepts locally supplied retained binary firmware as a development
  and device-test path. Fully open replacement firmware is not a prerequisite
  for upstream host support. Keep exact blob identities and standard loading
  contracts; unresolved redistribution alone does not stop private analysis or
  otherwise admitted local testing. Do not commit or bundle a blob without
  verified rights, and do not treat abandonment as a redistribution license.
- The owner also authorizes return from a completed, attributable mainline
  session to Gemian using the reviewed native recovery path. One named device
  custodian must preserve pending unique evidence, verify the live release,
  boot identity and required recovery-tool identity, then confirm changed-boot
  known-good Gemian before probing. Do not interrupt an active experiment or
  guess bootloader controls. An unavailable or mismatched path is a refusal.
- Verify actual bindings, power/resource ownership and firmware activity in
  Gemian; a vendor OS boot does not prove every device is active. Prefer bounded
  reads of documented interfaces. Radio actions, debug ioctls, calibration,
  resource writes and consuming observers require their own admitted protocols.
- This inspection authorization does not select boot2 automatically, waive the
  post-install shutdown rule, or add partition/firmware write authorization.
  Coordinate all live access through the single device custodian and publish
  only sanitized facts and independently reviewed reusable code with verified
  source rights. Host-driver licensing and firmware rights are separate audits.

## Safety and validation

- Never add a default action that writes the preloader, NVRAM, GPT, or an entire
  device. Hardware-writing operations require an explicit target and opt-in.
- The owner gives standing opt-in to install the latest validated boot
  candidate to logical `boot2` whenever the named Gemini is reachable in its
  known-good OS; no new prompt is required. Resolve `boot2` from the live GPT
  each time—never assume a partition number—and proceed only when it is not the
  active root or mounted, the target identity/size/writable state is exact, and
  power is stable. Skip the write when its full-partition checksum already
  matches. Otherwise record the predecessor checksum but do not create a fresh
  partition backup solely for the write; recovery relies on the verified
  project-wide device backup captured at project start. Verify the candidate
  fits, pad it to the exact target size, write, sync and flush, then require a
  matching full-partition readback checksum and record the result. After a
  verified write, shut down the device cleanly so the owner can physically
  select `boot2`; never reboot it automatically. If unavailable or any check
  fails, defer and report; never substitute another partition. This
  authorization does not cover primary `boot`, `boot3`, preloader, NVRAM, GPT,
  or whole-device writes.
- Prefer read-only probes, bounded operations, and dry-run defaults.
- Recover Candidate L ramoops evidence with
  `scripts/collect-device-pstore --target USER@HOST --wait-for-cycle`; add
  `--ask-sudo-password` when sudo is not passwordless. The helper requires a
  confirmed disconnect, reconnect, and changed boot ID and never removes remote
  pstore records.
- The owner gives standing authorization to commit and push sanitized device
  deployment and runtime evidence to `origin/main` at
  `https://github.com/ixoo/gemini-pda-mainline.git` without another prompt.
  This includes boot IDs, partition device names and labels, artifact and
  partition checksums, kernel identities, power state, serviceability results,
  and bounded hardware/runtime counters. Verify the exact `origin` URL before
  each push. This authorization does not cover credentials, keys, serials,
  IMEI values, calibration data, personal identifiers, raw partition contents,
  proprietary material, or unsanitized private evidence; those remain excluded
  under the repository's existing review and redaction rules.
- Run `bash -n` and ShellCheck for shell changes, `git diff --check`, the relevant
  kernel checks, and the smallest meaningful build through
  `./scripts/build-kernel --backend buildbox`. Run a VM kernel build only when
  the owner explicitly requests it. Document what was and was not tested.
- Before commit or push, inspect the exact staged file list and run
  `git diff --cached --check`. Include new files in syntax, link, license, and
  sensitive-data checks; reject credentials, proprietary inputs, raw artifacts,
  and personal absolute host paths. Confirm that no path below `artifacts/` is
  staged and that no unreviewed unstaged or untracked residue is being omitted
  from an all-worktree commit.
