# Experiment: repair the A72 expected-policy MIDR model guard

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-31-mainline-a72-expected-midr-model-guard-repair` |
| Status | `patch generation pending` |
| Subsystem | arm64 late-CPU expected mitigation planning |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-31 |
| Investigator(s) | repository owner and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

Will changing the stale expected-policy MIDR equality to a Cortex-A72 model
comparison restore the three r0p1 mitigation capabilities and the exact READY
frame without weakening the later exact target-register validation?

## Provenance

- Parent: canonical Linux 7.1.3 series through patch `0459`.
- Parent prepared source state:
  `1f9a5748fbbcc0b4dd929841a36314ac1e374400a09a065a75a9cce9e7ccad88`.
- Parent source integrity:
  `536c2258f3518d65b4231a910507b7d1f36cfd3fce4d4249365ef48f762b2cb2`.
- Parent `proton-pack.c` SHA-256:
  `414038771febf064a4574ad587d51b4d075c495cc906a7f5b846a20ddf2173dc`.
- Runtime selector: candidate `b5328f6a...`, plan mask `0x12f7b00`, missing
  capability word mask `00000000,000d0000,00000000,00000000`, zero trigger.

## Safety assessment

The repair changes one pure expected-input predicate. It adds no hardware
access, CPU request, CPU9 route, CPU_OFF route, retry, power operation, storage
access, retained-RAM access, or reboot path. The existing default-off one-shot
CPU8 transaction and watchdog recovery ownership remain unchanged.

## Procedure

1. Generate and replay canonical patch `0460` on exact post-`0459` Buildbox
   source.
2. Prove A72 r0p1 acceptance, other-revision acceptance, and other-model
   rejection while preserving all action-call inventories.
3. Add the patch to the canonical series and audit every manifest profile.
4. Build the focused KUnit and production profiles on Buildbox and run the
   no-network 51-test suite.
5. Construct and independently validate one exact production candidate.
6. Deploy only to live-resolved inactive `boot2`, verify full readback, and
   shut down.
7. On one fresh boot, require READY before issuing CPU8 exactly once.

## Current conclusion

The previous physical boot supplies an attributable, zero-execution source
selector. No new hardware conclusion exists until the repair passes offline
gates and a fresh pretrigger frame.

CPU9 remains vetoed until CPU8 is reproducibly online.
