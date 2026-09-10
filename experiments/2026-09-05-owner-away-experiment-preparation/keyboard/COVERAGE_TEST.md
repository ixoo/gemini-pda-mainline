# Twenty-step keyboard coverage preparation

State: implementation prepared; Buildbox validation and live admission pending.

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
