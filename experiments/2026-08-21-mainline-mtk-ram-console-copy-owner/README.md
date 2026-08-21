# Experiment: MediaTek retained ram-console copy owner

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-21-mainline-mtk-ram-console-copy-owner` |
| Status | implementation and Buildbox patch generation pending |
| Subsystem | MediaTek retained ram-console and reserved memory |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-21 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, production A34 provenance owner |

## Question or hypothesis

Can the selected source contract take exactly one private 64 KiB copy through
a transient `MEMREMAP_WB` mapping, unmap before calling the proven parser, and
publish one immutable typed snapshot while remaining default-off and without
creating reset or secure-epoch authority?

## Provenance and environment

- Repository parent: signed and pushed copy-owner audit commit `8516481`.
- Prepared source state through canonical patch `0304`:
  `6a904f3dbbaf8c7946d6a11c13fe768e16e63db6dd5650f2ad3aa57c8b830209`.
- Selected design:
  [`../2026-08-21-mainline-retained-ram-console-copy-owner-audit/DESIGN.md`](../2026-08-21-mainline-retained-ram-console-copy-owner-audit/DESIGN.md).
- Builds must use `./scripts/build-kernel --backend buildbox`; no VM-native
  kernel build is permitted.

## Safety assessment

The implementation is default-off. Generation and focused KUnit use no
device, physical mapping, hardware write, firmware call, reset, provider,
PSCI, or CPU operation. The production source contains one physical read path,
but the Gemini DT consumer remains disabled and no boot candidate or device
attempt is authorized by this experiment.

## Associated code

- `source/mediatek,mt6797-ram-console.yaml` defines one optional consumer with
  one `memory-region`.
- `source/mtk-ram-console-reader.c` contains the one-shot copy owner and seven
  injected-memory tests.
- `source/mtk-ram-console.h` adds only the typed snapshot getter.
- `scripts/source_edits.py` applies three deterministic logical phases.
- `scripts/validate_source.py` and `scripts/validate_patches.py` enforce the
  effect and patch boundaries.
- `scripts/generate-on-buildbox` produces three replayable format-patch files
  from the exact managed source state.
- `results/test-matrix.tsv` freezes seven tests and five design checks.

## Procedure

1. Commit and push this clean experiment scaffold.
2. Run `./scripts/buildbox generate-mtk-ram-console-copy-owner-patches`.
3. Fetch only the validated review with
   `./scripts/buildbox fetch-mtk-ram-console-copy-owner-patches`.
4. Inspect the exact patches and generation/checkpatch receipts.
5. Admit them as canonical patches `0305`--`0307`, update the manifest and
   focused configuration, and audit every manifest profile.
6. Commit and push the exact intended tree before invoking
   `KERNEL_PROFILE=mtk-ram-console-reader-kunit ./scripts/build-kernel --backend buildbox`.
7. Run the bounded network-free QEMU KUnit suite from only the validated
   package and record exact evidence.

## Observations

Pending deterministic generation and proof.

## Analysis

The source deliberately separates physical discovery from the injected copy
state machine. KUnit can prove attempt latching, copy count, parse failure,
second-capture refusal, source independence, and every-bit preservation. It
cannot execute the Gemini physical mapping branch; that remains compile/source
evidence only.

## Conclusion

Pending. A successful build and KUnit run will close only the immutable copy
transport. It will not establish a fresh secure epoch, open A34, admit CPU8 or
CPU9, or justify a device attempt.

## Follow-up

After proof, continue the separate search for independent secure-epoch
attestation. Do not combine reset-history values into authority.
