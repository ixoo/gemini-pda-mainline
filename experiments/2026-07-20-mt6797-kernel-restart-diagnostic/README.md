# Experiment: MT6797 kernel restart ordering

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-20-mt6797-kernel-restart-diagnostic` |
| Candidate | AB |
| Status | Passed once: AA r1 hardware baseline, build 3/build 4 package reproducibility, exact AB container/installer validation, guarded `boot2` installation, and the attended prompt kernel-restart test passed |
| Subsystem | ARM64 restart notifier ordering and MediaTek MT6797 TOPRGU |
| Device variant | Current Gemini PDA unit; exact retail sub-variant not independently established |
| Date(s) | 2026-07-20 through 2026-07-21 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Did Candidate X's typed `reboot` hang because ARM64 invoked PSCI's priority-129
restart notifier before the MediaTek watchdog-core priority-128 TOPRGU restart
handler?

Patch 0087 makes restart priority per MediaTek SoC data and selects priority
255 only for MT6797. All other supported MediaTek variants retain the existing
priority 128 fallback. The falsifiable hardware hypothesis is:

> When an ordinary `reboot(2)` request reaches `machine_restart()`, the
> MT6797 TOPRGU software-reset callback at priority 255 will run before PSCI at
> priority 129 and reset this Gemini promptly, without opening a userspace
> watchdog or waiting for its timeout.

Before the hardware test, this hypothesis did not assume that mainline's
current TOPRGU software-reset sequence was sufficient. If the higher-priority
callback had run but failed to assert reset, it would have looped forever and
produced the same visible hang, selecting a separate experiment comparing the
complete working 3.18 TOPRGU sequence.

Priority 255 is SoC-wide policy for every MT6797 board and outranks every
restart handler, not only PSCI. That matches the working downstream
architecture in which MT6797 restarts through TOPRGU, but is an explicit
upstream-review tradeoff. Priority 130 would be the narrower alternative if
reviewers require only that TOPRGU outrank PSCI's priority 129.

## Provenance and environment

- Kernel source: Linux 7.1.3, source SHA-256
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`.
- Previous X/Z patchset SHA-256:
  `4cd417adb0d79aad2f021e1f07e47bed4825cb51b3a069e5258ea4eb49ca5ef4`.
- Candidate AB patchset SHA-256:
  `efb79d0ced5ebee485e337f224075faaa4abf7eb7d5e6a38326383274cd75f93`.
- New patch: `patches/v7.1.3/0087-watchdog-mtk-prioritize-MT6797-TOPRGU-restart.patch`,
  SHA-256
  `81168e4cc12d9ffad7645f667c0211d8dff73b0dadda3ebd422f63378e411d56`.
- Build profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot`.
- Resolved configuration SHA-256 remains exact X/Z:
  `0a0e4ef39d5d89d0d54f55be44da753c93779d88bb94b35623679d1b08b66e74`.
- Selected reproducible package name:
  `linux-7.1.3-gemini-observability-fbcon-rotation-keyboard-wrrd-manual-reboot-efb79d0c-c811a159`.
- Selected build 3/build 4 `Image.gz` SHA-256:
  `37ba538e76e329f3e57cfa78b481151e2d1e5eabcc321a29c7b54d476b6ec26f`.
- Selected build 3/build 4 raw `Image` SHA-256:
  `0ccb5490bc97e288210637b04ede52cf01b0105e1d4d3ee88e7ad21608ecf004`.
- Previous X/Z `Image.gz` SHA-256:
  `d69b2cdc0a2dca05919e5e0dc25c54920a509af89eb1a7f16336e82d368fda41`.
- The first package's ordinary board DTB remains byte-identical to the prior
  package at SHA-256
  `f9be46ffed6cf598f7892d88d8702ff6a4ede074c5b477734ae11bcb4c093db5`.
- The validated boot container retains the proven final keyboard/watchdog/
  framebuffer DTB SHA-256
  `bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f`.
- Build host: repository-managed AArch64 recovery development VM, GCC 13.3.0
  and GNU binutils 2.42.
- Post-fix `scripts/kernel` SHA-256:
  `75995c6cde44cefb50950097bff26c62f26df01ca0f487e2a3bcfc8fcf159634`.

The first kernel was built through `./scripts/dev-vm build-kernel` with the
named profile and passed `./scripts/dev-vm validate-kernel`. A clean build 2
then differed because the kernel automatically advanced its local build number
from `#1` to `#2`: `Image`/`Image.gz` and the embedded build ID changed while
`System.map` remained exact. `scripts/kernel` now pins
`KBUILD_BUILD_VERSION=1`. Post-fix builds 3 and 4 both passed package
validation. Their 221 non-dynamic files and modes are exact; after removing
only `generated_utc`, `provenance/build.json` is exact, and each
`SHA256SUMS` differs only in that timestamp-bearing file's entry. This closes
the package reproducibility gate. Build 1 versus build 3 remains only
regression evidence because build 1 used the older script. None of these
packages is itself a boot candidate. The validated container assembled from
the post-fix package pair is
`candidate-AB-mt6797-kernel-restart-final-61c74592`, with raw boot-image
SHA-256
`61c74592267466735164c19f8b831ea18db2892de95e32109f2aacd7ec5c5446`.

