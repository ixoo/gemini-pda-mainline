# Candidate Q: keyboard and supervised local-shell diagnostic

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-18-keyboard-shell-diagnostic` |
| Candidate | Q |
| Status | Runtime failed: the intended `boot2` selection did not provide a working text console; no deeper Q gate was observable |
| Subsystem | MT6797 I2C5, AW9523 GPIO/IRQ, matrix keyboard, evdev, VT, and initramfs shell |
| Device variant | Current Gemini PDA unit; exact retail sub-variant not independently established |
| Date | 2026-07-18 through 2026-07-19 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Agreed acceptance contract

Candidate Q is the next implementation and hardware gate. By owner decision it
combines the previously separate keyboard-event and local-shell plans so that
one costly manual `boot2` selection can provide a useful interface. It must
still make the layers independently observable:

1. built-in MT65XX I2C, AW9523, matrix-keypad, and evdev closure;
2. corrected, candidate-only board-DT enablement;
3. a bounded pre-shell input-device and raw-event probe; and
4. a supervised interactive BusyBox shell on the framebuffer console.

The shell is not allowed to hide a keyboard failure. Before the prompt, Q must
show whether I2C5 exists, whether the client at `0x5b` bound to the upstream
AW9523 driver, whether a matrix input device and evdev node exist, and whether
press/release events arrive. A unique marker must distinguish Q from the
inherited Candidate O/P initramfs lineage.

Normal operation has no countdown, inactivity timeout, success reboot, or
deadman reset. Probe failure, shell exit, and user inactivity are not severe
failures and must not reboot the device. Recovery after the attended test is
explicitly owner-initiated.

The old planned Candidate R shell stage had no implementation or artifact. It
is retired and folded into Q; do not reuse the R identifier. Candidate S
remains the later eMMC series and Candidate T remains the later USB-networking
series unless a separate renumbering decision is recorded.

## Question and independently observable gates

With exact hardware-passed Candidate P as the readable-console baseline, can
Linux 7.1.3 reuse the upstream `pinctrl-aw9523` GPIO/IRQ provider and generic
`gpio-matrix-keypad` consumer for the Gemini keyboard, then accept typed input
in a supervised local initramfs shell, while remaining visible and running
indefinitely without a programmed reboot?

The attributable gates are:

1. **Q entry:** exact Q marker appears in the correct landscape orientation.
2. **I2C/AW9523:** the physical I2C5 controller is resolved dynamically by OF
   ancestry to `/i2c@1101c000`; its actual Linux adapter number and matching
   `${adapter_number}-005b` client are reported, and the client binds or an
   exact probe error is printed. Never assume that I2C5 becomes Linux adapter
   5.
3. **Matrix/evdev:** the matrix input device and dynamically resolved event
   node appear.
4. **Electrical/input events:** a clearly announced 60-second `MSC_SCAN`,
   `EV_KEY`, and `EV_SYN` window records press/release evidence without
   grabbing the device.
5. **VT/TTY:** the same keyboard types into the `tty1` shell.
6. **Supervisor:** shell exit respawns a prompt and does not reboot.
7. **Long-lived console:** the prompt and display remain available for at
   least 15 idle minutes, beyond the normal ten-minute VT blanking boundary.

## Exact Candidate P baseline

Q must pin and verify the exact Candidate P package and exported runtime image,
not select a file by timestamp:

| Input | Exact Candidate P value |
| --- | --- |
| Source revision | `170a6403ef41438e01a512d65eb9ad9c223118b0` |
| Package | `linux-7.1.3-gemini-observability-fbcon-rotation-e1d4f6f3-03ac37f8` |
| Patch count / series SHA-256 | 82 / `e1d4f6f36b49c5f6064bd7344e31c69b05903ef2f37fa8d9af736035faf47a8a` |
| Compiler | `gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0` |
| Linker | `GNU ld (GNU Binutils for Ubuntu) 2.42` |
| Resolved configuration SHA-256 | `0759fdb25abf25008ecf967736316a2d16d227c80c6835dad5875e8a612ef424` |
| Raw boot image SHA-256 | `d192dac9e4516eac9319da2a885abaf3203da6c357c574e7f1f6deef2208d341` |
| Full padded `boot2` readback SHA-256 | `cea00d591e74a29d74200f4d292a92aaca2f890bd965af37a7673ab906f4afbc` |
| Appended DTB SHA-256 | `c574762aa178cb5a7238400b499d2edcdd3acb3538d2255e916b041f2074c379` |
| External initramfs SHA-256 | `3f19afd81632fbe654c024b9f865180b42caf61163bb26ea26211884271a11d8` |
| Static BusyBox SHA-256 | `52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933` |
| Kernel address | `0x40200000` |
| Ramdisk address | `0x45000000` |
| Second address | `0x40f00000` |
| Tags address | `0x44000000` |
| Android page size | `2048` |
| Android name / command line | `gemini-obs-L` / `bootopt=64S3,32N2,64N2` |

Candidate P passed one attributable hardware run: its console was readable in
normal landscape orientation, the retained trace completed every CPU1--7
checkpoint and final `online=0-7` success, and it returned to Gemian without
owner intervention. See the [P runtime record](../2026-07-18-fbcon-rotation-diagnostic/results/runtime-candidate-p-attempt-1-20260718.txt).

Q must preserve P's simplefb/fbcon geometry, `fbcon=rotate:3`, 8x16 font,
no-IRQ watchdog DT, pstore layout, LK container and addresses, USB diagnostic
foundation, CPU topology, memory reservations, and unrelated configuration and
DT data except for the explicit deltas below. Q does **not** repeat P's initramfs
CPU sweep: forced `maxcpus=1` remains, no CPU-online path is written, and the
interactive test runs on CPU0.

## Controlled kernel-configuration delta

Add `configs/gemini-keyboard.fragment` and pin a dedicated
`observability-fbcon-rotation-keyboard` manifest profile whose fragments are
the exact `observability-fbcon-rotation` list followed only by that new
fragment. Because `CONFIG_MODULES=n`, the keyboard path must be built in:

```text
CONFIG_I2C=y
CONFIG_I2C_MT65XX=y
CONFIG_PINCTRL_AW9523=y
CONFIG_KEYBOARD_MATRIX=y
```

The kernel-package build entry point is therefore:

```sh
KERNEL_PROFILE=observability-fbcon-rotation-keyboard ./scripts/dev-vm build-kernel
```

The resolved configuration validator must also require the built-in dependency
closure, including `CONFIG_INPUT=y`, `CONFIG_INPUT_EVDEV=y`,
`CONFIG_INPUT_KEYBOARD=y`, `CONFIG_INPUT_MATRIXKMAP=y`, `CONFIG_GPIOLIB=y`,
`CONFIG_GPIOLIB_IRQCHIP=y`, `CONFIG_EINT_MTK=y`,
`CONFIG_PINCTRL_MT6797=y`, `CONFIG_REGMAP_I2C=y`, `CONFIG_TTY=y`,
`CONFIG_VT=y`, and `CONFIG_VT_CONSOLE=y`. It must retain
`# CONFIG_MODULES is not set`, `# CONFIG_I2C_CHARDEV is not set`,
`# CONFIG_DEVMEM is not set`, `# CONFIG_MMC is not set`, and the existing
storage, kexec, host-USB, and raw-memory exclusions.

