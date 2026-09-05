# Revised generation attempt 1: refused; no review archive produced

## Terminal result and preserved evidence

One generation invocation ran at exact published main
`7209e9d07026456be01e19c0cc87e9b04a13ffda`, branch `refs/heads/main`.
The outer process exited 1 after 52.520 seconds. The original
[result](results/attempt-1-7209e9d0/result.json) is **REFUSED** and remains
byte-for-byte unchanged, SHA-256
`128e94568e44a7fef105c6848321717825ff3785077a9c4f50ef205a46ccb281`.
There was no retry, kernel build, schema/QEMU run or device access.

The first fourteen bounded commands completed normally, including exact
publication, full retained-source integrity, the filtered upstream fetch,
new-path absence, index initialization and first-patch check/apply/whitespace.
Command fifteen, `input-1-tree`, ran ordinary `git write-tree`, timed out at
30.015724 seconds and returned -15 after termination. Its
[stderr](results/attempt-1-7209e9d0/input-1-tree.stderr) contains the fetch-pack
invalid-index-pack diagnostic; stdout is empty. No generated commit/tree,
format-patch archive, final-source comparison, checkpatch, maintainer result
or replay result was recorded. Full post-source scanning was not reached.

The [inventory](results/attempt-1-7209e9d0/inventory.json) identifies all 31
original regular files, totaling 21,402 bytes. Each fit the 256 KiB cap and
all original command-log hashes matched after transfer. Only this bounded
receipt/log package was fetched, not Git objects or Linux sources. Separate
outer process records and a later host/source audit are included beside the
original files; they do not rewrite the original collector decision.

## Cleanup and post-state

The original receipt says `scratch_removed=true`, and its final twenty
source/build pins match the initial pins without preservation errors. A fresh
post-collection check reacquired the shared lock nonblockingly, confirmed those
pins, tools, the original processed-schema hash
`a3265d87a3617c19c3463fb3a728df2120b8932ee0be686dcd8c4f69fac82b38`, absent scratch
and the clean exact project checkout. The original full pre-scan passed; the
full post-scan was not rerun and must not be inferred from these limited checks.

`input-1-tree` records `group_absent=false`, `term_sent=true`, `kill_sent=false`.
The retained collector sets `group_absent` from its initial pre-termination
lookup, and never updates that field after TERM/reaping. The false value thus
records the group present at cleanup entry, not a later surviving-group check.
With the stop reason still `timeout`, the later unsent KILL corresponds to
ProcessLookupError: no group remained at that lookup. A subsequent process
inspection showed no Git, fetch, generator or zombie entry, and the lock was
available. No zombie classification at the earlier snapshot is possible from
this receipt. The refusal and original accounting remain unchanged.
The backend window was released after collection and post-state checks.

## Primary-source diagnosis and bounded correction

The observed backend reports Git 2.39.5. The
[source ledger](results/attempt-1-7209e9d0/git-source-audit.json) pins that
upstream tag to `cc7d11c16782041a6bb73e2fb56417b7d4c6d186` and records the
three audited file hashes. In `cache_tree_update`, a promisor repository
prefetches index entries unless `WRITE_TREE_MISSING_OK` is set. Ordinary index
entries here lack the skip-worktree exemption. The same flag bypasses object
existence checks while tree serialization still uses indexed names, modes and
object identities.
[Git cache-tree source](https://github.com/git/git/blob/cc7d11c16782041a6bb73e2fb56417b7d4c6d186/cache-tree.c#L433).

The command option sets that flag, and its documented purpose is to permit
referenced objects absent from the local database.
[Command source](https://github.com/git/git/blob/cc7d11c16782041a6bb73e2fb56417b7d4c6d186/builtin/write-tree.c#L23),
[matching manual](https://github.com/git/git/blob/cc7d11c16782041a6bb73e2fb56417b7d4c6d186/Documentation/git-write-tree.txt).

The exact log proves a fetch-pack operation occurred inside tree writing.
The filtered-fetch design and source path support the inference that tree
writing triggered unrelated missing-blob prefetch. There is no object-count,
pack-size or fetch trace proving how many objects were requested or whether
the invalid pack diagnostic preceded termination; those details are not claimed.
Increasing the deadline would leave the unnecessary fetch behavior intact.

The corrected revised path adds `--missing-ok` at both actual write-tree call
sites (six generation phases and the separate replay). It keeps the exact
upstream commit/full index, ordered patch hashes, changed-path footprint,
eleven materialized source hashes and final full-tree replay equality. Only
local availability of unrelated upstream blobs is omitted; no partial or
prefix tree is substituted. A missing or incorrect changed source still fails
its explicit materialization/hash or footprint/replay check. No limits increase.

[The synthetic host test](test-partial-tree.py) uses only two invented files and
a local Git transport. Ordinary write-tree fetches the omitted unrelated blob;
`--missing-ok` does not, yet matches the tree from an independent complete-object
repository and a separate replay index. A missing changed object fails explicit
materialization, and changed or unrelated reference mutations alter the tree.
It asserts both actual revised call sites use the tested option. The
[result](partial-tree-host-check.json) is host Git 2.50.1 behavior, supplemented
by the source audit of observed backend 2.39.5; it is not a backend rerun.

The 36 existing input/final-source/scratch refusals and historical executable
body comparison still pass. The old mode, original patches and all historical
receipts remain unchanged. The corrected generator requires a new reviewed,
published revision and a fresh explicit backend admission; attempt 1 cannot be
reclassified and its output directory cannot be reused.

Publication checks passed for this 43-file evidence/correction packet: all
original byte hashes, focused host tests, Python syntax, local links, diff and
sensitive-data exclusions, and the common repository gate (190 profiles;
unchanged metadata debt 37). Linux-only provenance fixtures remain CI-only.

The Perl version log contains an original final blank line. A single exact-path
Git attribute exempts only that log from the blank-at-EOF check; its recorded
bytes/hash are preserved and all other diff whitespace checks remain enabled.

## Coordinator acceptance of the correction

The coordinator independently verified the 31 original files and 21,402 bytes,
all command-log hashes, the unchanged refusal identity, fourteen successful
commands followed by the timeout, and matching retained-input snapshots. The
synthetic partial-clone reproduction passed independently, as did the existing
36 refusal checks after integration. Both actual revised tree-writing sites use
the tested option. Accept the bounded correction for a fresh generation attempt;
attempt 1 remains refused and no successful archive is inferred.
