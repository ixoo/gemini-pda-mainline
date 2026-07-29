# Experiment: Photon — compare copied-back bytes with distinct RX prefills

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-27-da9214-rx-sentinel-photon` |
| Status | `r0/r1 superseded; embedded r2 failed pre-serviceability; exact volatile r2 completed on Hubble` |
| Subsystem | MT6797 I2C6 receive DMA and legacy DA9214 observation |
| Device variant | Named Gemini PDA unit |
| Date(s) | 2026-07-27 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Not yet assigned |

## Question or hypothesis

What copied-back post byte follows each distinct nonzero receive prefill under
Candidate Cassini's otherwise exact six I2C6 transactions? Can two different
prefills for each register distinguish Cassini's ambiguous zero-prefill result
without assigning an unevidenced device, controller, or DMA cause?

Photon r2 repeats Cassini's exact six combined `I2C_RDWR` pointer/read
transactions at 7-bit address `0x69`, over offsets `0x05`, `0x06`, and `0x47`
twice. Immediately before each ioctl, its only decision-changing observation
delta assigns a distinct nonzero receive prefill:
`a1,b2,c3,d4,e5,f6`.

Photon r0 stopped after the first copied-back byte equal to its prefill. Review
found that result ambiguous with a returned byte that happened to have the same
value. R0 was installed and fully read back but was never booted and its probe
was never invoked. R1 changed only successful-transfer control flow so a
post-equals-prefill result no longer stopped the loop; its complete-success
path contains all six reads, pairing two distinct prefills per register. A
final evidence-language audit then found that r1's `overwritten` labels
described a cause it had not observed. R1 was reproduced but never installed
or booted.
R2 keeps r1's exact `I2C_RDWR` request/message sequence,
successful-transfer control flow, and return policy, changing only diagnostic
identifiers, embedded strings, comments, and artifact provenance to report
objective pre/post comparisons.

The kernel, combined kernel/DTB field, standalone DTB, resolved configuration,
controller timing, I2C address, register order, message shape, and maximum
transfer count are byte-for-byte Cassini. Photon retains the childless adapter,
the fail-closed and unrequested CPU8/9 path, and all no-regulator/no-A72
boundaries.

## Provenance and environment

- Kernel release: `7.1.3-gemini-cassini`.
- Kernel profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve-i2cdev-cassini`.
- Patch series:
  `patches/series-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve`.
- Exact tested foundation:
  `candidate-Cassini-da9214-direct-address-e02e2673`.
- Cassini full artifact-manifest SHA-256:
  `0d1a954827f5ebd31abc12b4d0a207105c5e270403a9b3a66cbd70626e5b2306`.
- Exact inherited `Image.gz` SHA-256:
  `3e9eeb5a2d28f857a1bd25dca8f033f0a19f854a0c8e1839a98bb1aba0df06dc`.
- Exact inherited combined kernel/DTB field SHA-256:
  `9bdda4ae8a20ad215fc53bd3ef3e8c6c5e92171e3e6613415f460bc22f63f85c`.
- Exact inherited standalone DTB SHA-256:
  `8faee2918ce72b08907affa73bfbaf1c5bbbffafde0f4f4c2693977468291768`.
- Exact inherited resolved-configuration SHA-256:
  `83c85429cdcb7d66cb96df2c9005456afd67fc5c7dbfe5d76e9879bf45c1759b`.
- Probe compiler: recovery-VM AArch64 GCC 13.3.0, static non-PIE.
- Photon r2 probe source SHA-256:
  `029fbe15270eada880e3ac74d73de20029743b06fffa44f7fa7b75f105cad62b`.
- Photon probe ELF SHA-256:
  `b36cefe50227f8fe6a838cba0c8757279dcd0766b804afa77de5518c263cbdf4`.
- Photon initramfs SHA-256:
  `6269c04ae5fc29f77986e774faa3b667351357dace98420882e0f5d86ca9c77f`.
- Photon raw Android-v0 SHA-256:
  `75b9081c013408c2358ec3c4cafcf7381294c22215432add98739f72033e8ad6`.
- Photon raw size: 7,647,232 bytes.
- Photon exact 16 MiB padded SHA-256:
  `0ffe1ee750ff219c9ee6f9d4809ecb8748bdd2a35ba63d68a99b3d74e599c2f7`.
- Photon artifact-manifest SHA-256:
  `5b036d5234ab8d27eddcf152f44d5627de2ba669cb0571491f186cd977f2a551`.
- Photon guarded-installer SHA-256:
  `6d98d9a807687567f91513466587ce2b644e5935f841292205fd4a3d25820d5c`.
