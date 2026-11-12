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

### Rotation from the kernel (`gemini-base` 18, 2026-11-08)

The owner asked for the rotation to come from the device tree. Patches 0647/0648 make touch
report panel-native coordinates. Patches 0649/0650 report the panel's orientation (rotation
270, "Left Side Up"). The display session read niri 26.04's `src/backend/tty.rs`: niri applies
that orientation itself, then adds the config transform on top.

`gemini-base` 18 therefore drops `transform "90"`, which would otherwise turn the screen 180°,
and drops `70-gemini-touch.rules`, whose matrix would be wrong for native coordinates.

**Pairing:** the root follows the boot2 kernel, so `gemini-base` 18 belongs only with a station
image built with 0647–0650. With the older kernel (`station-work-89`), card-16 (`gemini-base`
17) is the matching root. Neither pairing has been built or booted yet.

### Umbriel and Noctalia instead of niri and Waybar (owner, 2026-11-08)

The owner asked to "Remove Waybar", "replace Niri with Umbriel and Noctalia", and said first-time
setup "doesn't need to configure wifi": iwd runs, and the user joins networks from Noctalia.

**The two projects:**

- [Umbriel](https://github.com/noctalia-dev/umbriel) is the Noctalia project's own Wayland
  compositor. It is built on wlroots 0.20, with a hard fork of SceneFX in-tree, and needs C++23.
- Noctalia 5 is a native C++ shell, no longer Quickshell-based, and supports Umbriel directly.

**Packaging:**

- Arch Linux ARM ships `noctalia` 5.4.1 for aarch64, and every Umbriel dependency, including
  `wlroots0.20`.
- No repository or release ships Umbriel itself. The AUR has only `umbriel-git` and a
  placeholder `umbriel`.
- `umbriel/PKGBUILD` therefore pins upstream commit `94ab5961` by its archive checksum. It
  follows the AUR recipe, without `xdg-desktop-portal-umbriel`, which only covers screen sharing
  and input capture, and adds one small patch for the keyboard (below).
- `build-card.sh` builds it in the card's chroot as `nobody`, installs it, then removes the build
  tools that nothing needs any more.

**Rotation:**

- niri applied the kernel's panel orientation (Left Side Up, from 0649/0650) by itself. Umbriel
  does not: neither its source nor wlroots reads the property.
- `/etc/xdg/umbriel/config.toml` therefore sets `transform = "90"` on `DSI-1`. That is the same
  wl_output transform niri derived from Left Side Up.
- wlroots maps touch onto the output's box without rotating it, unlike niri.
- With 0647/0648, touch reports the panel's portrait coordinates. Left Side Up puts the panel's
  left edge at the top, so the screen point is (1 − panel y, panel x), in normalised coordinates.
- `70-gemini-touch.rules` returns with matrix `0 -1 1 1 0 0`. This is derived, not yet seen on
  the device. It agrees with card-14: the old driver's landscape coordinates were exactly that
  point, which is why niri, rotating them again, needed a matrix. Card-18 showed this matrix
  wrong; touch needs none (see "Touch on card-18" below).

**Wi-Fi:**

- First boot no longer runs `iwctl`; iwd is enabled at boot.
- Noctalia picks iwd over D-Bus when neither NetworkManager nor wpa_supplicant is present.
  iwd's D-Bus policy lets `wheel` use it, and the first user is in `wheel`.
- The country question stays: nothing transmits until a country is set, Noctalia doesn't set
  one, and Bluetooth and FM wait for it too.

**Keyboard:**

- Umbriel takes xkb layout names, not a keymap file.
- libxkbcommon 1.13 builds one group per named layout, whatever the rules. Through names, the
  two-group Gemini layouts (ru, jp, ara, cz, sk, gr) failed to compile in the VM, even with
  rules of gemini-base's own; the other 18 matched their keymap files.
- `umbriel/keymap-file.patch` (about 15 lines) lets `UMBRIEL_XKB_KEYMAP_FILE` name a complete
  keymap file instead.
- `umbriel-session` takes the layout first boot wrote to `/etc/vconsole.conf` and loads
  `/usr/share/gemini/xkb/LAYOUT.xkb`, the same file niri used.

**Pairing:** this root, `gemini-base` 19, goes with `station-work-90`, which is composed from
`37c50274` with 0647–0650.

**Browser:** the owner asked for qutebrowser, so gemini-base depends on `qutebrowser` and
`qt6-wayland`. With it the root uses 2.4 GB of the 3.9 GB partition. In the VM, QtWebEngine
6.11.3 under Qt 6.12 rendered a test page offscreen, in software. Whether Chromium uses the Mali
through Panfrost, or falls back to software, needs the device.

#### Keybindings on the Gemini keyboard (owner, 2026-11-08)

The owner asked that the Umbriel and Noctalia bindings "make sense on the gemini". What the
keyboard has ([keyboard](../../docs/hardware/keyboard.md)):

- **Modifiers:** Ctrl and Alt at the bottom left, and both Shift keys.
- **Fn:** it is `KEY_LEFTMETA`, but the Gemini layouts make it xkb level 3 (Mod5), the symbol
  layer. There is no usable Super key, and Umbriel's default `Mod` (Super) never fires.
- **Missing keys:** there are no F-keys (Shift+Fn+1 to 0 types F1 to F10), and no plain - = /
  ; keys.
- **Fn-layer actions:** Fn plus a letter gives the media, volume, brightness and Print keysyms.
- **PMIC keys:** Esc is the power key, and the outer side key sends `XF86Send`.

Two Umbriel facts shape the bindings:

- Binds match the key's unshifted symbol, and the modifiers exactly. Fn+T arrives as
  `XF86AudioMute` with Mod5, so a plain `XF86AudioMute` bind never fires. `gemini-keyboard.patch`
  lets a bind name `Mod5`.
- The matrix has no diodes. Ctrl (row 4, column 6) and Alt (row 4, column 1) plus a key in
  column 1 or 6 (2 7 9 0 W R D H K L C Left) form a rectangle that reads a phantom key until
  patch 0385's rescan clears it.
  - Left Shift shares Ctrl's column, so Ctrl+Alt+left Shift reads a phantom C.
  - The bindings avoid those columns where they can, and use the right Shift.

| Keys | Action |
| --- | --- |
| Ctrl+Alt+Space, or the side key | Noctalia launcher |
| Ctrl+Alt+A / N / B | Control Center: home / Network / Bluetooth |
| Ctrl+Alt+T or Ctrl+Alt+Enter | Terminal (foot) |
| Ctrl+Alt+Q | Close the window |
| Ctrl+Alt+Z | Window switcher |
| Ctrl+Alt+O | Overview |
| Ctrl+Alt+Backspace | Noctalia session menu (log out, reboot, power off) |
| Ctrl+Alt+I | Umbriel's binding cheat sheet |
| Ctrl+Alt+Tab | Text console on tty2 (Ctrl+Alt+1 or Alt+Left comes back) |
| Ctrl+Alt+arrows | Focus; with the right Shift, move |
| Ctrl+Alt+1 to 5 | Workspace; with the right Shift, move the window there |
| Ctrl+Alt+Comma / Period | Take the window into the column on the left / right |
| Ctrl+Alt+S / F / G / V | Cycle width / maximize / fullscreen / float |
| Fn+Q / W / E | Play-pause / previous / next |
| Fn+T, Fn+C / V | Mute, volume down / up |
| Fn+B / N | Brightness down / up |
| Fn+R | Screenshot of a region |
| Alt+drag | Move a window with the pointer |

**Backspace (owner: "the backspace key was mapped to delete" under sway):**

- The kernel isn't the cause: the matrix maps the key to `KEY_BACKSPACE` (row 6, column 2).
- The cause wasn't found in the xkb symbols either. Every shipped keymap, sway's included, gives
  BackSpace plain, Delete with Shift and XF86Tools with Fn.
- The console map gives Delete (DEL, the backward erase) plain and Remove with Shift.
- So a plain press erases backward in every layer we ship, and the sway report stays unexplained.
  A held Shift would give Delete.
- `gemini-base` 19 makes Fn+Backspace give Delete as well, in the keymap files and on the
  console; Shift+Backspace still does.
- Owner check: `xkbcli interactive-evdev --keymap /usr/share/gemini/xkb/LAYOUT.xkb` on a console
  shows the keysym of each press.

**Owner checks on the device:**

- Ctrl+Alt+Left, Ctrl+Alt+2 and the right-Shift moves read no phantom key.
- The Fn bindings fire.
- The side key opens the launcher at runtime. LK only reads it at boot.
- Noctalia's volume and brightness actions do something. There is no PipeWire daemon (audio is
  ALSA), and the backlight path is untested.

