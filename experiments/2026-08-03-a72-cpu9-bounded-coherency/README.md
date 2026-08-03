# Experiment: CPU8/CPU9 bounded coherency

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-03-a72-cpu9-bounded-coherency` |
| Status | `runtime-attempt-1-passed-repeatability-pending` |
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
- Exact compile-review repository commit:
  `938cdefde98522a2cd3504605aee04e4c83d5671`.
- No container, deployment, or runtime claim exists yet.

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
- [`scripts/source_edits.py`](scripts/source_edits.py): deterministic exact-parent
  source transformation.
- [`scripts/test_static.py`](scripts/test_static.py): source contract and 11
  rejected mutation checks.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox): Git-pinned,
  Buildbox-only exact-parent patch generation.
- [`patches/`](patches/): one accepted Buildbox-generated logical child patch.
- [`results/patch-generation-review-20260803.txt`](results/patch-generation-review-20260803.txt):
  exact identities, rejected generation attempts, source/mutation audit, and
  compile-only acceptance decision.
- [`results/compile-review-20260803.txt`](results/compile-review-20260803.txt):
  exact Buildbox child/parent identities, configuration, diagnostics, linked
  barrier/symbol checks, and stack bounds.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh),
  [`scripts/assemble.py`](scripts/assemble.py), and
  [`scripts/test_candidate.py`](scripts/test_candidate.py): pinned,
  device-free Android-v0 construction and independent validation.
- [`results/offline-container-review-20260803.txt`](results/offline-container-review-20260803.txt):
  two-root reproducibility, exact container identities, inherited ramdisk, and
  offline-only acceptance boundary.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh),
  [`scripts/capture-live-outcome.sh`](scripts/capture-live-outcome.sh), and
  [`scripts/test_runtime_tools.py`](scripts/test_runtime_tools.py): guarded
  deployment, optional read-only USB/netcat capture, and mutation-tested result
  contracts.
- [`results/runtime-decision-map-20260803.txt`](results/runtime-decision-map-20260803.txt):
  exact candidate, pair-v4 pass/fault oracle, changed-cycle requirements, and
  predeclared decision branches.
- [`results/deployment-20260803.txt`](results/deployment-20260803.txt): exact
  live-GPT target, predecessor/candidate/readback identities, no-backup policy,
  temporary cleanup, and confirmed shutdown.
- [`results/runtime-attempt-1-pass-20260803.txt`](results/runtime-attempt-1-pass-20260803.txt):
  exact pair-v4 pass, fault exclusions, watchdog recovery, CPU state, changed
  boot identity, and unchanged full boot2 checksum.

## Conclusion

`runtime-attempt-1-passed-repeatability-pending`: Buildbox compiled the bounded-
coherency child and exact terminal parent from repository commit `938cdef`,
with identical configuration deltas and compiler diagnostics. Linked child
code contains the expected synchronous IPI/work callbacks and acquire/release
barriers; the exact parent excludes those symbols. Child stack use is bounded
at 64 bytes for the work callback, 16 bytes for the IPI callback, and 160 bytes
for the extended terminal worker. Two independent output roots then produced
byte-identical raw and padded Android-v0 images with the unchanged known-good
ramdisk. The guarded installer pins the exact terminal predecessor, creates no
fresh backup, requires two full readbacks, and powers off after success. The
read-only collector requires the complete pair-v4/HPS/coherence terminal. This
exact candidate replaced the expected terminal predecessor on live-GPT-resolved
inactive `boot2`; two full readbacks matched and shutdown was confirmed. The
first selected cycle then retained an exact pair-v4 pass: both CPUs completed
the 1,024-round exchange with zero errors and final sequences 1,024/1,024 while
the inherited HPS CPU9 `-EPERM` attribution remained intact. Watchdog recovery,
offline CPU8/9, changed boot identity, fault exclusions, and unchanged boot2
passed. This is one bounded runtime pass, not general coherency support.

## Follow-up

Publish the sanitized first-pass record. Then run the one exact repeatability
cycle earned by the fixed decision map from a new ordinary-Gemian baseline. Do
not extend load or cross another power boundary yet.
