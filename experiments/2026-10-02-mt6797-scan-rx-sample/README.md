# MT6797 early receive statistic samples

Status: one diagnostic lifetime consumed; all four early samples and the
ordinary management count were zero, with no host frame or BSS. Changed-boot
Gemian recovery confirmed.
This is a measurement toward receive support, not working Wi-Fi.

The [tuning sample](../2026-10-02-mt6797-scan-tuning-sample/results/runtime-1.json)
matched channel software state while the ordinary scan counter and host BSS
result remained zero. The
[receive-boundary analysis](../2026-10-02-mt6797-scan-tuning-sample/results/receive-boundary-analysis.json)
identifies byte updates earlier in the selected receive routine than the
mode/processing-gated ordinary counter. The
[Gemian reference](../2026-10-02-gemian-passive-scan-reference/README.md)
returned recent probe-response BSS information with different association and
possibly active-scan conditions. Neither result identifies the mainline receive
failure.

## Hypothesis and single-session protocol

Hypothesis: management packets may enter early firmware processing and then
bypass the ordinary scan counter or host delivery. The unique observation is
two pairs of earlier probe-response/beacon statistic bytes during the same
500 ms passive channel-40 scan, alongside the ordinary counter and host results.

Patch 0082 retargets the existing four-query sampler in a new isolated profile.
It reads exactly the aligned ordinary RAM words `0xf006bf38` and `0xf006bf3c`.
The selected probe-response statistic is word 0 bits 31:24; the beacon statistic
is word 1 bits 7:0. Other packed bytes are retained but not interpreted as
receive evidence. This has no arbitrary address, target write, hardware-register,
special-prefix, calibration or filter interface. The retained ordinary query
branch performs one target load; request-buffer, reply allocation/queue and
normal TC4 debit effects are admitted as in the validated parent.

Keep firmware, private record, board DT, authenticated userspace, broadcast
filter and BSS setup unchanged. Issue pair 0 no earlier than 100 ms and pair 1
no earlier than 300 ms after scan submission. Keep one outstanding query, fresh
shared sequence/history, exact address/sequence matching and a 100 ms reply
deadline. There are at most four queries and no reply credit refund. Retain the
five-second scan deadline, 256 polls, sixteen packets per tick, 4096 packets
overall and retired lifetime. DONE permits only the existing bounded RX tick;
no later query or polling extension is allowed. Pending, missing, duplicate,
late, malformed or unmatched replies make the diagnostic incomplete and retire
it without extra cleanup I/O. Do not retry this lifetime.

The pairs are non-atomic. Eight-bit values can wrap at 256 or be reset; there is
no pre-scan baseline or complete writer/callback audit. Selected scan-state
paths clear them, but execution of that reset is not proved by source analysis.
Changes are reported modulo 256, never as an exact packet count.

- Changed or nonzero early statistics with ordinary count zero: support early
  processing as an alternative to no reception; inspect later processing gates,
  while retaining reset/other-writer and attribution limits.
- Unchanged zero samples and ordinary count zero: leave radio reception, entry,
  filtering, timing, reset and wrap unresolved. Do not claim RF silence.
- Positive ordinary count without host frame: prioritize firmware-to-host delivery.
- Valid host beacon and standard BSS: demonstrate management reception only for
  the exact candidate; association and traffic remain subsequent requirements.
- Incomplete queries, transport or ownership failure: preserve an inconclusive
  result and retire the lifetime.

Before a boot, validate Buildbox provenance, exact candidate and all tool/source
pins, guarded live-GPT boot2 installation and full readback. The owner selects
boot2 physically. Verify live release and changed boot identity before the sole
START. Preserve unique evidence before reviewed recovery and confirm changed-boot
Gemian. No probe transmission, association, key, data TX, IRQ enable or packet
DMA is added by this experiment.

## Source validation

