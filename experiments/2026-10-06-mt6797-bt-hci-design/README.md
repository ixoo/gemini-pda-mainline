# Design: MT6797 Bluetooth HCI device over STP task 0

| Field | Value |
| --- | --- |
| ID | `2026-10-06-mt6797-bt-hci-design` |
| Status | Design approved; implementation compile-only, not booted |
| Date | 2026-10-06 |
| Device action | None |

## Why now, and why it is bigger than H1

[C3-3](../2026-10-05-mt6797-bt-h1/RUNTIME_3.md) proved that the ROM answers
WMT Bluetooth function-on and plain HCI commands on STP task 0. The next step
the [Bluetooth record](../2026-10-04-gemini-bluetooth-re/README.md) names is a
small `hci_dev`, so BlueZ can drive the controller.

The current transport cannot carry that. Each exchange registers the BTIF
interrupt, sends one command, waits for one reply on one task and frees the
interrupt. A controller sends unsolicited events (inquiry results, connection
events, ACL data), so an `hci_dev` needs a receive path that is always on and a
transmit path that is not tied to a single expected reply. That is the concrete
need for the new code below; nothing else is added.

## Shape

Two pieces, both in the existing experimental CONSYS area.

**1. A persistent full-STP link (CONSYS owner).** Once negotiation (and later
common init) completes, the owner keeps the BTIF interrupt registered for the
rest of the boot.

- **RX.** The interrupt handler drains the FIFO into the existing stream
  parser, validates frames with the existing link state, and delivers each new
  data frame to the bound client for its task through the existing
  `stp_full_task_deliver()` routing. ACK owed is sent from the same context.
- **TX.** One queue of whole payloads per task, sent in order. The existing
  seven-frame window and cumulative ACKs gate it. No retransmission in the
  first version: an ACK timeout is reported as a link failure and stops the
  link, matching the current first-failure policy.
- **Clients.** WMT keeps its command/event use through this link. Bluetooth
  registers a task-0 client. GPS and Wi-Fi function control can follow later.

**2. A small HCI driver (`btmt6797`).**

- Registers one `hci_dev` with bus `HCI_UART`, like `btmtkuart`.
- `open` sends WMT Bluetooth function-on and enables VCN33-BT, as H1 did, and
  binds the task-0 client. `close` reverses it.
- `send` queues the H:4 packet (type byte included) on task 0.
- Received task-0 payloads go through `h4_recv_buf()` with a stub `hci_uart`,
  as `btmtkuart` does, to `hci_recv_frame()`.
- `set_bdaddr = btmtk_set_bdaddr`, available but not needed: H6 showed the
  controller reports a non-placeholder address.
- No vendor init script, sleep parameters, radio settings or power saving
  (H5). The core's own HCI Reset and reads run at power-on.

## Order of work

1. Link engine with host fixtures: continuous RX across many frames and tasks,
   ACK generation, the window, unknown-task refusal, and failure stopping the
   link. Reuse the existing fixture style and sanitizers.
2. HCI driver on top, with a host test of the H:4 path.
3. A device boot: `hciconfig hci0 up`, read the version through BlueZ, one
   inquiry scan. It needs BlueZ tools in the RAM root, a protocol and owner
   approval.

## Out of scope for the first version

Retransmission, link resynchronization and reset recovery; WMT sleep and the
BTIF wake pulse; SCO over CVSD; coexistence with a running Wi-Fi; upstream
submission. Each is recorded in the Bluetooth record's hypotheses.

## Questions for review

- Keep the persistent link in the CONSYS owner, or split it into its own
  file now? Splitting adds no behaviour; it only eases review.
- Is a link failure on ACK timeout acceptable for the first device boot, given
  there is no retransmission?

## Implementation (2026-10-07)

The coordinator approved the design for offline implementation with no
device test. Four experiment-only patches form the
`mt6797-a53-bt-hci-compile` profile, which is the Phase A series plus:

- [0116](../../patches/proposals/0116-soc-mediatek-add-a-persistent-MT6797-full-STP-link-engine.patch),
  the pure link engine `mt6797-stp-engine.h`;
- [0117](../../patches/proposals/0117-dt-bindings-soc-mediatek-mt6797-consys-add-the-Bluetooth-HCI-flag.patch),
  the `mediatek,bt-hci` flag, which requires negotiation and the Bluetooth
  supply and excludes the one-shot Bluetooth and common-init flags;
- [0118](../../patches/proposals/0118-soc-mediatek-run-a-persistent-MT6797-STP-link-for-Bluetooth.patch),
  the CONSYS glue and the exported attach, detach and send calls;
- [0119](../../patches/proposals/0119-Bluetooth-add-an-experimental-MT6797-CONSYS-HCI-driver.patch),
  the `btmt6797` HCI driver.

The release is `7.1.3-gemini-a53-bt-hci`.

### Behaviour

- **Ownership.** The CONSYS owner keeps the BTIF interrupt, the link and the
  Bluetooth rail. The hard IRQ handler drains RX, routes frames, refills the
  TX FIFO and calls clients only under one spinlock; it never sleeps and does
  no regulator or WMT work.
- **WMT.** Commands run in process context under a mutex and wait 2 s for
  their event. Unsolicited WMT events are counted and dropped.
- **Bluetooth.** Attach enables VCN33-BT and sends function-on; detach sends
  function-off and drops the rail only after its event. The driver copies each
  task-0 payload in IRQ context into a 16-slot ring and refuses it when full,
  so the controller resends; a work item reassembles H:4 and hands packets to
  the core. Send waits up to 1 s for queue room.
- **Failure.** Malformed STP input, a 2 s ACK timeout or a WMT command timeout
  stops the link once: interrupts off, waiters completed, queued frames
  dropped, and the HCI core told through `hci_reset_dev()` from process
  context. Power, clocks and rails stay as they are. There is no retry or
  resynchronization.

### Deviations from the design

- **No DT child node.** The owner registers a `btmt6797` platform device itself
  when the link starts, so the binding gains only one flag.
- **Own H:4 reassembler.** `btmt6797-h4.h` replaces `h4_recv_buf()` so that
  reassembly across STP frames is host-testable.
- **No `set_bdaddr` hook.** No address write path exists, as required;
  `btmtk` is not needed.
- **First version is Bluetooth-only.** The flag excludes common init, so Wi-Fi
  and the persistent link are not combined yet.

### Tests

- [test-stp-engine.c](test-stp-engine.c) compiles the real engine with ASan and
  UBSan. It covers interleaved unsolicited WMT and Bluetooth frames with task
  routing, one ACK covering several frames, the shared seven-frame window with
  an eighth queued message, piggyback ACK retirement, queue bounds, unbind and
  client refusal without credit followed by redelivery, ACK-timeout fail-stop
  that drops the queue, and malformed-input fail-stop.
- [test-bt-h4.c](test-bt-h4.c) feeds an event, a maximum-size ACL packet, an
  empty event and an SCO packet split at every chunk size from 1 to 39, and
  checks bad types and oversize lengths.
- All four patches pass strict checkpatch, excluding only the missing
  sign-off, the new files' maintainer entries and inherited spelling. The
  binding passes `dt-doc-validate`; a test DTB with the flag validates, and it
  is rejected with the one-shot Bluetooth flag or without negotiation.

IRQ and work teardown, and the HCI core's behaviour, are covered by review and
compilation only. A device test needs BlueZ tools in the RAM root, a protocol
and owner approval.
