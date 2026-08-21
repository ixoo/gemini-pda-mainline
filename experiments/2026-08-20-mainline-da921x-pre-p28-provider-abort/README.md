# Experiment: mainline DA921x pre-P28 provider abort

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-20-mainline-da921x-pre-p28-provider-abort` |
| Status | Buildbox compile passed; QEMU stack remediation pending regeneration |
| Subsystem | MT6797 CPU8 membership owner and DA921x Buck B provider |
| Device variant | Planet Gemini PDA named development unit |
| Date(s) | 2026-08-20 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7 |

Attempt 1 on published commit `feaa97f601925b68484ec222f385adca70175215`
passed contract, edited-source, patch-inventory, and exact replay validation.
Strict checkpatch rejected 74 formatting checks with zero warnings and zero
errors, so no validated package was published. The exact bounded result is in
[`results/patch-generation-attempt-1-checkpatch-20260820.txt`](results/patch-generation-attempt-1-checkpatch-20260820.txt).
Attempt 2 on `0e2a1a74642d58542834cb876dc3d80b1663cd4e` applied all
four source phases, then exposed one stale validator boundary for the newly
wrapped acquire signature; no package was accepted. The bounded trace result
is in
[`results/patch-generation-attempt-2-validator-boundary-20260820.txt`](results/patch-generation-attempt-2-validator-boundary-20260820.txt).
Attempt 3 on `700a87bf4967e8ab44d954c83d7d2a7f96f69eb4` restored all
semantic and replay validation and reduced strict checkpatch from 74 to 17
alignment-only checks, with patch `0298` already clean. The remaining exact
column corrections and bounded result are recorded in
[`results/patch-generation-attempt-3-checkpatch-20260820.txt`](results/patch-generation-attempt-3-checkpatch-20260820.txt).
Attempt 4 on `52451875a7bd1e7daa554b0d2b8feeeb8a9a4e1e` left only one
four-column continuation offset in patch `0297`; the other three patches were
strict-clean and all semantic/replay validators passed. The bounded result is
in
[`results/patch-generation-attempt-4-checkpatch-20260820.txt`](results/patch-generation-attempt-4-checkpatch-20260820.txt).
Attempt 5 on exact clean commit
`809b0caf263bb180a4dddf2a52b06fb3fc5bcb56` passed contract,
edited-source, inventory, exact replay, and strict checkpatch validation. The
validated package `da921x-pre-p28-provider-abort-patches-809b0caf263b` contains
four patches with zero errors, warnings, or checks. Their exact SHA-256
identities are pinned in [`contract.json`](contract.json) and verified against
the canonical import by [`scripts/validate.py`](scripts/validate.py). The
bounded result is in
[`results/patch-generation-attempt-5-success-20260820.txt`](results/patch-generation-attempt-5-success-20260820.txt).

The exact focused Buildbox build from signed commit
`14723ceee84f94fd5ce6b9b26f5f1357ec5e637f` compiled and passed package
validation. QEMU attempt 1 then failed before provider semantics: the first
case's large automatic membership state overflowed the 16 KiB arm64 kernel
stack while being cleared. The fail-closed classifier rejected the incomplete
KTAP. The remediation moves all six cases and the release-callback snapshot to
KUnit-managed heap state; it changes test storage only, not the production
owner/provider implementation. The bounded failure is in
[`results/qemu-attempt-1-stack-overflow-20260820.txt`](results/qemu-attempt-1-stack-overflow-20260820.txt).

## Question or hypothesis

Can the current closed membership owner consume exactly one successful DA921x
vote, release it before P28 with the exact provider handle, and retire the P27
prefix without making P28, CPU_ON, or production hotplug reachable?

The falsifiable claim is that a default-off production seam can map every
ambiguous acquire/release return to reset-only `FAULT_UNKNOWN`, while the sole
successful path advances `HELD -> RELEASE_INFLIGHT -> NONE` and reaches P29
only with an exact positive-abort proof.

## Provenance and environment

- Exact parent: Linux 7.1.3 plus canonical patches through `0295`.
- Prepared parent source-state SHA-256:
  `2e804ec33835f0e14b050773c52d1d39acf573e6e71eee8257f8c282b54c8f2a`.
- [`contract.json`](contract.json) pins all edited parent file identities.
- Patch generation and kernel builds run only on Buildbox from a clean pushed
  repository commit. No native VM build is permitted.
- The focused proof uses an unregistered in-memory I2C adapter. It registers
  no adapter, client, device, regulator consumer, MMIO range, or CPU callback.

## Safety assessment

The lifecycle owner remains closed with no production `CLOSED -> AVAILABLE`
writer or CPUHP caller. The new config is default-off. P27 and P28 remain
attestation ledgers rather than hardware executors. The test makes no physical
DA921x call, P28 effect, CPU_ON, CPU_OFF, boot image, boot2 write, or device
connection. A26 and A14 remain unchanged; CPU8 and CPU9 admission stays closed.

## Associated code

- [`DESIGN.md`](DESIGN.md) freezes the state edges and terminal policy.
- [`scripts/source_edits.py`](scripts/source_edits.py) applies four logical
  source phases to the exact prepared Buildbox parent.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox) creates normal
  `git format-patch` output, replays it, validates the edited source, and runs
  strict checkpatch.
- [`source/da9213-legacy-membership-test.c`](source/da9213-legacy-membership-test.c)
  is the hardware-free integration KUnit source.
- [`scripts/validate.py`](scripts/validate.py),
  [`scripts/validate_source.py`](scripts/validate_source.py), and
  [`scripts/validate_patches.py`](scripts/validate_patches.py) fail closed on
  contract, source, patch, profile, and forbidden-effect drift.
- [`scripts/run-kunit-qemu`](scripts/run-kunit-qemu) accepts only the exact
  published Buildbox package and one focused KUnit suite; its separate
  [`scripts/classify-kunit.py`](scripts/classify-kunit.py) requires exact KTAP
  success before the expected rootfs-panic timeout boundary.
- [`scripts/test-kunit-classifier.py`](scripts/test-kunit-classifier.py)
  demonstrates fail-closed rejection of altered suite, case, plan, checksum,
  kernel-release, exit, and panic-boundary evidence.

## Planned procedure

1. Commit and push the source tooling and isolated profiles. Complete.
2. Generate four normal patches on the integrity-verified Buildbox parent.
   Complete.
3. Fetch only the validated patch package, review it, and import it at the end
   of canonical `patches/series`. Complete.
4. Build the exact integration KUnit profile on Buildbox. Initial compile
   passed; stack-safe test regeneration and rebuild pending.
5. Run the focused suite under QEMU with no network and classify the KTAP. The
   first run failed before provider semantics; a distinct stack-safe run is
   pending.
6. Record exact package, config, Image, QEMU, and suite identities.

## Decision rule

The slice passes only if all six test families pass, source replay is exact,
strict checkpatch and Buildbox compile pass, and no P28/CPU/device path becomes
reachable. Any incomplete acquire or release proof is terminal, keeps
conservative provider ownership, consumes its one-shot budget, and permits no
retry or speculative inverse.

## Follow-up

Passing this experiment will close only the pre-P28 owner/provider inverse.
It will not authorize a physical provider call or CPU8 boot. The next boundary
must be selected separately by [Roadmap Gate 7](../../docs/ROADMAP.md#7-bring-up-cpu8).
