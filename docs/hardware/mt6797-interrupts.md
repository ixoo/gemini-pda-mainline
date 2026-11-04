# MT6797 and Gemini interrupt map

Scope: the GICv3, EINT, SPI, PPI and SGI resources used by the Gemian MT6797
vendor stack on the named Gemini PDA, their numbering, dispatch path, and
handler behavior. This is a static source/DT audit with retained live
cross-checks, not a live trace.

| Field | Value |
| --- | --- |
| Device | Named Gemini PDA development unit (MT6797X) |
| Last verified | 2026-10-31 |
| Vendor baseline | Gemian Linux `3.18.41+`, source equivalent `59e00a91` |
| Controller | ARM GICv3 at `0x19000000`; redistributor `0x19200000` |
| EINT controller | MediaTek EIC at `0x1000b000`, GIC SPI 170 |
| Final Gemian DTB | `9e26929563f7682d1f7545d6007f0092c7e085a4edbd6e7be0ac8eaa5159b2f9` |
| Raw SoC map | [spi-map.tsv](../../experiments/2026-10-31-mt6797-interrupt-map/results/spi-map.tsv) |
| Experiment | [MT6797/Gemian interrupt map](../../experiments/2026-10-31-mt6797-interrupt-map/README.md) |

Confidence follows the [hardware knowledge base](README.md) convention. A
reference-board DT entry is not proof that the Gemini probes that device.

## 1. Numbering and dispatch

| Space | Range | Linux IRQ | Notes |
| --- | --- | --- | --- |
| SGI | 0-15 | 0-15 | Per-CPU IPIs; GICv3 SGI |
| PPI | 0-15 | 16-31 | Per-CPU private interrupts |
| SPI | 32-1019 | SPI + 32 | Shared peripheral interrupts |
| EINT | 0-191 | 384 + EINT | Vendor EIC domain; `max_eint_num = 192` |

The live EINT evidence confirms the base: EINT 3 -> IRQ 387, EINT 8 -> 392,
EINT 11 -> 395, EINT 16 -> 400. The denominator is the vendor
`mt_get_supported_irq_num()` result, which is 384 on this GIC configuration.

The GIC node also describes the syscon windows used by the vendor affinity and
polarity code. SPIs are level or edge per DT; most Gemini peripherals are
`IRQ_TYPE_LEVEL_LOW`, with edge entries for the watchdog, keypad, USB IDDIG,
EINT controller and a few debug blocks.

## 2. SGI and PPI

| Interrupt | Linux IRQ | Owner | Use |
| --- | --- | --- | --- |
| SGI 0-8 | 0-8 | arm64 SMP | Reschedule, call-function, CPU stop, irq_work, timer and backtrace IPIs |
| PPI 7 | 23 | `arm,armv8-pmuv3` | Performance monitor overflow |
| PPI 9 | 25 | GICv3 | Maintenance interrupt (virtualization) |
| PPI 10 | 26 | arm64 timer | Hypervisor physical timer |
| PPI 11 | 27 | arm64 timer | Virtual timer |
| PPI 13 | 29 | arm64 timer | Secure physical timer (not used by Linux) |
| PPI 14 | 30 | arm64 timer | Non-secure physical timer; clocksource/clockevent |

The live vendor kernel warns that IRQ 101-103 and 354-355 have SMP affinity
inconsistent with `GICD_ITARGETSR`. Those are cpuxgpt SPIs 69-71 and 322-323,
not PPIs; the warning is the vendor GIC affinity check, not a functional
failure.

## 3. SPI map

The generated [spi-map.tsv](../../experiments/2026-10-31-mt6797-interrupt-map/results/spi-map.tsv)
contains every enabled `GIC_SPI` declaration in the exact retained Gemian final
DTB. The tables below summarize the decision-relevant entries. `live` means
retained Gemian dmesg, `/proc/interrupts` or a published runtime record shows
the handler or activity; `DT` means the final DTB declares it but no retained
live handler evidence was found.

### 3.1 Core, clocks, timers and debug

