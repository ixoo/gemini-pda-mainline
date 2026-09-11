# One physical snapshot-export session

Status: preparing. The [physical recovery prerequisite](EXPORT_RECOVERY.md#attended-result)
has an owner-reported Esc restart and authenticated changed-boot Gemian return.
This packet does not install or boot an image.

## Hypothesis and fixed inputs

The [46-patch native kernel](results/full-kernel-link-46.json),
[compact fourth filesystem](results/runtime-compact.json) and
[validated native container](results/export-container.json) can reach export
PID1, preserve the initial raw PMSG snapshot and send its 65,536 bytes through
one ACM exchange. This tests the real native mount and USB path that fixtures
cannot establish. It starts no WLAN cycle or capture initializer and clears
no retained bytes.

Before admission, freeze the exact private container, padded image, session
and filesystem checksums from their validated receipts. Recheck the seven
startup hashes and kernel package identity. Complete the recovery prerequisite,
guarded boot2 installation, full-partition readback and clean shutdown before
issuing a physical boot2 request. Record the preceding authenticated Gemian
boot UUID. A package timestamp, a matching release string or this packet does
not replace those checks.

## Host preparation and one request

Prepare the host receiver and an existing caller-owned mode-0700 output parent
before physical selection. The new export directory must be absent. Retain
host stdout, stderr, exit status and timing privately. Use the exact selected
session digest and previous Gemian UUID with the existing
[receiver command](CAPTURE_EXPORT.md); it must not prompt interactively after
the terminal appears.

Record the host USB/serial inventory before boot and identify the PDA's physical
connection to its left USB-C port. After boot, resolve the new ACM terminal
through that USB parent, not a wildcard or the first serial filename. The
inspected [USB source](results/capture-device.json) defaults are VID `18d1`,
PID `0001`, manufacturer/product
`Android`, and serial string `0123456789ABCDEF`. These shared defaults are
checks on enumeration, not unique device authentication. The minimal startup
does not override them. The source's charging-boot branch changes VID/PID to
`0e8d:20ff`; that is not the expected session. Refuse missing, mismatched or
ambiguous attribution before opening a terminal. Keep observed host identifiers
private.

Start exactly one receiver invocation on the attributed character terminal.
Each endpoint has one 60-second request/data deadline. Prepare collection
before asking for physical selection; do not spend that deadline installing
host tools. The device configures one ACM instance, waits for the host request,
requires USB `CONFIGURED` and checked capture state, then sends one frame.
No terminal probing, retransmission or second invocation is admitted after
the request has been sent. A pre-request attribution failure also ends this
attempt; diagnose the cause before selecting another boot.

## Result and recovery

A preservation pass requires receiver exit zero, exactly 65,536 saved bytes,
matching complete-file checksum and receipt, the selected session digest and
a nonzero boot UUID different from the preceding Gemian boot. Preserve the
private snapshot and receipt before recovery. Their bytes need not match the
earlier unfrozen Gemian read: that read did not establish a predecessor for this
boot. Do not publish retained contents or interpret a valid ring header as
proof of coherent firmware data.

The receiver confirms one frame, not the device's subsequent state. The bridge
rechecks capture state after sending, but the protocol transmits no completion
status for that check. Therefore a successful receipt does not prove the final
check passed or that PID1 stayed healthy afterward. It establishes preservation
of the supplied snapshot under the stated code/deployment assumptions, not
authorization to clear or admission to a WLAN cycle.

Missing USB, malformed/partial data, identity mismatch, timeout or failed host
save is a failure or inconclusive result at its observed stage. Preserve any
partial files and available console/host evidence; file presence alone is not
a pass. Do not change gadget settings, extend the timeout or repeat the request.
After evidence preservation, obtain owner confirmation for recovery and use
only the reviewed physical procedure. If USB never worked, explicitly record
that the complete snapshot could not be retrieved before recovery. Confirm
changed-boot known-good Gemian afterward. A deadline never authorizes restart.

A pass advances same-boot preservation design; it does not implement the
separate compare-and-clear operation. A failure must identify a changed
measurement or corrected input before another physical selection.
