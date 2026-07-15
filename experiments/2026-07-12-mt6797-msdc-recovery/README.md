# Experiment: MT6797 MSDC recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-mt6797-msdc-recovery` |
| Status | `inconclusive` for current-mainline runtime; compatibility and conservative DT boundary recovered |
| Subsystem | MT6797 MSDC0 eMMC and MSDC1 microSD |
| Device variant | Gemini PDA running Gemian |
| Date | 2026-07-12 through 2026-07-14 |
| Investigator | Repository maintainer with Codex assistance |

## Question

Which Linux 7.1 `mtk-sd` compatibility flags accurately describe MT6797, what
are the live eMMC/card-slot operating states, and which conservative device
tree contract can bring up storage without prematurely enabling high-speed or
voltage-switching modes?

## Evidence and safety

The owner-authorized live probe uses the committed
[`collect-live-msdc.sh`](scripts/collect-live-msdc.sh). It excludes CID, CSD,
serial number, and raw uevent data. Raw output is private and ignored by Git at
`artifacts/device-inventory/20260711-live/msdc.txt`; only a normalized summary
will be committed. A fresh read-only run is retained privately at
`artifacts/device-inventory/20260714-live/msdc.txt` and hashed in the
[consolidated live snapshot](../2026-07-14-first-boot-probe-audit/results/live-runtime-snapshot-20260714.txt).

The optional register snapshot was audited against the exact downstream
`drivers/mmc/host/mediatek/mt6797/dbg.c`. Writing `5 4 ID` to
`/proc/msdc_debug` only queues `SD_TOOL_REG_ACCESS` operation 4. Reading the
file then enables the selected controller clock, reads ordinary registers,
explicitly skips the TX and RX FIFO registers, and disables the clock. No
controller register, storage block, tuning value, clock source, drive strength,
or regulator state is written.

Source comparison uses the exact Gemian GPL tree at downstream commit
`d388d350` and the Planet board tree at commit `c5b0be85`, compared with the
pinned Linux 7.1.3 source. Public source is implementation evidence; live
state wins when it differs.

## Associated source analyzer

