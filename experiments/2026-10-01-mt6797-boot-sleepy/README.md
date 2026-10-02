# MT6797 boot sleepy notification under active ownership

The [header boot](../2026-10-01-mt6797-tx-status-header/results/runtime-1.json)
identified a complete 12-byte event `0x07` after two debug events. The
[pinned gen3 source](../2026-10-01-mt6797-tx-status-header/results/sleepy-sources.json)
handles this as a sleep-state notification and only requests firmware ownership
when active power references have been released. The previous candidate refused
it; it did not exercise configuration or post-configuration page counters.

Patch 0072 accepts this exact notification while keeping initialization's active
power/HIF owner. It requires the already-validated `0xe000` event, ID `0x07`,
exactly 12 logical bytes and state 0 or 1. The source's byte carrier does not
itself define an enum range; refusal of other values is this diagnostic's
conservative admission policy. Header sequence and reserved bytes are not an
ACK or a private calibration input and impose no invented zero requirement.
Reuse the existing serialized logical WHLPCR reader once per admitted notice,
and stop unless its driver-own bit is set. Do not release ownership, poll for
it, or copy the vendor's low-power worker.

## One-boot protocol

Hypothesis: the source-defined notification can be handled under retained host
ownership, allowing the reviewed configuration sequence and post-counter pair.
The unique observations are its decoded state, one WHLPCR read, drain counts
separating debug and sleepy notices, and the existing post-configuration page
counters. The total boot receive budget stays eight packets, with at most eight
logical WHLPCR reads and one shared one-second drain deadline. The first
malformed or unadmitted notice, lost ownership, unknown event, port-1 packet,
transport/deadline failure or excess packet stops the session. Do not consume
another packet or repeat the candidate after a failure.

The [original counter protocol](../2026-10-01-mt6797-tx-status/README.md#one-boot-protocol)
owns all WMT/START, configuration, status-consumption and post-pair budgets.
No explicit RF request, IRQ enable, firmware-own write, packet DMA, interface
or credit refund is added. If the post pair completes with attributable
CPU/free-pool deltas and clearing, implement conservative reconciliation next.
Uncleared, zero or unattributable counts require a changed acquisition diagnosis.
Successful configuration PIO still does not prove firmware application or RF
power. Preserve complete private evidence, same-boot wiphy observation and A53
regression, then use reviewed recovery and independently confirm changed
Gemian identity and carrier. Physical boot2 selection remains an owner action.

## Focused validation

`tests/boot-drain-test.c` compiles the actual patched drain function against
bounded injected receive and ownership callbacks. Strict C11 warnings-as-errors
and ASan/UBSan pass for all 256 state bytes, all 256 event IDs, lengths 0–16,
wrong packet type, missing driver ownership, first and later ownership-read failures,
RX failure, port-1 conflict, empty queue and the eight-packet bound. It verifies
the one-second deadline and existing reader's logical register 4 at every call;
it does not emulate the HIF bus or firmware behavior. The HIF implementation
is unchanged from the tested counter candidate.

To reproduce, extract only `mt6797_consys_drain_boot_events` from the exact
selected prepared source into a temporary `boot-drain-under-test.inc`, compile
the fixture with that temporary include directory and
`cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -fno-sanitize-recover=all`,
then execute it and remove the temporary include/binary. No kernel source tree
is stored here. Linux 7.1.3 checkpatch reports zero errors/warnings with
`--no-tree --no-signoff`; optional spelling and const lists were unavailable.
No DCO certification or upstream submission readiness is claimed. Buildbox,
offline candidate and device validation remain pending.