Append exactly `consoleblank=0` to P's forced `CONFIG_CMDLINE` for a persistent
interactive display. `CONFIG_CMDLINE_FORCE=y` means an Android-header-only
token would be discarded and must be rejected. Preserve `maxcpus=1`,
`panic=0`, `clk_ignore_unused`, `fbcon=rotate:3`, the current font and local
version, `CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y`, and
`CONFIG_WATCHDOG_OPEN_TIMEOUT=0`.

The reviewed build pins the complete resolved-config diff. Its minimal I2C
dependency closure explicitly suppresses unrelated arm64 I2C controller
defaults which otherwise became newly visible after `CONFIG_I2C=y`.

## Controlled Device Tree delta

The upstream-facing board DTS must remain conservative: I2C5, the AW9523
client, and the matrix consumer stay disabled in the normal packaged board
description until Q passes. Add one reviewable patch after the current series
to correct the disabled candidate and describe the missing SoC-side pinctrl;
then let Q's packaging-only DT step enable exactly the three named nodes.

The disabled source correction must:

- assign the existing `i2c5_pins_a` state to I2C5;
- add a source-backed MT6797 state with GPIO58 in GPIO mode/output-high and
  GPIO87 in EINT10 mode;
- select that SoC state on `gpio-expander@5b`;
- retain `reset-gpios = <&pio 58 GPIO_ACTIVE_HIGH>` because the upstream
  AW9523 driver's logical 0-to-1 reset sequence then produces the required
  physical low pulse followed by high release;
