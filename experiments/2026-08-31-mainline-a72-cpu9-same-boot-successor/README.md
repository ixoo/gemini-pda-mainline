# Experiment: same-boot CPU9 successor after repeatable CPU8

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-31-mainline-a72-cpu9-same-boot-successor` |
| Status | `CPU9 finalization defect isolated; narrow repair generated, rebuild pending` |
| Subsystem | MT6797 A72 CPU9 retained-cluster admission |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-31 |
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
- `scripts/` and `templates/`: exact-source Buildbox generation, mutation
  validation, and hardware-free KUnit tooling for the independent record-1
  ledger. Canonical patch `0463` adds the ledger but deliberately has no
  production caller and does not enable CPU9.

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

Generated patch `0465` makes only that phase distinction: before success the
active CPU9 transaction requires member bit 0; after success publication it
requires bits 0+1. The exact CPU8 retired parent, provider identity, budgets,
caller set, and effect set remain unchanged. Five source mutations and strict
replay validation pass; Buildbox compilation and the exact 55-case rerun are
pending.

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
The first logical layer, the guarded independent retained ledger, is now
canonical, compiled, and runtime-tested. The detailed remaining implementation
and evidence contract is frozen in [`DESIGN.md`](DESIGN.md); no CPU9 support or
device result is claimed yet.

## Follow-up

Implement owner-local CPU9 derivation and CPU9-specific membership lifecycle
entry points next, with focused no-network tests. Then add the retained-cluster
executor, bind P30E/PSCI/completion dispatch, and chain the candidate-only
controller before candidate validation and one predeclared device attempt.
CPU_OFF, retry, sustained load, hotplug, thermal, and suspend remain outside
that first CPU9 attempt.
