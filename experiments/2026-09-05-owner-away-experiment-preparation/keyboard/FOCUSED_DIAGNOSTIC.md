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
The legacy monitor invocation selects `--capture`. The separate focused build
described below selects `--diagnose`. Do not repurpose the consumed retry receipt or rewrite historical
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

## Focused monitor preparation

`KEYBOARD_MONITOR_FOCUSED=1` selects the existing supervisor's focused variant.
It uses the fixed parent `/a53-keyboard-focused` and executes only its delivered
`keyboard-observe --diagnose eventN 13 MINOR`. There is no runtime path, command
or mode override. The separate `KEYBOARD_MONITOR_ENABLED=1` switch is still
required; selecting a focused build alone does not enable its target entry.

This variant retains the existing exclusive `keyboard-attempt` claim, file
limits, direct-child identity, signal handling and disconnect preservation.
The complete expected observation is 32 seconds. Its planned TERM trigger is
39 seconds (hard bound 40), KILL trigger 43 (hard bound 44), and reap/exit bound
45 seconds. Early cancellation or transport failure still uses the existing
four-second termination grace and one-second reap allowance. A forced stop or
missed bound remains inconclusive. This changes neither the legacy 215-second
monitor nor its frozen runtime evidence.

The `--keyboard-focused` package now builds both the reader and this monitor,
with matching replicas and both compilation header inventories. The
[focused monitor tests](test-focused-monitor.py) check the production entry's
exact fixed path/arguments with a harmless substitute, then exercise the full
32-second observation boundary and forced cleanup of a child that ignores
TERM. The existing thirteen scaled supervisor fixtures also run for this
variant. These tests use no physical input device or PDA connection.

Both the thirteen focused and thirteen legacy host fixtures pass. The composed
Buildbox package at `11f830c68866044cd7b86dd95e743adfa4997345` passed the eleven
reader cases, thirteen scaled ARM64 supervisor cases, exact focused-entry
argument/once-only check, and the full observation/forced-cleanup check. The
latter observed the 32-second marker and verified TERM within 39–40 seconds,
KILL within 43–44 seconds and child reaping by 45 seconds, with no identity
loss or late flag. These are fixture bounds, not device timing measurements.

The validated package identity is
`0c08662aa4c52120820e55b6f036b8b1e93a8abe489f231b2b4db8d88cba1f76`.
The 66,672-byte supervisor has SHA-256
`52310c8189f3603f2a2ac3e5729a1be45daf9576b99c25e47a1ef10b598b3971`.
The reader remains byte-identical to the earlier validated reader above.
Both binaries have matching replicas. The combined fixture transcript has
SHA-256 `33dcfd0ecbe62b6639251553b0c0f8a14a4990967945a635804af17d97153b4b`.
The fetched source inputs match the reviewed files. Only the validated package
was transferred; no kernel or device action occurred.

A fresh host-side delivery/admission binding, combined logger budget and owner readiness
are still required before any device execution; the old capture adapter does
not select this variant.

## Host plan and remaining runtime facts

[focused-session.py](focused-session.py) freezes four private command files and
their digests, source identities, exact package and expected boot into a plan.
It has no transport or execution action. It reuses the existing live identity,
RAM, map, logger, ancestry, capability and reader guards. The two delivery
steps install the supervisor/notices, then reader/GPL notice. A UUID readiness
record binds the completed delivery; capture rechecks every delivered file and
the record before invoking the focused supervisor. Existing files, symlinks,
mounted delivery paths, partial delivery and a consumed attempt refuse reuse.

The actual prepared commands occupy 197,234 bytes for delivery A and 124,934
for B, each below the existing 262,144-byte command cap. Capture is 14,475 bytes
and export 4,415 bytes. Their host limits are 30, 30, 60 and 30 seconds.
Capture starts only while the restarted logger is younger than 120 seconds.
Allowing the full 60-second capture host limit, 30-second export and 30-second
independent seal leaves completion before logger age 240 seconds, within its
unchanged 600-second/2-MiB envelope. The Space wait precedes logger startup.
These are proposed phase bounds, not observed transfer timing or log coverage.

The [disconnect source review](focused-disconnect-source-review.json) compared
the retained probe revision with the focused variant on Buildbox using the
installed target GCC preprocessor and headers. Both scaled probe configurations
produced identical 120,596-byte output with SHA-256
`adc56233836aa73dc5b75a4973cda7ef45c25413a267ed605c06bf6477817efe`.
This preserves the historical probe's relevance to the unchanged scaled engine;
it is neither binary equivalence nor a focused production device proof. The
focused production argument and deadline fixtures remain separate evidence.

The prerequisite verifier now accepts an explicit historical monitor source
pin. Its default still requires the current source. The planner verifies the
historical pin against its Git revision and validated package before rechecking
all seven raw disconnect evidence members and the historical duration, metadata
and custody receipts. Those checks passed for the retained session. Historical
custody never becomes fresh owner readiness, and a different boot invalidates
the same-boot reuse decision.

The plan remains disabled. The retained host logger-clock record precedes the
latest completed logger run; it must not be substituted for that run's current
clock/PID. Obtain and preserve a bounded readback after verifying live identity,
then prepare restart from the latest `retry-seal`, with a fresh archive claim.
Bind fresh owner/Space readiness and retain the actual phase, export and seal
receipts before using the analyzer for an attributable observation. No restart,
capture or recovery was performed while preparing this plan.

Both actual command generation and Bash syntax/ShellCheck passed (SC2016 is
excluded for intentional literal awk programs). Focused assembly and historical
source-pin refusal fixtures cover the new code; target-shell execution of this
plan and device timing remain untested.

## Attended execution preparation

