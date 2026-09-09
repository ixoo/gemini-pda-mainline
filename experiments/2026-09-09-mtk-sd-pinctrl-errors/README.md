# MediaTek MMC voltage-switch pinctrl errors

Status: source and injected regression checks passed; Buildbox compilation
pending. Unsigned upstream-preparation checkpoint, not a boot candidate.

## Problem and change

The shared `mtk-sd` driver's `msdc_ops_switch_volt()` changes VQMMC, selects
the corresponding pin state, then returns success even if pin selection
failed. For example, a successful regulator request followed by pinctrl
`-EINVAL` returns zero. The MMC core consequently retains the requested
signaling voltage as though the full transition succeeded.

The [single patch](../../patches/upstream-4d7d9486/mmc/0001-mmc-mtk-sd-propagate-pinctrl-errors-during-voltage.patch)
returns the pinctrl result for both the 1.8 V and 3.3 V paths. It preserves
operation order, unsupported-voltage rejection, regulator errors and the
existing missing-supply behavior. It introduces no retry or driver-local
voltage rollback. A failed pin operation may follow a successful regulator
change; returning an error does not prove electrical restoration.

The inspected core `mmc_set_signal_voltage()` restores its previous software
voltage on error. Its SD UHS sequence treats this failure as a failed switch
and takes the existing power-cycle branch. Other callers have their own
recovery behavior; this fix makes no blanket rollback guarantee.

This is a generic prerequisite for later voltage-switch testing, independent
of MT6797 compatibility data and Gemini pinctrl/regulator wiring. It does not
enable microSD, UHS modes or a Gemini board node. Existing storage candidates
and their finite observation budgets remain unchanged.

## Source and overlap

[Source inputs](source-inputs.json) pin the exact upstream files and inspected
refs. The complete host driver is byte-identical at the manifest-selected
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c`, mainline HEAD observed on
2026-09-09, and the observed MMC `next` and `fixes` heads. All retain the
ignored return values. A bounded public search found an earlier
[AN7581 proposal](https://lists.infradead.org/pipermail/linux-mediatek/2025-January/088665.html)
moving pin selection, but that proposal also discards its result. This is not
an exhaustive public-review search; recheck the final submission base.

The inspected mainline driver and binding still lack `mediatek,mt6797-mmc`.
The historical local MT6797 descriptor differs from `mt2701_compat` in
`recheck_sdio_irq`. This audit does not replace that descriptor with an alias
or infer SDIO behavior from eMMC results. The
[original controller contract](../2026-07-12-mt6797-msdc-recovery/results/mt6797-msdc-mainline-design.md)
remains the separate source/evidence foundation.

## Validation

The [focused regression](test-voltage-switch.py) compiles the actual driver
callback together with the actual MMC core caller. It injects missing/present
supply, three voltage choices, negative/zero/positive regulator returns and
successful/two failing pinctrl returns. All 54 cases pass with the patch.
The unmodified upstream callback fails because a pinctrl `-EINVAL` becomes
zero. Checks also cover state selection, call order/count, core software
voltage restoration and the absence of a new regulator rollback. This is a
host fixture, not a hardware voltage or pinctrl-core recovery test.

```sh
python3 experiments/2026-09-09-mtk-sd-pinctrl-errors/test-voltage-switch.py \
  /path/to/prepared/linux/drivers/mmc/host/mtk-sd.c \
  /path/to/prepared/linux/drivers/mmc/core/core.c
KERNEL_PROFILE=mtk-sd-pinctrl-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mtk-sd-pinctrl-compile ./scripts/buildbox fetch-package
```

The isolated profile selects only this fix against the pinned upstream source
and enables the MMC host driver and pinctrl. All 200 previously defined
profiles, their effective series and fragment bytes are unchanged.
Strict checkpatch passes with only `MISSING_SIGN_OFF` excluded. No bindings or
DT changed, so there is no new schema or DT validation claim. Kernel
compilation and package validation remain pending at this checkpoint.
No device access, voltage switching, pin configuration or boot test occurred.

## Upstream boundary

The pinned maintainer file assigns `mtk-sd.c` to Chaotian Jing and the MMC
subsystem to Ulf Hansson / `linux-mmc`, with the MMC tree as the target.
Run maintainer discovery and refresh overlap against the final outgoing
revision before submission. The synthetic archive author supplies no DCO
certification; actual authorship and truthful certification remain required.
No message was sent. Remove the local patch after an equivalent upstream
fix enters the selected project baseline and its regression is validated.
