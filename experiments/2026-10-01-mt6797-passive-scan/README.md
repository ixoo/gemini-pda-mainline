# MT6797 one bounded passive scan

The [TC4 accounting boot](../2026-10-01-mt6797-tc4-reconcile/results/runtime-1.json)
returned matched command credit while retaining unmatched free-pool returns.
The next connected test adds fresh runtime accounting and one standard
mac80211 passive scan. It is an experimental management receive path;
association, keys, data TX, packet DMA and working Wi-Fi remain unproved.

## Protocol inputs

The [source receipt](results/sources.json) pins individual Planet gen3 objects
at `c5b0be85017ad0c599725e8273842efdbecdd88a` and the actual Linux 7.1.3
mac80211/cfg80211 headers. The existing [scan lifetime analysis](../2026-09-08-mt6797-wlan-offloads/FIRMWARE_SCAN_LIFETIME.md)
joins V2 CID `0x03`, payload scan sequence and the 24-byte `0x0d` constructor.
Its outer sequence is zero. Cancellation CID `0x1b` has no proved completion
or drain fence; this candidate therefore accepts one scan and never reuses
its scan, BSS or BMC lifetime before reviewed recovery.

`nic.c:1376–1424` encodes BSS activation CID `0x11` using a twelve-byte payload.
`cnm.c:823–847` allocates the first AIS BSS at index zero and starts own-MAC
allocation at one. The active `privacy.c:948–1033` branch allocates the first
unused unencrypted BMC slot from zero, rather than the historical reserved
index constants. The sole owner reserves these slots for the whole retained
firmware session. The [RE-VM follow-up](results/firmware-bss.json) joins the
mapped activation handler's reads of BSS, active, network type, own-MAC,
MAC bytes and BMC fields to that layout. Its bounded direct graph exhausts at
186 instructions with thirteen skipped callees. Their application, scheduling
and RF effects are not proved by the internal zero return.

`scan_fsm.c:283–356` and `nic_cmd_event.h:1169–1217` define the 226-byte
no-IE V2 request and completion. This candidate uses passive type zero, no
SSID, no probes, zero reserved extension and an explicit permitted 2.4 GHz
channel list. `scan.h:448` says milliseconds for legacy dwell, while line 466
says TU for V2. The retained request decoder joins V2 offset 154 to the core's
zero/default branch, already in the [private scan analysis](../2026-09-08-mt6797-wlan-offloads/results/firmware-scan-lifetime.json).
Keep zero/default dwell and timeout fields rather than selecting unproved
nonzero units. A separate host deadline bounds the scan.

Native management RX uses the sixteen-byte descriptor and optional groups
4,1,2,3 in that order, with sizes 16,16,8,24 (`nic_rx.c:283–335`,
`nic_rx.h:455–489`). Require a complete native unprotected beacon/probe
response, valid RX vector, permitted channel and bounded frame extent. Group
3 word 2 bits 8–15 carry RCPI. Report its half-dBm measurement through
cfg80211; do not invent a receive rate or hardware timestamp. Translated data,
fragmentation, protection and unsupported metadata are never delivered.
The [receive lifetime record](../2026-09-08-mt6797-wlan-offloads/RECEIVE.md)
continues to own unresolved station, key and reorder requirements.

## Implementation and owner

Patch 0074 adds one fresh, complete runtime TC4 snapshot on the mature
accounting owner. It requires the zero baseline and complete initial pair,
preserves pending CPU/FFA counts and sequence history, and commits no refund
on a partial read, foreign queue, excessive return or expired deadline.
Historical diagnostic budgets and observation-only callers stay unchanged.

Patch 0075 connects a default-off passive scan through standard mac80211
callbacks. Only the permanent-address station-type interface can open; the
CONSYS owner admits it after successful initial accounting. The scan and
regulatory callbacks and receive work share the existing MAC/HIF mutex order.
The caller checks current cfg80211 permissions, with no private country hint,
regdomain, random address or active scan. Firmware owns scan tuning; no
operating channel or associated station is established by the idle interface.
Peer station transitions and host TX remain refused.

A completed matching event, cancellation, timeout, regulatory change, interface
removal or transport/protocol failure has one serialized terminal transition.
Complete every accepted host request once; failures and cancellations are
aborted. Join delayed work before removing its interface. Never issue cleanup
I/O after failed transport, lost ownership or unadmitted wire state. On a
healthy normal completion submit one BSS deactivation; on admitted cancellation
or host timeout submit at most one cancel and one deactivation. These are
submissions, not stop acknowledgements. All wire slots stay retired.

## One-boot protocol

