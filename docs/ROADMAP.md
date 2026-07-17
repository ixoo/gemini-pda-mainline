# Roadmap

Milestones are evidence gates, not release dates. Work may proceed in parallel when it does not compromise a safe boot loop, but a milestone is complete only when all exit criteria are demonstrated on real hardware and documented.

## Immediate priority: first attributable Linux 7.1.3 handoff (2026-07-17)

The latest reviewed `bsg100/gemini-linux` main revision is
`9d1e565a5ba11ae9585340e3e4bf4cacc233d13c`. Its hardware logs establish a
useful sequence: satisfy LK's pre-jump DT assumptions first, prove the selected
partition and jump address, start with one CPU, and only then enable storage or
serviceability drivers. Its later B-17 audit also corrects an early false
conclusion: some `0x40080000` cycles in that investigation had selected Android
`boot`, while the corresponding Linux `boot2` cycles jumped to `0x40200000`.
The project also records a genuine earlier Linux/default-`boot` handoff at
`0x40080000`, so the address alone never identifies the payload. Treat the
project as corroborating evidence, not as a patch source or proof for this
unit.

Priorities for the next controlled test are:

1. **P0 — static handoff candidate: complete.** Linux 7.1.3 is still the
   pinned/latest stable release. The `handoff` profile builds a little-endian,
   4 KiB-page, relocatable kernel with `maxcpus=1`, a storage-inert initramfs,
   and no modules or stateful PMIC, storage, DMA/IOMMU, SCP, thermal, USB,
   network, or multimedia probes. A packaging-only DT overlay supplies LK's
   ten CPU frequencies, the causally isolated ATF-ramdump compatible, two
   conservatively co-restored secure-memory compatibles, and a disabled SCP
   node without polluting the upstream-facing board DT.
2. **P1 — one reversible display-first boot: complete but inconclusive.** The
   display candidate was selected from non-primary `boot2` with the silver
   button. The screen remained dark, serial produced no output, and neither the
   initramfs marker nor an interaction path appeared. No boot loop was
   observed, unlike earlier attempts. A post-test fixture audit found that the
   initial `devtmpfs` mount could not run, so marker absence is not a valid
   negative signal. The non-looping difference remains useful evidence, but it
   cannot distinguish Linux execution from a silent early hang or panic;
   runtime remains unknown.
3. **P2 — host-observable USB enumeration: complete but inconclusive.** The
   exact MTU3/T-PHY image was written and fully read back from non-primary
   `boot2`. During the owner-run boot the device remained dark and steady; a
   90-second check and 60-second retry found no USB child, unique identity, or
   network interface. That is a failed USB test, not proof that Linux failed to
   execute: slot selection, the physical data path, LK handoff, early kernel
   execution, T-PHY, MTU3, and gadget binding remain indistinguishable.
4. **P3 — attended fixed-delay reboot marker: complete, interpretation
   provisional.** A reproducible follow-up
   retains the exact USB candidate kernel and DTB and changes only initramfs
   `/init` to call `/bin/busybox reboot -f` after 10 seconds. It is built,
   validated, synchronized, and fully read back from non-primary `boot2`.
   Because UART remains unavailable, the owner
   approved a documented alternative-recovery exception based on known-good
   primary Gemian boot, private backups, and the proven MediaTek restore path.
   On the first attended boot, the screen was dark with the backlight initially
   on; it later entered an off-like state with the backlight off and did not
   restart automatically. Manual power-key start was required. Because this is
   a one-file `/init` delta from the dark, steady USB baseline, `/init`, timer,
   and reboot-path execution have strong indirect support, not confirmation.
   The owner later estimated 5–10 seconds from backlight-on to off, compatible
   with the 10-second timer, but this was not stopwatch measured or repeated
   and no candidate log survived.
5. **P4 — retained simplefb/fbcon visibility: first positive signal; broad
   control ready.**
   Candidate E reconstructs and hash-pins candidate D, retains
   its byte-identical `Image.gz`, adds only the allowlisted LK simplefb node,
   and uses `/init` to validate `simple`, 1080×2160, 32 bpp, and 4352-byte
   stride before one `0x8f7000`-byte striped framebuffer write. Two builds are
   byte-identical; the candidate was written, flushed, and fully read back
   from `boot2`. Its first owner-run boot was black and showed none of the
   expected bands. The positive criterion therefore failed, but the result is
   inconclusive because every fail-closed `/init` branch is black and the
   simplefb node names no display clocks. A focused audit of bsg100's working
   native-fbcon history identifies unused-clock cleanup of
   `CLK_INFRA_DISP_PWM`/`pwm_sel` as a concrete loader-backlight failure. The
   resulting Candidate F preserves Candidate E's Image, initramfs and marker
   byte-for-byte and adds only one path-resolved simplefb
   `clocks = <&infrasys CLK_INFRA_DISP_PWM>;` property. Two builds are
   identical, all static gates pass, and its synchronized `boot2` write has a
   matching full readback. On the first attended boot, sideways console text
   moved across the display for about one second before black. That is the first
   positive visual Linux 7.1.3 handoff signal and strongly supports
   simplefb/fbcon output; unread text does not independently prove `/init`.
   Candidate G kept F's exact kernel and DTB while removing only the raw marker
   access. Its attended boot reproduced sideways scrolling for 1–2 seconds
   before black with the backlight apparently off, rejecting the raw-write
   explanation. Candidate H kept G's exact kernel and initramfs and appended
   only `CLK_TOP_MUX_MM` to the simplefb clock references. In one attended
   series, two attempts visibly progressed farther and the owner approximately
   recognized H's initramfs-only marker; the backlight stayed on with the text
   and went off at the black transition. Later attempts did not reproduce the
   progress. This strongly attributes those visible attempts to external
   `/init`, but H did not provide a repeatable stable console. Candidate I
   preserved H's exact kernel and DTB and exact initramfs tree except `/init`,
   emitted one tty0 line per second through `T+60`, and then held silently. Its
   reported intended `boot2` selection went directly to black with no unique I
   marker, counter, or other text. Exact attempts, backlight state, final state,
   and recovery were not recorded, so I selection and `/init` remain
   unconfirmed and its timing hypothesis is untested.

   Candidate J was the bounded broad control for the completed J series. It
   appends
   `clk_ignore_unused` to forced kernel `CONFIG_CMDLINE` through a rebuilt
   kernel; a header-only variant was rejected as a no-op under
   `CONFIG_CMDLINE_FORCE=y`. It retains exact I's DTB, initramfs, and header
   command line and changes only the kernel payload plus payload-derived header
   fields. The raw image SHA-256 is
   `6d5bad08c2f93eba7fbd66ea5c54de2437f81e44832426a97d4d65d550c659f4`.
   An isolated clean build reproduced the config, kernel payload, `System.map`,
   all 119 DTBs, and boot image byte-for-byte; only timestamp-derived build
   metadata manifests differ. J was synchronized to logical `boot2`; that full
   16 MiB target and readback matched SHA-256
   `465e4c747138e12191d38fd6b4cde68cd0b9a19f918030dea05c9b8dbdd4d3fc`.
   The write did not reboot or shut down the device. On the first later
   owner-attended intended `boot2` selection, the last visible suffix before
   black was reported as `4/60`. Only the tracked shared I/J `/init` emits that
   counter, so the verified target/readback and intended selection strongly
   support Linux entry, fbcon/tty0 output, and `/init` execution through tick
   04 for that attempt. The full line and marker were not exactly transcribed.
   A later two-bullet report is provisionally interpreted as two additional
   intended J/`boot2` selections because the outcomes are mutually exclusive,
   with owner confirmation pending. One reached "iteration 4" before black,
   compatible with and corroborating tick 04 without an exact marker
   transcription. One went directly black with no console and cannot establish
   selected slot, kernel entry, or `/init`. Provisionally, two of three intended
   selections had tick-04-compatible visible output and one of three was
   no-console and unattributable. This materially associates transient visible
   output with broad clock retention, but stable visibility, causality, and
   clock identity remain unestablished. `clk_ignore_unused` neither turns on
   already-off clocks nor prevents explicit disables or retains
   regulators/power domains. Stop further J repetition. The completed
   reassessment selected Candidate K rather than a matched-I rollback. K keeps
   exact J's kernel, appended DTB, forced command line and container layout and
   changes only `/init`: 20 one-second fixed-width carriage-return updates with
   no deliberate newline, then a distinct transition and 12 controlled
   one-second newline lines. Asynchronous kernel printk remains a confounder.
   Its two final VM builds are byte-identical; raw SHA-256 is
   `83704cde0e3e4ed897990b230a817a1c7618201a6b8a33a86a2e19c8e07a07cb`.
   K is synchronized, flushed and fully read back from logical `boot2` after a
   fresh exact-J backup; the padded SHA-256 is
   `959092428f849c5ee2612c352ac4e4f707a4e0ec8696bda6632252e7194a7927`.
   The device remains in Gemian. Perform one attended K selection after a
   known-good boot and normal temperature; runtime is pending.
