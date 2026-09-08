# MT6351 MFD upstream preparation

Status: incomplete upstream-preparation checkpoint, 2026-09-08. No new kernel
candidate, device access or upstream submission. Selected series and profiles
are unchanged. [Source receipts and check results](source-review.json) pin the
individual public files inspected; Linux sources are not vendored here.

## Scope and result

The existing Gemini MT6351 core patch combines a four-bank extension with a
correction to an already supported chip. Separate that correction before
adapting the MT6351 topic. The unsigned [MT6328 draft](patches/0001-mfd-mt6397-size-MT6328-interrupt-domain.patch)
adds a terminal interrupt count and selects it for MT6328 alone. It does not
add Gemini support and is not a prerequisite for unrelated board progress.

At Torvalds commit `5acbae5f7eb3d5275120abfe698c394b7325dcec`, MT6328's
header names interrupts through 46, and `mt6397-irq.c` handles three banks,
but initialization creates a 32-source domain. MFD-next commit
`b07adc1a304c7ca9ac25a01051561538757363c9` has identical relevant MFD
files and MT6328 header. Its IRQ-domain implementation sets `hwirq_max` to
the requested size and rejects `hwirq >= hwirq_max` before mapping.
Consequently the existing domain cannot map named sources 32–46.
The draft uses 47, covering the named range without assigning an undocumented
source to bit 47. Other chips retain their existing domain size.

The local patch 0010 instead uses bank count times 16 for every chip, thereby
quietly changing MT6328's domain to 48 while adding MT6351. Its successful
application to current source does not establish that the combined change is
the appropriate upstream topic.

## MT6351 dependency split

| Topic | Evidence and next action |
| --- | --- |
| PMIC wrapper | Current upstream already has MT6797 wrapper and MT6351 PMIC entries in `mtk-pmic-wrap.c`; no replacement wrapper is indicated. |
| MFD binding | Parent/core support remains absent in the inspected upstream files. Local 0008 fails application at the changed PMIC-keys schema. Adapt the parent binding separately and check current child schema dependencies. |
| Core and IRQ | Extract MT6351 chip identity, four-bank storage and IRQ handling from local 0010 after separating the existing-chip correction. Preserve mask, suspend and handler behavior for existing chips; review error handling and registration ordering. |
| Regulators | Local regulator support underlies demonstrated storage supplies. A new MFD parent must be paired with the corresponding reviewed regulator driver/binding; the inspected upstream regulator Makefile has no MT6351 entry. |
| RTC and keys | The inspected MFD-next drivers have no MT6351 match. Do not equate creating these child devices with working RTC, keys or wakeup. |
| Audio | The upstream MT6351 codec exists, but its component initialization writes PMIC registers, including protection settings. Keep codec/card enablement out of this topic until analog routes and resource ownership are established. |

The earlier corrected-reset storage evidence establishes bounded VEMC/VIO18
use through the local stack. It does not establish all 64 MT6351 interrupts,
other regulators, RTC, key wakeup or audio. The
[support matrix](../../docs/HARDWARE_SUPPORT.md) retains those runtime limits.

## Validation and submission boundary

The draft applies cleanly to both pinned source snapshots. The pinned MFD-next
`checkpatch.pl --no-tree` reports **one error: missing Signed-off-by**, with
zero warnings; this is deliberately an unsigned draft, not a passing
submission check. No kernel compilation or hardware test was performed.
Before promotion, compile the focused MFD configuration through the documented
Buildbox workflow and review the MT6328 mapping boundary. Binding adaptations
will additionally need focused schema checks.

The archive identity is non-certifying. Historical patch author/sign-off lines
are not evidence of current authorship certification. Resolve actual authorship
and truthful DCO certification before submission. The inspected `MAINTAINERS`
entry identifies Lee Jones, `mfd@lists.linux.dev`, and the
[MFD tree](https://git.kernel.org/pub/scm/linux/kernel/git/lee/mfd.git/).
Re-run maintainer discovery against the final series before contacting anyone;
no mail or issue comment was sent during this review.

To reproduce application checks, retrieve the paths and commits in the receipt
into a disposable source checkout, verify their SHA-256 values, and run
`git apply --check` on the linked draft. Run the recorded checkpatch version
with its adjacent spelling and constant-structure files. Receipt entries refer
to source inspection, not a complete checkout or a kernel build.
