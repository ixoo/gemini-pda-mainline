# Experiment: A41 ABI-5 six-row fixture evaluator

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-a41-six-row-fixture` |
| Status | `completed` (offline source-contract validation only) |
| Subsystem | arm64 late-CPU capability classification and typed-effect planning |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date(s) | 2026-08-05 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 4, A41 |

## Question or hypothesis

Can ABI 5 evaluate the six previously evidence-dependent Cortex-A72 rows for
two exact source fixtures, preserve the result independently for CPU8 and CPU9,
and derive the exact typed CTR, Spectre-v2, Spectre-v4, and Spectre-BHB effects
without publishing a plan or reaching a live architecture mutation?

The fixtures are deliberately synthetic. A successful result establishes a
pure source evaluator for one accepted evidence domain; it is not runtime
evidence for either physical CPU.

## Provenance and environment

- Kernel release: Linux 7.1.3, official archive SHA-256
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`.
- Source parent: commit
  `7fcc8ca433d2306d2e3d005289d6cf01dfbf0f4c`, tree
  `47133d89119afe60e38057c8ac39840665a1f142`.
- Source commit:
  `57d36fd59821b7de2fd81c938414e7f3c5a54229`, tree
  `253625b12d09411997e1877a58ffd843f417ad7d`, diff SHA-256
  `069ae9b8add4d197bf4c1de7bb0f874db91cd5129df9269aa30d6bf17a052199`.
- Format-patch:
  [0154](../../patches/v7.1.3/0154-arm64-evaluate-MT6797-late-CPU-fixture-evidence.patch),
  SHA-256
  `71908b62b275710223523102448b7fbcecb8cd557a2537259274f7986f7a3445`.
  It uses the synthetic, non-certifying author
  `Gemini Mainline Project <noreply@invalid>`, has no `Signed-off-by`, and is
  not submission-ready.
- Selected series:
  [`patches/series-a72-reject-gate-a41-six-row-fixture`](../../patches/series-a72-reject-gate-a41-six-row-fixture),
  96 entries, SHA-256
  `8c76d1cef1ddd7f452ef7604d6b2581c56c13c1a982e3492e0d0c31f20d9e3da`.
- Ordered patchset identity:
  `1247936c6f7ed6850434cd2a8402a53c9588444a608fa33e965a5f9bf445ed5e`.
- Externally computed selected source-state identity:
  `2750c74f4c2c5c5ce0c07b90e57489fe6d412ec57fec7618b70a327623d5c058`.
- In-source non-circular parent source-state identity:
  `78fcb018e5693cc258127ea6e2655319f55b80135c1230cb42fbf70c6d2e6deb`.