The [source review](results/source-review.json) binds the whitelist, finite
budgets and unchanged parent lifecycle. All 264 prior profile objects remain
unchanged; the new series is the parent plus one canonical-order patch. The
focused wire test checks the exact new addresses, rejects both retired tuning
addresses, and retains malformed reply, sequence reuse, credit debit, capacity
and failed-transport checks. The classifier separately checks wrapping, zero
values, unrelated packed bytes, timing and malformed observations; neither
nonzero nor changed bytes set a receive-proof flag. Strict resulting-Kconfig
checking passes; the patch
check needs a documented config-description parser exclusion. Synthetic archive
authorship supplies no DCO certification; this is not submission-ready.

## Build and candidate

The [build receipt](results/build.json) binds the clean pushed source commit,
validated package and six independently matched Buildbox source files. The
[candidate receipt](results/candidate.json) binds the existing proven booted DT,
unchanged firmware/private record/userspace, release-only RAM-root transform and
exact 16 MiB boot2 padding. Physical admission remains false. Runtime wrappers
are retargeted to this manifest and release, with the standalone classifier's
source hash pinned. Complete their offline preflight and installer review before
any device write, then record the actual guarded deployment separately.

The [offline preflight](results/preflight.json) validates the private record,
authentication, reviewed recovery binary and generated installer. The published
RAM-root transform reproduces byte-identical bytes. Full capture/host preparation
remains pending actual deployment evidence and private session setup. No fake
receipt was supplied. The offline installer must be regenerated against fresh
live Gemian identity before execution.

## Deployment and physical handoff

The [deployment receipt](results/deployment-1.json) records the live-GPT guard,
exact predecessor, independent full-partition byte comparison and matching
checksum. Stable power was present; boot2 was separate from the live Gemian root.
The reviewed installer requested clean shutdown and confirmed LAN unreachability,
without reboot. Capture and host offline preparation now pass against this actual
receipt and private authentication, candidate and recovery inputs. Neither START
nor scan has been consumed.

The owner physically selects boot2 for release
`7.1.3-gemini-a53-wifi-scan-rx-sample`, boot image
`1be497945a2b9f01eaaf3632739d16e35741a19c12a8019596a789374718f48f`
and padded partition
`4a9499f1861dbc899edb7ebcdf54cf08e8c52a727794870469f13f686397385a`.
Verify a changed live boot and this release, then use the prepared capture once
for WMT/START and the prepared host once for the scan, evidence sealing and
reviewed Gemian recovery. The hypothesis and decision branches above remain the
pre-boot contract. Installation does not establish receive support.

## Runtime result and next decision

The [single runtime](results/runtime-1.json) completed on the exact candidate.
Four replies matched before DONE: probe-response/beacon values were both zero
in both pairs. The ordinary management count was also zero. The scan finished
after 528683 us with returned credit, no host management frame and no standard
BSS result. A53 serviceability checks passed. The complete log was sealed before
one reviewed native recovery; changed-boot Gemian and carrier were confirmed.
The host exit status was 1 because reception acceptance failed, while diagnostic
completion and recovery passed.

This does not support the specific alternative of observed early bytes bypassing
a later ordinary-counter gate. It also does not prove absence of RF reception: byte
wrap, resets, timing and unresolved earlier dispatch/filtering remain alternatives.
Inspect the path into the selected receive routine and earlier receive enabling
using retained firmware and vendor evidence before designing another measurement.
This boot and scan budget is consumed; do not repeat it. Mainline association
and traffic remain unproved.

## Earlier dispatch analysis

The [retained-firmware analysis](results/dispatch-analysis.json) identifies the
subtype table selecting the early receive routine for both beacons and probe
responses. Its dispatcher increments another statistic byte before selection.
That byte is the low byte of the already sampled word `0xf006bf38`, whose two
retained values were zero. This retrospective interpretation adds no device read
and leaves the original classifier intact. It is not a packet count or RF proof.
One immediate-pair caller is identified; its entry and preceding admission gates
remain unresolved. Resolve those gates before changing later management logic.
