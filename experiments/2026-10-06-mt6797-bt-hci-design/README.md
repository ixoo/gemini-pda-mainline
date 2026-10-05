# Design: MT6797 Bluetooth HCI device over STP task 0

| Field | Value |
| --- | --- |
| ID | `2026-10-06-mt6797-bt-hci-design` |
| Status | Design for coordinator review; no code |
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
