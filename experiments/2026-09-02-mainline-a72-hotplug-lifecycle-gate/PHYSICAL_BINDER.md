# CPU9 physical binder and restore contract

## Purpose

This contract fixes the production boundary around the already hardware-free
CPU9 down executor.  It does not implement that boundary, select a boot
candidate, or authorize a device run.  Its job is to make the next source
slice reviewable before `cpu_can_disable()` can return true.

The source audit found that this is not a single callback hookup.  The binding
must join four independently owned lifecycles: the established CPU8/CPU9
bring-up parent, CPU9 down, physical observation, and a distinct CPU9 restore.
It also needs a new retained record because the four existing records already
belong to CPU8, CPU9, CPU9 admission progress, and CPU9 CPU_ON progress.

## Entry and trigger ownership

Only the existing one-shot admission trigger may authorize this experiment.
After its one CPU8 request and one initial CPU9 request both return exact
success, the same task must immediately issue one `remove_cpu(9)` followed by
one `add_cpu(9)`.  There is no userspace delay, second trigger, retry, sysfs
hotplug entry, or automatic probe action.

Before down preflight, a read-only parent proof must establish all of the
following together:

- the CPU8 and CPU9 initial-up transactions are exact retired successes;
- membership is `0x3`, CPUs 8 and 9 are online, and the complete online set is
  CPUs 0--9;
- the provider is still held under the same identity;
- no owner or policy transition is active;
- the CPU8 binder terminal is the accepted online proof; and
- the inherited watchdog identity is nonzero, owned, and no older than 5
  seconds from its recorded takeover time.

The admission task publishes a one-use authorization before `remove_cpu(9)`.
Down preflight must match that task and authorization.  The target-side
`cpu_can_disable()` may return true only for CPU9 after the exact down
transaction has reached the validated executor state.  It remains false for
CPU8, CPUs 0--7, CPU9 outside that state, frozen/suspend hotplug, and every
internal or userspace bypass.

## Inherited watchdog

The binding adds a read-only validation operation to the MTK watchdog driver.
It must take the recovery lock, compare the exact nonzero software ownership
identity, read the mode and length registers, and require the original
15-second recovery configuration.  It performs zero writes and cannot mint,
take over, reload, refresh, cancel, or release ownership.

The CPU8 binder must expose the identity and monotonic takeover time already
associated with its accepted terminal.  This is observation of existing
state, not a second watchdog owner.  Any mismatch before CPU_OFF rejects the
request.  After CPU_OFF commit, the only recovery is the original watchdog
reset.

## Record 4 retained ledger

The binder owns exactly one 4 KiB record at physical `0x44414000`, record 4 of
the existing `0x44410000..0x444effff` no-map ramoops reservation.  Records
0--3 are immutable inputs and must never be written by this slice.  The writer
requires record 4 to be raw-empty or pstore-empty and never clears, repairs,
reopens, or retries it.

The dedicated wire format has a three-word pstore header and two alternating
27-word little-endian copies.  Each copy contains its own magic, version,
generation, stage, terminal, error, parent/session, down, restore, and
watchdog identities, result flags, exact call counts, online/membership
state, mismatch mask, and CRC32.  A record write clears only the destination
copy's integrity word, writes data, commits CRC last, performs an ordered full
copy readback, and publishes the pstore signature last on first use.

The successful path has at most 16 record commits and 451 32-bit MMIO writes,
including the maximum three first-use header writes.  Failures replace the
next normal stage with one terminal record; they do not add a retry.  Recovery
must decode the newest unique CRC-valid copy after a confirmed disconnect,
changed boot ID, and Gemian reconnect.  It never removes the remote pstore
record.

The stages distinguish entry/parent proof, owner preparation, watchdog
validation, baseline, generic validation, target disable, CPU_OFF commit,
an impossible CPU_OFF return, the one affinity result, post-state, CPU8
response, off proof, generic down completion, restore preparation, CPU_ON
commit, secondary completion, and full restore completion.  Screen color and
the expected watchdog reset are never result evidence.

