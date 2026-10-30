# Experiment: a long-running mainline development station

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-30-mainline-dev-station` |
| Status | `planned`: kernel change, profile and RAM root for review; tested in the VM and QEMU; not built on Buildbox or booted |
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
  - the firmware still starts at boot, and CONSYS keeps the started HIF;
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
- **No radio action:** `mac` is not loaded. The CONSYS owner starts the
  firmware at boot, as on every Wi-Fi boot so far.
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

None yet.

## Conclusion

Not run.

## Follow-up

If it holds: load `mac` on the station; then module unload and reload
(a detach in 0338's place); then the methodology change.
