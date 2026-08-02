# Experiment: Gemian bounded A72 owner-observer boot image

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-02-gemian-a72-bounded-observer-boot` |
| Status | `inconclusive`: offline construction and guarded `boot2` deployment pass with full readback and shutdown; first boot and one-cycle runtime evidence remain pending |
| Subsystem | Gemian 3.18 MT6797 A72 owner observer and retained Planet LK Android-v0 boot path |
| Device variant | Current named Gemini PDA unit |
| Date(s) | 2026-08-02 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Can the exact timing-bounded owner-observer kernel field be placed in an
otherwise byte-lineage-equivalent Gemian Android-v0 container, so one later
natural CPU8 online/offline transaction can be captured without changing the
ramdisk, command line, addresses, appended DTB, or known-good recovery path?

This experiment first answers only the offline container question. A valid
image is not hardware evidence and does not itself authorize deployment.

## Provenance and environment

- Reviewed project commit: `bc01fc33ec60540b86cd1133697c6fc4a6d1b857`.
- Public hook-equivalent vendor source:
  `59e00a9144d782e148332009a835b99c43382467`.
- Observer patchset SHA-256:
  `85ac017a2fec821ee930a74d021cb6d2224ea958929c5bbffaf7ec480e19f9c9`.
- Exact observer `Image.gz-dtb` SHA-256:
  `5864c083a156fcb023e62a5e8dd3fd4c75d68fb119c82492ed4653065ca39a18`.
- Exact project-start full-backup Gemian boot image SHA-256:
  `1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513`.
- Exact active ramdisk field SHA-256:
  `a1ee05445e9a2bd8fbc1f75d7cda326b9ca7a6d3b644cbb1d5fc0ac167835be4`.
- Retained container: Android boot image v0, 2048-byte pages, kernel address
  `0x40080000`, ramdisk `0x45000000`, second `0x40f00000`, tags
  `0x44000000`, empty name, and command line
  `bootopt=64S3,32N2,64N2 log_buf_len=4M`.
- The exact vendor ARM64 header contract is text offset `0x80000`, nonzero
  image size, and legacy flags `0x0`, yielding placement base `0x40000000`.
- Build backend: the kernel was built only on Buildbox. Container assembly is
  local serialization of already validated binary inputs, not a native kernel
  build.

## Safety assessment

Offline assembly reads only the ignored Buildbox bundle and the project-start
full-device backup. It does not access the device, create another backup, write
a partition, request a CPU, or modify the private source artifacts. Outputs
remain mode 0600 below ignored `artifacts/boot-candidates/`.

The serializer rejects any input identity drift, symlink, empty file, header or
address change, ramdisk mismatch, nonzero second/legacy-DT field, invalid ARM64
gzip stream, malformed appended DTB, nonzero container padding, or image larger
than logical `boot2`. It assembles two independent destinations, compares them
byte-for-byte, pads the raw image to 16 MiB twice by different methods, and
requires identical full images.

A later deployment must separately name the exact candidate and test
hypothesis. It must resolve live logical `boot2`, preserve the known-good Gemian
path, verify full-partition readback, and shut down after the verified write.
The first boot must stop without a load pulse if the kernel identity, observer
ABI, USB shell, power state, or CPU8/CPU9-offline baseline differs.

## Associated code

- [`scripts/assemble.py`](scripts/assemble.py): identity-pinned Android-v0
  replacement serializer and structural validator.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh): two-assembly,
  two-padding, manifest, and private-output orchestration.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh): source-pinned guarded
  logical-`boot2` installer with exact predecessor/candidate gates, no fresh
  backup, full readback, private evidence, and shutdown.
- [`scripts/remote-initial-probe.sh`](scripts/remote-initial-probe.sh): exact
  build/ABI/power/temperature/CPU identity gate and one immutable observer copy;
  it contains no load or writable operation.
- [`scripts/collect-initial.sh`](scripts/collect-initial.sh): exact-dependency,
  bounded authenticated Gemian collector with ignored mode-0600 output.
- [`scripts/validate-initial.py`](scripts/validate-initial.py): strict observer
  ABI, record, sequence, CPU, disposition, and no-load validator.
- [`scripts/test-initial.py`](scripts/test-initial.py): positive scenarios and
  ten fail-closed/static safety checks.
- [`results/predeployment-hypothesis-20260802.txt`](results/predeployment-hypothesis-20260802.txt):
  exact one-cycle hypothesis, expected ordering, stop conditions, outcome
  matrix, and guarded deployment boundary.
- [`results/installer-validation-20260802.txt`](results/installer-validation-20260802.txt):
  source identity, exact candidate/predecessor gates, retained live-GPT safety
  checks, syntax, and managed-VM ShellCheck.
- [`results/deployment-20260802.txt`](results/deployment-20260802.txt): exact
  live target, predecessor, candidate/readback identity, power gate, cleanup,
  and confirmed shutdown.
- [`results/initial-collector-validation-20260802.txt`](results/initial-collector-validation-20260802.txt):
  dependency hashes, bounded behavior, syntax, ShellCheck, positive scenarios,
  and fail-closed checks.
- [Owner-observer review](../2026-07-23-gemian-a72-owner-observer/README.md):
  exact compiler, stack, lock, and bounded timing evidence.
- [Calibrated two-worker trigger](../2026-07-23-gemian-a72-load-assisted-observation/README.md):
  the only later load pulse permitted by the planned runtime phase.

Invocation from the repository root:

```sh
experiments/2026-08-02-gemian-a72-bounded-observer-boot/scripts/build-candidate.sh \
  --bundle artifacts/buildbox/bc01fc33ec60540b86cd1133697c6fc4a6d1b857/gemian-observer-bc01fc33ec60 \
  --active-boot artifacts/device-partitions/20260715T020041Z/mmcblk0p22-boot.img \
  --output-parent artifacts/boot-candidates
