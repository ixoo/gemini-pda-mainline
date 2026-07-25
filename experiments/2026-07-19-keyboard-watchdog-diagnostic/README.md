# Gemini keyboard watchdog diagnostic (Candidate V)

## Status

Candidate V is a new experiment; it does not relabel the runtime-failed
Candidate U artifact. Its builder, deterministic initramfs, exact-P Device Tree
transform, component validators, and negative mutation suite are self-contained
in this directory. Two independent V builds were recursively byte-identical and
all 24 negative mutations were rejected. V was installed to live-resolved
logical `boot2` on 2026-07-19 and fully read back. Its first intended selection
then produced a visible console and an automatic watchdog return. Retained
`console-ramoops` proves exact V kernel and initramfs entry, but the AW9523
provider timed out and never bound, leaving the matrix consumer, evdev node,
and keyboard unavailable. V is closed after this one attributable run; do not
repeat it unchanged. See the [runtime record](results/runtime-candidate-v-attempt-1-20260719.txt)
and [probe-boundary audit](results/aw9523-probe-boundary-audit-20260719.txt).

## Why V is decision-changing

Candidate U's first intended selection produced a black screen, no visible
marker, and no automatic return. Later inspection found a concrete packaging
error independent of the keyboard driver: U built its final DTB from the
kernel package DTB, not from Candidate P's hardware-passed final DTB. U's DTB
therefore omitted P's loader-retained `/chosen/framebuffer@7dfb0000`, its two
clock references, the no-IRQ watchdog state, and other LK-aligned fixups.

The missing simplefb node explains why U did not carry the configured P
console path. It does **not** prove that the intended slot was selected, that
U entered Linux, or that this omission caused the observed black screen.
U's empty post-return pstore leaves those gates unestablished.

V changes the observation and recovery contract in two independently useful
ways:

1. its final DTB starts from exact, hardware-passed Candidate P bytes and
   permits only an audited keyboard-resource/polling transform; and
2. it restores the hardware-proven no-IRQ watchdog/ramoops cycle, so a dark
   display can still return automatically and leave durable `/dev/kmsg`
   markers for the known-good Gemian boot to collect.

## Hypothesis

With P's complete final DT state retained, a corrected Linux 7.1.3
`gpio-matrix-keypad` polling implementation can bind the upstream AW9523 GPIO
provider, register an exact matrix-owned evdev node, and deliver typed input to
an independently supervised tty1 shell. Even if the screen remains dark, the
no-IRQ MT6797 watchdog should reset about 31 seconds after userspace ownership
handoff, and P's ramoops console should preserve the last V checkpoint.

The corrected polling patch adds managed delayed-work cancellation before
input registration and serializes suspend/resume against input open/close,
gating restart on `input_device_enabled()`. V hard-pins that patch; it does not
use the historical U kernel image.

## Exact DT lineage

The immutable base is Candidate P DTB SHA-256
`c574762aa178cb5a7238400b499d2edcdd3acb3538d2255e916b041f2074c379`.
The corrected package DTB SHA-256
`f9be46ffed6cf598f7892d88d8702ff6a4ede074c5b477734ae11bcb4c093db5`
is an oracle for keyboard resources only; it is never copied as the V base.

The exact allowlist is:

- allocate fresh, globally unique P-local phandles `0x2a` and `0x2b` after
  asserting P's exact maximum `0x29` belongs to `hall-pins`;
- attach the already-described I2C5 pin group and recreate the oracle's GPIO58
  reset-high plus GPIO87/EINT10 pin state;
- enable I2C5 at 400 kHz, the upstream AW9523 provider, and the existing matrix
  consumer;
- make AW9523 `gpio-ranges` self-referential and remove its parent/nested IRQ
  properties for this polling-only active path; and
- set a 20 ms poll interval and 2 us column delay without the polling-inert
  debounce property.

