# V9 tools-preflight with the exact preloaded `_queue` extension

This prospective amendment is designed against clean parent
`d8ba3f43339482b52665cdcd5c45a62d778f64f4` (`origin/main`). It permits one
new, separately dispatched **tools-preflight**, not private analysis. Design
and publication of this contract do not execute it. Every earlier source,
receipt, refusal and consumed run remains immutable.

The accepted [Amendment 23 result](EXTENSION-LOAD-DIAGNOSTIC.md) establishes
one ordinary `_queue` import/initialization and its bounded mapping effect in
an isolated process. [Amendment 19](EXTENSION-EVENT-DIAGNOSTIC.md) identified
the first refused extension event but did not establish its literal package
caller join. The next question is whether V8's complete tools-preflight can
finish when this exact extension is explicitly preloaded before pyelftools.
Do not attribute the preload to a package request or infer a missing caller.

## Inputs, ownership and freeze

The design-parent [inputs.json](inputs.json) SHA-256 is
`d4a51657e6671d7183259c8e9945f4649cc60518f99a0e8e682c4a0033ab4c95`.
Its 92 existing pins were verified during design. The future dispatch must
pin and verify this amendment, amended [WORK_ITEM.md](WORK_ITEM.md), every
earlier control/dependency, V8 and its refusal, and all complete accepted
Amendment 19–23 trios. In particular, retain these exact SHA-256 identities:

| Input | SHA-256 |
| --- | --- |
| `bootstrap-v8.json` | `bc769538ecf3edad9361294f313bd96099cc4da1d848bc875cbd1a13b7ff6f75` |
| V8 embedded source | `3fe4fb8bc87cd46774944c4c10a7d892122ca3dee94ee7cfa39ba0ccfb70332b` |
| `VALIDATION-V8-REFUSED.md` | `cbfcdbf9ecf81622cfa63aef381cc5da71720205596d5599f9ada351f58c2866` |
| Amendment 19 result | `04e1fdfc801b5deb6a6da033a5fc9f79eabc0a9a56324c923397264ed98cfa82` |
| Amendment 20 result | `be64ee02da0daa61068e3dfdf25972d52b2bd70370183817583b632a2e5155dc` |
| Amendment 21 result | `0594feadfe743487cbff6489d0d9d1f0b145439e1228efbd9a144dd91b7865f9` |
| Amendment 22 result | `eac9d08935b88bb565d4bab87ed1d02699a79ac0f10bcc9198068a531ff66508` |
| Amendment 23 source container | `c43ec9e150c8f92d90ceef7907dbf9aa5a8dd52b9b75623ef1f1a933bcb4ea90` |
| Amendment 23 embedded source | `faffb8c563ea015c74009dc0e68eed9bc07f7bc19fbdd5402bbe649ba9dead2f` |
| Amendment 23 result | `155ddb7da5d3872c69393723a342a456a268fd6e819b51357543e20976534a21` |

Astra Medium owns the bounded integration uncertainty; Sol Medium reviews;
`/root` integrates. A future execution dispatch must name its sole RE-VM
custodian. Design ownership is only this amendment and minimal work-item/input
updates; no bootstrap is created or run during design. The future implementation
owns only `bootstrap-v9.json`, `bootstrap-v9-result.json`, `VALIDATION-V9.md`
and authorized work-item/input state updates. No shared ledger, roadmap,
support, dependency, kernel or device file belongs to that implementation.

Before any guest execution, freeze `bootstrap-v9.json` containing the complete
independent source, source SHA-256, dispatch commit, dispatch-input digest,
all accepted identities, UTC freeze time, exact mode/argument schema and
`preflight_runs_permitted: 1`, `analysis_runs_permitted: 0`. Independently
verify the complete container digest and record it outside the container in
the result. Host AST/compile-only review must precede execution; do not run
the source against a fixture or another binary. The sole future command is
`/usr/bin/python3.12 -I -S -B - preflight` through `./scripts/dev-vm re-shell`,
with the inherited no-download/network/debuginfod/bytecode controls.

V9 has only this preflight mode. Reject absent/other modes, extra arguments,
method descriptor/input, callback or private path before package entry. Remove
the analysis branch and private/method/callback entry functions from V9; do
not retain an invocable dormant analysis route. No result of this amendment
may create `method.json` or enable an analysis child. The earlier two-mode
contract is not silently renewed by a successful tools-preflight.

## Inherited boundary and exact insertion

