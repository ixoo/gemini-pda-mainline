# Architecture and ownership

## Target architecture

The project aims to move the maintainable boundary as far down the boot stack as practical without making risky boot-firmware replacement a prerequisite for useful Linux support.

```text
Phase 1: safe enablement

MediaTek BootROM                 immutable silicon
  -> retained preloader / ATF    DRAM, secure-world, early platform init
  -> retained Planet LK          development shim and recovery choices
  -> upstream-derived Linux      generic MT6797 support + Gemini board DT
  -> standard initramfs/rootfs   distribution-neutral userspace

Phase 2: boot ownership

MediaTek BootROM
  -> retained or replaceable early firmware, evaluated separately
  -> maintained U-Boot/open LK chainloader
  -> standard Image/DTB/initramfs selection
  -> owner-controlled verification and recovery keys
```

Replacing the preloader or secure firmware is a separate stretch project. Linux hardware enablement must not depend on it.

## Ownership boundaries

| Layer | Desired owner | Project rule |
| --- | --- | --- |
| Linux generic drivers | Upstream subsystem | Extend generic drivers; no Gemini-only copies |
| MT6797 SoC description/support | Upstream Linux/DT maintainers | Keep reusable SoC work separate from board data |
| Gemini board Device Tree | Upstream Linux | Declarative board description with reviewed bindings |
| Temporary integration series | This repository | Pinned, reviewable, disposable after upstream merge |
| Initramfs/build tooling | This repository or distribution | Reproducible and non-destructive by default |
| Root filesystem | Distribution | No project-specific userspace requirement |
| Boot selection/recovery | Device owner | Preserve known-good path and owner-controlled artifacts |
| Modem/Wi-Fi firmware | Device firmware boundary | Retain only where unavoidable; expose standard kernel/userspace interfaces |

## Non-negotiable principles

### Upstream is the product

Every local kernel change needs:

- an upstream destination;
- a responsible issue;
- test evidence;
- a stated dependency chain;
- a deletion condition.

Branches may be rebased. GitHub issues and public mailing-list archives are the durable project record.

### No vendor-code laundering

Vendor source is evidence, not automatically acceptable implementation. Facts may be re-expressed; copied code must have clear provenance, compatible licensing, and a reason it cannot be replaced with an existing upstream abstraction.

### Generic before board-specific

Changes should layer cleanly:

```text
binding -> generic driver capability -> MT6797 SoC node -> Gemini board node
```

A Gemini quirk in a generic driver must be narrowly justified. Board policy does not belong in a reusable SoC driver.

### Chip identity before driver reuse

Driver reuse is a protocol decision, not a naming decision. For each vendor
component, compare the observed chip-ID/register map, bus transaction model,
power/reset/IRQ contract, and firmware ownership with the Linux 7.1.x driver
and binding:

| Evidence | Mainline action |
| --- | --- |
| Same silicon protocol and standard resources | Reuse the existing driver; add only SoC/board data, a binding extension, or a mount/power description. |
| Same family but an unrepresented register revision or board state machine | Extend the generic driver with narrowly scoped data and a reviewable compatibility record. |
| Different chip ID, register map, transport, or firmware ownership | Select an existing family driver or write a new chip/transport driver. Do not make the closest generic driver emulate the vendor ABI. |
| Identity or resources remain indirect | Keep the node disabled and record the discriminating probe; do not promote a compatible string to hardware support. |

The legacy Gemini sensor stack illustrates the rule: `bmi160_acc` and
`bmi160_gyro` are strong software-path evidence, but the vendor probes rewrite
both logical clients to `0x69` and the electrical ID was not directly captured.
The current record therefore favors one standard BMI160 IIO instance while
leaving LSM6DS3 or a genuinely different part free to select its own upstream
or new driver. See the [sensor/IIO recovery experiment](../experiments/2026-07-12-sensor-iio-recovery/README.md)
and [vendor IMU probe record](../experiments/2026-07-12-sensor-iio-recovery/results/vendor-imu-probe.txt).

### Standard subsystem contracts

Userspace should see ordinary Linux interfaces. Examples include DRM/KMS, evdev, power_supply, hwmon/thermal, MMC, USB role switch, ALSA ASoC, rfkill, and a documented modem transport usable by ModemManager or oFono.

### Firmware is isolated

Some embedded firmware will likely remain opaque. Acceptable firmware:

- runs on an isolated device or coprocessor;
- is loaded through a standard kernel mechanism where possible;
- does not require an out-of-tree proprietary kernel module;
- has documented version, source, checksum, and redistribution status outside Git when redistribution is not allowed.

### Reproducibility and evidence

Every boot artifact must be traceable to source revisions, configuration, toolchain, and packaging inputs. Hardware claims progress through the support-matrix states; compilation alone never means `working`.

### Safety is architectural

- Development targets a non-primary boot slot.
- Recovery remains independently bootable.
- Scripts reject ambiguous block-device and partition targets.
- NVRAM, GPT, preloader, and secure firmware are outside ordinary workflows.
- Logs are redacted before publication.

## Patch lifecycle

Temporary patches live below the pinned upstream-base directory. The canonical
`patches/series` is the superset and ordering authority; a manifest-pinned
experiment profile may select a named canonical-order subsequence:

```text
patches/
  series                         canonical ordered superset
  series-<named-experiment>      optional manifest-pinned subsequence
  <upstream-base>/
    0001-*.patch
```

Every selected patch must also remain in the canonical series in the same
relative order. Experiment documentation records purpose, dependencies,
owner, upstream target, and status.

Once merged upstream, remove the patches and replace them with the first containing release/commit in the issue and support matrix.

## Baseline and current implementation map

The subsystem audit baseline is Linux 7.1.3 with 72 non-comment entries and
patchset SHA-256
`c2d9eea95daa25dd8faddef4f9822e663db67d5d0946f06f0251cc52c92cf08c`.
The canonical working series has 101 ordered entries and extends through patch
0102, with unsafe active-A72 draft 0093 and legacy-DA9214 draft 0096 excluded.
Patches 0072–0076 add
disabled SPI and input candidates; the latest validated package for that
boundary is `linux-7.1.3-gemini-6116c9e7da3f` with patchset SHA-256
`6116c9e7da3fc2f56612029236a3bcd370c61f91b3c0951dd4e2c1915537f55e`.
Patches 0088–0091 are the later DA9214, TOPRGU-reset, and read-only resource
observer integration stack; they are resource discovery, not Cortex-A72
support. Corrected 0092 adds a DT-selected fail-closed method for CPU8/9: its
boot callback returns `-EAGAIN` before generic PSCI `CPU_ON`, reports CPU
disable unavailable, and exposes no disable/die/kill callback. The Candidate
AI profile selects exact 0001–0087 plus corrected 0092 while omitting 0088–0091
and the unlisted active-power draft 0093. Two independent AI package trees now
reproduce all 225 substantive files and modes plus normalized provenance. Their
common SHA-256 values are `Image`
`fb2c02601a07b49781b97ef9d39b79218db1c158ce1547a2ea53df7fb1e51fe2`,
`Image.gz`
`b87984a570567ef47f151024612889f7d5d49b938c10bd08f0aecfea47b481a9`,
`System.map`
`622945b38e025db7ee7719f2fa3132e17f8ad0158651e2f77e57918a76ac384d`,
resolved config
`32dd13a6704e5fa591236ba114d43e8e7e1aeb3eb123d9d4f124b5f551301d46`,
packaged Gemini DTB
`510669e70cd39df3c0e1a1b4c806c0eeaa8e0b0fe02e037ee1bf405d39498af8`,
and compiled audit
`67519ff0a82376e2d0628f7061af474b0df6427c0f54878717a6c6b1d672a525`.
Two independent 20-member Android-v0 artifact trees are byte- and mode-exact,
with raw SHA-256
`1ecfc787fec2f5dc11c5b7d30eb4f11d34b0496e57daf42adea567f010282309`
and manifest SHA-256
`b8c2953dd07e2a84a05e99f7bd0a981cbe593e928ba7507f16691279d82fa8cc`.
Two ephemeral 16 MiB padding checks independently verified the all-zero tail
and SHA-256
`8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86`;
the temporary files were removed and not published. Guarded installation,
exact USB/runtime attribution, readable console, native reboot, changed-Gemian
return, and post-cycle full-`boot2` integrity passed for AI. CPU0–7 advanced;
CPU8/9 stayed offline and unrequested. Exact AH attempt 2 separately proved
that its AF-kernel/AD-board split retains the same working console, exact USB
service, advancing CPU0–7, offline and unrequested CPU8/9, native reboot, and
post-cycle `boot2` integrity. Neither baseline exercised an A72 path.

