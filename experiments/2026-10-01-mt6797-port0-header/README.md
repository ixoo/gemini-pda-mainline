# Observe the pending port-0 packet header

The [authenticated capability boot](../2026-09-30-mt6797-capability-port0/results/runtime-1.json)
received a valid port-1 reply while WRPLR reported 89 unread bytes on port 0
both before and after the query. The packet was not read. Its kind remains
unknown; the reported length alone does not prove its identity or cause.

Pinned Planet gen3 `nicRxWaitResponse()` at revision
`c5b0be85017ad0c599725e8273842efdbecdd88a` selects the WRPLR half and
WRDR data port separately. `nic_rx.c` SHA-256
`a844bdf75065a152e78d30c789aabb398b0d0f336d30d6ffd028793bf091412b`
uses `ALIGN_4(length + 4)` for an RX read. Its RX descriptor defines the
first two bytes as byte count and the next two as packet type; the pinned
software event and management masks are `0xe000` and `0xe001` under `0xe00f`.
These source facts support a bounded header read, not a claim that the queued
packet is an event.

[Patch 0057](../../patches/proposals/0057-wifi-mediatek-observe-one-port0-header.patch)
adds one port-0 PIO read after a successful capability query on the same HIF.
The capability trace must have reported 89 bytes on port 0 before and after
its port-1 reply. A fresh WRPLR read must still be exactly `0x00000059`;
otherwise the packet is left unread. The read requests 93 logical bytes and
transfers 96 padded bytes once. It reports only length, packet type, derived
kind, optional event ID/sequence and pre/post WRPLR. Payload and device
addresses are not logged. A new packet of the same size could have replaced
the earlier one; this diagnostic does not prove continuity. Any transport or
header error poisons the HIF session. No radio command, calibration write,
packet DMA, network interface or packet processing path is enabled.

The [focused host test](tests/test-port0.c) compiles the exact patched HIF
source. It covers actual START then capability on one HIF object, the one
successful port-0 header read, refusal without a previously reported packet,
a changed queue length, malformed header length, all 29 port-0 scalar access
faults and the prior 69 capability faults. [Validation](results/host-validation.json)
records the compiler and patch identity.

The next candidate's boot hypothesis is that the queued port-0 packet remains
89 bytes after capability and yields a classifiable header. The unique new
observation is its bounded header plus the post-read queue length. If the
length changed, stop without reading. If a valid event, management or data
header is observed, use only that classification to choose the next offline
protocol step. If malformed or transport-failed, preserve the trace and stop.
In every branch, preserve private evidence and return through the reviewed
Gemian recovery path. This image is not to be repeated without a
new decision-changing measurement.

The clean pushed input commit `a26d68dcf2489f807a765277800d53f7c1d8bac9`
built on Buildbox as profile `mt6797-a53-wifi-port0-header`, release
`7.1.3-gemini-a53-wifi-port0-header`. The validated package inventory is
SHA-256 `329ee08938421543c5baf84d0b5520f6ea25f64be3b79bd0f369e67ad47b25f3`.
The private 52-member RAM root changed only `/init`'s release gate; retained
firmware remained hash-identical. The assembled board DT matches the
previously booted candidate at SHA-256
`cef9373ea3aa0e1a8a45a13b953ae95e48939b211e41a73052543be784ee3214`.
The [sanitized candidate receipt](results/candidate.json) pins the exact
16 MiB boot2 checksum
`fa7dc1a6a96f7b2e8c7e875271882b27f7e73148508a0ae4ae2880e32802165d`.
[Build details](results/build.json) preserve the package and candidate
identities. A build is not hardware support.

The guarded boot2 installer ran from authenticated Gemian boot
`19fbba30-27a4-4689-8252-8c0ab8d5ca70`, with Wi-Fi carrier 1. It resolved
logical boot2 to p30, separate from root p29, checked stable power and the
previous full checksum `503126de747a15bc922d845dd4cfe6709eb6ba30ea5b150b62d051b9b6a20f39`.
It wrote, synced, flushed and matched the new full readback, then shut down
cleanly. The [sanitized watch receipt](results/watch-1.json) pins the private
deployment and USB-event evidence.

The 900-second watch was armed before the physical handoff. It observed
preloader activity and then MediaTek `20ff`, which remained through expiry.
No mainline USB gadget route or device SSH attempt occurred; the known-good
Gemian LAN endpoint also timed out. Physical boot2 selection and screen state
remain unconfirmed. There is no mainline boot ID, kernel log, port-0 header,
A53 regression or verified Gemian return for this attempt. The verified image
remains installed; `20ff` alone does not establish a kernel failure or even a
live boot. Do not repeat an identical watch without a decision-changing
physical observation.

## Confirmed later boot2 handoff

The owner later confirmed physical boot2 selection with the console on. A new
mainline USB gadget route was already present, so no second watch was started.
The exact installed image booted as
`126ba4cd-08f2-4104-b7d3-b2c3ae1c4f53`, release
`7.1.3-gemini-a53-wifi-port0-header`. The [runtime receipt](results/runtime-1.json)
pins the complete private log and the following single-boot observations.

WMT setup and START completed once. Firmware-ready WCIR was `0x00300279`.
The capability command again received a valid 124-byte port-1 reply while
port 0 reported 89 bytes. The guarded port-0 read transferred 96 padded bytes
for that 89-byte packet. Its header was type `0xe000`, event ID `0x27`,
sequence 0. The pinned gen3 event enumeration labels `0x27`
`EVENT_ID_DEBUG_MSG`, and its handler forwards the event body to the firmware
log printer. This is source-supported classification of the observed header;
the body was not logged or published. Post-read WRPLR reported another 80-byte
packet on port 0, which this one-read diagnostic left untouched. It does not
show whether that packet is also a debug event or whether the debug stream is
continuous.

The full log was preserved privately at SHA-256
`33ba77f23979ff7548889232975a61a1a36d8d6cd4591847c8546586d3aa704c`.
No bounded search hit a kernel panic, BUG, WARNING, unhandled fault or call
trace. The A53 RAM-service regression passed. Reviewed recovery confirmed a
changed Gemian boot `37602366-2e40-42ca-a05f-ec12a3026614`, release
`3.18.41+`, with `wlan0` carrier 1. No mainline radio command, calibration
application, packet DMA, network interface, scan, association or traffic was
demonstrated. The debug event shows asynchronous port-0 traffic, but it does
not establish an operational receive path or usable Wi-Fi.
