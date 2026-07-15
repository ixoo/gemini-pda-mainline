# Experiment: Gemini UART and early-console recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-13-uart-console-recovery` |
| Status | `completed` for live topology and static source comparison; mainline boot remains untested |
| Subsystem | MT6797 UARTs, AP-DMA, serial console, LK handoff |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant is not independently established |
| Date(s) | 2026-07-13 |
| Investigator(s) | Repository maintainer with Codex assistance |
| Tracking issue | None |

## Question or hypothesis

Can the Gemini's UART0 console use the existing Linux 7.1.3 MediaTek 8250
driver, and which vendor DMA/console details must not be copied into the
mainline board description?

## Provenance and environment

- Live kernel: Linux `3.18.41+`, AArch64, Gemian Debian 9 userspace.
- Live device: `gemini@192.168.1.50` over the owner's private LAN.
- Private raw capture: `artifacts/device-inventory/20260713-live/uart-console.txt`
  (Git-ignored and access-restricted).
- Fresh point-in-time status probe: [`results/live-status-20260713.txt`](results/live-status-20260713.txt).
- A second bounded capture on 2026-07-14 is recorded in the consolidated
  [live runtime snapshot](../2026-07-14-first-boot-probe-audit/results/live-runtime-snapshot-20260714.txt);
  its private UART payload is `artifacts/device-inventory/20260714-live/uart.txt`.
- Vendor source: Planet MT6797 tree commit
  `c5b0be85017ad0c599725e8273842efdbecdd88a`.
- Mainline comparison: Linux `7.1.3` in the development VM.
- Existing board candidate: patch `0020`, which enables only `uart0` and
  selects `serial0` at 921600 8N1.
- Retained LK source audit: `dguidipc-gemini-lk-android8/lk`, commit
  `f4988d74bb70a0a15d7f362f412afba7e7fcda46`.

## Safety assessment

The live collector is read-only. It reads `/proc/consoles`, non-sensitive
sysfs tty/platform metadata, flattened-DT UART properties, interrupt counters,
and device-node permissions. It does not open a tty, change termios, transmit
characters, bind/unbind a driver, read the complete boot command line, or
modify pinctrl/clock state. Kernel messages are deliberately omitted because
the vendor ring can be large and may contain user or network data.

The source analyzer reads immutable vendor Git objects and Linux source. No
vendor UART code is copied into this repository.

## Associated code

From the repository root:

```sh
mkdir -p artifacts/device-inventory/20260713-live
ssh -i artifacts/credentials/gemini_ed25519 \
  -o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes \
  gemini@192.168.1.50 'bash -s' \
  < experiments/2026-07-13-uart-console-recovery/scripts/collect-live-uart.sh \
  > artifacts/device-inventory/20260713-live/uart-console.txt
chmod 700 artifacts/device-inventory/20260713-live
chmod 600 artifacts/device-inventory/20260713-live/uart-console.txt
./scripts/dev-vm run bash -lc \
  experiments/2026-07-13-uart-console-recovery/scripts/analyze-uart-contract.sh
./scripts/dev-vm run env \
  CURRENT_PACKAGE=/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-b7721ab55e41 \
  experiments/2026-07-13-uart-console-recovery/scripts/audit-mainline-console-contract.sh
./scripts/dev-vm run env \
  LK_TREE=/home/julien.guest/src/reference/dguidipc-gemini-lk-android8/lk \
  CURRENT_PACKAGE=/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-b7721ab55e41 \
  LIVE_IDENTITY=/mnt/gemini-pda-mainline/artifacts/device-inventory/20260714T-handoff-refresh/identity.txt \
  experiments/2026-07-13-uart-console-recovery/scripts/audit-lk-console-mutation.sh
./scripts/dev-vm run env \
  LINUX_TREE=/home/julien.guest/src/gemini-pda/linux-7.1.3 \
  experiments/2026-07-13-uart-console-recovery/scripts/audit-uart-clock-contract.sh
```

## Procedure

1. Run the key-only collector once without opening any serial device.
2. Compare the live UART nodes, tty names, IRQ counters, and console record
   with the pinned vendor DT/source.
3. Compare the existing MT6797 Linux 7.1.3 UART binding, 8250 driver, and board
   patch. Hash the relevant sources.

## Observations

- Four live devices are bound to the vendor `mtk-uart` driver:
  `ttyMT0`–`ttyMT3`, with major `204` minors `209`–`212`. `/proc/consoles`
  identifies `ttyMT0` as the active write-capable serial console; `tty0` and a
  pstore console are also registered.
