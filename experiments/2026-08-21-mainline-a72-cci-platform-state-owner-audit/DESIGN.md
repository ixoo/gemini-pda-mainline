# Capture-only platform-state source boundary

## Selected ABI

The next implementation is one default-off MT6797 platform driver. Its DT node
must provide named `mcucfg` and `cci` resources, an SPM syscon phandle, and the
existing PWRAP reset. Physical addresses remain in DT; no source file contains
a fallback or magic mapping.

One explicit snapshot call returns a fully initialized typed record containing:

- raw SPM `PWR_STATUS`, `PWR_STATUS_2ND`, `CPU_PWR_STATUS`, and
  `CPU_PWR_STATUS_2ND`;
- raw `MP2_CPUSYS_PWR_CON`, `MP2_CPU0_PWR_CON`, `MP2_CPU1_PWR_CON`, and
  `CPU_EXT_BUCK_ISO`;
- locked logical PWRAP reset state;
- raw MP2 synchronous DCM;
- MP2 CCI port control; and
- CCI global status sampled before and after the port.

The returned record is immutable to the caller. The implementation owns a
mutex for its own snapshot calls, zeroes the destination on every failure,
uses exactly one bounded sampling pass, and returns an error if either CCI
status sample has bit 0 set, if the two status samples differ, or if the
A72-relevant SPM/DCM fields move across the immediate double sample. It does
not poll, retry, write, enable a resource, call PSCI, or publish lifecycle
state.

## Field rules

- CCI inactivity uses only port bits 1:0 and global status bit 0. Upper CCI
  bits are opaque raw evidence.
- CPU8/CPU9 source identity is `CPU_PWR_STATUS[7:6]` and
  `CPU_PWR_STATUS_2ND[7:6]`. Both words are preserved; no equality rule is
  invented.
- General `PWR_STATUS` words are correlation context. Their unrelated bits do
  not participate in A72 stability or acceptance.
- Cluster/per-core SPM control and external isolation retain full raw words,
  but later acceptance may compare only the vendor-defined masks.
- MP2 DCM has a source-backed mask of `GENMASK(6, 0)`; upper bits remain raw.
- PWRAP state comes only from `reset_control_status()` after the watchdog
  driver adds a `.status` callback under its existing `WDT_SWSYSRST` lock.

## Caller contract

This source cannot create cross-owner atomicity. A future production caller
must hold the A72 transition/hotplug owner from before the first read through
consumption, exclude CPU8/CPU9 PSCI actions, and combine this record with the
DA921x, protected-clock, secure-state, generic CPU, and Linux-owner snapshots.
Until then every result is diagnostic and A34 remains closed.

## Explicit exclusions

No generic CCI registration, CCI control call, SPM/DCM/TOPRGU write, sysfs
state, debugfs state, polling loop, hardware enable, A34 ABI change, lifecycle
publication, CPU veto change, build candidate, device access, or CPU request is
part of this boundary.
