# MT6797 MSDC1 input-enable fields

Status: source review and strict checkpatch passed; Buildbox compilation pending.
Unsigned upstream-preparation checkpoint, not a device candidate.

## Change and scope

An `input-enable` request for GPIO129–134 currently fails because the upstream
MT6797 pin controller has no IES register calculation. The
[single patch](../../patches/upstream-4d7d9486/pinctrl/0001-pinctrl-mediatek-add-MT6797-MSDC1-input-enable-fields.patch)
maps their six independent input-buffer enables to IOCFG_B offset `0x020`,
bits 25–30. The existing Paris operations perform the read and masked update;
no new callback or register resource is introduced. Other pins retain their
unsupported input-enable behavior.

The [pad investigation](../2026-07-12-mt6797-msdc-recovery/MICROSD_PADS.md)
joins two vendor source maps, retained DT resources and the compiled MMC
helper's combined mask. It also explains why Schmitt, pull, delay, drive and
bias-tuning operations are separate work. This patch selects no board state,
changes no GPIO direction, and leaves the existing eMMC/microSD candidates
and power policies unchanged. A provider field map is not proof that a card
can enumerate or that a complete pin/power transition is safe.

## Validation

[Source inputs](source-inputs.json) pin the public files and observed refs.
The complete upstream MT6797 pinctrl driver is identical at the selected
baseline, observed mainline HEAD, and pinctrl `for-next`/`devel` heads.
A bounded public search found no matching IES field addition; this is not
an exhaustive review search. Recheck the final submission base.

Strict checkpatch passes with only `MISSING_SIGN_OFF` excluded. The field
range resolves pins 129–134 to base index 2, offset `0x020`, individual bits
25–30 with no register crossing. Adjacent pins remain outside the range.
There are no binding or DT edits and no new schema-validation claim.

The isolated compile profile selects only this patch against pinned upstream
and explicitly enables `CONFIG_PINCTRL_MT6797`. All 201 existing profile
definitions, selected series and configuration fragments are preserved.

```sh
KERNEL_PROFILE=mt6797-msdc1-ies-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-msdc1-ies-compile ./scripts/buildbox fetch-package
```

## Upstream boundary

The destination is the pinctrl subsystem, with MediaTek review. The pinned
maintainer file names Linus Walleij and the linux-gpio list for pinctrl.
Refresh full maintainer discovery and overlap before any submission. The
synthetic archive identity supplies no DCO certification; actual authorship
and truthful certification remain required. No message was sent.
Remove this local patch after equivalent support enters the selected upstream
baseline and its input-buffer behavior is validated on hardware.
