# MT6351 PMIC key preparation

Status: incomplete compile-preparation checkpoint, 2026-09-08. This topic
adds chip support and prerequisite error handling. It is not a Gemini boot
candidate, key-event demonstration or approved change to hardware reset policy.

## Scope and source match

The [source receipt](source-inputs.json) pins the inspected files after the
existing twelve-patch [MFD/regulator topic](../2026-09-08-mt6351-mfd-upstream-preparation/README.md),
plus the public Gemian register header. That header confirms:

| Function | Register | Field |
| --- | --- | --- |
| Power/home debounce | TOPSTATUS `0x0220` | Bits 1/2, respectively |
| Power/home interrupt selection | INT_MISC_CON `0x02da` | Bits 2/1, respectively |
| Power/home long-press reset enables | TOP_RST_MISC `0x02b6` | Bits 9/8, respectively |
| Reset timeout selector | TOP_RST_MISC `0x02b6` | Bits 13:12 |

The chip's power/home press and release interrupt IDs are 0/1 and 2/3.
Historical Gemian evidence demonstrates both power-key edges and Linux
`KEY_POWER`; home/reset-key physical wiring remains unproved. See the
[PMIC recovery record](../2026-07-11-mt6351-pmic-recovery/README.md#mt6351-interrupt-and-mfd-model).
The register fields fit the upstream MT6331-style data structure, with MT6351
addresses and separate release IRQs. No RTC reload or counter assumption is
needed for this input topic.

## Five separate changes

The [named series](../../patches/series-mt6351-keys-compile) retains the twelve
MFD/regulator prerequisites unchanged, followed by:

1. [Failed key reads](../../patches/upstream-4d7d9486/keys/0001-Input-mtk-pmic-keys-ignore-failed-state-reads.patch):
   report the transport error and emit no input event from unavailable data.
2. [Reset setup errors](../../patches/upstream-4d7d9486/keys/0002-Input-mtk-pmic-keys-propagate-reset-setup-errors.patch):
   return a failed reset-policy update and stop probe before input registration.
3. [Binding](../../patches/upstream-4d7d9486/keys/0003-dt-bindings-input-mediatek-pmic-keys-add-MT6351.patch):
   add the MT6351 key compatible to the existing schema.
4. [Driver data](../../patches/upstream-4d7d9486/keys/0004-Input-mtk-pmic-keys-add-MT6351-data.patch):
   add the confirmed register fields and separate-release behavior.
5. [MFD resources](../../patches/upstream-4d7d9486/keys/0005-mfd-mt6397-add-MT6351-key-resources.patch):
   supply four named IRQs and the chip-specific key cell.

The first two fixes also affect previously supported chips. They introduce no
retry or new register masks. Reset setup moves before input registration so
that its failure follows managed probe cleanup. This does not roll back prior
hardware writes or prove recovery after a bus fault.

The key cell is named `mt6351-keys`, while the generic platform driver is
named `mtk-pmic-keys`. As with the other chips, a matching enabled OF child is
needed to bind it; an absent child must not trigger a generic name match.
No Gemini key node is added. RTC and audio cells remain absent from this topic.

## Validation

The [focused test](test-key-state.py) compiles the actual MT6351 data and two
driver functions with a small transport/input fixture. Its 42 cases cover
both debounce masks, press/release state, read failures, default and explicit
reset policy, preservation of unrelated reset bits, and update errors.
Restoring the unchanged upstream IRQ handler compiles but fails the no-event
assertion on a bus error. Discarding the reset update error also compiles but
fails the error-propagation assertion. The fixture does not execute a complete
probe, model IRQ timing, or establish either physical key's behavior.

Strict checkpatch passes for all five patches with only `MISSING_SIGN_OFF`
excluded. Buildbox compile and focused schema checks are pending at this
checkpoint. The [schema fixture](joint-example.dts) is an offline parent,
regulator and power-key example, not a board DTS. Existing profiles are
unchanged; the new profile explicitly enables `KEYBOARD_MTK_PMIC`.

```sh
python3 experiments/2026-09-08-mt6351-keys-preparation/test-key-state.py \
  /path/to/prepared/linux/drivers/input/keyboard/mtk-pmic-keys.c
KERNEL_PROFILE=mt6351-keys-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6351-keys-compile ./scripts/buildbox fetch-package
```

## Admission and upstream limits

Probe writes interrupt selection and long-press reset configuration, including
reset fields for both key functions even with only a power-key child. The
default clears hardware long-press reset enables; that must not be described
as preserving the retained recovery behavior. A board node needs a separately
reviewed recovery/reset policy and an attributable physical key session before
device admission. No device access, key press, reset-policy change or boot was
performed here. Suspend/wakeup behavior remains unvalidated.

The key data is adapted from historical local patch 0011; the error fixes and
integration were prepared during this review. Archive identities are synthetic
and non-certifying. A targeted public overlap search found no external MT6351
key topic; repeat maintainer-tree and mailing-list checks before submission.
The Input, DT and MFD maintainers must review their respective changes, with
truthful authorship and DCO certification. No submission or message was sent.
Remove these local changes when equivalent upstream support reaches the
project's selected baseline.
