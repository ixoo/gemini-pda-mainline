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

## Firmware-version read correction

The isolated [one-line patch](patches/0001-wmt-check-firmware-version-read.patch)
now assigns the `GEN_FVR` return to `iret`, preserving the existing `-2` error
path before chip lookup and cached identity publication. It applies to the
hash-pinned Gemian source above. It selects no kernel profile or device
candidate and carries a non-certifying experiment identity, without a DCO.

The [focused regression](test-version-read.py) takes the unmodified public
`wmt_ic_soc.c` as its argument, verifies its hash, applies the actual patch in
a temporary directory and compiles the exact original and changed function
with fake register reads. It reproduces publication after failed firmware
read in the original; the corrected function stops before lookup/publication.
Hardware-read failure, missing chip information and normal success also pass
for both versions. Compilation used C11 with `-Wall -Wextra -Werror` on the
host. This verifies function control flow, not real transport or a kernel build.

Strict checkpatch passed using the retained current checker with SHA-256
`2553cc1a601e70522e03fbce633d4e79fa5936f7f56a66de1899b7ddd247820a`
and `--no-tree --no-signoff`; the legacy 3.18 checker could not parse on the
available modern Perl. Commit-message wrapping was corrected before the pass.
Full vendor-kernel compilation and runtime validation remain outstanding.
The existing A72-only build lane has not been repurposed for this Wi-Fi patch.

## Single-attempt startup policy

The caller audit confirms that a version-check error returns through
`wmt_core_hw_check()` and `wmt_core_stp_init()` before software initialization
and patch search. However, `opfunc_pwr_on()` then performs cleanup and retries
initialization with `WMT_PWRON_RTY_DFT=2`. The pinned `osal_assert` only logs;
it does not stop this path. A single userspace request can therefore produce
three initialization attempts. The [additional source receipt](results/startup-retry-sources.json)
pins the core and assertion definition; the retry constant is in the previously
pinned `wmt_lib.h`.

The second [experiment patch](patches/0002-wmt-use-one-startup-attempt.patch)
removes this function's retry branches, retaining its cleanup and error
returns. Changing the global retry constant to zero would be incorrect: the
hardware-power failure branch uses an inverted equality test and would then
retry. The patch leaves that global constant and other transport policies
unchanged. It is a deliberate experiment policy, not a general driver fix.

The [regression](test-startup-attempt.py) applies the actual patch to the
hash-pinned public `wmt_core.c` supplied as its argument, then compiles both
exact functions against fake operations. It reproduces three power/init/cleanup
sequences in the original and one in the changed function, including when
cleanup reports failure. Normal success, hardware-power failure and an already
powered entry also pass. Strict checkpatch passes. This establishes the local
control-flow change, not physical shutdown, a total time bound or absence of
requests from other actors. `opfunc_func_on()` returns `-3` after this caller
fails; it does not retry at that call site. Kernel compilation, integrated
capture/recovery and device validation remain outstanding for both patches.

## Complete source-file compilation

The [Buildbox check](check-startup-objects.py) now compiles the complete original
and patched `wmt_ic_soc.c` and `wmt_core.c` for AArch64. The
[result](results/startup-object-compile.json) pins project commit
`44eeec9ee843c99568984a6c292bddf7057d3b91`, source, patches, compiler-command
hashes, configuration and all four object identities. The checksum-validated
package was fetched under the ignored Buildbox artifact directory.

The old generated headers had been cleaned up. The check regenerated them
from the clean pinned baseline and retained live configuration, allowing only
the existing absent-to-disabled ANBOX normalization. It reused the pinned
GCC 6.3 toolchain and complete commands from the verified full-build log,
changing source/include paths to the clean baseline and output paths to
temporary files. No A72 observer patch was selected. Compiler output for both
patched files was empty, with the recorded flags (including `-w`) preserved;
this is not a claim that new strict warning checks passed.

