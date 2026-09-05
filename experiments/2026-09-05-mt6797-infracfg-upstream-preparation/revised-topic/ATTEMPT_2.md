# Revised generation attempt 2: collected for independent review

One admitted invocation ran at exact published main
`725c6756e30c0e13613ee740f1a69d896fb8bea1`, `refs/heads/main`, using the
reviewed two-call-site `--missing-ok` correction. The original
[receipt](results/attempt-2-725c6756/result.json) remains
**COLLECTED_REVIEW_REQUIRED**, SHA-256
`46bbd012153289726d98a5636ab0db4b4b963b08ffb466bbb982666d2f1df86a`.
This record does not supply integrator acceptance. Attempt 1 remains refused.

## Actual generation and validation

The outer process exited 0 after 48.828 seconds. All 77 bounded commands exited
0, with no stop reasons, stderr output or surviving-group observations.
The 80-command ceiling and original per-command, stream, file and outer limits
were unchanged. No kernel build, schema comparison, QEMU or device run occurred.

| Measured identity | Value |
| --- | --- |
| Upstream parent | `4d7d9486c04d917265f64c55bd23b2cc4fe7749c` |
| Generated topic HEAD | `2338c81b81a52c5af4876bac9552ce4582fe9414` |
| Generated and replayed full tree | `bf26a25105f86061d9600a33e2461a76d072176e` |
| Optional binding SHA-256 | `0610f891e326d1e0a7ce9ffe3ef0513ab229bf37eee8177de0999cac17157c6f` |
| Header-only patch 3 mail SHA-256 | `0c8af0a97f42424830d5c6b59f9830a42d4212b728507ea6f433f7a8713fff25` |

The exact eleven final source hashes match the immutable proposal: all ten
non-schema sources equal the original topic and the binding equals upstream
optional bytes. The actual changed-path list contains exactly those ten
non-schema paths. Six generated mails replayed through a separate complete
index to the same full tree; no prefix tree or unrelated source checkout was
substituted. Both retained MT6797 DTBs report one reset cell at
`syscon@10001000`; they were inspected, not rebuilt.

The [mail archive and order](results/attempt-2-725c6756/patches/series) contain
actual Git-generated commits. [Host payload comparison](results/attempt-2-725c6756/mail-comparison.json)
confirms positions 1, 2, 4, 5 and 6 preserve their entire original diff payloads;
position 3 matches the exact 481-byte selected header-only diff. Mails 1 and 2
are also byte-identical to their historical mails. Later commit identities
change with the revised ancestry. The original proposal and all historical
patches remain unchanged.

[Checkpatch](results/attempt-2-725c6756/checkpatch.stdout) reports six totals of
zero errors, warnings and checks with only the original exclusions
`MISSING_SIGN_OFF`, `FILE_PATH_CHANGES` and `COMMIT_LOG_LONG_LINE`. Its generic
submission-ready wording does not resolve authorship, DCO or maintainer review.
The archive retains the explicitly synthetic non-certifying identity and has
no Signed-off-by, Tested-by or Reviewed-by trailers. It is not submission-ready.

[Maintainer discovery](results/attempt-2-725c6756/maintainers.stdout) records the
pinned source's DT, MediaTek, clock and reset routing. These are review contacts,
not approvals or a current-tree rebase result. No upstream message was sent.

## Preservation, inventory and handoff

Both full retained-source scans passed with integrity
`90923e5fb4d9bf2db35049abb6011437bc334aeedc528f099591f6198e9fc7aa`.
All twenty source/build pins and retained tools match before/after, and the
original processed schema remains
`a3265d87a3617c19c3463fb3a728df2120b8932ee0be686dcd8c4f69fac82b38`.
The handled scratch cleanup and final signal boundary completed normally.
A fresh post-collection check independently reacquired the shared lock,
rechecked retained pins/tools/processed schema, and confirmed absent scratch
and the clean exact project checkout. The backend window was released after
bounded collection; no further run is selected.

The [inventory](results/attempt-2-725c6756/inventory.json) covers 162 original
regular files totaling 105,885 bytes: 154 command logs, one original receipt,
six mails and their series file. Every hash was verified on the host, including
all 77 command-log inventories and six mail hashes. Files fit the 256 KiB log
and 64 KiB patch caps. Only that bounded review output was fetched; no object
database, source tree, kernel package or private device material was transferred.

Original receipts/logs/mails are published byte-for-byte. Five separate host
records accompany them: inventory/post-state, outer stdout/stderr/result and
mail comparison. A single exact-path Git whitespace exemption preserves the
Perl-version log's original final blank line. Mainline/default selection,
compilation decisions and submission certification remain integrator-owned.

The separate [integration proposal](INTEGRATION_PROPOSAL.md) describes one new
header-only patch path and named canonical subsequence/profile for root review.
It reuses five byte-identical historical payloads, preserves the old profile,
and selects no new build. This packet does not apply that proposal.

Publication validation passed for the 172-file packet: original byte/log/mail
hashes, exact payload comparison, local links, sensitive-data review, diff
checks and the common repository gate (190 profiles; metadata debt unchanged
at 37). The proposed canonical insertion was checked without editing it.
Linux-only package-provenance fixtures remain CI-only.
