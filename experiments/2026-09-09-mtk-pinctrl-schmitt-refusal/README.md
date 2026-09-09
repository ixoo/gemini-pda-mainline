# MediaTek Schmitt refusal before direction writes

Status: unsigned implementation checkpoint; focused host regression and strict
checkpatch pass. Buildbox compilation remains pending. No device candidate.

The [microSD API audit](../2026-07-12-mt6797-msdc-recovery/MICROSD_PADS.md#schmitt-api-follow-up)
reproduced a direction write before `-ENOTSUPP` when an SMT field is absent.
This is independent of the unresolved direction policy for supported requests.
The [patch](../../patches/upstream-4d7d9486/pinctrl/0002-pinctrl-mediatek-preflight-Schmitt-field.patch)
exposes the existing field lookup to Paris and checks SMT before changing DIR.
The lookup validates the field, pin range and register base without MMIO.
The successful DIR-then-SMT order and Boolean argument conversion are retained.
No MT6797 field, board state or binding is added; this does not enable microSD.

## Validation

[Source identities](source-inputs.json) pin the three upstream inputs at
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c`. The missing-field branch and lookup
were inspected directly. The lookup uses immutable SoC field data; its result
is not a sampled hardware state. Exporting it avoids an extra register read
or duplication of the range lookup in Paris.

Run the [focused test](test-refusal.py) against the patched prepared source:

```sh
python3 experiments/2026-09-09-mtk-pinctrl-schmitt-refusal/test-refusal.py \
  "$SOURCE/drivers/pinctrl/mediatek/pinctrl-paris.c"
```

It compiles the actual Schmitt switch cases with injected lookup and register
setter results, then executes 72 cases: both parameters, both initial DIR
values, arguments 0/1/2, successful/unsupported/invalid-base lookup results,
and successful/failed DIR operations. Lookup failure must cause zero writes;
DIR failure must prevent SMT writes; success must retain DIR-then-SMT ordering.
The patched cases pass and the original upstream cases fail the regression.
This is control-flow testing, not an electrical or concurrency model. It does
not test the real field lookup; source review covers that unchanged algorithm.

Strict checkpatch passes with only `MISSING_SIGN_OFF` excluded. The isolated
profile selects only this fix and builds MT6797 and the shared pinctrl layers:

```sh
KERNEL_PROFILE=mtk-pinctrl-schmitt-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mtk-pinctrl-schmitt-compile ./scripts/buildbox fetch-package
```

All prior manifest profiles and their series are preserved. Kernel compilation
and symbol-link verification are pending at this checkpoint. No kernel/DT,
device, pin transition or card-enumeration result is claimed yet.

## Upstream boundary

Destination: pinctrl, with MediaTek review. The supported Schmitt direction
policy remains a separate review question; this fix only prevents a rejected
request from changing direction. A bounded public overlap search found no
matching preflight correction, which is not an exhaustive submission search.
Refresh maintainers and target-tree overlap before submission. Actual authorship
and truthful DCO certification remain required; the archive identity does not
certify the patch. No message was sent. Remove the local patch when equivalent
behavior enters the selected upstream baseline.