### Card-18 first boots, and `gemini-base` 20 (2026-11-08, `station-work-90`)

Observed by the custodian with card-18 (`gemini-base` 19):

- Umbriel started on Panfrost, but every launch failed with `systemd-run: Failed to start
  transient scope unit: Unit session-c1.scope not found`. Noctalia, foot and `chvt` never
  ran, so no keybinding did anything.
- With `unset SYSTEMD_EXEC_PID` added to the session script live on the card, boot `2ae75d4c`
  started Noctalia and the owner saw it.
- On that boot, Panfrost loaded with `renderD128` present and no kernel faults. The Bluetooth
  and FM modules loaded once first boot had set the country, and `gemini-wifi` and iwd were
  active.
- CMA was 32768 kB total with 4036 kB free. Within seconds of start, Umbriel logged about 40
  `DRM_IOCTL_MODE_CREATE_DUMB` ENOMEM errors ("Failed to create effect framebuffer").

Cause, from Umbriel `94ab5961`:

- **Launches.** Umbriel takes itself for a systemd user service when `SYSTEMD_EXEC_PID` equals
  its own pid (`src/server/server.cpp`), which is true when `gemini-session@.service` execs the
  session script. It then starts each app with `systemd-run --user --scope` bound to its own
  unit, which is `session-c1.scope` in the system manager and unknown to the user manager.
- **Memory.** umbrielfx allocates its offscreen buffers from the output's allocator. On this
  display that means mediatek dumb buffers in CMA, one 9.3 MB buffer per full-screen target,
  and the screen's own buffers nearly fill the 32 MiB. Blur and the animations use these
  buffers; shadows do not. niri drew its effects in GPU memory, so it never hit this.

`gemini-base` 20:

- `umbriel-session` unsets `SYSTEMD_EXEC_PID` before starting Umbriel, so apps start as plain
  child processes.
- `umbriel.toml` turns blur and animations off, since they could not get buffers anyway. A
  larger CMA reservation on the kernel side would allow them again.
- Card-19 (dev VM, `gemini-base` 20, image sha256 `a576124182bc…`, 387 packages) pairs with
  `station-work-90`. Umbriel's `config validate` passes on the image. Untested on the device.

### Touch on card-18, and `gemini-base` 21 (2026-11-08, `station-work-90`)

Measured by the custodian on card-18 (kernel `37c50274`, Umbriel `94ab5961`, output transform
90, touch mapped to `DSI-1`), with `LIBINPUT_CALIBRATION_MATRIX` set to the identity. A
qutebrowser tap-target page in an 844x346 viewport recorded target → touch:

| Target | Touch |
|---|---|
| (717, 69) | (728, 82) |
| (717, 276) | (726, 285) |
| (126, 276) | (141, 279) |
| (422, 173) | (438, 179) |

Every tap lands within about 16 px of its target. One first tap, made while the page loaded,
was an outlier and is left out. The packaged `0 -1 1 1 0 0` was wrong, and the owner also
found `0 1 0 -1 0 1`, `0 -1 1 -1 0 1` and `0 1 0 1 0 0` wrong.

Inference: with this kernel the touchscreen already reports coordinates in the landscape frame
of the rotated output, so the assumption above that it reports portrait coordinates was wrong.

`gemini-base` 21 drops `70-gemini-touch.rules`, so libinput uses no calibration. Blur and
animations stay off: the 256 MiB CMA kernel (`65549ff5`) has not yet been tested on the device.
Card-20 (dev VM, image sha256 `b7cea5be8283…`) carries it: no calibration rule on the image,
and Umbriel's `config validate` passes. Untested on the device.

### Effects with 256 MiB of CMA, hostname and a left bar (`gemini-base` 23, 2026-11-08)

Measured by the custodian on `station-work-91` (`65549ff5`, boot `50572be9`) with card-18
(`gemini-base` 19 plus the launch fix, blur and animations on):

- The kernel logged `cma: Reserved 256 MiB at 0xf0000000`, and CmaTotal read 262144 kB.
- CmaFree read 195812 kB at the desktop, and 192620 kB after a minute with the launcher, foot
  and qutebrowser open, so about 68 MiB was in use.
- No `CREATE_DUMB` or "Failed to create effect framebuffer" errors appeared. The owner: "Smooth
  now". Touch worked with the identity calibration.

`gemini-base` 23 (owner requests, 2026-11-08):

- Blur and animations are back on, with blur radius 3. The card therefore needs
  `station-work-91` or later; on a 32 MiB kernel the allocation errors and the lag return.
- First boot asks for a hostname after the time zone. An empty answer keeps `gemini`. The name
  goes to `/etc/hostname` and the running kernel; `nss-myhostname` resolves it.
- Noctalia's bar is vertical on the left edge. Noctalia reads no system-wide config, only
  `~/.config/noctalia/*.toml` merged in name order, plus GUI changes in
  `~/.local/state/noctalia/settings.toml`. So the package installs
  `/etc/skel/.config/noctalia/00-gemini.toml` (`[bar.default] position = "left"`), and the user
  created at first boot gets a copy. The user's own files and GUI settings override it.
  Checked against Noctalia 5.4.1: the file changes only that key in
  `noctalia config export full`.
- The bar shows the battery (owner, 2026-11-08). Noctalia's default bar already lists the
  `battery` widget, which reads UPower and hides itself without one. Card-18 had no `upower`, so
  `gemini-base` 23 depends on it. UPower starts on demand over D-Bus. On `station-work-91`,
  `/sys/class/power_supply/battery` reads type Battery, capacity 98 and "Not charging" on USB;
  the charger is `bq25890-charger-0`.

Card-21 (dev VM, `gemini-base` 23, image sha256 `8550dfaab9a6…`, 393 packages, root 2.50 GB used)
pairs with `station-work-91` or later. Checked read-only on the image: upower 1.91.5 with its
D-Bus activation file, the bar default in `/etc/skel`, blur on, and the hostname prompt.
Umbriel's and Noctalia's config checks pass. The prompt logic, run in the VM, kept `gemini` for
an empty answer, rejected `-x`, and wrote `my-pda`. Untested on the device.

### The keybind cheatsheet: first login only, and fitted (`gemini-base` 24, 2026-11-08)

Owner, with a photo of card-18 at startup: "it's nice for the first boot (but it needs to fit),
but not for the subsequent starts". In the photo, the Focus group and workspaces 4 and 5 ran off
the bottom of the screen.

Cause, from Umbriel `94ab5961` (`src/scene/cheatsheet.cpp`, `cheatsheet_rows.cpp`):

- The cheatsheet opens at every start while `general.show_cheatsheet` is true, which is the
  default.
- The panel may use the output height less a fixed 120 px. On the 432 px desktop that leaves
  312 px, and the title, footer and padding take about 120 of them.
- The body tries 11, 10 and 9 point text in up to four columns, each at most 600 px wide. When
  nothing fits, it keeps the last attempt.
- A run of workspace binds collapses into one row only when all of 1 to 9 are bound. The card
  binds 1 to 5, so `workspace-switch` and `window-move-to-workspace` took ten rows.

Changes:

- `umbriel/gemini-cheatsheet.patch` (Umbriel `pkgrel` 4):
  - It collapses any full run 1..n, with n of at least 2.
  - It caps the margin at an eighth of the output height (54 px here).
  - It tries 8 and 7 point text after 9.
- `umbriel.toml` sets `show_cheatsheet = false`.
- Umbriel's autostart runs `/usr/lib/gemini/first-login`. Unless
  `~/.local/state/gemini/cheatsheet-shown` exists, it runs `umbriel msg cheatsheet-open` and then
  creates that marker. A failure leaves no marker, so the next login tries again. Ctrl+Alt+I
  still shows the cheatsheet at any time.

The fit is not measured. The dev VM has no DRM device, and Umbriel's renderer needs one. The
layout arithmetic suggests three columns at 7 or 8 point, but only a screenshot on the device
settles it.

**The left bar, as kept.** The custodian tried a denser bar live on card-18, and the owner said
"Keep it". It passed `noctalia config validate` there, and Noctalia reloaded it live.
`noctalia.toml` now carries it:

- full height: no end or edge margins, no radius, 40 px thick;
- launcher and workspaces at the top, the clock (hours over minutes) in the centre, and network,
  volume, battery and the control center at the bottom;
- the battery drawn as a fill, since a vertical bar has no room for the percentage.

