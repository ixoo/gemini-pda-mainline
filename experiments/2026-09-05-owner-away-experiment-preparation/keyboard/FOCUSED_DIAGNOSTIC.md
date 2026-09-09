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
pass. Before live use, finish the repeat-aware evidence interpretation and
bind an exact package to a fresh monitored session, including prompt ownership,
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

Local routing, Python syntax, shell syntax/ShellCheck and the unchanged v1
packet tests pass. ARM64 compilation and fixture execution are pending at this
implementation checkpoint. No kernel build or device action is required for
this userspace preparation.
