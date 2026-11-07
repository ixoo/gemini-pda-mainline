# Experiment: a persistent Arch Linux ARM root, systemd-native, on microSD first

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-06-gemini-arch-root` |
| Status | running: design agreed with the owner on 2026-11-06; step 1 tested in the VM, not booted |
| Subsystem | Root filesystem, boot handover, userland |
| Device variant | The project's development Gemini PDA |
| Date(s) | 2026-11-06 |
| Investigator(s) | Julien Etienne (owner decisions), Claude (design) |
| Tracking issue | [Roadmap step 1](../../docs/ROADMAP.md#1-after-v1), [v1 gaps 1, 4, 6, 10](../../docs/RELEASE_READINESS.md#known-gaps-in-v1) |

## Question or hypothesis

Can the mainline 7.1.3 kernel hand over from its boot image to a persistent
Arch Linux ARM aarch64 root, run by systemd, that keeps every boot-time
protection the [station](../2026-10-30-mainline-dev-station/README.md) has? The root
should join Wi-Fi with iwd, update with `pacman`, and start a sway session on
the panel, all without writing any eMMC partition.

This record is the design. Each part becomes true only when a numbered step
below runs and records its result here.

## Owner decisions (2026-11-06)

Earlier decisions for a first install still hold: it replaces Gemian, Arch is the
distribution, no SSH to start, and a disclosure takes the place of a backup.
Today's decisions:

| Topic | Decision |
| --- | --- |
| Base | The official Arch Linux ARM aarch64 tarball, checked against the pinned build-key fingerprint, plus this project's own packages on top |
| Kernel and modules | A `linux-gemini` package holds the boot image. The image's initramfs carries its own matching modules, and a pacman hook writes it to `boot2` with `flash-boot2` |
| Session | Graphical from the start: sway |
| Session start | Autologin of the first user into sway, with no password prompt |
| Access | One user in `wheel` with sudo, `root` locked, default `alarm`/`root` logins locked, no sshd until the owner installs one |
| Wi-Fi | iwd |
| Style | Stay systemd-native as much as possible |
| Development root | microSD, so that `linux` and Gemian stay untouched on this unit |

## Design

### Base and reproducibility

- **Base.** The installer, or the card builder during development, fetches the
  official ALARM aarch64 tarball and its `.sig`. It checks them with `gpgv`
  against the build-key fingerprint, which the card builder pins in step 2.
  - TLS doesn't carry the trust, since a mirror redirects to plain HTTP.
  - Arch Linux ARM keeps no dated archive, so the base can't be pinned by date.
  - The SHA-256 of the tarball used is recorded with each build.
  - The project never redistributes Arch binaries, so it owes no sources for them.
- **The project's layer is the reproducible part:** PKGBUILDs in this repository for
  `linux-gemini` (the boot image) and `gemini-base` (units, configuration, the sway
  setup). They are built from pinned inputs like the kernel is, and installed with
  `pacman -U` until a signed package repository is worth having.
- **Removed from the tarball:** `linux-aarch64`, `linux-firmware` and `mkinitcpio`. They
  go in `IgnorePkg`, since only boot-slot writes change the kernel.
- **Firmware.** The device's own files are copied to `/usr/lib/firmware/mediatek/mt6797/`,
  with no package owning them. They come from `firmware-get`, or from Gemian's `/vendor/firmware` at install
  ([firmware](../../docs/hardware/firmware.md)), and are never in a published image.

### Placement and handover

- **Root location.** The root is one GPT partition labelled `gemini-arch`, ext4, with
  the Discoverable Partitions root type for 64-bit ARM
  (`b921b045-1df0-41c3-af44-4c6f280d3fae`), so systemd's tools recognise it.
  - During development it's on the microSD card.
  - The [microSD slot](../2026-11-05-gemini-microsd/README.md) is built in, DT only,
    so stage 1 needs no module to see it.
  - Whether a later install puts the root on the card or on `linux` is decided
    after the card root has run. Stage 1 finds the root by label, so the image is
    the same either way.
- **Stage 1 stays the busybox init.** It is the station or release RAM root with one
  added branch, about 20 lines. A systemd initramfs was weighed and not chosen:
  - the boot partition is 16 MiB, with about 2.5 MB free today;
  - the busybox root is also the rescue system;
  - the charging-mode check and the key prompt have no systemd counterpart.

  systemd takes over at `switch_root`.
- **The branch, in order:**
  1. Do everything the station does today up to the root decision: guard and
     thermal status, and `nvdata` set read-only and mounted `ro,noload`.
  2. Set the eMMC and every partition on it read-only with `blockdev --setro`.
     While it writes, `flash-boot2` clears the disk's flag and `boot2`'s, then sets both
     again. The disk's flag alone keeps every partition read-only.
  3. In power-off charging mode (`atag,boot` mode 8), don't hand over. Stay in
     the RAM root ([LK behaviour](../2026-11-05-gemini-lk-behaviour/README.md)).
  4. Look for exactly one `PARTNAME=gemini-arch`. With none, or more than one,
     carry on as the station.
  5. Show a 3 s prompt on the console. Any key keeps the RAM root, as the rescue.
  6. Mount the root **read-only**. Mount a tmpfs holding this image's modules
     over `/usr/lib/modules`. Move `/nvdata` and `/run` into the new root. Then
     `switch_root` to `/sbin/init`.
  7. systemd's `systemd-fsck-root` and `systemd-remount-fs` check the root and
     remount it read-write, as they would on any Arch system.
- **Back to the station:** remove the card, or press a key at the prompt.

### Kernel, modules, updates

- **The boot image** comes from Buildbox, unchanged, holding kernel, DTB and an
  initramfs with this kernel's modules. The modules are always the ones the running
  kernel was built with, whichever slot started it.
- **Autoload.** `modules.alias` stays, so udev autoloads by device. A `modprobe.d`
  file in `gemini-base` blacklists every module that isn't proven at boot, so
  `modprobe` by hand still works: GPU, camera, A72, Bluetooth, GNSS, touch,
  sensors, the Wi-Fi trio and the display. That keeps "nothing loads at boot until
  proven".
- **Proven boot-time modules** load through `modules-load.d` (lid, LEDs, vibrator)
  or their own units below.
- **Kernel updates.** `pacman -Syu` installs a new `linux-gemini`. Its hook runs
  `flash-boot2` with the package's SHA-256, which includes the full readback.
  - The owner powers off and selects `boot2`.
  - Promotion to primary `boot` is a separate, later tool, outside standing
    approval ([install design](#follow-up)).
- **Kernel options to add,** in `configs/gemini-a53-station.fragment`, which both the station and
  release profiles use (`configs/gemini.fragment` serves only the `full` profile), batched
  with the stage-1 change:
  - for iwd: `CRYPTO_USER_API_HASH`, `CRYPTO_USER_API_SKCIPHER` and
    `KEY_DH_OPERATIONS`, all off in the station config today;
  - systemd's own requirements were checked earlier (cgroups, fhandle, inotify,
    signalfd, timerfd, epoll, autofs, tmpfs xattrs, seccomp, 4K pages);
  - IPv6 and netfilter stay off.
- **Release profile.** It has to gain the microSD DT patches before a published image
  can use a card root.

### Boot-time essentials, mapped

| Station today | In the Arch root |
| --- | --- |
| Charge guard (built into `bq25890`) | Unchanged, kernel. A oneshot logs its presence to the journal |
| Thermal trips, hardware reset | Unchanged, kernel |
| Left Type-C chip set to sink (`i2cset`) | Moves to the kernel through the usb-c work. The release config has no `/dev/i2c`, and the root shouldn't need it |
| `nvdata` read-only for Wi-Fi calibration | Stage 1 sets it read-only, mounts it, and moves it into the root |
| Wi-Fi modules and country | Built-in `cfg80211` can't take a country from module options under a forced command line. `gemini-regdom.service` runs `iw reg set` from Arch's `/etc/conf.d/wireless-regdom`, then `gemini-wifi.service` loads the three modules in order. iwd starts after them |
| Audio routes (`audio-start`) | `gemini-audio.service`, a oneshot running the same script. UCM later |
| Native display with the hang marker | `gemini-display.service` with the same marker, in `/var/lib/gemini`. sway waits for it |
| Lid (`gemini-lid`) | `modules-load.d`. `logind.conf.d` sets `HandleLidSwitch=ignore`, since there's no suspend and the kernel module already blanks the panel |
| LEDs, vibrator | `modules-load.d` |
| Keymap, console font, cursor | `vconsole.conf`, with the Gemini keymap shipped in `gemini-base`, and a `tmpfiles.d` line for the cursor |
| USB gadget address | `systemd-networkd`, `usb0` with the station's fixed address. No SSH server |
| Status file | The journal, persistent with a small size limit for the card, plus `systemd-pstore` for crash records |

### Userland

- **systemd components:**
  - systemd as init and journald;
  - networkd, resolved and timesyncd;
  - logind, udev, `modules-load.d` and `tmpfiles.d`;
  - `systemd-firstboot` for locale, timezone, keymap and hostname;
  - `systemd-pstore`.
- **Not from systemd, because it has no tool for the job:**
  - iwd, for WPA joins. Its address setup is off, so networkd configures `wlan0`.
    MAC randomisation is off as well, because the driver is unproven with it;
  - `iw`, for the country;
  - sudo;
  - sway with Mesa (Panfrost), and PipeWire and WirePlumber as user services;
  - pacman.
- **First boot** runs a `ConditionFirstBoot` unit on the console:
  1. `systemd-firstboot --prompt`;
  2. country;
  3. user name and password, with `useradd` into `wheel`;
  4. a Wi-Fi join with `iwctl`.

  systemd-homed was left out: its activation and autologin behaviour adds questions
  with no need behind them.
- **Session.** `gemini-session@USER.service` runs sway on `tty1` with `PAMName=login`,
  in place of the getty there, enabled for the first user. Other VTs keep a getty.
  - The sway config rotates the output to match `fbcon=rotate:3`, maps touch to the
    panel, and sets the Gemini keyboard layout. Each is checked by measurement on
    the panel, not by eye.
  - If Panfrost isn't loaded, sway falls back to `WLR_RENDERER=pixman`.
- **Updates:** `pacman -Syu` for everything, the project's packages included.

### Safety and recovery

- **Never written by the root or its tools:** preloader, `lk`, `nvram`, `nvdata`,
  `seccfg`, `proinfo` and other identity or calibration partitions, the GPT and
  the eMMC boot areas.
  - Stage 1 makes the user-area partitions read-only, and the kernel already keeps
    the boot areas `force_ro`.
  - This guards against mistakes, not against root deliberately undoing it.
- **Written:**
  - the root partition;
  - `boot2`, only by `flash-boot2` with full readback;
  - primary `boot`, only by the separate promotion tool, once it exists and is approved.
- **During development**, `linux` stays mounted read-only, as in the release image,
  and Gemian stays bootable.
- **Recovery, in order:**
  1. a key at the 3 s prompt keeps the RAM root;
  2. without the card, `boot2` is the station as before;
  3. the station can rewrite `boot2`;
  4. Gemian is still on the primary slot.
- **A no-SSH image leaves only the screen when it fails.** The project's own test
  images keep the station's SSH key argument, as the install design says.

## Provenance and environment

Nothing has been built. Each step records its kernel commit, profile, package
SHA-256, tarball SHA-256 and signature result when it runs.

## Safety assessment

This record is a design. Device steps go through the custodian, under the station's
standing `boot2` approval, and write only `boot2` and the microSD card. They don't
write primary `boot`, `linux` or any other eMMC partition.

## Procedure

First implementation steps, in order:

1. **Kernel and stage 1, one image.**
   - Add the three iwd options to `configs/gemini-a53-station.fragment`.
   - Add the handover branch to the station init, with the `setro` pass and the
     charging-mode check.
   - Teach `flash-boot2` to clear the read-only flags on the disk and `boot2` for the write.
   - Check with ShellCheck, then run init as PID 1 in the dev VM, as the release
     root was, with a loop image labelled `gemini-arch`.
   - One Buildbox build.
2. **Card builder, in the dev VM.** A script that:
   - fetches and checks the tarball;
   - makes a GPT image with one `gemini-arch` partition, ext4;
   - extracts it with `bsdtar`, keeping extended attributes;
   - locks the default logins and removes the kernel, firmware and mkinitcpio
     packages;
   - adds `gemini-base`.

   It contains no firmware and no keys.
3. **`gemini-base` package:** the units, configuration files and sway setup in the
   tables above, kept to what the station does today.
4. **Device step, through the custodian.**
   - Write the card from the station over USB SSH and hash it back.
   - Copy the device's firmware onto it.
   - Write `boot2` with step 1's image and power off. The owner selects `boot2`.
   - Observe, in order:
     1. stage 1 picks the card;
     2. systemd reaches the default target;
     3. no blacklisted module is loaded;
     4. the guard and thermal zones are present;
     5. an iwd WPA2-PSK join, then `pacman -Sy`;
     6. sway on the panel, with rotation and touch measured.
   - Remove the card and confirm the station comes back.
5. **`linux-gemini` package** and its `flash-boot2` hook, then one update cycle through it.
6. **Later, owner decisions:** card or `linux` for installs, the primary `boot`
   promotion tool, and the Gemian erase. These follow the
   [first-install design](#follow-up).

## Observations

### Step 1 result

**Changes:**
- [`configs/gemini-a53-station.fragment`](../../configs/gemini-a53-station.fragment) adds
  `CRYPTO_USER_API_HASH`, `CRYPTO_USER_API_SKCIPHER` and `KEY_DH_OPERATIONS`.
- The station's [`init`](../2026-10-30-mainline-dev-station/initramfs/init) gains the
  handover branch.
- [`flash-boot2`](../2026-10-30-mainline-dev-station/initramfs/flash-boot2) lifts the
  disk's read-only flag and its own for the write. It records which were set and sets them
  again on any exit.

ShellCheck is clean on both scripts.

**Dev VM, 2026-11-06.** Ubuntu's static busybox 1.36.1 stood in for the station's Alpine
one. A test copy of `init` ran as PID 1 of a new PID and mount namespace, in a chroot
on tmpfs:
- a loop device stood in for the eMMC, with GPT partitions `boot2`, `linux` (ext4) and
  `nvdata` (ext4), and `mmcblk0` replaced by its name;
- a second loop device stood in for the card, with one `gemini-arch` partition using the
  64-bit ARM root type and holding a stand-in root;
- the copy read the boot mode from a file and the key from a file, and stopped after the
  branch on the station's path.

| Case | Result |
| --- | --- |
| Normal start, no key | `arch=handover`. In the new root, as PID 1: `/` ext4 `ro` from the card, a tmpfs at `/usr/lib/modules` holding this image's modules, `/nvdata` `ro,norecovery`, and `ro=1` on the disk and all three partitions. A write to `linux` was refused. `flash-boot2` wrote `boot2`, and the readback matched. Every flag read `1` again afterwards, and a second run exited 0 |
| Key within 3 s | `arch=kept-ram-root`; `/mnt/data` still `rw`; no flags set |
| Boot mode 8 | `arch=refused boot-mode=8`; nothing changed |
| Two `gemini-arch` partitions | `arch=refused count=2`; nothing changed |
| Root without `/sbin/init` | `arch=refused no-init`, then `station-continues`: eMMC read-only, `/mnt/data` remounted `ro,norecovery` |
| No card | `arch=none` after 1 s; nothing changed |

The first `flash-boot2` version cleared only `boot2`'s own flag. With the disk's flag still
set, `boot2` stayed read-only on the VM's 6.8 kernel and the write was refused. Hence the
change above.

On the station's normal path, with no flags set, `flash-boot2` still wrote, verified,
left every flag at `0`, and refused a wrong checksum.

**Buildbox, 2026-11-06.**
- **First build, `aa40fb18`:** stopped at configuration. The AF_ALG options select
  `CRYPTO_USER_API`, which `gemini-usbdiag.fragment` asks to be off, and the profile
  check enforces each symbol's last request.
- **Fix, `32e00098`:** names `CRYPTO_USER_API=y` in the station fragment.
- **Rebuild of `mt6797-a53-station-a72` with `BUILD_MODULES=1`:** validated. Job
  `32e00098…-mt6797-a53-station-a72-m1`, package `linux-7.1.3-gemini-3b7c38d2…`,
  config `8b1dc525…`, `Image.gz` `b8309b93…`, `hardware_write=none`.
- **Resolved config:** `CRYPTO_USER_API`, `_HASH`, `_SKCIPHER`, `KEY_DH_OPERATIONS` and
  `CRYPTO_DH` are `=y`. `MMC_MTK` is built in and `I2C_CHARDEV` stays on for the station.
- **Not fetched:** `fetch-package` only follows HEAD, which has moved on, so the image is
  built again from HEAD when step 4 composes it.
- **Not built:** the release profile, which shares the fragment.

**Not tested:**
- the real eMMC, card detection timing and the console key on the device;
- the station's own busybox;
- a real systemd behind `switch_root`.

## Analysis

Not started.

## Conclusion

Not started.

## Follow-up

- The first-install design, kept privately for now: placing the root on `linux`
  by erasing Gemian, and promoting a tested image from `boot2` to primary `boot`
  through the power-off-charging start. Its T1 and T2r reads, which wrote nothing,
  found `boot` unprotected in that mode on this unit.
- The left Type-C chip's sink mode belongs in the kernel, with the usb-c work.
- The [support matrix](../../docs/HARDWARE_SUPPORT.md) changes only once step 4
  has a result.
