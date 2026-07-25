# Gemini keyboard polling diagnostic (Candidate U)

## Status

Candidate U was independently built twice with matching validated outputs and
installed to the live-resolved logical `boot2` with a matching full-partition
readback. Its first intended selection failed the visible-console gate: the
screen was black, the console stayed dark, and no automatic reboot occurred.
No U marker or other text was observed. The device was later reachable in
Gemian with a changed boot ID; its non-identifying boot fields report
`power_key`/`keypad`, corroborating a power-key-class recovery rather than an
automatic watchdog return. An authenticated read-only post-return capture
found an empty pstore, so kernel and `/init` entry and every keyboard or shell
gate remain unestablished. Do not repeat unchanged U.

See the exact [build and reproduction
record](results/final-build-reproduction-20260719.txt) and guarded [`boot2`
write/readback record](results/boot2-write-candidate-u-20260719.txt), plus the
[first runtime record](results/runtime-candidate-u-attempt-1-20260719.txt).

A post-runtime exact-DTB comparison found a larger packaging regression:
installed U was transformed from the package DTB rather than exact P. It
dropped P's `/chosen/framebuffer@7dfb0000` node and both retained display
clocks, and it reintroduced SPI137 falling-edge while exact P has no watchdog
`interrupts` property. The missing simplefb node explains why U had no
configured loader-framebuffer console if it reached Linux, but does not prove
selection or kernel entry. U also did not retain P's proven no-IRQ
watchdog-registration foundation. U deliberately did not open the watchdog in
userspace, so the IRQ regression alone does not explain the lack of automatic
reset. Both boundaries must be corrected before another boot. See the
[DTB regression audit](results/u-watchdog-dtb-regression-audit-20260719.txt).

Candidate Q did not produce a working text console. No exact marker, input
event, driver-binding result, or other deeper gate was visible, and the
known-good recovery boot exposed no pstore record from the attempt. Q must not
be repeated unchanged.

## Hypothesis

Candidate U tests whether the upstream AW9523 GPIO provider and generic
`gpio-matrix-keypad` can expose the Gemini keyboard when the matrix is scanned
every 20 ms and neither the AW9523 parent interrupt nor per-row GPIO interrupts
are required.

The hypothesis is motivated by two independent observations:

- the latest `bsg100/gemini-linux` main branch at
  `60f5f4ac777a0aeccc89b5d3a4f8cd1f1ebe57b3` has same-board physical typing
  evidence for a 20 ms polled matrix (keyboard commit `6bd4d5726706`, followed
  by keyboard/USB coexistence commit `aff681d3c727`); and
- local MT6797 evidence says pin GPIO87 maps to raw EINT10, while Q encoded
  raw EINT87 in the interrupt-parent domain. Thus Q's active parent IRQ tuple
  was misaddressed even though its pinmux selected the EINT10 function.

The external tree is evidence, not vendored code. U retains Linux 7.1.3's
upstream `pinctrl-aw9523` driver and its active-high reset contract. The external
v6.6 custom AW9523 driver and legacy matrix-keypad patch are not copied.
The exact latest-tree and debounce-use findings are preserved in the
[related-project audit](results/bsg100-latest-keyboard-audit-20260719.txt).

## Attributable U delta

Patch 0083 adds an optional generic `poll-interval` property to the Linux 7.1.3
`gpio-matrix-keypad` binding. Patch 0084 implements that policy in the driver:
with the property present, it skips row IRQ conversion, request,
enable/disable, and wake handling, and reschedules its existing full-matrix
scan.

The retained board source remains safe by default: I2C5, AW9523, and the matrix
consumer are disabled. It now describes GPIO87 correctly as raw EINT10 for any
future IRQ-mode experiment. Candidate-only DT packaging then makes this exact
transform:

- enable I2C5, AW9523, and `keyboard-matrix`;
- remove AW9523 `interrupt-parent`, `interrupts`, `interrupt-controller`, and
  `#interrupt-cells`;
- retain the GPIO87/EINT10 input pinmux state but give it no active consumer;
- retain GPIO58 active-high reset and the upstream AW9523 compatible;
- set I2C5 to 400 kHz;
- set `poll-interval = <20>` and `col-scan-delay-us = <2>`, with no separate
  debounce property in polling mode; and
- retain `gpio-activelow` plus `drive-inactive-cols`, because local vendor
  protocol evidence says selected columns are driven low, inactive columns are
  driven high, and low rows are pressed.

The 400 kHz transport rate, 20 ms poll, and 2 us column delay match the
same-board working polling description. That DT also carries a 5 ms debounce
property, but its polling branch never consumes `debounce_ms`; U omits the
inert property so the attributable contract matches behavior. An 8x7 full
scan over an I2C expander should not consume most of a 20 ms period.

## Console and observation design

U preserves Candidate P's exact known-good framebuffer-console configuration,
rotation, `maxcpus=1`, watchdog policy, and storage/network exclusions. It adds
`consoleblank=0` as Q did.