Preserve V8's helper import statements and ordering exactly: its initial
`sys`, followed by the frozen `os` through `importlib.machinery` imports and
`email.parser.Parser`. Add no helper warm-up, extension preload or package
import there. Require `_queue` absent from `sys.modules` after helper startup
and from every file-backed map snapshot before its explicit preload. Retain
the irreversible audit hook before discovery, isolated Python 3.12.3 checks,
installed-root/source-rights rules, source-forced loader/finder, inert-asset
and bytecode refusals, and every pre-entry containment/uniqueness predicate.

Complete both installed inventories (25 Capstone plus 52 pyelftools sources,
77 mapped sources) and their pre-import drift before any package body enters.
Keep the exact Capstone 4.0.2 import/native-primary/`DT_NEEDED` closure and
resource preload unchanged. Keep the exact pre-entry resource AST join and
one separately owned `os.sysconf("SC_PAGE_SIZE")` reference, including its
unchanged guarded state and map checks. No package discovery is allowed after
the common entry gate; each demanded mapped source may enter once within 77
entries, and every entered body must complete on success. Do not require every
mapped source to be demanded.

Insert the new queue route **after** `page_size_reference()` returns and
**before** setting the pyelftools owner, installing the resource profile or
executing the top-level pyelftools import. At insertion require: no earlier
refusal; original import function still installed; resource state `none`;
one resource spec/create/exec/extension event; zero cached-resource requests
and resource function events; one completed page reference; optional-route,
engine, method-pipe, callback and private counters zero; all entered Capstone
bodies complete; and no pyelftools body entered.

## One bootstrap-owned ordinary queue preload

Embed the exact module `_queue`, event digest
`1f44854434c4d88a28f07834aff0629e5de462ee8cbbb3a6a6d3cd9245e56cf1`,
accepted Amendment 22 and 23 result digests, and this identity:

- path `/usr/lib/python3.12/lib-dynload/_queue.cpython-312-aarch64-linux-gnu.so`;
- content SHA-256
  `0ab94b7c54af74d78b85b00bea6527e4dffc56304625995b0016429defe8edba`;
- full stat tuple `(device, inode, mode, nlink, size, mtime_ns, ctime_ns)`:
  `(64769, 8678, 33188, 1, 68496, 1781873160000000000, 1785067980603724344)`;
- exact four permission/offset rows: `r-xp/0`, `---p/16384`, `r--p/61440`,
  `rw-p/65536`, all device `253:1`, inode `8678`.

Use Amendment 23's twelve ordered queue stages and predicates, with a distinct
bootstrap owner `stdlib-queue`. Save the live path/meta-path/path-hook objects
and their element identity/order at this insertion; they include the already
installed terminal finder. Do not compare their process-local identities to
Amendment 23's other process. The finder must fall through for `_queue` without
creating a substitute spec, loader or module.

Take two direct counted `os.lstat` snapshots before and two after import, all
equal to the accepted tuple. While the narrow queue audit overlay is active,
admit only one baseline and one post-import read-only `/proc/self/maps` open,
and the exact five-field `_queue` import events during the single request:
at most one absent-filename discovery event followed by exactly one extension
event with the exact path. Search fields must be absent or match the frozen
live objects/element order. All other events are counted refusals, including
candidate content opens, other imports, `ctypes.dlopen`, writes, mutations,
network and process operations. No inherited broad read rule may bypass this
overlay.

The counted wrapper must delegate exactly once to
`ORIGINAL_IMPORT("_queue", None, None, (), 0)` and reject every other request
before delegation. Restore and verify the exact original import object in
`finally` immediately after return/exception, before post-return audit checks.
Record one call/delegation, zero rejected calls, one extension event, discovery
count zero or one and all forbidden counters zero for success. A cached
preload return or missing extension event is refusal.

Require the returned object is the unique exact module object in `sys.modules`,
with exact name, empty package and exact file; its unique exact `ModuleSpec`
has matching name/origin and shares the module's exact `ExtensionFileLoader`
object. Freeze these live objects for the remainder of this process without
enumerating module attributes, invoking a queue API or modifying the loader.

Both new map snapshots use the strict Amendment 23 grammar and
512 KiB/256-row/1,024-byte-row bounds. Retain only bounded internal rows.
The baseline path set and permission/offset rows must match the last inherited
post-page-reference map state. The post snapshot must preserve every baseline
file-backed device/inode/permission/offset row, add only the exact candidate
with its four accepted rows, and preserve the exact full vDSO row. Keep V8's
32-pseudo-row/128-file-component caps and nonexecutable-pseudo-map policy.
Do not publish or hash virtual addresses or unrelated raw rows.

