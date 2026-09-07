# Exact `_queue` standalone load-route diagnostic amendment

This twenty-third prospective amendment follows the accepted
[Amendment 22 identity result](EXTENSION-IDENTITY-DIAGNOSTIC-3.md). The exact
installed `_queue` file now has a pinned stable path/stat/content identity,
bounded ELF64 little-endian AArch64 `ET_DYN` structure, no parsed `DT_NEEDED`
entries, and was absent from the isolated diagnostic's maps. Empty
`DT_NEEDED` is not a claim of no external symbols or runtime dependencies.
The file has not been loaded or initialized by any admitted diagnostic.

Before execution, pin and verify in [inputs.json](inputs.json) the exact
SHA-256 values of this amendment, amended [WORK_ITEM.md](WORK_ITEM.md), all
earlier controls and the complete accepted Amendment 19–22 diagnostic trios.
Reject drift.

## One exact standalone import

Create and freeze `extension-load-diagnostic-v1.json` containing the complete
independently written source and embedded SHA-256 before first execution. Run
it exactly once with `/usr/bin/python3.12 -I -S -B` through the approved RE-VM
shell. Embed the exact `_queue` module name, path, event/content/stat identities
and accepted Amendment 22 result digest. Do not execute pyelftools, Capstone or
another package, create a decoder engine, inspect private content, or call an
exported `_queue` API.

Preload exactly `sys`, `os`, `stat`, `builtins`, `importlib.machinery`, `types`,
`re`, `json`, `hashlib` and `datetime`. Require `_queue` is absent from
`sys.modules`. Install an irreversible audit hook before target metadata or
maps inspection. Its only admitted `open` events are one read-only
`/proc/self/maps` baseline and one read-only post-import snapshot in their exact
phases. No candidate content open is admitted.

Save the exact original import function. Install a counted import wrapper that
admits exactly one request equivalent to
`ORIGINAL_IMPORT("_queue", None, None, (), 0)`: exact name, globals and locals
both `None`, fromlist exactly the empty tuple, and level exactly zero. It
delegates that request once to the original function and rejects every other
wrapper call before delegation. Restore and verify the exact original import
object in `finally`, immediately after the request returns or raises and before
post-return audit validation. A cached return, absent audit event or second
request is refusal.

During that single request, the audit hook admits only the documented import
events for module `_queue`: at most one discovery event with absent filename
and exactly one extension event whose filename equals the frozen exact path.
Require every event has the five-field shape. Each search-path/meta-path/
path-hook field must be absent or equal the frozen live value; publish only an
absent/present enum. Reject any other module, filename, event count, import
phase, `ctypes.dlopen`, open, write/mutation, socket/network, subprocess/shell/
fork or other audit event before it returns.

## Identity and mapping checks

Before the import, take two exact `lstat` snapshots of the candidate and require
both equal the accepted Amendment 22 tuple. Read `/proc/self/maps` once with a
512 KiB/256-row/1,024-byte-row ceiling and the same strict row grammar as
Amendment 22. Require the candidate path absent. Retain only a bounded internal
file-backed mapping identity keyed by absolute path with device, inode,
permissions and file offset; publish no path set, address or raw row.

After ordinary import returns, require exactly one `_queue` module object in
`sys.modules`, identical to the returned object, with exact `__name__`, empty
`__package__`, exact `__file__`, and a unique spec whose name/origin match and
whose loader object is the module's loader. Require the loader is exactly the
preloaded `importlib.machinery.ExtensionFileLoader` type. Record only these
closed identity booleans and the module type name; do not enumerate attributes,
instantiate a queue or call a module value.

Take two more candidate `lstat` snapshots equal to the accepted tuple. Read one
strict post-import maps snapshot under the same bounds. Require every baseline
file-backed path and permission/offset/device/inode row is unchanged; require
the sole new file-backed path is the exact candidate; require its rows' device
and inode equal the accepted tuple; and require at least one readable and one
executable candidate row. Reject any additional or missing file-backed mapping.
Ignore bounded anonymous allocation differences, but require the sole
anonymous executable mapping remains the exact unchanged vDSO row.

Use this exact ordered stage set: `lexical`, `pre-lstat`, `baseline-maps`,
`import-wrapper`, `import-restoration`, `import-audit`, `module-object`,
`module-spec`, `post-lstat`, `post-maps`, `mapping-delta`, and
`final-counters`.
Any false identity, mapping or event predicate; exception; drift; bound or
counter mismatch; audit/wrapper rejection; missing restoration; or internal
schema failure is `refused` at its exact first stage. Mark the suffix
`not-evaluated`; no catch may advance. Only all stages passing is
`complete-positive`. No partial load or mapping identity may be promoted from a
refusal; process exit is the cleanup boundary because extension unloading is
not attempted.

Write only `extension-load-diagnostic-result-v1.json` and
`EXTENSION-LOAD-DIAGNOSTIC.md`, with source/result/canonical hashes, UTC
chronology, closed stage outcomes, import-wrapper/audit/map/stat counters,
bounded module/spec identity, sanitized candidate map rows without addresses,
and `private_reads: 0`. Publish no bytes, unrelated map path, pointer, raw event
list, dynamic exception text, module attribute list, credential or private path.

Stop after the one diagnostic; refusal consumes its budget. A positive result
establishes only one exact ordinary `_queue` import/initialization route and its
bounded mapping effect in this isolated process. It does not prove package
usability, authorize its use in the full bootstrap, admit another extension,
call a queue API or authorize retained private analysis. No package execution,
engine, method, callback, private content, acquisition, network, device action
or build is admitted.
