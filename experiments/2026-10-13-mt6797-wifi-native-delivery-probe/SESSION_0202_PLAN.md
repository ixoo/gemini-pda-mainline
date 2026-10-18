# 0202 session preparation — UNBUILT, NOT ADMITTED

The owner's latest order supersedes the earlier six-second trial preparation:
scan/group regression first, controlled SSH priming A/B, then a staged sustained
window. No new kernel build or device action has occurred. The local 0202
ownership prototype remains unbuilt. This document is preparation, not a result.

## Scan prerequisite result

The actual C10 and local 0202 `mt6797_mac_scan_packet` function, `scan-wire.h`,
`native-beacon.h` and `action-frame.h` are byte-identical. Scan frames are
selected by descriptor type, independently of the requested metadata mask.
The scan decoder walks G4/G1/G2/G3 as 16/16/8/24 bytes, then optional two-byte
padding. It requires G3 for RCPI and checks bounds before reading vector/MPDU.
The handler queues only the decoded MPDU with channel/frequency/signal.
Unsupported forms are withheld; malformed lengths are errors.

The existing scan-report fixture covered only G3. Its
[actual-source cases](../2026-10-07-mt6797-wifi-phase-b-join/tests/scan-report-test.c)
now cover all 16 masks, padding both ways, beacons and probe responses, exact
queued bytes, missing-G3 withholding and every truncation before the required
fixed fields. ASan/UBSan passed locally against both source trees. The runner's
Linux-only non-PIE flags are now conditional for local Clang. An initial local
invocation failed at that compiler flag, before executing any case.

The existing [joined-beacon fixture](tests/native-beacon-test.c) already covers
all 16 masks and padding, strict addresses/status/frame shape and truncation;
it also passed against 0202 locally. The class7 keyed-beacon selector remains
strict about its existing shape; it is not broadened to reinterpret class2 or
scan frames. These are host parsing results, not proof of firmware behavior
after requesting mask 7 before scan-ready. Linux ASan/UBSan scan delivery and
joined-beacon cases, and all seven A/B helper tests, passed from clean pushed
input `cf927f441e58369912687b49faaa2e50d4f0aff0` against the retained C10 source.
Its scan headers and MAC digest matched the frozen local C10 source. The 0202
scan function/headers are identical; the full 0202 prototype has not received
Linux validation. Repository checks passed locally; no kernel build or device
test ran. No framing check or production decoder changed for this prerequisite.

## Controlled SSH A/B

Hypothesis: an otherwise healthy session can fail before TCP acceptance because
the laptop needs group ARP delivery. Device-originated traffic to the laptop may
populate its neighbor entry. C11's acquired data accounting contains no extra
unicast SYN, but does not observe losses before acquisition. Timing correlation
does not establish the ARP/cache cause; the long-gap passing run contradicts a
simple expiry-only model.

The [prepared operation](ssh-prime.py) is deliberately not wired into the old
C10 session or admitted as a standalone tool. The future 0202 adapter must bind
the validated candidate, fresh boot, ACTIVE ready block, listener and lease.
Preflight must independently verify the laptop's current numeric LAN IPv4
address on the actual routed Wi-Fi interface, excluding the device lease,
router, USB endpoint, network and broadcast addresses. DHCP/local interface
evidence stays private. No hostname resolution, cache flush, packet capture,
laptop privilege or alternate device control API is allowed.

Preassign alternating OFF/ON arms before boot; never select an arm after reading
neighbor state. After fresh readiness:

1. Read numeric route and laptop neighbor entry for the device's fresh lease.
2. ON: one guarded USB command makes the device ping the laptop's verified LAN
   address through `wlan0`, once, with a two-second reply limit and three-second
   process limit. Recheck boot, exact ready identity, listener, ACTIVE and fatal/
   terminal gates before ping. OFF: no device ping.
3. Read the neighbor entry again, then perform the original boot-bound Wi-Fi
   SSH authentication/challenge. Retain stdout, stderr and process exit/timing.
4. Read neighbor state afterward, including after a failed SSH attempt.

Local reads retain D2's 0.5-second limit. The optional operation and reads consume
the original exchange budget of at most 25 seconds; they cannot extend it.
Unknown query results are not absent entries. A guard/transport refusal prevents
SSH; an unanswered admitted ping is recorded and SSH is still observed. No retry.
Seven focused helper cases pass locally: arm ordering, no control-arm ping,
guard refusal, unanswered ping, query timeout, shared-budget exhaustion and
non-numeric/non-unicast refusal. Runtime binding and sustained SSH are pending.

