# Experiment: a long-running mainline development station

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-30-mainline-dev-station` |
| Status | `running`: station boot `eda50de3…` up; all six hypothesis items observed (2026-10-30) |
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
- [`initramfs/`](initramfs/), [`build-station-initramfs.py`](build-station-initramfs.py)
  and [`compose-station.py`](compose-station.py).

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

Confirmed so far, for the named Gemini and boot `eda50de3…`: the station
boots with all six items. Long uptime and the return through `reboot` are
not yet observed.

## Follow-up

If it holds: load `mac` on the station; then module unload and reload
(a detach in 0338's place); then the methodology change.