6. **P5 — isolate the restart path before widening the platform.**
   `reboot -f` requests `RB_AUTOBOOT`. Linux 7.1.3 invokes PSCI
   `SYSTEM_RESET` before the MT6797 TOPRGU watchdog fallback. The off-like state
   could therefore be a PSCI off/key-gated result, a successful TOPRGU reset
   that waits for the power key, or a quiesced hang if reset never asserts.
   The second branch has a concrete source discrepancy: Gemian sets TOPRGU mode
   bit 4 to bypass the power key for normal reboot, while mainline preserves
   its inherited value. The following manual Gemian boot reported `power_key`
   with zero PMIC watchdog, AED watchdog, exception, and battery-removal flags,
   which is compatible with that key-gated reset. Use the existing 5–10-second
   owner estimate only as supporting evidence, then design a bounded test that
   distinguishes PSCI from TOPRGU and tests bit-4 policy; only then repeat the
   exact candidate hash and record
   recovery behavior. Then test PSCI with two CPUs and then the
   eight Cortex-A53 cores; keep the Cortex-A72 pair deferred if the reported
   secure-firmware `CPU_ON` hang reproduces. Next add read-only eMMC discovery
   and safe battery telemetry. Native DRM/panel, keyboard, charging policy,
   storage writes, and connectivity follow only after each dependency has its
   own reversible experiment.

The exact handoff package, candidates, hashes, parser gates, and first runtime
observation are recorded in the [LK handoff alignment result](../experiments/2026-07-16-lk-handoff-alignment/results/lk-handoff-candidate-20260716.txt)
and [boot2 observation](../experiments/2026-07-16-lk-handoff-alignment/results/runtime-boot2-silver-button-20260716.txt).
The failed USB gate is recorded in the [USB gadget diagnostic](../experiments/2026-07-16-usb-gadget-diagnostic/README.md).
The fixed-delay observation and next reset-path gate are recorded in the
[fixed-delay reboot diagnostic](../experiments/2026-07-16-timed-reboot-diagnostic/README.md)
and its [sanitized runtime record](../experiments/2026-07-16-timed-reboot-diagnostic/results/runtime-timed-reboot-attempt-20260716.txt).
The [restart-path source audit](../experiments/2026-07-16-timed-reboot-diagnostic/results/restart-path-source-audit-20260716.txt)
records the PSCI ordering and TOPRGU bit-4 discrepancy.
The failed visible gate, exact image hash, and runtime observation are recorded in the
[deterministic screen-marker experiment](../experiments/2026-07-16-screen-marker-diagnostic/README.md).
The current no-marker observation and broad clock control are recorded in the
[Candidate I timing experiment](../experiments/2026-07-16-fbcon-refresh-timing-diagnostic/README.md)
and [Candidate J clock diagnostic](../experiments/2026-07-17-clk-ignore-unused-diagnostic/README.md).
Candidate J's safe synchronization is captured in its
[write/readback record](../experiments/2026-07-17-clk-ignore-unused-diagnostic/results/boot2-write-candidate-j-20260717.txt).
Its attended observations are captured in the
[Candidate J first runtime record](../experiments/2026-07-17-clk-ignore-unused-diagnostic/results/runtime-candidate-j-attempt-1-20260717.txt)
and [repeat report](../experiments/2026-07-17-clk-ignore-unused-diagnostic/results/runtime-candidate-j-repeat-report-20260717.txt).
The completed reassessment and next attended gate are recorded in the
[Candidate K newline-boundary experiment](../experiments/2026-07-17-fbcon-newline-boundary-diagnostic/README.md)
and its [write/readback record](../experiments/2026-07-17-fbcon-newline-boundary-diagnostic/results/boot2-write-candidate-k-20260717.txt).

## Current evidence snapshot (2026-07-17)

