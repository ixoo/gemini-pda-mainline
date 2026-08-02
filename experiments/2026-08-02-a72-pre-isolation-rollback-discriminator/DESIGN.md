# CPU8 pre-isolation rollback contract

## Exact entry gate

All values are captured synchronously under their existing owners before the
first mutation. The attempt is rejected without writes unless every predicate
holds:

- the immutable observer is actively capturing the exact CPU8 HPS-up
  transaction; a CPU8 request before that latch returns `-EAGAIN` without
  consuming the one-shot or invoking any hardware owner;
- target is CPU8; CPU8 and CPU9 are offline;
- this is the first and only latched attempt on the boot;
- DA921x page is `0x80`, BUCKB enable is zero, and BUCKB VSEL is `0x46`;
- SPM `0x218` is exactly `0x00010132` for the retained relevant state and bit 0
  is clear;
- SPM `0x290 & 0x3` is exactly `0x2`;
- TOPRGU PWRAP reset bit 11 is clear;
- the retained secure SRAM/iDVFS sentinel set is the clean zero state;
- MP2 DCM bits 6:0 are zero; and
- power/recovery and immutable evidence paths pass their separate gates.

An exact full-register equality is required where the successful latch supplied
one. A future implementation must explicitly identify which unrelated bits may
change asynchronously; it must not silently weaken an equality into a mask.

## Forward boundary and injection

The only permitted forward steps are:

1. under the SPM owner, set `0x218 bit 0` and require the exact retained
   `0x00010132 -> 0x00010133` readback;
2. under the watchdog/TOPRGU owner, assert PWRAP reset bit 11 and require its
   masked readback;
3. under the DA921x owner, preserve page ownership, enable BUCKB from zero to
   one, restore page `0x80`, wait the existing 1 ms settle interval, and require
   enable one with unchanged VSEL `0x46`; and
4. take the one-shot diagnostic failure branch.

The branch is compiled and one-shot; it has no userspace trigger. It occurs
before the SPM `0x290` external-isolation mutation. The code path must prove
that no isolation clear, PWRAP deassert from the normal forward path, 240 us
SRAM interval, SRAM-LDO SMC, PSCI call, DCM action, iDVFS action, CPU online
publication, or CPU9 activity occurred.

## Bounded rollback

Rollback changes only attempt-owned state and rechecks ownership immediately
before each inverse:

1. If page is restored, VSEL remains `0x46`, and BUCKB is still exactly one
   from this attempt, disable BUCKB under the DA921x owner and verify enable
   zero, VSEL `0x46`, page `0x80`, and status zero. Otherwise do not guess a
   write; retain power and mark `fault-retain`.
2. If external isolation is still `0x2` and SPM `0x218` still matches the exact
   attempt post-state `0x00010133`, clear only bit 0 under the SPM owner and
   require exact return to `0x00010132`. Otherwise skip that inverse and mark
   `fault-retain`.
3. If TOPRGU bit 11 is still asserted by this attempt, deassert it under its
   owner and require clear readback. If ownership cannot be proved, make no
   unrelated reset change and mark `fault-retain`.
4. Capture the full final DA921x, SPM, TOPRGU, secure, clock and DCM state. A
   `rolled-back` result requires byte-for-byte equality with the exact entry
   state for every field in scope, both A72 CPUs offline, no forbidden boundary
   event, and immutable stability on delayed reread.

Every mismatch is terminal for the boot. There is no re-arm or retry. A
`fault-retain` result is evidence, not permission to continue or improvise
cleanup. The independent watchdog/native reset path remains recovery, not proof
of rollback correctness.

## Evidence ABI

The immutable header must identify one of:

```text
state=rolled-back
state=fault-retain
state=rejected-prestate
```

The record must include entry values, every forward write/readback, the exact
injection boundary, every rollback ownership decision, every inverse/readback,
forbidden-boundary counters, CPU masks, and final values. Two delayed reads must
be identical for `rolled-back` and `fault-retain`.

## Decision matrix

| Result | Decision |
| --- | --- |
| Exact `rolled-back`, all equality and forbidden-boundary gates pass | Close only the pre-isolation BUCKB/reset rollback claim; keep later rollback rows open |
| Entry mismatch before writes | `rejected-prestate`; revise assumptions, do not retry unchanged |
| Ownership/readback mismatch during forward or inverse | `fault-retain`; recover through reset and inspect evidence |
| Isolation, SRAM-LDO, PSCI, DCM, CPU online, or CPU9 event | Reject experiment as boundary violation |
| Crash, unstable evidence, or missing final equality | Inconclusive/rejected; no retry before redesign |

No result from this experiment authorizes a mainline regulator provider,
external-isolation clear, SRAM-LDO call, PSCI request, CPU8 consumer, CPU9,
suspend, or resume.
