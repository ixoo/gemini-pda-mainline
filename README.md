# Gemini PDA Mainline

Upstream-first Linux enablement for the Planet Computers Gemini PDA.

> [!WARNING]
> This is an early hardware-enablement project, not a custom ROM or a daily-driver image. An incorrect image, partition write, clock, regulator, or memory-map change can corrupt data or damage hardware. Preserve a known-good recovery path, back up device-specific data, and never experiment on the preloader, NVRAM, or partition table.

## Mission

Make the Gemini PDA a first-class mainline Linux device: bootable with an ordinary upstream-derived arm64 kernel, described by upstream Device Tree, usable with standard Linux subsystems, and maintainable without a permanent vendor-kernel fork.

The desired end state is distribution-owned kernel updates, not a repository-owned ROM:

```text
MediaTek BootROM
  -> retained low-level firmware while bring-up is in progress
  -> maintained bootloader or chainloader
  -> standard Linux Image + upstream DTB + initramfs
  -> Debian, Alpine, postmarketOS, or another ordinary distribution
```

## What this repository is

This repository is the coordination and reproducibility layer for:

- hardware archaeology backed by evidence;
- a safe, repeatable mainline boot loop;
- temporary, reviewable patch series on current upstream Linux;
- test logs and hardware-support tracking;
- upstream submission state across Linux, Device Tree bindings, bootloaders, and userspace;
- cross-project coordination.

It is intentionally **not** a long-lived Linux source fork. Generic support belongs in the relevant upstream subsystem; Gemini-specific description belongs in an upstream board Device Tree.

## Current status

The project is at **M0: safe reproducible lab**.

