# Experiment: a long-running mainline development station

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-30-mainline-dev-station` |
| Status | `running`: station, lid, brightness, blanking and Wi-Fi load work; unload works, re-attach is refused by the HIF's one-time configuration window (boot `caac239d…`, 2026-10-30) |
| Subsystem | development method; RAM root; eMMC data mount; kernel modules |
| Device variant | named Gemini PDA (MT6797X), boot2 |
| Date(s) | 2026-10-30 |
| Investigator(s) | project custodian |
| Tracking issue | none |

## Question or hypothesis

Every boot so far has been a bounded session:
- a logger deadline;
- SSH limits;
- a sealed export;
- a return.

The owner's challenge: boot one mainline kernel that simply stays up as a
development machine.

**Hypothesis.** One boot of the station kernel and RAM root gives, together
and with nothing else:
- all eight A53 cores online;
- key-only SSH over the USB Ethernet gadget, with no session limits;
- a local shell on the console, typed on the Gemini keyboard;
- a RAM root of at most 1 GiB;
- Gemian's `linux` partition mounted read-write at `/mnt/data`;
- the Wi-Fi mac80211 layer built as a module (`mac`), present in the RAM root
  and not loaded.

It is falsified by any of these missing on the booted station.

Loading `mac`, Wi-Fi joins and module reloads are not part of this test. If
it holds, the methodology is revised separately.

## Provenance and environment

- **Kernel:** Linux 7.1.3 with `patches/series-a53-station`, which is the
  soak series (`series-a53-wifi-soak`: AV's series plus 0336 and 0337) plus
  [0338](../../patches/proposals/0338-wifi-mt6797-build-the-mac80211-layer-as-a-loadable-m.patch).
  The profile is `mt6797-a53-station` and the release is
  `7.1.3-gemini-a53-station`.
- **Configuration:** the soak profile's fragments plus
  [`gemini-a53-station.fragment`](../../configs/gemini-a53-station.fragment).
- **RAM root:** built by [`build-station-initramfs.py`](build-station-initramfs.py)
  from the retained soak RAM root. That root supplies busybox, dropbear, the
  SSH keys, the keymap, the Wi-Fi firmware and the Wi-Fi tools.
- **Boot image:** composed by [`compose-station.py`](compose-station.py) with
  the soak candidates' container and LK checks.

## The change

**0338: the mac80211 layer as a module.** `MT6797_MAC80211` becomes
tristate.
- **Built in**, the CONSYS owner attaches the layer exactly as before,
  through one function, `mt6797_consys_wlan_attach()`. That function holds
  the same code: private record, registration, the initial TC4 accounting
  pair, then scan ready.
- **As the module `mac`**:
  - CONSYS still starts the firmware (on the `wmt_negotiate` trigger, as
    before) and keeps the started HIF;
  - loading `mac` runs that attach once;
  - a second attach is refused, as is one before the firmware is ready, and
    a failed attach is not retried;
  - there is no detach yet, so `mac` cannot be unloaded.
- The module keeps the name `mac`, so `/sys/module/mac/parameters` is
  unchanged.
- Its debugfs helpers stay built in, and the 40 functions it calls are
  exported GPL-only.

**The station fragment.** It turns modules on (with unload, no signing, no
modversions), sets `mac` to `m`, gives the station its own local version and
a 1 MiB log buffer.
- Turning modules on would move 115 defconfig drivers from built-in to
  modules that nothing loads. These include the PMIC keypad, the
  polled GPIO keys, SPMI and PWM. The fragment keeps each one built in.
- Against the soak kernel's resolved config, the station's differs only in:
  - modules (`MODULES`, `MODULE_UNLOAD`, `STRICT_MODULE_RWX`,
    `MODPROBE_PATH`);
  - `MT6797_MAC80211=m`;
  - the local version and the log buffer;
  - one new module-only option, `CRYPTO_BENCHMARK=m`, which nothing loads.

**The RAM root** ([`initramfs/`](initramfs/)):
- [`init`](initramfs/init):
  - mounts devtmpfs, proc, sys, devpts and a `/run` tmpfs;
  - installs the busybox applets;
  - caps the tmpfs root at 1 GiB;
  - records the CPUs, release and boot ID in `/run/station/status`;
  - mounts the one `mmcblk0` partition whose GPT name is `linux` at
    `/mnt/data` (ext4, `rw,noatime`), never choosing a partition by number;
  - then hands over to busybox init.
  - No step holds the boot: a failure is recorded and the rest still runs.
- [`inittab`](initramfs/inittab):
  - [`usb-ssh`](initramfs/usb-ssh) and [`console-shell`](initramfs/console-shell)
    are respawned;
  - at shutdown it syncs and unmounts `/mnt/data`, falling back to
    read-only if the unmount fails.
- [`usb-ssh`](initramfs/usb-ssh): `usb0` at `10.15.19.82/24` and dropbear,
  key-only, with no idle, session or file-size limits.
- [`console-shell`](initramfs/console-shell): a login shell on tty1 with the
  Gemini keymap.
- The parent's logger, seal, reboot wrapper and bounded session scripts are
  dropped. `mac.ko` is placed under `lib/modules/<release>/`.

**Lid handling (owner request after the first boot).**
- [`station-dt.sh`](station-dt.sh) derives the station board tree from the
  package's `wifi-service` tree (revised after boot `bac0f387`, below):
  - the hall node from 0074 is enabled as `gpio-keys-polled`, read every
    100 ms: GPIO66, active-low, `EV_SW/SW_LID`, 64 ms debounce, GPIO mode,
    no pull setting;
  - the PWM backlight is enabled (display H8): `pwm_sel` on the 26 MHz
    oscillator, 1024 levels at 39385 ns, default level 512. The PWM node's
    MM `power-domains` reference is removed;
  - the framebuffer is left as the package has it.
- **Why polled.** On five C1 boots
  ([C1 record](../2026-10-04-gemini-c1-preparation/README.md)) GPIO66's
  level followed the lid (high open, low closed), but EINT5 never fired. A
  pull-up, input-enable, no debounce and Schmitt were each ruled out, and
  boot `bac0f387` repeated the zero count. Polling uses the level, which works.
- **Why no MM reference.** This kernel registers only the CONN power domain
  (proposals 0012 and 0029). So every consumer of the MM domain defers
  forever, and nothing here can switch MM off.
- **Brightness keys.** `lid-guard` also reads the keyboard. With Fn
  (`KEY_LEFTMETA`) held, N steps the backlight up and B steps it down,
  through levels 16, 32, 64, 96, 128, 192, 256, 384, 512, 640, 768 and 1023,
  never fully dark. Autorepeat steps too.
  - The RAM root builder sets the console keymap's Fn entries for B and N to
    no action (`K_HOLE`). Before, Fn+B was a hex digit for typed code input,
    emitting U+000B on Fn release, and Fn+N typed `n`.
- **Screen blanking.** The kernel's console blank timer (`ESC [9;N]`,
  what `setterm --blank N` sends) blanks tty1 after 2 idle minutes, set by
  `console-shell`. Any key unblanks it.
  - The simple framebuffer cannot blank, so `lid-guard` checks the blanked
    console (`TIOCL_BLANKEDSCREEN`) once a second and powers the backlight
    down while it is blanked. The backlight is therefore off while the lid
    is closed or the console is blanked.
  - busybox has no `setterm`, so [`initramfs/setterm`](initramfs/setterm)
    implements `--blank N` (0 to 60 minutes, 0 off) and writes to tty1, so
    it works from SSH too.
- **Flashing boot2 from the station** (owner decision, 2026-10-30):
  [`initramfs/flash-boot2`](initramfs/flash-boot2) `IMAGE SHA256`.
  - **It refuses unless:**
    - the image is exactly 16 MiB with that SHA-256;
    - exactly one `mmcblk0` partition is named `boot2`;
    - that partition's sysfs and device-node numbers agree;
    - it is 16 MiB, writable, and neither mounted nor swap.
  - It records the predecessor checksum and skips an already matching
    partition.
  - It writes with `fsync`, syncs, drops the page cache and requires a
    matching full readback.
  - Selecting boot2 at the next boot stays a physical owner action. This
    replaces the round trip through Gemian's installer for station images.
- [`lid-guard.c`](lid-guard.c) is a small static program, respawned by init:
  - On `SW_LID` closed it inhibits the `keyboard-matrix` input device
    (`inhibited` = 1), powers the backlight down (`bl_power` = 4) and blanks
    the console. Open undoes all three.
  - It acts only after it has seen the lid open, so a misread or floating
    lid input at boot cannot take the console away.
  - Each transition goes to the kernel log.

## Safety assessment

- **Writes to the device:** boot2 only, through the reviewed installer,
  once.
- **Owner decision, 2026-10-30:** mounting Gemian's `linux` partition
  read-write from mainline. That partition is Gemian's root and the
  recovery system.
  - It is chosen by GPT name.
  - It is unmounted on `reboot` and `poweroff`, through busybox init's
    shutdown actions.
  - A crash with it mounted leaves an ext4 journal that Gemian replays on
    its next boot.
  - Shut down with `poweroff` or `reboot`, never `reboot -f`.
  - Writes under `/mnt/data` should stay in a dedicated directory, for
    example `/mnt/data/station/`, so Gemian's own files are not touched.
- **Return to Gemian:** `reboot` from either shell. Without the button, LK
  boots the primary boot partition, which is Gemian. Afterwards, confirm a
  changed boot ID through the known-good LAN endpoint.
- **No radio action:** `mac` is not loaded, and the WMT/WLAN start is not
  run. As on every Wi-Fi boot so far, the CONSYS owner starts the firmware
  only when userspace writes its `wmt_negotiate` attribute. The soak
  harness did that; the station does not.
- **Lid boot (third boot, revised DT), effects beyond the first boot:**
  - GPIO66 read every 100 ms (no interrupt);
  - one `pwm_sel` mux write to the 26 MHz oscillator;
  - the PWM register writes of the backlight's first apply, at level 512,
    then at levels 0 and 512 through `bl_power`.
  - There is no ULPOSC, panel or sleep-controller access.
  - H8 is booted here without H2. If the screen goes dark
    after the PWM probe, the console is lost but SSH is not: record
    `/sys/class/backlight/backlight/*` and return.
  - GPIO66 has no mainline pull setting. Its level followed the lid on
    the C1 boots, and `lid-guard`'s wait-for-open rule and SSH cover a
    misread.
- **Heat and battery:** there is no thermal driver or charger telemetry. A
  long session is attended. Stop on noticeable heat, a battery warning, or
  the owner's word.
- **Watchdog:** the kernel keeps the watchdog armed, so a hang resets to
  Gemian.

## Associated code

- [0338](../../patches/proposals/0338-wifi-mt6797-build-the-mac80211-layer-as-a-loadable-m.patch),
  [`series-a53-station`](../../patches/series-a53-station), and the
  `mt6797-a53-station` profile in [`kernel/manifest.json`](../../kernel/manifest.json).
- [`gemini-a53-station.fragment`](../../configs/gemini-a53-station.fragment).
- [`initramfs/`](initramfs/), [`build-station-initramfs.py`](build-station-initramfs.py),
  [`station-dt.sh`](station-dt.sh), [`lid-guard.c`](lid-guard.c) and
  [`compose-station.py`](compose-station.py).
- `lid-guard` is built with `gcc -static -O2 -Wall -Wextra -Werror` on
  aarch64 (in the VM) and passed to the composer:
  `compose-station.py PACKAGE PARENT_INITRAMFS LID_GUARD OUTPUT_DIR`.

## Tested offline (2026-10-30)

**In the VM**, on the soak tree plus 0338:
- the station config resolves with the differences above;
- `Image` and `mac.ko` link;
- `mac.ko`'s code is the size of the built-in `mac.o` (76,252 vs 76,188
  bytes of text);
- W=1 builds of the driver and CONSYS are clean both built in and as a
  module;
- checkpatch is clean.

**In QEMU** (`virt`, 8 CPUs, the VM-built station `Image`), with a test copy
of the RAM root that adds a serial shell and, for the data mount only, looks
for `vda*` instead of `mmcblk0p*`:
- init reaches busybox init, and the root is tmpfs at 1 GiB;
- the status file records CPUs 0–7, the release and the boot ID;
- `insmod mac.ko` links and returns `-ENODEV`, the designed refusal with no
  CONSYS;
- a GPT partition named `linux` is found and mounted read-write;
- a file written there survives `poweroff`, and `e2fsck -fn` reports the
  filesystem clean.

The composer builds a 12.46 MB boot image (under boot2's 16 MiB) that passes
the LK checks.

**Not tested:**
- the Buildbox build;
- the USB gadget, dropbear, the console and the keyboard, which QEMU does
  not have;
- the eMMC itself;
- any device boot.

## Procedure

1. Commit and push, then run the Buildbox build of profile
   `mt6797-a53-station` with `BUILD_MODULES=1`.
2. Compose with `compose-station.py`, bind the reviewed installer to the
   image's checksum, install boot2 from Gemian and shut down. The owner
   selects boot2.
3. On the station:
   - check `/run/station/status`, `/sys/devices/system/cpu/online`,
     `/proc/mounts` and `df`;
   - log in over USB SSH;
   - use the console shell from the keyboard;
   - list `/lib/modules/7.1.3-gemini-a53-station/` and confirm `lsmod`
     shows no `mac`.
4. `reboot`, then confirm Gemian, its changed boot ID, and that the root
   filesystem mounted cleanly.

## Readings (predeclared)

| Observation | Reading |
|---|---|
| All six hypothesis items hold | The station works; the methodology change is next |
| No USB SSH, but the console shell works | The station runs; the cause is visible in `/run/station/status` and `dmesg` on the console |
| `data=not-found` or `data=mount-failed` | The data mount is the item; the rest of the station is graded as is |
| No console and no SSH | The boot is inconclusive; the watchdog or a reboot returns to Gemian |

## Observations

**Build and install (2026-10-30).**
- **Buildbox build at `d6bba526`:**
  - 805 patches, `modules_built=true`;
  - config `d8890f4e…`, image gzip `3f5e8532…`;
  - the resolved config differs from the soak kernel's exactly as listed
    above;
  - `mac.ko` has vermagic `7.1.3-gemini-a53-station SMP preempt mod_unload
    aarch64`.
- **Packaging fix.** The first build at `350b95e8` compiled, then failed
  package validation: `modules_install` linked `lib/modules/<release>/build`
  back into Buildbox's build tree. `scripts/kernel` now removes that link.
- **The boot image:**
  - boot2 `eb860aba…`, 12.45 MB, LK checks passed;
  - the decompressed kernel is 19.9 MB (soak: 16.0 MB), effective size
    21.4 MB, against the 50 MiB MT6797 decompression limit.
- **Install** through the reviewed installer, bound by identity lines only:
  - from Gemian `9afe57a1…`, predecessor `d05536e8…`;
  - write, sync and flush, with matching full readback;
  - clean shutdown, confirmed unreachable.

**Station boot `eda50de3-60a5-4693-bf66-f60f23b953d3`** (release
`7.1.3-gemini-a53-station`):
- `/run/station/status`: `root=tmpfs-1g`, `cpus_online=0-7`,
  `data=mounted device=/dev/mmcblk0p29`.
- **Root:** `rootfs rw,size=1048576k`.
- **CPUs:** `/sys/devices/system/cpu/online` reads `0-7`.
- **`/mnt/data`:** `/dev/mmcblk0p29 ext4 rw,noatime`, 56.5G, 49.6G free.
  - The kernel logged `EXT4-fs (mmcblk0p29): recovery complete`, then the
    read-write mount. So Gemian's journal was replayed at mount, although
    Gemian had shut down through `systemctl poweroff`.
- **SSH:** reachable at 10.15.19.82 under 30 s after boot, key-only.
  - A 20 MB file pushed over SSH into `/mnt/data/station/` took 3 s and its
    SHA-256 matches. The test file was then removed.
- **Console:** the owner reports that the console shell and keyboard work.
- **Module:** `mac.ko` is in `/lib/modules/7.1.3-gemini-a53-station/`, and
  `lsmod` is empty.
- **Kernel log:** no Oops, BUG, WARNING or panic. The two error lines are
  the soak boots' own: `regulatory.db` is absent, and the I2C6 guard is
  denied.
- **Wi-Fi:** one CONSYS one-shot record, the region 19 read; no WMT or WLAN
  start.

**End of boot `eda50de3…`.** The console record in pstore, preserved from
Gemian, ends with `reboot: Restarting system` at 1519.8 s. This was an
orderly busybox `reboot`, presumably the owner's.
- Gemian then booted as `b6866994-dad2-4cb0-a28a-20090081bf6b`.
- Gemian mounted `mmcblk0p29` without journal recovery, so the station's
  shutdown unmounted `/mnt/data` cleanly.

**Lid change, tested offline (2026-10-30).**
- `station-dt.sh` is reproducible (`0f4085a9…`): the delta is exactly the
  three changes above, with no new `dtc` warning.
- `lid-guard` builds clean with `-Werror`. It was run in QEMU on a VM station
  `Image` with `uinput` added for the test only, against a fake `gpio-keys`
  lid and a fake `keyboard-matrix`:
  - with no devices it retries;
  - started closed, it waits;
  - after the first open it arms;
  - close sets `inhibited` = 1 and reopen sets it back to 0;
  - console blanking returns 0, and the backlight write returns `-ENOENT`,
    as QEMU has no backlight.
- The composed image is 12.74 MB, and the LK checks pass.
- **Not tested:** GPIO66 under mainline, the real backlight, and any device
  boot of the lid change.

**Lid boot `bac0f387-783a-4bd1-99de-398549103302`** (boot2 `c4946751…`,
first DT revision, with display H2).
- **No console.** The owner saw the boot logo stay on the screen. The
  framebuffer and the PWM both deferred forever: `supplier
  10006000.power-controller not ready`. The `10006000.power-controller`
  probe returned 19, while its child `power-controller` node bound.
  `/proc/fb` was empty.
- **The station otherwise worked:** CPUs 0–7, a 1 GiB root, `/mnt/data`
  mounted read-write, and SSH.
- **The lid:**
  - `gpio-keys` bound, and `lid-guard` started with the lid open and
    armed.
  - One close and reopen by the owner gave EINT5 ("Hall lid", edge) a
    count of 0 and no `SW_LID` event.
  - GPIO66 read `hi` with the lid open. The pin's pull fields read
    `-ENOTSUPP`.
- The kernel log, the status file and the lid test are retained
  privately.

**Lid boot `13055ae9-6f43-4b81-80a2-f2c365be1e2e`** (boot2 `0bdcd90f…`,
revised DT `609fc172…`, pushed at `4c771b06`).
- **Return from `bac0f387`.** An orderly `reboot` over SSH after its log was
  saved. Gemian came back as `34357248-944c-496b-8e0e-56227242925e` and
  mounted `mmcblk0p29` without journal recovery.
- **Console:** `simple-framebuffer` registered `fb0` (1080x2160) at 0.77 s.
- **Backlight:** `1100f000.pwm` and `backlight` probed with return 0.
  `brightness` and `actual_brightness` read 512 of `max_brightness` 1023,
  with `bl_power` 0.
- **Lid:**
  - `gpio-keys` (polled) bound, and `lid-guard` started with the lid open
    and armed.
  - The owner closed the lid at 9.45 s and opened it at 14.04 s, logged as
    `lid closed: keyboard_inhibit=0 backlight=0 console_blank=0` and the
    matching open line.
  - The owner reports that it works: the screen goes off while closed, the
    keyboard is ignored, and both come back on open.
- The status file again shows CPUs 0–7, the 1 GiB root and `/mnt/data`.
  There is no Oops, BUG or WARNING.

**Brightness keys, live on boot `13055ae9…` (no rebuild, no reboot).**
- The new `lid-guard` (`9936014b…`, built `-Werror` in the VM) and the
  adjusted keymap (made by the builder's own function) were pushed over USB
  SSH.
- The binary was renamed over the running one, since a plain copy failed
  with "text file busy", and restarted through init's respawn. It armed
  with the lid open. The keymap was loaded with `loadkmap`.
- **Owner:** Fn+N brightens and Fn+B dims, with no characters reaching the
  shell. Brightness read 384 afterwards. There is no Oops, BUG or WARNING.
- This is the first change deployed on the running station. It went from
  edit to running on the hardware in minutes, with no build or boot. The
  boot image does not carry it until the next compose.

**Wi-Fi unload test, station 4 boot `caac239d-fa37-4d3d-8d83-e6f8e941ac7a`.**
- **Boot:** booted manually by the owner after an orderly `poweroff` of
  `13055ae9…`. `lid-guard` `4a935e33…` and `mac.ko` `ef248a48…` as built;
  console, backlight and lid up.
- **Firmware start:** `region19_prepare` then `wmt_negotiate`. Common init
  completed 285/285, `START ready`, then `the mac module attaches on load`.
- **Cycle 1 passed:**
  - `insmod` 0; record prepare 0; regulatory configuration 0;
  - the TC4 pair (free 14); `phy0`; `wlan0` added and up;
  - a passive scan of 5200 MHz admitted and complete, with 3 BSS;
  - `rmmod` 0, logging `one-shot WLAN mac detached; firmware kept`;
  - `phy0` and `wlan0` gone, `mac` not in `lsmod`.
- **Cycle 2 failed at re-attach:** `insmod` returned `EBUSY`. Record
  prepare was 0 and `phy1` registered, but the regulatory configuration
  returned -5 about 18 ms later.
- **Cycle 3:** `insmod` `EBUSY`, as designed. A failed attach is not
  retried.
- There is no Oops, BUG or WARNING. The logs are retained privately.
- **Reading** (the second predeclared row, located on the host):
  - `mt6797_hif_send_config()` admits configuration commands only while the
    built-in HIF's normal phase is `CAP_RECEIVED` or `NVRAM_SUBMITTED`, the
    one-time init window. After the first lifetime it has left that window.
  - So the second load's first configuration command was refused with
    `-EIO` before any transfer. Nothing reached the firmware.
  - That path returns before `mt6797_hif_fail()`, so the HIF is not
    poisoned.
- **What CONSYS must keep across loads:** the fact that the firmware is
  already configured. A re-attach must not replay the one-time
  configuration (TX power, edges, domains, NVRAM settings, TX control);
  the firmware keeps it. Whether anything in it must be re-sent per
  lifetime is open.

**Station 4, flashed from the station (boot `13055ae9…`).**
- **Build:** Buildbox at `51a5fb6e` (806 patches with 0339,
  `modules_built=true`). The config is identical to the previous station
  package, and `mac.ko` (`ef248a48…`) now has `cleanup_module`.
- **Composition:** boot2 `a3e68ff9…`. The RAM root carries `lid-guard`
  `4a935e33…`, `setterm`, `flash-boot2` and the keymap with Fn+B/N set to
  no action.
- **Flasher refusals,** tested on the station:
  - a malformed checksum, an image that is not 16 MiB, and a checksum
    mismatch were each refused;
  - with the installed station 3 image, every partition guard passed on
    `/dev/mmcblk0p30` (179:30), and it stopped at `already current`.
- **Flash:** predecessor `0bdcd90f…`, then
  `result=written-synced-readback-verified` with readback `a3e68ff9…`. It
  took 3 s.

**Screen blanking, live on boot `13055ae9…`.**
- The new `lid-guard` (`4a935e33…`) and `/bin/setterm` were pushed over SSH
  and swapped in.
- With `setterm --blank 1`, the console blanked about 63 s later.
  `lid-guard` logged `console blanked`, and `bl_power` read 4.
- **Owner:** a key press wakes the screen. The log shows `console unblanked`
  20 s later, with `bl_power` back to 0.
- `setterm --blank 2` restored the default, and `--blank 99` is refused.

**Wi-Fi module load, live on boot `13055ae9…` (no rebuild, no reboot).**
- **Firmware start.** It is two userspace writes of `1`, as in the soak
  harness:
  - `region19_prepare` logged `WMT setup complete: clear=351232 verified,
    CONN held off`;
  - then `wmt_negotiate` passed prepower admission. WMT common init
    completed 285/285, then `START ready`, then `firmware ready; the mac
    module attaches on load`.
  - A first `wmt_negotiate` write before the prepare was refused with
    `ENODEV`, with nothing attempted.
- **`insmod mac.ko`** returned 0:
  - private record prepare 0, regulatory configuration 0;
  - the TX-status and TC4 accounting pair: released 1, free 14;
  - `phy0` registered;
  - `lsmod` shows `mac` as `[permanent]`, having no exit in 0338.
- **Scan.** `iw phy phy0 interface add wlan0 type managed` and link up
  worked.
  - A default passive scan was refused with `ret=-95 why=shape`: 13
    channels, while the driver admits only its pinned channel.
  - `iw dev wlan0 scan freq 5200 passive` was admitted and completed,
    finding 3 BSS on 5200 MHz.
  - There is no Oops, BUG or WARNING. The logs are retained privately.

**Unload: proposal
[0339](../../patches/proposals/0339-wifi-mt6797-detach-the-mac80211-layer-on-module-unl.patch).**
- `mac` gets a module exit. `mt6797_mac_unregister()` reverses
  registration:
  - unregister the hardware (which stops it: joins closed, scan
    cancelled);
  - cancel the scan and join work, and purge their queues;
  - release the snapshot action when built;
  - unregister the test configuration;
  - free the hardware.
- CONSYS exports `mt6797_consys_wlan_detach()`, which runs that unregister
  and clears the attached state, so the next `insmod` attaches again to the
  same started firmware.
- **Tested in the VM:** the build links; W=1 is clean built in and as a
  module; checkpatch is clean; `mac.ko` has `cleanup_module`.
- **Not tested:** the device. CONSYS is built in, so this needs a station
  kernel rebuild and one boot. After that, fixes to the teardown are
  module-only and can be pushed live.
- **Device test, predeclared.** Start the firmware, then load, add
  `wlan0`, scan, and `rmmod`, three times on one boot.

  | Observation | Reading |
  |---|---|
  | Each cycle: insmod 0, record and regulatory 0, scan admitted with BSS found; rmmod 0, `mac detached; firmware kept`, `phy0` gone | Load and unload work on one firmware start |
  | The second load's regulatory configuration or scan fails | The firmware does not accept a second configuration; that names what CONSYS must keep across loads |
  | `rmmod` hangs, or an Oops in teardown | The log names the step; fix in `mac.ko` and push it live |

## Analysis

All six hypothesis items hold on one boot. Two facts were found only on
the device:
- the firmware start is a userspace trigger, not a boot step;
- the data partition's journal needed recovery at mount.

The cause of that recovery is not identified. Gemian's root is mounted
`data=journal`, so a clean poweroff may still leave journal work; this is
inference. Still open:
- uptime beyond the first minutes;
- shutdown through `reboot`, with `/mnt/data` unmounted, and Gemian's next
  mount of the partition.

## Conclusion

Confirmed for the named Gemini and boot `eda50de3…`: the station boots with
all six items.
- It ran for 25 minutes and returned through an orderly `reboot`, leaving
  the data partition clean.
- Longer uptime is not yet observed.
- The first lid boot gave the lid input, but no console and no backlight.
- With the revised DT (polled lid, PWM without the MM reference), boot
  `13055ae9…` keeps the console. Closing the lid powers the backlight down
  and ignores the keyboard, and opening it restores both. This is a polled
  lid; EINT5 is still unresolved.

## Lid boot readings (predeclared)

| Observation | Reading |
|---|---|
| Console up; `gpio-keys` (polled) and `backlight` bound; close: screen dark, keys ignored; open: both back | The lid works |
| Lid events, but the screen stays lit on close | Backlight control is the item: `/sys/class/backlight/backlight/*` and the `bl_power` result in `lid-guard`'s log line |
| No `SW_LID` events | The polled level is the item: compare GPIO66 in `/sys/kernel/debug/gpio` with the lid state |
| Screen dark after the PWM probe, or the console lost | H8's dark branch, or MM is not held: record the backlight, clock and `/proc/fb` state over SSH, then return |

## Follow-up

If it holds: load `mac` on the station; then module unload and reload
(a detach in 0338's place); then the methodology change.