The validator parses the whole FDT and requires every other P node/property,
the reservation map, and `boot_cpuid_phys` to remain exact. It also rebuilds
the transform and requires byte-identical output. In particular, V does not
mutate P's already absent watchdog IRQ and must retain exact P simplefb,
ramoops, CPU frequency fixups, ATF reserved-memory tags, SCP node, USB/T-PHY/
MTU3 status, native-display exclusions, and unrelated board data.

## Runtime sequence

The exact marker is:

`GEMINI_KEYBOARD_WATCHDOG_20260719_V`

PID 1 mounts only devtmpfs, read-only procfs, and read-only sysfs. It then
launches the watchdog owner and keyboard probe as independent background
workers before executing BusyBox init, which immediately supervises an
interactive tty1 shell. Neither worker can postpone shell creation or the
other worker.

The keyboard probe waits at most five seconds for an event node below the
exact matrix platform device, then passes that exact `/dev/input/eventN` path
and its exact sysfs name to a static helper. After open, the helper revalidates
the name with `EVIOCGNAME`, never uses `EVIOCGRAB`, and captures for at most 15
seconds against an absolute monotonic deadline. Thus raw observation does not
steal events from the tty path and completes within 20 seconds of userspace
entry. V intended `/bin/v-pass` to emit the distinct durable
`SHELL_INPUT_PASS` checkpoint. Post-runtime audit found that this literal
command is not normally typeable from V's base map because neither
`KEY_SLASH` nor `KEY_MINUS` is present. The prompt is also non-durable, tty1
is not explicitly selected as the foreground VT, and later worker messages can
bury it. Absence of `SHELL_INPUT_PASS` is therefore not a valid keyboard-failure
oracle; a follow-up must use a letters-only command, explicitly select tty1,
and keep background records off the interactive terminal.

The watchdog worker checks the live DT, exact watchdog0-to-
`10007000.watchdog` association, `mtk-wdt` identity/driver, timeout attributes,
and ramoops platform binding. DT, timeout, pretimeout, or ramoops observation
mismatches are recorded but do not sacrifice recovery when watchdog0 is still
safely attributable to `mtk-wdt`. It opens watchdog fd 3 once, sends exactly
one ownership-handoff ping, retains the fd, and sends no further pings. There
is no generic reset command. The expected single-stage TOPRGU reset occurs
about 31 seconds after that ping; a surviving 40-second marker means expiry
failed.

Every scripted checkpoint fans out to `/dev/kmsg`, `/dev/console`, tty0, tty1,
and ttyS0. `/dev/kmsg` is the durable route into P's exact primary
`console-ramoops` zone at `0x44410000` for later Gemian collection.

## Decision oracle

| Retained or visible result | Interpretation | Next action |
| --- | --- | --- |
| `entry` plus automatic return, but no later V marker | P console/ramoops path is present but execution stopped early | Use last durable checkpoint; change only that failed gate |
| `watchdog_association=exact` and automatic return | Independent recovery path passed | Treat later keyboard markers as attributable even if display was dark |
| AW9523 client present but provider unbound with register/Chip-ID timeout | Controller-to-provider transfer gate failed before matrix polling | Keep AW9523 reset/cache, matrix, and I2C frequency fixed; correct the MT6797 controller match and WRRD/aux-length contract |
| Matrix device/driver present, exact event absent | Polling driver bound but input registration/event exposure failed | Instrument the matrix registration boundary only |
| Exact event plus raw `EV_KEY` records, shell does not type | Matrix and evdev pass; investigate keymap/VT routing | Keep kernel/DT fixed and isolate input-to-tty routing |
| `SHELL_INPUT_PASS` survives | AW9523, polling matrix, mapping, tty1 and typed shell pass once | Preserve exact evidence; test key coverage separately |
| Safely identified watchdog exists but no automatic return and `watchdog_expiry_failed` survives | Recovery path regressed | Stop keyboard testing and restore watchdog recovery first |
| No V marker and no pstore after a confirmed cycle | Selection/kernel entry remain unattributable | Do not repeat unchanged V; add a new independent pre-userspace path |

