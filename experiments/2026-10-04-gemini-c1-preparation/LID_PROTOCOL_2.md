# C1-4 lid test protocol: Schmitt trigger on GPIO66

Status: draft for coordinator review, 2026-10-07. Package pending; no
candidate composed and no device action taken under this protocol.

C1-3 under [LID_PROTOCOL.md](LID_PROTOCOL.md) is consumed. It showed GPIO66
following the lid with EINT5 silent, with and without debounce; see the
[EINT5 analysis](README.md#eint5-analysis-offline-2026-10-06).

## Hypothesis and unique observation

When GPIO66 becomes an EINT, the common code tries to enable its Schmitt
trigger and silently skips it because MT6797 maps no SMT field. Patch c1/0011
maps GPIO66's SMT bit, so the same claim now enables it. The unique
observation is whether EINT5 fires once the pad has Schmitt conditioning.

## Artifact changes from C1-3

Only patch c1/0011, which maps IOCFG_R `0x30` bit 27 as GPIO66's SMT field.
That bit also serves GPIO67, the microSD card-detect input, which has no
driver in this profile. Debounce stays 0 and debugfs stays on, so the C1-3
observations repeat unchanged.

## Sequence

As [LID_PROTOCOL.md](LID_PROTOCOL.md): read the GPIO66 level and the Hall
EINT5 count with the lid open, closed, then open, with one background event
capture. One close/open, read-only reads, no register writes beyond driver
probe, no retry.

## Decision branches

- **EINT5 fires and events appear.** Missing SMT was the cause. Map the SMT
  fields for other EINT pads before relying on them, and restore a software
  debounce for the lid.
- **Level changes, EINT5 still silent.** SMT is not sufficient. Next: a
  reviewed software-triggered EINT5 (controller `soft_set`) to separate
  routing from pad detection.
- **Level stops changing.** The SMT bit has an unexpected effect; revert it
  and inspect the shared GPIO67 bit.