The repository has a reproducible Linux `7.1.3` baseline with a prepared arm64
configuration and packaged kernel/DTB artifacts. The latest complete Image/DTB
package is `linux-7.1.3-gemini-6116c9e7da3f` (77 patches, patchset SHA-256
`6116c9e7da3fc2f56612029236a3bcd370c61f91b3c0951dd4e2c1915537f55e`); it was
validated with `modules_built=false`, so it is an Image/DTB package rather
than a module-inclusive rootfs artifact. Patch 0076 adds disabled-only AW9523
matrix polarity properties. The 76-patch and 72-patch packages described below
remains the baseline for most subsystem audits; the working series adds
patches 0072–0073 for MT6797 SPI reuse and disabled SoC nodes, patch 0074 for
the disabled hall candidate, and patch 0075 for the disabled NT36772 backend.
The focused input follow-up is package
`linux-7.1.3-gemini-a21fac4139df` (75 patches, patchset SHA-256
`a21fac4139dfff0f448d5e8a30a15530bf3c9bb8ae7d04f17355062478c857e3`); it adds
the disabled GPIO66 `SW_LID` candidate and records the keyboard map/XKB boundary
without claiming runtime support. The matching first-boot dependency rerun is
[`first-boot-probe-audit-current-75-package-20260714.txt`](../experiments/2026-07-14-first-boot-probe-audit/results/first-boot-probe-audit-current-75-package-20260714.txt);
it confirms that this input-only addition does not alter the UART/PWRAP/MT6351/
MSDC0 boot chain. A matching private gzip+appended-DTB candidate also parses
against the retained LK contract; its non-flashing provenance is recorded in
the [75-patch LK candidate result](../experiments/2026-07-12-boot-contract-recovery/results/mainline-75-lk-candidate-current-20260714.txt).
The current 77-patch package now has a regenerated private gzip+appended-DTB
candidate; its parser and hash record are in the [77-patch LK candidate diagnostics result](../experiments/2026-07-12-boot-contract-recovery/results/mainline-77-lk-candidate-diagnostics-current-20260714.txt).
It was written to non-primary `boot3` and read back byte-for-byte, but was not
independently boot-tested before a later prototype replaced those bytes; see
the [77-patch boot3 write](../experiments/2026-07-15-boot3-mainline-write/README.md).
A separate framebuffer-console prototype was then written to non-primary
`boot2` and `boot3`, with matching full-partition checksums. The subsequent
boot attempt was inconclusive: a later snapshot showed the vendor 3.18 kernel,
but the exact key sequence, selected slot, LK acceptance, and Linux execution
were not established. See the [prototype boot2 write](../experiments/2026-07-15-display-console-write-boot2/README.md),
[prototype boot3 write](../experiments/2026-07-15-display-console-write/README.md),
and [runtime snapshot](../experiments/2026-07-15-display-console-recovery/results/runtime-boot-attempt-20260715.txt).
Both artifacts used the legacy `0x40080000` kernel-address default and are now
historical. The corrected handoff Image uses `0x40200000` so
`(kernel_addr - text_offset)` is 2 MiB aligned. Its display candidate was later
selected from `boot2` with the silver button; the observed dark screen, silent
serial path, absent interaction, and lack of a boot loop leave Linux runtime
unknown. The historical fixture's broken initial `devtmpfs` mount makes its
absent marker non-evidence. Patches 0077–0078 and the USB diagnostic were then
tested from `boot2`: the device remained dark and steady, and no USB child was
observed during a 90-second host check or 60-second retry. Linux execution is
still unconfirmed. The next diagnostic candidate preserves that exact kernel
and DTB and changes only initramfs `/init` to request a forced reset after 10
seconds. It was validated, fully read back from `boot2`, and booted once under
the recorded exception. Unlike the baseline's dark steady state, its backlight
later turned off and it entered an off-like state without automatically
restarting. That one-variable delta gives external `/init` execution strong
indirect support, reinforced by the owner's later 5–10-second estimate;
the timing was not measured by stopwatch, the test was not repeated, and no
candidate log survived. The
next manual Gemian boot reported `power_key` and zero watchdog/exception flags.
Gemian explicitly sets TOPRGU mode bit 4 to bypass the power key for normal
restart, while mainline does not. Physical poweroff, a successful key-gated
reset, and a quiesced failed restart handler remain unresolved; the bit-4
policy is the leading source-backed discrepancy.
Candidate E retained that exact `Image.gz`, added an allowlisted simplefb node,
and wrote one validated frame from `/init`; it remained black. Candidate F
added only `CLK_INFRA_DISP_PWM` retention and produced about one second of
sideways fbcon text before black, the first positive visual Linux 7.1.3 signal.
Candidate G retained F's exact kernel/DTB, removed all raw framebuffer access,
and reproduced sideways scrolling for 1–2 seconds before black with the
backlight apparently off. Candidate H preserved G's exact kernel/initramfs and
added only the `CLK_TOP_MUX_MM` simplefb reference. Two attempts then showed
more progress and an approximately recognized initramfs-only marker before the
screen and backlight went off; later attempts did not reproduce that progress.
Candidate I preserves H's exact kernel/DTB and changes only initramfs `/init`
to emit one line per second through `T+60` before a silent hold. Its exact
padded image is fully read back from `boot2`, but the reported intended
selection went directly to black with no unique I marker, counter, or other
text. Selection and `/init` are not established, so the timing hypothesis
remains untested. Candidate J rebuilds that kernel with `clk_ignore_unused` in
forced `CONFIG_CMDLINE`, retaining I's exact DTB, initramfs, and header command
line. Its raw SHA-256 is
`6d5bad08c2f93eba7fbd66ea5c54de2437f81e44832426a97d4d65d550c659f4`;
the original and isolated clean build produced the same config, kernel
payload, `System.map`, all 119 DTBs, and boot image. J was synchronized and
fully read back from logical `boot2` under the standing safety policy; that
full partition/readback SHA-256 was
`465e4c747138e12191d38fd6b4cde68cd0b9a19f918030dea05c9b8dbdd4d3fc`.
Its first intended selection visibly reached the shared `/init` counter suffix
`4/60` before black. A later report is provisionally mapped to two additional
intended selections: one iteration-4-then-black outcome compatible with that
same boundary, and one direct-black/no-console outcome that cannot establish
kernel or `/init` execution. Provisionally, two of three intended selections
had tick-04-compatible visible output, but stable visibility and clock
causality remain unestablished. Stop further J repetition; no matched-I
rollback is authorized. The completed reassessment selected Candidate K, an
exact-J initramfs-only derivative with 20 fixed-width CR/no-newline updates and
12 controlled newline lines. Its raw SHA-256 is
`83704cde0e3e4ed897990b230a817a1c7618201a6b8a33a86a2e19c8e07a07cb`;
it is synchronized and fully read back from `boot2` with padded SHA-256
`959092428f849c5ee2612c352ac4e4f707a4e0ec8696bda6632252e7194a7927`.
The device remains in Gemian. One attended K selection is the next gate;
runtime is pending and asynchronous printk remains a confounder.
The normal UART prerequisite remains unmet; the experiment records the
one-time alternative-recovery exception, observation, and stop path.
The prior 76-patch package has a regenerated private gzip+appended-DTB
candidate that also parses against the retained LK contract; its candidate,
initramfs, Image.gz, and Gemini DTB hashes are recorded in the [diagnostic
76-patch LK candidate result](../experiments/2026-07-12-boot-contract-recovery/results/mainline-76-lk-candidate-diagnostics-current-20260714.txt).
It has not been transferred, flashed, or booted. The fresh 77-patch package
first-boot dependency and three-board schema audit also passes with zero schema
diagnostics; see the [77-patch first-boot audit](../experiments/2026-07-14-first-boot-probe-audit/results/first-boot-probe-audit-current-77-package-20260714.txt).
The latest vendor handoff refresh confirms that LK currently injects
`maxcpus=5`, `console=ttyMT0,921600n1`, and `printk.disable_uart=1`; final
post-LK bootargs and CPU online state therefore remain mandatory first-boot
captures, not properties inferred from the candidate header.
The corresponding current 76-patch CPU/PSCI/timer package audit preserves all
ten generic PSCI nodes and records this discrepancy explicitly; see the
[CPU contract result](../experiments/2026-07-13-cpu-psci-timer-recovery/results/mainline-cpu-psci-timer-current-76-package-20260714.txt).
The retained Planet Android 8 LK source audit shows that those earlier raw-
`Image` appended-DTB and header-DT-field candidates are not valid for its
64-bit path: LK requires `bootopt=...64...`, gzip, an appended DTB, and a
decompressed payload under the MT6797 50 MiB buffer. The rebuilt package emits
`Image.gz` at 48,547,848 decompressed bytes, and a private gzip+appended-DTB
candidate parses with the observed bootopt. The exact hashes are recorded in
the [LK boot-contract audit](../experiments/2026-07-12-boot-contract-recovery/results/lk-boot-contract-audit-20260713.txt).
The full source/config/DTB validation passes, including the bounded
[Gemini-only schema validation](../experiments/2026-07-14-first-boot-probe-audit/results/gemini-dtb-schema-current-72-package-20260714.txt), as does a retained-LK source/DT audit proving that LK rewrites the handoff FDT and appends runtime mblock reservations. Static post-LK snapshots were removed from the board DT to avoid
LK's pre-Linux reservation-conflict loop; the pre-LK dynamic reservation
contract is preserved. No generated mainline image has a confirmed Linux
runtime result on Gemini hardware yet; the timed-reboot result is the first
strong indirect `/init` execution evidence, not confirmation. The patches therefore
describe and compile candidate SoC/board
support; they do not claim runtime support. The earlier baseline package is
`linux-7.1.3-gemini-c2d9eea95daa` with patchset SHA-256
`c2d9eea95daa25dd8faddef4f9822e663db67d5d0946f06f0251cc52c92cf08c`.
For the SPI boundary, the current 74-patch working package is
`linux-7.1.3-gemini-c2feb465d6c6` (patchset SHA-256
`c2feb465d6c6debf6f333516ce360cf8a1259da5dde631e828e7efac92ed33ae`);
its validation proves only compile/schema/package contracts and keeps all six
SPI nodes disabled. See the [SPI patch validation](../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/spi-mainline-patch-validation-c2feb-20260714.txt).
The live Gemian device also confirms the retained LK `/chosen/atag,devinfo`
property's 103-word structural handoff without exposing calibration values;
see the [sanitized handoff result](../experiments/2026-07-13-mt6797-thermal-recovery/results/live-atag-devinfo-handoff-20260714.txt).
The shared MT6797 Device Tree changes also pass the bounded merged-schema check
for `mt6797-evb`, `mt6797-gemini-pda`, and `mt6797-x20-dev` with zero
diagnostics; see the [three-board result](../experiments/2026-07-14-first-boot-probe-audit/results/mt6797-dtb-schema-bounded-current-72-20260714.txt).
The latest vendor-kernel capture confirms USB1/MUSB and UART topology but does
not substitute for a mainline boot; the battery-recovery rerun also confirms
both populated FUSB301 clients return Device ID `0x12`, while only the I2C0
GPIO64/EINT path has a valid IRQ. See the [fresh USB/Type-C result](../experiments/2026-07-12-usb-typec-recovery/results/runtime-usb-typec-battery-recovery-20260714.txt).
The next-boundary decision and runtime gate are recorded in the
[current integration result](../experiments/2026-07-13-kernel-integration/results/mainline-74-patch-current-20260714.txt)
and [LK FDT fixup audit](../experiments/2026-07-13-lk-fdt-fixup-recovery/README.md).
The [driver coverage audit](../experiments/2026-07-13-driver-coverage-audit/README.md)
also records which live vendor-owned blocks are linked into the bootable Image,
which are module-only, and which remain separate firmware/ABI investigations.
The companion [Linux 7.1.3 MT6797 source census](../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/mt6797-source-coverage-current-c2d-20260714.txt)
confirms that existing clock, audio, MMC, IOMMU/SMI, USB, DRM, Panfrost, and
standard input/sensor frameworks are the reuse base, while no direct MT6797
CONSYS/WMT/BTIF, CCCI/CLDMA/CCIF, SENINF/CAM/ISP, SP5509, NT36xxx, or CPU-DVFS
implementation exists in the scanned Linux source.
The current-package rerun ([74-patch source census](../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/mt6797-source-coverage-current-c2feb-20260714.txt))
adds the SPI source path to that same classification without changing the
vendor-only conclusions.
The exact current 74-patch USB/Type-C package audit is also reproducible and
keeps all USB11, MTU3/xHCI, T-PHY, and FUSB301 board consumers disabled; see
the [current USB package result](../experiments/2026-07-12-usb-typec-recovery/results/mainline-usb-current-74-package-20260714.txt).
The focused [I2C controller audit](../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/i2c-mt6797-controller-reuse-20260714.txt)
also confirms that MT6797 reuses the upstream `mt6577` `i2c-mt65xx` register
and quirk profile; the remaining gate is a mainline runtime transfer, not a
new controller backend.
The companion [SPI controller audit](../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/spi-mt6797-controller-reuse-20260714.txt)
finds a similar reuse path through `spi-mt65xx`'s existing `mt6765_compat`.
Patches 0072–0073 now add the MT6797 alias and six disabled controller nodes
with standard clock/pad descriptions; pinctrl groups and runtime transfers
remain open. The recovered SPI1 GPIO234–237 function-switching contract is
recorded in the [SPI1 pinctrl result](../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/spi1-pinctrl-contract-20260714.txt).
See the [SPI patch validation](../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/spi-mainline-patch-validation-c2feb-20260714.txt).
A fresh post-reboot sysfs/Device-Tree probe reproduced the six-master resource
map and child topology byte-for-byte; it did not issue a transfer. See the
[post-reboot SPI result](../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/spi-live-postreboot-20260714.txt).
The refreshed [configuration-gap audit](../experiments/2026-07-12-kernel-config-gap-audit/results/current-validation.txt)
now uses the same 72-patch merged config and distinguishes explicit fragment
policy from actual requests for missing options.
The current package revalidation used `BUILD_MODULES=1` and exports a
1,570-`.ko` `modules/` tree for later rootfs integration. The first-boot Image
and its built-in dependency boundary are unchanged. The refreshed [driver
coverage audit](../experiments/2026-07-13-driver-coverage-audit/results/driver-coverage-20260714.txt)
records the exact linked-in/module-only ownership boundary for that package.
The current 74-patch rerun of the [first-boot dependency audit](../experiments/2026-07-14-first-boot-probe-audit/results/first-boot-probe-audit-current-74-package-20260714.txt)
confirms that the SPI additions do not alter the UART/PWRAP/MT6351/MSDC
probe chain; the PMIC remains part of the eMMC path.
The focused display/input package audit for the same current 74-patch artifact
records reusable AW9523, matrix-keypad, PWM, DRM/DSI/PHY, and panel modules
while keeping all Gemini consumers disabled; see
[`mainline-display-input-current-74-package-20260714.txt`](../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-74-package-20260714.txt).
The post-battery-recovery passive touchscreen capture still shows the vendor
`NVT-ts` binding at I2C4 `0x62` but no identity surface. A later focused
filtered-dmesg capture identifies the live family as NT36772 (trim entry 8,
event map `0x11e00`); the alternate-address transport and runtime protocol
remain a separate-driver gate. Patch 0075 now records a disabled-by-default
backend boundary and passes focused object/module and binding checks, but it
does not add a DT node or runtime claim. See the [live NT36772 identity result](../experiments/2026-07-12-input-backlight-recovery/results/nvt-live-trim-identity-20260714.txt),
the [boundary checks](../experiments/2026-07-12-input-backlight-recovery/results/nt36772-mainline-boundary-20260714.txt),
and the [earlier passive result](../experiments/2026-07-12-input-backlight-recovery/results/live-input-touchscreen-recovery-20260714.txt)
and the [earlier passive result](../experiments/2026-07-12-input-backlight-recovery/results/live-input-touchscreen-recovery-20260714.txt).
The complete 76-patch Image/DTB package and checksum validation are recorded
in the [current package result](../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-77-package-20260714.txt);
the package intentionally excludes loadable modules, while the focused
NT36772 module checks remain in the boundary result.
The owner-authorized post-reboot vendor captures also reconfirm the
connectivity and CCCI transport boundaries after battery depletion; they show
stable topology and firmware hashes, while preserving the distinction between
vendor `ueventd` firmware fallback and a future mainline firmware-loader path.
See [connectivity](../experiments/2026-07-12-connectivity-wmt-recovery/results/live-connectivity-postreboot-20260714.txt)
and [CCCI](../experiments/2026-07-13-modem-ccci-recovery/results/live-ccci-postreboot-20260714.txt).
The [module-closure audit](../experiments/2026-07-14-mainline-module-closure-audit/results/module-closure-current-72-20260714.txt)
now records exact packaged-module dependency edges and hashes for deferred
keyboard, Type-C, thermal, audio, media, GPU, Bluetooth, and WWAN consumers;
the minimal UART initramfs intentionally carries none of them.
The focused [package-delta audit](../experiments/2026-07-14-mainline-module-closure-audit/results/package-delta-a9a7-to-c2d9-20260714.txt)
proves that the corrected packet-semantics rebuild leaves the Image, DTB,
configuration, and unrelated module hashes unchanged; only the intended panel
module differs from the prior package.
The current private LK candidate was regenerated from that exact package,
current Gemini DTB, and a minimal static UART initramfs; its parse-only hashes
are in the [current 72-patch LK candidate result](../experiments/2026-07-12-boot-contract-recovery/results/mainline-72-lk-candidate-current-20260714.txt).
The earlier candidate result remains historical because it used the superseded
`86145c09fc00` package.
After the SPI controller additions, the authoritative private candidate was
regenerated from the current 74-patch package `c2feb465d6c6`; its parse-only
hashes are in the [current 74-patch LK candidate result](../experiments/2026-07-12-boot-contract-recovery/results/mainline-74-lk-candidate-current-20260714.txt).
It has not been transferred, flashed, or booted.
The fresh live-kernel ownership audit confirms the vendor image has no module
namespace (`CONFIG_MODULES` unset and `/proc/modules` absent), so vendor-active
paths must be treated as built-in ownership rather than as loadable-module
requirements. The current 72-patch package comparison is recorded in the
[current ownership result](../experiments/2026-07-14-live-kernel-ownership-audit/results/live-kernel-ownership-current-72-package-20260714.txt);
the older capture result remains historical.
The authoritative current package provenance is recorded in the [2026-07-14
integration result](../experiments/2026-07-13-kernel-integration/results/mainline-74-patch-current-20260714.txt);
older 56–72-patch package hashes in subsystem experiments are historical build
evidence, not the current artifact.
The current built-in handoff closure independently verifies the packaged
UART/PSCI/timer/GIC/eMMC/watchdog contracts and absence of static post-LK
reservations; see the [current handoff result](../experiments/2026-07-13-mainline-handoff-closure/results/handoff-closure-current-77-package-20260714.txt).
In the priority table below, the connectivity source-transport result dated
2026-07-13 is historical source evidence; the package-boundary result dated
2026-07-14 is authoritative for the current artifact.
The [full current checkpatch audit](../experiments/2026-07-14-patch-quality-audit/results/checkpatch-current-77-20260714.txt)
found ten unsigned patches and review diagnostics that must be resolved
before upstream submission; no contributor sign-off is inferred or fabricated.
The current transport/firmware boundary result is tied to the same package in
the [77-patch reconciliation](../experiments/2026-07-14-transport-firmware-boundary-audit/results/transport-firmware-boundary-current-77-20260714.txt);
its proprietary firmware remains private and unloaded. The companion
[firmware-loader audit](../experiments/2026-07-14-transport-firmware-boundary-audit/results/firmware-loader-boundary-current-77-20260714.txt)
confirms that the upstream touchscreen driver has no firmware-loader path,
the packaged Bluetooth transports have no MT6797 match, and the DTB has no
active firmware-owned transport consumer.
The targeted [first-boot static compile audit](../experiments/2026-07-14-first-boot-probe-audit/results/first-boot-static-compile-20260714.txt)
passes W=1 and sparse for UART, pinctrl, PWRAP/MT6351, watchdog, and MSDC;
this is still source evidence, not a runtime boot result.
The current 72-patch watchdog policy is separately recorded in the
[current watchdog audit](../experiments/2026-07-12-mt6797-watchdog-recovery/results/mainline-watchdog-current-72-policy-20260714.txt);
the older 71-patch link in the priority row is retained as historical context.
The corresponding current 72-patch thermal/AUXADC policy audit confirms the
calibration-backed providers are packaged but both consumers remain disabled;
see [thermal audit](../experiments/2026-07-13-mt6797-thermal-recovery/results/mainline-thermal-current-72-policy-20260714.txt).
The private Android `power.mt6797.so` ELF is only a logging callback shim with
no kernel policy imports; its static boundary is recorded in the
[power-HAL audit](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/power-hal-elf-audit-20260714.txt).
The [current 77-patch console contract](../experiments/2026-07-13-uart-console-recovery/results/mainline-console-contract-current-77-20260714.txt)
also confirms the packaged `serial0`/`stdout-path`/`ttyS0` alignment while
keeping the vendor `ttyMT0` and AP-DMA path out of the first boot.
A current-package CPU/PSCI/timer audit independently confirms the same
ten-core generic handoff in the current artifact, with no
MT6797 DVFS, OPP, idle-state, or per-CPU frequency consumer selected; the
[record](../experiments/2026-07-13-cpu-psci-timer-recovery/results/mainline-cpu-psci-timer-current-72-package-20260714.txt)
supersedes older 72-patch package provenance for this boundary.
A fresh owner-authorized, read-only vendor snapshot on 2026-07-14 found no
durable delta in the console, PMIC, or eMMC baseline; its sanitized hashes and
explicitly omitted stateful register reads are recorded in the
[live runtime snapshot](../experiments/2026-07-14-first-boot-probe-audit/results/live-runtime-snapshot-20260714.txt).
The earlier read-only mainline runtime access attempt timed out before SSH
authentication or a probe could run; it remains recorded as negative network
evidence in [the handoff access result](../experiments/2026-07-13-mainline-handoff-closure/results/runtime-access-attempt-20260714.txt).
A later bounded SSH session successfully captured the existing Gemian image's
vendor baseline, including its `3.18.41+` kernel, ten-core CPU topology,
vendor cpufreq and platform bindings, and dynamic vendor reservations. The
sanitized index is [here](../experiments/2026-07-13-mainline-handoff-closure/results/vendor-baseline-runtime-20260714.txt);
the raw mode-0600 capture remains Git-ignored. The post-reboot rerun is [here](../experiments/2026-07-13-mainline-handoff-closure/results/vendor-baseline-postreboot-20260714.txt);
it again shows the same ownership split and DF4064 eMMC identity after a
battery-depletion reboot. A later battery-recovery snapshot is [here](../experiments/2026-07-13-mainline-handoff-closure/results/vendor-baseline-battery-recovery-20260714.txt);
it preserves those facts but reports 0–2 rather than 0–1 CPUs online with
0–9 still possible/present, so the online mask remains time-dependent. This
confirms device access and
provides a comparison baseline, but is not evidence that a mainline candidate
has booted.
The deterministic [vendor-to-mainline gap audit](../experiments/2026-07-14-live-vendor-mainline-gap-audit/results/runtime-boundaries-current-20260714.txt)
now records the direct-reuse candidates and the remaining new-driver/runtime
gates; it also records that vendor `mt-pmic`/`mt-rtc` bind as standalone devices
while `1000d000.pwrap` is unbound, unlike mainline's parent/child topology. The
capture's online CPU mask is time-dependent (`0-2` in the latest run; the prior
post-reboot read reported `0-1`, and an earlier read reported `0-1,4`).
The retained LK console audit adds a bootloader gate to the otherwise reusable
UART path: its non-FPGA default contains `maxcpus=5`, runtime policy appends
`printk.disable_uart`, LK rewrites its downstream `ttyMT3` default from
preloader log settings, and it overwrites `/chosen/bootargs` after appending
the boot-image header command line. The packaged `ttyS0`/`serial0` contract is
consequently static only until a non-primary boot captures the final command
line and early output; see the [current 77-patch LK console mutation result](../experiments/2026-07-13-uart-console-recovery/results/lk-console-mutation-current-77-20260714.txt).
The static source-ordered merge predicts both vendor `ttyMT0` and appended
mainline `ttyS0` tokens; see the [77-patch console merge record](../experiments/2026-07-13-uart-console-recovery/results/lk-console-merge-current-77-20260714.txt).

