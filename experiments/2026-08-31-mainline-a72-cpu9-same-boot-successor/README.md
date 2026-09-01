# Experiment: same-boot CPU9 successor after repeatable CPU8

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-31-mainline-a72-cpu9-same-boot-successor` |
| Status | `sole corrected attempt proved CPU8 terminal success and stopped before the first CPU9 ledger checkpoint` |
| Subsystem | MT6797 A72 CPU9 retained-cluster admission |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-31--2026-09-01 |
| Investigator(s) | repository owner and Codex |
| Tracking issue | `docs/ROADMAP.md` Gate 8 |

## Question or hypothesis

After the exact production path has reproducibly brought CPU8 online and
retained the cluster rail, isolation, SRAM, and DCM state, can a separate
same-boot executor admit CPU9 with one standard PSCI per-core request while
provably skipping every CPU8-only cluster acquisition and preserving fixed
watchdog recovery?

## Provenance and environment

- Exact prepared source state:
  `cd7156ab8500b033998eb6bf1e35c3afea91d02b4f3df50a41917ef49029bc5c`.
- Exact parent repository build commit:
  `aa2efd3f00f9b632a5a2c570e4319e6c987e3d90`.
- Exact parent patchset SHA-256:
  `dd0725996f2792c965c85792d62d9ae7c0b6b94d419d6a22341daf96d8e26b46`.
- Exact parent kernel: `7.1.3-gemini-a72-admission-live`.
- Exact installed parent partition SHA-256:
  `42c984ee72fe93e7f6157598dd479a9348a03d733df7948e4e4c14aa356c78ee`.
- CPU8 parent evidence: two fresh exact-candidate boots reached terminal
  membership proof; the repeat also advanced CPU8 accounting across one
  second. See the parent [attempt 2 result](../2026-08-31-mainline-a72-expected-pair-model-contract-repair/results/runtime-attempt-2-cpu8-repeat-accounting-20260831.txt).
- Build backend for future implementation: Buildbox only.

## Safety assessment

This audit is read-only. It issued no build, CPU request, device write, reboot,
retained-RAM write, or hardware operation.

The frozen successor permits one CPU9 request only after the existing CPU8
executor has durably finalized `CPU8_ONLINE_PROOF` in the same boot. CPU9 must
not reacquire or release the external provider, replay P27, clear isolation,
program SRAM-LDO, update DCM, arm or refresh the watchdog, request CPU_OFF, or
retry. A CPU9 failure retains CPU8 and the already-owned cluster state and
waits for the existing fixed recovery watchdog.

CPU9 receives a separate two-copy ledger in the already reserved second
4 KiB ramoops dmesg record at `0x44411000`. Its writer must verify the exact
DT reservation and the CRC-valid CPU8 terminal record in record 0 before its
first write. No new physical range is introduced.

## Associated code

- [`DESIGN.md`](DESIGN.md): frozen owner, sequencing, retained-evidence,
  failure, and validation contract.
- [`results/source-audit-20260831.txt`](results/source-audit-20260831.txt):
  exact source state, current callback matrix, production gaps, and selected
  boundary.
- [`results/patch-generation-20260831.txt`](results/patch-generation-20260831.txt):
  exact Buildbox generation, strict review, replay, and mutation result for
  canonical patch `0463`.
- [`results/ledger-build-kunit-20260831.txt`](results/ledger-build-kunit-20260831.txt):
  exact published-commit Buildbox package validation and the six-case,
  no-network QEMU runtime result.
- [`results/membership-patch-generation-20260831.txt`](results/membership-patch-generation-20260831.txt):
  exact post-`0463` Buildbox generation, strict review, replay, and eight
  mutation rejections for owner-local CPU9 membership patch `0464`.
- [`results/membership-kunit-attempt-1-20260831.txt`](results/membership-kunit-attempt-1-20260831.txt):
  exact Buildbox package and no-network QEMU result: 54 of 55 cases passed;
  CPU9 success finalization rejected the already-published member bit 1.
- [`results/membership-finalize-patch-generation-20260831.txt`](results/membership-finalize-patch-generation-20260831.txt):
  exact post-`0464` generation and five mutation rejections for the narrow
  pre-success/post-success member-mask repair in patch `0465`.
- [`results/membership-kunit-attempt-2-20260831.txt`](results/membership-kunit-attempt-2-20260831.txt):
  exact repaired Buildbox package and no-network QEMU result: all 55 owner,
  transition, and binder cases passed with zero failures or skips.
- [`results/executor-patch-generation-20260831.txt`](results/executor-patch-generation-20260831.txt):
  exact post-`0465` Buildbox generation, strict replay, and ten mutation
  rejections for the hardware-free retained-cluster executor in patch `0466`.
- [`results/executor-kunit-attempt-1-20260831.txt`](results/executor-kunit-attempt-1-20260831.txt):
  first exact Buildbox compile; the production executor reached compilation,
  but the KUnit file used two names for its private fixture type.
- [`results/executor-fixture-fix-generation-20260831.txt`](results/executor-fixture-fix-generation-20260831.txt):
  exact failed-source Buildbox generation, strict replay, and two mutation
  rejections for the test-only fixture repair in patch `0467`.
- [`results/executor-kunit-attempt-2-20260831.txt`](results/executor-kunit-attempt-2-20260831.txt):
  exact repaired Buildbox package and preserved no-network QEMU result: all 65
  executor, owner, transition, and binder cases passed with zero failures or
  skips.
- [`results/dispatch-patch-generation-20260831.txt`](results/dispatch-patch-generation-20260831.txt):
  exact post-`0467` Buildbox generation, deterministic replay, ten mutation
  rejections, and the explicit narrow style exception for canonical dispatch
  patch `0468`.
- [`results/dispatch-kunit-attempt-2-20260831.txt`](results/dispatch-kunit-attempt-2-20260831.txt):
  exact corrected Buildbox package and five-suite no-network QEMU result: all
  73 owner, transition, executor, CPU9 dispatch, and CPU8 regression cases
  passed with zero failures or skips.
- [`results/controller-patch-generation-20260831.txt`](results/controller-patch-generation-20260831.txt):
  exact post-`0468` Buildbox generation, strict unchanged-source style gate,
  deterministic replay, ten mutation rejections, and the rejected auto-fixed
  predecessor for canonical controller patch `0469`.
- [`results/controller-kunit-attempt-2-20260831.txt`](results/controller-kunit-attempt-2-20260831.txt):
  exact corrected Buildbox package and seven-suite no-network QEMU result: all
  91 controller, dispatch, executor, owner, transition, and CPU8 regression
  cases passed with zero failures or skips.
- [`results/production-candidate-20260831.txt`](results/production-candidate-20260831.txt):
  exact production Buildbox package, provenance-preserving DT composition,
  two byte-identical candidate constructions, 32 LK gates, and all 10 DT plus
  six container mutation rejections.
- [`results/deployment-20260831.txt`](results/deployment-20260831.txt): exact
  live-GPT target, proven predecessor, full-partition candidate readback, power
  state, and confirmed clean shutdown before the first attributable boot.
- [`results/runtime-tooling-20260831.txt`](results/runtime-tooling-20260831.txt):
  exact source pins, pristine CPU8/CPU9 pre-trigger contract, one-session
  request bounds, success and named-failure classification, and seven offline
  mutation rejections for the first attributable device attempt.
- [`results/runtime-attempt-1-profile-config-identity-blocked-20260901.txt`](results/runtime-attempt-1-profile-config-identity-blocked-20260901.txt):
  fresh exact-candidate boot, pre-trigger proof-mask `0x40000` attribution,
  zero CPU requests, unchanged recovery partition, and the exact one-file
  production-identity repair selected as patch `0470`.
- [`results/production-config-identity-repair-candidate-20260901.txt`](results/production-config-identity-repair-candidate-20260901.txt):
  exact repaired Buildbox package, two byte-identical provenance-preserving DT
  compositions, two byte-identical Android-v0 candidates, 32 LK gates, and all
  10 DT plus six container mutation rejections.
- [`results/runtime-tooling-config-identity-repair-20260901.txt`](results/runtime-tooling-config-identity-repair-20260901.txt):
  exact candidate retarget of the unchanged pristine gate, one-session request
  bounds, dual-accounting success contract, and named failure classifier.
- [`results/deployment-config-identity-repair-20260901.txt`](results/deployment-config-identity-repair-20260901.txt):
  live-GPT target resolution, exact predecessor, stable power, full-partition
  write/readback identity, unchanged trusted partitions, and confirmed shutdown.
- [`results/runtime-attempt-1-cpu8-terminal-cpu9-ledger-empty-20260901.txt`](results/runtime-attempt-1-cpu8-terminal-cpu9-ledger-empty-20260901.txt):
  sole corrected trigger, exact CPU8 terminal membership proof, exact-empty
  CPU9 lane, changed-ID recovery, and the bounded pre-ledger localization.
- `scripts/` and `templates/`: exact-source Buildbox generation, mutation
  validation, and hardware-free KUnit tooling for the independent record-1
  ledger, owner-local membership lifecycle, retained-cluster dispatch, and
  same-task controller, plus the source-pinned production DT and candidate
  construction and independent-validation chain.

Implementation patches, generators, validators, and build results will be
added here only after each logical source boundary passes deterministic
generation and hardware-free rejection tests.

## Procedure

1. Identify the exact prepared source from the parent package provenance and
   source-state hash.
2. Trace production admission, binder, transition, PSCI, membership, P30E, and
   retained-ledger callers for CPU8 and CPU9.
3. Compare those production paths with the existing generic CPU9 membership
   and P30E contracts and with the historical PSCI-only CPU9 runtime evidence.
4. Freeze a successor that leaves the CPU8 executor intact and adds a separate
   retained-cluster CPU9 state machine plus independent durable evidence.
5. Keep build, candidate, deployment, and device action closed until the
   logical patches and focused hardware-free suites pass on Buildbox.

## Observations

The membership owner already recognizes CPU9-up, requires CPU8 online and
CPU9 offline, carries forward the held provider identity, and gives CPU9 only
a CPU_ON budget. The generic P30E wire also already supports CPU9 and MPIDR
`0x201`.

Production remains intentionally CPU8-only: admission derives CPU8 only; the
public preflight, claim, begin, publish, and finalize wrappers reject CPU9;
the binder has one consumed CPU8 transition; the PSCI boot dispatch rejects
CPU9; and the retained ledger seals record 0 at CPU8 terminal proof.

Canonical patch `0463` now adds the independent CPU9 record-1 ledger. The
exact 463-patch series compiled on Buildbox from published commit `837860bc...`
and passed package checksums and provenance validation. Its isolated QEMU
profile executed exactly one six-case suite with zero failures or skips. The
runtime cases cover the full five-stage sequence, raw-header commit, missing/
partial/wrong-attempt CPU8 proof, corrupt CPU8 proof, committed/malformed CPU9
lane refusal, ordering, one-shot admission, and terminal sealing. The profile
has no production caller or physical CPU request.

The existing CPU8 transition always performs watchdog, P27, provider,
isolation, SRAM, CPU_ON, IPI, DCM, and membership stages. Generalizing that
executor for CPU9 would make forbidden cluster-effect replay reachable.
Historical named-device evidence independently shows that CPU9 can execute
through standard PSCI while CPU8 and the cluster state are retained.

Generated patch `0464` now implements the owner-local boundary without a
caller. It accepts only the exact retired CPU8 success with member bit 0, the
held provider identity, CPU8 live and CPU9 offline, and a fresh one-shot CPU9
attempt. The derived CPU9 transaction has no cluster/provider budgets and one
CPU_ON budget. Four focused owner cases cover the parent gate, parent
mutations, success finalization to members 0+1, and rejection that retains
CPU8/provider state. At generation time, Buildbox compilation and no-network
KUnit execution were still pending, so the patch was not a boot candidate.

The first exact Buildbox package subsequently compiled and passed package
validation. Its no-network QEMU run executed all 55 named cases: 54 passed and
the CPU9 success lifecycle failed only at finalization. Success publication
correctly changed membership from bit 0 to bits 0+1, but finalization reused a
parent helper that still required bit 0 exactly and returned `-EPERM`. The
other 33 owner cases, all 12 transition cases, and all 9 binder cases passed.
The next patch is therefore a narrow phase-aware membership repair; no caller,
device candidate, or physical action is justified by this failed gate.

Canonical patch `0465` makes only that phase distinction: before success the
active CPU9 transaction requires member bit 0; after success publication it
requires bits 0+1. The exact CPU8 retired parent, provider identity, budgets,
caller set, and effect set remain unchanged. Five source mutations and strict
replay validation passed. Exact published commit `322681f1...` then compiled
on Buildbox, passed package and provenance validation, and passed the exact
55-case no-network QEMU rerun with zero failures or skips. The repaired CPU9
success lifecycle now finalizes members 0+1; all 33 other owner cases, all 12
transition cases, and all 9 binder cases remain green. No physical backend,
production caller, CPU request, or device action was present.

Canonical patch `0466` now adds the distinct hardware-free executor. Its
atomic one-shot lifecycle accepts only the exact CPU8 terminal parent and a
fresh CPU9 transaction, then exposes only injected prestate, CPU_ON, online
completion, IPI, membership, checkpoint, and terminal callbacks. All failure
paths retain CPU8, its provider, and the cluster; the result surface keeps
CPU_OFF and retry counts at zero. Buildbox rejected the first generation when
one membership-callback mutation escaped the source gate and rejected the
second for strict style checks. The repaired exact-source generation rejects
all ten mutations and passes strict style and deterministic replay. It still
has no production caller, physical backend, CPU request, CPU_OFF, retry, or
cluster effect. Canonical compilation and the exact 65-case no-network KUnit
gate remain pending, so it is not a boot candidate.

The first exact Buildbox compile then rejected only the KUnit source: its
private fixture was declared as `mt6797_cpu9_executor_test_state` while test
instances used the A72-qualified name. No package or QEMU run was admitted.
Canonical patch `0467` now uses the A72-qualified private type consistently in
that test file only. Exact failed-source generation, two type-divergence
mutations, strict style, and deterministic replay pass. Production executor
source and behavior are unchanged; the Buildbox/KUnit rerun remains pending.

Exact published commit `b0750bb3...` then compiled on Buildbox and passed
package, checksum, and provenance validation. The single no-network QEMU run
executed all 65 named cases: all 10 CPU9 executor cases and all 55 prior owner,
transition, and binder regressions passed with zero failures or skips. The
first classifier invocation rejected only because it expected the binder
suite before the new executor suite; Makefile link order emitted executor then
binder. Published harness commit `d771bb17...` encoded that deterministic
order and accepted the same preserved raw log, so no runtime rerun occurred.
The profile contained no physical backend, production caller, CPU request,
MMIO, retained-RAM action, watchdog action, SMC, device action, or boot
candidate.

Canonical patch `0468` now adds the separate CPU9 production dispatch adapter.
It maps only CPU9 preflight, validation, P30E arm/readback, the single standard
PSCI CPU-on callback, generic secondary and final completion, synchronous IPI,
CPU9 membership, record-1 terminal publication, and P32 failure handoff. The
existing CPU8 binder file is unchanged. The adapter has no controller or
`add_cpu` caller, and its failure terminal performs no membership rejection or
inverse cluster action after CPU-on. The exact-source generator rejected ten
unsafe mutations and replayed the generated patch deterministically. Strict
checkpatch passed with `OPEN_ENDED_LINE` explicitly excluded because the
kernel formatter necessarily breaks the new long identifiers after an open
parenthesis; no semantic warning or error was excluded. The first exact build
then caught missing direct ledger includes in the CPU9 binder test. After that
repair, the next build passed and the first no-network QEMU run passed 72 of
73 cases; its sole failure showed that one existing owner assertion still
expected the CPU8 binder's `-EAGAIN` even though the selected CPU9 binder
correctly rejected that invalid target with `-EINVAL`. Exact regeneration made
that assertion selector-aware. Published commit `9a191eff...` then compiled
on Buildbox, passed package and provenance validation, and passed all 73 cases
across the five owner, transition, executor, CPU9 binder, and CPU8 binder
suites with zero failures or skips. The harness observed no physical backend,
CPU request, MMIO, retained-RAM write, watchdog action, SMC, or device action.
No controller or `add_cpu` caller exists, so this remains not a boot candidate.

Canonical patch `0469` now adds the candidate-only outer one-shot controller.
One live trigger first executes the unchanged CPU8 core, then requires exact
terminal CPU8 membership, retained P27/provider state, CPU8 online, and CPU9
offline before deriving, publishing, preparing, and requesting CPU9 once in
the same task. Every CPU9 failure is terminal and retains CPU8, the provider,
and the cluster; there is no CPU_OFF, retry, cluster reacquisition, or watchdog
refresh. The initial generated artifact was rejected before integration because
`checkpatch --fix-inplace` duplicated two source lines, including one that
would not compile. The generator now permits no source rewrite. Exact
generation from published commit `efdfc677...` passed strict style unchanged,
deterministic replay, and all ten mutation traps. Published build commit
`699ac9dd...` then compiled on Buildbox and passed package, checksum, and
provenance validation. A fresh no-network QEMU run executed all 91 named cases
across seven suites with zero failures or skips. The production controller was
linked but had no QEMU device node; no physical CPU request, MMIO,
retained-RAM write, watchdog action, SMC, or device action occurred. This
closes the offline controller gate but does not itself select a boot candidate.

Exact published production-profile commit `479f938f...` then compiled on
Buildbox as `7.1.3-gemini-cpu9-controller`. The package contains all five CPU9
production options plus the existing live trigger and excludes KUnit and all
CPU9 KUnit suites. Its current package provenance leaf was composed into the
unchanged exact serviceability/admission DT; two independent compositions were
byte-identical at SHA-256 `603335e6...`, and the semantic validator rejected
all ten unsafe DT mutations. Two independent Android-v0 constructions using
the unchanged serviceability ramdisk were byte-identical at raw SHA-256
`dd4b9358...` and exact-16-MiB padded SHA-256 `fb473d2f...`. Both independent
validations passed all 32 LK gates and rejected all six corrupt-container
mutations. The candidate exposes exactly one CPU8 and one CPU9 request path,
with zero requests during validation and no CPU_OFF or retry path. It is the
selected production boot candidate; no device access or hardware write was
used to establish that selection.

Known-good Gemian boot ID `591a4ade...` then resolved inactive logical `boot2`
to `/dev/mmcblk0p30` while root remained `/dev/mmcblk0p29`. Power was online,
full, and good; the full partition matched the exact proven CPU8 predecessor
`42c984ee...`. The guarded installer wrote, synchronized, flushed, and fully
read back the selected padded CPU9 candidate `fb473d2f...`; the readback
matched exactly. It made no fresh backup, touched no substitute partition,
requested no reboot, and confirmed the device unreachable after clean
shutdown. No CPU9 boot or runtime result has occurred yet.

The boot-bound runtime tooling now rejects any different candidate, release,
boot ID, non-pristine CPU8 or CPU9 state, repeated trigger, CPU_OFF, retry, or
request count above one per A72 CPU. Its single netcat session invokes the
outer controller once, records both CPU8 and CPU9 accounting across one
bounded second, and classifies success only with exact terminal proofs, CPUs
0--9 online, and advancing counters for both A72 CPUs. Synthetic validation
accepted the exact success shape and rejected all three pre-trigger plus all
four attempt mutations. This preparation used no device access or hardware
action.

The first fresh physical selection booted the exact candidate and exposed its
USB shell with fresh boot ID `ef3e1eb4...`. The candidate identity and release
matched, the controller was bound and pristine, CPUs 8--9 were offline, and
all CPU8, CPU9, CPU_OFF, and retry counts were zero. The pre-trigger gate
correctly stopped before its sysfs write because the arm64 profile recorded
one block at proof mask `0x40000`; no effect plan completed and no hardware
attempt occurred. Read-only source attribution found the production profile
still embeds config-input identity `1e7f3047...`, while the exact CPU9 package
and verified runtime leaf carry `cda6d936...`. The device was returned through
the USB shell to changed-ID Gemian, where inactive `boot2` still hashes to the
exact candidate.

Canonical patch `0470` changes only those four production identity words in
`mt6797_psci.c`; the fixture identity and every CPU, power, retry, CPU_OFF,
storage, and device path are unchanged. Its parent and replacement Git blobs,
full-file hashes, and the package-derived identity are exact, and the
164-profile canonical-series audit plus all eight invariant mutations pass.
Exact published commit `45582eea...` then compiled on Buildbox with the
intended configuration-input identity. Two independent DT compositions were
byte-identical at `ca7e9516...`; two independent Android-v0 constructions
were byte-identical at raw `e7ea9113...` and padded `11809635...`. Both
candidate validators passed all 32 LK gates, ten DT mutations, and six
container mutations. Known-good Gemian resolved inactive `boot2`, proved the
exact predecessor, wrote and fully read back `11809635...`, preserved both
trusted-environment partitions, and shut down cleanly without a fresh backup
or reboot.

The corrected candidate then passed the fresh source-pinned pre-trigger gate
on boot ID `1958698a...`: exact installed identity and release, one completed
effect plan, bound pristine controller, CPUs 0--7 online, CPUs 8--9 offline,
and zero requests, CPU_OFF operations, or retries. The sole trigger commit was
observed, but its sysfs write never returned before USB disappeared and
changed-ID Gemian returned 91 seconds later. The live transcript therefore
classified only transport-boundary loss and was not repeated.

Recovery supplied the decision-changing evidence. Ramoops record 0 contained
two CRC-valid copies for attempt 1: generation 20 was `AFTER MEMBERSHIP`, and
generation 21 was terminal stage 10, terminal 5
`CPU8_ONLINE_PROOF`. A separate bounded read-only Gemian `/dev/mem` check
confirmed record 1 at `0x44411000` and the spare record at `0x44412000` both
retained exact logical-empty `DBGC/0/0` headers. CPU8 therefore completed, but
the CPU9 executor did not reach its first `BEFORE PRESTATE` ledger checkpoint
and could not have issued its ordered physical CPU_ON request. The current
evidence cannot distinguish the CPU8-proof, ready-token, derive, publish,
prepare, `add_cpu(9)` entry, and record-1 begin boundaries.

Canonical patches `0471` and `0472` now add and wire the independent record-2
progress owner across those exact boundaries. The first exact Buildbox build
found only omitted public phase and module-metadata includes; compile-only
follow-up `0473` supplies them without changing the retained wire or runtime
order. Published commit `90972eac...` then compiled and passed package,
checksum, and provenance validation. Its single no-network QEMU run passed all
97 cases across eight suites with zero failures or skips, including all four
progress-owner cases and both CPU8/CPU9 controller failure matrices. No
physical CPU request, MMIO, retained-RAM write, watchdog action, SMC, or device
action occurred. A separate production profile now selects this diagnostic
while disabling the overlapping legacy admission trace; it is not a selected
boot candidate until its exact package and container validations pass.

Exact published build commit `63035018...` completed that production gate.
Two independent provenance/serviceability DT compositions were byte-identical
at `08ccef4f...`; their independent validator preserved the serviceability,
controller, binder, and exact package provenance contracts and rejected all
ten negative DT mutations. Two independent Android-v0 constructions were
byte-identical at raw `85d3b591...` and padded `ce154daf...`. Both independent
candidate validations passed all 32 LK gates and all six negative container
mutations. The source-pinned recovery classifier additionally accepted the
valid record-2/record-1 relationships and rejected twelve malformed or
cross-lane-inconsistent cases. This exact progress-ledger image is therefore
the selected boot candidate; no device access or hardware write was used to
establish that selection.

Known-good Gemian then resolved inactive logical `boot2` to
`/dev/mmcblk0p30` while root remained `/dev/mmcblk0p29`. Power was online,
full, and good, and the full predecessor matched the exact configuration-
repair candidate `11809635...`. The guarded installer wrote, synchronized,
flushed, and fully read back the selected progress candidate `ce154daf...`;
the readback matched exactly and both trusted-environment partition hashes
remained unchanged. It made no fresh backup, used no substitute partition,
requested no reboot, and confirmed the device unreachable after clean
shutdown. The selected progress candidate has not been booted yet.

The first fresh selection booted that exact progress candidate on boot ID
`23135ff2...` and passed the complete read-only gate with CPUs 8--9 offline
and every trigger, CPU request, CPU_OFF, and retry count at zero. Its sole
trigger returned a complete terminal frame: CPU8 reached exact terminal stage
10/terminal 5 and remained online, while progress begin returned `-EBADMSG` at
stage 1 before any CPU9 request, binder entry, CPU9 ledger write, or membership
publication. No retry, CPU_OFF, or native reboot was requested. The device
later returned automatically to changed-ID Gemian.

Recovery decoded record 0 as the same CRC-valid CPU8 attempt 1 terminal and
found records 1--3 logically empty. This proves that CPU8's durable record was
valid after reboot and that neither the progress owner nor CPU9 owner committed
a record. The first unresolved operation is the immediate CPU8-record read in
progress begin. Both progress begin and CPU9 ledger begin reopen the CPU8 slot
with `ioremap()`, while the CPU8 owner writes it through `ioremap_wc()` and the
adjacent retained lanes also use `ioremap_wc()`. Canonical follow-up `0475`
therefore changes only those two CPU8 readers to the writer's mapping type;
wire formats, gates, request bounds, and failure behavior remain unchanged.

Exact published commit `6f72e3dd...` then passed Buildbox compile and package
validation for both the full CPU9 KUnit profile and the production progress
profile. The no-network KUnit run passed all 97 cases across eight suites with
zero failures or skips and no physical CPU request, retained-RAM access, MMIO,
watchdog, SMC, or device action. The production configuration-input identity
remained exactly `c10a2188...`, matching the identity already bound by `0474`,
so no additional identity patch was required. Two independent package-exact
DT compositions were byte-identical at `f999758e...` and rejected all ten
unsafe mutations. Two independent Android-v0 constructions were byte-identical
at raw `a7290cdb...` and padded `c531a9e0...`; both independent validations
passed all 32 LK gates and rejected all six corrupt-container mutations. This
is the selected one-shot reader-mapping successor; selection required no
device access or hardware write.

## Analysis

The current generic owner and P30E layers contain useful CPU9 primitives, but
they are not a production CPU9 path. The narrow safe integration is a distinct
second-stage executor that consumes the post-CPU8 owner state and implements
only prestate, CPU_ON/P30E, online completion, IPI, and membership proof.

Because record 0 is deliberately sealed after CPU8 success, reopening it would
weaken the proven CPU8 evidence contract. The next existing ramoops record is
an independent, recoverable evidence lane and lets CPU9 fail closed unless the
CPU8 terminal is already CRC-valid.

## Conclusion

`confirmed`: on the exact parent source, CPU9 must be a separate same-boot,
retained-cluster PSCI executor. Reusing the CPU8 transition or merely widening
its CPU checks is rejected because it exposes repeated cluster acquisition.
The guarded independent retained ledger and owner-local CPU9 derivation/
membership lifecycle are canonical, compiled, and runtime-tested. The third
logical layer—the hardware-free retained-cluster executor plus its test-only
fixture repair—is now canonical, compiled, and runtime-tested. The fourth
logical layer—the isolated CPU9 dispatch binder—is now canonical, compiled,
and runtime-tested across the full 73-case offline regression profile. The
fifth logical layer—the exact same-task CPU8-to-CPU9 controller—is now
canonical, compiled, and runtime-tested across the full 91-case offline
regression profile. The detailed device evidence contract is frozen in
[`DESIGN.md`](DESIGN.md). The progress production candidate is independently
reproducible. Its sole device attempt again proved CPU8 terminal membership and
now places the CPU9 stop at progress begin stage 1, before any CPU9 request.
CPU9 was not durably admitted and no CPU9-online result is claimed.

## Follow-up

The exact progress candidate is retired after its one decision-bearing
attempt. Its mapping-consistency successor passed every offline gate and is
selected. The next action is a guarded write to inactive logical `boot2`, clean
shutdown, and one fresh selection. Success requires exact CPU8 terminal proof
followed by progress stage 2 or later or an attributable CPU9 ledger entry;
another stage-1 `-EBADMSG` rejects the mapping hypothesis. The ordered device
action and its exit criteria remain owned by
[Roadmap gate 8](../../docs/ROADMAP.md#8-validate-cpu9-and-the-complete-cluster).
CPU_OFF, retry, sustained load, hotplug, thermal, and suspend remain outside
this diagnostic.