Candidate AJ changes only `maxcpus=8` to `maxcpus=9`. Its first owner report
was rejected as an identity mismatch. Its exact second runtime passed with one
CPU8 pre-PSCI gate rejection and one `-11` boot failure, no CPU9 attempt, and
advancing CPU0–7. Native reboot returned to changed-boot-ID Gemian and a full
read-only post-return `boot2` hash still matched AJ. The retained pstore is a
deliberately unpaired post-return snapshot, not a paired recovery-collector
cycle. AJ remains partial only until the owner explicitly confirms that the
local console in attempt 2 was readable. A separate safety-predecessor audit
keeps that status but accepts the exact compound runtime, native-reboot,
changed-Gemian-return, and full-readback chain as sufficient to build and
guardedly install the fail-closed CPU9 control AK over exact AJ.

The A72 firmware/power audit fixes the future ownership boundary. Linux owns
external DA9214 BUCKB, temporary TOPRGU PWRAP reset, MP2 reset-release and
external-isolation preparation, the SRAM-LDO request, and the post-success DCM
toggle. Captured secure firmware owns the initial B PLL/mux/divider,
cluster/core MTCMOS and reset, internal bus protection, and CCI coherency
admission. SRAM-LDO completion requires independent readback because the
captured service returns zero unconditionally. No safe inverse/off sequence is
proven; after isolation is cleared, failure must retain power, fault without
retry, and rely on independent reset recovery. Draft patch 0093 therefore
remains unsafe and unselected. Private-binary reconciliation separates the
active March 29 Gemian boot image from the different May 24 `gbp59e00a`
installed package. The active image's exact public commit remains unresolved;
`59e00a` is the chosen equivalent for verified owner-safe observer-hook blobs,
not exact provenance. A bounded two-worker pulse directly observed one short
CPU8 online/offline cycle with CPU9 excluded, so trigger calibration is
complete, but the sequential companion observer missed the transaction.
Candidate AL tested the mainline I2C6/DA9214 resource-only predecessor without
requesting either A72. I2C6 bound, exact client `0x68` appeared, and the
inherited eight-A53/serviceability path survived, but the upstream
DA9211-family probe read unsupported device ID `0x0`, returned `ENODEV`, and
registered neither regulator. AL therefore fails and must not be repeated
unchanged. Candidate AN then established the exact stopped/reset-like PCM
signature while exposing that I2C_APPM remained ungated. Exact binary recovery
identified reversible vendor stop and the per-transaction pause protocol.
Candidate AO's one-way owner subsequently passed its named-unit acceptance
test: one balanced CCF reference left the PCM signature unchanged, gated
I2C_APPM after release, and remained gated at 45 seconds with zero faults.
I2C6 remained disabled and no DA9214 or A72 operation occurred. Candidate AP
then added the separate access-controller dependency and enabled only childless
I2C6. Its exact live FDT passed, but the named-unit runtime failed closed:
I2C_APPM regated after one guarded clock hold while AP_DMA stayed ungated
through all 32 cleanup samples. The provider faulted, I2C6 returned `-EIO`
before binding an adapter, and no transfer, client, regulator, DA9214, or A72
operation occurred. AP's initial samples already showed AP_DMA ungated, and
enabled UART0 and I2C5 share that CCF gate. Candidate AQ then kept I2C6
disabled and added only read-only debugfs observation. Its early and five-second
summaries were byte-identical: AP_DMA was enabled with refcount 2 and owner
`1101c000.i2c` (`dma`), while I2C_APPM was disabled with refcount 0 and owner
`11015000.dvfsp-handoff`. The owner reported a readable console and the
inherited eight-A53, keyboard, USB, and reboot path survived; AQ performed no
I2C6, DA9214, A72, clock-control, storage, or reboot operation. This attributes
the surviving AP_DMA reference to the enabled I2C5 DMA path. The next
architectural layer is therefore a baseline-preserving cleanup contract that
retains I2C5/AP_DMA while handling the separate I2C_APPM handoff gate—not an
unchanged AP/AQ retry or DA9214 access. Candidate AM, the
first active CPU8 experiment, additionally requires that corrected
consumer/regulator prerequisite and a fixed-register, owner-local in-kernel
record of the online and last-A72-offline paths from the chosen source
equivalent; no synchronized live register-state capture exists yet. See the
[A72 firmware/power contract](../experiments/2026-07-22-a72-firmware-power-contract/README.md),
[load-assisted observation](../experiments/2026-07-23-gemian-a72-load-assisted-observation/README.md),
[Candidate AL runtime](../experiments/2026-07-23-da9214-resource-only/results/runtime-candidate-al-attempt-1-20260723.txt),
[Candidate AO](../experiments/2026-07-24-mt6797-dvfsp-one-way-handoff/README.md),
and [Candidate AP](../experiments/2026-07-24-mt6797-dvfsp-i2c6-consumer/README.md).
Patches 0077–0078 add an opt-in T-PHY B-device-session capability and disabled
Gemini MTU3 peripheral wiring for the separate USB diagnostic. The exact USB
image was tested from non-primary `boot2` and did not enumerate. A follow-up
that retained its kernel and DTB while changing only initramfs `/init` reached
a delayed off-like state after an owner-estimated 5–10 seconds instead of
remaining dark and steady. This is strong indirect evidence for external
`/init` execution, but it is not a stopwatch measurement, repeat, or surviving
log and does not establish that the USB driver probed or works. A subsequent
screen-marker candidate retains the same `Image.gz`, adds only a validated
simplefb description, and performs one bounded framebuffer fill. It was
written, flushed, fully read back from `boot2`, and attempted once; the display
was black and showed none of the expected bands. This fails the positive test
but does not distinguish kernel entry, simplefb, the write, or LK scanout
retention. Candidate F keeps that exact Image and initramfs while adding only a
path-resolved `CLK_INFRA_DISP_PWM` simplefb reference. Its first attended boot
showed sideways console text for about one second before black. This is the
first positive visual Linux 7.1.3 signal and strongly supports simplefb/fbcon
output, although the unread text does not independently prove `/init`.
Candidate G keeps F's exact kernel segment and DTB, removes all raw framebuffer
access through an initramfs-only delta, and holds a distinctive tty0 banner.
Its two builds are byte-identical and its logical-`boot2` write has a matching
full readback. Its attended boot reproduced sideways scrolling for 1–2 seconds
before black with the backlight apparently off. Candidate H preserves G's exact
kernel and initramfs and appends only `CLK_TOP_MUX_MM` to the simplefb clocks
property. In one attended series, two attempts visibly progressed farther and
the owner approximately recognized H's initramfs-only marker before the screen
and backlight went off; later attempts did not reproduce the visible progress.
This strongly attributes those visible attempts to external `/init`, but does
not establish repeatability or stable display retention. Candidate I preserves
H's exact kernel and DTB and exact initramfs tree except `/init`, then emits one
tty0 line per second through `T+60` before a silent static hold. It was built,
exported, synchronized, and fully read back from logical `boot2`, but the
reported intended selection went directly to black with no I marker, counter,
or other text. Its selection, `/init`, active-refresh interval, and static hold
are therefore unestablished; the timing hypothesis remains untested.

