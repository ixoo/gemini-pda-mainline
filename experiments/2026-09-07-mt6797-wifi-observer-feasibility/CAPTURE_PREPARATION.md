# Capture preparation: nonempty retained memory

One bounded read on known-good Gemian found the selected PMSG range nonempty.
The [sanitized receipt](results/capture-preparation-inspection.json) records
the observation; the complete raw snapshot remains private. This is a
preparation refusal, not a capture run or a retention test.

## Observed state

The same authenticated boot reported a bound ramoops backend, a 64-KiB PMSG
zone and no exported pstore files. Its covering DT reservation is
`0x44410000` plus `0xe0000` bytes, without `no-map`. The selected PMSG range is
`0x444e0000` through `0x444effff`. The earlier `ram_console@44400000` node is
a different reservation and must not be used to identify this range.

A single 65,536-byte read through an independently identified, read-only
`/dev/mem` descriptor returned 60,814 nonzero bytes. Private analysis in the
RE VM found the native ring signature, an in-bounds start of 7,169 and size
65,524. These header observations do not certify coherent payload contents.
The read's length and digest matched the privately retained receipt; boot
identity and ramoops parameters were unchanged across the read. No memory,
pstore, radio, partition or reset write was issued.

An empty pstore directory therefore does **not** establish an empty current
PMSG zone. The directory exposes recovered records, not all current RAM bytes.

## Why this snapshot cannot authorize preparation

The ordinary Gemian PMSG writer was not frozen. The single read is not an
atomic or quiescent snapshot, and later writes may change the predecessor.
The inspected native `/dev/mem` read path uses the ARM64 linear RAM mapping;
the experimental capture backend instead requires a separate mapping and
rejects valid RAM PFNs. This observation does not establish coherence between
those mappings. Nor does it prove which bytes survive shutdown and the next
boot. A digest of this file cannot resolve any of those gaps.

Consequently, do not add an automatic clear to capture initialization, clear
through the current Gemian mapping, or package this snapshot as a certified
predecessor for a later boot. An exact byte comparison could refuse a mismatch,
but cannot by itself create the missing freeze/export contract.

## Required next boundary

Before implementing a destructive preparation operation, specify how the
selected capture-mode boot will export its complete initial raw snapshot to
external private storage while ordinary writers remain excluded. Bind that
export and any subsequent preparation request to the same boot and exact
current bytes. Resolve the transport and failure recovery before selecting a
candidate; the earlier minimal PID1 filesystem supplies no such export path.
The [stream transfer implementation](CAPTURE_EXPORT.md) now supplies bounded
framing and private host preservation. The [device bridge](CAPTURE_DEVICE.md)
adds acquisition and USB integration; packaging and actual device export still
precede any claim that this same-boot requirement has been satisfied.

Only after that contract is concrete can a separately reviewed operation
compare the preserved predecessor, perform one bounded zero pass and require
full ordered readback. Preserve the initial snapshot, refuse mismatch or
interference, and prohibit retry or capture admission after a failed attempt.
These are requirements, not implemented or tested behavior.

The [standing retained-RAM policy](../../docs/SAFETY.md#standing-retained-ram-diagnostic-authorization)
explicitly excludes clearing nonempty slots. Physical clearing requires
separate owner approval after the exact implementation, preserved evidence,
candidate and recovery path are reviewable. No approval is requested here:
those prerequisites are incomplete. The existing
[capture admission](PERSISTENT_CAPTURE.md#native-acquisition-and-raw-recovery-integration)
continues to require both the initial snapshot and current zone to be zero.
