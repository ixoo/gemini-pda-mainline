# A72 safe-off contract design

## Shared rules

Both transitions run under one cluster state lock and require a boot-local,
non-rearmable transaction. Suspend/resume must be inactive. A separately owned
policy gate must freeze policy and suspend admission, drain in-flight policy
writers, and capture the exact shared entry state without changing hardware
before notifier dispatch. The suspend interlock remains held through every
post-PSCI gate and is released only by the successful final software commit;
reset clears it on terminal failure. That owner and its readback timeouts are
currently unresolved. A broad Linux errno, policy counter, or watchdog return
is not a hardware-state oracle.

The current blocking contract recognizes only these outcomes:

- reject before CPU_OFF, with no hardware mutation;
- success after every required readback; or
- retain all shared power still present, fault the transaction, forbid retry,
  and recover by reset.

There is no CPU_ON compensation after CPU_OFF and no guessed post-isolation
inverse. The reset path is a terminal recovery action, not rollback proof.

## CPU9-off while CPU8 retains the cluster

Entry requires CPU8 and CPU9 online, a complete `members=0x3` software ledger,
one exact provider reference, and no suspend owner. The current parent does not
meet the ledger requirement.

1. Freeze the exact entry state under the cluster lock.
2. Through the unresolved policy coordinator, freeze policy and suspend
   admission, drain in-flight policy writers, and capture named entry values for DA921x page,
   BUCKB enable/VSEL, SPM reset/isolation, SRAM and secure sentinels, MP2 DCM,
   iDVFS, B/CCI clocks, and CCI admission. Do not change hardware.
3. Before generic notifier dispatch, prove that the non-last CPU9 transition
   cannot enter any cluster-off cpufreq/CPUHVFS notifier or mutate policy.
4. Before invocation, require an exact source/binary audit of the secure CPU9
   CPU_OFF handler showing a per-core-only effect set and an empty
   cluster-shared write set. Then let generic arm64 hotplug invoke standard
   PSCI CPU_OFF on CPU9 only. This audit gate is currently unresolved.
5. If CPU_OFF returns on CPU9, record a terminal fault; do not change shared
   state or membership and do not retry.
6. From the controlling CPU, poll level-0 `AFFINITY_INFO` ten times at 10 ms.
   Anything except OFF is terminal and leaves the `0x3` ledger conservative.
7. After OFF, complete one bounded CPU8 callback while conservatively retaining
   `members=0x3` and the provider reference. The callback timeout is currently
   unresolved.
8. Prove the provider reference and every named shared entry field are
   bit-exact, including DA921x page and VSEL. No shared-resource writer is
   permitted in this transaction. The owner-safe observation paths and their
   per-owner timeouts remain unresolved.
9. Only after every gate passes, atomically commit `members=0x1` and release the
   policy/suspend freeze and transition lock. CPU8 remains online and the
   provider reference remains one. Consume the boot-local transaction and keep
   CPU9 on/off admission closed until a separately owned transition exists.

The exact secure CPU9-off behavior and a live CPU9-off observation are missing,
so this is a blocking contract rather than an implementation design.

## Last-A72-off

Entry requires CPU8 online, CPU9 already affinity-OFF, `members=0x1`, one exact
provider reference, and no suspend owner. It does not assume iDVFS has already
been disabled.

1. Freeze the entry state under the cluster lock.
2. Through the unresolved policy coordinator, freeze policy and suspend
   admission, drain in-flight writers, capture the exact shared entry snapshot,
   and prove a safe last-user predicate without writing hardware.
3. Before generic notifier dispatch, require an audited last-user notifier
   path that cannot change shared hardware or lose ownership before CPU_OFF.
4. Let generic arm64 hotplug invoke standard PSCI CPU_OFF on CPU8.
5. Require level-0 `AFFINITY_INFO=OFF` within the ten-by-10-ms parent-side bound
   before any Linux shared-state teardown.
6. Independently attribute the resulting per-core/cluster power, bus
   protection, CCI-port, B-PLL/mux/divider, iDVFS, MP2 DCM, SPM reset,
   external-isolation, SRAM, and secure-sentinel states. Each field must match
   a separately audited exact offline or retained state; PLL-off is not
   assumed. The proof-order rows are attribution gates and do not claim the
   firmware/platform write order. They authorize no compensating write.
7. Only after every attribution and independent readback gate passes, release
   the final BUCKB provider reference under the legacy regulator owner and
   verify enable, VSEL, and page. Releasing the reference must not invent a
   VSEL write; a broad operation return is not a hardware-state readback.
8. Commit `members=0x0` only after the complete final snapshot is exact, then
   release the software policy/suspend/transition state. The conservative
   ledger stays at `0x1` until this final commit. Consume the boot-local
   transaction and keep A72 on/off admission closed until a separately owned
   transition exists.

Any mismatch after CPU_OFF retains whatever power remains and recovers by reset.
There is no safe same-transaction restart of CPU8 or re-enable sequence.

## Rejected vendor ordering

The chosen public-equivalent vendor source is evidence, not code to copy. Its
kill loop performs last-user iDVFS disable, clears `g_cl2_online`, and disables
DCM before the subsequent affinity query proves OFF. Its external-off helper
disables BUCKB while the SRAM-LDO disable wrapper performs no hardware disable,
and it supplies no explicit external isolation/reset inverse. The validated
contract requires affinity proof before any Linux shared teardown and keeps
the relative off-effect order, post-off accessibility, and unassigned secure,
policy, SPM, and SRAM boundaries blocked.

## Exit criteria

The contract can become implementation-eligible only when:

- the current parent has an exact CPU8/CPU9 membership and provider-reference
  ledger whose update ordering passes mutation review;
- the exact verified secure payload's CPU_OFF paths distinguish per-core
  CPU9-off from last-core teardown and assign CCI/cluster/SPM/SRAM effects;
- every required readback has an owner-safe observation path and timeout;
- policy and suspend admission have one held interlock with audited release and
  terminal-reset semantics;
- the writable legacy-provider reference/release contract is separately
  reviewed; and
- the validator can replace every blocking decision without weakening any
  failure response or the CPU9 shared-resource prohibition.

Until then, CPU_OFF, HPS-veto removal, build, deployment, and boot are forbidden.
