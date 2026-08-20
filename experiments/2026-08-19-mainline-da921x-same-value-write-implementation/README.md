# Experiment: mainline DA921x same-value-write implementation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-19-mainline-da921x-same-value-write-implementation` |
| Status | `running`; exact boot2 deployment and shutdown pass, one runtime attempt pending |
| Subsystem | DA921x regulator, MT6797 I2C6 ledger and transaction window |
| Device variant | Planet Gemini PDA named unit |
| Date(s) | 2026-08-19--20 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 6 |

## Question or hypothesis

Can the exact contract admitted by the fresh pre-write review be represented as
three logical, default-off kernel patches and exhaustively exercised without a
physical adapter before any candidate or device action exists?

The source claim is falsifiable: the production sequence must consume exactly
12 transfers under one root lock, attempt `[0xda, 0x46]` once at ordinal 6,
stop on every error or mismatch, and restore retries on every exit. The
controller must independently attribute both write bytes.

## Provenance and environment

- Fixed review parent: `ca3caa3e3c814da61a0ca113c69fc87e3bc1140e`.
- Frozen review contract: [pre-write contract](../2026-08-19-mainline-da921x-same-value-write-preflight-review/contract.json),
  SHA-256 `3f851743de01404a728327a9763aadf6c6dc4ab30024a9be7912841500a5850b`.
- Managed Buildbox parent state:
  `3cd27f8d5432e8de0a495d2b9f9c266f8de9cb78077f9091bcc35a2548edcdfc`.
- The exact five parent file checksums are pinned in
  [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox).
- Focused Buildbox commit: `169d86ef5bc961a30bf07d2da4cb39234c9914cd`.
- Focused release: `7.1.3-gemini-da921x-same-write-kunit`.
- Production Buildbox commit: `7c012d736f78898be08bfd8430a25c8708a62e1d`.
- Production release: `7.1.3-gemini-da921x-same-write`.
- Exact padded boot2 candidate: SHA-256
  `b81813d13acc970c7b9203b89ec034921ef6f7e1017539a0c228754619af7b22`.
- No native VM build is permitted. The focused Buildbox compile and isolated
  network-free QEMU run passed; no device action occurred.

## Safety assessment

The hardware-free phase compiled on Buildbox and ran under arm64 QEMU with an
unregistered fake adapter and networking disabled. It performed no physical
I2C transaction, device access, boot image construction, partition write,
regulator action, or CPU request.

Patch 0291 contains a real register-write path, but it is default-off and
reachable only through one exact-token device attribute in the isolated
profile. A source patch, compile result, or KUnit pass does not authorize that
path on hardware. Package, candidate, collector, and predeployment gates now
pass offline; physical writing remains closed until this evidence is published
and the live known-good-OS serviceability gates pass. Candidate construction
contacted no device and wrote no hardware. CPU8 and CPU9 remain offline and
unrequested.

## Associated code

- [`contract.json`](contract.json) freezes the three-patch plan and workflow.
- [`DESIGN.md`](DESIGN.md) describes the production and test seams.
- [`scripts/validate.py`](scripts/validate.py) validates the implementation
  contract and its unsafe-mutation matrix.
- [`scripts/source_edits.py`](scripts/source_edits.py) applies the three
  deterministic logical source phases.
- [`scripts/validate_source.py`](scripts/validate_source.py) validates the
  complete edited-source semantics.
- [`scripts/validate_patches.py`](scripts/validate_patches.py) validates the
  normal patch inventory, logical path boundaries, and hardware-free test.
- [`scripts/test-patch-validator.py`](scripts/test-patch-validator.py) rejects
  13 decision-changing identity, path, payload, ordering, and hardware-escape
  mutations of the normal patch set.
- [`scripts/validate_admission.py`](scripts/validate_admission.py) pins the
  imported patch hashes, focused profile ancestry, fragments, and 87-profile
  canonical-series audit.
- [`scripts/run-kunit-qemu`](scripts/run-kunit-qemu) verifies the exact fetched
  Buildbox package and launches one bounded, network-free arm64 virtual boot.
- [`scripts/classify-kunit.py`](scripts/classify-kunit.py) requires the exact
  six-case suite and its post-test boundary before reporting a pass.
