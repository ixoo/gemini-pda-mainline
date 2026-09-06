# Validation record

Normal and optimized Python each pass 31 refusal fixtures, including coordinated
identity mutation, in-bounds anchor relocation, direct predecessor tuple drift,
guard inversion, invented callers, wrong mode/pointer, reachability/invocation
conflation and authority promotion. No assertion-based safety gate is used.

Checks actually run on 2026-09-06:

- `python3 verify.py`: PASS, five independent predicates, 22 source tuples,
  36 exact citation anchors, 18 request receipts and 31 refusal fixtures.
- `python3 -O verify.py`: identical PASS. No source execution or network fetch.
- All eight files: JSON parsing, in-memory Python compile, final-newline and
  trailing-whitespace checks, local Markdown link targets and bounded sensitive
  markers: PASS. No bytecode or `__pycache__` was created or present.
- `git diff --check`: PASS. The separate all-file whitespace scan also covers
  the untracked experiment files, which ordinary diff output alone omits.
- `./scripts/check-repository`: PASS (`repository_checks=pass`), including
  manifest, source-integrity, publication, target guard, backend/preflight,
  host-tool and workflow refusal checks. The gate reports 37 grandfathered
  metadata records. Linux-only checks and full-package validation were skipped
  or deferred as printed; they are not claimed as passes.

The independent source/citation freeze was declared before verifier creation.
All ten inherited source identities also compare field-for-field against the
pinned predecessor inputs, and its four local evidence-file hashes are checked.
All 18 network requests are retained: 13 successful raw requests of 12 new
regular files, two explicit initial header-path 404s and three immediate-directory
inventories. A successful header request had no target guard definition; the
last batch resolved the guard in the actual function header. No retry or test
repair was required. The platform.c second read selected only a previously
unread initializer; inherited data context was reused without a new request.

The remaining risks are the two uninspected outer built-in callers and product
build/runtime equivalence. The negative callback-clear reachability result is
conditional static dispatch only; invocation, unrelated clearing paths, pointer
mutation, synchronization and resource effects remain outside its boundary.
The predecessor's accepted lifetime/cleanup verdicts were not rewritten.

No shell changes: bash syntax and ShellCheck are not applicable. No kernel,
checkpatch, DT-schema, Buildbox/VM or device test was performed. No source body,
private input, raw artifact, staging, commit or push was created. Independent
semantic review and frozen-integration publication remain the coordinator's
handoff. Credits are unavailable; the coordinator owns any accepted/excluded
workflow measurement.

## First-review repair 1

The independent review found mutable directory request identities/entries and
no-hit accounting were not protected by the existing source/citation freeze.
It also found the proposed next source selection omitted common_drv_init.c
without first establishing the detector Makefile's selected producers.

The bounded repair adds the explicitly declared immutable-request-evidence
freeze in FREEZE.md, then validates that independent digest. It covers all 18
receipts, including contents URLs, response SHA-256/byte counts, exact entries,
failures/timestamps, allowlists and the no-hit record. The original 22 source
tuples and 36 anchors remain unchanged. All matching next-discriminator text
now requires drv_init/Makefile first, followed only by its demonstrated
lifecycle producer/caller sources and subsequent direct edges.

Checks actually run for this repair:

- Normal and optimized verifier: PASS, **37 refusal fixtures** each. Six new
  fixtures reject coordinated inventory mutation/emptying, no-hit deletion,
  contents URL mutation, response-hash mutation and response-size mutation.
- Eight-file JSON parsing, in-memory compile, whitespace/newlines, local links
  and bounded sensitive scan: PASS; no bytecode or pycache present.
- `git diff --check`: PASS, including the concurrently dirty worktree without
  modifying any other owner's files.

No test repair, fetch, source read, device/build action, staging or commit was
performed. The full repository gate was not rerun for this bounded repair; the
earlier gate result above is historical, and final integration validation stays
with the coordinator. The five semantic verdicts, state model and source budgets
are unchanged. No runtime/ownership authority is added.