The immediate implementation order is:

Keyboard map correction (2026-07-14): the exact active boot ELF resolves the
physical `(row=4,col=3)` entry to `KEY_LEFTMETA`, not the retained source
checkout's `KEY_FN`. Patch 0054 now follows that active-boot-normalized map;
the remaining keyboard gate is physical press/release, modifier, rollover,
wake, polarity, and timing validation. See the [active ELF result](../experiments/2026-07-12-input-backlight-recovery/results/active-aw9523-elf-keymap-20260714.txt).

Links below whose filenames contain `current-71` are retained historical
source/build evidence; the adjacent `current-72` or `current-package` record
is authoritative for the present artifact.

The table is the longer-term subsystem order. For the next boot's target,
observability, and one-CPU scope, the 2026-07-16 P0–P4 plan at the top of this
document supersedes the older first-row wording.

| Priority | Area | Linux 7.1.3 reuse decision | Required new work or gate |
| --- | --- | --- | --- |
| 1 | UART, timers, PSCI, watchdog, RAM | Reuse `8250_mtk`, architectural timer, generic PSCI, and `mtk_wdt`; current DT/resource patches are disabled or boot-only | Boot a non-primary candidate, first resolve LK's command-line mutation and capture early/normal logs, verify ten CPUs, reserved memory, watchdog behavior, and repeated recovery before enabling consumers. bsg100's hardware-tested 6.6 logs show CPU1–7 PSCI success but a CPU8/A72 `CPU_ON` boundary; use `maxcpus=8` only as a diagnostic if 7.1.3 reproduces it, not as a default yet. The current package's PM audit confirms generic PSCI topology only—no OPP or idle-state table—while `WATCHDOG_HANDLE_BOOT_ENABLED` means firmware-running TOPRGU state must be explicitly monitored. See [UART](../experiments/2026-07-13-uart-console-recovery/README.md), [CPU/PSCI/timer](../experiments/2026-07-13-cpu-psci-timer-recovery/README.md), [CPU cross-check](../experiments/2026-07-13-cpu-psci-timer-recovery/results/bsg100-cpu-psci-crosscheck-20260714.txt), [current PM package audit](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/mainline-pm-current-72-package-20260714.txt), [memory](../experiments/2026-07-13-memory-carveout-recovery/README.md), and [watchdog policy audit](../experiments/2026-07-12-mt6797-watchdog-recovery/results/mainline-watchdog-current-72-policy-20260714.txt). |
| 2 | PMIC, regulators, eMMC, GPIO/EINT | Reuse upstream PWRAP/MT6397, `mtk-sd`, pinctrl, EINT, and power-supply frameworks with MT6797 data; the MT6351 MFD/regulator/RTC layer is a local implementation because no upstream MT6351 provider exists | The current PMIC audit confirms MT6351 E2, 39 unique rail descriptors, and the stateful pwrap/MFD probe boundary; the current MSDC audit confirms live DF4064 HS400/eMMC and an empty powered-off microSD host while retaining a 25 MHz legacy-only first-boot node and pinmux-only MT6797 state. The direct 77-patch package audit ties that node to built-in MMC/PWRAP/MT6351/pinctrl objects and confirms no HS200/HS400 flags; its first probe still changes clocks, controller registers, IRQ state, and PMIC rails before eMMC identification. An independent bsg100 Linux 6.6 boot corroborates the level-low MSDC0 IRQ, explicit VEMC/VIO18 supplies, MT2701-generation register profile, and pinmux-only boundary, but does not validate the current 7.1.3 image. The first-boot dependency audit confirms that eMMC supply consumers make PMIC probe part of the storage path. The current charger package audit confirms reusable BQ25890/FAN49101 provider objects but no enabled charger, battery, or fuel-gauge consumer in the Gemini DTB. Validate pwrap/PMIC identity, rail readback, reset/RTC, storage read-only I/O, input IRQs, and charger identity/telemetry on hardware before attaching consumers. See [first-boot probe audit](../experiments/2026-07-14-first-boot-probe-audit/README.md), [current PMIC validation](../experiments/2026-07-11-mt6351-pmic-recovery/results/mainline-mt6351-current-72-validation-20260714.txt), [current MSDC validation](../experiments/2026-07-12-mt6797-msdc-recovery/results/mainline-msdc-current-77-package-20260714.txt), [MSDC cross-check](../experiments/2026-07-12-mt6797-msdc-recovery/results/bsg100-msdc-crosscheck-20260714.txt), [current charger package audit](../experiments/2026-07-12-charger-power-recovery/results/mainline-charger-current-72-package-20260714.txt), [PMIC](../experiments/2026-07-11-mt6351-pmic-recovery/README.md), [MSDC](../experiments/2026-07-12-mt6797-msdc-recovery/README.md), and [EINT](../experiments/2026-07-12-mt6797-eint-recovery/README.md). |
| 3 | Keyboard, USB serviceability | Reuse AW9523 matrix input and FUSB301; patches 0066–0070 now split the source-derived USB3 and USB11 windows across existing T-PHY/MTU3/xHCI/MUSB frameworks, with all USB nodes disabled. The current package audit confirms the controller/PHY code is built in and `fusb301.ko` is packaged, while the Gemini DTB has no FUSB301 client, role-switch owner, or VBUS supply | Prove board GPIO/rails, USB1 USB11 glue, two-SIF T-PHY initialization, and role/VBUS ownership. The current display/input package audit confirms the AW9523 and matrix-keypad objects plus a disabled keyboard consumer, while I2C5 and the expander remain disabled. The vendor scan is active-low (selected column low, inactive columns high, low row bit pressed), and follow-up patch 0076 adds the existing matrix consumer's `gpio-activelow` and `drive-inactive-cols` properties; the 76-patch package predates that correction; the 77-patch package now contains it. The exact active boot ELF resolves the disputed physical `(row=4,column=3)` position to `KEY_LEFTMETA`; four spare positions remain explicit `KEY_UNKNOWN`, while the retained source checkout labels that same position `KEY_FN`. See the [active-ELF provenance](../experiments/2026-07-12-input-backlight-recovery/results/active-aw9523-elf-keymap-20260714.txt), [polarity audit](../experiments/2026-07-12-input-backlight-recovery/results/keyboard-polarity-contract-20260714.txt), and [capability comparison](../experiments/2026-07-12-input-backlight-recovery/results/live-keyboard-capability-compare-20260714.txt). The next keyboard gate is an owner-assisted one-key/modifier/rollover test with reset, debounce, wake, polarity, and the physical `(4,3)` `KEY_LEFTMETA` check. Start with keyboard and USB gadget serial, and keep host/VBUS disabled. See [input](../experiments/2026-07-12-input-backlight-recovery/README.md), [keyboard runtime gate](../experiments/2026-07-12-input-backlight-recovery/results/keyboard-next-gate-20260714.txt), [current display/input package audit](../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-77-package-20260714.txt), [historical 71-patch input validation](../experiments/2026-07-12-input-backlight-recovery/results/mainline-input-current-71-validation-20260714.txt), [current USB package audit](../experiments/2026-07-12-usb-typec-recovery/results/mainline-usb-current-72-package-20260714.txt), and [USB](../experiments/2026-07-12-usb-typec-recovery/README.md). |
| 4 | Display, touch, and camera | Reuse DRM component, generic DSI/PWM, `sii902x`, and the standard Novatek framework only where identities and graph resources match | Complete one verified panel/power/DSI graph and touchscreen identity; the current display/input package audit confirms MT6797 DRM/DSI/PHY and NT36672E panel objects are packaged, but all display consumers and the panel graph are disabled/absent. A fresh vendor probe log now identifies the touchscreen family as NT36772 (trim entry 8, event map `0x11e00`), while the alternate-address transport and mainline runtime remain unresolved. Patch 0075 supplies a disabled-by-default NT36772 boundary with passing focused object/module and binding checks; the DT node and runtime remain gated. Panel identity is still an explicit gate: the named-device capture selects an NT36672-named LCM, while bsg100 direct hardware evidence names SSD2092; shared geometry does not prove shared command tables. The camera package audit confirms that only generic media/CAMSYS building blocks are present; SP5509 and the MT6797 SENINF/ISP pipeline remain new work. See [DRM](../experiments/2026-07-12-mt6797-drm-component-recovery/README.md), [live NT36772 identity](../experiments/2026-07-12-input-backlight-recovery/results/nvt-live-trim-identity-20260714.txt), [boundary checks](../experiments/2026-07-12-input-backlight-recovery/results/nt36772-mainline-boundary-20260714.txt), [current display/input package audit](../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-75-package-20260714.txt), [camera package validation](../experiments/2026-07-13-camera-recovery/results/mainline-camera-current-77-package-20260714.txt), [input/backlight validation](../experiments/2026-07-12-input-backlight-recovery/results/mainline-input-current-71-validation-20260714.txt), [panel](../experiments/2026-07-11-gemini-panel-recovery/README.md), [bsg100 panel cross-check](../experiments/2026-07-13-bsg100-gemini-linux-comparison/results/bsg100-panel-crosscheck-20260714.txt), and [external display](../experiments/2026-07-13-external-display-recovery/README.md). |
| 5 | Thermal and CPU power | Reuse the generic MediaTek thermal/AUXADC, OPP, regulator, CCF, and SVS patterns where contracts match; source/data-model reuse is confirmed, but MT6797 variant data is required | The current package audit confirms generic SVS/AUXADC/cpufreq helpers are present, but no MT6797 cpufreq consumer, CPU OPP/idle-state table, or enabled thermal node exists; the MT6797 thermal variant builds as `auxadc_thermal.ko` with `CONFIG_MTK_SOC_THERMAL=m` and both DT nodes remain disabled. Recovery must first wire or reject calibration (the current generic fallback is not a safe thermal policy), then recover EEM/thermal calibration, AUXADC register/idle ownership, ARMPLL/CPU-mux ownership, DA9214/Vsram tracking, and rollback before any frequency or trip transition. The calibration audit shows vendor words 31–33 arrive via LK's `/chosen/atag,devinfo`, not a proven MT6797 MMIO efuse provider. Patch 0057a now supplies a bounded, read-only, root-only NVMEM parser and wires the ordered 12-byte cell into the board DTS; its provider object, Gemini DTB, focused binding schema, and module-enabled package pass in the VM. Preserve that bootloader ABI and keep both thermal/AUXADC nodes disabled until the LK handoff is validated on a candidate boot and fail-closed invalid-calibration behavior is validated. DVFSP/SPM/deep idle remain disabled. See [current PM package audit](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/mainline-pm-current-72-package-20260714.txt), [CPU power](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/README.md), [thermal](../experiments/2026-07-13-mt6797-thermal-recovery/README.md), [current thermal package audit](../experiments/2026-07-13-mt6797-thermal-recovery/results/mainline-thermal-current-72-policy-20260714.txt), [thermal safety contract](../experiments/2026-07-13-mt6797-thermal-recovery/results/mainline-thermal-safety-contract-20260714.txt), and [calibration ownership audit](../experiments/2026-07-13-mt6797-thermal-recovery/results/mainline-thermal-calibration-ownership-20260714.txt). |
| 6 | Audio, sensors, GPU | Reuse existing MT6797 AFE/codec, standard IIO, and Panfrost core/platform patterns | Resolve the audio machine-card/analog graph and exact sensor IDs; validate MFG power/clock ownership and GPU reset/OPP policy. The current audio package selects the AFE, MT6351 codec, and machine objects as modules and packages the matching 1,570-module tree; only a disabled eight-clock AFE resource node exists and no machine-card/codec/analog graph is represented. The sensor package audit confirms IIO plus BMI160/LSM6DSX/STK3310 modules are present, but only a disabled BMI160 candidate has a Gemini DT node and it lacks IRQ/supply data. The current GPU package audit confirms `panfrost.ko` and the MT6797 MFG/RT5735 providers are packaged, while all GPU clock/rail consumers remain disabled and no OPP/reset/IOMMU contract is present. See [audio](../experiments/2026-07-12-audio-afe-recovery/README.md), [current audio package audit](../experiments/2026-07-12-audio-afe-recovery/results/mainline-audio-current-72-package-20260714.txt), [current audio validation](../experiments/2026-07-12-audio-afe-recovery/results/mainline-audio-current-71-validation-20260714.txt), [sensor package audit](../experiments/2026-07-12-sensor-iio-recovery/results/mainline-sensors-current-72-package-20260714.txt), [sensors](../experiments/2026-07-12-sensor-iio-recovery/README.md), [current GPU package audit](../experiments/2026-07-12-mt6797-gpu-panfrost-recovery/results/mainline-panfrost-current-72-package-20260714.txt), and [GPU](../experiments/2026-07-12-mt6797-gpu-panfrost-recovery/README.md). |
| 7 | Wi-Fi, Bluetooth, GNSS, modem | Reuse standard cfg80211/HCI/GNSS/WWAN user-facing frameworks only | Write new MT6797 CONSYS/BTIF and CCCI/CLDMA transports after firmware ownership, shared memory, and non-transmitting handshake contracts are recovered. Linux `btmtksdio` and `t7xx` are not drop-in matches. The current connectivity package audit confirms generic HCI/GNSS/cfg80211/MT76 layers but no MT6797 transport or active connectivity DT node; it records the exact old-combo SDIO IDs, four-byte/512-byte transport contract, BTIF DMA windows, and current Linux source hashes. The modem audit records the APB CCCI/CLDMA/CCIF windows, 16-byte CCCI header, queue/descriptor contract, WWAN configuration, and current package boundary (generic WWAN options plus retained CCCI reservations, but no active modem node). The consolidated transport/firmware audit correlates these package boundaries with all five retained no-map reservations and the private 28-file firmware inventory. The current 77-patch package reruns confirm the SPI additions do not change those transport boundaries. See [connectivity](../experiments/2026-07-12-connectivity-wmt-recovery/README.md), [current 77-patch connectivity package validation](../experiments/2026-07-12-connectivity-wmt-recovery/results/mainline-connectivity-current-77-package-20260714.txt), [historical 71-patch connectivity source validation](../experiments/2026-07-12-connectivity-wmt-recovery/results/mainline-connectivity-current-71-validation-20260713.txt), [current 77-patch modem package validation](../experiments/2026-07-13-modem-ccci-recovery/results/mainline-ccci-current-77-package-20260714.txt), [modem](../experiments/2026-07-13-modem-ccci-recovery/README.md), and [transport/firmware boundary audit](../experiments/2026-07-14-transport-firmware-boundary-audit/README.md). |

