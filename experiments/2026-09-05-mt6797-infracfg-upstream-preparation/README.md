# Experiment: MT6797 infracfg upstream preparation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-05-mt6797-infracfg-upstream-preparation` |
| Status | running; coherent review topic generated and style-checked, unbuilt |
| Subsystem | MediaTek clocks/resets and Devicetree |
| Device variant | Gemini PDA MT6797; no hardware operation in this audit |
| Investigator | Gemini mainline project, integration owner |
| Tracking | [upstream delivery gate](../../docs/ROADMAP.md#upstream-delivery-gate) |

## Question and result

Can the corrected infracfg reset implementation become a coherent upstream
series without the historical repair chain or unrelated power diagnostics?

**Confirmed for the topic boundary, incomplete for submission.** The pinned
upstream implementation has the compact reset-index and SET/CLEAR API needed
for the two proved reset lines. It does not register an MT6797 reset provider.
The local bounds protection remains a required part of the proposed series;
using an existing API does not justify dropping a tested refusal guarantee.
The coherent review patches are now generated and replayed as recorded below.
Schema, compile, KUnit execution and new hardware claims remain unestablished.

## Provenance and reproducibility

The repository parent is `77d0e419`. The observed upstream commit is
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c`; the related Gemini tree is
`e744a43f9d68cd3251dc0c9743ca41aac74853a8`. These are review inputs, not changes
to the kernel manifest or a declaration of the final maintainer merge base.

[Sources](sources.json) pins complete hashes and lengths for six upstream
files, two related patches and nine historical local patches.
[The audit result](results/input-audit.json) verifies all of them and inventories
the local changed paths. Public files were fetched into memory only. No Linux
source tree or third-party patch copy was created on the host.

Run from the repository root:

```sh
python3 experiments/2026-09-05-mt6797-infracfg-upstream-preparation/scripts/test-inputs.py
python3 experiments/2026-09-05-mt6797-infracfg-upstream-preparation/scripts/audit-inputs.py --fetch
```

Without `--fetch`, the auditor verifies only local inputs and explicitly reports
remote inputs unverified. Its seven tests cover valid bytes, truncation,
same-size modification, HTTP failure, redirect, partial response and bounded
downloads. An HTTP failure never establishes source absence. This tool checks
integrity and footprint; the semantic review below is a separate human-readable
finding. It does not classify upstream readiness.

## Upstream observations

At the pinned commit:

- `clk-mt6797.c` has early and platform clock initialization but no reset
  descriptor or registration. Its PLL reset-bar bit is not an infracfg reset
  provider. Registration belongs in the platform path, with failure handling
  reviewed alongside already registered clocks and the early clock provider.
- `reset.c` already selects SET/CLEAR operations, uses a compact `rst_idx_map`
  for DT translation, and checks the public index against both exposed and map
  counts. Its SET/CLEAR handler indexes the offset array with the translated
  internal bank without checking that bank against `rst_bank_nr`.
- `reset.h` already defines the 32-bit bank width, SET/CLEAR version and offsets
  `0x120` and `0x140`. No new reset-controller API is needed for valid MT6797
  descriptor entries.
- `mediatek,infracfg.yaml` lists the MT6797 compatible and allows one reset
  cell, but does not include MT6797 in the conditional list requiring it.
  Adding that requirement needs binding review, including compatibility with
  existing DTs; it is not just a header change.
- The upstream MT6797 DTS has no reset properties. Provider export and actual
  consumer wiring are distinct changes.

The source links and full hashes are in the manifest. This is a bounded review
of a named upstream revision, not proof that no unpublished or mailing-list
work exists. Repeat overlap and target-tree discovery before submission.

## Proposed coherent boundary

| Logical change | Historical inputs | Required final behavior |
| --- | --- | --- |
| Generic bounds protection with focused tests | generic portions of 0515 and 0516 | Reject an internal bank outside the descriptor before regmap; preserve normal behavior for existing users |
| MT6797 binding | 0001 corrected by 0514 | Export only public thermal ID 0 and PWRAP ID 1; review schema requirement; no TOPRGU definitions |
| MT6797 provider and descriptor tests | 0002 corrected by 0515; SoC tests in 0516 | Two SET/CLEAR banks, compact map 0 to 0 and 1 to 32, platform registration and reviewed error path |
| SoC provider declaration | 0003 | Add one reset cell on the existing infracfg node |

This split preserves the protection in the accepted
[local design](../2026-09-03-mt6797-infracfg-reset-repair/DESIGN.md).
The generic change is a separately reviewable prerequisite, not an excuse to
remove the refusal behavior. Final test placement and helper visibility need
review against existing MediaTek conventions. Do not introduce a generic API
solely to make tests easy.

Public ID 0 resolves to assert/deassert `0x120/0x124`, mask bit 0. Public ID 1
resolves to `0x140/0x144`, mask bit 0. Public 2, historical public 64, and a
malformed mapped bank must be rejected before a register write. The unproved
RST1 pair and other historical reset names remain excluded. The
[transaction audit](../2026-09-03-mt6797-thermal-auxadc-transaction-audit/README.md)
owns primary hardware-source attribution; this review does not replace it.

The local helper narrows `unsigned long id / 32` to `unsigned int`. Its actual
mapped inputs are `u16`, so this inspection does not establish a reachable
huge-ID bug. When deriving the final helper, retain the full-width bank until
validation and cover invalid input without claiming a demonstrated exploit.

## Consumer and evidence dependencies

| Consumer/evidence | Dependency missing from a provider-only series | Limit of existing evidence |
| --- | --- | --- |
| PMIC wrapper | Historical 0007 supplies the node, reset-header include and reset phandle | [Serviceability](../2026-09-04-mt6797-pwrap-reset-serviceability/README.md) validates the local corrected deployment, not the final upstream revision |
| Thermal | Historical 0519 supplies the thermal reset phandle, with its other driver/resource prerequisites | [Corrected V4 runtime](../2026-09-04-mt6797-thermal-snapshot/results/v4-runtime-pass.txt) establishes bounded observation on the local integrated candidate |
| Reset arithmetic | Production helper/descriptor plus focused KUnit configuration | [Six-case KUnit result](../2026-09-03-mt6797-infracfg-reset-repair/README.md) does not test final rebased code or provider registration failure |

Do not silently bundle either consumer into the reset topic or treat their
runtime results as `Tested-by` for an unbuilt revision. Exact final build/schema
checks and evidence mapping remain necessary. Default profiles, A72 admission,
thermal policy and TOPRGU restart remain outside this topic.

## Related work and routing

The two pinned public patches in `bsg100/gemini-linux` are useful overlap
signals, not code imported here:

- The optional-PWRAP-reset patch bypasses the missing provider by accepting no
  reset control and relying on loader initialization. It does not implement or
  prove the corrected reset mapping.
- The second infracfg-node patch adds the `0x10201000` syscon for bus protection.
  It intentionally avoids registering a second clock provider. This does not
  relocate the reset banks from the AO `0x10001000` resource.

Pinned `MAINTAINERS` routes the clock/provider work to MediaTek and common-clock
maintainers, the binding and DTS to Devicetree/MediaTek maintainers, and the
reset binding to reset-controller maintainers as applicable. Candidate trees
are the common-clock tree, MediaTek SoC tree and Devicetree tree; exact routing
and cross-tree dependency handling remain unresolved. Run upstream
`get_maintainer.pl` on the actual final patches, rather than treating a broad
path match as the recipient list. No submission or message has been sent.

## Authorship and safety

Historical 0001–0003 contain a named author and sign-off; 0514–0516 use an
unsigned synthetic experiment identity. Existing text alone does not establish
who can truthfully certify the final implementation. Audit actual derivation
and obtain genuine certification before submission. Preserve all historical
bytes and never mechanically rename or add a certifying identity.

This audit is host-only and read-only with respect to hardware. It builds no
kernel, writes no device partition, creates no backup, and consumes no device
observer or workload budget. The current corrected thermal session remains
closed to further sampling. A new build, if needed for the final series, must
use the clean pushed revision and explicit Buildbox backend.

## Handoff

- Owner: integration owner, branch `codex/infracfg-upstream-preparation` in an
  isolated small repository worktree; review is integration diff review.
- Scope: this experiment and its upstream-topic inventory entry; no manifest,
  canonical series or candidate delta.
- State: coherent review archive generated; final upstream validation active work.
- Validation: eight public input identities, nine local patch identities and
  seven auditor fixtures passed. The common repository gate passed, including
  all 189 profile-series invariants; Linux-only provenance fixtures were
  explicitly skipped on macOS and remain mandatory in CI. No final kernel
  compilation, schema validation or hardware run was performed.
- Dependencies: final coherent patch derivation, generic bounds/error-path
  review, target selection, focused validation and truthful certification.
- Removal condition: accepted equivalent changes must be present in a selected
  pinned upstream baseline and pass regression before removing local patches.
- Follow-up priority is owned by the [roadmap](../../docs/ROADMAP.md), not this
  historical handoff. This audit does not authorize a boot or upstream send.

## Coherent derivation tooling

[The derivation manifest](derivation-inputs.json) separately freezes upstream
Kconfig, Makefile and checkpatch inputs alongside the previously audited
sources. It does not alter the historical input-audit receipt.
[The generator](scripts/generate-on-buildbox) accepts one exact clean, published
project commit on Buildbox. It fetches the pinned upstream Git commit into a
bounded sparse scratch checkout and emits six unsigned normal patches in an
ignored review package. The six commits separate generic protection, generic
KUnit, binding, provider, SoC KUnit and DTS. They do not enter the active
canonical series or any runtime profile at this preparation stage.

[Source derivation](scripts/derive-topic.py) verifies every original file hash,
every intermediate source, and absence of the new paths in the actual upstream
Git tree before editing. Reset registration precedes platform clock allocation;
this intentionally differs from the historical placement and needs final build
and failure-path validation. The private reset helper retains a full-width bank,
rejects a missing offset table and leaves output addresses untouched on error.
The generated KUnit suites cover generic arithmetic separately from MT6797
mapping; their presence is not a claim that they have run.

[Eight derivation tests](scripts/test-derivation.py) passed against the pinned
public inputs, including all eleven parent-input mutations and all six repeated
phase refusals. They also check exact phase footprints, source anchors, provider
registration order and exclusion of consumer/TOPRGU changes. They fetch public
inputs into memory and do not compile or execute kernel C. The initial DTS
anchor allowed a repeated insertion; its closing-node boundary was tightened
before publication and the repeat fixture now rejects it.

The generation gate performs normal patch replay against the complete upstream
Git tree using a second index, compares the resulting tree identity, and runs
pinned strict checkpatch. Missing sign-off, new-file MAINTAINERS bookkeeping and
commit-log line length are explicitly excluded from this internal style gate;
certification and final routing remain required before submission. The sparse
checkout is removed on exit. Generated review patches remain outside the active
kernel patch inventory until a separately reviewed integration mechanism exists.
No build, schema validation, hardware operation or submission is implicit.

The first Buildbox generation at `b18a0a13` reproduced all six commits through
exact-tree patch replay, then correctly refused publication on five KUnit
continuation-alignment checks and one short Kconfig help paragraph. The
[sanitized refusal](results/first-generation-style-refusal.json) preserves that
result. The sparse source checkout and unpublished partial were removed. The
continuations and help text were corrected before a new exact revision was
submitted; no kernel compilation or device operation occurred in the failed run.


## Coherent review archive result

Exact generator revision `aa9828f93fe111ff80abec73d5a79c1af2873ae6` produced
six normal patches against upstream `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`.
The generated head is `885ecc4a32ec54bc60b570d7a2c88d7b89fd4e18`, with final tree
`04572ddae2b7f5fefaac76525f74c216a98a8c5d`. Replay through a separate Git index
reproduced that exact complete upstream tree. All six patches pass pinned strict
checkpatch with zero errors, warnings or checks under the declared exclusions.

[The generation receipt](results/coherent-topic-generation.json) records each
patch digest, all eleven changed-source digests, replay identity, style counts,
package manifest and successful Linux repository CI. Host review verified the
complete ten-file package inventory and every digest, then inspected each patch.
The review archive is retained privately under
`artifacts/upstream-review/infracfg-aa9828f9/`; it is not an active kernel series.
Buildbox retains the matching small review package, and both disposable sparse
source and project checkouts have been removed.

This establishes reproducible derivation and patch applicability to the pinned
upstream tree. It does not establish C compilation, KUnit execution, binding/DT
schema validity, controller registration behavior or runtime support for this
revision. Those gates, actual author certification and current maintainer
routing remain open. The active device inputs and all historical patch bytes
are unchanged; the topic inventory now links this bounded preparation record.

## Exact-upstream build dependency

The existing builder and package validator use one global kernel source and
assume an xz release archive with root `linux-VERSION`. The exact upstream topic
is based on a post-7.3-rc1 commit; the existing 7.1.3 local repair build cannot
validate that whole revision. A [tested integration handoff](SOURCE_INTEGRATION.md)
now supplies a complete source-selection/provenance contract and preservation
fingerprints for all 189 existing profiles. This proposal remains experiment
code until the integration owner reviews and wires it into the production
builder and verifier. The global manifest, canonical series and shared scripts
are unchanged by this handoff.

## Maintainer discovery method

[The maintainer auditor](scripts/audit-maintainers.py) runs the pinned upstream
`get_maintainer.pl` against all six exact generated patch digests on Buildbox.
It records path-only and path-plus-keyword modes separately, with Git history,
mailmap, file-address harvesting and Fixes-derived recipients disabled. Empty
local configuration and ignore files prevent account-specific exclusions.
The resulting routes are candidates for review, not an automatic mailing list or
proof of the final merge tree. No message or patch submission is sent.

The maintainer audit completed for all six patches in both modes.
[Review notes](REVIEW_NOTES.md) map their routes, identify the path-only omission
of MediaTek reviewers for the generic changes, and record the binding
compatibility question and source-level registration/resource review. The
[full routing result](results/maintainer-routing.json) is pinned evidence;
reviewer discovery does not establish a merge agreement or submission readiness.
