# Experiment: MT6797 display-mutex recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-mt6797-display-mutex-recovery` |
| Status | `completed` |
| Subsystem | MT6797 display hardware mutex |
| Device variant | Gemini PDA running Gemian |
| Date | 2026-07-12 |
| Investigator | Repository maintainer with Codex assistance |

## Question

What module bits, SOF/EOF values, register layout, clock policy, power domain,
interrupt, and GCE client tuple must Linux 7.1 model for the MT6797 display
mutex?

## Provenance and environment

- Exact Gemian GPL tree: commit
  `d388d350cb2dda8f23b99be6fa5db9628896e87f`, principally
  `drivers/misc/mediatek/video/mt6797/dispsys/` and
  `arch/arm64/boot/dts/mt6797.dts`.
- Mainline comparison: checksum-verified Linux 7.1.3 prepared by the
  repository workflow.
- Live target: Gemini PDA running kernel 3.18.41+; unique device identifiers
  are excluded.

## Safety assessment

The collector's default path reads only kernel-exported state. Its explicit
`--read-driver-dump` mode reads the vendor driver's read-only `disp/dump`
debugfs callback. That callback first checks the DDP manager's power state and
then uses the driver's existing mapping to read and format display state. The
script contains no MMIO write, clock, power, display, or driver-control
operation. Raw output remains in the Git-ignored
`artifacts/device-inventory/` tree.

An earlier source-audited attempt to read the same ordinary registers through
BusyBox `devmem` was stopped after the SoC's DEVAPC rejected every access and
logged an access violation for each read. All values returned as zero and are
not hardware state. The distributed collector deliberately has no direct
physical-memory mode, and that probe must not be repeated.

## Associated code

- [`scripts/collect-live-display-mutex.sh`](scripts/collect-live-display-mutex.sh)
  captures the live DT, platform, interrupt, clock-search, and optional
  source-audited vendor display dump.
- [`scripts/check-mutex-contract.py`](scripts/check-mutex-contract.py)
  mechanically compares the vendor module/SOF tables with the Linux driver
  data and SoC node.

## Procedure

1. Recover the register and bit contract from the exact Gemian GPL revision.
2. Compare it with the Linux 7.1 generic MediaTek mutex implementation and
   every existing platform record.
3. Run the collector normally, then once as root with `--read-driver-dump`
   while the stock display is active.
4. Decode the capture and compare the live mask with the source-defined path.
5. Add the minimal binding, platform data, and standalone SoC provider; run
   schema, object, DTB, full-series, and package-integrity checks.

## Observations

The normalized capture is committed as
[`results/runtime-summary.txt`](results/runtime-summary.txt). Private raw
captures are retained as
`artifacts/device-inventory/20260712-live/display-mutex.txt` and
`display-driver-dump.txt`, with SHA-256 values
`8d8f4205f7af042abc42b0e385ee0ae4a573351adb3aa856cd796ae17fa82dfa`
and
`374e590a5d9737f81fbb6dacbd997ef4895b229f339e66b67f9f5c2a7e66f1dd`.
The later source-audited `/sys/kernel/debug/mtkfb` capture is
`display-state-mtkfb.txt`, SHA-256
`1f709ae04ff506635423d39e9b122a7dac8142efc635bceb464ea407df8a3ded`.

The live platform device is `1401f000.mm_mutex`, with vendor compatible
`mediatek,mm_mutex`, a 4 KiB aperture, and Linux IRQ 234 (SPI 202 plus the
GIC SPI base), level-low. It had handled 3,888 interrupts across two online
CPUs at the first snapshot. No debug-clock name contains `mutex`, consistent
with the complete downstream clock table having no mutex gate.

The SoC's DEVAPC rejected direct physical reads even as root. Every returned
value was zero and therefore invalid; the 52 access-violation messages are
the useful result. The source-audited vendor display dump used the driver's
existing mapping safely, but reported that the DDP power state was off at
capture, so that immediate callback did not expose a live module mask. The
vendor `mtkfb` ring buffer nevertheless retained a source-audited active
boot-time dump with mutex0 enabled, module mask `0x05fcb400`, and SOF/EOF
value `0x41`.

