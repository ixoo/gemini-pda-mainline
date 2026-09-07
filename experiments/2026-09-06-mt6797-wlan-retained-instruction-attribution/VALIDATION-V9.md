# V9 tools-preflight: complete in the explicitly preloaded environment

The single [Amendment 24](AMENDMENT-24.md) tools-preflight, clarified by
[Amendment 25](AMENDMENT-25.md), returned `tools-preflight-only`.
All 20 outer stages and all 12 queue-preload stages passed. No first refusal
or failed restoration was recorded.

This proves the bounded tool import/engine lifecycle in this exact process
with `_queue` explicitly preloaded. It does not establish a package caller
join, general package or queue API usability, repeatability, a private-analysis
method, retained-binary behavior or hardware support. In particular,
`analysis_admitted` remains false and the private-analysis budget remains
unused. This is not an analysis-ready or hardware-ready receipt.

## Frozen identity and chronology

- Clean dispatch, equal to `origin/main` before freeze:
  `9c2c63a302bc19639d032a8755eca2b3aa1564b3`.
- Dispatch [inputs.json](inputs.json) SHA-256:
  `ae9e6abeb836faf32d18bb1bdb1d46cc1bc97d5d5d5d5d4615fe343b34573602e5`.
  All 94 controls/dependencies passed before construction/freeze.
- [Frozen bootstrap](bootstrap-v9.json) SHA-256:
  `c8de911c9d62b389b04beafb08aa5c30beb72c1898190177190e764214cb922a`.
- Complete embedded independent MIT-licensed source SHA-256:
  `d1e807146ab4983142e817bec3be79fb6db5894bb9ebd74f2fb09759c25301e1`.
- Source/container frozen at `2026-09-07T07:48:24.869208+00:00`.
- Sole execution: `2026-09-07T07:48:56.987585+00:00` through
  `2026-09-07T07:48:57.677804+00:00`.
- [Complete sanitized result](bootstrap-v9-result.json) SHA-256:
  `334149f00090c18d6f51baf84d05d94844a15aece74da43aeb1282cf87b87fb3`.
- Canonical child receipt SHA-256:
  `743b7f9833844649070d0cb4b4aac5a367faa0a33da4125978cebd39b10fbdb3`.

The approved `./scripts/dev-vm re-shell` supplied the frozen source once on
stdin to `/usr/bin/python3.12 -I -S -B - preflight`, with empty
`DEBUGINFOD_URLS`, no-user-site and no-bytecode environment controls. No guest
source file, method input, private path or analysis database was created.
The child and outer RE shell exited; RE-VM custody is released.

The original child JSON was retained as text and parsed/formatted losslessly
with host Python. Its canonical digest matched before publication. Large
nanosecond integers were not passed through JavaScript numeric serialization.
The current input pins additionally cover this result trio and handoff state;
the immutable dispatch-input digest above remains the pre-execution reference.

## Complete bounded observations

The 25-source Capstone and 52-source pyelftools inventories passed their common
pre-entry gate and subsequent required drift checks. There were 73 demanded
module entries and 73 completions within the 77-source budget; no claim is made
that all mapped source modules were demanded. The original Capstone native
request occurred once and the optional route was refused once as required.
Exactly one ARM64, little-endian, detail-enabled Capstone engine was
constructed and its configuration remained checked. No engine decode or
disassembly, `ELFFile` construction or target/private parser was invoked.

The exact resource extension's spec/create/exec/extension/cached-request/
function-call/function-return counters were each one, with zero function
exceptions and final state `returned`. The separate `SC_PAGE_SIZE` reference
used mapped value 30 and returned 4096 once. Its guarded state stayed unchanged;
the completed pyelftools `PAGESIZE` global equaled 4096 through final checks.
No other resource function was admitted.

The bootstrap-owned `_queue` preload occurred after the page reference and
before pyelftools import. It recorded one wrapper call/delegation, one discovery
event and one exact extension event. The discovery search fields were present
and matched the frozen live objects/order; the extension search fields were
absent. The original import function was restored immediately after the
request. Exact module/spec/loader identity and candidate mappings remained
stable through the later required checks.

Two cached `_queue` requests completed in the inherited wrapped pyelftools-
import interval, without a new queue audit event or object replacement. No
caller frame, literal source join or member value was captured. This interval
observation does not identify which package or intermediate helper made either
request, nor prove a direct pyelftools `_queue` dependency.

