# First-step cutoff audit

Offline analysis at parent `2b829c9c`, 2026-09-09. This changes the next
diagnostic design, not the keyboard support claim or any live admission.
The [Space-start record](SPACE_START.md) owns the session chronology.

## Evidence

The preserved observer stdout has SHA-256
`34e53e29f83cc4f610bf0f430656112a6e95f115d600d0c4351e86baf832e9b1`.
It contains exactly 64 event records:

| Records | Meaning |
| --- | --- |
| 3 | Scan 30, left Shift press (42), synchronization |
| 3 | Scan 35, Fn press (125), synchronization |
| 58 | 29 Fn repeat events, each followed by synchronization with value 1 |

No digit, release or VT byte was recorded. The owner reported completing the
sequence. The monitor reaped exit 2 at 10,622 ms, with no signal, identity loss
or stderr. The observer reported console restoration. Its two-second idle
preflight precedes the ten-second step; monitor elapsed time is not a key-event
timestamp and cannot date the owner's actions.

The inspected [observer](keyboard-observe.c) has SHA-256
`f46eff614c6cfbabc2864148560636e7d26d9dfd693908d21f3284ae45c1bd8c`.
Its `window()` reads a whole input event before testing `++events > EVENT_LIMIT`.
On event 65 it returns without printing that event. Thus the 64-line prefix is
consistent with overflow, but neither identifies event 65 nor proves that all
later physical actions were absent from the input path. The generic failure
footer does not distinguish overflow from a read, poll or other failure.
Do not claim that event 65 was a repeat or that overflow is a directly reported
failure branch.

There is a separate protocol limitation. Running the current
[parser](classify.py) on the retained stdout, with the recorded event basename
and minor, rejects its first repeat as `repeat-or-malformed-key`. This was a
parser-only check, not a successful admission/receipt classification. Increasing
the event ceiling would still leave this trace inconclusive under v1. Repeated
Fn presses must not be rewritten as physical edges to obtain a pass.

## Next distinguishing observation

Use a separate focused diagnostic before attempting all 20 regression cases:
first tap and release 1 alone, then perform the original Shift/Fn/1 sequence
and its final unmodified A. Keep the kernel, keymap and input repeat settings
unchanged so the observation can distinguish missing input from VT translation
and collection cutoff. Preserve the v1 regression and its negative evidence.

The diagnostic needs the following concrete differences in the existing reader:

- Report the exact stop branch and the first event exceeding capacity. Record
  elapsed time at window boundaries and for key events, so a cutoff can be
  related to the prompt without inferring timing from the monitor lifetime.
- Retain repeat and synchronization records as diagnostic evidence, separately
  from physical press/release edges. A repeat is not a new press; dropped input,
  malformed frames, unfinished releases and collection limits remain explicit
  inconclusive outcomes.
- Size collection for a full bounded window using an observed read-only repeat
  delay/period, with room for the requested edges and synchronization records.
  The present capture has no event timestamps or repeat period, so it cannot
  justify a numeric rate or a guaranteed replacement ceiling. Keep an absolute
  byte/event/time cap and report any overflow without assigning a hardware cause.

If 1 alone is absent, investigate its matrix/input path. If it is present alone
but absent in a fully observed chord, investigate chord/rollover behavior. If
all chord edges are present but VT output differs, investigate the map/console
path. If both pass, resume regression preparation with the demonstrated timing
and repeat behavior; this two-case diagnostic cannot certify the 20-case suite.

No reader change, build, device query, new capture, boot or recovery was performed
for this audit. A future capture still requires a fresh bounded session and
owner participation. Raw captures remain private; only numeric counts, source
identities and reviewed conclusions are published here.

The later [focused reader implementation](FOCUSED_DIAGNOSTIC.md) addresses
collection separately from live admission and regression acceptance.