- [`scripts/test-kunit-classifier.py`](scripts/test-kunit-classifier.py)
  rejects decision-changing runtime and package-manifest mutations.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox) generates,
  replays, source-validates, and strict-style-checks the patches on Buildbox.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh) assembles the exact
  Android-v0/LK candidate twice from pinned package, ramdisk, and DTB inputs.
- [`scripts/test-candidate.py`](scripts/test-candidate.py) independently checks
  package provenance, container layout, DT semantics, and eight mutations.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh) source-pins the guarded
  live-GPT boot2 installer and clean-shutdown policy.
- [`scripts/collect-runtime.sh`](scripts/collect-runtime.sh) preserves the exact
  pre-trigger state, sends one token with no retry, and reboots only after a
  durable terminal classification.
- [`scripts/classify-runtime.py`](scripts/classify-runtime.py) accepts exact
  success and both bounded terminal failure families.
- [`scripts/test-runtime-classifier.py`](scripts/test-runtime-classifier.py)
  rejects 13 payload, accounting, sysfs, CPU, and transaction mutations.
- [`scripts/test-collector.py`](scripts/test-collector.py) checks checksum pins
  and host-side one-shot ordering without contacting the device.
- [`results/source-tool-validation-20260819.txt`](results/source-tool-validation-20260819.txt)
  records the pre-generation validations.
- [`results/patch-generation-attempt-73fb7a3-20260819.txt`](results/patch-generation-attempt-73fb7a3-20260819.txt)
  records the first formal Buildbox rejection and bounded correction check.
- [`results/patch-generation-success-2759b83-20260819.txt`](results/patch-generation-success-2759b83-20260819.txt)
  records the validated package, exact canonical imports, and profile audit.
- [`results/kunit-harness-validation-20260819.txt`](results/kunit-harness-validation-20260819.txt)
  records the hardware-free runner and classifier validation.
- [`results/kunit-build-runtime-success-20260820.txt`](results/kunit-build-runtime-success-20260820.txt)
  records the exact focused Buildbox package and single QEMU 6/6 pass.
- [`results/production-candidate-validation-20260820.txt`](results/production-candidate-validation-20260820.txt)
  records the production Buildbox package and independent LK candidate proof.
- [`results/collector-prearm-validation-20260820.txt`](results/collector-prearm-validation-20260820.txt)
  records the hardware-free runtime-tool validation.
- [`results/predeployment-hypothesis-20260820.txt`](results/predeployment-hypothesis-20260820.txt)
  freezes the one-attempt observation and decision map.
- [`results/deployment-1-20260820.txt`](results/deployment-1-20260820.txt)
  records the live-GPT target, predecessor, exact readback, and clean shutdown.

## Procedure

1. Validate the implementation contract against the checksum-pinned pre-write
   review.
2. Apply the three deterministic phases to bounded copies of the exact managed
   Buildbox parent files.
3. Validate exact source semantics and strict kernel style.
4. Commit and push these clean project inputs.
5. Generate and fetch three normal patches through the first-class Buildbox
   lane; replay them and reject any path, payload, safety, or identity drift.
6. Admit the exact patches to canonical order, add isolated implementation and
   KUnit profiles, and audit every manifest profile.
7. Build the exact clean pushed KUnit profile through Buildbox and run the
   hardware-free suite before constructing any boot candidate.
8. Build the exact production profile through Buildbox; fetch only its
   checksum-validated package.
9. Assemble the LK container twice, validate it independently, and validate
   the one-shot collector and all terminal runtime classifications.
10. Publish the offline evidence before read-only live serviceability or boot2
    deployment.

## Observations

- The deterministic editor applies cleanly to the exact managed parent.
- The edited-source validator passes the three logical patches, six KUnit
  cases, all 12 transfer-failure ordinals, and all 11 read-value mismatches.
- The prototype combined-delta check reported zero errors, zero warnings, and
  zero checks across 533 changed lines. Formal per-patch checking then exposed
  14 KUnit-only indentation checks in patch 0292; patches 0290 and 0291 were
  clean.
- After correcting only those generated-source formatting defects, a bounded
  Buildbox file check reports zero errors, zero warnings, and zero checks
  across the 309-line generated KUnit source. That check preceded the formal
  rerun recorded next.
- Formal generation at corrected commit `2759b83ce522` passed exact replay,
  source semantics, inventory, and strict style for all three patches. The
  fetched package passed its SHA-256 manifest.
