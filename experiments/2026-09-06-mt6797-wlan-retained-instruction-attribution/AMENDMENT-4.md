# Pyelftools direct installed-source amendment

This fourth prospective amendment resolves only the pyelftools provenance stop
in [VALIDATION-FINAL.md](VALIDATION-FINAL.md). The earlier amendments,
bootstraps and refusal records remain immutable. `bootstrap-v3.json` and
`VALIDATION-FINAL.md` are now an explicit refusal pair and are not executable
or reusable as final-result evidence. No private ELF has been opened; the one
private analysis execution remains unused.

The failed repairs exposed two separate installed-distribution facts: Capstone
4.0.2 required a complete mixed-content package inventory, which Amendment 3
successfully completed, while pyelftools 0.30 independently returned no
`importlib.metadata` file inventory at its still-mandatory RECORD gate. The
third preflight did not search for a RECORD elsewhere and does not prove none
exists. The next discriminating check is the exact bounded direct-tree rule
below. It is deliberately specific to pyelftools and does not widen Capstone's
rule or create a general exception for other packages.

Before another preflight, pin and verify in [inputs.json](inputs.json) the exact
SHA-256 values of this amendment, the amended [WORK_ITEM.md](WORK_ITEM.md), all
earlier amendments, and every earlier bootstrap/refusal record. The verifier
must reject drift in every path.

## Exact pyelftools boundary

In one fresh `/usr/bin/python3.12 -I -S -B` no-private-content process, locate
exactly one installed distribution whose normalized name is `pyelftools` and
whose parsed metadata version is exactly 0.30. Require one absolute resolved
nonsymlink installed root. Require the distribution metadata directory and
the exact `<installed-root>/elftools` package directory to exist, be canonical
nonsymlink directories and remain strictly contained beneath that root.

Before any decoder import, recursively enumerate the complete metadata tree
with at most 32 entries and 16 regular files, and the complete `elftools`
package tree with at most 768 entries, 512 regular files, 384 `.py` source
files, 128 stat-only `.pyc` files and 64 inert assets. Apply Amendment 3's
component, inode, hard-link, case-fold, canonical-path, file-kind, executable-
bit, fixed-signature, phase and drift refusals independently to this tree.
Require exactly one metadata `METADATA` or `PKG-INFO` file whose parsed
normalized name/version agrees with the selected distribution. Record whether
the distribution file inventory is `None`; do not claim a RECORD or package-
manager manifest.

Every `.py` file is exact executable source: hash all bytes and freeze path,
size, mode and mtime, then derive a unique complete module map rooted at the
required `elftools/__init__.py`. Refuse namespace extension, missing parent
initializers, module collision with Capstone, source-signature conflict,
ordinary finder fallback or execution absent from the map. The terminal source
loader alone may compile the already frozen bytes in memory.

A `.pyc` is admitted only below a directory named `__pycache__`; record only
its path and stat identity and never open, hash, import or execute it. Every
other regular file is an opaque inert pyelftools asset governed by Amendment
3's hash/signature-only inventory rule. It may be reopened only by the named
pre-import and final drift inventories and cannot enter a module, path, native
target, parser configuration or analysis input. Pyelftools has no admitted
native load route; any native mapping or library request attributable to it is
a refusal.

This is exact direct installed-source and complete-tree identity for the
selected pyelftools 0.30 installation. It is not RECORD/package-manager
provenance, source authorship, redistribution permission, correspondence to an
upstream release archive, or a general trust claim. The final receipt and
conclusions must keep Capstone and pyelftools provenance classes separate.

## Replacement bootstrap and one-analysis chronology

Create and freeze a distinct `bootstrap-v4.json` with the complete amended
bootstrap source and embedded SHA-256 before its first execution. Its audit
hook must precede metadata discovery and remain active through exit. It must
reproduce Capstone's already accepted complete inventory from scratch, perform
the separate pyelftools inventory above, source-force both exact module maps,
prove Capstone's optional/system-native route, prove pyelftools requested no
native load, perform both packages' named pre-import/final drift inventories,
restore the exact loader endpoint, finder and isolated path, and emit a
sanitized no-ELF receipt.

Only a fully successful v4 receipt may be used to freeze `method.json` with the
complete analysis harness. Only then may the still-unused single private child
open the exact retained ELF. A failed v4 preflight must produce an immutable
`VALIDATION-V4-REFUSED.md` and stop. An accepted result uses
`VALIDATION-RESULT.md`; neither earlier file named `VALIDATION.md` nor
`VALIDATION-FINAL.md` may be repurposed.

Refuse an ambiguous distribution/metadata/package root, cap overflow,
incomplete tree, metadata disagreement, incorrect phase, inventory drift,
unmapped execution, inert or bytecode use, native request from pyelftools,
provenance-class promotion or any earlier-amendment refusal. No package-manager
command, network, acquisition, private read, instruction decode, device action
or build is admitted during this no-ELF preflight. There is still no second
private-analysis run.
