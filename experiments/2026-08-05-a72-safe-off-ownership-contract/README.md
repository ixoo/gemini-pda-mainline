# Experiment: A72 safe-off ownership contract

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-safe-off-ownership-contract` |
| Status | `completed-blocking-contract`: exact secure source attribution is reconciled, but both CPU9-off and last-A72-off remain blocked |
| Subsystem | MT6797 Cortex-A72 CPU_OFF, active affinity teardown, membership, shared power, and rollback ownership |
| Device variant | Named Gemini PDA development unit |
| Date(s) | 2026-08-05 UTC (2026-08-04 America/New_York) |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 4 |

## Question or hypothesis

Do the retained source, exact private-firmware attribution, runtime records,
and ownership audits now assign enough ownership to implement either CPU9-off
while CPU8 remains online or the final A72-off transaction?

The two transitions remain separate. CPU9-off may change only CPU9's per-core
power word, the exact diagnostic command, and firmware-private membership; it
must leave cluster power, clocks, CCI, shared SPM state, and the provider
unchanged. Last-A72-off has a larger exact secure effect set, but Linux/provider
release still cannot begin until the state-changing secure call returns and
independent observers attribute its result.

## Provenance and environment

- Original contract evidence base: commit
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
- Exact secure attribution:
  [`2026-08-05-a72-secure-cpu-off-attribution`](../2026-08-05-a72-secure-cpu-off-attribution/README.md).
  It publishes only sanitized derived results for private payload SHA-256
  `2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3`.
  Its effect inventory SHA-256 is
  `deaa6686582e6e3f2e3453ff626f14b2ec555d9be468ac2f67fb350e6eead8bc`,
  and its validation transcript SHA-256 is
  `6da8ad1883362b32fe7b8e2332f262ec8ebf195db09c91872a0ce59eda429af6`.
- Chosen public observer-equivalent source: Gemian commit
  [`59e00a9144d782e148332009a835b99c43382467`](https://github.com/gemian/gemini-linux-kernel-3.18/tree/59e00a9144d782e148332009a835b99c43382467).
  Its `arch/arm64/kernel/psci.c` SHA-256 is
  `a1d5367bb23c4838deb862d01fc9f2aaabd854a8695f906191713f2398fdd11b`.
  It remains observer-equivalent, not the unresolved exact active Gemian
  source revision.

No kernel was built. No native VM or Buildbox kernel build was run.

## Safety assessment

This experiment is offline and read-only. It reads committed text and
sanitized derived source-attribution records only. It does not access the
device, invoke an SMC, request a CPU, change a CPU mask, read or write a
partition, build a kernel, deploy an image, or reboot anything.

Validation fails if `AFFINITY_INFO` is treated as passive, if an outer polling
loop is claimed to bound an unbounded inner secure wait, if query count is
substituted for the private `big_on` hardware replay gate, if a retained/non-
target CPU is queried, if CPU9 gains a cluster-resource effect, if last-core
isolation is omitted, or if any unresolved owner is promoted. The existing
CPU8/CPU9 CPU-disable veto remains mandatory.

## Associated code

- [`DESIGN.md`](DESIGN.md): two-case state machine and evidence boundary.
- [`results/safe-off-contract.tsv`](results/safe-off-contract.tsv): exact
  owner, pre-state, readback, timeout, inverse, failure response, and decision
  for each transition boundary.
- [`results/evidence-reconciliation.tsv`](results/evidence-reconciliation.tsv):
  current disposition of the historical Gate 4 rows.
- [`scripts/validate_contract.py`](scripts/validate_contract.py): validates
  schema, evidence identities, active-query semantics, ordering, fail-closed
  responses, and the continued blocked decision.
- [`scripts/test_contract.py`](scripts/test_contract.py): rejects safety,
  ordering, ownership, timeout, query, effect-set, reconciliation, and
  authorization mutations.
- [`results/contract-validation-20260805.txt`](results/contract-validation-20260805.txt):
  exact validation outcome.

Run from the repository root:

```sh
python3 experiments/2026-08-05-a72-safe-off-ownership-contract/scripts/validate_contract.py
python3 experiments/2026-08-05-a72-safe-off-ownership-contract/scripts/test_contract.py
```

## Procedure

1. Pin the historical matrix, every decision-changing runtime/source record,
   and the sanitized exact secure effect inventory by SHA-256.
2. Reconcile all 19 historical rows without promoting static attribution to
   runtime completion or failure safety.
3. Model CPU9-off with CPU8 retained independently from last-A72-off, and keep
   Linux `members` separate from firmware-private `big_on`.
4. Split target CPU_OFF from controlling-CPU `AFFINITY_INFO`: the former ends
   in target WFI without A72 MTCMOS teardown; the latter calls
   `power_off_big` and performs the physical transition.
5. Assign an owner, required pre-state, success evidence, timeout, inverse, and
   failure response at every boundary. Preserve unresolved private-ledger,
   policy, notifier, observer, SRAM, DCM, provider, and timeout owners.
6. Reject an unchanged ten-by-10-ms polling bound because one secure query can
   remain inside unbounded waits. Do not re-query a retained or already-off
   non-target CPU.
7. Run the validator and negative-mutation suite. A PASS freezes the blocking
   contract only; it never authorizes CPU_OFF.

## Observations and source findings

- **Source finding:** Target-side CPU_OFF preparation, GIC deactivation, cache
  maintenance, and terminal WFI are exact. For CPU8/CPU9, the target callback
  skips its CCI/SCU block and performs no A72 MTCMOS teardown.
- **Source finding:** AArch64 `AFFINITY_INFO` is active. When the target-node
  gate is set, it calls `power_off_big`; eight reachable secure wait sites in
  the last-core path have no counter or timeout.
- **Source finding:** Hardware replay is controlled by the target bit in
  firmware-private `big_on`, not Linux query count. The source defines the
  transition but does not provide Linux an owner-safe private-ledger readback.
- **Source finding:** CPU9 teardown writes `0x0000001b` to diagnostic register
  `0x10222400`, reads `0x10222404` twice, clears bits 2 then 0 in CPU9
  `PWR_CON` `0x10006244`, and clears private `big_on` from `0x3` to `0x1`.
  It returns before cluster power, clock, CCI, shared-SPM, or provider writes.
- **Source finding:** Last-CPU8 teardown clears the equivalent CPU8
  `PWR_CON`, takes private `big_on` to zero, withdraws CCI snoop/DVM, applies
  the cluster-snoop and internal-bus-protection sequence, changes the B mux and
  B PLL, updates `0x10006218`, and applies `0x10006290 |= 0x2`.
- **Negative source finding:** The audited direct last-core callgraph contains
  no direct write to MP2 DCM `0x10222274` or SRAM-LDO
  `0x102222b0`/`0x102222b4`. It does not identify those final-state writers.
  The meaning of `0x1022220c |= 0x11` remains unresolved.
- **Observation:** The natural CPU8-as-last record still supplies the named
  final runtime state and OFF result, but not a bound on the secure call,
  owner-safe failure semantics, or a CPU9-off runtime result.
- **Source/runtime finding:** Generic CPU-down notifier dispatch still precedes
  the late platform veto. The retained child already faulted in the policy
  notifier before that veto, so source attribution does not close notifier or
  policy admission.

## Analysis

The hypothesis remains rejected for an implementation. Exact secure source
attribution closes C04 and L04: their target CPU_OFF paths are defined and do
not perform A72 MTCMOS teardown. C05 and L05 are not passive affinity
observations; they are state-changing `AFFINITY_INFO -> power_off_big`
transactions with unbounded inner waits, so both are explicit timeout
blockers.

CPU9-off remains blocked by the Linux/private membership proof, policy and
suspend admission, notifier path, unbounded secure call, owner-safe retained-
CPU8 callback, independent resource invariance, and absent CPU9-off runtime.
The static empty cluster-resource effect set cannot replace C07's independent
readbacks, and querying CPU8 for confirmation would itself be unsafe.

Last-A72-off additionally remains blocked by policy/DCM ownership, the missing
SRAM writer, owner-safe post-call observation timeouts, writable provider
release, and failure semantics. The exact secure source attribution for SPM
reset and external isolation does not supply a same-transaction inverse.

After either target enters CPU_OFF, there is no defensible in-transaction
inverse. A returned target call, a controlling query that does not return, a
mismatch, or failed independent readback must retain all still-powered shared
state, prohibit retry, and use the established reset recovery path. Reset is
recovery, not proof that the incomplete off transaction was safe.

## Conclusion

`rejected` for implementable CPU_OFF from current evidence. Two source-only
target paths are contract-defined; the other 20 boundaries remain blocking.
Both transitions and Gate 4 remain blocked. No CPU_OFF candidate, HPS-veto
removal, kernel build, deployment, or device action is authorized.

## Follow-up

Continue only through the ordered Gate 4 action in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md). Keep the existing A72 CPU-disable
veto until the independent Linux/private membership, notifier,
policy/suspend, secure-timeout, observer, SRAM/DCM, and provider gaps change
the contract with separately reviewed evidence.
