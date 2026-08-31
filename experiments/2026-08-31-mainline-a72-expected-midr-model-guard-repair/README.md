# Experiment: repair the A72 expected-policy MIDR model guard

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-31-mainline-a72-expected-midr-model-guard-repair` |
| Status | `runtime attempt 1 stopped before CPU8; MIDR guard fixed, effect planning remains blocked` |
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

Runtime attempt 1 passed the selected repair boundary but stopped safely before
CPU8. The three previously missing mitigation capabilities are restored, the
target, required, and expected capability vectors now match, and the
expected-pair diagnostic mask is zero. This confirms the stale MIDR equality
was the cause of the earlier local-capability rejection.

The remaining READY mask is `0x36000`: local capability planning completed,
but production effect planning returned `-EINVAL`, leaving both the effects
and dependent expected-HWCAP plans empty. The one-shot trigger was not issued;
CPU8, CPU9, CPU_OFF, retry, and storage-write counts all remained zero. The
guarded USB recovery reboot returned the device to changed-ID Gemian
`3.18.41+`. See the
[runtime evidence](results/runtime-attempt-1-local-caps-restored-20260831.txt).

Buildbox generated and replayed canonical patch `0460` from the exact
post-`0459` source. The one-line change accepts A72 r0p1 and another A72
revision, rejects A53 r0p1, preserves the exact late-target MIDR contract, and
does not change any action-call inventory. See the
[generation evidence](results/patch-generation-20260831.txt).

CPU9 remains vetoed until CPU8 is reproducibly online.

All offline gates now pass. Three exact Buildbox packages were fetched from
commit `8810735d`, the no-network transition suite passed 51 of 51 tests, and
the production image passed two independent assemblies, all 32 LK gates, and
six negative container mutations. The exact full-partition candidate is
`5e686d2c7e9f59c7345ec3c50048a01371ab1938ceb8753b599d0afdd3084d69`.
See the [build evidence](results/buildbox-builds-20260831.txt),
[KUnit evidence](results/focused-kunit-qemu-20260831.txt),
[candidate evidence](results/production-candidate-20260831.txt), and
[predeployment hypothesis](results/predeployment-hypothesis-20260831.txt).

The full-partition candidate was then written to live-resolved inactive
`boot2`, read back exactly, and the device was shut down. See the
[deployment evidence](results/deployment-boot2-20260831.txt). The next action
is to localize and cover the production-only effect-plan rejection offline,
then build a distinct candidate. No identical device retry is justified.