- Boot path: owner-selected non-primary logical `boot2`; r2 was installed
  through the repository's live-GPT and full-readback policy. Attempt 1
  failed before recoverable serviceability and returned automatically to
  Gemian; the exact full image remained intact.
- Evidence basis: the
  [Cassini reconciliation](../2026-07-27-da9214-direct-address-cassini/results/gemian-da9214-live-dump-reconciliation-20260727.txt)
  records two private, hash-pinned Gemian boot logs with live `d9 d0 c0`,
  Cassini's pre-zeroed receive buffers, and the exact active-binary PAGE_CON
  read-modify-write correction.

## Safety assessment

The helper is fixed-function, accepts no arguments, resolves exactly the
adapter whose OF path ends in `/i2c@1100e000`, and can issue only one-byte
register-pointer plus one-byte read messages to address `0x69`. It cannot
access `PAGE_CON`, change an address, choose another register, retry, write a
device register, touch a regulator, request an A72, access storage, own a
watchdog, reboot, or select a boot slot.

The initramfs inventory and all member metadata remain exact Cassini; only the
data bytes of its manually invoked `bin/cassini-probe` member change. Nothing
invokes it automatically. A transfer or pre-marker error stops the sequence;
otherwise all six transactions complete even when a post-read byte equals its
prefill. The successful path emits exactly eight persistent messages—one
BEGIN, six pre-transfer markers, and one aggregate RESULT—within Cassini's
observed default printk burst of ten.

The only authorized device write is the already-approved guarded replacement
of inactive logical `boot2`. The installer must resolve that label from the
live GPT, reject the active root/mounted/read-only/wrong-size target, require
battery present with health `Good` and capacity strictly above 80 percent,
retain a mode-0600 full predecessor backup, write exactly 16 MiB, flush, and
require a matching full-partition readback. It never writes primary `boot`,
GPT, NVRAM, preloader, any other partition, or the whole device.

## Associated code

- `initramfs/photon-probe.c`: fixed six-transaction observer.
- `initramfs/photon-probe-r0.c`: exact installed-but-unbooted r0 source
  preserved for reproducibility.
- `initramfs/photon-probe-r1.c`: exact reproduced-but-uninstalled r1 source
  preserved for reproducibility.
- `scripts/validate-photon-probe.py`: source and static AArch64 ELF contract.
- `scripts/test-photon-contracts.py`: source-pinned AArch64 contract harness.
  It compiles and executes synthetic r1 and r2 request paths with an
  intercepted `ioctl`, requires their six canonical request records to be
  byte-identical, exercises all six neutral r2 classifiers, validates the
  exact r2 artifact and components, and never opens a device.
- `scripts/build-photon-probe.sh`: deterministic static helper build.
- `scripts/validate-photon-initramfs.py`: exact Cassini archive comparison.
- `scripts/build-photon-initramfs.sh`: one-member-data replacement.
- `scripts/replace-cassini-ramdisk.py`: independently replaces the exact
  Android-v0 ramdisk field while preserving Cassini's combined kernel field.
- `scripts/build-candidate-photon.sh`: two-path container assembly, LK
  validation, padding, and artifact manifest.
- `scripts/derive-installer.py`: source-pinned guarded `boot2` installer
  derived from Cassini's validated installer foundation, but accepting only
  exact installed/readback-verified Photon r0 as r2's live predecessor.

All build tools are storage-inert. Only the derived installer has a device
write path, and it is bounded by the safety gates above.

## Procedure

### Build and package

1. Validate the complete exact Cassini artifact, including its manifest and
   every inherited boot-bearing hash.
2. Build the Photon helper twice independently and require byte identity.
3. Replace only `bin/cassini-probe` data in the exact Cassini initramfs, repack
   twice, and require byte identity plus a whole-archive member/metadata gate.
4. Assemble Photon independently by:
   - replacing only Cassini's Android-v0 ramdisk field and canonical image ID;
   - invoking the shared Android-v0 serializer with Cassini's exact
     `Image.gz`, DTB, header name, command line, and addresses.
5. Require the two container paths to be byte-identical and require all 32 LK
   analyzer gates.
6. Build two complete candidate trees under separate recovery-VM output roots
   and require all 20 files and modes to match.
7. Derive and syntax-check the exact guarded installer.

### Installation

1. Reach the named Gemini in known-good Gemian.
2. Resolve logical `boot2` from the live GPT and apply every target, root,
   mount, holder, swap, writable, size, boot-ID, and battery gate.
