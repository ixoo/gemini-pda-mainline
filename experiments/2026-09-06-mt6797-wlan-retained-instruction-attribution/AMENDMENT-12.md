# Exact Python resource-extension amendment

This twelfth prospective amendment resolves only the file-backed mapping delta
captured by [MAPPING-DIAGNOSTIC-4.md](MAPPING-DIAGNOSTIC-4.md) and its
hash-pinned result. All earlier contracts, bootstraps, refusals and diagnostics
remain immutable. The v4 result established first observation and a unique
frozen-source import join, not causation or admission. No engine, method,
callback or private access occurred; the single private analysis remains
unused.

The first accepted delta followed completed import event 16: exact frozen
`elftools.elf.elffile` source at line 16 requested top-level module `resource`.
The observer saw one added file with four rows:

- `/usr/lib/python3.12/lib-dynload/resource.cpython-312-aarch64-linux-gnu.so`;
- SHA-256
  `2e1deb71ff45f48040851b25eb46d106baacbcd1804641105dce48f8ed278e44`,
  size 68,288, mode `0644`, mtime 1781873160000000000 ns; and
- mapping permission/offset pairs `r-xp/0x0`, `---p/0x3000`, `r--p/0xf000`,
  and `rw-p/0x10000`, with no published virtual addresses.

Python 3.12 documents `resource` as a Unix-specific standard-library module,
and documents `importlib.machinery.ExtensionFileLoader` as the loader for
extension modules; see <https://docs.python.org/3.12/library/unix.html> and
<https://docs.python.org/3.12/library/importlib.html>. This supports only the
exact separately verified standard-library extension route below. It does not
make the file pyelftools package code or generally admit extension modules.

Before replacement preflight, pin and verify in [inputs.json](inputs.json) the
exact SHA-256 values of this amendment, the amended
[WORK_ITEM.md](WORK_ITEM.md), all earlier amendments, every earlier
bootstrap/refusal record and all four mapping-diagnostic trios at their explicit
dependency paths. Reject drift.

## Exact standard-library extension route

Complete the frozen standard-library helper imports, full source-forced
Capstone inventory/import and exact native-closure checks first. Create a
strict file-backed mapping snapshot only after those checks and before loading
`resource`. Require the exact resource path absent from mappings and module
name `resource` absent from `sys.modules`. Resolve exactly one module spec for
name `resource` using only the frozen Python 3.12
standard-library/lib-dynload search roots. Require:

- exact absolute canonical nonsymlink origin equal to the path above;
- loader is exactly `importlib.machinery.ExtensionFileLoader` with name
  `resource` and the same exact origin;
- the filename suffix equals the frozen interpreter's exact `EXT_SUFFIX`;
- the origin's hash, size, mode and mtime equal the diagnostic identity; and
- independently parsed file format is ELF64, little-endian, AArch64 `ET_DYN`.

Independently parse the extension's dynamic table with the frozen
standard-library-only parser. Bound `DT_NEEDED` to eight names and require each
to resolve uniquely by basename to an already identity-frozen file in the
pre-resource interpreter/stdlib/Capstone baseline; the resource extension may
not introduce another dependency mapping.

With the audit hook active and `IMPORT_OWNER` exactly `stdlib-resource`, invoke
the original import object once for exact name `resource`, level zero and empty
fromlist. Require exactly one extension-load audit event whose module/path equal
the frozen spec, no ctypes load request, and a post-import mapping delta of only
the exact resource path with exactly the four recorded permission/offset rows.
Require its module object, `__name__`, `__file__`, `__spec__.origin` and loader
identity to agree exactly. Do not call a `resource` function, mutate a resource
limit, inspect extension symbols or retain its mapping addresses.

Take the post-resource mapping dictionary as the extended frozen
interpreter/stdlib/Capstone baseline. Then run the complete source-forced
pyelftools inventory/import. The exact frozen `elftools` source join must still
request `resource`, but it must resolve to the identical cached module object
and create no mapping, native-load audit event or module reinitialization.
Require no file-backed delta attributable to pyelftools after the resource
preload. Keep the resource extension, its `DT_NEEDED` closure and Capstone's
native library/closure as separate named component classes.

This changes Amendment 4's zero-native rule only by moving the exact verified
Python stdlib `resource` extension into the pre-pyelftools baseline. Pyelftools
still has no package-owned native component or native-load route. Refuse any
other extension, origin/loader/identity/ELF/needed mismatch, additional mapping,
resource object replacement, second initialization, function invocation or
promotion to package-manager/upstream provenance.

## Replacement v7 lifecycle

Create and freeze `bootstrap-v7.json` with the complete two-mode bootstrap and
embedded SHA-256 before first execution. Run exactly one no-ELF preflight mode
that proves the resource route, both package imports, exact 77-module budget,
Capstone native closure, vDSO/mapping stability, named restoration and final
drift without a callback or private read.

Only its complete successful receipt may feed the frozen `method.json`. Then at
most one analysis-mode child may run using Amendment 8's exact method pipe,
existing-engine callback and pre/post-analysis drift lifecycle. A v7 preflight
failure writes only `VALIDATION-V7-REFUSED.md` and stops; a successful final
result uses `VALIDATION-RESULT.md`. No private-analysis retry is admitted.

Refuse any earlier-amendment mismatch, unaccounted resource or Capstone mapping,
ordinary nonfrozen extension load, callback/preflight crossover, or scope/bound
change. No acquisition, network, device action or build is admitted. This
extension classification establishes no private-binary behavior, runtime
invocation, teardown safety or hardware support.