Decision branches: compare successful priming plus actual neighbor change against
OFF runs, not merely arm labels. Failures with a present neighbor require the
client failure stage (TCP/KEX/auth) and separate transport evidence. An ON pass
or OFF failure alone is not causation. No DHCP/listener/ACTIVE means the A/B was
not reached. Do not continue an invalid or shortened run as a successful sample.

## Duration conflict and smallest proposed change

Current C10 limits, also retained by the ownership prototype:

| Source limit | Consequence |
| --- | --- |
| `mac.c`: request 9,000 ms; `join-commands.h`: request ceiling 10,000 ms | A 60-second grant is currently refused by host encoding. |
| Actual grant minus 2,500 ms tail minus association/key setup | Explains a roughly six-second available data phase; only the actual grant event establishes its expiry. |
| `native-diag.h`: wall 10,000 ms | Independently prevents a 60-second ACTIVE observation. |
| `mac.c`: data budget 60,000 ms | Already sufficient for the first stage, insufficient for 120/600 seconds. |
| 4,096 worker polls; 20 ms scheduled cadence | About 81.92 seconds at nominal cadence; no assurance of a 120-second lifetime. The exact counter remains authoritative. |
| RX 512 frames / 1 MiB; checked PTK 64; data PIDs through 126 | Any may end a run earlier, including beacon traffic or sustained SSH. No reuse or counter reset is permitted. |
| `join-ccmp.sh`: listener 90 seconds, overall 300 seconds | Blocks later 120/600-second stages. Its current SSH proof is one exchange, not sustained authenticated traffic. |
| Existing SSH helper: one process exchange capped at 25 seconds | A successful one-shot exchange cannot demonstrate sustained authenticated traffic for 60 seconds. Keep initial identity/authentication admission within this cap; sustained observation needs a separately bounded post-authentication phase in the same owned SSH process. |
| Teardown 5,000 ms; grant tail 2,500 ms; command 100 ms; frame/drain 750 ms | Preserve these failure/cleanup limits; do not make timeouts disappear by increasing them. |

Owner-approved first-stage preparation, implemented as a separate unbuilt
[0203 patch](../../patches/proposals/0203-wifi-mt6797-bound-first-fixed-format-window-to-60s.patch):
request 65,000 ms and narrowly admit that request in the encoder; retain the
matching token/channel grant validation and refuse a nominal 60-second trial
unless at data opening at least 62,500 ms of granted ownership remains. Raise
only the diagnostic observation wall to 60,000 ms. The existing data budget is
already 60,000 ms. A 32-bit interval field can encode this request, but does not
prove firmware will grant it: a smaller/refused grant is a distinct admission
failure, never a shortened pass. No renewal, new callback interpretation or
speculative register access is proposed. The owner explicitly approved preparing this exception while keeping kernel
builds on hold. All other limits below remain unchanged; this approval is not
a build or device admission.

Keep all other resource, poison, PN, transaction and cleanup limits. If one ends
the run before 60 seconds, report its exact counter/time as the first sustained
operation failure and stop. Do not silently increase it. A later 120-second and
then 600-second stage needs a separate evidence-based budget/ownership review;
they are not authorized by the first-stage proposal. Update the owned session's
bounded SSH operation to keep authenticated traffic throughout the admitted
window, binding the same boot/listener and checking every scheduled exchange;
an initial successful login does not count as a full-duration pass.

Rekey, key reuse, reconnect and GTK delivery remain disabled. Therefore one
lifetime per boot is the current maximum; batching several lifetimes in one
boot would violate those boundaries. A three-run sample cannot establish a
15–20% failure rate: under independent trials, 19 runs are needed for a 95%
chance of seeing at least one 15% failure (14 for 20%). These are sampling facts,
not permission for unattended repeats or evidence that runs are independent.
Each run needs its own reviewed handoff and owner boot2 selection.

## Evidence and later work

Use exactly one sanitized scalars JSON and one table row per run, with links to
sealed private evidence rather than a new per-run result document. Retain arm,
boot/image/source identity, grant interval and available budget, neighbor
before/after-prime/after-SSH status, ping exit/results, SSH stage and monotonic
failure offset, resource counters, actual/planned duration and independent
transport/network/cleanup verdicts. Unknown is explicit. Raw client/query logs
remain in the existing private evidence seal, not public scalars.

| Run / arm | Boot ID | Transport | DHCP | Individual pings | SSH / failure stage | Cleanup | Actual / planned duration | Scalars |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

No 0202 run has occurred. Stop for a physical handoff only after a validated
build/package, reviewed session preparation and guarded install/readback/clean
shutdown. After reporting the 0202 result, the next design item is strict GTK
delivery with per-frame group PN checking grounded in C11's observed metadata.
No GTK implementation is part of this preparation.
