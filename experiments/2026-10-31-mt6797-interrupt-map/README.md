# Experiment: MT6797/Gemian interrupt map

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-31-mt6797-interrupt-map` |
| Status | `completed` for the static SoC map and handler audit; exact Gemini board status and full live counters remain partial |
| Subsystem | GICv3, EINT, SPI/PPI/SGI, vendor IRQ ownership |
| Device variant | Planet Gemini PDA, MT6797X, Gemian 3.18 vendor stack |
| Date(s) | 2026-10-31 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | interrupt ownership and mainline portability |

## Question

Which interrupts are used on the Gemian stack, how are they numbered and
dispatched, and what does each handler actually do?

## Provenance and environment

- Public vendor source: Gemian `gemini-linux-kernel-3.18` commit
  `59e00a9144d782e148332009a835b99c43382467`.
- SoC DT: `arch/arm64/boot/dts/mt6797.dtsi`; reference board DT
  `arch/arm64/boot/dts/aeon6797_6m_n.dts`.
- Exact Gemian final DTB: retained `board.dtb`, SHA-256
  `9e26929563f7682d1f7545d6007f0092c7e085a4edbd6e7be0ac8eaa5159b2f9`,
  extracted from the active Gemian boot image
  `1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513`.
- GIC/EINT source: `drivers/misc/mediatek/irq/mt6797/irq.c`,
  `drivers/irqchip/irq-mt-eic.c`.
- Active vendor vmlinux: symbol-bearing 3.18 ELF, SHA-256
  `cc66df06194d3315335462760962165e1dcb2e50221574aeb45a0805bb17a162`.
  Symbols and disassembly were used to confirm `mt_eint_demux`,
  `mt_eint_register`, `mt_irq_mask_all`, the threaded EINT registration and
  the GPIO-to-EINT mapping path.
- Live Gemian evidence: retained dmesg and `/proc/interrupts` snippets from
  the 2026-07/09/10 captures, plus the durable resource map.
- Firmware: retained TEE/ATF and SCP strings, already covered by the
  [firmware boundary](../../docs/hardware/firmware.md).

## Method

1. Decompile the exact retained Gemian `board.dtb` and extract every enabled
   `GIC_SPI` declaration. The reference `aeon6797_6m_n` DTS is used only to
   explain nodes and compare status.
2. Normalize to SPI number and Linux IRQ (`SPI + 32`), deduplicate and record
   node/compatible/trigger.
3. Extract live IRQ numbers, names and EINT mappings from retained Gemian
   dmesg and `/proc/interrupts` snippets.
4. Read the GIC, EINT, PMIC, I2C, UART, MSDC, USB, display, GPU, thermal,
   watchdog, modem and connectivity handlers for the top-half/threaded
   behavior and status/ack ordering. Cross-check the EINT registration and
   demux path against the active vendor vmlinux symbols/disassembly.
5. Record the limits: reference-board DT status is not exact Gemini status,
   and no complete live `/proc/interrupts` snapshot is public.

## Associated code

- [`scripts/parse-irq-dt.py`](scripts/parse-irq-dt.py): extract enabled GIC
  SPIs from a `dtc -I dtb -O dts` dump.
- [`results/spi-map.tsv`](results/spi-map.tsv): generated SoC SPI map.
- [`results/live-irq-evidence.md`](results/live-irq-evidence.md): sanitized
  dmesg and `/proc/interrupts` anchors.

## Observations

The durable conclusions are in
[MT6797 interrupts](../../docs/hardware/mt6797-interrupts.md). Key results:

- Linux IRQ = SPI + 32 for GIC SPIs; EINT Linux IRQ = 384 + EINT number.
- The EINT controller is a chained GIC SPI170 handler that scans up to 192
  EINT status bits, applies hardware or software debounce, takes a 0.5 s
  wakeup event and dispatches the nested handler.
- Live Gemian IRQs include GIC 101-103/354-355 (CPU timers), 105 (USB11),
  110 (thermal), 111/112 (MSDC), 115-126 (I2C/UART), 158/159 (USB3),
  184/185 (GCE), 188 (M4U), 202 (EINT), 210 (PWRAP), 234 (display mutex),
  and EINT 3/5/6/8/10/11/16/106/176.
- Several DT-enabled blocks are reference-board nodes, not proven Gemini
  users; camera, video, IR, and some display IRQ nodes have no retained live
  handler evidence.

## Limits

- The exact Gemini final DTB and its EINT mapping table are retained and were
  used. The SoC map and enabled-node set are therefore exact for that boot.
- No complete `/proc/interrupts` from Gemian is retained; per-IRQ counts and
  some handler names are partial.
- Handler behavior is source-level. No live tracing or interrupt injection was
  performed.
- Secure-world IRQ delivery (ATF/TEE) is inferred from DT and strings, not
  from a secure trace.

## Follow-up

One bounded read-only Gemian session capturing the complete
`/proc/interrupts`, `/sys/kernel/debug/irq` domains, and EINT mappings would
close the live-status gaps. That is a runtime step, not offline RE.
