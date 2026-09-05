# Experiment: project workflow corrective review

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-05-project-corrective-review` |
| Status | complete for repository corrections and parallel-work proposal |
| Subsystem | Repository workflow, deployment guards and delivery coordination |
| Device variant | No device action; planned protocols retain the named MT6797X Gemini boundary |
| Date | 2026-09-05 UTC |
| Investigator | Codex, with bounded independent tooling/review agents |
| Tracking | [Project plan](https://github.com/ixoo/gemini-pda-mainline/issues/1), [CI](https://github.com/ixoo/gemini-pda-mainline/issues/8) |

## Question and provenance

Can the project enforce the reviewed build/deployment invariants and make
independent upstream work possible without changing active kernel inputs or
losing experiment history?

The review began at repository `ed2c1287`; independent thermal work continued
through `6a8c730a` and was coordinated with its owner before roadmap edits.
That owner committed the complete host-protocol work as
`5194011ee370080ca4f231764dca11f021fdb330` and released roadmap ownership.
The exact original roadmap is preserved by commit, blob and SHA256 in
[roadmap-history.json](results/roadmap-history.json); its instructions are
historical, not current admission.

At the audit boundary there were 531 canonical patch entries, 189 profiles,
an 8,576-line roadmap and a 17,632-line Buildbox dispatcher. The issue tracker
retained its July 11 seed updates; open issues intentionally remain open until
upstream acceptance. Those counts describe this audit only.

## Safety and scope

This work changes repository tooling and coordination documents. It does not
change kernel patches, manifest selections, configuration fragments or the
active corrected thermal candidate. The thermal owner retains control of that
experiment and independently validated integration of the new mount guard.
No historical installer is automatically made current by adding a shared helper.

Device writing, consuming runtime observations and firmware operations are not
part of this review. Any Buildbox package created for validation is a tooling
regression artifact and does not replace the experiment-selected boot candidate.
No backup, credential, calibration, proprietary input or raw runtime capture is
an opportunistic cleanup target.

## Corrective implementation

- Build selection defaults to explicit Buildbox behavior and never chooses the
  native VM automatically when Buildbox is unavailable.
- Package publication validates content and preserves distinct immutable
  identities instead of deleting an older experiment package at a reused name.
- A sourceable [device guard](../../scripts/boot2-device-guard.sh) compares
  live block identities with mountinfo/root/holder/swap state. Its tests use
  synthetic observations and make no device write.
- The [common repository gate](../../scripts/check-repository) and Linux CI run
  shared fixtures and publication checks. Historical synthetic-certification
  debt is held by exact file hashes and explicitly remains a submission blocker;
  the gate rejects new or changed debt rather than inventing authorship.
- README and architecture distinguish isolated A72 results from default and
  upstream support. The roadmap now owns concise ordered work, separate
  deliverables and a serial device queue. Historical anchors remain available.
- The [registry](../../project/workstreams.json),
  [handoff contract](../../project/WORK_ITEM.md) and
  [upstream topic inventory](../../project/upstream-topics.json) make task
  boundaries explicit. Unassigned entries are proposed work, not running tasks.

## Validation and limitations

The [initial local gate](results/local-validation.json) and subsequent
[Linux CI runs](results/ci-portability.json) pass the shared invariant,
source-integrity, publication, backend, preflight, device-guard and package
fixtures, plus changed-file syntax, shell, links and bounded publication checks.
Linux exercised the full artifact provenance validator and full-package branch.
All 189 selectable profiles satisfy canonical order. Independent review found
and corrected legacy-fetch provenance and unreadable-inventory cases.

The final [Buildbox build and fetch](results/buildbox-validation.json) both
returned success at `871bdbb7c27ec5af9e3e66dbef773075466bcccc`. The managed source
was reused, the kernel image and configuration retained their selected-input
checksums, and older packages remained unchanged. New package identity includes
the complete inventory and exact repository provenance. Two failures in the
initial run are recorded: an ignored local Git refresh failure, fixed with
explicit refusal and 22 preflight cases; and a post-transfer shell parse error
caused by editing the running dispatcher. The final run froze the integration
checkout through fetch and passed cleanly. Workers must use separate worktrees
during that window.

The thermal [shell-suite record](../2026-09-04-mt6797-thermal-snapshot/results/v4-exact-shell-pass.json)
confirms the exact candidate BusyBox/QEMU suite passed at that
same published revision, together with installer/path/receipt and synthetic
deployment fixtures. Its [host protocol](../2026-09-04-mt6797-thermal-snapshot/V4_HOST_PROTOCOL.md)
owns the exact test record and device admission. Fixtures establish
refusal/identity behavior, not physical mount state or hardware support.
No device boot/write was performed by this corrective review. Kernel patches,
manifest and configuration inputs are unchanged, so no new checkpatch or DT
schema claim is made. The regression packages do not replace the selected boot
candidate.

The existing synthetic sign-offs remain unresolved historical debt. Existing
patch bytes and evidence hashes are preserved. New upstream submission topics
must establish actual authorship and truthful certification before submission.
The metadata gate is not a certification or proof of a complete license review.

## Follow-up ownership

Ordered corrective and parallel delivery gates are in the
[roadmap](../../docs/ROADMAP.md). The thermal experiment owns candidate admission
and any physical result. Upstream topics own target-tree review, actual author
provenance, public feedback and eventual local-patch removal. The workstream
registry helps coordinate ownership; it does not bypass either boundary.
