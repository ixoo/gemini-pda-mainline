# Focused schema collector preparation

Status: revised after [attempt 1 refused](VALIDATION_ATTEMPT_1.md); the correction
is prepared for review, with no second execution admitted. The [helper](scripts/schema-check.py)
defaults to printing its plan. Only an integrator-assigned lock window can admit
`--execute`. The [contract](schema-contract.json) freezes the existing source,
protected build files and schema-tool setup. No kernel compile, extraction,
source preparation, package replacement or device action is selected.

The helper supplements [the schema protocol](QEMU_VALIDATION.md#focused-schema-protocol-for-review).
The retained source recipes use `|| true` for some validators, so a zero make
status cannot establish schema success. The helper deliberately has no automatic
`PASS` outcome: complete collection is `COLLECTED_REVIEW_REQUIRED`. Root must
review every diagnostic before publishing a schema claim. Unexpected stderr,
missing explicit DTB attribution, truncation, timeout or changed inputs refuses.

## Identity and lock

The initial read-only preparation inspected source markers and tool interfaces.
The separately admitted first attempt ran the source-integrity precheck and
binding recipe, then refused; its immutable receipt remains authoritative. Source state is
`2d5410d33d5c55def94fdb025de329e4486d929963b097623bf35790b5840c3f`, integrity
`90923e5fb4d9bf2db35049abb6011437bc334aeedc528f099591f6198e9fc7aa`.
The source/build roots remain those of exact build
`4ec63076aeb6388ba24b33ee20afcf19ced541e1`.

The admitted schema environment is
`/workspace/gemini-pda/cache/validation-tools/schema-2026.6`. Its `SETUP.json`
SHA-256 is `36a938aee866f09eb650769e8f5ae049f7793a719f966eaf5050a2d761a90383`.
The collector requires that environment's Python, dtschema 2026.6, Yamllint
1.38.0, pylibfdt 1.7.2.post2 and the recorded extension digest. It records actual
schema CLI, make, system DTC, retained build DTC, cross-compiler and linker
versions/digests; the latter two must match the exact kernel build provenance.
Tool versions are bounded read-only queries, not installation or upgrades.

Execution opens the existing normal Buildbox `~/gemini-pda-buildbox/build.lock`
without following a final-component symlink, requires a regular file and takes
an exclusive nonblocking lock. Contention refuses before tools or source access.
The lock is never recreated, truncated or removed. The same open descriptor is
inherited by command processes, so a surviving descendant cannot silently release
the shared build exclusion merely because the coordinator died. The collector
never guesses that a stale job has finished or removes another task's lock.

Source markers, all eleven generated-source file hashes, resolved config,
release, Image.gz, four production/test objects and both DTBs are pinned before
work. Full source integrity is checked with the existing repository verifier
before recipes and after complete collection. Protected file checks also run
on failure; a failed attempt does not claim a full post-run source audit when
that audit could not complete. No mismatch is repaired automatically.

## Commands and ceilings

The planned sequence is one `dt_binding_check`, one `dtbs_check`, then exactly
one direct verbose `dt-validate` for each of the two MT6797 DTBs. Both make targets
use the same source/build, `ARCH=arm64`, cross-compiler, one job, verbose command
logging and `DT_SCHEMA_FILES=clock/mediatek,infracfg.yaml`.

Direct checks use the resulting processed schema with the same exact filter.
They provide explicit attribution even when incremental make does not rerun an
unchanged DTB. The helper requires the processed schema's normalized ID and
MT6797 compatible, and exactly the pinned tool's `Check:  <DTB>` output. pylibfdt
then checks a unique MT6797 infracfg node with `#reset-cells = <1>`. The public
header bytes are pinned to the reviewed two-ID header through the source receipt.

Proposed ceilings, requiring review with this helper:

- Each make target: 300 seconds; each direct DTB check: 30 seconds.
- Each full source-integrity read: 180 seconds; each tool version query: 5 seconds.
- Every captured command: 16 MiB each for stdout/stderr, five-second TERM-to-KILL
  grace and one bounded second for reaping; no core files. Parent-owned pipe
  capture never writes more than 16 MiB per stream; reaching that limit refuses.
- Each generated regular file: 128 MiB through inherited `RLIMIT_FSIZE`. This
  is a per-file ceiling, not an aggregate quota; the fixed one-job recipes,
  timeouts and free-space checks remain required.
- At least 512 MiB free on the build filesystem and 256 MiB for captured evidence.
- No retry or additional target; output goes to one new named attempt directory.

The subprocess runner reuses the reviewed group cleanup, handled-signal guard
and completed-decision publication semantics without changing QEMU's frozen
runner or contract. Schema children receive the separate 128 MiB regular-file ceiling and
Linux direct-child parent-death setup. SIGTERM/HUP/INT stop the batch and preserve
incomplete evidence. Abrupt coordinator death does not provide arbitrary
recursive descendant containment; the inherited build lock prevents another
build from racing such a survivor. Root must reconcile incomplete jobs before
allocating another window. No guest or virtual machine is involved.

Recipe `mktemp` files use an explicit context-managed scratch directory inside
the evidence attempt, cleaned on ordinary success/failure. An uncatchable kill
may leave scratch there: preserve the attempt and reconcile process/lock state
before root removes disposable scratch. Never delete raw logs or reuse the
attempt to bypass refusal. Raw stdout/stderr and atomic receipts remain available.

## Invocation after review

The helper does not accept alternate source/build/tool roots or action budgets
from the command line. The values come from the reviewed contract.

```sh
python3 experiments/2026-09-05-mt6797-infracfg-upstream-preparation/scripts/test-schema-check.py
python3 experiments/2026-09-05-mt6797-infracfg-upstream-preparation/scripts/schema-check.py
# Only in an assigned lock window, from the exact reviewed repository revision:
/workspace/gemini-pda/cache/validation-tools/schema-2026.6/bin/python \
  experiments/2026-09-05-mt6797-infracfg-upstream-preparation/scripts/schema-check.py \
  --execute --output "$evidence_parent/infracfg-schema-4ec63076-attempt-2"
```

The host fixtures use tiny synthetic files/properties/processed-schema objects
and fake Python subprocesses. They cover the fixed plan, default nonexecution,
input changes/symlinks, schema/DTB refusal, held-lock refusal, timeout and exact
log-ceiling refusal even on zero exit. They do not replace exact Linux fixtures,
real libfdt traversal, source-integrity checking or schema execution. Review and
publish sanitized diagnostics only after an admitted run.

## Correction evidence and limits

The pinned source recipe `Documentation/devicetree/bindings/Makefile` has SHA-256
`622c42e361dfd164313fa987a92f58bf555931a65ffe52d09927e2fccf224698`.
Its `cmd_mk_schema` feeds `find_all_cmd` through an argument file to
`dt-mk-schema`, then redirects the resulting JSON to `processed-schema.json`.
Thus a focused DT schema filter does not make this aggregate generated file a
small diagnostic stream. Attempt 1's exact error came from that redirected
output; make reported deleting the partial target. A subsequent bounded
read-only existence check confirmed that target absent. No source repair or
manual partial-output removal was performed.

The correction changes only host collection and the generated-file allowance.
Thirteen offline fixtures include a real synthetic 17 MiB generated file that
succeeds, independent stdout/stderr floods that refuse with each retained log
hard-capped at 16 MiB, a scaled generated-file limit refusal, and the existing
timeout, lock and protected-file tests. The stream collector drains both pipes
without blocking one behind the other, rejects exact-limit output even at zero
exit, and retains the original process-group cleanup/refusal semantics.

These fixtures passed on macOS; Linux fixtures from the new committed revision
are still required before any second schema window. No schema target was rerun
to choose 128 MiB, and no claim is made that this allowance is sufficient. If
the reviewed second window exceeds its allowance or fails another gate, retain
that refusal without automatic retry. Original attempt-1 receipts and its
16 MiB limit remain unchanged.
