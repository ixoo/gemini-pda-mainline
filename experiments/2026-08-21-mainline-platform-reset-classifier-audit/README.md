# Experiment: mainline platform-reset classifier audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-21-mainline-platform-reset-classifier-audit` |
| Status | completed; no positive classifier is transportable to Linux |
| Subsystem | MT6797 TOPRGU, preloader reset classification, retained ram-console, A34 |
| Device variant | Planet Gemini PDA named development unit |
| Date | 2026-08-21 America/New_York |
| Tracking issue | Roadmap Gate 7, production A34 provenance owner |

## Question or hypothesis

Can the already implemented immutable TOPRGU `WDT_STATUS` and current-
preloader ram-console snapshots prove a platform or external reset strong
enough to authorize A34, while rejecting ordinary Linux reboot, unknown bits,
and contradictory observations?

The positive hypothesis requires exact source-backed semantics through the
shipping preloader and LK. It is not enough for two fields to agree if one is
only a projection of the other, and a positive reset class must still be
available after LK hands control to Linux.

## Provenance and environment

- Repository input: signed and pushed commit
  `a313a85b05095dcba811f580d4354f995064637f`.
- Exact retained preloader: SHA-256
  `25319ce877bd17b204fa264645aebf4583ec10ae2f05f6d8a7fff5efe4c06246`.
- Public Planet LK: commit
  `f4988d74bb70a0a15d7f362f412afba7e7fcda46`.
- Public Gemian kernel: commit
  `d388d350cb2dda8f23b99be6fa5db9628896e87f`.
- The retained preloader was inspected read-only in the managed analysis VM.
  No firmware bytes or private paths are committed.
- One bounded read-only Gemian probe tested whether the preloader classifier
  cell remained safely readable. It stalled before returning a value and the
  device became unreachable over SSH. That address and access method are
  rejected and must not be repeated.

Exact sanitized addresses, mappings, and source identities are recorded in
[`results/provenance-20260821.txt`](results/provenance-20260821.txt). The
failed runtime discriminator is recorded separately in
[`results/runtime-probe-20260821.txt`](results/runtime-probe-20260821.txt).

## Safety assessment

The source audit was offline and read-only. The live discriminator issued one
32-bit read through Gemian `/dev/mem`; it performed no write, reset request,
CPU request, partition access, or firmware call. The read did not complete and
the unit did not recover over the bounded SSH observation window. Physical
restart into known-good Gemian is required.

This failure closes the direct preloader-SRAM route. No kernel patch, build,
boot candidate, boot2 write, or further device action is authorized by this
audit.

## Procedure

1. Reconstruct the exact preloader TOPRGU initializer and every branch that
   derives the retained `wdt_status` word.
2. Reconstruct the separate preloader power-off/on classifier from the raw
   status and entry-time `INTERVAL` marker.
3. Trace both values through the retained ram-console writer and LK watchdog
   initialization.
4. Determine whether Linux can recover the positive power-off/on class from
   the two immutable snapshots.
5. Reject unknown, ordinary-reboot, contradictory, and non-transported cases.
6. Test the sole apparent direct transport only with one bounded read, then
   stop permanently on non-completion.

## Observations

The exact preloader function at analysis address `0x21d560` snapshots raw
TOPRGU status from `0x1000700c`. It derives the retained ram-console word as a
lossy semantic projection of that same raw value. The retained writer receives
that projection at `0x213fe0` and stores only that word through the call at
`0x213fe2`. Therefore the current-preloader snapshot is not independent of the
mainline raw TOPRGU snapshot.

The same preloader function does contain a stronger classifier. Before
changing TOPRGU `INTERVAL`, it combines the raw reset status with
`INTERVAL[1:0]`. Raw-zero plus the hardware-default stage marker `3` produces
class `4`, which the exact strings and public LK source identify as power off
and power on reset. Nonzero raw status plus stage `0`, `1`, or `2` produces
preloader-, LK-, or kernel-stage RGU reset classes.

That positive class is not transported. It remains in a preloader-private
cell whose complete static cross-reference set is confined to the classifier.
The ram-console writer receives the separate lossy status word. The preloader
then rewrites `INTERVAL[2:0]`; pinned LK consumes bit 2 into a private Boolean
and unconditionally rewrites those bits to `U_BOOT_MAGIC | IS_POWER_ON_RESET`.
LK exports neither the Boolean nor the original interval value to Linux.

Consequently, exact raw status zero plus exact retained status zero proves
only that none of the represented TOPRGU causes was observed. It does not
recover the discarded entry-time interval marker. Watchdog/reset values prove
a cause but not that every external DA921x, SPM, clock, CCI, DCM, and A72
power-state prefix was restored.

The apparent direct alternative was also rejected empirically. A single
read-only access to the analyzed preloader cell did not return and made the
known-good Gemian SSH endpoint unreachable throughout the bounded follow-up.
No value was obtained, and no second access was attempted.

## Analysis

There is no honest positive row for a classifier whose inputs are only the
implemented immutable raw TOPRGU and current-preloader snapshots. Their
agreement is expected because the latter is derived from the former. The one
source-backed positive power-on class depends on `INTERVAL` state that both
preloader and LK overwrite before Linux.

Implementing a classifier now would therefore add only another permanent
reject gate. Worse, accepting raw-zero/retained-zero would silently replace
the missing interval proof with an assumption. Modifying or replacing LK to
transport the value would cross the separate bootloader-partition boundary and
is not a boot2 kernel step.

The safer next question is state-based rather than cause-based: can existing
owner-safe observers directly prove that every A34 hardware and cross-owner
prefix is in its exact recovered zero/off state after the already proven BL31
primary-entry replay clear? That audit must include the external DA921x Buck B
state, SPM power/reset/isolation state, TOPRGU PWRAP reset, protected clocks,
CCI/DCM, CPU8/CPU9 physical and generic state, and the complete Linux owner
tuple. Any unobservable prefix keeps A34 closed.

## Conclusion

`confirmed`: the exact shipping preloader has a source-backed power-off/on
classifier based on raw TOPRGU status plus entry-time `INTERVAL`.

`confirmed`: the current ram-console status is a lossy projection of raw
TOPRGU status, not independent evidence, and the positive power-on class is
not transported through pinned LK.

`rejected`: every positive platform/external-reset classification using only
the two implemented Linux snapshots; direct access to the preloader-private
cell; and an LK modification as the next boot2 step.

The production A34 owner, classifier implementation, lifecycle publication,
CPU8 request, boot image, and device attempt remain closed.

## Associated records

- [`DESIGN.md`](DESIGN.md) freezes the no-positive decision and next audit boundary.
- [`results/classifier-matrix.tsv`](results/classifier-matrix.tsv) records every admitted and rejected input family.
- [`results/provenance-20260821.txt`](results/provenance-20260821.txt) records exact sanitized source and analysis facts.
- [`results/runtime-probe-20260821.txt`](results/runtime-probe-20260821.txt) records the stopped live discriminator.
- [`scripts/validate.py`](scripts/validate.py) validates the frozen audit.
- [`results/audit-validation-20260821.txt`](results/audit-validation-20260821.txt) is the validation receipt.

Run from the repository root:

```sh
python3 experiments/2026-08-21-mainline-platform-reset-classifier-audit/scripts/validate.py
```

## Follow-up

Audit a direct, immutable A34 recovery-state attestation against the canonical
tree and existing owner-safe observers. Do not implement a reset-cause
classifier, touch LK, repeat the SRAM access, build a boot candidate, or issue
a CPU8 request from this result.