The source-level comparison is read-only. It reads vendor files from Git
objects and compares MT6797 registers and compatibility flags with Linux
7.1.3's `mtk-sd` driver:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-12-mt6797-msdc-recovery/scripts/analyze-mt6797-msdc-contract.sh
```

Its design record is
[`mt6797-msdc-mainline-design.md`](results/mt6797-msdc-mainline-design.md).

The current Linux 7.1.3 source-contract capture is
[`mainline-msdc-contract-audit-20260714.txt`](results/mainline-msdc-contract-audit-20260714.txt).

The package-boundary reconciliation for the corrected current c2d package is
[`mainline-msdc-current-c2d-reconciliation-20260714.txt`](results/mainline-msdc-current-c2d-reconciliation-20260714.txt).
It uses the package-delta proof to carry the MSDC source, probe-safety, and
pinctrl conclusions forward from the prior package without rebuilding or
claiming a runtime boot (result SHA-256
`b35518c9b787937291c3f67c1d435af95a0fe32885c3048515548bbf169bf837`).

The authoritative 77-patch diagnostic package is audited directly by
[`audit-current-package-msdc.sh`](scripts/audit-current-package-msdc.sh); its
result is [`mainline-msdc-current-77-package-20260714.txt`](results/mainline-msdc-current-77-package-20260714.txt).
That package carries the built-in MMC, PWRAP, MT6351 regulator, and MT6797
pinctrl chain, with the same conservative 8-bit/25 MHz eMMC DT contract. The
audit is static package evidence only; it does not claim a mainline boot.

The probe and MMC-core side-effect audit is recorded in
[`mainline-msdc-probe-safety-audit-20260714.txt`](results/mainline-msdc-probe-safety-audit-20260714.txt)
and is reproducible with
[`audit-mainline-msdc-probe-safety.sh`](scripts/audit-mainline-msdc-probe-safety.sh).

The pinctrl callback and property boundary is recorded in
[`mainline-msdc-pinctrl-audit-20260714.txt`](results/mainline-msdc-pinctrl-audit-20260714.txt)
and is reproducible with
[`audit-mt6797-pinctrl-contract.sh`](scripts/audit-mt6797-pinctrl-contract.sh).

The independently tracked bsg100 hardware result is checked without importing
its source or binary artifacts by
[`audit-bsg100-msdc-crosscheck.sh`](scripts/audit-bsg100-msdc-crosscheck.sh).
The normalized cross-check is
[`bsg100-msdc-crosscheck-20260714.txt`](results/bsg100-msdc-crosscheck-20260714.txt).

## Compatibility findings

The MT6797 register map requires a dedicated compatibility record:

- the clock divider is 12 bits and `MSDC_PAD_TUNE0` is at `0xf0`;
- asynchronous FIFO and data tuning are present;
- `0x228` is `EMMC50_BLOCK_LENGTH`, not the newer `SDC_FIFO_CFG`, so
  `stop_clk_fix` must remain false;
- the vendor map has no `SDC_ADV_CFG0` at `0x64`, so `enhance_rx` must remain
  false;
- the vendor initialization value has patch-bit-1 bit 7 set, matching the
  Linux 7.1 path selected by `busy_check = false`;
- the hardware defines high-address descriptor fields, but the downstream
  driver truncates GPD, BD, and payload pointers to 32 bits and never enables
  `MSDC_PB2_SUPPORT64G`; Linux must start with `support_64g = false`;
- no separate top register window is used.

These facts make reuse of `mt6779_compat` unsafe even though it is structurally
close. In particular, its stop-clock workaround would modify eMMC block-length
state on MT6797.

## Live findings

The normalized capture is committed as
[`results/runtime-summary.txt`](results/runtime-summary.txt). The internal
device identifies as a 64 GB-class SanDisk DF4064 eMMC. Unique CID/CSD and
serial fields were excluded.

The 2026-07-14 read-only run still identifies DF4064 on MSDC0 and the same
MT6797 MSDC0/MSDC1 providers. It deliberately did not use `--read-registers`,
so the current snapshot is not a new tuning/register capture; the earlier
stateful record remains the source for HS400 and pad-register observations.

| Property | MSDC0 / eMMC | MSDC1 / microSD |
| --- | --- | --- |
| Runtime media | DF4064 eMMC present | no card present |
| Clock | 200 MHz | 0 Hz |
| Bus width | 8 bits | reset state, 1 bit |
| Timing | MMC HS400 | legacy |
| Signal voltage | 1.8 V | 3.3 V reset state |
| Power | on | off |
| Controller version | `0x20141118` | `0x20140512` |
| Host IRQ count | 10,937 combined across two CPUs at capture | 0 |

MSDC0 `MSDC_CFG=0x03700099` decodes to clock mode 3, the HS400 bit set,
and divider zero. This independently confirms that the vendor stack really
runs the interface at the 200 MHz/HS400 capability advertised by its DT.

The live patch registers materially support the compatibility choices:
`PATCH_BIT1=0xfffe00c0` has bit 7 set, while
`PATCH_BIT2=0xa48d180d` has SUPPORT64G bit 1 clear. DMA high-address register
`0x8c` is also zero. `PAD_TUNE0=0x002b2100` is active and `PAD_TUNE1=0`,
confirming that PAD_TUNE0 is the correct generic tuning-register anchor for
the captured state.

VEMC is enabled at 3.0 V with one consumer. VMCH and VMC both report enabled
at 3.0 V with two vendor-framework consumers despite an empty, powered-off
MSDC1. Their class enable/user state is therefore not a trustworthy proxy for
whether the card slot is electrically powered; the MMC IOS state is the
stronger observation.

## Bring-up policy

Patches 16 through 18 add the binding compatible, dedicated driver data, and
disabled MT6797 SoC nodes. Patches 19 and 20 add the Planet board identity and
an initial Gemini DTS. They pass strict `checkpatch.pl` apart from the generic
new-file MAINTAINERS reminder; the driver builds with `W=1`; the focused
binding checks pass; both upstream MT6797 DTBs and the Gemini DTB build and
validate against the relevant schemas.

The Gemini DTS deliberately uses a different capability set than the vendor
tree: 8-bit, non-removable eMMC capped at 25 MHz with no HS, HS200, or HS400
flags. Its pin state covers GPIO114–125 at the vendor's raw drive code 1,
represented by the upstream MT6797 drive table as 4 mA. VEMC is the 3.0–3.3 V
core supply. VIO18 is the 1.8 V signaling supply, matching live 1.8 V IOS,
the enabled fixed VIO18 rail, and the established MT8173 eMMC supply model;
because downstream never manages this rail and other unmodeled consumers may
share it, the initial DTS marks it always on.

The board file preserves all fixed firmware carveouts recovered from the live
boot contract. It intentionally does not copy the vendor's ten CPU
`clock-frequency` properties: Linux 7.1.3's CPU binding rejects that metadata,
and the values are retained as descriptive evidence rather than treated as an
OPP/DVFS table. The shipping LK behavior documented by the historical 4.9 port
must therefore be handled by the boot handoff, not by an invalid mainline CPU
property.

The first mainline board boot enables only MSDC0/eMMC at conservative timing.
HS200/HS400 and MSDC1 UHS voltage switching remain opt-in later milestones
after runtime validation of the regulator, pinctrl, tuning, and card-detect
paths. Build/schema success is not runtime proof; no mainline image has yet
been booted on the Gemini.

### Probe-safety boundary

Linux 7.1.3's `msdc_drv_probe()` is stateful: it allocates DMA descriptors,
enables the controller clocks, resets and programs the MSDC registers, installs
the IRQ, enables runtime PM, and calls `mmc_add_host()`. The MMC core then
starts the host, powers it up through the driver's `set_ios()` callback, and
schedules card identification. With the current non-removable/no-SD/no-SDIO
Gemini node, that path will attempt eMMC identification rather than merely
registering a passive controller.

The first `set_ios()` path can set/enable VEMC through `mmc_regulator_set_ocr()`
and enable the always-on VIO18 consumer; a later signal-voltage switch can
change VQMMC and select the default/UHS pinctrl state. These are intentional
controller and PMIC ownership transitions, not read-only probes. The current
25 MHz, no-HS/HS200/HS400 board policy limits the protocol surface, but it does
not remove the register, clock, regulator, or card-identification side effects.
The first runtime test therefore needs a non-primary boot, external recovery,
and a read-only rootfs/storage policy. See the
[source audit](results/mainline-msdc-probe-safety-audit-20260714.txt).

The earlier 72-patch package text below is retained as historical build
evidence. The canonical current package is
`linux-7.1.3-gemini-b7721ab55e41`, and its direct MSDC provenance is recorded
in the current 77-patch result above. The canonical workflow applies the
current 77-entry series to a fresh
checksum-verified Linux 7.1.3 tree, builds `Image` and every arm64 DTB, and
produces the package artifacts. Its source,
patchset, merged-config, Image, Image.gz, and Gemini-DTB SHA-256 values are
recorded in
[`mainline-msdc-current-77-package-20260714.txt`](results/mainline-msdc-current-77-package-20260714.txt).
The current diagnostic package intentionally has `modules_built=false`; its
Image and DTBs contain the built-in first-boot path but no module tree. (The
older module-bearing package remains historical evidence.) The validation and
all three source audits are read-only build/source-contract results: the
conservative eMMC node has not
been booted, no MMC I/O has run under mainline, and no storage hardware was
written. The cross-subsystem [first-boot probe dependency audit](../2026-07-14-first-boot-probe-audit/README.md)
proves that this eMMC consumer depends on the built-in PWRAP, MT6351 MFD, and
regulator path; the storage test is therefore not PMIC-independent.

The source audit confirms that the existing Linux `mtk-sd` driver is the right
controller implementation with a dedicated MT6797 compatibility record; no
new MSDC driver is indicated. The experiment remains runtime-inconclusive
until the conservative eMMC node boots on Gemini and microSD voltage/card-
detect behavior is tested separately.

## Cross-repository pinctrl check

The independent [bsg100/gemini-linux](https://github.com/bsg100/gemini-linux)
record (see the [repository-wide comparison audit](../2026-07-13-bsg100-gemini-linux-comparison/README.md))
reports that its first MT6797 eMMC boot failed because `pinctrl-mt6797.c` had only mode, direction, data-in,
and data-out maps; removing pull, input-enable, and drive-strength properties
allowed the card to enumerate. The current Linux 7.1.3 MT6797 descriptor has
the same four register maps and no bias, IES, or drive callbacks. Our original
Gemini board patch nevertheless supplied all three unsupported generic
pinconf classes.

The follow-up patch
`0071-arm64-dts-mediatek-gemini-use-pinmux-only-for-MT6797-MSDC.patch` removes
those properties from the first eMMC state and leaves pad configuration to the
boot firmware until a source-backed MT6797 pinconf map is recovered. This is
a conservative compatibility correction, not proof that the boot firmware's
pad values are ideal. The reproducible source audit is
[`audit-mt6797-pinctrl-contract.sh`](scripts/audit-mt6797-pinctrl-contract.sh)
with output in
[`mainline-msdc-pinctrl-audit-20260714.txt`](results/mainline-msdc-pinctrl-audit-20260714.txt).

The same bsg100 log sequence provides a stronger hardware cross-check than a
source similarity alone: its level-low SPI79 declaration removed an interrupt
storm, explicit VEMC/VIO18 supplies removed the empty OCR failure, and the
MT2701-generation compatibility profile plus pinmux-only groups produced a
real DF4064 eMMC with partitions p1–p33. The local 7.1.3 board keeps those
validated boundaries while using the more specific `mediatek,mt6797-mmc`
identity and a 25 MHz first-boot cap. This is corroborating evidence from a
Linux 6.6 boot, not a runtime result for the current 7.1.3 package.
