# A33: exact implementation and namespace closure for the recovery observer

Design parent: `af58842a9beb22972527f6bd7d26d8f2214b0608`.
Published A32 input/work-item snapshots have SHA-256
`c733c83f942a2cafb6f49d4d7dd3e7e6d6b045fa4b96be5762440e48ac32cb18` and
`f2a1f18bef95334f9122df7b09a1ca02058fbf574fd58a2774595c954ed9f649`.
[AMENDMENT-32.md](AMENDMENT-32.md) remains immutable, SHA-256
`5ab561c0bcb7b701eeb55794a98248fe6481c6990cfa863ca6a1b93871f77c9c`.

Astra Medium `/root/runtime_identity_specialist` owns the import-closure
uncertainty; Sol Medium independently reviews; `/root` integrates and records
workflow measurement. Ownership is this amendment and minimal
[WORK_ITEM.md](WORK_ITEM.md)/[inputs.json](inputs.json) state updates, restored
from published A32 rather than promoting rejected construction state.
The unrelated AGENTS.md edit is preserved. This contract-only dispatch removes
the rejected untracked observer container; it creates no source candidate,
fixture, result or verifier. No observer/CPython-source execution, VM, private
evidence, device, build, commit or push is admitted.

## Rejected constructions and exact supersession

Three source-only freezes were independently rejected, never executed or
accepted for publication. Hashes below identify rejected bytes, not candidates.

| Freeze | Source SHA-256 | Container SHA-256 / bytes | Rejection |
| --- | --- | --- | --- |
| Original A32 construction | `9b0cf8a41a803f55d6b79b237b70306612a7f358205e801e99a36dfb7a3ad2f8` | `63f2042fdfab255bde7b89dd9dfca8a5ed6216811de57b8939c8286d68903b54` / 60303 | Missing live-link metadata checks on association paths. |
| Luna repair | `2703c5363e01f92a33e4c7cf1b9bf7fef54bba15e27a956ac57f49765e6d965a` | `7324825641a416e74de21323324318ee29601553b58cec1d311f02ad28420687` / 61926 | Live-link checks repaired; complete deadline checkpoint placement remained unproved. |
| Astra deadline repair | `e7d406b8dc8868cac46ed06114e4e42d622db8ce3531742250f31cb78ffd24d5` | `54c7578e944ac6dc01a0634d8c94f97d6526042d46f23f9ebe10b36a21a0ee9b` / 87276 | Closed imports omitted built-in `_stat`, which frozen `stat` imports. |

The last source was 25308 UTF-8 bytes. Its untracked
`recovery-observer-v1.json` is removed, not rebound to A33. These rejections
consumed no recovery access or observer-process budget. Prior source checks
are historical construction checks, not successful runtime evidence.

A33 supersedes only A31's closed import/namespace/origin definitions and
clarifies their source-review acceptance. Initially, the authorized correction
was `_stat` only. Tagged-source inspection also found that `os` creates the
`os.path` namespace key; the old new-key guard would reject it if absent at
startup even though its implementation is already admitted `posixpath`.
Work stopped for scope clarification. The coordinator then explicitly admitted
that exact alias, with no other dependency, alias or event expansion.
All A31/A32 object acquisition, metadata, privacy, transport, count, byte,
deadline, receipt, authority and custody rules remain in force.

## Tagged primary-source evidence