The session widget is gone; its panel stays on Ctrl+Alt+Backspace and in the control center.

**PipeWire.** The owner: "It looks like pipewire is missing and noctalia relies on it". On
card-18 Noctalia logged `pipewire disabled: pipewire: failed to create context`, so the volume
widget, the media controls and the Fn volume keys had nothing behind them.

- `gemini-base` now depends on `pipewire`, `wireplumber`, `pipewire-pulse` and `pipewire-alsa`.
- The card has no UCM profile or alsa-lib config, so WirePlumber's automatic profiles would
  open unrouted and hostless PCMs. The audio session agreed to direct nodes instead:
  - `50-gemini.conf` in `pipewire.conf.d` defines one sink, "Headphones", on
    `hw:mt6797mt6351,0` at 48 kHz. That is Playback_1 (DL1), the only PCM that audio-start
    routes to the MT6351 headphone drivers.
  - `50-gemini.conf` in `wireplumber.conf.d` disables the card's automatic device.
- Hardware gain stays where audio-start leaves it: Headphone Volume 0, which is −10 dB.
  Volume is PipeWire's software volume.
- PipeWire's 100% means full scale into the headphones, and full-scale output at −10 dB has
  not been measured. So `first-login` sets the default sink to 35% once per user, with its own
  marker; WirePlumber keeps later changes.
- If 100% proves too quiet, the audio record's advice is to raise Headphone Volume by 2 at a
  time with the owner listening, and to go no higher than 10 (0 dB) without a level check.
- Speakers and capture stay off. Capture needs routing that audio-start does not set, and the
  microphones are preliminary.

Card-23 (dev VM, `gemini-base` 24 and Umbriel `pkgrel` 4, image sha256 `99a2da8ba983…`, 417
packages, root 2.53 GB used) pairs with `station-work-91` or later. Checked read-only on the
image:

- pipewire 1.6.10 and wireplumber 0.5.18 are installed, and `pipewire.socket`,
  `pipewire-pulse.socket` and `wireplumber` are enabled for every user under `/etc/systemd/user`;
- both `50-gemini.conf` files parse with `spa-json-dump`;
- `show_cheatsheet = false` is set and the autostart runs `first-login`;
- Umbriel's config check passes, and so does Noctalia's with the packaged bar.

Untested on the device: the cheatsheet's fit, the sink on the real card, and the 35% start.

### Card-23 first login, and a hidden cursor (`gemini-base` 25, 2026-11-08)

From the owner's photo of card-23 at first login, as relayed by the custodian:

- The cheatsheet fits: every group and the footer are on screen, with the workspace binds
  collapsed.
- The bar is as kept.
- The volume widget reads 35, so Noctalia found PipeWire.
- The battery graphic shows 88.

Not yet observed: sound through the headphones, and the cheatsheet staying away at the second
login.

The owner: "the mouse cursor is visible, it would be nice to have it disappear unless a mouse
is connected". Umbriel `94ab5961` can already hide the cursor after a timeout without pointer
motion, and on typing. Only pointer input (motion, buttons, scrolling, tablet tools) shows it
again; touch does not (`src/input/cursor.cpp`). The Gemini has no pointing device, so
`umbriel.toml` now sets `[input.cursor] hide_when_typing = true` and `hide_timeout_ms = 1500`.
In practice the cursor stays hidden until a mouse moves. Showing it only while a mouse is
attached would need Umbriel to track pointer devices; that is left unless the timeout falls
short.

Card-24 (dev VM, `gemini-base` 25, image sha256 `cd7154c33a12…`, 417 packages) pairs with
`station-work-91` or later. Umbriel's config check passes with the cursor settings. Untested on
the device.

### A simpler bar (`gemini-base` 26, 2026-11-08)

The owner, with a photo of card-23's bar, which shows the network name beside the Wi-Fi icon
and the volume value under its icon: "don't display the network name, icon is enough", "could
we add bluetooth?", "don't display the volume value, icon is enough".

`noctalia.toml` now:

- adds `bluetooth` to the bar's end section, after `network`;
- sets `show_label = false` on the network, Bluetooth and volume widgets.

Noctalia 5.4.1's `config validate` passes with it, run from the card-24 image.

In Noctalia 5.4.1 (`src/shell/bar/widgets/bluetooth_widget.cpp`), the Bluetooth widget draws
only while bluez reports an adapter. The card leaves `bluetooth.service` stopped, so there is
no adapter on D-Bus and the widget hides itself completely. With the service running, it
shows: the off glyph while the adapter is powered down, and its normal glyph once powered.
Whether to start bluetooth at boot is the owner's decision.

The owner chose to start Bluetooth at boot with the radio off (`gemini-base` 27):

- `build-card.sh` enables `bluetooth.service`.
- bluez 5.87 powers every adapter it finds by default (`#AutoEnable=true`), and it owns
  `/etc/bluetooth/main.conf` with no drop-in directory. So `build-card.sh` sets
  `AutoEnable=false` in `[Policy]` in the image's copy, and fails if it can't.
- The adapter appears to Noctalia unpowered, and the owner turns it on from the bar or the
  control center. Starting the service is no radio action by itself.

The owner also asked for a simpler, macOS-like launcher on Ctrl+Alt+Space (`gemini-base` 28):

- `noctalia.toml` sets `[shell.launcher] layout = "simple"`: a search field over one result
  list, instead of the full layout's toolbar and Recent, Pinned, All, Categories and Providers
  tabs.
- It also sets `categories = false` (no chip row), `compact = true` (tighter rows) and
  `show_app_origin_indicator = false`.
- The simple layout is a fixed 560x500 in Noctalia 5.4.1. The panel manager clamps any panel
  to the output less its padding (`src/shell/panel/panel_manager.cpp`), so it fits the 432 px
  height.
- Noctalia's `config validate` passes, and `config export full` differs from the defaults in
  exactly those four keys.
- Not seen on the device yet.

A media player (owner, 2026-11-08, `gemini-base` 29):

- `gemini-base` depends on `mpv` and `mpv-mpris`.
- Against the card-24 image, pacman would download 3.3 MB for them: mpv, its plugin and nine
  small libraries. ffmpeg is already on the card.
- mpv has no MPRIS interface of its own. Noctalia's media controls and the Fn play, previous
  and next binds (`noctalia msg media …`) work through MPRIS, so they need the plugin.
  mpv-mpris 1.3 installs `/etc/mpv/scripts/mpris.so`, which mpv loads for every user.
- Mainline has no MT6797 video decoder, so mpv decodes on the CPU. Playback speed is not
  measured.
- Gemian does the same (owner question, 2026-11-11; read-only check on Gemian boot
  `56e31061`, kernel 3.18.41+, Debian 9). Its kernel has the vendor decoder built in
  (`/dev/Vcodec` and `/dev/MJC`, root-only), and the Android 7.1.1 container lists MediaTek
  OMX decoders for AVC, HEVC, VP9, VP8, MPEG-4, H.263, DivX, Xvid and VC-1. Nothing on the
  Debian side reaches them: no droidmedia, gst-droid or OMX/hybris GStreamer element, and no
  `hwdec` setting for its mpv 0.23. Its desktop players decode in software too. The decoder
  hardware itself works on this unit: the
  [video codec experiment](../2026-11-09-mt6797-video-codec/README.md) decoded HEVC through
  `/dev/Vcodec` with MediaTek's own test tool during the same boot.

Bigger bar icons and a display name (owner, 2026-11-08, `gemini-base` 30, Umbriel `pkgrel` 5):

- The owner wanted the bar's icons to fill its width. Tried live on card-23 and approved:
  `scale = 1.6` on the launcher, network, Bluetooth, volume and control-center widgets.
  The battery keeps its size, at the owner's request.
- Noctalia's control center listed the display as "(null) (null) (DSI-1)". wlroots 0.20
  (`backend/drm/drm.c`) builds a DRM output's description with
  `snprintf("%s %s… (%s…)", make, model, …, name)`. Make and model come from the EDID, which
  the DSI panel lacks, so they are NULL and glibc prints "(null)". Noctalia shows that
  description.
- `umbriel/gemini-output-name.patch` sets the description to "Built-in display (DSI-1)" for
  a DRM output with neither make nor model. Other outputs keep wlroots' description. The
  root cause, a NULL passed to `%s`, is wlroots'; an upstream fix there would make the
  patch unnecessary.

- Brightness (owner: "the display brightness should work"). Noctalia skipped
  `/sys/class/backlight/backlight` with "could not be matched to an active output". The PWM
  backlight is a platform device with no link to the DSI connector, so the Monitor tab's
  slider showed "Disabled".
