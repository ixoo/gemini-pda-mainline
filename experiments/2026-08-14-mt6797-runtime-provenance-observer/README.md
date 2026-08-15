# Experiment: MT6797 runtime provenance observer

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-14-mt6797-runtime-provenance-observer` |
| Status | `full-vendor DCT contract corrected; full-link pending` |
| Subsystem | MT6797 EEM/PPM DVFSP provenance |
| Device variant | Planet Gemini PDA, MT6797; no live-device action yet |
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
- Boot path: none; the first package is compile-review-only and must record
  `boot_candidate=false`

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

The current phase is host/build-only. It performs no device access and creates
no boot container. A successful full link advances only to separate package
and boot-container review.

## Associated code

- [`patches/series`](patches/series) selects the single generated vendor patch.
- [`scripts/validate.py`](scripts/validate.py) enforces patch scope, default-off
  selection, read-only output, and the explicit nonclaims.
- [`scripts/build-on-buildbox`](scripts/build-on-buildbox) reconstructs and
  fully links the exact vendor source on Buildbox.
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

## Observations

The normal `git format-patch` was generated from the exact pinned vendor parent
in a disposable Buildbox worktree. A pre-build lifecycle audit rejected the
first draft: it initialized the PPM epoch before a real commit and used a mutex
from an interrupt path. The regenerated patch starts with epoch and handle
zero, completes the PPM epoch only after every reported cluster table is
present, publishes a calibration handle only after the exact five non-SOC EEM
INIT02 banks (`0x3b`) have completed, and uses an IRQ-safe spinlock. No build or
device observation is recorded yet.

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

## Analysis

This observer intentionally does not port the Linux 7.1 experimental
coordinator into Linux 3.18. Such a port would create a large vendor-only owner
implementation without advancing the upstream kernel. Instead, this candidate
tests whether the real vendor EEM/PPM lifecycle can provide the missing runtime
provenance evidence. Its zero owner fields preserve the unresolved production
gate rather than hiding it.

## Conclusion

Inconclusive pending the complete Buildbox link. Even a successful link remains
compile-only evidence.

## Follow-up

After successful full-link and package review, a separate decision may admit a
read-only boot candidate. Runtime success would require two stable reads with
`observation_complete=1`, all reported PPM cluster bits present, EEM bank masks
equal to `0x0000003b`, and nonzero variant, table epoch, and calibration handle,
while owner/transition handles remain zero. That would confirm table and
calibration publication—not asynchronous voltage-setter completion. The
upstream path would still require one coherent transition owner for the
DVFSP/I2C6/DA921x operation and rollback boundary before CPU8/CPU9 admission.