| SPI | Linux IRQ | Block | Status | Role / handler |
| --- | --- | --- | --- | --- |
| 64-71 | 96-103 | `mediatek,mt6797-cpuxgpt` | live (101-103 warnings) | Per-CPU vendor general-purpose timers; not the arm64 clocksource |
| 73 | 105 | `mediatek,mt6797-usb11` | live | MUSB/USB11 controller |
| 74 | 106 | `mediatek,mt6797-auxadc` | live | AP AUXADC conversion completion |
| 77 | 109 | `mediatek,pwm` | live/DT | Infrastructure PWM |
| 78 | 110 | `mediatek,mt6797-therm_ctrl` | live | Thermal controller bank conversion |
| 79 | 111 | `mediatek,mt6797-mmc` (MSDC0) | live | eMMC command/data completion |
| 80 | 112 | `mediatek,mt6797-mmc` (MSDC1) | live | microSD command/data completion |
| 83-96 | 115-128 | `mediatek,mt6797-i2c` | live | I2C0-8 transfer completion; one IRQ per bus |
| 91-94 | 123-126 | `mediatek,mt6797-uart` | live | UART0-3; UART0 is the `ttyMT0` console |
| 97 | 129 | `mediatek,ap_dma` | live/DT | AP DMA completion |
| 108-115 | 140-147 | UART AP-DMA | DT | Vendor UART DMA channels |
| 116,117 | 148,149 | `mediatek,btif_tx/rx` | DT/live | BTIF TX/RX DMA |
| 118,119 | 150,151 | `mediatek,mt-cqdma-v1` | DT | CQDMA channels 0/1 |
| 122 | 154 | `mediatek,mt6797-spi` (SPI0) | DT | SPI controller |
| 129 | 161 | `mediatek,mt6797-eem_fsm` | live/DT | EEM/PTP finite-state machine |
| 130 | 162 | `mediatek,btif` | DT/live | BTIF block |
| 131-135 | 163-167 | `mediatek,mt6797-spi` (SPI1-5) | DT | SPI controllers |
| 137 | 169 | `mediatek,mt6797-toprgu` | live | Watchdog bark/pretimeout |
| 139-143 | 171-175 | dbgapb, bus_dbg, devapc, EMI | DT | Debug/APC/EMI monitoring |
| 147,149 | 179,181 | AP CCIF0/1, C2K CCIF | live/DT | Modem/C2K mailbox interrupts |
| 148 | 180 | `mediatek,trng` | DT | True random number generator |
| 151 | 183 | `mediatek,audio` | live/DT | AFE audio interrupt |
| 152,153 | 184,185 | `mediatek,gce` | live | CMDQ/GCE normal and secure threads |
| 156 | 188 | `mediatek,m4u` | live | M4U IOMMU fault/completion |
| 158 | 190 | `mediatek,dramc_nao` | DT | DRAM controller NAO |
| 159 | 191 | `mediatek,gcpu` | DT | GCPU |
| 161 | 193 | `mediatek,mt6797-dvfsp` | live | DVFSP/CSPM event |
| 165 | 197 | `mediatek,dvfs_proc2` | DT | DVFS processor 2 |
| 168 | 200 | `mediatek,irtx` | DT | IR transmitter |
| 169 | 201 | `mediatek,mt6797-apxgpt` | live/DT | APXGPT timer |
| 170 | 202 | `mediatek,mt-eic` | live | EINT controller parent |
| 178 | 210 | `mediatek,pwrap` | live | PMIC wrapper |
| 179 | 211 | `mediatek,mt6797-keypad` | live | SoC keypad |
| 180 | 212 | `mediatek,sleep` | live | SPM sleep/wake event |
| 196 | 228 | `mediatek,hacc` | DT | Hardware crypto |
| 202 | 234 | `mediatek,mm_mutex` | live | Display mutex/SOF |
| 322,323 | 354,355 | `mediatek,mt6797-cpuxgpt` | live | Additional CPU timer lines |
| 329-335 | 361-367 | `mediatek,ocp_cfg`, `ptp3_idvfs` | DT/live | OCP, iDVFS and protection lines; 331 is iDVFS |

### 3.2 Display and multimedia

