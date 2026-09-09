# Fresh keyboard metadata collector

[metadata.py](metadata.py) fills the existing runtime prerequisite from one
bounded read-only connection. It does not enable capture. With `--execute`, it
first validates the exact current source/package/dependency admission and the
seven retained files of the passing disconnect proof from the same admission
ID and boot. A missing or rejected proof refuses before a claim or transport.
The default only prepares and hashes the command; it makes no connection.

The execution creates one private claim under that session's `prerequisites/metadata`
and has no retry. It uses the existing authenticated transport with 30 seconds,
16 KiB stdout and 16 KiB stderr bounds. Raw commands, output and process status
remain private. The collector exports metadata, not evdev events or VT bytes,
and performs no map, termios, driver, resource or device-storage writes.

## Observations and checks

The command reuses the exact boot/CPU/member identity, RAM, live-logger, console
map and complete reader guards used by capture. Refactoring these guards for
reuse preserved both generated initial/postflight capture guards byte for byte.
It requires a unique matrix event among at most 256 event entries, the actual
character-device number, matrix ancestry and driver, and one bound AW9523
provider at the expected device-tree node. It checks all four recorded driver
and device-tree links directly; the I2C bus number is observed, not assumed.

The matrix path and provider node are grounded in the selected candidate's
composed DTB: `/keyboard-matrix` references the AW9523 provider at
`/i2c@1101c000/gpio-expander@5b`. The retained passing-disconnect boot log also
records `/devices/platform/keyboard-matrix/input/input0` and the provider probe.
Those observations guide the predicates but do not supply future runtime facts.
See the [candidate identity](../../2026-09-08-keyboard-console-ownership/validation.json).

All nine capability bitmaps are bounded and preserved exactly. The parser
requires key and scan event support and all 25 keycodes in the targeted protocol.
It rejects malformed bitmaps, wrong ancestry/device fields, duplicate fields,
partial output, failed transport, changed boot and boot age 240 seconds or older.
The map/reader predicates must pass before the final same-boot completion frame.

Only after full parsing does it create the existing `runtime.json` prerequisite
and a runtime-contract file with actual event, minor, ancestry, capabilities,
resource paths and receipt digest. The unchanged prerequisite verifier accepts
that receipt. This is a current inventory; custody still separately supplies
actual owner readiness, readable screen and continuous exclusion of other readers.
Delivery and capture recheck the resource links, capability bytes, map and readers.

## Validation and remaining work

Five metadata fixtures pass: receipt integration, identity/capability/age
rejections, malformed or incomplete transport, command syntax/ShellCheck and
source binding, and missing-proof refusal before claim/transport. Seven capture,
eight disconnect and six prerequisite fixtures also pass. The initially failing
missing-proof fixture used the host's symlinked temporary path; resolving the
fixture root allowed it to reach the intended missing-file check. No production
predicate was relaxed. Python syntax and repository checks passed.

The generated metadata command has not run on the device. All four generated commands subsequently passed exact ARM64 BusyBox syntax
validation; see the [attended contract](ATTENDED_SESSION.md#validation-and-limits).
Actual fresh runtime conditions remain pending.
Capture and disconnect execution bindings remain disabled, and the shared queue
is not ready for physical selection. No kernel, userspace rebuild, or device
access was needed for this collector. The [combined budget](CAPTURE_ADMISSION.md)
remains unchanged.
