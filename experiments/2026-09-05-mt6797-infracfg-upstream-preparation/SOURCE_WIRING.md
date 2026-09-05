# Source-selection production proposal

## Scope

This isolated proposal promotes the reviewed source contract into the production
builder and package validator. It does not change the manifest, any profile,
configuration, patch, series, or selected device candidate. Project Planning
owns integration and source-profile admission. No kernel build is selected.

The builder resolves the profile before reading its source, records the entire
normalized source tuple in new packages, and keys profile-override archives by
full SHA-256 plus compression. Existing global release paths and source-state
markers remain unchanged. Override source-state markers include the complete
tuple so changing a declared archive root cannot bypass extraction validation
by reusing a prepared tree. The existing Buildbox serialization remains the
source/cache mutation boundary; this proposal adds no alternate build backend.

Downloads use HTTPS, bounded transfer size/time and managed partial files. The
digest must match before publication to the cache. Failed transfers remove the
partial file; a subsequent invocation removes the exact stale partial path.
Symlink and non-regular cache entries refuse. No cache migration, retained
archive copy, source extraction, or build has occurred for this proposal.

The shared extractor validates the complete digest and declared gzip/xz format,
then inventories all members before writing. It rejects wrong roots, unsafe
paths, duplicate names, special nodes, non-directory ancestors, escaping links,
link chains and hard links without a regular archived target. It creates regular
files/directories before links in managed staging, strips special permission
bits, ignores archive ownership, and only installs the root after success.
Real source archives still require compatibility inspection before admission;
passing tiny fixtures alone does not prove acceptance of all Linux archives.

The package validator retains historical checksum-only acceptance for global
packages that never recorded `kernel_source`, including legacy manifests whose
source metadata contains only the digest. It does not reinterpret a missing or
null profile override as global fallback. Overrides require complete provenance;
when a global package supplies the new tuple it must also agree exactly.
Existing configuration, selected-series, inventory and digest checks remain.

## Validation

The following local checks pass on the proposal:

- Seven shared source-contract groups, covering historical metadata, full tuple
  mutations, override provenance, default normalization and duplicate JSON.
- Six real tiny archive groups, covering gzip/xz extraction, content/modes,
  safe links, digest/compression/root refusals, traversal, special files,
  duplicates, non-directory ancestors, escaping/chained links and residue.
- Four actual builder preparation groups using tiny synthetic inputs and explicit
  fake download/compiler/platform commands. Real patch application, prepared-tree
  integrity/reuse, content-key cache paths, root-policy revalidation, interrupted
  transfer/stale-partial cleanup and legacy source/build/cache paths pass. No
  Linux kernel source or compiler output is produced by these fixtures.
- The effective-input oracle preserves all 189 existing profiles with no added
  profiles. Bash syntax, ShellCheck and the common repository gate pass locally.

The Linux package fixture now adds minimal historical metadata acceptance,
complete profile-source acceptance, all six missing tuple fields, and absent
required tuple refusal. Its Linux execution remains pending before integration.
The builder fixture's explicit simulated platform is not a Linux package test.
The common gate runs all three new test programs and reports Linux-only skips.

A first macOS builder-fixture run exposed a host `sha256sum` implementation lacking
GNU long options. The fixture now selects installed GNU `gsha256sum` when
available. Production remains Linux-only and its checksum behavior was not
relaxed to accommodate the test host.

## Review and remaining evidence

Before integration, run the actual Linux provenance fixture and all new fixtures
from a clean, Git-fetched exact revision on Buildbox, coordinated with the A53
userspace worker. Inspect the retained pinned snapshot using the new member
validator without extracting or duplicating it. Record any incompatibility and
resolve it before a build is admitted. This evidence does not authorize a source
profile, V4 series migration, kernel build, device boot or upstream submission.

The source admission contract and eventual build boundary remain in
[SOURCE_INTEGRATION.md](SOURCE_INTEGRATION.md). The immutable source archive
identity remains in [its receipt](results/upstream-archive.json).

## First Linux execution and cleanup correction

Exact revision `06a5885c99cff7e07754e07dc9050b6e63f9fdd4` passed the seven
source and six archive groups on Buildbox. The actual builder fixture rejected
two failure-cleanup cases: wrong compression and changed archive root left an
empty preparation directory. The job stopped before package fixtures or retained
archive inspection and cleaned its disposable project checkout. No shared source
or device state was touched.

Bash on Linux unwound the preparation function's local `temporary` variable
before its outer EXIT trap used it. Preparation now owns state and traps inside
a subshell, which also prevents it from replacing a caller's cleanup trap.
Download and preparation signal handlers exit through their cleanup traps.
The download fixture additionally sends real SIGTERM to its parent after writing
a partial file and requires complete cleanup. Linux revalidation is required;
the first rejected execution is retained rather than treated as a pass.