3. Require the full current target SHA-256 to equal installed and
   readback-verified but unbooted Photon r0
   `5c044fc3d2ccecf399d6ccb058f354b43e9d14b3fb98f9eb448016ab7f9e8e04`,
   or skip if it already equals exact Photon r2.
4. Preserve a full mode-0600 backup, write/flush exact Photon, and require the
   full readback SHA-256 to equal
   `0ffe1ee750ff219c9ee6f9d4809ecb8748bdd2a35ba63d68a99b3d74e599c2f7`.
5. Shut down from Gemian without automatically selecting or booting `boot2`.

### Hardware gate

Before the boot, state the hypothesis: distinct nonzero prefills and paired
same-register observations will distinguish a stable copied-back tuple from
Cassini's single-value zero-prefill ambiguity. The unique evidence is the
exact pre/post byte pair for each otherwise identical transaction; it does not
by itself identify whether the device, controller, DMA, or another layer
produced a post byte.

1. The owner manually selects `boot2`.
2. Confirm the inherited delayed but readable console and exact Cassini USB
   gadget service. The unchanged kernel reports `7.1.3-gemini-cassini`; exact
   Photon attribution comes from its full image hash and helper markers.
3. Confirm CPU0--7 online, CPU8/9 unrequested, childless I2C6 ready, and zero
   prior I2C6 transfer counters.
4. Invoke `/bin/cassini-probe` once with no arguments.
5. Capture stdout, the complete eight-line persistent sequence, and I2C6
   counter deltas. Do not repeat unchanged.
6. Confirm CPU0--7, USB, handoff, AP-DMA preservation, console, and keyboard
   remain serviceable, then use the already validated native reboot to return
   to Gemian.
7. Collect pstore, require a changed boot ID, and verify the full `boot2`
   checksum still equals exact Photon.

## Observations

Two independent complete Photon r2 trees reproduced all 20 files and modes. A
third post-calibration build also passed exact helper, initramfs, raw size and
hash, padded, and manifest pins. The
helper, initramfs, direct Android-field replacement, independent serializer,
32-gate LK analysis, raw image, zero-padded image, and artifact manifest are
byte-identical across the builds.

The raw image is
`75b9081c013408c2358ec3c4cafcf7381294c22215432add98739f72033e8ad6`;
the full 16 MiB image is
`0ffe1ee750ff219c9ee6f9d4809ecb8748bdd2a35ba63d68a99b3d74e599c2f7`.
No device was accessed during the build.

Photon r0's guarded installer resolved exact logical `boot2` as
`/dev/mmcblk0p30`,
16 MiB, while Gemian's active root was `/dev/mmcblk0p29`. Battery was
present, 95 percent, and `Good`; AC state was ignored under the documented
policy. The full target matched exact Cassini before the write. A mode-0600
full Cassini backup was preserved, r0 was written and flushed, and both remote
post-flush and streamed local full readbacks matched exact r0
`5c044fc3d2ccecf399d6ccb058f354b43e9d14b3fb98f9eb448016ab7f9e8e04`.
The device was then shut down separately and confirmed unreachable. It did not
boot r0. Before any owner boot, review found the sentinel-collision ambiguity,
the owner was told to hold boot2, and r0 was superseded. R1 was then
reproduced but review superseded its causal output vocabulary before
installation.

The r2 installer later resolved the same exact inactive `boot2` and active
Gemian root, required the full target to equal exact unbooted r0, and observed
battery present at 97 percent with `Good` health. It retained a new mode-0600
full r0 backup, wrote and flushed exact r2, and both its remote post-flush hash
and independently streamed 16 MiB local readback matched exact r2
`0ffe1ee750ff219c9ee6f9d4809ecb8748bdd2a35ba63d68a99b3d74e599c2f7`.
The local readback was byte-identical to the padded candidate. A separate
Gemian poweroff closed SSH and the follow-up probe timed out.

On r2 attempt 1, the owner selected `boot2`, observed a white screen, and then
observed an automatic return to Gemian without a recoverable Photon console or
USB service. Post-return Gemian reported boot reason 4,
`androidboot.bootreason=wdt_by_pass_pwk`, and `powerup_reason=reboot`; that
watchdog-block reason does not localize the reset source. Pstore was present
but empty. `/proc/last_kmsg` contained only its 74-byte ram-console header
(`hw_status: 5`, FIQ step 0) and no Photon or Cassini marker. A live-GPT
resolution and one full read-only checksum showed `boot2` still matched exact
r2. The Gemian boot ID remained stable across that checksum.

