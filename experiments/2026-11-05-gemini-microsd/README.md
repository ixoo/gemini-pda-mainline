# Experiment: the microSD slot on MSDC1 with the upstream mtk-sd driver

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-05-gemini-microsd` |
| Status | `planned`: patch 0579 is in the station series; the first device test is predeclared and not run |
| Subsystem | MSDC1 (`mmc@11240000`), MT6351 VMCH and VMC, GPIO67 card detect, GPIO129-134 |
| Device variant | Planet Computers Gemini PDA, MT6797X, boot2 station |
| Date(s) | 2026-11-05 |
| Investigator(s) | project session, device custody with the custodian session |
| Tracking issue | microSD, listed as not started in [hardware support](../../docs/HARDWARE_SUPPORT.md) |

## Question or hypothesis

Does the upstream `mtk-sd` driver, with the MT6797 compatible data the eMMC already
uses, detect, read and write a microSD card on MSDC1 at default speed and 3.3 V
signalling, without disturbing the eMMC on MSDC0?

Hypothesis: card detect on GPIO67 reads high with a card in, as the vendor driver
interprets it; the firmware leaves the MSDC1 pads usable for default speed; VMCH and
VMC at 3.0 V power the card and its I/O; and the eMMC stays `mmc0`/`mmcblk0`.

## What earlier records establish

From the [2026-07-12 MSDC recovery](../2026-07-12-mt6797-msdc-recovery/README.md) and
its microSD follow-ups. None of these is a mainline microSD observation.

| Fact | Kind | Source |
| --- | --- | --- |
| MSDC1 at `0x11240000`, SPI 80; clocks `infra_msdc1` (parent `msdc30_1_sel`), AXI and the MSDC30_1 mux | in the SoC node from patch 0018, disabled | [0018](../../patches/v7.1.3/0018-arm64-dts-mediatek-mt6797-add-MSDC-controllers.patch) |
| `mediatek,mt6797-mmc` compatible data | used by the eMMC on every station boot | [0017](../../patches/v7.1.3/0017-mmc-mtk-sd-add-MT6797-support.patch) |
| Under Gemian, MSDC1 empty: 0 Hz, 1 bit, power off, 3.3 V reset state, no interrupts | observed, 2026-07 | [runtime summary](../2026-07-12-mt6797-msdc-recovery/results/runtime-summary.txt) |
| Vendor card supply VMCH, I/O supply VMC, both requested at 3.0 V | vendor source and retained kernel | [contract](../2026-07-12-mt6797-msdc-recovery/MICROSD_CONTRACT.md#power-ownership) |
| Card detect GPIO67, vendor reads high as present | vendor DTB and retained kernel; the switch's polarity is not measured | [contract](../2026-07-12-mt6797-msdc-recovery/MICROSD_CONTRACT.md#card-detection) |
| GPIO67 reaches EINT6 in mode 1 | patch 0377, in the station series | [0377](../../patches/proposals/0377-pinctrl-mediatek-mt6797-use-the-EINT-mux-mode-on-ded.patch) |
| GPIO129-134 are CMD, DAT0-3, CLK, function 1 | vendor GPIO table, matches upstream pin functions | [pads](../2026-07-12-mt6797-msdc-recovery/MICROSD_PADS.md#field-map) |
| The vendor probe nudges the VMCH and VMC trim fields and sets a pad bias field; upstream does neither | retained kernel | [power](../2026-07-12-mt6797-msdc-recovery/MICROSD_POWER.md), [pads](../2026-07-12-mt6797-msdc-recovery/MICROSD_PADS.md#boundaries-a-direct-table-port-would-miss) |
| The upstream regulator operations leave the trim bits as they find them | source | [power](../2026-07-12-mt6797-msdc-recovery/MICROSD_POWER.md#the-standard-regulator-operations-preserve-trim-bits) |

Inferred, to be tested: that the firmware's pad state (pull, drive, input enable) is
good enough for default speed, since the MT6797 pin data in the station series has
pinmux only, as the eMMC already relies on. The isolated pull, drive and input-enable
topics from 2026-09-09 are against 7.3-rc1 and are not in the station series.

## The change

[0579](../../patches/proposals/0579-arm64-dts-mediatek-gemini-station-describe-the-micro.patch),
one DT change to `mt6797-gemini-pda-station.dts`, appended to `patches/series` and
`patches/series-a53-station`. No driver, clock or regulator code was missing.

- `&mmc1` enabled: 4 bits, `max-frequency` 25 MHz and no `cap-sd-highspeed`, so default
  speed; `no-1-8-v` and no UHS modes, so the 1.8 V switch never runs; `no-mmc`,
  `no-sdio`; `cd-gpios = <&pio 67 GPIO_ACTIVE_HIGH>`, no `cd-inverted`.
- `vmmc-supply` VMCH and `vqmmc-supply` VMC, each held at exactly 3.0 V.
- A pinmux-only state for GPIO129-134. GPIO67 isn't in it: the GPIO request and then
  the interrupt request set its mode, as with the lid sensor.
- `mmc0`/`mmc1` aliases. The station's `init`, `flash-boot2` and `radio-start` search
  only `mmcblk0p*` for their partitions; the aliases keep the eMMC there whichever
  host probes first.

`CONFIG_MMC_MTK`, `MMC_BLOCK`, `VFAT_FS` and `EXT4_FS` are already built in; there's
no exFAT, so an SDXC card in its factory format can't be mounted here. The change is
DT only, so it needs a boot2 image; it has no module form.

## Compile check

Against the prepared `series-a53-station` source on Buildbox, with that tree's `cpp`
include paths and the kernel's `dtc`, output in a scratch directory since removed: the
station DTS with the change compiles with the same four warnings as without it. The
decompiled difference is the two aliases, the `mmc1-default-pins` state (pinmux
`0x8101`-`0x8501`, `0x8601`), `ldo-vmch` and `ldo-vmc`, and the `mmc1` properties with
`cd-gpios = <&pio 0x43 0>`. No schema check: Buildbox has no `dt-validate`. The full
build is below once it has run.

## Safety assessment

- **eMMC.** MSDC1 has its own registers, interrupt, gate and mux; it shares only the AXI
  bus clock, which is reference-counted and held by the eMMC. VMCH and VMC don't feed
  the eMMC (VEMC and VIO18 do). Pins 129-134 and 67 are not eMMC pins. The aliases pin
  the eMMC to `mmcblk0`. The test writes only to the card's block device, found by
  host name, never by number alone.
- **Card.** The read-only card is mounted `ro` and only listed by count; no file names,
  CID, CSD or serial number leave the device. The read-write step uses a card the owner
  calls disposable, writes one 64 MiB file and deletes it.
- **PMIC.** VMCH and VMC switch on and off at 3.0 V through the regulator core, as the
  MMC core powers the slot; the trim bits are left as found. Their state at mainline
  entry is read in step 1. Nothing writes a PMIC register directly.
- **Electrical.** 3.0 V on both rails is the vendor's own request. No 1.8 V switch.
- **Reversible.** Removing the node or the card ends it. boot2 only, written with
  `flash-boot2`; the other boot slots are untouched.

Stop at once, `umount` anything mounted and power off for the owner, on: any `mmc0`
error in `dmesg`, a kernel warning or Oops, the eMMC not at `mmcblk0`, or a write
appearing anywhere but the card.

## Associated code

- [`sd-state.sh`](sd-state.sh), read-only: MMC hosts and block names, `mmc1` `ios`, the
  card-detect GPIO and pinctrl lines for pins 67 and 129-134, interrupts, the `vmch`
  and `vmc` regulators, MT6351 registers `0x0a2e`, `0x0aaa`, `0x0ace`, `0x0ae2` through
  regmap debugfs one line at a time, and the MSDC1 pad registers in IOCFG_B and IOCFG_R
  with `devmem`. It needs debugfs and `devmem`, so a station profile, not the release
  one.

## Procedure (predeclared T1)

Image: profile `mt6797-a53-station` with `BUILD_MODULES=1`, from the commit that adds
this record or later, composed as a station image and written to boot2 with
`flash-boot2`. Batch it with other DT changes if any are waiting. Attended: the owner
inserts and removes cards. Cards: a test card with some files on it, FAT32 or ext4, and
a disposable card, which may be the same card if the owner says its contents can go.
Budget: one boot; each step once; one write of 64 MiB.

1. Slot empty. Status lines as usual (`data=mounted` from `mmcblk0`), `uname -r`,
   taint, `dmesg | grep -i -E 'mmc|msdc'`, `sh sd-state.sh empty`.

   Expect `mmc0` on `11230000.mmc` with the eMMC's partitions on `mmcblk0`, `mmc1` on
   `11240000.mmc` with no card, `ios` power off, and GPIO67 low.
2. Owner inserts the test card. Within 10 s: new `dmesg` lines, `sh sd-state.sh inserted`.

   Expect a card-detect interrupt, `mmc1: new SD`/`SDHC card at address`, `mmcblk1` with
   its partitions, `ios` at 4 bits, up to 25 MHz, 3.30 V signalling, power on; `vmch`
   and `vmc` enabled at 3000000.
3. `mount -o ro /dev/mmcblk1p1 /mnt/sd` (after checking
   `/sys/block/mmcblk1/device` resolves under `11240000.mmc`), the entry count of its
   root and `df` for it, then `time dd if=/dev/mmcblk1 of=/dev/null bs=1M count=64`.
   `umount`.
4. Owner removes the card. New `dmesg`, `sh sd-state.sh removed`. Expect the removal,
   no `mmcblk1`, `ios` power off.
5. Owner inserts the disposable card. Same host check, then mount it read-write,
   `head -c 67108864 /dev/urandom > /mnt/sd/gemini-sd-t1.bin`, `sync`, `sha256sum` it,
   `umount`, `echo 3 > /proc/sys/vm/drop_caches`, mount `ro`, `sha256sum` again, remount
   read-write, delete the file, `umount`. Time the write and the second read.
6. `dmesg` since step 1 and taint. Leave the card in or out as the owner likes.

If the card's partition isn't FAT or ext4 (`blkid -s TYPE`), skip the mounts in steps 3
and 5, keep the `dd` read, and say so.

## Decision table

| Observed | Do |
| --- | --- |
| All as expected | Record; update hardware support for microSD at default speed; next, `cap-sd-highspeed` at 50 MHz on the next batched image |
| eMMC not at `mmcblk0`, or any `mmc0` error | Stop, power off. The node or aliases are wrong |
| `mmc1` host absent, or probe error | Send step 1; stop. Probe or supply problem in the node |
| No change on GPIO67 when the card goes in | Send steps 1 and 2; stop. Next: the pin's pull, or the switch has no pull-up without the vendor's setting |
| GPIO67 changes the opposite way (high when empty) | Finish nothing more; next image adds `cd-inverted` |
| Card detected, then `-110` timeouts on CMD | Send steps 1-2; stop. Next: the CMD/DAT pull-ups, from the pull topic, or the pad bias the vendor sets |
| Identified, but reads fail or CRC errors | Send; stop. Next: a lower `max-frequency` or the pad drive |
| Write or readback hash differs | Send; stop. No second write |

## Observations

Not run yet.

## Follow-up

- High speed (50 MHz), then UHS with the 1.8 V switch, each after this test, and the
  latter only with the VMC trim question in the [power record](../2026-07-12-mt6797-msdc-recovery/MICROSD_POWER.md#the-18-v-trim-subtraction-has-a-refusal-boundary) settled.
- exFAT as a module, for SDXC cards in their factory format.