Unlike Q, PID 1 does not run the 60-second input probe before starting BusyBox
init. BusyBox immediately supervises an interactive shell on tty1 and starts
the bounded probe as an independent `once` action. Keyboard probe failure
therefore cannot postpone shell creation. The unique marker is:

`GEMINI_KEYBOARD_POLLING_20260719_U`

The probe records I2C5 discovery, AW9523 binding, matrix-platform binding,
input-event discovery, EINT10/EINT87 observations, waits at most 20 seconds
for a late input node, and then opens a bounded 60-second raw event window when
one exists. It writes to `/run/u-status`, kmsg, tty0, `/dev/console`, and
ttyS0 when present. It does not grab the input device, access storage, configure
networking, or reboot.

## Decision table for the first boot

| Observation | Interpretation | Next action |
| --- | --- | --- |
| `GEMINI-U#` appears and typing works | Console, upstream AW9523, generic polling, mapping, and tty path pass | Run `/bin/u-pass`; preserve exact log and then test key coverage separately |
| Shell appears but typing does not | Console is good; inspect `/run/u-status` to distinguish I2C/AW/matrix/event gates | Change only the first failed gate |
| Marker appears but no shell | PID1/BusyBox tty supervision failed independently of keyboard | Repair console/initramfs only; do not change keyboard DT |
| No U marker is visible | Failure precedes the first visible userspace gate | Recover pstore after a confirmed boot cycle before another candidate |

No identical U derivative should be booted unless repeatability is the explicit
hypothesis and a new independent measurement can change the decision.

The first intended U selection matched the final row. Post-return pstore was
empty, so the next candidate must add a durable independent observation path.
It must also restore the exact no-IRQ watchdog DT and take bounded userspace
ownership; correcting build-time or driver-lifecycle defects alone is not a
reason to spend another device boot.

## Safety boundary

Building and validating U performed no hardware write. Its later installation
used the repository's standing, guarded authorization for the live
GPT-resolved logical `boot2`: exact identity/size/writable/power checks, a
mode-0600 full backup, exact-size zero padding, write/sync/flush, and a matching
full-partition readback. No other partition was targeted and the device was not
rebooted.

## Validation and installation

Completed static/build gates:

- all 86 pinned series entries applied to pristine Linux 7.1.3, and strict
  checkpatch reported no errors, warnings, or checks for patches 0083–0085;
- two independent AArch64 builds produced byte-identical `Image`, `Image.gz`,
  `System.map`, resolved config, package DTB, series, and manifest inputs;
- the final boot image is
  `aa163793df1f6a82eb18ee71c73c7e8a07696b4fd2f866e34ec9e2703a1905fe`,
  the transformed DTB is
  `e541c9dffac15de859a876e80409eec4591d36319646845cb25c6eecb8ddf5b1`,
  and the initramfs is
  `d05b29071cc8d2be8795c246b527ed315591a2e8e692cf6d050d4c7915783f4f`;
- focused board/I2C/pinctrl/AW9523/matrix schema validation exited zero with
  empty output. The package and transformed DTBs had identical normalized
  full-schema output consisting only of the six pre-existing disabled MT6797
  SPI-node diagnostics;
- exact DT, canonical initramfs, static-helper, Android-v0/LK, size, checksum,
  safety-policy, and mutation-rejection gates passed; and
- the pinned watchdog audit confirmed the boot-time keepalive policy remains
  built in while Candidate U deliberately opens no userspace watchdog.

Completed installation gates:

- logical `boot2` was resolved uniquely from the live GPT as
  `/dev/mmcblk0p30`, verified unmounted, writable, inactive, and holder-free
  while the device was on AC with a full battery;
- its exact previous 16 MiB contents were preserved with mode 0600 and checksum
  `ccf8d80f40b334dd3900d72901b1fa6ccdb9bf796a81c72b97bf680f2080508e`;
- the padded U image was written, synced, and block-device-flushed; and
- the complete device checksum and an independent local 16 MiB readback both
  matched
  `7c57176f3fb5e8e7c9619f038cf09517ca85ee0323ff48ff8c382b60b2794c6e`
  byte for byte.

The first runtime adds one negative visible observation only: the exact U image
produced a black screen with no visible marker or working console and did not
automatically return to Gemian. A later changed Gemian boot ID and
`power_key`/`keypad` fields establish a separate power-key-class recovery. Empty
pstore does not establish LK selection, kernel or `/init` entry,
framebuffer/VT output, a shell, I2C5 transfer, AW9523 probe/reset, matrix
registration, key events, typing, polling timing, CPU0 execution, or watchdog
behavior. The post-runtime DTB audit further shows that U lost exact P's
simplefb/handoff properties and reintroduced the optional watchdog IRQ. The
missing simplefb node accounts for the absent configured console path if U
entered Linux, while the deeper boot boundary remains unknown. Candidate U is
rejected and must not be repeated unchanged.
