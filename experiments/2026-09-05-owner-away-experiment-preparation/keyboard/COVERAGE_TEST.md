# Twenty-step keyboard coverage preparation

State: attended capture completed. Build and delivery identities are recorded
in [coverage-preparation-result.json](coverage-preparation-result.json); the
[attended result](coverage-result.json) owns the runtime evidence.

The focused hardware session showed that ordinary held-modifier repeats can
exceed the original 64-event ceiling before a chord finishes. The reader's
`--coverage` mode uses the same repeat query, 1024-event capacity, timestamped
records, loss detection and console restoration as `--diagnose`, with the
existing twenty instructions from [protocol.json](protocol.json). Each step
lasts ten seconds after a two-second idle preflight: 202 seconds total.
The historical `--capture` interface and its contract remain unchanged.

The coverage monitor executes only `/a53-keyboard-coverage/keyboard-observe`
with `--coverage`, retaining the existing full-session 209-second TERM trigger,
213-second KILL trigger and 215-second cleanup boundary. Its once-only attempt
lives under that distinct RAM directory. A one-MiB file ceiling accommodates
20 windows of 1024 timestamped event lines and 128 VT bytes per window.
No partition installation or new kernel boot is needed for this RAM helper.

Build the committed inputs with the existing userspace Buildbox entry and
`--branch main --keyboard-coverage`. The package must pass the focused
regressions and [test-coverage.py](test-coverage.py), which checks the exact
monitor entry and all twenty production-duration reader windows using a PTY
and synthetic evdev, including modifier repeats beyond the old ceiling.
These fixtures establish helper behavior, not hardware support.

For the attended run, use a fresh delivery directory, verify live boot,
helper/map identities, console exclusivity and logger separation, preserve
existing evidence, and use the already validated console-drain/Space-start
sequence. Do not start the ten-second windows before owner readiness.
Follow the on-screen instructions once, tap the requested non-modifier keys
briefly, release all keys, and wait for the next numbered prompt.

Analyze the private capture with `analyze-focused.py --coverage CAPTURE`.
Physical edges/scans and exact VT bytes are checked separately. Modifier
repeat frames are preserved and validated; repeated character/function bytes
remain an explicit VT mismatch for trace review. The analyzer does not certify
the live identity, map, logger or owner witnesses. A complete attributable
session must record those separately before any hardware-support claim.

## Attended result

All twenty ten-second windows completed and the monitor reaped the reader
normally at 202.348 seconds, with no signals, lost identity or late cleanup.
The corrected startup found zero queued bytes and accepted a fresh Space press
and release. Export preserved all seven result files; the saved observer stream
exactly matches the forwarded capture. Same-boot CPU, map, binding and console
checks passed before and after. The owner confirmed all prompts remained
readable and the keyboard responsive.

All observed key presses and repeats produced the expected console bytes:
F1–F10, Home/End/Page Up/Page Down, both Shift keys, Ctrl+A, Alt+A, Fn release,
and `help` followed by Enter. The 361 repeat events remain in private evidence.
Nineteen instructed physical sequences matched exactly. Step 17 recorded A
released before Ctrl; the requested Ctrl-first release while A remained down
was therefore not exercised. Its Ctrl+A and subsequent plain A translated
correctly for the observed ordering. The owner was unsure which key was
released first, so the requested ordering check remains unresolved. This
distinction is retained in the result.

The strict single-tap byte oracle matches nine cases; the other eleven include
legitimate character/function repeats. A bounded review reconstructed output
from each recorded press/repeat and its held modifiers, using the verified map
and protocol function strings, and matched every case. This is an observed
translation result, not a claim that the original twenty single-tap sequences
all passed. The owner subsequently accepted Ctrl+A as sufficient for this
milestone and explicitly requested moving on without another keyboard test. The recorded
release order remains unchanged; it is no longer a scheduling gate. Wider
coverage and reliability remain separately scoped work.
