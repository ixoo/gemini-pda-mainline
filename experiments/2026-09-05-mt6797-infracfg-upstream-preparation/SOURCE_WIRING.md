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
required tuple refusal. Its Linux execution now passes on the corrected revision recorded below.
The builder fixture's explicit simulated platform is not a Linux package test.
The common gate runs all three new test programs and reports Linux-only skips.

A first macOS builder-fixture run exposed a host `sha256sum` implementation lacking
GNU long options. The fixture now selects installed GNU `gsha256sum` when
available. Production remains Linux-only and its checksum behavior was not
relaxed to accommodate the test host.

## Review and remaining evidence

The required Linux fixtures and retained-snapshot inspection are now complete,
as recorded below. Integrator review and source-profile admission remain. This evidence does not authorize a source
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

## Corrected Linux result and handoff

[The sanitized receipt](results/source-wiring-linux.json) records exact clean
revision `02c6c39b9ae7c75785dcd9e256f8bdece3b06116`: all 17 source/archive/builder
groups pass on Buildbox, including both previously failing cleanup cases and
SIGTERM. Linux artifact validation accepts six positive packages and rejects
28 mutations. The retained snapshot still matches its published digest and all
102,310 archive members pass the production inventory rules without extraction.
The disposable Git-fetched project and all fixture temporary roots were removed;
no kernel build, real source-tree extraction, candidate or device operation ran.

The implementation commits are `06a5885c` and `02c6c39b`, based on archive receipt
`f4368b78`. This is a clean proposal handoff for integration review, not permission
to build. All 189 pre-existing profile inputs remain unchanged. The original
source-contract proposal and acquisition history remain independently reviewable.
Before an eventual build, adopt the retained archive into the new full-digest
cache location with verified identity and a migration receipt; do not silently
make a second retained copy. The actual legacy release archive was not unpacked
or inventoried in this run; legacy xz preparation and package compatibility were
covered by real synthetic archives/packages rather than a kernel build.

## Independent review: traversal before normalization

Review of `e3f0304d` found that lexical normalization could hide a link component
before the chain check. With `linux-test/sub -> .`, the target
`sub/../outside` lexically normalizes inside the root, but filesystem traversal
follows `sub` first and then moves outside the root. Source integrity hashes the
link text and does not establish safe resolution. The earlier passing fixture
and snapshot receipts remain scoped observations, not a proof of this boundary.

The extractor now checks every appended target component against the complete
member inventory before any subsequent `..` can remove it. The regression group
covers the reviewer's escaping symlink in both archive orders and a hard-link
variant. All must refuse before extraction and leave the destination empty.
This correction must be reviewed before source-wiring integration. No actual
kernel source extraction, build or device access is required for these fixtures.
