# Experiment: MT6797 TOPRGU restart upstream readiness

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-05-mt6797-toprgu-upstream-preparation` |
| Status | completed readiness assessment; submission readiness inconclusive |
| Subsystem | MediaTek watchdog system restart |
| Device variant | Existing named Gemini PDA; retail subvariant unconfirmed |
| Date | 2026-09-05 |
| Investigator | Repository assistant source review; no kernel authorship certification |

## Question or hypothesis

Can the demonstrated Gemini kernel restart be proposed independently of the
infracfg series, TOPRGU reset-controller exports and experiment observers?
The implementation can be separated. Its policy scope, pending overlap,
authorship and exact modern regression remain unresolved.

## Provenance and environment

Review target: upstream Linux `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`,
queried from the Torvalds master commit API on the review date. Immutable URLs
and file hashes, plus historical patch hashes, are in
[the source receipt](results/source-review.json). This selects no build profile.

Historical runtime authority is the
[Candidate AB experiment](../2026-07-20-mt6797-kernel-restart-diagnostic/README.md)
and its [single attended result](../2026-07-20-mt6797-kernel-restart-diagnostic/results/runtime-candidate-ab-attempt-1-20260721.txt).
Candidate AB raw boot-image SHA-256 is
`61c74592267466735164c19f8b831ea18db2892de95e32109f2aacd7ec5c5446`.
Do not infer that a modern minimal derivative has been tested from this result.

## Safety assessment and associated code

Read-only review of repository patches and individual public upstream files.
No source tree was extracted, no shared manifest, series or cache changed,
and no kernel built. No device connection, observer, watchdog open, register
write, reset or upstream message occurred. This directory supplies prose and a
JSON receipt, not an executable session or a deployment candidate.

## Procedure and observations

Read historical patches 0081, 0087 and 0090; inspect the exact upstream driver,
binding, MT6797 DTS, PSCI priority and MAINTAINERS; compare with retained AB
evidence and public overlap. File hashes make the source comparison repeatable.

At the pinned revision, `mtk_wdt_restart()` clears IRQ mode and writes the mode
key before its software-reset loop. It does not set bit 4. The driver defines
`WDT_MODE_AUTO_START`, but neither start nor adoption applies the historical
MT6797 policy. Watchdog restart priority remains 128; PSCI remains 129.
There is no explicit MT6797 driver match entry. The existing MT6797 DTS and
binding use the MT6589 fallback. No new compatible string or DT property is
needed merely to attach MT6797-specific match data while retaining that form.

The [July compatible-cleanup proposal](https://lore.kernel.org/all/20260716161923.266315-1-akkun11.open@gmail.com/)
adds explicit matches, changes fallback policy and adds MT6589 resets.
Its [archived cover letter](https://lists.openwall.net/linux-kernel/2026/07/16/1687)
was read directly. That proposal overlaps the MT6797 match-entry prerequisite;
it is not evidence that Gemini restart policy was accepted. The pinned driver
still lacks the entry. Pending status is unresolved: an HTTPS refs query to the
MAINTAINERS watchdog tree failed certificate verification, which was not bypassed.
This review cannot claim absence of equivalent pending changes.

Pinned MAINTAINERS names Wim Van Sebroeck and Guenter Roeck for watchdog,
with `linux-watchdog` as the subsystem list and the linux-watchdog.org tree.
MediaTek review belongs with Matthias Brugger and AngeloGioacchino Del Regno
and the MediaTek list. Resolve the exact submission base and generated recipient
list again before any submission; no mail was sent.

## Analysis: proposed independent delta

| Logical change | Proposed boundary | Evidence and remaining decision |
| --- | --- | --- |
| MT6797 match data | Add or reuse the explicit compatible entry; obtain match data before policy use; keep null-data behavior for other SoCs | Coordinate with pending compatible cleanup; do not duplicate its entry or remove fallback incidentally |
| Restart mode | Apply the existing bit-4 policy only to MT6797 in the software-restart path | Historical 0081 also changes watchdog start and adoption; extracting only restart is a new untested derivative |
| Restart ordering | Carry a per-match priority, retain 128 for other SoCs | Historical 0087 uses 255, above PSCI 129; 130 is a narrower untested alternative, not an interchangeable proven value |
| Match-data/reset separation | Register a reset controller only when a nonzero reset count is supplied | Policy-only match data must not accidentally register an empty reset controller |

Prefer two reviewable behavior changes: restart-mode policy with the required
match-data plumbing, then ordering policy. The exact split remains a proposal,
not generated patches. Do not silently include 0081's IRQ/dual-mode normalization
on adoption, or its start-path behavior: those affect watchdog expiry and
pretimeout contracts beyond ordinary restart and require separate justification.
Check all early match-data consumers and initialization ordering when implementing.

The priority decision is substantial: 255 gives MT6797 a high-priority restart
handler across boards, not just this Gemini. A success on one firmware stack
does not justify universal preference over firmware. Establish the scope of the
firmware limitation before choosing a SoC-wide rule or a narrower policy.
The suspected PSCI hang before TOPRGU remains an inference; no retained trace
captures the failing handler entry. Do not present that mechanism as measured.

0081/0087 carry synthetic internal author identities. Neither commit metadata
nor the existing driver's author establishes who can certify these new changes.
Actual authorship and truthful DCO remain gates. Preserve the historical files;
do not mechanically rename their authors or invent sign-offs.

Exclude 0090's reset IDs and `#reset-cells`, A72 power/unpark changes in
0093/0111, raw/locked status observers in 0303/0308, and recovery takeover
0386/0387/0489. They are separate behaviors even where they touch the same
driver. Restart does not depend on the six infracfg patches or their reset header.

AB supplies one ordinary kernel restart with no userspace watchdog, a retained
candidate marker, owner-observed prompt reset and changed-boot Gemian return.
Its 27.854 ms interval ends at the final retained kernel restart line; it is not
an instrumented reset-completion latency. Firmware's watchdog-class reason
cannot distinguish software reset from expiry. Repeatability, other MT6797
boards and modern minimal-source behavior remain unestablished.

## Readiness gates and conclusion

Confirmed: an independent restart topic is structurally possible. Inconclusive:
submission readiness and modern hardware equivalence. Required evidence before
admission is an exact current subsystem base/overlap resolution, justified policy
scope and bit semantics, actual authorship, and a reviewed minimal patch series.

Offline validation should exercise match-data absence, MT6797 policy selection,
unchanged non-MT6797 priority/mode behavior, zero-reset-count registration
refusal, and watchdog adoption/start/pretimeout non-regression. Review generated
patches with Checkpatch and build only an exact clean pushed revision through
Buildbox after integration admits it. No build is required for this prose review.

A future separately admitted session must bind an exact candidate and preserve
pending evidence before one explicit ordinary restart, exclude userspace
watchdog fallback, and confirm a changed known-good recovery boot. Failure or
missing attribution stops the attempt; a restart pass establishes only that
bounded result. This is a proposed acceptance boundary, not a selected boot or
permission to repeat an existing session.

## Follow-up

Validation: common repository checks passed, including all 189 manifest profiles
and the invariant refusal fixtures. JSON parsing, local links, staged scope and
sensitive-data exclusions passed. The Linux-only artifact-provenance fixture was
skipped on macOS; no kernel build, Checkpatch, DT schema or device test was run.

Integration owns adoption and scheduling through
[the roadmap](../../docs/ROADMAP.md) and
[the upstream topic registry](../../project/upstream-topics.json).
Hardware support and the registry remain unchanged by this assessment.
