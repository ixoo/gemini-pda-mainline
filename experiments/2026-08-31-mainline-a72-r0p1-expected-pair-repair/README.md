# Experiment: repair the exact A72 expected MIDR revision

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-31-mainline-a72-r0p1-expected-pair-repair` |
| Status | `patch-generation tooling prepared; build pending` |
| Subsystem | arm64 late-CPU expected pair |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-31 |
| Investigator(s) | repository owner and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

Will replacing the immutable expected-pair MIDR model base `0x410fd080` with
the named unit's independently observed Cortex-A72 r0p1 value `0x410fd081`
allow CPU8 to pass exact late-target validation and continue toward generic
online publication?

## Provenance

- Parent: canonical Linux 7.1.3 series through patch `0458`.
- Parent prepared source state:
  `9c4c8924132e37a40fb6b334e8bcfa4e1d241bd34542a6736d6fba9f5e488b8e`.
- Parent source integrity:
  `19387cb31b807805a120732f76b2183534aa63ab9cb811f1acb20dd185616e10`.
- Parent `mt6797_psci.c` SHA-256:
  `db06b8ad0f8552c908c4f29f7cda4a86745efceea27e0d8a15cd68dfe93c7265`.
- Runtime selector: predecessor reason 8, bitmap `0x2`, expected
  `0x410fd080`, observed `0x410fd081`.

## Safety assessment

This is a one-line expectation repair. It adds no hardware access, power step,
CPU request, CPU9 route, CPU_OFF route, retry, storage access, retained-RAM
access, or reboot path. The existing default-off one-shot CPU8 transaction and
watchdog recovery ownership remain unchanged.

## Procedure

1. Generate and replay canonical patch `0459` on the exact managed Buildbox
   source.
2. Prove the revision-neutral capability model checks and action-call inventory
   are unchanged.
3. Add the patch to the canonical series and audit every manifest profile.
4. Build the focused KUnit and production profiles on Buildbox and run the
   existing no-network 51-test suite.
5. Construct and independently validate one exact production candidate.
6. Deploy only to live-resolved inactive `boot2`, verify full readback, and
   shut down.
7. On one fresh boot, prove zero prior execution and issue CPU8 exactly once.

## Current conclusion

The repair is selected by exact mainline runtime evidence and agrees with the
independent CPU8/CPU9 target-local capsules. No new hardware conclusion exists
until the successor passes offline gates and one attributable CPU8-only boot.

CPU9 remains vetoed until CPU8 is reproducibly online.
