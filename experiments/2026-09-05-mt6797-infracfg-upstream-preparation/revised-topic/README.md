# Revised minimal MT6797 reset topic: concrete review inputs

## Selected correction

This proposal consumes the accepted [focused compatibility comparison](../binding-compatibility/ATTEMPT_3.md)
from exact execution revision `003e552ec598061cb711e321bb39a36fab846079`.
It replaces only original patch 3's payload with the concrete
[header-only Git diff](0003-mt6797-reset-header-only.diff). The other five input
patches remain byte-for-byte historical originals. No manifest, canonical series,
source tree, build or device candidate changes here; root owns any integration.

The [ordered proposal](proposal.json) is the exact six-input review artifact:
positions 1, 2, 4, 5 and 6 reference existing normal patches by path and SHA-256;
position 3 references the supplied 481-byte diff, SHA-256
`dc1e60d1a528931eb035093132b35c4c32a7169d62a2cf8b4b77777fdee99ba2`.
This is a usable Git patch payload, **not a newly generated format-patch mail**.
No replacement Git commit/tree identity, mail author or certification is invented.
A full regenerated mail archive requires a separately assigned backend window.

[Existing derivation](../binding-compatibility/derive.py) generated that file
from exact original patch 3 SHA-256
`88e629b8a56aa892f43949bc052322efb38ba209df7b4d5c6a8d8df936c6fb03`.
It preserves the complete new-header hunk and omits the sole schema hunk.
`git apply --numstat` reports one file, eight insertions, no deletion. This
parses the supplied patch; it is not a full-upstream-tree application test.

