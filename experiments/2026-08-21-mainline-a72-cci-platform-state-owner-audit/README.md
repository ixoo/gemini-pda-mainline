# Experiment: MT6797 A72 CCI and platform-state owner audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-21-mainline-a72-cci-platform-state-owner-audit` |
| Status | completed offline audit; capture-only source selected |
| Subsystem | MT6797 Cortex-A72 CCI, SPM, TOPRGU, and MP2 DCM state |
| Device variant | Planet Gemini PDA named development unit |
| Date | 2026-08-21 America/New_York |
| Tracking issue | Roadmap Gate 7, production A34 owner |

## Question

Which exact MT6797 registers can supply fresh A72 platform state, which owner
may read them safely, and what serialization is required before they can join
the direct A34 recovery record?

The audit must not manufacture an `arm,cci-400` description, add a physical
address in C code, write CCI/SPM/DCM/TOPRGU, or imply that independently timed
reads are an atomic recovery proof.

## Provenance and safety

- Repository input: signed and pushed commit
  `a72e9032c3be9d329cb28d7bee491547d5396599`.
- Canonical full-series source state:
  `905fb7f5ead29cbe65eaf7f66e41433aea417c2ee15d751ebda6ddf79f19ad8e`.
- Public vendor-kernel input: exact clean revision
  `59e00a9144d782e148332009a835b99c43382467`.
- Private secure input: the same immutable payload previously attributed by
  SHA-256
  `2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3`.
- The prepared mainline and vendor trees were inspected read-only on
  Buildbox. Bounded secure disassembly was performed read-only in the analysis
  VM. No source or private payload was copied into this repository.

This audit performed no build, device contact, MMIO access, SMC, I2C transfer,
partition access, boot2 write, reboot, or CPU request. It authorizes only the
default-off, read-only source described in
[`DESIGN.md`](DESIGN.md). Exact hashes and findings are pinned in
[`results/provenance-20260821.txt`](results/provenance-20260821.txt) and
[`results/ownership-matrix.tsv`](results/ownership-matrix.tsv).

## Exact CCI result

The MT6797 vendor DT provides one `0x10000`-byte CCI window at physical
`0x10390000`. Public vendor hotplug code names the global status at base
`+0x000c`, `CHANGE_PENDING` as bit 0, and snoop/DVM request bits as port-control
bits 0 and 1. It names only the existing SI3/SI4 ports at `+0x4000` and
`+0x5000`.

The exact secure A72 path closes the missing MP2 identity in two independent
ways:

- generic CCI control extracts affinity level 1 from MPIDR `0x80000200`, uses
  cluster table entry 2, whose initialization writes offset `0x6000`, and
  adds it to the global CCI base; and
- `power_off_cl3` directly accesses `0x10396000`, clears bits 1:0, then checks
  those same bits after the transition.

Both secure paths poll global `0x1039000c` bit 0. They do **not** poll
`0x1039600c`. The earlier EF24 row in the secure CPU-off attribution audit
incorrectly added the global status offset to the MP2 port base; that row and
its validator now carry an explicit 2026-08-21 correction.

The owner-safe inactive predicate is therefore limited to:

- `(mp2_port_control & 0x3) == 0`; and
- `(global_status & 0x1) == 0` before and after the port sample.

Upper port-control bits are retained as evidence but are not assigned a new
meaning or compared to an invented constant. A capture source must never poll:
one pre-status read, one port read, and one post-status read either complete
immediately or return a movement/busy error.

The generic ARM CCI driver is not an honest owner for this SoC. Its CCI-400
control model is fixed at two ACE plus three ACE-lite ports and its standard
control interfaces end at `+0x5000`; it has no typed read-only state getter and
requires BSP locking for mutations. Current MT6797 mainline has no CCI node.
Adding a standard `arm,cci-400` node would omit the source-proven MP2 port, so
the selected source uses an explicit DT resource in a default-off
MT6797-specific observer and performs no CCI write.

## Exact platform-state result

Current mainline already describes SPM as the `0x10006000` syscon and SCPSYS
owner. The A72-relevant vendor definitions are:

- `CPU_PWR_STATUS` `+0x188` and `CPU_PWR_STATUS_2ND` `+0x18c`; CPU8 and CPU9
  use bits 7 and 6, and vendor software reports a CPU on only from the
  intersection of the two words;
- `MP2_CPUSYS_PWR_CON` `+0x218`; documented fields cover reset, isolation,
  primary/secondary power, clock disable, SRAM clock/isolation, power-down,
  acknowledgement, and sleep state;
- `MP2_CPU0_PWR_CON` `+0x240` and `MP2_CPU1_PWR_CON` `+0x244`, with the same
  per-core power/reset/isolation/SRAM field family; and
- `CPU_EXT_BUCK_ISO` `+0x290`, where bit 1 is `B_EXT_BUCK_ISO`.

The general-domain `PWR_STATUS` pair at `+0x180/+0x184` belongs to SCPSYS
context, not to the CPU8/CPU9 on predicate. It may be retained raw for
correlation, but unrelated-domain changes cannot invalidate A72 state by
full-word comparison. Likewise, the stable historical recovered state
`CPU_PWR_STATUS=0x00350c08` and `CPU_PWR_STATUS_2ND=0x00350cff` proves that the
two CPU-status words need not be identical while CPU8/CPU9 are off. The source
must preserve both raw words; it must not borrow SCPSYS's different
general-domain mismatch rule.

MP2 synchronous DCM is exactly `MCUCFG2 + 0x274` (`0x10222274`). Bits 6:2 are
the divider, bit 1 the update toggle, and bit 0 the enable. The full word is
captured, while only bits 6:0 have source-backed semantics.

TOPRGU `WDT_SWSYSRST` is at watchdog offset `+0x18`, and PWRAP reset is bit 11.
The current reset controller already protects assert/deassert read-modify-write
operations with its spinlock, but exposes no `.status` operation. The safe
accessor is a locked reset-controller status callback, consumed through
`reset_control_status()`; duplicating the watchdog mapping in the platform
source is rejected.

## Ownership and serialization

Regmap locking alone does not make the tuple atomic: current SCPSYS accesses
the same SPM window directly, TOPRGU has its own lock, and secure firmware owns
A72 CCI/SPM transitions through PSCI. A local observer mutex cannot serialize
against an in-flight secure call.

The capture-only source may serialize its own callers, validate immediate
double samples, and use the TOPRGU owner's locked accessor. The later A72
transition/hotplug owner must additionally hold its operation lock, prove both
A72 CPUs are outside an in-flight transition, and prohibit a concurrent PSCI
CPU action from the first platform read through publication. A snapshot taken
outside that transaction is diagnostic only and cannot open A34.

## Conclusion

`confirmed`: MP2 CCI port control is `0x10396000`; its snoop/DVM request bits
are 1:0; the sole source-backed change-pending word is global `0x1039000c`
bit 0.

`confirmed`: the exact SPM, TOPRGU PWRAP, and MP2 DCM surfaces and their local
read owners are sufficient for a default-off typed capture source.

`rejected`: `0x1039600c`, a fake standard CCI-400 node, CCI writes, duplicated
TOPRGU mapping, full-word equality on unrelated SPM status, or local locking as
cross-PSCI serialization.

`selected next`: implement the default-off capture-only source and the locked
TOPRGU status accessor. It has no A34 caller and cannot request CPU8.

A34, lifecycle publication, CPU8/CPU9 requests, a boot candidate, and device
action remain closed.

## Validation

Run from the repository root:

```sh
python3 experiments/2026-08-21-mainline-a72-cci-platform-state-owner-audit/scripts/validate.py
```
