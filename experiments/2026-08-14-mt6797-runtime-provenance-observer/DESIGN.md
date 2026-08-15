# Runtime provenance observer design

## Observation contract

The observer is compiled only when
`CONFIG_GEMINI_MT6797_DVFSP_PROVENANCE_OBSERVER=y`. It attaches to three
existing vendor lifecycle points:

1. EEM publishes each completed non-SOC INIT02 bank from the existing ISR; a
   calibration handle appears only when the exact required mask `0x3b` is
   complete.
2. EEM invalidates the calibration before resume recalibration and exit.
3. PPM records each cluster after committing its DVFS table and advances the
   epoch only when every cluster bit in the reported cluster count is present.

The debugfs snapshot is bounded, read-only, and spinlock-consistent. The
IRQ-safe lock is required because INIT02 completion is observed in interrupt
context. The snapshot reports a variant derived through the existing
device-info accessor, observer generation, completed PPM cluster mask, EEM bank
mask, table epoch, current calibration handle, and event counts. Epoch and
handle start at zero, so an absent hook cannot create a successful observation.

## Explicit nonclaims

The observer is not a transition owner. It therefore reports
`owner_handle=0`, `transition_handle=0`, and
`coherent_transition_owner=0`. It registers no provider, performs no hardware
write, and does not alter CPU policy. CPU8/CPU9 admission remains closed.

These fields are part of the evidence contract rather than placeholders: any
future candidate that claims ownership must be a separately reviewed design,
not a silent reinterpretation of this observer.

## Build decision table

| Result | Decision |
| --- | --- |
| Patch does not apply normally to the pinned parent | Reject the source candidate |
| Any changed path or configuration delta exceeds the pinned set | Reject the source candidate |
| Complete kernel link fails or leaves an unresolved symbol | Repair or reject; do not package |
| Complete link passes but package nonclaims are absent | Reject the package |
| Validated package passes | Advance to separate container review only |

## Possible runtime decision table

| Runtime observation | Decision |
| --- | --- |
| Kernel identity or debugfs ABI differs | Reject attribution |
| `observation_complete` is zero, a mask is incomplete, or variant/epoch/handle is zero | Observation path is insufficient; do not repeat unchanged image |
| Two reads are stable, masks are complete, and lifecycle counts are plausible | Confirm vendor table/calibration publication only, not setter completion |
| Any serviceability regression or unexpected write/owner claim | Reject candidate and recover Gemian |

No outcome from this experiment alone opens the CPU8/CPU9 production gate.