- `noctalia.toml` now pins it with `[brightness.monitor.DSI-1] backlight_device = "backlight"`.
  Applied live on card-23, Noctalia logged that it used the configured backlight for DSI-1.
  Writes go through logind's `SetBrightness`. A kernel-side link between the panel and its
  backlight might make the pin unnecessary.

- Owner, tried live on card-23: 2.2 and then 2.3 for the output scale ("ok perfect! let's bake
  this in the next card"), and "bar text scale should be 1.3". `umbriel.toml` sets
  `[output.DSI-1] scale = 2.3`, giving a desktop of about 939x470 (it was 864x432), and `noctalia.toml` sets `[bar.default] font_scale = 1.3` (it was
  1.15). The clock's own `font_scale` 1.3 stays.

Card-25 (dev VM, `gemini-base` 30 and Umbriel `pkgrel` 5, image sha256 `299d4ac7c28d…`, 429
packages, root 2.55 GB used) pairs with `station-work-91` or later. It carries `gemini-base` 26
to 30: the simpler bar, Bluetooth at boot with the radio off, the simple launcher, mpv, and the
changes above. Checked read-only on the image:

- Umbriel's and Noctalia's config checks pass. A first build had appended the icon scales as
  repeated `[widget.*]` tables, which TOML rejects. The scales now sit in the existing tables.
- `AutoEnable=false` is set and `bluetooth.service` is enabled.
- `/etc/mpv/scripts/mpris.so` is present.
- `umbriel` contains the "Built-in display" description.

Untested on the device. The UCM audio profile is not in it; it waits for the audio session's
test.

### Suspend on lid close, with the radios unloaded (`gemini-base` 31, 2026-11-10)

From the [power-management record](../2026-11-06-gemini-power-management/README.md)
("Owner decisions: charger wake, Wi-Fi across a suspend"): the owner approved unloading and
reloading Wi-Fi around a suspend ("wifi unload/reload during a suspend is ok"). The kernel
refuses a suspend while CONSYS is loaded (0653), so the card needs a `systemd-sleep` hook.

`/usr/lib/systemd/system-sleep/gemini-radios`:

- **`pre`:**
  - It stops iwd and bluetoothd if they are running.
  - It records them, and which of `mac`, `mt6797-wlan-core`, `btmt6797`, `gnss-mt6797`,
    `radio-mt6797` and `mt6797-consys` are loaded, in `/run/gemini/sleep-radios`.
  - It unloads them in that order. A module still busy is retried once a second for up to
    10 s; on the station, `mt6797-wlan-core` returned EAGAIN once just after `mac` went.
- **`post`:** it restores only what was loaded:
  - Wi-Fi through `wifi-start`, the card's boot path, which sets the country and loads the
    modules in its proven order. If only CONSYS was loaded, it loads just
    `mt6797-wlan-core` and `mt6797-consys`.
  - Then Bluetooth and FM through `hw-load`, GNSS through `modprobe`, and then the daemons
    that were running.
- If an unload still fails, the hook lets the suspend go on, and the kernel refuses it
  safely.

The logind and sleep settings follow the record:

- `HandleLidSwitch=suspend`, while `HandleLidSwitchExternalPower` and `HandleLidSwitchDocked`
  stay `ignore`.
- `[Sleep] MemorySleepMode=s2idle`, in `sleep.conf.d`, until the cpuidle work makes `mem`
  the default.

Checks:

- ShellCheck passes.
- A local run with stub `modprobe`, `systemctl`, `wifi-start` and `hw-load`, and a fake
  `/sys/module`, gave the expected sequence:
  - with iwd running, and `mac`, `mt6797-wlan-core`, `btmt6797` and `mt6797-consys` loaded,
    `pre` recorded them, stopped iwd, retried `mt6797-wlan-core` once and left nothing
    loaded;
  - `post` ran `wifi-start` and `hw-load bluetooth`, restarted only iwd, and removed the
    state file.
- Untested on the device. The power-management session's R-W test (lid closed for 60 s with
  Wi-Fi joined) decides it.

Card-26 (dev VM, `gemini-base` 31, image sha256 `8848f0e6ab68…`, 429 packages) is card-25 plus
the hook. On the image: `gemini-radios` is installed mode 0755, `sleep.conf.d/50-gemini.conf`
sets s2idle, and `logind.conf.d/50-gemini.conf` sets lid suspend on battery only. Pair it only
with a kernel that refuses a suspend while CONSYS is loaded (0653) or a charger is attached
(0630): with this card, closing the lid suspends. The custodian pairs it with
`station-work-97` (from `bca6ccc6`) or a descendant, which carries both; `station-work-96`'s
0630 guard refused both `mem` and `s2idle` with the cable in. The R-W test follows the
current `station-work-97` tests.

**Unload order fixed (`gemini-base` 32).**

- Card-26's `pre` would have failed on the device. The custodian measured on
  `station-work-97` (boot `56832cd1`) and `station-work-96`: `mt6797_wlan_core` returns
  EAGAIN for as long as `mt6797_consys` is loaded.
  - After `mac`, ten 1 s retries still failed.
  - Once CONSYS was unloaded, `rmmod mt6797_wlan_core` succeeded at once.
  - The earlier "retry after 2 s" had CONSYS removed in between.
- The hook now unloads `mac`, `btmt6797`, `gnss-mt6797` and `radio-mt6797`, then
  `mt6797-consys`, then `mt6797-wlan-core`. Bluetooth, GNSS and FM call CONSYS's exported
  STP functions, so CONSYS can't unload while they are loaded. That follows from the code
  (suspend session), but is untested on the device. The power-management record has the same
  order (`94bc6cb2`).
- The 10 s retry stays, for a module still busy for a moment after its user went.
- `post` is unchanged.
- A stub run in which `mt6797-wlan-core` refuses while CONSYS is loaded, and CONSYS refuses
  while any of its users is, unloaded everything first time. It then restored Wi-Fi,
  Bluetooth, FM and both daemons.
- Card-27 (dev VM, `gemini-base` 32, image sha256 `a1a0e7ae25d8…`, 429 packages) replaces
  card-26, with the same pairing (`station-work-97` or a descendant).

### GNSS daemon and gpsd (`gemini-base` 33, 2026-11-10)

The owner asked, relayed by the custodian: "Do we have the gnss userland to produce a fix and
position? If not can we write it and package it for arch on the sdcard?" The GNSS session
wrote `gnss-mt6797d` ([its record](../2026-11-10-gemini-gnss-daemon/README.md), `4f6ef122`).
It runs the MT6797 GNSS DSP through `/dev/gnss0` and publishes NMEA on a pty at
`/run/gnss-mt6797/nmea`.

- **Build:** `build-card.sh` builds that package from the GNSS session's directory, the same
  way as `gemini-base`, and installs it. Its hash goes in `card.json`.
- **Not enabled:** `gnss-mt6797.service` isn't enabled, since starting it switches the GPS
  radio on.
- **Needs:** a kernel with 0636, and `gnss_dsp_6797.bin`, which `gemian-firmware` already
  makes from the owner's Gemian.
- **gpsd:** `gemini-base` now depends on `gpsd`, and `build-card.sh` enables `gpsd.socket`.
  The unit hands its pty to gpsd with `gpsdctl add`. With no gpsd control socket, `gpsdctl`
  starts gpsd itself, here inside the unit's sandbox, with `PrivateNetwork`, where no client
  could reach it. Socket activation keeps gpsd off until a client or `gpsdctl` connects.
- **Sleep hook:** `gemini-radios` now also stops and restarts `gnss-mt6797.service`. Without
  that, the daemon's open `/dev/gnss0` would keep `gnss-mt6797` loaded, and with it CONSYS,
  so every suspend would be refused while GPS ran.
- Not run on the device. The daemon was tested offline by the GNSS session (replays, a
  fake-device loop, and gpsd 3.25 reading its pty in the dev VM).

Card-28 (dev VM, `gemini-base` 33, image sha256 `0368fe4e9a2c…`, 432 packages, root 2.55 GB
used) is card-27 plus the GNSS daemon and gpsd, and pairs with `station-work-98` (`47b11c27`,
which has 0636) or a descendant. Checked read-only on the image:

- `gnss-mt6797d` 1-1 and gpsd 3.27.5 are installed;
- `gpsd.socket` is enabled, and nothing under `/etc/systemd/system` enables
  `gnss-mt6797.service`;
