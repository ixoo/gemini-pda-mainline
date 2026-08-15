# Experiment: DA921x read-only provider observer

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-15-da921x-readonly-observer` |
| Status | running |
| Subsystem | legacy DA9213/DA9214/DA9215 regulator provider |
| Device variant | Planet Gemini PDA, MT6797; device remains on ordinary Gemian |
| Date(s) | 2026-08-15 America/New_York |
| Investigator(s) | repository owner and Codex |
| Tracking issue | none |

## Question or hypothesis

Can the native Linux 7.1 legacy DA921x provider produce one uniquely
attributable observation proving its identity transcript, two read-only
provider registrations, bounded state reads for both rails, and zero
register-data writes, while failing closed on every partial observation?

## Provenance and environment

- Kernel release: Linux 7.1.3 from the manifest-selected prepared source.
- Parent series: canonical `patches/series` through patch `0277`.
- Build backend: Buildbox only.
- Boot path: none during source design and validation.

## Safety assessment

The proposed observer is default-off and reuses only the provider's existing
`get_voltage_sel`, `list_voltage`, and `is_enabled` operations. It adds no
setter, regulator consumer, IRQ, page selection, register-data write, firmware
call, CPU request, or device write. Hardware-free tests use a fake read
callback. No device backup is needed. Until source, KUnit, full Buildbox,
package, and container validation pass, no boot candidate exists.

## Associated code

- [`DESIGN.md`](DESIGN.md): observation, failure, and lifecycle contract.
- [`scripts/source_edits.py`](scripts/source_edits.py): deterministic bounded
  source transformation used only in a temporary Buildbox Git repository.
- [`scripts/validate_source.py`](scripts/validate_source.py): source contract
  and no-write validation.
- [`scripts/validate_tool.py`](scripts/validate_tool.py): deterministic editor
  contract validation.
- [`scripts/validate.py`](scripts/validate.py): canonical patch, profile, and
  no-write integration validation.
- [`scripts/validate_patch.py`](scripts/validate_patch.py): generated
  format-patch validation.
- [`scripts/test_mutations.py`](scripts/test_mutations.py): decision-changing
  mutation checks.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh): exact portable
  Android-v0/LK container assembly.
- [`scripts/test_candidate.py`](scripts/test_candidate.py): independent
  container parser and mutation validator.
- [`scripts/remote-runtime-probe.sh`](scripts/remote-runtime-probe.sh): bounded
  read-only observer and CPU-state capture streamed to the initramfs shell.
- [`scripts/collect-runtime.sh`](scripts/collect-runtime.sh): exact USB/netcat
  collector with private raw capture.
- [`scripts/validate-runtime.py`](scripts/validate-runtime.py): result
  classifier implementing the frozen decision map.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh): source-pinned guarded
  boot2 installer with dynamic predecessor evidence, no fresh backup, full
  readback, and shutdown.

## Procedure

1. Audit the exact final driver, Device Tree node, and Kconfig on Buildbox.
2. Freeze the read-only observation and cleanup contract.
3. Commit and push the deterministic source tool and validators.
4. Generate one normal experiment-only `git format-patch` from a bounded
   temporary Git repository on Buildbox.
5. Add the patch in canonical order plus isolated observer and KUnit profiles.
6. Run static, mutation, patch-apply, checkpatch, focused KUnit, and normal
   Buildbox validation.
7. Decide from that evidence whether one separately attributable boot2
   candidate is justified.

## Observations

The final Linux 7.1 driver performs the exact two-pass, seven-sample identity
transcript before registering two descriptors. Each descriptor exposes only
`get_voltage_sel`, `list_voltage`, and `is_enabled`. The final driver has two
`__i2c_transfer()` call sites, both combined reads; it has no register-data
write helper or writable regulator operation. The Gemini Device Tree node has
the exact primary and page2 addresses and no regulator child.

Exact pushed tooling commit `3320d44` generated one normal five-path
format-patch from a bounded temporary Git repository on Buildbox. Source
validation and clean application to the full prepared tree passed. Focused
checkpatch passed with zero errors and warnings after excluding only the
synthetic DCO, experiment-file, single-record string, and generated commit-body
notice classes. The repository patch is byte-identical to the Buildbox output:
SHA-256 `6225f78584357a1b59dbe4b210c9cab7271175ebbe3d07b719429d503cad3696`.
See the [patch-generation receipt](results/patch-generation-buildbox-20260815.txt).

Exact implementation commit `d0d511e` passed the isolated KUnit Buildbox
profile and package validation. The fetched image contained the observer and
five test cases. ARM64 QEMU ran all five tests: the success case, each of the
four bounded read-failure positions, incomplete-state refusal, invalid-value
refusal, and cleanup invalidation all passed with no failure or skip. After
the tests completed, the device kernel reached the expected root-filesystem
panic because the isolated VM had no root disk; that post-test condition is
not a KUnit failure. See the [KUnit build](results/kunit-buildbox-20260815.txt)
and [QEMU result](results/kunit-qemu-20260815.txt).

The separate KUnit-free runtime profile then passed a clean Buildbox build and
full fetched-package checksum validation at the same commit and 267-patch
source state. The runtime image contains the observer and its two marker
formats, contains no observer test symbols, and has SHA-256
`3483fb980c8c59ea0a10bf356737391aaa6b49969e39b4a3cee3831774f5fbf9`.
See the [runtime build receipt](results/runtime-buildbox-20260815.txt).

The exact runtime package, the existing mainline DA921x serviceability ramdisk,
and the package Gemini DTB were assembled twice in each of two independent
output roots. All four raw assemblies and all four 16 MiB padding constructions
are byte-identical. The raw Android-v0 image has SHA-256 `1a55a25b7d6bff44`
and the padded boot2 image has SHA-256 `7a3ce120de99d7c5`. Both independent
parsers pass all 32 LK gates and reject six structural mutations apiece. See
the [offline container review](results/offline-container-review-20260815.txt).

The [predeployment hypothesis](results/predeployment-hypothesis-20260815.txt)
and [runtime decision map](results/runtime-decision-map-20260815.txt) freeze the
only success signal as one exact bound record with 14 identity reads, two
providers, four completed provider reads, valid buck states, and zero writes.
Display color and an automatic return to Gemian are explicitly cycle evidence,
not provider evidence.

The source-pinned installer, direct USB/netcat collector, read-only remote
probe, and mutation-tested classifier pass syntax, ShellCheck, exact derivation,
and eight negative classification cases. Both independent candidate roots were
revalidated after the tooling was frozen. The
[tool validation receipt](results/runtime-tool-validation-20260815.txt) sets
the device-write gate only for this exact candidate.

## Analysis

The smallest decision-changing runtime evidence is a one-shot record after
both registrations. It must exercise the same regulator operations exposed by
the descriptors instead of introducing a parallel raw-register reader. A
devres action registered before the provider registrations can distinguish a
normal unbind from a failed later probe and runs after the later provider
devres entries have been released.

Offline evidence now closes the implementation, test, package, and container
uncertainty. It does not establish that the native provider binds on the Gemini
or that the two live rail reads succeed. One exact diagnostic boot, armed with
the read-only USB/netcat collector, is required for that claim.

## Conclusion

Source, mutation, KUnit, runtime Buildbox, package, container, runtime-tool, and
installer validation pass. No runtime hardware claim is made. The exact
candidate earns one guarded boot2 test after this evidence is committed and
pushed.

## Follow-up

Validate and push the frozen runtime/deployment tools, then perform one guarded
boot2 deployment and arm the read-only collector before the owner selects
boot2. Provider setters, hardware writes, transition ownership, and CPU8/CPU9
admission remain closed.
