# Manual retained-checkpoint control

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-21-mainline-manual-checkpoint-control` |
| Status | running; patch-integrity correction selected after Buildbox attempt 1 |
| Subsystem | pstore/ramoops, retained-RAM observation, arm64 serviceability |
| Device variant | Gemini PDA x27, named project unit |
| Date(s) | 2026-08-21 |
| Investigator(s) | Julien Etienne, Codex |
| Tracking issue | Gate 7 / CPU8 prerequisite localization |

## Question or hypothesis

Does the exact shared two-record retained writer complete both writes and full
local readbacks when called independently from a late initcall on the
runtime-proven current-tree serviceability base, without the clock backend,
observer, either protected transport, or the DA921x action path?

The same mainline boot must also remain serviceable. After an exact live pass,
one native return to Gemian tests whether the two records survive the cross-
version recovery path. Returned empty slots alone remain non-causal evidence.

## Provenance and environment

- Runtime-proven foundation: exact padded candidate
  `7084f2ee87af103dfcf1dfad9956f54c2a9df8d37b5f6d0388ba45464d8d52a3`
- Foundation kernel release: `7.1.3-gemini-service-ctl`
- Foundation runtime result: exact USB/netcat serviceability pass, CPU0--7,
  keyboard, read-only DA921x provider, and native changed-ID return
- New profile: `da921x-manual-checkpoint-control`
- Expected release: `7.1.3-gemini-checkpoint-ctl`
- Build backend: Buildbox only from an exact clean pushed commit
- Boot path: guarded live-GPT logical boot2 only

Exact build, package, DTB, and candidate identities remain pending Buildbox
validation.

## Safety assessment

Patch `0327` and its profile are default off. The profile disables the arm64
entry ledger before enabling the exact existing protected-readback writer and
its isolated manual control. The late initcall makes at most two short writes,
one each to existing owned dmesg slots 173 and 174. The inherited writer
requires the exact Gemini reservation and four empty valid headers, commits
payload before metadata, fully reads every byte back, never retries, never
clears, and never overwrites a nonempty slot.

The new call site returns zero on success or refusal so observation cannot
block serviceability. It makes no protected read, secure call, device MMIO,
clock operation, I2C transaction, regulator-data write, owner transition, CPU
request, storage access, timer, watchdog, reset, or power operation. CPU8 and
CPU9 remain closed. These two bounded retained-RAM writes are within the
owner's standing diagnostic authorization.

Any installation must use the standing guarded boot2 workflow and shut down
after a matching full readback. The runtime observer must be armed before the
single physical selection.

## Associated code

- `patches/v7.1.3/0327-pstore-add-Gemini-manual-checkpoint-control.patch`:
  default-off Kconfig mode, two unique record identities, and one late initcall
- `configs/gemini-manual-checkpoint-control.fragment`: exact profile delta and
  release identity
- `kernel/manifest.json`: named canonical-series Buildbox profile
- `scripts/validate.py`: patch, profile, record, CRC, and safety validation
- `scripts/test-validate.py`: negative source and configuration mutations
- `contract.json`: frozen writer boundary, safety scope, and decision map

Candidate, installer, live probe, retained recovery, and independent container
tooling will be added only after the exact Buildbox package exists.

## Procedure

1. Validate patch `0327`, the exact parent-profile derivation, all record CRCs,
   default-off behavior, canonical series order, and all manifest profiles.
2. Sign and push the clean definition commit to the exact project origin.
3. Build only with
   `KERNEL_PROFILE=da921x-manual-checkpoint-control ./scripts/build-kernel --backend buildbox`.
4. Fetch only the validated package, derive the exact proven serviceability DT,
   construct twice, and independently reject configuration, source, DT,
   container, and safety mutations.
5. Guardedly install to inactive logical boot2, match the full readback, shut
   down, and pre-arm both exact USB and changed-cycle recovery.
6. Physically select boot2 once. Require the exact release, serviceability
   oracle, and one unique live result with `first=1 second=1 retained_writes=2`.
7. Only after the live pass, issue one native USB-shell reboot and recover both
   exact records plus unchanged boot2 from changed-ID Gemian.

## Observations

The predecessor serviceability control passed on one exact selection. The
shared writer remains unproved independently because all earlier returned slot
captures were empty even after a known serviceable mainline boot.

Buildbox attempt 1 fetched exact signed commit `733c9e36d4e77bf33d5ce71e9924fe3ede021bf2`
and applied canonical patches `0001` through `0326`, then rejected patch `0327`
as corrupt at its second file boundary. The failure occurred before
configuration, compilation, packaging, candidate assembly, or device access.
Review found incorrect hand-authored unified-diff line counts. The correction
adds an exact four-hunk count validator plus a thirteenth negative mutation;
independent `git apply --numstat` parsing now reports Kconfig `22/1` and C
`29/1`. Attempt 1 produced no package or boot candidate and cannot be used for
hardware inference. See the
[attempt-1 receipt](results/buildbox-attempt-1-patch-reject-20260821.txt).

## Analysis

Clock-entry candidates combined a new Image/configuration, the shared writer,
and clock-driver call sites. The new current-tree control removed that writer
and restored serviceability. This experiment reintroduces only the writer and
two direct calls while keeping every clock and protected-transport path absent.
It therefore separates a general writer/mapping/prefix failure from clock-node
registration and probe behavior.

## Conclusion

Pending Buildbox and runtime evidence. No checkpoint, persistence, or hardware-
support claim has yet been made.

## Follow-up

If the live two-write oracle passes, redesign the next enabled-clock-node probe
to expose a live result rather than relying on returned empty slots. If this
control loses serviceability or refuses locally, stop clock and CPU8 work and
repair the shared writer on the exact proven base. CPU8 and CPU9 remain closed.