The governing rule is protocol equivalence, not component names: identical
register/transaction and resource contracts justify a generic-driver data
extension; a different transport, firmware owner, or ABI requires a new
backend while retaining the standard Linux subsystem interface. A compile
result or a populated vendor node never advances a support state by itself.

## M0 — Safe reproducible lab

**Outcome:** contributors can perform reversible experiments with traceable artifacts before attempting new hardware enablement.

Exit criteria:

- recovery procedure, protected partitions, and UART access documented and tested;
- device variants and component claims tracked with provenance and confidence;
- historical patchsets classified against current upstream;
- reproducible source, toolchain, configuration, DTB, initramfs, and boot-image build defined;
- repository checks cover documentation, scripts, patch hygiene, and DT schemas as those artifacts appear;
- stock/recovery boot path remains intact;
- every planned local kernel patch has an upstream target and tracking issue.

## M1 — Current-mainline UART boot

**Outcome:** a current upstream-derived arm64 kernel boots repeatedly from a
named, non-primary Gemini development target and reaches an observable initramfs
without vendor kernel code. UART remains the preferred evidence channel, but
an attributable on-screen or USB initramfs marker is acceptable on a unit
whose serial path is independently known to be unavailable.

Exit criteria:

- early and normal UART logs captured when the hardware path is available; on
  this unit, record USB enumeration separately from ping and the TCP initramfs
  marker, without treating enumeration alone as `/init` evidence;
