# Experiment: mainline MTK watchdog boot-status capture

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-21-mainline-mtk-wdt-boot-status-capture` |
| Status | implementation and Git-pinned Buildbox generation lane prepared |
| Subsystem | MediaTek TOPRGU watchdog reset-status observation |
| Device variant | MT6797/Gemini contract; hardware-free implementation phase |
| Date(s) | 2026-08-21 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, production A34 provenance owner |

## Question or hypothesis

Can exact mainline capture the complete raw MT6797 TOPRGU `WDT_STATUS` word
once, before watchdog initialization, and expose an immutable typed snapshot
without classifying reset provenance or making any A34 lifecycle path
reachable?

The falsifiable source claim is one audited `readl()` after successful resource
mapping and before `mtk_wdt_init()`. Invalid, exact, every-bit, and repeat-
capture behavior must be testable without MMIO; the first captured value must
remain immutable.

## Provenance and environment

- Repository parent: signed and pushed audit commit
  `6be86b582a1fcb40d79126a6c83ad24f0e7ad65c`.
- Kernel baseline: pinned Linux 7.1.3, prepared source state
  `efc26dede64ec019c074d29f5cd625767f11fb5a16db376b1549f72a4614a735`,
  and canonical series through patch `0302`.
- Decision authority: the completed
  [A34 provenance-owner audit](../2026-08-21-mainline-a72-a34-provenance-owner-audit/README.md).
- Build policy: commit and push a clean repository input, generate and build
  only on Buildbox, and fetch only checksum-validated packages.
- No source tree is copied to or from Buildbox.

## Safety assessment

The implementation is default-off and hardware-free unless explicitly enabled
in a later named profile. When enabled on MT6797 it performs one read of an
already-mapped status register before watchdog initialization. It adds no
register write, reset action, status classifier, ram-console mapping, A34
caller, lifecycle publication, provider call, P30 arm, PSCI call, CPU request,
boot-veto change, boot image, or device action.

This phase does not contact the Gemini, build a device candidate, write boot2,
reboot, or shut down hardware.

## Associated code

- [`DESIGN.md`](DESIGN.md) freezes the typed snapshot and ordering contract.
- [`contract.json`](contract.json) pins the decision and exact source parent.
- [`results/test-matrix.tsv`](results/test-matrix.tsv) separates source and
  runtime claims.
- [`results/design-validation-20260821.txt`](results/design-validation-20260821.txt)
  records the passing repository and generation-lane validation.
- [`source/mtk_wdt.h`](source/mtk_wdt.h) is the deterministic new-header input.
- [`scripts/source_edits.py`](scripts/source_edits.py) applies the source delta.
- [`scripts/validate_source.py`](scripts/validate_source.py) enforces ordering,
  immutability, test inventory, and effect exclusions.
- [`scripts/validate_patches.py`](scripts/validate_patches.py) validates the one
  generated patch.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox) generates,
  replays, and strictly checks the patch from the exact managed source.
- [`scripts/validate.py`](scripts/validate.py) validates the repository-side
  design and generation lane.

Repository validation:

```sh
python3 experiments/2026-08-21-mainline-mtk-wdt-boot-status-capture/scripts/validate.py
```

After committing and pushing a clean input:

```sh
./scripts/buildbox generate-mtk-wdt-boot-status-patch
./scripts/buildbox fetch-mtk-wdt-boot-status-patch
```

## Procedure

1. Validate the signed audit identity, canonical parent patch, source hashes,
   generator syntax, and effect exclusions.
2. Commit and push the exact repository input to `origin/main`.
3. Let Buildbox fetch that commit into its managed checkout.
4. Verify the prepared source state and exact watchdog source hashes.
5. Apply the deterministic source edits in a temporary reduced Git tree.
6. Validate the source, create one format-patch, replay it byte-for-byte, and
   run strict checkpatch.
7. Fetch only the checksum-validated patch-review package.
8. Admit the canonical patch and isolated source/KUnit profiles only after
   reviewing the exact generated diff.
9. Build and run the four focused KUnit cases on Buildbox/QEMU before advancing
   the Roadmap.

## Observations

The source design and generation lane are prepared. Repository validation,
`bash -n`, ShellCheck, and whitespace validation pass. No patch-generation,
compile, QEMU, boot, or device result is claimed yet.

## Analysis

Keeping the first patch capture-only preserves the independent evidence
boundary selected by the audit. A raw word and validity bit are sufficient for
a later combiner to reason about exact values without letting this driver
invent “safe reset” semantics. Release/acquire publication and first-write-wins
capture make the snapshot immutable for later readers while remaining
testable as pure memory behavior.

The MT6797 match-data flag prevents this audited offset from being read on
other MediaTek variants merely because the default-off option was enabled.
The exported getter still requires the exact bound watchdog device; it does
not add device discovery or a production consumer.

## Conclusion

`inconclusive` until Buildbox generation, strict patch validation, compile,
and focused KUnit pass. The source design is ready for that hardware-free
proof and authorizes no device work.

## Follow-up

The authoritative order remains in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md). Generate and review the single
capture-only patch, admit isolated profiles, then prove compile and the four
focused KUnit cases on Buildbox. Only after that may the separate retained-
ram-console/cold-platform-epoch combiner be audited.
