# Experiment: MT6797 runtime provenance observer

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-14-mt6797-runtime-provenance-observer` |
| Status | `runtime tools accepted; guarded boot2 deployment pending` |
| Subsystem | MT6797 EEM/PPM DVFSP provenance |
| Device variant | Planet Gemini PDA, MT6797; read-only Gemian preflight only |
| Date | 2026-08-14 America/New_York |
| Investigator | Gemini mainline project |

## Question or hypothesis

Can one default-off, read-only observer linked into the complete current Gemian
kernel publish the real EEM calibration lifecycle and PPM table-commit epoch,
while explicitly showing that no coherent transition owner or regulator
provider has been established?

The observer is useful only if the complete vendor kernel links, the selected
configuration differs from `gemini_modular_defconfig` only by the observer and
local version, and the resulting image retains the exact read-only markers.
A compile result cannot establish runtime publication or hardware support.

## Provenance and environment

- Vendor source: `https://github.com/gemian/gemini-linux-kernel-3.18.git`
- Vendor source commit: `d388d350cb2dda8f23b99be6fa5db9628896e87f`
- Generated vendor commit: `f3d2a14bd1b8355c68e59e8bd4be6bc1525f9c24`
- Patch SHA-256: `3520538de1c31ea592c2f0c76af7deef10f5c1ee00689d74bdac17def48dbb11`
- Configuration source: vendor `gemini_modular_defconfig`, with only
  `CONFIG_GEMINI_MT6797_DVFSP_PROVENANCE_OBSERVER=y` and
  `LOCALVERSION=-gemini-provenance-observer` added
- Build backend: Buildbox only, using the pinned Debian Stretch GCC 6.3
  toolchain manifest already used by the Gemian full-link experiments
- Boot path: the exact Android-v0 container, pre-boot contract, runtime
  classifier, and guarded installer pass their separate offline reviews;
  guarded boot2 deployment is the next ordered action

The synthetic patch author is experiment-only and non-certifying. The patch
contains no synthetic `Signed-off-by` and is not submission-ready.

## Safety assessment

The source change is default-off. When selected it creates one mode-0444
debugfs file and records counters under an IRQ-safe spinlock because the exact
EEM completion hook runs from its interrupt handler. It does not register a
regulator, replace a voltage or frequency setter, write a register, change CPU
policy, or admit CPU8/CPU9. The output permanently reports zero owner and
transition handles, `provider=none`, `hardware_write=none`, and closed CPU
admission.

Container construction and runtime-tool validation are host/offline-only. The
exact container preserves the known-good Gemian header and ramdisk, changes only
the validated kernel field and canonical image ID, and is padded to exactly
16 MiB by two independent methods. A later read-only Gemian preflight checked
only OS, root, GPT identity, power, and sudo readiness; it did not read boot2.
No device write or candidate boot has occurred in this experiment yet.

## Associated code

- [`patches/series`](patches/series) selects the single generated vendor patch.
- [`scripts/validate.py`](scripts/validate.py) enforces patch scope, default-off
  selection, read-only output, and the explicit nonclaims.
- [`scripts/build-on-buildbox`](scripts/build-on-buildbox) reconstructs and
  fully links the exact vendor source on Buildbox.
- [`scripts/assemble.py`](scripts/assemble.py) pins the retained Android-v0/LK
  serializer and exact replacement kernel.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh) performs two raw
  assemblies and two independent exact-size padding constructions offline.
- [`scripts/test_candidate.py`](scripts/test_candidate.py) independently pins
  the package, Android header, kernel, DTB, ramdisk, image ID, padding,
  provenance, and negative mutations.
- [`scripts/remote-runtime-probe.sh`](scripts/remote-runtime-probe.sh) reads the
  exact mode-0444 ABI twice without mounting, writing, or changing power state.
- [`scripts/collect-runtime.sh`](scripts/collect-runtime.sh) waits for the exact
  direct USB/netcat path and retains one private, checksummed capture.
- [`scripts/validate-runtime.py`](scripts/validate-runtime.py) applies the fixed
  attribution, lifecycle, nonclaim, and serviceability decision map.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh) resolves live-GPT boot2,
  records but does not back up its predecessor, verifies a full write and
  independent readback, and powers off without rebooting.
- [`scripts/test_runtime_tools.py`](scripts/test_runtime_tools.py) exercises the
  accepted runtime outcome and seven decision-changing mutations offline.
- [`DESIGN.md`](DESIGN.md) defines the observation and decision contract.

## Procedure

1. Run the static validator locally.
2. Commit and push the exact experiment and Buildbox tooling with a clean
   worktree.
3. Run `./scripts/buildbox build-gemian-provenance-observer`.
4. Require a complete `Image.gz-dtb`, `vmlinux`, and `System.map`, zero
   unresolved symbols, exact observer symbols/strings, and a validated package
   whose provenance says `boot_candidate=false`.
5. Fetch only that validated package with
   `./scripts/buildbox fetch-gemian-provenance-observer`.
6. Review the package and boot-container boundary separately before deciding
   whether a device boot is justified.
7. Require two independent candidate roots, exact file equality, independent
   structural validation, and negative mutation rejection before admitting the
   container to runtime-tool review.
8. Freeze the pre-boot hypothesis and decision map; require the collector,
   classifier, and guarded installer to pass syntax, ShellCheck, offline
   positive/negative classification, and static safety review before deployment.

## Observations