- retain parent interrupt GPIO87 with `IRQ_TYPE_LEVEL_LOW`;
- replace the current unvalidated `gpio-ranges = <&pio 0 0 16>` mapping with
  the binding-validated combined-controller mapping, expected to be
  `gpio-ranges = <&aw9523 0 0 16>`; and
- retain `gpio-activelow`, `drive-inactive-cols`, and the active-ELF-normalized
  8x7 map, including physical `(row=4,column=3) = KEY_LEFTMETA`.

The four unassigned matrix positions remain omitted/`KEY_RESERVED` until real
events prove that any is a contact. Do not convert Gemian XKB policy into DT
keycodes.

Do not add GPIO87 `bias-pull-up` or `input-enable`: the current MT6797 pinctrl
data lacks the pull and input-enable register maps needed to honor those
properties. The unknown retained/electrical pull state on GPIO87 is Q's main
named electrical risk. Do not hide it with polling or a guessed pin setting.
Do not add debounce, scan-delay, periodic-polling, wake, or vendor timing
properties before the event trace measures the actual behavior. Preserve the
controller's default conservative bus rate; do not silently copy a vendor
400-kHz policy.

The final diagnostic DTB may change status only for:

```text
/i2c@1101c000
/i2c@1101c000/gpio-expander@5b
/keyboard-matrix
```

The DT validator must derive paths and phandles from the exact input DTB,
reject guessed numeric phandles, validate the AW9523 and matrix schemas, and
prove that simplefb, ramoops, watchdog, CPU, USB, storage, reserved-memory, and
the FDT reservation map remain unchanged.

## Controlled initramfs delta

Build a deterministic archive around the exact P BusyBox bytes rather than
copying an unpinned host binary. The expected implementation is:

```text
experiments/2026-07-18-keyboard-shell-diagnostic/
├── README.md
├── initramfs/
│   ├── init
│   ├── inittab
│   ├── local-shell
│   └── q-pass
├── src/
│   └── input-event-capture.c
└── scripts/
    ├── build-input-event-capture.sh
    ├── build-initramfs.sh
    ├── build-keyboard-dtb.sh
    ├── build-keyboard-shell-candidate.sh
    ├── validate-package-delta.py
    ├── validate-dtb-delta.py
    ├── validate-initramfs-delta.sh
    ├── validate-boot-delta.py
    └── test-validator-mutations.sh
```

The tracked changes outside that directory are the new
`configs/gemini-keyboard.fragment`, the pinned
`observability-fbcon-rotation-keyboard` entry in `kernel/manifest.json`, and
one next-in-series reviewable patch for the disabled board-DT correction. The
agent must derive the patch number from the live `patches/series`; do not
assume a number from this plan. The candidate-only status enablements remain
in the deterministic Q DT builder and must not alter the reusable board
defaults.

The deterministic archive member map is:

```text
/
├── init                              regular, executable PID-1 bootstrap
├── bin/
│   ├── busybox                       exact P bytes
│   ├── input-event-capture           new static AArch64 ELF
│   ├── local-shell                   regular executable script
│   ├── q-pass                        regular executable script
│   └── {ash,cat,dmesg,grep,init,ls,mount,ps,readlink,reboot,sed,sh,
│       sleep,stty,tail,true,uname}    symlinks to busybox
├── etc/
│   └── inittab                       regular file read by BusyBox init
├── dev/
├── proc/
├── run/
└── sys/
```

The allowlist is exact: do not retain P's `ip`, `nc`, or `usb-report` members
in a physical root-shell archive. Before packaging, execute the exact AArch64
BusyBox under the development VM and prove every listed applet exists; a
symlink alone is not evidence. The initramfs validator must check each source
file's destination, type, mode, symlink target, and absence of any additional
member.

Do not create `results/` records until the corresponding build, write, or
runtime action actually occurs.

`/init` must:

1. mount devtmpfs, read-only procfs, and read-only sysfs only;
2. emit exact marker `GEMINI_KEYBOARD_SHELL_20260718_Q` to tty0, `/dev/kmsg`,
   and a `/run` status file;
3. find the physical I2C5 controller by its OF node `i2c@1101c000`, report its
   actual `i2c-N` Linux adapter name and derived `N-005b` client/driver state,
   then report matrix input identity, the event node selected through sysfs/OF
   ancestry, and the relevant EINT10 count;
4. run one clearly instructed 60-second raw-event window and continue even if
   the device or events are absent; and
5. activate `tty1` and `exec` BusyBox `init` as PID 1.

The input-event helper must be retained as source and installed at
`/bin/input-event-capture`, compile as a static AArch64 ELF with warnings
treated as errors, contain no `PT_INTERP`, resolve the
keyboard dynamically rather than assuming `event0`, and perform bounded reads
for at most 60 seconds without `EVIOCGRAB`. It reports `MSC_SCAN`, `EV_KEY`,
and `EV_SYN` values and must not write an input device, GPIO, I2C register,
sysfs control, or storage.

The tracked `initramfs/inittab` source is installed as `/etc/inittab`; it must
respawn only `/bin/local-shell` on `/dev/tty1` and map Ctrl-Alt-Delete to
`/bin/busybox true`:

```text
tty1::respawn:/bin/local-shell
::ctrlaltdel:/bin/busybox true
```

`/bin/local-shell` sets `PATH=/bin`, `TERM=linux`, `HOME=/root`, and a unique Q
prompt, invokes `/bin/busybox stty sane`, and starts interactive
`/bin/busybox ash` with a real controlling terminal. Shell exit or Ctrl-D
respawns the prompt. Start with the standard kernel console keymap; no guessed
`loadkeys` data or Gemian XKB symbols belong in this gate. The physical root
shell has no password, so networking must remain unconfigured and no network
listener may start.

The manually typed `/bin/q-pass` helper emits an exact durable shell-success
marker to tty and `/dev/kmsg`; it does not reboot or change hardware.

## No-automatic-reboot policy

Q must not open `/dev/watchdog*`, run BusyBox's watchdog daemon, send a
userspace handoff ping, or install any countdown, success reset, inactivity
timer, or deadman. Retain P's proven no-IRQ `mtk-wdt` and the kernel's
boot-enabled-watchdog handling. With
`CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y` and
`CONFIG_WATCHDOG_OPEN_TIMEOUT=0`, the pinned 7.1.3 source contract must be
re-audited to confirm that the kernel keepalive worker services an inherited
running watchdog indefinitely until userspace opens it; the Q validator must
fail if that contract is not present.

The intended normal state is an indefinitely live prompt. A catastrophic
kernel stall may stop the kernel keepalives and permit hardware expiry, but Q
does not deliberately manufacture that outcome and does not promise recovery
from every severe failure. Keep `panic=0`. Probe failure, a missing keyboard,
shell exit, Ctrl-D, Ctrl-Alt-Delete, and idle time must never trigger a reset.
Recovery after acceptance is owner-selected and outside Q's pass criteria. A
typed `/bin/busybox reboot -f` is allowed only as a separately labeled,
non-gating observation: the prior exact mainline test entered an
off-like/key-gated state and required a power-key start, because the mainline
restart path does not establish Gemian's TOPRGU bit-4 bypass-key policy. See
the [timed-reboot diagnostic](../2026-07-16-timed-reboot-diagnostic/README.md).

