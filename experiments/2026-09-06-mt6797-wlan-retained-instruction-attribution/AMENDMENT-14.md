# Resource-callsite terminal diagnostic amendment

This fourteenth prospective amendment resolves only the unidentified resource
function attempt in [VALIDATION-V7-REFUSED.md](VALIDATION-V7-REFUSED.md).
`bootstrap-v7.json` and its refusal record remain immutable. V7 proved the
exact standard-library extension preload and cached `resource` reuse within the
still-running pyelftools import, then refused one function attempt before an
engine, callback, method or private read. The single private analysis remains
unused.

Python 3.12 documents a `sys.setprofile` `c_call` event as occurring when a C
function is about to be called and says its `arg` is that function object; see
<https://docs.python.org/3.12/library/sys.html#sys.setprofile>. This amendment
authorizes one no-private terminal diagnostic that identifies that exact
object and its frozen-source callsite at the documented pre-call boundary. It
does not authorize the function to execute or classify its effects as safe.

Before the diagnostic, pin and verify in [inputs.json](inputs.json) the exact
SHA-256 values of this amendment, the amended [WORK_ITEM.md](WORK_ITEM.md), all
earlier amendments, every earlier bootstrap/refusal record and every mapping-
diagnostic trio at its explicit dependency path. Reject drift.

## Frozen source inventory and event join

Create and freeze `resource-callsite-diagnostic-v1.json` with the complete
independently written source and embedded SHA-256 before first execution. Run
it exactly once with `/usr/bin/python3.12 -I -S -B` through the approved RE-VM
shell. The irreversible audit hook must precede metadata discovery and remain
active through exit.

Reproduce the Amendment 13 common 77-module pre-entry inventory, Capstone
import/native closure, and Amendment 12 exact `resource` preload. Before
entering pyelftools, parse all 52 exact frozen pyelftools sources without
executing them. Enumerate at most 16 direct AST calls whose callable is an
attribute rooted at the exact module binding established by `import resource`
or an exact binding established by `from resource import NAME`. Record only
module name, exact frozen source identity, call line/end line/column, import
binding form and bounded literal attribute name. Refuse star imports, rebinding
or deletion of a resource binding, dynamic attribute access, alias ambiguity,
more than 16 candidates or an unbounded/nonliteral name. This inventory is
candidate evidence, not execution or a call claim.

Require the initial profile function to be exactly `None`, then install a
dedicated profile function immediately before the already-inventoried
pyelftools import. Ignore every event except `c_call` whose function object has
exact `__module__ == "resource"`. At the first such event, require:

- exact bounded ASCII `__name__` and identity equality with exactly one entry
  of the frozen `resource` module dictionary;
- the caller frame's module and canonical filename equal one exact frozen
  pyelftools source, and its current line be contained by exactly one enumerated
  direct-call candidate for the same resource binding and callable name;
- no earlier resource-function event, engine, callback, method, private read or
  forbidden operation; and
- exact resource module/object/file identity, route counters and file-backed
  mapping dictionary remain equal to the accepted post-preload state.

Construct one bounded `first_callsite` record from only those validated fields,
encode it immediately as canonical UTF-8 JSON, retain its SHA-256, set an
irreversible terminal latch and raise a payload-free dedicated `BaseException`
before returning from the `c_call` observer. Do not invoke the function object,
read its representation, inspect a return value, or allow pyelftools import to
complete. No `c_return` or `c_exception` for the latched object is admitted.

Python documents that an error raised by the profile function unsets it, so do
not require or accept a later profile event. Catch only the exact dedicated
signal outside the interrupted top-level import, require the terminal latch and
`sys.getprofile() is None`, and make each still-active source-loader completion,
wrapped-import completion and outer-import-return boundary re-raise or refuse
while latched. The exact outer handler must reject normal return, another
exception class or an absent latch; it must not resume package execution.

In a fixed top-level `finally`, attempt and independently verify all seven named
restorations: initial profile function, original import object, Capstone native-
load endpoint, terminal finder, isolated path, and the resource loader's exact
original inherited `ExtensionFileLoader.create_module` and
`ExtensionFileLoader.exec_module` endpoints temporarily overridden on that
loader instance for the resource preload. Attempt every
restoration even when an earlier one fails. Serialize a successful diagnostic
only when all seven checks pass and the canonical record digest re-verifies.
Process exit is the cleanup boundary on refusal. Do not require the interrupted
pyelftools module to complete or instantiate a decoder engine.

## Output and decision boundary

Write only `resource-callsite-diagnostic-result-v1.json` and
`RESOURCE-CALLSITE-DIAGNOSTIC.md`, with script/result hashes, UTC chronology,
the bounded static candidate inventory, exact first-callsite record and digest,
aggregate module/resource/guard counters, restoration booleans and
`private_reads: 0`. Publish no source text, callable representation, virtual
address, pointer, private path or dynamic exception text.

Stop after this diagnostic. The result may identify the exact callable and
source join but does not prove successful execution, return value, purity,
resource-limit safety, pyelftools usability or general permission to call
standard-library extensions. A later prospective reviewed amendment must use
the callable's documented semantics and exact caller contract to decide whether
one narrowly verified invocation is admissible. No function execution, engine,
method freeze, callback, private analysis, acquisition, network, device action
or build is admitted here.