## Safety assessment

Building and validating the kernel package is hardware-inert. Candidate AA r1
has now supplied the attended console-map result: its keyboard map and typed
watchdog reboot path worked on the named device. F1-F10 and Page Up/Page Down
were not explicitly testable in that console session; they remain unconfirmed,
not failed. Candidate AB derives from the exact hardware-passed artifact
`candidate-AA-keyboard-console-map-final-37e82bf3` and retains its known-good
full console map,
display, font, CPU0-only, storage-exclusion, networking-exclusion, and ramoops
basis. It contains no automatic or background userspace watchdog owner.
Only an owner-typed bare `reboot` may request the ordinary kernel restart.

Installation remains limited to the live-GPT-resolved logical `boot2` under
the repository standing authorization. The installer must reject active root,
mount, swap, holder, identity, size, writable, power, boot-ID, or predecessor
checksum mismatches; preserve a private full backup; write only the exact
inactive target; flush; and require a matching full readback. It must not
reboot or select a slot. Primary `boot`, `boot3`, preloader, NVRAM, GPT, and
whole-device writes remain prohibited.

Because failure may leave the diagnostic kernel stopped in its restart loop,
the attended test requires the known power-key recovery path. The experiment
does not mount writable storage, so its forced no-sync diagnostic request does
not risk a mounted root filesystem.

## Associated code

- `patches/v7.1.3/0087-watchdog-mtk-prioritize-MT6797-TOPRGU-restart.patch`
  adds the isolated per-SoC priority selection.
- `patches/series` orders patch 0087 after the previously tested keyboard and
  MT6797 I2C changes.
- `scripts/dev-vm` and `scripts/kernel` provide the required managed build and
  package validation path.
- [kernel-build1-validation-20260720.txt](results/kernel-build1-validation-20260720.txt)
  records the first package's exact identities and validation boundary.
- [kernel-reproducibility-ab-20260721.txt](results/kernel-reproducibility-ab-20260721.txt)
  records the completed post-fix build 3/build 4 package gate.
- `initramfs/` contains only the four audited AB substitutions over the exact
  AA r1 archive: AB attribution in `init`, `local-shell`, and `x-record`, plus
  a no-sync forced BusyBox reboot wrapper that does not touch a watchdog.
- `scripts/build-candidate-ab.sh` performs two initramfs constructions, two
  Android boot-v0 serializations, LK compatibility analysis, exact package and
  AA-baseline validation, dynamic dispatch execution, input-tree hashing, and
  final artifact validation before publishing an output directory.
- `scripts/test-validator-mutations.py` requires focused corruptions of the
  container, initramfs semantics, boot layout, package, and repository
  provenance to fail closed.
