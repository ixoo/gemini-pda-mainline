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
passed. No runtime result exists yet.
