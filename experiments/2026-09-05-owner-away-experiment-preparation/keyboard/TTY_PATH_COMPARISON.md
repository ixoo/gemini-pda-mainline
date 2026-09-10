# Console input path comparison after the plain-1 cutoff

The [attended capture](focused-key1-result.json) recorded a correct key-1 press
followed by 160 console-input bytes of `6e`. The earlier
[Space observation](focused-successor-readiness-result.json) also returned `6e`.
These observations do not identify where the character changes or multiplies.
The reader stopped before key release; it cannot establish a stuck key.

## Gemian reference

The [fresh reference](gemian-console-reference.json) is from Gemian 3.18.41+
boot `38a5040d-c5f7-4deb-9b2a-5e7be87042c3`. Mainline USB was absent; the normal
Gemian LAN endpoint confirmed the changed boot. This investigation issued no
restart command.

Read-only ioctls on tty1 found Unicode keyboard mode and N_TTY line discipline.
Table 0 maps keycode 2 to `0x0031` and keycode 57 to `0x0020`. Shift maps 1 to
`!`. The sampled Fn/keycode-125 entries are holes, unlike our explicit VT AltGr
policy; Gemian's desktop Fn behavior belongs to the retained XKB layout.
See the [durable keyboard comparison](../../../docs/hardware/keyboard.md).

A newly allocated private PTY, set to raw nonblocking input with VMIN=0 and
VTIME=0, returned exactly `31201b5b5b4161` after those seven bytes were written
to its master. No further input was ready. Only that new PTY's termios changed;
physical console settings and input were untouched. This proves a reference
PTY roundtrip, not physical-key or VT-translation correctness.

## Kernel source comparison

The retained public Gemian source revision is
`59e00a9144d782e148332009a835b99c43382467`. Its `k_self()` calls
`k_unicode(conv_8bit_to_uni(value), up_flag)`; releases do not emit characters.
Its `put_queue()` inserts one character into the tty flip buffer and schedules
the buffer. Linux 7.1.3 retains this translation model, using
`tty_flip_buffer_push()` after insertion. Function strings use a bulk insertion
in the newer source instead of Gemian's character loop. No project format-patch
modifies the tty sources examined here.

The raw N_TTY read path differs: Gemian copies queued bytes directly to userspace;
7.1.3 copies them into the tty core's intermediate buffer, which `copy_to_iter()`
then exports. Both advance the queue by the copied byte count. Source inspection
found no demonstrated reason to replace either implementation.

| Source | Gemian SHA-256 | Linux 7.1.3 SHA-256 |
| --- | --- | --- |
| drivers/tty/vt/keyboard.c | 1876417aadbc02f2199be931d8002a3e92011e2f1ae552c3c0a5d05763d4e4be | cd0ca2d6183ebad4bbd4aacfb3326d010d0cafa7bdbd854fd30eaa80d7c35799 |
| drivers/tty/n_tty.c | ee1597ce55ef957cc648f5301c8edbfe00e7b7b7a9736575afb7d78733cdc277 | 5f33bf3bca249d246c2bbf85f7852e77dd65dc14e57a135a83fa03adb9dda0a9 |
| drivers/tty/tty_io.c | 55ac5178ed056a20c60b472426fd1a6ead0c03c7bcdb6c8da82c2917c90e9105 | 2c307ceaf3f39bd15d6948818ab605f15ad62c5533dadbf762542348dc899881 |

These are inspected source identities, not a new runtime instruction trace.

## Next discriminating observation

Use a fresh SSH-owned PTY on an explicitly identified mainline boot, set only
that PTY raw, and exchange the same seven bytes. No keyboard press, physical VT
write, new kernel, or larger keyboard byte limit is needed. Preserve the command,
transmitted bytes, stdout, stderr and exit status. Bound the exchange to ten
seconds and refuse absent USB routing or a boot/binary mismatch.

An exact roundtrip would show the common PTY/N_TTY path works for that sample;
it would leave keyboard translation and the VT-specific path under suspicion.
Wrong or multiplied bytes would instead justify examining the common read path
before changing the matrix driver. A transport or PTY-allocation failure is
inconclusive. The prepared mainline attempt stopped at the local route check
before any device connection, so neither branch is established yet.


## Mainline roundtrip result

