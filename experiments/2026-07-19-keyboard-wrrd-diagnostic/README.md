# Candidate W: MT6797 I2C WRRD diagnostic

| Field | Value |
| --- | --- |
| Experiment ID | `2026-07-19-keyboard-wrrd-diagnostic` |
| Candidate | W |
| Status | Reproduced, validated, installed, and hardware-tested once; AW9523, matrix, event-node, and bounded physical-key gates passed, while console/log isolation and useful interactive duration failed |
| Device scope | Named Gemini PDA used for Candidate V attempt 1 |
| Baseline | Exact Candidate V hardware, DT, kernel-policy, console, ramoops, and watchdog foundation, except for separately identified observation-only deltas |
| Causal kernel delta | One direct MT6797 I2C controller-data match to the existing MT8173-generation data |
| Reference head | Latest checked `bsg100/gemini-linux` `main`: [`60f5f4ac777a0aeccc89b5d3a4f8cd1f1ebe57b3`](https://github.com/bsg100/gemini-linux/commit/60f5f4ac777a0aeccc89b5d3a4f8cd1f1ebe57b3) |
| Device state | Candidate W remains installed on logical `boot2`; attempt 1 returned automatically to Gemian through the deliberate watchdog timeout |

## Purpose and pre-boot hypothesis

Candidate V established exact Linux and external-initramfs entry, a visible
loader-retained framebuffer console, durable `console-ramoops`, and automatic
recovery through the no-IRQ MT6797 watchdog. Its
[attempt-1 record](../2026-07-19-keyboard-watchdog-diagnostic/results/runtime-candidate-v-attempt-1-20260719.txt)
shows that the first keyboard gate failed before matrix polling: every observed
AW9523 register read on I2C adapter 0 at address `0x5b` timed out, the AW9523
provider remained unbound, and consequently the matrix consumer and input
event device never appeared.

The exact working 3.18 binary issues the same one-byte register-address write
followed by a one-byte read, recognizes it as hardware `I2C_MASTER_WRRD`, and
programs receive length at auxiliary controller offset `0x6c`. Candidate V has
no direct `mediatek,mt6797-i2c` driver match and falls through to
`mt6577_compat`, which has `auto_restart = 0` and `aux_len_reg = 0`; V therefore
does not select that WRRD path. The
[working-3.18 and bsg100 controller audit](../2026-07-19-keyboard-watchdog-diagnostic/results/working-3.18-aw9523-i2c-binary-audit-20260719.txt)
reports the same combined-read failure under the MT6577 fallback and a pass
after a direct MT6797 match using `mt8173_compat`.
The latest checked `bsg100/gemini-linux` `main` revision is
[`60f5f4ac777a0aeccc89b5d3a4f8cd1f1ebe57b3`](https://github.com/bsg100/gemini-linux/commit/60f5f4ac777a0aeccc89b5d3a4f8cd1f1ebe57b3);
its retained controller patch and later keyboard evidence are cross-device
corroboration, not a result on this unit.

The Candidate W hypothesis is therefore:

> A direct `mediatek,mt6797-i2c` match to the evidence-backed
> MT8173-generation controller data will make the AW9523 register-address/read
> pair use WRRD with the auxiliary receive-length register. With every AW9523,
> DT, I2C-frequency, matrix, console, ramoops, and watchdog input otherwise
> retained from V, an AW9523 provider-bind result is attributable to that
> controller-data correction.

This was the pre-boot hypothesis for one named-device run. Source comparison
and another Gemini's result did not establish causality on this unit; the
single hardware result below now resolves the provider, matrix, and bounded
physical-key gates without establishing repeatability or all-key coverage.

## Exact retained baseline

Candidate W must reject any input that is not the exact validated Candidate V
foundation or one of the separately permitted observation-only deltas below:

- raw Android-v0 image SHA-256:
  `9ef0ee8dc1eb49752f9cf8f60b247b9b85e4fd2a9f090473f1d91848114087b0`;
- installed 16-MiB Candidate V SHA-256:
  `57d362a86fae38c0ec2cec909ef6ae8d8ad124b87abb2ee58d179184c1f19168`;
- final V DTB SHA-256:
  `bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f`;
- final V initramfs SHA-256:
  `9382288385b50fed67b47ae494609f4ee9d314cfac0257c738e33e86094508b6`;
- V's CPU0-only policy, storage/network exclusions, LK-compatible Android-v0
  addresses and header, loader simplefb, rotated fbcon, `console-ramoops`, and
  no-IRQ 31-second watchdog ownership/recovery contract;
- V's final I2C5/AW9523/matrix DT, including 400-kHz I2C, GPIO58 reset polarity
  and timing, regmap-cache policy, no active AW9523 parent IRQ, 20-ms generic
  matrix polling, 2-us column scan delay, and `drive-inactive-cols`.

Candidate W must use V's final DTB, not the package DTB. The package DTB may be
used only as a validated source oracle. No reset-delay, regmap-cache, I2C
frequency, IRQ, keymap, polling, storage, networking, CPU, watchdog, ramoops,
or display-hardware change belongs in W.

## Causal and observation-only changes

The sole keyboard-causal source change is the direct controller-data match in
`drivers/i2c/busses/i2c-mt65xx.c`, expressed as one match-table line using
`mt8173_compat` or a named `mt6797_compat` with exactly the same evidenced
fields:

```c
{ .compatible = "mediatek,mt6797-i2c", .data = &mt8173_compat },
```

Patch
[`0086-i2c-mediatek-use-MT8173-data-for-MT6797.patch`](../../patches/v7.1.3/0086-i2c-mediatek-use-MT8173-data-for-MT6797.patch)
implements exactly that one source line. The selected
`observability-fbcon-rotation-keyboard-wrrd` profile appends
[`configs/gemini-keyboard-wrrd.fragment`](../../configs/gemini-keyboard-wrrd.fragment)
after the Candidate V keyboard profile; the controller correction remains in
the patch rather than in board policy.

A generic WRRD-guard relaxation while retaining `mt6577_compat` is not the
selected experiment because it does not reproduce the working path's auxiliary
receive-length contract at offset `0x6c`.

The following implemented changes are independent observation-path
improvements and are identified separately in the candidate manifest:

- use a unique `GEMINI_KEYBOARD_WRRD_20260719_W` marker;
- select tty1 as the foreground VT before starting the local shell;
- stop background probe/watchdog marker fanout to tty1 before the prompt;
- use the exact letters-only `pass` success token, requiring only P, A, S, and
  Enter from the retained base keymap;
- compile `CONFIG_FONT_TER16x32=y` and force
  `fbcon=font:TER16x32` for larger text.

The forced kernel console is fixed at tty2 while BusyBox `init` respawns the
local shell on foreground tty1. Background probe and watchdog records go only
to `/run/w-status`, `/dev/kmsg`, and serial, so they cannot overwrite the tty1
prompt. `TER16x32` approximately changes the retained 1080×2160 framebuffer
grid from 270×67 to 135×33 characters.

That was the intended separation. In attempt 1 the owner saw kernel logs mixed
with the shell on the same visible console, so selecting tty2 did not deliver
the required interactive-VT isolation. The larger font was reported as
perfect.

Those changes may make a result observable but cannot be credited with an
AW9523 provider-bind change. The builder and validators must distinguish the
one causal kernel line from each observation-only configuration/initramfs
delta.

## Unique attributable evidence

Before a device boot, W had to have two independently reproduced,
byte-identical candidate directories and a complete manifest that pins the
source tarball, ordered patch series, resolved configuration, exact V baseline,
W kernel, DTB, initramfs, Android-v0 fields, and final image. That build gate is
now complete; installation alone is not runtime evidence.

The bounded runtime must write the following to `/dev/kmsg` so it can survive
in V's exact `console-ramoops` zone:

1. the exact W marker and kernel/initramfs entry checkpoint;
2. the resolved `1101c000.i2c` platform device and bound `i2c-mt65xx` driver;
3. the first AW9523 transfer result and the `0-005b` provider bind state;
4. the matrix platform-device/driver bind state;
5. the exact matrix-owned input event node, when one exists;
6. bounded, non-grabbing raw `EV_KEY` records and a letters-only typed-success
   marker, when input exists;
7. exact `mtk-wdt` association, one ownership-handoff ping, and the same
   31-second recovery checkpoints used by V.

An exact W marker plus the verified W image and retained one-line causal delta
makes a changed AW9523 bind result attributable even if the screen becomes
unusable. Marker text alone is insufficient: the provider and first-transfer
state must distinguish the result.

## Decision oracle

| Retained or visible result | Interpretation | Next action |
| --- | --- | --- |
| No exact W marker and no retained pstore after a confirmed cycle | W selection or kernel/initramfs entry remains unattributable | Do not repeat unchanged W; add a genuinely independent early observation path |
| Exact W entry plus automatic recovery, but the same AW9523 `-110` occurs before provider bind | The direct controller-data match did not clear the first provider gate on this unit | Confirm the built/running match and first transfer, then reopen reset recovery, power, pinmux, or physical-bus hypotheses; keep matrix code fixed |
| AW9523 binds or chip ID `0x23` is observed, but the matrix consumer remains deferred/unbound | The controller correction passes its provider gate; the next failure is downstream | Preserve kernel/I2C/AW9523 state and isolate only matrix supplier/bind state |
| AW9523 and matrix bind, but no matrix-owned input event node appears | Provider and polling-driver bind pass; input registration/exposure fails | Instrument only matrix input registration |
| Exact event node exists but no physical `EV_KEY` record appears | Controller, provider, matrix bind, and evdev exposure pass | Keep those inputs fixed; isolate scan polarity/timing, wiring, or physical key coordinates |
| Exact press/release records and the letters-only shell token survive | One bounded keyboard-to-tty path passes | Preserve the exact evidence; test key coverage, modifiers, rollover, wake, and repeatability separately |
| Safely identified watchdog fails to return the unit automatically | Recovery regressed independently of keyboard behavior | Stop keyboard testing and restore the proven V recovery contract first |

One successful run does not establish repeatability, all key positions,
rollover, wake, LED control, normal-rootfs serviceability, native display, or
long-idle stability.

## Runtime attempt 1

The owner selected exact Candidate W from logical `boot2` once. A shell
appeared, the physical keyboard worked for the attempted input, and the
`TER16x32` font was reported as perfect. Kernel logs nevertheless remained
mixed with the shell on the same visible console. The deliberate 31-second
watchdog expiry then returned the device automatically to Gemian before a
useful interactive session was possible; the owner prefers a typeable manual
`reboot` command.

The authenticated post-return `console-ramoops` record contains the exact W
marker and resolves every causal provider gate:

- `1101c000.i2c` bound `i2c-mt65xx`;
- client `0-005b` probed successfully and bound `aw9523-pinctrl`, with no
  `-110`/`ETIMEDOUT` in the captured console window;
- the initially deferred `keyboard-matrix` consumer subsequently bound
  `matrix-keypad`, registered `keyboard-matrix`, and exposed exact
  `/dev/input/event0`;
- the non-grabbing 15-second capture retained press and release records for H,
  E, L, P, and Enter. Enter produced four press/release pairs; each letter
  produced one pair.

Those records establish only the listed key positions in one run. They are
consistent with typing `HELP` and Enter, but shell command execution was not
retained and W's `pass` success marker is absent. They do not establish all
keys, modifiers, rollover, repeatability, or long-idle behavior.

The watchdog record shows the exact `mtk-wdt` open, one handoff ping, and waits
through 30 seconds, with no 35-second or expiry-failure marker. Gemian then
reported boot reason 4, `androidboot.bootreason=wdt_by_pass_pwk`, and
`powerup_reason=reboot`. Collection began after the owner-observed return, so
the collector did not itself span the disconnect/reconnect transition; the
verified installed image, exact W marker, retained timing sequence, owner
observation, and boot reason provide the attribution.

Compared with exact V's repeated AW9523 `-110` and unbound provider, W's
successful provider bind strongly attributes the changed result in this run to
the one-line MT6797 controller-data match while the final DTB and AW9523/matrix
policy remained exact. No physical I2C waveform or controller-register trace
was captured, so describe this as hardware support for the WRRD hypothesis,
not a direct electrical measurement.

Close unchanged W. Preserve its kernel/controller, final DTB, AW9523, matrix,
keymap, font, and ramoops inputs. The next observation-only derivative must
remove kernel logs from the interactive VT and avoid the deliberate userspace
watchdog timeout while keeping a typeable manual reboot path. See the complete
[attempt-1 runtime record](results/runtime-candidate-w-attempt-1-20260719.txt).

## Build and validation gate

The Candidate W profile, builder, component validators, deterministic
initramfs construction, and guarded installer are implemented beside this
document. The kernel-package build entry point is:

```sh
KERNEL_PROFILE=observability-fbcon-rotation-keyboard-wrrd \
  ./scripts/dev-vm build-kernel
```

Two clean W kernel builds completed from independent source/build roots. Their
package content is byte-identical except for `SHA256SUMS` and
`provenance/build.json`'s `generated_utc`; deleting that timestamp produces the
same normalized build-JSON SHA-256
`d2e4c1367d8394340efa4d1f67c2404c13c1f323b9490dacc59dd3be2512847a`.
The first and second package-manifest SHA-256 values are respectively
`6337c00318acecea64ed77fe67757744f9c2ad9d730c1c22b14b7ad43b2a91d0`
and
`53bf80a6bf071f48248639c5fc6c914e9a260c71806a62ca80593767e49d441e`;
their difference is confined to the timestamp-bearing provenance just noted.
Both passed the generic artifact, focused package, exact controller-patch, and
exact V-baseline validators. Two final Candidate W assemblies, `rebuild3` and
`rebuild4`, are recursively identical and share SHA-256
`257b17585c171e29ae3510fdab7602aa59e4da570aa906abb8b9e5b7e8da5851`
for their complete `SHA256SUMS` manifest. The 24-case mutation suite passed
24/24; the tested suite's SHA-256 is
`1d253b14090316565edfeb2ca10fa6875bddac6d39e4d2b5ffa1328c18d2ba44`.
The final calibrated identities are:

- package:
  `linux-7.1.3-gemini-observability-fbcon-rotation-keyboard-wrrd-4cd417ad-28a94091`;
- patchset SHA-256:
  `4cd417adb0d79aad2f021e1f07e47bed4825cb51b3a069e5258ea4eb49ca5ef4`;
- resolved W initramfs SHA-256:
  `3793bec7a63074b237d041bcd42e6edfccc80f0a3d7b19869abf99ee7874dac6`;
- exact retained V DTB SHA-256:
  `bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f`;
- raw 6,866,944-byte Android-v0 image SHA-256:
  `34c41fad1e86de05b6a1f64f7e5d9229bd26ea88d982b0a57f2b9573aeb782d4`.

The selected `rebuild4` artifact was exported to
`artifacts/vm-export/boot-candidates/candidate-W-final-rebuild4/candidate-W-keyboard-wrrd-final-34c41fad`.
The complete evidence is in the
[independent reproduction result](results/final-build-reproduction-20260719.txt),
[mutation result](results/validator-mutations-20260719.txt), and
[guarded write/readback result](results/boot2-write-candidate-w-20260719.txt).

These build results selected W as the validated artifact but, by themselves,
proved no runtime behavior. The separate attempt-1 record above supplies the
single-run hardware evidence.

## Guarded logical-boot2 installation

After independent reproduction identified one unique latest validated W
artifact, the guarded helper installed it only to live-resolved logical
`boot2` while the named Gemini was running its known-good Gemian root. The
completed invocation used the exported `rebuild4` artifact; the helper has no
reboot or password interface:

```sh
bash experiments/2026-07-19-keyboard-wrrd-diagnostic/scripts/install-candidate-w-boot2.sh \
  --target gemini@192.168.1.50 \
  --candidate artifacts/vm-export/boot-candidates/candidate-W-final-rebuild4/candidate-W-keyboard-wrrd-final-34c41fad/gemini-keyboard-wrrd.boot.img \
  --expected-candidate-sha256 34c41fad1e86de05b6a1f64f7e5d9229bd26ea88d982b0a57f2b9573aeb782d4 \
  --expected-current-sha256 57d362a86fae38c0ec2cec909ef6ae8d8ad124b87abb2ee58d179184c1f19168 \
  --backup-dir artifacts/device-partitions/pre-candidate-w-20260719T212622Z
```

The helper requires the mode-0600 repository SSH identity, a manifest-listed
artifact matching the explicit expected Candidate W checksum, and passwordless
remote sudo. It resolves exact `boot2` from the live GPT in every gated phase,
samples and canonicalizes the active known-good root before the first gate and
requires that exact root to remain unchanged and separate, checks size/writability,
mount/swap/holders, stable boot ID, and two exact stable power samples. It skips
the write when the full target already matches padded W. Otherwise it creates a
new private directory, globally syncs and revalidates a mode-0600 full backup
plus checksum sidecar, and reserves and flushes the complete local-readback
capacity before writing. It pads W to the exact 16-MiB target size, verifies the
user upload, copies it into a root-owned read-only file inside a root-only runtime
directory, and uses only that immutable copy as the write input. It repeats the
live-GPT, in-use, root, boot-ID, and power gates in the same remote process
immediately before the bounded write, then syncs and flushes and requires
matching full remote and local readback
checksums. It removes only its exact temporary staging objects and never
reboots, selects a boot target, or writes another partition.

The live GPT resolved `boot2` as `/dev/mmcblk0p30` while the active root was
the separate `/dev/mmcblk0p29`. The full pre-write backup matches the expected
V checksum
`57d362a86fae38c0ec2cec909ef6ae8d8ad124b87abb2ee58d179184c1f19168`.
After padding W to 16 MiB, the candidate, post-flush remote checksum, and full
local readback all match SHA-256
`0ff3220096aa53f792116b3899e356bc2516816c9c330309c3d81e9fe1446608`.
The boot ID and exact AC/full-battery power sample remained stable, and the
helper performed no reboot or shutdown. See the
[write/readback record](results/boot2-write-candidate-w-20260719.txt).

The owner later selected `boot2` with the silver button and observed the
completed automatic return. Because that cycle had already completed before
collection began, retained evidence was recovered without requesting a new
cycle:

```sh
scripts/collect-device-pstore \
  --target gemini@192.168.1.50 \
  --output artifacts/device-pstore/candidate-w-attempt-1-20260719
```

The private capture remains mode 0700 with mode-0600 files under the
Git-ignored artifact path; no pstore record or partition was removed. The
sanitized result is the linked public attempt-1 record. Do not select unchanged
W again: its keyboard gates passed, but its deliberate timeout and visible
kernel-log mixing make it a poor serviceability image.
