# Keyboard boot2 session readiness audit

Review-ready UTC: `2026-09-07T21:09:17Z`.

## Verdict

The packet is **not offline-ready for final device admission**. The existing
authenticated-baseline kernel, DT, configuration and candidate are adequate for
the narrowly declared keyboard observation; this audit found no predicate that
requires a kernel or DT change. Reuse only the unchanged raw Android-v0 candidate
`a25fe4cb907f4f3da2bf9f36fcf38b3fff7d8ba84adc37562fdcff2f1a422daf`
and its candidate manifest
`54b07f0c70e77fd1e34fde4fc1c929980f0d8c3410f0a97ce3f15ffec1a66179`.
The baseline observation established authenticated USB, readable tty1, the
expected map and matrix input on that candidate, and the supplemental recovery
review established changed-ID Gemian return for dependent preparation. It did
not grant another execution or observation budget.

The single current blocker is **unvalidated prerequisite evidence, specifically
the absent exact Dropbear no-PTY disconnect proof**. In
[`capture.py`](../2026-09-05-owner-away-experiment-preparation/keyboard/capture.py),
`prepare()` checks `full_duration_receipt_sha256`,
`disconnect_receipt_sha256`, `runtime.metadata_receipt_sha256` and
`custody.receipt_sha256` only as 64-hex strings. It does not open a referenced
receipt, verify its inventory or source/package bindings, or require a passing
classification. The queue independently records transport-disconnect evidence
and prerequisite validation as incomplete. Consequently an invented digest can
cross the current host preparation boundary. In the disconnect case that leaves
the decisive ambiguity: transport may disappear without proof that the remote
monitor became terminal and reaped, retained its partial files, released its
input/tty reader, and remained recoverable by one independent export connection.

Stop here under the work-item rule for ambiguous process and reader ownership.
Do not build, deploy, select boot2, or consume the one keyboard capture claim.

## Minimal repair that removes this blocker

Add one versioned, read-only prerequisite verifier and bind it into `prepare()`
before any local claim or transport. It must open bounded private regular files,
verify exact inventories and digests, and require passing outcomes rather than
hash-shaped strings. For the disconnect proof it must bind the exact Dropbear
server build and options, target shell, monitor source and enabled-package
identity; one no-PTY connection and one claim; deliberate transport loss; an
independent later reconnect/export; complete preservation of every available
bounded member; terminal/reaped monitor status; and absence of a surviving
monitor, observer, tty1 or input reader. Missing, altered, failed, inconclusive,
late or nonterminal evidence must refuse. Mutation fixtures must prove each
binding and outcome is enforced.

After that validator exists, one separately reviewed bounded target disconnect
proof must produce the exact passing receipt. That proof is not the keyboard
capture and grants no keyboard result. Only its independently reviewed digest
may populate the later admission. The already accepted full-duration receipt
may then be consumed through the same semantic verifier; it records one passing
213.053-second harmless ARM64/QEMU lifecycle and explicitly records that no
enabled monitor was built.

No kernel/DT source or kernel build is needed for this repair. Subsequent, still
required preparation is mechanical: add an explicit enabled userspace build
mode for the frozen monitor source, build it once through Buildbox with two
identical static ARM64 replicas and `production_entry=enabled-admission-v1`, pin
the package/binary, remove the host execution refusal only in the reviewed
enabled revision, capture fresh candidate-bound input/capability/resource and
custody receipts, and obtain the required Astra review of exclusive reader,
disconnect, power/budget and recovery ownership. These steps do not alter the
one-blocker diagnosis above.

## Exact observation scope

The protocol is internally exact and remains unchanged: 20 indexed cases,
142 press/release edges, 71 presses, and 25 distinct Linux keycodes
`2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 18, 25, 28, 29, 30, 35, 38, 42, 54, 56,
103, 105, 106, 108, 125`. The two-second idle preflight plus twenty ten-second
windows is 202 seconds. It covers F1-F10, Home, Page Up, Page Down, End, both
Shift cases, Ctrl-A release order, Alt-A, Fn release and `HELP` plus Enter.
It does not cover all matrix positions, rollover, repeats, unlisted combinations
or release reliability. `capture_sessions` is one and no retry is admitted.

