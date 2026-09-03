# Mainline A72 physical-hotplug lifecycle gate

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-02-mainline-a72-hotplug-lifecycle-gate` |
| Status | hardware-free CPU9 down/restore owner admitted; Buildbox compile pending |
| Subsystem | arm64 CPU hotplug, PSCI, MT6797 A72 membership |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-09-02 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 8, A72 lifecycle correctness |

## Question or hypothesis

Can current mainline physically offline CPU9 while retaining CPU8, CPUs 0--7,
and USB serviceability, then restore CPU9 in the same boot through a separately
owned transaction without retrying an unbounded secure call or entering the
last-A72 power-down branch?

## Provenance and environment

- Repository parent: `0dc07a6bc46da6bb1b074ffee4ce5efd26908411`.
- Canonical series: 474 entries, SHA-256
  `3f55b6be379d540d947c68deb74966b2a7f0ae05819305841f1a077c33da4610`.
- Manifest SHA-256:
  `af9331a6d97a73475243dc1f79df6ca70206d3daf69405c20e9145e7c9930b43`.
- Exact prepared-source file identities are in
  [`contract.json`](contract.json).
- Runtime parent: accepted exact 4+4+2 topology/RAM and concurrent dual-A72
  execution on the named device.
- Build backend for future kernel work: Buildbox only.
- Boot path and target: none in this definition phase.

## Safety assessment

This phase is read-only with respect to the device and kernel source. It
defines no boot candidate and performs no CPU, PSCI, MMIO, watchdog,
retained-RAM, partition, or reboot operation.

The selected eventual physical action is CPU9-off with CPU8 retained. CPU8 as
the last A72, CPUs 0--7, primary boot, and every shared power-policy change are
forbidden. The secure affinity call is explicitly recorded as internally
unbounded; the physical candidate cannot proceed until the independent
watchdog, immutable pre-CPU_OFF attribution, one-query rule, reset-only fault
handling, and exact restore token are implemented and machine-checked.

## Associated code

- [`DESIGN.md`](DESIGN.md) fixes the end state, lifecycle ownership, failure
  boundary, and phase order.
- [`contract.json`](contract.json) is the machine-readable gate.
- [`scripts/validate_contract.py`](scripts/validate_contract.py) validates the
  contract and optionally the exact prepared source.
- [`scripts/test_contract.py`](scripts/test_contract.py) requires critical
  unsafe mutations to fail closed.
- `scripts/source_edits.py`, `validate_source.py`, and
  `test_source_validator.py` define and reject mutations of the first generic
  handoff slice.
- `scripts/generate_patch.py` and `generate-on-buildbox` create a normal
  format-patch from the exact managed source without changing it.
- `scripts/owner_source_edits.py`, `owner_test_edits.py`,
  `validate_owner_source.py`, and `test_owner_source_validator.py` define the
  second hardware-free owner slice and its rejecting source oracle.
- `scripts/owner_terminal_parent_fix_edits.py` and
  `test_owner_terminal_parent_validator.py` define the follow-up correction
  and six rejecting mutations for the finalized CPU8/CPU9 parent pair.
- `scripts/generate_owner_patches.py` and `generate-owner-on-buildbox` create
  the exact owner/test pair plus its follow-up correction from the canonical
  prepared source through `0485`, while proving the first two patch identities
  remain unchanged.
- [`results/contract-validation-20260902.txt`](results/contract-validation-20260902.txt)
  records the local contract/mutation pass and exact Buildbox prepared-source
  validation.
- [`results/generic-down-handoff-generation-aa014ea0-20260902.txt`](results/generic-down-handoff-generation-aa014ea0-20260902.txt)
  pins the generated patch, strict review, replay, mutation, and all-profile
  invariant results.
- [`results/generic-down-handoff-build-1f17299f-20260902.txt`](results/generic-down-handoff-build-1f17299f-20260902.txt)
  pins the exact pushed Buildbox compile, validated package identities, and
  linked handoff symbols.
- [`results/hardware-free-owner-generation-d266765e-20260902.txt`](results/hardware-free-owner-generation-d266765e-20260902.txt)
  pins the exact generated owner/test patches, independent review correction,
  strict review, replay, mutation, and all-profile invariant results.
- [`results/hardware-free-owner-kunit-attempt-1-20260902.txt`](results/hardware-free-owner-kunit-attempt-1-20260902.txt)
  records the first no-network QEMU run, its 56 passes and four attributable
  failures, and the common terminal-parent predicate defect.
- [`results/hardware-free-owner-terminal-parent-generation-9a9f0455-20260903.txt`](results/hardware-free-owner-terminal-parent-generation-9a9f0455-20260903.txt)
  pins the exact follow-up generation, preserved predecessor identities,
  strict review, replay, 27 total rejecting mutations, and profile invariant.
- [`../../patches/v7.1.3/0483-arm64-add-CPU-down-lifecycle-handoffs.patch`](../../patches/v7.1.3/0483-arm64-add-CPU-down-lifecycle-handoffs.patch)
  is the exact admitted no-op-by-default implementation.
- [`../../patches/v7.1.3/0484-arm64-mediatek-add-hardware-free-CPU9-hotplug-owner.patch`](../../patches/v7.1.3/0484-arm64-mediatek-add-hardware-free-CPU9-hotplug-owner.patch)
  is the exact admitted one-attempt CPU9-down and distinct-restore owner.
- [`../../patches/v7.1.3/0485-arm64-mediatek-test-hardware-free-CPU9-hotplug-owner.patch`](../../patches/v7.1.3/0485-arm64-mediatek-test-hardware-free-CPU9-hotplug-owner.patch)
  is its focused hardware-free KUnit coverage.
- [`../../patches/v7.1.3/0486-arm64-mediatek-validate-finalized-CPU9-before-hotplug.patch`](../../patches/v7.1.3/0486-arm64-mediatek-validate-finalized-CPU9-before-hotplug.patch)
  preserves the active parent rule and adds the exact finalized-pair rule.

Patches `0483`--`0486` are experiment-only archives with a synthetic,
non-certifying author identity, no DCO sign-off, and are not submission-ready.
Upstream submission requires the actual author metadata and truthful
certification.

## Procedure

1. Pin the current repository, canonical series, manifest, prepared-source
   files, and accepted runtime parents.
2. Audit generic `cpu_down`, arm64 target disable/die/kill, MT6797 P32 guards,
   and membership attempts.
3. Select CPU9-off with CPU8 retained; reject last-A72-off.
4. Define the exact generic, target, controller, physical readback, restore,
   watchdog, and recovery handoffs.
5. Validate the contract locally and against the Buildbox-managed source; run
   the rejecting mutation suite.
6. Do not build or boot until each hardware-free implementation phase passes.

## Observations

The current source has no normal A72 down or restore owner and deliberately
hides the hotplug control. P32 guards protect failed CPU-up rollback only. The
secure-source audit establishes a per-core-only CPU9-off effect set when CPU8
remains present, but also establishes that the active affinity call contains
unbounded waits.

The exact contract passed locally, the 21 unsafe mutations all failed closed,
and the same validator passed against the six hash-pinned files in the
Buildbox-managed prepared source.

The first generation from repository commit `36f746d6...` reached strict
Checkpatch and stopped on five declaration-alignment checks. It produced no
admitted patch. The alignment-only generator correction in `aa014ea0...`
then produced exact patch `0483`: source validation and replay passed, all ten
unsafe source mutations failed closed, and strict Checkpatch reported zero
errors, warnings, or checks. The 165-profile canonical-series invariant passes
with `0483` appended as entry 475.

Exact pushed repository commit `1f17299f...` then compiled successfully on
Buildbox with the isolated `a72-cpu9-progress-candidate` profile. Package
validation passed for `Image`, `Image.gz`, `System.map`, all 123 DTBs,
configuration, and provenance. `System.map` contains all four new arm64
handoff dispatchers. The fetched `Image.gz` identity is
`6356e5bbe433aa76846a444c27336e2b458d004a6cb84774005c0138677843fa`.
One pre-existing frame-size warning remains in an MT6797 A72 membership test
helper; no warning arose from patch `0483`.

The first complete owner package at repository commit `95bb4265...` passed
strict Checkpatch, source replay, 20 rejecting source mutations, and all five
focused lifecycle cases. Independent pre-admission review rejected it because
the restore mint did not reject reserved or overflowing generation/cookie
values. No canonical patch was admitted from that package. Commit
`d266765e...` added the symmetric restore guard and a dedicated rejecting
mutation. Buildbox regenerated exact patches `0484` and `0485`; strict review
and replay passed, all 21 unsafe source mutations failed closed, and the five
focused lifecycle cases remained present. The admitted patch SHA-256 values
are `7f78083783287d2a270197fc537c1a1eba41446a5eb2182be102d44e6995af27`
and `443e2983110c743ecb3f93439f71ea2631a19cc0b66cb58cb208b162487e08e7`.
They append as canonical entries 476--477; the resulting series SHA-256 is
`6e0b25585badd53b66723f9c68213e87d29ca60175afdb4efb1c033cf2baacbb`,
and all 165 manifest profiles retain canonical-order subsequences.

The user-reported boot immediately before this audit did not produce a boot
cycle: Gemian remained reachable under the unchanged boot ID for the complete
observation window, and the mainline netcat endpoint did not appear. It is not
classified as a kernel attempt.

The exact admitted `0484`--`0485` series then compiled successfully on
Buildbox as repository commit `7fbd9ac1...`. Its no-network four-vCPU QEMU
gate ran all 60 expected cases. All 55 pre-existing owner, transition, and
binder cases passed, as did the new entry-rejection case. The other four new
cases failed at the same first down-preparation assertion with `-EPERM`.
Source audit traced this to reuse of the active-CPU9 parent predicate: that
predicate correctly requires retired slot 1 to be empty while CPU9 bring-up is
active, but successful CPU9 finalization correctly fills slot 1 before the
down lifecycle begins. The runtime result is an actionable implementation
defect, not hardware evidence; no physical effect or device action occurred.

Buildbox generation at exact pushed commit `9a9f0455...` then preserved the
admitted `0484` and `0485` byte identities and produced standalone follow-up
`0486` with SHA-256
`a583e8184b39dc51aa0556a5531ebe6d403e54ad8106ca8dbebbf1259c2ea019`.
Strict Checkpatch, exact replay, all 21 predecessor mutations, and all six new
terminal-parent mutations pass. The resulting 475-patch canonical series has
SHA-256 `640f8757299432cf125d34f3049e2aa7b1f1c19b0688e46cbafd1bdb7749bd19`,
and all 165 manifest profiles retain canonical-order subsequences.

## Analysis

The accepted online/topology/load evidence closes the entry-state uncertainty
that blocked earlier offlining designs. It does not close CPU-down ownership,
the active-affinity timeout, or a same-boot restore. Exposing the existing
generic path would skip all three requirements.

A CPU9-first transaction is decision-bearing because its successful effect set
does not include cluster shutdown. The independent watchdog converts a stuck
secure call into bounded reset recovery, not into a successful hotplug return.
Only the independent per-core readback and retained-CPU observation can permit
the membership commit and subsequent restore.

## Conclusion

The physical hypothesis remains untested. The exact parent code is confirmed
incapable of safely running the experiment as-is. Patch `0483` supplies and
Buildbox-proves the generic ownership handoffs. Patches `0484`--`0485` add the
hardware-free one-attempt CPU9-down owner, single affinity-proof budget,
distinct parent-linked restore, and reset-only post-commit failure model, but
their first runtime gate exposed the finalized parent-state defect above.
Patch `0486` corrects that source defect without weakening the active-CPU9
rule. The combined series binds no callback, preserves the MT6797 disable veto,
and performs no physical action. The final requirement remains physical
CPU9-off and same-boot CPU9 restore.

## Follow-up

Rebuild the admitted `0486` series on Buildbox and rerun the identical 60-case
no-network gate. Only a complete pass permits the independently bounded
physical executor, watchdog, readback, and callback-binding slice; no boot
candidate is selected here.
