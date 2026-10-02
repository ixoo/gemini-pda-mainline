# MT6797 boot receive rejection metadata

The [counter-observation boot](../2026-10-01-mt6797-tx-status/results/runtime-1.json)
completed capability but stopped the boot-debug drain with `-EPROTO` after two
recognized events. Its log did not identify the rejected packet. Do not
reclassify that refusal as a successful counter test or repeat its artifact.

Patch 0071 records transfer flags and logical length/type from the existing
bounded read before its existing admission check. For a successfully returned
8-byte-or-larger `0xe000` event, it also records ID and sequence. It logs no
body, does not parse an unknown data layout, and adds no HIF access, packet,
retry, control write or acceptance rule. The selected profile adds only this
patch and a distinct release to the predecessor's exact patch/configuration
selection. It remains a diagnostic, not a usable station driver.

## One-boot protocol

Hypothesis: the drain refusal is attributable to an additional event or a
specific existing receive-transfer boundary. The unique observations are at
most eight read-result records and eight event-header records from the same
existing packet budget. Transfer flags distinguish a failing transport/header
boundary from successful RX followed by class rejection. If an unknown event
appears, identify its exact selected source/firmware contract before admitting
it. If it is a malformed length or transport failure, diagnose that boundary
before another candidate. Do not discard unknown packets to reach configuration.

The [parent protocol](../2026-10-01-mt6797-tx-status/README.md#one-boot-protocol)
owns the one WMT/START, configuration, three status snapshots, exact finite
deadlines and status-consumption effects. All its stop conditions and refusal
rules remain intact. If configuration and the post pair complete, use their
actual CPU/free-pool deltas to decide whether conservative reconciliation is
supported. No credit refund, interface, scan, new RF request, IRQ enable or
packet DMA is added. Preserve the complete private log, same-boot wiphy query
and A53 regression before reviewed recovery and independently verify changed
Gemian identity and carrier. Owner physical boot2 selection is required.

## Validation

Linux 7.1.3 checkpatch on the exported patch reports zero errors and warnings
with `--no-tree --no-signoff`; its optional spelling and const-structure lists
were unavailable. No DCO certification or submission readiness is claimed.
The change records existing results only, so no synthetic transport behavior
is introduced or claimed. The [clean pushed Buildbox build](results/build.json) and
[candidate validation](results/candidate.json) passed. The
[offline preflight](results/preflight.json) records the wrapper, installer and
A53 recovery dependency checks. Six Python AST checks, bounded metadata
classifier fixtures and generated installer/wiphy shell syntax and ShellCheck
passed. The [runtime result](results/runtime-1.json) identified the refused
packet without changing admission.

## Runtime and selected-source result

The [deployed candidate](results/deployment.json) completed one WMT/START and
capability. The existing reads returned 89-byte and 80-byte debug events,
then a complete 12-byte `0xe000` event, ID `0x07`, sequence 0. The drain refused
that third event with `-EPROTO`; its post-read WRPLR was zero. The metadata
witness distinguishes class refusal from transport/header failure. The
sleepy-state payload byte was not logged, so its value is not established.
Configuration, wiphy registration and post-configuration counters did not run.

The [pinned source receipt](results/sleepy-sources.json) identifies `0x07` as
unsolicited `EVENT_ID_SLEEPY_INFO`: an eight-byte event header plus a four-byte
body containing one sleep-state byte and three reserved bytes. The RX handler
records this state and, in the multithreaded path, wakes the HIF worker for a
nonzero state. That worker marks the request and releases its power reference.
The PM macro only calls firmware-own when the sleepy state is set and the
active power-reference count is zero; the firmware-own function then writes
WHLPCR. The event itself is neither a host ownership-release command nor an
observed ownership readback. The next bounded initialization can retain its
active host ownership, accept only this exact notice and verify WHLPCR's driver
ownership before continuing. No implicit low-power handoff is justified.

Complete private evidence was preserved, the A53 RAM-service regression and
provider query passed, and reviewed recovery returned a changed Gemian boot.
Independent SSH confirmed the recorded identity, `3.18.41+` and WLAN carrier 1.
This candidate is consumed. No packet bodies, private record bytes or raw
returned-page counters are published. Wi-Fi remains unusable in mainline.
