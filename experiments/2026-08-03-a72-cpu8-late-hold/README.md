# Experiment: Retain a late CPU8 execution sample

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-03-a72-cpu8-late-hold` |
| Status | `source-accepted-compile-pending` |
| Subsystem | MT6797 CPU8 IPI/coherency and retained pstore evidence |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-03 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 7 stability follow-up |

## Question or hypothesis

Does CPU8 remain online and execute a third synchronous callback about ten
seconds after its already-proven completion, while CPU9 remains offline and the
existing fail-closed down barriers prevent the prior notifier fault?

## Provenance and environment

- Exact source: `59e00a9144d782e148332009a835b99c43382467`.
- Exact parent: the three-patch CPU8 held-online experiment.
- Build backend: Buildbox only; no native VM kernel build.
- Intended boot path: live-GPT-resolved non-primary `boot2` after all offline
  gates pass.

## Safety assessment

The child changes only the delayed sampler. It retains the exact startup path,
HPS floor, generic pre-notifier CPU8/9 down veto, CPU9 startup rejection,
CPU_OFF prohibition, fixed watchdog owner and deadline, and recovery path. The
third sample is one synchronous IPI and accounting check; it adds no load,
voltage, clock, hotplug, watchdog refresh, control interface, or CPU9 action.

The first sample remains at about +1 second, the second at about +6 seconds,
and the new terminal sample is at about +10 seconds. The parent runtime's
watchdog ended near 14 seconds after a completion near 1.932 seconds, leaving
about two seconds between the third sample and recovery.

## Associated code

- [`DESIGN.md`](DESIGN.md): timing, terminal record, and result decisions.
- [`scripts/source_edits.py`](scripts/source_edits.py): deterministic parent
  transformation.
- [`scripts/validate_patch.py`](scripts/validate_patch.py): source ordering,
  timing, inventory, and forbidden-action checks.
- [`scripts/test_static.py`](scripts/test_static.py): mutation rejection.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox): exact-parent
  patch generation on Buildbox.
- [`scripts/build-on-buildbox`](scripts/build-on-buildbox): exact child versus
  held-online parent compile review.
- [`patches/`](patches/): the one logical Buildbox-generated child patch.
- [`results/patch-generation-review-20260803.txt`](results/patch-generation-review-20260803.txt):
  two rejected validator revisions and the accepted source identity.

## Procedure

1. Apply the exact held-online parent patch series to the pinned source.
2. Generate one logical child patch that makes sample 2 nonterminal, schedules
   sample 3 four seconds later, and emits a versioned terminal only after the
   third successful synchronous CPU8 callback.
3. Reject timing, CPU identity, CPU9, hit-count, scheduling, watchdog, load,
   hotplug, and forbidden-action mutations.
4. Commit and push the clean source/tooling revision before Buildbox patch
   generation and compilation.
5. Compare the child and exact parent diagnostics, disassembly, and stack use.
6. Construct and independently validate an Android-v0 container before one
   guarded boot2 deployment and changed-cycle pstore capture.

## Observations

Buildbox applied the full exact parent and generated one 13-addition/8-removal
patch. Two earlier generation revisions stopped before publication: one had an
ambiguous mutation anchor, and the next exposed that loose token-order checks
did not reject a wrong callback CPU. The accepted validator requires the full
IPI/accounting predicate exactly once and rejects all seven unsafe mutations.
No kernel compile or device action has occurred.

## Analysis

The prior run did not retain its +1-second and +6-second measurements because
the 65,524-byte console tail began at 9.166 seconds. A new +10-second
synchronous callback is decision-changing evidence of a longer stable hold and
is expected inside that measured retention window. Reprinting an old result
without executing CPU8 again would not meet the experiment contract.

## Conclusion

`source-accepted-compile-pending`: the exact parent, one logical patch, timing,
failure predicate, terminal, forbidden actions, and mutation gates pass.
Hardware behavior is not established.

## Follow-up

Commit and push the generated patch, then compile it against the exact
held-online parent on Buildbox. CPU9 remains blocked.