After the owner selected boot2, boot
`f2999a36-edfe-42ea-bca4-1abf8db1a7f9` passed the pinned kernel, init, helper,
and CPU0–7 identity checks. The [result](mainline-pty-reference.json) records two
fresh SSH-owned PTY exchanges. Both returned exactly `31201b5b5b4161`, with
normal exit and no stderr, in less than one second. The first used raw mode
with VMIN=1 and seven one-byte BusyBox `dd` reads. The second used VMIN=0,
VTIME=0 and BusyBox ash's bounded seven-byte read. Each restored its own PTY
settings before exit; neither accessed the physical VT.

A separate read-only physical-console query verified all eight keymap tables,
1,024 payload entries, 2,048 kernel entries, unused entries/tables, and Unicode
mode. tty1 was foreground with line discipline 0 and ordinary canonical/echo
settings. These checks changed no physical-console state.

The shared tty path works for these samples, including the zero-minimum input
setting. This leaves the physical VT translation path and the observation
binary as distinctions requiring a further measurement. The tests used BusyBox,
not the musl-linked keyboard reader, and did not reproduce a physical key press.
No keyboard-driver correction or complete keyboard-support claim follows yet.


## Independent physical-console comparison

The [comparison](independent-reader-comparison.json) uses the same new boot.
The owner missed the first fifteen-second BusyBox window. A successor kept the
prompt available for ninety seconds and completed in 5.289 seconds with byte
`31`, using the same raw termios bit changes as `cfmakeraw()` and VMIN=0/VTIME=0.
It restored settings. This is one physical-console byte, not a full event or
release trace; the shell reader's descriptor did not use O_NONBLOCK.

The existing validated musl Space helper then received `31313120` (`111 `).
Its first event was the Space scan, followed by the preserved Space press and
sync; it cancelled because the prefix was not Space. The owner confirms the
Space action. The prefix therefore predates the observed Space sequence, which
suggests queued input rather than a Space-to-1 keymap error. Neither result
proves the origin of the preceding digit bytes.

## Pending flip-buffer hypothesis and diagnostic

In the inspected 7.1.3 source, `tty_port_default_receive_buf()` returns zero
without `port->itty` or an available line discipline. `flush_to_ldisc()` then
leaves the bytes queued. Initial tty setup attaches the terminal and opens its
line discipline without restarting this work; a later keyboard character's
`tty_flip_buffer_push()` schedules it again. A read-side empty result or quiet
poll therefore need not describe a previously stalled flip buffer. This is a
source-derived explanation to test. Gemian also has this general buffering
model; ordinary persistent console ownership differs from our diagnostic's
requirement that all physical-console descriptors be closed between readers.

Only `space-ready --drain-console` now requests the existing N_TTY discipline
again after verifying it with TIOCGETD. The pinned kernel's same-discipline
TIOCSETD branch does not close, replace or flush the discipline, but restarts
its buffer worker. The helper then polls for up to one second and uses its
existing 4,096-byte preservation limit and termios restoration. It refuses a
non-N_TTY discipline or failed ioctl. Normal Space readiness and state-only
queries remain unchanged pending evidence.

The added PTY fixtures exercise the real no-op ioctl, inject bytes only after
that call, and check wrong-discipline and failed-set refusals. Injection models
a deferred source; it is not a hardware reproduction of a closed VT. A build
and an attributable device observation are still required before concluding
that requeueing resolves the recorded backlog. No keyboard-driver or kernel
patch is justified by these observations alone.


## Closed-console comparison result and startup correction

The [controlled comparison](console-requeue-comparison.json) used the same
mainline boot. With no reader running, the owner tapped and released unshifted
A once. The old drain then reported zero bytes and restored termios. Without
another keypress, the revised drain reselected N_TTY and recovered exactly `61`,
then reported empty and restored termios. Both commands exited successfully.
This demonstrates input invisible to the old empty check becoming available
when the buffer worker is restarted, consistent with the inspected closed-VT
path. It does not establish where the earlier repeated `n`/`1` bytes originated.

Normal Space readiness now performs that same bounded preservation step before
its prompt, keeping the descriptor open through the fresh Space press/release.
It records every preflight byte, refuses concurrent evdev input or held keys,
and preserves the existing fresh-event and restoration requirements. No flush,
keymap change or keyboard-driver change is involved. The added PTY case releases
a queued prefix during preflight and then requires a new Space sequence to pass.
The physical startup and full keyboard sequence still require validation.
