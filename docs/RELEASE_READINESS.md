# Release readiness

What v1 is, what it leaves out, and what stands in the way of daily use.

> [!CAUTION]
> **v1 ships as it is, and you use it entirely at your own risk.** It can corrupt your data,
> cost you your recovery path or damage your device. It has had limited testing, on one unit.
> There is no warranty ([MIT licence](../LICENSE)) and no promise of support.

The owner shipped v1 on 2026-11-04: "v1 is what we have now. we can always do better, but let's
ship what we currently have." So the gaps below are known limits of v1, not conditions on it.
This comes from reading the records, patches and logs, not from new device runs. The
[support matrix](HARDWARE_SUPPORT.md) owns demonstrated support.

## What v1 is

Everything shown working so far, with the limited testing it has had. The
[support matrix](HARDWARE_SUPPORT.md) is the list, and each row says how little has been run: most
of it on one unit, much of it on one boot, and several parts from modules loaded by hand.

It's for technical owners who can recover a device and want to experiment. It isn't a Gemian
replacement or a daily driver. As it stands:

- **Most results come from the station,** the project's own image, whose RAM root holds private
  keys and firmware and doesn't ship. The public release image is built to replace it for others.
- **The candidate has booted once.** [`10f2e142`](../experiments/2026-10-30-mainline-dev-station/README.md#the-v1-candidate-2026-11-05)
  carries every working module, and `hw-start` loads the optional groups by hand. On its one
  [boot](../experiments/2026-10-30-mainline-dev-station/README.md#v1-candidate-boot-2026-11-05) `firmware-get` copied matching firmware, and every group but the radios loaded with
  taint 0. That's load level only: radios, rendering, capture and persistence weren't tested.
- **Modules aren't applications.** The image has no Mesa, BlueZ, GNSS host or camera tool, so those
  need userspace you bring.
- **Nobody else has installed it,** and there's no first-install tool. Getting it onto boot2 the
  first time is yours to work out, and yours to answer for.
- **cpufreq and power governors are missing,** so CPUs stay at firmware's clocks and battery life
  isn't useful.

## Status by area

| Area | In the release image | State and limit |
| --- | --- | --- |
| Recovery, boot selection | Yes | Works, one unit. Primary boot untouched; hold the side key for boot2. Holding Esc reset a running station once, untimed, and on a hung kernel it's untested |
| Install | From a running image only | `flash-boot2`. No first install; the [guide](TESTING_GUIDE.md) says so |
| Reproducibility | Partial | Kernel pinned, built on Buildbox only. The RAM root has a [public recipe](#release-ram-root) |
| Unit dependence | Low | No keys, firmware or fixed country in the image. USB addresses stay fixed |
| Root filesystem | RAM only | Nothing persists across a reboot, firmware and the country included. No distribution path |
| Charging, running | Yes | Guard bound on the one boot. 80% and the 0 to 50 °C window shown by moved limit and emulation, not a real charge or a really hot or cold battery |
| Charging, powered off | Not limited | The loader decides; it can pass 80% |
| Thermal | Built in | Trips armed on the station, and none has fired. No CPU cooling, so nothing slows a hot CPU before the power-off at 110 °C (inference from the trip table) |
| cpufreq, cpuidle, suspend | No | Not started. CPUs stay at the clocks firmware left. Decides battery life and heat |
| A72 | In the image, by hand | One option on a station profile, loaded by hand, fixed 750 MHz. The command line keeps `maxcpus=8` |
| Keyboard, lid | Yes | "All fine" by the owner on one boot, with no key-by-key check. Fn map captured once on the station; wider rollover open |
| Display | Loader framebuffer | Native at 54 Hz works on the station, adopted from the loader. Here it needs `display-start` by hand, not run on this image: blocker 4 |
| Speakers, headphones | Yes | A speaker tone on one boot. Both at 48 kHz on the station |
| Internal mic, jack | Yes | On the station, capture follows speech. Headset type and buttons open |
| Wi-Fi | Yes, off until set up | Never run on this image. On the station: two 5 GHz channels on one network, WPA2-PSK. No rekey, WPA3, DFS or power save. Idle link lost at about 6 min. `ip link down` is one-way until `mac` reloads |
| USB | Yes | Gadget and SSH work; no host or role switch |
| Touch | In the image, by hand | Hand-loaded on the station; events on one boot, accuracy untested, a blanked screen gave no interrupt |
| GPU, desktop | In the image, by hand | Panfrost hand-loaded on the station. No Mesa in the image and no compositor |
| Bluetooth | In the image, by hand | A2DP heard with one headset, from a private chroot. mSBC clean on one run with no bridge for voice. Placeholder address. [SBC skips from about 4 yards](../experiments/2026-11-02-gemini-bluetooth/README.md#t14-result-no-timeouts-at-all-and-the-music-skips-with-distance-2026-11-04), with no control yet |
| Sensors | In the image, by hand | [IMU and light/proximity](hardware/gemini-sensors.md) hand-loaded on one boot, uncalibrated |
| Indicator LEDs | In the image, by hand | [Module](hardware/aw9120-led.md) lights them at 3.5 mA on one boot; caps lock as the default trigger hasn't run |
| GNSS | In the image, by hand | No position on mainline; needs a userspace host |
| Camera | In the image, by hand | [Capture node through a test tool](../experiments/2026-11-04-gemini-camera-receiver/README.md#n1-and-n2-the-capture-node) on the station; local format codes, [libcamera so far gives no frames](../experiments/2026-11-04-gemini-camera-receiver/README.md), and M4U bypassed |
| microSD | Unknown | Prepared, never booted |
| Modem | No | Not started |

"In the image, by hand" means `hw-start` loads it, and nothing does at boot. None of these has run
on this image yet.

<a id="blockers-for-a-first-test-release"></a>
<a id="blockers-for-v1"></a>
## Known gaps in v1

Numbers stay as they were, since records cite them. All of these are open in v1, and closing
them is for later releases. Where a decision was pending, v1 takes the state that booted.

| # | Gap | State | In v1 | Effort |
| --- | --- | --- | --- | --- |
| 1 | RAM root from public sources, with no keys or firmware; host key made on first boot, tester's own SSH key | Booted once on the author's unit, [below](#release-ram-root). Not on a tester's. Alpine's package pins need a kept copy or mirror | The recipe fails loudly once a pin goes | M |
| 2 | The image gets firmware from the owner's own device, with a hash check; Wi-Fi absent cleanly otherwise | [`firmware-get`](hardware/firmware.md#getting-them-from-the-owners-own-device) reads it from Gemian's `system.img`, each boot. Run in a VM on one retained image; not on a device. Absence booted once | Automatic on Gemian's layout, one unit's known; by hand otherwise | S-M |
| 3 | Release profile, below | Package booted once. The command line items stay open | Keeps the test-named USB identity | S-M |
| 4 | Leave Gemian's root read-only by default, or use one dedicated directory | Read-only booted once, at a cost to the display: [below](#release-ram-root) | Read-only, so the console stays on the loader framebuffer | S |
| 5 | A country setting replaces fixed US; radio off until set | `radio-start` refused without a country on one boot; the path with one hasn't run. Owner protocol open | Set by hand on each boot | S |
| 6 | First-install tool from Gemian using the existing guard; backup, restore and removal steps | Not started | None: the guide offers no first install | M |
| 7a | Ten cold boots and a real charge reaching 80% | Not run | Unknown | M, needs the device |
| 7b | The Esc reset on a hung kernel, the Wi-Fi baseline, a soak | Not run. The owner said "Not now" to the baseline | Unknown | M, needs the device |
| 8 | One non-author unit follows the guide unaided | Not done | No other unit has run it | M, availability risk |
| 9 | Tester docs, refreshed matrix, sanitized bug-report tool, source for shipped binaries | [Guide](TESTING_GUIDE.md) written, followed by nobody. No scrubbing tool. The kernel's source is this repository at `4c2fc3b7` and the pinned upstream; no source copies of Alpine's binaries, which the recipe downloads rather than ships | Scrub reports by hand | S |
| 10 | A published kernel package, from a public manifest, with its source and no firmware | Not published yet. Testers have no Buildbox, and the VM path is reserved and untried on this profile | Build it yourself until then | S-M |
| 11 | A way to try the optional modules: add them to the image, or document loading them. Mesa and BlueZ would need a public userspace, or stay out | The modules are in the image with `hw-start`; each non-radio group loaded on one boot No public userspace for Mesa or BlueZ | Bring your own userspace | S-M |

For a later release, items 1 to 4 and 11 change boot files, so batch them into one image.

### Release profile

Phase A's profile is `mt6797-a53-release`, from
[its fragment](../configs/gemini-a53-release.fragment), which says what each removal
breaks and what stays open. It has [booted once](../experiments/2026-10-30-mainline-dev-station/README.md#first-boot-of-the-release-image-2026-11-04).
The list below is the station it departs from.

- Forced command line today: `initcall_debug`, `nokaslr`, `earlycon`,
  `clk_ignore_unused`, `console=ttyS0` only, and a test-named USB identity with a fixed
  address.
- `panic=10` (owner decision, 2026-11-04): a panic restarts after 10 s and keeps the crash
  record, as [pstore T1](../experiments/2026-11-03-gemini-pstore-retention/README.md)
  showed with that value set at run time. There's still no lockup detector or
  `panic_on_oops`, so an Oops or a lockup stays hung, and a kernel stuck like that no
  longer kicks the charger watchdog, which restores charging in about 47 s (inference
  from the guard record). The command-line value is live on the station and this image;
no panic has run on either with it.
- Remove unless justified: `THERMAL_EMULATION`, `DEVMEM`, `I2C_CHARDEV`, `DEBUG_FS`.
- Log noise: 150 `dev_info` calls in Wi-Fi and CONSYS with no `dev_dbg`, and "one-shot"
  naming 82 times in Wi-Fi. `wait_for_bt_irq` printed 1939 lines in one Bluetooth run,
  55% of that log. Debug module parameters on Panfrost, panel and `mtk_drm`.

### Release RAM root

Two steps, with [`compose-station.py`](../experiments/2026-10-30-mainline-dev-station/compose-station.py)
and the files in [`release/`](../experiments/2026-10-30-mainline-dev-station/release/):

```sh
# In the VM. Pinned by SHA-256: the Alpine 3.22.7 minirootfs, packages.sha256, Linux's keymap.
release/build-parent.sh WORK
# With a mt6797-a53-release package. The last argument is the tester's public key.
compose-station.py PACKAGE WORK/out/parent-initramfs.img WORK/out/tools OUTPUT KEY.pub
```

The image holds Alpine's busybox, dropbear, iw, wpa_supplicant, amixer and aplay with
their libraries and regulatory.db, and two tools compiled from this repository. The
station's path doesn't change: its boot2 stays
`91ac2cbefa3a6529e5a6a09265df2f5b9f8177c726f08ec48b53beb62c051195`. The differences
are in `release/`:

- **Keys.** `authorized_keys` comes from the compose argument, and the composer refuses
  a key that's empty, truncated or of a type dropbear lacks, and a parent that holds a
  key or firmware. `usb-ssh` makes the host key in RAM, so it
  changes on every boot, and `/run/station/host-key.pub` shows it on the console.
- **Radio.** Init loads no Wi-Fi module by itself. `radio-start` needs a two-letter
  `/etc/radio-country`, gets the three firmware files through `firmware-get`, then sets the
  country, waits to see it applied, and loads the driver. Both live in RAM, so a tester sets the
  country after each boot and runs it by hand. `wifi-up.sh` runs it first on this image and stops if it doesn't start.
- **Gemian.** `linux` mounts `ro,noload`, with the block device set read-only first, and
  so does `nvdata` in `radio-start`. Without that, a read-only ext4 mount still clears an
  orphan list on disk: in a VM, `ro,noload` alone changed an image holding one, and
  7.1.3's `ext4_orphan_cleanup` has the same path. The station's `nvdata` mount [gained
  this later](../experiments/2026-10-30-mainline-dev-station/README.md#nvdatas-block-device-is-read-only-2026-11-04),
  normal path only. Without a writable marker a stuck native
  display load couldn't be skipped on the next boot, so the console stays on the
  loader framebuffer and `display-start` is by hand. So v1 has no native console at boot.
- **Removed interfaces.** `power-status` is left out. Nothing else in the image uses
  `/dev/i2c`, `/dev/mem` or debugfs.

**Checked offline, 2026-11-04:** two recipe runs gave the same parent. Every binary ran
in a VM chroot of the composed RAM root. SSH there took the key and refused a password,
with dropbear on loopback, not `usb0`. `radio-start` stopped before any module without a
country, with a bad one, and with a missing firmware file. `regulatory.db` verifies
against the same signer as the station's.

A second pass the same day ran the composed root's own init as PID 1 of a VM namespace,
with a veth named `usb0` and loop devices behind a stand-in for the partition list. Init
reached SSH and a console shell with a controlling terminal, the keymap loaded, the
loop images of `linux` and `nvdata` stayed byte-identical, `poweroff` ended it cleanly,
`flash-boot2` wrote and read back a loop device and refused bad input, and `insmod` loaded
a VM module. `iw` was a stand-in past `reg set`, since the VM has no `cfg80211`.

**[First boot](../experiments/2026-10-30-mainline-dev-station/README.md#first-boot-of-the-release-image-2026-11-04), 2026-11-04, one unit:** init, Alpine's `insmod`, USB SSH, the
host key, the read-only mount settings and a speaker tone with Alpine's ALSA worked, the
radio stayed off, and the owner found the screen, typing and lid fine.

**Unverified:** Wi-Fi with Alpine's wpa_supplicant and
its older `regulatory.db`, `iw reg get` matching the wait, and that the partition's
contents stay unchanged across a boot. Alpine removes old package
revisions, so the pins fail loudly once one is replaced; a kept copy of the packages or
a mirror is still needed, along with the source for shipped binaries (gap 9).

<a id="proposed-v01-for-testers"></a>
<a id="proposed-v1-scope"></a>
## v1 scope

**Everything in the [matrix](HARDWARE_SUPPORT.md) that works,** with the limits each row gives.

**Shown on the release image, once, on the author's unit:** boots from boot2 by holding the side key.
Console and typing on the loader framebuffer. USB SSH with your own key. Charge guard bound, lid, a
speaker tone. Primary boot, NVRAM, GPT and the preloader weren't written; partition contents weren't
hashed across the boot.

**Shown only on the station so far:** native display, thermal trips, headphones and capture, Wi-Fi as
a beta with your device's own firmware, touch, GPU, Bluetooth, sensors, LEDs, the A72 pair, GNSS tracking and the
camera through a test tool.

**It doesn't:** replace Gemian or persist anything across a reboot; suspend, scale CPU clocks or offer
useful battery life; slow down when hot rather than power off; limit charging while off; provide a
desktop, USB host, microSD, modem or a GNSS position; offer reliable Wi-Fi; support unique Bluetooth
addresses or more than one nearby Gemini on Bluetooth; promise anything about other hardware variants, or
any unit but the author's.

**Safety:** back up every readable partition privately, since backups hold calibration and
identifiers. Confirm Gemian boots and `boot2` exists by GPT name. Use stable power for writes. A plain
`reboot` returns to Gemian. Stop on heat, swelling, charging anomalies or watchdog loops. Holding Esc
about 11 s resets the device; it ran once, on a running station. Scrub logs of addresses and network
names. Set the right country before radio use.

## Code quality

Reviews read the code; sampled checkpatch found 0 errors, so style isn't the problem.
Structure is.

- **Series shape, at the audit.** 712 patches, +113.6k lines. 95 of 136 new C and asm files (47.3k of
  73.1k lines) and 183 of 204 new Kconfig symbols are off in the station config. 303
  patches touch only files the series itself created. No maintainer could review this.
- **Authorship, at the audit.** 508 of 712 have a placeholder `From:`, and few have a true
  `Signed-off-by`. Only the owner can certify; none may be invented.
- **Generic code.** Diagnostics in `lib/kobject_uevent.c`, `kernel/ksysfs.c`,
  `kernel/cpu.c` and `i2c-mt65xx.c`; thermal maps TOPRGU registers directly.
- **Wi-Fi.** 14k lines; `mt6797_mac_join_work` is 1036 lines; polled receive. Expect
  rejection as it stands (inference).
- **CONSYS.** A static singleton with hardcoded addresses, and a 296-line probe.
- **`check-repository`.** It refuses orphan patches and MAC addresses, and counts
  placeholder `From:` lines, warning on new ones. It still misses IP or SSID patterns.

**Proposed cut.** Phase A: a `release` profile from HEAD, leaving history alone, which is done.
Phase B: delete the off scaffolding, prove objects match today's build, and regenerate
about 60-80 patches by area, SoC foundation first, with A72 as a separate last topic.
The old series stays in Git as evidence.

## Upstream blockers from the patch review

Details are in each experiment's record.

- **Charge guard:** suspend and unbind fail open; DT properties encode policy; `0520`
  needs `i2c0` enabled in source.
- **Display and lid:** the `0515` hold doesn't hold against VT and DRM restore paths;
  `0503` uses a provider API from consumer drivers; `0502` and `0507` delete required DT
  properties; the backlight link exists only through `station-dt.sh`.
- **Bluetooth and CONSYS:** a resent STP frame may be transmitted twice, which would fit
  T13's `sent 0 < count 1` warnings, though the firmware mechanism is inferred, and
  `0525` keeps its resend until that's tested. btcvsd has no dependency on CONSYS being
  powered, so it stays hand-loaded with CONSYS up. Send blocks shorter than recovery;
  clients aren't told of a link stop.
- **GPU:** `0493` may wait on reclaim in the fence path.
- **PMIC keys:** patches 0001, 0002, 0006 and 0007 of the keys topic carry a placeholder
  author, and the first two are marked as unsigned drafts. The owner has to review and
  certify them.
- **Camera:** the format codes are local, CAMSV0 bypasses the M4U through a larb2 bit with
  stray writes not ruled out, and the SMI clock is critical until an SMI driver owns it.
