# Complete inert-package inventory amendment

This third prospective amendment resolves only the package-tree refusal in
[VALIDATION.md](VALIDATION.md). The two earlier bootstraps and refusal records
remain immutable historical evidence. Neither bootstrap is executable under
this amendment. No private ELF has been opened and the one private analysis
execution remains unused. Here, `VALIDATION.md` is specifically the immutable
bootstrap-v2 refusal; any eventual accepted result uses `VALIDATION-FINAL.md`.

Before another preflight, pin and verify in [inputs.json](inputs.json) the exact
SHA-256 values of this amendment, the amended [WORK_ITEM.md](WORK_ITEM.md), both
earlier amendments, `PREFLIGHT.md`, `bootstrap-refused.json`,
`VALIDATION-REFUSED.md`, `bootstrap-v2.json` and `VALIDATION.md`. The verifier
must reject drift in every path.

## Complete package boundary

Retain Amendment 2's exact direct-installed-tree identity rule and metadata
boundary. In one fresh `-I -S -B` no-private-content process, recursively
enumerate the complete exact `capstone` package directory before import. Admit
at most 512 total entries, 256 regular files, 96 Python source files, 192 inert
regular files and 64 stat-only bytecode files. Refuse a cap overflow,
incomplete traversal, symlink, path escape, case-fold collision, nonregular
entry, duplicate inode/path identity, hard link, executable permission bit or
tree drift.

Classify every regular file into exactly one of these disjoint classes:

- A `.py` file is executable source. Hash it completely, freeze its identity,
  map it uniquely beneath the required `capstone/__init__.py`, and permit only
  the terminal source loader to compile its exact frozen bytes.
- A `.pyc` file is admitted only below a directory named `__pycache__`. Record
  its path, stat identity and class without opening, hashing, importing or
  executing it. Ordinary and sourceless bytecode finders remain forbidden.
- Every other regular file is an opaque inert package asset. Open it only while
  constructing or repeating the complete identity inventory, hash all bytes,
  record path, size, mode, mtime and a classification derived solely from its
  first fixed sixteen bytes and relative suffix, then close it. Recognize ELF,
  ZIP, gzip, bzip2, xz and common script or bytecode signatures explicitly;
  other content remains `opaque`. A recognized native, archive, compressed,
  script, bytecode or opaque classification grants no execution semantics.

After the initial inventory, prohibit every read, import, parse, compile,
execution, extraction, mapping or native-library load of an inert asset. The
only later access is the same bounded identity-inventory routine used for the
mandatory pre-import and final drift comparisons; that routine may reopen an
inert asset solely to recompute its hash and fixed signature. No asset may
contribute a module, path entry, native load target, decoder behavior or
analysis input. A `.py` file whose fixed prefix has a binary, archive,
compressed or bytecode signature is a refusal rather than source. A non-`.py`
file whose prefix denotes a text script remains inert and must never compile.

The separately frozen absolute system `libcapstone.so.4` and its `DT_NEEDED`
closure remain the only native files eligible for decoder loading. A package
asset with identical bytes is still ineligible because its absolute path is
not the frozen native load target. Require the audit log and mapping delta to
show that no package asset was opened after inventory except by an explicitly
named drift-check phase and that no package asset was mapped or loaded at any
time.

This rule establishes a complete, bounded identity of the selected installed
package tree. It does not establish package-manager or RECORD provenance,
redistribution rights, header/native compatibility, source correspondence, or
trust in inert contents.

## Replacement bootstrap and chronology

Create and freeze a distinct `bootstrap-v3.json` containing the complete
amended bootstrap source and SHA-256 before its first execution. Reproduce all
guards, source-only loader restrictions, exact optional/native routes,
postconditions and two-phase rules from Amendments 1 and 2. Add an explicit
phase state that authorizes inert-asset opens only during the initial inventory
and the two named drift comparisons. The audit hook must be installed before
metadata discovery and remain active until process exit.

The fresh preflight must finish the entire metadata and package inventories,
then source-force both decoders, prove the optional/native route and restore
the named hooks and path before it can emit a successful no-ELF receipt. Freeze
`method.json` only from that successful receipt and the already frozen complete
analysis source. Only then may the one fresh private analysis child run. There
is no retry of the private analysis, and a failed third preflight returns a new
immutable refusal record instead of changing this amendment in place.

Refuse an unclassified entry, incorrect phase, post-inventory asset use,
package-asset mapping/load, signature/source conflict, inventory drift, or any
earlier-amendment refusal. No package-manager command, network, tool install,
private read, instruction decode, device operation or build is admitted during
the no-ELF preflight.
