# Contributing

Thank you for helping make the Gemini PDA supportable by upstream Linux.

## Before starting

- Read [Safety and recovery](docs/SAFETY.md).
- Search existing issues and related projects before beginning driver work.
- Comment on the issue you intend to tackle so hardware access, dependencies, and upstream ownership are clear.
- For invasive or cross-subsystem work, open a research issue before writing code.

## Choose the correct contribution path

### Hardware research and documentation

State:

- exact Gemini variant and board identifiers, without publishing personal identifiers;
- evidence source: observed bus transaction, vendor DTS path, schematic fragment, boot log, or datasheet;
- whether a claim is inferred or confirmed on hardware;
- conflicting evidence and unresolved questions.

Do not copy proprietary documents or source code into this repository. Record facts, offsets, bindings, and independently written descriptions with a source reference.

- Put durable, provenance-backed facts in [`docs/hardware/`](docs/hardware/README.md).
- Put each reproducible investigation and its associated code in
  [`experiments/`](experiments/README.md), starting from the experiment template.
- Link experiment conclusions to the hardware document, support-matrix row,
  patch, and tracking issue they affect.
- Preserve negative and inconclusive results; distinguish direct observation
  from inference and secondary reports.

### Kernel and Device Tree work

The normal lifecycle is:

```text
research -> minimal local patch -> hardware evidence -> upstream review -> upstream merge -> delete local patch
```

- Base work on a named upstream tag or commit from an actively maintained kernel.
- Keep generic MT6797 support separate from Gemini board description.
- Use existing bindings and drivers where possible. New bindings must pass `make dt_binding_check`; Device Trees must pass `make dtbs_check` for the relevant files.
- Follow Linux coding style and run the relevant `scripts/checkpatch.pl` checks.
- Keep each commit reviewable and include the problem, hardware behavior, and test result in the commit message.
- Identify the intended upstream tree, maintainers, and mailing lists using the upstream `MAINTAINERS` file and `scripts/get_maintainer.pl`.
- Post patches upstream using the subsystem's current process. Link the public submission and record revisions in the tracking issue.
- Do not add proprietary kernel modules, opaque executable code, or blanket downstream driver drops.

Kernel contributions intended for Linux must use an upstream-compatible SPDX identifier and include a Developer Certificate of Origin sign-off:

```text
Signed-off-by: Your Name <you@example.com>
```

Use `git commit -s` only when you can truthfully make the certification described at <https://developercertificate.org/>.

### Tooling and reproducibility

- Pin external source revisions and verify downloads where practical.
- Keep build outputs outside the repository.
- Make destructive commands opt-in and require an explicit partition target.
- Default scripts to dry-run or read-only behavior when feasible.
- Never make preloader, NVRAM, GPT, or whole-device writes part of a default target.
- Document host dependencies and the exact generated artifacts.

## Test evidence

A hardware result should include:

- device variant;
- kernel commit and local patch-series revision;
- compiler and configuration identity;
- boot path and target partition/slot;
- complete relevant log, with secrets and identifiers redacted;
- expected and observed behavior;
- number of repetitions for reliability claims;
- regression result for already-supported subsystems.

Use `Tested-by` only for the exact revision tested.

## Pull requests

Pull requests are appropriate for project documentation, safe tooling, test fixtures, and temporary patch-series mirrors. A pull request is not a substitute for upstream kernel submission.

- Keep the scope focused.
- Link the tracking issue and upstream submission where applicable.
- Explain how to reproduce the result.
- Complete the safety and provenance checklist in the pull-request template.
- Do not commit device dumps, firmware, personal identifiers, credentials, generated images, or third-party code without verified redistribution rights.

Maintainers may ask that a large patch series be replaced with links to a public upstream series plus small project-specific metadata.

## Issue and label conventions

- `type:*` describes the work product.
- `subsystem:*` identifies the primary technical area.
- `status:*` describes the next action or external dependency.
- `priority:*` reflects project sequencing, not importance to an individual user.
- `hardware:*` records variant or hardware-access constraints.

The declarative inventory is in [`project/labels.yml`](project/labels.yml).

## Conduct

Be precise, patient, and respectful. Challenge technical claims with evidence, not people. Safety concerns, licensing concerns, and upstream maintainer feedback take precedence over schedule.
