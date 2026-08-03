# Experiment: CPU8/CPU9 bounded coherency

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-03-a72-cpu9-bounded-coherency` |
| Status | `design-only-source-pending` |
| Subsystem | MT6797 retained Cortex-A72 pair and cache coherency |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-03 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 8 CPU9 retained coherency/load |

## Question or hypothesis

Can CPUs 8 and 9 complete a bounded concurrent shared-memory ping-pong with
explicit publish/consume barriers while the exact repeatable retained-execution
parent preserves CPU startup, HPS down-pressure vetoes, fixed watchdog
recovery, and every power boundary?

## Provenance and environment

- Exact parent: `2026-08-03-a72-cpu9-terminal-attribution`, including two
  exact runtime passes and its self-contained pair-v3/HPS terminal.
- Exact generated parent kernel commit:
  `0cea53b8b19e5b58e6b2cb748466d6e620a4c911`.
- Exact parent terminal patchset SHA-256:
  `2d94a2cd489e33a7df854ffec7533fbf969dc9c810e9eece57d118b905060310`.
- Build backend: Buildbox only; no native VM kernel build.
- No patch, compile, container, deployment, or runtime claim exists at this
  design stage.

## Safety assessment

The child may add only one CPU0-pinned observation worker, one concurrent
cross-call to already-online CPUs 8 and 9, bounded shared-memory handshakes,
and a self-contained terminal snapshot. It must not enable CPU_OFF, initiate
hotplug, alter startup or pair timing, change HPS policy, touch a regulator or
power register, modify the watchdog, allocate persistent userspace control, or
continue after recovery.

## Associated code

- [`DESIGN.md`](DESIGN.md): exact concurrency oracle, boundedness, terminal,
  result classes, source invariants, and safety boundary.

## Conclusion

`design-only-source-pending`: the exact experiment is predeclared. It uses a
CPU0-pinned worker so the cross-call caller cannot be either A72 target, and a
fixed 1,024-round CPU8↔CPU9 publish/consume handshake with finite spin budgets.
No kernel source has been changed.

## Follow-up

Commit and push this design. Then implement it as a deterministic source-minimal
child of the exact terminal-attribution kernel, add mutation checks, and use
Buildbox for patch generation and exact-parent compilation.
