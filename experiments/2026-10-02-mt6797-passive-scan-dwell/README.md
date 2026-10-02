# MT6797 passive scan with explicit channel dwell

Status: installed with full-partition readback; one scan consumed and evidence
preserved; reviewed recovery to changed-boot Gemian confirmed. The scan completed
with timing consistent with the request but received no management frame or BSS.
This candidate supersedes the unconsumed
[broadcast parent](../2026-10-02-mt6797-passive-scan-broadcast/README.md).

## Listening-time evidence

The [retained analysis](results/dwell-analysis.json) joins V2 payload offset 154
to the passive decoder's unchanged halfword, nominal default 100, selected dwell
state and timer argument. The timer splits at 60000 and its local conversion
uses 32768, 999 and divisor 1000, matching the millisecond timer API in the
pinned gen3 source. The arithmetic helper and physical clock remain unmeasured;
the host V2 TU comment alone is not the selected firmware path's unit proof.

The known-good connection's retained cache reported 5200 MHz and a 100 TU
(102.4 ms) beacon interval. This stale cache is context, not a new observation.
A nominal 100 ms window is shorter than one cached beacon interval. A 500 ms
request covers about 4.88 such intervals; unknown beacon loss and actual RF
scheduling still limit negative results. Firmware branches can shorten dwell,
including an unresolved internal-state clamp to 18. No register write or guessed
state repair is derived from that branch.

## Candidate change and finite protocol

Patch 0079 requests fixed 500 ms dwell and accepts exactly one currently
permitted channel per scan. The named profile appends it to the broadcast
parent in canonical order. Standard channel policy, private record, firmware,
broadcast setup, PIO owner and receive parser remain inherited. The test selects
channel 40 with `iw dev wlan0 scan freq 5200 passive`, with no SSID or probe TX.
A multi-channel request is refused before the lifetime or first write.

The one-boot observation is whether the new request reaches matching completion,
how long submission-to-completion takes, and whether a valid native beacon and
standard BSS appear on that channel. The candidate logs requested milliseconds,
channel count and host elapsed microseconds before cleanup. Host elapsed includes
setup, scheduling and delivery; even a long result is not measured RF dwell.
This scan is also the admitted bounded timing observation for the parent's
listening-time requirement; it does not assume all shortening branches are off.

Keep one scan, one filter submission, one BSS activation, the existing five-second
host deadline, 256 polls, sixteen RX packets per tick and 4096 packets overall.
The half-second one-channel request leaves time for grant/setup and delivery
within that unchanged deadline. Existing maximum-one cancellation/deactivation,
terminal no-retry and reviewed recovery remain mandatory. No active probes,
association, key operation, packet DMA, IRQ or direct radio/register write is
added. Build and exact boot2 identity checks must precede runtime.

A valid beacon/BSS establishes management reception for the exact candidate and
permits association design. A completed empty scan with elapsed time shorter
than 500 ms contradicts the intended nominal window and prioritizes firmware
timing/shortening diagnosis. An empty scan lasting at least 500 ms still leaves
actual RF dwell and tuning unverified; it cannot establish a filter cause or
justify repeating an identical image. Transport, ownership or protocol failure
stops I/O and retires the lifetime. Preserve evidence before reviewed recovery
and require changed-boot Gemian plus the inherited A53/provider regressions.

## Focused validation

The wire test checks the source-defined 500 ms halfword at offset 154, one-channel
layout, unchanged reserved/probe/timeout/IE bytes and refusal of multi-channel or
invalid requests without output mutation. Compile it with the selected patched
`scan-wire.h` and the existing
[compatibility header](../2026-10-01-mt6797-normal-sets/tests/test-compat.h), using
C11, Werror, ASan and UBSan. Kernel builds use
`./scripts/build-kernel --backend buildbox` from clean committed/pushed inputs.
No build or host fixture establishes Wi-Fi support.

## Build and offline preparation

The [build receipt](results/build.json) records the clean pushed kernel commit,
validated package and exact compiled MAC/wire/helper identities. The focused C
wire test passed with C11/Werror/ASan/UBSan. Strict checkpatch reported zero
errors, warnings and checks, excluding synthetic-signoff checking; optional
spelling/const lists were unavailable. All 262 profiles preserve canonical order
and the 261 existing profiles retain their inputs. Only the historical whitespace
and unused CPU-helper diagnostics remained; the changed MAC compiled cleanly.

The [candidate](results/candidate.json) preserves the proven booted board DT,
firmware, private board record, authentication and six userspace ELFs. Its RAM
root changes only the release gate; the published transform reproduced it byte
for byte. Container composition and full 16 MiB padding passed validation.
The [offline preflight](results/preflight.json) validates candidate/session
source pins, private authentication, reviewed recovery binary, exact tool
identities and generated installer/scan shell checks. Classifier fixtures retain
shortening, missing/duplicate timing and unknown RF dwell as distinct states.

The [offline preflight](results/preflight.json) is historical preparation evidence
from before installation. Its reference installer was not executed: a fresh live
Gemian identity bound the regenerated installer. Capture and host preparation
then passed against the actual full-readback deployment receipt. Installation,
START and the single scan are recorded below; the offline receipt remains unchanged.

## Runtime result

The [single runtime receipt](results/runtime-1.json) binds the validated candidate,
guarded boot2 installation, exact mainline boot and changed-boot Gemian return.
Gemian reported carrier and a 5200 MHz connection before installation and after
recovery. Pre-install cached beacon interval was 100 TU; its last-seen age was
95580 ms, so the cache is not a fresh beacon measurement.

WMT pre-start preservation and the single firmware START passed. The standard
passive scan on permitted channel 40 returned success, matching completion and
runtime credit. Requested dwell was 500 ms; host elapsed time was 513501 us.
No native management frame, validated beacon or standard BSS result appeared.
A53 service and provider checks passed; logs were sealed before reviewed recovery.
Raw captures and peer identifiers remain private. The host command exits 1 because
passive reception was not demonstrated, despite successful scan completion and
recovery.

This result supports nominal command timing, not measured RF listening time. It
does not establish whether channel tuning, firmware shortening, receive setup or
delivery caused the empty result. The next observation must distinguish those
paths using the selected Gemian/firmware contract; do not repeat this consumed
one-shot image or infer a filter cause from the empty scan alone.
