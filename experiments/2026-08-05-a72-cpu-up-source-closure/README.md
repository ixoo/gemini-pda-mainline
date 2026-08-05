# Experiment: A72 CPU-up source closure

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-cpu-up-source-closure` |
| Status | `completed-blocking-contract`: the source inventories and closure contract are frozen; implementation remains blocked |
| Subsystem | MT6797 late Cortex-A72 arm64 capability admission, early-secondary status, and post-CPU_ON CPUHP rollback |
| Device variant | Named Gemini PDA development unit; no live-device action |
| Date(s) | 2026-08-05 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 4 |

## Question or hypothesis

Can the remaining Linux 7.1.3 CPU-up blockers be reduced to exact,
source-attributed contracts before another kernel patch, build, or device boot?

The audit must answer three questions:

1. Can a Cortex-A72 first appear after an A53-only boot has finalized arm64
   capabilities, alternatives, mitigations, and user HWCAP state?
2. Can every early-secondary failure or timeout enter P30 without racing a late
   successful publication, CPU_OFF, affinity, or reuse of stale global startup
   state?
3. Can a post-publication CPUHP callback failure enter P32 before automatic
   rollback crosses a physical teardown boundary, while preserving every
   partial callback and architecture effect?

## Provenance and environment

The audit is pinned to official Linux 7.1.3 source SHA-256
`be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`,
canonical patchset SHA-256
`f6f7aff7e8db59520eee22c52e726d91401ab209c6dc47e87024eefd215310d1`,
and prepared source-state SHA-256
`001976aca83e752b36d76e5b8b0ba40addd741cc8e31e6c046e27b9890db2b41`.
The exact source file and patch identities are in
[`results/source-inventory.tsv`](results/source-inventory.tsv).

Reachability is pruned against the retained Buildbox package from repository
commit `e0fc95ff0686e6989fe7a38ef40d01c34f50f463`, profile
`da921x-post-event-lifecycle`, kernel release
`7.1.3-gemini-da921x-life27`, and configuration SHA-256
`f655beba038ad5d98f3af5897fb080329d45781b637ab7dcb409e8a353c54440`.
The Image and System.map identities are recorded only to bind the configuration
lineage; this experiment makes no runtime claim about that artifact.

Canonical patch 0092 remains selected with SHA-256
`cbd54d048e2233ffcb268174037248ade9ab8716f9816481d926b20b4bd3bba5`.
Its MT6797 A72 method returns `-EAGAIN` before CPU_ON, reports
`cpu_can_disable=false`, and implements no `cpu_disable`, `cpu_die`, or
`cpu_kill`. Consequently, the audited P30/P32 paths are dormant until a later
reviewed implementation changes the veto.

No kernel was built, and neither Buildbox nor the native VM backend was invoked
for a build. The table pins the prepared-source marker identity and patched-file
hashes recorded during the managed-source inventory. A complete optional
prepared-root recheck was not rerun after Buildbox became unavailable, so that
evidence remains explicitly incomplete. No source was copied to or from
Buildbox and no managed state changed. The audit made no device connection or
request. The owner's contemporaneous return from boot2 selection into a Gemian
reboot is treated
only as recovery chronology because exact candidate identity and a stopping
point were not attributable in this source-only turn.

## Safety assessment

This experiment is offline and read-only with respect to Linux source and the
device. It does not invoke an SMC, change a CPU mask, request CPU hotplug,
generate a patch, build a kernel, assemble an image, write boot2, reboot, or
shut down hardware.

These markers are normative:

```text
implementation_authorized=no
cpu_on_authorized=no
cpu_off_authorized=no
build_authorized=no
device_action_authorized=no
device_action=none
current_cpu_boot_veto=REQUIRED
```

The validator rejects raw capability-bit mutation after finalization,
late-permitted shortcuts, omission of capability-specific effects, timeout
without park acknowledgment, stale completion reuse, P30/P32 CPU_OFF or
affinity, P32 publication after rollback begins, optimistic rollback state,
generic-return success, retry, provider release, and membership commit.

## Associated code

- [`DESIGN.md`](DESIGN.md): exact A41, P30, and P32 ownership and ordering.
- [`results/source-inventory.tsv`](results/source-inventory.tsv): selected
  source composition, conclusion-bearing file, patch, configuration, and
  package identities.
- [`results/config-inventory.tsv`](results/config-inventory.tsv): selected
  Kconfig reachability inventory.
- [`results/capability-admission.tsv`](results/capability-admission.tsv): every
  currently known A53-to-A72 local-capability difference and its required
  side effects.
- [`results/early-status-contract.tsv`](results/early-status-contract.tsv):
  P30K/C/P/E/U branch closures.
- [`results/post-cpu-on-callbacks.tsv`](results/post-cpu-on-callbacks.tsv):
  exact selected fixed groups, mandatory dynamic relative order, conditional
  insertion points, and the unresolved same-boot numeric-state proof.
- [`results/p30-p32-closure.tsv`](results/p30-p32-closure.tsv): P32A/D/F/X/R
  publication, guard, retained-state, and result contracts.
- [`scripts/validate_contract.py`](scripts/validate_contract.py): portable
  schema, row identity, semantic, provenance, document, and transcript checks.
- [`scripts/test_contract.py`](scripts/test_contract.py): adversarial mutation
  suite.
- [`results/contract-validation-20260805.txt`](results/contract-validation-20260805.txt):
  frozen validation transcript.
- [`results/optional-evidence-validation-20260805.txt`](results/optional-evidence-validation-20260805.txt):
  successful official-source and selected-configuration rechecks plus rejected
  corruption probes; the managed prepared-root recheck was not rerun.

Run from the repository root:

```sh
python3 experiments/2026-08-05-a72-cpu-up-source-closure/scripts/validate_contract.py
python3 experiments/2026-08-05-a72-cpu-up-source-closure/scripts/test_contract.py
```

An optional read-only source recheck accepts the expanded official archive:

```sh
python3 experiments/2026-08-05-a72-cpu-up-source-closure/scripts/validate_contract.py \
  --source-root /path/to/linux-7.1.3
