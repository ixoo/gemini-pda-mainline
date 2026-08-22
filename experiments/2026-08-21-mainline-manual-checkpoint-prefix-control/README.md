# Manual checkpoint live prefix-reason control

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-21-mainline-manual-checkpoint-prefix-control` |
| Status | running; exact Buildbox candidate admitted, device deployment pending |
| Subsystem | pstore retained writer, live prefix-header attribution |
| Device variant | Gemini PDA x27, named project unit |
| Date(s) | 2026-08-21 |
| Investigator(s) | Julien Etienne, Codex |
| Tracking issue | Gate 7 / CPU8 prerequisite localization |

## Question or hypothesis

Which first live header makes the unchanged four-slot prefix predicate refuse
the isolated manual checkpoint: a bad signature, nonzero start, nonzero size,
or a value that changes between the predicate and its bounded post-refusal
snapshot?

This is not a repeat of candidate `43e7f44e...eac3`. Canonical patch `0329`
adds one independent live observation that reports the first failing relative
slot index and its three header words. It does not change the predicate or
attempt to repair the header.

## Provenance and environment

- Runtime-proven foundation: manual checkpoint stage candidate
  `43e7f44eeef694ef876f7686ae03e2a779a118141e7f9efa060ccc1182c8eac3`
- Foundation result: exact serviceability pass with
  `stage=prefix-refused`, `first=0`, `second=0`, and zero writes
- Foundation mainline release: `7.1.3-gemini-checkpoint-stage`
- Foundation evidence commit: `55690096fe502064cfa25110bca6801ff5ee3d85`
- New profile: `da921x-manual-checkpoint-prefix-control`
- Expected release: `7.1.3-gemini-checkpoint-prefix`
- Build backend: Buildbox only from an exact clean pushed commit
- Boot path: guarded live-GPT logical boot2 only

Buildbox fetched exact clean commit `49f8e7f`, compiled release
`7.1.3-gemini-checkpoint-prefix`, and produced package
`linux-7.1.3-gemini-da921x-manual-checkpoint-prefix-control-b0fce1cc-f81f3888`.
The admitted raw Android-v0 candidate is `1d69e033...5e6ee`; its exact 16 MiB
boot2 image is `ced1f56f...f3901`.

## Safety assessment

Patch `0329` and its profile are default off. The profile inherits the exact
manual call count, at-most-two retained writes, fixed stage oracle, and every
clock, protected-transport, DA921x-action, owner, and CPU veto. The new code is
called only after the existing prefix predicate returns false. It reads the
rejected slot's 12-byte header with exactly three `readl()` operations and
records only those values, the relative slot index, checkpoint, and a fixed
reason string.

The patch does not modify `gemini_prb_slot_empty()`,
`gemini_prb_slot_exact()`, the loop order, write target, write protocol, or
return value. It adds no write, retry, clear, loop, timer, mapping, storage,
firmware or device-register MMIO action, I2C transaction, regulator-data
operation, clock or protected read, owner registration, CPU request, reset,
or power action. If the build and candidate gates pass, installation must use
the standing guarded boot2 write/readback/shutdown workflow and the exact
observer must be armed before one physical selection.

## Associated code

- `patches/v7.1.3/0329-pstore-report-Gemini-manual-checkpoint-prefix-reason.patch`:
  default-off post-refusal header snapshot and one new live marker
- `configs/gemini-manual-checkpoint-prefix-control.fragment`: exact profile
  delta and unique release
- `kernel/manifest.json`: named canonical-series Buildbox profile
- `scripts/validate.py`: patch, fragment, profile, contract, safety, and
  canonical-tip validator
- `scripts/test-validate.py`: negative source/configuration mutations
- `contract.json`: frozen hypothesis, result map, and safety scope
- `scripts/build-candidate.sh` and `scripts/test-candidate.sh`: exact two-way
  construction and independent package, DT, Image, symbol, and container gates
- `scripts/install-boot2.sh`: source-pinned live-GPT write/readback/shutdown
- `scripts/collect-runtime.sh`, `scripts/remote-runtime-probe.sh`,
  `scripts/validate-runtime.py`, and `scripts/validate-retained.py`: exact
  pre-armed reason capture, native Gemian return, and bounded recovery

## Procedure

1. Validate the patch, unchanged predicate, exactly three post-refusal reads,
   fixed reason inventory, default-off Kconfig gate, exact parent-profile
   derivation, canonical order, and every manifest-selected series.
2. Sign and push the clean definition commit to the exact project origin.
3. Build only with
   `KERNEL_PROFILE=da921x-manual-checkpoint-prefix-control ./scripts/build-kernel --backend buildbox`.
4. Fetch only the validated package, then pin and independently validate the
   exact Image, configuration, symbols, serviceability DT, Android-v0
   container, and negative mutations before admitting one candidate.
5. Guardedly install to inactive logical boot2, match the full readback, shut
   down, and arm the exact USB observer.
6. Select boot2 once. Require the exact candidate, release, serviceability,
   historical boolean marker, `prefix-refused` stage marker, and one unique
   prefix-reason marker before a native return to Gemian.

## Observations

The exact parent completed one physical selection with serviceability intact.
Sequence, exact DT/resource conversion, and `ioremap_wc()` passed. The first
call then reported `prefix-refused` before any retained write; the second call
was short-circuited. Changed-ID Gemian recovered the owned slots empty, but
that later cross-version view cannot reveal what the mainline late initcall
read.

The new patch parses as 14/0 Kconfig lines and 59/1 C lines. A read-only
Buildbox `git apply --check` passes against the exact prepared canonical source
through patch `0328`. Strict checkpatch has no warning; its sole error is the
intentionally absent synthetic-author sign-off.

The exact fragment/profile contract, four unified-diff hunk counts, five fixed
reasons, three-read ceiling, canonical-series invariant across all 110
profiles, eight series-invariant self-test mutations, and 16 unsafe source or
configuration mutations pass. See the
[prebuild receipt](results/prebuild-definition-20260821.txt).

The Buildbox package passes its full checksum inventory and binds the clean
pushed commit, profile, 24 configuration fragments, cross toolchain, Image,
configuration, symbols, DTBs, and release. No native VM build occurred. See
the [build receipt](results/build-49f8e7f.txt).

Two independent serviceability-DT derivations, two raw assemblies, and two
padding constructions are byte-identical. The exact candidate passes all 32
LK Android-v0 gates, 15 independent DT mutations, exact Image markers and
reason strings, configuration and symbols, 16 definition mutations, and the
offline runtime tools. Those tools accept four header-consistent live reasons
while rejecting 32 unsafe live mutations and eight retained mutations. See the
[candidate receipt](results/candidate-1d69e033.txt).

## Analysis

The parent stage result eliminates sequence, DT/resource, and mapping refusal.
Because `gemini_prb_prefix_valid()` walks relative slots 0 through 3 and
returns on the first mismatch, a post-refusal snapshot at that return point
identifies the earliest rejected header without altering the decision. Raw
signature/start/size values keep the fixed reason independently auditable.

The snapshot is deliberately after the existing predicate. If all three words
appear valid despite the refusal, `unstable-or-other` identifies a changed or
otherwise non-reproduced read rather than silently claiming an empty header.

## Conclusion

Exact candidate `ced1f56f...f3901` is admitted for one guarded boot2
deployment and one physical selection. No device write, runtime prefix reason,
persistence result, or hardware-support claim is made yet. CPU8 and CPU9
remain closed.

## Follow-up

Commit and push this candidate admission, install it through the guarded live
GPT workflow, confirm full readback, shut down, and arm the observer before one
physical selection. The live reason must select the next correction or
observation; do not change the prefix policy or proceed to clock-node
population until the header mismatch is attributable.