- `scripts/materialize-aa-r1-installer.py`, `scripts/derive-installer.py`,
  `scripts/derive-installer-wrapper.py`,
  `scripts/install-candidate-ab-boot2.sh.in`,
  `scripts/calibrate-installer.py`, and `scripts/test-installer-static.py`
  reconstruct the hash-pinned X-to-AA-r1 installer lineage, validate the final
  artifact, derive its exact padded identity, preserve AA r1 as the required
  predecessor, then produce/test an outer wrapper that pins the derived inner
  installer, exports an explicit canonical repository root, and invokes the
  guarded logical-`boot2` installer without device contact during calibration.
- [boot2-write-candidate-ab-20260721.txt](results/boot2-write-candidate-ab-20260721.txt)
  records the exact guarded installation, private backup, full readback, and
  no-reboot boundary.
- [runtime-candidate-ab-attempt-1-20260721.txt](results/runtime-candidate-ab-attempt-1-20260721.txt)
  records the attended idle/reboot result, exact retained attribution and
  timing, changed boot ID, post-return boot reason, and the limits of this
  one-device result.

The construction and guarded-installer pipelines passed their exact validation
gates. The exact resulting AB artifact was then selected manually and passed
the attended runtime gate once: the owner observed no automatic reboot during
at least 45 seconds of idle, typed bare `reboot`, observed the reset trigger
immediately with no countdown, and returned to Gemian with a changed boot ID.

## Procedure

Completed package work:

1. Apply the complete ordered Linux 7.1.3 series through patch 0087 in the
   managed VM.
2. Resolve the exact X/Z configuration profile and require its unchanged
   whole-file SHA-256.
3. Compile `Image`, `Image.gz`, and all DTBs; package provenance and checksums.
4. Run the generic kernel-artifact validator, including every packaged patch,
   DTB, configuration input, image, map, and provenance file.
5. Preserve build 1 and build 2. Record build 2's `#2`-only reproducibility
   failure, pin `KBUILD_BUILD_VERSION=1`, and complete builds 3 and 4.
6. Validate both post-fix packages and require every non-timestamp byte and
   mode to match, with `generated_utc` normalized separately.

Completed container and installation work:

1. Construct one AB container with the new `Image.gz`, exact proven final DTB,
   and the exact hardware-passed AA r1 initramfs. Preserve its full keymap and
   dispatch oracle, but replace the inherited typed-watchdog `/bin/reboot`
   body with the statically audited generic `reboot -n -f` syscall wrapper and
   AB attribution. It must have no watchdog open, ping, countdown, or fallback.
2. Build and validate the complete container from each reproducible package,
   require byte-identical outputs, reject focused mutations, and validate the
   calibrated installer without device contact.
3. Resolve inactive logical `boot2` from the live GPT, require the exact
   hardware-passed AA r1 predecessor, preserve a private full backup, write AB
   once, flush, and require an exact full-partition readback. Do not reboot or
   select a slot.

Completed attended hardware work:

1. The owner manually selected `boot2`, obtained the exact AB marker and prompt
   with a working keyboard, and waited at least 45 seconds without an automatic
   reset before typing bare `reboot` once.
2. The owner observed the reset trigger immediately after command execution,
   with no countdown, and the device returned to Gemian with a changed boot ID.
   This is an attended prompt-reset observation, not an instrumented
   Enter-to-LK-splash measurement.
3. Ramoops was recovered read-only after return. It attributes the request to
   exact AB with no userspace watchdog and records `reboot: Restarting system`
   27.854 ms after the request marker. The watchdog-class platform boot reason
   was recorded but not used alone to distinguish TOPRGU software reset from
   timeout, because both paths reset through the watchdog block on this SoC.

## Observations

Candidate X previously booted and accepted keyboard input, but the owner's
typed `reboot` appeared to hang until power-key recovery. Its retained evidence
did not establish runtime wrapper entry, BusyBox applet entry, or syscall
entry. Separate static execution shows that the exact wrapper and BusyBox
applet issue the ordinary reboot syscall if reached; it does not move X's
observed failure boundary past dispatch. ARM64 registers PSCI reset at priority
129, one step ahead of the previous MediaTek watchdog-core priority 128.

