# Experiment: left-port USB gadget diagnostic

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-16-usb-gadget-diagnostic` |
| Status | First USB-enumeration test failed; kernel runtime remains unconfirmed |
| Subsystem | MT6797 MTU3/T-PHY, USB gadget, early userspace |
| Device variant | Current Gemini PDA unit; exact retail sub-variant not independently established |
| Date(s) | 2026-07-16 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Can the non-looping LK handoff candidate expose two host-observable milestones
without UART, framebuffer, or storage?

1. A uniquely named `g_ether` device proves that Linux initialized the MTU3,
   USB2 T-PHY, and built-in gadget driver far enough to enumerate.
2. Ping and a TCP diagnostic shell at `10.15.19.82:2323` prove that the external
   initramfs reached `/init`, configured `usb0`, and started userspace service.

## Evidence basis

The latest reviewed `bsg100/gemini-linux` main revision remains
`9d1e565a5ba11ae9585340e3e4bf4cacc233d13c`. Its earlier commit
`fd5b10277198356d8c9b93478af6054b1c643597` demonstrated left-port MTU3
gadget networking. Commit `76cd816b3da62ab918b2eed1312c5b18f6538c31`
causally showed that MT6797 requires the U2 PHY session state forced to
`0x3e2e`, then passed three cable-attached cold boots. Those results are
external evidence, not a runtime claim for Linux 7.1.3 or this unit.

The local implementation deliberately ports only the peripheral path:

- one high-speed USB2 PHY, `dr_mode = "peripheral"`;
- the existing three SSUSB clocks plus the proven parent selection;
- the opt-in B-device session force;
- gadget-only MTU3 and built-in `g_ether` with fixed local MAC addresses;
- one IPv4 interface configured by a storage-inert initramfs.

It does not enable xHCI, USB host/dual-role mode, the USB3 PHY, VBUS sourcing,
Type-C policy, charging control, eMMC, native display, or another network
device.

## Safety assessment

All associated scripts only build, parse, and validate files. They accept no
device, partition, adb, fastboot, MediaTek, or flashing argument. The TCP shell
is intentionally unauthenticated and therefore binds only in a candidate with
no other network-device family enabled; use it only on the direct USB link and
never as a general root filesystem. PID 1 performs no storage discovery or
mount. The kernel configuration disables `/dev/mem` and `/dev/port`, and PID 1
mounts procfs and sysfs read-only. The shell still runs as root and can invoke
privileged operations such as reboot, so the directly attached host must be
trusted. Here, `hardware_write=none` describes candidate generation, not a
sandbox around the runtime shell.

The owner separately authorized one write to the already proven non-primary
`boot2` development target. The prior bytes were copied to the Git-ignored
device-artifact directory, the candidate was zero-extended to the exact 16 MiB
partition size, and the synchronized full-partition read-back matched. Primary
`boot` remained protected. The write evidence is recorded separately because
the build scripts still have no hardware interface.

## Associated code

- `dts/usb-gadget.dtso`: changes only the three already-described USB node
  statuses from `disabled` to `okay`.
- `initramfs/init` and `initramfs/usb-shell`: fixed-IP diagnostic PID 1 and
  marker shell.
- `scripts/build-initramfs.sh`: deterministic static BusyBox archive.
- `scripts/build-usb-diagnostic-dtb.sh`: mandatory LK overlay plus USB status
  overlay and exact-delta validation.
- `scripts/build-usb-diagnostic-candidate.sh`: provenance-bound Android v0
  packaging; no hardware interface.
- [`results/boot2-write-20260716.txt`](results/boot2-write-20260716.txt):
  authorized target, backup, synchronized write, and complete read-back hashes.
- [`results/runtime-usb-enumeration-attempt-20260716.txt`](results/runtime-usb-enumeration-attempt-20260716.txt):
  bounded macOS USB/network observation after the owner connected the device.

The authoritative static result is
[`results/usb-diagnostic-candidate-20260716.txt`](results/usb-diagnostic-candidate-20260716.txt).
The exact candidate is:

```text
package: linux-7.1.3-gemini-usbdiag-3d92a7e9-fdf1d345
file: gemini-lk-usbdiag.boot.img
size: 6520832 bytes
sha256: 41b97a83c53e76cc0fc117660dd4f7189b397f63ea5f6545fc00ef89af0263ca
```

It passed the packaged-kernel checksum/provenance validator, the restricted
USB configuration check, exact DT-delta validation, the recovered LK/arm64
layout parser, and a second complete byte-for-byte candidate build. The
exported copy and every companion log also pass `SHA256SUMS` on macOS at:

```text
artifacts/vm-export/boot-candidates/gemini-usbdiag-20260716-B-3d92a7e9-fdf1d345/
```

That path is deliberately Git-ignored. Re-exporting this exact directory is
bounded and refuses to overwrite an existing host copy:

```sh
./scripts/dev-vm export-artifact \
  boot-candidates/gemini-usbdiag-20260716-B-3d92a7e9-fdf1d345
