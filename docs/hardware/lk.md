# Retained LK bootloader

LK is the second-stage loader on the Gemini PDA. It runs after the preloader
and ATF, chooses a boot partition from the keys, decides the boot mode, sets
eMMC write protection, rewrites the device tree and jumps to the kernel. This
page is what the project relies on about it. The chronology, method and exact
evidence are in the
[LK behaviour record](../../experiments/2026-11-05-gemini-lk-behaviour/README.md).

Each fact carries its basis:

- **observed**: measured on the named unit;
- **source**: read in the public Planet LK source,
  [`dguidipc/gemini-lk-android8`](https://github.com/dguidipc/gemini-lk-android8/tree/f4988d74bb70a0a15d7f362f412afba7e7fcda46)
  at `f4988d74`, under `lk/`;
- **binary**: checked in the unit's own `lk` partition (`lk` and `lk2` are
  identical, SHA-256 `75ec9f0b…`);
- **inferred**: reasoning from the above, not measured.

The retained binary matches the source on every path checked here: slot
selection, the boot-mode key loop, the charging decision, write protection and
the absence of the `bypass_wp` switch. Source facts are therefore the working
model, but only observed facts count as hardware behaviour.

## Start sequence

The order matters because LK reads the keys at several points. Paths are under
`lk/`.