## Physical snapshot

The existing direct-state compositor cannot be used because it requires the
old pristine/offline parent.  The existing physical-source capture cannot be
used because it writes the protected-readback ledger.  The binder therefore
needs a dedicated snapshot adapter with long-lived references to the exact
platform-state, DVFSP-clock, and BigiDVFS devices plus the registered provider.

There are exactly two binder-level snapshots and no binding-level retry: one
baseline and one post-affinity sample.  Each uses the existing stable platform
state capture, one provider sample, one DVFSP-clock backend call, and one
BigiDVFS backend call.  Sample-generation fields are excluded from equality.

The DVFSP clock backend is not literally read-only: its established readback
transport writes the fixed CSPM power-on value once and uses at most 200
semaphore requests to acquire and 200 to release per call.  Those bounded
transport writes are the only observation-side MMIO writes admitted here.
They do not authorize PLL, divider, OPP, voltage, rail, or clock ownership
changes.  BigiDVFS is restricted to its eight stable REG_READ calls per
snapshot; the SRAM-set FID is forbidden.

The post-state predicate remains the one in `PHYSICAL_EXECUTOR.md`: CPU9 is
off in both CPU status words, CPU8 remains on in both, the named cluster,
provider, clock, BigiDVFS, isolation, DCM, and CCI fields are unchanged, both
CCI pending samples are clear, the CPU9 core-control word is evidence only,
and general SPM status is correlation only.

## Bounded retained-CPU callback

The controller queues exactly one asynchronous call to CPU8 with
`smp_call_function_single(..., wait=0)`.  The callback context and completion
live in the binder, not on the requesting task's stack.  The callback validates
CPU8 and the down identity before publishing completion.  The controller waits
at most 250 ms.  It never issues a second IPI, uses `wait=1`, frees callback
state early, or treats timeout as success.

## Exact PSCI boundaries

The target CPU9 path first uses the ordinary PSCI disable guard.  After the
owner consumes its CPU_OFF budget and record 4 durably publishes the commit,
the target invokes exactly one direct `psci_ops.cpu_off()` with the standard
power-down state.  A return is a terminal post-commit fault.

The controller then makes exactly one direct
`psci_ops.affinity_info(cpu_logical_map(9), 0)` call.  It must not call
`cpu_psci_ops.cpu_kill()`, whose generic implementation polls repeatedly.
Only the exact PSCI OFF result permits physical readback and down completion.

Restore is a parent-linked transaction, not reuse of the initial CPU9 binder.
CPU-up preflight prepares it; validation checks the same controller and exact
offline parent; CPU boot consumes the one CPU_ON budget, durably records that
commit, and calls `cpu_psci_ops.cpu_boot(9)` once.  Secondary completion records
the returning CPU, and full CPUHP completion calls the membership restore
completion before publishing the terminal 4+4+2 result.  Any CPU-up rollback
is routed to `fail_restore()` and suppresses the unrelated P32 initial-up
rollback publication.

## Failure boundary and implementation order

Before the durable CPU_OFF commit, failure closes the one trigger and releases
only attempt-owned software state.  At or after that commit, every unexpected
return, timeout, observation mismatch, callback failure, publication failure,
generic completion failure, or restore failure latches a terminal fault and
waits for reset.  There is no second CPU_OFF, affinity query, callback, CPU_ON,
guessed inverse, or last-A72 operation.

Implementation proceeds in separately reviewable hardware-free pieces:

1. add and test the parent proof, read-only watchdog validator, dedicated
   record-4 ledger/decoder, and snapshot adapter, with no production caller;
2. add and test the distinct restore executor and its CPU-up failure routing,
   still disconnected;
3. add and test the one-task down/restore binder and admission orchestration,
   keeping candidate DT/config selection off; and
4. only after exact replay, rejecting source mutations, Buildbox compile, and
   no-network runtime tests may a separate commit select one boot candidate.

[`physical-binder-contract.json`](physical-binder-contract.json) is the
machine-readable authority.  Its validator and mutation suite must pass before
source generation begins.
