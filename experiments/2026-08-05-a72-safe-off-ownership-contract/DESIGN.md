# A72 safe-off contract design

## Shared rules

The contract distinguishes two membership ledgers. Unqualified `members` is
the Linux A72 state-machine ledger. `firmware-private-big_on` is private secure
state in the verified payload. Evidence for one never substitutes for evidence
for the other.

Both transitions run under one cluster state lock and require a boot-local,
non-rearmable transaction. Suspend/resume must be inactive. A separately owned
policy gate must freeze policy and suspend admission, drain in-flight policy
writers, and capture the exact shared entry state without changing hardware
before notifier dispatch. The suspend interlock remains held through every
post-PSCI gate and is released only by the successful final software commit;
reset clears it on terminal failure. That owner and its readback timeouts
remain unresolved. A broad Linux errno, policy counter, watchdog return, or
outer polling loop is not a hardware-state oracle.

The exact secure-source audit changes the meaning of the PSCI sequence. The
target CPU's CPU_OFF call performs source-closed preparation, GIC CPU-interface
deactivation, cache maintenance, and WFI entry. It does not tear down A72
MTCMOS. The controlling CPU's later `AFFINITY_INFO` call enters
`power_off_big`, performs the physical teardown, and only then can return the
affinity result. Several inner waits have no bound. A nominal outer ten-by-
10-ms poll cannot bound a first query that does not return. A later query can
re-enter `power_off_big`, but after successful teardown the cleared private
`big_on` target bit returns before per-core or cluster hardware effects. That
private bit, not query count, is the hardware replay gate. The Linux contract
still permits only one controlling query attempt because Linux lacks an owner-
safe `big_on` observation and cannot recover from an in-flight SMC that hangs.

The current blocking contract recognizes only these outcomes:

- reject before CPU_OFF, with no hardware mutation;
- success after the one state-changing affinity query and every independent
  required readback; or
- retain all shared power still present, fault the transaction, forbid another
  query or CPU retry after the fault, and recover by reset.

There is no CPU_ON compensation after CPU_OFF and no guessed post-isolation
inverse. The reset path is a terminal recovery action, not rollback proof.

## CPU9-off while CPU8 retains the cluster

Entry requires CPU8 and CPU9 online, a complete Linux `members=0x3` ledger,
owner-safe proof that firmware-private `big_on` selects the `0x3` retained-
cluster branch, one exact provider reference, and no suspend owner. The source
audit establishes branch semantics but does not give Linux an owner-safe
private-ledger readback. Both that proof and the Linux ledger remain open.

1. Freeze the exact entry state under the cluster lock.
2. Through the unresolved policy coordinator, freeze policy and suspend
   admission, drain in-flight policy writers, and capture named entry values
   for the DA921x page, BUCKB enable/VSEL, SPM reset/isolation, SRAM and secure
   sentinels, MP2 DCM, iDVFS, B/CCI clocks, and CCI admission. Separately close
   the currently unresolved owner-safe private-`big_on` entry proof. Do not
   change hardware.
3. Before generic notifier dispatch, prove that the non-last CPU9 transition
   cannot enter any cluster-off cpufreq/CPUHVFS notifier or mutate policy.
4. Let generic arm64 hotplug invoke standard PSCI CPU_OFF on CPU9. The exact
   secure path prepares the target, deactivates its GIC CPU interface,
   performs cache maintenance, and enters WFI. It performs no A72 MTCMOS,
   cluster-power, clock, CCI, SPM, or provider teardown. A returned target call
   is terminal.
5. From the controlling CPU, issue one level-0 `AFFINITY_INFO` attempt for CPU9.
   That query actively enters `power_off_big`: it applies the exact CPU9
   per-core `PWR_CON` sequence at `0x10006244`, writes `0x0000001b` to the
   diagnostic command at `0x10222400`, reads `0x10222404` twice, and updates
   private `big_on` from `0x3` to `0x1`. Its cluster-power, clock, CCI, shared-
   SPM, and provider effect sets are empty. These diagnostic/private-ledger
   effects are not Linux membership or cluster-resource invariance fields.
6. The CPU9 path reaches two inner secure waits, and both are unbounded, so no
   complete query timeout is established. Do not issue another query after a
   fault. A non-return or any result other than OFF is terminal and leaves
   Linux `members=0x3` conservative. Do not
   query retained CPU8: in this payload an AFFINITY_INFO request for CPU8 can
   itself enter `power_off_big`, wait for CPU8 WFI, and tear it down or hang.
7. After the single query returns OFF, complete one bounded CPU8 callback while
   conservatively retaining Linux `members=0x3` and the provider reference.
   This owner-safe non-PSCI callback is the retained-CPU8 proof. Its timeout
   remains unresolved.
8. Independently prove the provider reference and every named cluster-resource
   entry field bit-exact, including DA921x page and VSEL. The static empty
   secure-resource effect set does not replace owner-safe runtime readbacks.
   Private `big_on=0x1` and the diagnostic command are source-attributed
   effects outside that resource-invariance set; they do not supply Linux an
   owner-safe private-state readback. Observation owners and per-owner timeouts
   remain unresolved.
