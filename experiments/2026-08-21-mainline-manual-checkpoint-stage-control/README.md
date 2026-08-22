# Manual checkpoint live-stage control

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-21-mainline-manual-checkpoint-stage-control` |
| Status | running; prebuild definition |
| Subsystem | pstore retained writer, live refusal attribution, serviceability |
| Device variant | Gemini PDA x27, named project unit |
| Date(s) | 2026-08-21 |
| Investigator(s) | Julien Etienne, Codex |
| Tracking issue | Gate 7 / CPU8 prerequisite localization |

## Question or hypothesis

Which exact internal boundary makes the first isolated manual checkpoint call
return false on the otherwise serviceable current-tree base: sequence, exact
DT/resource conversion, retained mapping, prefix/header validation, write
precondition, metadata readback, or payload readback?

This is not a repeat of candidate `53e03cb...e5c`. Canonical patch `0328` adds
a durable independent live observation path whose result selects a different
next action. The old boolean marker remains unchanged for comparison.

## Provenance and environment

- Runtime-proven foundation: manual checkpoint candidate
  `53e03cb7100cbb355b7513320428cea8bf39c8c81da9b89a52c91cadd24e8e5c`
- Foundation result: exact serviceability pass with unique
  `first=0 second=0 retained_writes=0`
- Foundation mainline release: `7.1.3-gemini-checkpoint-ctl`
- New profile: `da921x-manual-checkpoint-stage-control`
- Expected release: `7.1.3-gemini-checkpoint-stage`
- Build backend: Buildbox only from an exact clean pushed commit
- Boot path: guarded live-GPT logical boot2 only

Exact build, package, DTB, and candidate identities remain pending Buildbox
validation.

## Safety assessment

Patch `0328` and its profile are default off. The profile inherits the exact
manual checkpoint call count and at-most-two retained writes. It adds no writer,
retry, clear, loop, timer, mapping, device access, or hardware action. It only
records a fixed internal stage string and prints one additional live marker
after the existing call sequence. When the new mode is disabled, its setter is
a compile-time no-op and the historical manual marker remains unchanged.

The clock backend, observer, BigiDVFS, protected transports, DA921x action,
owner registration, and CPU8/CPU9 requests stay absent. There is no protected
read, secure call, new MMIO, I2C transaction, regulator-data write, storage
access, retry, reset, or automatic power action. Any eventual candidate must
use the standing guarded boot2 write/readback/shutdown workflow. The exact live
observer must be armed before the single physical selection.

## Associated code

- `patches/v7.1.3/0328-pstore-report-Gemini-manual-checkpoint-stage.patch`:
  default-off stage capture and one additional live marker
- `configs/gemini-manual-checkpoint-stage-control.fragment`: exact profile
  delta and unique release
- `kernel/manifest.json`: named canonical-series Buildbox profile
- `scripts/validate.py`: exact patch, stage inventory, fragment, profile, and
  safety validator
- `scripts/test-validate.py`: negative source/configuration mutations
- `contract.json`: frozen hypothesis, stage decisions, and safety scope

Build, candidate, deployment, and runtime tooling will be added only after the
exact Buildbox package exists.

## Procedure

1. Validate patch `0328`, every fixed stage, the default-off Kconfig gate, the
   exact parent-profile derivation, canonical series order, and all profiles.
2. Sign and push the clean definition commit to the exact project origin.
3. Build only with
   `KERNEL_PROFILE=da921x-manual-checkpoint-stage-control ./scripts/build-kernel --backend buildbox`.
4. Fetch only the validated package; derive the exact proven serviceability DT
   and independently validate configuration, symbols, Image markers, container,
   and negative mutations before admitting a candidate.
5. Guardedly install to inactive logical boot2, match the full readback, shut
   down, and arm the exact USB observer.
6. Select boot2 once. Require exact identity and serviceability plus one unique
   boolean marker and one unique fixed stage marker. Reboot natively only after
   that bounded capture.

## Observations

The exact parent completed one physical selection with full serviceability.
Its first checkpoint returned false, the short-circuited second call returned
false, and zero retained writes completed. Read-only live diagnostics confirmed
the expected model and five ramoops property values, but the boolean marker
could not distinguish the remaining resource, mapping, prefix, or write/readback
boundaries. Changed-ID recovery was empty and adds no causal precision.

No build or device access has occurred for this new definition.

The prebuild definition passes its exact fragment/profile contract, seven
unified-diff hunk counts, Buildbox prepared-source apply check, canonical-series
audit across 109 profiles, and 14 negative source/configuration mutations.
Strict checkpatch reports no warning and only the intentionally absent
synthetic-author sign-off. See the
[prebuild receipt](results/prebuild-definition-20260821.txt).

## Analysis

The new fixed stage values align exactly with the existing early returns. A
single live marker therefore turns the already proven refusal into a
decision-bearing observation without moving the call site or changing the
retained write protocol. `success` also remains meaningful: it would prove the
unchanged writer locally and admit a live stage oracle for the later enabled-
clock-node population control.

## Conclusion

Pending exact Buildbox and runtime evidence. No stage, checkpoint,
persistence, or hardware-support claim has yet been made.

## Follow-up

Use the one live stage to repair or remove the refusing boundary before clock-
node population. Do not repeat the boolean-only candidate. CPU8 and CPU9 remain
closed.
