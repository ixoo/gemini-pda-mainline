# Experiment: first dmesg raw-write qualification

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-22-mainline-first-dmesg-raw-write-qualification` |
| Status | exact candidate admitted; boot2 deployment pending |
| Subsystem | retained ramoops writer / downstream dmesg enumeration |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-22 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, retained checkpoint qualification |

## Question or hypothesis

Will known-good Gemian expose the already-qualified one-record raw write when
the same signature-last transaction targets first dmesg record 1 at physical
`0x44410000` rather than sparse record 173?

The predecessor proved that one exact record can be committed, fully read back,
and retained through a native reboot. Its valid record at `0x444bd000` remained
behind empty earlier dmesg records and was not enumerated. Pinned downstream
control flow selects only one dmesg index per backend read, and pstore stops
when that read returns zero. The same parser accepts the predecessor's record
prefix. See the [predecessor result](../2026-08-22-mainline-manual-checkpoint-raw-write-qualification/README.md).

This successor changes only the owned dmesg position. Its exact hypothesis is:

1. known-good Gemian sees record 1 as exact empty before deployment;
2. the isolated mainline late initcall sees the record's raw header as all ones;
3. the qualified writer commits only record 1 in payload, start, size, signature
   order and fully reads it back;
4. exact serviceability passes before one identity-gated native reboot; and
5. changed-ID Gemian exposes the exact record through pstore, while a bounded
   direct read independently confirms the retained header and payload.

## Provenance and environment

- Writer, full-readback, and warm-retention evidence: signed and pushed commit
  `117aaf7`.
- Parent profile: `da921x-manual-checkpoint-stage-control`.
- New profile: `da921x-first-dmesg-raw-write`.
- Canonical patch: `0333-pstore-qualify-Gemini-first-dmesg-raw-write.patch`.
- Expected release: `7.1.3-gemini-checkpoint-first-dmesg`.
- Build backend: Buildbox only; no native VM build.

## Safety assessment

The option is default off and mutually excludes both prior raw-write modes. It
retains the exact Gemini DT/resource gate, the proven late initcall, raw
all-ones precondition, signature-last transaction, one-write ceiling, exact
full readback, and no-retry behavior. It maps only record 1 at `0x44410000`.
The live read-only preflight found this record exact empty.

The candidate does not map or write the nonempty primary console ring. It has
no normal ramoops registration, second record, clock backend, protected
observer or call, BigiDVFS backend, DA921x action, transition owner, CPU
request, storage access, timer, watchdog, reset, or power operation. CPU8 and
CPU9 admission remain closed.

## Associated code

- `patches/v7.1.3/0333-pstore-qualify-Gemini-first-dmesg-raw-write.patch`
- `configs/gemini-first-dmesg-raw-write.fragment`
- `contract.json`
- `scripts/validate.py`
- `scripts/test-validate.py`
- `scripts/build-serviceability-dtb.sh`
- `scripts/build-candidate.sh`
- `scripts/test-candidate.sh`
- `scripts/install-boot2.sh`
- `scripts/remote-runtime-probe.sh`
- `scripts/validate-runtime.py`
- `scripts/validate-retained.py`
- `scripts/collect-runtime.sh`
- `scripts/test-runtime-tools.py`

## Procedure

1. Validate the exact patch, profile, canonical-series placement, default-off
   mode, record-1 address, one-write ceiling, signature-last inherited writer,
   full readback, live marker, and complete protected/CPU veto inventory.
2. Commit and push the definition with a clean worktree.
3. Build the exact commit on Buildbox with
   `KERNEL_PROFILE=da921x-first-dmesg-raw-write ./scripts/build-kernel --backend buildbox`.
4. Fetch only the validated package, construct the serviceability DT and
   Android-v0 container twice, and require complete configuration, symbol, DT,
   LK, padding, and mutation gates before admission.
5. From known-good Gemian, resolve inactive live-GPT `boot2`, require exact
   empty record 1 plus all existing storage/power gates, write and fully read
   back the admitted candidate, then shut down cleanly.
6. Arm USB and changed-ID recovery before one physical selection. Return
   natively only after exact live identity, serviceability, record-1 success,
   and zero-action attribution.
7. Capture pstore contents, direct record-1 bytes, ramoops registration lines,
   pstore mount state, changed boot ID, and exact boot2 checksum before choosing
   any protected-call successor.

## Decision map

- Live success plus exact pstore recovery qualifies the raw writer, warm
  retention, and first-record cross-version enumeration.
- Live success plus an exact direct record but no pstore exposure keeps the
  remaining boundary in Gemian backend or userspace recovery behavior.
- A live refusal remains inside its exact validation, mapping, prefix, write,
  or readback stage.
- Loss of serviceability without an attributable record rejects the artifact
  without repetition.

No branch authorizes a protected clock call or CPU8/CPU9 admission.

## Conclusion

The source and configuration definition passes its exact Buildbox-source apply,
all 114 manifest-profile series invariants, 14 unsafe definition mutations,
eight invariant-auditor mutations, JSON and whitespace gates, and strict style
gate with only the policy-required synthetic-signoff and inherited split-string
diagnostics explicitly excluded. See the
[prebuild result](results/prebuild-definition-20260822.txt).

The first Buildbox submission of commit `dd9b3ec` stopped during Kconfig before
compilation because both raw-write options carried reverse negative
dependencies. Kconfig treats that redundant mutual exclusion as a recursive
dependency. The correction removes the reverse dependency from the historical
option while the new option still excludes the historical mode and its profile
explicitly disables it. No binary or candidate was produced. See the
[failed build result](results/build-dd9b3ec-kconfig-recursion.txt).

The corrected commit `41a7b69` built successfully on Buildbox as exact release
`7.1.3-gemini-checkpoint-first-dmesg`. The fetched package passes its complete
checksum manifest. Two independent serviceability-DT constructions are
byte-identical to runtime-proven SHA-256 `b638674b...12dd`.

Two independent Android-v0 assemblies and two independent padding methods are
byte-identical. The raw container is 6,895,616 bytes with SHA-256
`bcb8b61a...e5b5c`; the exact 16 MiB `boot2` payload is
`b96ec109...9e96`. Independent admission passes all 32 LK gates, rejects 15
DT/container mutations, and confirms the exact configuration, unique record
and live markers, writer symbols, zero protected-call paths, and closed CPU8/9
admission. The candidate is admitted for one physical `boot2` selection; this
does not yet make a hardware-support claim. See the
[Buildbox result](results/build-41a7b69-success.txt) and
[candidate admission](results/candidate-admission-bcb8b61a.txt).

## Follow-up

Install the exact admitted padded image to live-resolved inactive `boot2`, shut
the device down, pre-arm the observer, and spend one physical selection. The
changed-ID result chooses between a protected-call successor and a remaining
Gemian pstore/backend recovery investigation. The ordered successor after this
qualification remains owned by Roadmap Gate 7.
