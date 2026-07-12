# Gemian hardware-specific userspace

This document identifies the binary compatibility stack installed on the
observed Gemini PDA. It explains the vendor interfaces that made hardware work
under Gemian; it does not make those proprietary binaries part of this
repository or the intended mainline architecture.

For private local analysis, [`scripts/extract-device-userspace`](../../scripts/extract-device-userspace)
copies the identified vendor payload and Gemian bridge files into the
Git-ignored `artifacts/` directory. It never selects NVRAM, calibration,
protection partitions, user data, or block devices.

## Provenance

Observed read-only on 2026-07-11. Android `build.prop` identifies:

| Property | Value |
| --- | --- |
| Product | `Gemini 4G` by Planet |
| Platform | `MT6797`, chip revision `S01` |
| Android | 7.1.1, build ID `NMF26O` |
| Vendor release | `Gemini-7.1-Planet-08102018-V1` |
| MediaTek branch | `alps-mp-n1.mp9` |
| Vendor project | `device/eastaeon/aeon6797_6m_n` |
| ABI | AArch64 with ARMv7 compatibility |

This is strong evidence that the installed system image targets the Gemini 4G
variant. It is not a physical SKU or modem-band inspection.

The supporting experiment and exact HAL hashes are in the
[Gemian hardware-userspace inventory](../../experiments/2026-07-11-gemian-hardware-userspace-inventory/README.md).

## Compatibility architecture

The running system crosses three software boundaries:

1. The MediaTek 3.18 kernel provides most Gemini platform drivers built in.
2. An Android 7.1.1 filesystem runs in an `android` LXC container and supplies
   MT6797 HALs, daemons, proprietary libraries, and firmware-loading helpers.
3. Native Debian/Gemian services use libhybris and purpose-built bridges to
   consume Android graphics, audio, radio, camera, and power interfaces.

Observed active native processes included `lxc-start -n android`, `connmand`,
`ofonod`, `gemian-leds`, `repowerd`, Xorg, and PulseAudio. Observed Android-side
processes included `surfaceflinger`, `cameraserver`, and `sensorservice`.

## MT6797 Android HAL modules

The system contains 29 `*.mt6797.so` HAL paths: 15 32-bit paths and 14 64-bit
paths. Two Vulkan paths are symbolic links to the proprietary Mali library, so
there are 27 distinct regular HAL files.

| HAL | 32-bit | 64-bit | Important vendor dependencies |
| --- | --- | --- | --- |
| Primary audio | yes | yes | audio parameter/custom NVRAM, TinyALSA/compress, AEE |
| Remote-submix audio | yes | yes | Android audio/NBAIO |
| USB audio | yes | yes | TinyALSA and ALSA utilities |
| Camera | yes | yes | `libmtkcam_*`, camera device 1/3, metadata |
| Consumer IR | yes | yes | minimal Android HAL support; physical device not established |
| GNSS | yes | yes | vendor GPS kernel/device interface |
| Gralloc | yes | yes | ION, MTK ION, gralloc-extra, GLES |
| Hardware composer | yes | yes | M4U, ION, display-processing framework, GED, gralloc-extra |
| Lights | yes | yes | LED/backlight HAL |
| Memory tracking | yes | yes | Android memtrack interface |
| Power | yes | yes | Android power HAL |
| Sensors | yes | yes | vendor sensor/input stack |
| Sound trigger | yes | no | Android media stack |
| Thermal | yes | yes | vendor thermal interface |
| Vulkan | link | link | `lib/egl/libGLES_mali.so` and `lib64/egl/libGLES_mali.so` |

The 32-bit and 64-bit primary audio HALs are about 1.31 and 1.33 MB. Camera HAL
entry points are small because the implementation fans out into a large
proprietary camera stack: `libcamalgo.so` is about 18 MB and
`libcameracustom.so` about 8 MB in each ABI. These libraries likely encode ISP,
sensor, tuning, and board policy that cannot be inferred merely from exported
HAL symbols.

## Graphics and display

The Android graphics path consists of:

- proprietary Mali `libGLES_mali.so` for each ABI (about 23.4 and 26.1 MB);
- MT6797 gralloc and hardware-composer HALs;
- `libm4u.so`, `libion_mtk.so`, `libgralloc_extra.so`, `libgpu_aux.so`,
  `libdpframework.so`, and `libged.so`;
- native `libhybris`, `drihybris`, `glamor-hybris`, and
  `xserver-xorg-video-hwcomposer` packages;
- `/usr/lib/xorg/modules/drivers/hwcomposer_drv.so` as the Xorg display bridge.

This stack confirms that Gemian retained Android framebuffer/composer and Mali
userspace. It is not reusable as the target mainline DRM/Panfrost architecture,
but its buffer formats, rotation, synchronization, and M4U/ION expectations are
valuable reverse-engineering evidence.

## Audio, camera, sensors, and power

| Native bridge | Installed component | Role in Gemian |
| --- | --- | --- |
| Audio | `pulseaudio-module-droid` | PulseAudio sink/source/card modules backed by Android audio HAL |
| Camera | libhybris `libcamera.so`, Gemian camera packages | Access to Android camera service/HAL |
| Sensors | MT6797 sensors HAL plus Android `sensorservice` | Multiplexes vendor input/sensor drivers |
| Power | `repowerd`, MT6797 power/thermal HALs | Display/power policy and suspend coordination |
| LEDs | `gemian-leds` service and `/usr/sbin/gemian-leds` | Gemini keyboard/status LED integration |

