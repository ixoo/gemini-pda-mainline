# Experiment: a persistent Arch Linux ARM root, systemd-native, on microSD first

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-06-gemini-arch-root` |
| Status | running: design agreed with the owner on 2026-11-06; steps 1 to 3 done in the VM and on Buildbox; R1 (2026-11-07) handed over to the card and ran systemd, then stopped in the stock first-boot prompt on the serial console; R2 reached sway on the panel, then hit the stop rule: `nvdata`'s hash changed, cause unknown, card boots stopped; the owner chose to continue; R3 got iwd up but no join (the driver refuses iwd's key order), no bar, and no Gemini keymap in sway; R4 joined with iwd, but the setup console's keymap differed from sway's |
| Subsystem | Root filesystem, boot handover, userland |
| Device variant | The project's development Gemini PDA |
| Date(s) | 2026-11-06 to 2026-11-07 |
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
  with no package owning them, by [`gemian-firmware`](gemian-firmware) from the owner's
  Gemian system ([firmware](../../docs/hardware/firmware.md#the-set-the-card-root-carries)).
  They are never in a published image.

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
     over `/usr/lib/modules`. Move `/run` into the new root, and `/nvdata` only into
     a root that has that directory (since `gemini-base` 10, the card root doesn't). Then
     `switch_root` to `/sbin/init`.
  7. systemd's `systemd-fsck-root` and `systemd-remount-fs` check the root and
     remount it read-write, as they would on any Arch system.
- **Back to the station:** remove the card, or press a key at the prompt.

### Kernel, modules, updates

- **The boot image** comes from Buildbox, unchanged, holding kernel, DTB and an
  initramfs with this kernel's modules. The modules are always the ones the running
  kernel was built with, whichever slot started it.
- **Autoload.** `gemini-modules.service` runs `depmod` on the tmpfs, then removes
  `modules.alias`. udev then loads nothing by device, while `modprobe` by name and
  `modules-load.d` still work. That keeps "nothing loads at boot until proven", as on
  the station. It replaces the first design's `modprobe.d` blacklist, which would
  have needed a list of every unproven module and kept up to date (step 3).
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
| `nvdata` read-only for Wi-Fi calibration | Not mounted (owner, 2026-11-07): card preparation copies the Wi-Fi record into the root's firmware directory, and the root has no `/nvdata` |
| Wi-Fi modules and country | Built-in `cfg80211` can't take a country from module options under a forced command line. `gemini-wifi.service` runs `iw reg set` from Arch's `/etc/conf.d/wireless-regdom`, waits to see it applied, then loads the three modules in order. With no country it stays off. iwd starts after it |
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
- **First boot** runs `gemini-firstboot.service` on the console. It's gated by a marker in
  `/var/lib/gemini`, so an interrupted run asks again:
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
     3. no module loaded but those the units and `modules-load.d` load;
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

### Step 2 result

**[`build-card.sh`](build-card.sh), run as root in the dev VM:** `build-card.sh CACHE OUT [SIZE]`.

**What it does:**
- Fetches the official tarball and its `.sig` over HTTP.
- Fetches the build key by its pinned fingerprint `68B3537F…52BDBE6A6`, refuses any other
  fingerprint, and checks the tarball with `gpgv`. The project's
  [signing page](https://archlinuxarm.org/about/package-signing) lists that key as
  "Arch Linux ARM Build System".
- Makes a sparse GPT image with one ext4 partition named `gemini-arch`, of the
  64-bit ARM root type, and extracts the tarball there with `bsdtar -xp`.
- In a chroot:
  - removes `linux-aarch64`, every `linux-firmware*` package and `mkinitcpio*`, and adds
    them to `IgnorePkg`;
  - runs `pacman -Syu` with `iwd`, `iw`, `wireless-regdb` and `sudo`.
- Locks root, removes the `alarm` user, and disables and masks `sshd`.
- Writes `uninitialized` to `/etc/machine-id`, adds `/nvdata`, `/usr/lib/modules` and a
  root `fstab` line.
- Records every checksum in `card.json`.

**Why packages are added.** The tarball has none of the Wi-Fi tools, and Wi-Fi is the
root's only way to its packages. The full upgrade avoids a partial upgrade. pacman checks
the packages against a keyring in `/run`, so the image ships no keyring and the first boot
makes its own.

**Run, 2026-11-06:**
- tarball `42a4eeaa…`, 829,367,415 bytes, good signature from the build key;
- 15 packages removed, 155 installed, systemd 262.1, iwd 3.12, wireless-regdb 2026.09.03;
- 0.80 GB used in a 4 GiB image;
- image `b7430bc5…`, kept in the VM. It isn't published: it holds no firmware or keys, but it
  redistributes Arch binaries.

**Read back from the image:**
- the partition type and label are as above;
- root reads `!`, no user has a UID of 1000 or more, and there's no keyring;
- `sshd` links to `/dev/null` and isn't wanted by any target;
- the machine-id is `uninitialized`;
- `/sbin/init` resolves to systemd;
- the package cache, `/usr/lib/firmware/mediatek` and `/usr/lib/modules` are empty;
- `e2fsck -fn` is clean.

**A mistake on the way, in the VM only.** An earlier version deleted its work directory
while the chroot's bind of the VM's `/dev` was still mounted: pacman-key's gpg-agent held
it busy. That deleted the VM's device nodes. No disk data was lost, and a VM restart
restored them. The script now:
- binds `/dev` and `/sys` as slaves;
- stops gpg in the chroot;
- removes the work directory only when nothing is mounted under it.

The run above left the VM's `/dev` at 196 entries before and after, with no mount or loop
device remaining.

**Not tested:** the image on a card or the device; anything at first boot, from the keyring
and user to iwd.

### Step 3 result

**The [`gemini-base`](gemini-base/PKGBUILD) package**, `arch=any`, MIT. It contains:
- `gemini-modules.service`: `depmod`, then no alias index;
- `modules-load.d` entries for the lid, LEDs and vibrator;
- `gemini-audio.service` running the station's own `audio-start`;
- `gemini-display.service` running `display-start` behind the station's hang marker,
  now in `/var/lib/gemini`;
- `gemini-wifi.service` with the country gate;
- networkd files for `usb0` (the station's fixed address) and `wlan0` (DHCP);
- iwd set to leave addresses to networkd, with MAC randomisation off;
- `logind.conf.d` setting the lid switch to `ignore`, and `journald.conf.d` making the
  journal persistent at 64M;
- `vconsole.conf` with `KEYMAP=us`, a wheel sudoers file, and the `WIFI.storage` link
  into `/nvdata`;
- a sway drop-in rotating the output 270° and mapping touch to it;
- `gemini-session@.service`: sway on `tty1` with `PAMName=login` and software rendering
  until Panfrost loads at boot;
- `gemini-firstboot.service`, which:
  - initialises the pacman keyring;
  - creates one user in `wheel` with a password;
  - asks for the Wi-Fi country and offers an `iwctl` join;
  - then enables that user's session and the graphical target.

It depends on `kmod`, `alsa-utils`, `iwd`, `iw`, `wireless-regdb`, `sudo`, `sway`, `foot`
and `ttf-dejavu`.

**`build-card.sh` builds and installs it.** It stages the station's `audio-start` and
`display-start` beside the PKGBUILD, so each script keeps one copy. It builds with
`makepkg` as `nobody`, using `fakeroot` that is installed for the build and removed, and
installs with `pacman -U`. It then enables the units and `iwd`, plus `systemd-pstore`, and
sets `multi-user.target` until the first boot finishes.

**Run, 2026-11-06:** `gemini-base` `03cad732…`, 235 packages, 1.27 GB used, image
`855cc1d0…`. The VM's device nodes were intact afterwards, and no mount or loop device
was left behind.

**Container boot**, `systemd-nspawn -b` of a copy of the previous image (`7525afd5…`), in
the VM:
- systemd 262.1 came up `degraded`, with these failures:
  - `gemini-display`, because the container has no modules. Fixed by the condition above,
    then rebuilt;
  - `gemini-firstboot`, because there's no `/dev/tty1` in a container;
  - `systemd-remount-fs`, because there are no block devices in a container, so
    `PARTLABEL=gemini-arch` didn't resolve.
- `systemd-analyze verify` passed on every `gemini-*` unit.
- logind reported `HandleLidSwitch=ignore`, journald read `Storage=persistent` and
  `SystemMaxUse=64M`, `visudo -c` passed, and the `WIFI.storage` link was in place.

**A wrong image hash, found before R1.** `855cc1d0…` above didn't match the file
afterwards. The card's mount had propagated into the mount namespaces of the VM's
long-running services (udevd, resolved, logind and others). Making the `/dev` and `/sys`
binds slaves then stopped our unmounts from reaching those copies. The copies kept the
loop device attached, and its last writes reached the file after the hash.

`build-card.sh` now:
- runs in a private mount namespace (`unshare --mount --propagation private`);
- flushes and waits for the detach, recording `detach_wait_s`;
- hashes the image twice, two seconds apart.

The rebuild gave `detach_wait_s` 0 and image `79c921e3…`, unchanged 30 s later, with no
process holding a mount of it. Images `7525afd5…` and `855cc1d0…` aren't used.

**Not tested:**
- anything with the hardware: the modules, audio, display, Wi-Fi and the sway session;
- the first-boot dialogue, which needs a console;
- whether `systemd-remount-fs` resolves the label on the device and remounts the root
  read-write, and whether `systemd-fsck-root` runs;
- whether `systemd-firstboot` also prompts.

Step 4 answers these.

### Step 4, R1 (predeclared): the first boot of the card root

**Candidate.**
- **Kernel:** the Buildbox package of `mt6797-a53-station-a72` with `BUILD_MODULES=1`, built at
  the commit that adds this section. It holds the iwd options, and HEAD's station `init`
  and `flash-boot2`.
- **Boot image:** composed by `compose-station.py` as for any station image, with the
  project's SSH key, since the station path stays the evidence path.
- **Kernel package:** job `f60e405e…-mt6797-a53-station-a72-m1`, package
  `linux-7.1.3-gemini-2fb41787…`, `Image.gz` `1cb93a0e…`, config `8b1dc525…`. It is
  fetched under `artifacts/buildbox/f60e405e…/`. Nothing the composer reads changed
  after `f60e405e`.
- **Card image:** `79c921e3…` (`gemini-base` `bb075b3a…`, 235 packages), in the dev VM at
  `~/artifacts/arch-card-2/`, from `build-card.sh` as committed with this change.
- **Changed before the boot (2026-11-07): the P5 image instead.** boot2 already holds
  `station-work-77`, boot2 `93873a03…`, built from `eea46408` for the
  [power record's P5](../2026-11-06-gemini-power-management/README.md#p5-2026-11-07-06330635-on-a-built-image)
  and booted there as `ae534d13`. Between `f60e405e` and `eea46408` nothing changed in the station's
  `initramfs/`, its build and compose scripts or `configs/`, so it has the same `init` with the
  handover and the same config `8b1dc525…`. Its package `linux-7.1.3-gemini-86631330…` holds every
  module the card's units load. It adds patches 0632–0635 (MTU3 suspend and reconnect, the
  regulator late cleanup), tested on the device in P5. So step 7 writes nothing: it is only the
  `poweroff`, and the budget has no boot2 write.

**Hypothesis.** On a normal start with the card in, stage 1:
1. shows the prompt and, with no key pressed, hands over (`arch=handover`);
2. sets the eMMC and its partitions read-only and mounts the card read-only.

Then systemd 262:
1. remounts the root read-write;
2. runs `gemini-modules`, the three `modules-load.d` modules, `gemini-audio` and
   `gemini-display`;
3. runs the first-boot dialogue on `tty1`;
4. with a country set, starts the Wi-Fi so that iwd joins as WPA2-PSK and `wlan0` gets an
   address;
5. starts sway on the panel.

Throughout, nothing writes the eMMC.

**The unique observation.** No mainline boot has yet run systemd, a persistent root or iwd.

**Before, on the running station:**
1. Confirm stable power.
2. The owner confirms that the card in the slot can be erased, and that it is at least
   4 GiB.
3. Check that `/dev/mmcblk1` resolves under `11240000.mmc`, is at least 4 GiB, and isn't
   mounted.
4. Send the card image gzip-compressed over USB SSH, and write it with `dd` and `sync`.
   Read the first 4 GiB back and require the image's SHA-256.
5. Mount `mmcblk1p1` read-write and run [`gemian-firmware`](gemian-firmware)
   `/mnt/data/data/system.img` on it, which copies the six files and checks each hash. Record
   its output, then unmount.
6. Record SHA-256 of `boot`, `boot2`, `lk`, `nvram`, `nvdata` and `proinfo`, by GPT name
   and read-only.
7. Write the boot image with `flash-boot2`, then `poweroff`. The owner selects `boot2`
   with the card in. With the P5 image already on boot2 (see Candidate), only the `poweroff`.

**On the device, the owner:**
1. Leaves the 3 s prompt alone.
2. Answers the first-boot questions: a user name and password, the country, and a join
   to their usual WPA2 network with `iwctl`.
3. Photographs the panel at the prompt, at the end of the boot messages and once sway is
   up. Colour isn't judged.
4. In sway, opens a terminal (Mod+Enter) and runs `sudo poweroff`.

**After, on the station.** Boot `boot2` again and press a key at the prompt, which keeps
the RAM root. Then:
1. Repeat the hashes of step 6.
2. Mount the card read-only and copy `/var/log/journal`, `/var/lib/gemini` and
   `/etc/machine-id`.
3. Read `/sys/fs/pstore`.

The journal stays private and is read on the laptop with `journalctl --file`. Anything
quoted publicly drops every line naming a network or an address.

**Readings.**

| Observation | Reading and next |
| --- | --- |
| `arch=` other than `handover` | Stage 1 refused; its reason is in the status file. Fix stage 1 |
| Prompt, then no systemd output, or a restart after `panic=10` | `switch_root` or systemd start. pstore and the console photo decide |
| systemd up, root still read-only | `systemd-remount-fs` didn't resolve `PARTLABEL`: use the device path or a stage-1 remount |
| First boot done, no sway | Display or session. The journal says which unit |
| sway up, no join | iwd on our driver. The journal's iwd and kernel lines decide whether to fall back to wpa_supplicant |
| Any eMMC hash changed | Stop. Something wrote through the read-only flags |

**Budget.** One `boot2` write (none with the P5 image) and one card write. Up to two card boots, then one station
boot for the evidence. No retries of an identical artifact.

**Stop rules.** Stop on heat, a charging anomaly, an Oops or a watchdog loop.

### R1 result (2026-11-07): handover and systemd, then a prompt on the serial console

Run by the custodian. The private evidence (journal, `machine-id`, logs) is kept outside Git.

**Before.**
- Station boot `ae534d13`, the P5 image (`station-work-77`, boot2 `93873a03…`), stable USB power.
- Card: 1430 GiB SD on `11240000.mmc`, not mounted; the owner confirmed it could be erased. Write
  rc 0; the 4 GiB readback is `79c921e3…`, matching; one partition, `gemini-arch`.
- `gemian-firmware` from `0a39b7be`: exit 0, six files copied, `gnss_dsp_6797.bin` 61,546 bytes,
  `WIFI.storage` a link to `/nvdata`.
- eMMC by GPT name, read-only: `boot` `1fa78de9…`, `boot2` `93873a03…`, `lk` `75ec9f0b…`, `nvram`
  `3db493b4…`, `nvdata` `3e095b0a…`, `proinfo` `56de3103…`.

**Card boot, observed.** The owner selected `boot2` with the card in and left the prompt alone. The
panel showed stage 1's handover line and nothing after, and no key did anything. The device answered
ping on its USB address and port 22 was closed, as designed. The owner held the power key. No photos.

**Evidence boot `bfeee4e3`** (key pressed): `arch=kept-ram-root`; all six eMMC hashes identical to
before; `/sys/fs/pstore` empty; `/var/lib/gemini` absent.

**Journal** (one boot, 2,319 lines, ending at 19.2 s):
- 6.47 s "Detected first boot", since `machine-id` is `uninitialized`. 7.03 s "Applying preset
  policy", then 29 "Failed to preset all unit" lines, nearly all "Read-only file system": the root
  is still the read-only mount stage 1 handed over.
- 8.90 to 9.42 s `systemd-remount-fs`; `fsck` reports the root clean. So `PARTLABEL` in fstab
  resolved, and the root went read-write.
- `systemd-modules-load` inserted `gemini_lid`, and failed to find `pkcs8_key_parser`, from iwd's
  `modules-load.d`. `depmod` warns that the copied `/lib/modules` has no `modules.order`,
  `modules.builtin` or `modules.builtin.modinfo`.
- 10.41 s the cfg80211 udev rule's `set-wireless-regdom` exited 1 (no country in its file yet).
- 10.55 s "Starting Initial Setup": Arch's `systemd-firstboot.service`, enabled in
  `sysinit.target.wants` by the systemd package, with `ConditionFirstBoot=yes`. It prompts for
  locale, keymap, time zone and root password on `/dev/console`, which is `ttyS0` from the forced
  command line, and mutes the console meanwhile. It never finished.
- `usb0` came up from `50-gemini-usb0.network`; networkd and resolved ran.
- After 12.23 s only kernel lines: `sysinit.target` never completed, so no `gemini-*` unit, getty,
  iwd or sway started. The keyboard had probed at 1.26 s; nothing read `tty1`.

**Reading.** Stage 1, the read-only eMMC, the handover and the root remount all work. The stop is
not in the table: it is closest to "prompt, then no systemd output", but the cause is the stock
`systemd-firstboot` waiting for answers on the serial console ahead of `sysinit.target`. The
container test in step 3 had no console to block it, so it didn't show this. Nothing wrote the eMMC.

**Next fixes for the card builder (R2).**
1. Mask `systemd-firstboot.service`. `gemini-firstboot` already asks for what this device needs
   on `tty1`, and the root stays locked.
2. Ship `modules.builtin`, `modules.builtin.modinfo` and `modules.order` with the modules stage 1
   copies, so `modprobe` knows a built-in from a missing module; then check whether
   `pkcs8_key_parser` is built in or only absent.
3. The first boot's preset pass runs before the remount, so it fails and leaves the units as
   the builder enabled them. Decide whether that is acceptable, or whether the builder applies
   presets itself. A bare `preset-all` is not that: Arch's default preset disables every unit
   not listed, the gemini units included, so it would need a `gemini-base` preset file.

**Budget used:** one card write, one card boot, one evidence boot, no boot2 write. The second card
boot in the budget needs a new card image, so it is not a retry of an identical artifact.

### Step 4, R2 (predeclared): the panel as the console

**What changed since R1.**
- **Kernel command line:** `console=tty1` after `console=ttyS0`, in
  `gemini-a53-station-a72.fragment` (`44bc7705`), on the owner's choice. `/dev/console` is
  the last one named, so systemd's status, the emergency and rescue shells and any prompt
  go to the panel; kernel messages at `loglevel=4` go to both. The station's own services
  already name `tty1` or log to the kernel log; nothing there writes to `/dev/console`.
  The release profile keeps its own line.
- **Card:** the builder masks `systemd-firstboot.service`, and `gemini-firstboot` asks for
  the time zone itself through `systemd-firstboot --prompt-timezone` on `tty1`
  (`51bb5d45`, `gemini-base` 2). Arch's own unit was the only enabled one that waited on
  a console; the R1 image was scanned for every unit with `ConditionFirstBoot` or tty input.

**Candidate.**
- **Kernel:** Buildbox, profile `mt6797-a53-station-a72`, `BUILD_MODULES=1`, at `44bc7705`.
  It is P5 plus the command line and `0636`, the GNSS DSP boot in the `gnss-mt6797` module,
  which nothing loads at boot. Job `44bc7705…-mt6797-a53-station-a72-m1`, package
  `linux-7.1.3-gemini-1c6af8ff…`, `Image.gz` `540278a7…`, config `f6b79a90…`, fetched under
  `artifacts/buildbox/44bc7705…/`. The config differs from P5's `8b1dc525…` only in
  `CONFIG_CMDLINE`, and the package holds every module the card's units load.
- **Boot image:** composed by the custodian as for the current station images (a72 tree,
  same parent, project key), then written with `flash-boot2`.
- **Card image:** `0b2487341eb62044d4331e0a4928f94b78734773f68b3065ac76109bbc11e75e`, from
  `build-card.sh` at `51bb5d45`, `gemini-base` `742b5531…`, 235 packages, systemd 262.1,
  in the dev VM at `~/artifacts/arch-card-3/`.

**Container boot of the card image** (`systemd-nspawn -b`, a copy, no console input, 90 s):
`systemd-firstboot.service` is linked to `/dev/null`; `sysinit.target`, `basic.target` and
`multi-user.target` were reached; nothing waited on the console. `gemini-firstboot` failed
only because a container has no `tty1`. The container didn't count it as a first boot, so
this doesn't show the first-boot path.

**Hypothesis.** As R1 up to the root remount. Then:
1. systemd's status lines appear on the panel after stage 1's handover line;
2. `sysinit.target` completes;
3. `gemini-firstboot` asks on the panel for the time zone, a user and password, the country
   and a join; systemd holds its status lines while it runs, because `tty1` is the console;
4. iwd joins as WPA2-PSK and `wlan0` gets an address;
5. sway starts on the panel.

Throughout, nothing writes the eMMC.

**The unique observation.** No mainline boot has yet had the panel as `/dev/console`, and
none has completed systemd's first boot.

**Before, on the running station:** R1's steps 1 to 6, with the new card image and
`gemian-firmware` from main. Step 7 writes the new boot image with `flash-boot2`, then
`poweroff`; the owner selects `boot2` with the card in.

**On the device, the owner:** as in R1, plus the time zone question, which shows a paged
list of zones. Photos of the panel at the prompt, during systemd's messages, and once sway
is up.

**After, on the station:** as in R1. Also confirm on the evidence boot that the station's
own `tty1` shell and USB SSH still work with the panel as the console, since that boot runs
the same kernel.

**Readings.**

| Observation | Reading and next |
| --- | --- |
| No systemd lines on the panel after the handover | `/dev/console` didn't move: check the booted command line, then the journal |
| systemd lines, then a stop before the first-boot dialogue | Another unit waits; the journal names it |
| Dialogue garbled by status lines | systemd didn't treat `tty1` as the console: give `gemini-firstboot` `TTYPath=/dev/console` |
| First boot done, no sway | Display or session; the journal says which unit |
| sway up, no join | iwd on our driver; decide on a wpa_supplicant fallback from the journal |
| Station shell or SSH broken on the evidence boot | The console move affects the station: revert `44bc7705` for the station, keep it for the card |
| Any eMMC hash changed | Stop. Something wrote through the read-only flags |

**Budget.** One `boot2` write and one card write. Up to two card boots, then one station
boot for the evidence. No retries of an identical artifact.

**Stop rules.** As R1: heat, a charging anomaly, an Oops or a watchdog loop.

### R2 result (2026-11-07): first boot on the panel, then a stop on `nvdata`

Run by the custodian, with the owner at the device. Private evidence (journal, photos, `nvdata`
images, logs) is kept outside Git.

**Identities.**
- Before: station boot `bfeee4e3` (P5); card rewritten and firmware copied in that boot.
- Card boot: journal boot `01f49ad0…`, about 466 s, shut down from sway with `poweroff`.
- After: station boot `4407aa68`, image `station-work-79` (boot2 `e79a334a…`), booted command line
  with `console=ttyS0,921600n8 console=tty1`. `arch=kept-ram-root`; USB SSH and a shell work.

**Observed on the card boot.**
- The first-boot dialogue ran on the panel, sway came up, a foot terminal opened with Fn+Enter and
  typing worked. So `/dev/console` on `tty1` and the masked `systemd-firstboot` did what R2 asked.
- Wi-Fi failed. `iwctl` waited for iwd until the owner interrupted it. iwd started three times; each
  time it logged "Module rfkill failed to start: -2", then "D-Bus disconnected, quitting". Also,
  `gemini-wifi.service` had already run at boot with no country (`off-no-country`), so first boot's
  `systemctl start` of it did nothing: it needs a restart once the country is written.
- foot warned that `C` is not a UTF-8 locale. The bar clock was wrong (no network to set it).
- The owner: the interface is far too small, and the bar would be better as a side column. Done in
  `9134421f` (scale 2, waybar on the left, `LANG=C.UTF-8`, a first-boot note that Mod is Fn).

**eMMC hashes, before → after.** `boot`, `lk`, `nvram`, `proinfo` unchanged; `boot2` changed by the
intended `flash-boot2` write; **`nvdata` changed**, `3e095b0a…` → `67981430…`. That is a stop rule:
no card boot until it is understood. R1 had the same procedure without the console change, the
boot2 write and the Wi-Fi start, and `nvdata` was unchanged across it.

**What was checked.**
- **Files are intact.** Mounted `ro,noload` and compared with the July backup, only one modem record
  differs, last changed by Gemian on Nov 5; the Wi-Fi and Bluetooth records match July.
- **No read-write mount of `nvdata`.** The superblock's last mount and write are still Nov 6 12:20,
  mount count 9, from before the before-hash. The card journal shows one mount, by stage 1 at 5.02 s,
  "ro without journal", after `setro`, and systemd's unmount at 466.37 s. No fsck, trim, `tune2fs` or
  `blockdev` of `mmcblk0` appears. Two images of `nvdata` within boot `4407aa68` are identical.
- **Not a trim through ext4:** in 7.1.3, `FITRIM` returns `-EROFS` on a `noload` mount with a journal.
- **Not ext4's unmount, as far as the source shows:** `ext4_put_super` commits the superblock only on a
  read-write mount; on a read-only one it only syncs the block device. R2 was, though, the first time
  a mainline kernel unmounted `nvdata`: the station never does, and R1 ended on the power key.
- **The read-only flag is not a barrier against the kernel.** In 7.1.3 `bio_check_ro()` prints "Trying
  to write to read-only block-device" once per device and lets the write through. The flag refuses
  opening the device for writing and a read-write mount, and stops ext4's orphan cleanup; a write the
  kernel itself issues still lands. The card's kernel log has no such warning while journald ran,
  which leaves the last seconds of shutdown and the station boots unlogged.
- **The July backup can't localize it.** The 79 blocks that differ from July are the superblock, inode
  table blocks, the journal (inode 8) and one file's data, which Gemian's own use since July explains.
  Without an image from before R2, the changed bytes can't be told apart.

**Reading.** The cause is unknown. New in R2 were the `console=tty1` kernel, the Wi-Fi start on the
card, iwd, and a clean systemd shutdown that unmounted `nvdata`; the `flash-boot2` write also lifted
the disk's read-only flag on the before boot. Calibration and records read the same as July.

**Corrections to this record.**
- The Safety section's read-only flags guard against userspace mistakes only, as it says; they don't
  stop the kernel, so "nothing wrote the eMMC" can only come from the hashes.
- The station's stage 1 mounts `linux` read-write, replaying its journal, before the handover, and
  unmounts it. The card root never sees it, but "`linux` stays read-only" holds only after stage 1.

**Next, for the owner to decide.** First localize, then change the design:
1. Image all of `nvdata` (32 MiB, private) before and after each step, and compare, so the bytes and
   the step are known.
2. Station only: two boots of `station-work-79` with images between, to rule its kernel and the
   station's shutdown in or out.
3. Then one card boot with the same images, Wi-Fi off, then one with Wi-Fi.
4. Whatever the cause: stage 1 can copy the 514-byte Wi-Fi record into RAM and unmount `nvdata`
   before the handover, so the card root never mounts it.

**Budget used:** one card write, one boot2 write, one card boot, one evidence boot.

**Localized (2026-11-07, custodian).** The only byte that changed is the ext4 superblock's
`s_mnt_count`, at partition offset 1076: 7 before R2, 9 after. Writing 7 back into the after image
gives exactly the before hash. `s_mtime`, `s_wtime` and `s_kbytes_written` are unchanged;
`s_max_mnt_count` is 10. Station-only boots of `station-work-79`, imaged each time: `4407aa68` 9,
`32368f26` 10, `ed8a4c32` 10.

| Boots | Image | Count |
| --- | --- | --- |
| R1: `ae534d13`, the card boot, `bfeee4e3` | P5 (`station-work-77`) | 7, unchanged |
| R2 card boot, `4407aa68`, `32368f26` | `station-work-79` | 8, 9, 10 |
| `ed8a4c32` | `station-work-79` | 10: stops at the maximum |

**Reading.** It fits one increment per boot of `station-work-79`, up to `s_max_mnt_count`, and none
for P5. The two images' RAM roots are identical apart from modules, and their board trees are
identical, so the kernel is the difference: the `console=tty1` command line and the `gnss-mt6797`
module from `0636`. But Linux's ext4 isn't a fit for the writer: it raises the count only on a
read-write mount, always with `s_mtime`, commits `s_kbytes_written` with it, and doesn't stop at the
maximum; every mount here was read-only on a read-only device, with no warning logged. The writer is
not identified. Since the count now sits at the maximum, the same writer would no longer show, so
another boot can't localize it further by this byte. Gemian's next boot will see the maximum and
check the file system itself, as it does whenever the count is reached.

**Further checks (2026-11-07).**
- LK and the preloader (bootloader session, offline): no ext4 superblock or mount-count handling;
  `nvdata` appears only in LK's partition table, and nothing there writes it.
- Not loaded at boot in `station-work-79`: `gnss-mt6797`. No kernel line names `mmcblk0p6` but the
  read-only mount in the station boots, though two of those logs were kept only as a grep.
- The card's fstab names only its own root, it has no mount unit for `nvdata`, and its journal
  shows only stage 1's read-only mount and systemd's unmount at shutdown.
- In the dev VM (kernel 6.8), on a private copy with the count set back to 7: three `ro,noload`
  mounts on a read-only loop device and one on a writable one leave the image byte-identical; one
  read-write mount raises the count to 8, sets the mount time and replays the journal. The device
  shows the count alone, so not a Linux read-write mount.

**Open, unexplained.** The writer of `nvdata`'s `s_mnt_count` is not identified. File data and
calibration are intact.

**Owner decision (2026-11-07):** "Let's take a note of it and keep going." Card iterations
continue. The owner then dropped the proposed before/after copies of `nvdata`: "don't bother taking
a copy of nvdata." The six eMMC hashes stay as before.

**Later (2026-11-07), before R5's card boot.** `nvdata` changed again with no card or Gemian boot
in between: the mount count went back to 1, and the last-check, mount and write times were set,
with about 8 KiB written. The custodian placed it about 2 s into station boot `56dc88a8`, when
station init mounts `nvdata`; no kernel log of that boot was kept. The station's RAM root has no
`e2fsck`, `tune2fs` or `fsck` (its busybox carries only `mke2fs`), and Linux ext4 sets the
last-check time only through the tuning ioctl `tune2fs` uses. The times read as 2094, today plus
exactly 68 years: the offset between a 1900 and a 1968 year base in the MT6397 RTC, so the clock
that wrote them likely read 1968-based. Inference only; the writer is still not identified.

**Owner decision (2026-11-07), relayed by the custodian:** the card root never mounts `nvdata`.
Card preparation copies the 514-byte Wi-Fi record into the card's firmware directory as
`WIFI.storage`, a private regular file (mode 0600), with `gemian-firmware SOURCE ROOT RECORD`
on the station. The card root has no `/nvdata`, and
stage 1 mounts `nvdata` into a root only when that directory exists, so station init is unchanged.
`gemini-base` 10 drops the link, and `gemini-wifi.service` waits for the copied record instead of
the mount. Then the owner chose the station side too ("Stop mounting it"): stage 1 mounts `nvdata` only to
copy the record into RAM, unmounts it, and no longer mounts it into a card root
([station record](../2026-10-30-mainline-dev-station/README.md#nvdata-is-mounted-only-to-copy-the-wi-fi-record-2026-11-07)).
`RECORD` on the station is that RAM copy, `/lib/firmware/mediatek/mt6797/WIFI.storage`.

**The writer runs before the station's Linux (2026-11-07).** `station-work-82` (`boot2` `7ac0369f`, boot
`2262f250`) worked as intended: `nvdata=record-copied`, `nvdata=unmounted`, no `nvdata` in
`/proc/mounts`, the device read-only, and the kernel log shows only the read-only mount without
journal at 2.396 s and its unmount at 2.412 s. Yet `nvdata` changed between boot `10db4660` and this
one (`7c925690…` → `c87107d7…`): mount count 1 → 2, mount and write times set, last-check time
unchanged. The times read 2094-11-07 19:14:31, 2026-11-07 19:14:31 UTC less the 68-year offset.
This kernel started at 19:14:49.9 UTC (RTC time less uptime), so the write came about 19 s before
Linux started, while the owner was selecting `boot2`. Linux only mounted read-only, on a read-only
device. Private evidence: `station-work-82/boot-2262f250-nvdata.txt` under ignored artifacts.

**Correction: a charging start of Gemian's kernel (inference, confirmed by the owner's
observation).** The first reading of this boot (`0446ca24`) named LK or the preloader. The
bootloader work found no ext4 or raw block writer in LK, the preloader, ATF or TEE. Its
explanation: `poweroff` with the USB cable in lets the PMIC power the device up again. LK then
starts in charging mode and boots the primary `boot`, Gemian's kernel, whose start-up checks
`nvdata` (`e2fsck`, which resets the count and sets the last-check time) and mounts it
read-write. The owner confirmed it: "Yes, charging screen" appears after the power-off and
before they select `boot2`. That fits a write at 19:14:31, between the power-off at 19:14:01.7
and this kernel's start at 19:14:49.9. Not verified: that Gemian's kernel stamps the time 68 years
ahead. So neither the station's nor the card's Linux writes `nvdata`. Mounting it only to copy
the record stays, but it was not the cause. The earlier "Gemian: no boot" counted only
deliberate boots, not this charging start. No device action was taken for this correction.

### Step 4, R3 (predeclared): Wi-Fi, and the interface at scale 2

**What changed since R2.**
- **Kernel:** `CONFIG_RFKILL=y` in `gemini-a53-station-a72.fragment` (`69a9c63c`). iwd 3.12 exits
  when `/dev/rfkill` is missing: its rfkill module fails with `-ENOENT`, it tears its modules down,
  and the last line is "D-Bus disconnected". Reproduced in a container with the R2 card image; with
  the VM's `/dev/rfkill` bound in, iwd got past rfkill and stopped only at nl80211, which a
  container lacks. The release profile is unchanged.
- **Card** (`gemini-base` 4):
  - first boot restarts `gemini-wifi` after writing the country, since the unit already ran at
    boot without one;
  - the owner's interface choices: sway at scale 2, waybar as a left column in place of swaybar,
    `wmenu` for the launcher, `LANG=C.UTF-8`, and a closing note that Mod is the Fn key.

**Candidate.**
- **Kernel:** Buildbox, profile `mt6797-a53-station-a72`, `BUILD_MODULES=1`, job
  `bb2ed0c4…-mt6797-a53-station-a72-m1` (the record-only commit after `69a9c63c`; the build at
  `69a9c63c` gave the same `Image.gz` and config), package `linux-7.1.3-gemini-d363158a…`,
  `Image.gz` `9858b743…`, config `de3f80be…`, fetched under `artifacts/buildbox/bb2ed0c4…/`.
  Against R2's config the only change is `CONFIG_RFKILL=y`, with its defaults `RFKILL_LEDS=y`,
  `RFKILL_INPUT=y` and `RFKILL_GPIO=m`. Every module the card's units load is in it.
- **Boot image:** composed by the custodian as for `station-work-79`, then written with `flash-boot2`.
- **Card image:** `24d4812ed4471df41b059c6e464169667bb325da6d3f4ac77547c109ab6792ab`, from
  `build-card.sh` at `69a9c63c`, `gemini-base` `5e4f881c…`, 315 packages (waybar brings GTK 3),
  systemd 262.1, in the dev VM at `~/artifacts/arch-card-4/`.

**Container boot of the card image** (as for R2): `systemd-firstboot` masked; `sysinit.target`,
`basic.target` and `multi-user.target` reached; nothing waited on the console; `gemini-firstboot`
failed only for want of `tty1`. `C.UTF-8`, the waybar files, the scale and the restart are in place.
sway, run headless on the R2 image, used the waybar command for `bar-0`.

**Hypothesis.** As R2 to the first-boot dialogue. Then:
1. the country starts Wi-Fi: `gemini-wifi` restarts and loads the three modules;
2. iwd stays up, `iwctl` joins as WPA2-PSK and `wlan0` gets an address from networkd;
3. timesyncd sets the clock;
4. sway comes up at scale 2 with waybar as a column on the left, and `pacman -Sy` works.

**The unique observation.** No mainline boot has yet joined with iwd.

**Before, on the running station:** R1's steps 1 to 6 with this card image and `gemian-firmware`
from main, then step 7 with `flash-boot2` and `poweroff`.

**On the device, the owner:** as in R2. After the join, in a foot terminal (Fn+Enter): `date` and
`sudo pacman -Sy`. Photos once sway is up, showing the text size and the bar.

**After, on the station:** as in R2, the six eMMC hashes included.

**Readings.**

| Observation | Reading and next |
| --- | --- |
| iwd still exits | The journal's iwd lines name the module; check `/dev/rfkill` exists |
| iwd up, no networks seen | The driver's scan under iwd; compare with the station's wpa_supplicant |
| Joined, no address | networkd on `wlan0`; check `50-gemini-wlan.network` matched |
| Joined and addressed, `pacman -Sy` fails | DNS through resolved, or the keyring from first boot |
| Text still small, or no bar | sway's output scale or waybar's start; the journal and `swaymsg -t get_outputs` decide |
| Any eMMC hash changed | Stop, as before; `nvdata`'s mount count is already at its maximum, so it should not move |

**Budget.** One `boot2` write and one card write. Up to two card boots, then one station boot for
the evidence. No retries of an identical artifact.

**Stop rules.** As R1.

### R3 result (2026-11-07): iwd up, no join; no bar; the keymap is missing

Run by the custodian, with the owner at the device. Evidence boot `0993c976` (`station-work-80`,
boot2 `0277e13a…`), `arch=kept-ram-root`, pstore empty. Private evidence (journals, logs) is kept
outside Git.

**eMMC.** `boot`, `lk`, `nvram` and `proinfo` unchanged; `boot2` changed by the intended write;
`nvdata` changed again, `d1abc376…` → `42c28749…`. Read without copying it (owner): `s_mnt_count` is
11, and `s_mtime`/`s_wtime` are still Nov 6 12:20. **Correction:** the count does not stop at
`s_max_mnt_count`. The boot `32368f26` → `ed8a4c32` simply left it at 10, and R3's window raised it
to 11. So it is not one increment per boot either: two in R2's window, one each in the next two
station-to-station or R3 windows, none in another. Still open and unexplained.

**Wi-Fi.**
- rfkill fixed the start: iwd 3.12 stays up. `gemini-wifi` restarted after the country, the modules
  loaded and the firmware started; iwd saw `phy0` and `wlan0`, and networkd matched
  `50-gemini-wlan.network`.
- The owner's connect left iwd at "connecting", with no further iwd state and no driver line.
- **Cause, from a station test the owner approved** (the card's iwd in a read-only chroot of the
  card, on `station-work-80`): authentication, association and the 4-way handshake all work.
  iwd then installs the group key before the pairwise key; the driver refuses a group key that
  comes first ("join key command refused: group status=-95"), iwd sees `-EINVAL`, disconnects,
  and the driver restarts the WLAN. Three times. wpa_supplicant installs the pairwise key first,
  which is why the station joins. The fix belongs in the driver; the Wi-Fi driver session has it.
- iwd also logs that MD4 is missing, which matters only for EAP-MSCHAPv2, not PSK.

**Interface.**
- No bar was visible, and neither journal has a waybar line. Whether sway started swaybar or
  waybar isn't logged; sway logged only that Xwayland and swaybg are missing.
- The owner: "the graphical env doesn't have the gemini keymap". sway used plain US, so the Fn
  layer the console has was missing. The owner's choice: package all of Gemian's Gemini layouts,
  pick one at first boot, and make sway's Mod Ctrl+Alt, so that Fn is the symbol layer.

**Next.** The driver's key order (Wi-Fi driver session), the bar (investigate why waybar did not
show), and the Gemian layouts with a layout question at first boot.

### Step 4, R4 (predeclared): join with iwd, the bar, and the Gemini keyboard

**What changed since R3.**
- **Wi-Fi driver:** patch 0637 (`5e4cffbc`) holds a group key given before the pairwise key. On
  the station the card's own iwd 3.12 then joined the owner's network, got a lease and pinged the
  gateway five times out of five, with no restart; wpa_supplicant still joins. iwd recreates the
  interface (it came up as `wlan3`), so the card matches it by type: `50-gemini-wlan.network` has
  `Type=wlan`, and first boot asks iwd for the device name (`e63e084b`).
- **Keyboard** (`5993fe1c`, owner): Gemian's Gemini layouts, `planet_vndr/gemini` from Gemian's public
  `xkeyboard-config` at `64c6c0e4`, pinned by SHA-256 (`56baafdd…`) and fetched at package time, with
  xkeyboard-config's licence. One complete keymap per layout, composed as Gemian's `planetgemini`
  rules did; all 24 compile with the card's libxkbcommon. First boot asks for the layout. Fn is the
  symbol layer, so sway's Mod is Ctrl+Alt, set by a session wrapper on Arch's default config;
  floating windows drag with Alt. A headless sway read the result with no config error and 53
  Ctrl+Alt bindings.
- **Bar:** sway's `swaybar_command` is now one program, `waybar-bar`, which runs waybar with its
  options. With the options on the sway line, no bar appeared in R3.

**Candidate.**
- **Kernel:** Buildbox job `e63e084b…-mt6797-a53-station-a72-m1`, package
  `linux-7.1.3-gemini-b27d2b9f…`, fetched under `artifacts/buildbox/e63e084b…/`. `Image.gz`
  `9858b743…` and config `de3f80be…` are R3's; only `mac.ko` differs. The card takes its modules
  from the station's RAM root at handover, so the boot image changes.
- **Boot image:** composed by the custodian as for `station-work-80`, written with `flash-boot2`.
- **Card image:** `f1fcd84233ba9d24bb017f633b22fa1fa7e1d349cac2af7299c7a0182450c1af`, from
  `build-card.sh` at `e63e084b`, `gemini-base` 6 (`594278b3…`), 315 packages, in the dev VM at
  `~/artifacts/arch-card-6/`. Container boot as before: `sysinit.target` and `multi-user.target`
  reached, nothing waited on the console, and the layouts, wrappers and `Type=wlan` are in place.

**Hypothesis.** As R3 to the country. Then:
1. first boot lists the layouts, and the chosen one is in sway, with Fn typing the printed symbols;
2. iwd joins as WPA2-PSK, networkd gives the interface an address, timesyncd sets the clock, and
   `sudo pacman -Sy` works;
3. sway shows waybar as a column on the left, at scale 2; Ctrl+Alt+Enter opens a terminal.

**The unique observation.** No mainline boot has yet joined with iwd, shown the Gemini layouts in
a graphical session, or run waybar.

**Before, on the running station:** R1's steps 1 to 6 with this card image and `gemian-firmware`
from main, then step 7 with `flash-boot2` and `poweroff`. The six eMMC hashes as before; no copy of
`nvdata` (owner).

**On the device, the owner:** as in R3, choosing their layout at first boot. Then in a terminal
(Ctrl+Alt+Enter): type a few Fn symbols, run `date` and `sudo pacman -Sy`. Photos once sway is up,
showing the bar and the text size.

**After, on the station:** as in R3.

**Readings.**

| Observation | Reading and next |
| --- | --- |
| No join | iwd and driver lines in the journal; compare with the station test of 0637 |
| Joined, no address | networkd didn't match the renamed interface; check `Type=wlan` |
| Still no bar | waybar's own errors in the user journal; run `waybar-bar` from a terminal |
| Wrong symbols, or Ctrl+Alt bindings missing | the keymap file or the session wrapper; `swaymsg -t get_inputs` and the generated config in `/run/user/` |
| `nvdata` hash changed | expected so far: the open finding above; read the mount count as in R3 |
| Any other eMMC hash changed | Stop |

**Budget.** One `boot2` write and one card write. Up to two card boots, then one station boot for
the evidence. No retries of an identical artifact.

**Stop rules.** As R1.

### R4 result (2026-11-07): Wi-Fi joins with iwd; the setup keymap differs from sway's

Run by the custodian, with the owner at the device. Boot image `station-work-81` (boot2
`4ef93f07…`); evidence boot `7f8bde8f`, `arch=kept-ram-root`, pstore empty. Private evidence (journal,
`/var/lib/gemini`, logs) is kept outside Git.

**Observed.**
- **Wi-Fi works:** the owner joined with `iwctl` from a sway terminal: "network is up now". So iwd
  with 0637 joins on the card root, and networkd addressed the renamed interface.
- **Keymap during setup:** "the keymap during the setup isn't correct and that's why my wifi password
  is failing". The card's `KEYMAP=us` had replaced the Gemini console map stage 1 loads, so the
  first-boot dialogue had no Fn layer. Fixed after the run (`70f0177b`, `KEYMAP=@kernel`).
- **Passwords:** the user's password was typed under that plain US map; under the Gemini layout
  chosen for sway, `sudo` then failed. The owner reset it from the station: the card mounted
  read-write there, `passwd` in a chroot, typed by the owner on the station console; nothing else on
  the card changed. Even with `70f0177b`, the console has the Gemini US map while sway has the chosen
  layout, so a password can still type differently in the two unless the layout is US.
- **The owner:** "do not turn sshd up by default on the card". It stays masked, with no key.
- The bar and the scale weren't reported yet.

**eMMC.** `boot`, `lk`, `nvram` and `proinfo` unchanged; `boot2` changed by the intended write;
`nvdata` changed (`42c28749…` → `97653c9b…`), mount count 11 → 12, the open finding above.

**Later in R4.**
- The owner: "yes the bar was there, the scale is a bit too small". So `waybar-bar` fixed the bar.
- A second card boot, after first boot: Wi-Fi joined by itself (iwd connected at 13.25 s, a lease
  at 13.34 s), so 0637 and `Type=wlan` hold across boots. sway did not start: at 14 s logind refused
  it `/dev/dri/card0` ("Could not take device: Operation not permitted"), 3.4 s after the device
  appeared, and the session exited for good. In first boot the same session worked a few minutes
  in. Why logind refused isn't known from the journal.
- A third boot of that card, the owner present, with sshd started for that boot only: the session
  failed the same way at 13.8 s, and `systemctl restart` of it at 376 s brought sway up on `seat0`,
  `tty1`. So it is a start-up race; R5's retries (3 s apart, five a minute) are meant to cover it.
- The text console still had `KEYMAP=us` on that image, so the password the owner had reset under
  the Gemini map failed there; the custodian had them set a letters-and-digits one.

### Step 4, R5 (predeclared): one keymap from setup to sway

**What changed since R4** (the card, and since the revision below, stage 1).
- **Console keymaps for every layout** (`75e82eef`, owner): each Gemian layout is converted to a
  console keymap with the same composition as sway's, by `ckbcomp` from Debian's console-setup 1.216,
  fetched pinned and used at build time only (GPL-2.0-or-later, not installed). The build parses each
  map with `loadkeys -u -b` and fails on a bad one. First boot asks the layout first, loads it on the
  console at once, and keeps it in `vconsole.conf` and for sway. Before that, `KEYMAP=@kernel` keeps
  stage 1's Gemini map (`70f0177b`).
- **Scale 2.5** (owner) and **the session retried** after 3 s if it fails, at most five times a
  minute (`e3fbca2a`).

**Candidate (revised 2026-11-07, before any R5 boot: `nvdata` no longer mounted).**
- **Kernel:** no new build. R4's package `b27d2b9f…` stays.
- **Boot image:** a new one, composed from that package as for `station-work-81`, with stage 1
  from this commit, which copies the Wi-Fi record into RAM and unmounts `nvdata`. One
  `flash-boot2` write.
- **Card image:** `f04952e10675f4966fdb4a10017b1bf756b5a3da4596ef2d86b06a55848de1c6`, from
  `build-card.sh` at `5751db56`, `gemini-base` 10 (`9865231b…`), 315 packages, in the dev VM at
  `~/artifacts/arch-card-9/`. It has no `/nvdata`, and no `WIFI.storage` until card preparation
  copies the record. It replaces `arch-card-8` (`87402f22…`, `gemini-base` 9), which was written
  but never booted.
- **Card preparation:** `gemian-firmware SYSTEM_IMG ROOT /lib/firmware/mediatek/mt6797/WIFI.storage`
  on the new station; seven files, `WIFI.storage` checked by size and against its source.

**Hypothesis.**
1. First boot asks the layout first; from then on the console types with it, so the passphrase and
   the user's password type the same in setup, on the text console and in sway.
2. sway comes up at scale 2.5 on first boot and, on a second boot, either at once or after a retry.

**The unique observation.** No boot has yet used one Gemini layout across setup, console and sway.

**Before, on the running station:** `flash-boot2` with the new boot image, `poweroff`, the owner
selects `boot2` with a key at the prompt; on that station, check `nvdata=record-copied` and
`nvdata=unmounted` in the status and that `/proc/mounts` has no `nvdata`. Then R1's steps 1 to 6
with this card image and `gemian-firmware` as above, then `poweroff`.

**On the device, the owner:** first boot as in R4, choosing their layout, with a password that uses
Fn symbols; the Wi-Fi join in first boot. In sway: `sudo true` with that password. Then `sudo
poweroff`, boot the card again, log in on `tty2` with the same password, and see whether sway comes
up on `tty1`.

**After, on the station:** as in R4.

**Readings.**

| Observation | Reading and next |
| --- | --- |
| Setup still types differently from sway | the console map didn't load; the journal and `/etc/vconsole.conf` |
| Password works in sway but not on `tty2` | `systemd-vconsole-setup` didn't apply `gemini-<layout>` |
| Second boot: sway fails five times | the refusal is not a short race; capture `loginctl session-status` |
| Second boot: sway after one or more retries | the race is real; look for its cause, keep the retry meanwhile |
| `nvdata` changed | now that only stage 1's brief read-only mount remains, a change narrows the writer to that mount or to something before Linux; read the mount count |
| `nvdata=record-failed` | no Wi-Fi on the station or a new card; stop before the card write |
| Any other eMMC hash changed | Stop |

**Budget.** One card write, one `boot2` write. Up to two card boots, then one station boot for the
evidence.

**Stop rules.** As R1.

### R5, card boot 2 (2026-11-07, `station-work-83`, boot `057c908b`): no session, no console

From the custodian's reading of the private card journal (full R5 result to follow):
- `modprobe@drm.service` loaded `drm` at 7.0 s, and with it `drm_panel_orientation_quirks`.
  `display-start` then failed its own `insmod` of that module ("already loaded") at 12.34 s, so no
  DRM device appeared and sway failed six times with "Found 0 GPUs". On card boot 1,
  `modprobe@drm` hadn't loaded `drm`, and `display-start` did at 13.09 s: the outcome depends on
  start order.
- The failed load left `display-boot`'s marker, so the next start skipped the display as if the
  load had hung.
- Once `gemini-session@` gave up, `tty1` had no login (the session conflicts with its getty), and
  the Gemini keyboard has no F-keys to reach another console. The owner: "let's make sure we
  implement a way to switch console with the gemini keyboard".

**Fixes, after the run.**
- `display-start` (station and card) treats a module already in `/sys/module` as loaded.
- `display-boot` clears its marker whenever `display-start` returns; only a hang or power loss
  leaves it.
- `gemini-session@` starts `getty@tty1` when it fails for good.
- **Console switching without F-keys:**
  - Alt+Left/Right steps between consoles; the station's map already had it, and the card's maps
    now do too.
  - Ctrl+Alt+1 to 0 picks console 1 to 10, in both.
  - In sway, Ctrl+Alt+Tab runs `chvt 2` through one passwordless sudo rule for `wheel`.
  - `gemini-base` 11; the station needs a new boot image for its map and `display-start`.

### `gemini-base` 11 on the R5 card (2026-11-07, `station-work-84`, `boot2` `a443d7d0`)

The custodian installed `gemini-base` 11 on card-9 in place (`pacman -U` from the station),
keeping the owner's setup. Private journal under `station-work-84/card-boot1/`.
- **Display:** `drm` at 13.18 s, `display-boot` `native` at 13.52 s.
- **Consoles:** the owner switched to `tty5` and logged in.
- **Wi-Fi:** joined at the first try, at 15.2 s.
- **sway:** logind refused the DRM device on all six tries, from 17.22 s to the start limit at
  35.6 s ("Could not take device: Operation not permitted", then "Found 0 GPUs"). This is R4's
  symptom, but no retry recovered. After boot: `seat0` can do graphics and TTYs, `card0` has the
  `seat`, `uaccess` and `master-of-seat` tags with the user's ACL, and the `tty5` login is
  active. `systemd-vconsole-setup` ran again from 13.28 s to 14.54 s, overlapping the display
  handover. The cause is not known.
- **`OnFailure=` fired on every failure,** not just the last. Each one started `getty@tty1`, and
  the next retry stopped it: the flashing the owner saw.

**Changes, `gemini-base` 12.**
- `sway-session` logs, before sway starts: the session's seat, VT, TTY, active state, state,
  type and class; `seat0`'s active session; the active VT; and `card0`'s `ID_SEAT` and tags.
  In logind, this refusal comes from a session without a seat, or from a device on another seat.
- `OnFailure=` starts `gemini-session-fallback@`, which starts the getty only when the session
  unit is `failed`, not while it waits to retry.

### `gemini-base` 12 on the R5 card (2026-11-07, boot `93343f9d`): the cause of sway's refusal

- **Fallback:** the retries logged "no getty", and `tty1` got one login prompt at 36.4 s, after
  the start limit. No more flashing.
- **Diagnostic:** every try had a sound session (`seat0`, VT 1 active, the session active,
  `card0` tagged for the seat). So the seat checks in logind's `TakeDevice` were not the source
  of EPERM. The only other EPERM on that path is from `open()` itself, and a failed
  `drmSetMaster` gives EBUSY or EACCES instead.
- **Cause (from the journal, and systemd's units and source):**
  - `systemd-logind.service` has `DeviceAllow=char-drm rw`, a device cgroup filter that systemd
    resolves through `/proc/devices` when it sets the filter. logind is ordered after
    `modprobe@drm` for that reason.
  - On this boot, `modprobe@drm` finished at 7.344 s, in parallel with `gemini-modules.service`,
    whose `depmod` finished at 7.345 s. With no `modules.dep`, `modprobe -q drm` loaded nothing.
  - logind started at 12.64 s, and `drm` registered at 12.82 s, when `display-start` loaded it.
    So logind's filter had no `drm` entry, and its own `open()` of `/dev/dri/card0` was refused.
  - Restarts that worked came after something re-applied logind's cgroup settings: first boot's
    `systemctl enable` (a daemon reload), a package install, or starting another system service.
    That last one is an inference, from systemd re-applying a slice's member units when one
    starts.
  - On card boot 2, `modprobe@drm` won the race and loaded `drm` at 7.0 s, so logind could open
    the device. There, `display-start` stopped instead (fixed in `gemini-base` 11).
- **Fix, `gemini-base` 13:** a drop-in orders `modprobe@drm` after `gemini-modules.service`, so
  `drm` is registered before logind starts. Not yet booted.

### `gemini-base` 13 on the R5 card (2026-11-07, boot `4dbf5ee7`): sway starts

`station-work-84` (`boot2` `a443d7d0`), card-9 with `gemini-base` 13 installed in place. Private
journal under `station-work-84/card-boot-gb13/`.
- **Order, as predicted:**
  - the module index finished at 7.311 s;
  - `drm_core_init` ran at 7.312 s;
  - `modprobe@drm` finished at 7.3125 s;
  - logind started at 11.83 s.
- **sway:** the session started at 12.93 s, with no "Could not take device", no restart and no
  `tty1` fallback. The owner: "it worked!!!".
- **Wi-Fi:** joined at the first try, at 14.93 s.

This confirms the cause recorded above: `drm` has to be registered before logind starts.
Not yet confirmed in R5: the password on `tty2`, and `pacman` syncing under Landlock.

### niri instead of sway, and profiling tools (owner, 2026-11-07)

The owner: "I'd like to switch from sway to niri", and wants the kernel and the image to carry
perf and power-analysis tools. `gemini-base` 14:
- **niri 26.04** from Arch Linux ARM, with `/etc/niri/config.kdl`:
  - `DSI-1` rotated 270 at scale 2.5, touch mapped to it;
  - waybar as the left column;
  - every shortcut on Ctrl+Alt, as with sway: Enter for foot, D for wmenu, Shift+/ for the list,
    Shift+E to quit, Tab for `tty2`.
  - The keyboard file is included from `/etc/niri/gemini-keyboard.kdl`, which first boot writes.
    On upgrade, the layout chosen for sway carries over.
- **Rendering:** niri needs EGL, and Panfrost isn't loaded at boot. The session forces Mesa's
  software path (`GBM_ALWAYS_SOFTWARE`, `LIBGL_ALWAYS_SOFTWARE`): llvmpipe, shown through
  `kms_swrast` on the display-only `mediatek` driver. Whether that works on the device, and how
  fast, isn't known yet.
- **Tools:** `perf`, `trace-cmd`, `powertop` and `cpupower`.
- **Kernel:** `configs/gemini-a53-station-perf.fragment` in `mt6797-a53-station-a72` turns on
  perf events, the tracepoints, kprobes, uprobes and BPF events. Its first form, with the
  function tracers, made the station boot image 565 KB too big for `boot2` (16 MiB); they
  were dropped. mt6797's device
  tree has no CPU PMU node, so perf gets no hardware counters until one is added.

### Drivers at boot, and niri on the Mali (owner, 2026-11-07)

The owner: "All features should be loaded to make full use of the device", and then "Yes, load
them all". Until now, every driver proven only by hand on the station stayed unloaded (the
repository's "nothing loads them at boot until they are proven"), so niri rendered in software
while the Mali sat idle.

- **Station image:** `compose-station.py` now packs the release's optional modules, plus FM's
  `radio-mt6797`, into the station RAM root as well. The station's `init` loads none of them;
  stage 1 copies them to the card.
- **`gemini-base` 15:**
  - `gemini-hw@<group>.service` runs `hw-load` at boot for six groups: `gpu`, `touch`,
    `sensors`, `camera`, `bluetooth` and `fm`, in `release/hw-start`'s order.
  - The groups load after the display, so the panel keeps `card0`. Bluetooth and FM also wait
    for `gemini-wifi`, and skip with no country set.
  - niri starts after the GPU group and renders on the Mali through Panfrost, falling back to
    software when no render node appears.
  - `bluez` and `bluez-utils` are installed; `bluetooth.service` is left for the owner to
    start.
- **Held back, each named by its own record:**
  - cpuidle: "would hang every CPU at its first idle";
  - the A72 pair: no cooling, only the 117 °C reset; loading at init is the record's step 9;
  - A53 cpufreq: wants a soak under real heat first;
  - USB host: `fusb301` takes over the left Type-C chip, which carries charging, and the
    left-port host failed;
  - GNSS: no position yet, and a firmware assert takes Wi-Fi down;
  - Bluetooth voice: hand-load only.
- **Limits that now apply at every boot:** with Panfrost loaded, the GPU's VGPU rail and LDOs
  stay on at idle. Each group's other limits are in
  [the support matrix](../../docs/HARDWARE_SUPPORT.md).

### Card-14 first boot (2026-11-08, `station-work-89` `a01d1b0c`, boot `bc53ae17`)

The owner: "works now!". Observed by the custodian over USB SSH:

- All six `gemini-hw@` services are active, and no unit failed.
- niri renders on the Mali: `/dev/dri/renderD128` exists and `niri-session` logged "rendering on
  the GPU".
- `panfrost`, `novatek_nt36xxx`, `bmi160_i2c`, `stk3310` and `hi556` are loaded, with no kernel
  fault lines.
- `btmt6797` and `radio_mt6797` were not seen in `lsmod`. Inference, not checked: `hw-load`
  skips both without `mt6797_consys`, which `gemini-wifi` loads, and the card was not reachable
  over Wi-Fi this boot.
- About 30 systemd "Failed to preset all unit" lines appear at 8.8 s, before the root is
  remounted read-write. The root is read-write afterwards.

The owner reported two faults, and fixed both live:

- **Upside down:** the display was upside down with `transform "270"`; `transform "90"` is the
  right way up.
- **Touch off by 90°:** `novatek-nt36xxx` already reports landscape coordinates (X = raw y, Y =
  raw x max − 1 − x), and niri turns touch again by the output transform. A libinput calibration
  matrix of `0 1 0 -1 0 1` fixes it; `0 -1 1 1 0 0` was 180° off.

The owner asked for both in the next card. `gemini-base` 16 ships them: `niri.kdl` uses `"90"`,
and `70-gemini-touch.rules` in `/usr/lib/udev/rules.d` sets the matrix. Removing the driver's own
rotation would make the matrix unnecessary, but needs a kernel change, so it is left for later.

Bluetooth and FM on that boot (custodian): at boot `gemini-wifi` printed `off-no-country`, so
both `gemini-hw@bluetooth` and `gemini-hw@fm` printed `needs-connectivity`. First-boot setup then
set a country and restarted `gemini-wifi` (`on country=US`, `mt6797_consys` loaded), but nothing
retried the two groups. `gemini-base` 17 has `firstboot` restart both after Wi-Fi starts. On later
boots the country is already set and `gemini-wifi` orders first; that path is not yet verified.

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
