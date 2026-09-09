# MT6797 MSDC1 drive-strength fields

Status: unsigned implementation checkpoint. Strict checkpatch passes;
Buildbox compilation and focused schema validation are pending. No candidate.

## Change and evidence

The [pad map](../2026-07-12-mt6797-msdc-recovery/MICROSD_PADS.md) identifies
three drive-selector fields for GPIO129–134 at IOCFG_B offset `0x1b0`:
CMD bits 23:21, DAT0–3 shared bits 26:24, and CLK bits 29:27. The
[driver patch](../../patches/upstream-4d7d9486/pinctrl/0004-pinctrl-mediatek-MT6797-MSDC1-drive-fields.patch)
adds those fields, selects `DRV_GRP4` for these six pins, and uses the existing
rev1 drive callbacks. Requests on other pins remain unsupported. The data pins
share one physical field; conflicting per-pin requests cannot be independent.

The pinned vendor GPIO setter independently clears and sets only each pin's
DRV field. Its ordinary branch uses the clear/set aliases; its bring-up branch
uses masked reads/writes. Neither branch adds the MMC helper's bias-tuning
operation. The GPIO field table agrees with the MMC map and assigns each of
these six pins a three-bit field. The MMC source documents selectors 0–7 as
2–16 mA in 2 mA steps, which matches `DRV_GRP4`, not the current `DRV_GRP3`.
These current labels are source evidence, not measured pad currents.

The [binding patch](../../patches/upstream-4d7d9486/pinctrl/0003-dt-bindings-pinctrl-mediatek-MT6797-drive-strengths.patch)
allows the missing 6, 10 and 14 mA settings for MT6797. Its shared schema keeps
MT6779's original allowed values through the existing compatible conditional.
No new binding property or pinctrl callback is introduced.

The drive mask excludes the five-bit bias-tuning field at bits 20:16. This
provider topic preserves that field; it does not implement the complete MMC
pad/power sequence. No board state is selected, and none of this resolves the
bias tune, PMIC trim, Schmitt direction or actual card-test prerequisites.

## Validation and reproduction

[Source inputs](source-inputs.json) pin the upstream and public vendor files.
Only independently described facts are used from the vendor source. Upstream
review files retain their existing authorship and license notices. Strict
checkpatch passes with only `MISSING_SIGN_OFF` excluded. A bounded public
search found no matching six-pin drive-field topic; refresh target-tree overlap
and maintainer discovery before submission.

The isolated profile selects the binding and driver patches in canonical order,
without the separate IES or Schmitt-refusal topics. All 203 existing profiles
and their series remain unchanged.

```sh
KERNEL_PROFILE=mt6797-msdc1-drive-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-msdc1-drive-compile ./scripts/buildbox fetch-package
```

Compilation, descriptor/encoding checks and positive/negative binding checks
remain pending at this checkpoint. No hardware behavior is claimed.

## Upstream boundary

Destination: pinctrl and Device Tree, with MediaTek review. Actual authorship
and truthful DCO certification remain required; the synthetic archive identity
does not certify these patches. No submission was sent. Remove the local topic
when equivalent support enters the selected upstream baseline; card and pad
transition validation remain required before board enablement.
