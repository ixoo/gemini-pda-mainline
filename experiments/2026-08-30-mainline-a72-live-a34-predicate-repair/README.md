# Experiment: live A34 predicate repair with terminal stage attribution

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-live-a34-predicate-repair` |
| Status | `initial KUnit rejection localized; intersection and stale-test repairs admitted for validation` |
| Subsystem | MT6797 CPU8 derived admission and A34 eligibility |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-30 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

The first exact live CPU8 trigger returned `-EPERM` after consuming the
admission core but before issuing a CPU request. Source registration cannot
return that errno. Source inspection shows that A34 compares the complete raw
physical snapshot against an injected fixture whose unspecified live register
fields are zero. Prior exact device evidence proves several of those fields
are legitimately nonzero, including the per-core MP2 power words and CCI port
state. Does replacing that byte-wide fixture comparison with the documented
CPU8-off predicates allow admission to reach `add_cpu(8)`?

The candidate also retains the exact terminal controller stage and the first
derived-admission substage. This makes every result attributable even if the
A34 diagnosis is incomplete.

## Safety assessment

The stage patch adds observation only. The predicate patch does not write
hardware or add a request path. It keeps exact topology, owner, replay,
provider, MP2 reset, external isolation, DCM, CCI, PWRAP, ABI, reserved-field,
and source-generation checks. Only unrelated online-A53 bits and raw protected
clock/BigiDVFS payload words are excluded from the A34 authorization predicate;
their readbacks remain structurally validated and later effect owners retain
their own exact checks.

The existing live route remains one-shot, CPU8-only, and consumed before the
first owner mutation. CPU9, CPU_OFF, retry, and automatic reboot paths remain
absent. No device action is permitted until both focused KUnit and the exact
candidate profile pass on Buildbox.

## Procedure

1. Generate two normal patches from the exact managed post-`0441` source:
   terminal stage attribution, then semantic A34 predicate repair.
2. Replay and strictly check both patches; run focused source assertions.
3. Admit the patches canonically, commit and push the exact inputs, and build
   focused KUnit plus the physical candidate on Buildbox.
4. Run the no-network live-controller, A34 evaluator, derived-admission, and
   atomic-publication KUnit profiles before assembling any candidate.
5. If all offline gates pass, construct and validate one exact boot image,
   install it to live-GPT inactive `boot2`, verify full readback, and shut down.
6. On one fresh boot, capture the armed frame and issue at most one CPU8
   trigger. Classify CPU8 online, a request-bearing terminal result, or an
   exact pre-request stage. Keep CPU9 vetoed.

## Observations

The predecessor attempt and its exact hashes are recorded in
`../2026-08-30-mainline-a72-cpu8-ready-one-shot/`. Its terminal tuple is
`operation_ret=-1`, `core_consumed=1`, `cpu_requests=0`, with CPUs 0--7 online
and CPUs 8--9 offline.

Prior exact mainline observations record:

- provider `7b/c1/00/46/46`;
- MP2 control `00010132/00010332/00010332`;
- external isolation `00000002`, DCM `00000000`;
- CCI `c0000000/00000000/00000000`; and
- CPU-status movement outside the A72 identity bits while both A72 bits stayed
  clear.

The current A34 positive fixture leaves the two `00010332` words and
`c0000000` as zero and requires an exact `memcmp()` across them and all raw
clock/BigiDVFS payloads. Therefore a valid live snapshot is guaranteed to
differ from that fixture.

## Analysis

Buildbox generated the two patches from repository commit `8f286012` against
the exact managed post-`0441` source state
`24a6905922ecd7d6a618bedd8da3819de5d7d8b97c92f081f95fd9c28e3cf041`
with source-integrity identity
`e62aa413d9a4126e428608e07c4f7e8245ca123a9457b874ef42057b7a620db1`.
The checksum-covered outputs are:

- `0442-soc-mediatek-retain-live-CPU8-admission-failure-stage.patch`:
  `75be779895558c344f0c025a79079569cd00b1325554ae5a51f6d15d757ee24c`;
- `0443-arm64-mediatek-validate-live-A34-admission-predicates.patch`:
  `f4b8d1a32c8cab7296010a9a820d9c3781c1af622abe7b2d500cc2840287b7f2`.

Generation validation found three retained controller failure stages, all 15
derived substages, unchanged request order, and no new CPU request, CPU9,
CPU-off, retry, or hardware-write path. The A34 audit confirms that only A72
CPU-status bits 7:6 remain authorizing; unrelated A53 bits and raw clock and
BigiDVFS payloads are non-authorizing, while topology, owner, replay, provider,
and platform predicates remain fail-closed.

The first live-controller run compiled and executed all 16 current cases with
zero failures. Its inherited 2026-08-28 classifier rejected only because that
older harness expected the pre-`0422` nine-case controller plan instead of the
current ten-case plan. The raw transcript remains ignored evidence. This
experiment now owns a four-profile exact-inventory runner and classifier so
the diagnostic, repaired predicate, derived path, and updated atomic fixture
are each compiled and exercised without networking.

The first current `a72-a34-v2-kunit` run rejected the candidate before any
device action. All 20 late-CPU cases passed, but the positive A34 fixture
returned `-EPERM` in each of its three acceptance checks. The failure exposed
a real predicate contradiction: the live fixture has SPM CPU status
`003dce08/003dceff`, while patch `0443` incorrectly required bits 7:6 to be
clear independently in both words. MT6797 defines CPU-on state from their
intersection, so these exact words prove both A72 bits clear. Follow-up patch
`0444` applies that intersection and tests that CPU8 or CPU9 is still rejected
when its bit becomes set in both words.

The same run also found the pre-existing `direct_snapshot_success` expectation
stale after the default-off binder gate was introduced: an isolated KUnit
profile without the binder correctly returns `-EOPNOTSUPP`, not the closed
owner's later `-EAGAIN`. Patch `0445` makes both affected read-only tests assert
the configuration-selected result. Neither follow-up patch adds a request,
retry, CPU9, CPU-off, hardware-write, or device path.

Fresh canonical-series validation and all four KUnit profiles remain pending.

## Conclusion

Pending.

## Follow-up

Validate patches `0444`--`0445`, rebuild and run all four focused KUnit
profiles, then build and validate one exact physical candidate on Buildbox.
