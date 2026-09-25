# Capture preparation: retained-memory state is boot-specific

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
The [stream transfer implementation](CAPTURE_EXPORT.md) supplies bounded
framing and private host preservation. The [device bridge](CAPTURE_DEVICE.md)
adds acquisition and USB integration. Its later physical result is recorded
below. That result does not satisfy a future same-boot preservation requirement
for nonempty bytes.

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

## Later mainline export

The second [role-trace boot](USB_ROLE_TRACE.md#physical-results) identified its
USB Ethernet route, exported one 65,536-byte initial PMSG snapshot, received a
host preservation acknowledgement and returned normally to authenticated
Gemian. Private offline analysis verified that every exported byte was zero;
the strict capture decoder refused the absent fixed header. The retained
console shows the export action, not a capture producer. Neither the export nor
the host collector cleared PMSG memory.

This is an observation of that mainline boot's initial old-log copy. It does
not prove why it differs from the earlier nonempty Gemian read, that the current
zone was zero at a future capture-begin call, or that another boot will start
empty. Do not infer that the earlier nonempty evidence was safely cleared.

The next candidate can use the existing non-destructive capture-begin gate:
require zero in both its initial snapshot and current raw zone, then write the
fixed header and identity once. A nonzero byte remains a refusal and preserves
the predecessor; it does not trigger a clear, retry or alternate radio path.
This avoids selecting a destructive preparation operation for a state that may
already be empty. Recovery isolation, producer packaging and a separately
reviewed effect-bearing cycle are still required before device execution.

The [linked-producer audit](results/cycle-producer-boundary.json) distinguishes
that packaging gap from absent kernel code. The 54-patch kernel links capture,
recovery and controller entry points; the last physical image selected the
export-only startup action and never called the detector capture path. A future
`cycle` action must pass the boot-specific zero checks before any connectivity effect,
and its recovery collector must preserve the resulting PMSG record after reset.
The all-zero exported snapshot does not validate either later step.

## Changed-boot PMSG preservation

The [host collector](collect-gemian-pmsg.py) is prepared for a future admitted
cycle. After Gemian returns, it requires a boot ID different from the Gemian
boot preceding the test, the known-good MT6797X/ARM64/3.18.41+ identity, a
pstore mount, and exactly one `pmsg-ramoops-0` of 65,524 bytes. It saves that
old-log payload and a checksum receipt in a new private, ignored `artifacts/`
directory, then checks the same boot and file again. A short read or identity
change preserves the bytes but refuses classification. The collector only
reads Gemian and has not yet preserved a capture produced by a cycle boot.

This recovered old-log payload is distinct from the 65,536-byte raw snapshot
exported by the mainline boot: Gemian omits the native 12-byte ring header.
Decode only with independently expected
cycle, candidate, boot and input identities and the matching old-log format.
The current returned Gemian boot exposes `console-ramoops` alone, consistent
with the zero-filled export; it supplies no PMSG sample for this collector.
