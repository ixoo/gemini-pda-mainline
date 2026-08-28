# Experiment: serviceable live admission past an unavailable retained trace

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-mainline-a72-admission-softtrace-serviceable` |
| Status | `complete; one live trigger stopped at the unpublished arm64 READY token` |
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

The guarded installer resolved inactive live-GPT `boot2` as
`/dev/mmcblk0p30`, recorded predecessor `83dec186...`, wrote exact padded
candidate `df82bbfa...`, and required the matching full-partition readback.
It made no fresh backup, then shut Gemian down and confirmed three consecutive
TCP closures. The sanitized receipt is
[deployment-df82bbfa-20260828.txt](results/deployment-df82bbfa-20260828.txt).

The owner-selected boot exposed exact USB/netcat and boot ID `fa6df396...`.
The pre-trigger frame passed with the controller bound and armed, CPUs 0--7
online, CPUs 8--9 offline, and zero prior executions or requests. One durable
host intent preceded exactly one trigger session. The action completed with:

```text
operation_ret=-11 core_consumed=0 entry_trace_ret=-5
terminal_trace_ret=0 cpu_requests=0 cpu9_requests=0
cpu_off_requests=0 retries=0
```

The first host classifier rejected only because its model expected the commit
and token on one line while the preserved wire format contains two lines. The
corrected source-pinned classifier accepts the preserved bytes as
`terminal-admission-error`; the trigger was not repeated.

Controller order makes `-11` with `core_consumed=0` exact: binder readiness
passed, `arm64_get_late_cpu_ready_token()` returned `NULL`, and the operation
stopped before source registration, transaction derivation, publication, or
`add_cpu(8)`. A separate read-only same-boot session repeated the terminal
state and found two arm64 messages: the static runtime identity record was
unavailable or invalid, and profile `mt6797-a53-a72-a41-v7` was blocked with
proof mask `0xffffc`.

The source audit independently explains why READY cannot be published by this
image. ABI 7 always adds `ARM64_LATE_CPU_BLOCK_COMMIT_PATH`, describes its
architecture-owned mutation implementation as unavailable, and returns a
READY token only after PLAN_FROZEN, COMMITTED, system verification, and user
finalization. The selected serviceability DT also lacks the separate
`/chosen/gemini-late-cpu-provenance` leaf, but restoring that leaf alone cannot
remove the unconditional commit-path blocker or supply target evidence.

An identity-gated USB reboot returned to changed-ID Gemian. Read-only recovery
verified `boot2` still matched `df82bbfa...`, but pstore, both admission trace
slots, and the transition ledger were empty. Those retained records therefore
did not preserve the complete live terminal state and do not override it. The
sanitized attempt record is
[runtime-attempt-1-ready-boundary-20260828.txt](results/runtime-attempt-1-ready-boundary-20260828.txt).

## Conclusion

Exact candidate `df82bbfa...` restored serviceability and produced the first
decision-changing result past retained-trace failure. The trace-softfail change
worked: entry trace `-EIO` remained visible while the controller continued.
The operation then stopped safely at the unpublished arm64 READY token before
consumption and before any CPU request.

This is progress in attribution, not CPU8 support. It retires the candidate,
proves that repeating it cannot reach `add_cpu(8)`, and exposes a design
mismatch: the production controller requires a token that the active late-CPU
profile deliberately cannot publish.

## Follow-up

Do not repeat this artifact and do not fabricate or bypass a READY token. First
define the smallest architecture-owned, source-reviewable closure for the
missing runtime evidence and commit path, or revise the admission transaction
so that it depends only on an equivalently strong token that can truthfully be
published. Restore the serviceability and provenance DT transforms together in
any future container. Build the next kernel only on Buildbox after source-only
validation and focused failure-path tests.