- `gnss-mt6797d --help` runs under the card's Python 3.14.9;
- the sleep hook lists `gnss-mt6797`.

### GeoClue for every application (`gemini-base` 34, 2026-11-10)

Owner, relayed by the custodian: "It needs to be done in a standard way for all software that
require a position to be able to use it." gpsd serves libgps clients, but desktop applications
and browsers ask GeoClue. The design was agreed with the GNSS session.

- **GNSS package** (`712770f4`):
  - The daemon now also serves its NMEA on a UNIX socket, `/run/gnss-mt6797/nmea.sock`
    (group `geoclue`, 0660). Arch Linux ARM's GeoClue 2.8.2 reads that socket through
    `[network-nmea] nmea-socket=`, which the package's
    `/etc/geoclue/conf.d/90-gnss-mt6797.conf` sets.
  - The package now depends on gpsd and geoclue. `build-card.sh` copies that conf file too.
- **Agent:**
  - GeoClue answers an application only once an agent authorises it, or once its config lists
    the application with `allowed=true` (Firefox and Epiphany are listed).
  - Neither Umbriel nor Noctalia runs XDG autostart entries, so `umbriel.toml`'s autostart
    starts GeoClue's demo agent, `/usr/lib/geoclue-2.0/demos/agent`, which GeoClue's
    whitelist accepts.
  - In the GNSS session's VM test, GeoClue 2.7.0 with this agent and drop-in gave 406
    locations described "GPS GGA" from the daemon on a fake device.
- **No network sources:** `gemini-base` installs `/etc/geoclue/conf.d/95-gemini.conf`, which
  turns off GeoClue's IP, Wi-Fi, 3G, CDMA and modem sources.
  - Otherwise an application asking for a position while GPS is off would make GeoClue send
    the device's address to an online lookup service (BeaconDB by default).
  - Positions come only from the GNSS receiver, and a later conf.d file can turn a source
    back on.
- **Radio unchanged:** GPS stays off until `gnss-mt6797.service` is started. An application
  asking GeoClue gets no position until then.
- Qt's GeoClue 2 positioning plugin, which QtWebEngine and so qutebrowser use, was already on
  the card (`qt6-positioning`).

Card-29 (dev VM, `gemini-base` 34, GNSS package from `230df821`, image sha256
`860fb1ef9bc6…`, 438 packages, root 2.57 GB used) supersedes card-28. It pairs with
`station-work-98` or a descendant. Checked read-only on the image:

- geoclue 2.8.2, gpsd 3.27.5 and `gnss-mt6797d` are installed;
- `/etc/geoclue/conf.d` holds `90-gnss-mt6797.conf`, which sets the NMEA socket, and
  `95-gemini.conf`;
- the demo agent is at the autostart path;
- the `geoclue` and `uucp` groups exist;
- `gpsd.socket` is enabled, and Umbriel's config check passes.

Not run on the device.

### The processor's name (2026-11-10)

The owner: "the cpu is marked as 'Unknown', it would be good to address it". Noctalia's System
panel showed "Unknown CPU".

- **Cause:** Noctalia 5.4.1 reads the CPU name only from `/proc/cpuinfo`'s "model name"
  (`src/system/hardware_info.cpp`), which arm64 kernels never print. Upstream main has not
  changed it. A kernel `soc0` entry alone would not help, since Noctalia never reads it.
- **Patch:** `noctalia/gemini-cpu-name.patch` falls back the way `lscpu` and fastfetch
  describe ARM processors:
  - the SoC from `/sys/devices/soc0/machine`, else from the device tree's last `compatible`
    entry, through a small vendor table;
  - and the online cores, decoded from their implementer and part numbers.
  - A "model name" still wins where the kernel prints one.
- **Expected on the Gemini:** "MediaTek MT6797 (8× Cortex-A53)". The Cortex-A72 cores are
  offline, so they are not listed.
- **Tested:** standalone against fake roots: the Gemini, a mixed Rockchip SoC with and
  without `soc0`, and one with nothing to describe, which keeps "Unknown CPU".
- **Package:** `noctalia/` is the repository's 5.4.1 recipe (Arch's packaging) with that
  patch, as `pkgrel` 1.1. That is newer than the repository's 5.4.1-1, and its next release
  replaces it.
- **build-card.sh:** builds it like Umbriel, through one `build_local` function. Each
  package's dependencies and build tools come from its own PKGBUILD.

### A GPS switch in Noctalia (`gemini-base` 35, 2026-11-10)

The owner, in the GNSS session: "I don't want the gnss to be up by default, only when
activated in noctalia (if possible)". The GNSS package (`4e6b52c8`) adds:

- a Noctalia plugin, `gemini/gnss`, under `/usr/share/noctalia/plugins/gnss/`, with a
  control-center tile that starts and stops `gnss-mt6797.service`;
- a polkit rule that lets the active local session start, stop and restart that one unit
  without a password.

`build-card.sh` now copies the GNSS package directory whole, since its sources include the
`noctalia-gnss/` plugin at that path. `noctalia.toml` now:

- enables the plugin and adds a `gemini` path source at `/usr/share/noctalia/plugins`.
- keeps Noctalia's `official` and `community` git sources listed. An explicit
  `[[plugins.source]]` list replaces Noctalia's defaults (`src/config/config_service.cpp`).
- lists the control-center tiles: Wi-Fi, Bluetooth, GPS, caffeine, night light and
  notifications. An explicit list replaces the defaults here too.
  - The Home tab shows six tiles, so the default power-profile tile is the one left out;
    the card has no power-profiles-daemon.
  - The GNSS session raised the six-tile limit.

The bar gets no GPS indicator, since the owner asked for a simpler bar. The service is still
not enabled. Whether Noctalia loads the plugin, and the polkit rule lets its commands
through, can only be seen on the device; the GNSS session folds those checks into its GPS
device run.

Card-30 (dev VM, `gemini-base` 35, Noctalia 5.4.1-1.1, image sha256 `242eb0601f46…`, 438
packages, root 2.57 GB used) is card-29 plus the processor name and the GPS switch. It pairs
with `station-work-98` or a descendant.

Checked read-only on the image:

- the Noctalia binary carries the new core names;
- the plugin's three files and `50-gnss-mt6797.rules` are installed;
- Noctalia's `config validate` passes with the plugin, sources and tiles;
- no build tool (gcc, meson, base-devel, stb, fakeroot) is left.

Two build fixes on the way:

- Noctalia's compile ran the 8 GiB dev VM out of memory at ninja's default ten jobs, so the
  recipe uses four.
- makepkg looks up a local source by its file name, so `build-card.sh` also copies the
  plugin files flat beside the GNSS PKGBUILD.

### Clock at the top, no launcher button (`gemini-base` 36, 2026-11-11)

The owner, trying it live on card-27 (boot `58bcf387`): "move the clock to the top of it" and
"I don't need the search under the clock, remove this icon", then "Keep it". `noctalia.toml`'s
bar now has `start = ["clock", "workspaces"]`, an empty centre, and the same end section. The
launcher stays on Ctrl+Alt+Space and the side key, so the launcher widget's scale entry goes.
Noctalia's `config validate` passes. It is in no card image yet, and rides with the next one.

### A charge-limit switch (`gemini-base` 37, 2026-11-11)

The owner asked for a charge-limit switch in Noctalia's Power tab. The kernel side, a
`charge_control_end_threshold` of 80 from boot, is 0695 and needs the next station image.
UPower 1.91.5, read in its source and on the card-30 image:

- UPower offers the control only for a battery whose udev properties include `CHARGE_LIMIT`.
  `61-gemini-charge-limit.rules` sets `75,80` on the `battery` power supply. A live sysfs
  end threshold between 1 and 99 overrides the 80.
- Switching on writes those thresholds to sysfs, and switching off writes 0 and 100. The
  choice is saved as a bare `1` or `0` in `/var/lib/upower/charging-threshold-status`, which
  the upower package leaves absent, so UPower would start with the switch off. A tmpfiles
  `f` line creates it as `1`, matching the kernel's 80, and leaves an existing file alone
  (checked with `systemd-tmpfiles --root`, which wrote one byte, `1`).
- At start-up UPower writes the thresholds only when the saved switch is on. With it off, the
  kernel's 80 would come back after a reboot while Noctalia showed the limit off. The same
  udev rule runs `charge-limit` when the battery appears, which writes 100 when the saved
  switch is `0`. udev runs it before announcing the battery, so UPower sees the corrected
  value.
