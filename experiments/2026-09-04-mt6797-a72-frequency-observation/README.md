# Experiment: attributable MT6797 Cortex-A72 frequency observation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-04-mt6797-a72-frequency-observation` |
| Status | `running`; EPROTO diagnostic installed, read back, and shut down |
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

No device action occurred during the new failure-stage offline gate. Exact
candidate `d4eb9cb9...` may use the standing guarded `boot2` workflow: live GPT
resolution, inactive/unmounted target checks, no fresh backup, full 16 MiB
readback, and clean shutdown. Its runtime makes one userspace observer request;
on failure it preserves every emitted six-line callback record, starts no load,
makes no additional request, and issues no reboot. Longer load after an
observer failure and all policy experiments remain closed.

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
- `results/successor-deployment-20260904.txt`: live-GPT target resolution,
  predecessor, exact full readback, no-backup policy, and confirmed shutdown.
- `results/successor-runtime-attempt-1-frequency-before-rejected-20260904.txt`:
  exact live CPU8/CPU9 stage-18 success, observer-first-read rejection,
  changed-ID retained proof, and the decision-changing repeat boundary.
- `results/successor-repeat-readiness-20260904.txt`: published host-only error
  capture, exact already-current `boot2` readback, no-write decision, and
  confirmed shutdown before the one admitted repeat.
- `results/successor-runtime-attempt-2-eproto-20260904.txt`: repeated live
  CPU8/CPU9 stage-18 success, exact two-callback `EPROTO` observation, retained
  recovery, and the no-more-identical-repeat decision.
- `results/eproto-patch-generation-20260904.txt`: strict Buildbox generation,
  replay, source, style, and six-state failure-trace proof for canonical
  patches `0531` and `0532`.
- `results/eproto-focused-kunit-20260904.txt`: exact clean-revision Buildbox
  compile and isolated no-network 5/5 arm64 KUnit proof for the failure-stage
  diagnostic and its unchanged attempt/call budgets.
- `results/eproto-offline-candidate-20260904.txt`: exact production Buildbox
  package, DT, Android-v0/LK container, runtime-tool, mutation, and independent
  candidate admission for the new attributable diagnostic.
- `results/eproto-deployment-20260904.txt`: live-GPT target resolution,
  predecessor replacement, exact full-partition readback, no-backup policy,
  and confirmed shutdown for the attributable diagnostic.

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
11. If the first observer read fails without preserving its kernel errno,
    publish an immediate failure-log path and permit one identical-candidate
    repeat solely to classify that error before selecting a code change.

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
- Published tooling commit `198286f6...` froze the admitted identities and
  direct-USB capture path. Its guarded installer then resolved inactive live-GPT
  `boot2` as `/dev/mmcblk0p30`, distinct from Gemian root `/dev/mmcblk0p29`,
  under stable external power at 100%/Good. It replaced retired predecessor
  `03cbaa72...`, synchronized and flushed the write, independently read and
  compared all 16 MiB as exact successor `54a02dd0...`, made no new backup,
  issued no reboot, and confirmed clean shutdown. See
  [results/successor-deployment-20260904.txt](results/successor-deployment-20260904.txt).
- The fresh successor boot reached exact release
  `7.1.3-gemini-a72-frequency-thermal`, record `018de915...`, and boot ID
  `122934e8...` over direct USB while the owner observed no visible console.
  Its zero-read frame passed with one mode-0444 observer, thermal serviceability,
  a ready late profile, CPUs 0--7 online, CPUs 8--9 offline, and pristine
  observer/lifecycle accounting.
- The initially generated runtime inherited the predecessor lifecycle release
  check and rejected `kernel-identity` before any remount, trigger, CPU request,
  or observer read. After correcting the host-only materialization, the same
  pristine boot committed one trigger. CPU8 booted once, CPU9 booted before and
  after its one down/restore transaction, the binding record returned zero at
  stage 18, and CPUs 0--9 were online. The first frequency read then failed
  before printing a sample, so the finite workload never started. The old host
  failure path did not preserve the kernel errno.
- The device returned automatically to changed-ID Gemian boot
  `8c26b876...`; no native reboot command had been issued. Private recovery left
  all remote records intact and decoded the CRC-valid hotplug ledger as stage
  18, `restored-success`, error zero, online mask `0x3ff`, members `0x3`, and
  one call each to CPU_OFF, affinity, CPU8 IPI, and restore CPU_ON. The thermal
  ledger independently ended `probe-complete`/success. See
  [results/successor-runtime-attempt-1-frequency-before-rejected-20260904.txt](results/successor-runtime-attempt-1-frequency-before-rejected-20260904.txt).
- Commit `cecfeb50...` published the exact runtime identity repair, immediate
  observer-failure log capture, attempt-2 private output path, and this runtime
  record. The guarded readiness check then resolved inactive live-GPT `boot2`
  as `/dev/mmcblk0p30`, found its full checksum already equal to
  `54a02dd0...`, performed no write or backup, independently re-read the full
  16 MiB under stable external power, and confirmed clean shutdown. See
  [results/successor-repeat-readiness-20260904.txt](results/successor-repeat-readiness-20260904.txt).
- The one admitted repeat passed its pristine frame on exact mainline boot ID
  `196f51e7...` and again completed the full stage-18 lifecycle with CPU8 once,
  CPU9 before and after restore, and CPUs 0--9 online. Its first userspace
  observer request generated two kernel callbacks, attempts 1 and 2, both with
  `ret=-71` (`EPROTO`). The immediate failure frame captured those lines and
  terminal CPU/status state; it issued no additional observer request, started
  no load, and requested no reboot.