- Selected manifest profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate-a41-six-row-fixture`.
- Ordered configuration-input identity:
  `8ab011246184c5fff4885bdc38fef09d24cc31960235fb7640ea081505949815`.
  This is not a resolved or running `.config` identity.
- Fixture evidence identity:
  `c41b8b84d68f9c0f05a9a047d319de9cfe8d41e8b792cb509ffa4be08341e887`.
- Repository manifest audit scope: 60 profiles; the selected series is a
  canonical-order subsequence.
- Build/compiler: not invoked; no compile claim is made.
- Boot path, target partition, and network access: none.

## Safety and chronology

This milestone did not build a kernel, create a package or boot image, contact
the Gemini, call firmware, request CPU_ON, write a partition, reboot, shut down,
or use the network. The inherited `maxcpus=8` setting, patch-0092
`.cpu_boot = -EAGAIN` veto, and `.cpu_can_disable = false` veto remain in
force.

The latest user-reported chronology was a boot2 start followed by a Gemian
reboot. That sequence is inconclusive and unattributed to this source-only
milestone; it supplies no CPU8/CPU9, fixture, kernel, or hardware-support
evidence.

## Associated code and evidence

- Patch 0154, selected series, profile, and fixture configuration above.
- [Design](DESIGN.md).
- [Exact 40-row result](results/six-row-fixture.tsv).
- [Typed effects](results/typed-effects.tsv).
- [Implementation markers](results/implementation.tsv).
- `scripts/validate.py` and `scripts/test_mutations.py`; both are offline and
  require no privilege or hardware.

## Procedure

1. Start from exact source commit `7fcc8ca4…` and retain the ABI-4 independent
   CPU8/CPU9 target representation.
2. Select the default-off fixture profile. It supplies CPU8 at MPIDR `0x200`
   and CPU9 at MPIDR `0x201`, both with Cortex-A72 MIDR `0x410fd080` and the
   exact register, GIC/hyp, firmware-status, policy, and early-system baseline
   recorded in [the design](DESIGN.md).
3. Classify all 40 local descriptors independently for both targets. Invoke
   only pure descriptor/evidence helpers; do not execute a matcher against the
   running A53 CPUs.
4. Derive independent per-target effects, require equality where the current
   aggregate ABI has one shared setting, and validate every aggregate and
   per-target typed field.
5. Require the exact profile validator and profile preparation callback to
   return `-EAGAIN`, retain runtime and commit blockers, preserve a zero plan
   identity, and leave all admission vetoes unchanged.
6. Run repository, patch-application, source, and mutation validation only. Do
   not build or access the device.

## Observations

- Target 0 is CPU8, MPIDR `0x200`; target 1 is CPU9, MPIDR `0x201`. Both exact
  fixtures carry MIDR `0x410fd080` and REVIDR `0`.
- Each target classifies all 40 compiled rows. The aggregate is exactly 8
  PRESENT and 32 ABSENT, with no unresolved or conflicting row.
- The six previously evidence-dependent rows resolve as follows: GICv5 legacy
  and ICH HCR TDIR are ABSENT; mismatched cache type, Spectre-v2, Spectre-v4,
  and Spectre-BHB are PRESENT.
- Those four newly PRESENT rows join the two static required errata
  (`ARM64_WORKAROUND_1742098` and
  `ARM64_WORKAROUND_SPECULATIVE_AT`) to produce exactly six required rows.
- CTR mismatch requires both targets, CTR_EL0 trapping, and its alternative.
  Spectre-v2 selects mitigated SMC callback state and the Spectre-direct hyp
  vector. Spectre-v4 selects mitigated dynamic firmware state, callbacks for
  both targets, and the firmware alternative. Spectre-BHB selects the A72
  eight-loop method, loop vector template, system method bit `0x1`, and a
  Spectre-direct hyp vector. Compat AES clearing and speculative-AT
  finalization are also set.
- `local_caps_planned` and `effects_planned` become 1 only in the scratch plan.
  The exact profile validator then deliberately returns `-EAGAIN`; preparation
  also returns `-EAGAIN` and retains the runtime-binding and commit-path
  blockers. Every plan-identity word remains zero.
- PLAN_FROZEN, COMMITTED, SYSTEM_VERIFIED, and READY remain unreachable. The
  architecture commit function is still unavailable and fail-stops if reached
  out of order.

## Analysis and claim limit

The source evaluator closes the representation and pure-computation gap for
one tightly bounded fixture. It accepts only the exact named-status evidence
domain, including named SMCCC outcomes, identical target policies, and an
unaffected early-system Spectre-v2/v4/BHB baseline. Unknown firmware status,
reserved register encodings, incomplete validity, target disagreement, changed
policy, or an already affected early baseline fail closed. This result does not
establish behavior for arbitrary firmware responses.

Fixture origin is not runtime provenance. The binding is explicitly FIXTURE,
has no complete matching running identities, and cannot satisfy the runtime
publication guard. No physical CPU register, firmware call, resolved/running
configuration, built/running image, or command line was observed.

## Conclusion

Confirmed for Linux source commit `57d36fd5…`: the implementation state is
exactly `PARTIAL_SIX_ROW_FIXTURE_EVALUATOR`. A41 remains incomplete; no build,
boot candidate, device action, network result, runtime evidence, commit-path,
CPU admission, or hardware-support claim is made.

## Roadmap boundary

[The roadmap](../../docs/ROADMAP.md) alone owns the ordered next action and exit
criteria.
