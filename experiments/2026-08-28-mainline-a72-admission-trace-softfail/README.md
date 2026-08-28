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

Buildbox generated two exact format-patches from its integrity-verified
post-`0420` prepared tree. Both source stages, strict checkpatch, independent
replay, and replay source validation passed. The admitted patch SHA-256 values
are `e5b55c5e...` and `01a6155c...`.

Canonical integration contains 414 patches. Both named profiles are
canonical-order subsequences and all 158 manifest profiles pass the invariant
audit.

Buildbox compiled both profiles from exact clean commit `f89406be...`. The
hardware-free QEMU run reported all 6 admission-trace cases and all 10
admission-controller cases passing, including both the new live soft-failure
case and the unchanged automatic fail-closed control.

The production package and LK container passed independent checksum, config,
symbol, DT graph, reproducible assembly, zero-padding, and all 32 recovered LK
container gates. The exact 16 MiB `boot2` payload is `83dec186...` and is now a
validated boot candidate.

The owner observed that the preceding mainline boot remained on the boot image
without displaying a framebuffer console. USB/netcat was live on that same
boot, so this is recorded as a display-path observation rather than a kernel
health or boot-failure result. The next attempt therefore makes USB/netcat the
authoritative path and does not require a framebuffer console.

## Analysis

The delta changes no hardware call site. It adds one policy bit to
the injected controller operations, selects it in production only when the
existing live-trigger Kconfig option is enabled, and preserves both trace
return values alongside the real admission result. The pre-existing strict
KUnit case remains the automatic fail-closed control; a new case covers live
entry and terminal trace failures. The runtime parser now requires those trace
returns independently of the admission operation return, preventing another
instrumentation failure from being mistaken for the CPU8 result.

## Conclusion

Offline validation is complete. One deployment and one boot remain pending.
This candidate is not a repeat: unlike the previous image, its exact root-only
trigger continues beyond retained-trace `-EIO` and should expose the first real
source-register, derive, publish, or CPU8 request result.

## Follow-up

If the core reaches `add_cpu(8)`, use its return and the resulting online mask
to select the next hardware boundary. If it stops earlier, act on that named
stage. Do not repeat an identical artifact.