```

The selected configuration and a managed prepared tree can be checked
separately; the latter must carry the exact `.gemini-source-state` marker:

```sh
python3 experiments/2026-08-05-a72-cpu-up-source-closure/scripts/validate_contract.py \
  --config /path/to/kernel.config \
  --prepared-source-root /path/to/prepared/linux-7.1.3
```

## Procedure

1. Verify the official archive, manifest, canonical series, patch 0092, and
   retained package identities.
2. Bind the full upstream-plus-canonical-patch composition, then hash every
   conclusion-bearing arm64, CPUHP, and callback source file before inspecting
   its exact control flow.
3. Resolve the selected Kconfig values and exclude only paths that are truly
   compiled out or unregistered.
4. Enumerate every local arm64 capability that can differ between the early
   Cortex-A53 set and late Cortex-A72 targets. Record capability-specific
   mitigation, alternative, parameter, and user-HWCAP effects.
5. Enumerate all early-secondary controller statuses and the target/controller
   chronology around the shared `secondary_data` and `cpu_running` objects.
6. Enumerate selected STARTING and ONLINE CPUHP callbacks, mandatory relative
   dynamic order, every conditional insertion, each reachable failure, nested
   AP rollback, outer BP rollback, and the first architecture teardown
   boundary; leave absolute dynamic slots open without same-boot evidence.
7. Freeze A41, P30K/C/P/E/U, and P32A/D/F/X/R, including all fail-stop and
   reset-only outcomes.
8. Run the portable validator and every negative mutation. Passing freezes a
   source-only blocking contract; it authorizes no kernel or hardware action.

## Observations

### Late A72 capability admission currently cannot succeed

#### Source observations

With the selected `maxcpus=8` lineage, CPUs 0-7 are Cortex-A53. Arm64 finalizes
system capabilities, alternatives, mitigations, and user HWCAPs from that early
set. A later CPU8 or CPU9 executes `check_local_cpu_capabilities()` in
`secondary_start_kernel()`. Linux permits a late CPU to omit an optional local
erratum already enabled system-wide, but it does not permit a late CPU to
introduce a local erratum that the system did not enable.

Three compiled differences are deterministic in the exact profile:

- `ARM64_SPECTRE_BHB`: Cortex-A53 is safelisted; Cortex-A72 is affected and
  requires loop value `k=8` unless an exact stronger local mitigation applies.
- `ARM64_WORKAROUND_1742098`: every Cortex-A72 revision matches. Because
  `CONFIG_COMPAT=y`, system enablement must also remove
  `COMPAT_HWCAP2_AES` before userspace HWCAP publication.
- `ARM64_WORKAROUND_SPECULATIVE_AT`: every Cortex-A72 revision matches through
  `CONFIG_ARM64_ERRATUM_1319367=y`. Its selected functional use is KVM-only,
  but KVM being absent does not remove the capability verifier conflict.

Exact Spectre-v2 and Spectre-v4 results depend on SMCCC firmware responses that
are not pinned here. `ARM64_MISMATCHED_CACHE_TYPE`, A72 ASID width, actual
52-bit-VA selection, and exact 4-KiB granule support are also unresolved.
`CONFIG_RANDOMIZE_BASE=n` compiles out Spectre-v3a in this profile.

#### Contract inference

This is a concrete blocker, not a speculative one. Merely setting three bits
late is unsafe: BHB needs its loop/vector/alternative state, erratum 1742098
needs the compat-HWCAP fixup, and every capability must be established before
the relevant finalization points. The conditional and unresolved rows must be
pre-accounted conservatively, and configuration drift reopens the inventory.

### P30 needs a cancellation-versus-publication protocol

#### Source observations

`__cpu_up()` waits five seconds on one global completion, checks `cpu_online`,
clears one global task pointer, and reads a global status. There is no attempt
generation and the completion is not reinitialized per target. A delayed
secondary can already hold the task pointer, later publish SUCCESS and online,
and complete after the controller returns failure. Its completion can then be
mistaken for a later CPU or attempt.

The raw status paths are distinct. `cpu_die_early()` clears present, publishes
`CPU_KILL_ME`, and calls `.cpu_die`; if that callback is missing or returns, it
overwrites the status with bare `CPU_STUCK_IN_KERNEL` before parking. The panic
status reaches an unconditional panic branch. Pre-C 52-bit-VA and unsupported-
granule assembly paths write a reason into a scalar early-status cell that is
not reset per attempt.

#### Contract inference

The unknown/default timeout is not evidence that the target parked. P30U
requires a generation-bound arbitration:

- a startup object is PREPARED before dispatch, becomes ABORTED only with proof
  that no CPU_ON was issued, becomes FAULTED if that proof is missing, and
  becomes ARMED at the exact P24 CPU_ON boundary;
- a synchronous CPU_ON error or uncertainty enters ARMED-to-FAULTED and P16
  with reset-only recovery, never ordinary disarm or state reuse;
- the target wins one `ARMED -> PUBLISHING` CAS immediately before the booted
  log and first `CPU_BOOT_SUCCESS` write, then emits online, release-publishes
  PUBLISHED, and signals the exact completion; the controller requires both
  PUBLISHED and that completion even when the online bit was already visible;
- every K/C/P/E or unexpected no-fail STARTING error first wins
  `ARMED -> FAILING`, while timeout cancellation wins only
  `ARMED -> CANCELLED`; either terminal target
  release-publishes PARKED with the exact final reason and possible effect
  prefix;
- if bounded publication or PARKED acknowledgment is absent, all later CPU-up
  attempts are quarantined and the system fails stop through panic or platform
  reset.

`CPU_KILL_ME` races target `cpu_die` against controller cleanup; the final
PARKED reason must therefore be allowed to refine KILL_ME to the post-C bare-
STUCK branch. The panic branch must publish terminal state and the stuck/kexec
interlock before preserving panic. Pre-C reasoned STUCK is controller-owned
because assembly cannot touch the C ledger, but it is accepted as P30E only
with a generation-bound MMU-off-visible target/generation/cookie sentinel and
matching cache and barrier ordering; otherwise it is P30U uncertainty.

### P32 needs a guard before architecture teardown

#### Source observations

The selected post-publication callback set cannot be proven non-failing.
Kthreads, cacheinfo, CPU capacity, cpuinfo, timer migration, padata, and the
conditional pvtime, SDEI, and ITS paths have reachable or conditional error
returns. Rollback callbacks can fail too. Io-wq always reserves a dynamic state
and applies its zero-return callbacks to each live instance.

Source fixes the mandatory dynamic order as writeback, vmstat, padata, arm64
topology, io-wq, CPU capacity, cpuinfo, per-CPU counter, CPU LED, and printk.
ITS, pvtime, SDEI, or the mismatched-32-bit command-line state can insert at
specific points. This source-only experiment has no same-boot CPUHP-state
capture, so it makes no absolute `DYN+N` claim and A25 remains incomplete.

An AP callback failure first unwinds completed AP-online callbacks toward
`CPUHP_AP_ONLINE_IDLE`. The outer rollback then walks toward OFFLINE. The first
target CPU-ops boundary is `.cpu_disable`; it precedes topology/NUMA removal,
online clear, IPI teardown, and IRQ migration. Generic CPU-up returns the
original startup error while cleanup errors are warned and swallowed.

#### Contract inference

P32 must be published by the controller at the `cpuhp_up_callbacks()` error
point, before `cpuhp_reset_state()` and the outer reverse range.

An exact-token `.cpu_disable` guard can acknowledge P32 and return an error
without crossing those architecture effects. However, higher ONLINE callbacks
may already have been removed while the CPU remains online, so this is
fail-stop state, not usable retained-up success. If rollback reaches
`.cpu_die`, the target must park after `DEAD` without CPU_OFF and controller
`.cpu_kill` must wait for that acknowledgment, avoid affinity, and return
nonzero. If rollback stops earlier, P32 retains the exact partial prefix and
never invents a clean state.

The swallowed cleanup result requires an independent exact-generation P32 side
channel consumed before transaction or HPS completion.

## Analysis

The hypothesis is confirmed as a source-level closure. The work narrows the
path to CPU8 from an open-ended boot loop to three implementation obligations:

1. A41 must pre-account the complete late-A72 capability set and all of its
   side effects before finalization.
2. P30 must make timeout/status publication race-free and fail stop whenever a
   target park cannot be acknowledged.
3. P32 must publish before rollback, intercept teardown at `.cpu_disable`,
   retain die/kill defense, and preserve every partial cleanup prefix.

These obligations are finite, but none is implemented here. A successful
Linux 3.18 Gemian A72 run does not contradict the Linux 7.1.3 admission result;
the capability and CPUHP implementation under audit is different.

The strict boot-capability and ELF-HWCAP callsites are separate from the local
capability conflict. Exact GICv3 CPU-interface usability and the complete
advertised AArch64/compat HWCAP match remain explicit proof items; an earlier
dynamic or strict conflict may therefore precede the first guaranteed BHB
failure without changing the exhaustive set.

## Conclusion

`confirmed` as a completed source-only blocking contract for the exact Linux
7.1.3 source, canonical patchset, and selected configuration.

The A26 CPU-up veto remains required. No CPU_ON/CPU_OFF patch, build, candidate,
deployment, or device boot is authorized by this experiment.

## Follow-up

Follow the work ordered only in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md). Use this experiment's A41, P30, and
P32 closures as the source-review inputs while retaining the existing CPU boot
veto. This source-only result does not authorize a Buildbox build or device
cycle.
