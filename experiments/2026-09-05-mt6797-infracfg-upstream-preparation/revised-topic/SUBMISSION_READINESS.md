# Integrated topic: final submission-readiness review

The exact application series at `538906df82588885e5f2606cf40901f354c90748`
is technically collected and independently accepted, but **not ready to send**
with its synthetic unsigned metadata. The human authorship/certification and
assistance disclosure must be finalized. Local preparation now explicitly
selects the six-patch topic first because the overlapping MT6797 common-probe
conversion is absent from the inspected current trees; that is not maintainer
ordering agreement. No upstream message or new build is selected.
[Integration](https://github.com/ixoo/gemini-pda-mainline/blob/538906df82588885e5f2606cf40901f354c90748/experiments/2026-09-05-mt6797-infracfg-upstream-preparation/revised-topic/INTEGRATION.md)
limits inherited evidence: the newly named profile was not rebuilt or run on
hardware. This review supersedes the old readiness packet's pending binding
correction and compile-only common-cleanup proposals, not their original records.

## Fresh routing and overlap

The prior [readiness ledger](readiness-refresh.json) pins the six integrated
patch hashes and profile. The [current-ref record](../results/upstream-ordering-refresh-20260906.json)
records the exact inspected refs. Mainline is
`9f0346dcbea363787186c94ef94dd01aaa215afa`; clock `clk-next` is
`91b1b8d437abe0cd83210d8f257b785a63047aa9`; MediaTek `for-next` is
`f5be25e697e0362103625b1b197af126ae4ba5f7`.

The compact [refresh record](../results/upstream-ordering-refresh-20260906.json)
enumerates all eleven patch-footprint paths against the three official refs.
For byte identity, this handoff claims only the four paths independently
verified by the coordinator: `clk-mt6797.c`, the supplemental `clk-mtk.c`, the
infracfg binding, and `mt6797.dtsi`. The record retains the other path statuses
without promoting them to an outgoing replay result. The MT6797 file still
uses `mtk_infrasys_init()` and has no common-probe conversion symbol in the
inspected mainline or clock snapshots. Exact outgoing replay on the final
current tree remains required before send; these are not ancestry or rebase
tests.

Proposed recipients, confirmed against the actual archive's
[maintainer output](results/attempt-2-725c6756/maintainers.stdout) and refreshed
sections:

| Patches | Primary routing | Additional review |
| --- | --- | --- |
| 1, 2, 4, 5 | Clock: Stephen Boyd, Brian Masney, Jerome Brunet; `linux-clk@vger.kernel.org` | MediaTek: Matthias Brugger, AngeloGioacchino Del Regno; `linux-mediatek@lists.infradead.org`, ARM/kernel lists; reset review as appropriate |
| 3, header only | Keep with clock/reset provider topic | Rob Herring, Krzysztof Kozlowski, Conor Dooley, Philipp Zabel; `devicetree@vger.kernel.org` |
| 6, shared DTS | MediaTek with DT review | Same MediaTek/DT maintainers and lists; no new-header include dependency |

Exact public addresses remain in the linked generated output and fresh ledger.
The cover can copy the relevant combined audience; this is not permission to
send. Do not infer acknowledgements or merge agreements from routing output.

The [August 3 common-probe conversion](https://lists.infradead.org/pipermail/linux-mediatek/2026-August/111265.html)
by Akari Tsuyukusa removes the function edited by patch 4. The official August
and September thread indexes and exact message were refreshed; no newer
MT6797 conversion title appeared in those bounded indexes, and the conversion
is absent from the current selected files. This does not
exclude another list, unindexed version, private branch or unpublished work.
The web viewer failed on those archive URLs; bounded direct HTTPS retrieval
succeeded and its hashes are recorded. There is no new evidence of acceptance.

Keep current reset-first registration for the locally selected topic-first
ordering. If maintainers select the conversion first, adapt only provider
integration to its `rst_desc` hook on that exact base. The separate common
clock cleanup is implemented and validated locally, but is conditional and
excluded from this topic; its post-publication reset-error ordering would be a
prerequisite to that adaptation. [Provider compile evidence](https://github.com/ixoo/gemini-pda-mainline/blob/a65946fb8bdd66232e95d61506cb43d27a5d22f6/experiments/2026-09-05-mt6797-infracfg-upstream-preparation/PROVIDER_COMPILE.md)
does not justify importing the conversion or passive SCPSYS changes here.

## Per-patch provenance and actual authorship boundary

[The metadata ledger](authorship-facts.json) hashes six historical inputs and
the six exact integrated patches. Historical 0001–0003 record Julien Etienne
as author/signatory. Historical repairs 0514–0516 and all six integrated review
patches record the synthetic experiment identity, without certification.
Those are observable metadata facts, not proof of who wrote or may certify the
regenerated work. Repository commit authorship is not a substitute either.

| Patch | Concrete derivation and retained content | Human fact still needed |
| --- | --- | --- |
| 1: generic bounds | Existing upstream reset API plus generic repair in 0515; regenerated private helper preserves full-width bank validation and explicit refusals before register access | Actual contributor(s) to the repaired/regenerated helper; no old sign-off covers it automatically |
| 2: generic tests | Generic portions of repair/test work in 0516, reorganized into four direct tests using the production private helper | Actual contributor(s) to the new split and assertions |
| 3: two-ID header | Historical 0001 reduced by 0514 to thermal 0/PWRAP 1; revised payload retains only the eight-line header, with no schema requirement | Actual contributor(s) and right to submit under its GPL-2.0-only OR BSD-2-Clause identifier |
| 4: provider | Historical 0002 repaired by 0515; two SET/CLEAR banks, compact map, new private descriptor and regenerated reset-first registration | Actual contributor(s) to corrected mapping, descriptor and registration changes |
| 5: descriptor tests | MT6797 portions of 0516 reorganized into four production-descriptor tests | Actual contributor(s) to the final four tests and build wiring |
| 6: DTS declaration | Retained one-cell declaration from historical 0003, rebased at the exact upstream node | Confirm final attribution; historical named metadata alone does not authorize carrying its sign-off |

The [derivation source](../scripts/derive-topic.py), pinned upstream inputs and
[repair design](../../2026-09-03-mt6797-infracfg-reset-repair/DESIGN.md) make the
transformation reviewable. Register facts come from the linked transaction
audit, not a license to copy proprietary implementation. The current packet
contains no private capture or vendor implementation. This is a provenance
review, not a fresh clean-room or legal-rights finding. New helper/test source
uses GPL-2.0-only identifiers; the public header's dual license is explicit.

## Smallest explicit human certification decision

After reviewing these exact six diffs and provenance, the owner needs to provide
one consolidated decision: identify the correct actual author(s) for patches
1–6 and the intended public name/email, state any per-patch exceptions, and
personally decide whether they can truthfully certify DCO 1.1 for the exact
contributions. If all six share one author/certifier, one explicit statement
covering all six suffices to settle the identity decision; otherwise retain the
per-patch distinctions. Do not infer the answer from device authorization,
repository push authorization, account ownership or historical trailers.

The current [submission process](https://docs.kernel.org/process/submitting-patches.html#sign-your-work-the-developer-s-certificate-of-origin)
and [DCO](https://developercertificate.org/) explain certification of creation
or permitted derivation and public retention of the contribution. The human
submitter must review the work and add their own certification. This packet
asks for no signature and adds none; it supplies a concrete decision for the
coordinator to put to the owner. If the owner cannot certify or identify the
actual authors, leave the archive unsigned rather than manufacturing a chain.

Current [coding-assistant guidance](https://docs.kernel.org/process/coding-assistants.html)
also calls for assistance attribution, distinct from human certification.
The final outgoing metadata should truthfully disclose `Assisted-by: LLM`;
do not list routine Git/compiler tools in that tag or invent reviewers/testers.
The [tool-generated-content guidance](https://docs.kernel.org/process/generated-content.html)
asks for tools, input/nature of assistance, affected scope and validation.
The cover draft supplies a factual summary of Codex assistance in source audit,
helper/test regeneration, compatibility correction and evidence review.
Preserve the immutable unsigned archive; any final author/assistance metadata
belongs to a separately reviewed outgoing representation with identical payloads.
No additional kernel build follows merely from that metadata change.

## Cover and validation boundary

[The cover draft](COVER_LETTER.txt) describes the accepted header-only series,
its exact base and scoped validation without repeating the superseded binding
proposal. It distinguishes eight intended arithmetic cases from the additional
four upstream QEMU cases, records the accepted compatibility comparison, and
avoids hardware support, new-profile build or certification claims. The source
base stays pinned until the integrator and maintainers choose any rebase.
No new Fixes/Reviewed-by/Tested-by attribution is invented.

The four-file host packet passed selected-source/patch hash comparisons, JSON
and local-link checks, sensitive-data/diff review and the common repository
gate (190 worker profiles; unchanged metadata debt 37). Root's integrated
192-profile validation remains the separate integration record. No kernel,
schema, QEMU, backend or device execution was performed for this refresh.

## Current blockers and handoff

The local ordering decision is bounded and reviewable, but the topic remains
conditional. Before sending, run current-tree outgoing replay, checkpatch and
get_maintainer on the exact final patches. Resolve the actual authorship,
truthful DCO certification and `Assisted-by` disclosure for each patch, then
coordinate ordering with the clock/MediaTek maintainers and the conversion
author. No manifest, profile, canonical series or patch bytes change here.

## Coordinator review

Project Planning checked the selected and historical patch hashes against the
actual integration worktree and confirmed the profile matches the manifest.
The cover retains the original test and no-new-build scope. The current
official-ref refresh independently covers all eleven footprint paths and
records the topic-first local ordering without promoting it to maintainer
agreement. Current official coding-assistant and generated-content guidance
was independently read; its assistance disclosure and human-certification
boundaries match this packet. This accepts the preparation handoff, not
permission to submit or proof of human authorship. The worker's 190-profile
check remains historical; integration checks cover all 192 profiles.
