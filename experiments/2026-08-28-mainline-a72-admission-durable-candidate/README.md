# Experiment: durable one-shot physical CPU8 admission candidate

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-mainline-a72-admission-durable-candidate` |
| Status | `running`; exact candidate and live preflight pass, deployment pending |
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
- Production source: signed and published commit `eb87d46a`.
- Exact validated package: `linux-7.1.3-gemini-a72-admission-durable-candidate-13dd59d3-a15d3567`.
- Exact raw candidate: `ed6fc5294f5677ed1895bf1157649330c91dd1f6051a6677f2d26972915cd185`.
- Exact boot2-sized candidate: `60902c7ba7e5cccd781082d6d17e1bcb273d184751ddc9dde6a64b2e2a58b8d1`.
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

1. Validate, sign, and publish the isolated production profile. Complete.
2. Build that exact clean commit only on Buildbox and fetch only its validated
   package. Complete.
3. Prove configuration, symbols, unchanged DT graph, container, and full
   checksum offline. Complete. Retained recovery and installer proof remain.
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

Pending. The production Buildbox package and exact boot container passed
independent offline validation. A first read-only Gemian preflight confirmed
all three retained headers were exact logical-empty, then failed closed because
the host regex asked POSIX ERE to repeat 8,192 times. The corrected exact-length
check passed on retry. A subsequent install invocation exposed a second local
pinning error before candidate upload: the derived installer used the artifact
manifest checksum as the padded image checksum. The corrected wrapper now
validates both identities independently and a fresh read-only preflight passes
with exact predecessor `fde53dca...` and all three records logical-empty. No
boot2 write, retained physical write, candidate boot, or physical CPU request
has occurred in this experiment.

## Follow-up

Finish and mutation-test the exact retained-record classifier and boot2
installer, then publish those gates before any device access. The ordered next
action remains owned by `docs/ROADMAP.md`.
