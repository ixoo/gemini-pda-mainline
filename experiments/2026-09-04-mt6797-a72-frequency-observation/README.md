# Experiment: attributable MT6797 Cortex-A72 frequency observation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-04-mt6797-a72-frequency-observation` |
| Status | `running`; successor passes offline gate, guarded deployment selected |
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

The completed offline phases generated normal review patches in a temporary
Buildbox Git repository, ran isolated KUnit proof under no-network QEMU, built
the successor production and focused profiles from exact clean pushed commit
`5d892a1c...`, and assembled its exact candidate without device access. The
decoder and tests make no hardware call. The production runtime exposes exactly
one inherited stage-18 lifecycle trigger plus three read-only frequency
observations and a finite volatile-RAM workload; it has no storage or reboot
action.

No device action occurred during the offline gate. The exact validated
candidate is eligible for the standing guarded `boot2` workflow: live GPT
resolution, inactive/unmounted target checks, no fresh backup, full 16 MiB
readback, and clean shutdown. One later fresh boot may run only the frozen
three-sample bounded observation; longer load and all policy experiments remain
closed.

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
- [`COMPOSITION.md`](COMPOSITION.md): exact production-profile, DT, runtime,
  and decision boundary for the stage-18 thermal/frequency successor.
- `scripts/generate-observer-on-buildbox`: pinned two-patch observer generator,
  exact replay, and strict review gate.
- `scripts/observer_source_edits.py`: deterministic production observer and
  injected five-case test edits.
- `scripts/validate_observer_source.py` and
  `scripts/validate_observer_patches.py`: operation, budget, path, and normal
  format-patch oracles.
- `scripts/run-observer-kunit-qemu` and
  `scripts/classify-observer-kunit.py`: exact focused-package runner and
  five-case KTAP classifier for the observer gate.
- `scripts/generate-successor-on-buildbox`, `scripts/successor_source_edits.py`,
  `scripts/validate-successor-source.py`, and
  `scripts/validate-successor-patches.py`: pinned two-patch repair for the
  production configuration binding and admission-owned observer attachment.
- `scripts/build-production-dtb.py` and `scripts/validate-production-dtb.py`:
  exact thermal/topology/provenance composition and independent DT-delta gate.
- `scripts/build-production-candidate.sh` and
  `scripts/validate-production-candidate.py`: deterministic Android-v0/LK
  assembly and independent candidate oracle.
- `scripts/remote-production-pretrigger.sh`,
  `scripts/validate-production-pretrigger.py`, and
  `scripts/collect-production-pretrigger.sh`: zero-observer-read, read-only
  fresh-boot admission frame and direct-USB collector.
- `scripts/build-production-runtime.sh`,
  `scripts/classify-production-runtime.py`, and
  `scripts/run-production-runtime.sh`: one boot-ID-bound stage-18, thermal,
  frequency, accounting, and four-round volatile-RAM capture.
- `scripts/install-production-boot2.sh`: exact-candidate guarded live-GPT
  `boot2` installation and shutdown wrapper.
- `results/source-semantics-audit-20260904.txt`: source and live-readback
  evidence that rejected the old decoder semantics.
- `results/observer-patch-generation-20260904.txt`: exact replay, source/path,
  Checkpatch, and package identity for canonical patches `0527` and `0528`.
- `results/buildbox-observer-kunit-build-20260904.txt` and
  `results/qemu-observer-kunit-20260904.txt`: exact focused compilation,
  package, and five-case isolated runtime proof.
- `results/production-candidate-20260904.txt`: exact Buildbox production
  package, DT transform, LK candidate, and pretrigger/runtime mutation gate.
- `results/successor-patch-generation-20260904.txt`: exact Buildbox generation,
  replay, path, style, identity, and no-new-effect proof for canonical patches
  `0529` and `0530`.
- `results/successor-offline-gate-20260904.txt`: exact successor production and
  focused Buildbox packages, isolated 5/5 and 14/14 KUnit results, production
  registration oracle, DT/container identities, and new candidate admission.

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
8. Only after that gate passes, compose one production successor with the
   runtime-proven thermal DT/configuration and stage-18 4+4+2 lifecycle.