Candidate Z later proved that the same TOPRGU block can reset this unit through
hardware watchdog expiry: the owner typed the command, Gemian returned, the
boot ID changed, and the boot reason was `wdt_by_pass_pwk`. That proves the
block and timeout reset path, not its software-reset register sequence.

Candidate AA r1 then supplied the hardware-passed baseline for AB. The exact
console-map gate loaded and verified the intended map, retained A/S key-event
evidence, and the owner reported that the new map worked and was otherwise
totally fine. Its typed watchdog reboot also worked. The session did not offer
a way to confirm F1-F10 or Page Up/Page Down, so those keys are unconfirmed,
not failed.

Patch 0087 applied and compiled reproducibly in post-fix builds 3 and 4.
Generic artifact validation, packaged checksums, complete non-dynamic package
comparison, timestamp-normalized provenance comparison, and VM-export
round-trip validation passed. The resolved configuration and ordinary package
DTB remain exact; `Image.gz` changed as expected.

The two exact AB container constructions passed package, AA-baseline,
initramfs, dispatch, Android boot-v0, LK, input-tree, final-artifact, and
focused mutation validation. They reproduced the same 7,378,944-byte image at
SHA-256
`61c74592267466735164c19f8b831ea18db2892de95e32109f2aacd7ec5c5446`.
The container retains the AA r1 keymap at SHA-256
`02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c`
and final DTB at SHA-256
`bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f`;
only `init`, `bin/local-shell`, `bin/reboot`, and `bin/x-record` differ from
the exact AA r1 initramfs. Exact installer derivation and static validation
also passed, including the AA r1 predecessor pin and absence of any automatic
reboot.

The guarded installer resolved `boot2` as `/dev/mmcblk0p30` while active root
was `/dev/mmcblk0p29`, confirmed exact AA r1 padded SHA-256
`38b49c7c19c2d97fa0c48436545219489221aa367aedf491ae6ebd4ec4856703`,
preserved it in a mode-0700 private backup, and wrote the 16,777,216-byte AB
image once. Sync, block flush, remote checksum, and complete local readback all
passed at SHA-256
`b58c0347d34a3fd9031c74cb03447dd7a6fc630d5b8ea2b7eabc36827e754350`.
The installer did not reboot or select a slot.

The owner then selected exact Candidate AB and reported that all tested
behavior worked, including the keyboard. The device remained up for at least
45 seconds before the command, with no automatic reset. Bare `reboot` triggered
the reset immediately after execution, without a countdown, and Gemian
returned. F1-F10 and Page Up/Page Down still lacked a visible test opportunity;
they remain unconfirmed, not failed.

Retained console-ramoops supplies exact AB attribution. Its entry marker is at
2.193904 seconds; the services record at 2.221192 seconds states
`watchdog_userspace=none`; and the complete keymap gate and `GEMINI-AB#` prompt
are retained at 2.420465 seconds. Input capture completed at 17.519871 seconds,
the exact bare-reboot wrapper recorded its request at 66.021584 seconds, and
the kernel recorded `reboot: Restarting system` at 66.049438 seconds. Thus the
request marker precedes the final retained kernel restart line by 27.854 ms,
while the quiet interval after input capture is 48.501713 seconds. The former
is internal retained-log timing, not an instrumented Enter-to-LK-splash
measurement; the owner separately observed the actual reset as immediate.

Gemian returned as kernel 3.18.41+ with boot ID
`e33a0d8e-0354-4c8c-95b3-07c6970152ec`, changed from
`0f8def4f-3f94-4c57-a34c-2bb37315b19f`. Its numeric boot reason was 4,
`androidboot.bootreason` was `wdt_by_pass_pwk`, and
`powerup_reason` was `reboot`. That reason class is nondiscriminating because
both direct TOPRGU SWRST and watchdog expiry use the watchdog block. Exact
command ownership, the absence of a userspace watchdog/countdown, prompt
timing, and the selected notifier ordering establish the intended prompt
kernel TOPRGU software-reset result for this attempt.

## Analysis

