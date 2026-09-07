# Validation and handoff

Review-ready: `2026-09-07T19:22:43Z`. Sol Medium independently accepted the
packet at `2026-09-07T19:32:12Z` without rework.

## Checks actually run

- All seven contract input SHA-256 values matched before investigation.
- All 15 inventoried repository input SHA-256 values matched the exact parent
  Git objects; sizes and evidence classes are recorded in `inputs.json`.
- RE VM status was Running before the approved explicit RE-shell invocation.
  One filename/stat inventory examined 697 file entries and selected zero
  candidates. No private body or raw output was read/exported; no scratch child
  was created. The Lima host printed a nonfatal Rosetta-detection warning;
  the requested inventory completed with its aggregate JSON receipt.
- `python3 experiments/2026-09-07-mt6797-wifi-retained-lifetime-audit/verify.py`
  passed: 15 input identities, 238 mutation refusals.
- The same command with `python3 -O` passed with the same 238 refusals.
- `git diff --check` passed. Assigned JSON parsing, local Markdown targets,
  Python AST syntax and absence of assertion-based checks passed.

One preliminary host comparison compared binary-encoded file strings with
UTF-8 Git output and rejected four equal-byte Unicode-containing records.
The immediate digest comparison showed equal hashes in each case. The
corrected byte-digest check passed all 15 records. No source drift was found;
this was a host validation-query defect, not contradictory hardware evidence.

## Limits and review decision

The verifier detects changes to the frozen receipt and external inputs. Its
mutation coverage is not a test of a hardware classifier, private parser or
observer, and cannot prove empirical truth or discovery completeness.

No kernel build, device test, private-body analysis, network lookup, firmware
action or upstream action was run. Existing source/static facts are not
promoted into executed effects. All five runtime predicates remain missing,
with no common successful cycle or temporal join.

The scratch-child instruction was not exercised because no raw private output
was created. The README explicitly discloses this departure from the dispatch
wording for independent review. Do not add a second private access method or
manufacture scratch output merely to hide it.

Sol review covered these seven outputs: README.md, inputs.json, inventory.json,
evidence-matrix.json, FREEZE.md, verify.py and VALIDATION.md. Concurrent
AGENTS.md and display-experiment work were untouched. Integration, publication
and workflow-ledger ownership remain with the parent; the worker made no commit
or shared-document edit.