- Canonical patches 0290--0292 exactly match the package. The two focused
  profiles extend the proven transaction-window profile, and the manifest
  series audit passes all 87 profiles; its self-test rejects eight mutations.
- The normal-patch validator accepts the exact imported set and rejects all 13
  mutations covering identity, subject order, synthetic sign-off, ledger
  attribution, payload, lock, call count, transfer seam, test count/address,
  physical-adapter escape, changed paths, and extra patch inventory.
- The focused QEMU harness passes Bash syntax and ShellCheck. Its classifier
  accepts the exact six-case fixture and rejects 11 runtime mutations plus
  three package-manifest mutations. It requires `-nic none`, exact package and
  profile identity, one focused KUnit symbol, and the expected bounded exit.
- The KUnit fixture uses address `0x2a`, registers no adapter or client, maps no
  MMIO, and performs no physical transfer.
- The focused Buildbox build at signed commit `169d86ef5bc9` compiled both
  `da9213-legacy-regulator.o` and `da9213-legacy-write-test.o`, linked release
  `7.1.3-gemini-da921x-same-write-kunit`, and passed package checksums.
- The one planned network-free QEMU run passed the exact ordered six-case
  suite with zero failures and zero skips. Its grouped cases exercised all 12
  transfer-failure ordinals and all 11 read-value mismatch ordinals.
- The production profile built at exact clean pushed commit `7c012d736f78`.
  Its arm64 release, package manifest, configuration, and image hashes pass;
  KUnit is disabled while the default-off same-value path is enabled.
- Two independent raw assemblies are byte-identical at `b84f3ba8d86e...`;
  two independent 16 MiB padding paths are byte-identical at
  `b81813d13acc...`. All 32 LK gates pass.
- The independent candidate validator checks the Android-v0 fields,
  kernel/DT/ramdisk placement, canonical ID, serviceability DT, CPU closure,
  and rejects eight semantic DT mutations.
- Runtime fixtures pass the exact 20-entry pre-trigger state, 12-action
  success, a pre-write terminal failure, and a post-write terminal failure.
  Thirteen decision-changing mutations are rejected.
- The collector pins the candidate, probes, and classifier; makes the
  pre-trigger capture durable before the token; permits one token, zero
  retries, and zero second writes; and sends native reboot only after a
  durable terminal classification.
- No device contact, partition write, or physical I2C transaction occurred in
  this production/candidate/tooling phase.

## Analysis

The controller patch and regulator patch are intentionally separate. The
controller owns physical attribution and can validate the exact retained
pointer-read prefix while the caller already holds the root lock. The regulator
owns the one-shot policy, exact bytes, action order, failure states, and retry
lifetime. A third patch tests the production sequence through injected
read-only ledger, transfer, and delay seams.

This avoids using the B2 single-transfer helper, which would release the root
lock between actions. The production operations instead bind the sequence to
`__i2c_transfer()` only after one lock is held, while KUnit binds the same
sequence to an unregistered fake.

## Conclusion

`confirmed` for the complete hardware-free implementation proof: the exact
three patches replay, compile, pass semantic and strict-style validation, and
the production sequence passes its exact 6/6 KUnit suite with every required
failure and mismatch ordinal covered. The superseded formal attempt at
`73fb7a3` remains rejected.

The exact production package, offline boot candidate, collector, and
predeployment decision map pass. The sanitized predeployment evidence was
published at signed commit `b1d251abc081`. Known-good Gemian then resolved
inactive, unmounted live-GPT `boot2` as `/dev/mmcblk0p30` while root remained
`/dev/mmcblk0p29`; stable power, exact predecessor, synchronized write, flush,
and two independent full-partition checks passed. The device shut down cleanly
without an automatic reboot. The single selected-boot runtime attempt is now
next. CPU8/CPU9 admission remains closed regardless of its result.

## Follow-up

Arm the checksum-pinned collector, then select boot2 exactly once. It must
retain the accepted pretrigger capture before sending the sole token, preserve
the terminal classification before requesting native reboot, and observe a
changed-identity Gemian return. Do not retry the token or repeat the candidate.
The authoritative ordered exit remains
[Roadmap Gate 6](../../docs/ROADMAP.md#6-prove-one-bounded-writable-operation).