The first attempt at project commit `c2be8bf14d817c8b6530dfd9fe87e29229853e1c`
failed because direct object targets omitted inherited parent include paths
and definitions. The successful correction uses the recorded full commands,
not guessed flags. Both attempts used clean pushed project checkouts; temporary
build output was removed. No source tree was copied from the host.

This closes complete-file compilation for the two changes. It does not link
a kernel, establish the final Wi-Fi configuration or replace the later
Buildbox kernel build, startup/capture integration and device recovery tests.

## Single-command reply guard (incomplete checkpoint)

The userspace responder can be descheduled after checking its deadline and
before writing its reply. The third [experiment patch](patches/0003-wmt-guard-single-patch-reply.patch)
therefore enforces reply acceptance in the kernel. The
[source receipt](results/command-guard-sources.json) pins all four parent files
at the same public Gemian revision. Apply this after the first two patches.

This experiment permits exactly one `srh_patch` transaction per boot. A mutex
serializes command initialization, reply acceptance and terminal cleanup. The
signal and command are initialized before publishing the pending bit; a reply
is refused while that bit still indicates an unread command. After consumption,
the first reply before the two-second jiffies deadline may complete the signal.
The write path returns the rejection errno for early, expired or duplicate
replies. A negative accepted reply still returns the byte count to userspace
and delivers failure to the waiting kernel caller. Later transactions are
refused for the remainder of the boot, including after timeout or an invalid
command consumes the one-command allowance. UART open/close commands are outside
this isolated BTIF experiment policy.

The [focused test](test-command-guard.py) accepts a public source root, verifies
the four source hashes, replays the actual patch and compiles the extracted
control, library and write functions together. It passed early/unread replies,
success, negative acknowledgement, duplicate replies, exact-deadline and late
replies, missing replies, unsigned-jiffies wraparound, concurrent-entry boundary
rejection, terminal reuse, invalid arguments and an occupied buffer. The host
compile used C11, `-Wall -Wextra -Werror`, with unused callback parameters
suppressed. The lock shim checks sequential boundary interleavings; it does
not test a real scheduler or simultaneous threads.

Checkpatch passed with `--no-tree --strict --no-signoff --ignore CAMELCASE`
using the previously pinned checker. The explicit CamelCase exception preserves
existing vendor identifiers; this is not an unqualified strict-style pass.

Complete-file AArch64 compilation of this third patch remains outstanding.
The two-file compilation receipt above does not cover it. The guard does not
serialize metadata ioctls, establish exclusive resource ownership, or impose
a total startup/shutdown deadline. Minimal startup, integrated capture and
recovery, and a full validated Buildbox candidate remain unfinished. No device
action, radio cycle or upstream submission is admitted by this checkpoint.

### Reply-guard complete-file compilation

The [five-file result](results/command-guard-object-compile.json) now covers all
three patches at clean pushed project commit
`ac6ebda89cff8fd7911b8bbeaffec12e073d68cc`. The existing Buildbox check compiled
original and patched `wmt_ic_soc.c`, `wmt_core.c`, `wmt_ctrl.c`, `wmt_lib.c` and
`wmt_dev.c`, producing ten AArch64 objects. It reused the pinned source,
configuration and GCC 6.3 toolchain described above.

The check copies the small neighboring core-header directory into its temporary
patch area and puts that directory first in the patched compiler's include
search path. For every patched object, the emitted dependency list must name
the changed `wmt_ctrl.h` and must not name the baseline copy. This passed for
all five files, closing the risk of silently compiling against the old header
through a quoted neighboring include. The receipt records the patched header
hash and each dependency-check result.

All five patched compiler logs were empty with the recorded flags, including
`-w`; this is not a strict-warning result. The 23-file package passed remote
and local checksum and exact-inventory validation and was retained under the
ignored Buildbox artifact directory. Temporary build output was removed and
the prepared baseline remained clean. This closes the checkpoint's outstanding
complete-file compilation, but does not link a kernel, verify scheduling,
establish a total cycle deadline or admit a device candidate.
