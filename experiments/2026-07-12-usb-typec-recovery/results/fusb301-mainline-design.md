# FUSB301 mainline design record

This record compares the vendor FUSB301 implementation with the Linux 7.1.x
Type-C framework. It records protocol facts and design boundaries without
copying the vendor implementation; the vendor header carries a separate
proprietary license notice and remains immutable evidence.

The source comparison is reproducible with
[`analyze-fusb301-contract.sh`](../scripts/analyze-fusb301-contract.sh).

The earlier live identity-access limitation is recorded in
[`fusb301-live-identity-attempt.txt`](fusb301-live-identity-attempt.txt). A
later vendor probe log captured both public device IDs and the asymmetric IRQ
paths in
[`runtime-usb-typec-battery-recovery-20260714.txt`](runtime-usb-typec-battery-recovery-20260714.txt).
The disabled-board Linux candidate is validated in
[`fusb301-mainline-validation.txt`](fusb301-mainline-validation.txt).

## Source identity

| Source | Revision/hash |
| --- | --- |
| Vendor tree | `c5b0be85017ad0c599725e8273842efdbecdd88a` |
| Vendor header | `drivers/misc/mediatek/usb_c/fusb301/fusb301.h` |
| Header SHA-256 | `f2c625a01842e1bc2e55139448489dfadcccbde424efac114e113e4bf6fa6c4b` |
| Vendor driver | `drivers/misc/mediatek/usb_c/fusb301/usb_typec.c` |
| Driver SHA-256 | `de3196f5ab6b3fac53ee1900736330aa18ef160aad90ac59e25a97a585395d06` |
| Linux comparison | pinned Linux 7.1.3 `drivers/usb/typec/` |

## Generic FUSB301 register contract

The vendor header defines the compact register block:

| Register | Address | Observed fields or purpose |
| --- | ---: | --- |
| Device ID | `0x01` | version/revision fields |
| Mode | `0x02` | source, sink, DRP, accessory mode bits |
| Control | `0x03` | interrupt mask, advertised current, DRP toggle |
| Manual | `0x04` | error/disabled/unattached states |
| Reset | `0x05` | software reset |
| Mask | `0x10` | attach/detach/BC/accessory interrupt masks |
| Status | `0x11` | attach, BC level, VBUSOK, orientation/CC state |
| Type | `0x12` | controller type/status block |
| Interrupt | `0x13` | interrupt status |

The vendor probe reads `0x01` and writes `0x02 = 0x01`. It does not expose a
complete, working Type-C state machine: `fusb301_eint_work()` only locks and
unlocks a mutex, the state-machine call is commented out, interrupt-mask
initialization is commented out, and the exported legacy callback registration
functions return success without registering or switching a consumer.

This is enough to establish a register-level starting point, not enough to
claim that the vendor behavior is a usable driver contract.

## Mainline shape

Base Linux 7.1.x has no FUSB301 driver or binding, but it does provide the Type-C
class, partner/orientation reporting, role-switch, mux, and TCPM/TCPci helpers.
Patch 0056 now implements the generic controller boundary using those APIs:

1. a generic I2C FUSB301 driver using regmap, validated device-ID reads,
   explicit mode/current configuration, mask/status/interrupt handling, and
   Type-C class registration;
2. an optional `typec_switch`/`typec_mux` or `usb_role_switch` consumer for
   SuperSpeed orientation and USB controller role;
3. Gemini board data for the separate VBUS and redriver GPIOs.

The candidate covers item 1 only. It intentionally does not implement item 2
or item 3 until the Gemini wiring is correlated on hardware.

The FUSB301 register set does not by itself prove USB-PD support. PD/TCPM
should not be added until the controller's capabilities and board wiring show
that it is present; initial work should cover attach/detach, CC orientation,
advertised BC current, VBUS safety, and USB data-role selection only.

## Gemini-specific glue and unresolved gates

The live topology has two FUSB301 clients at address `0x25`, on I2C0 and I2C1.
The vendor device tree/source also exposes separate pseudo-nodes for the
interrupt and board switch paths. Static/live evidence associates candidate
signals with GPIO64/EINT3, GPIO70 (`sw_en`), GPIO71 (`sw_sel`), GPIO72
(`sw7226_en`), and GPIO94 (`usb1_drvvbus`), but the physical left/right port
mapping is not resolved.

Before enabling any node or writing switch/VBUS controls, capture on named
hardware:

- each controller's returned device ID and interrupt polarity;
- which physical connector each I2C instance serves;
- CC1/CC2 orientation versus the `SS_SW`/redriver outputs;
- VBUS source/sink polarity and current limits;
- USB1/USB3 role-switch and SuperSpeed PHY ownership;
- detach/error recovery behavior with no accessory and with owner-authorized
  cables.

The vendor driver's incomplete state machine must not be copied as a new
mainline ABI. A post-recovery vendor probe independently logged the public
device ID `0x12` on both clients; this supports the candidate's identity gate,
but does not validate its mainline IRQ, connector, or board-switch wiring.
Until those mapping gates pass, keep FUSB301 nodes and board switch glue
disabled and use only read-only topology evidence.