No one run proves repeatability, wake, rollover, all key positions, native
display, parent IRQ behavior, or normal-rootfs serviceability.

## Attempt 1 result

The owner selected logical `boot2`, saw the text console, could not obtain a
usable shell or keyboard-test opportunity, and observed an unassisted return
to Gemian. The retained exact V marker establishes selection, Linux entry, and
external `/init`. The local-shell process reached its recorder immediately
before `exec ash -i`; that marker does not prove that ash executed, that the
prompt became visible, or that tty1 was interactive. The same log shows
simplefb registering its 1080×2160×32 loader buffer as fb0 and fbcon selecting
a 270×67 grid, consistent with V's compiled VGA8x16 font and the owner's report
that the console text was too small.

The first keyboard failure is exact. Linux adapter 0 corresponds to
`/i2c@1101c000`, and its `0-005b` AW9523 client repeatedly returned
`-110` (`ETIMEDOUT`) while reading register `0x02` and the chip-ID register,
including after the driver's reset retries. The AW9523 driver remained
unbound. `keyboard-matrix` consequently remained deferred and unbound while
waiting for the AW9523 pinctrl supplier; no matrix-owned input or event node
existed, so the raw-event window was correctly skipped. This run never reached
the generic polling implementation and supplied no physical key event.

The independent recovery path passed. The exact `mtk-wdt` device was opened,
pinged once, and retained on fd 3 with its 31-second timeout. Markers survived
through `watchdog_wait=30s`, with no 35-second or expiry-failure marker. The
post-return Gemian boot reported numeric reason `4`,
`androidboot.bootreason=wdt_by_pass_pwk`, and `powerup_reason=reboot`. Together
with the owner's automatic-return observation, that establishes the intended
single-stage watchdog reset rather than a panic or manual recovery.

Do not repeat unchanged V. Read-only disassembly of the exact working 3.18
kernel identifies the missing controller contract: its AW9523 register read is
a one-byte write plus one-byte read, and its MT6797 controller unconditionally
turns that pair into hardware WRRD while programming the receive length at
auxiliary offset `0x6c`. Linux 7.1.3 has no direct MT6797 driver match, so V
falls through to `mt6577_compat` (`auto_restart = 0`, `aux_len_reg = 0`) and
never selects WRRD. Latest bsg100 independently recorded the same combined-read
failure on another Gemini and fixed it in hardware by matching
`mediatek,mt6797-i2c` to `mt8173_compat`.

The next keyboard experiment should make that direct controller-data match its
only causal change while retaining exact V's DT, AW9523 reset timing and
regmap cache, I2C frequency, polling consumer, simplefb, ramoops, and no-IRQ
watchdog foundation. A generic WRRD guard relaxation alone retains the wrong
MT6577 auxiliary-length policy and is not the selected MT6797 correction.
Reset-delay/cache alternatives are deferred unless the controller-corrected
run reopens them. The next candidate must also repair the tty oracle. Per the
owner's visibility request, it should compile and force the built-in
`TER16x32` fbcon font; the tty and font edits are observation-path changes, not
keyboard-causality changes. See the
[working 3.18 binary/controller audit](results/working-3.18-aw9523-i2c-binary-audit-20260719.txt).

## Build and validation

The top-level builder accepts only a newly selected corrected polling-profile
package, exact Candidate P artifact, and a new output directory:

```sh
experiments/2026-07-19-keyboard-watchdog-diagnostic/scripts/build-keyboard-watchdog-candidate.sh \
  --package /home/julien.guest/artifacts/gemini-pda/EXACT-CORRECTED-PACKAGE \
  --baseline /home/julien.guest/artifacts/boot-candidates/candidate-P-fbcon-rotation-170a640 \
  --output /home/julien.guest/artifacts/boot-candidates/candidate-V-keyboard-watchdog
```

