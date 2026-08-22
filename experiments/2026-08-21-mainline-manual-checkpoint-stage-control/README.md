# Manual checkpoint live-stage control

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-21-mainline-manual-checkpoint-stage-control` |
| Status | complete; exact live stage localized to prefix validation |
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

The exact Buildbox package is
`linux-7.1.3-gemini-da921x-manual-checkpoint-stage-control-f7245421-75cbd9fd`.
Its raw Android-v0 candidate is `07d2f185...386d0`; the exact 16 MiB boot2
image is `43e7f44e...eac3`.

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
- `scripts/build-candidate.sh` and `scripts/test-candidate.sh`: two-way exact
  container construction and independent admission
- `scripts/install-boot2.sh`: source-pinned live-GPT write/readback/shutdown
- `scripts/collect-runtime.sh`, `scripts/remote-runtime-probe.sh`,
  `scripts/validate-runtime.py`, and `scripts/validate-retained.py`: pre-armed
  fixed-stage capture, native Gemian return, and bounded recovery

The exact runtime and changed-ID recovery evidence is recorded in the
[runtime receipt](results/runtime-attempt-1-prefix-refused-20260821.txt).

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

Buildbox fetched exact clean commit `f4b4819`, applied the canonical series,
compiled release `7.1.3-gemini-checkpoint-stage`, and validated the complete
package inventory. No native VM build occurred.

The prebuild definition passes its exact fragment/profile contract, seven
unified-diff hunk counts, Buildbox prepared-source apply check, canonical-series
audit across 109 profiles, and 14 negative source/configuration mutations.
Strict checkpatch reports no warning and only the intentionally absent
synthetic-author sign-off. See the
[prebuild receipt](results/prebuild-definition-20260821.txt).

The exact package and candidate pass two independent raw assemblies, two
independent padding constructions, all 32 LK Android-v0 gates, exact Image,
configuration, symbol, and provenance checks, and 15 independent DT
mutations. The runtime tools accept all eight fixed outcomes while rejecting
24 unsafe live mutations and eight retained-recovery mutations. No device
access occurred during build or admission. See the [build receipt](results/build-f4b4819.txt)
and [candidate receipt](results/candidate-07d2f185.txt).

From exact Gemian boot ID `dc1a8916...5f6c`, the guarded live-GPT workflow
resolved inactive logical boot2 as p30 while root remained p29. Power was
external, full, and good; slots 171--174 were exact-empty. The predecessor was
the previous manual control, and the write, sync, flush, and full-partition
readback matched `43e7f44e...eac3`. No fresh backup was made under the standing
project policy. The device was shut down cleanly and confirmed unreachable;
it was not rebooted. See the [deployment receipt](results/deployment-20260821.txt).

The observer was armed before the one physical selection. Mainline boot ID
`461d67ea-04ef-4347-a2d1-a46ada9f1112` reached the exact USB/netcat oracle on
release `7.1.3-gemini-checkpoint-stage`. CPU0--7, keyboard, and the read-only
DA921x client were healthy; CPU8--9 remained offline, and the clock, BigiDVFS,
protected-readback, same-value-action, storage, and CPU-action paths remained
absent. The historical and new markers each appeared exactly once:

`GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1 first=0 second=0 retained_writes=0 protected_calls=0 cpu_requests=0`

`GEMINI_MANUAL_CHECKPOINT_STAGE_V1 first=0 second=0 stage=prefix-refused writes=0 protected=0 cpu=0`

The exact classifier accepted `decision-stage-prefix-refused` and only then
sent one native reboot. Changed-ID Gemian returned, boot2 still matched
`43e7f44e...eac3`, owned slots 173 and 174 were exact-empty, and pstore had
zero files. Returned empty RAM is only a cross-version recovery observation;
it does not override the live stage. See the
[runtime receipt](results/runtime-attempt-1-prefix-refused-20260821.txt).

## Analysis

The new fixed stage values align exactly with the existing early returns. The
accepted live marker proves that exact DT validation and `ioremap_wc()` both
completed, then the first call rejected the four-slot live prefix before
selecting or writing owned slot 173. No write precondition, metadata readback,
payload readback, protected transport, or CPU path was reached.

The earlier Gemian preflight proved the same physical slots empty before
deployment, while changed-ID Gemian recovered them empty afterward. Those
observations do not reveal which header bytes the mainline mapping saw during
the late initcall. The next discriminator must therefore capture the first
failing live slot and its bounded signature/start/size fields before any
write. It must preserve the exact serviceability DT, mapping, call count, and
zero-action scope.

## Conclusion

Exact candidate `43e7f44e...eac3` completed its one physical selection and
preserved the CPU0--7 serviceability foundation. It localized the first
checkpoint refusal to live four-slot prefix validation after successful DT
and mapping gates. This is not a checkpoint or persistence pass. CPU8 and
CPU9 remain closed, and no new hardware-support claim is made.

## Follow-up

Add one default-off, read-only live prefix-reason marker to this exact first
call. Capture the first failing slot index plus its bounded signature, start,
and size fields before any write; distinguish a bad signature, nonzero empty-
slot metadata, and any other exact-header mismatch. Do not repeat this stage
candidate, change the prefix policy, enable the clock node, or request a CPU
until that observation identifies the mismatch.
