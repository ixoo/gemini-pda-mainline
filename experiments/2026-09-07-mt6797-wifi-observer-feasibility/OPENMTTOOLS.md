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
