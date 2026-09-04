# Experiment: attributable MT6797 Cortex-A72 frequency observation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-04-mt6797-a72-frequency-observation` |
| Status | `running`; corrected decoder passed exact Buildbox/QEMU proof |
| Subsystem | MT6797 CPU clock readback / Cortex-A72 lifecycle |
| Device variant | Gemini PDA x27, named development unit |
| Date(s) | 2026-09-04 |
| Investigator(s) | Project owner and Codex |
| Tracking issue | Roadmap thermal/frequency observability gate |

## Question or hypothesis

Can the existing protected clock and stable BigiDVFS snapshots be decoded into
an attributable, read-only Cortex-A72 frequency observation before any longer
load, cpufreq/OPP, or additional hotplug experiment?

The first falsifiable sub-question is offline: does the current decoder match
the two materially different MT6797 register formats and accept stable normal
PLL values whose bit 31 change strobe remains set?

## Provenance and environment

- Kernel release/commit: Linux 7.1.3 plus canonical project series; exact
  generation and build revisions will be recorded in `results/`.
- Prepared source state: `1f375445713c863e0959cb1364c4ae754376fe23f7ee836bf30d7bb50e852607`.
- Prepared source integrity: `e3cfd681e3599d84a4be7fbaac81d23c56c2674f2f87f84c721629accc889212`.
- Public comparison source: Gemian kernel revision
  `f3d2a14bd1b8355c68e59e8bd4be6bc1525f9c24` in the existing Buildbox
  public-source checkout.
- Build backend: Buildbox only; no native VM build.
- Boot path and target: none for the decoder-repair and KUnit gate.

## Safety assessment

The current phase is hardware-free. It generates normal review patches in a
temporary Buildbox Git repository, builds an isolated KUnit profile from an
exact clean pushed project commit, and runs that kernel under no-network QEMU.
The decoder and tests make no hardware call and expose no write path.

No CPU request, PSCI call, hotplug action, secure call, MMIO access, regulator
action, thermal action, retained-RAM write, device access, storage access, or
boot candidate is authorized by this phase. CPUs 8 and 9 remain closed until
the offline decoder gate and a separate observation composition pass.

## Associated code

- `scripts/generate-on-buildbox`: pinned two-patch generator and replay gate.
- `scripts/source_edits.py`: deterministic decoder repair and focused KUnit
  source edits.
- `scripts/validate_source.py`: source boundary and formula validator.
- `scripts/validate_patches.py`: normal-patch and changed-path validator.
- `scripts/run-kunit-qemu`: exact-package, no-network arm64 QEMU runner.
- `scripts/classify-kunit.py`: exact focused KTAP classifier.
- [`OBSERVER.md`](OBSERVER.md): frozen three-attempt live observation boundary,
  transport budget, hardware-free gate, and eventual device decision branches.
- `scripts/generate-observer-on-buildbox`: pinned two-patch observer generator,
  exact replay, and strict review gate.
- `scripts/observer_source_edits.py`: deterministic production observer and
  injected five-case test edits.
- `scripts/validate_observer_source.py` and
  `scripts/validate_observer_patches.py`: operation, budget, path, and normal
  format-patch oracles.
- `results/source-semantics-audit-20260904.txt`: source and live-readback
  evidence that rejected the old decoder semantics.

## Procedure

1. Pin the current prepared source and the four decoder-related input files.
2. Generate one production repair patch and one focused KUnit patch as normal
   `git format-patch` output on Buildbox.
3. Replay both patches from the pinned parent and run strict source,
   changed-path, and Checkpatch validation.
4. Admit both patches in canonical order with one focused KUnit profile, then
   audit every manifest profile.
5. Build the exact clean pushed KUnit profile on Buildbox and run only the
   decoder suite in isolated no-network QEMU.
6. Only after that pass, define a separate read-only observation patch that
   composes decoded A72 frequency with the exact successful stage-18 topology,
   thermal, accounting, and bounded volatile-RAM evidence.
7. Generate and hardware-free prove the three-attempt live observer before it
   enters any device profile.

## Observations

- Stable live normal-PLL samples have bit 31 set, including LL
  `0xc1114000` and CCI `0xc10c1d89`. The current decoder rejects either as an
  in-flight change.
- Both the public MT6797 cpufreq path and generic MediaTek PLL code treat bit
  31 as a write-trigger strobe, not a readable busy condition. The normal path
  leaves the bit set after programming.
- The secure BigiDVFS PLL is not a normal ARMPLL_CON1 record: its PCW is bits
  30:0 with 24 fractional bits, while its post-divider is in a separate
  register at bits 14:12. The current decoder instead truncates it to bits
  20:0 and reads post-divider bits 26:24.
- The BigiDVFS getter performs integer-MHz truncation before post-divider and
  kHz conversion. The repair must preserve that order.
- Buildbox generated and replayed exact normal patches `0525` and `0526` from
  clean pushed project revision `1e2bde54f05b...` and prepared source state
  `1f375445713c...`. The source and changed-path validators pass; strict
  Checkpatch reports zero errors, warnings, or checks. See
  [results/patch-generation-20260904.txt](results/patch-generation-20260904.txt).
- The exact clean pushed decoder revision `a14e7701...` passed a Buildbox arm64
  build of both the production decoder and its focused test object. All 515
  selected patches replayed and every packaged checksum passed. See
  [results/buildbox-kunit-build-20260904.txt](results/buildbox-kunit-build-20260904.txt).
- The fetched package then booted in isolated no-network arm64 QEMU and the
  only selected KUnit suite passed all six cases. The proof accepts stable
  normal-PLL bit-31 samples, derives the three live normal frequencies, derives
  the live B-cluster sample as 845000 kHz using its separate post-divider, and
  covers every ARMPLLDIV ratio. See
  [results/kunit-qemu-20260904.txt](results/kunit-qemu-20260904.txt).

## Analysis

The current decoder cannot support an attributable A72 frequency observation.
It rejects known-stable normal records and applies the wrong format to the B
cluster. Wiring it into a physical candidate would therefore turn a healthy
sample into a false failure or a wrong frequency. This was discovered offline
before composition and does not weaken the already proven stage-18 lifecycle,
thermal, topology, RAM-integrity, or accounting results.

The minimum corrective boundary is pure conversion logic plus focused tests.
Transport stability remains owned by the existing protected-clock semaphore
sample and the BigiDVFS identical-double-sample backend; bit 31 is not reused
as a second, unsupported stability oracle.

## Conclusion

`partial pass`: the prior decoder semantics are rejected and the corrected pure
conversion boundary has exact patch-generation, Buildbox compilation, package,
and isolated six-case KUnit proof. This establishes decoder math, not a live
A72 frequency claim. No device action or boot candidate occurred in this phase.

## Follow-up

Add one read-only lifecycle observation that publishes raw and decoded
B-cluster values at bounded attributable points. Compose that observation with
the proven thermal DT/configuration and exact 4+4+2 lifecycle profile. Keep
longer load, cpufreq/OPP, extra hotplug, idle, suspend, and identical-artifact
repeats closed.
