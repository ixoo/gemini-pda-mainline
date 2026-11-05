# Testing guide for v1

A guide for trying the v1 image on your own Gemini PDA. It goes with
[release readiness](RELEASE_READINESS.md), which says what v1 promises and what it
doesn't. The [safety policy](SAFETY.md) outranks anything here.

> [!CAUTION]
> **v1 ships as it is, and you use it entirely at your own risk.** It can corrupt your data,
> cost you your recovery path or damage your device. It has had limited testing, on one unit.
> There is no warranty ([MIT licence](../LICENSE)) and no promise of support.

> [!WARNING]
> **Nobody but the author has followed this guide, and it has holes:**
>
> 1. **No first install.** There's no tested way for a tester to put the first image on
>    boot2. See [Installing](#installing-to-boot2).
> 2. **No kernel package for testers.** Project kernels come from the project's own
>    Buildbox, and no package is published. See [Building](#building-the-image).
> 3. **One boot.** The release image has booted once, on the author's unit. Only the
>    author has ever written boot2 or booted any image.

## Who it's for

Owners who can use SSH and a Linux shell, can recover a Gemini by themselves, and can
accept losing the unit's data. It isn't a Gemian replacement or a daily driver. Don't
use a Gemini you depend on.

## What it does

The image runs from RAM and keeps nothing across a reboot. It's selected by hand for
one boot at a time, so Gemian stays the default. [Release
readiness](RELEASE_READINESS.md#proposed-v1-scope) has the full scope and the
list of what's missing.

In this image the console stays on the loader's
framebuffer unless you run `display-start`. Gemian's `linux` partition is at
`/mnt/data`, read-only, and the block device is set read-only too.

## Back up first

Do this from Gemian, before anything else, on a host with this repository:

```sh
./scripts/backup-device-mmc --target USER@HOST --dry-run
./scripts/backup-device-mmc --target USER@HOST --all --confirm-read --sudo-password-stdin
```

- The dry run lists the partitions. Stop unless `boot2`, `linux` and `nvdata` each
  appear once by name.
- The backup goes to the ignored `artifacts/device-partitions/`. Check that each image
  in `MANIFEST.tsv` is complete and non-empty, then store it offline and encrypted.
- It reads only, and it holds your IMEI, MAC addresses, calibration, and all your data.
  Never attach it to an issue. The tool has only run on the author's unit.
- Save your Gemian firmware files now as well: [Firmware and radio](#firmware-and-radio).

Before the first write, also follow [Before the first write](SAFETY.md#before-the-first-write),
and confirm Gemian boots.

## Prerequisites

- A Gemini with Gemian working, and a known-data USB cable for the left port.
- Power that won't fail during a write.
- An arm64 Linux host with `sudo`, network, `python3`, `cpio` and `readelf` for the RAM
  root. On an Apple Silicon Mac, `./scripts/dev-vm setup` provides one.
- `python3`, `dtc`, `fdtget`, `fdtput` and `gzip` where you compose the image.
- Your own SSH key pair. The image holds only the public half.

## Building the image

The image holds no firmware and no keys but your public key. You build it yourself,
because it carries your key.

**Kernel.** Profile `mt6797-a53-release`. The only commit booted in this form is `4c2fc3b7`, which
predates sensors, LEDs and the camera; later commits have run only under station profiles:

```sh
KERNEL_PROFILE=mt6797-a53-release BUILD_MODULES=1 ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-a53-release ./scripts/buildbox fetch-package
```

That needs the project's Buildbox, which testers don't have. This is a gap,
[gap 10](RELEASE_READINESS.md#known-gaps-in-v1).
`./scripts/build-kernel --backend vm` exists, but the [workflow](KERNEL_WORKFLOW.md)
reserves it for an explicit owner request, it hasn't been tried on this profile, and
the project doesn't boot VM-built kernels today.

**RAM root.** In the arm64 host, for example inside `./scripts/dev-vm shell`:

```sh
sh /mnt/gemini-pda-mainline/experiments/2026-10-30-mainline-dev-station/release/build-parent.sh ~/artifacts/release-parent
```

It takes only inputs pinned by SHA-256: an Alpine minirootfs, its packages and Linux's
keymap. Alpine removes old package revisions, so it fails with a checksum or download
error once a pin is replaced. That isn't your fault; report it. From the VM, bring the
output to the host with `./scripts/dev-vm export-artifact release-parent/out`.

**Compose.** With `PACKAGE` the fetched kernel directory, `PARENT` the RAM root's `out`
directory, and `OUTPUT` a directory that doesn't exist yet:

```sh
python3 experiments/2026-10-30-mainline-dev-station/compose-station.py PACKAGE PARENT/parent-initramfs.img PARENT/tools OUTPUT KEY.pub
```

It stops with an error on an empty, truncated, damaged or multi-line key, a private
key, or a parent that holds a key or firmware. The result is `OUTPUT/boot2-padded.img`,
exactly 16 MiB, and its checksum is `boot2_sha256` in `OUTPUT/station.json`.

## Installing to boot2

> [!CAUTION]
> Only the author has ever done this, on one unit, and from a running station. Boot2 is
> the only partition you may write. Never write primary boot, boot3, the preloader,
> NVRAM or the GPT.

**The first install is a gap: there's no path for a tester, and this guide doesn't
offer one.** It's [gap 6](RELEASE_READINESS.md#known-gaps-in-v1).

- `flash-boot2` runs on a running station's RAM root. It expects that root's
  `/bin/busybox` and `/run/station`, so it won't work from Gemian as it stands.
- [Writes from Gemian must use the device guard](SAFETY.md#device-identity-before-a-boot2-write)
  inside a complete installer. `scripts/boot2-device-guard.sh --check` only checks, and
  a pass doesn't authorize a write.
- The installers under `experiments/` are each bound to one past candidate, one host
  and private evidence paths. They refuse any other image, and the safety policy
  says not to reuse them.

v1 ships with this gap. The project's advice is to stop here until it's closed. If you go on
regardless, that's on you, and a careless `dd` to the wrong target can lose your recovery path.

**Later writes, from a running release image**, are the path that exists:

```sh
ssh -i KEY -o IdentitiesOnly=yes -o UserKnownHostsFile=/dev/null root@10.15.19.82 'cat > /tmp/boot2.img' < OUTPUT/boot2-padded.img
ssh -i KEY -o IdentitiesOnly=yes -o UserKnownHostsFile=/dev/null root@10.15.19.82 flash-boot2 /tmp/boot2.img BOOT2_SHA256
ssh -i KEY -o IdentitiesOnly=yes -o UserKnownHostsFile=/dev/null root@10.15.19.82 poweroff
```

The image has no `scp` or SFTP server, so files go through `cat`. `flash-boot2` resolves
`boot2` from the live GPT and refuses a wrong size or checksum, or a target that's
mounted, read-only or ambiguous. It keeps the old checksum, writes, and requires a
matching full readback. Keep the device idle, on stable power. Its [exact
checks](SAFETY.md#writing-boot2-from-the-mainline-station) don't cover everything the
guard does. If it reports `NOT intact`, boot2 is damaged, but Gemian isn't touched:
stop and report it.

## Selecting boot2

1. Power off from Gemian or with `poweroff`.
2. Hold the outside side key while the device starts. A start without it boots Gemian.
   The exact timing was never recorded, so keep holding through the startup.
3. Look for a `station#` shell on the screen. Start with the lid open: a closed lid
   turns the backlight off and stops the keyboard.

The first look, on the console:

```sh
cat /run/station/status
```

| Line | Meaning |
| --- | --- |
| `charge-guard=bound` | The charging guard is there. `MISSING` is a stop condition |
| `data=mounted-ro` | Gemian's partition is mounted read-only |
| `lid=gemini-lid`, `audio=ready` | Those modules loaded |
| `radio=off-no-country` | Expected: no radio without your files |
| `display=loader-framebuffer` | Expected |

`display-start` moves the console to the native display and prints `native`. Run it
from SSH, by hand. It worked on one unit on a different image. If it hangs, power off;
nothing runs it at boot.

**USB SSH.** Connect the left port. The device is `10.15.19.82`, with no DHCP. Give
the host side `10.15.19.1/24` on the interface whose MAC is `42:00:15:19:82:00`, and
nothing else: no gateway or sharing. On macOS, once you've [found that
interface](../experiments/2026-07-21-usb-gadget-ethernet/README.md):

```sh
sudo ifconfig "$IFACE" up
sudo ifconfig "$IFACE" alias 10.15.19.1 netmask 255.255.255.0
```

```sh
ssh -i KEY -o IdentitiesOnly=yes -o UserKnownHostsFile=/dev/null root@10.15.19.82
```

The host key is made in RAM and changes on every boot, so `known_hosts` is left out.
Compare the fingerprint `ssh` shows with the one from `cat /run/station/host-key.pub`
on the console. Passwords are refused. If SSH doesn't answer, look at
`/run/station/ssh.log` and `dmesg` on the console.

## Getting back to Gemian

- `reboot`, without holding the side key, returns to Gemian. So does `poweroff`
  followed by a normal start.
- Use those, not `reboot -f`. Then check that Gemian boots normally.
- **A hung kernel has no tested way out.** A panic restarts after 10 s and a restart
  normally lands in Gemian. An Oops or a lockup doesn't restart.
  Holding Esc for about 11 s reset a running station in one test; on a hung kernel
  it hasn't been tried.
  Report what you had to do.

## Firmware and radio

Wi-Fi is a beta. Nothing transmits until you've supplied all of this, and all of it goes
away at reboot, so it's done again on each boot.

1. **While in Gemian**, copy the three files listed in [the firmware
   table](hardware/firmware.md#files-the-mainline-wi-fi-driver-loads) to your host, and
   compare each SHA-256 with that table:

   ```sh
   ssh USER@HOST cat /vendor/firmware/WIFI_RAM_CODE_6797 > WIFI_RAM_CODE_6797
   ```

   They come from your own device. The project ships none, and you may not have the right
   to share them. Calibration is read from your own `nvdata`, read-only, and never copied.
2. **On the running image**, send each file in, with the same name:

   ```sh
   ssh -i KEY -o IdentitiesOnly=yes -o UserKnownHostsFile=/dev/null root@10.15.19.82 'cat > /lib/firmware/mediatek/mt6797/WIFI_RAM_CODE_6797' < WIFI_RAM_CODE_6797
   ```

3. **Set your real country** in capitals, then start. Use only the country you're in:

   ```sh
   echo XX > /etc/radio-country
   radio-start
   ```

| `radio-start` prints | Meaning |
| --- | --- |
| `started-XX` | Country applied, modules loaded. The firmware starts soon after, and `iw reg get` shows the country |
| `off-no-country`, `off-bad-country` | `/etc/radio-country` is missing, or isn't two capitals |
| `absent-no-firmware` | A firmware file is missing or empty |
| `off-reg-failed`, `off-reg-not-applied` | The country wasn't accepted; no module was loaded |
| `off-no-nvdata` | The calibration partition didn't mount; no module was loaded |
| `mt6797-wlan-core-failed`, or another module's name | That module wouldn't load; see `dmesg` |

A wrong ROM patch or a missing calibration record stops the start in the kernel, with an
error in `dmesg`.

**Joining a network.** [`wifi-up.sh`](../experiments/2026-10-30-mainline-dev-station/wifi-up.sh)
runs `radio-start` first and stops if it doesn't start. Its header describes
`/run/station/wifi.env`, which holds the name and PSK in hex (mode 0600, RAM only). This
repository has no tool that makes those values.

```sh
ssh -i KEY -o IdentitiesOnly=yes -o UserKnownHostsFile=/dev/null root@10.15.19.82 'sh -s' < experiments/2026-10-30-mainline-dev-station/wifi-up.sh
```

It's WPA2-PSK only and has only worked on two 5 GHz channels on the author's network, on
the station image: Wi-Fi hasn't run on this one, with Alpine's `wpa_supplicant`. `ip
link set wlan0 down` is one-way until `mac` reloads. Bluetooth isn't in this image.

## Other hardware

Touch, the GPU, Bluetooth, sensors, LEDs, the A72 pair and GNSS are modules in the kernel package,
not in the image. None has been tried on it, and this guide doesn't yet say how:
[gap 11](RELEASE_READINESS.md#known-gaps-in-v1). The camera's fragment isn't in this profile yet.
Results so far, on the author's station, are in the [support matrix](HARDWARE_SUPPORT.md).

## Stop conditions

Stop, power off and return to Gemian on any of these:

- unexpected heat, battery swelling, or a charging anomaly;
- `charge-guard=MISSING`;
- repeated filesystem errors, memory corruption or a watchdog loop;
- any change in how the device recovers, or Gemian not booting normally;
- a `flash-boot2` failure.

While running, the guard stops charging at 80%, at 50 °C and at 0 °C, shown only by moved
limits and emulated temperatures. Charging isn't limited while powered off, and can pass 80%. Don't leave the device
unattended on a charger. A boot that shows nothing isn't a reason to retry over and over:
go back to Gemian and report it. Before repeating a test after a safety stop, [open a
safety-labeled issue](SAFETY.md#stop-conditions).

## Reporting results

Open an issue on this project's GitHub repository. For a vulnerability, use
[the security policy](../SECURITY.md) instead.

Include the commit, `boot2_sha256` from `station.json`, your Gemini variant,
`/run/station/status`, what you did and saw, and what you didn't test. A failure with no
screen and no SSH is a useful report: say how long you waited and how you recovered.

There's no scrubbing tool yet, so do it by hand, and read the result before posting.

- **Remove** IMEI and serial numbers, MAC addresses, IP addresses other than the fixed
  `10.15.19.x` ones, network names, passwords and PSKs, Bluetooth device addresses and
  names, usernames, and host paths.
- **Delete whole lines** that mention your network name. A search-and-replace can miss
  an encoded form. Don't post `wpa.log` or debug supplicant output at all.
- **Never attach** a partition image, `wifi.env`, firmware, `nvdata` or the calibration
  record.
- **Say what you removed**, so that a gap isn't read as device behaviour.
