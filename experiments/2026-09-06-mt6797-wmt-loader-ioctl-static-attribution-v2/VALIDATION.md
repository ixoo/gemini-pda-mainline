# Validation record

Executed on 2026-09-06 after the two bounded static-analysis batches.

- Normal and optimized verifier: PASS, 80 refusal fixtures each; six predicates,
  22 binary anchors, eight child-tool receipts and fourteen distinct ioctl
  sites. Independent policy tests reject forbidden debug flags, external input
  or evidence, symbol-server environment and diagnostics without relying on
  the complete analysis hash gate. An inherited tuple mutation independently
  tests predecessor comparison.
- Refusals also cover binary drift/co-mutation, invented request/call/value
  origin, pointer/scalar confusion, command order, hidden aggregate discard,
  retry/gating, runtime/mainline promotion, missing receipts and budget drift.
- All eight files: JSON parsing, in-memory Python compile, newline/whitespace,
  local Markdown links, retained-suffix allowlist, bounded privacy and
  instruction-listing patterns, and no-pycache checks PASS.
- `git diff --check`: PASS. The separate all-file whitespace check covers
  untracked files that the Git check alone would omit.
- `./scripts/check-repository`: PASS (`repository_checks=pass`), including
  195 manifest profiles, source-integrity/publication/target guards, backend
  and preflight fixtures, host-tool checks and workflow validation. Existing
  metadata debt remains 37 records. Printed Linux-only and full-package
  skips/deferments are not claimed as passes.

Rights/privacy review: only two directly selected literals (device path and
chip property key), address/count metadata and independently normalized
semantics are retained. No raw bytes, instruction listing, complete function
dump, string corpus, decompiler output, analysis database, private path,
credential or personal identifier is retained. Binary/source/ABI reuse and
redistribution are not inferred. Temporary files were never created.

No shell changed, so bash syntax and ShellCheck do not apply. No kernel change,
build, checkpatch, DT-schema, device/SSH, live-process inspection, ioctl,
network retrieval, VM kernel build, Buildbox, staging, commit or push occurred.
The admitted RE VM only performed static reads of the exact binary; no program
execution/emulation or debug/unwind lookup was requested. No diagnostic or
external-file evidence occurred in either fresh v2 batch. V1 output was not
reused. No v2 repair attempt was needed.

Unresolved: runtime branch/value, dynamic libc parse/ioctl conversion, the
routine's startup caller and process exit status, external-call side effects,
resource lifetime, firmware success and standard mainline ABI design. The
source predecessor's arithmetic aggregate still cannot prove individual
component success. The closed analysis budget authorizes no further probes.

The coordinator owns independent review, integration/publication checks and
the accepted/excluded pilot-03 measurement. Credits remain unavailable.