The priority change tests the earliest concrete divergence from the working
3.18 restart architecture: that kernel excludes PSCI restart on MT6797 and
reaches TOPRGU directly. Selecting priority 255 is narrower than changing PSCI
CPU-management support or copying the downstream reset sequence. It preserves
all non-MT6797 behavior.

The result branches are decision-changing:

| Result | Interpretation | Next action |
| --- | --- | --- |
| No exact AB attribution or a pre-reboot keyboard/display regression | The restart observation is not valid for the intended artifact | Reject the attempt and audit the assembled inputs; do not infer restart behavior |
| Reset occurs automatically before the typed command | Userspace/watchdog isolation failed | Reject AB; locate the owner before any kernel conclusion |
| After at least 45 seconds of stable idle, an actual reset-cycle signal occurs within 5 seconds of typed bare `reboot`, with no countdown, and Gemian returns with a changed boot ID | Priority-first TOPRGU software reset passed once | Preserve patch 0087 and the separately passed AA r1 map in a later candidate |
| The typed request is attributable but the console hangs | Reaching TOPRGU before PSCI was insufficient | Keep the priority result separate; compare mainline's mode/SWRST sequence with working 3.18, including enable/dual/external-reset/PMIC preparation |
| The command returns to the shell with a syscall failure | Failure is before machine restart | Retain the shell and inspect the exact status; do not change TOPRGU sequencing |
| Gemian reports `wdt_by_pass_pwk`, but reset was prompt and there was no pre-command reset or countdown | Boot-reason class is consistent with either direct TOPRGU SWRST or watchdog expiry; timing and ownership carry the attribution | Record the reason without rejecting the prompt software-reset result |
| An actual reset-cycle signal occurs roughly 25–40 seconds after Enter | The timeout path, rather than immediate restart, still owns the observable reset | Audit the assembled initramfs and kernel restart path; do not credit immediate software reset |
| An actual reset-cycle signal occurs between the prompt and timeout bands | Timing alone does not distinguish SWRST from residual watchdog expiry | Preserve the evidence and add an independent observation path before changing the driver |

The attended attempt matched the predeclared prompt-reset branch. Exact AB ran
without an automatic watchdog owner for more than 45 seconds, owned the typed
request, reached the ordinary kernel restart line 27.854 ms after its retained
request marker, and then reset immediately by owner observation. The changed
boot ID and return to Gemian close the reset-cycle gate. The watchdog-class boot
reason is consistent with this result but does not distinguish it from timeout
by itself.

This result supports the notifier-order hypothesis and patch 0087 locally on
the named Gemini once. It does not independently prove every register write,
repeatability, or broad MT6797 reboot reliability.

## Conclusion

`kernel-package-reproducible`: PASS. Patch 0087 is implemented and post-fix
builds 3 and 4 passed exact package validation with the pinned build number,
exact X/Z configuration, and exact package-DTB identity.

`candidate-ab-container-and-installer`: PASS. The two constructions are exact,
the validators and focused mutations passed, and the calibrated guarded
installer pins exact hardware-passed AA r1 as its predecessor.

`candidate-ab-boot2-install`: PASS. The inactive live-GPT-resolved target was
backed up, written once, flushed, and matched a complete readback; no reboot or
slot selection occurred.

`candidate-ab-kernel-restart-runtime`: PASS once. Exact retained attribution,
the working keyboard report, at least 45 seconds without an automatic reset,
the owner-observed immediate response to bare `reboot`, the 27.854 ms internal
request-to-kernel-line interval, and the changed post-return boot ID establish
the prompt kernel TOPRGU software-reset result for this exact candidate and
device. F1-F10 and Page Up/Page Down remain unconfirmed, not failed.

`patch-0087-local-hardware-support`: PASS once. The result supports the MT6797
priority-first restart change on this unit; broad reliability and repeatability
are not yet established.

## Follow-up

Preserve patch 0087 and the separately passed AA r1 console map in the next
integration candidate. A later repeated reboot can establish repeatability;
use a console application with a visible discriminator if explicit F1-F10 and
Page Up/Page Down coverage is required. Keep the one-device runtime result
separate from broader MT6797 reliability and upstream-review conclusions.
