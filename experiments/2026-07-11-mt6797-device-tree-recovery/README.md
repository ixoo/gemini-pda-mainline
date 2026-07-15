# Experiment: MT6797 live device-tree recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-11-mt6797-device-tree-recovery` |
| Status | `completed` |
| Subsystem | SoC resources and board wiring |
| Device variant | Gemini PDA running Gemian |
| Date | 2026-07-11 |
| Investigator | Repository maintainer with Codex assistance |

## Question

Which register windows, interrupts, clocks, GPIOs, storage capabilities, and
vendor tuning references can be recovered from the running kernel's flattened
device tree without changing device state?

## Method and safety

The owner-authorized SSH session used the named key
`codex-gemini-192.168.1.50`. The existing read-only
[`collect.sh`](../2026-07-11-gemian-hardware-inventory/scripts/collect.sh)
collector captured the `device-tree` section. The enhanced capture added an
allow-list of driver-facing properties and phandles; no arbitrary device-tree
files, unique identifiers, block devices, or calibration partitions were read.

The raw capture is private and ignored by Git at
`artifacts/device-inventory/20260711-live/device-tree-v3.txt`. It was decoded
offline with
[`decode-dt-capture.py`](../2026-07-11-gemian-hardware-inventory/scripts/decode-dt-capture.py).
Public 3.18 and 4.9 GPL source trees were then used only to interpret register
semantics and identify downstream binding conventions.

## Results

- MSDC0 is the 8-bit, non-removable eMMC controller at `0x11230000`, SPI 79,
  using infra clock ID 33. MSDC1 is the 4-bit removable-card controller at
  `0x11240000`, SPI 80, using infra clock ID 35.
- MSDC1 card detect resolves to MT6797 GPIO 67 and its EINT node requests a
  debounce value of 1000. Polarity still needs a controlled card-insertion
  correlation before conversion to a mainline GPIO flag.
- The downstream storage binding advertises eMMC HS200/HS400 and microSD UHS
  modes. These are capability claims, not safe initial mainline settings.
- The PMIC rail relationship recovered from source is VEMC for eMMC, VMCH for
  microSD card power, and switchable VMC for microSD I/O voltage.
- A follow-up [MT6351 experiment](../2026-07-11-mt6351-pmic-recovery/README.md)
  confirmed the PMIC as E2 silicon and decoded the missing 192-line EINT
  controller. The PMIC path is pseudo-GPIO262→EINT176; storage GPIO67 maps to
  EINT6.
- M4U is at `0x10205000`, SPI 156, with seven multimedia larbs in the exact
  MT6797 source table. Mali is absent from that table and has its own MMU.
- Display component windows and IRQs were recovered through the DSI, mutex,
  and MMSYS path. The first-light target can be restricted to OVL0, RDMA0,
  DSI0, and the MM mutex.
- The root LCM nodes cannot identify the active panel. A follow-up
  [runtime panel experiment](../2026-07-11-gemini-panel-recovery/README.md)
  proved that this kernel bypasses the DT LCM table and selects a compiled-in
  single-DSI NT36672-family driver; the root R63419 dual-DSI node is inactive.
- The live tree contains inactive alternatives. In particular RT9466 at I2C0
  `0x53` is described as `primary_charger` but is unbound, while BQ25890 at
  `0x6b` is the running charger driver.

The durable interpreted output is the
[MT6797 live resource map](../../docs/hardware/mt6797-live-resource-map.md).

## Limitations

The capture proves the boot contract used by this vendor kernel, not mainline
compatibility or physical population of every node. Vendor phandle properties
such as `pinctl` and `register_setting` refer to downstream-only data
structures and must be translated, not copied. GPIO polarity, USB-C port
mapping, precise panel-module identity, PMIC selectors, and safe operating
frequencies remain subjects for separate controlled experiments.

## Conclusion

The live tree provides a reproducible resource map for initial Linux 7.1.x
driver data and DTS work. It also demonstrates why runtime driver binding must
be checked before treating vendor DT alternatives as populated hardware.
