# Validation: fresh source-forced no-database audit

## Executed checks

- Contract identity and twenty frozen predecessor/dependency file hashes:
  passed. Predecessor contents were not parsed or compared with fresh tuples.
- Installed Python 3.12.3, pinned distribution/tool identities, RECORD digest
  and size, nonsymlink source containment, static import closure, architecture
  state inventory and diagnostic-only database dataflow: passed.
- Frozen loader/collector/subclass syntax and hashes before content: passed.
- One guarded RE parser construction: passed; 64,417 monotonic tuples,
  seven executed source modules, 160 registered source-derived code objects,
  architecture/metadata override counts 1/1, detector calls zero and exact
  restoration, all six sentinel downstream read/use counts zero, all twelve guard
  classes zero. All source snapshots and synthetic-parent checks passed.
- Four fresh neighborhoods and conservative interval predicates: passed.
  Original type `T`, exact-name count one, alias count zero and retained ELF
  size zero for each target.
- `python3 -B experiments/2026-09-06-vmlinux-to-elf-symbol-provenance-v3/verify.py --self-test`:
  passed, 261 rejected mutations.
- The same command with `-O`: passed, the same 261 rejected mutations.
  Host verifier Python was 3.14.7; the actual RE parser used Python 3.12.3.
- Syntax, all eight new files' whitespace/local links/license/focused privacy
  checks, and `git diff --check`: passed. The verifier has no `assert` nodes.
- `./scripts/check-repository`: passed, including 196 manifest profiles.
  Its Linux-only artifact-provenance tests were skipped on this host; kernel
  build, checkpatch, DT schemas and device tests were not run. Existing
  grandfathered metadata debt remained 37. Intermediate document checks
  caught a not-yet-created freeze link and a trailing blank line; completion
  and formatting passed rechecks. The no-index check wrapper was corrected
  to accept an ordinary difference status with no whitespace diagnostics.

## Mutation coverage

Each mode rejected: identity 35; loader 68; metadata-only parent 13;
dependency 3; stub 7; sentinel 6; prohibited guard counters 12; method 19;
target 20; alias 16; boundary 22; strength 8; interval 16; authority 15;
chronology 1. Total: 261 per mode.

These mutate sanitized records in memory. They establish verifier refusal
behavior with optimization enabled and disabled, not runtime guard fault
injection, OS-level sandbox completeness, or a second kernel parse. The
verifier has no private-input, package-execution, device or build action.

## Scope, privacy and unresolved risks

The no-new-files statement concerns the guarded child only: zero attempted
writes after guards, unchanged admitted-source hashes/sizes/modes/mtimes and
an empty fresh cache. The coordinator clarified this before execution.
No database subtree was enumerated or statted; no global absence of externally
created package/database files is claimed. The outer collector's two explicit
private output writes are recorded separately.

The coordinator supplied Sol Medium's source-only sentinel ruling with
acceptance time `2026-09-07T01:17:21Z`: the contract's downstream operations
are read/use-context-limited. All enumerated read/use operations are
instrumented and zero. Ordinary instance attribute writes/deletes fail
naturally because the sentinel has slots and no instance dictionary;
subscript mutation protocols are absent and fail. Those unsupported
mutations were not separately counted or fault-injected. This is not a
general-purpose exhaustive mutation proxy. Frozen source confines database
global uses to the overridden metadata method. The ruling required no
loader change, private-input access or second parser construction.

The Python audit and exact-source provenance checks describe the reviewed
frozen process, not a general OS sandbox. Raw logs remain private, pinned by
hash in [analysis.json](analysis.json); no private bytes, log text, paths,
identifiers or calibration were published. The empty temporary cache was
removed; the two unique evidence files were retained.

The broad synthetic executable image region does not prove instruction
content. Next-symbol boundaries may include padding, pools, aliases or tail
sharing and are not exact ends. No instruction decoding, xrefs, call/return
analysis, runtime observation, teardown conclusion, device operation,
network access, database query, ELF reconstruction or kernel build was run.
Buildbox, shell syntax and ShellCheck are not applicable: no kernel or shell
source was changed.

Full-result independent Sol Medium review accepted every original and amended
predicate on first review at `2026-09-07T01:30:38Z`. The reviewer independently
repeated both 261-mutation verifier modes, `git diff --check`, focused privacy,
authority, link and staging checks, and the repository gate; all passed. No
actionable defect was found. The specialist did not commit, push, edit shared
files or append the integration-owned workflow ledger.

Review-ready UTC: `2026-09-07T01:27:13Z`.