- RAM size, reserved memory, timer, interrupts, PSCI, watchdog, and all CPUs checked;
- LK Device Tree and command-line mutations documented;
- minimal Planet vendor prefix and Gemini board Device Tree work is on a public upstream path;
- at least ten consecutive cold boots complete without observed memory corruption;
- every local kernel patch has an upstream target and tracking issue.

## M2 — Persistent headless system

**Outcome:** the device hosts a persistent root filesystem and can be administered without UART.

Exit criteria:

- PMIC wrapper, required regulators, RTC, reboot, and power-off are safe;
- eMMC works reliably with documented partition constraints;
- USB gadget serial and networking work through the normal connector path;
- charger and battery telemetry are exposed conservatively through standard interfaces;
- clean reboot and power-off do not corrupt storage;
- an ordinary distribution userspace reaches SSH.

## M3 — Keyboard and USB serviceability

**Outcome:** the device can be used and recovered through its built-in input and external ports.

Exit criteria:

- built-in keyboard provides a stable matrix and modifier map through generic input/GPIO infrastructure;
- vendor AW9523 timing is compared with the mainline IRQ/debounce contract, and any `debounce-delay-ms` or settling values are justified by a named-device event trace rather than copied from the vendor cadence;
- keyboard wake, rollover, LEDs/backlight, and lid/power buttons have documented status;
- microSD detection, I/O, remove/reinsert, and suspend behavior are tested;
- both USB-C paths are inventoried and supported to the extent hardware allows;
- device/host role switching and repeated hotplug pass a regression protocol.

