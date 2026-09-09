# Corrected monitor full-duration result

The single Buildbox run at `daaa4529d6be4e0e55570aba90f0e0f6b3a9418b`
passed for the monitor source used in the
[passing device disconnect test](../../../../2026-09-08-keyboard-console-ownership/DISCONNECT_RETEST.md#attended-result).
The previous duration receipt binds an older source and correctly refused
the corrected monitor; it remains unchanged.

The harmless static ARM64 fixture ran under QEMU for 213.055521 seconds.
TERM occurred at 209000 ms, KILL at 213000 ms and reap at 213021 ms, all within
the unchanged bounds. The saved status reports deadline cleanup, signal 9,
reaped 1, no identity loss and no lateness. Forwarded and retained stdout
match at 57 bytes; both stderr streams are empty. The unique 202000 ms marker
passed the existing proof classifier. No evdev, VT or device action occurred.

The existing dispatcher built from a clean published checkout, fetched only
the validated package, and exited zero. Local reparse checked the actual proof
inventory, source identities and lifecycle again. A read-only postflight
confirmed removal of the managed temporary duration stage.
[receipt.json](receipt.json) records the exact package, proof, source, tool and
member digests. Raw proof and executable remain in ignored artifacts.

The capture prerequisite now selects this receipt and proof identity while
retaining its source and timing checks. Focused prerequisite, capture, packet
and proof tests passed, as did repository publication checks. No monitor
source, enabled binary, kernel or device image changed.

Capture remains disabled. Fresh input metadata, custody, same-boot disconnect
evidence, exact capture admission and the finite owner sequence remain required.
This timing pass and the prior boot's disconnect pass cannot substitute for
those runtime facts.
