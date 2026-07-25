# Experiment: exercise the fail-closed CPU8 boot gate

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-22-a72-reject-cpu8-request` |
| Status | `PARTIAL: runtime, native reboot, Gemian return, and post-return boot2 integrity passed; explicit readable-console confirmation pending; accepted as AK's safety predecessor` |
| Subsystem | ARM64 SMP and MT6797 CPU operations |
| Device variant | Current named Gemini PDA unit |
| Date(s) | 2026-07-22 |
| Candidate | `AJ` |

## Question or hypothesis

Does exact Candidate AI continue booting on its eight proven Cortex-A53 CPUs
when Linux makes one boot-time request for logical CPU8 and corrected patch
0092 rejects that request before generic PSCI `CPU_ON`?

Candidate AJ is a configuration-only derivative of exact Candidate AI. It
selects the same 89-entry `patches/series-a72-reject-gate`, keeps the same DT,
initramfs, console, keyboard, USB, pstore, and native-restart contracts, and
changes only the forced kernel command line from `maxcpus=8` to `maxcpus=9`.
It does not enable either Cortex-A72. A successful result establishes only that
the fail-closed rejection path executes and the eight-A53 baseline survives.

## Pinned static boundary

- Linux source SHA-256:
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`.
- Candidate AI series SHA-256:
  `b172d419cc1e331932e734dda57be076872a442719dd6d406b217d81547dfd00`.
- Candidate AI patchset SHA-256:
  `ba2cd5a66bd1fcff6552674d6d875d363e4ef0a24cfd10ede4f304136f0dc0dd`.
- Corrected patch 0092 SHA-256:
  `cbd54d048e2233ffcb268174037248ade9ab8716f9816481d926b20b4bd3bba5`.
- New fragment SHA-256:
  `fbbc03dec4021f2e23e51e2aaad5f7bc8942d011470db90552a10d4467631ba3`.
- Configuration-input SHA-256:
  `9fa44c817649a81a633b0c2443e2d7bf73008af613431577b1cddc525121f409`.
- Resolved configuration SHA-256:
  `64f1c3d1b9a506aad5b0ee0549188abac2fbcff12e9e8aacbda015cf4ee7b8cb`.

`CONFIG_IKCONFIG=y` embeds a compressed copy of the resolved configuration in
the kernel. Consequently, changing `CONFIG_CMDLINE` does not make Candidate AJ
`Image` a fixed two-byte transform of Candidate AI `Image`; the earlier
predicted `Image`, `Image.gz`, `System.map`, and compiled-audit identities are
invalid and are not accepted as evidence.

Two independent VM builds agreed byte-for-byte on every substantive package
member and mode. Their timestamp-bearing manifests remain deliberately
distinct, and both exact manifest hashes are accepted. The reproduced
`Image`, `Image.gz`, `System.map`, packaged Gemini DTB, compiled-gate audit,
and both package-manifest identities are pinned in `scripts/candidate_aj.py`.

The artifact contract source-pins Candidate AI's final-DT and initramfs inputs
byte-for-byte. Two independently assembled AJ artifacts and two independent
zero-padding constructions agreed, so the raw Android-v0, complete artifact
manifest, and padded `boot2` identities are now pinned as well.

## Why `maxcpus=9` requests CPU8 only

In the exact Linux 7.1.3 source and resolved configuration,
`CONFIG_HOTPLUG_PARALLEL` is absent. Serialized `cpuhp_bringup_mask()` walks
the present mask in ascending logical-CPU order and decrements its limit after
every visited CPU, including a failed visit. CPU0 is the first visit, so a
limit of nine visits reaches CPU8 and stops before CPU9 even when CPU8 returns
`-EAGAIN`. The expected messages are exactly:

```text
mt6797-psci: CPU8 boot rejected: A72 power sequence inactive
CPU8: failed to boot: -11
smp: Brought up 1 node, 8 CPUs
```

The exact `-11` line is an expected negative result, not a general permission
to ignore CPU failures. Every other CPU failure, a CPU9 request, or an A72
secondary-boot line remains fatal to the experiment oracle.

## Safety boundary

- No patch 0088, 0089, 0090, 0091, or 0093 is selected.
- The gate performs logging and returns `-EAGAIN` before `PSCI_CPU_ON`.
- No CPU sysfs write, regulator/reset action, DVFS, idle, thermal, OPP,
  energy-model, capacity, or scheduler-policy change is permitted.
- Gemian's HMP/HPS/PPM policy is evidence, not code to copy. A generic
  three-cluster CPU map remains a later experiment after real CPU8/9 online
  support is proven.
- Candidate AJ requires Candidate AI's separately recorded runtime, console,
  native-reboot, recovery-return, and post-cycle boot2-integrity PASS as its
  sole hardware predecessor; AI's expired pre-cycle two-snapshot observer is
  recorded separately, and none of its evidence is inherited as AJ evidence.
- The guarded installer must require exact Candidate AI's full-partition SHA-256
  `8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86`
  as its sole accepted predecessor and retain the guarded logical-`boot2`
  contract.

## Associated code

- `scripts/candidate_aj.py`: shared deterministic identities and separate
  fail-closed package/artifact pin gates.
- `scripts/validate-profile.py`: repository profile, fragment, series, and
  maxcpus-attempt-order validator.
- `scripts/validate-package.py`: exact AI-to-AJ manifest-delta and package
  policy validator. This bootstrap validator deliberately uses semantic and
  lineage checks rather than unknowable AJ binary hashes so it can inspect the
  two fresh builds.
- `scripts/validate-package-reproduction.py`: two-tree package reproduction
  gate; it emits the observed binary identities only after both complete trees
  agree.
- `scripts/validate-package-pins.py`: post-reproduction gate that refuses
  before package I/O unless the selected Image, Image.gz, System.map, packaged
  DTB, audit, and two package-manifest records are all exact.
- `scripts/build-candidate-aj.sh`: deterministic two-pass Android-v0 artifact
  constructor for an already-built and validated AJ package; it performs no
  device access and publishes only to a caller-selected external directory.
- `scripts/validate-boot.py` and `scripts/finalize-artifact.py`: source-pinned
  AI-container contract adaptation and exact 20-member AJ artifact finalizer.
- `scripts/validate-artifact-reproduction.py` and
  `scripts/test-artifact-reproduction.py`: two-tree byte, mode, inventory,
  package-binding, Android-v0, lineage, and mutation gates.
- `scripts/validate-artifact-pins.py` and `scripts/test-artifact-pins.py`:
  production single-tree gate for the exact 20-member artifact, raw member,
  complete manifest, and reported padded identity; it performs no padding or
  device access.
- `scripts/verify-padding-reproduction.sh`: ephemeral sparse-extension and
  zero-allocation/overlay constructions with exact-prefix and all-zero-tail
  checks; both temporary images are removed afterward.
- `scripts/validate-runtime.py`: read-only USB/CPU runtime subgate requiring the
  one exact CPU8 rejection while forbidding CPU9 and every other fault. It is
  not an overall candidate PASS. Its production CLI refuses before capture I/O
  while any required identity is unpinned.
- `scripts/collect-runtime.sh` and `scripts/collect-cycle.sh`: source-pinned,
  one-session 45+5-second USB/CPU capture and one-shot USB-cycle watcher. They
  read no partition, request no CPU transition, and preserve rejected evidence.
- `scripts/derive-installer.py` and `scripts/test-installer-derivation.py`:
  source-pinned AI-to-AJ installer derivation plus inherited AF/AG/AH/AI and
  76 focused AJ mutations. The generated installer requires exact Gemian
  `3.18.41+` on `/dev/mmcblk0p29`, exact installed AI, live-GPT logical
  `boot2`, a private full backup, one bounded write, flush, and full readback;
  it never reboots or selects a slot.
- `scripts/request-native-reboot.sh` and
  `scripts/validate-native-reboot.py`: exact-runtime-boot-ID and inherited
  `/bin/reboot`-hash gate, one absolute reboot dispatch, and two fail-closed USB
  disappearance observations. The evidence validator accepts the exact leading
  PS1/PS2 prompt tokens emitted and coalesced by interactive BusyBox `ash`, but
  does not remove prompt-like text within evidence values.
- `scripts/collect-recovery-evidence.sh` and
  `scripts/validate-recovery-evidence.py`: exact Gemian pre/disconnect/post
  cycle with a strict disconnect-through-reconnect companion window. Missing
  or invalid companions are preserved and published; an exact unique AJ
  pstore triplet is only `ATTRIBUTED_PARTIAL`.
- `scripts/verify-post-cycle-boot2.sh`: separate read-only live-GPT `boot2`
  integrity gate bound to the final recovery boot ID. It is not an installer
  derivative and has no write path.
- `scripts/verify-attempt-2-post-return-boot2.sh`: attempt-2-only closure gate
  which binds the exact runtime and native-reboot captures to the deliberately
  unpaired raw post-return snapshot, verifies its internal manifest, then
  resolves live-GPT `boot2` with Gemian-compatible interfaces and performs one
  full read-only checksum. Its mocked test covers one success and sixteen
  fail-closed cases.
- The `test-*.py` and `test-*.sh` programs cover the static, runtime, installer,
  collector, reboot, recovery, and post-cycle mutation boundaries with mocked
  transport and no device access.

All hardware-facing layers were derived only after the reproduced raw,
artifact-manifest, and padded identities were fixed, avoiding circular
calibration. Their local mutation/mocked suites, shell syntax checks,
recovery-VM ShellCheck, and two independent read-only reviews pass.

## Build procedure

1. Require Candidate AI's complete hardware PASS before beginning AJ hardware
   preparation. Static validation may run earlier.
2. Run `validate-profile.py` against this repository.
3. Build the manifest profile only through `./scripts/dev-vm build-kernel`, in
   two independent source/build/artifact roots.
4. Run the bootstrap package validator on each fresh package against one exact
   accepted Candidate AI package. It must verify the exact resolved config,
   embedded IKCONFIG, insertion-only packaged-manifest delta, gate semantics,
   and allowed inventory without consulting an AJ binary hash. Then require
   the two complete package trees to reproduce. A valid package has 226
   members: exact AI inventory plus the new configuration fragment.
5. Pin every build-derived package identity emitted by that agreement and run
   `validate-package-pins.py` against both reproduced packages.
6. Only after package pins close, build and validate two Android-v0 artifact
   trees from the two packages, preserving the selected AI final DT and
   initramfs byte-for-byte.
7. Only after the raw image and complete artifact manifest reproduce, perform
   two independent ephemeral 16 MiB zero-padding checks and source-pin the
   resulting raw, manifest, and padded identities in every hardware-facing
   layer.
8. Derive and mutation-test a guarded AI-to-AJ installer plus separate USB/CPU
   runtime, recovery, native-reboot, and post-cycle integrity collectors.
9. Install only from exact AI while exact Gemian is active. Start the recovery
   and USB-cycle observers before selecting `boot2`; after exact runtime passes,
   use only the fresh-boot-ID-gated native reboot requester. Finish with the
   separate read-only full-`boot2` integrity check. Visible console remains an
   independent owner observation.

Use absolute, guest-local roots which were verified absent before each build.
The two builds for this experiment use:

```sh
DEV_VM_NAME=gemini-pda-build-recovery-20260717 \
  KERNEL_PROFILE=observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate-cpu8-request \
  BUILD_MODULES=0 KERNEL_JOBS=8 \
  GEMINI_SOURCE_ROOT=/home/julien.guest/src/candidate-aj-kernel-build1-20260722 \
  GEMINI_BUILD_ROOT=/home/julien.guest/build/candidate-aj-kernel-build1-20260722 \
  GEMINI_ARTIFACT_ROOT=/home/julien.guest/artifacts/candidate-aj-kernel-build1-20260722 \
  ./scripts/dev-vm build-kernel

