# MT6797 MSDC1 pull-field preparation

Status: unsigned implementation checkpoint. Strict checkpatch and focused host
checks pass; Buildbox compilation is pending. No device candidate.

## Changes

The [generic correction](../../patches/upstream-4d7d9486/pinctrl/0005-pinctrl-mediatek-propagate-advanced-pull-errors.patch)
propagates R0/R1 field errors from `mtk_pinconf_adv_pull_set()` instead of
reporting success. It preserves successful writes and the existing PUPD
fallback. An R1 failure can leave the preceding R0 write in place; no rollback
or atomicity is claimed. Existing consumers relying on silently ignored
unsupported advanced-pull requests will now receive an error and need review
before upstream promotion.

The [data patch](../../patches/upstream-4d7d9486/pinctrl/0006-pinctrl-mediatek-MT6797-MSDC1-pull-fields.patch)
adds the independent GPIO129–134 PUPD, R0 and R1 fields at IOCFG_B offsets
`0x100`, `0x110` and `0x120`, bits 18–23 respectively. The pull-type table
selects PUPD/R0/R1 only for these six pins. Existing combo and advanced-pull
callbacks implement the operations; other pins remain unsupported.
No new callback, binding property, board state or rail operation is introduced.

The [pad evidence](../2026-07-12-mt6797-msdc-recovery/MICROSD_PADS.md)
joins the vendor GPIO tables and MMC definitions. The GPIO disable path clears
R0/R1 without requiring a PUPD value. Its ordinary direction-selection path
changes PUPD only; the MMC helper explicitly sets all three fields. These are
source contracts, not proof of a current device state or safe transition.

## Consumer semantics

The existing binding's `mediatek,pull-up-adv = <1>` expresses the retained
CMD/DAT tuple PUPD/R0/R1 = 0/1/0. `mediatek,pull-down-adv = <2>` expresses
the retained CLK tuple 1/0/1. The raw advanced selector is 0–3 as already
documented by the binding; it is not an ohmic resistance value.

The combo API accepts `MTK_PUPD_SET_R1R0_00` through `_11` (100–103), plus
zero for disable. Thus explicit `bias-pull-up = <MTK_PUPD_SET_R1R0_01>` and
`bias-pull-down = <MTK_PUPD_SET_R1R0_10>` reach the same enabled tuples.
A bare `bias-pull-up`/`bias-pull-down` supplies argument 1 and is rejected;
no default resistor selection is invented.

Combo disable clears both resistor enables but sets PUPD to 1. The retained
MMC disable helper writes PUPD to 0 as well as clearing R0/R1. Therefore these
are not byte-identical disable operations. The vendor GPIO path's disable
contract supports treating both resistor bits as the disable control, but a
future board observation must not demand the MMC helper's full-register image
from combo disable.

Advanced writes use R0, R1, then PUPD; combo writes use PUPD, R0, then R1.
Neither promises a glitch-free transition. Resolve the complete pin/power
sequence, separate bias tune and PMIC trim before enabling a board state. The
vendor's two resistor comments do not establish a complete ohmic table.

## Validation and reproduction

[Source inputs](source-inputs.json) pin the upstream and public vendor files.
Strict checkpatch passes with only `MISSING_SIGN_OFF` excluded. The
[error regression](test-advanced-pull.py) executes the actual helper with
injected field results:

```sh
python3 experiments/2026-09-09-mt6797-msdc1-pull/test-advanced-pull.py \
  "$SOURCE/drivers/pinctrl/mediatek/pinctrl-mtk-common-v2.c"
```

All 64 cases pass: both directions, four selectors, each write ordinal or no
failure, and `-EINVAL`/`-ENOTSUPP`. The existing PUPD-to-rev1 fallback succeeds
when injected. The original helper fails the regression. A separate 12-case
host execution of the unchanged combo helper checks arguments 0, 100–103 and
1 for both directions, including the disabled PUPD value and rejection before
writes. These tests model control flow and register values, not physical MMIO,
current, concurrency or electrical safety.

The isolated profile selects only these two patches, preserving all 204
existing profiles and their selected series:

```sh
KERNEL_PROFILE=mt6797-msdc1-pull-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-msdc1-pull-compile ./scripts/buildbox fetch-package
```

Compilation and compiled field/type-table checks remain pending. No binding
was changed and no schema or runtime result is claimed at this checkpoint.

## Upstream boundary

Destination: pinctrl, with MediaTek review. A bounded public search found the
older PUPD fallback revisions but no matching R0/R1 error-propagation fix or
six-pin MT6797 pull topic. Refresh overlap and maintainers before submission.
Actual authorship and truthful DCO certification remain required; the synthetic
archive identity does not certify these patches. No message was sent. Remove
the local topic after equivalent support enters the selected upstream baseline;
board enablement still needs an admitted hardware result.
