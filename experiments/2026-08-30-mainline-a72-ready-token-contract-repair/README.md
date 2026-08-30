# Experiment: align CPU8 admission with expectation-only READY evidence

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-ready-token-contract-repair` |
| Status | `verified boot2 deployment complete; fresh runtime attempt pending` |
| Subsystem | arm64 late-CPU READY token and MT6797 CPU8 admission |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-30 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

The exact live trigger retained `failure_stage=2`, `derive_stage=2`, and
`operation_ret=-EPERM`, identifying `mt6797_a72_ready_token_validate()` before
A34 or any CPU request. Does the validator contradict the production READY
evidence contract by requiring pre-execution target observations that READY
must keep empty?

## Safety assessment

The production plan accepts only bound expectation evidence and explicitly
requires `observed_target_mpidr[]`, MIDR, REVIDR, and target-cap observations
to remain empty before either dormant A72 executes. READY copies that exact
validated evidence into its immutable token. The membership validator instead
requires `observed_target_mpidr[]` to equal `0x200/0x201`.

The repair keeps the target mask, target ordering, expected MPIDRs, profile,
ABI, and all identity checks. It changes the contradictory observed-MPIDR
predicate from “already equals the expected target” to “still empty,” matching
the production contract and remaining fail-closed. It adds no observation,
hardware effect, request, CPU9, CPU_OFF, retry, storage, device, or reboot path.

## Procedure

1. Pin the exact managed Buildbox source through canonical patch `0445` and
   copy only the files required for isolated format-patch generation.
2. Generate one normal format-patch that requires empty pre-execution observed
   MPIDRs and updates all exact READY fixtures.
3. Add a focused mutation proving that either premature observed MPIDR is
   rejected before source capture or owner mutation.
4. Replay and audit the patch on Buildbox, admit it canonically, then run the
   four affected KUnit profiles through the explicit Buildbox backend. The
   local QEMU harness reuses the immediately preceding source-pinned runner,
   extends its exact inventory with the new derived-admission case and the
   DA921x membership fixture, and keeps networking disabled.
5. Only if every offline gate passes, construct one separate boot2 candidate
   with the existing one-shot CPU8-only route and CPU9 veto.

## Observations

Exact candidate `7c962888...` reached serviceable mainline boot ID
`ae5a4cdf...`, verified runtime identity, and an armed zero-execution
controller. One trigger returned `operation_ret=-1`, `failure_stage=2`,
`derive_stage=2`, and zero requests while CPUs 0--7 stayed online and CPUs
8--9 stayed offline. See the
[runtime result](../2026-08-30-mainline-a72-live-a34-predicate-repair/results/runtime-attempt-1-ready-token-rejection-20260830.txt).

The exact prepared source shows:

- production plan validation accepts only bound expectation evidence and
  rejects any nonzero `observed_target_mpidr[]` before READY;
- READY copies that validated zero-valued pair unchanged into the immutable
  token; and
- `mt6797_a72_ready_token_validate()` requires the copied pair to equal
  `0x200/0x201`, then checks the selected member a second time.

No valid production token can satisfy both contracts. This is a deterministic
source contradiction at the exact runtime-retained substage, not an inference
from screen or reboot behavior.

The affected DA921x compatibility profile then exposed a separate stale test
fixture: its provider acquire and abort completed, but both P29 paths were
rejected because the fixture skipped the public CPU8 preflight and claim now
required by the production binder ordering. Patch `0447` adds that exact
hardware-free ordering to the test only; it does not alter production code.
Enabling the full Binder in that narrow profile was rejected at configuration
validation because its physical-effect dependencies are intentionally absent.
Patch `0448` instead adds a hidden KUnit-only owner helper that advances the
exact published CPU8 test transaction to the claimed state while retaining the
production claim's identity, controller, membership, provider, and online-CPU
predicates. The profile therefore remains isolated from the Binder and the
helper cannot perform a hardware access or CPU request.

Buildbox generated one normal patch from clean pushed definition commit
`b1d89d08...` and exact managed post-`0445` source state `36a08401...` with
integrity identity `c56cdf64...`. Patch `0446` is byte-identical to the fetched
review at `5e335ac3...`; deterministic replay and the source-contract audit
pass. Strict checkpatch with the non-submission synthetic-signoff check disabled
reports zero errors, warnings, or checks. The patch updates three exact READY
fixtures, adds one two-target premature-observation rejection case, and adds no
request, CPU9, CPU_OFF, retry, hardware-write, boot-candidate, or device path.
See [`results/patch-generation-20260830.txt`](results/patch-generation-20260830.txt).

The final canonical patchset `b24ad192...` was then rebuilt from clean pushed
commit `46ccf1ad...` in all four affected profiles. Their QEMU runs passed all
60 tests with no failures or skips: DA921x pre-P28 provider-abort 10/10, live
trigger 16/16, derived admission 6/6, and atomic publication 28/28. The focused
premature-observation mutation passes, as do both production-adjacent trigger
and publication suites. Every harness reported zero physical CPU requests,
CPU_OFF requests, and retries; networking and device actions remained absent.
See [`results/final-offline-validation-20260830.txt`](results/final-offline-validation-20260830.txt).

Buildbox produced the production profile from clean pushed evidence commit
`8dc8e806...` with the same serviceable configuration identity as the prior
runtime image and repaired patchset `b24ad192...`. Two independent DT
compositions added only its exact A41 provenance leaf to the runtime-proven
serviceability/admission tree; both produced `11eb5959...`. Two independent
Android-v0 assemblies produced raw image `efe47cb1...`, and two independent
padding paths produced exact 16 MiB boot2 image `a7ce2c2d...`.

The independent container validator passed all 32 LK gates and rejected six
corrupt-container mutations. The independent logical-tree validator preserved
the single controller and binder, proved the DT delta is one package-owned
provenance leaf, and rejected ten representative DT mutations. The candidate
contains exactly one dormant CPU8 request route and no CPU9, CPU_OFF, or retry
route. No request has executed and no device action has occurred. See
[`results/offline-candidate-20260830.txt`](results/offline-candidate-20260830.txt).

Guarded deployment from known-good Gemian boot `5a11f2c2...` resolved live-GPT
logical `boot2` as inactive, unmounted `/dev/mmcblk0p30`, with root on p29 and
exact expected predecessor `7c962888...`. External power was present, battery
was 100% and healthy, and retained transition and admission records were
logically empty. No fresh backup was made. The workflow wrote only `boot2`,
synced and flushed it, and matched complete 16 MiB readback `a7ce2c2d...`.
It then shut Gemini down without rebooting; SSH failure plus three consecutive
closed TCP/22 checks confirm power-off. See
[`results/deployment-20260830.txt`](results/deployment-20260830.txt).

## Analysis

The observed fields represent target-local facts and cannot exist before the
target CPU executes. The expected fields already bind CPU8/9 to MPIDRs
`0x200/0x201`; topology and the selected CPU slot are checked separately.
Requiring the observed fields to remain zero preserves the distinction between
expectation and observation and does not weaken target identity.

## Conclusion

`production-ready-token-contract-contradiction`.

## Follow-up

On one fresh owner-selected boot2 start, capture the immutable serviceability
frame and issue at most one CPU8 trigger. Classify CPU8 online, a
request-bearing terminal result, or an exact pre-request retained stage. Do
not repeat candidate `7c962888...` or trigger candidate `a7ce2c2d...` more than
once. CPU9 remains vetoed until CPU8 is reproducibly online.
