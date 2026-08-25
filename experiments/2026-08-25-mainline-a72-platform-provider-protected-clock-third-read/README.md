# A72 platform/provider/protected-clock third read

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-25-mainline-a72-platform-provider-protected-clock-third-read` |
| Status | definition frozen; source generation pending |
| Subsystem | MT6797 A72 state, DA921x provider, DVFSP protected clock |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-25 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, isolated third reader |

## Question

Can exactly one handoff-owned protected-clock snapshot return after the exact
platform/provider prefix that passed on the named Gemini, while Stage-27
serviceability survives and CPU8/CPU9 remain closed?

The predecessor qualified one two-sample platform snapshot with 26 register
observations, followed by one two-sample DA921x provider snapshot with ten I2C
reads and no data write. This experiment changes only the next boundary. It
does not repeat the old protected-readback artifact that returned to Gemian
before transport attribution, and it does not add BigiDVFS.

## Frozen discriminator

Before any physical call, a new candidate-only observer must resolve and hold
three exact bound sources: the platform-state device, `dlg,da9214-legacy`, and
`mediatek,mt6797-dvfsp-clock-backend`. A missing source returns
`-EPROBE_DEFER` with no platform, provider, retained-memory, or clock effect.

The admitted call order is platform, provider, retained `before-clock`, one
protected-clock call, retained `after-clock`. The two new records use token
`GAPC-20260825-A` in first-dmesg slots 1 and 2. They are independent of the
retired provider pair: no checkpoint is written around the already-qualified
provider call.

Once the clock function returns, the observer must never ask the platform core
to repeat it. A clock error or after-checkpoint failure is logged as a terminal
observation, with the exact return code and every clock record field. A
successful attempt requires `ret=0`, ABI 2, generation 1, both exact retained
records, one terminal receipt, and zero duplicate calls.

## Safety boundary

This runtime is deliberately not hardware-read-only. The clock backend uses one
balanced I2C clock prepare-enable/disable pair and the handoff-owned CSPM
protocol. Its source-enforced worst-case ceiling is one power-on write, at most
400 semaphore request writes, at most 400 semaphore reads, one power-on
readback, and 18 fixed payload reads. That is at most 401 explicit MMIO writes
and at most 419 explicit MMIO reads inside one backend call. There is no caller retry.

The experiment adds no DA921x register-data write, secure call, BigiDVFS read,
provider acquire/release, state publication, owner mutation, CPU request,
reset, or power action. `maxcpus=8` remains mandatory. A failed attempted clock
snapshot may set only the existing clock-backend fault latch.

Kernel generation and compilation run on Buildbox only from clean pushed
commits. No native VM build is authorized. Any later installation must use the
guarded logical-`boot2` workflow, full-partition readback, and clean shutdown;
no fresh partition backup is required.

## Provenance

- Canonical parent: patch `0373`, SHA-256 `de668030…`.
- Exact Buildbox prepared source state: `c5bc1470…`.
- Exact prepared source integrity: `7d12af97…`.
- The source audit pins the platform, provider, clock, handoff, retained-ledger,
  and public-ABI file identities.
- The live predecessor is exact release
  `7.1.3-gemini-a72-provider-ready`, boot ID
  `75276384-e76d-4e01-b527-7fde0273e043`, with its published
  `provider_ready_gate=passed` result. A later console attachment reported the
  same boot ID and is not counted as another attempt.

See [`contract.json`](contract.json), [`DESIGN.md`](DESIGN.md), and the
[prebuild source audit](results/prebuild-source-audit-20260825.txt).

## Planned implementation and validation

Buildbox generation will produce four post-`0373` patches: retained records,
binding, observer, and injected KUnit tests. The old platform/provider observer
stays unchanged as the control. The new candidate profile alone will enable the
three-reader observer and the mutually exclusive `GAPC` ledger mode.

Hardware-free tests must prove exact order and the following branches:

1. any supplier not ready: `-EPROBE_DEFER`, zero effects;
2. platform failure or invalid result: zero later effects and zeroed output;
3. provider failure or invalid result: no retained or clock effect;
4. before-clock checkpoint failure: no clock call;
5. clock success: one call, both checkpoints, exact valid result;
6. clock error: one call, both checkpoint attempts, terminal no-retry result;
7. after-clock checkpoint failure: one call, terminal no-retry result; and
8. every failure result before clock entry is byte-for-byte zero.

The smallest meaningful build is the isolated KUnit profile on Buildbox plus a
no-network QEMU run. Only after it passes may the separate device profile be
built, packaged, assembled, and evaluated by the existing container and runtime
mutation gates.

## Decision map

| Unique result | Interpretation | Next action |
| --- | --- | --- |
| Exact live success, both records, all serviceability and closure gates pass | Three-reader composition is qualified | Retire the artifact and freeze the one-request CPU8 candidate |
| `before-clock` only after changed-ID recovery | The clock call started but did not return | Split or repair only the protected-clock transaction |
| Both records with a nonzero clock return | The clock call returned an error | Diagnose that error; do not retry unchanged |
| No clock record | Failure occurred in readiness, platform, provider, or first checkpoint | Use the exact live error; do not implicate the clock transport |
| Duplicate call, missing serviceability, BigiDVFS, action, owner, or CPU effect | Candidate violated its contract | Reject it and repair only the violated boundary |

## Current result

The read-only Buildbox source audit passes and the definition is frozen. The
Git-pinned submit/fetch integration, deterministic four-phase source editor,
source and patch validators, four source templates, and strict no-native-build
gate pass local syntax and tooling validation; ten unsafe tooling mutations are
rejected. Buildbox attempt 1 then stopped during observer-source validation
because the validator ended each dependency-helper section at that helper's own
declaration and therefore inspected an empty string. This is a validator false
negative before patch packaging; the generated source was not rejected on a
semantic invariant. No kernel build, boot image, device write, retained-memory
write, or hardware call has occurred for this experiment. The ordered
continuation is owned by the [Roadmap](../../docs/ROADMAP.md#7-bring-up-cpu8).
