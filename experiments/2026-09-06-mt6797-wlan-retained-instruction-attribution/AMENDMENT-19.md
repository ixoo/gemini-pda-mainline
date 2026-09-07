# First refused extension-event diagnostic amendment

This nineteenth prospective amendment resolves only the unidentified extension
audit event in [VALIDATION-V8-REFUSED.md](VALIDATION-V8-REFUSED.md).
`bootstrap-v8.json` and its refusal remain immutable. V8 completed the exact
page-size reference and one `resource.getpagesize` call/return, then refused an
unadmitted `.so` import before engine, method or private access. The refusal
retained no module, origin or caller identity. Do not infer one from module
progress. The single private analysis remains unused.

Python 3.12 documents the `import` audit event arguments as module, filename,
`sys.path`, `sys.meta_path` and `sys.path_hooks`, and documents that
`sys.audit()` re-raises the first exception from an audit hook; see
<https://docs.python.org/3.12/library/audit_events.html> and
<https://docs.python.org/3.12/library/sys.html#sys.audit>. This amendment
authorizes one no-private terminal diagnostic that captures the first exact
event V8 would refuse and stops the import through that hook exception. It does
not authorize loading or admitting the extension.

Before the diagnostic, pin and verify in [inputs.json](inputs.json) the exact
SHA-256 values of this amendment, the amended
[WORK_ITEM.md](WORK_ITEM.md), all earlier controlling artifacts,
`bootstrap-v8.json` and `VALIDATION-V8-REFUSED.md`. Reject drift.

## Exact terminal event capture

Create and freeze `extension-event-diagnostic-v1.json` with the complete
independently written source and embedded SHA-256 before first execution. Run
it exactly once with `/usr/bin/python3.12 -I -S -B` through the approved RE-VM
shell. Reproduce V8 through its exact inventories, Capstone closure, resource
preload, page-size reference and exact `getpagesize` call/return. Do not create
an engine, load a method, compile or invoke a callback, or access private data.

Before package execution, augment only the frozen source loader with a bounded
active-source stack. Push the exact mapped module name immediately before its
body executes and pop it in `finally`; require exact nesting, maximum depth 77,
no duplicate active name and correspondence with the existing entered record.
This stack is execution context, not a caller or import claim.

Replace only V8's generic unadmitted-extension refusal branch. At the first
`import` audit event with a string filename ending in `.so` that is not the
already admitted exact resource event, require:

- event arguments have the documented five-field shape; module is an ASCII
  dotted identifier of 1–128 bytes with 1–64 byte components matching
  `[A-Za-z_][A-Za-z0-9_]*`; filename is an ASCII string of 1–512 bytes;
- filename is absolute, lexically beneath `/usr/lib` or `/usr/local/lib`, has
  no `.`/`..` component, and has a basename of 1–128 bytes ending in the exact
  frozen interpreter `EXT_SUFFIX`;
- the live search path, meta path and path hooks equal their frozen values and
  object identities/order. Each corresponding audit-event field must be either
  `None` or equal that live frozen value; record only a present/absent enum, not
  the lists or object representations;
- the exact resource call/return state is `returned`, all resource/page-size
  counters and the last strict file-backed map dictionary equal the accepted
  post-resource state, with no engine/callback/method/private or forbidden
  event; and
- the active-source stack is nonempty and its top is one exact currently
  entered, not-yet-completed mapped package module.

Scan at most 64 live frames from the audit hook's caller outward without
retaining frames. Record a bounded `source_context` only if the first frame
whose canonical code filename equals a frozen package source also has exact
module globals, current line within that source and module equal to the active-
stack top. If no such exact frame exists, record source context as unresolved;
do not infer a caller. If present, independently parse the frozen source and
record an import-statement join only when exactly one AST node containing that
line has a literal match under these rules: for `Import`, exactly one alias name
equals the complete event module; for an absolute `ImportFrom` with `level ==
0` and a nonempty module, exactly one non-star alias makes the event module
equal either that module or `module + "." + alias.name`. Never join a relative
`ImportFrom`, star import, computed name or multiple matching aliases. Mark
every nonunique or nonmatching case unresolved rather than infer a request.

Immediately encode only the validated module, lexical filename, active-source
top, optional exact source context and optional unique AST join as canonical
UTF-8 JSON; retain its SHA-256, set an irreversible terminal latch and raise a
payload-free dedicated `BaseException` from the audit hook before it returns.
Every active source-loader, wrapped-import and outer-import boundary must
re-raise or refuse while latched. Catch only that exact signal at the outer
handler. Reject normal return, another exception class, an absent latch or a
second candidate event.

## Post-stop identity and output

Only after the exact signal reaches the handler, enter a fixed diagnostic-
validation phase while the irreversible audit hook remains active. Its audit
allowlist and exact counters are: one read-only `open` of the sole captured
canonical candidate; one read-only `open` of exact `/proc/self/maps`; and one
zero-argument `sys.setprofile` event restoring the exact original profile
function. No `import`, `ctypes.dlopen`, second open, write-capable flag,
network/process event or other audit event is allowed. The loader-method
deletions, import/native restoration, finder removal and path restoration must
produce zero audit events; refuse if this runtime differs. Increment each
allowed counter before returning from the hook, reject overflow immediately,
and require exact counts `candidate_open=1`, `maps_open=1`,
`profile_restore=1`, `other=0` before output.

Use the single candidate open to read at most 1 MiB, requiring EOF within that
bound; hash and parse those same retained public bytes without another open.
Require the path is canonical and nonsymlinked, is one regular mode-`0644`
file, and remains within the admitted installed roots. Record SHA-256, size and
mtime. Independently parse and require ELF64,
little-endian, AArch64 `ET_DYN`; enumerate at most eight `DT_NEEDED` names and
resolve each uniquely by basename to an already identity-frozen mapped
interpreter/stdlib/Capstone/resource dependency. Do not load the candidate.

Use the sole `/proc/self/maps` open for one strict post-stop map snapshot.
Require it equals the last accepted pre-event file-backed dictionary and the
candidate path is absent; require the exact vDSO row unchanged. Attempt and
record every inherited named restoration, including profile, import/native
endpoints, finder, isolated path and both resource-loader methods. Do not rehash
other files during restoration. Process exit is the cleanup boundary if any
validation or restoration fails.

Write only `extension-event-diagnostic-result-v1.json` and
`EXTENSION-EVENT-DIAGNOSTIC.md`, with source/result hashes, UTC chronology,
canonical event digest, sanitized identity/ELF/needed fields, bounded source-
context resolution, aggregate counters, restoration booleans and
`private_reads: 0`. Publish no raw path stack, source text, virtual address,
pointer, dynamic exception text or private path.

Stop after the one diagnostic. A successful receipt establishes only the first
refused extension event, exact installed file identity and whether a frozen
source join was available. It does not establish successful loading, Python
module identity after initialization, return behavior, package usability or
general extension admission. A later prospective reviewed amendment must decide
classification and admission. No engine, method, callback, private analysis,
acquisition, network, device action or build is admitted.
