# Experiment: mainline MediaTek retained ram-console parser

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-21-mainline-mtk-ram-console-parser` |
| Status | canonical patch `0304` proven by Buildbox compile and focused QEMU KUnit |
| Subsystem | MediaTek retained preloader/LK ram-console wire format |
| Device variant | MT6797/Gemini contract; hardware-free implementation phase |
| Date(s) | 2026-08-21 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, production A34 provenance owner |

## Question or hypothesis

Can exact mainline validate the audited 64-byte retained ram-console prefix
and return the complete current-preloader status word from a caller-owned copy,
while rejecting corruption and adding no physical mapping, reset classifier,
or A34 lifecycle caller?

## Provenance and environment

- Repository parent: signed and pushed commit
  `97d9a02ab58dc967d0683380dbe3da481ccf8885`.
- Source authority: the completed
  [retained ram-console authority audit](../2026-08-21-mainline-retained-ram-console-authority-audit/README.md).
- Kernel baseline: pinned Linux 7.1.3 prepared source state
  `2719c3b91f238e83b32f22e19bc94c15a4b4aeb6a886a6548e8952b28497da9e`,
  containing the canonical series through patch `0303`.
- Build policy: commit and push a clean repository input, generate and build
  only on Buildbox, and fetch only checksum-validated packages.
- No source tree is copied to or from Buildbox.

## Safety assessment

The proposed implementation is default-off and parses ordinary caller-owned
memory only. It has no DT lookup, reserved-memory binding, `no-map` override,
physical mapping, MMIO, watchdog action, reset action, status classifier,
firmware call, provider action, P30 arm, PSCI call, CPU request, boot-veto
change, boot image, or device action.

This phase does not contact the Gemini, build a device candidate, write boot2,
reboot, or shut down hardware.

## Associated code

- [`DESIGN.md`](DESIGN.md) freezes the strict wire-format contract.
- [`contract.json`](contract.json) pins the audit and prepared source state.
- [`results/test-matrix.tsv`](results/test-matrix.tsv) separates parser claims
  from deferred hardware/authority claims.
- [`results/patch-generation-attempt-1-checkpatch-20260821.txt`](results/patch-generation-attempt-1-checkpatch-20260821.txt)
  records the first exact generation's strict alignment rejection.
- [`results/patch-generation-attempt-2-checkpatch-20260821.txt`](results/patch-generation-attempt-2-checkpatch-20260821.txt)
  records the second exact generation's narrower alignment rejection.
- [`results/patch-generation-attempt-3-checkpatch-20260821.txt`](results/patch-generation-attempt-3-checkpatch-20260821.txt)
  records the third exact generation's prototype-only alignment rejection.
- [`results/patch-generation-validated-20260821.txt`](results/patch-generation-validated-20260821.txt)
  records the fourth exact generation's package, patch, replay, and clean
  strict-check identities.
- [`results/buildbox-build-validated-20260821.txt`](results/buildbox-build-validated-20260821.txt)
  records the exact clean Buildbox package, configuration, image, and linked
  parser/test identities.
- [`results/qemu-kunit-validated-20260821.txt`](results/qemu-kunit-validated-20260821.txt)
  records the checksum-bound eight-case network-free runtime proof.
- [`source/mtk-ram-console.c`](source/mtk-ram-console.c) and
  [`source/mtk-ram-console.h`](source/mtk-ram-console.h) are deterministic
  source inputs.
- [`scripts/source_edits.py`](scripts/source_edits.py) applies the source delta.
- [`scripts/validate_source.py`](scripts/validate_source.py) enforces exact
  bounds checks, test inventory, and effect exclusions.
- [`scripts/validate_patches.py`](scripts/validate_patches.py) validates the
  generated one-patch review.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox) generates,
  replays, and strictly checks the patch from the managed source.
- [`scripts/run-kunit-qemu`](scripts/run-kunit-qemu) and
  [`scripts/classify-kunit.py`](scripts/classify-kunit.py) require the exact
  checksum-validated KUnit package and classify only the eight-case suite.
- [`scripts/test-kunit-classifier.py`](scripts/test-kunit-classifier.py)
  exercises the evidence classifier without a kernel build.
- [`scripts/validate.py`](scripts/validate.py) validates the repository-side
  design and generation lane.

Repository validation:

```sh
python3 experiments/2026-08-21-mainline-mtk-ram-console-parser/scripts/validate.py
```

The completed generation used:

```sh
./scripts/buildbox generate-mtk-ram-console-parser-patch
./scripts/buildbox fetch-mtk-ram-console-parser-patch
```

After canonical admission is committed and pushed, compile and fetch only the
focused profile:

```sh
KERNEL_PROFILE=mtk-ram-console-parser-kunit \
  ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mtk-ram-console-parser-kunit \
  ./scripts/buildbox fetch-package
