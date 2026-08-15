# Experiment: matched DA921x provider-only control

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-15-da921x-provider-control` |
| Status | offline validation complete; runtime pending |
| Subsystem | legacy DA9213/DA9214/DA9215 regulator provider and boot serviceability |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-15 America/New_York |
| Investigator(s) | repository owner and Codex |
| Tracking issue | none |

## Question or hypothesis

Does the exact current Linux 7.1 provider-only profile reach the existing
USB/netcat or retained-pstore evidence boundary when the default-off observer
and its four extra live reads are absent?

This is a matched control for the repeated pre-transport result of the
[`2026-08-15-da921x-readonly-observer`](../2026-08-15-da921x-readonly-observer/README.md)
candidate. It does not retry that artifact and does not test CPU8/CPU9.

## Provenance and environment

- Repository commit: `1ab09cd9ef39a9c99c82e639dcbc15cb6040c74c`.
- Kernel release: `7.1.3-gemini-da921x-resource`.
- Build profile: `da921x-resource-only-provider`.
- Patchset SHA-256: `eacf5b0f279ee8f9eababa1b191bfb4ba2b00efce87a0674981cc78097b49ef0`.
- Configuration SHA-256: `56a08dd0f2f4400044f15c2b597e23bbaeb1bd806658670c2d5facf3152d6ac6`.
- Build backend: Buildbox only; no native VM build.
- Boot path: Android-v0/LK container to live-GPT logical `boot2` only.

## Safety assessment

The control uses the already reviewed read-only provider: chip identity reads,
two regulator descriptors, and no setter or register-data write helper. The
observer is not compiled, so its four selector/enable reads and marker are
absent. CPU8 and CPU9 admission remains closed. The runtime probe reads only
kernel identity, CPU sets, filtered dmesg, driver binding, and regulator class
names through the existing initramfs netcat shell.

The guarded installer resolves logical `boot2` from live GPT, requires it to be
inactive and unmounted, records the predecessor checksum without creating a
fresh backup, validates an exact 16 MiB candidate, and requires full readback
and byte comparison. It then shuts ordinary Gemian down so the owner can select
boot2. No other partition is authorized.

## Associated code

- [`scripts/build-candidate.sh`](scripts/build-candidate.sh): source-pinned,
  deterministic control-container builder.
- [`scripts/test-candidate.py`](scripts/test-candidate.py): independent parser
  and structural-mutation validator.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh): exact guarded boot2
  installer and shutdown wrapper.
- [`scripts/remote-runtime-probe.sh`](scripts/remote-runtime-probe.sh): bounded
  read-only control probe.
- [`scripts/collect-runtime.sh`](scripts/collect-runtime.sh): exact USB/netcat
  collector; raw capture stays below ignored `artifacts/`.
- [`scripts/validate-runtime.py`](scripts/validate-runtime.py): frozen matched-
  control classifier.
- [`scripts/test-runtime-tools.py`](scripts/test-runtime-tools.py): positive,
  negative, and static safety checks.

## Procedure

1. Build the exact pushed commit with
   `./scripts/build-kernel --backend buildbox` and profile
   `da921x-resource-only-provider`.
2. Fetch only the validated Buildbox package and recheck its full manifest.
3. Compare its patch series, Gemini DTB, configuration, and decompressed Image
   with the observer package.
4. Assemble the Android-v0/LK image in independent roots, validate all LK
   gates, and reject structural mutations.
5. Freeze the exact candidate, hypothesis, runtime decision map, installer,
   and collector; commit and push before device action.
6. Install only the exact candidate to live-GPT logical boot2, require full
   readback, and shut ordinary Gemian down.
7. Arm the collector before one owner-selected boot2 start. If the candidate
   returns before USB, recover pstore immediately from the new Gemian boot.

## Observations

Buildbox completed all 267 patches, the exact provider-only profile, Image,
and 119 DTBs. The fetched package passes every manifest checksum. Against the
failed observer package, the patch series and Gemini DTB are byte-identical;
the generated configuration differs on exactly two lines: the unique local
version and observer disabled instead of enabled. Both Images decompress to
13,762,568 bytes and advertise the same 14,352,384-byte arm64 effective size.
See the [Buildbox receipt](results/buildbox-20260815.txt).

The exact package and unchanged serviceability ramdisk produced byte-identical
independent raw and padded images. Both parsers pass all 32 LK gates and the
independent validator rejects six structural mutations. The raw image SHA-256
is `76d32c74a8ffb714bd10ee7b2e6d1483e4c87e5fa62f0f1ec47d121ea8b95fa9`;
the exact 16 MiB boot2 SHA-256 is
`3188d474f5d6989a0eb0782cdfac781efaf43dd42a0bd11481277050e735f8a2`.
The runtime and deployment tools pass syntax, ShellCheck, classifier mutations,
source-pinned derivation, and static no-write checks. See the
[offline review](results/offline-validation-20260815.txt).

The [predeployment hypothesis](results/predeployment-hypothesis-20260815.txt)
and [decision map](results/runtime-decision-map-20260815.txt) freeze the control
result before device action. Runtime remains pending.

## Analysis

This is the smallest current-tree discriminator available after two identical
observer boots failed before USB and retained pstore. It holds the patch series,
DTB, ramdisk, LK layout, provider registration, CPU baseline, and recovery
policy fixed while removing the observer and its four live reads. The unique
release and container identity provide attribution; they are not evidence by
themselves.

If the exact control reaches USB or leaves attributable pstore, the failure is
localized to the observer-enabled delta. If it fails at the same pre-transport
boundary with no attributable pstore, the observer is not distinguished and
localization moves to the current base/container boundary against the last
known retained-pstore baseline.

## Conclusion

The matched control is a validated boot candidate offline. No runtime hardware
claim is made yet. Provider setters, transition ownership, hardware writes,
and CPU8/CPU9 admission remain closed.

## Follow-up

Follow the single ordered action in [`docs/ROADMAP.md`](../../docs/ROADMAP.md):
deploy this exact candidate, shut down, pre-arm the collector, and perform one
control boot. Do not repeat the observer candidate.
