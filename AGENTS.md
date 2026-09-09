# Repository instructions

Build maintainable upstream Linux support for the Gemini PDA. Keep this
repository a small patch, tooling and evidence layer; do not vendor Linux.

## Keep work simple

- Deliver the user's requested outcome and stop at that boundary. A pause stops
  work; a checkpoint or commit/push request does not authorize finishing
  unrelated or unfinished development. Clearly label incomplete checkpoints.
- Overengineering is prohibited unless needed to solve a concrete observed
  problem or explicitly requested by the user. Use the smallest correct change.
  Do not add speculative abstractions, frameworks, configuration, generic
  infrastructure, elaborate test harnesses or extra review stages.
- Explain the concrete need before adding significant complexity. Reuse existing
  tools. Resolve material uncertainty before implementation; stop repeating
  unsuccessful repairs when a different diagnosis is needed.
- Use focused tests and review proportional to the actual change and risk.
  Repeat broad checks only after relevant changes or new failures.
- Use the default harness behavior without project-specific agent routing,
  work contracts or workflow measurement requirements. Earlier agent-process
  records are historical, not instructions for new work.
- Preserve unrelated changes. Coordinate all live device access through one
  custodian.

## Project knowledge and reproducibility

- Read [safety](docs/SAFETY.md), [contribution rules](CONTRIBUTING.md) and
  [architecture](docs/ARCHITECTURE.md) before relevant changes. For kernel/build
  work also read [kernel workflow](docs/KERNEL_WORKFLOW.md) and
  [Buildbox](docs/BUILDBOX.md). Follow applicable technical and safety rules;
  the lightweight working policy above supersedes older process prescriptions.
- Pin upstream inputs in `kernel/manifest.json`. Keep one logical change per
  format-patch under `patches/`; every selected series must preserve canonical
  `patches/series` order. Audit profiles when changing manifests or series;
  quarantined historical profiles are not new foundations.
- Keep reusable board options in `configs/gemini.fragment`; isolate experiments
  in named profiles. Prefer standard upstream drivers and interfaces only when
  the observed chip protocol and resource ownership match.
- Build kernels with `./scripts/build-kernel --backend buildbox`. Commit and
  push intended inputs first and use a clean checkout. Never copy source trees
  to Buildbox or fall back to a VM build without an explicit owner request.
  Fetch only validated packages under ignored `artifacts/buildbox/<commit>/`.
- Reuse prepared sources and separate build outputs. Check free space before
  large operations; clean managed temporary and superseded regenerable data.
  Never opportunistically delete backups, calibration or unique runtime evidence.
- Experiments own chronology and exact evidence; `docs/hardware/` owns durable
  facts; `docs/HARDWARE_SUPPORT.md` owns demonstrated support;
  `docs/ROADMAP.md` owns priorities. Link rather than duplicate.

## Hardware and private evidence

- A build is not hardware support. Record observations, inference, negative
  results and limitations separately, with exact candidate and boot identity.
- Before a boot, state its hypothesis, unique observation and decision branches.
  Use the active experiment's validated candidate, never the newest timestamp.
  Do not repeat identical artifacts without a decision-changing measurement.
- Preserve unique evidence before recovery. Owner absence permits already
  authorized offline progress, not automatic physical selection or broader
  hardware actions. An explicit pause overrides continuation.
- Standing authorization covers bounded read-only Gemian inspection and private
  analysis of retained captures. Use the RE VM for binary analysis. Retained
  firmware may support private tests; redistribution rights remain separate.
- Verify live OS and boot identity. Gemian LAN SSH and mainline USB SSH are
  separate paths; check the known-good Gemian endpoint before declaring SSH
  unavailable. Prefer the ignored mode-0600 key
  `artifacts/credentials/gemini_ed25519` with `IdentitiesOnly=yes` and
  `IdentityAgent=none`; never expose it.
- Standing boot2 installation approval remains: resolve logical `boot2` from
  live GPT in known-good Gemian, use the reviewed device guard, verify identity,
  inactive/unmounted/non-root state, size, writability and stable power.
  Skip an already matching full-partition checksum; otherwise record predecessor,
  pad to exact size, write, sync/flush and require matching full readback.
  Rely on the verified project-wide backup; do not make a fresh backup solely
  for each write. Shut down cleanly after a verified write; the owner selects
  boot2 physically. Never reboot automatically or substitute another partition.
- Primary boot, boot3, preloader, NVRAM, GPT and whole-device writes are outside
  that approval. Radio actions, calibration and resource writes require their
  own admitted protocols. Follow the detailed safety rules for diagnostics.
- Return from a completed mainline session to Gemian is authorized only through
  the reviewed recovery path after preserving evidence and verifying live
  identity and recovery-tool identity; confirm changed-boot Gemian afterward.
  Ask the owner before restarting, including recovery, unless an actual urgent
  safety reason requires it. When waiting for owner input, wait; a completed
  test, timeout or logging deadline does not replace restart confirmation.

## Validation and publication

- Standing approval covers reviewed project code, patches, profiles, tooling,
  documentation and sanitized evidence to `origin/main` at
  `https://github.com/ixoo/gemini-pda-mainline.git`. Verify that exact URL before
  pushing. If commit signing is unavailable, use `--no-gpg-sign`.
- Run applicable repository and experiment checks, including
  `./scripts/check-repository` before publication, shell syntax/ShellCheck for
  shell changes, and relevant kernel/DT checks. Documentation-only changes need
  no kernel build. State what was and was not tested.
- Inspect the exact staged paths and diff; run `git diff --cached --check`.
  Include new files in applicable syntax, link, license and sensitive-data
  checks. Explain intentional exclusions from a checkpoint.
- Never commit artifacts, raw captures, firmware without redistribution rights,
  proprietary material, credentials, calibration, personal identifiers or
  personal absolute host paths. Sanitized boot IDs and deployment checksums
  remain publishable under standing approval.
- Vendor material is evidence, not automatically reusable code. Preserve source
  rights and actual authorship; never invent a DCO sign-off. Upstream submission
  requires truthful certification and the subsystem's normal review.
