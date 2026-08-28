# Experiment: durable CPU8 admission entry and zero-request trace

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-mainline-a72-admission-durable-trace` |
| Status | `hardware-free proof passed` |
| Subsystem | pstore retained records, MT6797 CPU8 admission controller |
| Device variant | Planet Computers Gemini PDA, named project device |
| Date(s) | 2026-08-28 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 7, attributable CPU8 admission |

## Question or hypothesis

Can two immutable retained records distinguish controller-core entry from every
consumed zero-request result, while leaving the existing mutable transition
ledger as the sole owner of the admitted physical-request path?

## Provenance and environment

- Exact parent: canonical Linux source through patch `0414`.
- Prepared Buildbox state and integrity: pinned in `contract.json`.
- Build backend: Buildbox only; no native VM build.
- Runtime target in this phase: none.
- Physical parent result: the retired admission candidate's single attempt
  returned without an exact live frame and with a logical-empty transition
  ledger.
- Patch `From:` metadata is the clearly synthetic, non-certifying experiment
  identity and carries no `Signed-off-by`. The archive is not
  submission-ready; actual author metadata and a truthful DCO certification
  are required before any upstream submission.

## Safety assessment

This definition and patch-generation phase is hardware-free. The proposed
default-off writer owns only dmesg records 2 and 3 at `0x44411000` and
`0x44412000`; record 1 remains exclusively owned by the existing transition
ledger. Each writer accepts only the exact logical-empty header, commits a
fixed payload before start and size metadata, performs ordered full readback,
and never clears, repairs, retries, or overwrites a foreign record.

The entry record may be recognized byte-for-byte during a deferred probe
without another write. The terminal writer runs only after the admission core
has consumed its one shot and before any CPU request, for exactly one of three
fixed source-register, derive, or publish failures. It performs no storage,
firmware, I2C, regulator, clock, CPU, watchdog, reset, reboot, or power action.
The existing CPU9, CPU_OFF, and retry vetoes are unchanged.

## Associated code

- `DESIGN.md`: exact address, wire, ordering, ownership, and decision contract.
- `contract.json`: prepared-source and parent-file identities.
- `templates/`: new pstore owner, public API, and injected KUnit suite.
- `scripts/source_edits.py`: deterministic four-stage source edits.
- `scripts/validate_source.py`: source, ordering, effect, and test validator.
- `scripts/generate-patches.py`: four logical format-patches and replay.
- `scripts/generate-on-buildbox`: exact Git/source-state Buildbox entry point.
- `scripts/validate.py`: local definition validator.
- `scripts/run-kunit-qemu`: exact fetched-package, configuration, symbol, and
  no-network QEMU gate.
- `scripts/classify-kunit.py`: exact two-suite, twelve-case runtime classifier.

## Procedure

1. Freeze the exact two-slot wire and controller call ordering.
2. Validate the definition and unsafe mutations without device access.
3. Commit, sign, and push a clean tree.
4. Generate and replay four logical patches against the exact managed
   post-`0414` Buildbox source.
5. Review and integrate the patches, then add an isolated KUnit profile.
6. Commit and push cleanly; compile only with `--backend buildbox` and run the
   focused no-network suites.
7. Only after hardware-free proof, define a distinct production candidate and
   its retained-runtime classifier. A build is not a boot candidate.

## Observations

The exact prepared source places the controller entry after DT supplier
resolution but before binder readiness, ready-token, physical-source capture,
transaction derivation, publication, or `add_cpu(8)`. The current transition
ledger begins only in the binder's CPU-boot callback, so it cannot classify a
zero-request return. Normal ramoops registration is already bypassed while the
transition-ledger profile is selected, leaving records 2 and 3 without a
concurrent Linux owner.

The first exact-source Buildbox generation stopped before producing a patch:
the editor required a physical-source dependency line to be globally unique,
but the controller and its KUnit option each contain that line. The corrected
editor anchors the complete admission-controller Kconfig prefix, preserving
the fail-closed one-match rule. No source package, build, device action, or
candidate resulted from the rejected attempt.

The second generation passed source editing and semantic validation, then
stopped during strict review of patch `0415`. Function continuations and an
uncommented retained-write barrier required style corrections. The only
suppressed check is now `SPLIT_STRING`, narrowly justified by the byte-exact
immutable wire literals; all other strict findings remain fatal. The rejected
attempt produced no admitted package, build, device action, or candidate.

The third generation left only strict continuation-column findings in patch
`0415`. The templates now align continued function parameters exactly to their
opening parentheses and keep production calls on single bounded lines. Again,
no package was admitted and no build, device action, or candidate occurred.

The fourth generation confirmed those columns but rejected their all-space
indentation. They now use tabs for each complete tab stop and spaces only for
the alignment remainder, as required by strict kernel style. No package,
build, device action, or candidate resulted.

The fifth generation made patch `0415` clean and reached patch `0416`, where
strict review rejected seven nested KUnit call continuations. The tests now
store return values before assertions and keep bounded owner calls on one
line. No package, kernel build, device action, or candidate resulted.

The sixth generation reduced patch `0416` to one 106-column loop call. A
loop-local operations alias now shortens the unchanged entry and terminal
calls. No package, kernel build, device action, or candidate resulted.

The seventh exact-source generation passes all four semantic stages, strict
review with only the documented exact-wire split-string exception, checksum
validation, and full-series replay. Canonical patches `0415`--`0418` and the
isolated `a72-admission-trace-kunit` profile are integrated. All 153 manifest
profiles remain canonical-order subsequences of the 410-entry series.

Exact clean commit `43eb3b06` compiles the isolated profile on Buildbox as
`7.1.3-gemini-a72-admission-trace-kunit`. The fetched package passes its full
checksum manifest and contains exactly the two intended KUnit suites. The
first bounded QEMU transcript contained 12 passing cases, but the classifier
failed closed because both six-case suites legitimately emit the same totals
line twice. Signed harness correction `ba171ca0` counts that exact expected
multiplicity. A fresh run of the unchanged package then passes both suites and
all 12 cases with zero failures or skips, no network, no physical DT match,
and zero physical CPU requests, CPU_OFF requests, or retries. No native VM
build, device access, retained physical write, candidate, or boot occurred.

## Analysis

An immutable entry in record 2 proves the controller core ran even when USB
never appears. A mutually exclusive record-3 terminal identifies the only
three failures possible after one-shot consumption and before the request.
Entry without terminal or transition evidence localizes the remaining branch
to prerequisite deferral or interruption before consumption. Entry plus a
committed transition ledger proves the admitted request reached the binder.

## Conclusion

Passed for the hardware-free scope and still inconclusive for hardware. The
successor evidence contract, exact-source patch generation, strict review,
replay, Buildbox compile, package checksums, and both focused KUnit suites now
pass. No production candidate has yet been defined or selected; the device was
not accessed and no physical CPU was requested.

## Follow-up

Define the separate production profile, exact retained-runtime classifier,
container gates, and one-attempt result-to-next-action map without changing
the proven source or DT hypothesis. The ordered next action remains owned by
`docs/ROADMAP.md`.