The normal `git format-patch` was generated from the exact pinned vendor parent
in a disposable Buildbox worktree. A pre-build lifecycle audit rejected the
first draft: it initialized the PPM epoch before a real commit and used a mutex
from an interrupt path. The regenerated patch starts with epoch and handle
zero, completes the PPM epoch only after every reported cluster table is
present, publishes a calibration handle only after the exact five non-SOC EEM
INIT02 banks (`0x3b`) have completed, and uses an IRQ-safe spinlock. No build or
device observation was recorded in that source-generation phase.

The first exact pushed Buildbox job at `b6e088b` passed static validation,
normal `git am`, generated-commit identity, and changed-path validation. It
then stopped before kernel compilation because the exact config oracle expected
the newly introduced symbol to be absent, while `olddefconfig` correctly
materialized its default-off state as `n`. The bounded follow-up reproduced
only two actual deltas: observer `n -> y` and the local-version string. The
oracle now pins that exact result; it was not relaxed. No package or device
action occurred. See the
[`b6e088b` config-gate receipt](results/buildbox-config-gate-b6e088b-20260815.txt).

The next exact job at `27f3d74` passed that configuration gate, then stopped
before kernel compilation in DCT generation. The full vendor revision differs
from the earlier fixed source: `gemini_modular_defconfig` selects
`k97v1_64_bsp`, and its tracked DCT generator is Python 3-compatible. A bounded
disposable Buildbox reproduction pinned the exact DCT tool, tracked DWS,
Python binary, project output path, and normalized `cust.dtsi` checksum. The
lane now enforces that complete full-vendor DCT contract. No package or device
action occurred. See the
[`27f3d74` DCT-gate receipt](results/buildbox-dct-gate-27f3d74-20260815.txt).

The exact `3556a9b` Buildbox job passed normal patch application, the two-symbol
configuration oracle, the pinned full-vendor DCT contract, the complete
`Image.gz-dtb`/`vmlinux` link, package checksums, linked-symbol and marker
checks, and zero-unresolved-symbol closure. Its only summarized diagnostic was
the vendor tree's six section mismatches. A disposable same-source diagnostic
link with detailed section checking attributed all six to existing battery
meter/OF and USB-host references and found no observer mention. The diagnostic
output directory was removed after the result was recorded. The validated
package remains compile-review-only with `boot_candidate=false`; no container,
device access, or device write occurred. See the
[`3556a9b` full-link receipt](results/buildbox-full-link-3556a9b-20260815.txt).

Two independent offline builder roots each performed two Android-v0 assemblies
and two different 16 MiB padding constructions. Every resulting file is
byte-identical. Both roots pass the independent structural validator, and each
run rejects five negative mutations. The generic LK analyzer passes all gates
except three mainline-specific address/relocatability expectations; the exact
same three differences are present in the retained, known-good Gemian boot
image. The experiment-specific validator therefore pins the inherited vendor
address, flags, aligned placement, header, ramdisk, and LK structure rather
than weakening them. No device was accessed. See the
[`e354ee4b` offline-container review](results/offline-container-review-20260815.txt).

The fixed runtime path now streams one read-only probe directly to the existing
USB/netcat shell, requires the exact kernel release and candidate identity, and
reads the observer twice two seconds apart. The classifier distinguishes a
complete stable lifecycle publication from unavailable, incomplete, unstable,
misattributed, faulted, ownership-claiming, or serviceability-regressing
outcomes. The guarded installer dynamically records the predecessor rather than
requiring a stale checksum, creates no fresh partition backup, and preserves the
project's live-GPT, inactive-root, stable-power, full-readback, and clean-shutdown
gates. A read-only Gemian preflight found the expected `3.18.41+` OS, root
`/dev/mmcblk0p29`, unique inactive 16 MiB boot2, healthy 69% battery with AC
online, and passwordless sudo. It did not read or write boot2. See the
[`2026-08-15` predeployment hypothesis](results/predeployment-hypothesis-20260815.txt),
[`runtime decision map`](results/runtime-decision-map-20260815.txt), and
[`runtime-tool review`](results/runtime-tool-review-20260815.txt).

## Analysis

This observer intentionally does not port the Linux 7.1 experimental
coordinator into Linux 3.18. Such a port would create a large vendor-only owner
implementation without advancing the upstream kernel. Instead, this candidate
tests whether the real vendor EEM/PPM lifecycle can provide the missing runtime
provenance evidence. Its zero owner fields preserve the unresolved production
gate rather than hiding it.

## Conclusion

The compile/link, offline container, and runtime-tool gates pass. This
establishes source integration, exact configuration scope, DCT reproducibility,
linked observer presence, symbol closure, one reproducible LK-compatible
container, and a fixed deployment/measurement contract. It does not establish
runtime lifecycle publication or hardware support. The next ordered action is
one guarded boot2 deployment followed by one read-only runtime observation.

## Follow-up

Install the exact accepted candidate to live-GPT-resolved inactive boot2,
require a matching full-partition readback and clean shutdown, arm the direct
USB/netcat collector, and physically select boot2 once. Runtime success requires
two stable reads with
`observation_complete=1`, all reported PPM cluster bits present, EEM bank masks
equal to `0x0000003b`, and nonzero variant, table epoch, and calibration handle,
while owner/transition handles remain zero. That would confirm table and
calibration publication—not asynchronous voltage-setter completion. The
upstream path would still require one coherent transition owner for the
DVFSP/I2C6/DA921x operation and rollback boundary before CPU8/CPU9 admission.