Candidate J is the broad early-handoff control. It rebuilds the kernel to
append `clk_ignore_unused` to the forced `CONFIG_CMDLINE`, while keeping exact
I's DTB, initramfs, and Android header command line. A header-only draft was
rejected because `CONFIG_CMDLINE_FORCE=y` makes that loader-provided addition a
runtime no-op. An isolated clean rebuild reproduced the resolved config,
kernel payload, `System.map`, all 119 DTBs, and raw boot image byte-for-byte;
only timestamp-bearing build provenance and its checksum manifest differ. The
raw J image SHA-256 is
`6d5bad08c2f93eba7fbd66ea5c54de2437f81e44832426a97d4d65d550c659f4`;
it was synchronized to logical `boot2`, and the full 16 MiB target/readback
matched SHA-256
`465e4c747138e12191d38fd6b4cde68cd0b9a19f918030dea05c9b8dbdd4d3fc`.
The write did not reboot the device. On the first later owner-attended intended
`boot2` selection, the last visible suffix before black was reported as
`4/60`. Only the tracked shared I/J `/init` emits that counter. Combined with the
verified J target/readback and intended selection, this strongly supports
Linux entry, visible fbcon/tty0 output, and shared `/init` execution through
tick 04 for this attempt. The full line and marker were not exactly
transcribed. A later two-bullet report is provisionally interpreted as two
additional intended J/`boot2` selections because its outcomes are mutually
exclusive, with owner confirmation pending. One reached "iteration 4" before
black, compatible with and corroborating tick 04 without an exact marker or
full-line transcription. One went directly black with no console; that
observation cannot establish selected slot, kernel entry, or `/init`.
Provisionally, two of three intended selections had tick-04-compatible visible
output and one of three was no-console and unattributable. Stable visibility,
clock causality, and a specific clock identity remain unestablished. Further J
repetition is stopped. This deliberately broad
diagnostic does not enable clocks that are already off, prevent explicit clock
disables, or retain regulators or power domains, and it is not a normal boot
policy. That exact J kernel compiled fbcon rotation out; the later isolated
Candidate P configuration gate subsequently established readable
normal-landscape loader fbcon in one run.

Candidate K was a reproducible exact-J initramfs-only newline/scroll
derivative. Its synchronized `boot2` write/readback record remains historical
evidence, but a strategy review cancelled its device test without a runtime
selection: K changes no kernel, DT, or configuration input, and no outcome
would change the next prerequisite.

[Candidate L](../experiments/2026-07-17-uart-pstore-observability/README.md)
was a historical observability gate. It changed the board UART0 pinmux to the
captured GPIO97 RX/GPIO98 TX state, mapped the mainline ramoops console exactly
onto the active Gemian kernel's primary console zone, and added MT6797 TOPRGU dual-stage and
auto-restart policy so a controlled watchdog expiry can leave persistent
evidence. The exact binary and pinned source independently support the primary
layout. Mainline pmsg supplies address alignment and is not a recovery
channel. A distinct fresh-source build reproduced all non-timestamp package and
candidate content, and the final image was exported, synchronized to logical
`boot2`, block-flushed, and fully read back. Attempt 1 showed LK splash then
black and was unattributable. Attempt 2 showed console output through exact
suffix `remaining 5s`, unique to Candidate L's tracked watchdog-device wait
loop. This strongly supports kernel, loader-simplefb/fbcon, and `/init` entry,
and establishes that `/dev/watchdog0` was absent at that check. Connected
serial was silent; manual recovery was required, and immediate pstore was
empty. No watchdog open, bark, expiry, automatic return, UART function, pstore
retention, USB, or native-display behavior is established.
The following map is the implementation boundary for the baseline candidate; it is
deliberately grouped by dependency rather than treating every patch as a new
driver.