- `org.freedesktop.UPower.enable-charging-limit` allows an active local session without a
  password, and upower's own polkit rule doesn't touch it. The autologin session on tty1 was
  active on `seat0` in the R4 diagnostics above, so the card needs no polkit rule.

`udevadm verify` passes on the rule and ShellCheck on the script. It rides with the next
card; the switch itself is not tried on the device yet.

Built into card-31 (image `a6da8be0…`, gemini-base 37 `92c80879…`), from main `7f6b6baf`.
On a read-only mount of the image: the rule, the script, the tmpfiles line and the new bar.

### Speaker, headphones and microphone through UCM (`gemini-base` 38, 2026-11-11)

The [audio UCM profile](../2026-11-08-gemini-audio-ucm/README.md) passed on card-31 (its
record, main `2b0c1623`): with `alsaucm` and PipeWire stopped, Speaker, Headphones and Mic
each set only their own switches, the owner heard each tone on the right output, and the
microphone captured. So gemini-base now uses it instead of its manual sink:

- `build-card.sh` stages the profile's two files beside the PKGBUILD, as it does
  `audio-start`, and gemini-base installs them under `/usr/share/alsa/ucm2/`
  (`conf.d/mt6797-mt6351/mt6797-mt6351.conf` and `Gemini/HiFi.conf`). It depends on
  `alsa-ucm-conf` now, whose `ucm.conf` leads alsa-lib to `conf.d`.
- The PipeWire sink on `hw:mt6797mt6351,0` and the WirePlumber rule that disabled the card
  are gone, so WirePlumber makes the devices from the profile. `audio-start` stays.
- `first-login` mutes the default source once (owner, on card-31: the microphone muted by
  default), with its own marker, so a card that already ran it mutes once at the next login.
- The output starts at 60% (`gemini-base` 39, owner on card-31: YouTube "all works" at 0.60).
  The earlier saturation was a kernel bug, not a level problem: PipeWire opens the PCM as
  S32_LE and the AFE read the low 24 bits of each word, about 48 dB too loud. Kernel patch
  0712 fixes it and 0707 removes the speaker click at start (main `5abb47f2`). The 35% before
  was tuned to the bug. The card carries no kernel, so 60% holds only with a station image
  that has both; with an older one it distorts on the speakers.

ShellCheck passes on `first-login` and `build-card.sh`; the package isn't built yet. To
check at the first boot: Noctalia shows "Speaker" as the output and "Mic" as the input, a
headphone plug switches the output, and the microphone starts muted.

### PipeWire found no profile on card-32 (`gemini-base` 40, 2026-11-11)

Card-32 (image `694dd988…`, gemini-base 39) on station-work-101, boot `0bad0df9`: the
output was PipeWire's Dummy Output. ACP probes each UCM profile by opening its PCMs before
enabling any device, so capture PCM 3 opened with its route off; the kernel answered
"Capture_1: ASoC: no backend DAIs enabled" and EINVAL, and both HiFi profiles, which each
include Mic, were dropped (`spa-acp-tool`: "input PCM open failed"). The custodian moved the
two `UL1_CH* ADDA_UL_CH*` route switches into the verb's EnableSequence in a temporary
`ALSA_CONFIG_UCM2` copy, and PipeWire then chose "HiFi (Mic, Speaker)" with the sink "Built-in
Audio Speaker" and the source "Built-in Audio Mic". The microphone switches still gate the
capsules. The audio session made the same change in its profile (`4e52b4f4`), and
gemini-base 40 carries it. `first-login` behaved as meant: with no sink it left no marker,
so it retries at the next login.

Installed live on card-32 (package `8a75f1b7…`, boot `0bad0df9`), with the custodian's
temporary override removed and PipeWire restarted: Active Profile "HiFi (Mic, Speaker)", sink
"Built-in Audio Speaker" at 0.60, source "Built-in Audio Mic" muted. Capture through
PipeWire works: with the microphone briefly unmuted, a 1 kHz tone at -15 dBFS from `pw-play`
on the speaker gave a `pw-record` Goertzel 1 kHz magnitude of 84–94 on the left channel and
53–60 on the right, against about 1.0 before the tone; the microphone was muted again after.
Not yet tried: headphone switching (needs headphones plugged in), pops at capture start.

### Keeping the learned battery capacity (`gemini-base` 41, 2026-11-11)

The owner approved the fuel-gauge session's learned capacity
([its record](../2026-11-11-mt6351-fuel-gauge/README.md), "Learned capacity"): kernel patch
0732 makes `charge_full` (µAh) writable, accepting 50–110 % of the 4268000 µAh design (ERANGE
otherwise), and raises a change uevent when the driver learns a new value. The kernel forgets
it at power-off, so gemini-base keeps it:

- `battery-capacity restore`, from `62-gemini-battery-capacity.rules` when the battery
  appears: writes `/var/lib/gemini/battery-charge-full` back into `charge_full`. A missing or
  non-numeric file, or an ERANGE, changes nothing. The driver answers ENODATA for a moment
  after the battery registers, so the write is tried three times, 1 s apart. udev runs it
  before announcing the battery, so UPower sees the learned value first, as with the
  charge-limit restore. The successful write raises a change uevent, which finds the value
  already saved.
- `battery-capacity save`, from the same rules on each change uevent and from
  `gemini-battery-capacity.service` at shutdown: writes the value only when it differs from
  the file, and never creates the file with the design value, so a fresh install keeps none
  until something is learned. Change uevents are frequent; the save costs one attribute read.
- From 0736 (`a7c590bc`, "charger finished = 100 %"), the driver reports `charge_full` and
  `charge_full_design` as usable charge, a fixed 93 % of the table charge: 3969240 µAh at
  design, writes accepted from 1984620 to 4366164. A number saved under 0732's scale would
  restore about 7 % high, and card-32's file already held 4268000 from a test write. So from
  `gemini-base` 46 the file holds "charge_full charge_full_design" as read when saved, and
  the restore writes value × today's design ÷ saved design. A single number is 0732's
  format, taken with a design of 4268000. That is exact in both directions and for any later
  scale change. Checked against a fake sysfs: 0732's 4268000 restores as 3969240 on 0736
  (health 100 %), a 0732-learned 3500000 as 3255000, and a 0736-saved 3600000 as 3870967 on a
  0732-only image; non-numeric or zero fields change nothing. While the driver answers
  ENODATA it does so for the design value too, so from `gemini-base` 47 the design is read
  inside the three tries (checked with the design file appearing 1.5 s late).
- A battery swap isn't detected: the driver exposes no serial or model name, and the cell
  has only an NTC. After fitting a new battery, `rm /var/lib/gemini/battery-charge-full`, and
  the gauge learns the new cell over its cycles.

`gemini-battery-calibrate` (root) walks the owner through one calibration cycle with the
charge guard's thresholds (0695), restoring the user's own on any exit, Ctrl-C included:

1. End 100 and start 99, so it charges to full; once charging stops and the current is within
   ±20 mA, 30 min plugged in for the rested full reading.
2. End 50 and start 0. The guard's end can't go below 50, but its "full" latch holds from the
   end down to the start, so with the battery full the latch holds charging through the
   discharge. The owner unplugs and uses it down to 20–30 %, then plugs in again.
3. Charging is held at that level for a 30 min rested low reading. If it charges instead, the
   helper stops.
4. It reports `charge_full` before and after and the gauge's "full charge" log lines.

It warns when a step breaks the gauge's rules (15–35 °C and within 10 °C of each other,
readings 40 points apart, within 72 h on the same boot), and restarts a 30 min count when the
current or temperature leaves its window. The gauge takes each reading at the first capacity
read after the 30 min, which UPower's polling provides. Accepted pairs show in `dmesg` as
"full charge N uAh from M uAh over P points"; rejections only at debug level, which the helper
says how to enable when nothing was learned.

What ends the hold (charging session, checked against the guard): nothing in the guard clears
the latch on unplug or replug, but a reboot or power-off does (the next boot starts at
80/75, and powered off with the cable in the bootloader charges unguarded), as does anything
that rewrites the thresholds: Noctalia's charge-limit switch, a UPower restart, or any write
of end 100. The helper tells the owner not to power off or touch the switch, checks that the
thresholds still read 50/0 at every poll while holding, and stops if they don't or if the
battery charges. Both rested readings need the charger to carry the whole system, so it
asks for a wall charger and an idle screen (`gemini-base` 43).

