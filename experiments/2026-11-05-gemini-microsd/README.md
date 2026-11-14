# Experiment: the microSD slot on MSDC1 with the upstream mtk-sd driver

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-05-gemini-microsd` |
| Status | `completed`: microSD at UHS SDR104 (192 MHz, about 86 MiB/s, vendor pad settings, exFAT), and the eMMC at HS400 (192 MHz DDR, about 250 MB/s reads, T9) after HS200's reads failed silently (T6-T8d), with hotplug and a card at boot. Card detect needs VMCH kept on (patch 0580) |
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

### T1c result (2026-11-05)

Custodian run, owner present. The owner approved the boot ("Yes, boot it") and the
write on the test card ("Same card is fine").

- Image `f0f66d1bdeb4859e705eeee4c019a58ae78448e6ccdaeaf073d4617669225236`, package
  `557f9d68…`, profile `mt6797-a53-station-a72` from `b23c2346`. That commit also
  carries the FM patches 0581 and 0582.
- Station DTB `c58c636f4adaf3ac96a23e28f83e2eda268eba061d79f077f49287acf74fc1fb`, with
  VMCH always on.
- Boot `0b3c33aa`, taint 0 throughout, no warning or Oops. `sd-state.sh` hash matched.
  Raw outputs are private.

1. **Slot empty.** The eMMC is `mmc0`/`mmcblk0`. `mmc1` has no card, `ios` power off,
   GPIO67 low. `vmch` is enabled at 3000000 with one user, and `vmc` is disabled.
   PMIC `0a2e` `da62` (VMCH enable bit set), `0aaa` `1a60`; trims as in T1. Pads are
   as in T1.
2. **Test card inserted.**
   - At 108.29 s the log shows "host does not support reading read-only switch,
     assuming write-enable", a new SDHC card, and `mmcblk1` of 14.8 GiB with one
     partition.
   - `ios`: 25 MHz requested (23999992 Hz actual), VDD bit 18 (3.0-3.1 V), power on,
     4 bits, legacy timing, 3.30 V.
   - GPIO67 high. EINT6 count 1, MSDC1 interrupt count 31.
   - The pinctrl lines changed from `1000` to `1001`: data-in went to 1.
   - `vmch` has two users, `vmc` is enabled at 3000000 (`0aaa` `da62`).
3. **Read-only.** `mmcblk1` resolved under `11240000.mmc`. The read-only mount
   returned 0, with 6 root entries; the filesystem is vfat. 64 MiB read with `dd` from
   the raw device in 5.86 s, about 11.5 MB/s. That is close to the 12.5 MB/s ceiling
   of 4 bits at 25 MHz.
4. **Removed.** Four CMD13 lines logged a timeout (`host->error=0x2`), then "card
   removed". GPIO67 low, EINT6 count 2, no `mmcblk1`, `ios` power off. `vmch` stays on
   with one user, and `vmc` is disabled.
5. **Reinserted and written.** Detected again at 226.35 s; host check passed.
   - Mounted read-write as vfat. A 64 MiB file from `/dev/urandom` plus `sync` took
     12.39 s, 2.57 s of it in user time generating the data, so about 6.7 MB/s to the
     card.
   - After `umount`, `drop_caches` and a read-only mount, `sha256sum` took 5.98 s and
     gave the same hash as before.
   - The file was removed and the card unmounted cleanly.
6. **End.** Taint 0, no new MMC error. The card is left in the slot.

**Conclusion.** The hypothesis held on one boot of one unit, with one card.

- The card-detect switch is referenced to VMCH. With VMCH on, GPIO67 reads high with a
  card in, as the vendor's `cd_level` says, and needs no pad pull-up from Linux.
- The upstream `mtk-sd` driver with the MT6797 data and the firmware's pad state
  identifies, reads and writes an SDHC card at default speed and 3.3 V.
- The eMMC stayed `mmcblk0` with no error throughout.

The CMD13 timeouts on removal are the MMC core polling a card that has just gone, not
a fault.

**Not shown:**
- high speed or UHS;
- SDXC or exFAT, or more than one card;
- suspend and resume;
- a card already in the slot at boot;
- long transfers or error recovery;
- the effect of the vendor's trim adjustments, which mainline doesn't apply;
- whether VMC or VMCH sit at their nominal voltage on this unit.

### Read benchmark (2026-11-05, unattended)

Custodian run on boot `a22a4ca8`, image `02e045fa` (0579 and 0580, default speed), with
the T1c card left in the slot and not mounted. `mmcblk1` was under `11240000.mmc`;
`ios` at 25 MHz (23999992 Hz actual), VDD bit 18. Raw output is private.

Caches were dropped before each read, then `dd if=/dev/mmcblk1 of=/dev/null bs=1M
count=256`, timed with `/proc/uptime`:

| Offset | Time | Rate |
| --- | --- | --- |
| 0 | 23.28 s | 11.5 MB/s |
| 4096 MiB | 23.29 s | 11.5 MB/s |
| 12000 MiB | 23.28 s | 11.5 MB/s |

There were no MMC or MSDC log lines and taint stayed 0. The rate is flat across the
card and matches T1c's. It sits just under the 12 MB/s that 4 bits at 24 MHz carry,
so the bus, not the card, sets it at default speed. Data integrity isn't covered by
these reads, which didn't hash anything.

### T2, card present at boot (2026-11-05, unattended)

Read-only, on the same boot `a22a4ca8` (image `02e045fa`), with the T1c card in the slot
since before boot. `sd-state.sh` hash matched. Raw output is private.

1. Boot log:
   - 0.856 s: `11240000.mmc` got its CD GPIO; both MSDC hosts probed with 0.
   - 0.953 s: the eMMC identified as `mmc0`/`mmcblk0`, with all its partitions.
   - 1.047 s: `mmc1` identified the SDHC card, and `mmcblk1` came up with one partition.
   - Both hosts enabled the MMC core's software queue.
2. `ios` at 25 MHz, VDD bit 18, 4 bits, power on. `mmcblk1` resolved under
   `11240000.mmc`.
3. The first 1 GiB of the raw card, read twice through `sha256sum`: 92.93 s each
   (11.55 MB/s), same hash both times.
4. No MMC or MSDC line after boot; taint 0.

So a card present at boot is identified during boot, after the eMMC, which stays
`mmcblk0`. Repeated 1 GiB reads return the same data. This is consistency, not a
comparison against known contents.

### T3, SD high speed (predeclared)

[0606](../../patches/proposals/0606-arm64-dts-mediatek-gemini-station-run-the-microSD-sl.patch)
adds `cap-sd-highspeed` and raises `max-frequency` from 25 to 50 MHz. Signalling stays
at 3.3 V, with no UHS mode, so no 1.8 V switch and no tuning.

- **Driver.** mtk-sd treats SD high speed like legacy timing. It has no tuning for
  it, and MT6797 has no top register window to program.
- **Clock.** The source runs at about 192 MHz (24 MHz was 192 / (4 x 2)). The
  divider for 50 MHz is 1, so the clock should be 48 MHz, double today's.
- **Pads.** They keep the firmware's state: drive selector 4 on CMD, DAT and CLK
  (`0x100025b0` bits 21-29), the vendor's bias value 5 in bits 16-20 of the same
  register, and no CMD pull-up.

**Candidate.** Built on Buildbox from `799bc8c4`, which also carries the usb-c
session's U3 changes: profile `mt6797-a53-station-a72` with modules, 777 patches,
package `3bc96f03…`, patchset `ff4ccf67…`, config `4df1f9bd…`, `Image.gz`
`15e43aa6…`; validation passed. Its `mt6797-gemini-pda-station-a72.dtb`
(`59a17455…`) has `mmc1` at `max-frequency` 50000000 with `cap-sd-highspeed` and
`no-1-8-v`. Built, not booted.

Hypothesis: the card switches to high speed at 48 MHz and reads at about twice T2's
rate, with no CRC error or timeout, and the same data. T2's hash of the first 1 GiB
gives a known answer.

Image: `mt6797-a53-station-a72` with `BUILD_MODULES=1`, from the commit adding this
section or later. DT only, so batch it. The T1c card stays in the slot; nothing
needs the owner except approving the write in step 4.

1. Boot with the card in. `dmesg | grep -i -E 'mmc|msdc'`; expect "new high speed
   SDHC card" on `mmc1`, and the eMMC unchanged as `mmc0`/`mmcblk0`. `sh sd-state.sh
   hs`: expect `ios` timing "sd high-speed", clock 50000000 requested, about 48 MHz
   actual, 4 bits, 3.30 V.
2. Host check as before, then `time dd if=/dev/mmcblk1 bs=1M count=1024 | sha256sum`,
   twice. Expect T2's hash `fd02d592…35c4` both times, in about 45-50 s each.
3. Three 256 MiB timed reads at offsets 0, 4096 MiB and 12000 MiB, after dropping
   caches, as in the benchmark.
4. If the owner approves a write on this card: T1 step 5 once (64 MiB, hash,
   readback, delete), timing the write.
5. `dmesg` MMC lines since boot, taint.

Stop on any `mmc0` error, a warning or Oops, a hash mismatch, or a CRC or timeout
error on `mmc1`. No retry, one write at most.

| Observed | Do |
| --- | --- |
| High speed, rates about doubled, hashes match | Keep 0606; microSD runs at SD high speed |
| Card stays at default speed | Send step 1. The card or the switch command refused high speed; check the log line |
| CRC errors, timeouts or a hash mismatch at 48 MHz | Stop. Next: the CMD pull-up and the pad drive, or fall back to 25 MHz by reverting 0606 |
| Rates not doubled, no errors | Record it. Something else bounds the transfer; look at the request size and DMA |

### T3 result (2026-11-06)

Custodian run on station-work-62: package `639e173b…` built from `15bde8ff`, which
carries 0606; DTB `417ad6d6…`; boot2 `676ad310…`. Boot `2dc6de9f` throughout, taint 0.
The T1c card was in the slot and nothing was mounted. Raw output is private.

1. **Boot.**
   - `mmc1` logged "new high speed SDHC card", then `mmcblk1` at 14.8 GiB. The eMMC
     was unchanged as `mmc0`/`mmcblk0`.
   - `ios`: 50 MHz requested, 47999984 Hz actual, VDD bit 18, 4 bits, SD high-speed
     timing, 3.30 V, driver type B.
   - `vmch` enabled at 3000000 with two users.
   - The pad drive, PUPD and R1 registers read as in T1.
2. **Repeat read.** The first 1 GiB, read twice through `sha256sum`: 54.45 s and
   52.75 s. Both gave T2's hash `fd02d592…35c4`, so the data read at high speed
   matches the data read at default speed. These times include the CPU's hashing.
3. **Spread reads.** 256 MiB after dropping caches: 11.72 s at offset 0, 11.73 s at
   4096 MiB, 11.71 s at 12000 MiB. That's about 22.9 MB/s, 1.98 times T2's
   11.55 MB/s.
4. **Write**, approved by the owner ("Yes, write"). `mmcblk1` resolved under
   `11240000.mmc`; mounted read-write as vfat.
   - 64 MiB from `/dev/urandom` plus `sync`: 8.79 s, 1.77 s of it user time, against
     12.39 s at default speed.
   - After `umount`, `drop_caches` and a read-only mount, the hash read back in
     3.09 s, against 5.98 s at default speed, and matched.
   - The file was deleted and the card unmounted.
   - No MMC or FAT error. The log was cleared at 194 s for another test, so this
     check covers 194 s onward; steps 1 to 3 had shown no error before that.
5. **Log.** No new error, warning or Oops line; no CRC error or timeout on either
   host; taint 0.

The hypothesis held on one boot of one unit with one card. At SD high speed the card
reads at twice the default-speed rate and returns the same data. A 64 MiB write reads
back intact, and the pads the firmware left need nothing more at 48 MHz. 0606 stays.

### T3 extra, second card (2026-11-06, read-only)

The owner supplied a second, larger SDXC card. Same boot `2dc6de9f`, taint 0, no
mount and no write. Card identity is kept private.

- **Hot swap.** The first card was logged as removed, then the second identified as
  a high-speed SDXC card with one partition. Card detect worked live.
- **Mode.** `ios` at 50 MHz requested, 47999984 Hz actual, 4 bits, SD high-speed
  timing, 3.30 V.
- **Reads.** Two 1 GiB raw reads after dropping caches, not hashed: 46.63 s and
  46.62 s, 22.0 MiB/s (23.0 MB/s) each. That is the 16 GB card's rate.
- **Log.** No error, warning or Oops line.

Two cards of different classes read at the same rate, close to the 24 MB/s a 4-bit
bus carries at 48 MHz. So the bus is the limit at SD high speed. More speed needs
UHS: 1.8 V signalling, SDR50 or SDR104, and tuning.

### T4, UHS SDR50 (predeclared)

Two cards hit the 4-bit, 48 MHz bus limit at SD high speed. The next step up is UHS.

[0609](../../patches/proposals/0609-arm64-dts-mediatek-gemini-station-allow-UHS-SDR50-on.patch)
makes these changes:

- VMC's range is now 1.8 to 3.0 V. For 3.3 V signalling the MMC core asks
  3.0-3.3 V first, so it still gets 3.0 V.
- `no-1-8-v` is removed.
- `sd-uhs-sdr12`, `sd-uhs-sdr25` and `sd-uhs-sdr50` are added, and `max-frequency` is
  raised to 100 MHz.

SDR104 and DDR50 stay out.

**Vendor 1.8 V sequence and mainline.** From the Gemian source:

| Vendor step | Here |
| --- | --- |
| VMC to 1.8 V | Done by the MMC core's signal-voltage switch through mtk-sd |
| VMC trim field set to its saved default minus 2, commented "+40 mV" ([`msdc_io.c` `msdc_sd_power_switch`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/mmc/host/mediatek/mt6797/msdc_io.c#L199-L222)) | Not done. VMC keeps the trim the firmware left (`0x1b`), which mainline has never changed. Its 1.8 V level relative to the vendor's is unknown |
| RDSEL to 0 for 1.8 V (`0xc30c` at 3.3 V) | Already 0: the firmware leaves `0x100024a0` at 0, and the slot has worked at 3.3 V with it |
| TDSEL `0xccc` in both modes | The firmware leaves `0x333`; working at 3.3 V |
| Drive changed for UHS (CMD/DAT 3, CLK 4 in the vendor's units, against 6 by default) | Not done. The pads keep the firmware's selector 4; MT6797 pinctrl here has no drive callback |

**Clock.** The source is about 192 MHz. mtk-sd gives a 100 MHz request as the source
divided by 2, 96 MHz. SDR104 at 208 MHz would need a faster parent, such as
`msdcpll_d2`, which is a separate step.

**Tuning.** mtk-sd runs its generic tuning through `PAD_TUNE0`, which the MT6797 data
already selects, the same as for the eMMC.

**Electrical.** 1.8 V is VMC's own table entry and the vendor's request. The card's
I/O and MSDC1's pads take 3.3 V already, so a VMC level off by the trim is a
functional risk, not an overvoltage. VMCH stays at 3.0 V. If the switch fails, the MMC
core power-cycles the card and comes back at 3.3 V without UHS.

**Candidate.** Built on Buildbox from `6488e6f8`: profile `mt6797-a53-station-a72`
with modules, 780 patches, package `e46c9f38…`, patchset `d77cde69…`, config
`4df1f9bd…`; validation passed. Its `mt6797-gemini-pda-station-a72.dtb`
(`4f0593cf…`) has `mmc1` at 100000000 with `sd-uhs-sdr12/25/50` and no `no-1-8-v`,
and VMC at 1800000-3000000. Built, not booted.

Hypothesis: the card accepts the 1.8 V switch and tunes, then runs SDR50 at 96 MHz.
It reads at 40 MB/s or more and returns T2's data unchanged.

Image: `mt6797-a53-station-a72` with `BUILD_MODULES=1`, from the commit adding this
section or later; DT only, so batch it. The 16 GB card in the slot. Step 4 needs the
owner's OK.

1. Boot with the card in. MMC lines; expect "new ultra high speed SDR50 SDHC card".
   `sh sd-state.sh uhs`, and `cat /sys/kernel/debug/clk/msdc30_1_sel/clk_rate`
   (not `clk_summary`). Expect `ios` timing "sd uhs SDR50", signal 1.80 V, about
   96 MHz; `vmc` at 1800000; PMIC `0ae2` VOSEL 3 with trim `0x1b` unchanged.
2. Twice: the first 1 GiB of `mmcblk1` through `sha256sum`. Expect T2's hash
   `fd02d592…35c4`.
3. Three 256 MiB reads after dropping caches, at 0, 4096 MiB and 12000 MiB.
4. With the owner's OK: T1 step 5 once (64 MiB write, hash, readback, delete).
5. Remove and reinsert the card once. Expect it back at SDR50 and VMC back to 3.0 V
   while it was out. MMC lines and taint.
6. If the owner offers the second card, steps 1 and 3 on it, read-only.

Stop on any `mmc0` error, a warning or Oops, a hash mismatch, or a CRC or timeout
error on `mmc1` after tuning. No retry, one write at most.

| Observed | Do |
| --- | --- |
| SDR50, about 96 MHz, faster reads, hashes match | Keep 0609. Next, SDR104 with a faster clock parent |
| Falls back to high speed at 3.3 V (switch or tuning refused) | Send step 1's log. Next: the vendor's VMC +40 mV, with its trim behaviour settled, or the drive |
| SDR50, but CRC errors or a hash mismatch | Stop. Same next steps; revert 0609 meanwhile |
| SDR50, rate not raised | Record it; the DMA or request path bounds it |

### T4 result (2026-11-06)

Custodian run on station-work-64: composed from package `e46c9f38…` (`6488e6f8`),
boot2 `54bab6bc…`, boot `294ae5a1`, taint 0. The image also carries the usb-c
session's 0608. Raw output is private.

**Second, SDXC card** (in at boot; the owner asked to start with it; read-only):

- The log shows "new UHS-I speed SDR50 SDXC card".
- `ios`: 100 MHz requested, 95999969 Hz actual, 4 bits, UHS SDR50 timing, 1.80 V.
- `vmc` at 1800000, `vmch` at 3000000. `msdc30_1_sel` reads 191999939 Hz, which
  confirms the 192 MHz source.
- 256 MiB reads at 0, 4096 MiB and 12000 MiB: 5.97, 5.87 and 5.86 s, which is
  42.9-43.7 MiB/s (about 45 MB/s).

**16 GB card**, hot-swapped in:

- The log shows "new UHS-I speed SDR50 SDHC card"; same `ios`, VMC at 1.8 V.
- Two 1 GiB reads through `sha256sum`, 41.88 s and 42.12 s, agreed with each other
  (`e6057a37…c6bb`).
- 256 MiB reads at the three offsets: 5.96-5.97 s, about 43 MiB/s.

No MMC, CRC, timeout or tuning error, and no warning; taint 0.

**Stale reference.** The 1 GiB hash didn't match T2's `fd02d592…35c4`, which tripped
step 2's stop rule. The predeclaration was wrong, not the data. T3's write step
created and deleted a 64 MiB file on this card after T2's hash was taken, which
changes FAT, directory and data clusters inside the first 1 GiB. So T2's hash was no
longer this card's content.

Decision (this session, 2026-11-06): take `e6057a37…` as the card's current
reference and continue on the same boot. T4's write step, a fresh write with hash
and readback at SDR50, carries the integrity check instead. Two reads agreeing and no
transfer error support this, but don't prove the content matches a 3.3 V read.

**Write (step 4).** The owner approved it ("Yes, write"). SDR50 was confirmed before
mounting and the host check passed; the card was mounted read-write as vfat.

- 64 MiB from `/dev/urandom` plus `sync`: 8.98 s (2.02 s user), against 8.79 s at SD
  high speed. The write is bound by the card, not the bus.
- After `umount`, `drop_caches` and a read-only mount, the readback took 1.98 s,
  against 3.09 s at SD high speed, and its hash matched.
- The file was deleted and the card unmounted.
- No error, CRC, timeout, tuning, FAT or warning line.

**Reinsert (step 5).** The card was logged as removed at 535.61 s and back as a UHS-I
SDR50 SDHC card at 539.26 s. `ios` at 95999969 Hz, 1.80 V; `vmc` at 1800000. No
error.

**Conclusion.** The hypothesis held on one boot of one unit with two cards.

- Both cards switch to 1.8 V and tune, then run SDR50 at 96 MHz.
- Reads run at about 43 MiB/s, 1.9 times SD high speed.
- A 64 MiB write reads back intact.
- A fresh insert returns to SDR50.
- Neither the vendor's VMC +40 mV trim nor its drive change was needed.

0609 stays. The 16 GB card's first 1 GiB changed again with step 4's file, so no
reference hash is kept for it.

### T5, the remaining gaps in one image (predeclared)

After T4 the owner asked for every remaining gap to be implemented and tested in
one go. Each one, and what this image does about it:

| Gap | Change | Patch |
| --- | --- | --- |
| eMMC at 25 MHz legacy timing | HS and HS200 at up to 200 MHz, 8 bits, 1.8 V (VIO18). The mux keeps the firmware's parent | [0615](../../patches/proposals/0615-arm64-dts-mediatek-gemini-station-run-the-eMMC-at-HS.patch) |
| microSD SDR104 | `sd-uhs-sdr104`, `max-frequency` 200 MHz, MSDC30_1 reparented to `msdcpll_d2`, the vendor's 200 MHz source. `msdcpll` and the eMMC's mux are untouched | [0614](../../patches/proposals/0614-arm64-dts-mediatek-gemini-station-allow-UHS-SDR104-o.patch) |
| "assuming write-enable" at each insert | `disable-wp` | 0614 |
| MSDC1 pads left as the firmware set them | MT6797 pinctrl gains input-enable, TDSEL, RDSEL, drive (2-16 mA) and PUPD/R0/R1 fields for GPIO129-134 | [0612](../../patches/proposals/0612-pinctrl-mediatek-mt6797-describe-the-MSDC1-pad-field.patch) |
| | The DT then sets the vendor's values: CMD and DAT pulled up (R0), CLK pulled down (R1), TDSEL `0xc`. At 3.3 V, 14 mA and RDSEL `0xc`; in the UHS state, CMD/DAT 8 mA, CLK 10 mA, RDSEL 0 | [0613](../../patches/proposals/0613-arm64-dts-mediatek-gemini-station-set-the-microSD-pa.patch) |
| exFAT for SDXC cards | `CONFIG_EXFAT_FS=m` with UTF-8 names (`NLS_UTF8=y`) in the station fragment | config |

**Left out, with reasons:**

- **eMMC HS400** needs a data-strobe delay this tree doesn't have.
- **DDR50** is commented out in the vendor's own board description.
- **The VMC +40 mV trim** wasn't needed at SDR50. It stays out unless SDR104 fails.
- **VMCH stays always on.** Card detect depends on it, so it isn't a gap to close.
  The card can't be power-cycled for recovery.
- **The pad bias-tuning bits** are left: the firmware already sets the vendor's 5.
- **Suspend** isn't started anywhere in the project.
- **A second unit** and **upstream submission** need the owner.

**Risk.** The eMMC holds the root and data partitions. If HS200 doesn't tune, the
MMC core gives up on the eMMC for that boot. The station's init then reports
`data=not-found` and keeps running from RAM, so USB SSH stays up. Recovery is the
reviewed Gemian path, since `flash-boot2` needs the eMMC.

A marginal link could damage data on a read-write mount. So this boot must mount
`/mnt/data` read-only, as the release init does, until the eMMC checks in step 2
pass. The custodian decides how to compose that. No eMMC partition is written in
this test.

**eMMC protection for T5.** The custodian's review asked for these answers before
the owner decides. HS200 changes the timing on the device that holds the GPT, the
boot partitions, NVRAM and the data partition, so the owner treats it as a new risk,
not under standing approval.

- **`/mnt/data` read-only from the start, guaranteed by the image.** The station's
  `init` is the only thing that mounts the `linux` partition, at
  `rw,noatime`. For T5 the composed RAM root uses one change in that mount, the
  same pattern `init` already uses for `nvdata`:

  ```sh
  $bb blockdev --setro "$data" && $bb mount -t ext4 -o ro,noload "$data" /mnt/data
  ```

  `--setro` makes the block layer refuse writes to that partition. `noload` stops a
  journal replay, and with the device read-only ext4 can't clear an orphan list
  either.

  Nothing else in the RAM root writes the eMMC:
  - `nvdata` is already `--setro` and `ro,noload`;
  - the display marker's `touch` fails on a read-only mount, so `init` reports
    `display=skipped-no-data` and keeps simplefb;
  - `flash-boot2` runs only by hand and isn't run on this boot;
  - pstore is in RAM;
  - `mmcblk0boot0/1` are read-only by kernel default (`force_ro`), and RPMB is
    untouched.

- **No eMMC data write until step 2 passes, and none at all in T5.** HS200 selection
  sends CMD6 to the volatile HS_TIMING byte, which a power cycle resets; it writes
  no stored data. The bus-width switch does the same today.

  If HS200 tuning fails, the 7.1 MMC core doesn't fall back to HS or legacy timing.
  `mmc_init_card` frees the card (`goto free_card` after `mmc_hs200_tuning`), and
  the eMMC is absent for that boot. Absent means no reads or writes, not a degraded
  mode.

- **The station without its data partition.** The root is the RAM initramfs, so
  busybox, dropbear on USB, the modules and the firmware tools keep working.
  - Status goes to `/run/station/status`, logs to the kernel ring and pstore, all
    in RAM.
  - With the eMMC absent, `init` reports `data=not-found`; with HS200 working but
    read-only, `data=mounted`.
  - The custodian copies evidence off over USB SSH before power-off.

- **Stop and recovery.** On any `mmc0` error, a tuning failure, an absent eMMC or
  disagreeing hashes: stop, copy the logs off over SSH, and `poweroff`. Don't rewrite
  boot2 from this boot, since that would itself be an eMMC write.
  - The owner powers on normally, which lands in Gemian from the primary boot slot.
  - From Gemian, the reviewed device guard writes boot2 back to the last good
    station image (station-work-65 or later without 0615), as in the station
    record's recovery path.
  - Gemian's first eMMC access after power-on is at its own timing; nothing from
    this boot persists in the eMMC's timing state.

**T5 candidate.** Built on Buildbox from `f0fe8d1a`, which also carries the usb-c
session's 0610 and the audio session's 0611. Profile `mt6797-a53-station-a72` with
modules, 786 patches, package `469cd863…`, patchset `00538f34…`, config `6316c478…`,
`Image.gz` `91e8fbae…`.

- Validation passed. The package was copied straight from Buildbox's validated
  artifacts, because `fetch-package` only looks up HEAD, and its SHA256SUMS check
  passed locally.
- `pinctrl-mt6797.o` compiled with no warning.
- Its `mt6797-gemini-pda-station-a72.dtb` (`d2f61e49…`) has:
  - `mmc0` at 200000000 with `cap-mmc-highspeed` and `mmc-hs200-1_8v`;
  - `mmc1` at 200000000 with `sd-uhs-sdr104`, `disable-wp` and the assigned
    MSDC30_1 parent;
  - both MSDC1 pad states.
- `fs/exfat/exfat.ko` is in the modules, with `EXFAT_DEFAULT_IOCHARSET="utf8"` and
  `NLS_UTF8=y`.

Built, not booted.

**Live clocks before T5** (custodian, boot `294ae5a1`, read-only debugfs, after the
patches were written):

| Clock | Rate | Parent |
| --- | --- | --- |
| `msdcpll` | 383999878 | `clk26m` |
| `msdcpll_d2` | 191999939 | `msdcpll_ck` |
| `msdc50_0_sel` | 383999878 | `msdcpll` |
| `msdc50_0_hclk_sel` | 273000000 | `syspll1_d2` |
| `msdc30_1_sel` | 191999939 | `msdcpll_d2` |

So `msdcpll` runs at 384 MHz under mainline, not the vendor's 400. MSDC30_1 is
already on `msdcpll_d2`, which makes 0614's reparent a no-op that only pins the
parent; its message says "move", and the record corrects it here. SDR104 will run
at the 192 MHz source rate, and eMMC HS200 at 384 / 2 = 192 MHz.

The eMMC's EXT_CSD reports revision `0x08`, DEVICE_TYPE `0x57` (HS200 and HS400 at
1.8 V, DDR52) and HS_TIMING 0. `ios` showed it at 24 MHz in legacy timing, with
VEMC at 3.3 V and VIO18 at 1.8 V.

**Hypothesis.**

- The eMMC tunes HS200 at 192 MHz and reads at least four times faster, with
  the same data.
- The microSD card tunes SDR104 at 192 MHz and reads faster than SDR50's
  43 MiB/s.
- The vendor's pad values read back from pinctrl in each state.
- exFAT mounts an SDXC card read-only.

Image: `mt6797-a53-station-a72` with `BUILD_MODULES=1`, from the commit adding this
section or later. One boot.

1. **Boot.** Status lines with `data` read-only; taint; MMC lines. Expect `mmc0`
   "new HS200 MMC card" and `mmc1` "new UHS-I speed SDR104 …".
   - `cat /sys/kernel/debug/mmc0/ios /sys/kernel/debug/mmc1/ios`.
   - For `msdcpll`, `msdcpll_d2`, `msdc50_0_sel` and `msdc30_1_sel`: their
     `clk_rate` and `clk_parent` (not `clk_summary`).
   - `sh sd-state.sh t5`.
   - The pinconf lines for pins 129-134 from
     `/sys/kernel/debug/pinctrl/*/pinconf-pins`.
2. **eMMC, read-only.**
   - Find the `linux` partition by its GPT name, as init does. Twice:
     `dd if=<it> bs=1M count=1024 | sha256sum`, timed. The two hashes must agree.
     The partition is mounted read-only, so they can.
   - Stop on any `mmc0` CRC, timeout or tuning error.
3. **microSD, read-only.** On whichever card is in: two 1 GiB hashes that must
   agree, and three 256 MiB timed reads at 0, 4096 MiB and 12000 MiB.
4. **microSD write**, only with the owner's OK: T1 step 5 once on the 16 GB vfat card.
5. **Hotplug.** Remove and reinsert; expect SDR104 again. The pinconf lines go back
   to the default state while the card is out.
6. **exFAT**, only if the owner supplies an exFAT card or the SDXC card's partition is
   exFAT: `modprobe exfat` or `insmod`, a read-only mount, the root entry count and
   `df`, then unmount. No write.
7. **End.** Taint, MMC lines, then normal operation. If step 2 passed, `data` may be
   remounted read-write as usual.

Stop on any `mmc0` error, a warning or Oops, disagreeing hashes, or CRC or timeout
errors after tuning. No retry, one write at most, never on the eMMC.

| Observed | Do |
| --- | --- |
| All as expected | Keep 0612-0615 and the exFAT config; record the speeds |
| eMMC not HS200 or absent | Stop, keep `data` unmounted, recover via Gemian. Revert 0615; HS (52 MHz) alone is the next step |
| eMMC HS200 but errors or disagreeing hashes | Stop, no write. Revert 0615 |
| microSD falls back to SDR50 or high speed | Record it. If tuning failed at SDR104, next is the vendor's VMC +40 mV, or a 400 MHz `msdcpll` check |
| microSD errors only with the new pads | Revert 0613 and keep 0612 |
| exFAT mount fails | Record the error; driver and mount only |

### T5 result (2026-11-06)

Custodian run on station-work-66:

- boot2 `c4093121…`, package `469cd863…` (`f0fe8d1a`), composed DTB `e7192694…`.
- The RAM root `38ac31fa…` has init's `linux` mount changed to `blockdev --setro`
  plus `ro,noload`. The custodian checked that this is the only data mount in it.
- Boot `40201d1f` throughout, taint 0.
- The owner approved the eMMC risk ("Yes, run T5") and the write ("Swapped, write
  OK").

Raw output is private.

1. **Boot.**
   - `data=mounted` from `mmcblk0p29`, with `/mnt/data` "ext4 ro,relatime,norecovery"
     and the partition's `ro` at 1. `display=skipped-no-data`, as expected.
   - "mmc0: new HS200 MMC card", with its boot partitions and RPMB present. `ios`:
     191999939 Hz, 8 bits, HS200 timing, 1.80 V.
   - "mmc1: new UHS-I speed SDR104 SDXC card". `ios`: 191999939 Hz, 4 bits, SDR104,
     1.80 V.
   - Clocks as before: `msdcpll` at 384 MHz, `msdc50_0_sel` on it, `msdc30_1_sel` on
     `msdcpll_d2`.
   - Pinconf in the UHS state read back as set: pins 129-133 pull-up 101, 8 mA, input
     enabled, TDSEL `0xc`, RDSEL 0; pin 134 pull-down 102, 10 mA, TDSEL `0xc`, RDSEL 0.
   - No error line.
2. **eMMC**, the `linux` partition read-only, found by GPT name.
   - The first 1 GiB, read twice after dropping caches, gave the same hash in 37.54 s
     and 35.67 s, including the CPU's hashing.
   - A raw 256 MiB read took 7.41 s, about 36 MB/s. That's above the 24 MB/s a
     legacy-timing bus could carry, but well below the predicted four times.
3. **SDXC card at SDR104.**
   - Two 1 GiB hashes agreed, limited by the hashing.
   - 256 MiB raw reads at 0, 4096 MiB and 12000 MiB took 3.08, 2.98 and 2.98 s:
     83-86 MiB/s, about twice SDR50.
4. **Write**, 16 GB vfat card.
   - 64 MiB plus `sync` took 9.29 s, which is card-bound as before.
   - The readback after a cache drop took 1.99 s and matched.
   - Deleted; no error, warning or FAT line.
5. **Swap.** Pulling the SDXC card logged two CMD13 timeouts and its removal, the
   usual pattern. The 16 GB card came back at SDR104, 192 MHz, 1.80 V.
6. **exFAT.** `exfat.ko` loaded; a read-only mount of the SDXC card's partition
   worked (empty, 1.4 TiB); unmounted cleanly.
7. **End.** Taint 0, no `mmc0` error at any point.

**Conclusion.** All the changes worked on one boot of one unit:

- the eMMC runs HS200 at 192 MHz;
- the microSD slot runs SDR104 at 192 MHz with the vendor's pad settings, reading at
  about 86 MiB/s;
- exFAT mounts.

Whether `disable-wp` removed the "assuming write-enable" line wasn't checked
explicitly; that line isn't counted as an error.

**Missed: the eMMC hypothesis.** Its rate rose only to about 36 MB/s, not four times
legacy. The custodian reads that as limited by the eMMC; that is an inference, not
shown. Candidates to check: request size and the software queue on `mmc0`, a cold
read of an unused region, and the device's own sequential rate under Gemian. HS200
stays, since it is correct and faster; its throughput is an open question.

### T6: why eMMC HS200 reads stop at about 36 MB/s (2026-11-06)

**What the source rules out.** Read from Linux 7.1.3 `mtk-sd.c` and the station DT;
not measured.

- Both hosts use the same MT6797 compatible data and the same request limits: 1024
  segments of up to 64 KiB, 512 KiB per request.
- Both have `no-sdio`, so both run the MMC host software queue; neither has CQE.
- The clock is right: HS200 at 192 MHz takes `msdc_set_mclk`'s no-divisor path from
  the 384 MHz `msdc50_0_sel`, and `ios` reported 191999939 Hz.
- The eMMC pads are at 4 mA, the vendor's eMMC drive selector too.
- T5 measured both buses the same way (buffered `dd`, 1 MiB blocks, so 128 KiB
  readahead requests): the microSD reached 83-86 MiB/s, the eMMC 36 MB/s.

So the gap is in the eMMC's link or the chip, not in a host limit. Three causes stay
open, each with its own sign:

| Cause | Sign |
| --- | --- |
| Data CRC errors and silent retuning at 192 MHz. `mtk-sd` logs data errors only at debug level, and the core counts only failed tunings | Far more `mmc0` interrupts per MiB than `mmc1`'s |
| The chip's per-command latency, paid on each 128 KiB readahead request | Large direct reads much faster than buffered ones |
| The chip's own sequential rate | Direct 4 MiB reads still about 36 MB/s, with interrupts per MiB like `mmc1`'s |

**Hypothesis.** Interrupts per MiB are similar on both hosts, and direct 4 MiB reads
are much faster than buffered ones: the limit is request size, not errors.

**Procedure.** On the running station, if its image has 0615 (`mmc0` at HS200);
no boot is needed for this. Read-only throughout; nothing is written to the eMMC
or a card, and no setting is changed. Raw output stays private.

1. Boot ID, boot2 hash, taint, `cat /sys/kernel/debug/mmc0/ios` and
   `/sys/kernel/debug/mmc0/err_stats`.
2. For `mmcblk0` and, if a card is in, `mmcblk1`: `read_ahead_kb`,
   `max_sectors_kb`, `max_hw_sectors_kb`, `nr_requests` and `scheduler` from
   `/sys/block/<dev>/queue/`.
3. Find the `linux` partition by GPT name, as `init` does. For each read below, drop
   caches, note the `mmc0` line of `/proc/interrupts`, run the read under `time`,
   then note the line again:
   - buffered: `dd if=<it> of=/dev/null bs=1M count=256`, as in T5;
   - direct: `dd if=<it> of=/dev/null bs=4M count=64 iflag=direct`;
   - direct: `dd if=<it> of=/dev/null bs=512K count=512 iflag=direct`;
   - buffered from 8 GiB in: `bs=1M skip=8192 count=256`, a region the T5 reads
     didn't touch, if the partition is that large.

   If `dd` doesn't support `iflag=direct`, skip those two and say so.
4. If a card is in, the buffered and the 4 MiB direct read of its whole device, with
   the `mmc1` interrupt line around each.
5. `err_stats` again, `dmesg` lines for `mmc`/`msdc` since step 1, taint.

Stop on any `mmc0` error, warning or Oops.

| Result | Decision |
| --- | --- |
| `mmc0` interrupts per MiB many times `mmc1`'s, or `err_stats` grows | Errors and retuning: look at the eMMC's tuning and pad timing, and consider HS at 52 MHz until fixed |
| Direct 4 MiB much faster than buffered | Request-size bound: the eMMC is fine, and `read_ahead_kb` is the lever |
| Direct 4 MiB also about 36 MB/s, interrupts normal | The chip or HS200 itself: compare with the vendor kernel's rate under Gemian before any change |
| The cold region much faster or slower | The chip's internal state; note it, no driver change |

### T6 result (2026-11-06)

Boot `4e6851f2`, image station-work-68 from `84a70e42`, which includes 0615. Taint 0
before and after. Read-only; nothing was written. Raw output is private. The
custodian stopped early once the first branch's sign was clear.

**Observed.**

- `mmc0`: HS200, 191999939 Hz, 8 bits, 1.8 V. `err_stats` stayed all 0 throughout.
  `mmc1`: SDR104 at the same rate.
- Both block queues: `read_ahead_kb` 128, `max_sectors_kb` 512, `nr_requests` 128,
  `mq-deadline`. The `linux` partition is `mmcblk0p29`, 58903 MiB.
- `mmc0` interrupts per MiB, first run:

  | Read | Interrupts per MiB |
  | --- | --- |
  | buffered, 1 MiB × 256 from 0 | about 4 |
  | direct, 4 MiB × 64 | about 12 |
  | direct, 512 KiB × 512 | about 1830 |
  | buffered, 1 MiB × 256 from 8 GiB | about 3830 |

- A second run, timed from `/proc/uptime` because busybox `dd` prints no timing:
  - the buffered read from 0 took 86.7 s, about 3 MB/s;
  - the 4 MiB direct read took 80.1 s.

  It was stopped during the 512 KiB read.
- 8 MiB buffered reads after a cache drop, counted from `/sys/block/mmcblk0/stat`:
  - From offset 0: 22 requests, 100 ms.
  - From 300 MiB, 8192 MiB, 8500 MiB and 20000 MiB: 17 requests and 17408 sectors
    each, 3.7-7.4 s each, with exactly 34816 interrupts, two per sector.
  - An earlier 4 MiB read at 20000 MiB took 49 ms.
- No `mmc` or `msdc` line in `dmesg`, no warning, no Oops.
- The card's interrupt line was mis-selected, so there are no `mmc1` counts.

**Inferred.**

- Two interrupts per sector, with the request count unchanged, is the block
  driver's recovery path. In 7.1.3, `mmc_blk_mq_complete_rq` requeues a request
  that moved no data with `MQRQ_XFER_SINGLE_BLOCK`. The rest of that request is then
  read one sector per command, each a command interrupt and a transfer interrupt.
  In the slow reads, every request took that path.
- The trigger is a failed multi-block read. `mtk-sd` logs data errors only at debug
  level, and the core's `err_stats` counts only failed tunings, which is why
  nothing showed.
- A data CRC error (`-EILSEQ`) also marks the host for retuning. Whether these were
  CRC errors or timeouts isn't shown.
- The failures come and go: the same read was fast in one run and slow in the next.
  Once they began, every read in the second run was slow.
- So T5's 36 MB/s was a mix of normal and single-sector reads, not the chip's rate.
  The fast reads (8 MiB in 100 ms) suggest the chip itself is well above it.

**Outcome.** The first row of the decision table: HS200 on this tree has data
errors at 192 MHz. The data is protected by the CRC and the retry, so nothing read
wrong. But the link is unreliable, and degraded reads are around 3 MB/s. Writes take
the same recovery path. The station's data partition is mounted read-write on
these images.

**Not shown.**

- Whether the errors are CRC errors or timeouts.
- Whether a fresh tuning holds until some later event.
- Whether the pad timing, the tuning window or something else is the cause.

Next, by the table: the eMMC's HS200 tuning and pad timing, with HS at 52 MHz as the
safe setting meanwhile.

### What the vendor tunes that mainline doesn't (2026-11-06)

Sources: the vendor's eMMC tuning in the public Gemian kernel
([`autok.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/mmc/host/mediatek/mt6797/autok.c),
`execute_online_tuning_hs200`, `autok_path_sel`, `autok_init_hs200`); its tuning
output in a retained Gemian boot log of this unit; Linux 7.1.3 `mtk-sd.c`. The log
itself stays private; the values below are read from it.

**Observed in the Gemian log.** HS200 at 200 MHz from a 400 MHz source, tuned over
64 pad delay cells. One clock cycle is 49 cells.

| Path | Pass map | Chosen |
| --- | --- | --- |
| CMD, rising edge | fails at 9-11 and 58-61 | |
| CMD, falling edge | fails at 34-36 | falling edge, delay 10 |
| Read data, rising edge only | fails at 14-20 and 61-63, passes 21-60 | delay 39-40 (31 in the first field, 8 in the second) |

The vendor also tunes the data latch clock (`INT_DAT_LATCH_CK`), which ended at 3
after a logged latch-tuning error. Its HS400 tuning that follows chose 0.

**How mainline differs** (from the source):

| Setting | Vendor HS200 | Mainline, MT6797 data |
| --- | --- | --- |
| Delay cells scanned | 64 | 32 for an eMMC (`mediatek,tuning-step` default), 64 when the host has `no-mmc`, as the microSD does |
| CMD and DATA | Tuned apart, CMD on both edges, data on the rising edge | One shared value (`msdc_tune_together`, as `data_tune` and `async_fifo` are set) |
| Data latch clock | Tuned, from 1 | `mediatek,latch-ck`, 0 by default |
| `CKGEN_MSDC_DLY_SEL` | 0 | 1 |
| CMD response and write CRC turnaround | 0 and 0 | 1 and 1 |
| `RESPSTSENSEL`, `CRCSTSENSEL` | 3 and 3 | 2 and 2 |

The MT6797 `PAD_TUNE1` register at `0xf4` has the second delay fields at the bits
`mtk-sd` uses past 32 cells, the same layout as the vendor's `msdc_reg.h`.

**Inferred.** Running `mtk-sd`'s `msdc_tune_together` and `get_best_delay` over the
vendor's rising-edge maps:

- With 32 cells, the widest rising window that passes both paths is 21-31, 11 long.
  That is under the 12 needed to skip the falling edge. If the rising edge wins, the
  shared delay is 26, six cells (about 0.6 ns) above the failing zone at 14-20. The
  falling-edge data map isn't known, since the vendor never scans it.
- With 64 cells, the window is 21-57, 37 long. The falling edge is skipped and the
  shared delay is 39, where the vendor puts its data delay, with 19 and 22 cells of
  margin. CMD at 39 on the rising edge is inside its 12-57 pass range.

Of the differences, the 32-cell scan is the one that explains a marginal data delay
on its own. The fixed path settings in the table are what `mtk-sd` uses for every
async-FIFO SoC, and the microSD host passes SDR104 with them. They stay as they are
unless the scan change isn't enough. The pass maps come from one Gemian boot and
shift between boots; that's why the margin matters.

**Change.**
[0625](../../patches/proposals/0625-arm64-dts-mediatek-gemini-station-scan-all-eMMC-HS20.patch)
sets `mediatek,tuning-step = <64>` on the station's `mmc0`. It's DT only, so it needs
an image.

**T6b result.** Boot `4e6851f2`, station-work-68, taint 0. Read-only. MSDC0
autosuspends when idle, so the custodian kept it active with a direct 32 MiB read of
`mmcblk0p29`. The registers were read only while `runtime_status` read `active`. Raw
output is private.

| Register | Value | Decoded with the `mtk-sd` layout |
| --- | --- | --- |
| `IOCON` (`0x04`) | `0x00000000` | CMD and data both sampled on the rising edge |
| `PATCH_BIT0` (`0xb0`) | `0x403c0446` | data latch clock 0, `CKGEN_MSDC_DLY_SEL` 1 |
| `PATCH_BIT1` (`0xb4`) | `0xfffe4089` | |
| `PATCH_BIT2` (`0xb8`) | `0x548a180d` | `RESPSTSENSEL` 2, `CRCSTSENSEL` 2 |
| `PAD_TUNE0` (`0xf0`) | `0x00313100` | data delay 17, CMD delay 17, both select bits set |
| `PAD_TUNE1` (`0xf4`) | `0x00002000` | second delay fields 0; the data second-field select bit is set, left from before |

So the 32-cell scan put the shared delay at 17 on the rising edge. That is inside
the zone where the vendor's data map fails (14-20). The vendor's map comes from
another kernel, at 200 MHz rather than 192 MHz, and with a different CKGEN delay,
so this kernel's map is shifted to some extent; 17 passed this kernel's own tuning.
Still, it stays within a few cells of failing reads, which fits T6's data errors
that come and go. The fixed path settings read back as mainline's init writes them.

### T7: HS200 with a 64-cell scan

**Hypothesis.**

- The eMMC tunes HS200 with a shared delay above 31, using the second field in
  `PAD_TUNE1`. The vendor's maps put it near 39; this kernel's map is shifted, so the
  exact value isn't predicted.
- Every eMMC read runs at about 4 interrupts per MiB, with none of T6's two per
  sector.
- Reads run well above 36 MB/s.
- The microSD is unchanged.

Image: `mt6797-a53-station-a72` with `BUILD_MODULES=1`, from the commit adding this
section or later. One boot. Read-only on the eMMC, as T6.

1. **Boot.**
   - Boot ID, boot2 hash, taint.
   - `mmc0` and `mmc1` `ios`.
   - The six registers from T6b, read while MSDC0 is active, as in T6b.
   - `dmesg` lines for `mmc` and `msdc`.
2. **Reads**, on the `linux` partition found by GPT name, each after a cache drop.
   For each, the read count and sectors from `/sys/block/mmcblk0/stat`, the `mmc0`
   interrupt count before and after, and the time from `/proc/uptime`:
   - 8 MiB buffered at 0, 300, 8192, 8500 and 20000 MiB, the T6 offsets;
   - 1 MiB × 256 buffered from 0;
   - 1 MiB × 1024 buffered from 8 GiB;
   - 4 MiB × 64 direct.
3. Repeat step 2's 8 MiB reads once, to catch a fault that comes and goes.
4. The six registers again, `err_stats`, `dmesg` lines, taint.

Stop on any `mmc0` error, warning or Oops. No write, no retry.

| Result | Decision |
| --- | --- |
| No reads at two interrupts per sector, rate well above 36 MB/s | 0625 fixes it. Record the rate; HS200 counts as working again |
| Still some fallback, but less | The scan helped. Next is the data latch clock (`mediatek,latch-ck`) or separate CMD and DATA delays, one at a time |
| No change in the fallback | The scan isn't the cause. Compare the fixed path settings in the table with the vendor's values |
| Tuning fails, or the eMMC is absent | Stop, recover via Gemian, revert 0625 |

### T7 result (2026-11-06)

Boot `0e752eb2`, image station-work-69 from package `bad37017` (`1a13a00b`), boot2
`a6acfc06…`, written by `flash-boot2` with a verified readback. The composed station
DTB differs from station-work-68's only by `mediatek,tuning-step = <0x40>` on `mmc0`.
`data` was read-only at the block layer; nothing was written. Taint 0 throughout.
Raw output is private.

**Observed.**

- `mmc0`: "new HS200 MMC card", 191999939 Hz, 8 bits, 1.8 V, no tuning error.
  `err_stats` all 0, and no `mmc0` or `msdc` error, warning or Oops at any point.
- Registers, read while MSDC0 was active:
  - `IOCON`, `PATCH_BIT0`-`2` are unchanged from T6b.
  - `PAD_TUNE0` is `0x00323200`: data and CMD delays 18, select bits set.
  - `PAD_TUNE1` is `0x00202000`: second delay fields 0, both second-field select
    bits set, as `mtk-sd` sets them for a 64-cell scan.
- Reads:

  | Read | Pass 1 | Pass 2 |
  | --- | --- | --- |
  | 8 MiB at 0 | 42 interrupts | 42 |
  | 8 MiB at 300 MiB | 2213 interrupts, 0.42 s | 2212, 0.42 s |
  | 8 MiB at 8192 MiB | 34 | 34 |
  | 8 MiB at 8500 MiB | 107 | 4126, 0.40 s |
  | 8 MiB at 20000 MiB | 214 | 34 |
  | 1 MiB × 256 from 0 | 1.74 s, about 147 MB/s | |
  | 1 MiB × 1024 from 8 GiB | 6.09 s, about 172 MB/s | |
  | 4 MiB × 64 direct | 1.69 s, about 155 MB/s | |

- The custodian also ran a 512 KiB × 2048 direct read from 4000 MiB, to keep MSDC0
  active for the register reads. It ran almost entirely at two interrupts per sector,
  about 1.1 MiB/s, and was stopped after about 150 s.

**Inferred.**

- 0625 moved the tuning, and healthy reads now run at 150-170 MB/s, two interrupts
  per request. T5's 36 MB/s was mostly fallback.
- The fallback isn't gone:
  - At 300 MiB it repeats with the same interrupt count, so it follows the data
    there rather than chance.
  - At 8500 MiB it comes and goes.
  - From 4000 MiB it holds over a long stretch.
- The scan picked 18, not a delay above 31 as predicted. In `get_best_delay`, a
  window starting at cell 0 is set at a third of its length, not its middle, so 18
  fits a window from 0 to about 54. That's longer than one clock cycle (about 51
  cells at 192 MHz, scaling the vendor's 49 at 200 MHz), which the 128-byte tuning
  block may allow while real data doesn't. This kernel's map isn't known: `mtk-sd`
  prints it only at debug level, and the station kernel has neither dynamic debug
  nor tracing.
- That leaves the decision table's second row, "the scan helped". Its next steps,
  the data latch clock and separate CMD and DATA delays, would each still be a
  guess without the map.

**Next.** A diagnostic boot that prints, at info level, `mtk-sd`'s pass maps and
chosen delay at each tuning and retune, and each data error's kind. It changes no
behaviour. Then choose between centring the data delay, the latch clock and
separate CMD/DATA tuning from the map, not by trial.

### T8: the eMMC tuning map and error kinds (diagnostic)

**Change.**
0626 (removed after T9; in history at `74afd852`),
for diagnosis only. It turns `mtk-sd`'s existing debug lines into info lines:
- each scan's pass map, longest window and chosen phase;
- the final shared delay and its edge.

It also adds a rate-limited line for each command or data error outside tuning:
the interrupt events, the opcode, argument and block count, and the pad-tune and
`IOCON` registers. Behaviour is unchanged. It's built in, as `mtk-sd` carries the
eMMC, so it needs an image.

**Hypothesis.** Unknown map, so this predicts what each outcome will show:

- The boot prints `mmc0`'s rising-edge map. A falling-edge map appears only if the
  rising window is under 12 cells.
- Every fallback starts with a data error line, `cmd` 18, `blocks` above 1.
  `events` tells a CRC error (`MSDC_INT_DATCRCERR`, bit 15) from a timeout
  (`MSDC_INT_DATTMO`, bit 14).
- Each CRC error is followed by a retune, which prints a fresh map.

Image: `mt6797-a53-station-a72` with `BUILD_MODULES=1`, from the commit adding this
section or later. One boot, `data` read-only as in T7. Nothing is written.

1. **Boot.**
   - Boot ID, boot2 hash, taint.
   - `ios` for both hosts.
   - Every `dmesg` line from `11230000.mmc` and `11240000.mmc`.
2. **Reads**, on `mmcblk0p29` by GPT name, each after a cache drop. For each: the
   `stat` reads and sectors, the `mmc0` interrupt delta, the time, and the new
   `11230000.mmc` lines.
   - 8 MiB buffered at 0, 300, 8192, 8500 and 20000 MiB, twice, as in T7.
   - 64 MiB direct from 4000 MiB in 512 KiB blocks, stopped after 60 s if it falls
     back.
3. **End.** All `11230000.mmc` lines since boot, how many lines rate-limiting
   suppressed if `dmesg` shows it, `err_stats`, taint.

Stop on a warning or Oops. No write, no retry.

| Result | Decision |
| --- | --- |
| Data CRC errors, a map whose window starts at 0 and runs past one cycle | The tuning block passes delays real data fails. Centre on the real eye: set the data delay apart from CMD, or limit the scan to one cycle |
| Data CRC errors, a clean single window | The delay is centred but the eye is too narrow. Next: the data latch clock, then the fixed path settings |
| Data timeouts, not CRC | Not a sampling problem. Look at the latch clock and the turnaround settings |
| Command or stop errors, not data | Tune CMD apart from data |

### T8 result (2026-11-06)

Boot `5a1721ee`, image station-work-70 from package `223574f5` (`74afd852`), boot2
`98a2fea1…` (verified readback). The DTB is T7's. `data` was read-only; nothing was
written. Taint 0, no warning or Oops, no rate-limited lines dropped. Raw output is
private.

**Observed.**

- Every fallback started with one data error with events `0xa040`: data CRC error
  (bit 15), transfer done (bit 13), DMA queue empty (bit 6). All were `cmd 18` with
  1024 blocks. There were no timeouts and no command errors; 33 data errors in all.
- At 300 MiB, both passes failed on the same request, `arg 0x1e6400`.
- In a 512 KiB direct read from 4000 MiB, all 31 logged errors fell on consecutive
  requests. The read took 56 s for 64 MiB.
- Every error was followed by a retune, which landed on delay 15-19 again. Across
  the boot the chosen delays were 15 (8 times), 16 (13), 17 (8), 18 (3) and 19 (2),
  always on the rising edge; no falling-edge map was printed.
- The boot map, pass `O`, fail `X`, cell 0 on the left:

  ```text
  eMMC     XXOOOOOOOOOOOOOOOOOOOOOOOOOOOOXXOXXXOXXXXXOOOOOOOOOOOOOOOOOOOOOO
  microSD  OOOOOOOOOOOOOOOOOOOOOOOOOOOXXXOXXOOOOOOOOOOOOOOOOOOOOOOOOOOOOOXX
  ```

  All 36 eMMC maps have that shape, with a failing band at about 30-43 and scattered
  passing cells inside it. The longest window, 2-29, always wins.

**Inferred.**

- The fallback is data sampling, not commands or timeouts: CRC errors on real reads
  at delays the 128-byte tuning block passes. They follow the data, since the same
  request fails each time.
- The eMMC's failing band is about 14 cells wide, with islands. That is twice the
  microSD's (27-32, about 6 cells, same clock and the same delay cells) and twice the
  vendor kernel's eMMC band (14-20, 7 cells). The data edges themselves are spread
  more than they should be, so moving the delay within this eye has limited room.
- A concrete difference fits that. The July MSDC record
  ([recovery README](../2026-07-12-mt6797-msdc-recovery/README.md)) says patch 0071
  removed the eMMC's pad properties, since MT6797 pinctrl had no pad callbacks, and
  "leaves pad configuration to the boot firmware". The vendor kernel rewrites those
  pads at init (`sd.c` `msdc_init_hw`): Schmitt trigger on, TDSEL `0xcccc`, drive
  selector 1 (4 mA) on all four groups. Its RDSEL helper writes 0 for the eMMC
  (`msdc_io.c`), but `msdc_init_hw` doesn't call it. The microSD pads
  get the vendor's values since 0612/0613, and its band is narrow.

**Next.** T8b reads the eMMC pad registers on the running station: IOCFG_B IES `0x20`,
SR `0x30`, SMT `0x60`, RDSEL `0x80`, TDSEL `0xd0`, PUPD/R0/R1 `0x100`-`0x120`, and DRV
`0x1a0`. If they differ from the vendor's values, describe the MSDC0 pad fields in
pinctrl, as 0612 did for MSDC1, and set the vendor's values in the DT.

### T8b result: the eMMC pads (2026-11-06)

Read once on the T8 station, boot `5a1721ee`, taint 0. Read-only. Raw output is
private. Decoded with the vendor's MSDC0 field masks (`msdc_io.h`); pins 114-121 are
DAT0-7, 122 CMD, 123 CLK, 124 DSL and 125 RSTB.

| Field | Register value | MSDC0 field | Vendor |
| --- | --- | --- | --- |
| IES `0x420` | `0x7fff9fff` | bits 0-11 all set | all set |
| SR `0x430` | `0x00000000` | bits 15-18 clear | not set at init |
| SMT `0x460` | `0x0001ff8f` | bits 0-3 all set | all set |
| RDSEL `0x480` | `0x00000000` | 0 | 0 |
| TDSEL `0x4d0` | `0x33330000` | **bits 0-15: `0x0000`** | **`0xcccc`**, in `msdc_init_hw` |
| PUPD/R0/R1 `0x500`-`0x520` | | DAT and CMD pull-up R1R0 01; CLK and DSL pull-down 10; RSTB 10 | the same |
| DRV `0x5a0` | `0x14aa5249` | 1 in all four groups (4 mA) | 1 |

TDSEL is the one difference: 0 in all four groups (DAT0-3, DAT4-7, CMD/DSL/RSTB,
CLK) under mainline, where the vendor's `msdc_init_hw` writes `0xc` to each. The
microSD pads have TDSEL `0xc` since 0613, and their failing band is the narrow one.
One caveat: the vendor's register dump comment for MSDC0 TDSEL reads "should:
0x????0000", which disagrees with its own init code. What Gemian runs with isn't
measured. The top half, `0x3333`, belongs to other pins.

### T8c: the eMMC with the vendor's TDSEL (diagnostic write, no boot)

**Hypothesis.** With TDSEL `0xc` on the eMMC pads, the reads that fell back in T8
read cleanly:
- the 8 MiB read at 300 MiB, which fails on request `0x1e6400` every time;
- the 512 KiB direct reads from 4000 MiB, where every request failed.

**Effects.** Two writes to one GPIO pad register, `0x100024d0` (IOCFG_B TDSEL):
- one setting bits 0-15 to `0xcccc` and keeping bits 16-31 as read;
- one restoring the value read before.

Nothing else is written; no eMMC write; `data` stays read-only. If the setting makes
eMMC commands fail, the core may give up on the eMMC for this boot, as a failed
HS200 tuning would. Recovery is then a reboot, with nothing on the eMMC changed.
That is the exposure T5 had.

Steps, on the running T8 station (diagnostic kernel, `data` read-only):

1. Read `0x100024d0`; record it as the original. Stop if bits 0-15 aren't `0x0000`.
2. Baseline: 8 MiB buffered at 300 MiB after a cache drop, with the `mmc0`
   interrupt delta and the new `11230000.mmc` lines. Expect T8's fallback.
3. Write the original with bits 0-15 set to `0xcccc`; read back and check it.
4. The same 8 MiB read at 300 MiB, then 8 MiB at 0, and 32 MiB direct
   from 4000 MiB in 512 KiB blocks (stop after 30 s if it falls back). Each with the
   interrupt delta, time and new lines. Any retune prints a new map; note it.
5. Write the original back; read back and check it. Repeat the 300 MiB read.
6. `dmesg` lines since step 1, taint.

Stop at once and restore the original value on:
- any `cmd error` line;
- a data error that isn't a CRC error;
- `mmc0` reporting the card removed or a failed tuning;
- a warning or Oops.

No retries; two writes at most.

| Result | Decision |
| --- | --- |
| No fallback at 300 MiB and 4000 MiB with `0xcccc`, fallback back after the restore | TDSEL causes it. Describe MSDC0 TDSEL in pinctrl and set `mediatek,tdsel = <0xc>` on the eMMC pins in the station DT; then a boot to confirm |
| Fallback reduced | TDSEL helps. Patch it, then look at the remaining fixed path settings |
| No change | TDSEL isn't it. Next: `CKGEN_MSDC_DLY_SEL` and the latch settings |
| Command errors or tuning failure | Restore, stop. TDSEL `0xc` is wrong for this pad; don't patch it |

### T8c result (2026-11-06)

Run on boot `5a1721ee` (T8, `data` read-only) after the owner approved the two writes
("Yes, run T8c"). Taint 0. No command error, non-CRC data error, tuning failure,
warning or Oops. `0x100024d0` ends at its original `0x33330000`. Raw output is private.

| Step | TDSEL | Read | `mmc0` interrupts | Time | `11230000.mmc` lines |
| --- | --- | --- | --- | --- | --- |
| Baseline | 0 | 8 MiB at 300 MiB | 2213 | 0.43 s | the usual CRC error at `0x1e6400`; retune to 18 |
| Changed | `0xc` | 8 MiB at 300 MiB | 34816, two per sector throughout | 3.51 s | none |
| Changed | `0xc` | 8 MiB at 0 | 34313 | 3.60 s | none |
| Changed | `0xc` | 512 KiB × 64 direct from 4000 MiB | 131072, two per sector | 28.67 s | none |
| Restored | 0 | 8 MiB at 300 MiB | 4259 | 0.84 s | the same CRC error at `0x1e6400`; retune to 17 |

**Outcome.**
- TDSEL `0xc` made every eMMC read fall back, including the read at 0 that is clean
  at TDSEL 0.
- Restoring 0 brought back T8's behaviour.
- TDSEL isn't the fix; the decision table's "no change" row, or worse. That fits the
  vendor's dump comment for this register ("0x????0000") better than its init code.

Not explained: the reads at `0xc` fell back without a single error or retune line,
though 0626 logs every data and command error outside tuning. Either the failure
took a path 0626 doesn't log, or something else sent the requests as single blocks.
Not pursued, as `0xc` is ruled out either way.

### T8d: the eMMC with the vendor's data latch clock (diagnostic write, no boot)

The next difference in the vendor comparison is the data latch clock,
`INT_DAT_LATCH_CK_SEL` in MSDC0 `PATCH_BIT0` bits 9:7. The vendor tunes it for eMMC
HS200 and ended at 3; mainline uses `mediatek,latch-ck`, 0 by default (T6b-T8:
`PATCH_BIT0` `0x403c0446`, field 0).

`mtk-sd` writes this field only when it tunes, which happens only after a data CRC
error. Runtime suspend saves and restores `PATCH_BIT0` whole. So a value written
while MSDC0 is active stays until the next CRC error, whose retune puts back 0 and
prints a map. The test is clean up to the first retune line.

**Hypothesis.** With the latch clock at 3, the read at 300 MiB that fails on request
`0x1e6400` every time reads cleanly, and so do the 512 KiB direct reads from
4000 MiB, with no retune.

**Effects.** Two writes to MSDC0 `PATCH_BIT0` (`0x112300b0`), each made while
MSDC0 is runtime-active (a read-only direct `dd` running, as in T6b):
- one setting bits 9:7 to 3 and keeping the other bits as read;
- one restoring the value read before, unless a retune has already put back 0.

No eMMC write; `data` stays read-only. A bad latch value gives CRC errors, which
the driver's retune undoes on its own. The exposure is the same as T8c.

1. Keep MSDC0 active; read `0x112300b0`. Stop if bits 9:7 aren't 0.
2. Baseline: 8 MiB at 300 MiB, expecting T8's error.
3. Keep MSDC0 active; write the original with bits 9:7 set to 3. Read back and
   check, then confirm `runtime_status` stayed `active` across the write.
4. 8 MiB at 300 MiB, 8 MiB at 0, and 512 KiB × 64 direct from 4000 MiB (stop after
   30 s if it falls back). For each: the interrupt delta, the time, and the new
   lines. Read `0x112300b0` after each to see whether a retune put back 0.
5. If bits 9:7 are still 3, write the original back and check it. Repeat the 300 MiB
   read.
6. `dmesg` lines since step 1, taint.

Stop on the same conditions as T8c: any command error, a non-CRC data error, the
card removed, a tuning failure, a warning or Oops. Two writes at most; no retries.

| Result | Decision |
| --- | --- |
| No fallback with 3, and the field stays 3 | The latch clock causes it. Set `mediatek,latch-ck = <3>` on the station's `mmc0` (DT only); confirm on a boot |
| A fallback with 3, then a retune back to 0 | 3 doesn't hold. Look at `CKGEN_MSDC_DLY_SEL`, which needs a patch and a boot, as it shifts the tuned delays |
| Worse, as T8c | Not the latch clock. Same next step |

### T8d result (2026-11-06)

Run on boot `5a1721ee` (T8, `data` read-only) after the owner approved the writes
("Yes, run T8d"). Taint 0. No command error, non-CRC error, tuning failure, warning
or Oops. Raw output is private.

- `PAD_TUNE0` at the baseline error was `0x313100`; retuned to 18.
- One write, `0x403c05c6` (latch clock 3), made while MSDC0 was active. The very next
  request hit a data CRC error. It was `arg 0x1150400`, in a region that read cleanly
  at latch 0 in T7 and T8.
- The retune that followed (to delay 16) put `PATCH_BIT0` back to `0x403c0446`
  before the readback. So no restore write was needed, and the steps after it didn't
  run.

**Outcome.** The table's "a fallback with 3, then a retune back to 0" row: the
vendor's latch value fails at once with mainline's tuned delay. That rests on one
error on one request.

### What the vendor actually runs: HS400, not HS200

**Observed in the retained Gemian logs.** The vendor kernel tunes HS200 for 37-41 ms
on the way to HS400, then runs the eMMC at HS400. In every retained Gemian log of
this unit (25 files from nine boots):
- the HS400 tuning set the data-strobe delay to `DLY1` 7 or 8, `DLY2` 0, `DLY3` 20;
- the read data delay was 1, with latch clock 0.

No vendor read of real data ever runs at HS200.

**Inferred.**

- Nothing in the vendor kernel shows that HS200 reads are reliable on this board.
  The comparison in T6-T8d asked mainline's HS200 to do what the vendor never relies
  on.
- At HS400 the card sends a data strobe with the data, and the host samples on that.
  The host's read delay, which T6-T8 show is marginal at HS200, no longer decides
  the sampling.
- The follow-up "eMMC HS400, once its data-strobe delay is known" now has its value.
  `mtk-sd` writes `hs400-ds-delay` as-is to `PAD_DS_TUNE` (`DLY_SEL` bit 0, `DLY1`
  bits 6:2, `DLY3` bits 16:12) on an SoC without its own HS400 tuning, as MT6797's
  data is. The vendor's `DLY1` 7 and `DLY3` 20 with `DLY_SEL` give `0x1401d`.
  Upstream MT8173 boards use `0x14015`, with the same `DLY3`.

Not shown: whether mainline's HS200 tuning, which only needs to pass the tuning
block, is enough to switch to HS400; and whether the vendor's 400 MHz HS400 source
matters, where mainline's is 384 MHz.

### T9: the eMMC at HS400

The owner chose HS400 over stepping down to HS (52 MHz).

**Change.**
[0627](../../patches/proposals/0627-arm64-dts-mediatek-gemini-station-run-the-eMMC-at-HS.patch)
adds `mmc-hs400-1_8v` and `hs400-ds-delay = <0x1401d>` to the station's `mmc0`. It
keeps 0625's 64-cell HS200 scan and corrects its comment.

What `mtk-sd` does with them (source, not run):
- The MMC core tunes HS200 as now, then switches the card to HS400.
- `msdc_prepare_hs400_tuning` writes `0x1401d` to `PAD_DS_TUNE`.
- `msdc_execute_hs400_tuning` rescans the strobe `DLY1` over 32 cells, reading
  EXT_CSD at each, and logs "Final PAD_DS_TUNE". The vendor's own scan passed 1-15,
  which this centring rule puts at 8.
- The clock is the 384 MHz source divided by 2: 192 MHz, both edges.

The image also carries 0626, so tuning maps and errors still print.

**Risk.** As T5: if the switch or the strobe tuning fails, the core gives up on the
eMMC for that boot. Recovery is via Gemian, with nothing on the eMMC changed. `data`
stays read-only for this boot. No write is planned.

**Hypothesis.**

- `mmc0` comes up as "new HS400 MMC card" at 192 MHz with "Final PAD_DS_TUNE" `DLY1`
  near 7-8 and `DLY3` 20.
- T8's reads all run clean: the 8 MiB read at 300 MiB, which failed on request
  `0x1e6400` in every earlier boot, and the 512 KiB direct reads from 4000 MiB.
  That means no data error lines and about two interrupts per request.
- Reads run faster than HS200's 150-170 MB/s.

Image: `mt6797-a53-station-a72` with `BUILD_MODULES=1`, from the commit adding this
section or later. One boot.

1. **Boot.**
   - Boot ID, boot2 hash, taint.
   - `ios` for both hosts.
   - Every `11230000.mmc` line.
   - MSDC0 `PAD_TUNE0`, `PAD_TUNE1`, `PAD_DS_TUNE` (`0x11230188`), `IOCON` and
     `PATCH_BIT0`, read while active.
2. **Reads** on `mmcblk0p29`, each after a cache drop, with the `stat` requests and
   sectors, the `mmc0` interrupt delta, the time and any new lines:
   - 8 MiB at 0, 300, 8192, 8500 and 20000 MiB, twice;
   - 1 MiB × 1024 buffered from 8 GiB;
   - 4 MiB × 64 direct;
   - 512 KiB × 256 direct from 4000 MiB.
3. **End.** All `11230000.mmc` lines, taint.

Stop on a warning or Oops, the eMMC absent or not at HS400, or a command error. No
write, no retry.

| Result | Decision |
| --- | --- |
| HS400, no data errors, faster than HS200 | HS400 works. Drop the diagnostic 0626 from the series, record the rate, and update the support row |
| HS400, but data errors remain | Look at the strobe delay (`DLY1` window in the log) and `DLY3` before anything else |
| Falls back to HS200 or fails to switch | Record the error. HS at 52 MHz is the safe setting meanwhile |
| eMMC absent | Stop, recover via Gemian, revert 0627 |

### T9 result (2026-11-06)

Boot `8cd1ffdc`, image station-work-71 from package `31eebf4e` (`9a35e96f`). `data`
was read-only; nothing was written. Taint 0, no warning or Oops, `err_stats` all
zero, no rate-limited lines dropped. Raw output is private.

**Observed.**

- `mmc0`: 200 MHz requested (191999939 Hz actual), 8-bit, timing 10 (MMC HS400),
  1.80 V, "new HS400 MMC card". `mmc1` stayed at SDR104.
- HS200 tuning: map `fffff003fffffffc` (pass cells 2-31 and 44-63), longest window
  32, final delay 18, rising edge.
- Strobe tuning: map `0000000000001fff` in the log's bit order, maxlen 13, final 4.
  Final `PAD_DS_TUNE` `0x14011`: `DLY1` 4, `DLY3` 20, against the DT's `0x1401d`
  (`DLY1` 7).
- During the strobe scan, 10 data CRC lines on `cmd 8` (EXT_CSD), 1 block, events
  `0xa040` once and `0x8040` nine times. These are the scan's failing cells, which the
  diagnostic logs because CMD8 is not a tuning opcode. They are the boot's only 15
  `11230000.mmc` lines with the maps and finals.
- Registers, read while active, the same before and after the reads: `PAD_TUNE0`
  `0x00322000`, `PAD_TUNE1` `0x00202000`, `PAD_DS_TUNE` `0x00014011`, `IOCON` `0x0`,
  `PATCH_BIT0` `0x403c0446`.
- Reads, with no data error and two interrupts per request throughout:

  | Read | Requests | IRQs | Time | Rate |
  | --- | --- | --- | --- | --- |
  | 8 MiB at 0 MiB, each pass | 21 | 42 | about 0.045 s | about 190 MB/s |
  | 8 MiB at 300, 8192, 8500, 20000 MiB, each pass | 17 | 34 | about 0.045 s | about 190 MB/s |
  | 1 MiB × 1024 buffered from 8 GiB | 2049 | 4098 | 4.10 s | about 262 MB/s |
  | 4 MiB × 64 direct | 512 | 1024 | 1.36 s | about 197 MB/s |
  | 512 KiB × 256 direct from 4000 MiB | 256 | 512 | 1.07 s | about 251 MB/s |

  The 8 MiB read at 300 MiB, which failed on request `0x1e6400` in every earlier
  boot, and the reads from 4000 MiB, which took 56 s for 64 MiB in T8, ran clean.

**Inferred.**

- HS400 works on this eMMC with mainline's strobe tuning, and the read errors were an
  HS200 sampling problem that HS400's data strobe avoids, as the vendor kernel does.
- The strobe window passes 13 cells from 0, so the centring rule picks 4, not the
  predicted 7-8. The vendor's scan passed 1-15. Both windows are wide; the
  difference may be the 384 MHz source against the vendor's 400 MHz, not shown.
- The DT's `DLY1` 7 is only the starting value; `mtk-sd` replaces it with its own
  scan, so the value that matters on this board is `DLY3` 20.

**Decision.** HS400 works. The diagnostic 0626 leaves the series; 0625 and 0627
stay. Not shown: write rates, suspend, and HS400 over many boots and temperatures.

### The card as the running root (2026-11-10, unattended)

Boot `58bcf387`, image station-work-98 (`47b11c27`). The root filesystem is ext4 on
`mmcblk1p1`, on an SDXC card written with a 4 GiB image, used for normal desktop work
including a browser. This is not a predeclared test. The raw `dmesg` is private.

**Observed.**

- `mmc1` came up at SDR104, 191999939 Hz, 4-bit, 1.8 V. `mmc0` came up at HS400.
- In 1258 s there were 6 `mtk-sd` lines, all between 631.5061 and 631.5065 s:
  `msdc_track_cmd_data: cmd=12 arg=00000000; host->error=0x00000002`. That is a
  command timeout on a stand-alone CMD12.
- There were no I/O errors, no ext4 errors and no `blk_update_request` lines.
- `err_stats` for both hosts was all 0.

**Inferred.**

- Six CMD12s in a row are one `mmc_blk_send_stop`, which sends CMD12 with 5 retries.
  Block recovery (`mmc_blk_mq_rw_recovery`) sends it after a read or write fails,
  when the card is not ready for data.
- The card answered none of them, and the request then completed, since nothing
  reached the filesystem.
- The error that started recovery is not visible. `mtk-sd` logs transfer errors only
  at debug level, and this kernel has no dynamic debug. `err_stats` counts only
  failed tunings on this host (see the [T6 result](#t6-result-2026-11-06)). Its zero
  rules out a failed retune, nothing more.
- There are two readings. One is a data CRC error at SDR104, as the eMMC had at
  HS200. The other is a write error while the card was busy programming, where an SD
  card ignores CMD12. This boot does not tell them apart.

### The card hangs in screen-off idle (2026-11-12, -13)

Reported by the custodian, with the owner's request to investigate. Two boots of the
station image (the second is station-work-115, boot `e02c9413`, Image.gz
`abd51ea9`), with the card as root (ext4 on `mmcblk1p1`). This is the same physical
card as in [the card as root](#the-card-as-the-running-root-2026-11-10-unattended):
it has the same relative card address. Raw logs are private. This section is
analysis only; no device test has run.

**Observed.**

| | Fault 1 (11-12) | Fault 2 (11-13) |
| --- | --- | --- |
| Lid closed (screen blanked, no suspend) | 31085 s | 2741 s |
| First error | 37032.81 s | 9644.90 s |
| Screen-off time before the fault | 1.65 h | 1.92 h |
| Charger | 1.5 A, connected | 1.5 A, connected |
| Failing request | write | write |

- Neither boot logged "PM: suspend entry". No `mmc`, regulator or thermal line
  appears between the lid close and the fault.
- Both faults have the same `mtk-sd` sequence, all with `host->error=0x2`
  (`REQ_CMD_TMO`, a command with no response):
  1. 2 × CMD13 (SEND_STATUS) timeouts;
  2. 6 × CMD12 (STOP) timeouts;
  3. 4 × CMD13 timeouts; steps 1-3 take about 1.3 ms;
  4. about 2.1 s later, `mmc1: Card stuck being busy! __mmc_poll_for_busy`,
     `tried to HW reset card, got error -110`, `mmcblk1: recovery failed!`;
  5. write I/O errors, the ext4 journal aborts, and the filesystem goes
     read-only.
- Each later request repeats steps 1-3, now 0.7 ms apart, and fails at once.
- After fault 1 the lid was opened at 64785 s. A read at 64904 s failed the same
  way: the card was still unusable 7.7 h later.
- No CMD8, CMD55 or ACMD41 timeout line appears anywhere.
- Earlier, on 11-10 at 631 s and under desktop use, the same card had only step 2,
  and that request completed.

**What the source says** (Linux 7.1.3 `drivers/mmc`, as built):

- Steps 1-3 are `mmc_blk_mq_rw_recovery` after a failed request:
  - CMD13 is sent twice without retries;
  - then `mmc_blk_fix_state` sends CMD12 with 5 retries (`mmc_blk_send_stop`);
  - then it polls for busy with CMD13, which has 3 retries;
  - the poll's CMD13 error ends `fix_state`.

  The error that failed the request in the first place is logged only at debug
  level (see the 11-10 note above). So the trigger is not in these logs.
- Step 4 is `mmc_blk_reset`, then `mmc_hw_reset`, then `mmc_sd_hw_reset`. That runs
  `mmc_power_cycle` and then `mmc_sd_init_card`. Re-initialisation sends CMD0, CMD8,
  and then ACMD41 (`mmc_send_app_op_cond`), which polls for up to
  `SD_APP_OP_COND_TIMEOUT_MS`, 2000 ms. "Card stuck being busy" with that 2 s gap
  is that poll timing out, so the error is -110.
- In that poll, `sd_app_op_cond_cb` returns command errors at once, and `mtk-sd`
  logs every command timeout outside tuning. With no CMD8, CMD55 or ACMD41 line,
  the card answered those commands at the 400 kHz init clock. For 2 s, though, it
  kept reporting that power-up was not complete.
- `mmc_power_cycle` cannot remove the card's power on this board:
  - `mtk-sd` powers off by setting `vmmc` to 0 and disabling `vqmmc` (VMC).
  - The station DT's `vmmc` is VMCH, marked `regulator-always-on` by
    [0580](../../patches/proposals/0580-arm64-dts-mediatek-gemini-station-keep-the-microSD-c.patch),
    because card detect reads wrong with VMCH off.
  - So the "power cycle" only drops VMC (I/O) for about 2 ms, and the card stays
    powered. That fits a card that answers but never finishes power-up, and that
    stays unusable for hours, until a power-off.
- Host runtime PM: `mtk-sd` autosuspends 50 ms after the last request. Its
  runtime suspend saves the registers and gates the MSDC clocks; resume ungates
  them and writes the registers back. It does not touch the regulators. Nothing in
  the DT gives the card runtime PM: there is no `MMC_CAP_AGGRESSIVE_PM`, so
  `mmc_sd_runtime_suspend` never runs.
- The images in both faults have no cpuidle and no SPM idle state
  ([cpuidle record](../2026-11-07-mt6797-cpuidle/README.md)). The A53 DVFS work
  scales the CPU rails, VSRAM_L and the CCI
  ([DVFS record](../2026-11-08-mt6797-a53-dvfs/README.md)). It does not touch
  Vcore, VMCH, VMC or the MSDC clock source.

**Inferred.**

- **Firm:** recovery can't work on this board. The card ends up in a state that
  only removing VMCH clears, and nothing can remove VMCH while the system runs.
  So any wedge of the card becomes a read-only root until the next power-off.
  That holds whatever the trigger.
- **Open:** what puts the card in that state. Before recovery it answered nothing,
  even CMD13, which a card busy programming still answers. Something stopped it
  at the command level, at 192 MHz, on a write, after about 1.7-1.9 h of sparse
  writes with the screen off and the charger on. Suspend and its resume order are
  not involved in these two faults.

**Hypotheses, most likely first.**

| | Hypothesis | For | Against |
| --- | --- | --- | --- |
| H1 | The card's own controller stalls (firmware, or internal work after long idle). This one card, or its model | Command-level silence; the same card had the milder 11-10 event; it still answers at 400 kHz after a fake power cycle but can't finish power-up | One card; no comparison with another card under the same idle |
| H2 | SDR104 margin at 192 MHz drifts (temperature, charging) until a transfer fails and the card is left mid-transfer | Faults come after long warm idle with charging (board 43-47 °C was logged before the lid closed) | Pure timeouts, no response CRC errors; the T-series map showed a wide window for this slot |
| H3 | A supply disturbance on VMCH or VMC while charging (VMC also has no vendor +40 mV trim, see the power record) | Both faults with the 1.5 A charger connected | No regulator line logged; no measurement |
| H4 | A host runtime-PM race: a request starts while the MSDC clock is gated or not yet stable | The clocks gate and ungate around every sparse write in idle | Thousands of such cycles per hour without a fault; the restore covers the tuning registers |

**Cheap discriminating tests** (proposals for the custodian; one change per run).
Each run repeats the faults' setup:
- the card as root, screen off by lid close;
- the charger connected unless the test says otherwise;
- at least 3 h of idle;
- `dmesg` captured live.

The fault came in two of two such runs, so one clean run is weak evidence. Two
clean runs in a row would be meaningful. Every test starts with an fsck of the
card's filesystem.

| Test | Change | Cost | If it faults | If it stays clean |
| --- | --- | --- | --- | --- |
| S1 | Lower the card clock at run time to 100 MHz: `echo 100000000 > /sys/kernel/debug/mmc1/clock` after boot. The timing mode and tuning stay as they are; the eye only widens | No build; undone at the next re-init or boot | Against H2 | For H2: cap the slot at SDR50 in the DT |
| S2 | Keep the host clocked: `echo on > /sys/bus/platform/devices/11240000.mmc/power/control` | No build; a little idle power | Against H4 | For H4: look at runtime resume on this slot |
| S3 | The same idle with the charger disconnected, on battery | No build; needs the charge | Against H3 as the only cause | For H3 (or heat): measure the rails |
| S4 | The same idle with a card of another model, same image | A second card prepared as root | For a host or board cause (H2-H4); continue S1-S3 | For H1: a card or model problem; record and avoid that model |

S1 also mitigates H2 and S4 mitigates H1. If the fault happens during a test,
capture `/sys/kernel/debug/mmc1/ios` before anything else, then power off: a reboot
alone doesn't remove VMCH.

**Separate from the trigger: a reset that works.** Fixing recovery needs a real
VMCH off-time in `mmc_sd_hw_reset` without losing card detect. One option is to drop
0580's `regulator-always-on` and have the slot keep VMCH on itself, except during a
power cycle. That is a design change, not a test, and it needs its own record.

### The card hang: vendor comparison and a real power cycle (2026-11-13)

The owner asked to treat the hang as a power-management problem, compare the vendor
kernel, and make the host recover the card. This is analysis and code only. Nothing
has run on the device, and no Gemian boot was needed: the public Gemian kernel
([`mt6797/sd.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/mmc/host/mediatek/mt6797/sd.c),
[`msdc_io.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/mmc/host/mediatek/mt6797/msdc_io.c),
the MT6351 field map in `mach/upmu_hw.h`) and the earlier T-series register reads
answer the questions below. The retained Gemian logs have no long idle with a card
in, so they say nothing about the hang itself.

**Vendor against mainline, slot 1** (source, not run):

| | Vendor kernel | Mainline station |
| --- | --- | --- |
| Card power off (`MMC_POWER_OFF`) | VMCH and VMC both off, pins pulled down, 10 ms wait (`msdc_set_power_mode`, `msdc_sd_power`) | VMC off only; VMCH is `regulator-always-on` (0580); no wait, pins unchanged |
| Card power on | VMCH, VMC on, 10 ms wait, then reads the MT6351 VMCH over-current flag (`OCSTATUS1` `0x0212` bit 4) and powers off again if set | VMC on; no over-current check |
| VMCH with no card | Turned on at the end of probe and left on, for card detect | Always on |
| VMCH, VMC voltage | 3.0 V; VMC 3.0 V, then 1.8 V for UHS with the VMC trim lowered by 2 steps (+40 mV) | 3.0 V; VMC 3.0/1.8 V with the firmware trim |
| LDO low-power mode | Not touched by the kernel | Not touched. T1 read `0x0a2e` and `0x0aaa` as `0xda62` with a card in: enabled, software mode (`MODE_CTRL` 0, `ON_CTRL` 0), normal mode (`DA_QI_*_MODE` 0) |
| Clock gating when idle | `msdc_gate_clock(host, 1)` arms a 5 s timer; the clock goes off 5 s after the last request. Before gating it sets `MSDC_CFG` mode to MS; when ungating it re-writes the divider (div+1, then div) and waits for `CKSTB`, with a retry | Runtime PM autosuspend after 50 ms; gates the clocks and saves registers. On resume, ungates, polls `CKSTB` and restores `MSDC_CFG` |
| Periodic or thermal retune | None | None; retune only after a CRC error |
| Stuck card | `msdc_set_bad_card_and_remove` after a stuck state: the card is removed, not recovered (`sd.c` near line 5284) | Block-layer reset with a "power cycle" that leaves VMCH on, so it fails (-110) |

**Inferred.**

- Both kernels leave the LDO modes to the firmware. In the one reading there is,
  VMCH and VMC run in software-controlled normal mode. An idle low-power mode on
  those LDOs is therefore unlikely. It has not been checked at a fault, though.
- The clearest power-management difference is the clock gating. In screen-off
  idle, every sparse write on mainline wakes the host from runtime suspend and
  gates it again 50 ms later. During active use, requests keep it awake. That
  makes many gate cycles an hour in exactly the state where both faults
  happened. The vendor keeps the clock 5 s after a request, and on the way back
  re-programs the divider and checks it, with a retry. A rare bad clock start
  would leave the card with no usable clock in the middle of a request. That
  matches the command-level silence, and the card wedged mid-write.
- The vendor does not recover a stuck card either; it removes it. Recovery is new
  ground, but the vendor shows what a real power-off is on this board: both
  supplies off and about 10 ms.

**Hypotheses, revised order.**

| | Hypothesis | Change since the last section |
| --- | --- | --- |
| H4 | Host runtime PM: a clock-gating cycle in idle goes wrong and the card is wedged mid-request | Up from last: the vendor keeps the clock 100 times longer after a request and checks it on ungating; idle is exactly where mainline gates most |
| H1 | The card's own controller stalls | Unchanged |
| H3 | VMCH or VMC disturbance (over-current or a low-power mode) while charging | Down: the LDOs are in software normal mode; an over-current flag at a fault is still unread |
| H2 | SDR104 margin drift | Unchanged; neither kernel retunes on time or heat |

**Recovery: a real power cycle.**

[0758](../../patches/proposals/0758-mmc-mtk-sd-power-the-card-off-for-real-through-a-car.patch)
lets an `mtk-sd` slot name the supply that card detect needs, as `cd-supply`:
- The host enables it at probe and holds it, so card detect keeps working with the
  card powered off.
- At every card power-off (`MMC_POWER_OFF`), after `vmmc` and `vqmmc`, the host
  drops it for `card_off_ms` (module parameter, default 100 ms), takes it back,
  and logs "card powered off for N ms".
- `card_off_ms=0` keeps today's behaviour.

[0759](../../patches/proposals/0759-arm64-dts-mediatek-gemini-station-let-the-microSD-sl.patch)
gives the station's slot VMCH as `cd-supply` and drops 0580's always-on. The two
patches belong together.

`mtk-sd` is built in (it also drives the eMMC), so this needs an image.

- **What it changes.** `mmc_sd_hw_reset` runs `mmc_power_cycle` and then
  re-initialises. The card is now without VMCH and VMC for about 100 ms, as the
  SD specification requires for a reset and as the vendor does (10 ms). The card
  restarts at 3.3 V signalling, and the core re-runs the 1.8 V switch and tuning.
- **Card detect during the pulse.** GPIO67 reads "no card" while VMCH is off. The
  card-detect interrupt schedules a rescan after the debounce delay. The rescan
  waits for the host claim, so it runs after the reset. The card then answers
  CMD13 and is kept. With the slot empty, the pulse can't make an edge.
- **What the block layer does with it.** In `mmc_blk_mq_rw_recovery`, a reset that
  succeeds returns with the retries left, and `mmc_blk_mq_complete_rq` requeues the
  request. So if the card comes back, the write that failed is retried. ext4 sees
  no error, and the journal does not abort. Only when the reset itself fails does
  the request end in an I/O error, which happens today on every fault.
- **Costs.**
  - About 100 ms more on every card power-off: removal, shutdown, suspend, and an
    empty-slot scan at boot.
  - A recovery stalls I/O for that plus a re-init, roughly half a second.
  - Every system suspend, s2idle included, now really powers the card off
    (`_mmc_sd_suspend` calls `mmc_power_off`). VMCH is back on through the
    suspend, and resume re-initialises the card from cold. Today the card keeps
    VMCH through that path. With the card as root, a failed re-init at resume
    removes the card at the post-suspend rescan. That is a hang, not a read-only
    root. Until R1 and R2 pass, a card-root boot of an image with 0758/0759 takes
    `mtk_sd.card_off_ms=0` on the kernel command line, which keeps VMCH on as
    0580 did.
  - If the card is truly dead (H1 at its worst), a real power cycle may not help
    either, and the result is what happens today.
- **What is not known.** Whether VMCH falls below 0.5 V within 100 ms depends on
  whether its discharge path (`RG_VMCH_NDIS_EN`, `VMCH_ANA_CON1` `0x0ad0` bit 1) is
  on. R1 reads it.
- **Not done here.** `cd-supply` is not in the `mtk-sd` binding yet. Upstream would
  need that binding change and review.

The station profile also gains `CONFIG_FAIL_MMC_REQUEST` (fault injection, inert
until set in debugfs). R1 needs it to drive a request through the reset.

**Device requests (proposals; the custodian schedules them with the owner).**

*At the next fault (any image), before the power-off.* These are read-only:
1. `sh experiments/2026-11-05-gemini-microsd/sd-state.sh`;
2. MT6351 `0x0212` (`OCSTATUS1`: bit 3 VMC, bit 4 VMCH over-current) and `0x0ad0`
   (`NDIS_EN` bit 1), read through regmap debugfs as `sd-state.sh` does.

What it decides: an over-current bit set points to H3; `0x0a2e` or `0x0aaa` showing
low-power mode (bit 8 set) points to H3. Don't `devmem` the MSDC1 registers: the host
is runtime-suspended and its clocks are gated.

*S2 first* (no build; tests H4, the leading hypothesis). It runs as written above:
- `echo on > /sys/bus/platform/devices/11240000.mmc/power/control` after boot;
- lid closed, charger on, at least 3 h, two runs.

| Outcome | Decision |
| --- | --- |
| Clean twice | H4 likely. Then try a longer autosuspend for slot 1 (`power/autosuspend_delay_ms`, for example 5000 as the vendor) for two runs, then make it the DT/driver default |
| Fault | H4 is out. Read the at-fault registers, then S4 (another card) or S1 |

*R1: the recovery path* (needs the image with 0758/0759 and fault injection; one
boot; root on the card is fine, but an eMMC root is safer for the first run).
Hypothesis: with `card_off_ms=100` a reset brings the card back at SDR104, and the
request that failed completes. With `card_off_ms=0` a reset of a healthy card
either fails as in the faults or comes back without UHS.

1. Boot. Record `ios` for `mmc1` (SDR104, 1.80 V) and `dmesg | grep 11240000`
   (no "card powered off" yet with a card in).
2. Read `0x0ad0`, `0x0a2e`, `0x0aaa`.
3. With the default `card_off_ms` of 100:
   - in `/sys/kernel/debug/mmc1/fail_mmc_request`, set `probability` 100,
     `interval` 1, `times` 2 and `verbose` 1;
   - then read one sector directly:
     `dd if=/dev/mmcblk1 of=/dev/null bs=512 count=1 skip=4096 iflag=direct`;
   - record the result, the new `11240000.mmc` and `mmc1` lines, and `ios`.

   Expect:
   - "card powered off for 100 ms";
   - no "recovery failed";
   - `dd` exits 0;
   - `ios` back at SDR104, 1.80 V;
   - the card still present after the card-detect debounce.
4. Then the comparison: run step 3 again with
   `echo 0 > /sys/module/mtk_sd/parameters/card_off_ms`.
   - A failed reset here blocks further read resets until a read succeeds. So if
     the card is left unusable, restore it by taking the card out and putting it
     back (owner), or by a power-off.
   - Set `card_off_ms` back to 100 afterwards.

Two injected failures on one request take it through exactly one reset (data
error, then the reset before the last retry), and the third try succeeds. Stop on a
warning or Oops, or if an injection lands on a write. With the eMMC as root, nothing
on the card is mounted, so no write is at risk.

| Step 3 (100 ms) | Step 4 (`card_off_ms=0`) | Decision |
| --- | --- | --- |
| Recovers at SDR104 | Fails with -110, as the faults | The fake power cycle explains why the faults are unrecoverable; 0758/0759 fix recovery. Keep them in the station image |
| Fails | Fails | 100 ms may not be enough: check `NDIS_EN`, try 500 ms after a reinsertion |
| Recovers | Recovers | A healthy card survives a fake cycle; the cards in the faults were really wedged. 0758/0759 still give the real power-off |

*R2: suspend with the card as root* (after R1; attended; on battery). Use
`card_off_ms=100` and run 3-5 s2idle cycles. After each resume, expect "card
powered off for 100 ms", `ios` back at SDR104 at 1.80 V, and no `mmc1` errors.
Only then drop the command-line override.

### Slow reads after an error: a sticky single-block flag (2026-11-13)

Boot `e7e3b009` of station-work-116 (`850e177e`), with the card as root and
`card_off_ms` at 0. Measured by the custodian; the raw log and trace are private.

**Observed.**

- At 20728.9 s there were six CMD12 timeouts within 0.6 ms, as on 11-10. After
  that, no I/O error.
- Direct reads of `mmcblk1` dropped from 59.3 MB/s earlier on the boot to
  2.3-10.5 MB/s, at SDR104 with no new log lines.
- A 32 MiB direct read took 98-196 block requests and 27-39 thousand `mmc1`
  interrupts.
- The shared CMD/DATA delay read `PAD_TUNE0` `0x003f3f00`, `PAD_TUNE1`
  `0x002f2f00`: delay 47. That is the middle of the longest passing window,
  33-61 in T8's map.
- S1: at 96 MHz the read was as slow as at 192 MHz, about 5 MB/s. (That measured
  the sticky state, not the error rate; see the next section.)
- An `mmc_request_start`/`done` trace of an 8 MiB direct read logged 5700 CMD17
  (all 512 B, no errors), 45 CMD18 and one retune.
  - One CMD18 failed with a data CRC error (-84). No timeouts.
  - The CMD17 runs walk consecutive sectors, and many came with no error before
    them in that request.
  - Each CMD17 took 0.3-0.4 ms.

**What the source says.**

- `mmc_blk_mq_complete_rq` (and the CQE path) sets `MQRQ_XFER_SINGLE_BLOCK` in a
  failed request's `mmc_queue_req` before requeueing it. With the flag set,
  `mmc_blk_data_prep` sends one sector per command.
- `mmc_mq_queue_rq` resets `retries` when it first sees a request, but never the
  flags.
- `mmc_queue_req` is the blk-mq request's private data, which is reused for every
  later request with the same tag. So each tag that ever saw an error moves one
  sector per command until reboot. A card re-init doesn't clear it.
- Upstream added the flag in `c7c6d4f51038` (writes) and `d34124edffdb` (reads).
  Linux master has the same code today.

**Inferred.** The slowdown is this host-side state, not the card and not timing
margin. The CRC errors themselves are rare: 1 in 45 multi-block reads at a centred
delay. Each one, though, slows its tag for the rest of the boot. The eMMC fallback
seen in T6-T8 at HS200 was probably made worse the same way.

**Change.**
[0774](../../patches/proposals/0774-mmc-core-start-each-request-in-multi-block-mode.patch)
clears the flags along with the retry count when a request is first issued. A
requeued request keeps `RQF_DONTPREP`, so it keeps its single-block retry. The
change is in the MMC core, which is built in, so it needs an image.

**Test.** On an image with 0774:
- after any data error, CMD17 runs appear only inside the request that failed;
- direct reads stay near the earlier rate after the error;
- the `mmc_request_*` trace from this section, repeated, shows CMD18 for new
  requests.

### 0774 on the device, and the CRC errors themselves (2026-11-14)

Boot `3f3e037b` of station-work-120 (package `57181f2d…`, from `64c1f85e`, with
0774). The card is root, at SDR104 192 MHz. Measured by the custodian with
`mmc_request_*` traces; raw traces are private.

**Observed.**

- 8 MiB direct read: 73.4 MB/s, 53 CMD18, no errors.
- 128 MiB direct read: 5.0 MB/s. Paired start and done events give:
  - 328 CMD18, of which 49 failed with a data CRC error. Every failure was 1024
    blocks (512 KiB) with nothing transferred.
  - 52224 CMD17 (51 requests' worth), with no errors.
  - 51 retune sweeps (3264 CMD19), with 316 failing cells.
- Most CMD17 fall inside the range of a failed CMD18: 28656 of the 30703 places
  where the sector run breaks. The rest are about two requests' worth not matched
  to a failed CMD18 in the trace.
- Errors came from 219.0 to 245.5 s, spread through the read. The 8 MiB read, and
  a 128 MiB read at another offset (61.5 MB/s), were clean.
- Each sweep's map is different. The failing band wanders between cells 22 and
  33, plus 58-63, so the longest window stays about 25 cells wide around 45.
- dmesg: no `mmc1` error lines.

**Inferred.**

- 0774 works: one-sector reads stay inside the requests that failed. The slowness
  that remains is the CRC error rate: 15 % of multi-block reads in that stretch,
  against 1 in 45 on `e7e3b009`. Each failure costs a retune and 1024 single-sector
  reads.
- The errors come at a delay that the tuning block passes, with a window about 25
  cells wide. Real data fails where the 64-byte tuning pattern doesn't.
- **Correction to S1.** On `e7e3b009` the slowness was the sticky flag of the
  previous section, which doesn't depend on the clock. So S1 did not test whether
  192 MHz causes the CRC errors, and H2 is open again. S1 has to be repeated on an
  image with 0774, counting CRC errors, not measuring rate.

### S1 again, counting errors (2026-11-14)

Boot `3f3e037b`, station-work-120 with 0774. The custodian ran four traced direct
reads of 128 MiB at the same offset (skip=1024). The only change was the debugfs
clock. No new `mmc1`, I/O or EXT4 line appeared. Raw traces are private.

| Run | Clock | Rate | CMD18 | Failed CMD18 (CRC) | CMD17 | CMD19 |
| --- | --- | --- | --- | --- | --- | --- |
| a | 192 MHz | 7.5 MB/s | 402 | 31 (7.7 %) | 31744 | 1984 |
| b1 | 96 MHz | 7.9 MB/s | 339 | 25 (7.4 %) | 25600 | 1600 |
| b2 | 96 MHz | 35.3 MB/s | 295 | 0 | 0 | 0 |
| c | 192 MHz | 9.4 MB/s | 337 | 23 (6.8 %) | 23552 | 1472 |

**Observed.**

- Every run has exactly 1024 CMD17 and 64 CMD19 per failed CMD18, so 0774 holds.
- At 96 MHz one run failed at the same rate as at 192 MHz, and the next was clean.

**Inferred.**

- Halving the clock doubles the timing window but doesn't lower the error rate,
  so the CRC errors are not sampling margin (H2 out).
- They come and go over time on the same sectors. That points to noise or a
  supply level on the card's I/O (H3), or the card itself (H1).
- One more cause would fit how the errors come and go: the A53 voltage scaling
  that these station images run since 11-12, changing the DA9214 CPU rails, the
  CPU SRAM LDOs and the PLLs as load changes. That is where the next test looks.

### S3: the CRC errors against CPU frequency (2026-11-14)

Boot `9a7d0389`, station-work-121 (with 0774), on battery, with the A72s offline.
The custodian traced 128 MiB direct reads with the `mmc1` events,
`power/cpu_frequency` and `regulator_set_voltage_complete`. No `mmc1`, I/O or EXT4
line appeared. Raw traces are private.

| Run | Governors | MB/s | Failed CMD18 |
| --- | --- | --- | --- |
| c1, c2 | schedutil | 13.7, 10.6 | 12/320, 16/318 |
| p1, p2, p3 | performance | 36.2, 40.1, 60.8 | 4/286, 3/316, 0/285 |
| r1, r2 | schedutil | 9.2, 9.8 | 24/316, 18/421 |

**Observed.**

- A failed CMD18 almost never overlaps a frequency or voltage change within its
  own start-to-done window: 2 of 70, against 2-20 % of good requests.
- By the LITTLE cluster's frequency at the request's start, across the schedutil
  runs:

  | Frequency | Failed |
  | --- | --- |
  | 221 MHz | 61/906 (6.7 %) |
  | 338 MHz | 9/267 (3.4 %) |
  | 481-1547 MHz | 0/165 |

- At performance, two of three runs still failed a few times.

**Inferred.**

- The errors follow the operating point the cluster sits at, not the switching.
- At a low LITTLE point three things are low together:
  - the CCI, which follows the LITTLE clusters through the passive devfreq
    governor;
  - the shared VPROC1 rail, with VSRAM_L;
  - the CPU's own speed, so interrupts are serviced later and the bus idles
    between requests.

  S3 doesn't separate them. That the performance runs weren't entirely clean says
  something else adds to it.

**Next: three settings to split them.** Each is a runtime sysfs change, restored
afterwards:

| Setting | LITTLE policies | CCI devfreq | Low together |
| --- | --- | --- | --- |
| A | pinned at the lowest point | as is (follows, low) | CCI, rail, CPU |
| B | pinned at the lowest point | `min_freq` set to its top | CPU only |
| C | performance | `max_freq` set to its bottom | CCI only (the rail stays high for the CPUs) |

| A | B | C | Reading |
| --- | --- | --- | --- |
| fails | clean | fails | CCI clock or bandwidth |
| fails | clean | clean | the rail voltage |
| fails | fails | clean | the CPU's own speed (latency, idle) |
| like the others | | | none of these; the card or the I/O supply |

### S3b: the split, and idle time before a request (2026-11-14)

Boot `9a7d0389`, station-work-121, A72s offline. The custodian traced three 128 MiB
direct reads per setting from the S3 table. A setting restore wrote an empty CCI
`max_freq`, so the last run, z1, ran with the CCI held at 988 MHz. Raw traces are
private.

| Setting | During | Failed CMD18 |
| --- | --- | --- |
| A, all low | LITTLE 221/325 MHz, CCI 234 | 39, 0, 34 of about 310 (7.8 %) |
| B, CPU low, CCI high | LITTLE 221/325, CCI 988 | 13, 0, 1 (1.4 %) |
| C, CPU high, CCI low | LITTLE 1547/2002, CCI 234 | 6, 5, 10 (2.4 %) |
| z1, schedutil, CCI 988 | | 16/321 (5.0 %) |

**Observed** (all 16 traced runs of S3 and S3b, 7404 CMD18 with 200 failures):

- Failures need idle time on the bus. Measured from the previous `mmc1` command's
  completion to the request's start:

  | Idle before the request | Failed |
  | --- | --- |
  | under 0.5 ms | 0/563 |
  | 0.5-2 ms | 46/1270 |
  | 2 ms or more | 154/3571 |

- The same card addresses fail again and again: 31 of the 132 1 MiB-aligned starts
  ever failed, and the worst failed in 13 of 17 runs. 1 MiB-aligned requests, the
  first half of each `dd` block, which follow `dd`'s gap, fail 145/2221. The
  512 KiB-aligned second halves fail 55/2177.
- Identical settings can give 39 or 0 failures.

**What the source says.**

- `msdc_set_mclk` clears `MSDC_CFG_CKPDN` (bit 1) every time it sets the clock. So
  the controller is left free to stop the SD clock while the bus is idle
  (inferred from how the vendor uses the bit). **Wrong:** it clears the bit only
  while it changes the divider, and sets it again once the clock is stable. T10
  read the bit set.
- The vendor's normal paths never touch the bit. Its autotuning (`autok.c`) sets
  it to 1 to force the clock on while it tunes, then puts the old value back.
- Mainline's tuning sends 64 CMD19 back to back, so the clock hardly stops either.

**Inferred.**

- The tuning measures a running clock, and a real request after an idle gap
  starts on a stopped one. A sampling problem of the first transfer after the
  clock restarts would fit everything so far:
  - only after idle;
  - not lowered by halving the clock;
  - more at low CPU and CCI points, which stretch the gaps between requests;
  - invisible to tuning.

  The addresses that fail again and again are partly the gap pattern (first halves
  of `dd` blocks). Some address or content dependence stays unexplained.
- Not shown: what `CKPDN` 1 actually does on MT6797, or that the restart is the
  cause.

**Proposed T10 (a diagnostic register write; needs the owner's admission).**

- Keep MSDC1 clocked with `echo on > /sys/bus/platform/devices/11240000.mmc/power/control`,
  so its registers can be written safely.
- Run setting A (the worst) with three traced 128 MiB reads per arm:
  - arm 0: `MSDC_CFG` as it is;
  - arm 1: `MSDC_CFG` bit 1 set with a `devmem` read-modify-write at `0x11240000`.
- Then clear the bit and set `power/control` back to `auto`.
- Stop on any `mmc1` error line, I/O error or EXT4 error.

| Arm 0 | Arm 1 | Decision |
| --- | --- | --- |
| fails | clean | The clock stopping when idle causes the errors: set `CKPDN` on the SD slot in `mtk-sd` (a small patch), then test the hang the same way |
| fails | fails | Not the idle clock: content dump of the failing blocks, or S4 |
| clean | | Inconclusive: repeat with more idle (`dd bs=512K` with a 5 ms pause) |

### T10 result (2026-11-14)

Boot `9a7d0389`, station-work-121, setting A (LITTLE pinned lowest, CCI 234 MHz).
`power/control` for MSDC1 was `on`, so runtime PM didn't gate it. The owner
admitted the test. Raw traces are private.

**Observed.**

- `MSDC_CFG` read `0x02100093` before any write, with bit 1 (`CKPDN`) already set.
  It read the same after every run, so arm 1's write changed nothing.
- Six traced 128 MiB reads in that one state failed 47, 22, 21, 13, 6 and 30
  times: 139/2089 (6.7 %), like S3b's A.
- No new `mmc1`, I/O or EXT4 line.

**Inferred.**

- The SD clock already runs between requests, so the idle-gap dependence comes
  from something else. The T10 premise came from misreading `msdc_set_mclk`
  (corrected above).
- Runtime PM was held off and the errors stayed, so host clock gating
  (`msdc_runtime_suspend`) doesn't cause the CRC errors either.
- What's left fits a card that needs time to come back after its bus has been
  idle, either in its own logic (H1) or in its I/O supply (H3). Together with the
  repeated addresses, the next tests compare cards and kernels instead of
  registers.

**Next.**

1. **A forced-idle stress test**, read-only, as the standard measurement from
   now on: 256 direct reads of 512 KiB with 5 ms of sleep between them, traced.
   It should fail at a high, repeatable rate in setting A.
2. **S4**: the same stress on a second UHS card of another model, same image.
   - The other card clean: this card or its model (H1).
   - Both fail: the board, I/O supply or host settings (H3), with the vendor's
     VMC +40 mV trim next.
3. **Gemian**: the same stress on this card under the vendor kernel, which logs
   MSDC1 CRC errors at error level. Clean there and failing on mainline means a
   host setting mainline lacks: the VMC trim, driving, or `autok` values.

### Forced-idle stress (2026-11-14)

Boot `4fb1600d`, image 122 (HZ=100 with lazy RCU), card as root, on battery. The
script reads 256 separate 512 KiB blocks with `iflag=direct` and sleeps 5 ms
between them, over the same 1 GiB region as S3b, with `mmc1` traced. Before it the
screen had been blanked for about 30 min. Governors and CCI limits were restored
afterwards. Raw traces are private.

| Run | Setting | Failed CMD18 | Time |
| --- | --- | --- | --- |
| f1 | A (LITTLE 221/325 MHz, CCI 234 MHz) | 0/324 | 16.2 s |
| f2 | A | 0/323 | 17.0 s |
| f3 | A | 1/323 | 17.6 s |
| f4 | schedutil (CCI 819 MHz) | 0/400 | 10.3 s |

**Observed.**

- The gaps were there: about 297 of the ~325 requests per run started 2 ms or more
  after the previous one completed. In S3b that bucket failed 154/3571 (4.3 %).
- Each read went out as one 1024-block CMD18. The one failure was a data CRC error
  (`-84`) at `0x217800`, followed by a retune.
- No new `mmc1`, I/O or EXT4 line.

**Inferred.**

- Idle before a request isn't enough to cause the errors, at least on this boot.
  S3b's reads differ in two ways:
  - each 1 MiB `dd` block became two 512 KiB requests issued back to back, with the
    second queued while the first ran;
  - they ran on a different boot and kernel (HZ=250), with a card already warm
    from earlier runs.
- So the forced-idle script isn't the standard measurement proposed after T10.
  Before comparing kernels, the S3b read must reproduce on this boot.

**Next, on the same boot (read-only, traced, setting A):**

1. The S3b read three times: `dd bs=1M count=128 skip=1024 iflag=direct`.
2. The forced-idle script with `bs=1M`: 128 reads with 5 ms of sleep between them.

| S3b read | 1 MiB forced-idle | Reading |
| --- | --- | --- |
| fails | fails | Two queued requests matter, not idle alone; the 1 MiB forced-idle read becomes the standard measurement |
| fails | clean | Streaming matters, not idle; the S3b read becomes the measurement |
| clean | clean | The rate changed with the boot or kernel (or the card's state); find what reproduces it before Gemian |

The Gemian comparison waits for a read that reproduces on mainline, and then uses
that read.

### The S3b read and 1 MiB forced-idle reads, same boot (2026-11-14)

Boot `4fb1600d`, setting A (CCI 234 MHz), traced like the forced-idle runs.
Hottest thermal zone 28.4 °C before, 26.0-26.3 °C during. No new `mmc1`, I/O or EXT4
line. Raw traces are private.

| Run | Read | Failed CMD18 |
| --- | --- | --- |
| s1 | `dd bs=1M count=128 skip=1024` | 29/399 |
| s2 | same | 10/324 |
| s3 | same | 1/319 |
| g1 | 128 separate 1 MiB reads, 5 ms between them | 6/328 |
| g2 | same | 6/296 |

**Observed.**

- Every one of the 52 failures followed 2 ms or more of bus idle. None followed a
  start less than 0.5 ms after the previous CMD18 completed. Most of the two
  512 KiB halves of a 1 MiB read were not back to back either.
- The same three reads failed less each time: 29, 10, 1.
- Some addresses failed again across runs, `0x201400` three times.

**Inferred.**

- The errors are back on this boot, so the kernel change (HZ=100) didn't remove
  them. 1 MiB reads reproduce them where 512 KiB reads over the same region gave
  1/970. Why the request size matters isn't known.
- The repeated identical read settling from 29 to 1 suggests the card, or its
  state for that region, changes after a read. That points towards the card (H1),
  but doesn't show it.
- g held steady at about 2 %, so it becomes the standard stress.

**Next: Gemian runs g** on this card, three runs, for about 900 requests. At the
mainline rate that should give about 18 failures.
- **None or nearly none:** a host setting mainline lacks. The VMC trim comes
  next, then drive and tuning values.
- **A similar rate:** the card itself.

### Gemian, the same card, the 1 MiB forced-idle stress (2026-11-14)

Gemian 3.18.41+ (#7, 2019-03-29), boot `ae60a241`, card-32 as `mmcblk1`, not
mounted, on battery. Vendor DVFS as is (no cpufreq policy sysfs; cores 4 and 8 to
4-5 online). The custodian ran g three times (128 × 1 MiB direct reads with 5 ms
between them, cache dropped before each run). Raw dmesg is private.

**Observed.**

- 0 new CRC, `msdc1` or `mmc1` lines in 3 × 128 reads, and no I/O error. The vendor's
  interrupt path logs every data CRC error with `pr_err` ("MSDC_INT_DATCRCERR"),
  rate-limited but always printing the first. So a 0 means no error. The boot
  log shows msdc1 lines, so logging was live.
- 6.1-6.2 s per run, about 49 MB/s per read, against 14.9-15.5 s on mainline at
  setting A.
- The vendor queue takes 1 MiB requests (`max_sectors_kb` 4096). Mainline's is
  512 KiB, so it splits each read into two CMD18.
- The vendor tuned SDR104 at 200 MHz with its own autok. Its boot log has one
  "Autok tune LATCH_CK error".

**From the mainline traces** (fi and sg runs on `4fb1600d`, bucketed by idle before
each CMD18):

- fi and g sent the same commands over the same sectors, 512 KiB CMD18s, almost
  all after 12 ms or more of idle. fi failed 1/1024; g failed 12/510.
- The continuous reads failed only after 1.5-8 ms of idle, never after more than
  8 ms.

**Inferred.**

- Gemian at 0 against about 18 expected favours a host-side cause over the card
  (H1 weakened). It doesn't prove it. Mainline also has zero runs (f1, f2, one S3b A
  run), and Gemian differs in request size, tuning and CPU speed.
- Idle on its own is not the cause. With the same commands and gaps, fi and g
  differ twenty-fold. What differs is what the system does around them: one dd
  process per 512 KiB, or a process waiting on two queued halves. The S3b idle
  pattern is real but not the mechanism.
- The candidates left are host settings that the vendor applies and mainline
  doesn't: VMC trim, pad settings, MSDC path bits. They are cheapest to find by
  reading them on both kernels.

**Next: R3, a read-only register comparison**, with the card active (a background
direct read running, so the clock is on):

- On mainline: `sd-state.sh` (pads, MT6351 `0x0ae2` with VMC at 1.8 V), and MSDC1
  `0x11240000`-`0x112402fc` with `devmem` while `power/control` is `on`. Skip `0x18`
  and `0x1c`, the FIFO data ports.
- On Gemian, at its next boot: the same MSDC1 range and pad registers, and MT6351
  `0x0ae2` through the vendor's PMIC access.

Every difference becomes one diagnostic write on mainline, or the VMC trim module,
each needing its own admission.

### R3 result: mainline and Gemian registers with the card active (2026-11-14)

Read-only, through `/dev/mem` (python `mmap`) and the MT6351 interfaces, while a
background direct-read loop kept the card active. Mainline: boot `ca480729`,
image 122, MSDC1 `power/control` `on` during the reads. Gemian: boot `b7d7ce15`.
Raw lists are private.

**MT6351 supply trims:**

| Register | Mainline | Gemian |
| --- | --- | --- |
| `0x0ace` (VMCH, CAL bits 4:0) | `0x0005` | `0x0000` |
| `0x0ae2` (VMC, VOSEL 10:8 = 3 for 1.8 V, CAL 4:0) | `0x031b` | `0x0300` |

**From the public vendor source** (`sd.c`, `msdc_set_host_power_control()` for host 1):

- The vendor's MSDC1 probe subtracts 5 from VMCH_CAL and `0x1b` from VMC_CAL, modulo
  32. Its comments call the firmware values a +100 mV calibration that it
  doesn't want at 3.0 V.
- The firmware leaves 5 and `0x1b`, as T1 read at mainline entry. So Gemian
  runs both at 0.
- Its later "+40 mV" step at 1.8 V computes 0 - 2 = `0xfffffffe`. Its PMIC write
  rejects that, as the [trim record](../2026-07-12-mt6797-msdc-recovery/MICROSD_POWER.md#the-18-v-trim-subtraction-has-a-refusal-boundary)
  predicted, so VMC stays at 0.
- Mainline never touches the CAL fields. It runs both rails with the firmware
  trims, which the vendor treats as 100 mV off.

**Other differences:**

- **Pads.** The pull-strength bits (`R0`/`R1` bits 15-16) and one Schmitt-trigger
  bit (`0x10002830` bit 26) differ, but they belong to other pins. The microSD
  pins use pull bits 18-23 and Schmitt bits 0-2, which match on both kernels
  (see T11 result).
- **MSDC1 sampling path.** Mainline uses data latch clock 0 with `CKGEN_MSDC_DLY_SEL`
  1, and pad delays of 47 for CMD and data, through the second delay field.
  Gemian uses latch clock 1 with CKGEN 0, and a data delay of 8 and a CMD delay
  of 4, from its own autok at 200 MHz.
  - `PATCH_BIT1` also differs: bit 16, the turnaround counters and `GET_BUSY_MA`.
  - `PATCH_BIT2` differs in the response and CRC-status sampling fields (write
    side).
- The rest (interrupt, DMA address and last-command registers) is request state,
  not configuration.

**Inferred.**

- The supply trims are the one difference the vendor sets on purpose and mainline
  doesn't, at a level outside tuning. They fit a fault that depends on the card
  waking after idle and not on the clock.
- Next comes the sampling path. Mainline's own tuning places it, so it's the least
  likely.

### T11: the vendor's supply trims (diagnostic PMIC write, needs the owner's admission)

**Hypothesis.** With VMCH_CAL and VMC_CAL at 0, as Gemian runs them, the 1 MiB
forced-idle stress (g) stops failing on mainline.

**Tool.** [`sd-trim/sd-trim.c`](sd-trim/sd-trim.c), a diagnostic module, built out
of tree against image 122's configuration.

- It gets the `vmch` and `vmc` regulators by name and writes only the CAL bits
  (4:0) of `0x0ace` and `0x0ae2` through the regulator's regmap. It logs the
  register and voltage before and after.
- Unloading puts the saved values back. A parameter of -1 leaves that rail alone,
  which allows a later split.
- Nothing loads it at boot, and a restart returns the firmware values.
- Built from `e95ed0af` on Buildbox-2 with the same GCC 12.2.0, against image
  122's `kernel.config` (package `38fbc8e1…`). `sd-trim.ko` sha256 `30a59c40…eb72e`.
  Its vermagic matches the image's modules, and all nine imports are exported in
  the image's `System.map`. It is built, not yet loaded.

**Procedure.** Image 122, card root, on battery, setting A, traced like the earlier
g runs. Read-only on the card apart from the root's own writes.

1. Record the boot ID, taint, `ios`, the regulators and the PMIC registers
   (`sd-state.sh`).
2. Arm 0: g twice, with no module.
3. `insmod sd-trim.ko vmch_cal=0 vmc_cal=0`. Check that dmesg shows both set lines
   and that `0x0ace` reads `0x0000` and `0x0ae2` `0x0300`.
4. Arm 1: g three times.
5. `rmmod sd-trim`. Check that the restored lines appear and that the registers
   read `0x0005` and `0x031b`.
6. Arm 0 again: g once.

**Stop.** At any `mmc1` error line, I/O error, `EXT4-fs error`, `Remounting`,
warning or Oops: `rmmod sd-trim` if it's loaded, then report. No retries.

| Arm 0 (3 runs) | Arm 1 (3 runs) | Decision |
| --- | --- | --- |
| 8 or more failures | 0-1 | The trims cause the errors. Split VMCH and VMC with the parameters, then a regulator-driver or DT change for the slot |
| 8 or more | similar to arm 0 | Not the trims. Next, the pad pulls and Schmitt bit as runtime pinconf writes, then the sampling path |
| under 8 | | No baseline. Repeat the arms on a boot that reproduces |

### T11 result (2026-11-14)

Image 122, boot `08e9a8ff`, card root, on battery, setting A (CCI 234 MHz), g with
`mmc1` traced. The owner admitted T11 with the text in the request. The custodian
ran three baseline runs instead of two, so the three-run rule applies as written.
Raw traces are private.

| Arm | Runs (failed CMD18) | Total |
| --- | --- | --- |
| Firmware trims (`0x0ace` `0x0005`, `0x0ae2` `0x031b`) | b1 7/320, b2 8/392, b3 7/320 | 22/1032 (2.1 %) |
| Gemian's trims (`0x0000`, `0x0300`) | m1 8/323, m2 8/392, m3 2/318 | 18/1033 (1.7 %) |
| Firmware trims again | r1 7/325 | |

**Observed.**

- The module set and restored both fields as logged. The register reads matched
  each time.
- No `mmc1`, I/O, EXT4, `Remounting`, warning or Oops line.

**Inferred.**

- The supply trims don't cause the CRC errors.
- The R3 pad differences belong to other pins. The vendor's MSDC1 masks (`msdc_io.h`)
  put the microSD pulls at bits 18-23 of `0x10002500`-`0x10002520` and its Schmitt
  triggers at bits 0-2 of `0x10002830`. Both kernels read the same values there.
  Slew rate (`0x10002430`) wasn't read.
- What's left is MSDC1's own configuration. One bit stands out, because it fits a
  fault that needs idle time:
  - `MSDC_CFG` bit 1 (`CKPDN`) is 0 on Gemian. The controller then stops the SD
    clock whenever it has nothing to do.
  - Mainline sets it after every clock change, so the clock runs continuously
    between requests (T10).
  - The vendor sets it only while autok tunes.
- The other MSDC1 differences:
  - `SDC_CFG`: SDIO detection, bit 20 set on mainline, which Gemian has clear;
  - `PATCH_BIT1` bit 16 and the turnaround counters;
  - the sampling path (latch clock, CKGEN delay, pad delays).

### T12: the SD clock stopped when idle, as Gemian runs it (diagnostic register write, needs the owner's admission)

**Hypothesis.** With `MSDC_CFG.CKPDN` cleared, g stops failing.

**Procedure.** Image 122, card root, on battery, setting A, g traced as before.

1. `echo on > /sys/bus/platform/devices/11240000.mmc/power/control`, so MSDC1 stays
   clocked and its registers can be written. Read `MSDC_CFG` (`0x11240000`); it is
   expected to read `0x02100093`.
2. Arm 0: g three times.
3. Clear bit 1 with a read-modify-write of `0x11240000`, through `/dev/mem`. The
   register must read back with bit 1 clear and everything else unchanged.
4. Arm 1: g three times. Read `MSDC_CFG` after each run. A clock change sets the
   bit again; if it is set again, record that and clear it once more.
5. Set bit 1 back, then `echo auto > …/power/control`.
6. Arm 0 again: g once.

**Stop.** At any `mmc1` error line, I/O error, `EXT4-fs error`, `Remounting`,
warning or Oops: set bit 1 back, restore `power/control`, then report. No retries.

| Arm 0 (4 runs) | Arm 1 (3 runs) | Decision |
| --- | --- | --- |
| 8 or more | 0-1 | The free-running clock causes it. Patch `mtk-sd` to leave `CKPDN` clear on the SD slot after a clock change, then test the hang the same way |
| 8 or more | similar | Not the idle clock. Next: `SDC_CFG` bit 20, then `PATCH_BIT1` bit 16 |
| under 8 | | No baseline |

## Follow-up

- Suspend and resume.
- The VMC trim question in the
  [power record](../2026-07-12-mt6797-msdc-recovery/MICROSD_POWER.md#the-18-v-trim-subtraction-has-a-refusal-boundary)
  still needs settling if UHS needs the vendor's +40 mV.
- eMMC HS400 ([T9 result](#t9-result-2026-11-06)): write rates and repeat boots.
  HS200 alone still has silent read errors ([T8 result](#t8-result-2026-11-06)), so
  a board without HS400 should not rely on it.
- The card stops answering during long screen-off idle, and the reset can't recover
  it ([the card hangs in idle](#the-card-hangs-in-screen-off-idle-2026-11-12-13)):
  S2 and the at-fault reads come first
  ([vendor comparison](#the-card-hang-vendor-comparison-and-a-real-power-cycle-2026-11-13)).
  The recovery change (0758/0759) needs R1.