## Readiness evidence matrix

| Predicate | Evidence and decision |
| --- | --- |
| Frozen audit inputs | All ten work-item SHA-256 values and parent `fa29ac5949416774f3bb5b46e76b34e8e4d049f8` match. |
| Kernel/DT/config | Adequate only as the exact baseline candidate above: keyboard fragments, AW9523 matrix, map, tty1, USB and CPU0-7 contracts were composed and observed. No new kernel candidate is justified. |
| Baseline and recovery | Baseline USB/console/input observation passed. Supplemental changed-ID Gemian recovery is accepted for preparation only; original native-request disconnect and aggregate remain inconclusive. |
| Protocol/classifier | Exact 20 cases/25 keycodes verified mechanically. Existing 26 packet tests and protocol rendering pass. Classifier never promotes hardware support. |
| Duration and supervisor | Exact frozen monitor source has a passing 213.053-second harmless ARM64/QEMU duration receipt. Normal success requires reaped exit 0 in `[202000,210000)` ms; TERM/KILL/final ceilings are 210/214/215 seconds. |
| One-shot and partial evidence | Remote `mkdirat` is the retained one-shot claim. Four bounded files are exported independently and all available partial members are preserved. Capture launch consumes the claim even on refusal or interruption. |
| Input/tty exclusion | Pre/post guards reject known processes and all open tty0/tty1/console/input descriptors, with finite 512-process/4096-descriptor bounds. Continuous ownership currently relies on custody evidence; that evidence is only hash-shaped and therefore is not admitted. |
| Disconnect | Blocked: no exact passing Dropbear disconnect receipt or semantic verifier. |
| Enabled package and host gate | Not yet produced. The accepted size package is disabled, the duration package built no enabled monitor, `monitor.c` defaults off, and `capture.py` refuses execution. |
| Candidate/runtime admission | Queue is unselected; candidate record is null; fresh boot ID, event/minor, ancestry, capabilities, resource links, logger age, stable power, owner readiness and custody are not frozen. |
| Final recovery | Must be a later attributable changed-ID known-good Gemian confirmation. The old recovery budget is consumed and cannot be replayed as the new session result. |

## Finite later session, refusal and recovery outline

Once every offline gate above passes independent review, the finite order is:
validate exact candidate and recovery closure; guarded boot2 installation only
if its full-partition checksum differs; clean shutdown; one owner physical boot2
selection; fresh authenticated metadata and exclusive-reader preflight; one
delivery; one 20-case capture; one independent export; preserve logs and assess;
clean recovery request; one owner physical known-good selection if needed; and
changed-ID Gemian confirmation. Delivery, capture and export have respective
transport ceilings of 30, 240 and 30 seconds; the original logger lifetime is
600 seconds and is never reset. Stable external power is required throughout.

Any identity, map, capability, ancestry, reader, tty, logger, power, timing,
screen, USB, held-key, partial-file, process-terminal or recovery mismatch
refuses the affected phase. Preserve the existing claim and all available
evidence; release every key; do not retry, automatically reboot, select another
candidate, start a shell after tty restoration failure, or delete remote files.

## Checks actually run and unresolved risks

`test_packet.py` passed 26 tests; `render_protocol.py` reported an exact header;
`capture.py` and `classify.py` compiled with Python's bytecode compiler. Protocol
counts were independently recomputed. The ten frozen hashes and parent commit
were recomputed and match. No build, device access, private raw-evidence read,
installation, boot, key press, capture, power action or recovery action occurred.

Unresolved risk is intentionally concentrated at the stop: actual Dropbear
disconnect behavior and continuous reader release are unproven. Enabled ARM64
package construction, fresh runtime metadata, owner timing, stable-power/custody
evidence, target evdev/VT behavior and post-session recovery also remain untested.
A build would not establish any of those hardware or process-ownership claims.
