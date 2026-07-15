# Experiment: Gemini boot contract recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-boot-contract-recovery` |
| Status | `inconclusive` for mainline boot; vendor image and LK handoff contract recovered |
| Subsystem | Android boot image, retained Planet LK, chosen DT properties, and root storage |
| Device variant | Gemini PDA running Gemian; installed image identifies Gemini 4G |
| Date | 2026-07-12 |
| Investigator | Repository maintainer with Codex assistance |

## Question

What does the current Planet LK → Linux handoff require, and how does it differ
from the raw `Image`/DTB artifacts emitted by the Linux 7.1.3 build workflow?

## Safety

The live probe reads only `/sys/firmware/devicetree`, `/proc/mounts`,
`/proc/partitions`, and block-device sysfs metadata. It does not open a block
device, read partition contents, change boot selection, or write any boot,
GPT, NVRAM, preloader, or secure-firmware area. Boot images remain private and
ignored; only redacted metadata and hashes are recorded.

Run the live probe through the existing key-only SSH path:

```sh
ssh -i artifacts/credentials/gemini_ed25519 \
  -o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes \
  gemini@192.168.1.50 'bash -s' \
  < experiments/2026-07-12-boot-contract-recovery/scripts/collect-live-boot-contract.sh
```

Parse a private Android boot image without extracting its payloads:

```sh
python3 experiments/2026-07-12-boot-contract-recovery/scripts/analyze-android-boot-image.py \
  artifacts/vendor-kernel/gemian-2019/boot.img
```

The repository also contains a non-flashing Android boot-image v0 serializer:
[`build-android-boot-v0.py`](scripts/build-android-boot-v0.py). It requires
explicit kernel, ramdisk, DTB, and command-line inputs and refuses to overwrite
an existing output. Its defaults reproduce the recovered LK addresses
(`kernel_addr=0x40080000`, `ramdisk_addr=0x45000000`, `tags_addr=0x44000100`,
page size 2048). The default `--dtb-mode append` matches the observed v0 image
shape (`dt_size=0` with a DTB appended to the kernel payload); `--dtb-mode
field` is available for loaders that explicitly support the header DT field.
The `--lk-android8` guard mirrors LK's `bootopt` token offset (`+0x12` from
the token start), additionally validates the 512 KiB kernel-address alignment,
checks the gzip stream, and rejects a decompressed Image larger than the MT6797
LK 50 MiB buffer.
The serializer does not flash, select a partition, or prove that LK accepts a
candidate. Do not reuse the vendor ramdisk or command line without a separate
review.

## Retained LK source audit

The public Planet Gemini Android 8 LK source was audited at commit
`f4988d74bb70a0a15d7f362f412afba7e7fcda46` (see
[`lk-boot-contract-audit-20260713.txt`](results/lk-boot-contract-audit-20260713.txt)
and [`audit-lk-boot-contract.sh`](scripts/audit-lk-boot-contract.sh); the
current package-only rerun is [`lk-boot-contract-audit-current-20260713.txt`](results/lk-boot-contract-audit-current-20260713.txt)). Its
MT6797 platform rules override the generic 28 MiB decompression buffer with
`0x03200000` (50 MiB). The 64-bit path is selected only when `bootopt` contains
`64`; it passes the Android kernel payload to `gunzip`, scans the loaded payload
for the last valid appended FDT, and does not use the Android header `dt_size`
field. The kernel address must satisfy the `0x7ffff` alignment mask; the
observed `0x40080000` address does.

The active vendor image matches that contract: gzip kernel, `bootopt=64...`,
`dt_size=0`, and a 130,745-byte FDT immediately after the gzip stream. The
earlier 72-patch candidates used the raw uncompressed `Image`, so their parser
success was not evidence of LK compatibility; the header-DT-field candidate is
also insufficient for this loader. They are retained as historical evidence,
not boot candidates.

The rebuilt package now emits `Image.gz`. Its 48,547,848-byte decompressed
payload fits the MT6797 LK buffer. A private Android v0 candidate using
`Image.gz`, the Gemini DTB, a minimal static ARM64 initramfs, and the observed
`bootopt=64S3,32N2,64N2` parses as LK-compatible. It has not been transferred,
flashed, or booted; UART evidence is still required.
The earlier [71-patch revalidation](results/mainline-71-lk-candidate-revalidation-20260714.txt)
and `ca17601dcdeb` candidate remain historical. The corrected 72-patch
candidate is also retained as provenance, but the current working series has
74 patches after the SPI controller boundary was added. The authoritative
current candidate was regenerated from package `c2feb465d6c6`; its sanitized
provenance is recorded in the [current 74-patch candidate result](results/mainline-74-lk-candidate-current-20260714.txt).
The corrected package-only LK recheck is recorded in
[`lk-boot-contract-current-c2d9-20260714.txt`](results/lk-boot-contract-current-c2d9-20260714.txt).
It uses the current `Image.gz` (`5602839538…`), Gemini DTB (`b4158026…`), and a
1,006,095-byte static ARM64 UART initramfs. The candidate parses as an Android
v0 gzip+appended-DTB image compatible with the retained LK contract; it has not
been transferred, flashed, or booted. Its serialized `console=ttyS0` token is
the boot-image header input, not proof of the final Linux command line: LK's
preloader-controlled console mutation runs before the header command line is
appended and LK then overwrites `/chosen/bootargs`. See the [LK console mutation
audit](../2026-07-13-uart-console-recovery/results/lk-console-mutation-current-76-20260714.txt).

