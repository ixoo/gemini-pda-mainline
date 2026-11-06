# Experiment: how the retained LK selects, protects and hands off

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-05-gemini-lk-behaviour` |
| Status | `completed`: source and binary read; write-protect behaviour in modes 0 and 8 observed. Open questions listed |
| Subsystem | Retained Planet LK: boot selection, boot modes, eMMC write protection, kernel handoff |
| Device variant | named Gemini PDA (MT6797X), boot2 RAM-root station and Gemian |
| Date(s) | 2026-11-05 |
| Investigator(s) | Repository maintainer with Claude assistance |
| Tracking issue | none |

## Question or hypothesis

How does the unit's LK choose a partition and a boot mode, what eMMC write
protection does it set in each mode, and what does it hand the kernel? The
first-install design needs this in one place, and needs to know whether a
side-key charging start leaves primary `boot` writable.

Prior reports: the boot contract and FDT fixup audits (July), the boot2
selection audit (July), the station's power-off tests and the side-key record.
They are linked below rather than repeated. The durable summary is the
[LK hardware page](../../docs/hardware/lk.md).

## Provenance and environment

- Public source: Planet LK,
  [`dguidipc/gemini-lk-android8`](https://github.com/dguidipc/gemini-lk-android8/tree/f4988d74bb70a0a15d7f362f412afba7e7fcda46)
  at `f4988d74bb70a0a15d7f362f412afba7e7fcda46`, project `k97v1_64_bsp`,
  fetched shallow in the development VM.
- Binary: the unit's `lk` partition from the private July capture, SHA-256
  `75ec9f0ba97af9e68d964b304e0de809f9b4546982570bd16b2e7fe88823282c`
  (`lk2` identical). ARM Thumb, loaded at `0x46000000`. Read with radare2 in
  the VM; nothing from it is committed.
- Device readings: taken by the device custodian during the first-install T1
  and T2r tests, on station boots `a09c7951` and `b84236ce`, with a static
  read-only reader that sends CMD8 once and CMD31 (`SEND_WRITE_PROT_TYPE`) per
  32 groups through `MMC_IOC_CMD`. It has no write, erase or protect command.
  The reader and its outputs stay with the install design notes, outside the
  repository.
- Earlier Gemian readings are cited from their own records.

## Safety assessment

This work was read-only. This session had no device access. The source and
binary reading is offline. The custodian's T1 and T2r readings write nothing
to any block device; T2r needed one owner-operated power cycle with the cable
and the side key. No partition was written. `lk`, `lk2`, preloader, primary
`boot`, `seccfg`, NVRAM, GPT and the boot areas stay outside every approval,
and no step here proposes writing them.

## Associated code

None committed. The source reading used `grep` and `sed` on the public
checkout; the binary reading used `r2 -a arm -b 16 -m 0x45fffe00`.

## Procedure

1. Read the slot-selection, boot-mode, charging, write-protect, image-load,
   verification and DT-fixup paths in the source.
2. For each path, find the matching routine in the binary through its log
   strings and check the branch conditions and constants.
3. Compare with the T1 and T2r readings and earlier Gemian records.

## Observations

### Source (`lk/` at `f4988d74`)

S1. **Slot rule.**
[`boot_linux_from_storage()`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/app/mt_boot/mt_boot.c#L2181)
loads `boot3` when keys 17 and 8 are down, `boot2` when 17 is down, else
`boot`. It applies to normal, META, advanced META, SW reboot, alarm, both
charging modes, factory and ATE factory. It reads the keys separately for the
header and for the body. Recovery mode loads `recovery`.

S2. **Early DTB.**
[`platform_init()`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/platform.c#L631)
applies the same rule to `bldr_load_dtb()` right after eMMC init, before
display init and boot-mode selection. The DTB is the last FDT magic found
in the last 512 KiB of `kernel_sz`, copied to `tags_addr`, at most 512 KiB.

S3. **Mode selection.**
[`boot_mode_select()`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/boot_mode.c#L81)
runs after display init, in this order:
1. kernel exception dump;
2. preloader mode (META, advanced META, ATE factory, alarm, fastboot, factory,
   recovery);
3. the PMIC just-reset check;
4. the RTC `PDN1` recovery flag;
5. `boot-recovery` in the misc area;
6. a 50 ms loop in which the power key down without key 17 selects recovery;
7. the charging decision.

S4. **Charging decision.**
[`kernel_power_off_charging_detection()`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/mt_kernel_power_off_charging.c#L97):
- `is_force_boot()` returns true for an RTC alarm or a bypass, factory-reset
  or alarm flag, META-type modes, the power key down, a watchdog
  bypass-power-key reboot or the RTC two-second reboot.
- Otherwise, with a charger: mode 8 if `off-mode-charge` is enabled (default
  when unset), else normal.
- Otherwise, with no charger: power off.

S5. **Power key during charging.** Battery init sets `boot_reason` to 4 when
the power key is down in mode 8; the mode stays 8.

S6. **Logo.** The boot logo is shown in normal and charging mode, after
`mt_disp_power(TRUE)` in charging mode; the low-battery image in mode 9;
nothing in alarm mode.

S7. **Write protection.**
[`set_write_protect()`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/write_protect.c#L137):
- normal mode: power-on protection on `preloader`, then `oemkeystore` to
  `keystore`;
- every mode: `seccfg`.

It is called from `boot_linux_from_storage()` just before the jump. The
`bypass_wp` environment read is under `#ifndef USER_BUILD`. `preloader` maps to
the active eMMC boot area. `mmc_set_boot_wp()` sets `B_PWR_WP_EN` and
`B_SEC_WP_SEL`, with `B_PWR_WP_SEC_SEL` clear for boot area 1. The user-area
path refuses a range that isn't group-aligned.

