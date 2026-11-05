# Experiment: the microSD slot on MSDC1 with the upstream mtk-sd driver

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-05-gemini-microsd` |
| Status | `running`: card detect never changed in T1, nor in T1b with GPIO67's pull-up on. Patch 0580 keeps VMCH on, as the vendor does; T1c is predeclared |
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
build follows.

**Buildbox build.** `83b0ad81`, profile `mt6797-a53-station`, `BUILD_MODULES=1`, 751
patches, package inventory `bda22044…`, patchset `db77f1a1…`, config `d7fb4aca…`,
`Image.gz` `eba89a7c…`; validation passed. Its station DTB (`5032d60c…`) has `mmc1`
`okay`, aliases `mmc0 = /mmc@11230000` and `mmc1 = /mmc@11240000`, and `cd-gpios`
`<&pio 0x43 0>`. Built, not booted. The station images are composed from
`mt6797-a53-station-a72`, which this profile can't stand in for, so the custodian
built that profile from `fec36c2e` for T1 (below).

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

Image: profile `mt6797-a53-station-a72` (the profile station images are composed from) with `BUILD_MODULES=1`, from the commit that adds
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

### T1 (2026-11-05)

Custodian run. Package `fcc3525b…`, profile `mt6797-a53-station-a72` from `fec36c2e`;
station DTB `59613dfa1c8aaff9893d10efcfe4353a4686f38fa329484645a8bd1229625e8a`; boot2
`8d620ab7beef73df3b8e0892e54d7a9550f2caff4f398ea5113c1fa12a493502`, written with
`flash-boot2` and verified; boot `9b4a0eca`; taint 0 throughout; `sd-state.sh` hash
matched. Raw outputs are private.

**Step 1, slot empty.** As expected:

- The eMMC is `mmc0` on `11230000.mmc`, at `mmcblk0` with its 33 partitions.
  `data` was mounted from it as usual.
- Both MSDC hosts probed with no MMC error, and `11240000.mmc` logged "Got CD GPIO".
- `mmc1`: no card; `ios` clock 0, power off, 1 bit, 3.30 V.
- GPIO67 is claimed as `cd`: input, low, with an IRQ. EINT6 is edge, count 0.
- MSDC1's SPI 80 count is 0.
- `vmch` and `vmc` are disabled at 3000000 µV with no users.
- MT6351 registers: `0a2e` `1a60`, `0aaa` `1a60`, `0ace` `0005`, `0ae2` `061b`.
  VMCH's trim field is 5 and VMC's is `0x1b`. VMCH's VOSEL is 0 and VMC's is 6, so both
  select 3.0 V. Both enable bits are clear.
- Pad registers at entry: IES `0x7fff9fff` (MSDC1 input enabled), PUPD `0x1b81803e`,
  R0 `0x40007fc0`, R1 `0x247b8021`, drive `0x24855555`, SMT `0x1d000f87`.

  Decoded for MSDC1: CMD has no pull (PUPD/R0/R1 0/0/0); DAT0-3 are 0/0/1; CLK is
  1/0/0. The vendor's active state is 0/1/0 on CMD and DAT and 1/0/1 on CLK, so the
  firmware didn't leave it. SMT bit 27, shared by GPIO66 and GPIO67, is set.

**Step 2, test card inserted.** The owner said the card was in. Nothing changed:

- GPIO67 stayed low and EINT6 stayed at 0.
- There was no MMC line and no `mmcblk1`.
- Rails, PMIC registers and pads were identical to step 1.

The only new log lines were a lid close and open during the insertion. Whether the card
clicked fully into place was asked afterwards. The owner answered "Yes, it clicked in",
so the result stands. Steps 3 to 5 weren't run, so nothing was mounted or written.

**Conclusion.** This is the table's "no change on GPIO67" branch.

The Gemian source explains it. Its MSDC1 probe selects an `insert_cfg` state that puts
GPIO67 in EINT6 mode with Schmitt trigger and `bias-pull-up`
([`msdc_io.c` lines 739-757](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/mmc/host/mediatek/mt6797/msdc_io.c#L739-L757),
[board DTS `mmc1_ins_cfg`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L748-L784)).
The same tree's GPIO table (`gpio_cfg.h`, SHA-256 `29ea8cc6…`, as in the
[pad record](../2026-07-12-mt6797-msdc-recovery/MICROSD_PADS.md)) places GPIO67's pull
fields in IOCFG_R:

| Field | Address | Bit |
| --- | --- | --- |
| pull-up enable | `0x100028e0` | 14 |
| pull-down enable | `0x100028c0` | 14 |
| input enable | `0x10002810` | 14 |
| Schmitt | `0x10002830` | 27 (already set) |

MT6797 pinctrl in this series sets no pull. A contact switch that opens when a card is
in then reads low both ways. The lid on GPIO66 works without a pull because its Hall
sensor drives the line. Inference, to be tested by T1b: the card-detect line needs the
pull-up.

### T1b (predeclared)

Same boot or any boot of the T1 image. If the card is still in at the start, run step 1
with it in, then step 2. The pin should then go high with an EINT6 edge. Then do step 3
in reverse: empty, then inserted again.

1. Slot empty. Read `0x100028e0`, `0x100028c0` and `0x10002810` with `devmem`, plus
   the `gpio-67` line and the EINT6 count.

   Expect pull-up bit 14 clear. If it is already set, stop: the pull isn't the cause.
2. One read-modify-write of `0x100028e0` setting bit 14 only, and clear bit 14 of
   `0x100028c0` if it is set. Read both back.

   No other writer exists: MT6797 pinctrl here has no pull support. These are input
   pads; the effect is a weak pull on GPIO67 alone.
3. Read `gpio-67` with the slot empty, then the owner inserts the test card until it
   clicks. Read again and note `dmesg` and the EINT6 count.

   Expect low when empty, high with the card, and an EINT6 edge.
4. If the card then identifies, continue T1 steps 2 to 6 as written, on this boot.
   If it identifies and then gives CMD `-110` timeouts, stop. That's the CMD pull
   branch, for the next image.
5. Undo by clearing bit 14 of `0x100028e0`, or by the next boot.

| Observed | Do |
| --- | --- |
| Pull-up set, GPIO67 follows the card, card works | Card detect needs the pull: add an MT6797 PU/PD map for GPIO67 and `bias-pull-up` in the DT, next batched image |
| Pull-up set, GPIO67 follows the card inverted | Same, plus `cd-inverted` |
| Pull-up set, GPIO67 still doesn't change | Stop. Next is the switch wiring; read Gemian's live GPIO67 with and without a card |
| Pull-up bit was already set at step 1 | Stop; the pull isn't the cause |

### T1b result (2026-11-05)

Custodian run, on the same boot `9b4a0eca` and image `8d620ab7`; taint 0. The owner
approved it ("Yes, run T1b"). Before T1b, the owner confirmed the T1 card had clicked in.

1. Card in, before any write:
   - `0x100028e0` = `0x00012b40`: pull-up bit 14 clear.
   - `0x100028c0` = `0x00028400`: pull-down bit 14 clear, so it wasn't written.
   - `0x10002810` = `0x0003ffff`: input enable bit 14 set.
   - `0x10002830` = `0x1d000f87`: Schmitt bit 27 set.
   - GPIO67 low, EINT6 count 0, no `mmcblk1`.
2. One write, `0x100028e0` = `0x00016b40`, read back as written. 3 s later, with the
   card still in: GPIO67 low, EINT6 0, no MMC line.
3. Card removed: GPIO67 still low, EINT6 0. The lid closed during the removal.
4. Undone: `0x100028e0` written back to `0x00012b40`.

So GPIO67 reads low with the card in and out, with or without its pad pull-up. This
is the table's "still doesn't change" row.

The Gemian source has one more step that mainline lacks. At the end of the MSDC1 probe,
after the generic code powers the empty slot off, a board addition calls
`msdc_sd_power(host, 1)` for any removable slot and prints "power on vmch"
([`sd.c` lines 5817-5820](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/mmc/host/mediatek/mt6797/sd.c#L5817-L5820)).
That is why Gemian showed VMCH on with an empty slot. Under mainline, VMCH was off at
both readings (`0a2e` bit 1 clear, 0 users).

Inference, to be tested by T1c: the card-detect switch is referenced to VMCH, so with
VMCH off the pin can't go high.

### T1c (predeclared)

[0580](../../patches/proposals/0580-arm64-dts-mediatek-gemini-station-keep-the-microSD-c.patch)
adds `regulator-always-on` to VMCH at 3.0 V, as the vendor leaves it. The MMC core
still asks for and releases VMCH around a card; the core just never turns it off.
VMC is unchanged.

Image: `mt6797-a53-station-a72` with `BUILD_MODULES=1`, from the commit adding this
section or later. It's DT only, so batch it with any waiting DT change. Same cards;
the owner is present.

1. Slot empty. `sh sd-state.sh empty`. Expect `vmch` enabled at 3000000 and `0a2e`
   bit 1 set; GPIO67 low.
2. Owner inserts the test card. As T1 step 2: expect GPIO67 high, an EINT6 edge and
   the card identified.
3. If GPIO67 still doesn't change, apply the T1b pull-up write once, read GPIO67 with
   the card in and then out, and undo it. That separates "VMCH alone" from "VMCH and
   the pad pull" before any driver work.
4. If the card identifies, continue T1 steps 3 to 6 as written.

Stop conditions are T1's. VMCH staying on adds the vendor's own idle state: 3.0 V on
the card supply with no card.

| Observed | Do |
| --- | --- |
| GPIO67 follows the card at step 2 | VMCH is the card-detect reference. Keep 0580 and go on to the card itself |
| Only with the pull-up at step 3 | Both are needed: an MT6797 PU/PD map for GPIO67 and `bias-pull-up`, as in T1b's table |
| GPIO67 inverted | Add `cd-inverted` |
| Still no change | Stop. Next, read-only on Gemian: GPIO67's level with and without a card, to check the slot and pin on this unit |
| Card detected, then CMD `-110` | Stop. The CMD pull-up is next, as in T1's table |

## Follow-up

- High speed (50 MHz), then UHS with the 1.8 V switch, each after this test, and the
  latter only with the VMC trim question in the [power record](../2026-07-12-mt6797-msdc-recovery/MICROSD_POWER.md#the-18-v-trim-subtraction-has-a-refusal-boundary) settled.
- exFAT as a module, for SDXC cards in their factory format.