## M4 — Native display and touch

**Outcome:** the Gemini is locally interactive with an upstream DRM/KMS display pipeline.

The archived display prototype explored a narrower diagnostic gate: an
LK-initialized `simple-framebuffer` plus built-in fbcon without enabling the
native DRM/DSI/panel graph. Its historical experiment fixture used the number
0077, which is now assigned to the active T-PHY patch and must not be confused
with that fixture. The VM candidate validated statically and was written to
non-primary slots, but its first selection attempt was inconclusive and the
later corrected `boot2`/silver-button attempt remained dark and silent without
a marker. The display patch is not active; future instrumentation belongs in
an optional handoff overlay. In every form this is diagnostic output, not
native display support, so the exit criteria below remain unchanged.

Exit criteria:

- MT6797 display pipeline dependencies are represented with reviewed bindings;
- panel identity is verified and initializes through a DRM panel driver;
- backlight and panel power sequencing survive repeated cycles;
- framebuffer console or simple DRM client renders reliably with software rendering;
- touchscreen reports calibrated multitouch input through evdev;
- GPU acceleration is not required for milestone completion.

## M5 — Mobile-grade power

**Outcome:** the port protects the hardware and behaves like a battery-powered mobile computer.

Exit criteria:

- required regulators and PMIC relationships are described correctly;
- thermal sensors and conservative trip points protect the SoC and battery;
- CPU frequency/voltage operating points are validated incrementally;
- runtime power management is enabled without subsystem regressions;
- suspend-to-RAM and wake sources work repeatedly;
- charging and thermal protection remain active while suspended;
- idle and suspend power baselines and known limitations are published.

