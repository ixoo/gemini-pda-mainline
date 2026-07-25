# MT6797 A72 owner-observer design and review contract

## Scope

This is a fixed diagnostic for CPU8 and CPU9 in the selected Gemian 3.18
hook-equivalent source. It records existing transition behavior; it does not
provide a generic register interface and does not correct vendor hotplug
ordering. Records are typed at compile time and appended to a statically
allocated ring.

The only userspace surface is `/proc/mt6797_a72_transition`, mode `0400`.
Opening it allocates a private point-in-time copy. Reads never hold the writer
lock, cannot clear the ring and cannot trigger a new hardware sample.

## Patch boundaries

| Patch | Logical responsibility |
| --- | --- |
| `0001` | Kconfig-gated recorder, 2048 typed records, per-A72 transaction slots, immutable proc snapshot |
| `0002` | Fixed owner-local DA9214, SPM, secure and clock snapshots |
| `0003` | Existing mutation-path ownership, pre/request/readback records, DCM serialization |
| `0004` | HPS, PSCI, secondary and offline lifecycle correlation |

## Fixed observation contract

| Owner | Fixed values | Serialization and failure contract |
| --- | --- | --- |
| DA9214 | page `0x00`, BUCKB enable `0x5e`, BUCKB VSEL `0xd9` | Existing `da9214_i2c_access` mutex covers selector, reads and restore. A pure snapshot restores the exact prior page. If prior bit 7 (`PAGE_REVERT`) is set, restore success is recorded without a verify-read. Failure is a typed status and never changes the caller's transition return. |
| SPM | offsets `0x180`, `0x184`, `0x188`, `0x18c`, `0x218`, `0x290` from `0x10006000` | Any fallback mapping is created before `__spm_lock`. Snapshot reads and the two observed RMWs are under `__spm_lock`. If observer mapping fails, the caller executes the old direct RMW path. |
| Secure iDVFS | `0x10222470`, `0x10222498`, `0x1022249c`, `0x102224a0`, `0x102224a4`, `0x102224ac`, `0x102224b0`, `0x102224b4`, `0x102224cc`, `0x102222b0`, `0x102222b4`, `0x10222274` | Exactly twelve `SEC_BIGIDVFS_READ` calls plus a repeat of the first address as a stability sentinel. No secure write or user-selected address. |
| B/CCI clock | offsets `0x224`, `0x270`, `0x274` from the existing owner mapping | `spin_trylock_irqsave` avoids waiting for the owner software lock. On success, one existing nominal 2 ms DVFSP hardware-semaphore attempt is made; failure is recorded and no register snapshot is claimed. No owner BUG/retry helper is called. |
| TOPRGU | existing `MTK_WDT_SWSYS_RST_PWRAP_SPI_CTL_RST` only | Pre-state, keyed requested value and readback are captured inside `rgu_reg_operation_spinlock`; the typed record is emitted after unlock. |
| MP2 DCM | existing `MCUCFG_SYNC_DCM_MP2_CONFIG` only | A dedicated spinlock covers pre-state, TOG1 write/readback, TOG0 write and final readback for both enable and disable. This newly serialized timing is an explicit pre-boot safety-review item. |

## Lifecycle correlation

| Stage | Record |
| --- | --- |
| HPS request | Start per-CPU transaction before `cpu_up`/`cpu_down`; finish after the call with its exact return value. |
| Power sequence | Fallback transaction creation, fixed pre-state, each observed owner mutation and fixed boundary snapshots. |
| PSCI external call | Raw firmware return immediately after `invoke_psci_fn`, before `psci_to_linux_errno`. |
| PSCI caller | Linux-mapped return immediately after `psci_ops.cpu_on`. |
| Secondary | `SECONDARY_ONLINE` after `set_cpu_online(cpu, true)` and before `complete(&cpu_running)`. |
| Offline entry | `CPU_DISABLE` after `set_cpu_online(cpu, false)`. |
| Last A72 | Fixed snapshot, iDVFS disable result, every affinity-info retry, buck/DCM/final state. |

Each record includes monotonic sequence, nanosecond timestamp, transaction ID,
target CPU, actor CPU and an observed online mask. The mask is context, not an
atomic hardware-state proof. If both per-A72 transaction slots are active,
owner callbacks without an explicit target remain unattributed rather than
guessing.

## Preserved behavior and known observer effect

- Existing mutation order and function return values remain unchanged.
- No added writer allocates, prints, sleeps for a new retry, warns, panics or
  aborts a transition.
- The existing `udelay` calls remain; the clock snapshot uses the owner's one
  bounded semaphore attempt.
- SPM observation failure falls back to the original mutation.
- The proc read is passive with respect to hardware; it copies already-recorded
  entries only.
- DA9214 selector/readback traffic, longer owner critical sections, fixed SMC
  reads, hardware-semaphore arbitration and DCM serialization are real observer
  effects. Static reasoning does not establish that their timing is safe.
- The exact active source is unresolved. Hook equivalence at `59e00a…` is not
  binary identity.

## Mandatory pre-boot review checklist

- Build all four patches with the exact active configuration plus only
  `CONFIG_MTK_A72_TRANSITION_OBSERVER=y`.
- Use only
  `/home/julien.guest/toolchains/debian-stretch-20170618-arm64-rootfs`
  (snapshot `20170618T000000Z`, GCC `6.3.0 20170516`, ld `2.28`); reject the
  2019 `+deb9u1` environment.
- Review old-GCC warnings, stack use, static ring size, symbol resolution and
  init ordering.
- Re-review every lock context for atomic/sleeping violations and lock-order
  inversion.
- Bound and review DA9214, secure-monitor and clock-snapshot latency at every
  hook.
- Confirm no proc write callback, module parameter or dynamic address path was
  introduced.
- Define a separate boot artifact, recovery path, exact test transition and
  decision table. Do not infer hardware support from this patch series.