Checked: ShellCheck on both scripts; `udevadm verify` on the rule; the save and restore logic
against a fake sysfs directory (fresh design value: no file; learned value: saved; restore;
non-numeric file: ignored). Not on a device: it needs a station image with 0732, which isn't
on one yet: the first station image built at or after `b4cf64c0` (station-work-107 has only
0730, where `charge_full` is read-only). The custodian verifies it once it is. Whether the
guard leaves the battery idle (within ±20 mA) while holding is asked of the charging
session.

### The screen turns off when idle (`gemini-base` 42, 2026-11-11)

The card had no screen blanking. The owner: "I'd like 10min if plugged, 2min if not", screen
off only, no lock. Noctalia's idle manager does it over `ext-idle-notify`, with Umbriel
turning the output off and on, and it respects idle inhibitors: Wayland idle-inhibit, and
`org.freedesktop.ScreenSaver` over D-Bus, which browsers use during video.

Noctalia 5.4.1 gives each idle behavior one timeout, with no power-source condition, but it
reloads its config directory on change and has hooks for Noctalia's startup and for the
battery's state. No patch is needed:

- `00-gemini.toml` turns on `[idle.behavior.screen-off]` (`action = "screen_off"`, 120 s), and
  sets the hooks `started`, `battery_charging`, `battery_discharging` and `battery_plugged`
  to `/usr/lib/gemini/idle-timeout`.
- `idle-timeout` writes `~/.config/noctalia/50-gemini-idle.toml` with 120 s when the battery
  reads Discharging and 600 s otherwise, which includes holding at the charge limit. It
  writes only a changed file, atomically, and Noctalia reloads it.
- The user's own `config.toml` sorts after `50-gemini-idle.toml` and wins, as do settings
  changed in Noctalia's Settings window, so a timeout the user picks there holds on both
  power sources. `noctalia msg config-set` was not used, because it stores into those same
  user overrides.

Checked against card-32's Noctalia 5.4.1: `noctalia config validate` passes, and with a 600 s
`50-gemini-idle.toml` beside it, `config export full` gives `timeout = 600.0` and lists the
four hooks. ShellCheck passes on the script. Not on the device yet. Since `/etc/skel` reaches
only new users, an existing user needs the new `00-gemini.toml` copied into
`~/.config/noctalia/`.

### Battery temperature and a compact battery card in Noctalia (noctalia 5.4.1-1.3, 2026-11-11)

The owner asked to see the battery temperature in Noctalia's Power tab, and for a more
compact battery panel. Neither is configurable in Noctalia 5.4.1, so both are patches in our
noctalia package, kept apart:

- `gemini-battery-temp.patch`: Noctalia reads UPower's `Temperature` with the other battery
  properties, and the battery card shows it under the charge rate ("25.7 °C"), only when it
  is above 0. The first build showed nothing on card-32 (station-work-107, boot `a1651d02`):
  UPower's DisplayDevice reports 0 for `Temperature` while `battery_battery` reports 25.3, so
  the state built from the display device now takes the temperature from the system
  battery. The same change is drafted for upstream Noctalia and checked on its main branch
  (build, clang-format 23, clang-tidy); it is not opened.
- `gemini-power-compact.patch`, the owner's choice B of three layouts: the time left follows
  the state ("Discharging · 3h 20m"), and the rate, temperature and battery health share one
  line, so the separate Battery Health card goes. `power_tab.cpp` only; not for upstream.

Built in an Arch chroot over card-32's image (`5.4.1-1.3`, `c738be76…`). Not yet seen on the
device.

### The owner's sudo policy survives upgrades (`gemini-base` 44, 2026-11-11)

`/etc/sudoers.d/10-gemini-wheel` (wheel may use sudo with a password, and `chvt 2` without
one, for Ctrl+Alt+Tab) wasn't a `backup=` file, so each `pacman -U` of gemini-base replaced the
owner's edit: on card-32 their NOPASSWD rule went with gemini-base 40 and again with 42
(journal 16:52:29 install, 16:52:54 "a password is required"). It is in `backup=` now: an
edited file stays, and an upgrade that changes the package's copy installs it as `.pacnew`
beside it. A fresh card keeps the same default; the policy itself is unchanged.

Tested in an overlay over card-32's image: gemini-base 42 installed, the file edited to a
NOPASSWD rule, then 44 (`50546fcc…`) installed. pacman warned "installed as
10-gemini-wheel.pacnew" and the edit stayed. sudo ignores `sudoers.d` files whose names
contain a dot, so the `.pacnew` copy has no effect.

On card-32 (custodian, after the owner restored NOPASSWD): 44 installed with the `.pacnew`
warning, and `sudo -l` still shows "(ALL : ALL) NOPASSWD: ALL". pacman also warned "directory
permissions differ on /etc/sudoers.d/": `install -D` made the directory 0755 in the package,
while sudo's is 0750. gemini-base 45 (`cd908a63…`) creates it as 0750 first; its listing shows
`drwxr-x---`.

### Low-battery policy and a voltage backstop (`gemini-base` 48, 2026-11-11)

The fuel-gauge session measured the owner's original cell at about 0.39–0.44 Ω under sustained
load, 2.5× the device tree's new-cell 165 mΩ. At 1.8 A the terminal sits about 0.7 V below the
open-circuit voltage, about 3.0 V at a true 20 %, so heavy use near empty can brown out before
UPower's stock poweroff at 2 %. UPower 1.91.5 acts only on a percentage or a time to empty,
never on voltage. The owner chose (through the custodian):

- UPower, in `/etc/UPower/UPower.conf.d/50-gemini.conf`: low at 20 %, critical at 12 %, and a
  clean poweroff at 8 % (`CriticalPowerAction=PowerOff`, as `Auto` resolves on a card without
  hibernation). UPower needs the three to run downwards, or it falls back to its defaults.
- Noctalia's low-battery notification at 20 % (`[battery] warning_threshold`), with UPower's
  low.
- A voltage backstop, `gemini-battery-guard.service`: while the battery reads Discharging, it
  reads `voltage_now` every 10 s. Three reads in a row under `MIN_UV`
  (`/etc/gemini/battery-guard.conf`) make it notify each user session over
  `org.freedesktop.Notifications` with `gdbus` (the card has no `notify-send`), wait 10 s and
  power off. A short spike resets the count. `MIN_UV` is 3.00 V from `gemini-base` 49, the
  fuel-gauge session's number: the MT6351 cuts the board off below its UVLO (2.60 V in the
  vendor kernel; mainline leaves the bootloader's value), load bursts between polls sag
  about 0.25 V further, and VSYS sits about 0.05 V below the battery. The first placeholder,
  3.30 V, would power off a healthy battery under heavy use: a browser session read 3.48 V at
  90 %. At 1.8 A, 3.00 V trips around 15–20 % charge; at 0.5 A or less it never trips before
  the gauge reads empty. It may move within 2.95–3.10 V once the fast-step resistance and the
  actual UVLO are measured.

Both configuration files are `backup=` files. Checked: `noctalia config validate` against
card-32's Noctalia; the guard's logic against a fake sysfs (charging at low voltage: no
action; discharging at 3.5 V: none; at 3.2 V: poweroff after the third read; two low reads
then recovery: none); ShellCheck. Not on a device. The custodian installs it after the owner's
calibration, since a poweroff mid-cycle would lose it.

The owner then asked for behaviour that adapts to the battery, not values tuned to this cell
("what will happen with the same setting on other devices?"), and approved the fuel-gauge
session's adaptive design (its record, "Adaptive resistance"): the gauge learns the cell's
resistance, and 0 % becomes the charge at which the cell, under its recent typical load,
reaches the cut-off. With that, `gemini-base` 50 replaces 48–49's battery-specific choices;
48 and 49 were never installed:

- No UPower drop-in: UPower's own defaults stand (low 20 %, critical 5 %, a clean poweroff at
  2 % through `Auto`, which resolves to PowerOff on a card without hibernation), since 0 %
  now means "about to reach the cut-off".
- The guard at 3.10 V, the same on every Gemini: the bootloader sets the MT6351's hardware
  cut-off (UVLO) to 2.70 V on every unit (`CHR_CON17` `0x0F9A` = `0x0004`, read by the
  custodian), plus 0.25 V for load bursts between polls (up to 1 A at an aged cell's fast
  resistance of up to 0.25 Ω), 0.05 V across the BATFET and a 0.10 V margin. The adaptive
  gauge reaches 0 % at 0.10 V above it, so the guard only catches what the gauge misses.
- Noctalia's warning stays at 20 %.


### Keeping the adaptive gauge's capacity and resistance (`gemini-base` 51, 2026-11-11)

