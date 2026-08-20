# Experiment: mainline CPU8 Gate-7 admission audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-20-mainline-cpu8-gate7-admission-audit` |
| Status | `completed` offline audit; positive provider transaction is first missing implementation |
| Subsystem | MT6797 Cortex-A72 CPU8, DA921x Buck B, CPU admission and recovery |
| Device variant | Planet Gemini PDA, named development unit |
| Date(s) | 2026-08-20 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7 |

## Question or hypothesis

Does the newly completed mainline DA921x same-value write make CPU8 eligible
for a production-mainline request, and if not, what is the first missing
implementation boundary that can be advanced without another device boot?

The falsifiable claim is that the one-write result closes the exact I2C6
transport/no-op boundary but does not turn the existing A72 provider callback
from structured refusal into an owned Buck-B acquire/release transaction.

## Provenance and environment

- Repository parent: `10afe6ce0e985f4294309b3e488a819e1e02327c`.
- Kernel baseline: Linux 7.1.3 and canonical repository patch series.
- Mainline write evidence: [Gate-6 runtime result](../2026-08-20-mainline-da921x-same-value-dt-contract-repair/results/runtime-attempt-2-success-20260820.txt).
- Hardware rollback evidence: [accepted pre-isolation rollback](../2026-08-02-a72-pre-isolation-rollback-discriminator/results/runtime-2-20260802.txt).
- CPU8 startup evidence: [one-way online checkpoint](../2026-08-02-a72-one-way-cpu8-boundary/results/runtime-attempt-1-cpu8-online-20260802.txt).
- Bounded CPU8 execution evidence: [repeatability result](../2026-08-03-a72-cpu8-late-hold/results/runtime-attempt-2-repeatability-pass-20260803.txt).
- Safe-off boundary: [safe-off contract](../2026-08-05-a72-safe-off-ownership-contract/README.md).
- Current provider seam: canonical patches `0172` and `0173`.
- No compiler, Buildbox job, device endpoint, partition, regulator action, CPU
  request, reboot, or retained private artifact was used by this audit.

## Safety assessment

This audit is repository-only and read-only. It authorizes no kernel build,
boot image, boot2 write, DA921x write, rail vote, CPU8/CPU9 request, CPU_OFF,
or device action. CPU8 and CPU9 remain behind the existing A26 boot veto and
A14 disable veto.

The next implementation boundary frozen here is hardware-free: a default-off
positive provider acquire/release state machine and its exhaustive tests. A
physical Buck-B transition remains a later, separately reviewed experiment.

## Associated code

- [`contract.json`](contract.json) freezes the evidence identities, decision,
  and next implementation boundary.
- [`results/admission-matrix.tsv`](results/admission-matrix.tsv) separates
  runtime proof, portable behavior, compile-only models, and missing current
  implementation.
- [`scripts/validate.py`](scripts/validate.py) verifies exact source/evidence
  hashes, manifest separation, vetoes, refusal behavior, result markers, and
  matrix/contract consistency.
- [`results/audit-validation-20260820.txt`](results/audit-validation-20260820.txt)
  is the sanitized validation receipt.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-20-mainline-cpu8-gate7-admission-audit/scripts/validate.py
```

## Procedure

1. Pin the current manifest, canonical series, CPU-up veto, dormant provider
   and P28 patches, and decision-relevant runtime evidence by SHA-256.
2. Separate the current mainline same-value profile from the source-only A72
   provider-refusal profile.
3. Verify that the current callback still returns structured refusal for both
   acquire and release and that the MT6797 CPU method still rejects CPU8/9.
4. Reconcile the mainline write result with the older named-unit rollback,
   CPU8-online, and bounded-execution results without treating the vendor-line
   implementation as current-mainline code.
5. Classify every Gate-7 boundary as current runtime proof, portable hardware
   behavior, compile-only model, or missing implementation.
6. Select the first missing source seam that can be implemented and tested
   without hardware.

## Observations

- The current mainline runtime proves one physical one-message two-byte write
  at `0x68`, payload `[0xda, 0x46]`, with exact controller attribution,
  immediate/delayed readback, no retry, and CPU8/9 closed.
- The current `da921x-same-value-write` profile does not select the P24 owner,
  admission hooks, P30 protocol, or provider-owner callback.
- The isolated `a72-p24-provider-owner-refusal` profile selects the closed
  owner and callback seam, but patches `0172` and `0173` deliberately return
  `-EOPNOTSUPP` before any vote or mutation for acquire and release.
- The older named-unit runtime proves the relevant physical behavior exists:
  Buck B can move `0 -> 1`, settle for 1 ms with VSEL `0x46`, and return
  `1 -> 0` before external-isolation clear while the full owned prestate is
  restored. That was a Gemian-derived experiment path, not the current Linux
  7.1 provider.
- A separate older runtime proves CPU8 can reach an attributable online
  checkpoint and bounded execution. It does not supply a production Linux 7.1
  transaction owner or lift the current A26 veto.
- P28 post-provider preparation, P24/P30 admission, and capability A41 remain
  dormant or partial source models. The safe-off contract still blocks normal
  CPU_OFF. Reset-only recovery is proven as an experiment technique but has
  not yet been integrated with a current-mainline positive CPU8 transaction.

## Analysis

The Gate-6 result removes a real blocker: current mainline can deliver and
attribute the exact short write shape under the stopped-firmware transaction
window. It does not prove the two state-changing writes required by an A72
provider vote (`BUCKB_CONT 0x00 -> 0x01` and the owned inverse), nor does it
create a durable provider handle or connect the positive P24/P28/P30 path.

The historical rollback and CPU8 runtimes are valuable hardware evidence but
cannot be promoted into current implementation evidence. They support the
choice of the next seam and its exact prestate/rollback semantics; they do not
justify bypassing the current callback refusal or boot veto.

The first missing implementation is therefore the positive provider boundary,
not another CPU8 boot. It can initially remain hardware-free: replace neither
veto and expose no CPU_ON caller, but model and test an exact acquire/release
transaction behind a new default-off profile. The frozen contract requires
full-byte preflight, one root-adapter lock, zero retries, stopped-firmware
checks at every transfer edge, one 1 ms settle, exact readback, a generation-
bound handle, an owned inverse, and terminal fault-retain when an inverse
cannot be proven. `PAGE_CON`, selector values, consumers, P28, and CPU_ON stay
untouched.

## Conclusion

`rejected` for immediate CPU8 admission on current mainline. Gate 6 is complete
for one exact same-value write, while the current A72 provider acquire/release
callbacks remain structured refusal and the A26/A14 vetoes remain required.

`confirmed` for the next source boundary: implement and exhaustively validate
one default-off, positive DA921x Buck-B acquire/release state machine without a
CPU request or device action. This audit does not authorize its later physical
execution.

## Follow-up

The authoritative order and exit criteria are in
[Roadmap Gate 7](../../docs/ROADMAP.md#7-bring-up-cpu8), which records the
resulting next implementation and its gates.
