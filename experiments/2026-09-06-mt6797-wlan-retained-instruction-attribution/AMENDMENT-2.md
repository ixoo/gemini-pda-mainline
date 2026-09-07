# Legacy Capstone source-manifest amendment

This second prospective amendment resolves only the fresh source gate recorded
in [VALIDATION-REFUSED.md](VALIDATION-REFUSED.md). The first frozen
[bootstrap-refused.json](bootstrap-refused.json) and its refusal remain
historical evidence and must not be modified or reused as the executable
bootstrap. The private ELF has not been opened and the one private analysis
execution remains unused.

The exact SHA-256 values of this amendment, the amended
[WORK_ITEM.md](WORK_ITEM.md), [AMENDMENT.md](AMENDMENT.md), the historical
`PREFLIGHT.md`, `bootstrap-refused.json` and `VALIDATION-REFUSED.md` paths must
be pinned in [inputs.json](inputs.json) before any new tool preflight. The
verifier must reject drift in every one.

## Exact legacy-metadata boundary

In a fresh `-I -S -B` no-private-content process, use the first amendment's
isolated metadata discovery to require exactly one distribution named
`capstone`, exact version 4.0.2 and one absolute resolved nonsymlink installed
root. Require its metadata directory and every component to be absolute,
nonsymlink and contained beneath that root. Recursively enumerate the complete
metadata directory before package import, with at most 32 total entries and 16
regular files. Record every relative directory/file name plus each regular
file's hash/size/mode/mtime. Refuse symlinks, path escape, nonregular entries,
duplicate inode/path identities, incomplete traversal or cap overflow at any
depth. Require exact name/version agreement between parsed metadata and the
selected package. No package module may be imported during this discovery.

The expected `importlib.metadata` file inventory may remain `None`; do not
claim a RECORD or complete distribution manifest. Instead, derive exactly one
package directory as `<installed-root>/capstone`. Require the directory and
every path component to be absolute, existing, nonsymlink and contained beneath
the installed root. Recursively enumerate it before import with a cap of 64
regular `.py` files and 128 total entries. Reject nested symlink, device, FIFO,
socket, hard-link duplication, path escape, case-fold collision, namespace
package, archive, extension module, executable file, or any non-`.py` regular
file except pre-existing `.pyc` below named `__pycache__` directories. Record
the complete entry-name inventory; bytecode is identity-recorded only and
remains forbidden from opening or execution.

Each `.py` source must be a distinct regular nonsymlink file with hash, size,
mode and mtime frozen before import. Convert the complete source inventory to a
unique module map rooted at the required `capstone/__init__.py`; reject an
ambiguous or missing package/module mapping. The terminal source loader must
compile only these exact bytes in memory, register every executed code object,
and refuse path-based discovery, bytecode, namespace extension and modules not
in the complete map. Before and after import require the package directory
entry inventory and every source/legacy-metadata/ignored-bytecode identity
unchanged. This is direct installed-source identity, not a claim that the
legacy package manager supplied cryptographic provenance.

Pyelftools remains governed by the first amendment's exact RECORD-backed
source rule. Native Capstone remains separately governed by the exact load-site,
absolute-library, mapping and `DT_NEEDED` closure rules. No package-manager
command, network, install, update or source acquisition is admitted.

## Replacement bootstrap and refusals

Create and freeze a new `bootstrap-v2.json` containing the complete amended
bootstrap source and SHA-256 before its first execution. It must reproduce all
first-amendment guards and postconditions and add the legacy-metadata/package
tree inventory above. The historical `bootstrap-refused.json` is not executable
under this amendment. Any new decoder import still requires a zero-write/cache/
network/process audit hook installed before metadata discovery and active to
exit.

Refuse missing/ambiguous legacy metadata, root or package directory; metadata
name/version mismatch; cap overflow; incomplete enumeration; any excluded file
kind/name; source/module collision; package-tree drift; executed source absent
from the frozen complete map; ordinary finder/bytecode use; any attempt to
promote this direct installed-source inventory into RECORD/package-manager
provenance; or any original/first-amendment refusal. Complete and freeze the
fresh no-ELF tool receipt and final method before the sole private analysis.
