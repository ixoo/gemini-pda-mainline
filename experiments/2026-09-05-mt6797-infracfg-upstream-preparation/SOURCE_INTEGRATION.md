# Buildbox source-selection integration handoff

## Outcome and boundary

Build the exact coherent upstream reset topic through the existing explicit
Buildbox entry point while retaining every existing Gemini profile's effective
source, architecture, configuration and patch inputs. The reviewed upstream
parent is a post-7.3-rc1 commit; compiling the old local 7.1.3 repair cannot stand
in for validation of that complete upstream tree.

This handoff contains a tested proposal, not a change to the production builder.
The upstream worker owns the experiment scripts below. Project Planning owns
integration into shared scripts, manifest and canonical series. No kernel build
or shared-input mutation has occurred for this proposal. No device is needed.

## Concrete implementation supplied

- [kernel_source_contract.py](scripts/kernel_source_contract.py) selects and
  normalizes the source tuple and checks source provenance. It has no network,
  extraction, build or device operation.
- [profile_inputs.py](scripts/profile_inputs.py) fingerprints each selected
  architecture, source tuple, base configuration, ordered fragments and ordered
  patch paths/bytes. A series-container rename alone does not change effective
  inputs; content, order and actual input paths do.
- [test-source-contract.py](scripts/test-source-contract.py) exercises valid
  selection, legacy packages, complete override provenance, invalid metadata,
  duplicate JSON fields, profile removal/default changes, and real fixture
  source/config/patch/order mutations. It also checks the existing profile set.
- [baseline-profile-inputs.json](results/baseline-profile-inputs.json) freezes all
  189 existing profiles at repository parent `2891e041`. This inventory is a
  preservation oracle, not permission to build or deploy any profile.

The original global source tuple remains the fallback. A profile may contain
an optional `kernel` object. If that key is present, it must supply the entire
source tuple: `version`, `released`, `source_url`, `sha256`, `archive_format` and
`archive_root`. `git_commit` is optional but required by this particular upstream
snapshot's eventual manifest entry. No partial merge with the global source is
allowed. Null, empty or malformed overrides refuse instead of falling back.

Only public HTTPS URLs without embedded credentials, queries or fragments are
accepted by this proposal. Source SHA-256 and optional Git identities are exact.
Supported archive formats are `tar.xz` and `tar.gz`; the archive root must be one
safe `linux-*` component. Existing four-field global tuples normalize to
`tar.xz` and `linux-VERSION`. Neither version text nor a URL replaces the archive
checksum. A snapshot's commit must be reflected in its immutable source URL and
verified against the generation inputs before admission.

New override packages must record the complete normalized tuple in
`provenance/build.json` as `kernel_source`, plus the existing `source_sha256`.
The validator must resolve the source from the packaged manifest and packaged
build profile and require exact agreement. Legacy global-source packages without
`kernel_source` remain accepted when their existing source checksum agrees;
if the new field is present, even a global-source package must match it exactly.
The resolver checks source identity only. It does not replace package inventory,
config, series, compiler, ELF, DTB or ABI checks.

## Shared integration points

1. Promote one reviewed resolver to `scripts/` and use it in both
   `scripts/kernel` and `scripts/validate-kernel-artifact`. Avoid independent
   shell/JSON implementations of fallback rules. Resolve the profile before
   reading its source tuple. Existing legacy manifests and packages must retain
   their current supported behavior.
2. Preserve existing release cache/source/build paths for the legacy global
   source. Key a new snapshot cache by its complete source digest and declared
   compression, so two commits with the same release string cannot overwrite
   one another's archive. Retain the existing source-state and integrity checks.
3. Download to managed temporary state, verify the declared digest before
   extraction, select the declared decompressor explicitly, and verify the
   declared top-level archive root. Reject unexpected roots and traversal before
   installing a prepared tree. Preserve the existing cleanup and serialized
   source-mutation contract. Do not relabel gzip bytes as a release `.tar.xz`.
4. Record the effective tuple in newly produced package provenance and validate
   it before publication or fetch. Package validation must not compare an
   override build only with the global `.kernel.sha256`.
5. Add meaningful end-to-end builder/package fixtures for both archive formats,
   wrong compression/root/checksum, interrupted downloads, and mismatched
   profile/source provenance. The supplied pure fixtures do not test shell
   wiring, archive extraction or package publication.

## Canonical series and candidate preservation

`gemini-thermal-v4-corrected` is the sole existing profile selecting the full
`patches/series` at the frozen parent. Before appending a separate upstream topic,
copy that exact old ordered selection into an immutable named series and point
only that profile to it. All of its effective patch and configuration bytes must
remain equal to the preservation oracle. Other profiles and the default remain
unchanged. This metadata migration is not a new V4 candidate or permission to
repeat the consumed gate; historical package manifests and receipts stay intact.

After that reviewed freeze, place the six exact generated topic patches under a
new upstream-specific directory in `patches/`, append them in canonical order,
and select only those six in the new upstream profile. Every manifest profile
must still pass the existing canonical-subsequence audit. Do not apply both the
historical integration repair and the coherent upstream equivalent to one tree.

The new profile needs an independently hashed source archive for exact upstream
commit `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`, the archive-root/compression
contract, a small arm64 QEMU configuration with both new KUnit suites, and exact
expected patch identities from the generation receipt. Those build inputs are
not yet admitted. No placeholder checksum is a usable source selection.

## Validation before build

From the owning worktree:

```sh
python3 experiments/2026-09-05-mt6797-infracfg-upstream-preparation/scripts/test-source-contract.py
python3 experiments/2026-09-05-mt6797-infracfg-upstream-preparation/scripts/profile_inputs.py . --compare experiments/2026-09-05-mt6797-infracfg-upstream-preparation/results/baseline-profile-inputs.json
```

The comparison requires every baseline profile to remain present and identical;
new profiles are reported separately. Run it before and after integration on
clean pinned revisions. Run all manifest, production-builder and Linux package
provenance fixtures as well. A hash equality proves effective-input preservation,
not that an unbuilt profile boots or that new shell wiring uses the resolver.

Once the shared change and new profile pass those gates, commit and push the
exact clean revision, then use only `./scripts/build-kernel --backend buildbox`
with the explicit upstream profile. Freeze that checkout through validated
package fetch. Run the exact KUnit image in bounded no-network QEMU and run the
focused binding/DT checks on Buildbox. Record real failures without relaxing the
contract. The existing named device candidate remains selected independently.

## Handoff state

Fifteen test groups passed, including the live repository comparison preserving
all 189 baseline profiles and real input/order mutations. The common repository
gate passed; Linux-only artifact fixtures remain an integration/CI requirement.
The pure contract and preservation oracle are review-ready. Production wiring,
archive acquisition, profile admission, kernel compilation, KUnit execution and
schema checks remain open. The integrator can review this bounded dependency
without waiting for physical boot selection. Until shared integration is
complete, this experiment must not claim that Buildbox supports profile source
overrides or that the upstream topic has compiled.