The queue gate's strict maps snapshots had 85 and 89 rows. Only the accepted
candidate was added, with device `253:1`, inode `8678`, and the exact four
permission/offset rows `r-xp/0`, `---p/16384`, `r--p/61440`, `rw-p/65536`.
Baseline file-backed rows and the exact full vDSO row were unchanged. The
queue-extended baseline was then used for the resource-call, post-pyelftools,
post-engine and final checks. All 13 maps snapshots passed their byte/row caps;
the eleven inherited map checks and both queue snapshots preserved the vDSO
predicate. Nonexecuting anonymous differences were bounded, not treated as
new file-backed native components.

| Counter | Observed |
| --- | ---: |
| Queue preload candidate content opens | 0 |
| Later queue content opens/audit opens/reads | 17 / 17 / 17 |
| Queue `lstat` / `fstat` | 38 / 34 |
| All maps opens / reads | 13 / 13 |
| Queue preload wrapper calls / delegations / rejections | 1 / 1 / 0 |
| Cached queue requests in the wrapped interval | 2 |
| Profile installation / restoration / rejected events | 1 / 1 / 0 |
| Asset opens: initial / pre-import / pre-analysis / final | 28 / 28 / 0 / 28 |
| Private reads / callback calls | 0 / 0 |

The 17 later queue identity reads consisted of four at each inherited
`resource-c-call`, `post-pyelftools`, `post-engine` and `final` maps stage, plus
one explicit component-drift read. Every full stat tuple, byte count and content
SHA-256 matched the frozen accepted identity. This is the explicit Amendment
24 rehash budget, separate from Amendment 23's earlier no-content load test.

All seven named restorations reported attempted/true: original import,
native-load endpoint, finder/meta-path, isolated path, resource loader create
method, resource loader exec method and profile. The irreversible audit hook
remained installed. No module unloading or `sys.modules` deletion was attempted;
process exit is the cleanup boundary.

Queue rejected/effect audit counters and inherited write/cache-write/network/
process counters were zero. The zero queue `ctypes.dlopen` count is not a claim
that no native loading occurred: the ordinary extension import and admitted
Capstone native route are separately recorded. No raw map address/row,
queue-observer path set, pointer, module attribute list, private byte or dynamic
exception text is published. The installed-tool identity inventory is inherited
sanitized provenance, not a private target capture.

## Checks actually run and limits

- Clean dispatch/origin identity and all 94 pinned hash checks before freeze.
- Host AST parsing and compile-only checks in normal and optimized modes;
  unique function definitions and active checks without `assert`.
- Exact helper-import AST comparison; unchanged ASTs for the selected inventory,
  resource, source-AST and cached-resource protocols, allowing only the renamed
  zero-use checker where applicable.
- Amendment 25 parsing/data-flow review: retained explicit metadata parser and
  five AST sites, two native `needed()` sites, source-only compile/exec input,
  removal of unused RECORD/CSV and method JSON-deserialization routes, and no
  dormant analysis/private/callback entry functions or objects.
- Source-derived successful-path parsing counts and candidate/map budgets;
  one engine, one queue preload, one page reference, original version-query
  multiplicity and direct counted new `os` metadata sites. These parsing counts
  are static call-path checks, not interpreter-wide parser instrumentation.
- Frozen source/container/input verification before the sole guest run.
- Exactly one tools-preflight run, with the positive stage/counter results above.
- Lossless result/canonical digest and JSON/schema checks; chronological,
  stage/module/queue/resource/engine/restoration/map/stat/authority predicates;
  updated pins, local links, privacy/license and whitespace checks.
- `git diff --check` passed.

No fixture execution, refusal mutation run, second preflight, method, private
analysis, network acquisition, device operation, Buildbox or kernel build ran.
Failure/cleanup branches were reviewed in source but not exercised by this
positive run. A Python audit hook and these observations are not a general
security sandbox or a proof of all in-process effects.

Only the three v9 artifacts and authorized work-item/input state pins changed.
No commit or push was performed; `/root` owns integration and workflow
measurement. The one preflight budget is consumed. Stop here: further use,
including any analysis-capable bootstrap or method, requires a new prospective
bounded contract and dispatch.