```

## Expected host observations

This candidate intentionally has no simple-framebuffer overlay, so a dark
screen is expected and is not a failure signal. Before connecting the Gemini,
save the existing Mac interface list:

```sh
BASE_IFACES="$(ifconfig -l)"
```

With a known-data cable directly in the left port, the host should first
enumerate:

```text
0525:a4a2 Gemini-LK-USB-Diagnostic-B
serial: GEMINI_USB_DIAG_20260716_B
```

On macOS, bound enumeration can be checked for up to 90 seconds without
assuming an interface name:

```sh
MARKER=GEMINI_USB_DIAG_20260716_B
n=0
while [ "$n" -lt 90 ]; do
  ioreg -p IOUSB -w0 -l | grep -qF "$MARKER" && break
  n=$((n + 1))
  sleep 1
done
ioreg -p IOUSB -w0 -l | grep -F "$MARKER"
```

The exact serial marker proves that this kernel reached MTU3/T-PHY/`g_ether`
enumeration; it does not yet prove `/init`. Find the interface by its fixed
host-side MAC instead of hard-coding `enN`:

```sh
find_gemini_if() {
  for i in $(ifconfig -l); do
    mac=$(ifconfig "$i" 2>/dev/null |
      awk '/^[[:space:]]*ether / {print tolower($2); exit}')
    case "$mac" in
      42:00:15:19:82:00|42:00:15:19:82:01) printf '%s\n' "$i"; return ;;
    esac
  done
}
IFACE=$(find_gemini_if)
```

If that is empty, compare `ifconfig -l` with `$BASE_IFACES` and inspect only
new Ethernet interfaces. Stop until the correct interface is known. Then give
it the host address and bind the probes to that link:

```sh
sudo ifconfig "$IFACE" up
sudo ifconfig "$IFACE" alias 10.15.19.1 netmask 255.255.255.0
ping -b "$IFACE" -S 10.15.19.1 -c 3 -W 2000 10.15.19.82
nc -4 -b "$IFACE" -s 10.15.19.1 10.15.19.82 2323
```

Enumeration without ping isolates the failure after the kernel gadget path and
before successful initramfs IP setup. Ping proves `/init`; the netcat session
must print both `GEMINI_USB_DIAG_20260716_B` and
`stage=interactive-initramfs`, then provides the first interactive channel.
Do not enable Internet Sharing or bridge this unauthenticated root shell.
Remove the temporary host address after the test with
`sudo ifconfig "$IFACE" -alias 10.15.19.1`.

## Runtime result

The exact candidate is present on logical `boot2` (`/dev/mmcblk0p30`), with a
matching full 16 MiB read-back. After the owner subsequently connected the
device to the Mac, a 90-second bounded check found no candidate USB marker, no
generic child USB device, and no fixed-MAC Ethernet interface. The former
Gemian SSH endpoint also timed out. An owner-requested retry watched all USB
children and the fixed MAC addresses for another 60 seconds with the same
result. These checks did not independently establish the selected boot slot,
button timing, physical Gemini port, or cable data capability, so they record
`enumeration not observed` rather than a USB-driver failure. Kernel and
initramfs execution remain unconfirmed; ping and the TCP marker could not be
attempted.

The owner subsequently confirmed that the test did not work. This promotes the
host observation from a provisional check to the negative result of this test,
and then reported that the device remained dark and steady without a reboot or
loop. That behavior rules out a visible reset cycle but still cannot
distinguish a running kernel, a held panic, or an early hang, nor identify which
pre-enumeration boundary failed.
