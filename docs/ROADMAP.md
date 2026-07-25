# Roadmap

Milestones are evidence gates, not release dates. Work may proceed in parallel when it does not compromise a safe boot loop, but a milestone is complete only when all exit criteria are demonstrated on real hardware and documented.

## Immediate priority: preserve AP_DMA ownership before another I2C6 or A72 power test (2026-07-25)

Candidate AC established the USB-only remote development service, and
Candidate AD booted the eight Cortex-A53 CPUs together while retaining console,
keyboard, USB, and native reboot. CPU8/9 remained offline. AE–AG did not reach
an attributable candidate identity, and AH attempt 1 was likewise inconclusive
after an owner-selected grey/no-text cycle. AH attempt 2 subsequently passed
with exact USB/runtime attribution: the console worked, CPU0–7 stayed online
and advanced, CPU8/9 stayed offline and unrequested, native reboot returned to
Gemian, and the post-cycle full `boot2` hash still matched exact AH. No physical
key was exercised in this run and no A72 path was tested. Candidate AI keeps
exact AD configuration and patches 0001–0087 plus corrected 0092 only, with no
A72 request or regulator/reset/observer/active-power stack. Its independently
reproduced package/artifact, guarded installation, exact USB runtime, readable
console, native reboot, changed-Gemian return, and post-cycle full `boot2` hash
all passed. CPU0–7 advanced while CPU8/9 remained offline and unrequested.
This completes AI's eight-A53 baseline; the visible `AB` prompt and USB `AC`
marker remain inherited userspace labels rather than artifact identity.

Candidate AJ is the installed configuration-only CPU8 rejection control. It
changes only `maxcpus=8` to `maxcpus=9`; exact raw SHA-256 is
`a3c649b5ca7a9ac07e290ca9a8838f0a3be33ab9e39554c4bafe50c98d18e2a8`
and exact padded 16 MiB SHA-256 is
`8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257`.
Its guarded write and full readback passed. Attempt 1 was an inconclusive
target-identity mismatch. Attempt 2 passed the exact USB/CPU oracle: CPU0–7
advanced over the 45-plus-5-second window, exactly one CPU8 gate rejection and
one `CPU8: failed to boot: -11` occurred before generic PSCI `CPU_ON`, CPU9 was
not requested, and no other bounded fault appeared. One native reboot closed
the exact USB endpoint, Gemian returned under a changed boot-ID, and a full
read-only post-return `boot2` hash still matched AJ. Retained pstore is a raw,
deliberately unpaired post-return snapshot (`wait_for_cycle=no`), not a paired
cycle-observer record. AJ remains `PARTIAL` solely until the owner explicitly
confirms that attempt 2's local console was readable. No repeat of the CPU8
request is needed for that confirmation, and none of this is A72 operation.

A separate safety-predecessor audit left AJ's console subgate pending and did
not call the raw snapshot paired, but accepted the exact runtime,
fresh-boot-ID native reboot, changed-Gemian return, and full-readback chain for
Candidate AK. Exact AK attempt 1 subsequently passed the ordered CPU8 and CPU9
fail-closed dispatch control with CPU0–7 advancing, neither A72 online, an
owner-attested readable console, native reboot, changed-Gemian return, and a
matching post-return full `boot2` hash. Its evidence chain remains unpaired.
AK establishes rejection dispatch only, not A72 power or scheduling support.

The completed offline firmware/power audit now establishes the forward
ownership split but rejects draft patch 0093 as unsafe. Linux owns external
DA9214 BUCKB, temporary TOPRGU PWRAP reset, MP2 reset-release,
external-isolation preparation, the SRAM-LDO request, and post-success DCM;
captured secure firmware owns the initial B PLL/mux/divider, MP2/core
MTCMOS/reset, internal bus protection, and CCI admission. SRAM-LDO requires
independent readback, and no safe inverse/off path is proven. After the
external-isolation write, failures must retain power, fault without retry, and
use independent reset recovery. Two independent predecessors remain.
Candidate AL tested the mainline I2C6/DA9214 resource-only boundary without
requesting either A72. Exact runtime evidence showed I2C6 bound to
`i2c-mt65xx`, a dynamically numbered adapter and exact `0x68` DT client
appeared, and the inherited eight-A53, keyboard, USB, and reboot path survived.
The upstream DA9211-family driver then read unsupported device ID `0x0`,
returned `ENODEV`, left the client unbound, and registered neither regulator.
No reported timeout/NACK accompanied that failure. AL therefore fails its
predeclared resource oracle and must not be repeated unchanged. The subsequent
Renesas datasheet cross-check isolates an A/non-A compatibility bug: the
A-family exposes `DEVICE_ID` at `0x201`, while the legacy family used on
Gemini does not expose that page and documents zero for nonexistent reads.
Reuse the existing DA9211-family regulator implementation with a fail-closed
legacy DA9214 identification/page-state path; do not add a standalone
regulator driver. The same audit also corrected I2C6 ownership policy: live
Gemian marks the bus `appm_used` and pauses active DVFSP around each transfer.
Candidate AO now supplies the first boot-bounded stopped-state normalization.
Candidate AP then made AO's validated ready state a hard dependency for
childless I2C6. Its exact post-LK FDT passed, but the runtime failed closed:
I2C_APPM regated in all 32 cleanup samples while AP_DMA remained valid and
ungated in all 32. I2C6 returned `-EIO` before binding an adapter or issuing a
transfer. The candidate recovered through native reboot and exact post-return
`boot2` verification. Candidate AQ kept that exact disabled-I2C6 DT and added
only read-only debugfs observation. Its early and five-second summaries were
byte-identical: AP_DMA refcount 2, enabled `Y`, owner `1101c000.i2c` (`dma`),
and I2C_APPM refcount 0, disabled `N`, owner `11015000.dvfsp-handoff`. The
owner reported a readable console, and CPU0–7, the keyboard-map markers, USB
shell, and reboot path survived without I2C6, DA9214, A72, clock-control,
storage, or reboot activity. This identifies the surviving AP_DMA reference
as the enabled I2C5 DMA path. The next candidate must preserve I2C5/AP_DMA and
use a baseline-preserving cleanup oracle for the separate I2C_APPM handoff
gate; resume validation, DA9214 access, and either A72 remain later separate
gates. Do not repeat AP or AQ unchanged.

Candidate AN completed that first handoff observation without touching I2C6.
It retained exact hardware-passed AH plus one read-only CSPM/infracfg observer,
reproduced in two clean kernel and two container builds, and was installed with
a matching full `boot2` readback. The exact runtime booted successfully:
CPU0–7 advanced, CPU8/9 stayed offline and unrequested, USB remained usable,
and no I2C6 platform device, adapter, client, regulator, fault, observer error,
watchdog owner, or automatic reboot appeared. All three snapshots were stable
and reset-like, but I2C_APPM was ungated, so the kernel and independent oracle
both returned `unknown`. Candidate AN must not be repeated unchanged and does
not authorize even a read-only DA9214 transaction. That immediate
active-binary step is now complete for the exact active normal-world kernel.
The recovered contract shows that vendor stop is a reversible PCM reset, not
an ownership latch: mode-0664 `/proc/cpufreq/enable_cpuhvfs`, initial probe,
and conditional syscore resume retain restart/kick paths.
`SEMA_I2C_DRV` is not a CSPM hardware semaphore. It takes the global DVFSP
lock, asserts the I2C pause source, waits up to 2 ms for all firmware-done
bits, and drops DVFSP's reference to the shared I2C_APPM clock while the
controller holds its own reference. I2C6 retries once; the vendor's second
timeout and unpause failures are fatal and must not be copied. The exact
active binary has two get call sites and one release, with release reached for
every transfer result after a successful acquire. A one-time latched observer
result remains insufficient synchronization. The exact retained LK/TEE/SCP
audit then found no positive direct `PCM_CON0 +0x18` restart writer. ATF does
write keyed CSPM `+0` and use secure semaphore `+0x448`, LK directly reads only
the CSPM watchdog latches, and SCP has no direct physical CSPM constructor
while retaining a local-alias uncertainty. Shared I2C_APPM references are now
assigned to normal-running DVFSP, each I2C6 transaction, and enabled A72
iDVFS. Candidate AO implemented the first sticky one-way owner while retaining
I2C6/DA9214 disabled. Its exact named-unit `boot2` runtime passed the
predeclared oracle: all six samples retained Candidate AN's stopped PCM
signature; the gate stayed open through one held CCF reference, closed after
exactly one balanced disable, and remained closed at the 45-second check.
Driver counters and the independent classifier agreed on one attempt, one
enable, one disable, one late check, and zero faults. CPU0–7 advanced,
CPU8/9 stayed offline and unrequested, and no I2C6, DA9214, A72,
watchdog-owner, or automatic-reboot activity appeared. The next step is not
another identical handoff boot. Candidate AP added the separate childless-I2C6
consumer dependency and reached one post-late-check supplier grant, but its
absolute AP_DMA-gated cleanup oracle failed: the bit was already ungated in
the initial samples and stayed ungated through all 32 cleanup samples. The
provider faulted closed and I2C6 never bound. Enabled UART0 and I2C5 share the
same AP_DMA clock in AP's exact DT, but this run does not attribute the
surviving reference. Add an independent owner/refcount observation and a
baseline-preserving oracle before any changed I2C6 candidate; do not proceed
to legacy DA9214 identification, resume, or A72 power yet.

