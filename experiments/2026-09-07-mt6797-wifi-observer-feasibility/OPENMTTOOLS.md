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
The actual MT6797 kernel/launcher interpretation still needs attribution before
the responder may publish this metadata.

Run it in the RE VM with the private firmware directory as its sole argument.
Both retained files passed. Eight in-memory mutations (truncation, extension,
one changed byte and changed sequence for each file) were refused. Missing,
symlink, FIFO and short-file inputs were also refused without manifest output;
the FIFO check completed within a three-second subprocess limit. Original
retained files were not modified. No firmware bytes are redistributed here.