| Series range | Area | Reuse decision | Current runtime boundary | Next evidence gate |
| --- | --- | --- | --- | --- |
| 0001–0006 | Infracfg reset, MT6797 pinctrl, EINT | Extend generic reset/pinctrl/EINT data; no vendor ABI copied | Pinctrl is built in; UART0 depends on its pin state; extra EINT consumers remain disabled | Verify GPIO polarity, IRQ routing, debounce, and wake on hardware |
| 0007–0015 | PWRAP, MT6351 MFD/regulator/RTC | Reuse upstream MTK PWRAP/MT6397 framework code; the MT6351 MFD/regulator/RTC implementation is a local 7.1.3 addition with MT6797 pwrap and rail data | Built-in and implicitly enabled; probe writes pwrap/IRQ state and can affect PMIC ownership | Capture before/after pwrap, PMIC interrupt masks, IDs, and rail selectors during recovery-backed boot |
| 0016–0020 | MSDC/eMMC and Gemini board description | Reuse `mtk-sd` with MT6797 tuning data and conservative board DT | MSDC0 is built in and enabled at 25 MHz legacy timing; microSD stays disabled | Read-only eMMC probe/I/O, then controlled timing escalation |
| 0021–0025 | CAM/MJC clocks, M4U/SMI | Reuse generic CCF/IOMMU/SMI with new MT6797 data; add only missing providers | Providers are built in or available, but multimedia DMA consumers remain disabled | Enable one verified DMA consumer after clock, larb, port, reset, and fault contracts are captured |
| 0026–0044 | GCE, mutex, MMSYS, DRM, DSI, PHY, panel, display PWM | Reuse generic multimedia cores with MT6797 platform data and a board panel descriptor | Display objects are module-only or disabled; panel graph and power sequence are not runtime-proven | First-light test only after exact panel bias/reset/backlight/graph evidence |
| 0045–0046 | AFE resources and thermal/DVFSP resources | Board DT description only; no consumer is enabled | AFE, thermal, and AUXADC nodes remain disabled | Resolve machine-card/calibration contracts and preserve fail-closed thermal behavior |
| 0047–0051 | MFG power domains/clocks, 52 MHz preclock, RT5735 VGPU | Reuse SCPSYS/CCF/regulator abstractions with MT6797 SRAM and ownership data | GPU/MFG/RT5735 consumers remain disabled; CPU clock ownership is separately secure/semaphore-mediated | Prove power/reset/OPP/rail ownership before Panfrost or DVFS |
| 0052–0057a | BMI160, watchdog, AW9523, FAN49101, FUSB301, thermal, LK calibration | Reuse standard BMI160/watchdog/AW9523 foundations; new chip driver/data only where register contract differs; NVMEM provider is a narrow LK ABI adapter | Watchdog is implicitly enabled; other candidates are disabled or module-only; calibration provider is read-only/root-only | Hardware ID/readback with explicit recovery; never promote a compatible string from indirect evidence |
| 0058–0065 | Panfrost, DPI, PMIC parent fix, SCPSYS/AFE bindings, DVFSP deferral | Reuse Panfrost/DRM/PMIC/SCPSYS/ASoC frameworks; keep undocumented DVFSP out | Panfrost/DPI/AFE consumers remain disabled or module-only | Validate each consumer’s clocks, resets, IOMMU, supplies, and firmware boundary independently |
| 0066–0071 | USB T-PHY/MTU3/xHCI/MUSB and MSDC pinmux policy | Reuse generic USB cores with MT6797 glue and source-derived split windows; use pinmux-only MSDC state | USB nodes remain disabled; built-in code is package capability, not probe evidence | Gadget-only console first, then role/VBUS and PHY tests with external recovery |
| 0072–0076 | SPI aliases/nodes, hall input, NT36772 boundary, keyboard polarity | Reuse generic SPI and input frameworks where the captured protocol matches; keep every new board consumer disabled | The 77-patch package validates, but these additions have no current-mainline runtime result | Test one bounded consumer at a time with exact identity and recovery evidence |
| 0077–0085 | MTU3 diagnostic, UART/pstore/restart observability, AW9523 resources, generic matrix polling, EINT correction | Reuse generic MediaTek USB, 8250, pstore, watchdog, I2C, AW9523, and input facilities; patch 0083 adds the polling binding, 0084 adds the generic matrix driver path, and 0085 corrects the disabled board's raw parent EINT | The USB candidate remains a failed host-observation gate. K was cancelled without runtime. Candidate L reached tracked external `/init`, but the optional IRQ-bearing watchdog did not register. Candidate M proved the no-IRQ `mtk-wdt`, 31-second automatic recovery, and cross-version console retention. Candidate O retained that exact recovery foundation while sequential standard hotplug requests brought logical CPU1–7 online; all seven checkpoints and final `online=0-7` survived one automatic recovery cycle. Candidate P then preserved those checkpoints while the owner observed readable normal-landscape fbcon and an unassisted Gemian return. Candidate Q was reproducibly built and written, but its intended selection supplied no working text console or retained pstore evidence; its deeper execution and keyboard gates are unestablished. Static review found that Q passed raw interrupt line 87 although GPIO87 maps to EINT10. Patches 0083–0085 and U's two matching validated builds are build/static evidence. U was installed to live-resolved logical `boot2` with a matching full-partition readback; its first intended selection produced a black screen and dark console with no marker or automatic reboot. A later changed Gemian boot ID and empty pstore establish no U kernel, `/init`, console, or keyboard gate. UART, bark/pretimeout, keyboard input, USB host behavior, and native display remain unproven. | Retain P's console and the basic no-IRQ watchdog/pstore foundation. Do not repeat K–U unchanged. Candidate U retained the upstream AW9523/reset contract and GPIO87/EINT10 pinmux, removes the parent-IRQ consumer from its candidate-only active path, polls every 20 ms with a 2 us column-scan delay and no separate polling debounce, and exposes the shell independently of input capture. Its configuration was CPU0-only, its initramfs omitted userspace-watchdog access, and the pinned Linux 7.1.3 watchdog-policy audit confirms `WATCHDOG_HANDLE_BOOT_ENABLED` keepalive for a boot-running timer; this is not runtime watchdog evidence. Keep bark, USB host/VBUS/Type-C/charging, and storage conclusions separate. |
| 0086 | MT6797 I2C controller-data match | Reuse the existing `mt8173_compat` data for a direct `mediatek,mt6797-i2c` match; the patch changes exactly one match-table line and does not add a Gemini-specific driver ABI | Candidate W's two clean kernel packages match after normalizing only `generated_utc`, two final assemblies are recursively identical, and all 24 mutation cases pass. Exact V's DTB, AW9523/matrix policy, no-IRQ watchdog, and ramoops are retained. In one exact W run, `0-005b` bound `aw9523-pinctrl`, `keyboard-matrix` bound and exposed `/dev/input/event0`, and press/release records survived for H, E, L, P, and Enter. The owner observed a visible shell, working keyboard, and approved font. This is one limited-key run, not repeatability or full key coverage. Z subsequently booted once with the keyboard still working and returned after its typed watchdog command; changed boot-ID and watchdog-reason evidence corroborate that return without adding individual-key coverage. | Preserve the controller, DTB, AW9523, matrix, keycodes, and font inputs. Close unchanged Z. Historical AA r0 was superseded before boot and must not be selected. AA r1 retains exact Z's kernel/DT/config, was built twice recursively identically, and replaced exact r0 on live-GPT `boot2` with a matching full readback and no install-time reboot. Attended attempt 1 then passed: pstore retained the exact Unicode/2,048-entry map gate plus AW9523/matrix/event0 identity and A/S press-release events, the owner reported the new map working, more than 123 seconds elapsed without automatic watchdog ownership, and typed watchdog recovery returned to Gemian. F1–F10 and Page Up/Page Down remain unconfirmed rather than failed; W's earlier H/E/L/P/Enter events and AA's A/S events still do not establish full coverage. |
| 0087 | MT6797 TOPRGU restart ordering | Make MediaTek watchdog restart priority per-SoC: MT6797 selects 255 so TOPRGU runs before ARM64 PSCI at 129; every other supported variant retains 128 | With `KBUILD_BUILD_VERSION=1` pinned, AB builds 3 and 4 reproduce all 221 non-dynamic package files and modes. Independent containers from those packages are recursively byte- and mode-exact, retain the hardware-passed AA r1 DTB/keymap, pass 32/32 LK gates and 25/25 focused mutations, and contain no userspace watchdog or automatic reboot. Exact padded AB was installed and fully read back from live-GPT logical `boot2`. In attended attempt 1 the exact marker, map gate, and `GEMINI-AB#` prompt survived; the keyboard worked, 45 seconds of idle caused no reset or countdown, and typed bare `reboot` reset immediately by owner observation. Pstore places the request at 66.021584 seconds and the final kernel restart line at 66.049438 seconds. Gemian returned under a changed boot ID. | Treat kernel restart as one local hardware pass on the named unit. The 27.854 ms retained-log interval is not instrumented Enter-to-LK timing, and watchdog-class boot-reason fields do not distinguish the reset mechanism. Preserve the MT6797-only priority scope and require repeat/integration evidence before claiming universal reliability. F1–F10 and Page Up/Page Down remain unconfirmed. |

Candidate V now carries the 0077--0085 path on exact P's final DT foundation,
including the no-IRQ watchdog and ramoops recovery contract. Its two fresh
kernel builds, two complete candidate assemblies, focused schemas, component
validators, and 24 negative mutation rejections passed. Attempt 1 selected V
from `boot2`, displayed the loader-retained console, and returned automatically.
Exact retained markers prove kernel/initramfs entry and the `mtk-wdt`
open/one-ping path through its 30-second wait. AW9523 transport at adapter 0,
address `0x5b`, repeatedly timed out with `-110`, including its reset retry;
the AW9523 and matrix drivers remained unbound and no event node existed. The
keyboard failure is therefore before matrix polling/input at the
controller-to-provider boundary, while the no-IRQ watchdog and visible fbcon
paths each passed once. Exact working-3.18 disassembly subsequently showed
unconditional hardware WRRD and auxiliary receive-length offset `0x6c` for the
same AW9523 read shape. V instead falls through to `mt6577_compat`, suppressing
WRRD and omitting that auxiliary-length contract; latest bsg100 independently
fixed the same cross-device failure with a direct MT6797-to-MT8173 controller
match.

