# MT6797 HIF executor review

This is an offline source review, not an HIF hardware result. The selected
Linux 7.1.3 source is the clean Buildbox input for project commit
`0d7f1582f4822c97b2c9803c9e1836485eab5364`, profile
`mt6797-a53-wifi-power-probe`. No device operation or kernel change was made
for this review. Its immediate purpose is to bound the HIF work that follows
CONN power and shared-owner admission.

The reviewed source identities in `drivers/net/wireless/mediatek/mt6797/` are:

| File | SHA-256 |
| --- | --- |
| `hif.c` | `79adeeee28a728aa2a6a284b4b435e76e35e459dec106966a4cbbd09fdef2f64` |
| `hif_pio.h` | `5862d6254384d3a4ac23dc2b79f084ad7842d7e2c94d762e7a18d4c3d101ef00` |
| `hif_config_phase.h` | `b78eb225ed0babfa31568707861fd59a79232dfbae906ca7f7d672961ea56858` |
| `hif_ordinary_section.h` | `13992b05aaa4f5133b2e2c0601cc508005b3560d9a1ba004fceb1b055e95b0cb` |
| `firmware-probe.c` | `f92319be1c67eaca7f2cc9d154dfef2fd475999ba176c456e94e6049cea278b7` |

The only bound WLAN platform child is `firmware-probe.c`: it prepares and
summarizes the retained image, then holds execution. It maps no HIF resource,
requests no IRQ and calls none of the HIF functions. The compiled HIF is a
caller-MMIO library, so its tests do not prove an active executor.

| Question | Source result | Active caller responsibility |
| --- | --- | --- |
| Setup/data serialization | Each `hif.c` operation takes one mutex around the setup register and finite data FIFO accesses; a busy concurrent HIF API call refuses. The mutex does not cover external owners or future IRQ work. | Hold the shared powered HIF lifetime, establish driver ownership, and mask or otherwise exclude IRQ consumers before a transaction can touch the same setup/data window. No current code acquires driver ownership or registers that IRQ. |
| Complete TX packet boundaries | CONFIG and START each use one setup plus their complete 20- or 16-byte packet. Each ordinary payload chunk constructs one eight-byte header plus at most 2048 bytes and calls PIO once; block padding is zero-filled. | Keep a packet wholly within that one command boundary, and do not treat submission as firmware acceptance or recovered credit. Later data TX needs its own packet and credit contract. |
| Selected INIT RX extra word | `hif_config_phase.h` reads 32 bytes from port 0 for an exact 28-byte CMD_RESULT, then validates only 28. The [selected source-mode analysis](../2026-09-05-mt6797-wifi-contract/INIT_CREDITS_RX.md) identifies the extra-four-byte setting. | Preserve the 32-byte bus span and one response transaction; never decode padding as another event. This proves no general data RX mode. |
| Enhanced RX metadata | No active RX data path or enhanced-mode metadata transaction exists in this source selection. No matching-mode evidence establishes whether the first PIO session selects enhanced RX metadata. | Check the matching host/firmware mode before implementation. If selected, read data and metadata in the required single transaction and test its length and packet boundaries. Do not bolt a second FIFO read onto the INIT reply path. |

The concrete next HIF gap is a caller-owned activation epoch: validated CONN
power and EMI ownership, HIF resource/IRQ admission, driver-ownership request
and proof, fresh INIT credit seed, then the existing bounded CONFIG/ordinary/
START PIO operations under one session identity. The current
[transport design](../2026-09-05-mt6797-wifi-contract/PIO_TRANSPORT_DESIGN.md)
separates FIFO submission from firmware completion and retains the refusal
rules for uncertain transfers. The current power probe deliberately stops
before this boundary. Add focused caller tests when the owner/IRQ/credit path
is implemented; repeating the scalar PIO primitive tests would not cover it.
