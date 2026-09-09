# Open MT Tools reuse assessment

The MIT-licensed [openmttools project](https://gitlab.com/Dahrkael/openmttools)
provides a source-available alternative to the retained Android launcher.
Revision `ef35f769d211a2942a6783410b58bd824dd363f9` is unsuitable unchanged for
the proposed minimal cycle. The [source and probe receipt](results/openmttools-review.json)
pins all five project files and the actual host result. This does not attribute
the retained vendor launcher to this independent implementation.

## Source findings and reproduced counterexamples

Both chip tables omit MT6797. The daemon's patch-name table also lacks it.
Its main path selects BTIF, configures WMT and starts a worker that requests
loopback power-off then power-on; this is not a passive responder. The
initializer attempts external detection/power and can select SDIO calibration.
Those extra paths are outside our proposed experiment.

The patch callback counts accepted files, not unique download sequences. It
ignores metadata-ioctl failures. The host [probe](probe-openmttools.c) reproduced
success with two synthetic files both claiming sequence 1 of 2, then reproduced
success while every metadata-publication ioctl failed. It also confirmed
MT6797 rejection and the worker's automatic off/on requests. Patch tests used
supported chip `0x6752` to reach the callback, not invented MT6797 support.

These are control-flow tests with mocked ioctls and synthetic 28-byte files.
No daemon main, real descriptor, target ABI, firmware, power or radio was tested.
The unchanged source produced two Clang extension warnings; the fixture's
initial missing mock prototype was corrected before the successful run.

## Consequence

This supplies an inspectable implementation reference with explicit reuse
terms. It does not justify running the generic tools or adding only a chip ID.
An experiment responder must separate command service from power requests,
validate an exact MT6797 patch manifest before publication, propagate every
publication failure and enforce the finite response contract from
[startup dependencies](STARTUP_DEPENDENCIES.md). The controller must retain
exclusive ownership of the single admitted load/shutdown request.

Prefer a narrowly adapted source-based responder over carrying Android runtime
libraries solely to launch the proprietary executable. Keep this as an isolated
vendor-kernel experiment tool; [the mainline interface decision](../2026-09-06-mt6797-mainline-connectivity-interface-design/README.md)
continues to exclude the WMT ioctl ABI from the upstream host design. Exact
MT6797 patch/header applicability, responder implementation and recovery remain
unfinished. No upstream message was sent and no code was deployed.

## Reproduction

Obtain the pinned project's five files from its commit URLs and verify the
receipt hashes. Keep the upstream MIT notice with any source or binary copies.
Compile the probe with `OPENMTTOOLS_SOURCE` defined as the quoted absolute path
to that revision's `mtdaemon.c`; use the flags recorded in the receipt and run
the resulting host executable. Do not run the upstream daemon or initializer.
The probe creates only its two synthetic temporary files, mocks every ioctl,
and removes the files on success. A passing result means that the four
counterexamples were reproduced, not that the daemon is suitable for hardware.

## Retained MT6797 header check, 2026-09-09

The offline [identity checker](check-retained-patches.py) now pins both retained
files and checks the candidate metadata interpretation in the RE VM. Their
complete hashes and sizes match the [earlier inventory](../2026-07-12-connectivity-wmt-recovery/results/runtime-summary.txt).
Applying the inspected openmttools offsets gives:

| Filename | Sequence / count | Bytes 22–23, interpreted big-endian | Address bytes after clearing the sequence byte |
| --- | --- | --- | --- |
| `ROMv3_patch_1_1_hdr.bin` | 1 / 2 | `0x8a00` | `00 00 0a f0` |
| `ROMv3_patch_1_0_hdr.bin` | 2 / 2 | `0x8a00` | `00 00 09 00` |

This order agrees with the [retained post-reboot load observation](../2026-07-12-connectivity-wmt-recovery/results/live-connectivity-postreboot-20260714.txt).
Do not derive order from the filename suffix or treat these address bytes as
an independently established host address. The checker verifies exact retained
identity before emitting a complete ordered manifest; it issues no ioctls.
It is an offline preparation tool, not protection against later file replacement
or proof that a running chip accepts the version or destination fields.
The static attribution below now establishes the kernel/launcher interpretation;
runtime applicability remains a separate gate before metadata publication.

Run it in the RE VM with the private firmware directory as its sole argument.
Both retained files passed. Eight in-memory mutations (truncation, extension,
one changed byte and changed sequence for each file) were refused. Missing,
symlink, FIFO and short-file inputs were also refused without manifest output;
the FIFO check completed within a three-second subprocess limit. Original
retained files were not modified. No firmware bytes are redistributed here.

## Retained launcher and kernel attribution, 2026-09-09

The [static receipt](results/retained-launcher-metadata.json) pins the retained
AArch64 launcher, audited virtual-address ranges and six kernel source files
verified against the recorded Gemian revision. Analysis ran in the RE VM;
the executable was not launched or emulated. No disassembly or binary is
redistributed. The current running launcher was not inspected.

The launcher requests chip identity using ioctl `0x8004a00c`, argument 0.
Both `0x0279` and `0x6797` select the `ROMv3_patch` prefix. Argument 2 obtains
the cached firmware version. The launcher seeks to offset 22 and reads the
two bytes individually into reversed positions, then compares only the low
eight bits of the assembled version with the returned version. Thus its
selection condition for the retained `0x8a00` header is a low byte of zero,
not equality with `0x8a00`. Openmttools' full two-byte comparison is a real
compatibility difference; do not substitute it without an explicit decision.

The next four bytes provide count in the first byte's high nibble and sequence
in its low nibble. The launcher submits count with `0x4004a00e`; it clears the
first address byte and submits a record with sequence at offset 0, address at
offset 4 and the relative filename at offset 8 using `0x4008a00f`. This matches
the kernel's 264-byte `WMT_PATCH_INFO` layout. The ioctl encodes pointer size,
not record size. The inspected launcher does not branch on these publication
results, so its behavior is evidence rather than a suitable failure policy.

Kernel `WMT_unlocked_ioctl()` returns the cached identity/version for those
selectors and places each record at sequence minus one. The patch downloader
retrieves them in index order and copies the four address bytes unchanged into
`WMT_PATCH_P_ADDRESS_CMD[12..15]`. It strips the 28-byte file header before
downloading the body. These findings resolve the candidate metadata layout and
ordering, not the physical meaning or safe ownership of the destination.

One additional source limitation matters to admission: `mtk_wcn_soc_ver_check()`
does not assign the return from its `GEN_FVR` read before testing `iret`.
It tests the preceding successful hardware-version read's status instead.
Therefore even a matching cached firmware version cannot independently prove
a successful firmware-version transaction. The experiment needs attributable
read completion before accepting it. Responder implementation, finite command
timing and full startup/recovery remain unfinished; no radio cycle is admitted.