## Explicit exclusions

Q adds no:

- CPU hotplug sweep, Cortex-A72 request, SMP stress, DVFS, idle, suspend, or
  thermal policy;
- MMC/eMMC, PWRAP, PMIC, regulator, filesystem, block-device, or rootfs access;
- raw I2C userspace access, `/dev/mem`, sysrq reset, kexec, or module loading;
- keyboard polling, guessed debounce/timing, wake, LED/backlight, hall, or
  vendor keyboard driver;
- native DRM, DSI, panel, touch, backlight, or font change;
- USB host, VBUS, Type-C, charging, mass storage, IP configuration, TCP shell,
  or other network listener.

Preserve P's existing T-PHY/MTU3/`g_ether` kernel and DT inputs and report their
registration as a negative-regression observation only. Host enumeration was
never established and is not a Q pass criterion.

## Required artifact validation

Before any device write, Q must pass all of these gates:

1. **Package:** exact P source/package provenance; explicit Q profile;
   built-in input closure; exact pinned resolved diff; no module, storage,
   raw-memory, networking-policy, or unrelated probe change.
2. **DT:** exact expected disabled-source correction plus only the three final
   status enablements; focused binding checks and `dtbs_check`; no unrelated
   node/property/reservation change.
3. **Initramfs:** exact BusyBox hash; static helper; canonical newc archive,
   root ownership, fixed modes, epoch zero and `gzip -n`; exact member allowlist;
   read-only pseudo-filesystems; Q marker; bounded input probe; supervised
   tty1; no automatic watchdog/reboot invocation, network action, CPU-online
   write, raw-memory access, block-device access, or storage action.
4. **Android v0:** Q kernel field equals the new `Image.gz` plus exact Q DTB;
   ramdisk equals exact Q initramfs; header name, Android command line,
   addresses, page size, empty second payload, zero padding, LK parser and
   arm64 placement remain exact P. Only payload-derived sizes and canonical ID
   may change.
5. **Negative mutations:** reject wrong P pins, module-valued input drivers,
   missing/wrong `consoleblank=0`, lost rotation, extra config/DT changes,
   wrong GPIO range/reset/IRQ/polarity, missing pinctrl, changed BusyBox/helper
   bytes, noncanonical archive metadata, assumed I2C adapter or event number,
   automatic watchdog/reboot/network/storage actions, incorrect TTY
   supervision, and non-derived Android header changes.
6. **Reproduction:** two clean VM builds must reproduce the resolved config,
   kernel payloads, complete DTB tree, helper, initramfs and boot image after
   normalizing only explicitly identified timestamp provenance.

Run `bash -n` and ShellCheck on shell sources, compile the event helper with the
project's warning policy, run `git diff --check`, and retain the normal package
validator output. Builders and validators have no flashing or device interface.

Completed build and write records are:

```text
results/final-build-reproduction-20260719.txt
results/boot2-write-candidate-q-20260719.txt
```

The first attended runtime result, when it occurs, should be recorded as
`results/runtime-candidate-q-attempt-1-YYYYMMDD.txt`.

## Reproducible build and installation procedure

The implementation followed this order:

1. author and validate the disabled board-DT correction as one reviewable patch;
2. add and pin the dedicated Q profile in `kernel/manifest.json`;
3. implement the tracked input helper and supervised initramfs;
4. implement exact package, DT, initramfs, Android-v0, and mutation validators;
5. build twice in the ARM64 development VM and pin every selected hash;
6. export one exact validated candidate directory; and
7. only then use the standing logical-`boot2` workflow from `AGENTS.md`.