## Analysis

The Gemian implementation defines ten hardware mutex handles. Its DDP manager
allocates handles 0 through 3 and reserves handle 4 for the separate overlay
software trigger. The register layout is the original MediaTek layout:
interrupt enable/status at 0x000/0x004 and each handle at a 0x20-byte stride,
with enable at 0x20, module mask at 0x2c, and combined SOF/EOF at 0x30.

Seventeen positive module bits occupy 10 through 26: OVL0, OVL1, OVL0_2L,
RDMA0, RDMA1, OVL1_2L, WDMA0, WDMA1, COLOR0, CCORR, AAL, GAMMA, OD, DITHER,
UFOE, DSC, and PWM0 in ascending order. This is not the MT6795/MT8173 map.
The three-bit SOF source is in bits 2:0 and the matching EOF source is in bits
8:6. Video-mode DSI0 therefore uses `0x41`; DSI1 uses `0x82`, and DPI0 uses
`0xc3`.

The retained active dump decodes mutex0's `0x05fcb400` mask to OVL0,
OVL0-2L, RDMA0, OVL1-2L, COLOR0, CCORR, AAL, GAMMA, OD, DITHER, UFOE, and
PWM0. Its `0x41` SOF/EOF value independently confirms the recovered DSI0
video-mode encoding. OVL1, WDMA, RDMA1, DSC, and unused outputs are absent as
expected for the named primary path.

The standalone provider requires the MM power domain but no clock. Its GCE
client address is selector `SUBSYS_1401XXXX` (ID 2), offset `0xf000`, size
`0x1000`; mutex0 and mutex1 stream-EOF events are 58 and 59.

Patches 28–30 add the binding compatible, dedicated 17-component/SOF driver
data, and enabled standalone SoC provider. `CONFIG_MTK_CMDQ`, its mailbox, and
`CONFIG_MTK_MMSYS` are built-in because the project package intentionally does
not install modules. Strict `checkpatch.pl`, the focused binding, all three
MT6797 DTBs with the focused schema, and a `W=1` mutex object build pass. The
mechanical checker reports:

```text
PASS components=17 module-bits=10-26 sof-sources=4 register-layout=0x2c/0x30 no-clk=true irq-spi=202 power-domain=MM gce-subsys=2
```

The complete series builds as the checksum-clean package
`linux-7.1.3-gemini-a5336f4954ff`. Its patch-set SHA-256 is
`a5336f4954ff0ac1c50a47b5ef9a008bf40f4d6d2f5afe5b69f86bc54d0ad345`
and configuration SHA-256 is
`0f98f03129508907261efaa6f1b195799313530628505e319d48427105ac385f`.
The packaged Image SHA-256 is
`802e760203e3c279db2b70d77bbeaf3aea84ea7074bfb68d945646ffcb819144`,
System.map is
`2f5ca28b11f050e290fa80463920606adeab8fbb8d03c287c3a2485aacc89fb0`,
the Gemini DTB is
`9ee924dddda8cd32e10b6b6768d991747ddeef8cea0ce763685b7f5af668ef8f`,
and `build.json` is
`398c75f2aa3dcf7456eb11050efee907f507ae3cdaec4dea68e3481b64f7112b`.
Every package manifest entry passes in both the VM and the ignored host
export `artifacts/20260712T072016Z/`. The compiled node contains SPI202,
MM-domain ID 3, events 58/59, and GCE selector 2 with offset `0xf000` as
intended.

## Conclusion

Confirmed for the named MT6797/Gemini evidence: the recovered binding and
platform contract agree with the live DT, IRQ, negative clock evidence, and
the retained active mutex0 register state. Linux 7.1 runtime remains unproven
until the resulting image is booted on Gemini hardware.

## Follow-up

Attach DRM consumers only after their own clocks, resets, interrupts, GCE
events, subsystem selectors, power-domain behavior, and M4U ports are
independently verified.
