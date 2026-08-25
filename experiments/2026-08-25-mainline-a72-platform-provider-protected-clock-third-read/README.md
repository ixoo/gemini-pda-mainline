# A72 platform/provider/protected-clock third read

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-25-mainline-a72-platform-provider-protected-clock-third-read` |
| Status | attempt 1 is an exact serviceable pre-clock `-EAGAIN`; failing stage is ambiguous between platform and provider snapshots; unchanged retry prohibited |
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
write, or hardware call has occurred for this experiment. Buildbox attempt 2
with the repaired endpoint validator passed every source phase, exact patch
scope, and byte-identical replay. Strict checkpatch then rejected only eight
production-patch style checks: seven lines ending at an open parenthesis and one
continuation alignment. The implementation and semantic validators had passed;
no package was promoted. The style-only repair also removes the same declaration
pattern from the later test patch before retry. Attempt 3 again passed all
semantic, patch-scope, and replay gates; strict checkpatch reduced to one
production log-function continuation-alignment check. The exact repair aligns
that argument and also fixes two test-template issues found by a proactive
strict diff check before attempt 4. Fresh Buildbox strict diagnostics now report
zero errors, warnings, or checks for both production and test template diffs.
Attempt 4 from signed commit `c89baef5` then passed all four source phases,
the exact patch inventory and scope, byte-identical replay, and strict style
with zero findings for every patch. The fetched checksum manifest passes;
canonical patches `0374`--`0377` match the fetched package byte-for-byte, and
all 135 manifest profiles preserve canonical order after adding only the
isolated eight-case KUnit and device profiles. No kernel build, boot image,
retained-memory write, hardware call, or device action has occurred. See the
[generation receipt](results/buildbox-generation-20260825.txt).
The first focused Buildbox build from admitted commit `32ed7377` applied all
377 patches but Kconfig rejected `defconfig` before compilation: the new and
predecessor ledger symbols had reciprocal negative dependencies. The repair
keeps the new mode's `depends on !...SNAPSHOT_LEDGER` gate and removes only the
reverse edge, preserving effective exclusion without a Kconfig recursion. A
new tooling mutation recreates and rejects the cycle. No compiler, KUnit,
QEMU, retained-memory, hardware, or device action ran. See the
[configuration rejection](results/buildbox-kunit-config-rejected-20260825.txt).
Generation attempt 5 then stopped before source editing because canonical
admission had advanced Buildbox's shared managed source from parent 0373 to
tail 0377. The corrected lane prepares a separately named, reusable managed
source from a manifest-selected canonical subsequence ending exactly at 0373;
it does not copy a source tree or invoke a native build. All 136 profiles pass
the series invariant, and a fourteenth tooling mutation rejects a wrong parent
profile. See the [parent-state rejection](results/buildbox-generation-attempt-5-parent-state-rejected-20260825.txt).
Attempt 6 prepared that exact post-0373 tree and independently matched its
full integrity plus both edited pstore file hashes, then stopped because the
managed series marker is `0ec8eccb…` rather than the legacy parent marker
`c5bc1470…`. The generator now pins the observed managed marker separately
while retaining every full integrity and file-identity gate. No source edit,
package, kernel build, QEMU, hardware, or device action occurred. See the
[marker rejection](results/buildbox-generation-attempt-6-parent-marker-rejected-20260825.txt).
Attempt 7 reused that verified managed parent and passed ledger, binding,
observer, eight-case source validation, exact patch scope, byte-identical
replay, and strict style with zero findings. The fetched checksum manifest
passes; corrected canonical patches `0374`--`0377` match the package
byte-for-byte, the reciprocal Kconfig edge is absent, and all 136 profiles
remain canonical subsequences. Exact admitted commit `8c400054` then compiles
the isolated KUnit profile on Buildbox as
`7.1.3-gemini-a72-clock-third-kunit`; its fetched package and checksum manifest
pass, the required composition symbols are present, physical writer symbols
are absent, and the new observer emits no compiler warning. The sole
no-network QEMU suite passes all eight cases with zero failures or skips,
including terminal clock-error, after-checkpoint-error, and invalid-identity
paths. No physical I2C, clock backend, MMIO, retained RAM, native VM build,
hardware write, CPU request, or device action occurred. See the [corrected
generation receipt](results/buildbox-generation-attempt-7-20260825.txt),
[Buildbox compile receipt](results/buildbox-kunit-compile-20260825.txt), and
[QEMU result](results/kunit-qemu-pass-20260825.txt). The next ordered action is
complete: signed commit `5e4b0d58` builds the separate device profile on
Buildbox as `7.1.3-gemini-a72-clock-third`, with no new observer warning and a
checksum-verified fetched package. The decision-bearing DT replaces only the
passed provider observer with the three-reader observer, preserves platform
phandle `0x2f` and provider phandle `0x30`, and adds clock phandle `0x31`; its
reverse replacement reproduces the sorted predecessor DTS byte-for-byte. Two
raw assemblies and two exact-padding constructions agree. All 32 LK gates and
six independent corruption mutations pass. Exact raw candidate `d2f4d2bd…`
pads to 16 MiB `1f7bd960…`. The guarded installer pins the successful provider-
ready predecessor `f55bb272…`, accepts only its exact completed retained pair
or an exact empty pair, requires live-GPT inactive `boot2`, verifies the full
partition after writing, and shuts Gemian down without rebooting or taking a
fresh backup. No device access or hardware write has occurred for this step.
See the [device compile receipt](results/buildbox-candidate-compile-20260825.txt),
[DT validation](results/offline-dtb-validation-20260825.txt), and
[container validation](results/offline-candidate-validation-20260825.txt).
The previously selected publication and guarded deployment are complete. The
installer resolved inactive live-GPT
`boot2` as `/dev/mmcblk0p30`, required exact predecessor `f55bb272…`, matched
the completed provider retained pair, stable external power and both TEE
identities, then wrote and independently read back exact padded candidate
`1f7bd960…`. It made no fresh backup or retained-memory write, removed staging
and readback temporaries, and confirmed a clean shutdown without rebooting.
See the [deployment receipt](results/deployment-boot2-20260825.txt). The next
ordered action is one owner-selected `boot2` start followed by the prevalidated,
identity-gated, no-reboot runtime collector. Its four accepted terminal
branches and 19 rejected attribution/safety mutations are recorded in the
[preboot tooling receipt](results/preboot-runtime-tooling-20260825.txt). The
artifact must not be retried unchanged after a decision-bearing result.
Attempt 1 is decision-bearing and leaves mainline running. Exact release
`7.1.3-gemini-a72-clock-third`, boot ID `574bb2c4…`, CPUs 0--7, USB, T-PHY,
I2C5, keyboard, platform-state, provider, clock backend, and BigiDVFS backend
all pass their identity and serviceability gates. The composed observer device
exists but is unbound; it emits one capture failure and no snapshot record.
Bounded follow-up dmesg identifies `-EAGAIN` at 46.168257 seconds. Exact source
order therefore proves zero retained writes, zero protected-clock calls, zero
gate pairs, and zero CPU requests. It cannot distinguish whether the unstable
two-sample operation was the platform snapshot or the provider snapshot. The
post-attempt classifier accepts only this exact failure plus its exact dmesg
evidence and rejects 15 mutations. See the
[runtime receipt](results/runtime-attempt-1-20260825.txt) and
[bounded dmesg excerpt](results/runtime-attempt-1-dmesg-20260825.txt).

The next discriminator adds an explicit platform-versus-provider failure stage
without changing the hardware call order or retrying this exact artifact. Only
after that hardware-free instrumentation passes may a distinct candidate make
the still-unreached protected-clock attempt.
The ordered continuation is owned by the
[Roadmap](../../docs/ROADMAP.md#7-bring-up-cpu8).
