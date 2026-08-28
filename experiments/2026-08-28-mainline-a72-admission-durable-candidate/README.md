# Experiment: durable one-shot physical CPU8 admission candidate

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-mainline-a72-admission-durable-candidate` |
| Status | `running` production definition; no candidate or device action |
| Subsystem | arm64 CPU hotplug, MT6797 admission, retained evidence |
| Device variant | Planet Computers Gemini PDA, named project device |
| Date(s) | 2026-08-28 |
| Investigator(s) | Julien Etienne and Codex |

## Question or hypothesis

Can the hardware-free-proven controller either bring CPU8 online or leave one
attributable retained branch after an automatic reset, without requesting
CPU9, CPU_OFF, or a retry?

## Provenance and environment

- Parent tail: canonical patches through `0418`.
- Hardware-free parent: exact Buildbox package from commit `43eb3b06` and the
  12-of-12 no-network proof classified by signed harness `ba171ca0`.
- DT hypothesis: byte-identical to the retired admission candidate's proven
  supplier graph; only the kernel/configuration gains the durable trace.
- Build backend: Buildbox only; no native VM build.
- Runtime target in this definition phase: none.

## Safety assessment

The current phase only defines a production profile. It enables the immutable
entry owner for retained record 2 and mutually exclusive zero-request owner
for record 3 while preserving the mutable transition ledger's exclusive
ownership of record 1. The controller still permits at most one synchronous
`add_cpu(8)` call. CPU9, CPU_OFF, retries, userspace triggers, and all KUnit
suites remain disabled.

Any later deployment must resolve inactive logical `boot2` from the live GPT,
require exact predecessor and power gates, perform a full-partition readback,
and shut down cleanly without reboot or a fresh backup. No device action is
authorized by this definition alone.

## Procedure

1. Validate, sign, and publish the isolated production profile.
2. Build that exact clean commit only on Buildbox and fetch only its validated
   package.
3. Prove configuration, symbols, unchanged DT graph, container, full checksum,
   retained recovery, installer, and one-attempt decision map offline.
4. Select a candidate only if every gate passes.
5. Install only exact live-GPT inactive `boot2`, verify full readback, and shut
   down for one owner-selected boot.

## Decision map

| Record 2 | Record 3 | Transition ledger | Decision |
| --- | --- | --- | --- |
| empty | empty | empty | pre-controller or retention failure; retire |
| entry | empty | empty | prerequisite deferral/interruption; retire and localize |
| entry | exact zero terminal | empty | exact zero-request source branch |
| entry | empty | committed | request reached binder; classify ledger stage |
| foreign/torn/conflicting | any | any | reject attribution; retire |

An exact live frame proving CPU8 online remains independently sufficient only
when candidate identity, one request, CPUs 0--8 online, CPU9 offline, and the
terminal transition ledger all agree.

## Conclusion

Pending. The production profile is defined from the hardware-free-proven
source, but no production build, package, candidate, device access, retained
physical write, or CPU request has occurred.

## Follow-up

Publish the clean definition and build the profile on Buildbox. The ordered
next action remains owned by `docs/ROADMAP.md`.