The companion [LK FDT fixup audit](../2026-07-13-lk-fdt-fixup-recovery/README.md)
establishes the next part of the contract: early-DTB loading is followed by
LK rewrites to `/memory`, `/chosen`, model/CPU metadata, and Android firmware
properties, then runtime `mblock-*` reservations are appended after an
overlap check. The current package preserves the pre-LK dynamic reservation
contract and intentionally omits static post-LK mblock snapshots. The
previously serialized private LK candidates used superseded package/DTB hashes
and must not be flashed. The current private candidate is
`guest:~/artifacts/boot-candidates/20260714-wrapper-repro-c/linux-7.1.3-gemini-c2feb465d6c6.boot.img`
(SHA-256 `ef8ea5de93aa32a632cfd9ace930e199953da8bf4be08a3d9774c4597f2b588e`),
with a deterministic 1,006,029-byte initramfs (SHA-256
`4d4bbe05fa7c11a39d5e6341e551458d787344fd311cbefcb82e071f83ce5ef4`). Two
independent wrapper runs produced byte-identical candidate and initramfs files.
It has not been transferred, flashed, or booted. The prior 72-patch candidate
and the pre-wrapper 74-patch candidate are historical provenance only.

The focused 75-patch package has since been wrapped independently as
`guest:~/artifacts/boot-candidates/20260714-75/linux-7.1.3-gemini-a21fac4139df.boot.img`.
Its gzip+appended-DTB parser contract passes with candidate SHA-256
`03642410126f4e10d71ae55d05539eadf1a15effc2227d3561324459b4eaf080`,
`Image.gz` SHA-256
`30c4f370382de1d2ba82417061b2712a5edc12fd16a0ab766358e7952a27d39c`, and
DTB SHA-256
`21529f78282cbf3a48f9260b8981f005f3643d54e729ab676384880c6ace1d4c`. The
sanitized record is
[`mainline-75-lk-candidate-current-20260714.txt`](results/mainline-75-lk-candidate-current-20260714.txt).
It remains private, non-flashed, and unbooted.

The authoritative current 77-patch package is now wrapped as
`guest:~/artifacts/boot-candidates/20260714-77-diagnostics4/linux-7.1.3-gemini-6116c9e7da3f.boot.img`.
Its candidate SHA-256 is
`4cc0cc0df784e7ff79633884e2b093e3c2bc1d9c6f74f01af972a7034e88997c`; the
matching Image.gz and Gemini DTB hashes are
`cd1b762413342f9fb0201c1689464f29d359e803f186c03857d12eb97e943ecb` and
`8fd50d0f9defa5014d34614300a5537f1252559d996a5adb5d61368a5781f39d`.
The candidate parses as gzip plus an appended DTB, has a 48,545,800-byte
decompressed kernel below LK's 50 MiB MT6797 limit, and is recorded in
[`mainline-77-lk-candidate-diagnostics-current-20260714.txt`](results/mainline-77-lk-candidate-diagnostics-current-20260714.txt).
It remains VM-private, untransferred, unflashed, and unbooted.

The prior 76-patch package is retained as historical evidence and is wrapped as
`guest:~/artifacts/boot-candidates/20260714-76/linux-7.1.3-gemini-db59a88057b4.boot.img`.
Its candidate SHA-256 is
`1e95bd92f654128620b284c7ea03595fdbc9d1a4ca693570de86ea6dfe55d408`; the
Image.gz and Gemini DTB hashes are
`cd1b762413342f9fb0201c1689464f29d359e803f186c03857d12eb97e943ecb` and
`21529f78282cbf3a48f9260b8981f005f3643d54e729ab676384880c6ace1d4c`.
The candidate parses as gzip plus an appended DTB, has a 48,545,800-byte
decompressed kernel below LK's 50 MiB MT6797 limit, and carries `bootopt=64`.
The sanitized provenance is in
[`mainline-76-lk-candidate-current-20260714.txt`](results/mainline-76-lk-candidate-current-20260714.txt).
That record predates the filtered first-boot diagnostics and is retained as
historical provenance. The regenerated candidate is recorded in
[`mainline-76-lk-candidate-diagnostics-current-20260714.txt`](results/mainline-76-lk-candidate-diagnostics-current-20260714.txt).
It remains VM-private, untransferred, unflashed, and unbooted.