Hypothesis: the retained image accepts the source-defined passive scan and
returns a matching completion plus native management results on the exclusive
PIO owner. The unique observation joins a created/up standard interface,
matched `0x0d`, validated native beacon and standard userspace scan result.
The [parent protocol](../2026-10-01-mt6797-tc4-reconcile/README.md#one-boot-protocol)
owns the single WMT/START, immutable private record, configuration, A53 checks,
evidence preservation and reviewed recovery. This is the first admitted scan
request in that fresh firmware session. It changes no protected partition,
calibration record, IRQ enable, firmware-own policy or packet DMA.

Allow one BSS activation, one passive request with at most thirteen currently
permitted channels, and the closing submissions above. No host or probe frame
TX is submitted. This source-defined passive request is not a measured RF
silence claim. Require WCIR identity/readiness and retained driver ownership
before submission and each receive tick. Allow one pre-admission fresh credit
snapshot and at most 256 runtime ticks, twenty milliseconds apart, under a
five-second host scan deadline. Each tick has one shared absolute budget of
at most 100 ms, sixteen RX packets maximum, and 4096 total packets maximum.
Finish the bounded tick after a matching done event to service the other RX
port; no empty poll or done event is treated as a firmware drain fence.
Each closing command has at most one second. Never reset quota/history,
retry a refused request or start another scan in the same firmware lifetime.

Decision branches:

- Matching completion, validated beacon and standard userspace result: advance
  to connected management TX/RX and mac80211 association requirements.
- Matching completion without usable results: diagnose retained RX metadata,
  filter and queue behavior; do not repeat the same artifact without a new
  measurement that changes that decision.
- Timeout/cancel: abort once under the admitted closing budget and retire the
  wire lifetime. No cancellation ACK, delay or unrelated query grants reuse.
- Failed ownership/readiness, fatal status, foreign counters, partial I/O or
  unknown/malformed event: stop further I/O, retain the owner and preserve
  evidence before reviewed recovery. Do not substitute another radio request.

Keep raw logs, scan output, SSIDs, peer addresses and descriptor/counter values
private. Publish only sanitized identities, checksums and derived support
booleans. Verify the exact candidate/boot, preserve the complete private log,
run the A53/provider regression and reviewed recovery, then independently
confirm changed-boot Gemian release and Wi-Fi carrier. Boot2 installation
remains guarded and fully read back; the owner selects it physically.

## Focused validation

The two original C fixtures compile the actual selected HIF and scan helpers
with the existing [compatibility shim](../2026-10-01-mt6797-normal-sets/tests/test-compat.h).
Strict C11 warnings-as-errors with ASan/UBSan pass. Runtime tests exercise fresh
snapshots, retained pending counts, complete depletion/refill without history
reset, missing mature-owner requirements, all twenty transfer faults, foreign
queues, excessive returns and deadline expiry after the final read. The prior
TC4 and observation-only fixtures pass unchanged against this HIF.

Wire tests cover channel bounds/duplicates, default fields, shared command
framing/debit, scan payload versus outer sequence, matching completion state
and channel count, all sixteen RX group combinations with both header offsets,
and every truncated extent. Translated/error/unavailable-vector input is
refused. These fixtures do not emulate firmware scheduling or bus exceptions.
The MAC completion/work joins were inspected; hardware timing remains untested.
Linux 7.1.3 checkpatch reports zero errors, zero warnings on 0074 and one
file-addition MAINTAINERS reminder on 0075. This is an internal experimental
driver archive, with no new maintainership or upstream submission readiness
claim. Optional spelling/const lists were unavailable. No synthetic DCO
sign-off is added.

The [userspace receipt](results/userspace.json) pins five Debian Bookworm ARM64
packages against the retained signed index and two required Debian signatures.
Only the six ELF files in that receipt are admitted: iw 5.19, its loader,
libc, libnl, libnl-genl and libc's libgcc dependency. Their dynamic dependencies
close within the bundle; a native RE-VM loader/version check passes without
radio access. The [RAM-root transform](retarget-initramfs.py) verifies that
receipt and each ELF, changes only the kernel release gate, and preserves all
53 parent members while adding exactly six regular files. Firmware and the
mode-0600 immutable private record remain byte-identical. Canonical archive
round-trip and isolation checks pass with 59 members. No package or private
RAM-root bytes are published.

The [clean pushed Buildbox build](results/build.json), [offline candidate](results/candidate.json)
and [installer/session dependency preflight](results/preflight.json) pass.
The actual prepared-source fixtures pass strict warnings and UBSan; ASan/UBSan
passes with `-no-pie` after a PIE-instrumented startup failure before ASan's
thread-stack/init-done record. This changes only host test executable layout.
No kernel change or hardware result follows from that host failure.

The standard [scan command](passive-scan.sh) verifies the authenticated boot,
sole CONSYS-bound wiphy, initial configuration/accounting and all six ELF hashes
before creating one permanent-address station-type interface and raising it.
It invokes one `iw dev wlan0 scan passive` under a twelve-second userspace
limit. There is no second request after a refused, failed or timed-out command.
The [host runner](passive-host.py) inserts that phase before the existing log
seal/export, saves raw scan output privately, then preserves it with the
complete kernel log before reviewed recovery. A failed scan remains negative
evidence and still permits ordinary evidence preservation and recovery.
Its focused pure check covers scan-before-export ordering and duplicate refusal;
classification covers successful synthetic output, six transport/identity refusals and absent
BSS output. The [installer](install-passive.py) retains the reviewed guard,
full-partition readback and clean shutdown. The [deployment receipt](results/deployment-1.json)
records successful full readback and confirmed shutdown. Exact capture and
host preflights pass against that real deployment. Await the owner’s physical
boot2 selection; no device scan has run for this candidate.