S8. **Verification.**
[`verified_boot_flow()`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/load_image.c#L319)
is the same for every slot and uses the `boot` policy entry:
- locked with verification required: a failure becomes yellow with a custom
  key, else red, with a warning and then `msg_img_error()`, which resets after
  8 s;
- locked with verification not required: green;
- unlocked: orange, with a 5 s warning.

The state is appended as `androidboot.verifiedbootstate`.

S9. **Fastboot.** The target sets `MTK_FASTBOOT_SUPPORT := no`. The non-menu
branch of `boot_mode_select()` therefore has no fastboot key or RTC check.
Fastboot mode is reached only through the preloader's mode argument.

S10. **Handoff.** `boot_linux()` writes the properties listed on the hardware
page:
- `/chosen/atag,boot` is `{size, 0x41000802, g_boot_mode}`;
- [`target_fdt_firmware()`](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/atags.c#L893)
  sets `/firmware/android/mode` to `normal`, `charger`, `recovery`, `meta` or
  `factory`;
- the command-line buffer is 1024 bytes.

`mmc_legacy_init(1)` initializes host 0 only. VMCH is touched only by MSDC
power code that LK never runs for the microSD host.

S11. **Image limits.** `KERNEL_DECOMPRESS_SIZE` is `0x03200000` (50 MiB). The
read size is `kernel_sz` + `ramdisk_sz` + one page, in pages. LK runs from
`0x46000000`.

### Binary (unit's `lk`)

B1. The slot rule and the early-DTB rule test codes `0x11` and `8` as in S1
and S2, before the partition lookups. This confirms the July
[selection audit](../2026-07-12-boot-contract-recovery/results/lk-boot2-software-selection-audit-20260718.txt),
whose second key site is the early-DTB routine.

B2. The key routine sends code 8 to a PMIC read of `TOPSTATUS` (`0x220`)
and code `0x11` to the home-key read. Other codes read the keypad.

B3. The boot-mode routine has the S3 order: preloader mode, PMIC just-reset,
RTC recovery flag, misc recovery, then a loop bounded at 50 timer ticks that
reads code 8 and then `0x11`, and sets mode 2 when 8 is down and `0x11` isn't.
No other key is read there, so there is no factory, boot-menu or fastboot key.
Then comes the charging decision, ending in the two log strings for
charging and normal.

B4. The charging decision matches S4: the force-boot test, then the off-mode
setting, then the charger-detect call. Mode 8 is stored when a charger is
present; the power-off routine is called when not.

B5. Present: the write-protect strings (`Lock seccfg`, `write protect Done!`).
Absent: `Bypass write protect`.

B6. Present: strings for the four verified-boot states, `fastboot` commands
including `flashing unlock`, and a lock and unlock confirmation screen.

### Device

D1. **T1, station boot `a09c7951`, side key, normal start.**
- `atag,boot` mode 0.
- Power-on write protection is one run, sectors 245760–458751. All other
  groups have none, including `recovery`, `system`, `cache`, `linux`, `boot2`,
  `boot3` and `userdata`.
- The WP group is 16384 sectors (8 MiB).
- `BOOT_WP` is `0x81`.

D2. **T2.**
- `poweroff` ran with the cable in, because USB SSH couldn't power off after
  an unplug.
- The owner saw a boot logo, then Gemian.
- The mode wasn't read.

D3. **T2r, station boot `b84236ce`.**
- The cable was unplugged before `poweroff`. The owner held the side key while
  plugging it in.
- `atag,boot` mode 8.
- Only sectors 245760–262143 are power-on protected. `boot`, `lk` and `nvram`
  read none.
- `BOOT_WP` is `0x00`.

D4. **Earlier, Gemian on `boot`.**
- `androidboot.verifiedbootstate=green` and `androidboot.veritymode=enforcing`
  ([handoff refresh](../2026-07-13-memory-carveout-recovery/results/live-handoff-refresh-20260714.txt)).
- The image has no AVB footer and a zeroed legacy hash area
  ([authentication check](../2026-07-15-display-console-write/results/boot-authentication-check-20260715.txt)).
- `boot_reason` 4 after reboots.

D5. **Earlier, July.** Every write to `boot`, from Gemian and from a mainline
boot, failed with `mmc_check_write: data error = -30, status=0x4000900`
([result](../2026-07-25-emmc-development/results/aw-to-primary-boot-protected-20260726.txt)).

D6. **Earlier, station 8.** A plain `poweroff` with the cable in came back up
by itself with the charging screen. A `poweroff` with the cable out stayed off,
and a later plug-in showed the charging screen
([station record](../2026-10-30-mainline-dev-station/README.md)).

## Analysis

- **Write protection matches the source exactly.** In D1, `seccfg` and
  `oemkeystore` through `keystore` are contiguous on this disk, which gives one
  run. The partition sizes from the capture end that run on sector 458751
  only if the partitions are packed in order, so the per-partition ranges on
  the hardware page are an inference with a strong check. In D3, mode 8 gives
  `seccfg` only and no boot-area protection, as S7 predicts.
- **D3 also shows** that a cold power-off and plug-in clears power-on
  protection, as eMMC power-on protection should. Whether a PMIC re-power
  with the cable in (D2, D6) or a warm reset clears it is not shown.
- **The July failure is explained.** Status `0x4000900` has bit 26 set, the
  eMMC's write-protect violation. Every mainline boot then was a normal-mode
  boot2 start, which protects `boot` (S1, S7).
- **T2 isn't diagnostic either way.** By S6 the logo appears in both modes,
  and by S1 an unheld side key loads `boot` in both. T2's restart could have
  been mode 0 or mode 8.
- **Verification.** D4 rules out unlocked, which would give orange, so the
  unit is locked and the `boot` policy doesn't verify; a passing signature on
  a Gemian-built kernel is unlikely. By S8 the same applies to every slot, so
  LK should accept our image on `boot` as on `boot2`. Only a boot from `boot`
  settles it.
- **Normal start without a charger.** S3 and S4, as written and as compiled,
  give recovery for Esc held during the window and power-off for Esc released
  with no flag. A normal Esc start works on the unit, so a flag must pass it:
  probably the RTC bypass bit set by the preloader. LK alone doesn't explain
  it. This doesn't affect the first-install route.
- **The DTB and the kernel come from separate key reads.** A release between
  them could pair one slot's DTB with another slot's kernel (S1, S2). This is
  an inference with no observed case.

## Conclusion

`confirmed`, for this unit and LK `75ec9f0b…`:

- LK chooses the slot from live PMIC key levels at three points, with the rule
  side+power `boot3`, side `boot2`, else `boot`, in every mode except
  recovery.
- Only a normal-mode start sets power-on protection on the boot area and on
  `oemkeystore` to `keystore`. Every mode protects `seccfg`.
- A side-key plug-in charging start is mode 8, loads `boot2`, and leaves
  `boot`, `lk`, `lk2`, `nvram` and the boot area writable.

Acceptance of our image on primary `boot` remains inferred.

## Follow-up

- The [LK hardware page](../../docs/hardware/lk.md) holds the durable facts
  and the open questions.
- Next read-only reading, one request to the custodian when a station is
  already up, with no power cycle: the station's
  `/sys/firmware/devicetree/base/chosen/bootargs` and
  `/sys/firmware/devicetree/base/firmware/android/mode`, with `serialno` and
  `androidboot.serialno` dropped. It gives the station's verified-boot state
  and LK's own command line for a boot2 start.
- The install design's T3 and T4 answer whether LK boots our image from
  `boot`.