The official CPython tag `v3.12.3` resolves directly to commit
`f6650f9ad73359051f3e558c2431a109bc016664`, not an annotated tag object.
The [official ref API](https://api.github.com/repos/python/cpython/git/ref/tags/v3.12.3)
response retrieved for this dispatch was 339 bytes, SHA-256
`8c645652955502a79ee2a040372fa1d911372c1487d19415cfd88293d765d98f`.
Each source below was fetched from both the tagged raw URL and the exact-commit
raw URL; byte counts and SHA-256s agreed pairwise. Canonical tagged and pinned
raw URLs are listed explicitly. The tagged raw counterpart replaces the pinned
commit component with `v3.12.3` in that exact raw URL.
Retrieval used bounded HTTPS reads (20-second request timeout, at most
1000000 accepted bytes per source), in-memory hashing and static text/AST
inspection only. No source was imported, executed, installed or retained as
a vendored file. These are upstream-source identities, not a new measurement
of guest interpreter bytes or proof of downstream build configuration.

| Tagged canonical source / pinned raw bytes | Bytes | SHA-256 |
| --- | ---: | --- |
| [Lib/os.py](https://github.com/python/cpython/blob/v3.12.3/Lib/os.py) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Lib/os.py) | 39786 | `316d1b7307fd851bded3423c9d437e0a383c725d993f0fcff2e8b749fe560b62` |
| [Lib/stat.py](https://github.com/python/cpython/blob/v3.12.3/Lib/stat.py) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Lib/stat.py) | 5485 | `052af0327eae6941b69b05c088b3e748f79995635f80ac4cc7125eb333eb4c77` |
| [Lib/posixpath.py](https://github.com/python/cpython/blob/v3.12.3/Lib/posixpath.py) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Lib/posixpath.py) | 17564 | `8396232224e1b9df7896a32980046825b64c00bb010ddd2a4ccc23fe4fbfe262` |
| [Lib/abc.py](https://github.com/python/cpython/blob/v3.12.3/Lib/abc.py) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Lib/abc.py) | 6538 | `e558702a95cdce3febd289da021715d2b92bc43995b8a1bc58dfa1c3d8010287` |
| [Lib/_collections_abc.py](https://github.com/python/cpython/blob/v3.12.3/Lib/_collections_abc.py) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Lib/_collections_abc.py) | 32082 | `90324ee3e1c4ca5319f7242d4b7c1e90eb8418b3f999d07c853aa488356282e6` |
| [Lib/genericpath.py](https://github.com/python/cpython/blob/v3.12.3/Lib/genericpath.py) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Lib/genericpath.py) | 5301 | `6a271770c5e0c0a594075cc0063c807421fac3474df05d91a01c91d12c36eb5f` |
| [Modules/Setup.bootstrap.in](https://github.com/python/cpython/blob/v3.12.3/Modules/Setup.bootstrap.in) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Modules/Setup.bootstrap.in) | 919 | `d7a4c34c97f414585c7e8480c106a0f85075fb166d4c82a91c5b0b00df455271` |
| [Modules/Setup.stdlib.in](https://github.com/python/cpython/blob/v3.12.3/Modules/Setup.stdlib.in) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Modules/Setup.stdlib.in) | 8108 | `9e305741899860a69787fb68356cc86fa7b71d8ab12ba0187e006f85fe8ab177` |
| [Modules/config.c.in](https://github.com/python/cpython/blob/v3.12.3/Modules/config.c.in) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Modules/config.c.in) | 1752 | `5c76ef60a799f420b09b047dc1087728e5ed08ba82f6c7664c4d4f1d1d715b21` |
| [Python/frozen.c](https://github.com/python/cpython/blob/v3.12.3/Python/frozen.c) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Python/frozen.c) | 8283 | `ff2d5e301f1725c013788f30882fd48127a9ecfe891bfaa592cc08c284d4f79f` |
| [Tools/build/freeze_modules.py](https://github.com/python/cpython/blob/v3.12.3/Tools/build/freeze_modules.py) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Tools/build/freeze_modules.py) | 24739 | `e41c913ae5b0cbec0b3051a175978d9bb52905a796beff2dec447fc666fd2641` |
| [Python/import.c](https://github.com/python/cpython/blob/v3.12.3/Python/import.c) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Python/import.c) | 111633 | `8b0473e3972d22ed745e44fb3c61d34328e4cd9813e22dd8f4f4d818fc4410c7` |
| [Lib/importlib/_bootstrap.py](https://github.com/python/cpython/blob/v3.12.3/Lib/importlib/_bootstrap.py) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Lib/importlib/_bootstrap.py) | 57056 | `9653944363a4773cc32bbb34426024597a9d2ee4cd42e7912b4daf8cadfb53ed` |
| [Modules/_stat.c](https://github.com/python/cpython/blob/v3.12.3/Modules/_stat.c) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Modules/_stat.c) | 15551 | `d0143089e529221faa379310a9afe733db62468b7c6949ed7f4207d6396027c6` |
| [Modules/timemodule.c](https://github.com/python/cpython/blob/v3.12.3/Modules/timemodule.c) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Modules/timemodule.c) | 64172 | `55ee3d5dfaab9ef4044f7537749ba1d4b17b8dc55796763ed65e4a3383075607` |
| [Modules/_abc.c](https://github.com/python/cpython/blob/v3.12.3/Modules/_abc.c) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Modules/_abc.c) | 26614 | `d62c93b997f251f0f2be7297fa392314e5c815ed279aa9ad00968745051126d4` |
| [Modules/posixmodule.c](https://github.com/python/cpython/blob/v3.12.3/Modules/posixmodule.c) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Modules/posixmodule.c) | 457007 | `8e55414e8f48d56180a4024f1ce659ebefefbeee7e5ce7a56b7cfa25108c225c` |
| [Modules/makesetup](https://github.com/python/cpython/blob/v3.12.3/Modules/makesetup) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Modules/makesetup) | 9312 | `0615264cbe9f3a4fce27de0054839ea814f2fe6f6091a0e17b18b5b15c665cfa` |
| [Python/marshal.c](https://github.com/python/cpython/blob/v3.12.3/Python/marshal.c) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Python/marshal.c) | 52334 | `b57cddb10515803695728f4c110436ab8fc44bb2f45342775740892ab2d18505` |
| [Programs/_freeze_module.c](https://github.com/python/cpython/blob/v3.12.3/Programs/_freeze_module.c) / [raw](https://raw.githubusercontent.com/python/cpython/f6650f9ad73359051f3e558c2431a109bc016664/Programs/_freeze_module.c) | 6530 | `95db9db1bddfc6c62ad85f846df01a82e2dd1f2dad59dc845ab4e9d2a133b011` |

## Implementation closure and excluded branches

Require exactly these eleven implementation identities after the explicit
`sys`, hook installation, `os`, `stat`, `time` sequence:

| Origin | Exact implementation names |
| --- | --- |
| built-in | `sys`, `time`, `posix`, `_abc`, `_stat` |
| frozen | `os`, `stat`, `posixpath`, `genericpath`, `abc`, `_collections_abc` |
| Alias only, not another implementation | `os.path` must be the identical object as `posixpath` |

At `Lib/os.py:25-29,50-68,95-97,670`, the Linux/posix initialization
imports `abc`, `sys`, `stat`, `_collections_abc`, `posix`, and
`posixpath`; repeated imports do not create new implementations.
`Lib/abc.py:85` imports built-in `_abc`.
`Lib/stat.py:192-195` attempts the built-in `_stat` star import.
The fallback that catches ImportError must not hide an audit refusal or permit
success without `_stat`: the hook's sticky failure and the mandatory final
implementation checks both remain required.
`Lib/posixpath.py:25-29,374` imports `os`, `sys`, `stat`,
`genericpath`, and `posix`'s native normalization function.
`Lib/genericpath.py:6-7` imports `os` and `stat`.
`Lib/_collections_abc.py:35-36` imports `abc` and `sys`.
Cycles revisit already-initializing modules; they do not authorize another name.

The Windows `nt`/`ntpath` branches, `abc`'s `_py_abc` fallback, and
function-local `warnings`, `pwd`, `re`, `io`, `subprocess`,
`resource`, and `_strptime` routes are not admitted. The relevant C module
initializers in `Modules/_stat.c`, `Modules/_abc.c`,
`Modules/posixmodule.c`, and `Modules/timemodule.c` introduce no extra
Python implementation import on this initialization path. The selected later
observer calls must still exclude functions that activate deferred imports.
Native initialization is not an attested no-read/no-effect sandbox.

`Modules/Setup.bootstrap.in:6,11,23,28,32` places `posix`, `time`,
`_abc`, `_stat` in the static bootstrap list.
`Modules/makesetup:25-29,309-322` inserts initialization entries into
`Modules/config.c.in`'s `_PyImport_Inittab`; that template also contains
the special `sys` entry. `Modules/Setup.stdlib.in` does not replace those
entries with filesystem extensions. This is the tagged build recipe, not
proof of the guest's build choices.
`Tools/build/freeze_modules.py` selects the six frozen implementations;
`Python/frozen.c:103-118` registers them with static code getters and
registers the additional `os.path` alias. Its alias table maps to
`posixpath`. `Programs/_freeze_module.c:123-128` establishes
the exact frozen-code filename convention.

## Import events, alias semantics and startup boundary

`Lib/os.py:95` assigns `sys.modules["os.path"] = path` after importing
`posixpath`; the next statement imports constants from that existing alias.
`Python/import.c:2850-2865` first retrieves the module cache entry; a present,
non-null initialized module bypasses `import_find_and_load`.
The `import` audit event is inside `import_find_and_load` at lines
2746-2753, not on that cache-hit path. The nonpackage from-list path at
2924-2936 returns the module without loading children.
`Lib/importlib/_bootstrap.py:1349-1360` corroborates the initialized-cache
shortcut. Therefore the already-installed alias requires **no import audit
event**, no separate execution event, and no `<frozen os.path>` allowance.
Do not add `os.path` to the import-event allowlist merely because it is an
allowed namespace key. A requested event for that alias is a refusal, not a
fallback through its frozen registration.

During imports, the only permitted `import` event has five arguments:
the exact string implementation name from the eleven-name set, filename
`None`, and the live `sys.path`, `sys.meta_path`, `sys.path_hooks`
objects by identity in positions 2, 3, 4. Require those live attributes to
exist with their expected list shape; do not inspect, emit or resolve their
contents. Missing attributes/None substitutions, wrong arity/type/name,
a filename or a substituted object refuse. No extension-load event shape is
admitted. A cache hit may emit no event; do not require an invented full event
trace for startup-preloaded helpers.

Permit `exec` only with exactly one code object whose filename is one of
`<frozen os>`, `<frozen stat>`, `<frozen posixpath>`,
`<frozen genericpath>`, `<frozen abc>`,
`<frozen _collections_abc>`. Built-ins need no Python code exec.
All opens, other imports, other execs, compile/eval and other unexpected
events remain denied; do not inspect event payload bytes.
FrozenImporter uses `_imp.get_frozen_object` then `exec`
(`Lib/importlib/_bootstrap.py:1172-1176`).
The tagged main-interpreter route uses `Python/frozen.c`'s non-null
GET_CODE registrations and returns static code in
`Python/import.c:2078-2085`, without unmarshalling.
The alternative marshalled/subinterpreter route would cause
`marshal.loads` (`Python/marshal.c:1516-1519,1629-1642`) and is
**not admitted**. No marshal event allowance is added; an unexpected runtime
build/path refuses. This is an upstream inference, not execution confirmation.

Freeze three separate sets: implementation/import-event names (eleven);
frozen exec filenames (six); and permitted new namespace keys (those eleven
plus `os.path`). Never infer implementation spec names from alias keys.
Before imports, retain the existing bounded startup key snapshot; after
imports, reject any newly added key outside that exact twelve-key set.
Require all eleven implementations to exist at their exact cache keys, even
if already startup-loaded, with exact spec name and expected origin. Check
the actual module object/type, not an arbitrary object exposing those strings.
The alias must exist and satisfy
`sys.modules["os.path"] is sys.modules["posixpath"]`, with
`os.path` the same object. Validate that object's `posixpath` spec/origin
once through the implementation entry; never demand spec.name `os.path`.
Reject missing/None/wrong-target aliases and inconsistent cache/spec identities.

`Lib/_collections_abc.py:59` deliberately assigns its internal `__name__` to
`collections.abc`; its cache key and spec.name remain `_collections_abc`.
This assignment creates no import event, additional sys.modules key,
implementation or admitted dependency. A final consistency check caught the
draft-only uniform module.__name__ requirement; work paused and the coordinator
approved removing that newly invented constraint. Do not conflate internal
`__name__` metadata with cache/spec identity, and do not add `collections.abc`
to any allowed import, namespace or execution set.

These metadata checks cover all closure members regardless of startup
presence, but they do not retroactively attest startup events, byte identity,
or every preloaded module. Existing unrelated startup keys remain outside this
closure validation and do not become admitted later imports. Preserve the
256-key cap and trusted startup qualifications. Seal all imports before
observation. Source review, not the audit-event name alone, establishes the
reachable callgraph and narrow trusted-code boundary.

## Preserve link checks and full deadline design

Carry forward the successful live-metadata repair as a design requirement,
not accepted runnable code: selected metadata includes bounded `st_nlink`;
require a positive link count before accepting matched directories/raw-file
identities, selected process metadata, and every followed cwd/fd target.
No missing/disappearing/deleted or malformed target becomes zero or a
nonmatch. Retain all A32 type/owner/device/inode comparisons, ambiguity refusal,
bounded process recheck and race limitations.

Carry forward the full deadline-placement design from the rejected third
freeze: set the inner monotonic 30-second deadline immediately when the admitted
time helper is available at observation entry; the outer 30-second limit
also covers startup/import/transport. Check before every potentially
state-observing or expanding operation, every streaming iterator advance,
each processing/parser/comparison loop iteration, and each metadata/scalar
validation path; shared checked iteration must actually mediate every such
reachable loop. Explicitly cover runtime/encoding/TTY/UID/helper-origin checks,
the interpreter stat, directory/process/fd acquisition and stat/fstat/scandir
calls, both bounded generated-stat reads, tuple matching and process recheck.
No parser, alias/origin-validation or helper path may bypass the checkpoints.
Finite fixed-size operations retain byte/count reservations and overflow gates.

Deadline detection stops new observation; it does not preempt a blocked native
call or prove timely process exit. Retain the special bounded owned-resource
cleanup and fixed-schema refusal serialization paths after a deadline:
they must not be prevented from releasing owned descriptors by an already
expired observation checkpoint. They add no metadata acquisition, follow,
content read, retry, reconnect or signal. Serialization remains bounded by
the unchanged receipt/stream caps, not permission for an unbounded loop.
The independent outer pipe/deadline/exit uncertainty and cleanup-failure
rules remain A31; do not claim an in-process checkpoint is a hard timeout.

## Future source review and mutation requirements

After independent A33 review and publication, only a new explicit construction
dispatch can produce a new observer freeze. Preserve A31/A32 source-first,
compile-only optimization 0/1/2, AST/literal round-trip, unresolved-name,
closed-callgraph/I/O and independently reviewed publication requirements.
No observer or fixture execution is part of those compile/static checks.

Require assert-free static normal/-O mutations with semantic enclosing hashes rebound;
digest mismatch alone is not evidence of a semantic guard. Individually
remove every one of the eleven implementation entries and every one of their
mandatory identity/origin checks, including preloaded and nonpreloaded cases;
mutate each expected origin, cache/spec name and module object type; bypass the final required
presence loop; and demonstrate rejection. Individually remove each frozen
exec filename and broaden each import/exec/event-shape gate; reject the change.
Mutate sticky audit-failure handling so caught `stat` ImportError cannot
conceal an earlier forbidden import.

Alias families independently remove its allowed namespace key, remove or
bypass the alias check, substitute another admitted module as target, change
the target origin, accept spec.name `os.path`, add another alias, or admit
an `os.path` import/exec event. Each must be rejected; correct startup
presence must not bypass the identity check. Include wrong event arity,
filename, path-object identities, object type, unexpected namespace keys,
marshal fallback and non-frozen source/extension attempts.
Reject a mutation that substitutes module.__name__ for cache/spec validation
or admits `collections.abc` because of that internal metadata assignment.
All these are future mutation requirements, not a claim that tests ran now.

Retain and individually mutate all live-link callsite checks and the complete
deadline-placement inventory, including helper/iterator/parser omissions and
the cleanup-after-deadline distinction. Keep all earlier descriptor-role,
no-follow/procfs-follow, bounds, privacy, receipt, false-authority, transport
and custody families. A source-only review must reject another unproved
dependency, alias, event shape, native route or missing checkpoint; do not
repair by executing the observer to discover the closure.

Future source/result bindings add this amendment's externally recorded SHA-256
alongside A30/A31/A32 and the transport bindings. No existing result or verifier
is rewritten now. Preserve all A28/A29/V9/V10/source/method pins.
The host result's receipt/status/null/authority schemas otherwise stay closed.

## Handoff and remaining uncertainty

Checks for this dispatch: tagged/commit source identity comparison, static
import/registration/cache-event analysis, JSON/pin/local-link/privacy checks,
`git diff --check` and the repository host-only gate. Record actual outcomes
in the handoff. No observer compile, fixture, runtime, VM, transport, device or
kernel test is claimed for this contract-only turn.

A29 stays consumed (`attempts=1, remaining=0, rerun_admitted=false`).
Recovery access and observer-process budgets each stay
`attempts=0, consumed=false, remaining=1`, explicitly unadmitted.
Every eventual recovery outcome leaves A29 custody unresolved; association
is not attribution, log custody, termination/deletion authority or closure.
Source inspection establishes the upstream intended closure; guest build
conformance, runtime feasibility and metadata availability remain unmeasured.
Independent Sol design review and integrator publication are the handoff,
not source-construction or execution authorization. Stop on any further scope
change or conflicting evidence and return evidence, attempts, the unresolved
question and next discriminating check. Credits remain unavailable.