- The live UART nodes are `apuart0@11002000` through `apuart3@11005000`, all
  compatible with `mediatek,mt6797-uart` and marked `okay`. UART0 exposes a
  0x1000 UART window plus vendor AP-DMA TX/RX windows and three interrupts; the
  other UARTs expose the analogous vendor resource shape. UART0 names
  `uart0-main` and `uart-apdma`; UART1–3 name only their UART clock.
- A fresh read-only SSH status probe confirms the same vendor baseline remains
  active: Linux `3.18.41+`, `MT6797X`, 3,860,680 kB total memory, and
  `ttyMT0` as the write-capable serial console. This is a live vendor-kernel
  observation, not a mainline boot result.
- The 2026-07-14 capture again reports `ttyMT0` and the four `mtk-uart`
  bindings, with no console or compatible-string delta. Interrupt counters are
  intentionally treated as point-in-time values rather than board facts.
- Only one filtered UART interrupt line is visible in this userspace view:
  GIC line 123 (`mtk-uart`) has nonzero counters. The three DMA interrupt lines
  are not separately named in `/proc/interrupts` here, so their runtime use is
  not inferred.
- The vendor platform code uses `of_iomap(node, 0)` for the UART register bank,
  parses the first UART IRQ, and separately maps the AP-DMA windows/IRQ entries.
  The vendor default settings use VFIFO DMA for UART0–2, while the console
  path explicitly switches to non-DMA operation and uses pinctrl states for
  RX/TX transitions.
- The vendor UART0 resource tuple is materially larger than the Linux one:
  `0x11002000+0x1000` for the UART bank, `0x11000600+0x1000` for DMA TX,
  `0x11000680+0x80` for DMA RX, and three IRQs (91, 108, 109). Linux 7.1.3
  advertises only `0x11002000+0x400` and SPI 91 for the board console. This is
  an intentional PIO boundary, not an assertion that the vendor DMA windows
  do not exist.
- Linux 7.1.3's `mediatek,uart.yaml` accepts `mediatek,mt6797-uart` with the
  `mediatek,mt6577-uart` fallback, one UART register range, one or two
  interrupts, one or two clocks, and optional generic DMA channels. The
  `8250_mtk` driver matches the fallback compatible and its early-console path
  uses the standard 8250 setup. It explicitly disables DMA for a console.
- The Linux MT6797 SoC DTS intentionally describes the UART register window and
  UART IRQ only. The local Gemini patch enables UART0 PIO operation, adds the
  standard `serial0` alias, and sets `stdout-path = "serial0:921600n8"`.
- The active Linux `uart0_pins_a` group is pinmux-only: it selects UTXD0 and
  URXD0 and requests no pinconf properties. It therefore avoids the missing
  MT6797 pinconf maps that required the separate eMMC pin-group correction.
- The vendor boot command line observed in the baseline uses the downstream
  device name `ttyMT0`. Linux 8250 normally exposes a `ttyS*` device, so that
  downstream `console=ttyMT0,...` token cannot be assumed to select the
  mainline port. The live chosen node did not expose a `stdout-path`, consistent
  with LK supplying the console handoff.
- The retained LK source sets a non-FPGA default of `console=ttyMT3,921600n1`,
  reads the preloader's `log_enable` and `log_port`, and rewrites the first
  `ttyMT` token to `ttyMT0` through `ttyMT3` based on that runtime selection.
  With logging disabled or an unknown port, this source selects UART2 and thus
  rewrites the default token to `ttyMT1`; the live `ttyMT0` observation therefore
  cannot be explained from the source default alone. It is consistent with,
  but does not prove, a preloader handoff selecting UART1 while logging is
  enabled.
- The same retained LK source's non-FPGA default already includes `maxcpus=5`.
  Its build-type/meta-log policy appends `printk.disable_uart=1` or `=0`.
  The fresh redacted device capture contains `console=ttyMT0,921600n1`,
  `maxcpus=5`, and `printk.disable_uart=1`, matching the source-level mutation
  path. This is vendor-runtime evidence only; it does not justify copying the
  CPU cap or UART-disable token into a mainline command line.
- At the final handoff LK calls `custom_port_in_kernel()`, appends the boot
  image header command line, and then overwrites both `atag,cmdline` and
  `/chosen/bootargs`. The header's `console=ttyS0` candidate is therefore
  appended after LK's downstream `ttyMT*` token, and may leave both console
  names in the Linux command line. The source-level audit is recorded in the
  [current 77-patch LK console mutation result](results/lk-console-mutation-current-77-20260714.txt);
  the earlier 76- and 72-patch results are retained as historical evidence.
  The source-ordered merge with the private 77-patch candidate is summarized in
  [`results/lk-console-merge-current-77-20260714.txt`](results/lk-console-merge-current-77-20260714.txt):
  the expected handoff contains both the retained vendor `ttyMT0` token and the
  appended mainline `ttyS0` token. This is an inference from pinned source and
  candidate metadata; only a UART capture from a booted candidate can resolve
  the effective Linux console.
