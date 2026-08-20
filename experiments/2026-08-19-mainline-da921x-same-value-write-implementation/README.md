# Experiment: mainline DA921x same-value-write implementation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-19-mainline-da921x-same-value-write-implementation` |
| Status | `running`; first formal patch generation style-rejected, corrected, no candidate |
| Subsystem | DA921x regulator, MT6797 I2C6 ledger and transaction window |
| Device variant | Planet Gemini PDA named unit; current work hardware-free |
| Date(s) | 2026-08-19 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 6 |

## Question or hypothesis

Can the exact contract admitted by the fresh pre-write review be represented as
three logical, default-off kernel patches and exhaustively exercised without a
physical adapter before any candidate or device action exists?

The source claim is falsifiable: the production sequence must consume exactly
12 transfers under one root lock, attempt `[0xda, 0x46]` once at ordinal 6,
stop on every error or mismatch, and restore retries on every exit. The
controller must independently attribute both write bytes.

## Provenance and environment

- Fixed review parent: `ca3caa3e3c814da61a0ca113c69fc87e3bc1140e`.
- Frozen review contract: [pre-write contract](../2026-08-19-mainline-da921x-same-value-write-preflight-review/contract.json),
  SHA-256 `3f851743de01404a728327a9763aadf6c6dc4ab30024a9be7912841500a5850b`.
- Managed Buildbox parent state:
  `3cd27f8d5432e8de0a495d2b9f9c266f8de9cb78077f9091bcc35a2548edcdfc`.
- The exact five parent file checksums are pinned in
  [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox).
- No native VM build is permitted. No kernel compile or device action has yet
  occurred in this experiment.

## Safety assessment

The current phase edits bounded temporary source views on Buildbox and creates
normal patches. It performs no kernel boot, I2C transaction, device access,
boot image construction, partition write, regulator action, or CPU request.

Patch 0291 will contain a real register-write path, but it is default-off and
reachable only through one exact-token device attribute in the isolated
profile. A source patch, compile result, or KUnit pass does not authorize that
path on hardware. Physical writing remains closed until every later package,
candidate, collector, predeployment, evidence-publication, and serviceability
gate passes. CPU8 and CPU9 remain offline and unrequested.

## Associated code

- [`contract.json`](contract.json) freezes the three-patch plan and workflow.
- [`DESIGN.md`](DESIGN.md) describes the production and test seams.
- [`scripts/validate.py`](scripts/validate.py) validates the implementation
  contract and 16 unsafe mutations.
- [`scripts/source_edits.py`](scripts/source_edits.py) applies the three
  deterministic logical source phases.
- [`scripts/validate_source.py`](scripts/validate_source.py) validates the
  complete edited-source semantics.
- [`scripts/validate_patches.py`](scripts/validate_patches.py) validates the
  normal patch inventory, logical path boundaries, and hardware-free test.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox) generates,
  replays, source-validates, and strict-style-checks the patches on Buildbox.
- [`results/source-tool-validation-20260819.txt`](results/source-tool-validation-20260819.txt)
  records the pre-generation validations.
- [`results/patch-generation-attempt-73fb7a3-20260819.txt`](results/patch-generation-attempt-73fb7a3-20260819.txt)
  records the first formal Buildbox rejection and bounded correction check.

## Procedure

1. Validate the implementation contract against the checksum-pinned pre-write
   review.
2. Apply the three deterministic phases to bounded copies of the exact managed
   Buildbox parent files.
3. Validate exact source semantics and strict kernel style.
4. Commit and push these clean project inputs.
5. Generate and fetch three normal patches through the first-class Buildbox
   lane; replay them and reject any path, payload, safety, or identity drift.
6. Admit the exact patches to canonical order, add isolated implementation and
   KUnit profiles, and audit every manifest profile.
7. Build the exact clean pushed KUnit profile through Buildbox and run the
   hardware-free suite before constructing any boot candidate.

## Observations

- The deterministic editor applies cleanly to the exact managed parent.
- The edited-source validator passes the three logical patches, six KUnit
  cases, all 12 transfer-failure ordinals, and all 11 read-value mismatches.
- The prototype combined-delta check reported zero errors, zero warnings, and
  zero checks across 533 changed lines. Formal per-patch checking then exposed
  14 KUnit-only indentation checks in patch 0292; patches 0290 and 0291 were
  clean.
- After correcting only those generated-source formatting defects, a bounded
  Buildbox file check reports zero errors, zero warnings, and zero checks
  across the 309-line generated KUnit source. Formal generation must still be
  rerun at the corrected immutable project commit.
- The KUnit fixture uses address `0x2a`, registers no adapter or client, maps no
  MMIO, and performs no physical transfer.
- No kernel was compiled and no boot candidate or device action exists.

## Analysis

The controller patch and regulator patch are intentionally separate. The
controller owns physical attribution and can validate the exact retained
pointer-read prefix while the caller already holds the root lock. The regulator
owns the one-shot policy, exact bytes, action order, failure states, and retry
lifetime. A third patch tests the production sequence through injected
read-only ledger, transfer, and delay seams.

This avoids using the B2 single-transfer helper, which would release the root
lock between actions. The production operations instead bind the sequence to
`__i2c_transfer()` only after one lock is held, while KUnit binds the same
sequence to an unregistered fake.

## Conclusion

`confirmed` only for corrected pre-generation source readiness: the exact
deterministic delta applies, passes semantic validation, and the corrected
generated KUnit file is strict-style clean. The superseded formal attempt at
`73fb7a3` remains rejected.

Implementation is not complete. Normal patch generation, canonical admission,
the focused Buildbox compile, and KUnit execution remain outstanding. No
physical DA921x write is authorized and CPU8/CPU9 admission remains closed.

## Follow-up

Generate and fetch the exact three-patch review from the clean pushed commit.
The authoritative ordered exit remains
[Roadmap Gate 6](../../docs/ROADMAP.md#6-prove-one-bounded-writable-operation).
