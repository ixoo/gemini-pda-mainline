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

Note, 2026-11-04: the Status line dates from 2026-10-30. Later sections supersede it, up to
the [first boot of the release image](#first-boot-of-the-release-image-2026-11-04).

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
- **Release variant:** [`release/`](release/) replaces that parent with a public one for
  `mt6797-a53-release`; see [release readiness](../../docs/RELEASE_READINESS.md#release-ram-root).

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
  - sets the left Type-C chip (FUSB301, I2C `1-0025`) to sink mode, because the
    chip keeps its mode through a power-off and a source mode left by a test
    removes VBUS and USB SSH from the left port. It reads before it writes, and
    it leaves the mode alone when no driver-free chip answers or when
    `/mnt/data/keep-left-typec-mode` exists. The result is recorded as
    `left-typec=` in the status file. This needs `I2C_CHARDEV`, so the release
    image, which leaves that out, gets no such reset;
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
  - the hall node from 0074 is enabled: GPIO66, active-low,
    `EV_SW/SW_LID`, GPIO mode, no pull setting. Until station 20 it was
    `gpio-keys-polled`, read every 100 ms with a 64 ms debounce. From
    station 21 it is `gpio-keys` on EINT5 with no debounce (see
    [lid interrupt](#lid-interrupt-station-21-owner-request));
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
- [`backlight-policy.c`](backlight-policy.c), named `lid-guard` until 2026-11-03,
  is a small static program, respawned by init. Older entries here use the old
  name. The kernel's `gemini-lid` module has since taken over the lid; the program
  keeps the brightness keys and fades. Since 2026-11-06 it also takes CPUs 1–7
  offline while the lid is closed or the console blanked, and brings back the
  ones it took
  ([power R1b](../2026-11-06-gemini-power-management/README.md#r1b-result-2026-11-06));
  not yet run on the device. As first written:
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
  [`station-dt.sh`](station-dt.sh), [`backlight-policy.c`](backlight-policy.c) and
  [`compose-station.py`](compose-station.py).
- `backlight-policy` is built with `gcc -static -O2 -Wall -Wextra -Werror` on
  aarch64 (in the VM) and passed to the composer in its tools directory.

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
- **Reading** (the second predeclared row, located on the host; corrected
  after reading the source):
  - Two boot-wide rules in the built-in HIF's normal-command state refuse a
    reloaded layer.
  - After the record (`NVRAM_SUBMITTED`), `mt6797_normal_prepare_config()`
    admits only domain, TX-control and scan commands: "never replay
    manufacture data". The reload's first command was TX power.
  - The command sequence history (32 bytes, the whole boot, never cleared)
    refuses reuse, and a fresh layer restarts at sequence 5.
  - The refusal aborts the normal transaction (`FAILED`), and
    `mt6797_hif_send_config()` then runs `mt6797_hif_fail()`. So the HIF
    is failed for the rest of boot `caac239d…`. Nothing reached the
    firmware.
- **What CONSYS must keep across loads:**
  - the fact that the firmware is configured, so a re-attach does not
    replay the record;
  - the TC4 baseline from the once-per-boot accounting pair;
  - and the re-attached layer must continue the boot's command sequence.

**Re-attach: proposal
[0340](../../patches/proposals/0340-wifi-mt6797-re-attach-the-mac80211-layer-to-the-conf.patch).**
- **CONSYS** sets `wlan_configured` after the first successful attach and
  passes a `reattach` flag to registration.
- **On re-attach, `mac`:**
  - marks itself configured without the record load;
  - continues from `mt6797_hif_next_sequence()`, a new HIF export: one past
    the highest used sequence, or `-EIO` once the HIF has failed;
  - and CONSYS skips the TC4 accounting pair.
- The first attach, and every built-in profile, is unchanged.
- **Tested in the VM:** W=1 is clean built in and as a module; the station
  `Image` and modules link; checkpatch is clean.
- **Not tested on the device.**
- **Sequence budget:** without 0334 the boot's sequences still run out
  after about 250 commands. One lifetime uses about 22.
- **Device test, predeclared** (the same three cycles as station 4):

  | Observation | Reading |
  |---|---|
  | Cycles 2 and 3: insmod 0, `regulatory configuration: status=0 (kept from the first attach)`, scan admitted with BSS found, rmmod 0 | Reload works on one firmware start |
  | Re-attach registers, but the scan is refused or times out | Something per lifetime beyond the record is needed; the scan refusal names it |
  | `mt6797_hif_next_sequence` returns `-EIO` | The HIF failed during the first lifetime or its teardown; the log names when |

**Station 5, boot `8fe8a9cc…`: reload works (0340).**
- **Identity:** release `7.1.3-gemini-a53-station`, boot2 `2ffbe478…`,
  `mac.ko` `335f2ec8…`; 8 CPUs, 1 GiB RAM root, `/mnt/data` mounted.
- **Run:** `CYCLES=3` [`wifi-cycles.sh`](wifi-cycles.sh) about 30 s after
  boot. The firmware start returned 0 for both steps.
- **Cycle 1:** insmod 0, record prepare and regulatory configuration
  `status=0`, `phy0`, scan 0 with 3 BSS, rmmod 0, `mac detached; firmware
  kept`.
- **Cycles 2 and 3:** the same, with `regulatory configuration: status=0
  (kept from the first attach)`, on `phy1` and `phy2`; each scan completed
  (`complete=1 frame=1 beacon=1 credit=1 retired=1`) with 3 BSS.
- **Kernel log:** no Oops, BUG, WARNING, call trace, refusal or stop.
- **Reading:** the first predeclared row. Reload works on one firmware
  start; a `mac` change now needs only `rmmod` and `insmod`, not a reboot.
- **Limit:** the boot's command sequences still run out after about 250
  commands (about 22 per lifetime, so roughly ten lifetimes).

**Station 9, boot `960b9505…`: a persistent WPA2 join, and 26 connections
on one firmware start.**
- **Setup:**
  - modules from the packages at `aa4f5a58` (0351), then `bcc82edd` (0352),
    loaded through R2 reloads
    ([restart record](../2026-10-30-mt6797-consys-restart/README.md#station-9-boot-960b9505-r2-works-three-restarts-in-one-boot));
  - [`wifi-up.sh`](wifi-up.sh), with the private join inputs sent to
    `/run/station` (RAM only);
  - the access point is the owner's, on channel 40 (5200 MHz).
- **Join:** `wpa_state=COMPLETED`, WPA2-PSK with CCMP, a DHCP lease and the
  gateway answering 3 of 3 pings. A ping to a public address answered in
  about 7.7 ms.
- **Kernel log:** only the named refusals known from the soak boots (EAPOL
  admission and RX classification of protected frames); no Oops, warning or
  call trace.
- **Reconnects** (`wpa_cli disconnect`, then `reconnect`; each one a new
  driver lifetime):
  - **On 0334 alone:**
    - lifetimes 1-9 joined within 2 s each;
    - at the tenth, `sequence recycle: from=215 to=17 ret=-16`, then the
      old wrap refusal, which poisoned `mac` until a reload;
    - a second R2 reload with 0351 repeated it at the same point. The
      logged ledger showed TC4 at 23 of 26 pages, nothing pending, and TC1
      complete (156/156).
  - **With 0352:** 25 reconnects in a row, all `COMPLETED` within 2 s and
    answering a gateway ping, so 26 lifetimes on one firmware start. The
    recycle ran twice: `ret=0 waits=1`, then `ret=0 waits=0`.

**Reading:**
- **0334 was right in its gate and wrong in its timing.** The cleanup's
  last command pages are reconciled only by the next scan's guard, so
  the recycle saw them as owed.
- **[0352](../../patches/proposals/0352-wifi-mt6797-reconcile-TC4-credits-before-a-sequence-.patch)**
  reconciles first and waits a bounded time for TC4. The connection limit
  (about an hour of daily use) is gone.
- **0335** (no packet budget for a connected lifetime) needs more than 2.3 h
  connected. A hold with a gateway ping every 30 s started at 1234 s of
  uptime.

**The hold (same boot, 1234-11282 s).**
- **Pings:** 335 gateway pings at 30 s, all answered, with `wpa_state`
  `COMPLETED` throughout.
- **One lifetime, ended by the custodian's `DOWN=1`:**
  `join data phase end: reason=disconnect elapsed_ms=10058076 rx_delivered=40044
  tx_queued=598 tx_done=598 tx_failed=0`.
- **Reason-4 notices:** `BSS timeout ignore record: ignored=307`, every one
  consumed while receive was fresh.
- **Kernel log:** no packet-budget stop, connection-loss report (before the
  disconnect), Oops, warning or call trace.
- **Station:** stayed up, attended by the owner.

**Reading:**
- **0335 holds:** a connected lifetime ran 2.79 h, past the 1.7-2.3 h at
  which the old 65536-packet budget ended it. The HIF packet count itself
  is not logged; at the 8-11 beacon and group frames a second recorded
  before, it passed the old budget (inference).
- **Together with 0334 and 0352:** the station's Wi-Fi now survives both
  the connection limit and the two-hour limit on the owner's access point.
- **No group-key rekey was seen** in 2.8 h, so the access point's rekey
  interval is longer, or it does not rekey. Rekey support remains the open
  daily-use item
  ([gaps](../2026-10-13-mt6797-wifi-native-delivery-probe/DAILY_USE_GAPS.md)).


**Station 8, boot `bb6c4873-f0f7-4a7a-a37d-8fe1c0d3e3a2`: power-off B
passed.**
- **Power-off B, cable attached:** a plain `poweroff`, after the kernel log
  was saved. The owner saw the charging screen, as after a Gemian shutdown
  with a charger.
- **Reading:** the second row. With a charger, the PMIC re-powers into
  charging mode by itself, so Gemian's watchdog restart step is not needed.
- **Result:** both cases now match Gemian's power-off.
- **Unplugged power-status read:** inconclusive. The read scheduled 45 s
  before power-off A still showed USB power good and fast charging
  (`0b=36`), most likely because the cable was still in at that moment. The
  next boot started with charging `no` again (`0b=26`).

**Station 8, boot `975af37c-6283-4cbf-903e-9fd42a5047ee`: power-off A
passed.**
- **Identity:** boot2 `62ae2230…`, `power-status` `361d522a…`.
  `mt6351-pwrc` bound to the `mt6323-pwrc` driver, and I2C0 is `i2c-0`.
- **Power-off A, cable detached:**
  1. The power-status read and a `poweroff` were scheduled on the device,
     then the owner unplugged the cable.
  2. The owner reported that the device powered off.
- **Reading:** the first row. The MT6351 RTC write powers off without a
  charger.
- **Comparison with Gemian:** plugging USB into the powered-off device
  brought up the charging screen, as after a Gemian shutdown (owner
  observation). The off state now matches Gemian's for this case.

**Station 8, flashed from station 6 (boot `967d17be…`): power-off and
power status.**
- **Build:** Buildbox at `0b3bb43f`. It is station 7 plus `CONFIG_I2C_CHARDEV`,
  I2C0 enabled with no child bound, and `power-status` (`361d522a…`) in the
  RAM root, for the
  [power-status experiment](../2026-10-31-gemini-power-status/README.md).
- **Flash:** boot2 `62ae2230…` over station 7's `e0825b6f…`,
  `written-synced-readback-verified`. Station 7 never booted; station 8
  carries its power-off change.
- **Test order on station 8:**
  1. The power-status runs, cable in and then unplugged.
  2. Power-off A, cable detached.
  3. After a boot: power-off B, cable attached.

**Power-off like Gemian: proposals 0342 to 0345, for station 7.**
- **Problem:** the station powers off through PSCI `SYSTEM_OFF` into the
  retained ATF. The owner observed that the resulting off state is not the
  one Gemian's shutdown leaves.
- **Gemian's path:** the vendor kernel never takes the PSCI path on MT6797
  ([PMIC findings F19 to F21](../2026-10-04-gemini-pmic-basics-re/README.md#restart-and-power-off)).
  Its `mt_power_off()`:
  1. clears the RTC two-second reboot (AL_SEC bits 8 and 6);
  2. without a charger only, sets the 32 kHz export off and drives
     `SRCLKEN` low;
  3. writes `BBPU = 0x4309` (key, AUTO and PWREN, power bit clear) and
     triggers it;
  4. with a charger, if still running after about 1.1 s, restarts
     through the watchdog without the reboot flag, which LK takes as a
     charging start.
- **The change:**
  - 0342: the binding.
  - 0343: an MT6351 power-controller cell at the RTC base `0x4000`.
  - 0344: an MT6351 entry in mainline's `mt6323-poweroff` driver, doing
    steps 1 and 3.
  - 0345: the DT node.
  - The station profile enables `CONFIG_POWER_RESET_MT6323`.
  - Steps 2 and 4 are not included. If the PMIC stays up after the
    write, the driver waits 1 s, warns `Unable to power off system` on
    the console, and the PSCI path runs as before.
- **VM checks:**
  - W=1 is clean for the driver and MFD, and the station image links;
  - the binding passes `dt_binding_check`;
  - the station DTB carries the node;
  - checkpatch reports only the absent Signed-off-by, which is never
    invented here.
- **Not run on the device.**
- **Station 7:**
  - Built on Buildbox at `8315ea93`. The config differs from station 6's
    only by `CONFIG_POWER_RESET_MT6323=y`; `mac.ko` is unchanged.
  - The DTB (`1099d931…`) carries the `mediatek,mt6351-pwrc` node.
  - boot2 image `e0825b6f…`, flashed from station 6 (boot `967d17be…`)
    over `fb6d3f13…`, `written-synced-readback-verified`.
- **Device test, predeclared:** two power-offs on station 7. The owner
  watches the screen, and the PMIC write is Gemian's own shutdown write.
  - **A, cable detached:** `sleep 20; poweroff` started over SSH, then the
    cable is unplugged.
  - **B, cable attached:** a plain `poweroff`.

  | Observation | Reading |
  |---|---|
  | A: off, the power key boots normally | The PMIC write powers off without a charger, as Gemian |
  | B: charging screen, as after a Gemian shutdown | With a charger, the PMIC re-powers into charging mode by itself; no restart step is needed |
  | B: `Unable to power off system` on the console, then the old off state | The charger holds the PMIC on; Gemian's watchdog restart (step 4) is needed next |
  | Either: an immediate reboot into the system | The two-second reboot or AUTO behaves differently; stop and record |

**Station 6, boot `967d17be…`: the R1 stop works (0341).** One cycle as
before (3 BSS), then the stop: WLAN_READY cleared, FW own was taken,
VCN33-WIFI went off, and a later `insmod mac` was refused with
`-ENODEV`, with no kernel fault. Details are in the
[restart record](../2026-10-30-mt6797-consys-restart/README.md#observations).

**Station 6, flashed from boot `8fe8a9cc…`.**
- **Flash:** `flash-boot2` over station 5's `2ffbe478…`,
  `written-synced-readback-verified` `fb6d3f13…`. The image stays on the
  data partition under `station/`. Boot `8fe8a9cc…` was then powered off.
- **Build:** Buildbox at `f328f438` (with 0341, the
  [restart](../2026-10-30-mt6797-consys-restart/README.md) stop half). The
  config is identical to station 5's. `mac.ko` is unchanged (`335f2ec8…`):
  0341 changes only built-in code.
- **Image:** boot2 `fb6d3f13…`, with the same RAM root inputs as station 5.
- **Test:** `CYCLES=1 STOP=1`: one cycle, then the stop.

**Station 5, flashed from boot `caac239d…`, ready for its boot.**
- **Build:** Buildbox at `21fa2220` (807 patches, with 0340). The config is
  identical to station 4's, and `mac.ko` is `335f2ec8…`.
- **Image:** boot2 `2ffbe478…`, with the same RAM root inputs as station 4
  (`lid-guard` `4a935e33…`).
- **Flash:** `flash-boot2` over station 4's `a3e68ff9…`,
  `written-synced-readback-verified`.
- **Test:** [`wifi-cycles.sh`](wifi-cycles.sh) runs the predeclared cycles
  over SSH (`CYCLES=3 /bin/busybox sh -s`). It starts the firmware once per
  boot, never clears the kernel log, and prints one line per step.
  - A first draft cleared the log between cycles, which erased the
    firmware-ready line. A dry run on `caac239d…` showed this, so the
    script was fixed before use.

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

## Lid interrupt (station 21, owner request)

Owner request: make the lid detection interrupt-based. Until now the kernel
polled GPIO66 every 100 ms, because EINT5 never fired on C1 to C1-5 or on
station boot `bac0f387`. Patch 0377 since restored the EINT mux mode on
EINT0-16 pads, and fixed the same silence on the keyboard's EINT10 (station
16). `station-dt.sh` now keeps the hall node as `gpio-keys` on its
interrupt and sets the debounce to 0. That avoids asking `mtk-eint` for
hardware debounce on a dual-edge line, which C1 suspected.

The kernel package (e80e197a) is unchanged; only the composed DTB differs.

| Observation on station 21 | Decision |
| --- | --- |
| `gpio-keys` bound; the EINT5 count in `/proc/interrupts` rises on close and open; `SW_LID` events arrive and `lid-guard` blanks and restores | Keep the interrupt. Debounce stays an open item |
| No EINT5 count and no `SW_LID` events, while the GPIO66 level follows the lid | 0377 alone is not enough. Check the pad mode and debounce state, then return to station 20 (polled) |
| Repeated events for a single close or open | The Hall output bounces. Add a software debounce |

**Station 21 result.**
- Composed from package e80e197a (inventory `4f760d85`) with the DTB from
  1e2c4c9b.
- boot2 `ae3311e9`, RAM root `a3b24863`, boot `073706eb`.
- `gpio-keys` (not `-polled`) bound, with "Hall lid" on `mt-eint 5 Edge`.
- The owner closed and opened the lid twice. EINT5 counted exactly 4
  interrupts, and `/dev/input/event1` carried `SW_LID` = 1, 0, 1, 0 at
  55.95, 65.42, 69.32 and 76.62 s, one event per movement with no bounce.
- `lid-guard` logged each close and open with zero results. The owner
  confirmed that the screen turned off on close and came back on open.
- The input numbering changed: the keyboard is now `event0` and the lid
  `event1`. `lid-guard` finds both by name.

0377 was the missing piece: EINT5 fires once the pad keeps its EINT mux
mode. The lid is interrupt-driven from station 21. No bounce appeared
without debounce, so none is added. Hardware debounce on the dual-edge
line remains untested.

## Lid policy in the kernel (station 22, owner request)

Owner request: the lid is core to the device, so closing it should turn the
screen off and make the kernel ignore the keyboard, driven by the interrupt
and not by a userspace service.

- 0386 adds the `gemini-lid` input handler as a module
  (`CONFIG_INPUT_GEMINI_LID=m` in the station fragment), and `init` loads it
  before `init` hands over. It follows `SW_LID`:
  - on close, the raw backlight goes to `BACKLIGHT_POWER_OFF`, and key
    presses and repeats from the `gpio-matrix-keypad` keyboard are dropped;
    releases still pass;
  - on open, both are undone;
  - nothing happens before the lid has been seen open once.
- `lid-guard` no longer acts on the lid. It keeps the Fn+B/Fn+N brightness
  keys and the console-blank backlight sync, and it skips that sync while
  the lid is closed. It no longer blanks the console on close. The backlight
  being off is the screen-off state.
- The keyboard is no longer inhibited, so the matrix scan still runs on its
  row interrupt while the lid is closed. With nothing pressed, that costs
  nothing.

| Observation on station 22 | Decision |
| --- | --- |
| `status` shows `lid=gemini-lid`; on close the kernel logs "gemini-lid: lid closed", the screen goes dark and typed keys do nothing; on open, the screen returns and typing works | Keep the policy in the kernel |
| Screen dark but keys still typed, or the reverse | Check the handler binding (`/proc/bus/input/handlers`) and the backlight type |
| `lid=insmod-failed` | Read the module error in dmesg. The lid then has no policy for this boot |

**Station 22 result.**
- Package c79829b1 (inventory `e746f703`), boot2 `fee767b9`, RAM root
  `333a5883`, boot `24d5c3ea`.
- `status` showed `lid=gemini-lid`. The module was loaded, and
  `/proc/bus/input/devices` listed `gemini-lid` first among the handlers on
  both `keyboard-matrix` and `gpio-keys`.
- The owner typed `abc`, closed the lid, pressed the closed keyboard for
  about 10 s, opened it and typed `xyz`.
  - The kernel logged "gemini-lid: lid closed" at 74.88 s and "lid open" at
    85.14 s, from 2 EINT5 interrupts.
  - The keyboard's `event0` carried only a, b and c (71.86-72.51 s) and
    x, y and z (90.31-91.07 s). Nothing reached it while the lid was
    closed, although EINT10 counted 2834 interrupts over the boot, most of
    them from the closed-lid presses.
  - The owner confirmed that the screen went dark while the lid was closed.
    After opening, `bl_power` was 0.
- The lid policy now runs in the kernel from the interrupt.
- Limitation: keys pressed by the closed lid still trigger matrix scans
  (row interrupts, plus the 20 ms held-key rescan while a key is down).
  They are dropped, not prevented. Inhibiting the device would stop the
  scans, but the input core does not export that to modules.

## Keyboard fully stopped while the lid is closed (station 23, owner request)

Owner request: ignoring the keys is not enough. No keyboard processing
should run while the lid is closed, and the interrupt should be masked.

- 0387 exports `input_inhibit_device()` and `input_uninhibit_device()` from
  the input core. These are the functions behind the `inhibited` sysfs
  attribute.
- 0388 makes `gemini-lid` inhibit the keyboard on close instead of
  filtering its events. The core closes `matrix_keypad`, which stops its
  scan work and disables its row interrupts. The AW9523 then sets those
  pins in its interrupt-disable register, so its INT line and EINT10 stay
  quiet. The interrupts are disabled lazily: the first press on each row
  after closing still raises one EINT10, which masks that row. That is at
  most 8 per closure. On open, the keyboard is reopened.

| Observation on station 23 | Decision |
| --- | --- |
| On close, dmesg shows "keyboard inhibited 0" and `inhibited` reads 1. Pressing the closed keyboard for 10 s adds at most 8 EINT10 interrupts and little I2C5 traffic; on open, typing works | Keep it |
| EINT10 keeps counting while the lid is closed | The rows are not masked. Look at `matrix_keypad_stop` and the AW9523 mask path |
| Typing is dead after opening | The uninhibit failed. Its error is in the dmesg line, and `inhibited` can be cleared through sysfs |

**Station 23 result.**
- Package 32bf670a (inventory `a421591b`), boot2 `bd14c0e9`, boot
  `f9097bd5`, sampled once per second.
- The owner typed `abc`, closed the lid, pressed the closed keyboard,
  opened it and typed `xyz`.

| Interval | EINT5 | EINT10 | I2C5 | `inhibited` |
| --- | --- | --- | --- | --- |
| Typing `abc` (47.5-48.1 s) | 0 | +28 | +827 | 0 |
| Close, at 55.25 s "lid closed, keyboard inhibited 0" | +1 | +3 | +6 | 0 → 1 |
| Lid closed, 55.9-76.1 s | 0 | **+1** | **+2** | 1 |
| Open, at 76.36 s "lid open, keyboard restored 0" | +1 | +2 | +69 | 1 → 0 |
| Typing `xyz` (81.7-82.5 s) | 0 | +31 | +797 | 0 |

- `event0` carried only a, b and c, then x, y and z.
- On station 22, the closed-lid presses gave about 2800 EINT10 interrupts.
  Here the closed keyboard caused one EINT10, with its two I2C transfers,
  over 20 s. That fits the predicted lazy mask: the first press on a row
  fires once, and that row stays masked in the AW9523.
- With the lid closed, the keyboard is inhibited, its scan stopped and its
  interrupts masked. On open, it is restored. 0387 and 0388 stay.

## Clean Wi-Fi series and keyboard cleanup (station 24)

Built at 6fea0382: the Wi-Fi patches replaced by the clean series
0390-0394 ([experiment](../2026-10-31-mt6797-wifi-clean-driver/README.md#result-station-24-boot-46c10546-2026-11-01)),
and the keyboard cleanup c0758ae6 (0375, 0379 and 0380 dropped). The
station profile now merges its own Wi-Fi fragment,
`configs/gemini-a53-station-wifi.fragment`, without the retired driver
options. boot2 `f7761f02…`, boot `46c10546`.

Keyboard, from the first SSH session: `gemini-lid` loaded; no
"row interrupt mode" line, and the `poll_override`, `trace_scans` and
`trace_irq` parameters are absent. Over 20 s idle, EINT10 stayed at 0
and the keyboard's I2C bus (`1101c000.i2c`) stayed at 173 interrupts.
The owner reports that typing works from boot.

## `wifi-up.sh` failure handling (2026-11-04)

The script's failure handling from `7bbff26b` ran on boot `fccba04c`, image `96338704`, as the custodian reports, with `PASSIVE_SCAN=1` and a pinned access point: rc=0, phy after 0 s, `up=0`, `COMPLETED` on the usual channel, lease after 4 s, gateway ping 3 of 3, one connect and no disconnects, tainted=0. This shows the normal path only. The failure paths have run only against stubs, not on the device.

## The station image carries the hand-loaded modules (2026-11-07)

`compose-station.py` packs the release's optional modules (touch, sensors, LEDs, GPU, camera,
A72, Bluetooth, GNSS) and FM's `radio-mt6797` into the station RAM root too, for the Arch card
root, which loads some at boot
([record](../2026-11-06-gemini-arch-root/README.md#drivers-at-boot-and-niri-on-the-mali-owner-2026-11-07)).
The station's `init` loads none of them; nothing changes on the station itself.

## The RAM root is xz-compressed (2026-11-07)

With the perf fragment (`configs/gemini-a53-station-perf.fragment`), the composed boot image
was 17,342,464 bytes, over `boot2`'s 16 MiB (Image.gz 8,990,724, RAM root 8,300,403). Dropping
the function tracers saved only 367 KB of Image.gz. The owner chose to compress the RAM root
with xz instead of gzip: `build-station-initramfs.py` writes xz with a CRC32 check, the one the
kernel's unpacker takes (`CONFIG_RD_XZ=y`), on one thread so the output is reproducible.
station-work-84's RAM root goes from 8,263,753 bytes as gzip to 3,662,992 as xz, because its
static binaries share most of their code. That leaves about 4.4 MB free in `boot2` with the
perf kernel. The parent RAM root stays gzip.

**Booted (`station-work-88`, `boot2` `a2003148…`, boot `e67cb217`).** It was built from
`b161467d` (package `d9e03ad1`) and `0bcbfef9`, and the boot image is 12,345,344 bytes.
- LK passed the xz ramdisk through and the kernel unpacked it. Every station status line was
  normal.
- Unpacking took 1.67 s, from "Unpacking initramfs" at 0.759 s to "Freeing initrd memory" at
  2.426 s. The gzip RAM root on `station-work-86` took 0.44 s.
- `/init` now starts at 2.55 s instead of 1.34 s, about 1.2 s later.
- The PMU node probed (`armv8_pmuv3`, 7 counters). Software, tracepoint, kprobe and uprobe
  events are present.

## nvdata is mounted only to copy the Wi-Fi record (2026-11-07)

Owner decision, after `nvdata`'s superblock changed with no read-write mount found
([Arch root record](../2026-11-06-gemini-arch-root/README.md)): `init` sets the device read-only,
mounts it `ro,noload`, copies the 514-byte Wi-Fi record into RAM as
`/lib/firmware/mediatek/mt6797/WIFI.storage` (mode 0600), and unmounts it at once. Status lines:
`nvdata=record-copied` or `record-failed`, then `nvdata=unmounted`. Nothing keeps `nvdata`
mounted, and a card root gets no `nvdata` mount; it carries its own copy. Not yet booted.

## nvdata's block device is read-only (2026-11-04)

`init` runs `blockdev --setro` on nvdata before mounting it (`2ab5699f`), because ext4 can
run orphan cleanup on a `ro,noload` mount unless the device itself is read-only. On boot
`fccba04c`, image `96338704`, the partition's sysfs `ro` reads 1, it is mounted
`ro,norecovery`, and the calibration stays readable. This shows the normal path only:
no orphan cleanup was provoked, so the protected case has not run.

## backlight-policy: the PMIC keys and idle wakeups (2026-11-03)

The program, then named `lid-guard`, woke once a second to check the blanked console,
and it watched only the lid and the matrix keyboard. The
[PMIC keys](../2026-11-03-gemini-pmic-keys/README.md) restart the kernel's blank timer
without it knowing, so from the code, using only Esc or the side key can start the fade
and turn the light off early. It also noticed their wakes up to a second late.

The change:

- It also watches `mtk-pmic-keys`, as input like the keyboard. Only the keyboard
  drives the brightness keys.
- It sleeps until input or the fade's start. It looks for a blank or unblank every
  50 ms for 1 s after a key or lid event, and once a second from the fade's start
  until the blank.

**Remaining gap:** other input devices, such as a Bluetooth or USB keyboard, can still
wake the console or restart the timer unseen. A wake then stays at the dim level until
the next watched event.

**Checked:** it builds with `gcc -static -O2 -Wall -Wextra -Werror`. **Not yet run on the
device.**

**Test (predeclared), on the running station.** The binary can be swapped in without
a new image.

1. Idle cost: `voluntary_ctxt_switches` in `/proc/PID/status` over 30 s rises by about 0
   when blanked, and when lit with the fade more than 30 s away. It rose by about 30
   before.
2. Esc as the only input, pressed every minute for 3 minutes: no fade and no dark screen.
3. Esc on a blanked console: the light fades up with no 1 s delay, and the log line
   follows within about 50 ms of the key event.
4. Unchanged: the idle fade and blank, a key cancelling the fade, Fn+B and Fn+N, and
   a lid close and open.

If 1 fails, look for what keeps it waking. If 2 to 4 fail, the previous binary is the
fallback.

**Results so far.** Binary `4ee9da4b…`, built from `91defc68`.

- **1, idle cost: passes.** On boot `7978f9ea`, image `8f2c1167`, the switches rose by 0
  over 30 s while lit. On boot `489e5436`, by an earlier live swap, they rose by 0 over
  30 s while blanked. `init` respawns the program under its new name.
- **2 and 3, Esc: pass, by the owner's report.** "esc: prevented from blanking, then woke
  up from blanking so all passed". The 50 ms log timing wasn't measured.
- **4, Fn+B and Fn+N: work, by the owner's report.** "Fn+n and b work too", on boot
  `7978f9ea` or `3fb07fd4`.
- **Still open:** the idle fade and blank, a key cancelling the fade, and a lid close
  and open.

**Regression, owner report:** "I saw the screen blanking without a fade", and "it woke up
with no fade either". From the code, not yet measured on the device: the sleeping program
didn't notice blanking being turned back on. Without input it slept past the fade's
start, so no fade ran, and the fade back up only follows a fade down. The old once-a-second
loop re-read the timeout and hid this. It can also happen at boot, if `console-shell`
sets the timeout after the program has read it.

**Fix.** `setterm` and `console-shell` send `SIGUSR1` after setting the timeout. The
program then restarts its deadline, as the kernel does. A raw `ESC [9;N]` from anything
else still goes unseen, so use `setterm`. A restart of the program also moves its
deadline later than the kernel's, which can miss one fade.

**Timing, boot `3fb07fd4`, binary `4ee9da4b…`.** Blanking was restored at uptime about 771.
A dmesg copy ending at 772.6 is stamped 21:29:49, so the 120 s timer expired about 21:31:50.
The owner reported the blank at 21:32:05, which fits this diagnosis if no key was pressed
after the restore. The log's `console blanked` at 1034.15 doesn't date that blank: the
program logs when it wakes and looks, so with this binary a log time can be much later than
the event. Not explained: brightness read 16 at uptime 1060, which a blank without a fade
wouldn't cause unless the level was already 16.

**Test (predeclared).** With the fix swapped in, and no input after this step:
`setterm --blank 1`. Expect a fade starting about 57 s later, the blank, and a fade up
on the next key. Then repeat step 4 of the earlier test.

**Result so far.** Boot `3fb07fd4`, binary `0a5d265a…` from `e1b603d4`, restarted at 1095.28,
brightness set to 512 first. Sampled every 0.25 s from `setterm --blank 1` at 1109.03, with
no input expected:

| After `setterm` (s) | Event |
| --- | --- |
| +56.89 | Brightness first changes from 512 |
| +59.98 | Brightness has reached 16 |
| +60.24 | `bl_power` 4 |
| +62.07 | `console blanked` logged |

**Step 1's fade and blank pass by measurement**, at the predicted time. The owner's view of
it, and the fade up, a key cancelling the fade and the lid, are still open.

The earlier no-fade blank stays not fully explained. The device session knows of no key
between 771 and 891 but can't rule one out, and the brightness before it wasn't read. A
level of 16 from the earlier Fn+B test would also have meant no fade, and it would explain
the reading of 16. The fixed path was shown at 512 only.

**Owner's verdict,** on the same boot and binary: "All good", answering a question that
covered the fade, the wake by key, a key cancelling a fade, and a lid close and open. It
doesn't itemise them, so those rest on this one report. The blank timeout is back at
2 minutes. The image still carries `4ee9da4b…`, so the fix and the new `setterm` and
`console-shell` need the next RAM root, and the `console-shell` signal hasn't run yet.

The owner then confirmed the fade cancel specifically: a key pressed while it fades
interrupts the blank. The binary and boot weren't stated.

**Review fixes (no device test yet).** An independent code review found these, and each
was confirmed by reading the code. None changes the path the owner passed:

- **simplefb:** only the panel's DRM link clears `bl_power` on a wake, so on the fallback
  path the screen stayed dark after the first idle blank. The wake now clears it if
  it's still set after 500 ms.
- **Lid close during a fade:** the aborted fade relit the backlight behind the closing
  lid. It now leaves that to the lid event.
- **Restart during a fade:** a new run clears a leftover `bl_power` if the console is
  awake and the lid open. The level itself is lost, so brightness stays at 16 until
  Fn+N.
- **Respawn rate:** the stream-ended and poll-error exits now wait 60 s, like the startup
  failures.
- **Unseen input:** if the console is still awake 5 s past the deadline, the program
  restores the light and restarts its deadline. Until then the screen stays dark.

Left as they are: `now_ms` uses `CLOCK_REALTIME`, so a clock step can start a fade early, and
the overdue check recovers from that. A signal arriving during a wake is seen at the next
one, which can miss one fade. `console-shell` resets the timeout to 2 minutes each time it
respawns, as it always has.

A second review found two more ways to relight behind a closing lid, both confirmed by
reading the code and fixed: the wake's `bl_power` write when the lid closes during the
500 ms wait, and a key arriving with the lid event in one fade step. No device test yet.

## First boot of the release image (2026-11-04)

**Hypothesis.** The release RAM root reaches USB SSH with only public userspace, with
Gemian's partition read-only and the radio off. If SSH failed, the console status file
would say why; with no console, Gemian would restore the station image.

**Candidate.** Profile `mt6797-a53-release` from `4c2fc3b7`, package inventory
`6ee52a73…`, public parent `f531d953…` built before `55f23783` (that commit changed only
files added at compose). boot2 `4eefdc42507eda5633f5dcb8186cd12adcd95680495922fa7839bddaa1aaee33`,
written from the station with `flash-boot2`, predecessor `2d6a20a5…`, full readback
matched. Boot `56d30c7c`, one unit, on USB.

**Before the write,** the composed RAM root held no firmware but `regulatory.db`, no
private or host key, and one `authorized_keys` line, the project's public key.

**Observed:**

- `7.1.3-gemini-a53-release`, 8 CPUs, tainted 0, and no kernel error or warning in the
  log. pstore held nothing. The `panic=10` value is on the command line.
- USB SSH took the key. `dropbearkey` waited for randomness, and crng finished at 4.15 s.
- Status lines: `charge-guard=bound`, `data=mounted-ro`, `lid=gemini-lid`,
  `radio=off-no-country`, `audio=ready`, `display=loader-framebuffer`.
- The `linux` partition was mounted `ro,norecovery` and `blockdev --getro` read 1.
- The guard stopped charging at 10.99 s, at 94% against the limit of 80.
- No Wi-Fi interface, no Wi-Fi module loaded, and `iw reg get` showed country 00.
- A 15 s, 1 kHz, −40 dBFS tone on the speakers through Alpine's `aplay` returned 0 and
  the owner heard it. The speaker switch read off afterwards.
- Asked whether the screen, typing and lid looked right on this image, the owner answered
  "All fine". That's by eye on the loader framebuffer, with no key-by-key check.

**Not shown:** every key of the keymap; partition contents unchanged, since no hash was taken before or after; a panic restart or the Esc reset here;
a real charge to 80%; Wi-Fi with firmware and a country; `display-start` here; a second boot.

**Conclusion.** The hypothesis held on one boot of one unit. That removes "never booted"
from release blockers 1 to 3, not the blockers: firmware supply, the country protocol and
a tester's own unit stay open.

## The v1 candidate (2026-11-05)

The owner's definition of [v1](../../docs/RELEASE_READINESS.md) is everything working so far. So `10f2e142`
adds the camera fragment to `mt6797-a53-release`, carries the optional modules in the public RAM root,
and adds `release/hw-start` to load a group by hand. Nothing new loads at boot.

**Built, not booted.** Package inventory `16e5acfd…`, composed on the same public parent `f531d953…` with the
project's public key: boot2 `9e47a9d1ea1bdf55e4a5fd37297eaea2ef943af95b1758e057e650c192f17dfe`, boot image 14202880
bytes. **Checked offline:** 57 modules, every `depends=` met inside the image, and every `hw-start` name
present. No firmware but `regulatory.db`, and no private or host key. The DTB has the sensors, LED, camera, touch
and GPU nodes.

**Test (predeclared).** Through the custodian, one boot, written with `flash-boot2`.

**Hypothesis.** The first boot's results hold, and each group that needs no radio loads from the image on the
release config, which has no `/dev/mem`, `/dev/i2c` or debugfs. The groups have run only on station images.

1. Status file and taint, as on the first boot.
2. `hw-start bluetooth` and `hw-start gnss` print `needs-radio-start`, with no module loaded.
3. One at a time, reading `dmesg` and taint after each: `touch` with one drag, `sensors`, `leds` with Fn+Caps,
   `display-start`, `gpu`, `camera`.
4. Last, `a72`, since CPU_ON is unbounded in secure firmware: `online` should read `0-9`.

| Observation | Meaning | Next |
| --- | --- | --- |
| All load, tainted 0 | The image carries what v1 says, at load level | The owner tags it |
| One group fails to load | That group needs something the release config removed, or an order | Record it; drop the group from v1's list or fix it, the owner's call. Carry on with the others |
| Oops, hang or lost USB | Stop | Preserve what's there; no retry; return to the station image |
| No console and no SSH at boot | The image itself failed | Back through Gemian to the station image; no tag |

**Not in this test:** Wi-Fi and Bluetooth, which need firmware and a country and their own protocol; function beyond
loading, such as rendering or capture, whose tools aren't in the image; colour, which this test doesn't judge.

### Firmware from the owner's device (2026-11-05)

The owner's requirement: "Our v1 image must provide a way for people to extract the fw files from their device."
`release/firmware-get` does that, and `radio-start` calls it after the country check; see
[firmware](../../docs/hardware/firmware.md#getting-them-from-the-owners-own-device). The kernel is unchanged, still package
`16e5acfd…`. The RAM root changes, so the candidate is now boot2
`99267ef0fe1541f4f135399134fa0ee5bbda8e133a644831ad7808ceead79503`, which replaces the hash above.

**Located** in the retained private backup of `linux`, read with `debugfs`: `/data/system.img`, `/vendor/firmware/` inside it,
and the three expected hashes. One unit. The private copy made for the test is deleted.

**Tested in a VM,** with the composed root's own busybox in a chroot, a read-only bind for `/mnt/data` and a copy of that image:

| Case | Printed |
| --- | --- |
| Image present, nothing in place | `ready`; three matching hashes, mode 0644; no loop, mount or partial left; image unchanged |
| Run again | `ready` |
| A bad file in place | `mismatch-WIFI_RAM_CODE_6797`, file left alone |
| One absent, others good | `ready` |
| No image | `no-gemian-system` |
| A wrong file in a stand-in image | `mismatch-ROMv3_patch_1_0_hdr.bin`, nothing kept |
| An image without the files | `missing-ROMv3_patch_1_0_hdr.bin` |
| `radio-start` with a country and no source | `firmware-no-gemian-system`, no module loaded |
| `radio-start` with no country | `off-no-country`, before any read |

**Not shown:** the device's eMMC or its kernel's loop path; a real radio start from these copies; any other owner's layout.

**Added device step:** before step 2, `firmware-get` alone, then compare the three hashes against the station's copies.

**What this candidate carries unproven,** as of the custodian's review: `d060cfa8`'s camera fix, whose retest hasn't passed,
and `kbd-capslock` as the default trigger. `6b966fe9`'s LED load at boot is the station's and isn't in this image, which loads
LEDs only through `hw-start`. Caps Lock turning off on a blank or lid change isn't in this image, and adding it would change the image.
**Queue:** accepted by the custodian after the libcamera retest, not yet written. It has since booted; see below.

### v1 candidate boot (2026-11-05)

Through the custodian, script `v1-boot.sh` `92f9fc89…`. Station `5d9563c7` wrote boot2 `99267ef0…` with `flash-boot2`,
verified, predecessor `aac84ef4`. After a delayed poweroff the owner selected boot2: **boot `2cab775f`**. The return
wrote `aac84ef4` back the same way, verified, and the station came up as `f01ee772` at taint 0. Outputs are kept privately.

**Every stage passed, taint 0 after each:**

| Stage | Observed |
| --- | --- |
| baseline | `root=tmpfs-1g`, CPUs 0-7, `charge-guard=bound`, `data=mounted-ro`, `lid=gemini-lid`, `radio=off-no-country`, `audio=ready`, `display=loader-framebuffer`. `/mnt/data` `ro,norecovery`. No `/dev/mem`, `/dev/i2c-0` or debugfs clocks. The four lines the error pattern matched are all `ramoops` lines. Owner: console, screen and Caps Lock work |
| firmware | `firmware-get` printed `ready`; all three hashes match the [table](../../docs/hardware/firmware.md). No loop device or mount left, only the `nvdata` partition read-only, `/mnt/data` still `ro,norecovery`. The kernel mounted the loop device read-only without journal, then unmounted it |
| radio-gate | `bluetooth` and `gnss` printed `needs-radio-start`, with neither module present |
| touch | NT36772 at 1080x2160, firmware 0x05; one drag gave 108 events |
| sensors | MT6351 (6), battery thermal (1), BMI160 (15) and STK3310 (11) channels. `stk3310` logs `new unknown chip id: 0x11`, not compared with the station's log |
| leds | 8 LEDs; the caps lock LED's trigger is `kbd-capslock` with no write. Caps on: that LED 255 and every other 0; Caps off: 0 |
| display | `display=native`, `mediatekdrmfb`; console moved to the panel at 135x33. Owner: console readable. Only the known `mipi-tx` nvmem line |
| gpu | `card0`, `card1`, `renderD128`; Mali-T880, VGPU at 937500 uV |
| camera | `/dev/media0` and `/dev/video0`, chip id 0x0556, `hi556` bound |
| a72 | CPUs 8 and 9 online, `online` reads `0-9` |

The charger read `Not charging` throughout and the SoC stayed at 29.6–30.5 °C.

**Meaning:** the image carries what v1 says, at load level, on the release config. Tagging is the owner's decision.

**Not tested:** Wi-Fi and Bluetooth, rendering, capture, persistence and partition hashes. Colour wasn't judged.

**Spectre state.** After `a72`, v1 read `Vulnerable` for `spectre_v2` and `spec_store_bypass`. The fresh station boot
`f01ee772`, with CPUs 0-7 and no A72 load, read the same. So this kernel reports both as `Vulnerable` without the A72
step, at least on the station config. Nobody read v1 before `a72`, so whether loading it changes anything there is unknown.
It's not shown that a reboot clears the state.

**Tagged (2026-11-05).** On the owner's word ("Tag v1"), the custodian pushed the annotated tag `v1` on `5c263c74`.
The tested image's inputs come from there: kernel package `16e5acfd…` from `10f2e142`, and the RAM root from `5c263c74`.
Nothing under `release/`, the compose scripts, patches, kernel or configs changed between them. The tag message names
boot2 `99267ef0…` and what wasn't tested. This boot record landed on `main` after the tag.

## Persistent root handover (2026-11-06)

For the [Arch root](../2026-11-06-gemini-arch-root/README.md), `init` gains one branch after
the Type-C step. On a normal start (`atag,boot` mode 0), with exactly one partition named
`gemini-arch` off the eMMC, it waits 3 s for a key on the console. A key keeps the station.
Otherwise it:

- unmounts `/mnt/data`;
- sets the eMMC and each of its partitions read-only;
- mounts the card root read-only, with this image's modules on a tmpfs at `/usr/lib/modules`
  and `nvdata` read-only at `/nvdata`;
- runs `switch_root` to its `/sbin/init`.

With no card, the station runs as before. Any refusal is recorded as `arch=` in the status
file. A failure after the eMMC went read-only leaves the station running, with `/mnt/data`
remounted read-only.

`flash-boot2` lifts the disk's read-only flag and boot2's own for the write, then sets both
again. In a VM, the disk's flag alone kept boot2 read-only.

Tested only in the dev VM so far: see the [Arch root record](../2026-11-06-gemini-arch-root/README.md#step-1-result).
No image with this `init` has been composed or booted.

## FM and GNSS firmware in `firmware-get` (2026-11-07)

[`release/firmware-get`](release/firmware-get) now also copies `mt6631_fm_v1_patch.bin`,
`mt6631_fm_v1_coeff.bin` and the GNSS DSP image `gnss_dsp_6797.bin`, cut out of `libmnl.so`, into
`/lib/firmware/mediatek/mt6797/`, with the hashes in the
[firmware table](../../docs/hardware/firmware.md#the-set-the-card-root-carries). The three Wi-Fi
files stay the only required ones, so `radio-start` behaves as before.

**Tested in the dev VM,** with a static busybox in a chroot and a stand-in `system.img` made from the
private vendor copies:

| Case | Printed |
| --- | --- |
| Image with all six | `ready`; six matching hashes |
| Run again | `ready` |
| Image without `libmnl.so` | `ready-missing-gnss_dsp_6797.bin`; Wi-Fi and FM files in place |
| Wi-Fi files copied by hand, no image | `ready-missing-mt6631_fm_v1_patch.bin`, exit 0 |
| Nothing, no image | `no-gemian-system`, exit 1 |
| A bad GNSS file in place | `ready-mismatch-gnss_dsp_6797.bin`, file left alone |
| Image without `WIFI_RAM_CODE_6797` | `missing-WIFI_RAM_CODE_6797`, exit 1 |

No loop device or mount was left. The RAM root changes, so a release image composed after this has a
new boot2 hash. None has been composed or booted.

**Later the same day, the GNSS file changed:** `gnss_dsp_6797.bin` is now the 106-byte boot header
followed by the image, 61,546 bytes, which `gnss-mt6797` loads to boot the DSP
([0636](../../patches/proposals/0636-gnss-mt6797-boot-the-DSP-from-its-firmware-file.patch)).
`firmware-get` rebuilds the header from `libmnl.so` with busybox `od` and `awk`, as
[`gemian-firmware`](../2026-11-06-gemini-arch-root/gemian-firmware) does, described with the
[firmware table](../../docs/hardware/firmware.md#the-set-the-card-root-carries). Retested the same
way: all six with the new hash, `ready` again, `ready-mismatch-gnss_dsp_6797.bin` for the old
image-only file in place, and `ready-missing-gnss_dsp_6797.bin` with `WIFI_RAM_CODE_6797` copied
when `libmnl.so` is absent. No loop device or mount was left.
