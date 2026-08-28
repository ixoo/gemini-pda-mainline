# Experiment: serviceable live admission past an unavailable retained trace

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-mainline-a72-admission-softtrace-serviceable` |
| Status | `running` |
| Subsystem | MT6797 CPU8 admission controller and boot-container DT selection |
| Device variant | Planet Gemini PDA, named project device |
| Date(s) | 2026-08-28 |
| Investigator(s) | Project owner and Codex |

## Question or hypothesis

Does the already-built trace-softfail kernel reach its root-only one-shot and
report the first real admission result when its container uses the exact
serviceability-restored DT that previously proved the complete prerequisite
graph?

The retired predecessor used raw full-admission DT `1bd6ce2d...`, which omits
the proven serviceability transform. This candidate changes only that container
input to exact restored DT `1478f2c8...`; kernel, configuration, ramdisk,
command line, trigger contract, and CPU action limits remain unchanged.

## Provenance and environment

- Kernel package: exact Buildbox output from clean commit `f89406be...`.
- Kernel release: `7.1.3-gemini-a72-admission-softtrace`.
- Base DT: `1bd6ce2d...`.
- Selected serviceability DT: `1478f2c8...`.
- Serviceability ramdisk: `e0dffa04...`.
- Kernel rebuild: none; the validated Buildbox package is reused.
- Boot path: LK Android-v0 container installed to live-GPT logical `boot2`.

## Safety assessment

Probe remains inert. Only the existing exact root-only token can execute the
controller once. The retained-trace return is advisory only for that explicit
live execution and remains fail-closed for automatic mode. CPU8 request maximum
is one; CPU9, CPU_OFF, retry, storage, reboot, and automatic probe action paths
remain absent.

The standing `boot2` authorization applies after exact package, DT, container,
target, power, and readback gates pass. No fresh backup is required. A verified
write ends in clean shutdown, never automatic reboot.

## Procedure

1. Source-pin the validated softtrace builder and replace only its raw DT input
   with exact proven serviceability DT `1478f2c8...`.
2. Require deterministic raw and padded construction plus all 32 LK gates.
3. Independently require exact package identities, the complete
   controller/binder graph, and all six restored serviceability nodes.
4. Install only the exact padded candidate to live-GPT inactive `boot2`, verify
   its complete readback, and shut Gemian down.
5. Arm USB/netcat before one owner-selected boot. Require the same-boot armed
   frame before sending the trigger once.
6. Classify the returned operation, source-register, derive, publish, CPU8
   request, or reset boundary. Never retry the trigger.

## Decision map

| Observation | Decision |
| --- | --- |
| No exact mainline USB | Recover retained records; reject serviceability despite corrected DT. |
| Armed frame, no trigger | Host observation only; do not infer CPU behavior. |
| Terminal source/derive/publish error | Fix the named prerequisite stage. |
| One `add_cpu(8)` error | Localize the generic/firmware CPU-on boundary. |
| CPU8 online, CPU9 offline | Run only the bounded same-boot acceptance checks. |
| Disconnect after committed trigger | Recover retained records; never retry. |

## Observations

The source-pinned builder selected exact restored DT `1478f2c8...` while
retaining the exact Buildbox kernel, configuration, serviceability ramdisk,
command line, and LK name from the retired image. Two independent raw
assemblies agree on `8dbc6642...`; two independent padding constructions agree
on exact 16 MiB boot2 payload `df82bbfa...`.

All 32 LK gates pass. The independent validator separately checked package and
artifact manifests, the appended DT boundary, six exact serviceability nodes,
one controller, one binder, no standalone observer, the complete supplier
graph, trace-softfail markers, and one-CPU8/zero-CPU9/zero-CPU_OFF/zero-retry
limits. No kernel rebuild, native VM build, device access, or hardware write
occurred.

## Conclusion

Exact candidate `df82bbfa...` is independently validated and eligible for the
guarded live-GPT `boot2` deployment gate. It differs from the retired candidate
only in the selected DT derivative and resulting deterministic container bytes.

## Follow-up

Use the single attributable operation result to choose the next CPU8 boundary.
Do not repeat an identical artifact.
