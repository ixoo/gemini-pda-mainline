# MT6797 A72 platform-state implementation contract

## Ownership

The watchdog driver alone maps TOPRGU and returns reset bit state while holding
its existing `WDT_SWSYSRST` spinlock. The platform source maps only the named
MCUCFG2 and complete CCI DT resources and reaches SPM through its existing
syscon. It has no fallback physical address and no write API.

## Bounded snapshot

The exported function clears the caller record before any lookup, serializes
its own callers with a mutex, reads two immediate samples, and never loops.
Every source error returns with the destination still zero.

Each sample reads eight raw SPM words, locked logical PWRAP reset state, MP2
DCM, global CCI status, MP2 CCI port control, and global CCI status again. A
set change-pending bit in either sample returns `-EBUSY`. Movement in any
A72-relevant field returns `-EAGAIN`. Only a stable second sample is copied and
marked valid.

## Atomicity boundary

The local mutex and double sample detect local overlap but do not serialize
secure firmware. A later caller must hold the production A72 transition/
hotplug owner and exclude in-flight CPU8/CPU9 PSCI actions from before the
first read until the combined immutable state is consumed. This patch has no
such caller and cannot open A34.

## Explicit exclusions

No register write, reset assert/deassert, CCI generic registration, polling,
retry, sysfs/debugfs state, DT enablement, A34 ABI change, lifecycle
publication, provider action, CPU veto change, CPU_ON/OFF, kernel image,
device access, or boot2 write is included.