- Automatic changed-ID Gemian recovery `d9252db6...` again decoded the hotplug
  ledger as stage 18, restored-success, error zero, online mask `0x3ff`, and
  the one-call CPU_OFF/affinity/CPU8-IPI/CPU_ON budget. Thermal again ended
  probe-complete/success, and remote pstore records were left intact. The
  offline classifier now accepts consecutive identical failure lines and
  preserves `attempts=1-2-of-3`, two callbacks, and errno `-71`. See
  [results/successor-runtime-attempt-2-eproto-20260904.txt](results/successor-runtime-attempt-2-eproto-20260904.txt).
- The first failure-stage generation was rejected only by strict style checks
  and admitted no package. Corrected exact clean pushed revision `5367f771...`
  then generated and replayed canonical patches `0531` and `0532` from exact
  prepared source state `93fbb771...`. Source/path validation and strict
  Checkpatch pass with zero errors, warnings, or checks. The six-state trace
  covers success, both transport failures, both record-shape failures, and
  decoder rejection while adding no hardware call, CPU request, write, DT
  change, or attempt. See
  [results/eproto-patch-generation-20260904.txt](results/eproto-patch-generation-20260904.txt).
- Exact clean published revision `538bfb37...` built the 521-patch focused
  profile on Buildbox. Its isolated no-network arm64 QEMU run passed all five
  named observer cases, including the complete failure-stage matrix, with no
  failure or skip. This is hardware-free diagnostic proof only; it does not
  admit a candidate or make a live-frequency claim. See
  [results/eproto-focused-kunit-20260904.txt](results/eproto-focused-kunit-20260904.txt).
- Exact clean published build revision `80abfffb...` then compiled the same
  521-patch production profile on Buildbox. Package, configuration, DT,
  provenance, and all 124 packaged DTB checks passed. Independent composition
  produced DT `626095e4...`, raw Android-v0/LK image `9d0f27dc...`, and exact
  padded candidate `d4eb9cb9...`; all structural and container gates pass.
  The revised host path preserves up to three complete ordered six-line
  failure records, associates both callbacks from one userspace read, and
  rejects malformed traces without another read or load. See
  [results/eproto-offline-candidate-20260904.txt](results/eproto-offline-candidate-20260904.txt).
- Published tooling revision `158f896c...` froze the exact candidate,
  installer, zero-read pretrigger, and multi-callback runtime paths. Guarded
  deployment resolved inactive live-GPT `boot2` as `/dev/mmcblk0p30`, distinct
  from Gemian root `/dev/mmcblk0p29`, and replaced retired `54a02dd0...` under
  stable external power. The synchronized, flushed write independently read
  back all 16 MiB as exact `d4eb9cb9...`, made no new backup, issued no reboot,
  and confirmed shutdown. See
  [results/eproto-deployment-20260904.txt](results/eproto-deployment-20260904.txt).
- The fresh diagnostic boot passed its exact pristine pretrigger on boot ID
  `8f6181a5...` and completed stage 18 with CPUs 0--9 online. One userspace
  observer read produced callbacks 1 and 2; both passed clock and BigiDVFS
  transport and shape checks, then returned `-EPROTO` at `decode` with the same
  raw tuple. The packed divider word was `0x00000008`: Big selector 8, with
  LL/L/CCI selectors all zero. No additional observer request or workload ran,
  no reboot was requested, and the device was left running. See
  [results/eproto-runtime-decode-zero-divider-20260904.txt](results/eproto-runtime-decode-zero-divider-20260904.txt).

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
successor fixed the two integration omissions and its live transaction now
proves the physical binder can complete stage 18 with both Cortex-A72 CPUs
online on this exact configuration. That is a material current-mainline CPU
result even though the larger composite acceptance test rejected.

The failure-stage candidate closes the remaining ambiguity. Both callbacks
passed the observer's transport, ABI, generation, and reserved-field gates and
failed only in the decoder. Its exact raw word gives the B cluster the admitted
identity selector 8 but gives LL, L, and CCI selector 0. The pinned public
vendor `_cpu_freq_calc()` treats zero as no division; the current pure decoder
omitted zero from its explicit identity encodings. That omission fully explains
both `EPROTO` results without weakening the already proven lifecycle or backend
stability.

The one `busybox cat` request again caused two sysfs show callbacks after the
negative return. That is an observed transport property, not a second request
made by the failure handler. The classifier preserved the complete stage/raw
record for both. The selected repair accepts only selector zero as another
identity encoding, continues rejecting all other unknown selectors, and adds
the exact live tuple to pure KUnit. The diagnostic candidate has no reason to
boot again.

## Conclusion

`stage-18 CPU8/CPU9 repeated; live zero-divider decoder repair selected`: exact
diagnostic candidate `d4eb9cb9...` passed its pristine boot and repeated stage
18 with CPUs 0--9 online. Both callbacks failed only at decode and preserved an
identical complete raw tuple. The result identifies omitted live selector zero
semantics for LL/L/CCI; it is not yet a frequency or composite load pass. The
next candidate must contain the narrow, hardware-free-proven decoder repair.

## Follow-up

Physically select boot2, then require the exact zero-read pretrigger before one
stage-18 transaction and observer request. A failure must yield complete
stage/raw records and stop before load; a valid sample may continue only into
the already-bounded three-sample workload. The full installation/readback and
shutdown gate is complete for exact `d4eb9cb9...`. Do not repeat exact
`54a02dd0...`. Keep cpufreq/OPP, extra hotplug, idle, and suspend closed.
