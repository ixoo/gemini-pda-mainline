# Focused digit/chord reader

This implements the collection part of the [cutoff audit](CUTOFF_AUDIT.md).
It is an offline preparation, not a new device admission or a replacement for
the 20-case regression. The current capture binding and deployed helper remain
unchanged.

The existing [reader](keyboard-observe.c) now accepts a separate `--diagnose`
mode. It reuses device identity, exclusive-console prerequisites, signal cleanup,
raw input and restoration code. `--capture` retains the v1 sequence, output
framing, ten-second windows and 64-event ceiling. The existing classifier is
unchanged and must not be used to certify diagnostic output.

The diagnostic has a two-second no-input preflight and two fifteen-second
windows. The first asks for 1 alone; the second asks for the original
Shift/Fn/1 sequence followed by unmodified A. The fifteen-second window is a
proposed usability allowance, not a measured owner completion time. Every
window still requires released keys at its end. Input queued at the deadline
is an explicit incomplete outcome.

Before changing console settings, `EVIOCGREP` obtains the existing delay and
period. A zero period, out-of-range values or an unavailable query refuse. No repeat
setting is written. The planning allowance is
`64 + 2 * ceil(15000 / period_ms)` events: room for sixteen physical edges,
their scan/synchronization records, up to eight initial repeats and paired
periodic repeat/synchronization records. It deliberately ignores the initial
delay when estimating capacity. A value exceeding the absolute 1,024-event cap
refuses before the prompt. This is a capacity check for the requested sequence,
not a guarantee about arbitrary input or scheduler timing; an actual overflow
still stops collection and preserves its first excess event.

Diagnostic lines beginning `event` or `overflow` contain four decimal fields:
elapsed milliseconds within this window, event type, code and value. Elapsed
time is a monotonic reader timestamp, not the kernel event's generation time.
Window summaries record actual elapsed time. Repeats remain raw value-2 records;
they are not converted into additional physical presses. The failure footer
names the stop branch and console-restoration result. VT bytes retain the
existing `tty hex=` framing and 128-byte per-window ceiling. The compact event
format keeps the bounded two-window output below the existing 98,304-byte
monitor file cap, including an overflow record and framing.

Exit zero means only that collection and restoration completed. Empty windows,
wrong keys, malformed frames or wrong VT bytes do not establish a diagnostic
pass. The [offline analyzer](analyze-focused.py) checks complete framing,
timestamps, counters, balanced physical edges and repeat/synchronization pairs.
It compares input coordinates/edges and VT bytes separately. It always reports
`hardware_claim=false` and `session_receipt_verified=false`: stream contents
cannot establish runtime attribution or the owner's physical actions.

Before live use, bind an exact package to a fresh monitored session, including prompt ownership,
reader exclusion, logging, the revised time budget and owner participation.
The old monitor invocation selects `--capture`; it cannot launch this mode
unchanged. Do not repurpose the consumed retry receipt or rewrite historical
capture evidence.

Build the separate reader package through the existing managed userspace lane:

```sh
python3 experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/buildbox_userspace.py --branch main --keyboard-focused
```

The builder requires clean pushed inputs, produces two matching static ARM64
binaries, runs [PTY/input fixtures](test-focused.py), and exports source,
licenses and exact provenance. The fixtures cover a long repeat prefix followed
by the remaining chord edges, the first overflow event, dropped input, short
read, signal restoration, held keys, repeat-query/capacity refusals, legacy
framing and both full production-duration windows. Simulated input cannot prove
the physical keyboard, matrix rollover or console mapping.

The managed Buildbox build at `f2b43fc044928f37ba9a30a7b169e79556a1871d`
passed all eleven ARM64 fixtures, including both full fifteen-second windows.
Its two stripped static binaries match at 67,280 bytes. The validated package
identity is
`903a846668b605bf076f234864e0b0820543c9aac33b2bfb170bef63fa5bd3df`;
the reader SHA-256 is
`41d7eb823cee071d36d71288bb4d00a96485b5a24ca37c3ccb035a063f6ab0ab`.
The fixture-results SHA-256 is
`90266f9b3e4c66f8624f669f83e568838a0ddb164afde5ba3a47a6038549da46`.
Only the validated package was fetched; the build stage was removed normally.

Local routing, Python syntax, shell syntax/ShellCheck and the unchanged v1
packet tests pass. The [analyzer fixtures](test-analyze-focused.py) distinguish
repeat events from physical presses, preserve independent input/VT mismatches,
and refuse truncated, overflowing, malformed or inconsistent records. These
are synthetic stream checks, separate from the compiled ARM64 reader fixtures.
No kernel build, new capture, live query or device transition was performed.
