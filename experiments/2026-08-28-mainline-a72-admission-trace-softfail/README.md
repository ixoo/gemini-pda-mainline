# Experiment: live admission past an unavailable retained trace

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-mainline-a72-admission-trace-softfail` |
| Status | `complete`; candidate retired after a serviceability-DT construction defect |
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

From known-good Gemian boot `a30458b2...`, the guarded installer resolved
logical `boot2` as inactive, unmounted `/dev/mmcblk0p30`, confirmed exact
predecessor `fd611a4c...`, stable external power and empty retained records,
then wrote `83dec186...`. Sync, flush, full-partition readback, and clean
shutdown all passed. No fresh backup was made and no reboot was requested.

Attempt 1 ended in an automatic return to Gemian before the exact USB network
interface appeared. The armed collector opened zero sessions and sent no
trigger. Recovery boot `def2064d...` confirmed the candidate remained installed,
pstore was empty, all three admission records were empty, and `last_kmsg` was
the known generic 74-byte header. This is strictly a pre-trigger
non-serviceability result; it does not test trace soft-failure or CPU8.

An identical unobserved repeat is forbidden. A new host-only observer now
records sanitized USB VID/PID/session and exact Gemini network transitions at a
0.25-second cadence while the existing collector remains authoritative for
packet readiness and netcat. This makes one repeat decision-changing even if
the device returns to Gemian before the network interface becomes usable.

Attempt 2 used that independent observer. After the owner selected `boot2`, the
host saw exact Gemian USB disappear, MediaTek preloader `0x0e8d:0x2000`, an
otherwise unidentified `0x0e8d:0x20ff` stage, a second preloader enumeration,
and finally changed-session Gemian USB. The exact mainline network interface
never appeared, so the collector opened zero sessions and sent no trigger.
Changed-ID Gemian `d473e30e...` still read exact installed candidate
`83dec186...`; pstore was empty, both admission traces were empty, the
transition ledger was logically empty, and `last_kmsg` was the same known
generic 74-byte header. This independently localizes the attempt before the
controller and still does not test CPU8 or trace soft-failure.

The post-attempt construction audit found the cause. Candidate validation had
recorded raw full-admission DTB `1bd6ce2d...`, not serviceability-restored DTB
`1478f2c8...`. The former is the already-rejected raw DT whose USB controller,
T-PHY/U2 port, I2C5, AW9523, and keyboard statuses require the proven
serviceability transform. The builder accidentally derived from the durable
raw-DT candidate instead of the serviceable ATAG lineage. The observed absence
of mainline USB is therefore consistent with a known container defect and is
not evidence against the trace-softfail kernel change.

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

Offline kernel and focused KUnit validation passed, but the selected boot
container used the wrong DT derivative. Neither physical attempt reached the
root-only trigger or requested CPU8. The subsecond second attempt and retained
recovery make the pre-controller result attributable, and the construction
audit explains it with the known raw-DT serviceability defect. Candidate
`83dec186...` is retired and must not be repeated.

## Follow-up

Assemble the already-built exact softtrace kernel with proven DT
`1478f2c8...` and the unchanged serviceability ramdisk. Independently require
the six restored serviceability nodes, complete controller/binder graph, exact
package identities, deterministic LK construction, and all container gates.
This correction needs no kernel rebuild. Only that non-identical, one-DT-change
candidate may return to the live one-shot decision map.