DEV_VM_NAME=gemini-pda-build-recovery-20260717 \
  KERNEL_PROFILE=observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate-cpu8-request \
  BUILD_MODULES=0 KERNEL_JOBS=8 \
  GEMINI_SOURCE_ROOT=/home/julien.guest/src/candidate-aj-kernel-build2-20260722 \
  GEMINI_BUILD_ROOT=/home/julien.guest/build/candidate-aj-kernel-build2-20260722 \
  GEMINI_ARTIFACT_ROOT=/home/julien.guest/artifacts/candidate-aj-kernel-build2-20260722 \
  ./scripts/dev-vm build-kernel
```

Because these overrides are intentionally scoped to `build-kernel`, pass each
result's explicit package path to `validate-kernel`; do not use its default
artifact selection.

## Predeclared result oracle

| Result | Decision |
| --- | --- |
| Exact AJ is observed through its pinned USB endpoint, records one CPU8 gate warning and one `CPU8: failed to boot: -11`, then reaches the 45+5-second sampling baseline with CPU0-7 advancing and CPU8/9 offline | `USB_CPU_RUNTIME_PASS`: the USB/CPU subgate passes; this is not an overall Candidate AJ PASS and establishes no A72 support. |
| The USB/CPU runtime subgate passes, but visible-console, unique recovery, native-reboot/cycle, or post-cycle boot2-integrity evidence is absent | `PARTIAL`: preserve the subgate result and collect each missing independent gate; do not call the candidate PASS. |
| Exact AJ separately demonstrates a readable visible console, attributable recovery evidence, native reboot into the intended next boot, and an unchanged full boot2 checksum after the cycle | Those independent gates may be combined with `USB_CPU_RUNTIME_PASS` for an overall decision; none is inferred by `validate-runtime.py`. |
| Exact AJ boots CPU8/9, requests CPU9, changes masks, faults, stalls, or resets unexpectedly | `FAIL`: reject the candidate and do not proceed toward active A72 sequencing. |
| Exact changed pstore contains the maxcpus=9 command line and both CPU8 rejection lines but no complete USB/CPU runtime | `ATTRIBUTED_PARTIAL`: preserve the decision-changing recovery evidence as its own subgate; do not call it runtime or overall PASS and do not repeat unchanged. |
| No exact AJ runtime boot ID is bound through live USB or a pre/disconnect/post recovery cycle | `INCONCLUSIVE`: do not repeat the identical artifact merely for another screen observation. Generic retained pstore text is not unique attribution. |
| Any series, config, DT, package, artifact, installed, or runtime identity differs | `INVALID`: correct lineage before interpreting hardware behavior. |

## Current observations

Two builds made through `./scripts/dev-vm build-kernel` used verified-absent,
non-overlapping source, build, and artifact roots in the same pinned AArch64
recovery VM. Their 226-member packages have distinct generation timestamps and
manifest hashes, but every substantive byte and mode reproduces. The exact
Image, Image.gz, System.map, packaged DTB, compiled gate audit, and both package
manifest identities are pinned and revalidated against both packages.

One Android-v0 artifact was then assembled from each package. The two exact
20-member trees reproduce byte-for-byte and mode-for-mode, including raw boot
image SHA-256
`a3c649b5ca7a9ac07e290ca9a8838f0a3be33ab9e39554c4bafe50c98d18e2a8`
at 7,380,992 bytes and artifact-manifest SHA-256
`143307167adcfe000e7ffc331217248404c1fa45e133600d5e21043d93186ac7`.
Independent sparse-extension and zero-allocation/overlay constructions both
produced the same exact 16 MiB padded SHA-256
`8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257`;
both raw prefixes and zero tails were verified and the temporary images were
removed. See `results/offline-reproduction-20260722.txt`.

Candidate AI's retained 64 KiB console ramoops had already evicted output
before roughly 1.274 seconds. AJ's early CPU8 rejection may therefore not
survive into post-return pstore. Hardware attribution must bind the validated
AJ runtime boot ID into a pre/disconnect/post recovery collection; inherited
console markers or generic pstore alone remain inconclusive.

The generated guarded installer has SHA-256
`5cd0d3f59a8a95705f11819ff2cf52c69fd14da04476b132e6000faee1b8c764`.
Its 76 AJ mutations and the inherited AF/AG/AH/AI suites pass. The runtime,
cycle, native-reboot, recovery, and post-cycle tools pass their focused
mutation and fully mocked transport tests; final recovery-VM ShellCheck and two
independent read-only reviews found no remaining blocker. See
`results/hardware-layer-preflight-20260722.txt`.

The guarded installer then ran from exact Gemian `3.18.41+` rooted on
`/dev/mmcblk0p29`. It live-resolved logical `boot2` as inactive
`/dev/mmcblk0p30`, preserved exact AI as a private mode-0600 full backup, wrote
one bounded 16 MiB image, synchronized and flushed it, and required a complete
byte-identical readback at exact AJ SHA-256
`8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257`.
The recovery boot ID remained unchanged; the installer did not reboot or
select a slot. See `results/boot2-install-candidate-aj-20260722.txt`.

An attended console was then reported with the inherited `AB` label and eight
`/proc/cpuinfo` entries. That appearance is compatible with AJ's predeclared
CPU8 rejection, but it is not attributable to the unit on which AJ was
installed: the exact `192.168.1.50` recovery target never satisfied the
observer's two-failure disconnect gate and remained in the same Gemian
`3.18.41+` boot on `/dev/mmcblk0p29` with an unchanged boot-ID hash after the
full 1,200-second window. The Mac observed only the vendor `g_android`
`0fce:7169` descriptor lineage, no exact mainline fixed-MAC interface, and no
packet-ready runtime service. A second generic USB watcher was stopped before
collection because the candidate's fixed MAC and serial are not unit-unique.
No runtime collector or reboot command ran, and no device read or write was
performed during the attempt. The exact pre-cycle snapshot was preserved
privately for a separately validated continuation path. See
`results/hardware-attempt-1-identity-mismatch-20260722.txt`.

Attempt 2 reached Candidate AJ through its exact USB endpoint. The private
runtime capture has SHA-256
`7cb5b63ad0ef24838cd63afc30d2af53df3ee7ae442a82453931cbca22929093`
and its boot-ID digest is
`6211c6051f9a53315bc465c8dcf57283128707274a8c5761ac8a04d9c730858c`;
the plaintext boot ID is not published. The runtime subgate passed: CPUs 0--7
were online and all advanced accounting across the 45+5-second window, CPUs 8
and 9 remained offline, the log contained exactly one fail-closed CPU8 gate
rejection and exactly one `CPU8: failed to boot: -11`, CPU9 was not requested,
and no other fault signature appeared. This is positive evidence for the
negative-control path only, not Cortex-A72 support.

The boot-ID-gated native requester then dispatched exact `/bin/reboot` once.
Its private transcript has SHA-256
`62be933afa872bdf25b42bf403bb0e044e9b57ac0325d1ccffbd51ca70bb2e11`;
it records the closed connection and two exact-MAC absence observations with no
partition read or device write. The first validator rejected the real
transcript only because interactive BusyBox `ash` coalesced leading PS1/PS2
prompts with two result lines. The corrected validator, SHA-256
`c9e5f2e0353cf20e61b93116ef214ad1eddb3459526f70378a326d675d6f7bbd`,
normalizes only those exact leading tokens and passes the original evidence
plus thirteen focused rejection mutations. The hardware reboot was not
repeated for this parser correction. See
`results/tooling-correction-attempt-2-20260722.txt`.

Gemian `3.18.41+` then returned on `/dev/mmcblk0p29`; its boot-ID digest changed
from
`c831f4c5d5e28b4b6a8a6d0f22fb258ce2d8385bfb0d5d2c3918d7908ff2a79a`
to
`fc23e897afb61177e976a77265435d467bdc8917a5c7d9f7c6bc132fc04e5b7b`.
The owner independently confirmed the return. The raw post-return snapshot is
deliberately unpaired (`paired_cycle_observer=no`, `wait_for_cycle=no`), so it
does not by itself prove a disconnect/reconnect pair. Its exact internal
manifest, SHA-256
`bc5862e09ff87216d098cc35930a291b9911b348d13327e8d2de098ae116715c`,
verifies, and its console ramoops records the native reboot request, orderly
driver shutdown including the watchdog, and `reboot: Restarting system`. The
64 KiB ring no longer contains the early CPU8 rejection; that exact line is
retained in the validated live runtime capture.

The first post-return verifier transcript was preserved at SHA-256
`a0cc1a5bc47f5a568a6fec8f04638f6bb7d9c3ab42dec50415bc4c3ed024f4e1`.
It stopped before partition resolution or a partition read because Gemian's
`lsblk` lacks the `PATH` column. A narrowly corrected verifier, SHA-256
`d358ac3f499b235c6dbabf3e939229bbcca3582ccf30cd56e672e11f0de03fa7`,
passed seventeen mocked success/failure cases and then produced the successful
private integrity record with SHA-256
`6abe2a264fe70ce8c3df71635f89767f07102160f985a3692dcfc79e3102ea9a`.
That record live-resolves inactive, unmounted logical `boot2`, reads the full
partition exactly once, performs no write, and verifies exact Candidate AJ
SHA-256
`8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257`.
See `results/hardware-attempt-2-runtime-reboot-return-20260722.txt`.

The owner's attempt-2 report was “boot on boot2 successful, device available
on usb eth.” That report establishes the intended selection and USB
availability, but it does not explicitly say whether the local console was
readable. Visible-console confirmation therefore remains the sole pending
independent AJ gate.

A post-test predecessor audit also checked the earlier owner statements. The
explicit “console works” report predates attributable AJ attempt 2, while the
later inherited-`AB` console report belongs to rejected attempt 1. Neither is
silently reassigned to attempt 2, so AJ's visible-console subgate remains
`PENDING` and its overall status remains `PARTIAL`.

That missing observation is not, however, a safety blocker for the narrower
CPU9 rejection control. Exact attempt 2 links AJ's runtime boot ID and expected
pre-PSCI CPU8 rejection to one fresh-boot-ID-gated native reboot, disappearance
of the exact USB endpoint, changed-boot-ID Gemian return confirmed by the
owner, and a full read-only checksum of the still-installed AJ image. This is
not one paired observer, and it is not described as one, but its independent
exact identities provide the decision-relevant unit and recovery attribution.
Because AK may change only `maxcpus=9` to `maxcpus=10` while retaining the
power-inert corrected-0092 gate, console/initramfs, USB service, and native
restart path, AJ is accepted as AK's safety predecessor. AK must still treat
its own visible console as an independent hardware gate and must require exact
AJ SHA-256
`8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257`
as its guarded install predecessor. See
`results/ak-predecessor-gate-adjudication-20260722.txt`.

## Conclusion

The package, artifact, padding, guarded installation, exact USB/CPU runtime,
native reboot, Gemian return, and post-return full-`boot2` integrity gates have
passed for attempt 2. The exact negative control behaved as predicted: one
CPU8 request was rejected before generic PSCI `CPU_ON`, CPU9 was not requested,
and CPUs 0--7 remained stable. Candidate AJ remains `PARTIAL` solely because
the owner has not yet explicitly confirmed a readable local console during
this attributable attempt. The exact compound evidence nevertheless passes the
narrow AK safety-predecessor gate, so the one-token, fail-closed CPU9 control
may be built, packaged, and guard-installed over exact AJ. This is not
Cortex-A72 support and provides no permission to run the draft active-power
sequence.