9. Independently validate its exact DT delta and Android-v0/LK container, then
   freeze a boot-ID-bound zero-read pretrigger and finite runtime classifier.
10. Publish those inputs before one guarded `boot2` installation and one fresh
    live observation.

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
- The initial bounded-observer generation attempt stopped at strict Checkpatch,
  before an output package was admitted. After the generator was corrected,
  exact clean pushed revision `dab92819...` produced and replayed canonical
  patches `0527` and `0528`. Their source/path oracles and strict Checkpatch
  pass, the latter with zero errors, warnings, or checks. The five injected
  cases cover live-value composition, the three-attempt ceiling, failed-attempt
  consumption, malformed generation, and null/source guards. See
  [results/observer-patch-generation-20260904.txt](results/observer-patch-generation-20260904.txt).
- Exact clean published revision `ea9ad80a...` compiled the production observer
  and its injected test object on Buildbox with all 517 selected patches and
  every package checksum validated. The only selected no-network QEMU suite
  then passed all five exact cases, including the live-value fixture's 845000
  kHz B-cluster result, three attempts followed by transport-free refusal, and
  failed-attempt consumption. See
  [results/buildbox-observer-kunit-build-20260904.txt](results/buildbox-observer-kunit-build-20260904.txt)
  and [results/qemu-observer-kunit-20260904.txt](results/qemu-observer-kunit-20260904.txt).
- Exact clean published revision `673df9c0...` built the production profile on
  Buildbox. All 517 selected patches and package checksums passed; the resolved
  configuration enables the stage-18 lifecycle, thermal serviceability, and
  bounded observer while leaving KUnit, cpufreq/OPP, CPU idle, and suspend off.
- The exact production DT is the successful 4+4+2 topology base plus only the
  reviewed thermal transform and the new package's provenance leaf. Independent
  structural validation passed with one policy-free thermal zone and preserved
  USB, keyboard, eMMC, PWRAP, and lifecycle nodes.
- The Android-v0/LK candidate has raw identity `d9f812c8...` and exact padded
  `boot2` identity `03cbaa72...`. Its manifest and all LK gates pass with the
  runtime-proven serviceability initramfs.
- The pretrigger accepts no observer read and rejected 12 unsafe mutations. The
  runtime accepts one exact positive fixture and rejected all 18 mutations. It
  performs three observations, proves both CPU8/CPU9 writers alive on both
  sides of the middle sample at their start barrier, then releases exactly four
  volatile-RAM rounds and takes the final sample after completion.
- Guarded deployment from published commit `75917139...` resolved live GPT
  `boot2` as inactive `/dev/mmcblk0p30`, distinct from Gemian root
  `/dev/mmcblk0p29`. With stable external power and 100%/Good capacity it
  replaced predecessor `93a78b49...`, synchronized and flushed the write, and
  independently read back the full 16 MiB as exact `03cbaa72...`. No fresh
  backup or reboot was requested and clean shutdown was confirmed. The private
  summary retained the source wrapper's prior experiment label; that metadata
  label was corrected immediately afterward and does not affect the recorded
  target, candidate, readback, boot ID, power, or shutdown evidence.
- The first fresh physical selection booted the exact release and provenance on
  boot ID `5e78e726...`; direct-USB netcat, thermal, controller, binder,
  platform-state, and CPU0--7 serviceability were present. The owner observed
  no visible local console, which is recorded separately from kernel identity
  and runtime admission. The zero-read pretrigger rejected before any mutation:
  the frequency observer attribute was absent, and the late CPU profile reported
  runtime-binding proof mask `0x40000`. CPU8/CPU9 remained offline, the one-shot
  trigger remained pristine, and no frequency read, sysfs write, CPU request,
  storage access, or automatic reboot occurred.
- One additional read-only diagnostic on that boot proved there was no observer
  sysfs path and that the production platform source became ready with no
  caller. Exact source comparison found two independent composition omissions:
  patch `0503` knows only the older physical-profile configuration identity,
  while patch `0527` registers the observer only on the disconnected snapshot
  adapter whose DT node is absent from the production composition. Native USB
  recovery then returned a changed boot ID on Gemian. See
  [results/production-runtime-attempt-1-20260904.txt](results/production-runtime-attempt-1-20260904.txt).