Offline comparison confirms that r2's kernel, combined kernel/DTB field,
standalone DTB, configuration, and `System.map` are exact Cassini. Its
decompressed initramfs has the same 37-member inventory, order, and every newc
header field; only the data of manually invoked `bin/cassini-probe` differs.
No initramfs member references that helper, so it cannot have caused a
pre-console failure by executing. The sole deterministic structural boundary
delta is the compressed ramdisk crossing one additional 2,048-byte Android
image page. That is a possible control variable, not an established cause.
The r2 probe was never invoked and no paired-prefill or DA9214 result exists.

The sanitized installation records are
[`install-candidate-photon-r0-boot2-20260727.txt`](results/install-candidate-photon-r0-boot2-20260727.txt)
and
[`install-candidate-photon-r2-boot2-20260727.txt`](results/install-candidate-photon-r2-boot2-20260727.txt).
The failed runtime evidence is
[`runtime-candidate-photon-r2-attempt-1-20260727.txt`](results/runtime-candidate-photon-r2-attempt-1-20260727.txt).

Exact hardware-passed Cassini was then restored unchanged as Candidate Hubble.
After its USB service became available, the exact r2 ELF was transferred into
volatile `/run`, verified, invoked once, removed, and guarded against a second
invocation. All six ioctls returned two messages with `errno=0`, and the I2C6
transfer, DMA-start, nonzero-start, and IRQ counters each advanced from zero
to six. Every post byte nevertheless equalled its distinct prefill:
`a1,b2,c3,d4,e5,f6`. The same-register post pairs therefore tracked their
different prefills: `0x05=a1/d4`, `0x06=b2/e5`, and `0x47=c3/f6`.
The exact runtime record is
[`runtime-candidate-hubble-photon-r2-attempt-1-20260727.txt`](../2026-07-27-da9214-transient-probe-hubble/results/runtime-candidate-hubble-photon-r2-attempt-1-20260727.txt).

## Analysis

The pre/post test is decision-changing despite its exact kernel/DT/config
lineage. Linux i2c-dev copies the userspace receive prefill into the kernel
buffer and copies the post-ioctl buffer back after a nonnegative transfer. On
the pinned arm64 path, the buffer is mapped for receive DMA and synchronized
back for the CPU. A single copied-back byte equal to its prefill is still
ambiguous. The paired observations add a discriminator: equal three-byte post
tuples across two different prefill tuples establish a stable copied-back
tuple even if one byte equals one transaction's prefill. They still do not
attribute that tuple to a physical source.

Outcome branches:

- `post_diff_mask=0x00`: all six copied-back post bytes equal their
  transaction-specific prefills. No post/pre difference was observed; a
  matching write or six coincidentally matching returned bytes is not
  logically excluded. Investigate MT65xx/APDMA receive semantics before
  another DA9214 test.
- Equal pass tuples: both three-byte copied-back post tuples match. This
  disambiguates a stable tuple when one post byte equals only one pass's
  prefill, without assigning its source.
- `post_diff_mask=0x3f` and all post bytes zero: all six copied-back bytes are
  zero and differ from their prefills. Cassini's zero result is therefore
  consistent with copied-back zeroes on this stack; source and wire behavior
  remain separate questions.
- Class `post-reference-tuple`: copied-back post values are
  `d9 d0 c0 d9 d0 c0`. This meets the direct-secondary-address observation
  gate for a separately reviewed provider-only experiment; A72 activation
  still does not follow automatically.
- Mixed equality, differing pass tuples, or an ioctl result other than two:
  preserve the available pre/post evidence and exact ioctl result, then stop
  without retrying or relaxing the gate. A short nonnegative ioctl result has
  no trusted post-value for that transaction.

## Conclusion

`post-all-equal-pre`: Photon r0 was installed/read back and superseded without
booting. R1 was reproduced and superseded before installation because its
labels overclaimed causality. Embedded r2 attempt 1 failed before service and
returned automatically under a watchdog-class reason, but exact r2 later ran
once from volatile memory on exact Cassini. Every CPU-visible receive byte
followed its private prefill despite successful ioctl returns and six
transfer/DMA/start/IRQ increments. Cassini's earlier zeros were therefore its
zero initialization, not a DA9214 tuple. The observation localizes the next
work to the mainline WRRD receive-data path without yet choosing among
wire-level receive, DMA destination/programming, completion/coherency, or
later copyback.

## Follow-up

Do not repeat r2. Keep the current exact Hubble boot alive and run only a new,
bounded volatile observation that can distinguish WRRD RX-DMA
programming/completion from the later CPU copyback boundary. Do not add a
DA9214 provider, voltage operation, CPU8 request, or A72 power sequence until
the receive path is localized and corrected.
