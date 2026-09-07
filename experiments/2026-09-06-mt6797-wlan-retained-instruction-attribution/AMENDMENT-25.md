# V9 public-metadata parsing clarification

This prospective clarification is based on exact clean parent
`c799d8b6faf682235c8299986db992382bde5fdf` (`origin/main`). It resolves only
the parsing wording in [Amendment 24](AMENDMENT-24.md), SHA-256
`9031c09a0e3375062d1c2c77be6eeb1bd58294d6340a5cd477a245ed911f7f6e`.
V8's complete container SHA-256 remains
`bc769538ecf3edad9361294f313bd96099cc4da1d848bc875cbd1a13b7ff6f75`,
with embedded source SHA-256
`3fe4fb8bc87cd46774944c4c10a7d892122ca3dee94ee7cfa39ba0ccfb70332b`.

## Pre-execution stop

The v9 execution dispatch stopped before source construction or freeze because
Amendment 24 required the unchanged V8 inventories while prohibiting a
"parser over any input". V8's `discover_legacy()` necessarily constructs
`email.parser.Parser` and calls `parsestr()` on installed distribution metadata
(embedded source line 257). The dispatch's parser prohibition did not state
that exception. The clean parent and all 93 pins passed; no source/result,
RE-VM session, package execution or private read occurred. There were zero
repair or execution attempts. The one v9 preflight budget remains unconsumed;
the private-analysis budget remains unused and unadmitted.

This amendment replaces that ambiguous prohibition with the closed boundary
below. Every other Amendment 24 source-freeze, one-run, audit, map/stat/content,
resource, engine, restoration, output and refusal predicate remains unchanged.
Earlier artifacts, including Amendment 24, remain immutable. Before future
construction, pin and verify this clarification and the amended
[WORK_ITEM.md](WORK_ITEM.md), along with every existing input/control pin.

## Exhaustive bootstrap-owned parsing boundary

Only the following existing call-site/input routes remain admitted. Names
below identify functions in the frozen V8 source, not newly acquired tools.
Their argument construction, selected inputs, containment checks and data
interpretation remain unchanged except the explicit Amendment 24 queue/map
instrumentation and removal of unavailable analysis branches. Counts are for
successful v9 preflight execution; a refusal records the reached prefix.

| Route | Exact retained boundary and count |
| --- | --- |
| Installed-distribution discovery | Exactly two `discover_legacy()` calls: `("capstone", "capstone", "4.0.2")` and `("pyelftools", "elftools", "0.30")`. Keep their existing `importlib.metadata.distributions(path=ROOTS)`, `d.metadata`, `d.version`, `d.locate_file`, `d._path` and `d.files` uses, selected installed roots, unique name/version checks and direct-installed-source provenance. No new metadata provider, root, distribution or discovery pass. |
| Explicit email metadata parsing | In each of those two initial calls, choose the sole already inventoried `METADATA` or `PKG-INFO` entry, read that same file as text, then execute exactly `Parser().parsestr((md/candidates[0]["name"]).read_text())`. Require parsed `Name`/`Version` to match the selected distribution as V8 does. This is exactly **two bootstrap-owned `Parser()` constructions and two `parsestr()` calls**, before package entry. No mailbox, message, arbitrary string or other path is admitted. |
| Tree/signature inspection | Preserve `checked_directory()`, `tree_inventory()`, `signature()` and `legacy_unchanged()` on the two selected metadata/package trees. Initial, pre-import and final passes remain; no pre-analysis pass. Per pass, inspect 77 source prefixes and 14 inert-asset prefixes; thus 273 `signature()` calls on success. Classification examines the existing at-most-16-byte prefix and suffix only: ELF/ZIP/gzip/bzip2/xz/script/bytecode/opaque recognition is not decoding, decompression, extraction or deserialization. Keep stat-only cached bytecode, source/inert hashing and every existing inventory cap. |
| Frozen-source AST parsing | `static_candidates()` calls `ast.parse()` once on each of 52 frozen pyelftools sources; `exact_resource_ast()` adds one parse of the exact `elftools.elf.elffile` source. `main()` parses frozen Capstone source once for native/optional call-site checks and parses that exact resource-caller source once. `cached_resource_import()` parses that same caller source once at the sole admitted cached resource request. This is **56 explicit `ast.parse()` calls** on success, all over the existing `SOURCES` byte strings, with their existing `ast.walk`/`iter_child_nodes`/`unparse`, node/class and line/column checks. No target-binary or method text is an AST input. |
| Frozen package-source compilation | `SourceLoader.exec_module()` compiles and executes each demanded exact mapped source body once under its existing identity, entry-latch and 77-module budget; it hashes that code via `marshal.dumps(code)`. This is at most 77 source compilations/executions, not 77 required entries. No `marshal.load(s)`, bytecode execution, alternate compiler input, callback compilation or generic evaluator is admitted. Existing source-forced package-body execution remains the Amendment 24 route, not a new parser entry point. |
| Native-tool ELF metadata | Keep exactly two `needed()` invocations: one on the exact selected Capstone `NATIVE_PATH`, one on the exact frozen `RESOURCE_PATH` during `resource_preload()`. Their existing `struct.unpack_from` formats parse only ELF/program-header/dynamic/string-table metadata and `DT_NEEDED` names. Keep the separate single resource-header `struct.unpack_from` in `resource_preload()`. Together these give three explicit ELF-header unpacks, with program-header/dynamic-entry unpacks bounded by the same admitted files, tables and existing checks. No sections, symbols, instructions, target/private ELF or `_queue` ELF reparse is admitted. |
| Map/stat/identity parsing | Keep V8's map field/number/permission/path interpretation and Amendment 24's strict row grammar, 13 map snapshots, candidate rows and direct counted stat/content checks. Existing path-component, stat-kind/mode, integer/hex/text conversions and SHA-256 identities serve only those already admitted installed files/maps. The 17 candidate hash reads do not admit semantic ELF or instruction parsing. |
| Receipt serialization | Keep `json.dumps()` for bounded in-memory receipt/canonical serialization and SHA-256 over those serialized bytes, as required by Amendment 24. No bootstrap-owned `json.load()`/`json.loads()` is needed or admitted: the V8 method-input JSON deserializer and analysis-only method canonicalization route must be removed with that mode. Host JSON parsing of frozen source/input/result containers and host AST/compile-only validation remain allowed; they are not guest parsing of an analysis input. |

