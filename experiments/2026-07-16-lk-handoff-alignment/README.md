# Experiment: align the Linux 7.1.3 candidate with the retained LK handoff

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-16-lk-handoff-alignment` |
| Status | Static packaging completed; first `boot2` runtime attempt inconclusive |
| Subsystem | Retained Planet LK / arm64 early boot |
| Device variant | Current Gemini PDA unit; exact retail sub-variant not independently established |
| Date(s) | 2026-07-16 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Can the Linux 7.1.3 integration kernel reach a storage-inert initramfs when it
is packaged with the pre-jump DT properties and ARM64 placement contract
expected by the retained Android 8 Planet LK?

The packaging result is not evidence that Linux executed. A later controlled
device test must observe the unique `GEMINI_LK_HANDOFF_20260716_A` marker.

## Provenance and environment

- Kernel release/commit: `7.1.3-gemini-handoff`, package
  `linux-7.1.3-gemini-handoff-6116c9e7-f43cb03c`.
- Patchset and configuration SHA-256: copied from package provenance.
- Reference implementation: `bsg100/gemini-linux` main commit
  `9d1e565a5ba11ae9585340e3e4bf4cacc233d13c` (2026-07-16).
- Android v0 ID algorithm: AOSP legacy
  [`mkbootimg.c`](https://android.googlesource.com/platform/system/core/+/35fc46d8e338181ee3caedc30f3627bad2ffe35e/mkbootimg/mkbootimg.c),
  pinned commit `35fc46d8e338181ee3caedc30f3627bad2ffe35e`.
- Boot path: packaging for retained Planet Android 8 LK. The owner reports
  selecting logical `boot2` with the silver button for the first runtime test;
  no build script in this experiment selects or writes a partition.

### Observed reference requirements

The pinned bsg100 revision is treated as external evidence, not as proof about
this unit. It reports that LK consumes ten CPU `clock-frequency` properties,
secure/reserved-memory compatibility strings, an SCP node, an Android
`bootopt` token selecting the 64-bit path, a gzip stream with an immediately
appended DTB, and an ARM64 placement derived from the Image `text_offset`.
Its hardware sequence causally isolated the ATF ramdump compatible; the ATF
reserved and cache-dump compatibles were restored in the same change and were
not independently isolated. This experiment retains all three conservatively
and records that evidence distinction. The project’s recovered LK behavior
independently supports the gzip/appended-DT and `bootopt` portions of the
contract.

The reference's early notes briefly attributed silent attempts to LK ignoring
the Android header's kernel address. Its later B-17 slot-attributed captures
correct that interpretation: the investigated `0x40080000` cycles identified
an Android fallback, while clean Linux `boot2` captures showed
`jump to K64 0x40200000`. It also records a genuine earlier Linux image handed
off at `0x40080000`, so this is not a universal address-to-slot mapping. The
retained LK source used by this project validates and then uses the header
address. The lesson carried into this experiment is to record selected
partition, jump address, and payload identity before attribution.

The same pinned reference has progressed well beyond early handoff, including
userspace, display, keyboard, left-port gadget/charging, and right-port MUSB
host experiments. Those results prioritize later work but are not copied as
7.1.3 defaults: each driver and binding still needs a current-upstream gap
check and a test on this device variant.

### Project packaging choices (inferences to test)

- Keep LK-only properties in a target-path overlay instead of the upstream DT.
- Use `kernel_addr=0x40200000`; the builder verifies both LK's 512 KiB address
  mask and `(kernel_addr - text_offset)` 2 MiB alignment from the actual Image.
- Require the exact ARM64 Image flags `0x0a`: little-endian, 4 KiB pages,
  relocatable, with all reserved bits clear.
- Test one storage-inert kernel twice: mandatory LK DT only, then the same DT
  plus an isolated `simple-framebuffer` node at the reported live framebuffer.
- Leave `stdout-path` unchanged. `simplefb` is diagnostic instrumentation, not
  part of the mandatory handoff and not a claim about stable display ownership.

## Safety assessment

All associated scripts are build/parse operations. They accept no host,
device, partition, block device, adb, fastboot, or MediaTek flashing argument.
Outputs are private guest artifacts. A separate future test must follow
`docs/SAFETY.md`, preserve recovery, use an explicitly reviewed target, and
stop after unexpected heat, recovery changes, or repeated watchdog loops.

## Associated code

- `dts/lk-handoff.dtso`: mandatory packaging-only target-path overlay.
- `dts/lk-simplefb.dtso`: optional display diagnostic overlay.
- `scripts/validate-lk-compatible-dtb.py`: pure-Python FDT parser and exact
  allow-delta validator.
- `scripts/build-lk-compatible-dtb.sh`: compiles, applies, and validates either
  overlay composition.
- `initramfs/init` and `scripts/build-initramfs.sh`: deterministic static
  BusyBox initramfs with the unique marker and no storage probing.
- `scripts/build-lk-handoff-candidate.sh`: requires an explicit handoff-profile
  kernel package, byte-binds its manifest, series, every patch, handoff
  fragment, and resolved configuration to the current repository, fingerprints
  every helper/input and the deterministic packaging tools, normalizes retained
  log paths, and emits serial/display Android v0 candidates plus hashes.
- [`results/lk-handoff-candidate-20260716.txt`](results/lk-handoff-candidate-20260716.txt):
  sanitized package, parser, exact-DT-delta, and reproducibility result.
- [`results/runtime-boot2-silver-button-20260716.txt`](results/runtime-boot2-silver-button-20260716.txt):
  owner-observed first `boot2` attempt and bounded interpretation.
- The hardened serializer and analyzer in
  `../2026-07-12-boot-contract-recovery/scripts/` enforce the byte contract.

No associated code requires privileges or hardware access.

## Procedure

1. Build the explicit handoff kernel profile in the development VM.
2. Print its exact package path; do not select a package by modification time.
3. In the VM, run:

   ```sh
   experiments/2026-07-16-lk-handoff-alignment/scripts/build-lk-handoff-candidate.sh \
     --package /home/YOU/artifacts/gemini-pda/EXACT-HANDOFF-PACKAGE
   ```

4. Confirm both parser logs say `lk_validation=passed`, verify
   `SHA256SUMS`, and retain `provenance.txt` with any future runtime record.
5. Stop. Candidate generation does not authorize a device write.

## Observations

Linux 7.1.3 remained kernel.org's latest stable release when checked on
2026-07-16. The final handoff package passed its complete checksum manifest and
resolved-config probe-closure checks. Its Image is 11,798,536 bytes with
`text_offset=0`, a 12,386,304-byte effective size, and relocatable flag set.

Two independent candidate builds produced byte-identical complete output
directories. Both Android images are 5,830,656 bytes. The mandatory-only
serial candidate is SHA-256
`e314c1b2eaba065289d416ad5c507d9d7a44b97d70c8647f7fd55c797d4451e5`;
the optional simplefb candidate is
`37e9be6a597dbcb690d5a57fb5d88ba038529b07cbe1b449456855e60e1fa82a`.
Both strict parsers report `lk_validation=passed`; the DT validator reports no
delta outside the named LK properties and optional framebuffer node.

The owner reports writing the immediately preceding exported display candidate
to logical `boot2` and selecting it with the silver button. In one attempt the
screen remained dark, no serial output was observed, no boot loop occurred,
and the device appeared to remain steadily powered. There was no interactive
channel and the initramfs marker was not observed. The write tool, complete
partition read-back hash, exact button timing, observation duration, and
recovery result were not recorded, so candidate attribution rests on the
conversation sequence rather than a target read-back.

A post-test source audit found that this historical initramfs fixture redirected
the initial `devtmpfs` mount's standard error to `/dev/null` before `/dev/null`
could exist. The shell therefore could not execute that mount, and the later
marker loop had no `/dev/console`, `/dev/tty0`, or `/dev/ttyS0` device node to
open. Preserve the fixture unchanged because its bytes are part of the recorded
candidate. This defect makes the absent userspace marker non-evidence; it does
not explain the absence of earlier kernel console output or establish how far
the kernel ran. The later USB diagnostic initramfs mounts `devtmpfs` before any
such redirection and stops explicitly if that bootstrap fails.

## Analysis

The exact-delta validator prevents an LK workaround from silently mutating the
Linux DT beyond the named pre-jump properties. Producing two images from one
kernel/initramfs isolates the optional framebuffer description from the
mandatory handoff. Passing the parsers only establishes internal consistency.
The effective Image leaves 40,042,496 bytes below LK's conservative 50 MiB
region. The first test profile also rejects stateful PMIC/regulator, storage,
DMA/IOMMU, SCP, thermal, USB, network, and multimedia probe families in the
resolved configuration.

The missing reboot loop is a useful differential from earlier malformed or
misplaced candidates, but it does not prove Linux execution. This profile has
`panic=0`; a pre-console hang, an early panic held indefinitely, and a healthy
PID 1 heartbeat are observationally identical when UART and framebuffer are
both silent. In addition, the post-test `devtmpfs` bootstrap finding means this
exact fixture could not emit its intended PID 1 heartbeat through the named
device nodes even if `/init` ran. The dark display establishes that the
proposed simplefb description produced no visible output in this attempt, not
why it failed.

## Conclusion

The corrected candidate no longer exhibits the earlier immediate reboot-loop
behavior when owner-selected from `boot2`. This supports the packaging
direction but does not confirm Linux execution or the initramfs marker. The
simplefb path produced no visible output; runtime handoff remains
`inconclusive`.

## Follow-up

The next candidate should preserve one CPU, storage isolation, and the same LK
contract while adding only a host-observable left-port MTU3 gadget channel.
Give the gadget a unique USB identity before userspace and configure a fixed
address only from `/init`; enumeration would prove the controller path, while
the address and diagnostic service would prove initramfs execution. Preserve
and verify the existing `boot2` contents before another separately authorized
write, read the result back, and retain the known-good recovery path. The
primary `boot` slot remains protected; using it requires a separate exception
design and explicit maintainer review.

Use the mandatory-only serial candidate as the A/B control if UART becomes
observable or if the simplefb-specific delta must be isolated. Record exact
hashes, boot selection evidence, behavior, recovery result, and whether the
marker appeared. Silence or a dark screen alone does not prove that LK entered
Linux and must not be used to infer a UART pinctrl change.