- Exact clean pushed revision `11af7dc3...` generated and replayed successor
  patches `0529` and `0530` on Buildbox. Strict path/source validators and
  Checkpatch pass with zero errors, warnings, or checks. The first patch
  preserves both predecessor identities while selecting exact `18ded825...`
  for the observer+physical profile. The second resolves the production
  admission controller's real snapshot suppliers before exposing one read-only
  observer attribute; it preserves the disconnected adapter, three-attempt
  budget, and all existing CPU actions. No DT, CPU request, hardware write,
  candidate, native VM build, or device action was added. See
  [results/successor-patch-generation-20260904.txt](results/successor-patch-generation-20260904.txt).
- Exact clean published revision `5d892a1c...` built the successor production,
  observer-KUnit, and hotplug-binding-KUnit profiles on Buildbox from source
  `be41c068...` and patchset `0f2a0357...`. Isolated no-network arm64 QEMU
  passed the observer suite 5/5 and binding suite 14/14 with zero failures or
  skips. The latter linked the production binding but invoked it zero times and
  performed no hardware action.
- The production package's exact configuration identity is `18ded825...`.
  A static package/source oracle proves the admission controller and its one
  read-only frequency attribute are present exactly as intended, while KUnit
  suites are absent. Independent composition preserved the 4+4+2 topology and
  serviceability nodes, added only the reviewed thermal transform and one
  package provenance leaf, and produced DT `a4bf5774...`.
- Two deterministic Android-v0/LK assemblies produced raw candidate
  `24cb227b...` and exact 16 MiB padded candidate `54a02dd0...`. All container,
  package, structural DT, 12 pretrigger-mutation, and 18 runtime-mutation gates
  pass; the independent validator reports `boot_candidate=true`. See
  [results/successor-offline-gate-20260904.txt](results/successor-offline-gate-20260904.txt).
- Before this successor was installed, the owner reported another selection
  with no visible console. The host could only identify the already-running
  Gemian recovery boot afterward, with its unchanged boot ID and 3.18 kernel.
  That screen observation is therefore unattributed and is not evidence for or
  against the successor.

## Analysis

The current decoder cannot support an attributable A72 frequency observation.
It rejects known-stable normal records and applies the wrong format to the B
cluster. Wiring it into a physical candidate would therefore turn a healthy
sample into a false failure or a wrong frequency. This was discovered offline
before composition and does not weaken the already proven stage-18 lifecycle,
thermal, topology, RAM-integrity, or accounting results.

The decoder repair remains valid: transport stability is owned by the existing
protected-clock semaphore sample and the BigiDVFS identical-double-sample
backend; bit 31 is not reused as a second unsupported stability oracle. The
first production boot exposed two later integration defects, not a conversion
failure. The successor now adds this exact profile's compile-time runtime-
binding identity and attaches the bounded observer to the in-memory snapshot
source owned by the physical binder. The clean production build, two focused
runtime suites, static registration oracle, and independent candidate gates
prove those paths offline; only live pretrigger evidence can now accept or
reject their real-device composition.

## Conclusion

`successor admitted offline`: the first candidate's live pretrigger correctly
found a stale runtime-binding identity and no production observer attachment.
Canonical patches `0529`--`0530` repair those two omissions, and exact successor
`54a02dd0...` passes every required offline gate. This is not yet a live
CPU8/CPU9 or frequency result; it authorizes one new guarded deployment and
fresh boot only.

## Follow-up

Publish the frozen successor tooling and evidence, install exact padded
candidate `54a02dd0...` to live-GPT-resolved inactive `boot2`, require a full
matching readback, and shut the device down. On one physical `boot2` selection,
ignore display state as an admission oracle and use exact USB/netcat identity.
The zero-read pretrigger must show one read-only observer attribute, the exact
new record identity, a ready late profile, and zero consumed attempts before the
single bounded runtime is permitted. Keep identical-artifact repeats, longer
load, cpufreq/OPP, extra hotplug, idle, and suspend closed.
