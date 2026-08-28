# Experiment: live admission past an unavailable retained trace

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-mainline-a72-admission-trace-softfail` |
| Status | `running` |
| Subsystem | MT6797 CPU8 admission controller |
| Device variant | Planet Gemini PDA, named project device |
| Date(s) | 2026-08-28 |
| Investigator(s) | Project owner and Codex |

## Question or hypothesis

The exact `7.1.3-gemini-a72-admission-live` attempt reached its root-only
trigger but returned `-EIO` from the retained admission-trace entry before the
controller consumed its core one-shot. The next discriminating question is:
does the same serviceable boot reach the existing CPU8 admission operations if
the explicitly triggered live mode records, but does not obey, a trace-write
failure?

This tests an instrumentation obstruction, not a claim that CPU8 will come
online. A resulting source-register, derive, publish, or `add_cpu(8)` result is
the unique decision-changing evidence.

## Provenance and environment

- Parent canonical patch: `0420-soc-mediatek-test-live-CPU8-admission-trigger.patch`
- Prepared source state: `339cd91972289d196912c2c2aa18670ced6ca70769b1905930aaf08998f9ce7c`
- Prepared source integrity: `ce015b21432cfbb8d16d79da4603d80732deef964f52f31da874f64c2d6bd1aa`
- Build backend: Buildbox only through `./scripts/build-kernel --backend buildbox`
- Boot path: LK container installed to live-GPT logical `boot2`

## Safety assessment

The production change is active only with the existing default-off live-trigger
configuration. Probe remains inert. One exact root-only token is consumed
before one synchronous controller execution. Entry and terminal trace errors
remain separately observable, while the admission result is no longer replaced
by diagnostic trace failure in this mode. Automatic admission remains
fail-closed. CPU8 request maximum remains one; CPU9, CPU_OFF, retry, storage,
reboot, and automatic probe action remain absent.

The standing `boot2` authorization applies after package, candidate, target,
power, and readback gates pass. No fresh device backup is required. A verified
write must end in clean shutdown, never automatic reboot.

## Associated code

- `scripts/generate-on-buildbox`
- `scripts/generate-patches.py`
- `scripts/source_edits.py`
- `scripts/validate_source.py`
- canonical patches `0421` and `0422` after admission
- named Buildbox KUnit and device-candidate profiles

## Procedure

1. Generate two format-patches from the exact prepared post-`0420` source on
   Buildbox and replay them there.
2. Admit them to canonical order and validate every manifest profile.
3. Build the KUnit profile and run the focused suites without device actions.
4. Build and independently validate the production candidate on Buildbox.
5. Install the exact padded candidate to logical `boot2`, verify full-partition
   readback, and shut down the device.
6. On the single boot, require the live pre-trigger frame before consuming the
   exact token. Treat USB/netcat as authoritative; framebuffer console absence
   is a display observation only.

## Observations

Pending.

## Analysis

Pending.

## Conclusion

Pending.

## Follow-up

If the core reaches `add_cpu(8)`, use its return and the resulting online mask
to select the next hardware boundary. If it stops earlier, act on that named
stage. Do not repeat an identical artifact.