- The authoritative current 77-patch package audit confirms `serial0` resolves to
  `/serial@11002000`, `stdout-path` is `serial0:921600n8`, the UART0 compatible
  and SPI 91 resource are present, and `mtk8250_probe`,
  `early_serial8250_setup`, and `serial8250_register_8250_port` are linked into
  `System.map`. See the [current 77-patch console contract result](results/mainline-console-contract-current-77-20260714.txt);
  the earlier 72-patch result is historical.
- The bsg100 Linux 6.6 hardware history found a late-clock-cleanup failure
  caused by `8250_mtk` acquiring the named UART `baud` clock without holding it
  enabled; the downstream fix changed that acquisition to
  `devm_clk_get_enabled()`, and the fix was validated through userspace and
  USB-gadget startup. Linux 7.1.3 already contains that exact lifetime rule for
  both the named baud clock and unnamed fallback (source SHA-256
  `9ed47647…`), so `clk_ignore_unused` is not a substitute or an additional
  Gemini patch. See the [clock contract result](results/uart-clock-contract-current-72-20260714.txt).

## Analysis

The UART register programming model is a standard MediaTek 16550-compatible
path already represented by Linux 7.1.3. A new UART driver is not justified by
the observed MT6797 identity: the existing 8250 MediaTek driver is the correct
reuse boundary for the console and PIO serial port.

The vendor VFIFO/AP-DMA implementation is a separate optimization and ABI. It
uses extra register windows, DMA IRQs, vendor channel constants, and console
pin-state transitions that are not part of the Linux 7.1 binding. The local
board's one-window/one-IRQ UART0 description intentionally avoids claiming
DMA support; this is sufficient for an early console and is safer for the
first bring-up. Optional DMA can be added later through the standard `dmas` /
`dma-names` contract only after the AP-DMA channel and interrupt mapping are
recovered.

The apparent register-size discrepancy is bounded by the current driver
source: Linux `8250_mtk` accesses the MediaTek extension registers below
offset `0x2b`, and its console path explicitly disables DMA. A 0x400 PIO
resource therefore covers the observed early-console path while leaving the
vendor-only DMA windows unclaimed. This is a source-backed reuse decision, not
proof that every vendor UART feature fits in 0x400. If a future non-console
experiment observes an access at or above `0x400`, or requires AP-DMA, reopen
the resource and IRQ mapping rather than enlarging the DT speculatively.

The current 72-patch Linux 7.1.3 package was revalidated after the memory
reservation update. The UART0 pinctrl declaration remains compatible with the
existing MT6797 pinctrl driver, so this subsystem needs no additional driver
or pinconf patch before a controlled boot attempt.

The main remaining console risk is bootloader command-line mutation, not a
missing UART driver. LK does not treat the DTB's `stdout-path` as the final
console-token authority: it builds and rewrites `/chosen/bootargs` late in the
handoff. A mainline 8250 console should use the standard `serial0` stdout path
and, if an explicit kernel command-line console is required, the actual
mainline tty name (normally `ttyS0`). The combined command line and first
earlycon output must be checked in a non-primary boot slot before changing any
boot image or loader state. The final command line must also be checked for
duplicate downstream `ttyMT*`, `maxcpus=5`, or `printk.disable_uart` tokens
introduced by LK; none should be treated as a mainline default without a
booted-kernel observation.

## Conclusion

`confirmed` for the live four-port MT6797 UART topology and the vendor
console's non-DMA behavior. `confirmed` as a source-level reuse decision for
Linux 7.1.3 `8250_mtk` in PIO/early-console mode. `inconclusive` for a real
mainline boot: no Image/DTB was flashed or booted and no serial character was
transmitted by this experiment.

## Follow-up

- Verify the runtime LK command-line and chosen-node mutation with a reversible,
  non-primary boot candidate; capture the first earlycon and normal 8250 log.
- Confirm the mainline device name and console token (`ttyS0` versus any
  platform alias) from the booted kernel rather than guessing from vendor
  `ttyMT0` names.
- Keep UART0 in PIO mode for the first boot. Recover AP-DMA channel/IRQ and
  pinctrl sleep/wake behavior separately before adding generic DMA properties.
- Update the UART row in [`docs/HARDWARE_SUPPORT.md`](../../docs/HARDWARE_SUPPORT.md)
  and the baseline only from an actual mainline boot capture.
- See the [source validation](results/mainline-uart-source-validation.txt)
  for exact hashes and the reuse decision.
