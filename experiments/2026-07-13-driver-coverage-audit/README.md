# Experiment: current driver coverage and ownership boundary

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-13-driver-coverage-audit` |
| Status | `completed` for static package/live ownership comparison; runtime mainline boot remains untested |
| Subsystem | kernel image composition, platform-driver ownership, MT6797 reuse boundary |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant is not independently established |
| Date | 2026-07-13–2026-07-14 |

## Question

Which drivers in the current Linux 7.1.3 candidate are actually available in
the bootable Image, which are module-only, and which vendor-owned blocks still
need a new MT6797 boundary or a deferred firmware/ABI investigation?

## Method and limits

The audit compares three immutable/read-only views:

1. `kernel.config` and `System.map` from the exact current 77-patch package;
2. the patched Linux source tree and its probe entry points;
3. the private, sanitized 2026-07-14 live driver/resource capture from the
   Gemian device.

`System.map` proves that a symbol is linked into the Image; a `CONFIG_*=m`
entry proves only that a module can be built. It does not prove that a module
was loaded or that a device probed. The current diagnostic package has no
optional module tree; the first-boot Image
still exposes only its linked-in drivers. No device writes, driver bind/unbind,
bus scans, or mainline boot were performed.

Run the reproducible audit in the VM:

```sh
./scripts/dev-vm run env \
  CURRENT_PACKAGE=/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-b7721ab55e41 \
  LIVE_CAPTURE=/mnt/gemini-pda-mainline/artifacts/device-inventory/20260714T211054Z-vendor-baseline-driver-refresh/mainline-runtime.txt \
  experiments/2026-07-13-driver-coverage-audit/scripts/audit-driver-coverage.sh
```

## Coverage decisions

| Live vendor ownership | Current Linux 7.1.3 boundary | Decision |
| --- | --- | --- |
| `mtk-uart` on all four UARTs | `8250_mtk`/MT6577-compatible driver is built in; UART0 DT is enabled with PIO resources; AP-DMA is module-only and not claimed by the board | Reuse the existing 8250 driver for the first console; keep vendor VFIFO/AP-DMA deferred |
| `mtk-msdc` on both MSDC controllers | `mtk-sd` with `CONFIG_MMC_MTK=y` and MT6797 compatibility is built in; Gemini enables only internal eMMC at 25 MHz | Reuse the generic host with MT6797 data; validate read-only storage after boot |
| vendor `mtk-wdt` | `mtk_wdt` and `MEDIATEK_WATCHDOG` are built in; Gemini carries the source-backed pretimeout IRQ | Reuse; test only with recovery and explicit opt-in |
| vendor pinctrl/GPIO and EINT | MT6797 pinctrl is built in; the local series supplies the decoded EINT map and virtual lines | Reuse the framework with MT6797 data; prove IRQ/polarity/wake on hardware |
| vendor pwrap/PMIC and rails | Upstream MTK pwrap/MT6397 framework is built in; the MT6351 MFD/regulator/RTC pieces are local 7.1.3 additions and remain unprobed on mainline | Reuse the upstream pwrap/MFD interfaces with the new local MT6351 implementation; keep consumers conservative until readback |
| vendor USB11/USB3 | MUSB, MTU3, and xHCI probe code are built in; Gemini USB nodes remain disabled and live vendor role/VBUS ownership is unresolved | Reuse generic cores plus local MT6797 glue; bring up gadget-only first |
| vendor display and audio | DRM Mediatek and ASoC MT6797 paths are module-only; optional modules are packaged but no rootfs loads them and board consumers remain disabled | Keep build-only; do not mistake source/object validation for a display/audio probe |
| vendor thermal/AUXADC | MTK thermal/AUXADC paths are module-only and calibration/ownership differs from the vendor ABI | New MT6797 calibration/data boundary is justified, but keep disabled until boot and raw-sample evidence |
| vendor M4U/SMI/CMDQ/display fabric | Mainline IOMMU/SMI/MMSYS/mutex paths are built in, with local MT6797 data; all risky consumers remain disabled | Reuse generic frameworks; attach one verified DMA consumer at a time |
| vendor WMT/CONSYS, CCCI/CLDMA, camera ISP, DVFSP, touch, and vendor framebuffer | No drop-in Linux transport/ABI; several live vendor drivers have no mainline equivalent or require firmware ownership | Deferred/new-driver investigations; do not copy vendor platform ABI |

The strongest immediate boot path is therefore intentionally small: built-in
PSCI/timer/GIC, pinctrl, UART0 PIO, watchdog, and eMMC. Everything else is
either a built-in provider without an enabled consumer, a module requiring a
rootfs/modules package, or a separate ownership/firmware problem.

## Associated evidence

- Historical package audits remain available for comparison.
- Current 77-patch package audit: [`results/driver-coverage-current-77-package-20260714.txt`](results/driver-coverage-current-77-package-20260714.txt), package `linux-7.1.3-gemini-b7721ab55e41`, with `modules_built=false`.
- Package source/config/DTB hashes and static handoff closure:
  [`handoff-closure-20260713.txt`](../2026-07-13-mainline-handoff-closure/results/handoff-closure-20260713.txt).
- Private live ownership capture is linked from the hardware inventory result;
  it remains Git-ignored and mode 0600.
- Module-bearing packages remain historical evidence and do not imply that a
  driver probed.
  Runtime mainline boot and module loading remain untested.