| SPI range | Linux IRQ | Block group | Status |
| --- | --- | --- | --- |
| 202-233 | 234-265 | Display mutex, MDP RDMA/RSZ/WDMA/WROT/color, OVL0/1, RDMA0/1, WDMA0/1, COLOR, CCORR, AAL, GAMMA, OD, DITHER, UFOE, DSC, DSI0/1, DPI0, MMSYS, LARB0/5 | live for mutex 234 and several display lines; DT for the rest |
| 235-245 | 267-277 | VENC, LARB3, JPGENC, JPGDEC, VDEC, LARB1, LARB4, MJC top/config, LARB6 | DT |
| 247-261 | 279-293 | CAMTOP, CAMA/B, CAMSV0/1/2 banks, LARB2, FD, DIP_A, DPE | DT |
| 262-264 | 294-296 | Mali GPU job/MMU/GPU | live when the vendor GPU stack is active |
| 265,266 | 297,298 | MD CLDMA | live/DT when modem is active |

Display and camera are large vendor subsystems. The IRQ numbers are stable,
but the exact sub-handler split (frame done, underrun, command done, error) is
driver-internal and not fully audited here. The durable ownership fact is that
these are normal GIC SPIs owned by the vendor multimedia stack, not EINT or
firmware lines.

### 3.3 Connectivity, secure world and firmware

| SPI | Linux IRQ | Block | Status | Role |
| --- | --- | --- | --- | --- |
| 283 | 315 | `mediatek,wifi` | DT/live | WLAN HIF interrupt |
| 284,285 | 316,317 | `mediatek,mt6797-consys` | DT/live | CONSYS/WMT |
| 286 | 318 | `mediatek,audio_bt_cvsd` | DT | BT CVSD audio |
| 287 | 319 | `mediatek,ap2c2k_ccif` | DT | C2K CCIF |
| 291 | 323 | `mediatek,mt6797-sys_cirq` | live/DT | GIC proxy for wake/pending sources |
| 292 | 324 | `trustonic,mobicore` | firmware | MobiCore TEE |
| 293 | 325 | `mediatek,atf_logger` | firmware | ATF log ring doorbell |
| 302,303 | 334,335 | `microtrust,utos` | firmware | uTOS TEE |

The secure-world lines are real GIC SPIs but deliver firmware logging/TEE
events to Linux; they are not device drivers in the normal sense.

## 4. EINT map

The EINT controller is a chained handler on SPI 170 (Linux IRQ 202). It scans
up to 192 status bits across six 32-bit banks. Each EINT can use hardware
debounce (EINT < 16), software debounce (timer), or no debounce.

The vendor DT `interrupts` first cell is the **GPIO/pin**, not the EINT number.
`mediatek,mapping_table` converts the pin to the EINT number. For example,
GPIO87 -> EINT10, GPIO88 -> EINT11, GPIO93 -> EINT16, GPIO262 -> EINT176 and
GPIO181 -> EINT106. `/proc/interrupts` prints the EINT number.