The latest read-only vendor handoff refresh records LK-injected `maxcpus=5`,
`console=ttyMT0,921600n1`, and `printk.disable_uart=1`, with only CPUs 0–1
online in the live snapshot. See the [handoff refresh](../2026-07-13-memory-carveout-recovery/results/live-handoff-refresh-20260714.txt).
These values are final-loader observations; the candidate header command line
is not proof of the post-LK Linux command line.

For a UART-only bring-up, build the minimal static ARM64 initramfs in the VM:

```sh
./scripts/dev-vm run bash -lc \
  'experiments/2026-07-12-boot-contract-recovery/scripts/build-minimal-initramfs.sh \
     --output /tmp/gemini-initramfs.img'
```

The builder copies only the VM's static ARM64 BusyBox and the repository's
`initramfs/init`; it does not include a root filesystem, vendor firmware, or
write-capable board tooling. The init mounts `devtmpfs`, `proc`, and `sysfs`,
prints a kernel/console marker, and leaves an interactive shell on
`/dev/console`. Metadata is normalized with `SOURCE_DATE_EPOCH` (default 0),
so repeated builds are byte-identical. Its output remains a private VM
artifact.

To build the complete current-package candidate with validation and parser
provenance, use the VM-only wrapper:

```sh
./scripts/dev-vm run bash -lc \
  'experiments/2026-07-12-boot-contract-recovery/scripts/build-current-lk-candidate.sh \
     --package "$HOME/artifacts/gemini-pda/linux-7.1.3-gemini-c2feb465d6c6" \
     --output "$HOME/artifacts/boot-candidates/<new-directory>"'
```

The single quotes keep guest `$HOME` from expanding in the host shell.
The wrapper refuses to overwrite an output directory, validates the complete
kernel package, serializes gzip+appended-DTB Android v0, parses the result
against the retained LK contract, writes mode-0600 provenance, and has no
device or flashing interface. The default `SOURCE_DATE_EPOCH=0` can be
overridden explicitly with `--source-date-epoch N` when a different
reproducible metadata epoch is needed.

The earlier 56-, 61-, 62-, 65-, 68-, 70-, and 72-patch `Image`/Gemini-DTB layout
checks remain historical provenance. The pre-audit 72-patch UART candidates
are recorded in
[`mainline-boot-current-validation-72.txt`](results/mainline-boot-current-validation-72.txt).
The three private host copies are under
`artifacts/boot-candidates/20260713-cpu-audit/` and are Git-ignored; their
hashes are recorded in that result before any transfer to the separate flashing
machine. They were regenerated after the CPU binding audit removed invalid
per-CPU `clock-frequency` metadata from the board DTS.
Both historical candidates contain the raw `Image`, Gemini DTB, and a fresh
static ARM64 UART initramfs; both parse as complete Android v0 images, but the
retained LK source audit proves neither is valid for its 64-bit gzip+appended-DTB
path. Use the regenerated private candidate described above for any future,
explicitly authorized boot test.

## Evidence

The retained vendor boot artifact is a 16 MiB Android boot image. The sanitized
provenance record in
[`vendor-kernel-provenance.txt`](../2026-07-11-mt6351-pmic-recovery/results/vendor-kernel-provenance.txt)
records that `boot`, `boot2`, and `boot3` were byte-identical, with a 2048-byte
page size, an 8,429,825-byte kernel, a 6,354,621-byte ramdisk, and a 130,745-byte
appended DTB. The installed `gemian-modular-kernel` package's `linux-boot.img`
is a different image and must not be used as evidence for the running kernel.

The live handoff provides:

- model `MT6797X` and compatible `mediatek,MT6797`;
- Android-style `chosen/bootargs` supplied by LK, including `root=/dev/ram`,
  `maxcpus=5`, `console=ttyMT0`, `androidboot.hardware=mt6797`, and reserved
  ramdump/log buffers (unique serial values are redacted);
- an initramfs at `0x45000000` through `0x4560f6bd` in the chosen DT; and
- the Gemian root filesystem mounted from `/dev/mmcblk0p29`.

The live vendor boot path is therefore not a standard upstream `Image` boot:
LK supplies an Android boot-image layout, an initramfs, chosen properties, and
vendor command-line policy. The current patch workflow correctly keeps this
packaging outside the kernel patch series, but a future boot experiment must
add an explicit, reproducible packager or loader integration.

## Interpretation