| Step | What LK does | Keys read | Basis |
| --- | --- | --- | --- |
| 1 | Vibrates 200 ms, unless the mode is already a charging or alarm mode ([`platform.c:597`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/platform.c#L597)) | none | source |
| 2 | Initializes the eMMC host only (MSDC0) | none | source |
| 3 | Loads the DTB early from `boot`, `boot2` or `boot3` ([`platform.c:631`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/platform.c#L631)) | side, power | source, binary |
| 4 | Initializes the display and fills it black | none | source |
| 5 | Selects the boot mode ([`boot_mode.c:81`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/boot_mode.c#L81)): META and similar from the preloader, the RTC and `para` recovery requests, a 50 ms key window, then the charging decision | power, side | source, binary |
| 6 | Reloads the DTB from `recovery` in recovery mode | none | source |
| 7 | Loads `logo`, starts the security library, checks `logo` | none | source |
| 8 | Battery init: low-battery handling, power key during charging mode | power | source |
| 9 | Shows logo slot 0 in normal and charging mode; not in alarm mode | none | source |
| 10 | Reads the boot image header, then the body, from the selected partition | side, power, twice | source, binary |
| 11 | Sets eMMC write protection for the mode | none | source, observed |
| 12 | Writes `/chosen`, `/memory`, `/firmware/android` and the command line, then jumps | none | source |

Keys are PMIC inputs, not keypad positions: code 8 is the power key, which the
keyboard reports as Esc, and code 17 is the home key, which is the outside side
key ([keyboard](keyboard.md)). Both are read live as debounced levels; nothing
is latched from power-on (source, binary).

## Choosing boot, boot2 or boot3

At steps 3 and 10 LK applies the same rule
([`mt_boot.c:2208`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/app/mt_boot/mt_boot.c#L2208)):

| Held at that moment | Partition |
| --- | --- |
| side and power | `boot3` |
| side only | `boot2` |
| neither, or power only | `boot` |

The rule applies in normal, charging, alarm, META and factory modes. Recovery
mode always loads `recovery`. No software path writes a one-shot choice of
`boot2` or `boot3` (binary, earlier [audit](../../experiments/2026-07-12-boot-contract-recovery/results/lk-boot2-software-selection-audit-20260718.txt)).

**Hold the side key from power-on until the logo has been up for a moment.**
The DTB is taken at step 3, before the display starts, and the kernel at step
10, after the logo. Each read is separate, so a key released in between gives a
DTB from one partition and a kernel from another, and a release between the
header and body reads mixes two images (source, inferred). The project's
procedure holds the key through the logo, which avoids this.

## Boot modes

`atag,boot` carries the mode as its third 32-bit word, and
`/firmware/android/mode` carries its name (source; mode 0 and 8 observed).

| Mode | Value | Trigger | Partition | Write protection | `firmware/android/mode` |
| --- | --- | --- | --- | --- | --- |
| Normal | 0 | At the charging decision: power key down (with the side key, since alone it selects recovery first), watchdog reboot, RTC two-second reboot or bypass flag, or a charger with off-mode charging disabled | key rule | full set | `normal` |
| Recovery | 2 | RTC `PDN1` recovery flag; `boot-recovery` in `para`; power key held **without** the side key during the 50 ms window at step 5; preloader request | `recovery` | `seccfg` only | `recovery` |
| META, advanced META | 1, 5 | Preloader request (tool handshake) | key rule | `seccfg` only | `meta` |
| Factory, ATE factory | 4, 6 | Preloader request; no factory key in this build | key rule | `seccfg` only | `factory` |
| Alarm | 7 | RTC power-on alarm, or preloader request | key rule | `seccfg` only | `normal` |
| Power-off charging | 8 | Charger present at step 5, no power key, no alarm, no reboot flag | key rule | `seccfg` only | `charger` |
| Low-power charging | 9 | Power-off charging with the battery below LK's low-voltage limit | key rule | `seccfg` only | `charger` |
| Fastboot | 99 | Preloader request only | none, stays in LK | none | n/a |

Notes:

- **No charger and none of the normal-start conditions: LK powers off**
  ([`mt_kernel_power_off_charging.c:97`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/mt_kernel_power_off_charging.c#L97);
  source, binary). How an ordinary Esc start meets a normal-start condition
  when Esc is already released is not settled: the preloader may set the RTC
  bypass flag that `rtc_boot_check()` accepts. Open question.
- **The 50 ms window comes first.** Read literally, Esc still held there
  without the side key selects recovery; Esc together with the side key does
  not ([`boot_mode.c:241`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/boot_mode.c#L241);
  source, binary). Not tried on the unit.
- **Esc during a charging start** keeps mode 8 but passes `boot_reason=4` to
  the kernel (source). The vendor kernel presumably starts normally on it
  (inferred).
- **The side key changes the partition, not the mode.** A side-key plug-in start
  is still mode 8 (observed, boot `b84236ce`).
- **Logo:** LK shows the same boot logo in normal and charging mode
  (source). A logo followed by Gemian therefore doesn't show which mode ran;
  only `atag,boot` or `androidboot.mode` does.
- **Plain `poweroff` with the cable in** restarts by itself: the PMIC re-powers
  with a charger present (observed,
  [station 8](../../experiments/2026-10-30-mainline-dev-station/README.md)).
  The mode of that restart was not read.
- Off-mode charging can be disabled by the `off-mode-charge` LK environment
  variable; it is enabled when unset (source). Not read on the unit.

## eMMC write protection

LK sets it at step 11 through `write_protect_flow()`
([`write_protect.c:137`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/write_protect.c#L137)):

- **Every mode:** user-area power-on protection on `seccfg`.
- **Normal mode only:** power-on protection on `preloader`, which is the
  eMMC boot area, and on the user range `oemkeystore` to `keystore`.
- The `bypass_wp` environment switch is compiled out of this build (source:
  user build guard; binary: no bypass string).
- Power-on protection lasts until the eMMC loses power or is hardware-reset.
  LK has no call to clear it.

Observed on the station, with a read-only CMD31 reader and `EXT_CSD`:

| Start | Mode | User area, power-on protected | `BOOT_WP` |
| --- | --- | --- | --- |
| Side key, normal start (boot `a09c7951`) | 0 | sectors 245760–458751, one run; everything else none | `0x81` |
| Cable out, off; side key held while plugging in (boot `b84236ce`) | 8 | sectors 245760–262143 only | `0x00` |

The write-protect group is 8 MiB (16384 sectors), and both ends are
group-aligned. From the partition sizes in the private capture, assuming
partitions follow each other on disk (inferred; the end of `keystore` lands
exactly on 458751):

| Partition | Sectors | Normal start | Charging start |
| --- | --- | --- | --- |
| `seccfg` | 245760–262143 | protected | protected |
| `oemkeystore`, `proinfo`, modem images, `scp1`, `scp2` | 262144–350207 | protected | not protected |
| `nvram` | 350208–360447 | protected | not protected |
| `lk`, `lk2` | 360448–362495 | protected | not protected |
| `boot` | 362496–395263 | protected | not protected |
| `logo`, `tee1`, `tee2`, `keystore` | 395264–458751 | protected | not protected |
| `recovery`, `para`, `system`, `cache`, `linux`, `boot2`, `boot3`, `userdata` | elsewhere | not protected | not protected |

`BOOT_WP` `0x81` sets power-on protection with the area selected by bit 1,
which is clear: boot area 1, `mmcblk0boot0` on Linux, the active preloader
copy. Boot area 2 is not covered even after a normal start (inferred from the
register layout and LK's
[`mmc_set_boot_wp()`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/mmc_core.c#L2737)).

This protection is a safeguard: a normal start keeps `nvram`, `lk` and `boot`
safe from a bad kernel. **A charging start leaves `nvram`, `lk`, `lk2`, the
boot area and `boot` writable for the whole boot.** These stay outside the
project's write approvals. The July `boot` write failures with
`WP_VIOLATION` came from this protection
([first-install notes](../../experiments/2026-11-05-gemini-lk-behaviour/README.md#analysis)).

## What LK hands the kernel

### Boot image

Basis: source, matching the stock image and every station image.

- **Container:** Android boot image v0 (`ANDROID!`), any page size given in
  the header. LK reads `kernel_sz` + `ramdisk_sz` + one page, rounded to
  pages; it ignores the rest of the partition, so zero padding is harmless.
- **64-bit:** chosen when the header command line contains `bootopt=64`. The
  kernel payload is gzip-compressed and decompressed to the header
  `kernel_addr`. The decompressed size limit is 50 MiB (`0x03200000`). Linux
  needs `kernel_addr - text_offset` 2 MiB-aligned ([boot contract](../../experiments/2026-07-12-boot-contract-recovery/README.md)).
- **DTB:** appended to the gzip payload, inside `kernel_sz`. LK scans the
  last 512 KiB of the kernel payload backwards for the last FDT magic, so the
  DTB must be at most 512 KiB and sit at the end
  ([`bldr_load_dtb()`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/app/mt_boot/mt_boot.c#L608)).
  The header `dt_size` is not used. The DTB is copied to `tags_addr`.
- **Addresses:** `kernel_addr`, `ramdisk_addr` and `tags_addr` from the header
  are claimed from LK's memory map; LK's own image starts at `0x46000000`. The
  project uses `0x40200000`, `0x45000000` and `0x44000000`.
- **Size:** bounded by the partition, 16 MiB for `boot`, `boot2`, `boot3` and
  `recovery` (observed sizes). The station's 16 MiB padded images follow the
  partition size, not an LK rule.
- **Command line:** the header's 512-byte field is appended to LK's own; LK's
  buffer is 1024 bytes in all.

### Device tree

LK edits the DTB in place before the jump (source; earlier
[FDT fixup audit](../../experiments/2026-07-13-lk-fdt-fixup-recovery/README.md)):

- `/memory` `reg` is replaced from LK's memory blocks, and runtime
  reservations are appended to `/reserved-memory`. Static entries that overlap
  them stop the boot.
- `/chosen`:
  - `bootargs`: LK's full command line;
  - `linux,initrd-start` and `linux,initrd-end`, one cell each;
  - `atag,boot`: size, tag `0x41000802`, mode;
  - `atag,cmdline` and `atag,mem`;
  - `atag,videolfb`: the framebuffer LK reserved and is displaying;
  - `atag,devinfo`, `atag,mdinfo`, `atag,meta`, `atag,ptp`, `atag,masp`;
  - battery and gauge values (`atag,imix_r`, `atag,fg_swocv_v`,
    `atag,fg_swocv_i`, `atag,shutdown_time`, `atag,boot_voltage`,
    `atag,two_sec_reboot`);
  - `kaslr-seed`, `tee_reserved_mem`, `non_secure_sram`, `ccci,modem_info`.
- `/firmware/android`: `compatible`, `hardware`, `serialno` and `mode`
  ([`atags.c:893`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/atags.c#L893)).
  `serialno` is an identifier; scrub it from published logs.
- The model and CPU nodes are rewritten; the command line carries
  `maxcpus=5` ([all cores](../../experiments/2026-11-01-mt6797-all-cores/README.md)).

The kernel's own `CONFIG_CMDLINE_FORCE` ignores `bootargs`, but the property
stays readable under `/sys/firmware/devicetree/base/chosen/`.

### Command line additions

On Gemian's normal start, LK's line contained
`console=ttyMT0,921600n1`, `maxcpus=5`, `androidboot.verifiedbootstate=green`,
`androidboot.veritymode=enforcing`, `printk.disable_uart=1`, boot timing,
`boot_reason`, `androidboot.serialno` and `androidboot.bootreason` (observed,
[handoff refresh](../../experiments/2026-07-13-memory-carveout-recovery/results/live-handoff-refresh-20260714.txt)).
`boot_reason` is the preloader's reason: 0 power key, 1 USB, 2 RTC, 3 watchdog,
4 watchdog reboot or charging-mode Esc, 6 two-second reboot (source).

### Hardware state at the jump

Basis: source, unless marked.

- **Display:** panel initialized, logo shown, backlight on in normal and
  charging mode. The framebuffer is reserved and described by `atag,videolfb`.
  This is the loader-retained console the station uses
  ([boot graphics](boot-graphics.md)).
- **Storage:** only MSDC0, the eMMC, is initialized
  ([`mmc_common_inter.c:422`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/mmc_common_inter.c#L422)).
  LK has VMCH code but never starts the microSD host, so card power and card
  detect are the kernel's job
  ([microSD record](../../experiments/2026-11-05-gemini-microsd/README.md)).
- **Modem:** MD1 is powered down. **SCP:** firmware loaded and described in
  the DT. **Clocks:** unused PLLs off, DCM on.
- **Vibrator:** pulsed at step 1 and left off.
- **Write protection:** as above, for the whole boot.

## Verification, fastboot and unlocking

- **Boot image check:** `verified_boot_flow()` runs the same way for `boot`,
  `boot2` and `boot3`, under the policy entry for `boot`
  ([`load_image.c:319`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/load_image.c#L319)).
  - Locked with verification required: a failed check falls back to a custom
    key, else red state, a five-second warning and a reset.
  - Locked without verification: green.
  - Unlocked: orange, with a five-second warning.
- **This unit:** Gemian's unsigned image on `boot` boots green (observed), so
  the device is locked and the policy doesn't verify `boot` (inferred). Since
  the slots share one code path, LK should accept our image on `boot` as it
  does on `boot2` (inferred). The station's own `verifiedbootstate` has not
  been read.
- **`logo` and `odmdtbo`** pass through a separate check and halt on failure
  ([boot graphics](boot-graphics.md)).
- **Fastboot:** compiled in, with `flashing unlock` and an on-screen
  confirmation. Its LK entries are off in this build (`MTK_FASTBOOT_SUPPORT :=
  no`, no fastboot key or RTC check in the boot-mode routine; source, binary).
  Only a preloader request reaches it. Not tried.
- **Unlocking isn't needed** to boot our images. It would also change
  `seccfg`, which is protected in every mode.

## For a first install

- `boot` is writable only from a non-normal start. A side-key charging start
  is mode 8 and loads `boot2`, with `boot` unprotected (observed).
- The same start leaves `lk`, `lk2`, `nvram` and the boot area writable. An
  installer running there writes only `boot`, by GPT name, with full readback.
- Init can tell a charging start from `atag,boot`, mode 8, or from
  `/firmware/android/mode`, `charger` (source; `atag,boot` observed).
- Once our kernel is on `boot`, every cable plugged into an off device starts
  it in mode 8. Init should stay in a charge-only state there, with the
  charge guard, and power off on unplug.
- A normal start of our kernel on `boot` gets the full protection set again.
- Recovery, META and alarm starts are also unprotected; nothing in the
  project uses them.

## Open questions

Each needs a device reading.

| Question | Reading |
| --- | --- |
| Station verified-boot state and LK's command line | `/sys/firmware/devicetree/base/chosen/bootargs` on the station, scrubbed |
| What mode the plain-`poweroff`-with-cable restart uses, and whether it clears protection | `atag,boot` and the write-protect reader after that restart, side key held |
| Whether a watchdog or warm reset clears power-on protection | The write-protect reader after a `reboot` into boot2 |
| How a normal Esc start passes the charging decision | Owner's description of how long Esc is held; LK UART log if ever available |
| Whether Esc held through the logo starts recovery | Not to be tried without a reason; `recovery` holds the vendor recovery |
| Whether a charging start vibrates | Owner observation during the next charging start |
| `off-mode-charge` setting | Not read; LK environment in `para` |
