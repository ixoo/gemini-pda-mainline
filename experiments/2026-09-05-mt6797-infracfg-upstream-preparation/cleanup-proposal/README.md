# Separate common-clock reset-registration cleanup proposal

Status: implementation and host fault fixtures prepared; unsigned format-patch
generation awaits its assigned Git-only preparation window. This proposal does
not change the validated six-patch infracfg topic, its manifest or its profile.
No kernel, schema, QEMU or device execution is selected.

## Minimal fix

The pinned `clk-mtk.c` is byte-identical in tested upstream
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c` and inspected clock-next
`91b1b8d437abe0cd83210d8f257b785a63047aa9`: 16200 bytes, SHA-256
`e8a89dffaffedfce01489b0887fb425d64649d6fb841157bbcea5aac0fc93e59`.
[The primary-source snapshot](../results/submission-routing-snapshot.json)
records both immutable URLs and the source-level finding.

The common probe publishes an OF clock provider, then attempts managed reset
registration. On reset error it currently unregisters/frees clocks without
removing that provider. Change only that error edge to a new
`unregister_provider` label which calls `of_clk_del_provider(node)` before the
existing clock unwind. The clock-publication error still jumps directly to
`unregister_clks`; it has no newly published provider to remove. Success and
normal remove are unchanged. Driver-core failed-probe cleanup already clears
driver data, so this proposal adds no redundant driver-data reset.

```diff
         if (r)
-            goto unregister_clks;
+            goto unregister_provider;
     }
```

The new two-line label/removal precedes `unregister_clks`. The entire corrected
source has SHA-256
`01f33c475e9bbe6ffef504d8247acd618bd53cc563de42abef4ada96b8344646`.
[The pure derivation](derive.py) checks complete input size/hash and unique
insertion boundaries; it refuses guessed or changed source bytes.

This fix is independently prepared from the upstream source/control-flow audit.
No vendor code or posted third-party patch was copied. It is a separate
common-helper correction, not a backdoor import of the 32-patch clock conversion.
If the MT6797 conversion lands first, that topic can use the existing reset
hook only with correct common-helper failure cleanup; the current validated
private MT6797 probe ordering remains separate.

## Actual C control-flow coverage

[The fixture](test-cleanup.py) reads the exact pinned public source only when
`--fetch-source` is explicit, extracts the *complete unchanged probe and remove
bodies*, and pipes those bodies plus [stub framework calls](harness.c) to a host
C compiler. The source exists in memory, not in a persisted Linux source copy.
The temporary binary is bounded and automatically removed on success/failure.
No production interface or test-only kernel API is introduced.

[The host result](host-fixtures.json) records six passing corrected cases:

- reset-registration failure after successful clock publication;
- clock-publication failure with no provider removal or reset call;
- gate-registration failure before publication;
- allocation failure;
- success followed by normal remove;
- a descriptor without resets, followed by normal remove.

The fixture records provider publication/removal and clock freeing, checks no
provider remains when backing data is freed, and verifies removal precedes the
existing reverse-order clock unwind. Compiling the original source reproduces
the reset-failure defect. Mutants that remove a provider on publication failure
or only remove it after freeing data also fail. Three complete-source input
mutations reject before derivation.

This is stronger than a handwritten reimplementation of the branch, but weaker
than an in-kernel framework integration test: OF registration, regmap, reset
core, devres, allocation and clock operations are stubs. It does not exercise
real provider lookup concurrency, outstanding consumers, runtime PM, module
unload races or hardware. No new `Tested-by` or upstream test acceptance is
claimed. An admitted final-source Linux build and focused kernel fault injection
remain possible follow-up, not actions selected here.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-09-05-mt6797-infracfg-upstream-preparation/cleanup-proposal/test-cleanup.py --fetch-source
```

## Unsigned patch generation and admission

The [generator](generate-on-buildbox) requires an exact clean published project
revision, the normal existing nonblocking Buildbox lock and sufficient space.
After a separately assigned window, it uses a disposable sparse upstream Git
checkout containing the one source file and review checker, derives the fix,
commits with an explicit synthetic non-certifying identity, emits a real
`git format-patch`, checks replay against the exact full parent tree and runs
strict checkpatch with only missing sign-off exempted. It removes sparse source
scratch and retains only a patch/check/identity package for review. No package
or prepared kernel tree is modified or exported.

The fixed experiment timestamp and synthetic `From` are reproducibility metadata,
not a claim about a human author's identity or certification. Actual authorship,
truthful DCO sign-off, final merge base, any supported `Fixes` tag and stable
routing must be resolved before upstream submission. No tag or signature is
invented. Root admission is required before changing any active series or
allocating a subsequent build. The optional-reset-cell binding correction stays
the next separate small topic after this cleanup handoff.