The 273 prefix-classification count follows three complete passes over
`25 + 52 + 14` source/inert entries. The final/pre-import metadata-tree passes
verify hashes and metadata; they do **not** repeat the two explicit email
parses. The 56 AST count is `52 + 1 + 1 + 1 + 1`. Program-header and dynamic
iteration counts depend on the exact admitted native files; do not invent
fixed totals or widen their inputs to satisfy a count.

This list is exhaustive at the bootstrap-owned call-site/input boundary.
It does not claim that `importlib.metadata`, email parsing, Python's ordinary
import machinery or the unchanged source-forced package bodies internally
construct no other parser objects. Their existing transitive behavior remains
confined by the same helper imports, selected arguments, frozen source/tool
identities and audit gates; it is not authority to add a new bootstrap call,
input, helper import or decoder route. In particular, the count two refers to
explicit bootstrap `Parser()` calls, not an unmeasured interpreter-wide count.

### CSV/RECORD helper is not a new route

V8 also contains the obsolete `discover()` definition. Its `csv.reader`,
`io.StringIO`, `.dist-info/RECORD` parsing and `base64.urlsafe_b64decode` calls
are not invoked by V8's selected legacy-inventory `main()`. V9 must not invoke
this helper or substitute it for `discover_legacy()`. Remove that unused
definition in V9 so it does not become an available fallback. Preserve
Amendment 24's exact helper-import statements, including their unused
`csv`, `io` and `base64` names; an import is not permission to call these
obsolete parsing endpoints. The allowed direct bootstrap CSV/RECORD/base64
decode call count is **zero**. Any existing transitive metadata helper behavior
remains scoped as above; do not claim zero interpreter-wide CSV activity.

## What remains forbidden

No `ELFFile` instance, parser/decoder over a target or private input, instruction
decode/disassembly, analysis method, callback, private path or private read is
admitted. There is no method descriptor/pipe, JSON method deserializer,
`load_method`, `private_opener`, `private_unchanged`, callback compiler,
`validate_result` analysis route or analysis-mode branch in v9. It may import
the source-forced `ELFFile` class as V8 does but may not call/instantiate it.

The single original Capstone engine construction/configuration and existing
version queries remain permitted by Amendment 24; no decoder operation over
bytes, second engine or new package API call is admitted. Do not parse a
synthetic ELF, public sample binary, alternate distribution or fixture to
circumvent the target/private-input prohibition. Do not add a `_queue` API
call or treat native metadata parsing as firmware/driver/teardown evidence.

## Static acceptance and handoff

Before the eventual freeze/run, the implementation reviewer must:

- verify all pinned controls and both V8 container/source hashes, then compare
  the candidate source AST against these exact permitted functions/call sites
  and their input-producing expressions; line numbers are references only;
- establish exactly two `discover_legacy()` calls with the literal tuples
  above, one explicit `Parser().parsestr(...)` site in that helper, and no
  repeat call from either drift pass;
- establish the five inherited `ast.parse()` sites and their 52-source/one-
  cached-resource execution structure, exactly two `needed()` call sites with
  the stated native inputs, the separate resource-header unpack, and only the
  existing source-loader compile/exec/marshal-dump route;
- verify the obsolete `discover()` definition/calls are absent, no bootstrap
  CSV/base64 decoder or JSON deserializer call exists, and no analysis-mode,
  method/private/callback function, argument or indirect dispatch remains;
- distinguish `from elftools.elf.elffile import ELFFile` from a call to that
  class: reject direct or aliased constructor use, target-data methods,
  engine decoding/disassembly, new evaluators or new parser call routes;
- inspect data flow as well as call spellings: only the frozen public
  metadata/source/native-identity/map inputs may reach permitted parsing;
  renaming/aliasing, a computed callable or wrapper cannot bypass the boundary;
  and
- retain all Amendment 24 host syntax/AST, stage, map/stat/content, helper,
  one-engine/one-preload, privacy and source-difference checks. If a required
  route or argument does not fit this exhaustive call-site list, stop before
  execution and escalate; do not add a parser or infer a new exception.

These are source-only checks, not permission for a fixture parse or guest
probe. This clarification creates no source container and consumes no run.
Future execution still requires its own bounded dispatch and complete freeze.
The design owner writes only this amendment and minimal work-item/input pins;
`/root` owns integration and workflow measurement. No VM, package, device,
build, network, acquisition, commit or push action is part of this handoff.