Audio depends on `libaudiocustparam.so` and `libcustom_nvram.so`; camera includes
`libcam.hal3a.v3.nvram.so`. Those names demonstrate a calibration/configuration
boundary. They are not permission to extract or publish the associated NVRAM.

## Connectivity and telephony

The installed vendor executables include:

| Group | Relevant binaries |
| --- | --- |
| Modem bring-up/filesystem | `ccci_mdinit`, `ccci_fsd` |
| RIL and multiplexing | `mtkrild`, `mtkrildmd2`, `rilproxy`, `gsm0710muxd`, `gsm0710muxdmd2`, `mtkmal` |
| Modem monitoring/logging | `md_monitor`, `md_monitor_ctrl`, `emdlogger1/2/3/5` |
| GNSS | `mtk_agpsd`, `wifi2agps` |
| Connectivity combo | `wmt_launcher`, `wmt_loader`, `wmt_concurrency`, `wmt_loopback` |
| NVRAM broker | `nvram_daemon`, `nvram_agent_binder` |

Related libraries include `libccci_util`, `mtk-rilproxy`, `librilproxy`,
`libmal_rilproxy`, `libviagpsrpc`, and the `libnvram*` family in one or both
ABIs.

Native Gemian uses `ofono`, `telepathy-ofono`, `libgrilio`, and related UI
packages for telephony. Wi-Fi management uses `connman` plus
`connman-plugin-suspend-wmtwifi`. `hybris-usb` supplies USB tethering support.

The modem/RIL/NVRAM programs are tightly coupled to the vendor CCCI ABI and
protected state. They document the old boundary but are not an upstreamable
mainline transport design.

## System integration packages

The most relevant installed Debian packages and observed versions are:

| Package | Version or family | Purpose |
| --- | --- | --- |
| `lxc-android` | Gemian 0.1 | Android mount/container and device-node rules |
| `libhybris` | Gemian 0.1 | Bionic-to-glibc hardware-library bridge |
| `drihybris`, `glamor-hybris` | Gemian 0.2 | Android graphics integration |
| `xserver-xorg-video-hwcomposer` | Gemian 0.3.9 | Xorg output through Android hwcomposer |
| `pulseaudio-module-droid` | Gemian PulseAudio 10 | Android audio HAL bridge |
| `ofono` | Gemian 1.21 | Telephony service |
| `connman-plugin-suspend-wmtwifi` | Gemian 0.0.1 | MTK Wi-Fi suspend integration |
| `repowerd` | Gemian 2019.03 | Power/display policy |
| `gemian-leds` | 0.2 | Gemini LED control |
| `hybris-usb` | 0.2 | USB tethering/network setup |
| `gemian-modular-kernel` | 0.2 | Broad generic 3.18 module supplement |

Enabled systemd integration includes `android-mount.service`,
`lxc@android.service`, `droid-hal-init.service`, `gemian-leds.service`, and
`repowerd.service`, plus Android device/firmware udev rules.

The `gemian-modular-kernel` package installs a very broad collection of generic
kernel modules and unrelated firmware. It does not represent the Gemini's
platform driver boundary: the observed MT6797 board drivers are predominantly
built into the vendor kernel, and no vendor platform `.ko` set was identified.

## Factory and diagnostic software

`factory`, `meta_tst`, `atci_service`, `atcid`, `audiocmdservice_atci`,
`mobile_log_d`, thermal test tools, WMT loopback, Bluetooth test libraries, and
modem loggers are installed. They may reveal protocol names and device nodes,
but they are diagnostic/manufacturing tools. Do not execute them casually:
factory, AT-command, radio, thermal, or NVRAM operations can change persistent
state, expose identifiers, transmit radio signals, or stress hardware.

## Mainline implications

- Treat HAL dependency names and device-node use as reverse-engineering leads,
  not source-compatible APIs.
- Replace gralloc/hwcomposer/Mali userspace with DRM, dma-buf, and Panfrost where
  feasible.
- Replace Android audio, sensor, thermal, lights, and power HALs with standard
  ALSA, IIO/input, thermal, LED, regulator, and power-management interfaces.
- Keep proprietary firmware behind standard firmware-loading boundaries when
  redistribution and hardware applicability are established.
- Keep modem/NVRAM tooling outside ordinary mainline bring-up. Cellular support
  needs a separately reviewed transport and security boundary.
- Never commit these binaries or libraries without verified redistribution
  rights.

## Private extraction

Run from the repository root using SSH-agent authentication:

```sh
./scripts/extract-device-userspace --target gemini@DEVICE
```

Use `--dry-run` to inspect the exact NUL-safe selection first, or
`--vendor-only` to omit native Gemian package files. The extractor refuses a
destination unless Git confirms that it is ignored, refuses to overwrite a
non-empty directory, preserves symbolic links, applies owner-only permissions,
and produces `FILES.sha256`, `SYMLINKS.txt`, and `SOURCE.txt` manifests.
For `lxc-android`, it retains the Gemini `aeon6797_6m_n` device rule and generic
fallback rather than unrelated device profiles.
Successful extractions directly under `artifacts/device-userspace/` update the
ignored `latest` symbolic link for stable access from analysis tools.

The extraction is a private research artifact. It must not be used as a source
of code for upstream patches or redistributed without a license audit.