The adaptive gauge (0745–0746, `1f532f3b`) learns a full charge Q and a resistance R, and
makes `charge_full` read-only and load-dependent. They are under the battery's platform
device: `learned_full_uah` and `learned_resistance_uohm` (read-write; Q is held within 50–110 %
of its basis, R within 50000–1500000 µΩ, ERANGE otherwise), with read-only bases
`design_full_uah` (4268000) and `design_resistance_uohm` (165000). A change of either raises a
change uevent, as before.

In `gemini-base` 51 (superseded by 52, below), `battery-capacity` kept the same rules, file
and triggers, and chose by what the driver offers:

- With 0746, the file holds `full <Q> <basis>` and `resistance <R> <basis>`. Each restores as
  value × today's basis ÷ saved basis, the basis read inside the three tries. A file saved
  before 0746 (`<charge_full> <charge_full_design>`, or 0732's single number) restores as
  Q = value × 4268000 ÷ its saved design, and the save that follows rewrites it in the new
  format. Nothing is saved until Q or R differs from its basis, or a file exists.
- Without 0746, `charge_full` is restored and saved as in `gemini-base` 47. A file already in
  the new format is left alone, so booting an older station image doesn't lose R.

Checked against fake sysfs directories (11 cases): migrating "3969240 3969240" gives
Q = 4268000, "3800000 3969240" 4086021 (3800000 × 4268000 ÷ 3969240 = 4086021.5), and 0732's
4268000 gives 4268000; the save after a migration writes both lines; a fresh install writes
nothing; R learned alone is saved; changed bases rescale both values; on an older image a
new-format file neither restores into `charge_full` nor gets overwritten; an old file still
restores there; a non-numeric file changes nothing. ShellCheck passes. Not on a device: it
needs a station image with 0746.

The fuel-gauge session's answers from the 0745–0746 code then changed three things
(`gemini-base` 52, replacing 51, which was never installed):

- **When to restore.** The attributes are driver `dev_groups`, created only after probe
  returns, while the battery supply's `add` uevent fires during probe. 51's restore on `add`
  would have found no attributes and restored nothing. The rule now restores on the gauge
  driver's `bind` (`ACTION=="bind", SUBSYSTEM=="platform", DRIVER=="mt6351-fuel-gauge"`), and
  saves on the battery's change uevents as before.
- **Older images.** Without the attributes, the script does nothing, neither restore nor
  save: those are transitional development images, and the new file then never holds
  usable-scale values.
- **The file.** Q and R go to `/var/lib/gemini/battery-learned`. An old
  `battery-charge-full` migrates as Q = value × 4268000 ÷ its design when the gauge binds;
  the restore then writes the new file itself and removes the old one. The bind restore and
  a battery change can run in parallel, so until then a save is skipped while Q still reads
  its basis (it would store the unrestored value); a value learned since is saved anyway.
  A migration whose write fails keeps the old file for the next boot, and an unreadable old
  file is removed.

Checked against a fake sysfs (11 cases): migrating "3800000 3969240" gives Q = 4086021
(confirmed by the fuel-gauge session) and removes the old file; card-32's "3969240 3969240"
and 0732's 4268000 give 4268000; a save before the restore keeps the old file; a fresh
install writes nothing; R learned alone is saved; changed bases rescale both; an image
without the attributes leaves everything alone; a failed migration write keeps the old file;
a junk old file goes; a learned Q is saved even with the migration pending. The rule passes
`udevadm verify`. Not on a device: it needs a station image built at or after `1f532f3b`.

The same race remained for a file already in the new format (fuel-gauge session's review):
a battery change uevent beside the bind restore could save Q and R still at their bases
over the learned values, and the restore would then read the defaults. `gemini-base` 53 never
saves both-at-basis, except as the result of a migration; a learned or restored value
practically never sits exactly on its basis, and resetting is deleting the file. Two more
fake-sysfs cases: a save before the restore leaves a new-format file unchanged, and a restore
followed by a save leaves it unchanged too.

### Clean poweroff as UPower's critical action (`gemini-base` 54, 2026-11-11)

gemini-base 53 on card-32 (station-work-110, boot `0ce7590c`, custodian): UPower's
`GetCriticalAction` answered "Sleep". With no drop-in, `Auto` picks suspend when the system
can suspend, and suspend isn't reliable on the Gemini yet, so at the critical level it would
suspend and keep draining, against the owner's choice of a clean poweroff. `gemini-base` 54
ships `/etc/UPower/UPower.conf.d/50-gemini.conf` (a `backup=` file) with only
`CriticalPowerAction=PowerOff`; UPower's percentages stay its own.

The guard also read "disabled" after `pacman -U` and wasn't running. The package has shipped
its `multi-user.target.wants` symlink since 48, so it starts at every boot; pacman just never
starts a newly installed unit, and `systemctl` called it disabled because the unit had an
`[Install]` section with no symlink in `/etc`. The guard's and the capacity unit's
`[Install]` sections are gone, so both show as static. After an install, start them once by
hand or reboot.

### The calibration helper waits for the gauge (`gemini-base` 55, 2026-11-11)

The owner's first calibration on card-32 learned a full charge at 20:19; the helper then
restored the limits (95/100), charging resumed, and capacity jumped 44 → 76 within a minute.
The fuel-gauge session traced the jump to the gauge: the first read after charging resumed
still counted as a rest and took the charging voltage for an OCV. 0747 (`2c8894ed`) fixes it.
The helper's ending had one real weakness: it restored the limits as soon as its own
30-minute count ended, while the driver takes its reading at the first capacity read after
30 min of its own rest, which can start seconds later. It learned this time by timing.

`gemini-base` 55:

- turns the gauge driver's debug messages on for the cycle and off at exit, so its
  "learning: …" reasons show (needs debugfs);
- after the low rest, keeps charging held and reads the capacity every 30 s until the
  driver prints a new "full charge … from M uAh over P points" line, for up to 15 min, then
  shows the gauge's last "learning" lines if none came;
- reports the learned full charge before and after from `learned_full_uah` on the adaptive
  gauge (0746), whose `charge_full` is load-dependent, and `charge_full` before it;
- prints the pair's own estimate, M × 100 ÷ |P| (here 1963017 × 100 ÷ 51 = 3849 mAh), and
  that the learned value moves a quarter of the way toward it per cycle;
- on images before the adaptive gauge, says the capacity may read high until the next
  charge finishes.

ShellCheck passes; the line parsing was checked on the reported line. Not run on a device.

### Restoring Q and R at boot (`gemini-base` 56, 2026-11-11)

gemini-base 55 on station-work-112 (0745–0747, boot `71c291ae`, custodian): the restore never
ran at boot. `learned_full_uah` stayed 4268000 and the old file was untouched. The gauge
driver binds in the station's initramfs, before the card's udev starts, and udev's coldplug
replays add and change, not bind, so the `bind` rule never fired; the unit only saved at
start. Run by hand, `battery-capacity restore` did everything right: `learned_full_uah`
4163262, `charge_full` 3871833, UPower health 97.546 %, `battery-learned` written with
`full 4163262 4268000` and `resistance 165000 165000`, the old file removed.

`gemini-battery-capacity.service` now restores at start (after local file systems, before
UPower; only where `device/learned_full_uah` exists) and saves at stop. The `bind` rule stays
for a driver bound later. A second restore writes the same values.

### Hardware video decoding for the video group (`gemini-base` 57, 2026-11-11)

The vcodec session's VA-API test (V16) on card-32 stopped at `/dev/dma_heap/system`: root:root
0600, so the driver, running as the owner, could not allocate its frames ("Permission
denied"), and every CAPTURE QBUF failed. The system heap hands out ordinary memory that
several devices can share without copying: the decoder writes a frame into it and the GPU
can display it directly. systemd 262 grants the decoder's own `/dev/video*` and
`/dev/media*` to group `video` (0660) plus an ACL for the active local session, the DRM render
node to everyone (0666), and the heap to nobody.

The owner wants hardware decoding for any session, remote ones included, so not by the
active-session ACL; and chose the video group over opening the heap to everyone:

- `71-gemini-dma-heap.rules`: `SUBSYSTEM=="dma_heap", KERNEL=="system", GROUP="video",
  MODE="0660"`, the system heap only.
- `firstboot` creates the user in `wheel,video`, so the decoder nodes and the heap open to
  them from any session. An existing card needs `usermod -aG video USER` once, then a new
  login.

The cost: a member can take memory through the heap that isn't charged to its memory
cgroup. `udevadm verify` passes on the rule, ShellCheck on `firstboot`. Not on a device yet.

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
