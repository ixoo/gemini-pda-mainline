# Validation record

Executed on 2026-09-06; source-only, offline checks after retrieval.

- Normal and optimized verifier: PASS, 67 refusal fixtures each; six predicates,
  19 complete source tuples, 38 anchors and six complete request receipts.
  Tests cover co-mutated sources/requests/citations, selected objects/config,
  invented producer/registration/exit, assumed chip identity, hidden aggregate
  loss/retry, order inversion, built-in/module confusion, authority promotion,
  no-hit deletion and budget drift. A separate predecessor mutation tests the
  field-for-field inherited comparison independently of the source digest gate.
- Initial repository gate refused the temporarily missing VALIDATION.md link
  while this record had not yet been created. The missing record was added;
  this is one packaging correction, not a source-evidence repair.
- All eight files: JSON parsing, in-memory Python compile, newline/whitespace,
  local Markdown links, bounded sensitive-data patterns and no-pycache checks
  PASS. Retained suffixes are only .json, .md and .py.
- `git diff --check`: PASS; the separate all-file whitespace check includes
  untracked experiment files that this Git check alone would omit.
- Final `./scripts/check-repository`: PASS (`repository_checks=pass`), including
  195 manifest profiles, source-integrity/publication/target guards, backend and
  preflight refusal fixtures, host-tool and workflow checks. Existing metadata
  debt remains 37 records. Linux-only checks and full-package validation were
  skipped/deferred as printed, not counted as passes.

Source-rights review: all new MediaTek notices and module-header attribution
were inspected for study only. Retained files contain independently authored
prose, metadata and verifier code; no vendor body/excerpt, raw artifact,
private source, credential or source-reuse claim is retained.

No shell changed: bash syntax and ShellCheck are inapplicable. No kernel change,
kernel build, DT-schema, checkpatch, device/SSH, private capture, VM, Buildbox,
staging, commit or push occurred. No hardware support is inferred.

Unresolved risks: actual external ioctl issuer/value/order/return policy,
int conversion for unvalidated out-of-range inputs, final ordinary/weak link
selection, deeper callback/resource lifetime and an actual gen3 exit join.
The source registration return can hide an SDIO registration error; the later
connection aggregate can hide individual component errors through summation.
Neither proves runtime success or radio safety. Both source batches are closed.

The frozen contract and predecessors were not edited. The coordinator owns
independent semantic review, accepted/excluded pilot-03 measurement and any
publication validation. Credits remain unavailable.
