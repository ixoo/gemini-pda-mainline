# Revised topic generation: bounded execution plan

Status: this plan was used by [attempt 1](ATTEMPT_1.md) and
[attempt 2](ATTEMPT_2.md); no further execution is admitted here.
The integrator must first review and publish the exact execution revision on
`origin/main`, then assign one Buildbox generation window. This is generation
of an unsigned review archive, not a kernel build or device operation.

## Exact invocation after admission

In the clean managed project checkout of the integrator-selected full revision:

```sh
timeout --kill-after=5 1000 bash \
  experiments/2026-09-05-mt6797-infracfg-upstream-preparation/scripts/generate-on-buildbox \
  --revised EXACT_PUBLISHED_40_HEX_REVISION refs/heads/main
```

The revision placeholder must be replaced by the admitted actual commit, not a
branch expression. The generator compares checkout HEAD, cleanliness, exact
project origin and a fresh remote branch advertisement before generation.
A branch advance is a refusal, not permission to choose another commit.
Use the existing SSH access with BatchMode, five-second connect timeout and
ForwardAgent disabled. Project checkout preparation remains Git-based.

One existing prepared source is retained read-only:
`/workspace/gemini-pda/src/linux-7.3-rc1-series-mt6797-infracfg-upstream-kunit-source`,
with its existing build and schema environment pinned by
[the retained contract](../schema-contract.json). No Linux working tree is
copied, extracted, edited or built. Disposable bare Git metadata fetches only
through Git from the exact upstream commit in [proposal.json](proposal.json);
two indexes generate and replay the complete tree without checking it out.

Before the window, require at least 1 GiB free on the host and each backend
scratch/output filesystem. The explicit real output parent
`/workspace/gemini-pda/review-packages/infracfg-revised` must already exist;
the integrator may create that managed directory during setup. The generator
uses the existing regular no-follow shared Buildbox lock exclusively and
nonblockingly. It requires the real managed scratch parent and checks backend
headroom itself. There is no tool installation or alternative backend.

## Checks and action ceiling

The mode pins the complete proposal digest, all six ordered selected inputs
and every historical input. It verifies the upstream Git identity and absence
of the five new files; applies each input with a preceding cached check; checks
whitespace and creates real commits. Only patch 3's message and selected payload
change deliberately. Original files and historical receipts are untouched.

Acceptance requires exactly the ten changed source paths and all eleven source
hashes in the proposal, including the unchanged optional binding. Six actual
format-patch mails must fit 64 KiB each. A separate index replays all six against
the exact upstream parent and must produce the identical complete tree.

The existing bounded process collector permits at most 80 commands (77 planned),
30 seconds each except the Git fetch (60 seconds) and two source integrity
checks (180 seconds each). Every stream is capped at 256 KiB; child-created
regular files are capped at 128 MiB. The outer command caps the entire run at
1,000 seconds, with five seconds for termination. These are per-file and time
bounds, not an aggregate scratch disk quota. Any timeout, nonzero status,
unexpected stderr, surviving process group or late observed signal prevents
acceptance. Existing process-group cleanup and final signal accounting are reused.

The retained checker runs strict checkpatch, with only the historical
`MISSING_SIGN_OFF`, `FILE_PATH_CHANGES` and `COMMIT_LOG_LONG_LINE` exclusions.
It records Git/Perl versions and maintainer discovery from the pinned prepared
source; discovery sends no message. Both retained MT6797 DTBs are checked for
the one-cell declaration. These are existing DTB observations, not rebuilt
DTBs. No schema comparison, QEMU run or kernel compilation is repeated.

Full retained-source integrity is checked before and after successful generation.
The existing 20 source/build pins, tool identities and original processed-schema
hash are checked before and in final preservation handling. A failure before
the full post-scan cannot claim that scan passed. Managed scratch is removed
on handled success/failure; recognizable stale scratch is cleared on the next
run, while unknown contents and symlinks refuse. A hard kill may leave scratch
and an INCOMPLETE receipt for review.

## Evidence and decision

The exclusive output directory is the admitted revision below the managed
output parent. It is never overwritten, including after refusal. Preserve its
original receipt and logs before considering a new admission. No automatic
retry is selected. Successful collection records the actual six patch hashes,
commit/tree identities, complete-tree replay and retained-input preservation
as `COLLECTED_REVIEW_REQUIRED`; the integrator must independently accept it.

Fetch only that bounded review package after checking its regular-file inventory
and size, keeping initial raw receipts private until sanitization review. No
source checkout, object database, kernel package or private device data is a
publication input. Publish the reviewed mails and sanitized evidence separately
from the immutable historical archive. Actual authorship/DCO remain unresolved;
all generated identities are explicitly synthetic and non-certifying.

[Host refusal checks](test-generation.py) exercise the actual input, final-hash
and scratch guards; they also compare the historical executable bodies against
`78318abe188f488b12e0016781a5bbf249a79735`. The
[host result](generation-host-check.json) is not evidence of backend generation,
checkpatch, maintainer discovery or full-tree replay. The integrator owns any
later manifest/series selection and any decision about compilation.

Host validation for this implementation passed all 36 refusal cases, historical
body preservation, Bash syntax, ShellCheck and the common repository gate
(190 profiles; unchanged metadata debt 37). Python syntax, local document links,
diff and sensitive-data exclusions were reviewed. Linux-only package-provenance
fixtures remain CI-only. No backend generation, kernel build, checkpatch, schema,
QEMU or device execution is claimed by these host results.

## First attempt and corrected partial-clone tree writing

The first admitted run refused during ordinary tree writing; see
[its immutable result and diagnosis](ATTEMPT_1.md). The revised generator now
uses `write-tree --missing-ok` in generation and replay to avoid prefetching
unrelated omitted blobs. It retains full indexed tree identities and every
explicit changed-source/footprint/replay check. All original limits are unchanged.
The correction passed the [synthetic host check](partial-tree-host-check.json)
and existing 36 refusals, and was exercised by [attempt 2](ATTEMPT_2.md). Any further execution needs
a fresh exact-revision admission; this document does not select another run.