Candidate W tested that controller correction without changing V's hardware
description: patch 0086 adds only
`{ .compatible = "mediatek,mt6797-i2c", .data = &mt8173_compat },`. It retains
V's exact final DTB, AW9523/reset/cache/matrix state, no-IRQ watchdog, and
ramoops. Its independent observation changes keep the forced kernel console on
tty2, respawn an unobscured foreground shell on tty1, and select the larger
`TER16x32` font. The latest checked `bsg100/gemini-linux` `main` reference is
[`60f5f4ac777a0aeccc89b5d3a4f8cd1f1ebe57b3`](https://github.com/bsg100/gemini-linux/commit/60f5f4ac777a0aeccc89b5d3a4f8cd1f1ebe57b3).
Two clean W kernel packages reproduced all non-timestamp content, two final
candidate assemblies matched recursively, and the 24-case mutation suite
passed 24/24. The calibrated 6,866,944-byte container's raw image SHA-256 is
`34c41fad1e86de05b6a1f64f7e5d9229bd26ea88d982b0a57f2b9573aeb782d4`
and the initramfs SHA-256 is
`3793bec7a63074b237d041bcd42e6edfccc80f0a3d7b19869abf99ee7874dac6`.
The exported `rebuild4` artifact was installed without reboot to live-resolved
logical `boot2`; its padded image, remote post-flush checksum, and full local
readback match SHA-256
`0ff3220096aa53f792116b3899e356bc2516816c9c330309c3d81e9fe1446608`.
The owner selected exact W once. Retained `console-ramoops` contains the exact
W marker, a successful `0-005b` probe and `aw9523-pinctrl` bind, the subsequent
`matrix-keypad` bind, exact `/dev/input/event0`, and press/release records for
H, E, L, P, and Enter. The owner observed the shell and working keyboard and
reported the `TER16x32` font as perfect. W's intended tty2/tty1 split failed:
kernel logs were visibly mixed with the shell. Its exact watchdog open, one
ping, waits through 30 seconds, owner-observed automatic return, and Gemian
`wdt_by_pass_pwk` reason establish the deliberate timeout recovery. No `pass`
marker or durable shell-command result exists, and one run does not establish
all keys or repeatability.

Candidate X is the serviceability derivative. Its hypothesis is
that removing only W's virtual-console command-line token, retaining serial
plus `/dev/kmsg`/ramoops logging, and omitting all userspace watchdog ownership
will leave tty1 clean and available until the owner types `reboot`. It retains
W's keyboard/controller result and final DTB byte for byte. Two clean packages
reproduced all 220 non-timestamp files, two complete X assemblies are
recursively identical, all 32 LK gates passed, and all 47 negative mutations
were rejected. The 6,864,896-byte raw image SHA-256 is
`bf4003871daaba1faa293f2b128021d3a67d41ebf3ddff1c42463409803b9296`;
the initramfs SHA-256 is
`b54ce3cd75e7947ed867165e31abbf6ee6cbac7d41d171435f99bba7825bc769`.
The guarded installer preserved exact W, live-resolved `boot2` as
`/dev/mmcblk0p30` while root was `/dev/mmcblk0p29`, and produced a synchronized,
flushed, full readback matching padded SHA-256
`e89d71f15465b544db163b5f0b90b456e913c38ba4d2ed49aa7bde345148c855`.
It did not reboot the device and the boot ID remained unchanged.

The owner later reported that X booted and worked, then appeared to hang after
typing `reboot`. No automatic return occurred; power-key recovery returned to
Gemian and pstore was empty. That passes only boot and pre-reboot interaction at
owner-report level. It does not establish clean tty1, an exact X marker, X
uptime, individual keyboard subgates, wrapper/syscall entry, or the internal
restart failure stage.

Candidate Y was reproducibly built and fully read back, but an exact BusyBox
audit rejected it before boot: bare `reboot` selects BusyBox's internal applet
instead of Y's external wrapper, and its watchdog-open failure cannot reach the
promised refusal branch. Y was never selected and has no runtime evidence.

Candidate Z is the hardware-tested keyboard/recovery artifact inherited by AA r1. It retains exact
Y's kernel, DTB, and configuration and changes four initramfs members plus adds
read-only `bin/reboot-dispatch.env`. Two complete builds match recursively, the
exact-BusyBox dispatch gate passed on Linux arm64, 32/32 LK gates and 75/75
mutation rejections passed, and its 6,866,944-byte raw SHA-256 is
`985a6472b7fdbfd4c58da4773a8c2cae1e3aa40ea90240eb2b309390ed7674b9`.
The full installation-time logical-`boot2` readback matches padded SHA-256
`ba21e6424f94c82f14fd51b5681eea68d6cf09e9177e4f9ca2061c9f129abb40`.
The owner later selected Z once, reported a successful boot with the keyboard
still working, typed its watchdog reboot, and observed the automatic return to
Gemian. A changed post-return boot ID and
`androidboot.bootreason=wdt_by_pass_pwk` corroborate a watchdog-class reset.
No exact Z text, dispatch/preflight trace, countdown timing, or individual-key
record survived, so Z added no detailed event coverage beyond W and its
internal subgates and repeatability remain unproved. AA r1 later retained A/S
press-release events in addition to W's H/E/L/P/Enter set.

Candidate AA r0 is historical. It was built, validated, installed, and fully
read back, but was superseded before selection because its map omitted the
Shift+Fn F1–F10 layer and its `dumpkmap` byte comparison was not a valid live
oracle. Do not boot it. Its immutable raw boot-image SHA-256 remains
`a2ad7a4107abd99cbd349b8f2deadd0185cbdd5bb0884ecbdae8ff2a7499ed4c`.
Its exact padded logical-`boot2` image and full readback remain SHA-256
`157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa`
and supply no hardware evidence.

Candidate AA r1 retains exact Z's kernel field, final DTB, configuration,
AW9523/matrix path, font, dispatch, and typed-watchdog recovery. It was built
twice with recursively identical bytes and metadata. The recovery-VM canonical
static AArch64 verifier is SHA-256
`29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238`;
the 7,378,944-byte raw artifact is SHA-256
`37e82bf3be87dd9e52fb8d60597b69f92a5c0dc5aebd51d178f1e7efd33343d7`.
Its 2,311-byte, eight-table VT map has SHA-256
`02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c`
and exactly 53 audited semantic changes. The policy covers photographed
printable/navigation legends, Fn+period U+263A, Shift+Fn F1–F10, the physical
backslash key's Ctrl/Alt semantics, and modifier press/release safety. Media,
brightness, phone, airplane, launcher, and voice functions remain userspace
policy. Its respawn-safe oracle sets Unicode mode, verifies an already exact
map or performs preflight before load, then reads all 2,048 planned-table
entries through `KDGKBENT`. It requires the untouched upper halves to be
`K_HOLE`, accounts for table 3's valid payload-entry-0 `K_HOLE` becoming kernel
`K_ALLOCATED`, and requires every undeclared table to remain absent. The
guarded installer required historical r0 padded predecessor
`157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa`,
resolved live-GPT `boot2` as `/dev/mmcblk0p30` with active root on
`/dev/mmcblk0p29`, preserved a private full backup, and wrote, flushed, and
fully read back padded AA r1 as SHA-256
`38b49c7c19c2d97fa0c48436545219489221aa367aedf491ae6ebd4ec4856703`.
The installation did not reboot.

Attended attempt 1 passed the isolated map gate. Retained pstore records
`origin=loaded-now` at 2.407618 seconds, tty1 `K_UNICODE`, exact readback of all
2,048 planned-table entries, high-half holes, every undeclared table absent,
table 3 allocated, `GEMINI-AA-R1#`, and validated reboot dispatch. The owner
reported that AA r1 booted and the new keymap worked; the same retained record
contains exact AW9523/matrix/event0 identity and A/S press-release events. Bare `reboot` was not
requested until 126.258967 seconds, proving more than 123 seconds without an
automatic watchdog owner; it then opened and pinged the 31-second watchdog
once, retained fd 3, and logged each five-second countdown checkpoint through
30 seconds. The changed post-return boot ID plus `boot_reason=4`,
`androidboot.bootreason=wdt_by_pass_pwk`, and `powerup_reason=reboot`
corroborate recovery. F1–F10 and Page Up/Page Down remain unconfirmed—not
failed—because the console supplied no visible discriminator. The private
capture manifest is SHA-256
`d18eff262b66af21ee5cd61b05fd2f25b8b107187564774001f09ae3d9765a6a`.

Candidate AB passed one attended local hardware test. Patch 0087 selects
restart priority 255 for MT6797 TOPRGU, ahead of ARM64 PSCI priority 129, while
retaining priority 128 for every other supported MediaTek watchdog variant.
After `KBUILD_BUILD_VERSION=1` was pinned, builds 3 and 4 reproduced all 221
non-dynamic package files and modes; their timestamp-normalized provenance is
exact. Independent AB containers derived from those packages and the exact
hardware-passed AA r1 artifact are recursively byte- and mode-identical. The
7,378,944-byte boot image has SHA-256
`61c74592267466735164c19f8b831ea18db2892de95e32109f2aacd7ec5c5446`;
it retains final DTB SHA-256
`bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f`
and map SHA-256
`02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c`.
Both builds passed all 32 LK gates, and the shared validator rejected all 25
focused mutations. Its four audited initramfs substitutions remove the
inherited watchdog open/ping/countdown/fallback path and issue one forced
no-sync BusyBox reboot request only after an owner types bare `reboot`.

The guarded installer required exact padded AA r1 SHA-256
`38b49c7c19c2d97fa0c48436545219489221aa367aedf491ae6ebd4ec4856703`,
resolved inactive live-GPT logical `boot2` as `/dev/mmcblk0p30` with active root
on `/dev/mmcblk0p29`, preserved a full backup, performed one exact write, then
flushed and fully read back padded AB as SHA-256
`b58c0347d34a3fd9031c74cb03447dd7a6fc630d5b8ea2b7eabc36827e754350`.
The installation did not reboot or change boot ID
`0f8def4f-3f94-4c57-a34c-2bb37315b19f`. Attended attempt 1 later retained the
exact `GEMINI_MT6797_KERNEL_RESTART_20260720_AB` marker, exact console-map gate,
and `GEMINI-AB#` prompt, and the owner confirmed the keyboard worked. The owner
waited 45 seconds with no automatic reset or countdown, typed bare `reboot`,
and observed an immediate reset. Pstore records the manual request at
66.021584 seconds and the final kernel `reboot: Restarting system` line at
66.049438 seconds, 27.854 ms later. That is a retained request-to-final-log
interval, not an instrumented Enter-to-LK measurement. Gemian returned with
boot ID `e33a0d8e-0354-4c8c-95b3-07c6970152ec`, changed from
`0f8def4f-3f94-4c57-a34c-2bb37315b19f`. The post-return `boot_reason=4`,
`androidboot.bootreason=wdt_by_pass_pwk`, and `powerup_reason=reboot` remain a
nondiscriminating watchdog-class reason; prompt command timing plus the audited
absence of userspace watchdog ownership support kernel TOPRGU SWRST. This
promotes restart to one pass on the named local unit, not repeatability or
universal reliability. F1–F10 and Page Up/Page Down remain unconfirmed, not
failed.

The [current driver-coverage audit](../experiments/2026-07-13-driver-coverage-audit/results/driver-coverage-current-77-package-20260714.txt), [first-boot dependency audit](../experiments/2026-07-14-first-boot-probe-audit/results/first-boot-probe-audit-current-77-package-20260714.txt), [77-patch package validation](../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-77-package-20260714.txt), [USB diagnostic experiment](../experiments/2026-07-16-usb-gadget-diagnostic/README.md), [broad unused-clock diagnostic](../experiments/2026-07-17-clk-ignore-unused-diagnostic/README.md), [cancelled newline-boundary diagnostic](../experiments/2026-07-17-fbcon-newline-boundary-diagnostic/README.md), and [UART/pstore observability experiment](../experiments/2026-07-17-uart-pstore-observability/README.md) provide the corresponding evidence boundaries. The older subsystem records remain content audits where later patches do not touch their inputs. This table is a design map, not a claim that any disabled, module-only, or diagnostic path works on hardware.
Candidate J's partition operation is separately recorded in its
[full write/readback result](../experiments/2026-07-17-clk-ignore-unused-diagnostic/results/boot2-write-candidate-j-20260717.txt).
Its attended observations are recorded in the
[Candidate J first runtime result](../experiments/2026-07-17-clk-ignore-unused-diagnostic/results/runtime-candidate-j-attempt-1-20260717.txt)
and [repeat report](../experiments/2026-07-17-clk-ignore-unused-diagnostic/results/runtime-candidate-j-repeat-report-20260717.txt).
Candidate K's synchronization is recorded in its
[full write/readback result](../experiments/2026-07-17-fbcon-newline-boundary-diagnostic/results/boot2-write-candidate-k-20260717.txt);
it was not runtime-tested and is superseded by Candidate L.
Candidate L's final software identity is recorded in its
[independent reproduction result](../experiments/2026-07-17-uart-pstore-observability/results/final-build-reproduction-20260717.txt),
and its partition operation is separately recorded in its
[full write/readback result](../experiments/2026-07-17-uart-pstore-observability/results/boot2-write-candidate-l-20260717.txt).
Its first unattributable observation is recorded in
[attempt 1](../experiments/2026-07-17-uart-pstore-observability/results/runtime-candidate-l-attempt-1-20260718.txt),
and the strongly attributed initramfs/watchdog-discovery boundary is recorded
in [attempt 2](../experiments/2026-07-17-uart-pstore-observability/results/runtime-candidate-l-attempt-2-20260718.txt).
The exact interrupt hierarchy and Candidate M discriminator are recorded in
the [watchdog registration audit](../experiments/2026-07-17-uart-pstore-observability/results/watchdog-registration-audit-20260718.txt),
and its successful runtime outcome is recorded in the
[Candidate M runtime record](../experiments/2026-07-18-watchdog-registration-diagnostic/results/runtime-candidate-m-attempt-1-20260718.txt).
Candidate N retains that exact kernel, configuration, no-IRQ DTB, and LK
container and changes only external `/init` to request CPU1 online after arming
the proven watchdog. Its two builds are byte-identical, and its exact padded
image was synchronized, flushed, and fully read back from logical `boot2`.
Its one retained runtime record then proves that the standard ARM64 hotplug
request returned, logical CPU1 mapped to DT `cpu@1`, initialized its GICv3
redistributor, booted as MPIDR `0x1` / Cortex-A53, entered online mask `0-1`,
and advanced its accounting. It remained online through the last 25-second
marker before the watchdog returned the device to Gemian automatically. This
promotes only the first secondary Cortex-A53 path in one run; every other core
and broader SMP behavior were untested by N. Candidate O applied the changed
sequential A53 gate with a durable execution checkpoint and fail-stop after
each core while keeping the Cortex-A72 pair separate.
See the [Candidate N build record](../experiments/2026-07-18-cpu1-online-diagnostic/results/final-build-reproduction-20260718.txt)
[write/readback](../experiments/2026-07-18-cpu1-online-diagnostic/results/boot2-write-candidate-n-20260718.txt),
and [runtime result](../experiments/2026-07-18-cpu1-online-diagnostic/results/runtime-candidate-n-attempt-1-20260718.txt).

Candidate O is now the hardware-proven diagnostic layer over that foundation.
It reused the exact N kernel, embedded configuration, DTB, and LK container and
changed only external `/init`. In its one retained run, every live logical
CPU1–9 `of_node` mapping matched the expected DT node. Standard hotplug requests
then brought the complete Cortex-A53 CPU1–7 set online sequentially: each
request returned success, emitted its GICv3/MPIDR boot line, advanced its
`/proc/stat` accounting, and left a durable cumulative checkpoint through
`online=0-7`. CPU8/9 mapped to the Cortex-A72 nodes, remained offline, and were
not written. The final success marker and two subsequent wait markers survived
the automatic watchdog recovery. This establishes the eight Cortex-A53 online
paths only for one hotplug run. It does not establish repeatability, boot-time
SMP, stress, coherency, DVFS, idle states, thermal behavior, or either
Cortex-A72 online path.

Candidate P is now the hardware-passed rotation layer over O. It rebuilds from
the exact O baseline with exactly two resolved configuration changes:
`# CONFIG_FRAMEBUFFER_CONSOLE_ROTATION is not set` becomes
`CONFIG_FRAMEBUFFER_CONSOLE_ROTATION=y`, and forced `CONFIG_CMDLINE` gains only
`fbcon=rotate:3`. Independent VM builds reproduced the substantive package and
candidate outputs. The exported raw image SHA-256 is
`d192dac9e4516eac9319da2a885abaf3203da6c357c574e7f1f6deef2208d341`;
the synchronized, block-flushed, padded logical-`boot2` target and full
readback SHA-256 is
`cea00d591e74a29d74200f4d292a92aaca2f890bd965af37a7673ab906f4afbc`.
On its one attributable selection, the owner observed readable console text in
normal-landscape orientation, the complete inherited O sweep, and an
unassisted return to Gemian. Post-return `console-ramoops` retains the exact O
marker, every CPU1–7 pass/accounting checkpoint, final `online=0-7` with
CPU8/9 offline, and both watchdog waits. Collection began after return, so it
did not measure the tested boot-ID transition or independently capture the
reset reason. This establishes one loader-retained simplefb/fbcon rotation
run, not repeatability or native DRM, panel, or backlight ownership. Do not
repeat unchanged P.

Candidate Q implemented the combined AW9523 keyboard and local-shell gate on
top of P's console inputs. Its kernel, DTB, helper, initramfs, and Android-v0
image were independently reproduced and the exact padded image was fully read
back from logical `boot2`. On the intended selection, however, the owner did
not get a working text console and could not observe any deeper gate. No Q
marker or pstore record survived. This is a rejected, non-diagnostic runtime
candidate: it establishes neither kernel/`/init` entry nor an AW9523, input,
TTY, or shell result. Static review additionally found that Q's parent
interrupt cell named raw line 87, whereas the recovered MT6797 map assigns
GPIO87 to EINT10. The encoding defect is actionable but is not proven causal.

Do not repeat Q unchanged. Candidate U used the next available identifier
because R was retired without implementation and S/T remain the separate eMMC
and USB networking gates. U was independently built twice with matching
validated kernel, DTB, initramfs, and Android-v0 outputs, then installed to the
live-resolved logical `boot2` with a matching full-partition readback. Its first
intended selection produced a black screen and dark console with no visible
marker or automatic reboot. The device later returned to Gemian with a changed
boot ID, but authenticated pstore was empty. U therefore establishes no kernel,
`/init`, console, AW9523, keyboard, or shell gate. A later artifact audit found
that its final DTB came from the kernel package rather than exact P. U therefore
omitted P's loader-framebuffer, no-IRQ watchdog, and other LK-aligned fixups;
that explains why it did not carry P's configured console path, but does not
prove the cause of the black screen. U retains the upstream AW9523 driver and
its active-high reset description and removes the AW9523 parent-interrupt
hierarchy from the active diagnostic DTB while retaining the GPIO87/EINT10
pinmux state with no active consumer. Patch 0085 first corrects the reusable
disabled board description from EINT87 to EINT10. Patch 0083 stages the binding
and patch 0084 stages the generic `gpio-matrix-keypad` polling implementation
adapted to Linux 7.1.3 rather than copying a separate silicon driver. U's
candidate-only DT polls every 20 ms with a 2 us column-scan delay and omits
`debounce-delay-ms`: the existing debounce delay schedules IRQ-triggered scans
and is runtime-inert on the continuous polling path, so U has no separate
polling debounce. That design choice is justified by
bsg100's hardware-tested
[typing](https://github.com/bsg100/gemini-linux/commit/6bd4d572670698f80ca08ad083657621b62cc8f3)
and [coexistence](https://github.com/bsg100/gemini-linux/commit/aff681d3c727137c4016376e12055d380867f5c3)
results. Its supervised shell must start independently of the bounded event
capture. U is CPU0-only by configuration and its initramfs omits userspace
watchdog access. The pinned Linux 7.1.3 watchdog-policy audit confirms that
`WATCHDOG_HANDLE_BOOT_ENABLED` keeps a boot-running timer alive before
userspace takeover; this is static policy evidence, not a claim about U's
runtime watchdog behavior. CPU hotplug, storage, network configuration, raw
I2C/memory access, native display work, and deliberate normal-path reset remain
excluded.

Candidate V corrects U's packaging foundation without rewriting its failed
runtime record. V starts from exact P's hardware-passed final DTB, permits only
the parsed keyboard-resource/polling transform, pins the corrected polling
implementation, and restores P's no-IRQ watchdog plus durable ramoops channel.
Its shell, no-grab event capture, and exact-device watchdog owner are
independent initramfs tasks. Two fresh kernel builds reproduced the selected
non-timestamp package content and two V builds were recursively identical; all
24 mutation cases were rejected. The raw image SHA-256 is
`9ef0ee8dc1eb49752f9cf8f60b247b9b85e4fd2a9f090473f1d91848114087b0`.
It is installed and fully read back from live-resolved logical `boot2` as exact
padded SHA-256
`57d362a86fae38c0ec2cec909ef6ae8d8ad124b87abb2ee58d179184c1f19168`,
with no installation-time reboot. Attempt 1 reached exact V markers on a
visible console and returned through the 31-second no-IRQ watchdog path.
Retained `console-ramoops` includes `tty1_shell=ready`, but that marker is
emitted immediately before the shell `exec`: it proves neither `ash` exec nor
prompt visibility/interactivity. The owner had no usable shell or keyboard
test opportunity. Because all probe/watchdog markers also target tty1, they can
bury a prompt; moreover, V's own matrix keymap has neither `KEY_SLASH` nor
`KEY_MINUS`, so its advertised `/bin/v-pass` command is not normally typeable
from that keyboard. AW9523 probe repeatedly returned `-110`/`ETIMEDOUT` at I2C
adapter 0 address `0x5b`, including the reset retry, leaving AW9523 and the
matrix unbound with no input event. Do not repeat unchanged V. The next causal
change is a direct `mediatek,mt6797-i2c` match using the evidence-backed
`mt8173_compat` data while AW9523 reset/cache and matrix polling stay fixed.
Foreground-tty and `TER16x32` changes are independent observation improvements.

Retained pstore first showed that the existing T-PHY/MTU3/`g_ether` path
reaches the driver's gadget pull-up log. Candidate AC then established exact
host enumeration, a fixed-MAC interface, carrier, static-address ping, TCP
marker, and bounded shell on a direct no-bridge link; exact AH attempt 2
independently retained that service under the AF-kernel/AD-board split. Host
mode, VBUS, Type-C policy, role switching, charging, physical-port mapping,
and an electrical D+ waveform remain open. See the
[Candidate AC experiment](../experiments/2026-07-21-usb-gadget-ethernet/README.md),
[AH attempt-2 result](../experiments/2026-07-22-ad-contract-af-kernel-split/results/runtime-candidate-ah-attempt-2-20260722.txt),
[Candidate O experiment](../experiments/2026-07-18-cortex-a53-sweep-diagnostic/README.md),
[Candidate O runtime result](../experiments/2026-07-18-cortex-a53-sweep-diagnostic/results/runtime-candidate-o-attempt-1-20260718.txt),
[Candidate P experiment](../experiments/2026-07-18-fbcon-rotation-diagnostic/README.md),
[Candidate P runtime result](../experiments/2026-07-18-fbcon-rotation-diagnostic/results/runtime-candidate-p-attempt-1-20260718.txt),
[Candidate P build reproduction](../experiments/2026-07-18-fbcon-rotation-diagnostic/results/final-build-reproduction-20260718.txt),
[Candidate P write/readback](../experiments/2026-07-18-fbcon-rotation-diagnostic/results/boot2-write-candidate-p-20260718.txt),
[Candidate Q experiment](../experiments/2026-07-18-keyboard-shell-diagnostic/README.md),
[Candidate Q runtime result](../experiments/2026-07-18-keyboard-shell-diagnostic/results/runtime-candidate-q-attempt-1-20260719.txt),
[Candidate U experiment](../experiments/2026-07-19-keyboard-polling-diagnostic/README.md),
[Candidate U build reproduction](../experiments/2026-07-19-keyboard-polling-diagnostic/results/final-build-reproduction-20260719.txt),
[Candidate U write/readback](../experiments/2026-07-19-keyboard-polling-diagnostic/results/boot2-write-candidate-u-20260719.txt),
[Candidate U runtime result](../experiments/2026-07-19-keyboard-polling-diagnostic/results/runtime-candidate-u-attempt-1-20260719.txt),
[Candidate V experiment](../experiments/2026-07-19-keyboard-watchdog-diagnostic/README.md),
[Candidate V build reproduction](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/final-build-reproduction-20260719.txt),
[Candidate V write/readback](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/boot2-write-candidate-v-20260719.txt),
[Candidate V runtime result](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/runtime-candidate-v-attempt-1-20260719.txt),
[working 3.18 AW9523/I2C audit](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/working-3.18-aw9523-i2c-binary-audit-20260719.txt),
[Candidate W MT6797 I2C WRRD diagnostic](../experiments/2026-07-19-keyboard-wrrd-diagnostic/README.md),
[Candidate W build reproduction](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/final-build-reproduction-20260719.txt),
[Candidate W mutation result](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/validator-mutations-20260719.txt),
[Candidate W write/readback](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/boot2-write-candidate-w-20260719.txt),
[Candidate W runtime](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/runtime-candidate-w-attempt-1-20260719.txt),
[Candidate X experiment](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/README.md),
[Candidate X build reproduction](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/final-build-reproduction-20260719.txt),
[Candidate X mutation result](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/validator-mutations-20260719.txt),
[Candidate X write/readback](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/boot2-write-candidate-x-20260719.txt),
[Candidate X runtime](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/runtime-candidate-x-attempt-1-20260719.txt),
[Candidate Y experiment](../experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/README.md),
[Candidate Y build reproduction](../experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/results/final-build-reproduction-20260720.txt),
[Candidate Y restart audit](../experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/results/restart-path-audit-20260720.txt),
[Candidate Y mutation result](../experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/results/validator-mutations-20260720.txt),
[Candidate Y write/readback](../experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/results/boot2-write-candidate-y-20260720.txt),
[Candidate Y command-dispatch rejection](../experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/results/preboot-command-dispatch-audit-20260720.txt),
[Candidate Z experiment](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/README.md),
[Candidate Z build validation](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/build-validation-20260720.txt),
[Candidate Z dispatch validation](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/ash-dispatch-validation-20260720.txt),
[Candidate Z mutation result](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/validator-mutations-20260720.txt),
[Candidate Z write/readback](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/boot2-write-candidate-z-20260720.txt),
[Candidate Z runtime](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/runtime-candidate-z-attempt-1-20260720.txt),
[Candidate AA r0/r1 experiment](../experiments/2026-07-20-keyboard-console-map-diagnostic/README.md),
[historical Candidate AA r0 build validation](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/build-validation-20260720.txt),
[historical Candidate AA r0 write/readback](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/boot2-write-candidate-aa-20260720.txt),
[Candidate AA r1 build validation](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/build-validation-aa-r1-20260721.txt),
[Candidate AA r1 installer validation](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/installer-validation-aa-r1-20260721.txt),
[Candidate AA r1 write/readback](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/boot2-write-candidate-aa-r1-20260721.txt),
[Candidate AA r1 layout reference](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/layout-reference-aa-r1-20260721.txt),
[Candidate AA r1 runtime](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/runtime-candidate-aa-r1-attempt-1-20260721.txt),
[Candidate AB experiment](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/README.md),
[Candidate AB first-package validation](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/kernel-build1-validation-20260720.txt),
[Candidate AB kernel reproducibility](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/kernel-reproducibility-ab-20260721.txt),
[Candidate AB container validation](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/container-validation-ab-20260721.txt),
[Candidate AB installer validation](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/installer-validation-ab-20260721.txt),
[Candidate AB write/readback](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/boot2-write-candidate-ab-20260721.txt),
[Candidate AB runtime](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/runtime-candidate-ab-attempt-1-20260721.txt),
[staged roadmap](ROADMAP.md#immediate-priority-aa-r1-console-map-and-ab-kernel-restart-passed-2026-07-21),
and [sanitized USB evidence](../experiments/2026-07-16-usb-gadget-diagnostic/results/retained-pstore-mtu3-gadget-evidence-20260718.txt).

## Decision records

Material decisions belong in issues labeled `type: decision`. A decision must state context, options considered, safety impact, upstream impact, and reversal conditions. This prevents repository-local convention from silently becoming a new downstream ABI.
