# MT6797 passive scan firmware counter

Status: source review, Buildbox build and candidate validated; deployment and
runtime pending.

The [500 ms parent](../2026-10-02-mt6797-passive-scan-dwell/results/runtime-1.json)
completed after 513501 us with returned credit and no management frame or BSS.
Timing alone cannot distinguish firmware reception from host delivery.

The [retained analysis](results/counter-analysis.json) joins the ordinary
24-byte completion counter to increments in a firmware routine that processes
beacon and probe-response frame-control values. Some probe paths can increment
twice. Record it as a management-processing counter, not a unique-beacon count.
The public gen3 header calls it u4ScanDurBcnCnt; its debug handler interprets
that field for completion versions greater than two. The selected retained
constructor supplies the counter regardless of that host debug condition.

Patch 0080 records version, counter and PNO indication only after the existing
completion validator succeeds and before its already-read packet is cleared.
It adds no command, register access, radio operation or timing change. The
isolated profile appends it in canonical order and changes only the release
gate relative to the parent. This archive uses a synthetic author without DCO
certification and is not submission-ready.

## Single-session protocol

Hypothesis: firmware processes management frames during the scan but host PIO
receives none. The unique observation is the existing completion counter joined
to host management-frame/BSS results and timing for one passive channel-40 scan.

Preserve the parent firmware, private record, DT, authentication and userspace.
Admit one supported broadcast-filter submission, one BSS activation and one
500 ms passive scan on the currently permitted known-good channel. Keep the
parent five-second deadline, 256 polls, sixteen RX packets per tick, 4096 total
packets, cancellation/deactivation bounds and terminal no-retry behavior.
No active probes, association, keys, packet DMA, IRQ or direct radio/register
write is added. Verify the selected candidate and exact boot before START;
preserve evidence before reviewed recovery and confirm changed-boot Gemian.

- Positive firmware counter with no host frame: prioritize forwarding and
  firmware-to-host receive delivery. This is no RF dwell or peer-validity proof.
- Zero counter with no host frame: investigate channel setup and receive paths
  before that processing point; neither radio silence nor a filter cause is proved.
- Valid beacon and standard BSS: establish management reception for that exact
  candidate and proceed to association design.
- Missing/malformed completion, unknown version semantics, transport or ownership
  failure: preserve the result as inconclusive and retire the lifetime.

A repeated empty result must change the diagnosis rather than justify an
identical re-run. The old parent lifetime remains consumed. Build and package
validation, guarded live-GPT boot2 installation, full readback and owner physical
selection precede hardware testing. Source analysis and a build are not support.

## Build and candidate

The [build receipt](results/build.json) records clean pushed inputs, validated
package and independently checked compiled-source hashes. The MAC compiled
without a new diagnostic; strict checkpatch and repository checks passed. All
263 profiles preserve canonical order and the 262 existing profiles retain
their inputs. No kernel/DT change beyond the diagnostic and release is added.

The [candidate receipt](results/candidate.json) binds the proven booted board
DT, parent firmware and private record, authenticated userspace and exact
16 MiB padding. The published RAM-root transform reproduced its output byte
for byte; only the release gate changes relative to the consumed dwell parent.
The focused classifier checks positive/zero counters, duplicate/missing records,
version and integer bounds, PNO extent and unchanged RF-dwell limitations.
The [offline preflight](results/preflight.json) also verifies private authentication
and the reviewed recovery binary against the RAM root. Capture and host
execution still require actual verified deployment evidence.