On complete queue-stage success, extend both V8's `after` file-identity
dictionary and `RESOURCE_BASE_MAP` by only the frozen candidate identity;
extend `RESOURCE_BASE_ROWS` by its exact rows. This is the explicit new baseline
for the later resource `c_call` observer and post-pyelftools/engine/final
checks. Do not replace the pre-reference baseline or repeat the page reference.
Exit the narrow overlay only into the inherited guarded decoder phase; the
irreversible audit hook stays active.

## Cached environment and complete tools-preflight

Continue the original source-forced pyelftools import with the original
resource caller-tuple/AST/cached-object and `getpagesize` profile protocol.
It must return normally, set and retain exact bounded `PAGESIZE` equal to the
reference, and complete every entered mapped body. Keep resource counts one
each for lookup/create/exec/extension/cached request/function call/return,
zero exceptions, and final state `returned`. Its pre-call maps must equal the
explicitly queue-extended baseline, not the earlier queue-absent baseline.

The inherited wrapped pyelftools-import interval may forward cached requests
for exact `_queue` at level zero; do not synthesize a caller or require a
literal package join. Count at most eight such requests prospectively, with
fromlist an empty tuple or at most eight unique bounded ASCII identifiers
(no star, dotted name or submodule); globals/locals must be `None` or ordinary
dictionaries. Before and after each delegation require the frozen module/spec/
loader objects unchanged and no `_queue` audit event. Publish only the count
and closed identity booleans, never globals, caller data or member values.
Zero cached requests is acceptable: success does not prove pyelftools requested
the extension. This counter covers only that wrapped interval, not arbitrary
cached imports elsewhere. Outside the sole preload, every `_queue` audit
event or other new extension load is refused, even if a cache check was passed.

Restore the inherited import function immediately after the top-level import
as V8 does. Construct/configure exactly one existing Capstone ARM64,
little-endian, detail-enabled engine and retain the original optional-route
refusal/count checks. No second engine, `ELFFile` instance, parser over any
input, analysis method, callback or private opener is admitted. The source-
forced module bodies and this original engine lifecycle are the only package
execution admitted; do not add direct `_queue` API calls or claim general
purity of imported code.

At post-pyelftools, post-engine, named restoration and final completion, require
the same queue module/spec/loader identities and accepted candidate rows. No
module deletion/replacement, spec/loader replacement, second initialization
or candidate unload/reload is admitted. All file-backed maps after queue
preload must equal the extended baseline; no new native or executable-pseudo
mapping is allowed. Preserve V8's exact component/source/stdlib/package final
drift and named restoration, adapted only for the added candidate below.

## Explicit content and operation budget

The queue preload itself has **zero candidate content opens** as in Amendment
23. Later V8 `maps()` and final-component checks rehash file-backed components;
this amendment explicitly admits those reads of the exact candidate and does
not pretend they are covered by Amendment 23's standalone budget.

Preserve V8's per-map-row identity-check multiplicity: four candidate identity
checks at each of `resource-c-call`, `post-pyelftools`, `post-engine` and
`final`, plus one candidate identity check in its explicit final-component
drift. Require exactly four accepted candidate rows before those per-row
checks; refuse overflow before any excess read. This is exactly **17** new
candidate content opens/reads on success, not a general installed-root grant.
Every such identity check must use one counted read-only open, matching full
tuple `lstat` before/opened `fstat`/post-read `fstat`/final `lstat`, one bounded
read of at most 1 MiB plus one byte reaching EOF at 68,496 bytes, and matching
SHA-256. Use direct counted `os` metadata, not hidden `pathlib` operations for
these new checks. No ELF/dependency reparse or extra candidate read is needed.

The successful new candidate totals are: `lstat=38` (four preload plus twice
17), `fstat=34`, `content_open=17`, `content_read=17`; preload-wrapper
calls/delegations `1/1`; cached wrapped requests `0..8`; discovery `0..1`;
extension event `1`; all candidate refusal/effect counters zero. Count each
attempt before operation/delegation and refuse overflow immediately. Refused
paths report actual partial counts without pretending success totals occurred.

Keep the original eleven preflight maps stages and add only the two queue
snapshots: **13 maps opens/reads** on success. Apply the strict byte/row bounds
above to every snapshot while retaining all original V8 mapping predicates.
The sequence is `stdlib-baseline`, `pre-import`, `post-capstone`,
`pre-stdlib-resource`, `post-stdlib-resource`, `pre-page-reference`,
`post-page-reference`, `queue-baseline`, `queue-post`, `resource-c-call`,
`post-pyelftools`, `post-engine`, `final`. Extra maps reads are refused.
Do not add maps reads inside cached-request or restoration checks; reuse the
last completed exact state there and perform the mandatory final snapshot.

