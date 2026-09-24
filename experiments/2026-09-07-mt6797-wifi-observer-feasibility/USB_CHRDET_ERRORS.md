# Distinguish charger detection from discarded errors

The [physical diagnostic](USB_CHRDET_DIAGNOSTICS.md#retained-physical-result)
recorded `chrdet=39`: the battery helper observed zero after its callback.
The [provider trace](USB_CHRDET_DIAGNOSTICS.md#detection-result-and-error-contract)
shows that both callback and PMIC read errors can leave outputs unwritten,
and the original callers discard those errors. A zero result alone cannot
justify changing cable detection or charger policy.

The [patch](patches/usb-chrdet-errors/0001-usb-retain-charger-dispatch-and-PMIC-read-outcomes.patch)
retains the existing command-12 callback status and the CHRDET getter's existing
read outcome. It is an assistant-generated, non-certifying native experiment;
the four source files retain their GPL version 2 headers. It is not an upstream
submission or a production error-handling repair. The [source receipt](results/usb-chrdet-errors.json)
pins four parent files, exact reversal and replay, and strict Checkpatch. The
first fifty patches, configuration and canonical upstream series are unchanged.
Compilation and linked inspection remain pending; no candidate is selected.

## Observations and bounds

The existing one-shot shutdown report becomes:

```text
wifi-usb-v3 paths=hhhh cable=hhhhhhhh chrdet=hhhh pmic=hh
```

`paths` and `cable` preserve the parent meanings. The low eight `chrdet` bits
also retain their meaning; bit 8 records an existing command-12 callback
returning zero status, and bit 9 records nonzero status. The helper definition
moves before that caller so the existing atomic marker can be reused. All
original call arguments, output and return behavior remain, including the
unwritten-output limitation; the diagnostic does not initialize or replace an
original output.

The new PMIC mask has five cumulative bits:

| Bit | Observation after the existing CHRDET getter's accessor returns |
| --- | --- |
| 0 | Normal getter completed its accessor |
| 1 | Nolock getter completed its accessor |
| 2 | Accessor returned nonzero status |
| 3 | Accessor succeeded with zero output |
| 4 | Accessor succeeded with nonzero output |

Only flag `MT6351_PMIC_RGS_CHRDET` contributes. The helper checks status before
reading the existing output through its pointer; an error path never examines
that potentially uninitialized value for instrumentation. A new ordinary getter
reads the software mask. Markers use the same diagnostic plus Ethernet and
without-Android gate as the parent. The PMIC declaration has a zero fallback
outside MT6797 with the selected legacy PMIC driver; that fallback is not evidence.
The selected configuration must compile the actual helper and unchanged hardware
accessors.

No new PMIC read, write, role operation, charger setting, work item, retry,
userspace interface or direct retained-slot writer is introduced. The existing
USB report-consumed bit remains set before either ordinary getter or printk,
allowing at most one summary from the first shutdown entry. An earlier shutdown
path can consume it, so missing output remains inconclusive.

Masks cover all callers, not only USB, and record neither count nor order. The
normal/nolock and outcome bits are set separately; a report can see a helper
in flight. Masks and the latest cable sample are independent. Callback success
does not imply PMIC read success because the concrete handlers still discard
read errors. Mixed zero/nonzero/error outcomes must retain that ambiguity.

## Validation and next physical question

Before candidate admission, verify the full Buildbox package, unchanged config
and DT, emitted status branches, no diagnostic load of the PMIC output on error,
unchanged original hardware calls, and the existing one-shot report guard.
Validate exact v3 parsing and reject invalid/reserved bits, malformed or duplicate
summaries, and summaries outside the attributed return-to-restart window.

Hypothesis: the observed zero comes from either a successful existing CHRDET
read or a discarded callback/accessor error. The unique measurement is the
existing status and successful-output classification. Preserve the parent's
CPU0–7 preflight, snapshot, bounded transport and normal return path.

- Successful zero without errors: investigate the native detection-bit path.
- Accessor error: investigate its existing transport/access error contract.
- Callback failure: investigate charger registration and control dispatch.
- Mixed outcomes or incomplete observation: preserve the ambiguity and choose
  a further discriminator; do not infer a per-call association.
- Controller start or export: apply the parent attribution and snapshot/ack
  validation before claiming transport success.

Any physical session still needs an exact validated container and session,
guarded boot2 installation/readback, clean shutdown, collectors armed and one
owner physical selection. No capture clear, radio action, forced VBUS value or
role override is admitted by this source record.