```

## Procedure

1. Validate the signed audit identity, source assets, generator syntax, and
   effect exclusions.
2. Commit and push the exact repository input to `origin/main`.
3. Let Buildbox fetch that commit into its managed checkout.
4. Verify the prepared source state and exact MediaTek Kconfig/Makefile hashes.
5. Apply deterministic source edits in a temporary reduced Git tree.
6. Validate the source, create one format-patch, replay it byte-for-byte, and
   run strict checkpatch.
7. Fetch only the checksum-validated patch-review package.
8. Admit a canonical patch and isolated source/KUnit profiles only after exact
   diff review.
9. Cross-build and run the eight focused KUnit cases before considering a
   separate physical mapping boundary.

## Observations

The audit selected only the pure parser. The first exact Buildbox generation
passed source semantics, patch inventory, and byte-for-byte replay, then strict
checkpatch rejected one continuation-line alignment in the disabled-config
header stub. A first correction still placed the continuation four columns too
far right because the split return type leaves the function at column one; the
second exact Buildbox attempt rejected that remaining check. Correcting both
continuations then made the split definition pass, while the one-line `int`
prototype required its original four-column offset; the third exact attempt
rejected only that prototype. All three partial packages were removed and no
patch was admitted from them. Definition and prototype were then aligned with
their respective opening parentheses. The fourth exact Buildbox generation
passed source semantics, one-patch inventory, byte-for-byte replay, and strict
checkpatch with zero errors, warnings, or checks across 397 lines. Its generated
patch SHA-256 is
`5d0f76141311b3036eddeca5672ef090d36b1fd040038a2bd011373ac9a1fc99`;
canonical patch `0304` is byte-identical and isolated source and KUnit profiles
are admitted.

Buildbox then fetched exact clean repository commit
`5b129a7b4af899a444f8b3bccf583de03f431227`, applied all 293 canonical
patches, merged the 11 fragments in profile
`mtk-ram-console-parser-kunit`, and compiled and linked release
`7.1.3-gemini-mtk-ram-console-parser-kunit`. The checksum-validated package
contains one exported parser symbol and all eight focused test symbols. Its
image SHA-256 is
`8afa5cd434cdf77a7113b9f05470ceb33411e7cc6c82c9f3e69682db2f61fa0f`.

One bounded QEMU 11.0.2 run used that exact image on `virt`, four Cortex-A53
vCPUs, and no network. The sole `mtk-ram-console-parser` suite ran exactly the
eight declared cases; all passed with zero failures or skips. The later VFS
rootfs panic and timeout were the predeclared terminal VM state. No physical
mapping, reset interpretation, A34 caller, boot candidate, or device action
was executed or inferred.

## Analysis

Parsing a copied byte buffer is independently reviewable and testable. It can
freeze strict corruption behavior without deciding how the `no-map`
reservation is located or whether any status value supplies reset authority.
Returning all 32 bits plus validity preserves unknown values for a later
owner; it does not make them safe.

## Conclusion

`pass` for the pure retained-header parser boundary. Exact Buildbox generation,
replay, strict style review, canonical admission, cross-compile, link, and all
eight focused KUnit cases pass. This does not prove a physical mapping owner,
reset classification, a fresh secure epoch, production A34 authority, or any
hardware behavior.

## Follow-up

Audit immutable physical copy ownership and independent secure-epoch
attestation as separate boundaries. Keep reset classification, A34 evaluation,
lifecycle publication, and device work out until both authority paths are
honestly resolved.