Separately, an unlabeled Gemian owner-local observer must capture the complete
CPU8 online and last-A72-offline transactions. A bounded two-worker pulse has
calibrated the CPU8 trigger, but the sequential observer missed the short
transition. The first owner-local patch draft is build/audit-only: review found
that its regulator helper could continue after a missing client, its write path
bypassed a vendor safety guard, and a large snapshot was placed inside a
timing-sensitive transition. It is not boot-ready. Reconciliation also
corrected the source provenance: the active March 29 boot image differs from
the May 24 `gbp59e00a` installed package; the active exact public commit is
unresolved, and `59e00a` is only the chosen equivalent for verified
observer-hook blobs. No synchronized DA9214/SPM/TOPRGU/SRAM/B/CCI/DCM
transaction is claimed. Patch 0093 stays unselected. Candidate AM is the first
active CPU8 experiment and must use a new one-way, no-hotplug-off
implementation only after the DA9214 resource failure is resolved and a
corrected owner-local observer captures both transactions.

The latest checked `bsg100/gemini-linux` `main` revision is
[`60f5f4ac777a0aeccc89b5d3a4f8cd1f1ebe57b3`](https://github.com/bsg100/gemini-linux/commit/60f5f4ac777a0aeccc89b5d3a4f8cd1f1ebe57b3).
Its hardware logs establish a
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
   regulators/power domains. Stop further J repetition. Candidate K was built
   and synchronized as an exact-J initramfs-only newline/scroll derivative,
   but the strategy review cancelled it without a runtime selection. It has no
   kernel, DT, or configuration delta, and no plausible result would change
   the next action. Its historical write/readback record is retained; do not
   boot it.
6. **P5 — Candidate L observability gate.** Candidate L introduces three
   decision-changing, source-backed deltas: UART0 board pinmux correction to
   GPIO97 RX/GPIO98 TX; an exact Linux 7.1.3 console to the active Gemian
   primary `console-ramoops` zone inside `ramoops@44410000`; and normalized
   MT6797 TOPRGU dual-stage/auto-restart mode to bypass the power-key gate.
   A `0x20000` mainline pmsg allocation supplies address alignment, initializes
   its backend header, and is explicitly not cross-version evidence.
   Its initramfs logs to the kernel console, opens the watchdog, sends one ownership-handoff ping to cancel the
   inherited kernel keepalive, and then sends no further pings. The resulting
   reset and subsequent pstore collection are independently meaningful. A
   successful UART trace, recovered pstore record, watchdog reset, or absence
   of all three lead to different next work. Its clean independent source
   rebuild reproduced every non-timestamp package and candidate file, and its
   exact padded image was synchronized, block-flushed, and fully read back from
   live-resolved logical `boot2`. Attempt 1 showed LK splash then black and was
   unattributable. Attempt 2 showed console output through exact suffix
   `remaining 5s`, unique to Candidate L's tracked `watchdog0=waiting` loop.
   This strongly supports kernel, loader-simplefb/fbcon, devtmpfs, and `/init`
   entry, and establishes that `/dev/watchdog0` was absent at that check.
   Connected serial was silent. The screen switched off, automatic return did
   not occur, manual power recovery was required, and pstore was empty. Do not
   infer bark, expiry, auto-return, UART function, ramoops retention, or native
   display support, and do not repeat unchanged L.
7. **P6 — Candidate M optional-IRQ discriminator: complete and passed.**
   Candidate M kept Candidate L's exact kernel/configuration, deleted only the
   optional bark IRQ from the final DTB as its hardware hypothesis, and added
   a measurement-only `/init`. Two builds were identical and the exact padded
   image was synchronized and fully read back from logical `boot2`. On its one
   controlled selection, the console scrolled and stayed visible through the
   watchdog progress, then returned to Gemian automatically. The recovered
   `console-ramoops` contains the exact M marker and proves that the live DT
   omission survived LK, `10007000.watchdog` bound to `mtk-wdt`, the probe
   returned zero, `/dev/watchdog0` appeared, the timeout was 31 seconds,
   pretimeout was unavailable, and one handoff ping armed the timer. The trace
   reached `watchdog_wait=30s` and ended before the 35-second marker. Gemian
   independently reported `wdt_by_pass_pwk`, `powerup_reason=reboot`, and both
   PMIC watchdog-reboot flags set. This establishes the basic single-stage
   TOPRGU timeout/reset and cross-version console-ramoops retention for this
   exact revision. The L/M comparison strongly isolates the optional
   IRQ-bearing path as L's registration blocker; it does not identify the
   request errno or prove SPI137 polarity, bark, or pretimeout delivery. Do not
   repeat unchanged M.
8. **P7 — online CPU1 only after arming the proven watchdog: complete and
   passed.** Keep
   M's one-CPU boot, no-IRQ watchdog, pstore layout, loader-simplefb/fbcon
   observation path, storage-inert policy, kernel, DTB, and configuration. In
   the external initramfs, mount only the sysfs instance required for CPU
   hotplug, record `present`, `possible`, and `online`, arm the 31-second
   watchdog first, and then request CPU1 online through its standard sysfs
   control. Record the write result, post-request masks, CPU1 state, and bounded
   PSCI/CPU kernel lines to the console and pstore; do not ping again. This
   keeps any `CPU_ON` stall behind the already proven automatic recovery path
   and avoids moving the failure boundary into pre-init boot with
   `maxcpus=2`. A successful CPU1 online is the gate to test the remaining
   Cortex-A53 cores incrementally. A failed or stalled request gets one source
   audit before another device cycle. Keep both Cortex-A72 cores deferred until
   the eight A53 path is understood. That CPU gate and the isolated console
   rotation gate subsequently passed. Candidate Q then combined bounded
   keyboard events and a supervised local shell, but its installed image did
   not provide a working text console and left no pstore evidence. Do not
   repeat unchanged Q. Candidate U was independently built twice with matching
   validated outputs and installed to live-resolved logical `boot2` with a
   matching full-partition readback. Its first intended selection also stayed
   black with no marker or automatic reboot, and post-return pstore was empty.
   Do not repeat unchanged U. Candidate V restores exact P's final DTB and the
   proven no-IRQ watchdog/ramoops path around a corrected polling-keyboard
   implementation. Its reproducible validated image is installed and fully
   read back from `boot2`. Attempt 1 showed a visible console, proved exact V
   kernel/initramfs entry and 31-second watchdog recovery, and isolated the
   keyboard failure at repeated AW9523 `-110` transport/reset timeouts before
   matrix polling or input. No usable shell or key test occurred; do not repeat
   unchanged V. Read-only eMMC discovery remains separate.
   Safe battery telemetry, native DRM/panel, charging policy, storage writes,
   and connectivity remain separate reversible experiments. Candidate
   N implements this exact initramfs-only delta. Two clean VM builds are
   recursively identical, the raw Android-v0 image SHA-256 is
   `43aea71224f6261001ff00904b30dae29063334172a2f6b0163b424a84c0e3aa`,
   and all static gates pass. Its exact padded image was synchronized, flushed,
   and fully read back from live-resolved logical `boot2` with SHA-256
   `a5cc12372ece5e50364a88bc0bf4401ff092e335281352b062ed0ad229fbb7bf`.
   Candidate N's retained exact-marker record proves that the standard
   CPU-hotplug request returned success, logical CPU1 mapped to DT `cpu@1`,
   initialized its GICv3 redistributor, and booted as MPIDR `0x1` / Cortex-A53.
   The online mask changed from `0` to `0-1`, two `/proc/stat` samples showed
   advancing CPU1 accounting, and CPU1 remained online through the 25-second
   marker. The watchdog then returned the device to Gemian automatically with
   no owner intervention. This passes only the first secondary Cortex-A53 path
   in one run; it does not establish repeatability, boot-time SMP, any other
   core, stress, coherency, DVFS, idle, or thermal behavior. Do not repeat
   unchanged N.
9. **P8 — Candidate O: complete and passed.** Candidate O pins and reuses N's
   exact kernel, DTB, configuration, LK container, storage-inert policy,
   watchdog, pstore, and fbcon paths, changing only initramfs `/init`. After
   the watchdog is armed and before the first CPU-online write, it validates
   all live CPU1–9 logical-to-DT mappings. It then requests CPU1 through CPU7
   online in order, once each, with a durable
   begin/return/mask, boot-line, accounting, and pass checkpoint after every
   request. It stops at the first failure. CPU8 and CPU9 are verified as the
   deferred Cortex-A72 pair, remain offline, and are never written. One
   ownership-handoff watchdog ping precedes the sweep; request/accounting
   budget gates keep the pass inside the proven 31-second reset window. Two
   clean VM builds are recursively byte-identical. The exact
   padded image has been synchronized, flushed, and fully read back from
   live-resolved logical `boot2`.

   Its first controlled run passed. Retained exact-marker pstore proves every
   CPU1–7 request returned success, each target booted with Cortex-A53 MIDR
   `0x410fd034`, initialized its GICv3 redistributor, advanced its accounting,
   and reached the expected cumulative checkpoint. The final mask was `0-7`;
   CPU8/9 remained offline and untouched. The cycle-aware collector observed
   return to Gemian with a changed boot ID, and Gemian reported a
   watchdog-class boot reason. This promotes only the eight-A53 hotplug path
   from one run. It does not establish repeatability, boot-time SMP,
   stress/coherency, DVFS, idle, thermal behavior, or either A72 `CPU_ON` path.
   Do not repeat unchanged O; bisect only if a later changed candidate
   regresses one of its exact checkpoints. See the
   [Candidate O experiment](../experiments/2026-07-18-cortex-a53-sweep-diagnostic/README.md),
   [build reproduction](../experiments/2026-07-18-cortex-a53-sweep-diagnostic/results/final-build-reproduction-20260718.txt),
   [write/readback](../experiments/2026-07-18-cortex-a53-sweep-diagnostic/results/boot2-write-candidate-o-20260718.txt),
   and [runtime result](../experiments/2026-07-18-cortex-a53-sweep-diagnostic/results/runtime-candidate-o-attempt-1-20260718.txt).
10. **P9 — Candidate P: passed once; rotation gate closed.** P is the exact
    two-line configuration derivative of hardware-passed O: it enables
    `CONFIG_FRAMEBUFFER_CONSOLE_ROTATION=y` and appends only
    `fbcon=rotate:3` to the forced command line. The raw image SHA-256 is
    `d192dac9e4516eac9319da2a885abaf3203da6c357c574e7f1f6deef2208d341`;
    the synchronized, flushed, padded logical-`boot2` target and full readback
    SHA-256 is
    `cea00d591e74a29d74200f4d292a92aaca2f890bd965af37a7673ab906f4afbc`.
    During the one attributable selection, the owner observed readable console
    text in the correct normal-landscape orientation, the inherited O sweep
    completed, and the device returned to Gemian without owner intervention.
    Post-return `console-ramoops` independently retains the exact O marker,
    every CPU1–7 success/accounting checkpoint, final `online=0-7` success with
    CPU8/9 offline, and both watchdog waits. Because collection began after the
    return, it did not span the tested boot-ID transition or capture an
    independent post-reset boot reason. P establishes loader-retained
    simplefb/fbcon rotation in one run, not repeatability or native
    DRM/panel/backlight ownership. Do not repeat unchanged P. See the
    [Candidate P experiment](../experiments/2026-07-18-fbcon-rotation-diagnostic/README.md),
    [runtime result](../experiments/2026-07-18-fbcon-rotation-diagnostic/results/runtime-candidate-p-attempt-1-20260718.txt),
    [build reproduction](../experiments/2026-07-18-fbcon-rotation-diagnostic/results/final-build-reproduction-20260718.txt),
    and [write/readback](../experiments/2026-07-18-fbcon-rotation-diagnostic/results/boot2-write-candidate-p-20260718.txt).
11. **P10 — AA r1 passed the console-map gate; AB passed one attended kernel-restart test.** Q was
    built twice, installed to live-resolved logical `boot2`, synchronized and
    fully read back with a matching checksum. During the intended selection it
    did not provide a working text console. No Q marker, AW9523 binding, matrix
    input device, raw input event, or shell was observed, and the post-recovery
    pstore check was empty. This is non-diagnostic beyond that first visible
    failure: kernel and initramfs entry remain unestablished. Static review also
    found that Q supplied raw parent interrupt cell
    `interrupts = <87 IRQ_TYPE_LEVEL_LOW>` even though MT6797 GPIO87 maps to
    EINT10. That defect is actionable but is not proven to have caused the
    unobserved execution path. Do not repeat Q unchanged. Preserve its
    [build reproduction](../experiments/2026-07-18-keyboard-shell-diagnostic/results/final-build-reproduction-20260719.txt),
    [write/readback](../experiments/2026-07-18-keyboard-shell-diagnostic/results/boot2-write-candidate-q-20260719.txt),
    and [runtime result](../experiments/2026-07-18-keyboard-shell-diagnostic/results/runtime-candidate-q-attempt-1-20260719.txt).

    Candidate U used the next identifier because R is retired and S/T are
    already reserved. U was independently built twice with matching validated
    outputs, then installed to live-resolved logical `boot2` with a matching
    full-partition readback. Its first intended selection also failed the
    visible-console gate: the screen and console stayed dark, no marker was
    observed, and no automatic reboot occurred. The later Gemian boot ID
    changed, but authenticated post-return pstore was empty. Kernel, `/init`,
    console, AW9523, keyboard, and shell entry remain unestablished.
    Its validated profile retained P's CPU0-only intent and storage/network
    exclusions plus Linux 7.1.3's upstream
    `pinctrl-aw9523` driver and its
    `GPIO_ACTIVE_HIGH` reset contract, and remove the unproven GPIO87 parent-IRQ
    path. Series patches 0083 and 0084 supply an explicit binding plus periodic
    polling mode in the generic matrix consumer, informed by bsg100's hardware
    keyboard commits
    [`6bd4d572`](https://github.com/bsg100/gemini-linux/commit/6bd4d572670698f80ca08ad083657621b62cc8f3)
    and
    [`aff681d3`](https://github.com/bsg100/gemini-linux/commit/aff681d3c727137c4016376e12055d380867f5c3),
    without copying that older custom AW9523 driver or platform-data ABI.
    Patch 0085 separately corrects the reusable disabled board description from
    raw EINT87 to EINT10; U's active DT removes the AW9523 parent-IRQ hierarchy
    while retaining that pinmux state with no active consumer.
    U's validated initramfs keeps the event probe from delaying shell creation:
    keyboard diagnostics and a supervised local shell have independent,
    simultaneously durable observation paths. Its static policy keeps console
    blanking disabled, reports or safely establishes the active VT, emits
    diagnostics over the requested tty sinks, makes devtmpfs setup idempotent,
    remains
    CPU0-only, performs no storage or network access, and deliberately opens no
    watchdog. The validated DT pins
    I2C5 at 400 kHz, polling at 20 ms, column scan delay at 2 us, no separate
    polling debounce, and retains `drive-inactive-cols`; build validation is
    complete, while the first hardware run supplied no polling-path evidence.
    A later artifact audit found that U's final DTB came from the kernel
    package rather than exact P and therefore omitted P's loader-framebuffer,
    no-IRQ watchdog, and other LK-aligned fixups. This explains why U did not
    carry P's configured console path, but does not establish entry or runtime
    causality.
    Preserve
    the [build reproduction](../experiments/2026-07-19-keyboard-polling-diagnostic/results/final-build-reproduction-20260719.txt)
    and [write/readback](../experiments/2026-07-19-keyboard-polling-diagnostic/results/boot2-write-candidate-u-20260719.txt)
    records, plus its [runtime result](../experiments/2026-07-19-keyboard-polling-diagnostic/results/runtime-candidate-u-attempt-1-20260719.txt).
    Do not repeat unchanged U. A later candidate must restore a durable
    independent observation and bounded recovery path before another boot.

    Candidate V provides that distinct observation contract without relabeling
    U. It rebuilds from exact P's hardware-passed final DTB, applies only a
    parsed allowlisted keyboard transform, hard-pins the corrected polling
    patch, and independently starts a supervised tty1 shell, bounded no-grab
    event capture, exact `mtk-wdt` ownership handoff, and durable
    `console-ramoops` checkpoints. Two fresh kernel builds reproduced the
    selected non-timestamp package content and two complete V builds were
    recursively identical. Package validation, focused binding schemas, and
    24 of 24 negative mutation rejections passed. Strict Checkpatch was clean
    for patches 0083--0085; patch 0082 has one commit-message long-line warning
    only.

    V's raw 6,864,896-byte image SHA-256 is
    `9ef0ee8dc1eb49752f9cf8f60b247b9b85e4fd2a9f090473f1d91848114087b0`.
    On 2026-07-19 it was installed without reboot to live-resolved
    `/dev/mmcblk0p30` (`boot2`). The exact padded target, remote checksum, and
    complete local readback all match SHA-256
    `57d362a86fae38c0ec2cec909ef6ae8d8ad124b87abb2ee58d179184c1f19168`;
    the full pre-write U backup matches SHA-256
    `7c57176f3fb5e8e7c9619f038cf09517ca85ee0323ff48ff8c382b60b2794c6e`.
    Root identity, boot ID, and power state remained unchanged during install.

    The owner then selected V from `boot2`. The console was visible and the
    unit returned automatically. Retained `console-ramoops` proves the exact V
    marker, kernel/initramfs entry, local-shell's `tty1_shell=ready` pre-exec
    recorder, exact association with `10007000.watchdog`, a single open/ping at
    timeout 31, and watchdog waits through 30 seconds; no 35-second or
    expiry-failure marker survived. Gemian reported `boot_reason=4`,
    `androidboot.bootreason=wdt_by_pass_pwk`, and `powerup_reason=reboot`.
    This establishes V's no-IRQ watchdog recovery and loader-simplefb/fbcon
    visibility once.

    AW9523 probe on I2C adapter 0 at address `0x5b` repeatedly failed with
    `-110`/`ETIMEDOUT`, including the reset retry. The AW9523 driver and matrix
    device remained unbound and no input/event node existed. This isolates the
    keyboard attempt before generic matrix polling/input at the
    controller-to-AW9523 provider boundary. The owner had no usable opportunity to test
    a shell or key. `tty1_shell=ready` precedes the shell `exec`, so it does not
    prove `ash` execution, a visible prompt, or interactivity. V also writes all
    probe/watchdog markers to tty1, which can bury the prompt, and its matrix
    keymap has neither `KEY_SLASH` nor `KEY_MINUS`, so `/bin/v-pass` is not
    normally typeable from V's own keyboard. Do not repeat unchanged V. See the
    [Candidate V experiment](../experiments/2026-07-19-keyboard-watchdog-diagnostic/README.md),
    [build reproduction](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/final-build-reproduction-20260719.txt),
    [guarded write/readback](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/boot2-write-candidate-v-20260719.txt),
    and [runtime evidence](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/runtime-candidate-v-attempt-1-20260719.txt).

    The exact working 3.18 binary makes the next discriminator concrete. Its
    AW9523 read is a one-byte write followed by a one-byte read; its MT6797 I2C
    master unconditionally selects WRRD and programs RX length at auxiliary
    offset `0x6c`. V has no direct MT6797 driver match and falls through to
    `mt6577_compat`, which suppresses WRRD and lacks that auxiliary-length
    contract. Latest bsg100 independently fixed the same cross-device
    combined-read failure by matching `mediatek,mt6797-i2c` to
    `mt8173_compat`, before later hardware-working keyboard builds.

    The next causal change is that direct controller-data match. Keep V's
    exact DT, AW9523 reset timing and regmap cache, I2C frequency, polling
    consumer, console, ramoops, and watchdog foundation unchanged. A generic
    WRRD guard-only patch under `mt6577_compat` does not reproduce the
    evidence-backed auxiliary-length contract and is not the selected sole
    change. Repair the tty oracle by
    selecting tty1, keeping background markers off it, and using a letters-only
    success token. Compile and force the built-in `TER16x32` fbcon font for the
    owner's requested larger text; record the tty and font edits as
    observation-path changes, not part of keyboard causality. See the
    [working 3.18 binary/controller audit](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/working-3.18-aw9523-i2c-binary-audit-20260719.txt).

    Candidate W tested that exact boundary. Patch 0086 adds only
    `{ .compatible = "mediatek,mt6797-i2c", .data = &mt8173_compat },` while
    the Android-v0 image keeps V's final DTB byte-for-byte, including its
    AW9523/reset/cache/matrix description, no-IRQ watchdog, and ramoops.
    Observation-only changes keep kernel messages on fixed tty2, respawn the
    foreground shell on tty1 without background marker fanout, use a
    letters-only success token, and select the larger built-in `TER16x32`
    font. Two clean kernel packages match after normalizing only
    `generated_utc` provenance, two final candidate assemblies match
    recursively, and the mutation suite passes 24/24. The initramfs SHA-256 is
    `3793bec7a63074b237d041bcd42e6edfccc80f0a3d7b19869abf99ee7874dac6`;
    the raw boot-image SHA-256 is
    `34c41fad1e86de05b6a1f64f7e5d9229bd26ea88d982b0a57f2b9573aeb782d4`.
    The exported `rebuild4` artifact was installed without reboot to
    live-resolved logical `boot2`; the prior V backup is SHA-256
    `57d362a86fae38c0ec2cec909ef6ae8d8ad124b87abb2ee58d179184c1f19168`,
    and the padded W image, remote post-flush checksum, and full local readback
    all match SHA-256
    `0ff3220096aa53f792116b3899e356bc2516816c9c330309c3d81e9fe1446608`.
    The owner then selected W once. Exact retained markers show successful
    `0-005b`/`aw9523-pinctrl` bind, subsequent `matrix-keypad` bind, exact
    `/dev/input/event0`, and press/release records for H, E, L, P, and Enter.
    The owner observed a visible shell and working keyboard and reported the
    font as perfect. This strongly supports the direct-controller-data
    hypothesis for one bounded run, not a physical WRRD trace, full key
    coverage, shell-command execution, or repeatability. W's `pass` marker is
    absent. Kernel logs remained mixed with the shell despite `console=tty2`,
    and the deliberate watchdog open/one-ping path returned the unit
    automatically before useful work. Do not repeat unchanged W. See the
    [Candidate W experiment](../experiments/2026-07-19-keyboard-wrrd-diagnostic/README.md),
    [build reproduction](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/final-build-reproduction-20260719.txt),
    [mutation result](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/validator-mutations-20260719.txt),
    [guarded write/readback](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/boot2-write-candidate-w-20260719.txt),
    and [runtime result](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/runtime-candidate-w-attempt-1-20260719.txt).

    Candidate X is the next observation-only gate. It retains W's exact
    kernel/controller, final DTB, AW9523/matrix/keymap, rotation, and
    `TER16x32` font. Its configuration removes only the virtual-console token;
    its initramfs keeps logging on serial and `/dev/kmsg`/ramoops, never opens
    or pings the watchdog, and exposes a typed `reboot` path with a durable
    request marker. Two clean packages reproduced all 220 non-timestamp files,
    two complete X assemblies are recursively identical, all 32 LK gates
    passed, and 47/47 mutations were rejected. The raw 6,864,896-byte image
    SHA-256 is
    `bf4003871daaba1faa293f2b128021d3a67d41ebf3ddff1c42463409803b9296`;
    its initramfs SHA-256 is
    `b54ce3cd75e7947ed867165e31abbf6ee6cbac7d41d171435f99bba7825bc769`.
    The guarded installer backed up exact W, resolved `boot2` as
    `/dev/mmcblk0p30` while root was `/dev/mmcblk0p29`, and synchronized,
    flushed, and fully read back X with padded SHA-256
    `e89d71f15465b544db163b5f0b90b456e913c38ba4d2ed49aa7bde345148c855`.
    No reboot occurred and the installation-time boot ID remained unchanged.

    The owner later reported that X booted and worked, but typed `reboot`
    appeared to hang. No automatic return occurred; power-key recovery reached
    Gemian and pstore was empty. Do not infer clean tty1, exact X entry, X
    uptime, or individual keyboard subgates. See the
    [Candidate X experiment](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/README.md),
    [build reproduction](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/final-build-reproduction-20260719.txt),
    [mutation result](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/validator-mutations-20260719.txt),
    [guarded write/readback](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/boot2-write-candidate-x-20260719.txt),
    and [runtime](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/runtime-candidate-x-attempt-1-20260719.txt).

    Candidate Y retained exact X's kernel/DT/config and changed four initramfs
    members, but the exact BusyBox pre-boot audit found that bare `reboot`
    selects the internal applet instead of Y's wrapper and that its
    watchdog-open refusal was unreachable. Y was never booted and must not be
    booted.

    Candidate Z retains exact Y's kernel/DT/config and changes four initramfs
    members plus adds read-only `bin/reboot-dispatch.env`. Two complete builds
    match recursively, the exact-BusyBox Linux-arm64 dispatch gate, all 32 LK
    gates, and 75/75 mutations passed, and the full `boot2` readback matches
    padded SHA-256
    `ba21e6424f94c82f14fd51b5681eea68d6cf09e9177e4f9ca2061c9f129abb40`.
    The owner subsequently selected Z once, reported a successful boot with
    the keyboard still working, typed its watchdog reboot, and observed an
    automatic return to Gemian. A changed boot ID and
    `androidboot.bootreason=wdt_by_pass_pwk` corroborate a watchdog-class reset.
    Exact Z text, clean tty1, dispatch/preflight output, countdown timing,
    individual keys, and repeatability remain unproved. Close unchanged Z. See
    the [Y rejection](../experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/results/preboot-command-dispatch-audit-20260720.txt),
    [Z experiment](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/README.md),
    [build validation](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/build-validation-20260720.txt),
    [dispatch validation](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/ash-dispatch-validation-20260720.txt),
    [mutations](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/validator-mutations-20260720.txt),
    [write/readback](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/boot2-write-candidate-z-20260720.txt),
    and [runtime](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/runtime-candidate-z-attempt-1-20260720.txt).

    Candidate AA r0 is historical. Its raw image SHA-256 is
    `a2ad7a4107abd99cbd349b8f2deadd0185cbdd5bb0884ecbdae8ff2a7499ed4c`,
    its incomplete map SHA-256 is
    `48f1f61a9ad8ba327a3105c0dfbbc698c1e55bb3bcca695b46887888be8ca821`,
    and its historical 16 MiB `boot2` image/readback SHA-256 is
    `157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa`.
    It was superseded before selection because it omitted Shift+Fn F1–F10
    and treated BusyBox `dumpkmap` output as a byte-exact runtime oracle. Do
    not boot r0.

    AA r1 is the current isolated console-map gate. It retains exact Z's
    kernel field, final DTB, and resolved configuration and completed two
    recursively byte- and metadata-identical builds. Its canonical static
    AArch64 verifier is SHA-256
    `29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238`;
    its 7,378,944-byte raw image is SHA-256
    `37e82bf3be87dd9e52fb8d60597b69f92a5c0dc5aebd51d178f1e7efd33343d7`.
    Its deterministic 2,311-byte, eight-table map has SHA-256
    `02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c`
    and exactly 53 semantic changes. Those changes add the photographed
    printable/navigation policy, U+263A smiley, Shift+Fn F1–F10, explicit
    modifier-release behavior, and the physical backslash key's plain, Shift,
    Ctrl, and Alt semantics while leaving unsupported modifier combinations as
    `K_HOLE`. A respawn first accepts an already loaded exact map; otherwise a
    preflight requires only the seven inherited tables before `loadkmap`.
    Post-load verification reads all 2,048 `KDGKBENT` entries for the eight
    declared kernel tables, including the table-3 keycode-0 normalization from
    payload `K_HOLE` to kernel `K_ALLOCATED`, every untouched upper-half
    `K_HOLE`, and absence of every undeclared table. Media, brightness, phone,
    airplane-mode, launcher, voice-assistant, and Sym actions remain userspace
    policy. The guarded installer required exact r0 padded predecessor
    `157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa`,
    preserved a private full backup, resolved live-GPT `boot2` as
    `/dev/mmcblk0p30`, and fully read back padded r1 as SHA-256
    `38b49c7c19c2d97fa0c48436545219489221aa367aedf491ae6ebd4ec4856703`.
    The installation did not reboot. Attended attempt 1 then passed. Retained
    pstore records `origin=loaded-now` at 2.407618 seconds, tty1 `K_UNICODE`,
    all 2,048 planned-table entries exact, upper-half holes, every undeclared
    table absent, table 3 allocated, `GEMINI-AA-R1#`, and validated reboot
    dispatch, plus exact AW9523/matrix/event0 identity and A/S press-release
    events. The owner reported the new keymap working. Bare `reboot` arrived
    at 126.258967 seconds, proving a >123-second interval without automatic
    watchdog ownership; the wrapper then opened and pinged the 31-second
    watchdog once, held fd 3, and logged countdown checkpoints through 30
    seconds. A changed boot ID plus Gemian watchdog-class reasons corroborate
    the return. F1–F10 and Page Up/Page Down remain unconfirmed—not failed—
    because the console offered no visible discriminator. See the [AA experiment](../experiments/2026-07-20-keyboard-console-map-diagnostic/README.md),
    r1 [build validation](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/build-validation-aa-r1-20260721.txt),
    [installer validation](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/installer-validation-aa-r1-20260721.txt),
    [guarded write/readback](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/boot2-write-candidate-aa-r1-20260721.txt),
    [layout reference](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/layout-reference-aa-r1-20260721.txt),
    and [runtime result](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/runtime-candidate-aa-r1-attempt-1-20260721.txt).

    Candidate AB is the separate kernel-restart experiment. Patch 0087 gives
    only MT6797's TOPRGU restart notifier priority 255 so it runs before PSCI
    priority 129; every other supported MediaTek SoC retains priority 128.
    After `KBUILD_BUILD_VERSION=1` was pinned, builds 3 and 4 reproduced all
    221 non-dynamic files and modes. Independent containers built from those
    packages and exact AA r1 are recursively byte- and mode-identical at raw
    image SHA-256
    `61c74592267466735164c19f8b831ea18db2892de95e32109f2aacd7ec5c5446`;
    each passed 32/32 LK gates, and all 25 focused mutations were rejected. The
    exact AA r1 DTB and keymap remain, but the userspace watchdog, countdown,
    and fallback are absent. The guarded installer required exact padded AA
    r1, backed it up, wrote only inactive live-GPT `boot2`, and fully read back
    padded AB as
    `b58c0347d34a3fd9031c74cb03447dd7a6fc630d5b8ea2b7eabc36827e754350`.
    The installation did not reboot or change the boot ID. During attended
    attempt 1, pstore retained the exact AB marker, console-map gate, and
    `GEMINI-AB#` prompt, and the owner confirmed the keyboard worked. The owner
    waited 45 seconds with no automatic reset or countdown, then typed bare
    `reboot` and observed an immediate reset. The retained manual request at
    66.021584 seconds precedes the final kernel `reboot: Restarting system`
    line at 66.049438 seconds by 27.854 ms; this is not instrumented
    Enter-to-LK timing. Gemian returned under changed boot ID
    `e33a0d8e-0354-4c8c-95b3-07c6970152ec`. Its watchdog-class boot-reason
    fields are nondiscriminating, while timing and the audited absence of a
    userspace watchdog path support prompt kernel TOPRGU SWRST. Kernel restart
    is now one local named-unit pass, not repeatability or a universal
    reliability claim. F1–F10 and Page Up/Page Down remain unconfirmed, not
    failed. See the [AB experiment](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/README.md),
    [kernel reproducibility](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/kernel-reproducibility-ab-20260721.txt),
    [container validation](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/container-validation-ab-20260721.txt),
    [installer validation](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/installer-validation-ab-20260721.txt),
    [guarded write/readback](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/boot2-write-candidate-ab-20260721.txt),
    and [runtime result](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/runtime-candidate-ab-attempt-1-20260721.txt).
12. **P11 — Candidate R: retired before implementation; folded into Q.** The
    earlier shell-only R concept had no profile, initramfs, artifact, write, or
    runtime result. Its scope is now part of Q, and the R identifier must not be
    reused for a derivative. This kept later Candidate S eMMC work and the
    separate USB-networking line independent; Candidate AC later completed the
    latter's direct-link serviceability gate.
13. **P12 — Candidate S series: eMMC identity, read-only root, then bounded
    diagnostics writes.** The current DT already describes conservative MSDC0
    eMMC at 25 MHz with the real VEMC/VIO18 dependencies, but Candidate N/O's
    exact config deliberately compiles out MMC, PWRAP, MT6351 MFD, and the
    MT6351 regulator provider. First make one explicit built-in config
    derivative with `MMC`, `MMC_BLOCK`, `MMC_MTK`, `MTK_PMIC_WRAP`,
    `MFD_MT6397`, and `REGULATOR_MT6351`; validate the resolved dependency
    closure. Because the PMIC/MMC probe is already the state-changing boundary
    and `ro,noload` requests no filesystem write, the first aggressive but
    bounded S candidate may combine discovery and read-only access. It records
    durable checkpoints for the PWRAP → MT6351 E2/regulator → MSDC0 →
    DF4064/mmc0 → unique GPT `PARTNAME=linux` chain, resolves `linux` by live
    PARTNAME rather than a remembered partition number, requires ext4, mounts
    `ro,noload,nosuid,nodev,noexec`, performs one bounded benign read, unmounts,
    and recovers automatically. It must not expose CID/CSD/serial values or
    accept PMIC/MMC/filesystem/I/O errors; the first failed checkpoint supplies
    the later bisect boundary. Repeat that cold-boot read-only gate before the
    write derivative. That derivative may create only a
    new mode-0700
    `/var/lib/gemini-mainline/diagnostics/<candidate-attempt>/`, cap its payload,
    sync and unmount, remount read-only, and verify the file hash. Never use raw
    writes, fsck, discard, or overwrite an existing path in this series.
14. **P13 — USB gadget Ethernet serviceability: complete on Candidate AC,
    independently retained by AH attempt 2.** Retained M/N pstore had already
    proved successful T-PHY/MTU3 probe, forced B-device session, built-in
    `g_ether`, and gadget pull-up. AC then established the exact USB identity,
    fixed-MAC host interface, carrier, static `10.15.19.82/24` device address,
    ping, TCP marker, and bounded shell on a physically direct, no-bridge link.
    AH attempt 2 passed the same exact USB oracle under the AF-kernel/AD-board
    split. The unauthenticated shell remains a development-only service on that
    isolated link. These results do not establish an electrical D+ waveform,
    physical-port mapping, host/dual-role mode, VBUS, Type-C, charging, mass
    storage, or Internet bridging. Preserve the dummy-`vusb33` warning until
    supply ownership is evidenced. See the
    [AC experiment](../experiments/2026-07-21-usb-gadget-ethernet/README.md),
    [AH attempt-2 result](../experiments/2026-07-22-ad-contract-af-kernel-split/results/runtime-candidate-ah-attempt-2-20260722.txt),
    and [earlier retained-pstore USB result](../experiments/2026-07-16-usb-gadget-diagnostic/results/retained-pstore-mtu3-gadget-evidence-20260718.txt).

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
The cancelled Candidate K design and its historical write/readback are recorded
in the [newline-boundary experiment](../experiments/2026-07-17-fbcon-newline-boundary-diagnostic/README.md).
The completed partial gate is [Candidate L UART/pstore observability](../experiments/2026-07-17-uart-pstore-observability/README.md). Its exact
[independent reproduction](../experiments/2026-07-17-uart-pstore-observability/results/final-build-reproduction-20260717.txt)
and [logical-`boot2` write/readback](../experiments/2026-07-17-uart-pstore-observability/results/boot2-write-candidate-l-20260717.txt)
are complete. [Attempt 1](../experiments/2026-07-17-uart-pstore-observability/results/runtime-candidate-l-attempt-1-20260718.txt)
was unattributable. [Attempt 2](../experiments/2026-07-17-uart-pstore-observability/results/runtime-candidate-l-attempt-2-20260718.txt)
strongly reached tracked `/init` line `watchdog0=waiting remaining=5s`, then
lost the screen and required manual recovery; connected serial was silent and
pstore was empty. The unchanged gate is closed. The
[registration audit](../experiments/2026-07-17-uart-pstore-observability/results/watchdog-registration-audit-20260718.txt)
defines Candidate M's optional-IRQ omission and bounded decision oracle.
Candidate M's exact [build reproduction](../experiments/2026-07-18-watchdog-registration-diagnostic/results/final-build-reproduction-20260718.txt)
and [logical-`boot2` write/readback](../experiments/2026-07-18-watchdog-registration-diagnostic/results/boot2-write-candidate-m-20260718.txt)
are complete. Its [one attended runtime result](../experiments/2026-07-18-watchdog-registration-diagnostic/results/runtime-candidate-m-attempt-1-20260718.txt)
passes the basic watchdog/reset/pstore decision oracle; unchanged M repetition
is closed. Candidate N's exact
[build reproduction](../experiments/2026-07-18-cpu1-online-diagnostic/results/final-build-reproduction-20260718.txt)
and [logical-`boot2` write/readback](../experiments/2026-07-18-cpu1-online-diagnostic/results/boot2-write-candidate-n-20260718.txt)
are complete. Its one [runtime result](../experiments/2026-07-18-cpu1-online-diagnostic/results/runtime-candidate-n-attempt-1-20260718.txt)
passes the CPU1 decision oracle and records the automatic watchdog return. The
changed [Candidate O artifact](../experiments/2026-07-18-cortex-a53-sweep-diagnostic/README.md)
also passed its one [runtime result](../experiments/2026-07-18-cortex-a53-sweep-diagnostic/results/runtime-candidate-o-attempt-1-20260718.txt):
all CPU1–7 hotplug requests returned success, every target booted and advanced
accounting, the mask reached `0-7`, CPU8/9 remained offline, and the watchdog
cycle returned to Gemian. Do not rebuild, rewrite, or select N or O unchanged.
Candidate P then passed its one attributable rotation run: the owner read the
console in normal landscape, the exact inherited O sweep completed, and the
device returned to Gemian without owner help. The surviving post-return
`console-ramoops` records every O checkpoint and watchdog wait, although that
capture began after recovery and therefore did not independently record the
tested boot-ID transition or reset reason. Do not repeat unchanged P.
Candidate Q's combined keyboard-input and supervised-local-shell experiment
was built, installed, and fully read back, but the intended selection supplied
no working text console and no pstore evidence. Because no Q marker or deeper
keyboard/shell gate was observed, the failing layer is unknown. Its raw parent
interrupt cell also incorrectly used line 87 where GPIO87 maps to EINT10; that
static defect does not establish runtime causality. Do not repeat unchanged Q.
Candidate U used an upstream-AW9523 polling matrix path and a shell independent
of the event-capture window. It was independently built twice with matching
validated outputs and installed to live-resolved logical `boot2` with a
matching full-partition readback. Its first intended selection stayed black
with no marker or automatic reboot; later authenticated pstore was empty. All
deeper runtime gates remain unestablished, and unchanged U is closed. The exact captured LK's
[software-selection audit](../experiments/2026-07-12-boot-contract-recovery/results/lk-boot2-software-selection-audit-20260718.txt)
finds hardware-key branches for `boot2` and `boot3` and found no direct software
destination from Gemian in the audited paths, so the currently supported test
loop still requires manual silver-button selection. A modified one-shot
selector is separate bootloader work, outside the standing `boot2`
synchronization authorization.

[Candidate V](../experiments/2026-07-19-keyboard-watchdog-diagnostic/README.md)
is the installed successor. It restores exact P's final DT and no-IRQ
watchdog/ramoops recovery path, applies only the allowlisted keyboard polling
delta, and uses the corrected polling patch. Its reproducible validated image
was fully read back from live-resolved `boot2`. Attempt 1 then proved exact V
kernel/initramfs entry, visible loader fbcon, and automatic watchdog recovery,
but AW9523 repeatedly timed out at adapter 0 address `0x5b`. With AW9523 and the
matrix unbound and no input event, the exact 3.18 and latest-bsg100 comparison
selects the missing direct MT6797 I2C controller match and WRRD/aux-length
contract as the next single-variable kernel change. Keep AW9523 reset/cache and
matrix polling fixed. No shell or keyboard usability was established;
unchanged V is closed.

[Candidate W](../experiments/2026-07-19-keyboard-wrrd-diagnostic/README.md)
retains the earlier H/E/L/P/Enter event set and proven watchdog-expiry evidence. Its one-line direct
MT6797-to-`mt8173_compat` match is the causal delta selected by the exact 3.18
WRRD/auxiliary-length audit and latest checked bsg100 `main`; exact V's DTB,
watchdog, ramoops, and keyboard consumer remain fixed. Fixed tty2 kernel
messages, a respawning foreground tty1 shell, and `TER16x32` are independently
identified observation changes. Two clean packages and two final assemblies
reproduce, all 24 mutation cases pass, and the exact image was installed
without reboot to live-resolved logical `boot2` with a matching full readback.
One later run passed AW9523/provider, matrix, exact event-node, and bounded
H/E/L/P/Enter gates; the owner also observed the shell, working keyboard, and
approved font. Kernel-log isolation and useful session duration failed. X later
booted and worked by owner report, but its typed generic reboot appeared to hang;
empty pstore leaves the failure boundary unknown. Y was rejected before boot;
Z later booted with the keyboard still working and returned through its typed
watchdog path by owner report, corroborated by changed boot-ID and watchdog
reason. Historical AA r0 was superseded before boot and has now been replaced
on `boot2`; it must not be selected. AA r1 was built twice identically,
installed with a matching guarded full readback, and passed its attended map
gate with exact pstore verification, retained A/S press-release events,
owner-confirmed new-keymap operation, >123 seconds without automatic watchdog
ownership, and typed recovery. Candidate AB's reproducible kernel and
container validation is complete and exact padded AB now occupies inactive
`boot2` with a matching full readback. Its attended attempt retained exact AB
attribution and the map gate, stayed idle for 45 seconds without an automatic
reset or countdown, then reset immediately by owner observation after typed
bare `reboot`. Pstore places the request and final kernel restart line 27.854
ms apart, and Gemian returned under a changed boot ID. This establishes one
local named-unit kernel-restart pass, not repeatability; F1–F10 and Page
Up/Page Down remain unconfirmed.

## Current evidence snapshot (2026-07-22)

The repository has a reproducible Linux `7.1.3` baseline with a prepared arm64
configuration and packaged kernel/DTB artifacts. Candidate U was built from an
86-entry polling-profile series and installed with a matching readback, but its
later black-screen run supplied no marker, automatic reboot, or retained
pstore. U is rejected for unchanged repetition.

Candidate V remains the attributable failed-provider baseline for W. It restores
the exact Candidate P final DTB, including the loader-retained console and
hardware-passed no-IRQ watchdog/ramoops foundation, then applies only the
audited keyboard-resource/polling transform. Two fresh kernel builds
reproduced the selected package content and two complete V builds matched.
Package validation, focused schemas, strict patch review apart from one
0082 commit-message long-line warning, and all 24 negative mutation rejections
passed. The raw image is 6,864,896 bytes with SHA-256
`9ef0ee8dc1eb49752f9cf8f60b247b9b85e4fd2a9f090473f1d91848114087b0`.
The exact padded `boot2` target, remote checksum, and full local readback are
SHA-256
`57d362a86fae38c0ec2cec909ef6ae8d8ad124b87abb2ee58d179184c1f19168`.
Installation left root identity, boot ID, and power state unchanged and did not
reboot the device. Attempt 1 later showed a visible console and automatic
return. Retained exact markers establish kernel/initramfs entry, the
local-shell pre-exec recorder, `mtk-wdt` open/one-ping waits through 30 seconds,
and one loader-fbcon/watchdog-recovery result. Repeated AW9523
`-110`/`ETIMEDOUT` probe failures, including reset retry, left AW9523 and the
matrix unbound and no event node. There was no usable shell or keyboard test;
do not repeat unchanged V. See the
[Candidate V experiment](../experiments/2026-07-19-keyboard-watchdog-diagnostic/README.md),
[build reproduction](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/final-build-reproduction-20260719.txt),
[guarded write/readback](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/boot2-write-candidate-v-20260719.txt),
and [runtime evidence](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/runtime-candidate-v-attempt-1-20260719.txt).

Candidate W retains the earlier detailed H/E/L/P/Enter events and a proven
watchdog-expiry return; AA r1 later adds retained A/S events. Patch 0086 adds the
exact one-line direct
MT6797-to-`mt8173_compat` match while retaining V's exact final DTB, no-IRQ
watchdog, ramoops, and AW9523/matrix policy. Two clean packages and two final
assemblies reproduce and all 24 mutation cases pass; the raw 6,866,944-byte
image SHA-256 is
`34c41fad1e86de05b6a1f64f7e5d9229bd26ea88d982b0a57f2b9573aeb782d4`.
The exact image was installed without reboot to live-resolved logical `boot2`;
the padded image, remote checksum, and full local readback match SHA-256
`0ff3220096aa53f792116b3899e356bc2516816c9c330309c3d81e9fe1446608`.
In one exact W run, the controller/provider/matrix/event path passed and
limited H/E/L/P/Enter transitions survived. The owner observed the visible
shell, working keyboard, and approved font; visible printk mixing and the
deliberate watchdog timeout prevented useful serviceability. Do not infer all
keys, command execution, or repeatability. See the
[build reproduction](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/final-build-reproduction-20260719.txt),
[mutation result](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/validator-mutations-20260719.txt),
[guarded write/readback](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/boot2-write-candidate-w-20260719.txt),
and [runtime result](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/runtime-candidate-w-attempt-1-20260719.txt).

Candidate X was the clean-console/manual-reboot derivative. It is a configuration/initramfs policy
derivative of exact W, not a new keyboard change. Two clean builds reproduced
220 non-timestamp files, two final artifacts are recursively identical, 32/32
LK gates and 47/47 mutation rejections passed, and the exact candidate was
synchronized, flushed, and fully read back from logical `boot2`. The owner then
reported that it booted and worked, but typed `reboot` appeared to hang; pstore
after power-key recovery was empty. See the
[build reproduction](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/final-build-reproduction-20260719.txt),
[mutation result](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/validator-mutations-20260719.txt),
[guarded write/readback](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/boot2-write-candidate-x-20260719.txt),
and [runtime](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/runtime-candidate-x-attempt-1-20260719.txt).

Candidate Y was reproducibly built and fully read back but rejected before boot:
bare `reboot` resolves to BusyBox's internal applet instead of its external
wrapper, and watchdog-open failure cannot reach the intended refusal. Y was
never selected and has no runtime evidence.

Candidate Z is the hardware-tested keyboard/recovery foundation inherited by AA r1. It keeps exact Y
kernel/DT/config and changes four initramfs members plus adds read-only
`bin/reboot-dispatch.env`. Two full builds match recursively, the exact-BusyBox
dispatch gate passed on Linux arm64, 32/32 LK gates and 75/75 mutations passed,
and the full padded `boot2` readback matches SHA-256
`ba21e6424f94c82f14fd51b5681eea68d6cf09e9177e4f9ca2061c9f129abb40`.
The owner then reported one successful Z boot, working keyboard, and automatic
return after the typed watchdog command. A changed boot ID and watchdog-class
boot reason corroborate the return without proving exact internal subgates or
individual keys. See the [Y rejection](../experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/results/preboot-command-dispatch-audit-20260720.txt),
[Z build](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/build-validation-20260720.txt),
[dispatch validation](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/ash-dispatch-validation-20260720.txt),
[mutations](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/validator-mutations-20260720.txt),
[write/readback](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/boot2-write-candidate-z-20260720.txt),
and [runtime](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/runtime-candidate-z-attempt-1-20260720.txt).

Candidate AA r0 is historical, superseded-before-boot, and must not be
selected. Its raw/map/former-installed-padded SHA-256 values are respectively
`a2ad7a4107abd99cbd349b8f2deadd0185cbdd5bb0884ecbdae8ff2a7499ed4c`,
`48f1f61a9ad8ba327a3105c0dfbbc698c1e55bb3bcca695b46887888be8ca821`,
and `157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa`.
AA r1 replaces its incomplete map and invalid dump-byte oracle with a
2,311-byte, eight-table map (SHA-256
`02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c`)
and exact `KDGKBENT` verification of all 2,048 declared-table entries plus
undeclared-table absence. Its 53 semantic changes cover the smiley,
Shift+Fn F1–F10, backslash Ctrl/Alt behavior, and modifier-release policy.
The recovery-VM canonical static AArch64 verifier is SHA-256
`29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238`.
Two clean constructions are recursively byte- and metadata-identical; the raw
7,378,944-byte image is SHA-256
`37e82bf3be87dd9e52fb8d60597b69f92a5c0dc5aebd51d178f1e7efd33343d7`.
The guarded installer required exact r0 padded predecessor
`157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa`,
preserved a private full backup, resolved live-GPT `boot2` as
`/dev/mmcblk0p30`, and fully read back padded r1 as SHA-256
`38b49c7c19c2d97fa0c48436545219489221aa367aedf491ae6ebd4ec4856703`.
The installation did not reboot. Attended attempt 1 subsequently passed: exact
pstore records the loaded-now Unicode/map gate at 2.407618 seconds, all 2,048
entries and table-presence invariants, the normal prompt marker, validated
dispatch, exact AW9523/matrix/event0 identity, and A/S press-release events.
The owner reported the new keymap working. Bare `reboot` at
126.258967 seconds proves more than 123 seconds without an automatic watchdog;
the one-open/one-ping 31-second wrapper then retained fd 3, logged all six
countdown checkpoints, and returned the device to Gemian with a changed boot
ID and watchdog-class reasons. F1–F10 and Page Up/Page Down are unconfirmed,
not failed, because the console offered no visible discriminator. See the
[AA experiment](../experiments/2026-07-20-keyboard-console-map-diagnostic/README.md),
r1 [build validation](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/build-validation-aa-r1-20260721.txt),
[installer validation](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/installer-validation-aa-r1-20260721.txt),
[guarded write/readback](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/boot2-write-candidate-aa-r1-20260721.txt),
[layout reference](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/layout-reference-aa-r1-20260721.txt),
and [runtime result](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/runtime-candidate-aa-r1-attempt-1-20260721.txt).

Candidate AB passed one attended local hardware test. Patch 0087 selects MT6797 TOPRGU
restart priority 255 ahead of PSCI 129 while leaving every other supported
MediaTek SoC at 128. Builds 3 and 4 reproduce all 221 non-dynamic files and
modes with exact normalized provenance and common `Image.gz` SHA-256
`37ba538e76e329f3e57cfa78b481151e2d1e5eabcc321a29c7b54d476b6ec26f`.
Independent AB containers built from that pair and the hardware-passed AA r1
baseline are recursively byte- and mode-identical at raw SHA-256
`61c74592267466735164c19f8b831ea18db2892de95e32109f2aacd7ec5c5446`.
They retain the exact AA r1 DTB/keymap, pass 32/32 LK gates and 25/25 mutation
rejections, and contain no userspace watchdog or automatic reboot. The guarded
installer preserved exact padded AA r1, wrote only live-resolved inactive
`boot2`, and fully read back padded AB as SHA-256
`b58c0347d34a3fd9031c74cb03447dd7a6fc630d5b8ea2b7eabc36827e754350`
without rebooting or changing the boot ID. Attempt 1 then retained the exact AB
marker, map gate, and `GEMINI-AB#` prompt, and the owner confirmed the keyboard
worked. After 45 seconds without an automatic reset or countdown, the owner
typed bare `reboot` and observed an immediate reset. Pstore places the manual
request at 66.021584 seconds and final kernel `reboot: Restarting system` line
at 66.049438 seconds, 27.854 ms later; this is not an instrumented
Enter-to-LK measurement. Gemian returned with boot ID
`e33a0d8e-0354-4c8c-95b3-07c6970152ec`, changed from
`0f8def4f-3f94-4c57-a34c-2bb37315b19f`. The watchdog-class boot-reason fields
are nondiscriminating, but timing and the absence of userspace watchdog
ownership support prompt kernel TOPRGU SWRST. Proper reboot is supported by
one local named-unit pass, without a repeatability or universal reliability
claim. F1–F10 and Page Up/Page Down remain unconfirmed, not failed. See the [AB
experiment](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/README.md),
[kernel reproducibility](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/kernel-reproducibility-ab-20260721.txt),
[container validation](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/container-validation-ab-20260721.txt),
[installer validation](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/installer-validation-ab-20260721.txt),
[write/readback](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/boot2-write-candidate-ab-20260721.txt),
and [runtime result](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/runtime-candidate-ab-attempt-1-20260721.txt).

The earlier pre-keyboard purpose-built observability package,
`linux-7.1.3-gemini-observability-e1d4f6f3-a73fd870` (82 patches, patchset
SHA-256 `e1d4f6f36b49c5f6064bd7344e31c69b05903ef2f37fa8d9af736035faf47a8a`),
is historical. It was independently rebuilt from a fresh source extraction and
validated with `modules_built=false`, so it is an Image/DTB package rather than
a module-inclusive rootfs artifact. The broad 77-patch package
`linux-7.1.3-gemini-6116c9e7da3f` remains the broad general subsystem-audit
baseline, while the 76-patch and 72-patch packages described below retain
their narrower historical evidence. Patch 0076 adds disabled-only AW9523
matrix polarity properties; the working series also adds
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
That historical 77-patch package has a regenerated private gzip+appended-DTB
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
rollback is authorized. Candidate K, an exact-J initramfs-only derivative, was
synchronized and fully read back from `boot2`, then cancelled without a runtime
selection because it offers no kernel/DT/configuration hypothesis. Candidate L
was reproduced and fully read back from logical `boot2`. Its first intended
selection was unattributable; its second strongly reached the unique tracked
`watchdog0=waiting remaining=5s` initramfs line before the screen switched off.
The adapter was connected but serial stayed silent. Manual power recovery led
to Gemian with empty pstore and no watchdog-reset indicators. Candidate M then
isolated that registration boundary by omitting only the optional bark IRQ as
its hardware hypothesis. Its one attended run kept the console visible,
registered and armed the basic watchdog, reached the durable 30-second marker,
and returned automatically. Gemian recovered the exact M `console-ramoops` and
reported a PMIC watchdog reset. Unchanged L and M are stopped. The normal UART
prerequisite remains operationally unmet, but fbcon plus pstore plus the proven
watchdog now provide the recovery-backed observation loop for the next CPU1
gate.
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
The corresponding historical 76-patch CPU/PSCI/timer package audit preserves all
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
contract is preserved. At that historical package-audit point, no generated
mainline image had a confirmed Linux runtime result on Gemini hardware and the
timed-reboot result was only strong indirect `/init` evidence. Later M–Z
experiments supersede that global runtime statement; they do not promote any
untested subsystem in these older packages. These patches therefore describe
and compile candidate SoC/board support only where no later named-device result
is cited. The earlier baseline package is
`linux-7.1.3-gemini-c2d9eea95daa` with patchset SHA-256
`c2d9eea95daa25dd8faddef4f9822e663db67d5d0946f06f0251cc52c92cf08c`.
For the SPI boundary, the historical 74-patch package is
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
The exact historical 74-patch USB/Type-C package audit is reproducible and
keeps all USB11, MTU3/xHCI, T-PHY, and FUSB301 board consumers disabled; see
the [current USB package result](../experiments/2026-07-12-usb-typec-recovery/results/mainline-usb-current-74-package-20260714.txt).
The focused [I2C controller audit](../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/i2c-mt6797-controller-reuse-20260714.txt)
also confirms that MT6797 reuses the upstream `mt6577` `i2c-mt65xx` register
and quirk profile. Candidate AL supplied a mainline I2C6 transfer, but a
2026-07-23 correction found that live Gemian marks this bus `appm_used` and
pauses its active DVFSP owner around each hardware transaction. Reuse the
existing transfer engine, but prove the mainline firmware owner quiescent or
add the matching ownership layer before any DA9214 rail write.
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
The historical 74-patch rerun of the [first-boot dependency audit](../experiments/2026-07-14-first-boot-probe-audit/results/first-boot-probe-audit-current-74-package-20260714.txt)
confirms that the SPI additions do not alter the UART/PWRAP/MT6351/MSDC
probe chain; the PMIC remains part of the eMMC path.
The focused display/input package audit for the same historical 74-patch artifact
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
checkout's `KEY_FN`. Patch 0054 now follows that active-boot-normalized map.
Candidate Q supplied no observable keyboard or VT evidence and must not be
repeated unchanged. Candidate U was independently built twice with matching
validated outputs and installed to live-resolved logical `boot2` with a
matching full-partition readback. Its first intended selection supplied no
visible marker or console and no retained pstore, so its intended coverage of
physical press/release, modifier, simultaneous-key, polarity, and VT input
through polling remains entirely unestablished. Do not repeat unchanged U.
Debounce/timing, wake, LEDs, and full rollover remain later focused gates. See the
[active ELF result](../experiments/2026-07-12-input-backlight-recovery/results/active-aw9523-elf-keymap-20260714.txt).

Links below whose filenames contain `current-71` are retained historical
source/build evidence; the adjacent `current-72` or `current-package` record
is authoritative for the present artifact.

The table is the longer-term subsystem order. For the next boot's target,
observability, and one-CPU scope, the current P0–P13 plan at the top of this
document supersedes the older first-row wording.

| Priority | Area | Linux 7.1.3 reuse decision | Required new work or gate |
| --- | --- | --- | --- |
| 1 | UART, timers, PSCI, watchdog, RAM | Reuse `8250_mtk`, the architectural timer, generic PSCI for the proven Cortex-A53 path, and `mtk_wdt`; Cortex-A72 external power coordination remains separate | Candidate AD and exact AI established the boot-time eight-A53 boundary with CPU0–7 advancing and CPU8/9 offline; AI also passed readable console, exact USB, native reboot, changed-Gemian return, and post-cycle `boot2` integrity. Exact AJ attempt 2 passed one fail-closed CPU8 dispatch but retained an unpaired pstore snapshot and pending console confirmation. Exact AK attempt 1 then passed the ordered CPU8/CPU9 fail-closed dispatch control with CPU0–7 advancing, neither A72 online, an owner-attested readable console, native reboot, changed-Gemian return, and a matching post-return full `boot2` hash; its chain remains unpaired. Draft patch 0093 remains unsafe/unselected: Linux owns DA9214/PWRAP/external-isolation preparation, secure firmware owns initial B PLL/MTCMOS/bus/CCI, SRAM needs independent readback, and no safe inverse/off exists. Gemian reconciliation separates the active March 29 image from the May 24 `gbp59e00a` package; the active exact public commit remains unresolved, and `59e00a` is only the chosen equivalent for verified owner hooks. A reviewed two-worker pulse directly observed one short CPU8 online/offline cycle with CPU9 excluded, but the sequential observer missed the transaction. Candidate AL's resource-only DA9214 attempt failed legacy identity, and Candidate AP's hard I2C6 handoff dependency then failed closed because shared AP_DMA never reached its absolute-gated cleanup oracle. Before another resource or CPU8 candidate, identify AP_DMA's existing owner, design a baseline-preserving I2C6 cleanup oracle, and separately capture the owner-local online and last-A72-offline records. Candidate AM is the first active CPU8 provider and remains blocked on those predecessors. Retain no-OPP/no-idle/no-thermal/no-hotplug-off policy and proven TOPRGU recovery. See [Candidate AI](../experiments/2026-07-22-a72-reject-gate-kernel-split/README.md), [AJ attempt 2](../experiments/2026-07-22-a72-reject-cpu8-request/results/hardware-attempt-2-runtime-reboot-return-20260722.txt), [AK attempt 1](../experiments/2026-07-22-a72-reject-cpu9-request/results/hardware-attempt-1-20260723.txt), [A72 firmware/power contract](../experiments/2026-07-22-a72-firmware-power-contract/README.md), [Candidate AP](../experiments/2026-07-24-mt6797-dvfsp-i2c6-consumer/README.md), [load-assisted CPU8 observation](../experiments/2026-07-23-gemian-a72-load-assisted-observation/results/live-attempt-1-20260723.txt), [CPU/PSCI/timer](../experiments/2026-07-13-cpu-psci-timer-recovery/README.md), and [watchdog policy audit](../experiments/2026-07-12-mt6797-watchdog-recovery/results/mainline-watchdog-current-72-policy-20260714.txt). |
| 2 | PMIC, regulators, eMMC, GPIO/EINT | Reuse upstream PWRAP/MT6397, `mtk-sd`, pinctrl, EINT, and power-supply frameworks with MT6797 data; the MT6351 MFD/regulator/RTC layer is a local implementation because no upstream MT6351 provider exists | The current PMIC audit confirms MT6351 E2, 39 unique rail descriptors, and the stateful pwrap/MFD probe boundary; the current MSDC audit confirms live DF4064 HS400/eMMC and an empty powered-off microSD host while retaining a 25 MHz legacy-only first-boot node and pinmux-only MT6797 state. The direct 77-patch package audit ties that node to built-in MMC/PWRAP/MT6351/pinctrl objects and confirms no HS200/HS400 flags; its first probe still changes clocks, controller registers, IRQ state, and PMIC rails before eMMC identification. An independent bsg100 Linux 6.6 boot corroborates the level-low MSDC0 IRQ, explicit VEMC/VIO18 supplies, MT2701-generation register profile, and pinmux-only boundary, but does not validate the current 7.1.3 image. The first-boot dependency audit confirms that eMMC supply consumers make PMIC probe part of the storage path. The current charger package audit confirms reusable BQ25890/FAN49101 provider objects but no enabled charger, battery, or fuel-gauge consumer in the Gemini DTB. Validate pwrap/PMIC identity, rail readback, reset/RTC, storage read-only I/O, input IRQs, and charger identity/telemetry on hardware before attaching consumers. See [first-boot probe audit](../experiments/2026-07-14-first-boot-probe-audit/README.md), [current PMIC validation](../experiments/2026-07-11-mt6351-pmic-recovery/results/mainline-mt6351-current-72-validation-20260714.txt), [current MSDC validation](../experiments/2026-07-12-mt6797-msdc-recovery/results/mainline-msdc-current-77-package-20260714.txt), [MSDC cross-check](../experiments/2026-07-12-mt6797-msdc-recovery/results/bsg100-msdc-crosscheck-20260714.txt), [current charger package audit](../experiments/2026-07-12-charger-power-recovery/results/mainline-charger-current-72-package-20260714.txt), [PMIC](../experiments/2026-07-11-mt6351-pmic-recovery/README.md), [MSDC](../experiments/2026-07-12-mt6797-msdc-recovery/README.md), and [EINT](../experiments/2026-07-12-mt6797-eint-recovery/README.md). |
| 3 | Keyboard, USB serviceability | Reuse upstream AW9523 GPIO/pinctrl and generic matrix input plus FUSB301; retain the existing USB framework split. | W proved AW9523/matrix binding, `/dev/input/event0`, and bounded H/E/L/P/Enter events once. AA r1 later retained exact map-table validation and A/S events, and the owner reported the new map working; F1–F10 and Page Up/Page Down remain unconfirmed rather than failed. AB then passed one prompt native-restart run with the physical keyboard working. Candidate AC established exact direct-link USB gadget Ethernet through host interface, carrier, ping, TCP marker, and bounded shell. AH attempt 2 independently retained that USB service and live AW9523/keymap binding while its console and native reboot passed, but no physical key was exercised in that AH run. Host mode, VBUS, Type-C, role switching, charging, physical-port mapping, and full keyboard coverage remain open. See [W runtime](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/runtime-candidate-w-attempt-1-20260719.txt), [AA r1 runtime](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/runtime-candidate-aa-r1-attempt-1-20260721.txt), [AB runtime](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/runtime-candidate-ab-attempt-1-20260721.txt), [AC experiment](../experiments/2026-07-21-usb-gadget-ethernet/README.md), and [AH attempt 2](../experiments/2026-07-22-ad-contract-af-kernel-split/results/runtime-candidate-ah-attempt-2-20260722.txt). |
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