The builder has no caller-provided hash overrides. It hard-pins the source,
complete package manifest, Image/Image.gz/System.map, package DT oracle,
resolved config and config inputs, exact toolchain, recomputed 86-entry patch
provenance, and corrected patch 0084. It first runs the repository's complete
kernel-artifact validator, then the V-specific package, patch, P-based DT,
canonical initramfs, exact Android-v0/LK, capacity, and checksum validators.
Build twice into new directories and require recursive equality before any
selection decision.

The validated build has these exact outputs:

- boot image: SHA-256
  `9ef0ee8dc1eb49752f9cf8f60b247b9b85e4fd2a9f090473f1d91848114087b0`,
  6,864,896 bytes;
- P-based V DTB: SHA-256
  `bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f`;
- V initramfs: SHA-256
  `9382288385b50fed67b47ae494609f4ee9d314cfac0257c738e33e86094508b6`;
- static capture helper: SHA-256
  `b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602`;
  and
- complete output `SHA256SUMS`: SHA-256
  `0ab8291fef437cc4d2cc2b415852d21e6ccfb9deff67e8bec41b4dbfc8068ef9`.

The two fresh kernel builds reproduced all selected non-timestamp package
content. The full package validator passed, as did the focused binding schemas.
Strict Checkpatch was clean for patches 0083--0085; patch 0082 has only one
commit-message long-line warning. The V validator rejected all 24 of 24
negative mutations. The exact package, component, and validation identities are
preserved in the [build reproduction](results/final-build-reproduction-20260719.txt),
and the post-build harness plus all rejected cases are pinned in the
[mutation result](results/validator-mutations-20260719.txt).

Run the mutation suite against that exact output. It rejects wrong P/oracle
inputs; loss or change of simplefb; a re-added watchdog IRQ; ramoops, CPU,
ATF, SCP, T-PHY, MTU3, unrelated-property, target-extra-property, and duplicate
phandle mutations; initramfs/helper/boot mutations; and coherent package,
config, Image, patchset, or packaged-0084 substitutions.

## Safety boundary

All build and validation commands are host/VM-only and have no target, SSH,
partition, block-device, or flashing interface. The automated runtime path
does not access storage, configure networking, issue raw I2C transactions,
touch raw memory/framebuffer devices, online CPUs, or run a generic reset
command. CPU policy remains `maxcpus=1`.

The interactive shell is intentional and exists only in the minimal RAM
archive; no automated script invokes it. The completed `boot2` synchronization
was a separate guarded repository operation under the standing device policy:
it resolved the live GPT, preserved and read back the full partition, and did
not reboot automatically as part of the write.

## Installation state

On 2026-07-19 the guarded synchronization resolved logical `boot2` from the
live GPT as `/dev/mmcblk0p30`; the active root remained separate. The raw
6,864,896-byte V boot image has SHA-256
`9ef0ee8dc1eb49752f9cf8f60b247b9b85e4fd2a9f090473f1d91848114087b0`.
After zero-padding to the exact 16 MiB target, its full-partition SHA-256 is
`57d362a86fae38c0ec2cec909ef6ae8d8ad124b87abb2ee58d179184c1f19168`.
The mode-0600 pre-write backup preserved Candidate U with SHA-256
`7c57176f3fb5e8e7c9619f038cf09517ca85ee0323ff48ff8c382b60b2794c6e`.
The remote post-write checksum and complete local readback both matched V's
padded hash. Root identity, boot ID, and power state were unchanged, and the
write operation did not reboot or shut down the device.
The complete safety gates, backup, write, flush, and readback are preserved in
the [guarded `boot2` record](results/boot2-write-candidate-v-20260719.txt).

Installation proves artifact and target identity only; the later runtime is
recorded separately. Attempt 1 established exact V entry, one visible
loader-retained simplefb/fbcon cycle, retained ramoops, and the intended
watchdog return. It failed at the AW9523 provider before matrix polling or
keyboard input, and it did not establish a visible or interactive shell.
