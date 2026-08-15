# Experiment: MT6797 runtime provenance observer

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-14-mt6797-runtime-provenance-observer` |
| Status | `pre-init recovery patch generated and validated; Buildbox compile next` |
| Subsystem | MT6797 EEM/PPM DVFSP provenance |
| Device variant | Planet Gemini PDA, MT6797; corrected boot2 installed |
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
- Boot path: attempt 1 installed and read back exactly but used the stock
  ramdisk, so its USB/netcat expectation was invalid. A kernel/DT/config-
  identical derivative with a vendor-RNDIS observation ramdisk passed
  independent offline review and deployment, but its selected cycle exposed
  neither USB transport nor retained candidate evidence.

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
The later guarded deployment wrote only inactive boot2 and then shut the device
down. Attempt 1 was manually recovered after a stuck splash and never exposed
the expected runtime interface. The corrected derivative changes only the
RAM-resident observation path. It temporarily remounts sysfs read-write only to
configure the live-verified legacy Android RNDIS gadget, restores sysfs
read-only, performs no storage or DVFSP write, and requests no reboot.

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
- [`initramfs/`](initramfs/) contains the minimal early observer recorder and
  legacy Android RNDIS transport for the corrected derivative.
- [`scripts/build-diagnostic-initramfs.py`](scripts/build-diagnostic-initramfs.py)
  makes the exact three-member delta from validated Candidate AC.
- [`scripts/assemble-diagnostic.py`](scripts/assemble-diagnostic.py) preserves
  the attempt-1 kernel, DTB, vendor address contract, and header strings while
  replacing only the ramdisk field and canonical image ID.
- [`scripts/build-diagnostic-candidate.sh`](scripts/build-diagnostic-candidate.sh)
  performs two initramfs/container assemblies and independent padding paths.
- [`scripts/test_diagnostic_candidate.py`](scripts/test_diagnostic_candidate.py)
  independently pins the delta and rejects five container mutations.
- [`scripts/preinit_source_edits.py`](scripts/preinit_source_edits.py) applies
  the deterministic isolated recovery companion to the exact observer parent.
- [`scripts/validate_preinit_source.py`](scripts/validate_preinit_source.py) and
  [`scripts/test_preinit_source_tools.py`](scripts/test_preinit_source_tools.py)
  enforce the default-off, late-init-sync, bounded-reset, no-storage, no-DVFSP,
  and closed-CPU contract and reject decision-changing mutations.
- [`scripts/generate-preinit-on-buildbox`](scripts/generate-preinit-on-buildbox)
  creates a normal `git format-patch` review from the exact vendor parent in a
  disposable Buildbox clone; it does not compile a kernel or access a device.
- [`scripts/validate_preinit_patch.py`](scripts/validate_preinit_patch.py) and
  [`scripts/test_preinit_patch_validator.py`](scripts/test_preinit_patch_validator.py)
  pin the generated commit, patch, isolated series, exact three-path delta, and
  recovery semantics and reject thirteen patch mutations.
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

The guarded deployment then resolved the unique inactive, unmounted 16 MiB
boot2 as `/dev/mmcblk0p30`, recorded predecessor `5b38e542586c...`, wrote the
exact `b17400c59f0a...` candidate, and passed both the post-flush full-partition
checksum and an independent byte comparison. It created no fresh partition
backup and removed the temporary readback. The device then shut down cleanly,
became unreachable, and was not rebooted. The direct USB/netcat collector is
armed for one physical boot2 selection. See the
[`2026-08-15` deployment receipt](results/deployment-20260815.txt).

On the one physical attempt-1 selection, the display reached the Gemian splash
and remained stuck. No matching USB interface, netcat shell, or SSH service
appeared. The owner manually returned to ordinary Gemian; its boot reason was
`power_key`, pstore was empty, `/proc/last_kmsg` contained only the generic
74-byte ram-console header, CPU8/CPU9 were offline, and inactive boot2 still
matched the exact deployed candidate. Offline inspection then proved that the
attempt-1 ramdisk was stock Gemian: it contains no `usb-shell`, `usb-net`, or
project USB marker. The runtime transport expectation was therefore impossible
for that container, independent of the still-unlocalized splash hang. Do not
repeat attempt 1. See the
[`attempt-1 service-failure record`](results/runtime-attempt-1-service-failure-20260815.txt).

The corrected derivative uses the exact validated Candidate AC initramfs as a
base, changes only `init` and `bin/usb-net`, and adds one early read-only
provenance recorder. The RNDIS helper follows the legacy Android gadget contract
observed on known-good Gemian, restores sysfs read-only before exposing the
shell, and records both an early snapshot and a fresh live snapshot path. Two
independent build roots are byte-identical. The full boot2 SHA-256 is
`ea603c1b1a64...`; the kernel, appended DTB, and configuration bytes are exactly
the attempt-1 bytes. Both independent validators pass and five mutations are
rejected. The generic LK analyzer retains only the same three inherited vendor
address/relocatability differences already accepted for attempt 1. See the
[`corrected observation-path review`](results/diagnostic-observation-path-review-20260815.txt)
and [`predeployment hypothesis`](results/predeployment-hypothesis-rndis-20260815.txt).

The second guarded deployment resolved the same inactive live-GPT boot2,
recorded the exact attempt-1 image as predecessor, wrote corrected full image
`ea603c1b1a64...`, and passed post-flush and independent byte readback. No fresh
backup was created. The device shut down cleanly without a reboot request, and
the corrected direct RNDIS/netcat collector was armed. See the
[`corrected deployment receipt`](results/deployment-rndis-20260815.txt).

On the one corrected selection, the owner observed the boot screen without the
stock Gemian splash and no automatic reboot. The exact RNDIS collector expired
after 900 seconds, and the host's post-deadline USB inventory contained no
Gemini device. The owner then returned to ordinary Gemian with the power key.
Recovery found configured but empty pstore, the same generic 74-byte last-kmsg
header as attempt 1, CPUs 8/9 offline, and inactive boot2 still matching exact
corrected checksum `ea603c1b1a64...`. Because the diagnostic ramdisk does not
launch the stock splash, its absence is not itself evidence of an earlier
kernel stop. No retained marker distinguishes kernel entry, initramfs entry, or
failure before Android USB service. Do not repeat the exact corrected artifact.
See the
[`corrected attempt-2 record`](results/runtime-attempt-2-pre-transport-20260815.txt).

The follow-up offline audit confirms that the exact linked vendor kernel
registers its ramoops console and MT6797 restart handler before the observer's
late initcall. It also rejects an initramfs-only watchdog design: the generic
watchdog core is absent and the vendor late-init kicker remains an independent
kernel owner. The selected successor is therefore a separate default-off
kernel companion. A late-init-sync checkpoint will run after the existing
observer and kicker, emit one pre-`/init` marker into the already registered
pstore console, and schedule one 120-second `emergency_restart()` worker through
the existing MT6797 reset handler. The corrected initramfs and DTB remain exact;
RNDIS becomes the fast live path rather than the only evidence path. See the
[`pre-init recovery boundary audit`](results/preinit-recovery-boundary-audit-20260815.txt).

The deterministic source editor and validator now pass one positive fixture,
reject a second application, and reject all thirteen default-on, dependency,
gating, deadline, marker, scheduling, restart, initcall, cancellation,
watchdog-ownership, storage, and CPU mutations. Bash syntax, Python compilation,
ShellCheck warning-or-higher, and whitespace checks pass. This is tooling only:
no vendor patch, kernel build, container, or device action exists yet. See the
[`pre-init source-tool review`](results/preinit-source-tool-review-20260815.txt).

The exact pushed tooling commit `fdd511e` then ran on Buildbox. A disposable
clone reproduced historical observer parent `f3d2a14...`, generated one normal
format patch with child commit `2dbf7be...`, and changed only Kconfig, the
MT6797 Makefile, and the new companion source. An independent clean clone
reapplied both patches, reproduced the child commit, passed the source
validator, and remained clean. The fetched checksummed patch is byte-identical
to the repository copy; the patch validator passes and rejects thirteen
mutations. No kernel build or device action occurred. See the
[`Buildbox patch-generation receipt`](results/preinit-patch-generation-buildbox-20260815.txt).

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
runtime lifecycle publication or hardware support. Attempt 1 had an invalid
transport expectation. Corrected attempt 2 had a valid transport design but
never made that transport serviceable and retained no candidate marker. EEM/PPM
runtime publication remains unobserved, and both deployed artifacts are closed
to identical repetition.

## Follow-up

Commit and push the generated patch, isolated series, and validators, then run
the exact child through the Buildbox full-link lane. The build must prove the
exact parent, isolated default-off configuration, initcall order, marker and
delayed-work boundaries, and final link before any container review. Runtime
success would still require two
stable reads with `observation_complete=1`, complete PPM and EEM masks, and
nonzero variant, table epoch, and calibration handle while owner/transition
handles remain zero. That would confirm publication only. The upstream path
still requires one coherent transition owner for the DVFSP/I2C6/DA921x
operation and rollback boundary before CPU8/CPU9 admission.
