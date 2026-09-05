# Proposed repository integration after independent acceptance

This is a proposal for the integrator, not a manifest/series edit or a build
selection. The collected [attempt 2](ATTEMPT_2.md) and its immutable six-mail
archive remain separate from repository patch application policy. Actual
certification remains unresolved. No kernel build or repeat is requested.

## Minimal patch destination and canonical order

Copy only the generated header-only patch 3, byte-for-byte, to the new path
`patches/upstream-4d7d9486/0003-dt-bindings-reset-mediatek-add-MT6797-infracfg-reset.patch`.
Its SHA-256 must remain
`0c8af0a97f42424830d5c6b59f9830a42d4212b728507ea6f433f7a8713fff25`.
Insert this new path in `patches/series` immediately after the historical patch
3 and before historical patch 4. Preserve all six historical patch files,
their canonical relative order, existing named series and runtime/build receipts.
The canonical list remains the superset, not a request to apply both patch-3
alternatives in one profile.

Reuse the existing historical paths for positions 1, 2, 4, 5 and 6 in a new
`patches/series-mt6797-infracfg-revised-kunit`, with this exact order:

```text
upstream-4d7d9486/0001-clk-mediatek-reject-out-of-bank-SET-CLEAR-reset-IDs.patch
upstream-4d7d9486/0002-clk-mediatek-test-reset-translation-bounds.patch
upstream-4d7d9486/0003-dt-bindings-reset-mediatek-add-MT6797-infracfg-reset.patch
upstream-4d7d9486/0004-clk-mediatek-add-MT6797-infracfg-SET-CLEAR-resets.patch
upstream-4d7d9486/0005-clk-mediatek-test-MT6797-infracfg-reset-mapping.patch
upstream-4d7d9486/0006-arm64-dts-mediatek-expose-MT6797-infracfg-resets.patch
```

The [measured payload comparison](results/attempt-2-725c6756/mail-comparison.json)
proves these five historical payloads equal the regenerated ones. Retaining the
historical files avoids redundant copies or ancestry-only mail replacements.
The complete regenerated archive still owns its actual commit/tree identities.
Do not claim the mixed application-series mail envelopes form that Git ancestry;
its applied source bytes are the comparison target.

## Isolated profile proposal

Add `config.profiles.mt6797-infracfg-revised-kunit` with the existing historical
`mt6797-infracfg-upstream-kunit` profile's exact `allnoconfig` base, unchanged
`configs/mt6797-infracfg-upstream-kunit.fragment`, and complete kernel source
object. Change only `patch_series` to the new named series above. Preserve the
old profile and default/global source/series selections. The pinned upstream
commit remains `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`, archive SHA-256
`45590c057805bc9cf7281ce04d5dbde5316b7c8b017998cafac301f67e92682d`.
No separate clock-cleanup or passive-SCPSYS proposal enters this profile.

This preserves the tested C/header/DTS/configuration bytes and removes only
the mandatory-binding delta. It does not turn earlier compilation or retained
DTB observations into a build of the newly named profile. The collected full
source/hash/replay and focused compatibility evidence justify reviewing that
source-only distinction without automatically scheduling another build.

At integration, compare the destination patch bytes and six selected payloads,
validate **all** manifest-selected series as canonical-order subsequences, run
the invariant refusals and common publication checks, and keep actual author/DCO
status explicit. Any future source modification, build selection or upstream
submission needs its own exact reviewed revision. The integrator owns these
edits and decisions; this worker has made none of them.