## M6 — Daily-driver peripherals

**Outcome:** major non-cellular peripherals work through upstream subsystems.

Exit criteria:

- speaker, microphones, headphone routing, and jack detection status documented;
- Mali GPU works with Panfrost or the exact upstream blocker is documented;
- Wi-Fi, Bluetooth, and GNSS use a documented firmware boundary and maintainable interface;
- supported sensors are exposed through standard IIO/input interfaces;
- runtime power-management and suspend regressions are tested.

Camera and external display work do not block this milestone.

## M7 — Standard boot and distro integration

**Outcome:** a distribution can consume upstream support without carrying a Gemini platform fork.

Exit criteria:

- Gemini board DT and required generic/MT6797 changes are merged upstream or on an accepted path;
- standard `Image`, DTB, and initramfs artifacts boot through a maintained loader/chainloader;
- boot configuration and recovery are owner-controlled and documented;
- at least one general-purpose distribution boots using its normal arm64 userspace and packaging flow;
- local patch inventory is empty or limited to explicitly time-bounded upstream backports;
- upgrade and rollback are tested.

## Stretch — Cellular and optional hardware

**Outcome:** retained baseband firmware is usable through a small, reviewable transport and standard userspace telephony components.

This is deliberately non-blocking. Cellular research must first establish shared-memory layout, boot ownership, crash isolation, regulatory constraints, and whether an upstreamable transport boundary is feasible. Cameras, external display, and replacement of retained early firmware are separate optional tracks. Replacing baseband firmware is out of scope.

## Cross-cutting upstream workflow

Every milestone includes:

1. identify existing binding/driver support;
2. reproduce hardware behavior with minimal risk;
3. implement the smallest generic change;
4. validate on Gemini and, where possible, another MT6797 device;
5. submit to the correct upstream maintainers;
6. track review revisions and accepted commits;
7. remove the local patch after it appears in the project baseline.
