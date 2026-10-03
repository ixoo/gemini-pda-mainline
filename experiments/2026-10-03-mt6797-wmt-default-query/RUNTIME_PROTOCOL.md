# First WMT query runtime protocol

Status: reviewed bounded effects and offline candidate; host enforcement and
installation are not yet ready. This record alone is not a deployment command.
The [candidate receipt](results/candidate.json) selects build `127166e4`, release
`7.1.3-gemini-a53-wmt-query`, padded boot2 SHA-256
`1b4f1064ab1e6a166b4e7cfa4dc1523b0e1923be0b3286614733454d189bc4ba`.

## Hypothesis and decision

After the existing admitted region-19 preparation and fresh CONSYS power/reset
release, the MCU can answer one default WMT query through BTIF mandatory STP.
A matched 16-byte event establishes this transport exchange only. Timeout,
partial/malformed/extra input or any prerequisite refusal retires the lifetime;
preserve evidence and return through reviewed recovery without a second query,
a wake pulse, FIFO repair or another trigger. No outcome establishes RF
calibration, reception, association or traffic.

## Shared AP-DMA clock boundary

The proven parent DT maps UART0's bus clock and the new query's AP-DMA clock to
the same infracfg provider and ID 46. It selects UART0 as stdout. Its complete
runtime log contains `console=ttyS0,921600n8` and final enabled ttyS0 console.
The selected kernel compiles the MediaTek 8250 driver and console support.

The pinned UART driver obtains an enabled bus clock and its ON power callback
gets a runtime-PM reference. Serial core leaves an active console ON rather than
performing the default non-console OFF transition. With that console retained,
its prepared/enabled clock vote remains. CCF calls the hardware enable operation
only on a zero-to-one enable-count transition. Adding the query's vote therefore
does not newly ungate AP-DMA or restart a dormant channel in this admitted state.
The [source receipt](results/clock-admission.json) pins this candidate-specific
reasoning; it is not a general guarantee for another profile or console state.

Before region preparation and again immediately before the query, the host must
require the exact release/boot identity, `/proc/cmdline` serial-console argument,
enabled ttyS0 entry in `/proc/consoles`, and UART0 platform runtime status `active`.
Require the UART0 device to remain bound to its selected MediaTek driver. Read
only `clk_prepare_count` and `clk_enable_count` under the `infra_ap_dma` debugfs
clock directory and require both positive. These files expose CCF RAM counters,
not register callbacks. If debugfs is absent, one read-only debugfs mount at the
existing `/sys/kernel/debug` mountpoint is admitted; no clock-summary walk or
other debugfs read is selected. Missing counters stop the trigger. No
serial close/unbind, runtime/system suspend, PM policy change, driver unloading
or concurrent diagnostic is allowed through evidence sealing. The controlled
RAM environment and sole device custodian enforce that boundary. Missing or
changed observations stop before the trigger; do not enable a clock to repair
this prerequisite. Standard console logging remains within this environment.

With that existing vote held, the query's clock acquisition is a reference
increment. The two BTIF channels must still pass their channel-local zero checks;
shared-clock activity from ordinary consumers is not BTIF channel ownership.
No UART/I2C channel registers, global DMA status, security fields, descriptors,
reset, STOP, FLUSH or interrupt-acknowledgment registers are written by this query.

## Exact effects and budgets

The existing region-19 collector must preserve two identical complete private
512-KiB preimages before its sole preparation trigger. Verify its exact admitted
clear extent and untouched suffix, remap, region policy and completion records.
The CONSYS trigger rechecks known-OFF domain, rails, selector, reservation and
region exclusions, consumes its attempt, then uses the existing power/rail/reset
sequence. All four HIF, EMI firmware-copy and WLAN continuation arguments are
false; the WLAN child is disabled. The inherited flags do not select a scan.

After reset release, map the source-fingerprinted SPI 130 level-low through the
inherited MT6797 sysirq provider. The standard provider owns polarity inversion
and the GIC parent; no raw polarity or guessed reset-controller operation is
added. Request an exclusive, initially disabled CPU IRQ, then enable it for RX.

| Operation | Maximum and boundary |
| --- | --- |
| AP-DMA channel observations | Up to ten 32-bit reads total: EN +0x08, STOP +0x10, FLUSH +0x14, internal bytes +0x38, valid bytes +0x3c on TX `0x11000a00` and RX `0x11000a80`; short-circuit on first nonzero word |
| BTIF clock | One framework prepare/enable, retained; controller `0x1100c000`, size `0x1000` |
| Normal bank / FIFO entry | FAKELCR +0x0c write 0; LSR +0x14 must show no RX data and TX empty before clears |
| Local DMA_EN +0x4c | One initial read, explicitly admitting timeout acknowledgment if automatic reset was off; refuse TX/RX request bits, then one write preserving unrelated fields and setting bit 2 |
| Initialization | IER +0x04 write 0; HANDSHAKE +0x6c read/write bit 0 on; four selected-source aliased IIR/FIFOCTRL +0x08 read/write clear pulses; TRI_LVL +0x60 write 0x18; final LSR mask 0x61 must equal 0x60 |
| IRQ / query | RX-only IER bit 0; reject pending startup RX; one 11-byte query, no padding/retry; absolute 500-ms deadline and at most 32 IRQ entries |
| Receive | At most 16 data-port byte reads under the fixed parser; one status observation after a matched frame rejects queued extra data without consuming it; conservative total IIR observation bound 53 including initialization |
| Retirement | Disable local IER and CPU IRQ, synchronize and free the exclusive IRQ; retain acquired clocks and CONSYS power until reviewed system recovery |

The four FIFO-control operations reproduce the revision-matched vendor source,
not an assumed IIR control readback. The document's RX/TX clear-bit order and
bank semantics conflict with that source. Both FIFOs must be empty first; the
bounded test admits those four controller-local operations, does not claim the
conflict resolved, and never retries to compensate for an unexpected result.
The initial DMA_EN read acknowledgment is also an admitted effect rather than a
passive observation. There are no packet-DMA starts, ROM patches, full-mode
negotiation, PA-rail/calibration commands, Wi-Fi firmware transfers or RF scans.

## Preservation and recovery

Capture the complete kernel log, trigger stdout/stderr/status, exact query
result/RX/IRQ counters, and private region-19 evidence in the same verified boot.
Even a trigger error may follow partial power or transport effects. Keep all
resources held; do not unbind, clear FIFOs, release clocks or reuse the consumed
owner. Restore sysfs read-only with a preinstalled trap on every return path.
Use the existing reviewed mainline-to-Gemian recovery only after evidence sealing
and live boot/recovery-tool identity checks. Confirm a changed known-good Gemian
boot afterward. A host timeout does not admit another trigger or recovery path.

A boot2 deployment must use the reviewed live-GPT guard, exact image and full
partition readback, then clean shutdown. Physical boot2 selection remains the
owner's action. No installation or device test has occurred for this candidate.