The header remains SHA-256
`d83d278526a434d453f66235d28a737d4803fe315b82c6bea79d27ecb6c23269`, with
thermal ID 0 and PMIC-wrapper ID 1. Relative to upstream
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c`, the binding is unchanged, SHA-256
`0610f891e326d1e0a7ce9ffe3ef0513ab229bf37eee8177de0999cac17157c6f`.
No compatible, optional value constraint, unrelated required branch or ID changes.

## Logical split and dependencies

| Position | Logical change retained | Dependency and route |
| --- | --- | --- |
| 1 | Generic SET/CLEAR reset translation bounds | Independent safety fix; clock tree, MediaTek/reset review |
| 2 | Generic arithmetic KUnit cases | Uses private helper from 1; clock tree |
| 3 | Two public MT6797 reset IDs, header only | Independent header definition; clock topic with DT/reset review |
| 4 | MT6797 descriptor and reset-first provider registration | Requires 1 and 3; clock tree |
| 5 | MT6797 descriptor/mapping KUnit cases | Requires 1, 3 and 4; clock tree |
| 6 | One reset cell on the shared MT6797 infracfg DTS node | No new-header include or consumer phandle; separate MediaTek/DT route |

Position 6 affects the shared description used by both MT6797 in-tree DTBs.
Its syntactic independence is not a promise that reset consumers work without
the provider. No thermal/PWRAP consumer, TOPRGU restart, CPU/power policy or
CONN implementation enters this topic.

The separately compiled provider components remain distinct:

- Common clock cleanup, patch SHA-256
  `eabc1a33c23b4511a285bb2660376585f4e8332f2bca124ffab606e308ee9a62`,
  fixes the post-publication reset-error unwind in `clk-mtk.c`.
  Current position 4 registers resets before platform clock allocation, so it
  does not depend on this common-probe error-path fix. If the separately proposed
  MT6797 common-helper conversion lands first, adapt position 4 to its `rst_desc`
  hook only on that exact selected base, with the cleanup prerequisite retained.
- Passive SCPSYS registration, patch SHA-256
  `e2338d566150a9e5a929b6a37e1bf76e356c4989391dd8549ed36b8e7554bc7f`,
  belongs to power-domain lifecycle work and is not a reset-topic prerequisite.
  No SoC/CONN selection or lifetime claim is inferred from its compilation.

Their [isolated compile evidence](https://github.com/ixoo/gemini-pda-mainline/blob/a65946fb8bdd66232e95d61506cb43d27a5d22f6/experiments/2026-09-05-mt6797-infracfg-upstream-preparation/PROVIDER_COMPILE.md)
at project `7029b1368134eef359dc43997bad84b73f426578` established ARM64
compilation/linkage for only those two proposals. Corrected source hashes are
`01f33c475e9bbe6ffef504d8247acd618bd53cc563de42abef4ada96b8344646`
(`clk-mtk.c`) and
`216b022e433b2a55b255d30933e313e296415c624306dd6b0c4f76ac65a51f54`
(`mtk-scpsys.c`). Neither component is silently imported into the six-input
proposal, and that compile is not a build of this revised reset topic.

## Generation path and exact validation boundary

Reuse the existing [Git generation/replay path](../scripts/generate-on-buildbox)
in a separately reviewed window; do not run the historical generator unchanged,
because its binding phase deliberately reconstructs the old mandatory hunk.
The required generation delta is specific: in the six-phase sequence, replace
the binding-phase payload with the supplied derived header diff and leave the
schema at its pinned upstream bytes. The old intermediate checker expects the
mandatory schema, so it must not be bypassed and then falsely reported as passed.
An exact revised input path can instead apply the six ordered review payloads
through the existing Git apply/commit/format-patch and separate-index replay
operations, with complete source hashes from `proposal.json` as the final check.
No new validation framework is proposed here.

The replacement position-3 subject should describe adding MT6797 reset IDs.
Its message should explain the two exported IDs and why the existing optional
reset-cell binding stays unchanged. Regenerate the one-file/eight-insertion
mail diffstat from Git. Subsequent mail commit IDs may change with ancestry;
compare unchanged patch payloads, not those regenerated mail envelopes, to the
historical positions 1, 2, 4, 5 and 6. Preserve the original files and receipts.

Required at that admitted generation boundary:

1. Verify exact upstream Git parent, absence of the five new file paths, all six
   ordered input hashes and a clean published project revision. Preserve shared
   prepared source/build inputs under the normal lock and existing cleanup rules.
2. Generate actual commits and format-patch output; replay against the complete
   pinned upstream tree using the existing separate-index check. Require all ten
   non-schema final source hashes to equal the original topic, and schema bytes
   to equal the accepted optional upstream hash. Record a new actual commit/tree.
3. Run pinned checkpatch and final maintainer discovery on that exact archive,
   identifying any explicit experiment-only exclusions. Verify both MT6797 DTBs'
   one-cell property from exact applicable evidence. Do not promote an expected
   source-hash ledger into a measured revised-tree or rebuilt-DTB result.
4. Review whether an exact build is needed after the actual replay/source
   comparison. This proposal changes no C, header, configuration or DTS payload
   relative to the tested topic; only its schema delta is removed. No automatic
   kernel rebuild, schema repeat, QEMU repeat or physical boot is selected here.

Existing evidence can be carried with its scope: original topic compilation,
reset arithmetic tests and original binding/DT checks; accepted 50-row focused
optionality comparison with attributed raw/decoder errors; separate actual-C
provider tests and two-proposal compilation. Full revised-topic generation,
exact replay/style/routing and final submission certification remain pending.

## Authorship, DCO and destination

All historical review mails use the explicitly synthetic non-certifying
`Gemini Mainline Experiment` identity. Actual authorship and DCO remain unresolved
for the corrected generic helper/tests, MT6797 descriptor/provider/tests, two-ID
header and DTS declaration. Historical named sign-offs do not certify combined
new work. No person is assigned authorship here, and no Signed-off-by, Tested-by,
Reviewed-by or maintainer acceptance is added. This packet is not submission-ready.

Read-only public-ref refresh on 2026-09-05 still reports clock `clk-next`
`91b1b8d437abe0cd83210d8f257b785a63047aa9` and MediaTek `for-next`
`f5be25e697e0362103625b1b197af126ae4ba5f7`. The
[existing routing/overlap record](../SUBMISSION_READINESS.md) therefore remains
the scoped destination proposal: generic/provider/test changes via clock,
header with DT/reset review, and the DTS declaration via MediaTek with DT review.
This refresh is not a full-tree rebase test or assurance against unpublished
conversion revisions. Maintainers still determine ordering with the overlapping
MT6797 common-helper conversion. No upstream message has been sent.

## Host checks and handoff

[Derivation checks](derivation-check.json) pass the three changed-input refusals
and preserve the header bytes. The complete six input hashes were independently
compared to the original generation receipt; only position 3 differs. Patch
parsing confirms its one-file/eight-line footprint. The proposal source map is
explicitly an expected result until backend replay. This packet contains no
kernel source tree or generated mail archive and changes no author's old patch.

Common repository checks passed for four scoped files (190 profiles; unchanged
metadata debt 37). JSON/link review and diff/sensitive-data checks passed. No
backend generation, kernel build, checkpatch, new schema/QEMU or device run
was performed for this proposal.

## Coordinator proposal review

The coordinator independently verified all original and selected input hashes,
reproduced the exact header-only diff with the existing derivation, rejected
three changed inputs, and confirmed the one-file/eight-insertion patch footprint.
The logical dependency split is accepted as the basis for revised generation.
Expected final source hashes remain expectations until the full-tree replay.
No manifest selection or historical patch replacement occurred in this review.
