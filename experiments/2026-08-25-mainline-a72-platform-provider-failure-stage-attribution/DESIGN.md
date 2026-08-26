# Failure-stage design

The failure stage is an internal output separate from the composed snapshot.
This preserves the proven all-zero snapshot invariant on every return before
the protected-clock call.

| Return boundary | Stage | Later effects |
| --- | --- | --- |
| missing supplier | `dependency` | none |
| platform error or invalid sample | `platform` | no provider/checkpoint/clock |
| provider error or invalid sample | `provider` | no checkpoint/clock |
| first checkpoint refusal | `before-clock` | no clock |
| protected-clock call returns | `none` | terminal result; no retry |

The probe logs `stage=<name> ret=<errno>` only when capture returns an error.
The successful four-record receipt is unchanged. All hardware-free failure
tests assert both the stage and the old zero-output/call-count invariants.

No new loop, delay, MMIO, I2C, retained-memory, secure, BigiDVFS, provider,
owner, publication, CPU, reboot, or power operation is introduced.