The command line is part of the boot contract, not a safe default for
mainline. In particular, `maxcpus=5`, `root=/dev/ram`, vendor `androidboot.*`
properties, and ramdump reservations should not be copied blindly into a
mainline board DTS. Mainline should describe memory reservations and console
requirements declaratively, then use a minimal initramfs command line that is
appropriate for the chosen rootfs and recovery path.

The Android boot header's physical load addresses (`kernel_addr=0x40080000`
and `ramdisk_addr=0x45000000`) are supplied by the retained loader. They are
not a requirement to modify Linux's AArch64 image format or to write a
partition. The first mainline boot test should preserve LK and use a named
development boot partition, with a kernel/DTB/initramfs package that is
independently hashed before transfer.

## Bring-up gates

### First-test go/no-go decision (2026-07-14)

`GO` for a minimal, non-primary UART boot test once the owner names the exact
development target and confirms an independently bootable recovery path. The
current 77-patch package and matching candidate satisfy the static loader contract: it emits
`Image.gz`, carries the Gemini DTB as an appended FDT, and can be wrapped with
a minimal static ARM64 initramfs that parses under the retained MT6797 LK
rules. The UART/PSCI/timer/watchdog and conservative PWRAP/eMMC chain are
represented; optional display, touch, keyboard, USB, camera, modem, DVFS, and
thermal consumers remain disabled. The matching private candidate has been
regenerated because the initramfs source now prints redacted console,
CPU, and memory diagnostics. The source hash and filtering boundary are
recorded in [`first-boot-initramfs-source-20260714.txt`](results/first-boot-initramfs-source-20260714.txt).

`HOLD` for a normal userspace boot or peripheral testing. LK's final
`/chosen/bootargs`, memory reservations, CPU online mask, and watchdog state
are still unobserved for a mainline kernel. The AW9523 matrix candidate now
contains the source-derived `gpio-activelow` and `drive-inactive-cols`
correction but remains disabled. No transfer, flash, reboot, or serial transmission
is authorized by this static decision.

The first test should change one variable only: boot the exact hashed candidate
through the retained LK development path, capture early and normal UART output,
then collect `/proc/cmdline`, `/proc/device-tree/chosen`, CPU/memory state,
reserved-memory nodes, watchdog status, and read-only eMMC identity. Do not
mount the normal root filesystem or enable optional consumers in this pass.
Repeat cold boots only after the first capture is internally consistent.

For the storage portion, “read-only” means kernel enumeration and metadata only:
capture `/sys/class/mmc_host`, `/sys/bus/mmc/devices` identity fields with
serial/CID/CSD values redacted, and the MMC debug IOS/status if available. Do
not open or mount `/dev/mmcblk*`, issue `mmc write`, change boot partitions,
run filesystem repair, or use a userspace probe that can alter eMMC state.
Remember that the built-in MMC probe itself is stateful: it enables clocks,
programs controller registers and IRQs, transitions VEMC/VIO18, and sends card
identification commands before these read-only observations are possible. If
the probe is unstable, stop and return to external recovery; do not retry with
HS200/HS400, MSDC1, or normal root mounting.

After retrieving a private UART log, summarize it without publishing the raw
capture or identifiers:

```sh
python3 experiments/2026-07-12-boot-contract-recovery/scripts/summarize-first-boot-log.py \
  artifacts/device-inventory/<timestamp>/mainline-uart.log
```

The summarizer emits only filtered console/earlycon tokens, CPU and memory
markers, broad watchdog/eMMC evidence, and failure indicators. It always ends
in `decision=manual_review_required`; a parser result never promotes runtime
support by itself.

1. Obtain a UART log from a non-primary development boot choice and confirm
   whether LK accepts the regenerated gzip+appended-DTB candidate. Keep the
   vendor boot image untouched and retain a recovery copy.
2. Use the recorded 77-patch candidate from explicit package, DTB, initramfs,
   and command-line inputs; recheck its hashes before any future transfer to
   the separate flashing machine. Do not reuse the historical raw-Image
   candidates.
3. Compare LK's resulting chosen DT and command line against the sanitized
   vendor baseline. Confirm console, memory, initrd, PSCI, GIC, and CPU
   topology before enabling any peripheral nodes.
4. Boot through UART first, then test eMMC root mounting. Never use the
   ordinary workflow to target a whole disk or protected partition.
5. Record cold-boot repeat count, exact image/header hashes, and every failed
   boot. A successful image parse is not a boot result.

## Conclusion

The existing Linux patches describe hardware support, but the device still
needs a validated Android boot-image/LK handoff before those patches can be
tested. The safest next boot artifact is a reversible development image that
retains the known LK/preloader path and carries only the upstream-derived
kernel, Gemini DTB, and minimal initramfs.
