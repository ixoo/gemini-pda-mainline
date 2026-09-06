# Work item: integrate and compile dynamic reserved-memory binding

- **Outcome:** integrate the accepted passive dynamic reserved-memory delta
  after its exact predecessor and prove that the real pinned arm64 kernel builds
  and links `image-binding.o` through the existing compile-only profile.
- **Owner and reviewer:** `/root` owns canonical/series integration and
  Buildbox submission; Sol Medium reviews the frozen integration/result.
- **Frozen parent:** repository commit
  `279c4879a9edceacc2df89debb80f01c79ff14c4`.
- **Inputs:** exact patch
  `../2026-09-06-mt6797-dynamic-reserved-binding/0006-wifi-mediatek-describe-dynamic-reserved-memory.patch`,
  existing `patches/series-mt6797-provider-compile`, and manifest profile
  `mt6797-hif-parser-compile` at Linux
  `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`.
- **Owned integration:** add one byte-identical proposal patch immediately after
  `proposals/0006-wifi-mediatek-describe-reserved-memory.patch` in the canonical
  and provider-compile series. Do not alter existing patch bytes, manifest,
  configs, DT, default profiles or hardware-support claims.
- **Acceptance:** exact patch checksum equality; all 194 manifest profiles retain
  canonical subsequence ordering; repository publication gate; clean committed
  and pushed build revision; `./scripts/build-kernel --backend buildbox` with
  `KERNEL_PROFILE=mt6797-hif-parser-compile`; exact source/object command identities;
  nonzero arm64 definitions for the reserved binding API; real references to OF
  reserved-memory/property APIs; no host hooks, initcall, registration, mapping,
  callback invocation, DMA, power or active-success path.
- **Stop:** refuse on series/profile drift, patch replay failure, unrelated dirty
  state, Buildbox provenance mismatch, compile/link failure or any effectful path.
  A compile failure triggers focused diagnosis, not a device action.
- **Hardware:** none. This is compile-only and creates no boot candidate.
- **Authorship:** synthetic non-certifying patch identity remains experiment-only;
  missing DCO is expected and blocks submission.
- **Handoff:** integration identity, Buildbox receipt, limitations and rollback
  (remove only the new proposal entry/file) with exact validation results.
- **State:** integrating; Buildbox not yet submitted.
- **Efficiency loop:** the Buildbox run is build-only; record the accepted
  integration handoff once, not the build as a second offline item.
