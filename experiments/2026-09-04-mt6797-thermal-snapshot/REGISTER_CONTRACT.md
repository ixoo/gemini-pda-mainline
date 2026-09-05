# Freshness register contract: evidence and decision

This is a source-only follow-up to the [sensor audit](SENSOR_FRESHNESS_AUDIT.md).
No device register was read, no diagnostic budget consumed, and no source tree
or kernel was built or copied. The archived vendor Git object was inspected
in place on Buildbox. Historical VM reference paths were absent; the retained
bare repository supplied the pinned object. Its current HEAD differs from the
pin and was not used. Exact file hashes are in the
[source receipt](results/freshness-register-audit.txt).

## Reviewed contract

Source pin: `c5b0be85017ad0c599725e8273842efdbecdd88a`. Paths below are relative
to that archive. It is implementation evidence, not a hardware specification
or permission to copy vendor code. Conclusions are limited to the reviewed
MT6797 paths; absence here does not prove silicon has no freshness mechanism.

| Candidate signal | Evidence | Admission decision |
| --- | --- | --- |
| Thermal `TEMPMSR0/1` low 12 bits | `thermal/mt6797/src/mtk_tc.c:929` reads and masks stored measurement data; mainline's matching scan converts the same field. | Existing locked read path only. A changed value is evidence of a changed reported result, not a timestamped physical conversion. |
| Bit 12 and `TEMPADCVALIDMASK=0x2c` | `mtk_tc.c:880` points validity and voltage addresses at AUXADC channel 11; lines 886--888 describe its input-valid bit. | This concerns AUXADC data consumed by the thermal engine. It does not establish bit 12 of `TEMPMSR` as a freshness flag. Reject that interpretation. |
| Standalone AUXADC ready transition | `auxadc/mt_auxadc.c:341` waits for old ready clear, triggers a conversion, then waits for ready set before reading. | A passive ready=1 read does not reproduce that transaction. Do not trigger or clear channel 11 beside the thermal owner. Standalone IIO remains disabled. |
| Filter/immediate interrupt status | `thermal/mt6797/inc/tscpu_settings.h:639` names immediate/filter status bits. The bank handler reads status at `mtk_tc.c:725`. | Names and an interrupt-handler read do not establish a non-destructive, per-sample generation protocol. Acknowledgement/read-clear semantics and IRQ ownership remain unresolved. No polling or IRQ probe admitted. |
| Filter setting `0x492` | `mtk_tc.c:830` and :850 describe two out of four samples; the deployed mainline config uses this value. | Configuration evidence for filtering, not proof of live filter timing, sample ages or why this run rose. Do not disable filtering as an observational shortcut. |
| Software scan timestamps | Existing snapshot owner brackets its normal bank scan. | Useful for request timing only. They do not acquire conversion timestamps. |

All paths in the table are abbreviated relative to `drivers/misc/mediatek/`;
subsequent `mtk_tc.c` references mean `thermal/mt6797/src/mtk_tc.c`.
No raw ADC or calibration data is published. A source comment about a clock
period or sample count is not a measured bound on hardware conversion age.

## Consequence for the next experiment

No freshness-only source change or boot is justified by this audit. Preserve
unknown conversion age. The earlier thermal rise/spread comparison remains
rejected, and this consumed session cannot be reused for more snapshots.

A prospective alternative is a **reported-temperature recovery** observation,
using the existing three-read snapshot interface on a fresh boot. Its unique
question is whether the slot-local rise remains after the finite owned workers
have finished, or decreases during a declared bounded interval with no new
owned workload. Either outcome adds a time point absent from the rejected
capture. A decrease would establish a transient in the reported value; it
would not distinguish physical cooling from filter/history effects. Persistence
would leave both heating and sampling explanations open and would not itself
prove a stuck sensor.

This is a design direction, not an executable or admitted protocol. Before
selection, freeze three stage boundaries (pre-workload, workers-complete,
post-completion observation), the delay and host/device time bounds, worker
quiescence, initial-state checks, unchanged finite CPU/lifecycle/frequency
ceilings, and complete per-slot/accounting/cleanup evidence. Test early/late
samples, new worker activity, reused boot IDs, missing fields, exceeded budgets,
and incorrect result promotion. Keep the old thermal refusal limits and do not
label a recovery response as integrated thermal repeatability or hardware
protection. A temperature refusal must stop the protocol according to its
published rules; do not add a recovery load or threshold relaxation.

Any recovery observation must avoid a kernel idle-state experiment, clock/OPP
changes, forced conversion, filter changes, interrupt reads and additional CPU
hotplug. Existing background activity means a no-owned-worker interval is not
an assertion that the whole system is idle. Reuse the exact deployed image only
if the complete host protocol can satisfy these requirements; no rebuild is
selected. Implementation order and admission belong to the [roadmap](../../docs/ROADMAP.md).
