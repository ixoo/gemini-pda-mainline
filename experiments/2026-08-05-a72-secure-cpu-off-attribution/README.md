# Experiment: A72 secure CPU_OFF attribution

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-secure-cpu-off-attribution` |
| Status | `completed-offline-attribution` |
| Subsystem | MT6797 Cortex-A72 PSCI CPU_OFF and final-cluster teardown |
| Device variant | Named Gemini PDA development unit; no live-device action |
| Date(s) | 2026-08-05 UTC |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 4 |

## Question or hypothesis

Does the exact retained secure payload distinguish CPU9-off while CPU8 remains
online from the final-A72-off path, and does it assign the decision-relevant
per-core, CCI, cluster, SPM, external-isolation, DCM, and SRAM effects without
assuming that `AFFINITY_INFO` is a passive or bounded query?

## Provenance and environment

The private secure payload is identified only by SHA-256
`2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3`.
No payload bytes, raw disassembly, partition contents, image names, or private
filesystem paths are published. Addresses in the result tables use the
repository's existing AArch64 analysis-address convention, whose full-image
mapping base is `0xff3c0`.

The audit reconciles the retained payload with these committed public records:

- [`A72 firmware power-contract prerequisites`](../2026-07-22-a72-firmware-power-contract/results/a72-firmware-power-contract-prerequisites-20260722.md)
- [`External-isolation owner audit`](../2026-08-02-a72-one-way-cpu8-boundary/results/isolation-owner-audit-20260802.txt)
- [`A72 safe-off ownership contract`](../2026-08-05-a72-safe-off-ownership-contract/README.md)

The analysis used read-only AArch64 control-flow and data-flow inspection. No
kernel was built and no native or Buildbox kernel build was run.

## Safety assessment

This experiment is offline and read-only. It does not contact a device, invoke
an SMC, request CPU_OFF, change CPU masks or policy, read or write a partition,
build a kernel, package or deploy an image, reboot, or shut down hardware.

These authorization markers are normative:

```text
cpu_off_authorized=no
build_authorized=no
device_action_authorized=no
device_action=none
```

A static attribution PASS is evidence only. It does not authorize a CPU_OFF
candidate, removal of the existing CPU-disable veto, a build, deployment, or
device action.

## Associated code and evidence

- [`results/callgraph.tsv`](results/callgraph.tsv): canonical CPU_OFF and
  active-`AFFINITY_INFO` callgraph rows.
- [`results/effect-inventory.tsv`](results/effect-inventory.tsv): canonical
  decision-relevant writes, reads, branches, negative findings, and waits.
- [`scripts/validate_audit.py`](scripts/validate_audit.py): pins the evidence
  identity and every canonical result row, then checks the safety semantics.
- [`scripts/test_audit.py`](scripts/test_audit.py): mutation tests for false
  passive, bounded, query-replay, empty-write-set, CPU9-cluster, isolation,
  negative-finding, identity, and authorization claims.
- [`results/audit-validation-20260805.txt`](results/audit-validation-20260805.txt):
  generated validation transcript.

Run from the repository root:

```sh
python3 experiments/2026-08-05-a72-secure-cpu-off-attribution/scripts/validate_audit.py
python3 experiments/2026-08-05-a72-secure-cpu-off-attribution/scripts/test_audit.py
```

## Procedure

1. Verify the retained private evidence against the single published SHA-256.
2. Trace standard `psci_cpu_off` through the generic affinity-level handlers,
   platform callback, cache maintenance, and terminal WFI.
3. Trace AArch64 `AFFINITY_INFO` and determine whether it only observes state
   or actively advances deferred platform teardown.
4. Separate CPU9-off with CPU8 retained from the `big_on == 0` last-core
   branch, including replay gating and every decision-relevant shared effect.
5. Record every polling loop reachable through `power_off_big`, CCI disable,
   and `power_off_cl3`, including its tested condition and timeout status.
6. Reconcile exact secure writes with named public SPM register evidence, and
   retain negative findings for MP2 DCM and B-cluster SRAM-LDO registers.
7. Run the validator and negative-mutation suite. A PASS freezes this audit;
   it grants no implementation or hardware authorization.

## Observations

### CPU self-side path

The target CPU enters generic `psci_cpu_off`, traverses the affinity-level
state machine and the platform `affinst_off` callback, performs power-down
cache maintenance, and reaches an infinite WFI. For linear IDs greater than
7, the platform callback skips its CCI-disable and `disable_scu` block. Thus
CPU8/CPU9 cluster teardown is not performed by that callback.

### `AFFINITY_INFO` is an active transition

AArch64 `AFFINITY_INFO` resolves the target node and, when
`[target-node+0x0a].bit0` is set, calls `power_off_big` for CPU8/CPU9. It is
therefore an active deferred-teardown request, not a passive observation.
The controlling CPU can enter unbounded secure polling inside one query, so a
Linux loop of ten calls separated by 10 ms does not bound an individual SMC.

Repeated queries may re-enter `power_off_big`. Hardware replay is prevented by
the secure private `big_on & BIT(linear_id - 8)` gate: after a successful
per-core sequence clears that bit, a later call returns before per-core or
cluster hardware teardown. Query count or elapsed Linux-side delay is not the
replay-safety mechanism.

Only the intended off target may be queried within the controlled transaction.
Querying retained online CPU8 while its `big_on` bit remains set enters
`power_off_big` and can wait forever for CPU8's WFI indication; it is not a
safe way to confirm that CPU8 is ON. Querying already-off CPU9 is likewise not
an independent observer: for this exact payload it depends on the private
replay gate, so it must not be used as a second state oracle.

### CPU9-off while CPU8 remains

CPU9 waits for its WFI indication, changes only CPU9's per-core power-control
word, waits for its per-core power-status acknowledgment, and clears CPU9 in
the secure `big_on` ledger. Because CPU8 remains represented, the cluster
branch returns without changing cluster power, clock, CCI, SPM, B mux/PLL, or
external isolation.

The broader shared write set is nevertheless not empty. The path writes the
shared diagnostic command register `0x10222400` and the private secure
membership ledger. The safe contract must prohibit cluster-resource changes,
not claim that all shared or secure state is untouched.

### Final A72-off

After the last `big_on` bit clears, secure firmware withdraws CCI snoop/DVM,
runs `power_off_cl3`, applies internal bus protection and secure-handshake
ordering, changes the shared B mux/PLL controls, powers down the MP2 cluster
through SPM, and RMW-sets bit 1 at `0x10006290`. Public register evidence names
that bit `B_EXT_BUCK_ISO`; its physical writer is therefore attributed to the
secure last-core path.

**2026-08-21 correction:** bounded re-analysis of the same pinned payload,
cross-checked against the vendor CCI definitions, found that EF24 polls the
global CCI change-pending word at `0x1039000c`. The earlier
`0x1039600c` target incorrectly added the global status offset to the MP2 port
base. The adjacent MP2 control accesses remain `0x10396000`; only the status
address and its scope are corrected. The original 2026-08-05 validation
transcript remains preserved as chronology, while the validator now pins the
corrected inventory.

The audited direct last-core callgraph contains no write to MP2 DCM
`0x10222274` and no write to the B-cluster SRAM-LDO registers `0x102222b0` or
`0x102222b4`. Their final off-state writers remain outside this secure
callgraph. The symbolic meaning
of shared control register `0x1022220c`, which is ORed with `0x11` twice,
remains unresolved and is not relabeled as DCM, SRAM, or iDVFS.

## Analysis

The hypothesis is confirmed for static secure-firmware attribution. CPU9-off
with CPU8 retained has no cluster power/clock/CCI/SPM effect, but its proven
shared diagnostic/private-state write subset is nonempty. Last-A72-off owns
the CCI withdrawal, cluster bus protection, B mux/PLL changes, MP2 SPM
power-down sequence, and `B_EXT_BUCK_ISO` assertion recorded in the effect
inventory.

The audit also rejects the existing assumption that ten parent-side
`AFFINITY_INFO` polls provide a 100-ms hardware bound. Eight distinct secure
wait sites reachable in the last-core path have no counter or timeout. An
owner-safe observer therefore cannot depend on the SMC returning.

This closes only the secure callgraph attribution. It does not assign the
Linux membership/notifier ledger, policy and suspend coordinator, owner-safe
post-off readback timeouts, MP2 DCM off writer, SRAM-LDO off writer, final
regulator-provider release, or runtime failure semantics.

## Conclusion

`confirmed` for the named payload hash and published analysis addresses.
`CPU9-retained` and `last-A72` secure effects are now distinguishable, active
`AFFINITY_INFO` ownership is established, replay is attributed to the private
`big_on` gate, and `0x10006290` bit 1 is attributed to `power_off_cl3`.

No CPU_OFF candidate, build, deployment, or device action is authorized.

## Follow-up

Reconcile this evidence into the ordered Gate 4 work in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md). The existing CPU8/CPU9 CPU-disable
veto remains in force until all independently owned contract gates pass.