```

After the owner selects `boot2`, the first runtime action is only:

```sh
experiments/2026-08-02-gemian-a72-bounded-observer-boot/scripts/collect-initial.sh \
  --tag first-boot-20260802
```

This invocation always forbids load. An empty/offline capture can only make a
separately validated second pre-pulse gate eligible.

## Procedure

1. Validate exact private input identities and the complete Buildbox manifest.
2. Parse the active container and prove its exact ramdisk/header contract.
3. Validate the observer gzip stream, ARM64 header, and single appended DTB.
4. Assemble the replacement container twice and require byte equality.
5. Construct the exact 16 MiB image by sparse extension and zero overlay;
   require byte equality and a fully zero tail.
6. Store the private candidate, manifest, analysis, and provenance below the
   ignored output root. Record only sanitized hashes and sizes here.
7. Apply the exact one-cycle runtime hypothesis, event order, retrieval
   boundary, stop conditions, and result-to-next-action matrix recorded with
   this experiment.

## Observations

Two independent raw assemblies produced the same 14,794,752-byte Android-v0
image with SHA-256
`d3ec1e13123e662076bdbbbde86f118a46cc30f4490f928e216bd783b37e088a`.
Sparse extension and independent zero-overlay construction produced the same
16,777,216-byte `boot2` image with SHA-256
`33ace2c30a8877be2a4b917135aa994ad718201f98ec36d8506a3b1f1d03a7aa`.
The private manifest passes.

The exact kernel field is 8,436,300 bytes, decompresses to 20,095,168 bytes,
and ends in one 130,745-byte appended DTB. The exact active 6,354,621-byte
ramdisk, empty name, command line, page size, addresses, empty second field, and
empty legacy-DT field are retained. The existing independent boot analyzer
reports `layout=complete`. See
[`results/offline-container-validation-20260802.txt`](results/offline-container-validation-20260802.txt).

The guarded installer then resolved live logical `boot2` as `/dev/mmcblk0p30`
while known-good Gemian remained rooted on `/dev/mmcblk0p29`. Its exact
predecessor was Stage27 SHA-256 `805c3c1ce281…`; power was present and the
battery was 100%/Good. The synchronized/flushed write and independent full
readback both matched padded SHA-256 `33ace2c30a88…`. No fresh backup was made,
temporary copies were removed, and the device was cleanly shut down and
confirmed unreachable. It has not booted the new image yet.

## Analysis

Byte-identical construction establishes a reproducible container and exact
payload lineage. It does not establish that the hook-equivalent public source
matches every behavior of the active private kernel, that the observer does not
alter the one natural transition, or that CPU8 can be enabled safely in
mainline.

## Conclusion

`confirmed` for offline container identity/layout and guarded deployment with
full readback; `inconclusive` for runtime and hardware behavior. The next boot,
not the write itself, determines whether the observer kernel is serviceable.

## Follow-up

The device is powered off after verified deployment. The owner may now select
`boot2` manually. On first serviceability, apply the predeployment contract:
retrieve identity and the initial immutable observer copy before deciding
whether the single calibrated two-worker pulse is allowed. The exact no-load
collector is validated and ready.
