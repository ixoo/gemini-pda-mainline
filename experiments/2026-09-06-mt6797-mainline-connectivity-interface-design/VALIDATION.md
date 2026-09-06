# Validation record

Corrected design review-ready at `2026-09-06T20:23:28Z`, after Astra rejected
the earlier lifetime/state model. Observed initial start was
`2026-09-06T20:02:55Z`; the authorized correction resumed at
`2026-09-06T20:16:52Z`. Measured credits are unavailable.

## Executed checks

- Normal verifier: PASS — eight decisions, fifteen states, thirty-two edges,
  twelve Wi-Fi proposals, three companion proposals and seventeen refusals.
- Optimized (`python3 -O`) verifier: identical PASS.
- Refusals cover the original thirteen policy mutations plus effect-bearing
  partial activation, wireless-registration failure, effectful unsupported
  secure operation and premature callback/module-code lifetime release.
- All four canonical JSON digests match the independent freeze. All forty-two
  frozen local file identities match; parent is exact and the manifest-Linux
  inspection budget remains zero of six.
- JSON parsing, in-memory Python compilation, exact file/suffix inventory,
  final newline, CR/trailing-whitespace, local Markdown links, no-pycache and
  bounded private/raw-material patterns: PASS.
- `git diff --check` and `git diff --cached --check`: PASS.
- `./scripts/check-repository`: PASS (`repository_checks=pass`), including 195
  manifest profiles and the workflow, publication, source-integrity, target,
  build-backend and preflight fixtures. The gate reported the existing 37
  metadata-debt records. Linux-only provenance and full-package checks were
  skipped/deferred as printed and are not counted as passes.

The initial draft's verifier failed twice before the mandated stop: first from
applying a prose-length threshold to enum classifications, then from a literal
raw-resource phrase mismatch. The reopened correction validates the normalized
responsibility text and the explicit no-export list. Astra's subsequent design
rejection is addressed by effect-history-based poisoning, separate
`FIRMWARE_READY` and registration transitions, and explicit callable/object/code
lifetime retention through `FAULT_HELD`, `QUIESCING` and owner-proven `OFF`.

## Scope and exclusions

Only files in this experiment directory other than the frozen `WORK_ITEM.md`
were edited. No manifest-Linux file/page, new source tree, private input, VM,
device, SSH, network, build, staging, commit or push was used. No kernel, DT,
configuration, proposal patch or shared file changed. No vendor code, raw
binary, disassembly, firmware or calibration data is retained.

No kernel build, Checkpatch, DT-schema or hardware test applies to this
documentation/verifier-only change. Compilation and verifier success do not
establish an implemented driver, firmware readiness, wireless registration,
runtime behavior or hardware support.

## Unresolved prerequisites

The real shared-resource implementation still needs an attributable
power/reset/downloader handoff; external-writer exclusion; deployed secure ABI,
selector and master/domain policy; actual boot reservation lifetime and mapping
visibility; HIF IRQ/transport completion; firmware-stop and AP-DMA idle
witnesses; cross-client recovery; final DT/firmware names and maintainer-owned
subsystem placement. The passive provider slice remains effect-free until those
requirements receive separate implementation and review.

## Independent acceptance

Astra Medium independently accepted the corrected design at
`2026-09-06T20:25:29Z`. It confirmed that the four prior rejection grounds are
closed: partial activation, post-readiness registration failure,
effect-sensitive error containment and callable/object/code lifetime. It also
inspected all seventeen refusal mutations, reran both verifier modes and
confirmed that the four new cases fail substantive predicates rather than a
count alone. This accepts the design record only; it grants no runtime,
hardware, build or device admission.
