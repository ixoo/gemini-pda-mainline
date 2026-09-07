# Exact resource pre-call join; execution not admitted

The single [Amendment 15](AMENDMENT-15.md) diagnostic successfully identified
the exact `resource.getpagesize` callable at its `c_call` boundary in frozen
`elftools.elf.elffile`, line 17. The payload-free terminal signal was raised
before returning from the profile observer, the exact handler verified automatic
profile removal, and all seven restoration checks passed. No function return
value, effect or successful package import was observed or admitted.

## Identities and chronology

- Dispatch: `b6799696f5d8a2c8f0d9cc61995431d6673cb35f`; Astra Medium.
- All 47 controlling and 18 explicit dependency hashes passed.
- [Amendment 16](AMENDMENT-16.md) corrected the historical profile statement
  before v2 construction. Profile installation remains before the top-level
  pyelftools import; the sole behavioral change is explicit original-caller
  tuple handoff between the two import-wrapper functions.
- [Source](resource-callsite-diagnostic-v2.json) frozen
  `2026-09-07 04:46:21 UTC`, file SHA-256
  `390b7c640f8980091f6d7f58dd81c6bf828f88a63101fff82058a36c0f2eb205`;
  embedded source SHA-256
  `4d9cc14cf9c74efb86b44c057fd7f69427821c7979222e61d25e183575a29c8b`.
- One fresh `/usr/bin/python3.12 -I -S -B` diagnostic through the approved
  RE-VM shell: `2026-09-07T04:47:06.451825+00:00` to
  `2026-09-07T04:47:06.828742+00:00`.
- [Result](resource-callsite-diagnostic-result-v2.json), SHA-256
  `fa92aaf9c089038267816c4503317b56a878bc6f588822b3f9bfc01f56c4aa74`.
- Canonical first-callsite JSON SHA-256:
  `cfbb15d6cc9c2e20b8b494a295f12c77b16f5fdcd3e0410131c7337e284516a1`.

## Bounded evidence

The complete 52-source static scan found one direct candidate. It uses the
`import-resource` binding named `resource`, literal callable `getpagesize`,
line/end-line 17 and column 15 in
`/usr/lib/python3/dist-packages/elftools/elf/elffile.py`, 37,150 bytes,
SHA-256 `457c93c8be327cbce2a86869aa40d9067f12f7c33052730f7e1cbcccb99b9b54`.

At the first matching pre-call event, the callable's exact module/name and
object identity matched exactly one frozen module-dictionary entry. The frame's
canonical source identity and line 17 matched that sole candidate; the runtime
binding still referred to the frozen resource module. Resource object/file
identity and the complete file-backed mapping identity/row dictionary matched
the accepted post-preload state.

The resource file remains
`/usr/lib/python3.12/lib-dynload/resource.cpython-312-aarch64-linux-gnu.so`,
68,288 bytes, SHA-256
`2e1deb71ff45f48040851b25eb46d106baacbcd1804641105dce48f8ed278e44`.
No source text, callable representation, pointer or virtual address is retained.

Resource spec lookup, creation, execution, extension audit, identical cached
reuse and pre-call attempt counts are each one. The canonical record was frozen
before setting the irreversible latch. Only the `profile-first-call` propagation
path was observed; alternate latch-boundary paths remain source-enforced but
were not exercised. The exact signal handler and `sys.getprofile() is None`
checks passed without waiting for a later profile event. No `c_return` or
`c_exception` was admitted.

All seven restorations passed: initial profile, original import object,
Capstone native-load endpoint, terminal finder, isolated path, and the resource
loader's inherited creation/execution endpoints after removing the instance
overrides. The diagnostic stopped with 28 entered and 27 completed modules;
the interrupted pyelftools module was not required or permitted to complete.
All six reached mapping stages preserved the in-process vDSO row.

One Capstone native request and zero optional requests were recorded. Write,
cache-write, network, process, engine, callback and private-read counts were
zero. The RE shell was closed immediately after the result. No raw capture,
method, private analysis, device action or build occurred. The single private
analysis budget remains unused.

## Validation and handoff

Tests actually run: 65 exact dependency hashes; syntax/source-digest checks;
an AST comparison proving only the two caller-handoff functions changed from
v1; the single guarded diagnostic; canonical-record digest, identity, schema,
bounds and terminal/restoration predicates; relative Markdown links; and
`git diff --check`. No alternate failure-path fixture or repeated diagnostic
was run.

Stop here. This identifies a pre-call object/source join, not a return value,
arguments, successful execution, purity, resource-limit safety or pyelftools
usability. A later prospective reviewed decision must use documented callable
semantics and the exact frozen caller use before admitting any invocation.
Only the three new diagnostic files are handed off; all predecessors remain
unchanged.
