# Experiment: vendor userspace to kernel ABI

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-11-vendor-kernel-abi` |
| Status | `completed` for static ABI inventory and mainline replacement mapping; runtime migration remains future work |
| Device | Planet Gemini 4G software image on MT6797 S01 |
| Vendor environment | Android 7.1.1 plus Gemian, Linux `3.18.41+` |
| Mainline comparison | Linux `7.1.3` from `kernel/manifest.json` |

## Question

Which private kernel interfaces does the working vendor userspace consume, and
what standard Linux subsystem interfaces should replace them during mainline
bring-up?

## Method and safety

The analysis is static and read-only. It scans the private extracted ELF files
for kernel paths, Android properties, ioctl names, dynamic dependencies, class
names, and retained source-path strings. It also reads extracted udev/systemd/LXC
configuration and compares it with the pinned Linux source. No vendor program is
executed, no live process is attached, and no protected data is read.

The private extraction remains outside Git. Only independently written
conclusions and generic interface names are committed.

## Reproduction

Enter the reverse-engineering VM and run:

```sh
mkdir -p ~/reverse-engineering/work/vendor-kernel-abi
python3 ~/gemini-pda-mainline-host/experiments/2026-07-11-vendor-kernel-abi/scripts/scan-interfaces.py \
  ~/reverse-engineering/gemini-vendor \
  > ~/reverse-engineering/work/vendor-kernel-abi/interfaces.tsv
```

The scanner emits a deterministic TSV mapping each kernel-facing path,
property, or ioctl label to its consuming ELF files. Raw generated output stays
in the guest work directory because it is bulky and derived from proprietary
binaries.

Run the sanitized Linux replacement audit after generating the inventory:

```sh
./experiments/2026-07-11-vendor-kernel-abi/scripts/analyze-mainline-abi.sh
```

It emits only inventory counts, exact-string match flags, and Linux source
hashes. The resulting replacement boundary is documented in
[`results/vendor-abi-mainline-design.md`](results/vendor-abi-mainline-design.md).

The 2026-07-11 run found 1,267 distinct interfaces: 790 kernel paths, 384
Android properties, and 93 named ioctl labels. These counts describe compiled
userspace surface area, not confirmed runtime use.

## Display ioctl call graph

`aarch64-linux-gnu-objdump` and radare2 confirm that the 64-bit hardware
composer opens `/dev/graphics/fb%d` and issues the following requests on that
framebuffer descriptor. The request values are independently reconstructed
from the instructions loading AArch64 register `w1` immediately before each
`ioctl` call.

| HWC method | Request | Encoded payload size | Retained label |
| --- | --- | ---: | --- |
| constructor / `queryCapsInfo` | `0x40384fda` | 56 | `DISP_IOCTL_GET_DISPLAY_CAPS` |
| `createOverlaySession` | `0x40244fc9` | 36 | `DISP_IOCTL_CREATE_SESSION` |
| `destroyOverlaySession` | `0x40244fca` | 36 | `DISP_IOCTL_DESTROY_SESSION` |
| `prepareOverlayInput` | `0x40244fcc` | 36 | `DISP_IOCTL_PREPARE_INPUT_BUFFER` |
| `prepareOverlayOutput` | `0x40244fcd` | 36 | `DISP_IOCTL_PREPARE_OUTPUT_BUFFER` |
| `getOverlaySessionInfo` | `0x40504fd0` | 80 | `DISP_IOCTL_GET_SESSION_INFO` |
| `setOverlaySessionMode` | `0x40244fd1` | 36 | `DISP_IOCTL_SET_SESSION_MODE` |
| `waitVSync` | `0x40184fd5` | 24 | `DISP_IOCTL_WAIT_FOR_VSYNC` |
| `prepareOverlayPresentFence` | `0x400c4fd8` | 12 | `DISP_IOCTL_GET_PRESENT_FENCE` |
| `frameConfig` | `0x40584fdc` | 88 | `DISP_IOCTL_FRAME_CONFIG` |
| `waitAllJobDone` | `0x40044fdc` | 4 | `DISP_IOCTL_WAIT_ALL_JOBS_DONE` |
| `queryValidLayer` | `0x40384fdd` | 56 | `DISP_IOCTL_QUERY_VALID_LAYER` |

`setPowerMode` also uses the standard framebuffer `FBIOBLANK` request
`0x4611`. The vendor request type byte is `0x4f` (`'O'`). The apparent
collision at request number `0xdc` is distinguished by encoded payload size.
The table establishes operation boundaries and structure sizes, but field
names inferred from retained C++ types remain unverified until structures are
recovered independently.

By contrast, `/dev/mtk_disp_mgr` is referenced by the picture-quality and
adaptive-backlight libraries (`libpqservice`, `libaal`, and their
dependencies), not by this HWC session path. This is evidence for two private
display control planes rather than one.

## Findings so far

- Display composition depends on the vendor framebuffer/session manager, ION,
  M4U, sync fences, and GED rather than DRM/KMS.
- Sensors use input events plus a broad MediaTek misc-device/sysfs control ABI;
  many virtual sensor classes are software fusion features, not physical chips.
- Thermal and power HALs consume vendor procfs/sysfs policy interfaces.
- Audio is ALSA-based at its core but adds vendor accdet, FM, HDMI, VOW, ANC,
  and CCCI speech paths.
- Connectivity uses STP/WMT character devices and firmware-loading daemons.
- Gemian's native compatibility layer exposes the Android devices through LXC
  and libhybris instead of replacing the vendor ABI.
- Linux 7.1.3 contains useful MT6797 clock, pinctrl, power-domain, I2C, UART,
  watchdog, PMIC-wrap, and ASoC code, but its MT6797 DTS is only a platform
  skeleton and omits almost every Gemini board-facing device.

The durable interpretation and mainline gates are in
[vendor kernel ABI and Linux 7.1.3 gaps](../../docs/hardware/vendor-kernel-abi.md).

## Limitations and next evidence

String evidence identifies interfaces and code organization but not ioctl
numbers, structure layouts, sequencing, electrical constraints, or whether a
compiled alternative path is active. Those require targeted decompilation,
safe live traces, vendor-source archaeology where legally available, and
controlled hardware experiments.

The owner's SSH-agent authorization was restored and the interface map was
correlated with a fresh read-only live DT and driver capture. The next passes
will recover sensor control semantics, ALSA topology, panel initialization,
USB-C port mapping, and boot/power sequencing.