- Current upstream Linux contains a skeletal MT6797 SoC description, but no upstream Gemini PDA board Device Tree.
- Historical work in [`Jasu/gemini-pda-buildroot`](https://github.com/Jasu/gemini-pda-buildroot) reached BusyBox over UART. That result is valuable prior art, but must be reproduced against a current upstream kernel.
- [`bsg100/gemini-linux`](https://github.com/bsg100/gemini-linux) is an active modern bring-up effort with substantial hardware research. Coordination and reuse-by-reference come before parallel driver work.
- The historical broad Linux 7.1.3 77-patch package validates in the ARM64 VM. Its historical LK candidate was written and read back on non-primary `boot3`; a later framebuffer-console prototype was written and read back on `boot2` and `boot3`. Owner-reported boot attempts were inconclusive: the subsequent live snapshot showed the vendor 3.18 kernel, but neither the selected slot nor LK/Linux execution was established. Those images also predate the corrected modern arm64 placement at `0x40200000` and must not be reused. These writes and attempts are evidence, not a mainline boot result. See the [77-patch boot3 write](experiments/2026-07-15-boot3-mainline-write/README.md), [prototype boot2 write](experiments/2026-07-15-display-console-write-boot2/README.md), [prototype boot3 write](experiments/2026-07-15-display-console-write/README.md), and [runtime snapshot](experiments/2026-07-15-display-console-recovery/results/runtime-boot-attempt-20260715.txt).
- A new Linux 7.1.3 `handoff` profile produces one-CPU, storage-inert LK candidates with the corrected address and packaging-only LK DT compatibility properties. The display candidate was selected from `boot2` with the silver button for one controlled attempt. The owner observed no serial output, a dark screen, no interaction, and no boot loop. A post-test audit found that this historical initramfs could not create the device nodes needed for its marker, so marker absence is non-evidence. The non-looping behavior differs from earlier attempts, but it does not prove that Linux or `/init` ran; runtime remains unknown. See the [current handoff experiment](experiments/2026-07-16-lk-handoff-alignment/README.md) and [prioritized test plan](docs/ROADMAP.md#immediate-priority-first-attributable-linux-713-handoff-2026-07-17).
- Patches 0077–0078 and the [USB gadget diagnostic](experiments/2026-07-16-usb-gadget-diagnostic/README.md) add a peripheral-mode MTU3/T-PHY test path. Its early exact candidate was tested from non-primary `boot2`; two bounded host checks found no USB child while kernel execution was unconfirmed. Later M/N retained pstore proves that the inherited T-PHY and MTU3 probes returned successfully, the forced B-device session ran, built-in `g_ether` became ready, and MTU3 logged its gadget pull-up action; electrical D+ state, host enumeration, networking, and a remote shell remain unproven. See the [sanitized retained-pstore result](experiments/2026-07-16-usb-gadget-diagnostic/results/retained-pstore-mtu3-gadget-evidence-20260718.txt). This makes no host-mode, VBUS, Type-C policy, or charging claim.
- The [deterministic screen-marker candidate](experiments/2026-07-16-screen-marker-diagnostic/README.md) was written, flushed, and fully read back from non-primary `boot2`. On its first owner-run boot, the display was black and none of the expected white/dark bands appeared. That fails the positive screen test but does not establish kernel failure: kernel entry, simplefb binding, the bounded framebuffer write, and retention of LK's scanout state remain indistinguishable without an independent signal.
- A focused review of [bsg100's working native-fbcon commit](experiments/2026-07-13-bsg100-gemini-linux-comparison/results/fbcon-commit-035d4b0-20260716.md) supplied the targeted clock-retention evidence used by Candidates F–H and a staged native-DRM port. Its generic MT6797 handoff/PHY findings are useful evidence; its SSD2092 panel data is not assumed to match this unit.
- [Candidate F](experiments/2026-07-16-screen-clock-retention-diagnostic/README.md) implements that one-property test while retaining Candidate E's exact kernel, initramfs and marker. On its first owner-attended boot, sideways console text was visibly scrolling for about one second before the display became black. This is the first positive visual Linux 7.1.3 handoff signal and strongly supports simplefb/fbcon output; the unread text does not independently prove `/init`.
- [Candidate G](experiments/2026-07-16-fbcon-text-diagnostic/README.md) is the controlled follow-up: the exact F kernel and DTB, with only the initramfs changed to remove every raw framebuffer access and hold a distinctive console banner. Its attended boot reproduced sideways scrolling for 1–2 seconds before black with the backlight apparently off, rejecting the raw-write explanation while leaving `/init` unconfirmed.
- [Candidate H](experiments/2026-07-16-simplefb-mm-root-retention/README.md) preserves G's exact kernel and initramfs and appends only `CLK_TOP_MUX_MM` to the simplefb clock references. In one owner-attended series, two attempts visibly progressed farther before black while later attempts did not reproduce it. The owner approximately recognized H's initramfs-only marker; the backlight stayed on while text was visible and went off at the black transition. This strongly attributes the visible execution to external `/init`, subject to the lack of an exact transcription or photograph, but H did not produce a stable console.
- [Candidate I](experiments/2026-07-16-fbcon-refresh-timing-diagnostic/README.md) keeps H's exact kernel and DTB and changes only initramfs `/init` to emit a unique marker and one tty0 line per second through `T+60`. The reported intended `boot2` selection went directly to black without its marker, a counter, or any other console text. The exact attempt count, backlight state, final state, and recovery action were not recorded. Candidate selection, `/init`, active refresh, and the static hold are therefore all unestablished; this is an inconclusive early-handoff observation, not a failed timing test.
- [Candidate J](experiments/2026-07-17-clk-ignore-unused-diagnostic/README.md) is the broad unused-clock diagnostic control. It rebuilds the kernel so its forced `CONFIG_CMDLINE` appends `clk_ignore_unused`; an Android-header-only draft was rejected as a runtime no-op because `CONFIG_CMDLINE_FORCE=y` replaces loader-provided bootargs. J keeps exact I's DTB, initramfs, and Android header command line while changing the kernel payload and payload-derived header fields. Its raw image SHA-256 is `6d5bad08c2f93eba7fbd66ea5c54de2437f81e44832426a97d4d65d550c659f4`. An isolated clean rebuild reproduced the config, kernel payload, `System.map`, all 119 DTBs, and the same boot image byte-for-byte; only timestamp-bearing `build.json` and its package checksum manifest differ. J was synchronized to logical `boot2`; its exact 16 MiB target and full readback matched SHA-256 `465e4c747138e12191d38fd6b4cde68cd0b9a19f918030dea05c9b8dbdd4d3fc`. The first intended selection reported `4/60` before black, strongly supporting Linux, fbcon/tty0, and shared `/init` through tick 04. A later two-bullet report is provisionally interpreted as two additional intended J/`boot2` selections because the outcomes are mutually exclusive, with owner confirmation pending: one reached "iteration 4" before black, compatible with and corroborating tick 04 without an exact marker transcription, while one went directly black with no console and cannot establish selected slot, kernel entry, or `/init`. Provisionally, two of three intended selections had tick-04-compatible visible output and one of three was no-console and unattributable. Stable visibility, clock causality, and any specific clock identity remain unestablished. Further J repetition is stopped. An initial reassessment produced Candidate K rather than a matched-I rollback; the later strategy review cancelled K without runtime. This option is a discriminator, not a proposed default: it does not enable already-off clocks, prevent explicit clock disables, or retain regulators or power domains. See the [write/readback](experiments/2026-07-17-clk-ignore-unused-diagnostic/results/boot2-write-candidate-j-20260717.txt), [first runtime](experiments/2026-07-17-clk-ignore-unused-diagnostic/results/runtime-candidate-j-attempt-1-20260717.txt), and [repeat report](experiments/2026-07-17-clk-ignore-unused-diagnostic/results/runtime-candidate-j-repeat-report-20260717.txt).
- [Candidate K](experiments/2026-07-17-fbcon-newline-boundary-diagnostic/README.md) was a reproducible exact-J, initramfs-only newline/scroll derivative. It was written and read back from `boot2`, but a strategy review cancelled it without a runtime selection: it has no kernel, DT, or configuration delta, and no result would change the next action.
- [Candidate L](experiments/2026-07-17-uart-pstore-observability/README.md) was the completed observability attempt. It added an evidence-backed UART0 GPIO97/98 pinmux correction, exact mainline-console alignment with the active Gemian kernel's primary `console-ramoops` zone, and MT6797 watchdog auto-restart plus IRQ-dependent dual-stage policy. A distinct fresh-source build reproduced all non-timestamp package and candidate content byte-for-byte; the final raw image is `5291832296106d36bc919671960b6150e530467057540a195bcf59e582ebb4c9`. It was written only to live-resolved logical `boot2`, synchronized, block-flushed, and fully read back as the exact padded SHA-256 `22d6ea23053514c4b5ad5cc2cf9ecb41fb800318533cbe94604302134e80daea`. Attempt 1 showed LK splash then black and was unattributable. Attempt 2 showed console output through exact suffix `remaining 5s`, unique to Candidate L's tracked `watchdog0=waiting` loop. This strongly supports kernel, loader-simplefb/fbcon, and `/init` entry, while establishing that `/dev/watchdog0` was still absent at that check. Connected serial was silent. The screen switched off, automatic return did not occur, and manual power recovery produced `power_key`/`keypad`, zero PMIC/AED watchdog indicators, and empty pstore. No watchdog open, bark, expiry, auto-return, UART function, ramoops retention, or native display support was established by L. Unchanged L repetition is stopped. A source audit rejected guessing a different IRQ polarity because MediaTek SYSIRQ translates the evidenced falling edge for the parent GIC; Candidate M subsequently tested the basic no-IRQ path. See the [reproduction](experiments/2026-07-17-uart-pstore-observability/results/final-build-reproduction-20260717.txt), [write/readback](experiments/2026-07-17-uart-pstore-observability/results/boot2-write-candidate-l-20260717.txt), [attempt 1](experiments/2026-07-17-uart-pstore-observability/results/runtime-candidate-l-attempt-1-20260718.txt), [attempt 2](experiments/2026-07-17-uart-pstore-observability/results/runtime-candidate-l-attempt-2-20260718.txt), and [registration audit](experiments/2026-07-17-uart-pstore-observability/results/watchdog-registration-audit-20260718.txt).
- [Candidate M](experiments/2026-07-18-watchdog-registration-diagnostic/README.md) passed its one controlled runtime test. It keeps Candidate L's exact Linux `Image.gz` and removes only the optional watchdog bark IRQ as its hardware hypothesis. The exact marker recovered from `console-ramoops` proves that the live DT omission survived LK, `10007000.watchdog` bound to `mtk-wdt`, `/dev/watchdog0` appeared, the 31-second timer was opened and pinged once, and execution reached `watchdog_wait=30s`. The console remained visibly active through the watchdog progress and the device returned to Gemian automatically. Gemian reported `wdt_by_pass_pwk`, `powerup_reason=reboot`, and both PMIC watchdog-reboot flags set. This establishes the basic no-IRQ TOPRGU timeout/reset path and cross-version mainline-to-Gemian console-ramoops retention for this revision, while strongly isolating Candidate L's optional IRQ-bearing path as the registration blocker. It does not establish bark/pretimeout, SPI137 polarity, native display, UART, SMP, or repeatability. Unchanged M repetition is stopped. See the [runtime evidence](experiments/2026-07-18-watchdog-registration-diagnostic/results/runtime-candidate-m-attempt-1-20260718.txt), [build reproduction](experiments/2026-07-18-watchdog-registration-diagnostic/results/final-build-reproduction-20260718.txt), and [write/readback](experiments/2026-07-18-watchdog-registration-diagnostic/results/boot2-write-candidate-m-20260718.txt).
- [Candidate N](experiments/2026-07-18-cpu1-online-diagnostic/README.md) passed its one recovery-backed CPU1 gate. It retains exact M's kernel, embedded configuration, no-IRQ DTB, pstore, fbcon, watchdog, and LK container, changing only external `/init`. Retained `console-ramoops` proves that the standard CPU-hotplug request returned success: logical CPU1 mapped to DT `cpu@1`, initialized its GICv3 redistributor, booted as MPIDR `0x1` / Cortex-A53, changed the online mask from `0` to `0-1`, and advanced its `/proc/stat` accounting. It remained online through the 25-second marker, after which the armed watchdog returned the device to Gemian automatically without owner help. This established only the first secondary Cortex-A53 in N's one run; all other cores, repeatability, boot-time SMP, stress, DVFS, idle, and thermal behavior were untested by N. Unchanged N repetition is stopped. Candidate O subsequently used the prescribed sequential checkpoints to test the remaining A53 path while keeping the A72 pair separate. See the [runtime evidence](experiments/2026-07-18-cpu1-online-diagnostic/results/runtime-candidate-n-attempt-1-20260718.txt), [build reproduction](experiments/2026-07-18-cpu1-online-diagnostic/results/final-build-reproduction-20260718.txt), and [write/readback](experiments/2026-07-18-cpu1-online-diagnostic/results/boot2-write-candidate-n-20260718.txt). A separate [audit of the exact captured LK](experiments/2026-07-12-boot-contract-recovery/results/lk-boot2-software-selection-audit-20260718.txt) found that the observed `boot2` path is hardware-key gated and found no direct Gemian-to-`boot2` destination in its audited paths, so the currently supported workflow still requires the silver button.
- [Candidate O](experiments/2026-07-18-cortex-a53-sweep-diagnostic/README.md) passed its first recovery-backed Cortex-A53 sweep. It retains exact N's kernel, configuration, DTB, watchdog, pstore, fbcon, and LK container, changing only external `/init`. The surviving exact-marker record proves that logical CPUs 1–7 mapped to the seven remaining Cortex-A53 nodes, each standard hotplug request returned success, every core initialized its GICv3 redistributor, booted with Cortex-A53 MIDR `0x410fd034`, advanced its own accounting, and reached its cumulative pass checkpoint. The final mask was `0-7`; CPUs 8–9 mapped to the Cortex-A72 nodes but remained offline and untouched. A cycle-aware collector observed disconnect and return to Gemian with a changed boot ID; a separate immediate sanitized Gemian query reported a watchdog-class boot reason. This establishes all eight Cortex-A53 cores online concurrently by hotplug in one run—not repeatability, boot-time SMP, stress/coherency, DVFS, idle, thermal behavior, or either A72 `CPU_ON` path. Unchanged O repetition is stopped. See the [runtime evidence](experiments/2026-07-18-cortex-a53-sweep-diagnostic/results/runtime-candidate-o-attempt-1-20260718.txt), [build reproduction](experiments/2026-07-18-cortex-a53-sweep-diagnostic/results/final-build-reproduction-20260718.txt), and [write/readback](experiments/2026-07-18-cortex-a53-sweep-diagnostic/results/boot2-write-candidate-o-20260718.txt).
- [Candidate P](experiments/2026-07-18-fbcon-rotation-diagnostic/README.md) passed its first attributable rotation-only run on exact O. Its raw image SHA-256 is `d192dac9e4516eac9319da2a885abaf3203da6c357c574e7f1f6deef2208d341`; its synchronized, flushed, full logical-`boot2` readback is `cea00d591e74a29d74200f4d292a92aaca2f890bd965af37a7673ab906f4afbc`. The owner observed readable text in the correct normal-landscape orientation and an unassisted return to Gemian. Post-return `console-ramoops` retains the exact inherited O marker, every CPU1–7 pass/accounting checkpoint, final `online=0-7` success with CPU8/9 offline, and the 5/10-second watchdog waits. Collection began after return, so it did not measure the tested cycle's boot-ID change or post-reset boot reason. This closes P once for loader-retained simplefb/fbcon rotation, not native DRM/panel/backlight ownership or repeatability. See the [runtime evidence](experiments/2026-07-18-fbcon-rotation-diagnostic/results/runtime-candidate-p-attempt-1-20260718.txt), [build reproduction](experiments/2026-07-18-fbcon-rotation-diagnostic/results/final-build-reproduction-20260718.txt), and [write/readback](experiments/2026-07-18-fbcon-rotation-diagnostic/results/boot2-write-candidate-p-20260718.txt).
- [Candidate Q](experiments/2026-07-18-keyboard-shell-diagnostic/README.md) is the documented next gate and has not yet been implemented. By owner decision it combines built-in I2C5/AW9523/matrix keyboard enablement, independently visible raw input diagnostics, and a supervised local `tty1` BusyBox shell. It retains P's readable rotation, adds `consoleblank=0`, performs no CPU sweep or storage access, and has no normal-path automatic reboot. The old planned Candidate R shell stage is retired into Q; later eMMC S and USB-networking T remain separate. See the [current roadmap](docs/ROADMAP.md#immediate-priority-keyboard-and-a-supervised-shell-on-the-readable-console-baseline-2026-07-18).
- No subsystem is marked working here until a reproducible log from real Gemini hardware supports the claim.

See the [hardware support matrix](docs/HARDWARE_SUPPORT.md) for the evidence model and current inventory.

## Project principles

1. **Upstream is the product.** Local patches are a staging area with an owner, upstream destination, and deletion condition.
2. **No permanent kernel fork.** Rebase temporary series onto current upstream; do not accumulate a private platform tree.
3. **Use standard subsystem interfaces.** Prefer DRM/KMS, input, power-supply, regulator, MMC, USB, ALSA, rfkill, and ModemManager-compatible interfaces.
4. **Separate SoC and board work.** Reusable MT6797 support must not be hidden in Gemini-only code.
5. **Keep blobs behind kernel interfaces.** Opaque modem, Wi-Fi, or microcontroller firmware may remain where unavoidable; proprietary kernel modules are not an acceptable end state.
6. **Make experiments reversible.** Keep a known-good boot mode and recovery image; never make preloader or NVRAM changes part of the normal workflow.
7. **Publish evidence, not folklore.** Record source, device variant, kernel commit, configuration, test method, and logs.
8. **Stay distribution-neutral.** A successful port boots standard userspace rather than requiring a project-specific root filesystem.

The full rationale and ownership boundaries are in [Architecture and ownership](docs/ARCHITECTURE.md).

## Roadmap

| Milestone | Outcome |
| --- | --- |
| M0 — Safe reproducible lab | Recovery, provenance, variant inventory, reproducible builds, and non-destructive CI |
| M1 — Current-mainline UART boot | Current upstream kernel reaches initramfs over UART repeatedly with core SoC behavior validated |
| M2 — Persistent headless system | PMIC basics, eMMC root, USB networking/serial, SSH, and safe battery telemetry |
| M3 — Keyboard and USB serviceability | Built-in keyboard, microSD, both USB-C paths, role switching, and hotplug |
| M4 — Native display and touch | DRM/KMS scanout, panel/backlight, and touchscreen input |
| M5 — Mobile-grade power | Thermal protection, DVFS, runtime PM, suspend, reliable wake, and measured power use |
| M6 — Daily-driver peripherals | ALSA audio, Panfrost acceleration, Wi-Fi, Bluetooth, GNSS, and sensors |
| M7 — Standard boot and distro integration | Standard boot artifacts and a released-kernel, distribution-owned update path |
| Stretch — Cellular and optional hardware | Cellular transport, cameras, external display, and deeper early-firmware ownership |

Detailed exit criteria and sequencing are in the [roadmap](docs/ROADMAP.md).

Live planning is tracked in the pinned [project plan](https://github.com/ixoo/gemini-pda-mainline/issues/1), the [milestones](https://github.com/ixoo/gemini-pda-mainline/milestones), and the [open issue backlog](https://github.com/ixoo/gemini-pda-mainline/issues).

## Start here

If you own hardware:

1. Read [Safety and recovery](docs/SAFETY.md) before connecting flashing tools.
2. Identify the exact device variant and record non-sensitive evidence.
3. Record durable facts in the [hardware knowledge base](docs/hardware/README.md)
   and reproducible investigations with their code under
   [`experiments/`](experiments/README.md).
4. Choose an issue with `status: ready` and `hardware: required`, or add research to an existing issue.
5. Never publish NVRAM dumps, IMEI values, serial numbers, keys, or calibration blobs.

If you work on kernels:

1. Read [Architecture and ownership](docs/ARCHITECTURE.md) and [Contributing](CONTRIBUTING.md).
2. Set up the supported [ARM64 development VM](docs/DEV_VM.md).
3. Use the [pinned stable-kernel patch workflow](docs/KERNEL_WORKFLOW.md).
4. Start from a pinned upstream release and preserve the complete build configuration.
5. Keep one logical change per patch and identify its upstream subsystem and maintainers.
6. Attach boot logs and test conditions; compile success alone is not hardware support.

## Repository layout

```text
configs/              Gemini kernel configuration fragments
docs/                 Architecture, roadmap, safety, references, and support matrix
experiments/           Reproducible investigations, associated code, and sanitized evidence
kernel/               Pinned stable-kernel source and configuration manifest
patches/              Temporary patch series grouped by upstream base (added when needed)
scripts/              Reproducible build, packaging, and test helpers (added when verified)
vm/                   ARM64 development VM definition and provisioning inputs
project/              Declarative labels, milestones, and initial backlog
.github/              Contribution, issue, and pull-request workflows
```

Large vendor trees, firmware images, partition dumps, root filesystems, and build outputs do not belong in Git.

## Related work

This project begins by mapping and coordinating existing work rather than claiming a green-field port. See [References and prior art](docs/REFERENCES.md), especially:

- [`bsg100/gemini-linux`](https://github.com/bsg100/gemini-linux) — active modern bring-up and hardware notes;
- [`Jasu/gemini-pda-buildroot`](https://github.com/Jasu/gemini-pda-buildroot) — historical mainline UART boot;
- [`gemian/gemini-linux-kernel-3.18`](https://github.com/gemian/gemini-linux-kernel-3.18) — downstream 3.18 source;
- [`planet-community/android_kernel_planetcom_mt6797`](https://github.com/planet-community/android_kernel_planetcom_mt6797) — vendor-kernel mirror;
- [`ixoo/gemini-flash-vagrant`](https://github.com/ixoo/gemini-flash-vagrant) — account-owned historical flashing helper.

References are not endorsements of flashing instructions or licensing. Verify every artifact before use.

## Contributing

Contributions are welcome across kernel development, hardware research, documentation, test automation, and careful on-device validation. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Kernel-bound work must follow the target upstream project's licensing, sign-off, and submission rules.

## License

Repository-authored documentation and tooling are available under the [MIT License](LICENSE) unless a file states otherwise. Imported or upstream-bound kernel material must preserve and follow its own license and SPDX identifiers.

Gemini PDA and Planet Computers are names associated with their respective owners. This independent community project is not affiliated with or endorsed by Planet Computers.