| GPIO | EINT | Linux IRQ | Owner | Trigger | Status | Role |
| --- | --- | --- | --- | --- | --- | --- |
| 64 | 3 | 387 | FUSB301 | edge/level per board | live | Type-C controller; `fusb300-eint` |
| 66 | 5 | 389 | hall/lid | level low/high | live/DT | Lid switch; vendor changes polarity on state |
| - | 6 | 390 | MSDC1 card detect | level | live | microSD insertion/removal |
| 85 | 8 | 392 | NVT touch | level/edge per board | live | Touch interrupt; `cap_touch`/NVT |
| 87 | 10 | 394 | AW9523 keyboard | level/edge | live | Keyboard interrupt; vendor AW9523 parent |
| 88 | 11 | 395 | ALS STK3x1x | level | live | Ambient-light/proximity; the vendor BMI160 driver's failed request for this line is a driver bug, and [mainline shows it firing](gemini-sensors.md#interrupts) |
| 93 | 16 | 400 | switch | edge | live | Vendor switch/ACCDET line; exact switch identity unresolved |
| 262 | 176 | 560 | MT6351 PMIC | level | live | PMIC external IRQ (CHRDET and PMIC events) |
| 181 | 106 | 490 | USB IDDIG | level low | live/DT | USB cable ID/role detect |
| 62 | 1 | 385 | SII9022 HDMI | level | DT | External-display interrupt |
| 58 | 46 | 430 | NFC | level | DT | NFC interrupt node; population not established |
| 63 | 2 | 386 | GSE_1 | level | DT | Vendor G-sensor/switch line; [untested as the IMU's](gemini-sensors.md#interrupts) |
| 179 | 104 | 488 | DSI TE | edge | DT | Panel tearing-effect input |

`/proc/interrupts` snippets confirm `mt-eint 3 fusb300-eint`,
`mt-eint 8 cap_touch`, `mt-eint 10 aw9523-eint`, `mt-eint 11 ALS-eint` and
`mt-eint 16 switch`. The PMIC and USB IDDIG lines are registered by their
drivers but were not all visible in the same retained snippet.

The generic `cust_eint.dtsi` also defines reference EINTs 2/5/6/10/65/66/67/78
(NFC, MSDC1, ACCDET, touch, ALS, GSE, GYRO, ext-buck OC). Those are MT6735
reference declarations; they must not be treated as Gemini wiring without the
live board overlay.

## 5. Precise handler behavior

### 5.1 EINT

`mt_eint_demux()` is the chained GIC handler (confirmed in the active vendor
vmlinux by symbol and disassembly):

1. `chained_irq_enter()`, schedule a tasklet that holds a 0.5 s wakeup event.
2. Read each 32-bit EINT status bank; for every set bit:
   - increment the per-EINT counter;
   - if software debounce is enabled and the EINT is >= 16, mask the line and
     arm a timer that unmasks and redelivers;
   - otherwise call `generic_handle_irq()` for the nested handler;
   - for hardware-debounced EINTs < 16, reset the debounce counter and restore
     the previous mask state;
   - flip edge polarity for dual-edge EINTs.
3. `chained_irq_exit()`.

The 0.5 s wakeup event exists so the nested driver can acquire its own wake
lock before the system suspends again. This is vendor power-management policy,
not a standard GIC behavior.

### 5.2 Vendor GIC layer

`drivers/misc/mediatek/irq/mt6797/irq.c` adds:

- an affinity check that compares the requested SMP affinity with
  `GICD_ITARGETSR` and warns on mismatch;
- `mt_irq_mask_all()` / `mt_irq_mask_restore()` for suspend, saving and
  restoring GIC enable/type/polarity state;
- `mt_irq_set_pending_for_sleep()`, `mt_irq_unmask_for_sleep()` and
  `mt_irq_mask_for_sleep()` for the SPM wake path;
- `INT_POL_CTL0` polarity handling and a vendor `mt_irq_chip`.

The live warnings 101-103/354-355 are the affinity check firing on cpuxgpt
lines; they do not indicate an interrupt storm.

### 5.3 PMIC

The PMIC path is two-stage:

- GIC SPI178 (`pwrap`) is the PMIC-wrapper interrupt.
- A separate EINT176 is the PMIC external line.
- The MT6351 child creates a four-bank, 64-source nested IRQ domain; its
  top-half reads/acks the PMIC banks and dispatches regulator, RTC, charger,
  keys and thermal children.

The wrapper and the external EINT are independent; losing one does not prove
the other is broken.

### 5.4 I2C, UART, MSDC and USB

- Each MT6797 I2C bus has its own SPI. The handler reads the transfer status,
  completes or errors the current message and wakes the waiter. There is no
  shared I2C interrupt line.
- UART0-3 use SPIs 91-94. UART0 is the vendor console; the driver is the
  MTK 8250 variant and the handler follows the 16550 IIR/THRE/RX path.
- MSDC0/1 use SPIs 79/80. Command/data completion is per controller; the
  microSD card-detect path is EINT6, not the MSDC SPI.
- USB11 uses SPI73. USB3 has SPI126/127 and xHCI uses one of them. IDDIG is
  EINT106 (GPIO181); the Type-C controller is EINT3. These are separate
  ownership boundaries.

### 5.5 Display, GPU, connectivity and modem

- Display mutex SPI202 is the SOF/EOF and mutex event; DSI/OVL/RDMA/WDMA
  blocks have their own SPIs in the 202-233 range. The vendor display stack
  uses CMDQ/GCE (SPI152/153) to chain register writes.
- Mali GPU uses SPIs 262-264 for job, MMU and GPU events; these are not M4U
  interrupts.
- Wi-Fi/BT/CONSYS use SPIs 283-287 and BTIF 116/117/130. WMT/CONSYS ownership
  is a separate runtime boundary.
- Modem uses CCIF 147/149, CLDMA 265/266 and MD IRQ 179. The modem and AP
  share the CCIF mailbox but not the same handler as the AP DMA.

### 5.6 Watchdog, sleep and sys_cirq

- SPI137 is the TOPRGU watchdog bark/pretimeout line; the live vendor kernel
  also reports an application bark line on IRQ169.
- SPI180 is the SPM sleep event. The vendor sleep code uses
  `mt_irq_mask_all`/restore and the sleep pending helpers.
- SPI291 `sys_cirq` is a GIC proxy for wake/pending sources. It is not a
  device interrupt; it aggregates system wake events.

## 6. Interrupt payloads

A GIC interrupt line carries no device payload by itself. The payload is the
status/queue state read by the handler. The main classes are:

| Class | Payload / status source | Data path |
| --- | --- | --- |
| EINT | EINT status bank bit, then the device's own status/INT register | Device register or FIFO; the EIC only supplies the pin event |
| PMIC | Wrapper status plus the MT6351 four-bank nested status | PMIC register read through PWRAP |
| I2C | Controller `INTR_STAT` (transfer complete/ack/error) | TX/RX FIFO or AP-DMA buffer |
| UART | 16550 IIR/LSR (RX, THRE, line status) | RX/TX FIFO |
| MSDC | Controller interrupt status (command/data/error) | Response and data FIFO |
| USB11/xHCI | MUSB endpoint/status or xHCI event ring | Endpoint FIFO or TRB ring |
| GCE/CMDQ | GCE thread/event status | Command buffer in DRAM |
| CCIF/modem | CCIF channel status | Shared-memory mailbox |
| M4U | Fault/translation status registers | Page-table/fault address registers |
| Display/GPU | Block status (SOF, underrun, job/MMU) | Register and command buffer |
| ATF/TEE | Doorbell/log-ring status | Shared ATF/TEE log buffer |

For the Gemini-specific EINTs, the useful payload is in the child driver, not
in the EIC: the touch controller's report, the AW9523 key matrix, the PMIC
bank/bit, the Type-C controller state or the lid level. The EIC mapping table
only converts the pin to the EINT number.

## 7. Live evidence and limits

Retained live evidence establishes these exact lines:

- GIC 101-103, 354-355: cpuxgpt affinity warnings.
- GIC 105: USB11 (`musbfsh`, DMA); GIC 158/159: USB3/xHCI.
- GIC 184/185: GCE/CMDQ; GIC 188: M4U.
- GIC 202: EINT; GIC 210: PWRAP; GIC 234: display mutex.
- EINT 3/8/10/11/16: Type-C, touch, keyboard, ALS and switch.
- EINT 176: PMIC external; EINT 106: USB IDDIG (GPIO181).

Not established:

- A complete `/proc/interrupts` count table for Gemian.
- Which of the DT-enabled nodes actually probe at runtime; the final DTB
  proves the declaration, not the bind.
- The identity of EINT16/GPIO93 switch.
- Full sub-handler behavior for camera, video, DSI and GPU.
- Secure-world interrupt delivery traces.

## 8. Mainline differences

Mainline Linux uses the standard GICv3 and arm64 timer paths. It does not
carry the vendor `mt_irq` affinity/polarity layer, the EINT chained driver, the
PMIC-wrapper nested domain, or the vendor display/GPU/modem IRQ users. The
current DT exposes only the nodes that mainline owns; the vendor IRQ map above
is therefore a portability reference, not a mainline configuration contract.

The keyboard and touch mainline paths are also different: the accepted
keyboard path uses polling, and the open touch backend does not yet take
EINT8/EINT10. Do not assume that a vendor EINT is available just because it
exists in the vendor DT.

## 9. Evidence index

- [Interrupt map experiment](../../experiments/2026-10-31-mt6797-interrupt-map/README.md)
- [Raw SPI map](../../experiments/2026-10-31-mt6797-interrupt-map/results/spi-map.tsv)
- [Live IRQ evidence](../../experiments/2026-10-31-mt6797-interrupt-map/results/live-irq-evidence.md)
- Active vendor vmlinux `cc66df06…` and Gemian final DTB `9e269295…`
- [MT6797 live resource map](mt6797-live-resource-map.md)
- [Keyboard](keyboard.md), [touchscreen](touchscreen.md), [charging](gemini-charging.md), [thermal management](mt6797-thermal-management.md)
- [Firmware boundary](firmware.md)
- [Gemian CPU/scheduler policy](../../experiments/2026-07-21-gemian-cpu-scheduler-policy/README.md)
