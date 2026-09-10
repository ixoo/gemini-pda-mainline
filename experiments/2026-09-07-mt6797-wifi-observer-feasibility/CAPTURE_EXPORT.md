# Private capture snapshot transfer

[capture-export.py](capture-export.py) implements the bounded stream transfer
and host preservation needed by [capture preparation](CAPTURE_PREPARATION.md).
The [device bridge](CAPTURE_DEVICE.md) now connects it to an explicit export
startup action. It selects no boot candidate and implements no clearing or
clearing-acknowledgement command.

The sender accepts one immutable 65,536-byte snapshot from a future checked
capture-mode caller. Its 88-byte little-endian header contains `WFP1`, the
16-byte boot UUID, 32-byte session-manifest digest, 32-byte snapshot digest and
32-bit length. The raw bytes immediately follow. The receiver requires the
independently selected session identity, exact length and matching digest
before creating output. It observes a nonzero boot UUID different from the
independently supplied previous Gemian boot, rather than requiring the new UUID
before this minimal boot has a communication channel. The fresh, separately
selected session-manifest digest binds the expected run.
It consumes exactly one frame and does not
interpret later stream bytes. Neither the digest nor caller-supplied identity
authenticates the kernel or proves writer exclusion.

The receiver requires a private, caller-owned parent directory and creates a
new mode-0700 child using an open directory descriptor. Existing directories
or links are refused. It creates mode-0600 snapshot and receipt files without
replacement, synchronizes the snapshot, checks its complete readback, then
synchronizes the receipt and both directories. Failed saves remain for private
inspection; their files alone must not be treated as a successful return.
These filesystem operations do not prove survival of every storage failure.
No receipt authorizes clearing, and the receiver sends no save acknowledgement.

Before transmission, the host opens the explicitly selected serial terminal
in raw, nonblocking mode and sends a 52-byte request: `WFR1`, the previous
16-byte boot UUID and selected 32-byte session digest. The device refuses a
same-boot or session mismatch before sending its snapshot. Waiting for this
request avoids transmitting before the host reader has configured its terminal.

The command-line receiver uses that duplex exchange:

```sh
python3 capture-export.py --serial "$selected_serial_terminal" \
  --previous-boot-id "$known_gemian_boot" --session-sha256 "$selected_session" \
  "$private_parent/new-export"
```

The selected terminal must be a character device and pass `isatty`; final
symlinks are refused. Each endpoint uses one 60-second deadline for nonblocking
request/data I/O. EOF, I/O failure, malformed input or timeout stops the exchange
without a retry or clearing command. This bounds userspace transport waits,
not arbitrary kernel stalls or filesystem synchronization. The host closes
its terminal afterward; the device retains its descriptor while PID1 parks.
Diagnostic console text uses a different descriptor from this binary stream.

## Transport evidence and remaining integration

The unchanged [45-patch kernel](results/full-kernel-link-45.json) includes
Android USB gadget and ACM function support; it excludes USB configfs and the
standalone Ethernet gadget. The inspected Android gadget source creates ACM
instances, supports selecting one instance and binds it through the gadget
framework. The [receipt](results/capture-export.json) pins that source.

A bounded read-only inspection on the same known-good Gemian boot found the
ACM controls and eight `ttyGS` character nodes. The enabled function was
`rndis`, state `DISCONNECTED`, with zero ACM instances and zero selected ACM
ports. No serial node was opened and no control was written. Node existence
does not establish successful enumeration, data transfer, resource isolation
or identity of the separately built kernel.

The [nine focused tests](test-capture-export.py) pass on the host and ARM64 RE
VM, including a real local pseudo-terminal transfer, fragmented reads/writes,
identity and corruption refusal, truncation, private modes, existing evidence
preservation and injected sync failure. The pseudo-terminal receiver sends no
save acknowledgement. They also exercise the request handshake, same-boot
refusal, a real nonblocking deadline and disconnect. All payloads are synthetic;
no retained bytes were exported through USB. These tests do not validate the
candidate's packaged runtime.

The device bridge implements checked acquisition and one ACM setup. Actual
enumeration/export, the complete candidate and recovery procedure still need
validation before a physical session. A saved snapshot does not release capture
admission or the separate owner-approval boundary for clearing.
