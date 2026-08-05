# Experiment: A72 safe-off ownership contract

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-safe-off-ownership-contract` |
| Status | `completed-blocking-contract`: the offline contract validates, but both CPU9-off and last-A72-off remain blocked |
| Subsystem | MT6797 Cortex-A72 CPU_OFF, cluster membership, shared power, and rollback ownership |
| Device variant | Named Gemini PDA development unit |
| Date(s) | 2026-08-05 UTC (2026-08-04 America/New_York) |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 4 |

## Question or hypothesis

Do the retained source, binary-audit, firmware-analysis, and runtime records now
assign enough ownership to implement either CPU9-off while CPU8 remains online
or the final A72-off transaction without guessing a shared-power inverse?

The two transitions are intentionally separate. CPU9-off must leave every
cluster-shared resource and its provider reference unchanged. On last-A72-off,
Linux/provider teardown or release may begin only after the target is
conclusively off; secure effects that may occur inside CPU_OFF must instead be
attributed by exact post-OFF observations without assuming their internal
order.

## Provenance and environment

- Repository evidence base: commit
  `5ccc88984786c2c72fcc92dbf19eae02f4791667`.
- Historical Gate 4 matrix SHA-256:
  `5b483482f9727b3648b15df1b5a4e92ca513c6413a0e64380cd3419ff7d4e6a8`.
- Accepted pre-isolation rollback result SHA-256:
  `1295291982ae539681fc817cebc894a6f7abb13484f000500e542caa861adaa4`.
- Natural CPU8-as-last pair SHA-256:
  `6db6ea41ba4689541cb504a0486c0a1b7249834ebdb8613f0e73b0bf56e808f5`.
- CPU9 retained-execution repeat result SHA-256:
  `a90f82f514b1853be6feae1a4751e46bce00aa5b6fa1ae3a194f15b88eb999ac`.
- Scheduler-context repeat result SHA-256:
  `6c0966228bb50fcc715c6734ce6e1804507743a820e07ce3e157d46e75fbf26c`.
- CPU-down notifier source-order audit SHA-256:
  `ce530fb74fe520d1899f94f64a2c4e2a0029699cb6dd91f7eaccb6d5f5e01a34`.
- External-isolation owner audit SHA-256:
  `9f3bc3463f9785d4eb94bd3e0a7f6ad8e3e83069b1b77ec2fe182d5cd55021e0`.
- Firmware power-contract prerequisites SHA-256:
  `0ce33cb344876363b9c35e3c12e9adef9fc4357071cc3d35f667da9d76b6cd97`.
- Exact active boot binary audit SHA-256:
  `c550de24db711c26b2426d061fcfba713de51b8b32c9959754e12fdbfef7c83a`.
- Active-kernel source reconciliation SHA-256:
  `709ae67b0e89c45828096837d6faee4f6f4e3b81e031c94ab6fd8d0b7b10577c`.
- CPU9 retained-cluster startup patch SHA-256:
  `4d72f15e739b788c32397927c03f52e6c6adde15c65008dd686ca50f62ce0a76`.
- One-way CPU8 startup and CPU_OFF-veto patch SHA-256:
  `d901475205f21494d9b64aaffe35a569fdb4f9f491289b3e3bd03e97b339a2ca`.
- Chosen public observer-equivalent source: Gemian commit
  [`59e00a9144d782e148332009a835b99c43382467`](https://github.com/gemian/gemini-linux-kernel-3.18/tree/59e00a9144d782e148332009a835b99c43382467).
  Its `arch/arm64/kernel/psci.c` SHA-256 is
  `a1d5367bb23c4838deb862d01fc9f2aaabd854a8695f906191713f2398fdd11b`.
  This is not promoted to the unresolved exact active Gemian source revision.
- The exact active boot binary audit confirms the forward call sites, but does
  not contain an exact CPU_OFF/secure-cluster teardown audit. The pinned source
  reconciliation keeps the public observer-equivalent revision distinct from
  the unresolved exact active source revision.
- Contract validator runtime: Python 3.14.6.

No kernel was built. No native VM kernel build was run.

## Safety assessment

This experiment is offline and read-only. It reads committed text and source
records only. It does not access the device, invoke an SMC, request a CPU,
change a CPU mask, read or write a partition, build a kernel, deploy an image,
or reboot anything.

Validation must fail if an unresolved owner is promoted, if CPU9-off changes a
shared resource or provider reference, if a Linux/provider teardown or release
gate precedes an OFF affinity result, or if a post-PSCI ambiguity is assigned a
guessed inverse. The existing CPU8/CPU9 CPU-disable veto remains mandatory.

## Associated code

- [`DESIGN.md`](DESIGN.md): two-case state machine and evidence boundary.
- [`results/safe-off-contract.tsv`](results/safe-off-contract.tsv): exact
  owner, pre-state, readback, timeout, inverse, failure response, and decision
  for each transition boundary.
- [`results/evidence-reconciliation.tsv`](results/evidence-reconciliation.tsv):
  current disposition of the historical Gate 4 rows changed or clarified by
  later evidence.
- [`scripts/validate_contract.py`](scripts/validate_contract.py): validates
  schema, evidence identities, ordering, fail-closed responses, and the
  continued blocked decision.
- [`scripts/test_contract.py`](scripts/test_contract.py): rejects safety,
  ordering, ownership, reconciliation, and authorization mutations.
- [`results/contract-validation-20260805.txt`](results/contract-validation-20260805.txt):
  exact validation outcome.

Run from the repository root:

```sh
python3 experiments/2026-08-05-a72-safe-off-ownership-contract/scripts/validate_contract.py
python3 experiments/2026-08-05-a72-safe-off-ownership-contract/scripts/test_contract.py
```

## Procedure

1. Pin the historical ownership matrix and every later decision-changing
   runtime/source record by SHA-256.
2. Reconcile all 19 historical rows against the accepted pre-isolation
   rollback and later CPU9 startup/execution evidence; leave historical
   chronology in its original experiments.
3. Model CPU9-off with CPU8 retained independently from last-A72-off.
4. Assign an owner, required pre-state, success readback, timeout, inverse, and
   failure response at every boundary. Preserve explicit unresolved owners and
   timeouts.
   `proof_order` is the order in which gates must be satisfied; the blocked
   post-affinity attribution rows do not assert an unobserved firmware or
   platform write order and authorize no write.
5. Reject the vendor kill ordering as an implementation template: it mutates
   iDVFS membership/DCM before `AFFINITY_INFO` proves the target OFF.
6. Run the validator and negative-mutation suite. A validation PASS freezes the
   blocking contract only; it never authorizes CPU_OFF.

## Observations and source findings

- **Observation:** The accepted pre-isolation discriminator closes the
  attempt-owned BUCKB, SPM-reset, and PWRAP-reset unwind before external
  isolation. It does not supply an inverse after isolation clear.
- **Observation:** Later CPU9 evidence closes startup and bounded retained
  execution, not CPU9-off. No retained runtime record exercises CPU9-off.
- **Source finding:** The current experiment parent publishes CPU8 in
  `g_cl2_online` but does not publish a complete `0x3` CPU8/CPU9 membership
  state after CPU9 completion.
- **Source/runtime finding:** Generic CPU-down notifier dispatch precedes the
  platform CPU-disable callback. The retained one-way child already faulted in
  `cpuhvfs_notify_cluster_off` before the late platform veto.
- **Source finding:** The public-equivalent vendor kill loop disables last-user
  iDVFS, clears the cluster membership bit, and may disable MP2 DCM before its
  bounded `AFFINITY_INFO` loop establishes OFF. Its external-off helper then
  disables BUCKB and calls an SRAM-LDO disable wrapper whose hardware action is
  absent.
- **Observation:** The natural CPU8-as-last record proves one successful final
  state, including offline affinity, DCM zero, restored SPM reset/isolation,
  secure zero state, and BUCKB off. It does not attribute the secure CPU_OFF
  branch, CCI/cluster teardown, restored SPM/SRAM writers, or failure
  semantics.

## Analysis

The hypothesis is rejected. The evidence is sufficient to freeze what a safe
implementation must prove, but not to select an implementation. CPU9-off is
blocked by the incomplete membership ledger, the unaudited secure CPU9-off
branch, the unresolved policy/suspend admission coordinator, and absent
CPU9-off runtime evidence. Last-A72-off is additionally blocked by unattributed
secure cluster/CCI teardown, unresolved restored SPM/SRAM writers, and the
missing writable legacy-provider reference contract.

The incomplete software membership ledger cannot safely select a last user.
The notifier ordering requires a pre-dispatch per-core-versus-last-user policy
contract. CPU9-off is structurally narrower than final A72-off: after the
per-core request and exact affinity result, every captured cluster-shared
resource must match its entry snapshot while CPU8 remains responsive.

After either PSCI CPU_OFF request, there is no defensible in-transaction
inverse. A returned call, affinity timeout, ownership mismatch, or failed
readback must retain all still-powered shared state, prohibit retry, and use
the already established reset recovery path. Reset is recovery, not evidence
that the incomplete off transaction was safe.

## Conclusion

`rejected` for implementable CPU_OFF from current evidence. The machine-checked
contract passes and deliberately reports both transitions and Gate 4 blocked.
No CPU_OFF candidate, HPS-veto removal, kernel build, or device boot is
authorized by this result.

## Follow-up

Continue only through the ordered Gate 4 action in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md). Keep the existing A72 CPU-disable
veto until that action changes the contract with independently reviewed
evidence.