9. Only after every gate passes, atomically commit Linux `members=0x1` and
   release the policy/suspend freeze and transition lock. CPU8 remains online,
   private `big_on` remains `0x1`, and the provider reference remains one.
   Consume the boot-local transaction and keep CPU9 on/off admission closed
   until a separately owned transition exists.

The secure source path is now attributed, but its unbounded inner waits, the
Linux membership/notifier and policy/suspend contracts, independent runtime
invariance, and a live CPU9-off observation remain blockers.

## Last-A72-off

Entry requires CPU8 online, a previously committed CPU9-off proof without a
new CPU9 AFFINITY_INFO query, Linux `members=0x1`, owner-safe proof that the
private `big_on` state selects the last-user branch, one exact provider
reference, and no suspend owner. The source audit defines that branch but does
not provide Linux with the private-ledger proof. It does not assume iDVFS has
already been disabled.

1. Freeze the entry state under the cluster lock.
2. Through the unresolved policy coordinator, freeze policy and suspend
   admission, drain in-flight writers, capture the exact shared entry snapshot,
   and prove a safe last-user predicate without writing hardware.
3. Before generic notifier dispatch, require an audited last-user notifier
   path that cannot change shared hardware or lose ownership before CPU_OFF.
4. Let generic arm64 hotplug invoke standard PSCI CPU_OFF on CPU8. As on CPU9,
   the exact target path ends in GIC deactivation, cache maintenance, and WFI;
   it performs no A72 MTCMOS teardown. A returned target call is terminal.
5. From the controlling CPU, issue one level-0 `AFFINITY_INFO` attempt for
   CPU8. Do not re-query CPU9; consume its already committed off proof.
   Its `power_off_big` last-user branch performs the CPU8 per-core teardown,
   changes private `big_on` from `0x1` to `0x0`, and applies the exact
   source-attributed CCI-port, cluster-power, bus-protection, B-mux, B-PLL, and
   SPM effect set. The last-core path reaches eight unbounded waits (two per-
   core, one CCI, and five cluster-off waits); an outer polling deadline
   supplies no bound. Private `big_on`, not query
   count, is the source-proven hardware replay gate, while a retry after an
   unresolved or faulted attempt remains forbidden by the Linux contract.
6. After the query returns OFF, independently attribute and read back the
   resulting per-core/cluster power, bus protection, CCI port, B PLL/mux/
   divider, and SPM state. PLL-off remains unassumed until the exact observed
   final state establishes it. Static source attribution does not replace
   owner-safe runtime readback.
7. Independently attribute iDVFS and MP2 DCM final states. Their policy owners,
   ordering, accessibility, and timeouts remain unresolved.
8. The secure last-user path is the exact source writer for the observed final
   `0x10006218` value and applies `0x10006290 |= 0x2`. Independently read back
   both fields after the query returns. No same-transaction inverse is known.
9. Keep the SRAM boundary blocked. The exact secure path contains no direct
   SRAM-register write, the public wrapper performs no hardware disable, and
   the natural final snapshot does not identify another writer.
10. Confirm the secure sentinels and private `big_on=0x0` poststate only after
    all preceding attribution gates pass.
11. Only after every attribution and independent readback gate passes, release
    the final BUCKB provider reference under the legacy regulator owner and
    verify enable, VSEL, and page. Releasing the reference must not invent a
    VSEL write; a broad operation return is not a hardware-state readback.
12. Commit Linux `members=0x0` only after the complete final snapshot is exact,
    then release the software policy/suspend/transition state. The conservative
    Linux ledger stays at `0x1` until this final commit. Consume the boot-local
    transaction and keep A72 on/off admission closed until a separately owned
    transition exists.

Any mismatch or non-return after CPU_OFF retains whatever power remains and
recovers by reset. There is no safe same-transaction retry after a fault,
restart of CPU8, or re-enable sequence. A later successful-path query may be
source-gated before hardware by private `big_on`; the contract does not mistake
query count itself for that replay control.

## Rejected vendor ordering

The chosen public-equivalent vendor source is evidence, not code to copy. Its
Linux kill loop performs last-user iDVFS disable, clears `g_cl2_online`, and
disables DCM before its later affinity query. The exact secure audit now shows
that the query itself is state-changing and may not return because of inner
unbounded waits. Its external-off helper separately disables BUCKB while the
SRAM-LDO disable wrapper performs no hardware disable. The validated contract
keeps Linux membership conservative until independent post-query proof and
does not assign an inverse to the unresolved policy, SRAM, provider, or
post-isolation boundaries.

## Exit criteria

The contract can become implementation-eligible only when:

- the current parent has an exact Linux CPU8/CPU9 membership and provider-
  reference ledger whose update ordering passes mutation review;
- the state-changing `AFFINITY_INFO -> power_off_big` inner waits have a real
  bound or an independently reviewed fail-closed completion contract;
- every required readback has an owner-safe observation path and timeout;
- policy and suspend admission have one held interlock with audited release and
  terminal-reset semantics;
- the non-last and last-user notifier paths cannot mutate shared policy before
  the secure transaction;
- the unresolved SRAM writer and writable legacy-provider reference/release
  contracts are separately reviewed; and
- the validator can replace every remaining blocking decision without
  weakening private replay attribution, the faulted-query retry prohibition,
  any failure response, or the CPU9 shared-resource prohibition.

Until then, CPU_OFF, HPS-veto removal, build, deployment, and boot are
forbidden.
