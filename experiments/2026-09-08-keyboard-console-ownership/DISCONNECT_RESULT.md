# Console successor disconnect result

The 2026-09-09 attended test **failed the disconnect cancellation requirement**.
The full reader scan is separately incomplete. The exact identities, transport
results and sanitized monitor fields are in [disconnect-result.json](disconnect-result.json).
All unique probe files and the complete kernel log were preserved before the
reviewed return to changed-ID Gemian. No keyboard capture or proof retry ran.

## Observation and interpretation

The existing boot2 image matched all 16 MiB; the guarded installer skipped its
write and shut Gemian down cleanly. The owner selected boot2 and confirmed a
readable console. One authenticated observation verified a fresh boot, the exact
candidate members, CPU0–7 and RAM guards. The actual dependency and enabled
monitor package passed offline preparation, and the exact boot-specific binding
was published at `6c11fd62` before execution. The binding is now disabled.

The one no-PTY client received the harmless child marker after complete stdin
and was killed at 0 ms marker-to-kill latency. The sole strict export exited 1
in 0.395 seconds, with no stdout and the diagnostic
`keyboard-disconnect-export stage=process-executable exit=1`.
This locates the refusal but does not distinguish a failed executable-link
lookup from the executable-match refusal. No surviving reader is established
by that diagnostic, and no complete reader scan is established either.

A separately admitted, read-only connection exported the four fixed regular RAM
files using the existing identity, RAM, file-type, ownership and size guards.
It omitted the process scan for preservation only, left source files intact,
and did not replace the failed proof export or manufacture a reader receipt.
Its 30-second host deadline is not a remote-shell termination guarantee.
The native preserver's historical delivery stop was not represented as resolved;
this bounded fixed-file action used the already available shell export instead.
All four files arrived completely with a final same-boot check.

The monitor reports `reason=deadline`, `cancel=0`, TERM at 280 ms, KILL at
360 ms and reap at 362 ms, with no identity loss or lateness. Outer exit is 2.
This establishes bounded deadline cleanup in this attempt. The verifier requires
`cancelled` or `forward-close-or-stall`; deadline cleanup does **not** satisfy
that requirement. Fixing only the scan would therefore not make this a pass.

The separate logger seal preserved 121,116 bytes / 1,746 records, from sequence
zero through explicit seal. Only afterward did the guarded native recovery
request run once. Its complete frame and normal reboot announcement were
accepted by the updated checker despite the old SSH timeout. Authenticated
Gemian `3.18.41+` returned with a new boot ID. This exercises the revised request
interpretation and changed-boot confirmation; it is not a new full baseline
aggregate receipt.

## Next decision

Diagnose the missing disconnect notification and executable-scan refusal from
the exact source and retained evidence before selecting another test. Keep the
original failure intact. There is no new physical test or keyboard capture
admission from this result, and the device is available in Gemian.

Validation: exact candidate/installer validation, generated shell syntax and
ShellCheck, dependency/package preparation, and the repository publication gate
passed. This session supplies device evidence; no kernel rebuild was needed.
Raw captures, executable payloads and device process identifiers remain private.
