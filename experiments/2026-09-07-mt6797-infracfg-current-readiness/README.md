# Experiment: MT6797 infracfg current upstream readiness

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-07-mt6797-infracfg-current-readiness` |
| Status | accepted ordering stop; no current rebase admitted |
| Subsystem | MediaTek clocks, resets and Devicetree |
| Device variant | Gemini PDA MT6797; no device access |
| Date | 2026-09-07 |
| Investigator | Astra Medium current-tree and overlap audit; accepted after Sol Medium review |

## Verdict

Stop before regenerating or building an outgoing series. The accepted local
six-patch topic still applies in canonical order to the inspected current
mainline, `clk-next`, MediaTek `for-next` and linux-next source contexts. Its
generic bounds check, compact two-ID namespace and provider work remain
technically relevant. That does not settle upstream ownership.

Akari Tsuyukusa's public patch 18/32 removes the private
`mtk_infrasys_init()` function edited by local patch 4 and replaces it with the
common descriptor/probe path. The conversion is not in any inspected tree, but
the public revision has substantive review feedback and no demonstrated
maintainer ordering decision. Selecting reset-first or conversion-first from
tree absence alone would claim an unresolved upstream integration boundary.

The exact audit scope is in [the work item](WORK_ITEM.md), with current refs,
source identities, public archive receipts and frozen local inputs in
[the source receipt](results/source-review.json). No patch, profile, manifest,
series, roadmap or upstream-topic registry changes in this assessment.

## Current source result

The four inspected trees still use MT6797's private probe. None contains an
`infracfg_desc`, MT6797 reset descriptor/header/tests or `#reset-cells` in the
SoC DTS. The current common MediaTek clock helper publishes the OF clock
provider before managed reset registration; reset-registration failure still
jumps directly to clock teardown without first removing that provider. The
separate removal-before-free cleanup therefore remains relevant if the
conversion-first path is selected.

The revised six patches apply cleanly in sequence to a minimal tree containing
the current mainline files they touch. All hunks also matched uniquely in the
other three inspected source contexts. These are exact textual/context checks,
not a full-tree replay, compile, schema run or runtime result.

## Per-patch disposition

| Patch | Current disposition | Reason |
| --- | --- | --- |
| 1: generic SET/CLEAR bank bounds | Retain | Current `reset.c` still indexes the translated bank without checking it against `rst_bank_nr`. This is a promised refusal contract, not a new exploit claim. |
| 2: generic KUnit | Retain with patch 1 | It exercises the production arithmetic without hardware. Historical results do not substitute for a current-base run. |
| 3: MT6797 two-ID header | Retain in header-only form | The current schema permits optional one-cell declarations. Making the property mandatory would reject older valid descriptions. |
| 4: MT6797 provider | Hold for ordering | Reset-first inserts registration in the private probe; conversion-first must use `infracfg_desc.rst_desc` on the exact converted base with safe common-helper unwind. |
| 5: MT6797 descriptor KUnit | Retain with the descriptor/header/helpers | It checks the two pairs and rejected public IDs, not controller registration lifetime or MMIO behavior. |
| 6: MT6797 SoC DTS declaration | Independently routable, still coordinated | The one `#reset-cells` property has no new-header or consumer dependency, but must remain semantically coordinated with provider availability. |
| Separate common-helper cleanup | Retain conditionally | It is required before a conversion-first reset hook because the current failure path leaves the published clock provider live while freeing its backing clocks. Private-probe patch 4 does not depend on it. |

## Conditional dependency decision

If maintainers select reset-first, preserve generic patches 1 then 2, the
header-only patch 3, provider patch 4 then descriptor test 5, and route DTS
patch 6 separately. If maintainers select conversion-first, start from the
exact accepted conversion base, apply or supersede the common-helper cleanup,
then adapt only the reset descriptor/header hook. Do not import the 32-patch
conversion into this repository merely to choose that branch.

Clock maintainers own the generic/provider/test and cleanup route, with
MediaTek review. The public reset header additionally needs DT and reset
maintainer review. The SoC DTS remains a MediaTek-tree change with DT review.
Current `MAINTAINERS` identities are pinned in the receipt; this assessment
does not claim their agreement.

## Evidence transfer and limits

The historical Buildbox compile, eight intended arithmetic cases, focused
binding compatibility comparison, exact old-base replay and cleanup fixtures
remain valid only for their recorded bytes and contracts. They support the
topic's feasibility and refusal intent. They do not establish a current-base
build, conversion/module behavior, current provider-failure lifecycle, hardware
support, a transferable `Tested-by`, authorship or DCO certification.

No current Buildbox run is justified until an ordering disposition admits one
implementation branch and changes exact kernel inputs. The synthetic archive
identity remains explicitly non-certifying and is not submission-ready.

## Single next discriminator

Obtain an attributable clock/MediaTek maintainer ordering disposition for the
exact public patch 18/32 revision and this reset topic. The disposition must say
whether reset integration should precede the conversion or target its accepted
base. Only then freeze the corresponding Luna High rebase contract and run its
current-base Buildbox, KUnit, schema, DT and checkpatch gates.

No maintainer contact was made by this audit. Contact, authorship and truthful
DCO certification remain separately authorized upstream-publication steps.

## Safety and validation

Four official refs, selected source bytes, directory absence, local hashes,
canonical series order and public archive pages were checked. The manifest
series invariant passed for all 196 profiles. A bounded temporary touched-file
tree confirmed current-mainline patch application and was removed. No Linux
tree was retained. No build, VM, device, private evidence, firmware action,
candidate, deployment or upstream contact occurred, and no hardware-support
claim follows.

Independent Sol review verified all per-patch dispositions, optional binding
compatibility, the conditional common-helper cleanup, exact hashes/links,
canonical order, the 196-profile invariant and the single discriminator. It
accepted the packet at `2026-09-07T18:52:09Z` without rework.