The `boot2` writer must still resolve the live GPT label, verify target identity,
power, mounts and holders, preserve a private full backup, pad to exactly 16
MiB, sync and flush, and require a matching full-partition readback. It must
skip a matching target and never substitute `boot`, `boot3`, or a remembered
partition number. The write was completed under the standing authorization
with a fresh backup, sync/flush, and matching full-partition readback. No reboot
was performed.

## Attended runtime procedure

For one attributable Q selection:

1. Record exact installed full-partition hash and intended silver-button
   `boot2` selection.
2. Confirm the Q marker and pre-shell probe instructions are readable in normal
   landscape orientation.
3. During the bounded probe, press and release one letter, Enter, Shift, the
   physical `(4,3)` Meta/Fn-position key, and a deliberate simultaneous-key
   combination. Record scan/key/sync values and any ghost, duplicate, bounce,
   or stuck event.
4. After the bounded probe exits, confirm the Q shell prompt appears. Verify
   letters, digits, Enter, Backspace, Shift, Ctrl-C, and arrows as available.
   Run `q-pass`, `uname -a`, `dmesg | tail`, and
   `cat /proc/bus/input/devices`.
5. Exit once and confirm the prompt respawns without a reboot.
6. Leave the device idle at the prompt for at least 15 minutes, then run
   another command. The screen must remain visible and the device must not
   return to Gemian automatically.
7. Record the retained MTU3/`g_ether` registration state without making host
   enumeration a pass condition.
8. After Q has already passed or failed, choose recovery manually. If the owner
   elects to type `/bin/busybox reboot -f`, record it as a separate restart-path
   observation and expect that a power-key start may be required. Collect
   pstore and non-identifying recovery evidence only after a later boot is
   independently confirmed; neither automatic return nor a changed-cycle
   capture is a Q requirement.

Stop immediately for an I2C or IRQ storm, unexpected heat, screen loss,
panic, unexpected power-off/reset, changed recovery behavior, or any evidence
of storage probing. Do not repeat an unchanged Q unless repeatability is the
explicit hypothesis and the next capture can distinguish outcomes.

## Runtime oracle and decision table

| Observation | Interpretation and next action |
| --- | --- |
| No Q marker | Q execution is not established; reverify exact target/readback and selection before changing keyboard inputs |
| Q marker, but I2C5 or AW9523 absent/error | Config, DT, reset, parent pinctrl, or electrical probe gate failed; inspect the exact first error and do not blame the shell |
| AW9523 bound, but matrix/evdev absent | Consumer/keymap/IRQ-domain description failed; inspect the exact platform/input registration path |
| Input device present, but no raw events | Investigate GPIO87 retained pull, interrupt delivery, reset, polarity, and scan behavior; do not add guessed timing or polling without evidence |
| Raw events appear, but shell receives no characters | The hardware/input path works; isolate VT key translation, foreground console, controlling TTY, and terminal setup |
| Prompt accepts commands, but exit/Ctrl-D reboots | Supervisor/no-reboot contract failed; stop and correct initramfs only |
| Prompt survives, but display blanks before 15 minutes | Inspect effective `consoleblank=0` and longer-term loader display/backlight retention without changing keyboard inputs |
| Any unexpected automatic return to Gemian | Treat as a failure; recover pstore and boot reason before another selection |
| Raw events, typed `q-pass`, commands, shell respawn, and 15-minute idle all pass | Preserve Q as the local-serviceability baseline; promote only the observed keyboard/VT/shell behavior |

## Safety assessment

This experiment is storage-inert but not electrically read-only: the kernel
will reset and configure the AW9523 and drive matrix columns through standard
upstream drivers. The enabled nodes are therefore limited to the exact keyboard
chain and remain disabled in the reusable board DT until the named hardware
gate passes. GPIO58 reset and GPIO87 interrupt/pull behavior are explicit stop
boundaries.

Recovery remains the known-good primary Gemian boot plus private full
partition backups and the proven MediaTek restore path. Only non-primary
logical `boot2` is eligible under the existing standing authorization. No
preloader, NVRAM, GPT, primary `boot`, `boot3`, whole-device, filesystem, or
firmware write is authorized by this plan.