Retain and publish V8's existing asset opens by phase (28 initial, 28
pre-import, zero pre-analysis, 28 final), exact native requests one, optional
requests one after engine, and zero write/cache/network/process attempts.
Other inherited inventory/source/stdlib/resource reads keep their frozen V8
call sites and bounds; the new 17-open capability cannot cover them or an
unrelated file. Do not claim the candidate counters enumerate all process I/O.

## Refusal, restoration, output and stop

Use this closed ordered outer stage list: `startup`, `initial-inventory`,
`pre-entry-static`, `pre-import-drift`, `capstone-import`, `capstone-closure`,
`resource-preload`, `page-reference`, `queue-preload`, `pyelftools-import`,
`pyelftools-identity`, `engine`, `post-engine`, `named-restoration`,
`component-drift`, `final-tree-drift`, `final-maps`, `final-stdlib-drift`,
`final-restoration`, `final-counters`. Within `queue-preload`, use exactly
Amendment 23's ordered `lexical`, `pre-lstat`, `baseline-maps`,
`import-wrapper`, `import-restoration`, `import-audit`, `module-object`,
`module-spec`, `post-lstat`, `post-maps`, `mapping-delta`, `final-counters`.
Record the first failing outer stage and nested queue stage when applicable;
retain the active map stage and candidate-read ordinal for a bounded read
failure. The source must assign the stage before each bounded operation and
retain the first failure.
Every false predicate, exception, audit/wrapper refusal, drift or overflow is
terminal `refused`; mark the remaining normal-execution suffix
`not-evaluated`. Use a payload-free dedicated `BaseException` for new terminal
guards, check the irreversible refusal latch at every mapped-source/import
boundary, and do not allow a package catch to resume after a refusal.

Always attempt the applicable named restorations separately from the terminal
normal stage sequence: original import and native-load objects, exact saved
meta-path/finder and isolated path, and both resource loader methods. Verify
the original profile was restored (one restoration event when the profile was
installed; otherwise verify it unchanged without calling `sys.setprofile`).
For success, count exactly two zero-argument `sys.setprofile` audit events:
one installation at `pyelftools-import` and one restoration at
`final-restoration`. Any other such event is refusal. A refused path may
attempt the sole restoration only if its installation occurred; the cleanup
receipt records that separate attempt without advancing the normal stages.
Record each attempted/not-applicable/failed restoration and closed booleans;
do not let one failed cleanup suppress other safe named restorations or replace
the first refusal. No drift/content/maps read is permitted solely for refusal
cleanup. No module unload or `sys.modules` deletion is a restoration action.
The irreversible audit hook remains installed; interpreter exit, followed by
closing the RE shell and releasing custody, is the native/module cleanup
boundary on both success and refusal.

Write only the frozen container, `bootstrap-v9-result.json` and
`VALIDATION-V9.md`, plus authorized work-item/input state pins. The result
must carry source/container/dispatch/dependency and accepted-event identities,
UTC chronology, one-run count, ordered stages, first closed refusal class,
restoration results, inherited sanitized tool identities and exact counters,
closed queue module/spec/cache predicates and address-free candidate rows.
Hash the canonical receipt losslessly; record result file SHA-256 in the
document. Preserve original integer values and raw receipt text privately.
Never publish raw map rows, unrelated path sets added by the queue observer,
object pointers, attribute lists, exception text, private paths or bytes.

Only all gates, counters, restorations and final drift passing may report
`tools-preflight-only`. A refusal exposes no partial successful queue/tool
identity claim, though prior accepted evidence remains valid. Explicitly set
method/callback absent, engine count as observed, private reads zero, and
`analysis_admitted: false`. The receipt proves only this preloaded environment's
import/engine lifecycle; it does not prove a `_queue` package caller, general
package usability, queue API behavior, repeatability or retained-binary facts.

Before future execution, verify pins, syntax/AST, no dormant private route,
exact one-engine/one-preload call sites, all stage/operation budgets and source
differences against V8/A23. Afterward verify source/result/canonical digests,
chronology, schemas, counters, restoration/authority fields, local links,
privacy/license and whitespace without rerunning. Any source/interface
ambiguity, conflicting evidence or required scope change stops implementation
before execution and returns evidence, attempts, unresolved question and the
next discriminating check. A refusal consumes the one preflight budget and
must not be repaired by another run. Stop at this handoff; no automatic method,
private analysis, acquisition, network, device operation or build follows.
