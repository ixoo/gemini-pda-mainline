# Validation record

Executed on 2026-09-06 for the specialist handoff:

- `python3 .../verify.py`: PASS, five predicates, three batches, 26 receipts,
  17 unique files (four new), 16 refusal fixtures.
- `python3 -O .../verify.py`: identical PASS; no assertion-based gate.
- In-memory Python `compile`: PASS, without bytecode output.
- Seven-file inventory, all-file whitespace/final-newline check, local Markdown
  link-target check and bounded sensitive-marker scan: PASS.
- `git diff --check`: PASS. The separate all-file check covers this untracked
  experiment, which ordinary diff output alone does not cover.
- `./scripts/check-repository`: PASS. It reported 195 manifest profiles,
  eight manifest mutations, seven source-integrity mutations, 13 publication
  mutations, 18 boot-target tests, 12 backend tests, 22 Buildbox preflight
  cases, and 17 workflow refusals, plus its remaining host test suites.
  Existing metadata debt remains 37 grandfathered records. Linux-only prepared
  source/artifact-provenance checks and full package validation were skipped or
  deferred as printed by the gate, not claimed as passed.

All 26 public file requests returned HTTP 200. Repeat fetches preserved their
whole-file hashes, and the 13 predecessor identities match. No network retry
was needed. The deferred-registration search in `wmt_dev` had no selected
function-body hit; the actual assignment/late callback is in `wmt_exp`.
Only independently authored Markdown/JSON/Python, hashes, URLs, identifiers and
line citations are retained; no copied source text or raw artifacts.

## Accounting and residual risks

One malformed local patch request was rejected before modifying files and then
corrected. Initial manually entered freeze-time labels were discovered to be
unmeasured/inconsistent with request clocks and removed. The allowlist patches
still preceded the requests; no invented freeze-time claim is retained.
Measured request timestamps are unchanged. Two deliberate contextual
whole-function rereads were declared; incidental locator contexts also repeated
parts of earlier functions. Integration must judge the strict budget
interpretation rather than treating the verifier as proof of that boundary.

The central source counterexample is late registration after a missing callback
and possible common power-off. The exact common compile guard and built-in
init/exit selection remain unjoined. Concurrent callback changes, OSAL timeout
ownership, successful rail/clock effects and safe probe-failure cleanup are not
proved. These findings neither establish live source equivalence nor authorize
Linux ownership, vendor reuse or a device experiment.

No shell changed: `bash -n`/ShellCheck are not applicable to this item.
No kernel patch or configuration changed; no Buildbox/VM build, checkpatch,
DT schema or device test was run. No SSH, private input, hardware, staging,
commit or push action was taken. The coordinator retains independent semantic
review and final frozen-integration publication checks, and records the
accepted/excluded workflow measurement. Credits are unavailable.

## First-review bounded repair

Sol's first review required an independent identity/anchor freeze and body-level
unregister wording. One authorized repair cycle addressed only those blockers,
without any new source read, request, build or device action.

- [FREEZE.md](FREEZE.md) declares `wlan-common-lifetime-evidence-v1`, including
  pre-repair whole-file identities and fixed canonical hashes for all 17 source
  tuples and 42 exact citation anchors. Expected digests are constants, never
  derived from mutable evidence at verifier startup.
- All 13 reused tuples additionally match every identity field against the
  independently pinned predecessor JSON. The predecessor check has its own
  direct mutation fixture, so coverage is not hidden behind the tuple digest.
- `wmt_wlan_unreg_body_clears_callbacks=true` records function-body behavior;
  `built_in_unregister_reaches_callback_clear=null` remains unresolved and does
  not claim either positive or negative execution. Cleanup remains unresolved.
- Normal and optimized Python: PASS, **22 refusal fixtures** each. New fixtures
  reject coordinated source-identity mutations, an in-bounds citation move,
  predecessor tuple drift, body-claim erasure and either boolean promotion of
  the unresolved built-in execution field.
- Eight-file inventory, JSON parsing, in-memory compile without bytecode,
  whitespace/final newlines, local links and sensitive markers: PASS. No
  `__pycache__` directory or bytecode existed; nothing required removal.
- Repository gate rerun: PASS (`repository_checks=pass`), with the same
  documented Linux-only skips/deferred full-package validation; no kernel,
  checkpatch, DT-schema or device test. `git diff --check`: PASS.

No verifier test failed during repair. One no-op documentation patch with an
incorrect context was rejected without changing a file, then replaced by this
explicit validation addition. This is not a second repair cycle or source read.
