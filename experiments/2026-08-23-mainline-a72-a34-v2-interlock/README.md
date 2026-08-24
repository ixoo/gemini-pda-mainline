# Experiment: mainline A72 A34-v2 evaluator and P30 interlock

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-23-mainline-a72-a34-v2-interlock` |
| Status | completed hardware-free compile and focused runtime proof |
| Subsystem | MT6797 A72 A34 input and P30 pristine exclusion |
| Device variant | Gemini PDA contract; injected hardware-free phase |
| Date(s) | 2026-08-23 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, pre-publication A34 proof |

## Question or hypothesis

Can three default-off source changes close the hardware-free prerequisites
selected by the publication-contract audit without opening the membership
owner or changing either CPU veto?

The changes are: an opaque P30 pristine claim, compositor-owned CPU method and
MPIDR identity in direct-state ABI 2, and A34 ABI 2 consuming exactly one
direct-state record plus one typed replay-applicability record.

## Provenance and environment

- Decision authority: the
  [publication-contract audit](../2026-08-23-mainline-a72-a34-publication-contract-audit/README.md).
- Repository parent: signed and pushed commit `83f9ef6c`.
- Canonical kernel parent: patch `0341`.
- Managed prepared source state and exact file identities are pinned in
  [`contract.json`](contract.json).
- Generation and compilation use Buildbox only. No native VM build is
  permitted and no source tree is copied to or from Buildbox.

## Safety assessment

This phase is hardware-free. It adds no production caller, lifecycle
publication, physical source binding, DT enablement, MMIO, SMC, I2C transfer,
provider action, P30 arm, CPU_ON, CPU_OFF, boot image, device access, or
partition write.

The A34 positive record is deliberately an over-strict injected fixture. It
is an executable ABI contract, not physical evidence and not authority to bind
a device reader. The membership owner remains `CLOSED / UNINITIALIZED` after
every case.

## Associated code

- [`source/mt6797_a72_a34_evaluator_test.c`](source/mt6797_a72_a34_evaluator_test.c)
  is the replacement focused A34-v2 suite.
- [`scripts/source_edits.py`](scripts/source_edits.py) applies the three exact
  logical source phases to the pinned managed files.
- [`scripts/validate_source.py`](scripts/validate_source.py) validates each
  cumulative source phase and the closed-lifecycle invariants.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox) creates three
  normal format patches from the exact prepared source, replays them, and runs
  strict checkpatch.
- [`scripts/validate_patch.py`](scripts/validate_patch.py) enforces patch
  separation and forbids publication, physical, or CPU effects.

## Procedure

1. Validate the repository-side contract and deterministic source editor.
2. Commit and push a clean exact input.
3. Generate three normal patches on Buildbox from the managed source through
   patch `0341`.
4. Require exact replay, semantic validation, strict checkpatch, and a
   checksum-covered review package.
5. Admit the reviewed patches canonically and add one isolated KUnit profile.
6. Build that profile on Buildbox and reject any new over-limit stack frame.
7. Run only the A34-v2 and P30 focused suites under bounded no-network arm64
   QEMU.

## Observations

The first three generation commits failed closed before patch creation: two
repository-side validators used boundaries that included adjacent declarations,
and one direct-test edit used the pre-stack-fix value rather than the pinned
pointer workspace. Commit `940d7e05` then passed every semantic phase and
exact replay but strict checkpatch rejected eight declaration lines ending in
`(`. Those failures changed only the deterministic editor or its validators.

Signed and pushed commit `91b6993a` passed all three cumulative source
validators, the three-patch separation validator, byte-exact replay, and
strict checkpatch with `0 errors, 0 warnings, 0 checks` for every patch. The
checksum-covered package is `a34-v2-interlock-91b6993a4ffc`; exact admitted
patch identities are recorded in [`contract.json`](contract.json). No kernel
was compiled and no QEMU or device action occurred during generation.

The exact admitted commit `b89e284f` then passed the isolated Buildbox compile
and package validation as release `7.1.3-gemini-a34-v2-kunit`. Its build log
introduced no over-limit stack frame. The two reported large frames—2,768
bytes in the late CPU profile and 6,672 bytes in the membership token
builder—are the same inherited warnings already classified by the parent
direct-state experiment. The log also retained one unused CPUHP inventory
helper warning and the canonical patch-0261 whitespace notice.

The checksum-validated `Image` then ran under bounded arm64 QEMU with networking
disabled. The exact three selected suites passed: 20 late-startup/P30 cases,
five A34-v2 cases, and seven direct-state-v2 cases. All 32 passed with no
failure or skip. The subsequent missing-root-filesystem panic is the declared
post-test VM terminal state. Exact compile and runtime records are in
[`results/buildbox-compile-pass-20260824.txt`](results/buildbox-compile-pass-20260824.txt)
and [`results/kunit-qemu-pass-20260824.txt`](results/kunit-qemu-pass-20260824.txt).

## Analysis

The P30 claim is deliberately narrower than a lifecycle state. It can be
acquired only from exact pristine state, blocks only the sole pristine-to-
active `prepare()` edge, uses an opaque cookie for release, and is invisible
in the public protocol snapshot after release.

Direct-state ABI 2 adds only target identity already owned by the compositor:
both enable methods must resolve to the MT6797 PSCI operations and both logical
MPIDRs must be exactly `0x200` and `0x201`. The existing hotplug, transition,
source-registry, owner-stability, zero-on-error, and no-effect rules remain.

A34 ABI 2 removes reset-cause and all duplicated caller-populated topology,
owner, counter, and P30 fields. Its only positive fixture is the exact injected
direct-state record plus typed applicable primary-BL31 replay clear and zero
private replay value. Because there is no production caller or positive replay
owner, a hardware-free pass cannot open A34 in production.

## Conclusion

The three normal patches are generated, exactly replayed, strictly checked,
admitted to the canonical series, compiled on Buildbox without a new stack
warning, and covered by 32/32 exact no-network arm64 KUnit tests. This closes
the hardware-free A34-v2 input and P30 exclusion proof. It does not publish the
membership owner, bind physical readers, or create a boot candidate.

## Follow-up

The authoritative next action is in
[Roadmap Gate 7](../../docs/ROADMAP.md#7-bring-up-cpu8). Atomic publication is
not part of this completed experiment.
