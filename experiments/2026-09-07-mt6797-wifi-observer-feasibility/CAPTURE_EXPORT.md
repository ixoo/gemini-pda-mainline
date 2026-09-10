# Private capture snapshot transfer

[capture-export.py](capture-export.py) implements the bounded stream transfer
and host preservation needed by [capture preparation](CAPTURE_PREPARATION.md).
It is not installed in startup, selects no boot candidate and implements no
memory acquisition, USB configuration, clearing or acknowledgement command.

The sender accepts one immutable 65,536-byte snapshot from a future checked
capture-mode caller. Its 88-byte little-endian header contains `WFP1`, the
16-byte boot UUID, 32-byte session-manifest digest, 32-byte snapshot digest and
32-bit length. The raw bytes immediately follow. The receiver requires the
independently selected boot and session identities, exact length and matching
digest before creating output. It consumes exactly one frame and does not
interpret later stream bytes. Neither the digest nor caller-supplied identity
authenticates the kernel or proves writer exclusion.

The receiver requires a private, caller-owned parent directory and creates a
new mode-0700 child using an open directory descriptor. Existing directories
or links are refused. It creates mode-0600 snapshot and receipt files without
replacement, synchronizes the snapshot, checks its complete readback, then
synchronizes the receipt and both directories. Failed saves remain for private
inspection; their files alone must not be treated as a successful return.
These filesystem operations do not prove survival of every storage failure.
No receipt authorizes clearing, and no byte is sent back to the device.

The command-line receiver reads an already established binary stream on stdin:

```sh
python3 capture-export.py --boot-id "$observed_boot" \
  --session-sha256 "$selected_session" "$private_parent/new-export"
```

The transport owner must supply binary terminal configuration, timeout and
disconnect handling before using this on hardware. A stalled stream may block;
the receiver does not select, configure or close a physical USB connection.
Do not redirect diagnostic console text into this binary stream.

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

The [seven focused tests](test-capture-export.py) pass on the host and ARM64 RE
VM, including a real local pseudo-terminal transfer, fragmented reads/writes,
identity and corruption refusal, truncation, private modes, existing evidence
preservation and injected sync failure. The pseudo-terminal receiver sends no
acknowledgement. All payloads are synthetic; no retained bytes were exported
through USB. These tests do not validate the candidate's packaged runtime.

Next connect a checked capture-mode old-log read to this sender, establish the
single ACM function's setup/teardown and deadline behavior, and preserve an
actual same-boot export before preparing a clear request. Startup, selected
kernel inputs, capture admission and the separate owner-approval boundary
remain unchanged.
