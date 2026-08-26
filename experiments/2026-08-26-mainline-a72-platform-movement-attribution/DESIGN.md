# Platform movement failure-detail design

## Proven input

Runtime attempt 1 of the failure-stage predecessor produced exactly one
`stage=platform ret=-11` result after all serviceability suppliers bound. In
the canonical platform source, CCI change-pending returns `-EBUSY`; only a
nonzero comparison between two completed samples returns `-EAGAIN`.

## API shape

Preserve `mt6797_a72_platform_state_snapshot()` for every existing caller. Add
`mt6797_a72_platform_state_snapshot_detailed()` for the one composed observer.
Its separate failure-detail object contains:

- the first completed sample;
- the second completed sample;
- a nine-bit movement mask; and
- `samples_valid`, set only after both reads complete and the transaction
  refuses for CCI busy or movement.

An internal injected `capture()` helper owns the exact two-read transaction.
The production wrapper holds the existing source mutex and supplies the same
read-once function. KUnit supplies an in-memory reader to test call count,
errors, CCI precedence, masks, and output clearing without physical access.

## Output invariants

- Null or malformed arguments return `-EINVAL`.
- A first-read failure performs one read and returns the original errno with an
  all-zero stable snapshot and all-zero detail.
- A second-read failure performs exactly two reads and returns the original
  errno with both outputs zero.
- CCI change-pending in either completed sample returns `-EBUSY`, preserves the
  completed pair in the detail, and takes precedence over movement.
- A nonzero nine-bit comparison returns `-EAGAIN`, preserves the pair and exact
  mask in the detail, and leaves the stable snapshot zero.
- A stable pair returns zero, publishes the second sample with `valid=true`,
  and leaves the failure detail zero.

The mask compares the same fields and masks as the predecessor. General SPM
power-status words, CCI status words, and unmasked MP2 DCM/CCI-port bits remain
observations but are not promoted into movement.

## Composed observer

The platform callback receives the out-of-band detail. Capture continues to
zero its public composite snapshot on every pre-clock failure. On exact
platform `-EAGAIN` with `samples_valid=true`, the probe emits one bounded line
containing the movement mask and first/second values for all nine comparisons.
Every other failure retains the predecessor's stage-and-errno line.

## Non-goals

This experiment does not stabilize the sample, retry, reinterpret a moving
pair as valid, call the provider or clock after failure, touch retained RAM,
request CPU8/CPU9, change the DT, or authorize a transition. Its only live
claim is attribution of the already observed platform movement.