The owner returned and reported the console visible. One bounded read-only USB
connection confirmed the original mainline boot
`e3a29c80-4948-4ef8-893a-cfbef0cd4918`, exact candidate guards and matching current
logger-clock/PID. The known-good Gemian LAN alias timed out; the authenticated
USB observation establishes that this is still mainline. No boot or partition
operation is needed. Previous capture and sealed-log evidence remain preserved.

The fresh plan `79424420-f296-49b3-a379-1e58d75970c9` uses the same reviewed
focused package and eight fixed phases: Space delivery/wait, logger start,
two focused deliveries, capture, independent export and log seal. The
[execution binding](focused-execution-binding.json) pins the private plan and
[phase runner](focused-run.py). Every phase has a persistent once-only host
claim, exact command digest, fixed deadline/caps and prerequisites. The runner
requires fresh Space acceptance before starting the logger, rechecks the source
closure, and uses the existing live guards in each frozen command. It has no
recovery or reboot phase. Export preserves available parsed files even when
completeness fails; sealing requires the exported monitor's reaped result.

The logger preparer now accepts the latest `retry-seal` only with an explicit
fresh clock file and new archive identity. It checks that clock's PID against
the live PID before moving the preserved log files, retains their exact hashes,
and preserves the original logger duration and byte limit. Older clock records
are not overwritten. This is a logger restart, not a device restart.

All eight frozen commands passed shell syntax and ShellCheck. SC2016 excludes
literal awk programs; SC2329 is additionally excluded for the logger's existing
signal-trap callback, which is invoked indirectly. The generated PID check was
verified before the archive claim. The disabled execution binding refused
before creating a claim or making a connection. Existing focused assembly and
historical-prerequisite fixtures passed. The owner-controlled Space wait and
actual focused capture have not yet run in this preparation record; their
receipts must establish the outcomes. Disable the binding after consumption.

## Attended readiness result

The single Space delivery passed. The readiness process then exited 2 after
5.152 seconds with complete stdin and empty stderr. Its explicit failure was
`console-byte`: the first recorded evdev item was MSC_SCAN value 36, while the
console supplied byte 27 (Escape). The helper reported console restoration.
The owner reports pressing Space; their photo shows the readiness prompt and
“Start cancelled. Test has not begun.” This is not attributed to a wrong key.
The scan is consistent with the matrix Space position, but the capture ended
before its EV_KEY edge and does not identify the source of the Escape byte.

[The sanitized result](focused-readiness-result.json) preserves the exact
outcome. No logger, focused delivery, timed capture, export or seal phase ran.
The prior logs remain sealed; there is no active capture deadline. The execution
binding is disabled. Do not repeat this consumed start or accept Escape as a
successful Space result. Resolve the console/input mismatch before a successor;
no keymap, modifier state, kernel, partition or boot was changed by this result.

The next observation is `space-ready --state eventN MINOR`, a read-only
snapshot using the same device and VT identity checks. It queries evdev held
keys, the transient VT shift bits before/after, LED flags, Meta mode, and Space
entries for maps 0–15. It does not consume input, print console prompts, change
termios/keymaps/modifiers, or admit the focused test. The LED byte is not the
VT lock/slock map state; equal shift samples do not make this an atomic snapshot.
Missing observations refuse. The Space readiness rule remains unchanged.

The read-only ioctl semantics were inspected in the retained Linux 7.1.3
`drivers/tty/vt/vt.c` (SHA-256
`e421d6ea542e6fe6a2711aaf27dd358f83429247d6676477f94d839230a22377`)
and `drivers/tty/vt/keyboard.c` (SHA-256
`cd0ca2d6183ebad4bbd4aacfb3326d010d0cafa7bdbd854fd30eaa80d7c35799`).
`TIOCL_GETSHIFTSTATE` returns the transient shift byte; `KDGKBLED` reports
current/default LED flags. These source observations explain the diagnostic
fields, not the failed Space press. Buildbox fixtures check successful and
failed metadata queries without consuming queued evdev data, changing terminal
settings, or writing a console prompt.

The guarded snapshot completed on the same boot in 0.840 seconds with empty
stderr: no held evdev keys; both shift samples zero; LED byte zero; Meta mode
4; plain and Shift Space entries 32. Alt Space was 2080 (Meta Space), but this
is a map entry, not evidence that Alt was active during the failed press.
[The complete sanitized snapshot](console-state-result.json) records all 16
entries and package identity. Nine ARM64/PTY fixtures and the common repository
gate passed. The query changed no console settings or input state and does not
explain the earlier Escape.

The failed readiness reader retained only the first non-Space byte and the
first evdev item, stopping before the actual keycode. Its successor preserves
the entire failing console read (at most 32 bytes) and up to eight already
queued evdev records after restoring the console. It does not wait for further
input or turn a failure into readiness. Reaching eight records is a bounded
prefix, not proof that the queue is empty. The new fixture supplies MSC_SCAN,
Space press/release and Escape+Space and requires the missing evidence to be
retained. A fresh attended attempt is justified by this added measurement;
the old attempt remains consumed and the focused binding remains disabled.

The successor package `410be65288d0350b47ec2eb63d72292c00eb61c0245783a824e6d054ec4c1581`
from commit `4ae54a6f5f55e53cacf2b247c5d04801023a5796` passed ten ARM64/PTY
fixtures, including complete Escape+Space/pending-event preservation. Both
compiled replicas matched. The owner reconfirmed attendance before binding
plan `e94119fc-dd80-4dec-b965-725ad5e8696c` to the same boot. All eight generated
commands passed shell syntax and ShellCheck (literal remote awk and indirect
logger trap callbacks retain their existing exclusions). No kernel changed.
A failed start remains a failure; a successful start permits the previously
prepared focused observation under the existing logger and preservation guards.