## Associated code

The controlled configuration fragment, next-in-series DT patch, deterministic
initramfs sources, static input-event helper, builders, exact-delta validators,
and mutation suite now exist. Historical/vendor code remains evidence, not
code to copy.

## Observations

Candidate Q was built twice from clean VM build directories. The kernel
configuration, `Image`, `Image.gz`, `System.map`, packaged disabled-source DTB,
and normalized provenance matched; the corrected final DTB, static helper,
initramfs, and Android boot image were also independently reproduced byte for
byte. Package, exact config-delta, DT-delta/schema, initramfs, Android-v0, and
negative-mutation validation passed. The first assembled derivative was
rejected before boot because archive-directory modes were 0700; the builder
and validator were corrected, the artifact was rebuilt twice, and that rejected
derivative was replaced on `boot2` without ever being selected.

The final raw boot image is 6,862,848 bytes with SHA-256
`66cec945eff5c8d34acbf61382d267533e4ac6894aac19093904dd9008da27c3`.
The live GPT uniquely resolved logical `boot2` to `/dev/mmcblk0p30`; the exact
16-MiB padded image and full readback both have SHA-256
`ccf8d80f40b334dd3900d72901b1fa6ccdb9bf796a81c72b97bf680f2080508e`.
The device remained in Gemian on `/dev/mmcblk0p29`; the write operation itself
did not reboot it. On the later intended Q selection, the owner reported that Q
did not provide a working text console and that no deeper behavior could be
identified. No exact Q marker, AW9523 binding line, matrix input device, event,
shell prompt, supervisor behavior, or idle-time result was observed. A
read-only check after recovery found no retained pstore file or Q-specific
console/panic/watchdog evidence. See the
[runtime record](results/runtime-candidate-q-attempt-1-20260719.txt).

## Analysis

The upstream AW9523 register protocol still matches the observed chip contract,
and generic matrix-keypad still represents the source-derived scan topology.
Q nevertheless made the unproven GPIO87/EINT10 path boot-critical. The latest
independent bsg100 Gemini evidence instead obtained working keyboard input with
the AW9523 parent interrupt absent and `matrix_keypad` scanning every 20 ms.
Its hardware-tested result is cross-device evidence, not proof on this unit,
but it supplies a decision-changing next test: retain the upstream AW9523
silicon driver and the GPIO87/EINT10 pinmux while removing its parent-IRQ
consumer from the active path and adding generic matrix polling. The absence of a Q marker or retained pstore does not prove an
IRQ hang; loader selection, display/TTY behavior, reset/probe failure, and an
early stall remain alternative explanations.

## Conclusion

`Rejected as a runtime candidate.` Q did not meet its first visible-console
gate, and none of its keyboard or shell gates was established. No keyboard or
shell support claim and no support-matrix advancement follows.

## Follow-up

Do not repeat unchanged Q. Candidate U was the next available identifier because
R is retired and S/T remain reserved. U was independently built twice with
matching validated outputs, then installed to live-resolved logical `boot2`
with a matching full-partition readback. Its first intended selection also
failed the visible-console gate: the screen and console stayed dark, no marker
was observed, and no automatic reboot occurred. The device was later reachable
in Gemian with a changed boot ID, but authenticated post-return pstore was
empty. U therefore establishes no console, kernel, `/init`, AW9523, keyboard,
or shell behavior and must not be repeated unchanged. Preserve the U
[build reproduction](../2026-07-19-keyboard-polling-diagnostic/results/final-build-reproduction-20260719.txt)
and [write/readback](../2026-07-19-keyboard-polling-diagnostic/results/boot2-write-candidate-u-20260719.txt)
records, plus its [runtime result](../2026-07-19-keyboard-polling-diagnostic/results/runtime-candidate-u-attempt-1-20260719.txt).
The next candidate needs a durable observation path that can distinguish early
entry from a display-only failure. Promote only behavior directly demonstrated
on this named device.
