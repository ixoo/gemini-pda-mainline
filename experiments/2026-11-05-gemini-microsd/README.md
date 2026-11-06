# Experiment: the microSD slot on MSDC1 with the upstream mtk-sd driver

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-05-gemini-microsd` |
| Status | `completed`: microSD at UHS SDR104 (192 MHz, about 86 MiB/s, vendor pad settings, exFAT), and the eMMC at HS200 (192 MHz), whose multi-block reads fail silently and fall back to single sectors (T6), with hotplug and a card at boot. Card detect needs VMCH kept on (patch 0580) |
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

## Follow-up

- Suspend and resume.
- The VMC trim question in the
  [power record](../2026-07-12-mt6797-msdc-recovery/MICROSD_POWER.md#the-18-v-trim-subtraction-has-a-refusal-boundary)
  still needs settling if UHS needs the vendor's +40 mV.
- eMMC HS400, once its data-strobe delay is known.
- eMMC HS200 data errors ([T6 result](#t6-result-2026-11-06)): 0625 widens the
  tuning scan, [T7](#t7-hs200-with-a-64-cell-scan) tests it.
