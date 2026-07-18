# Experiments and reverse engineering

This directory contains reproducible investigations of the Gemini PDA and its
software-visible hardware. The write-up, probe code, and sanitized evidence for
an investigation stay together so another contributor can repeat or challenge
the result.

## Index

- [2026-07-11 Gemian hardware inventory](2026-07-11-gemian-hardware-inventory/README.md)
  — read-only whole-device discovery baseline and reusable collector.
- [2026-07-11 Gemian firmware inventory](2026-07-11-gemian-firmware-inventory/README.md)
  — private vendor-firmware capture, sanitized hashes, and load evidence.
- [2026-07-11 Gemian hardware-userspace inventory](2026-07-11-gemian-hardware-userspace-inventory/README.md)
  — Android HAL, vendor library/daemon, and native compatibility-boundary map.
- [2026-07-11 MT6797 device-tree recovery](2026-07-11-mt6797-device-tree-recovery/README.md)
  — decoded live resources for mainline DTS and driver data.
- [2026-07-11 vendor userspace to kernel ABI](2026-07-11-vendor-kernel-abi/README.md)
  — static interface extraction and Linux 7.1.3 replacement-gap analysis.
- [2026-07-11 Gemini panel recovery](2026-07-11-gemini-panel-recovery/README.md)
  — runtime panel selection, DSI mode, command, bias, reset, false-DT-lead,
    and the descriptor-based mainline NT36672E framework recovery.
- [2026-07-11 MT6351 PMIC recovery](2026-07-11-mt6351-pmic-recovery/README.md)
  — direct PMIC identity, pwrap/reset clocks, regulators, RTC, power keys, and
  the missing MT6797 EINT prerequisite.
- [2026-07-12 MT6797 MSDC recovery](2026-07-12-mt6797-msdc-recovery/README.md)
  — storage-controller register contract, live eMMC/card-slot state, and a
  conservative Linux 7.1 bring-up plan.
- [2026-07-12 MT6797 M4U and SMI recovery](2026-07-12-mt6797-m4u-smi-recovery/README.md)
  — multimedia IOMMU topology, SMI larbs, fault IDs, ports, clocks, and
  power-domain recovery for Linux 7.1.
- [2026-07-12 MT6797 CMDQ/GCE recovery](2026-07-12-mt6797-cmdq-gce-recovery/README.md)
  — live mailbox execution, thread/address format, subsystem selectors,
  hardware events, clock gating, and normal/secure IRQ separation.
- [2026-07-12 MT6797 display-mutex recovery](2026-07-12-mt6797-display-mutex-recovery/README.md)
  — module bits, SOF/EOF encoding, register layout, live IRQ/clock evidence,
  DEVAPC boundary, MM power domain, and GCE client contract.
- [2026-07-12 MT6797 MMSYS routing recovery](2026-07-12-mt6797-mmsys-routing-recovery/README.md)
  — complete mux graph, active OVL/RDMA/UFOE/DSI route, reset banks, and GCE
  client contract.
- [2026-07-12 MT6797 DRM component recovery](2026-07-12-mt6797-drm-component-recovery/README.md)
  — OVL, fixed-function PQ, RDMA, UFOE, DSI, and MIPI-PHY register-generation,
  clock, interrupt, and safe first-light contract recovery.
- [2026-07-12 input and backlight recovery](2026-07-12-input-backlight-recovery/README.md)
  — live Novatek touchscreen/EINT, AW9523 keyboard matrix, and MT6797 display
  PWM contracts compared with Linux 7.1.3 reuse boundaries, plus a disabled
  standard AW9523 matrix-keypad candidate and vendor-ELF/source parity for the
  eleven-entry NT36xxx trim table.
- [2026-07-12 sensor and IIO recovery](2026-07-12-sensor-iio-recovery/README.md)
  — live I2C1 sensor bindings, vendor virtual-sensor boundary, and Linux 7.1.3
  reuse versus new-driver decisions.
- [2026-07-12 USB and Type-C recovery](2026-07-12-usb-typec-recovery/README.md)
  — live USB1/USB3 windows, MT6797 PHY clocks and tuning boundary, and the
  generic FUSB301 controller candidate plus the unresolved board/role contract.
- [2026-07-12 connectivity/WMT recovery](2026-07-12-connectivity-wmt-recovery/README.md)
  — MT6797 CONSYS/WMT identity, Wi-Fi/BTIF/GNSS/FM resources, firmware hashes,
  and the standard Linux 7.1 reuse boundary.
- [2026-07-12 audio AFE recovery](2026-07-12-audio-afe-recovery/README.md)
  — live ASoC endpoints, MT6797 AFE/MT6351 codec graph, and the existing
  Linux 7.1.3 reuse boundary.
- [2026-07-12 CPU DVFS, thermal, and suspend recovery](2026-07-12-cpufreq-thermal-suspend-recovery/README.md)
  — live cpufreq policies, vendor OPP diagnostics, thermal-zone sentinels,
  cpuidle/PSCI state evidence, and the missing MT6797 mainline contracts.
- [2026-07-13 CPU/PSCI/timer recovery](2026-07-13-cpu-psci-timer-recovery/README.md)
  — live ten-CPU DT topology, PSCI 0.2 SMC IDs, architectural timer PPIs,
  clocksource/clockevent selection, and the generic Linux reuse boundary.
- [2026-07-13 MT6797 thermal recovery](2026-07-13-mt6797-thermal-recovery/README.md)
  — live disabled thermal zones, six-bank/five-sensor mapping, efuse
  calibration contract, and the new MT6797 thermal-driver boundary.
- [2026-07-12 MT6797 GPU/Panfrost recovery](2026-07-12-mt6797-gpu-panfrost-recovery/README.md)
  — live Mali-T88x identity, vendor GPU DVFS/clock contracts, and the
  Panfrost-versus-platform integration boundary.
- [2026-07-12 RT5735 VGPU recovery](2026-07-12-rt5735-vgpu-recovery/README.md)
  — external GPU-buck identity, register/voltage contract, and the dedicated
  regulator-driver boundary.
- [2026-07-12 boot contract recovery](2026-07-12-boot-contract-recovery/README.md)
  — Android boot-image layout, retained LK chosen properties, root partition,
  and the reversible mainline boot-artifact boundary.
- [2026-07-12 charger and fuel-gauge recovery](2026-07-12-charger-power-recovery/README.md)
  — live BQ25890/FAN49101 ownership, the inactive RT9466 alternative, and the
  standard power-supply versus new-driver boundary, including the bounded
  FAN49101 register contract and disabled-only mainline driver candidate.
- [2026-07-12 MT6797 watchdog recovery](2026-07-12-mt6797-watchdog-recovery/README.md)
  — TOPRGU register/protocol reuse, the Gemini bark IRQ, and the vendor WDK
  side-channel boundary.
- [2026-07-12 MT6797 clock/power/reset recovery](2026-07-12-mt6797-clock-power-reset-recovery/README.md)
  — live clock summary, SCPSYS resource ordering, MFG/core SRAM handshake,
  and the generic-provider extension boundary.
- [2026-07-12 MT6797 EINT and pinctrl recovery](2026-07-12-mt6797-eint-recovery/README.md)
  — vendor-versus-live EINT contract, recovered GPIO map, virtual PMIC input,
  and the generic Linux reuse/new-data boundary.
- [2026-07-12 hall/lid/switch recovery](2026-07-12-hall-lid-switch-recovery/README.md)
  — GPIO66/EINT5 hall input, GPIO93/EINT16 toggle input, vendor polarity and
  debounce behavior, and the standard `gpio-keys` replacement boundary.
- [2026-07-12 kernel configuration gap audit](2026-07-12-kernel-config-gap-audit/README.md)
  — vendor 3.18 versus prepared Linux 7.1.3 options, modern symbol mappings,
  and the distinction between missing drivers and private policy switches.
- [2026-07-13 driver coverage audit](2026-07-13-driver-coverage-audit/README.md)
  — linked-in/module-only driver ownership and live vendor-driver comparison
  for the packaged Linux 7.1.3 candidate.
- [2026-07-13 bsg100 comparison](2026-07-13-bsg100-gemini-linux-comparison/README.md)
  — independent-reference audit, including a focused review of the later
  native-fbcon milestone, the portable MT6797 DRM/PHY findings, the targeted
  simplefb backlight-clock test, and the unresolved SSD2092/NT36672 variant
  boundary.
- [2026-07-14 first-boot probe audit](2026-07-14-first-boot-probe-audit/README.md)
  — static PWRAP/MT6351/regulator/MSDC probe ordering and write-side-effect
  boundary for the conservative first boot.
- [2026-07-14 mainline module closure audit](2026-07-14-mainline-module-closure-audit/README.md)
  — built-in versus optional-module availability and exact packaged dependency
  closures for the current 7.1.3 kernel artifact.
- [2026-07-16 LK handoff alignment](2026-07-16-lk-handoff-alignment/README.md)
  — modern arm64 placement, LK pre-jump DT properties, a probe-minimal kernel
  profile, reproducible serial/simplefb Android v0 test candidates, and the
  dark/serial-silent/non-looping `boot2` attempt whose Linux runtime remains
  unknown.
- [2026-07-16 USB gadget diagnostic](2026-07-16-usb-gadget-diagnostic/README.md)
  — MTU3/T-PHY peripheral candidate and storage-inert initramfs, now written
  and fully read back from `boot2`; two bounded host checks found no USB child
  while the device remained dark and steady, leaving that cycle's Linux
  execution unknown. Later exact M/N retained pstore independently proves the
  T-PHY and MTU3 probes, forced B-device session, `g_ether` registration, and
  MTU3 gadget pull-up log on the inherited path, but not electrical D+ state
  or host enumeration; see the
  [sanitized retained-pstore result](2026-07-16-usb-gadget-diagnostic/results/retained-pstore-mtu3-gadget-evidence-20260718.txt).
- [2026-07-16 fixed-delay reboot diagnostic](2026-07-16-timed-reboot-diagnostic/README.md)
  — reproducible ramdisk-only follow-up that preserves the tested USB kernel
  and DTB while arming a 10-second reset request from `/init`; owner-approved
  `boot2` write is synchronized and fully read back. Its first boot changed
  from the baseline's dark steady state to a delayed backlight-off, off-like
  state after an owner-estimated 5–10 seconds with no automatic restart. The
  timing and one-file delta strongly support `/init` execution but do not yet
  directly confirm it.
- [2026-07-16 deterministic screen marker](2026-07-16-screen-marker-diagnostic/README.md)
  — preserves exact candidate D's kernel while adding an allowlisted LK
  simplefb node and one bounded early-userspace framebuffer fill; two builds
  are byte-identical. The image was written and fully read back from `boot2`,
  but its first owner-run boot remained black with no expected marker. This is
  a failed positive screen test, not proof of kernel failure. The next
  one-variable derivative retains `CLK_INFRA_DISP_PWM` through simplefb based
  on the hardware-working bsg100 history.
- [2026-07-16 simplefb clock-retention diagnostic](2026-07-16-screen-clock-retention-diagnostic/README.md)
  — Candidate F reconstructs exact Candidate E and adds only its path-resolved
  `CLK_INFRA_DISP_PWM` simplefb reference. Its first boot showed sideways
  console text for about one second before black, the first positive visual
  Linux 7.1.3 handoff signal on this unit; unread text does not prove `/init`.
- [2026-07-16 fbcon text retention diagnostic](2026-07-16-fbcon-text-diagnostic/README.md)
  — Candidate G keeps exact F's kernel, DTB and simplefb clock reference while
  replacing only initramfs, removing all raw framebuffer access, and holding a
  distinctive sideways console banner. Its attended boot reproduced sideways
  scrolling for 1–2 seconds before black with the backlight apparently off,
  rejecting Candidate F's raw-write explanation but not confirming `/init`.
- [2026-07-16 simplefb MM-root retention](2026-07-16-simplefb-mm-root-retention/README.md)
  — Candidate H keeps exact G's kernel and initramfs and appends only
  `CLK_TOP_MUX_MM` to simplefb's retained clocks. Two builds are recursively
  byte-identical. In one attended series, two attempts visibly progressed
  farther and the owner approximately recognized H's initramfs-only marker;
  the backlight remained on with the text and went off at the black transition.
  Later attempts did not reproduce the progress, so stable retention remains
  unresolved.
- [2026-07-16 fbcon refresh-timing diagnostic](2026-07-16-fbcon-refresh-timing-diagnostic/README.md)
  — Candidate I keeps H's exact kernel and DTB and exact initramfs tree except
  `/init`, then emits one tty0 line per second through `T+60` before a silent
  static hold. Two builds are byte-identical; the exact image is exported,
  synchronized and fully read back from `boot2`. The reported intended
  selection went directly to black without I's marker, counter, or other text;
  selection and `/init` remain unconfirmed and the timing hypothesis is
  untested.
- [2026-07-17 unused-clock cleanup diagnostic](2026-07-17-clk-ignore-unused-diagnostic/README.md)
  — Candidate J rebuilds the kernel to append `clk_ignore_unused` to forced
  `CONFIG_CMDLINE` while retaining exact I's DTB, initramfs, and Android header
  command line. A header-only draft was rejected as a no-op under
  `CONFIG_CMDLINE_FORCE=y`. The raw image is
  `6d5bad08c2f93eba7fbd66ea5c54de2437f81e44832426a97d4d65d550c659f4`;
  an isolated clean build reproduced the config, kernel payload, `System.map`,
  all 119 DTBs, and boot image byte-for-byte. It was synchronized, flushed, and
  fully read back from logical `boot2`; that full 16 MiB partition/readback hash
  was `465e4c747138e12191d38fd6b4cde68cd0b9a19f918030dea05c9b8dbdd4d3fc`.
  No reboot was part of the [write/readback operation](2026-07-17-clk-ignore-unused-diagnostic/results/boot2-write-candidate-j-20260717.txt).
  On the first later owner-attended intended selection, the last visible suffix
  before black was reported as `4/60`. Only the tracked shared I/J `/init` emits
  that counter, so this strongly supports Linux/fbcon/tty0 and `/init` tick 04
  for the verified J target in that attempt, without an exact full-line or
  marker transcription. A later two-bullet report is provisionally interpreted
  as two additional intended J/`boot2` selections because the outcomes are
  mutually exclusive, with owner confirmation pending. One reached "iteration
  4" before black, compatible with and corroborating tick 04; one went directly
  black with no console and cannot establish selected slot, kernel entry, or
  `/init`. Provisionally, two of three intended selections had
  tick-04-compatible visible output and one of three was no-console and
  unattributable. The [first runtime](2026-07-17-clk-ignore-unused-diagnostic/results/runtime-candidate-j-attempt-1-20260717.txt)
  and [repeat report](2026-07-17-clk-ignore-unused-diagnostic/results/runtime-candidate-j-repeat-report-20260717.txt)
  preserve the unknowns. Stable visibility and clock causality are not
  established. Further J repetition is stopped; the completed reassessment
  initially selected Candidate K rather than a matched-I rollback, then the
  strategy review cancelled K without runtime. This broad control
  does not enable already-off clocks, prevent explicit disables, or retain
  regulators or power domains.
- [2026-07-17 fbcon newline-boundary diagnostic](2026-07-17-fbcon-newline-boundary-diagnostic/README.md)
  — Candidate K is a reproducible exact-J initramfs-only newline/scroll
  derivative. Its write/readback record is retained, but the strategy review
  cancelled the device test without a runtime selection because it changes no
  kernel, DT, or configuration input and would not alter the next action.
- [2026-07-17 UART/pstore observability](2026-07-17-uart-pstore-observability/README.md)
  — Candidate L was the bounded observability gate:
  UART0 GPIO97/98 correction, exact mainline-console/Gemian
  primary `console-ramoops` alignment validated from pinned source and the
  exact active binary, and MT6797 watchdog auto-restart plus IRQ-dependent dual-stage
  policy with persistent post-reset evidence. Pmsg supplies address alignment,
  not a cross-version recovery channel. A clean fresh-source rebuild reproduced
  the candidate exactly; it is exported and its synchronized logical-`boot2`
  write has a matching full readback. Attempt 1 showed the LK splash then black
  and was unattributable. Attempt 2 strongly reached tracked `/init` suffix
  `watchdog0=waiting remaining=5s`; connected serial stayed silent, the screen
  switched off, manual power recovery was required, and pstore was empty.
  Unchanged repetition is stopped. A source audit rejects changing the
  falling-edge flag because MediaTek SYSIRQ translates it for the parent GIC.
  Candidate M therefore omits only the optional bark IRQ and adds early
  binding diagnostics, matching an independent hardware-tested basic-watchdog
  configuration. See [attempt 1](2026-07-17-uart-pstore-observability/results/runtime-candidate-l-attempt-1-20260718.txt),
  [attempt 2](2026-07-17-uart-pstore-observability/results/runtime-candidate-l-attempt-2-20260718.txt),
  and the [registration audit](2026-07-17-uart-pstore-observability/results/watchdog-registration-audit-20260718.txt).
- [2026-07-18 watchdog registration diagnostic](2026-07-18-watchdog-registration-diagnostic/README.md)
  — Candidate M keeps Candidate L's exact Linux `Image.gz` and LK header
  contract, deletes only the optional watchdog bark interrupt from the
  appended DTB, and replaces only initramfs `/init`. A live-DT gate plus
  platform, driver, class, devnode, ramoops, kmsg, and filtered-dmesg evidence
  distinguishes an IRQ-blocked registration from the next probe-stage fault.
  Two clean VM builds are recursively identical; raw SHA-256 is
  `a0a6c520fcc170ee0a422e66384559c50100ee65645811c331149beec8c347da`.
  Its synchronized, flushed logical-`boot2` target and complete readback match
  padded SHA-256
  `53234ca7e81b23c77b0910e1e2bcdf54dc7a2984e28bbe9baac30ad26eeb7c2b`.
  Its first controlled runtime passed the decision oracle: retained
  `console-ramoops` proves the live IRQ omission, successful `mtk-wdt` probe,
  `/dev/watchdog0`, one handoff ping, a 31-second timeout, and progress through
  `watchdog_wait=30s`. The console remained visible and the device returned to
  Gemian automatically; Gemian reported `wdt_by_pass_pwk`, `reboot`, and set
  PMIC watchdog-reboot flags. This establishes the basic no-IRQ TOPRGU reset
  and cross-version console retention for this revision, not bark/pretimeout,
  native display, SMP, or repeatability. See the
  [runtime record](2026-07-18-watchdog-registration-diagnostic/results/runtime-candidate-m-attempt-1-20260718.txt);
  do not repeat unchanged M.
- [2026-07-18 CPU1 online diagnostic](2026-07-18-cpu1-online-diagnostic/README.md)
  — Candidate N passed its first bounded runtime gate. It retains Candidate M's exact
  kernel, embedded configuration, no-IRQ DTB, LK container contract, pstore,
  fbcon, and 31-second recovery timer, changing only initramfs `/init`. The
  exact kernel already has SMP, CPU hotplug, PSCI, and sysfs; the intended
  first secondary DT CPU is Cortex-A53 MPIDR `0x1`, and N gates the live CPU1
  `of_node` against it. N arms the watchdog before writing
  `1` exactly once to CPU1's standard `online` control, then records the return,
  masks, kernel lines, and CPU1 accounting without retrying or pinging again.
  Two clean VM builds are recursively byte-for-byte identical; the raw image
  SHA-256 is
  `43aea71224f6261001ff00904b30dae29063334172a2f6b0163b424a84c0e3aa`.
  It was synchronized to live-resolved logical `boot2`, flushed, and fully
  read back with exact padded SHA-256
  `a5cc12372ece5e50364a88bc0bf4401ff092e335281352b062ed0ad229fbb7bf`.
  Its one attended selection produced the exact N record in retained
  `console-ramoops`. The CPU-hotplug request returned success, CPU1 booted as
  MPIDR `0x1` / Cortex-A53, the online mask changed from `0` to `0-1`, and two
  `/proc/stat` samples proved advancing CPU1 accounting. CPU1 remained online
  through the 25-second marker, then the watchdog returned the device to
  Gemian automatically without owner help. This promotes only the first
  secondary Cortex-A53 path from one run; do not repeat unchanged N. The next
  candidate may request the remaining A53s in sequence, provided every request
  has a durable execution checkpoint and the sequence stops at its first
  failure; keep the A72 pair separate. See the
  [build reproduction](2026-07-18-cpu1-online-diagnostic/results/final-build-reproduction-20260718.txt),
  [write/readback](2026-07-18-cpu1-online-diagnostic/results/boot2-write-candidate-n-20260718.txt),
  and [runtime record](2026-07-18-cpu1-online-diagnostic/results/runtime-candidate-n-attempt-1-20260718.txt).
- [2026-07-18 Cortex-A53 sweep diagnostic](2026-07-18-cortex-a53-sweep-diagnostic/README.md)
  — Candidate O is the deterministic initramfs-only derivative of exact N for
  the next controlled boot. It validates all CPU1–9 logical-to-DT mappings,
  arms the proven no-IRQ watchdog, and requests CPU1 through CPU7 online in
  sequence with a durable boot/accounting checkpoint after each. It stops at
  the first failure and never writes the deferred Cortex-A72 CPU8/9 controls.
  The raw image is pinned to SHA-256
  `4376579c3b1a9ddfbec485eb62ba6cfc0af38183527924b5a250246345cb2146`;
  two clean VM builds are recursively byte-identical and the exact artifact is
  available in the Git-ignored host export. The exact padded image was then
  synchronized, block-flushed, and fully read back from live-resolved logical
  `boot2`; the full target matches SHA-256
  `5efda7d18ebb99d0152d872d6dd23e7e6345c56920a77fb1129c350e8e02102d`.
  No reboot was performed and the runtime result remains untested. See the
  [build reproduction](2026-07-18-cortex-a53-sweep-diagnostic/results/final-build-reproduction-20260718.txt)
  and [write/readback](2026-07-18-cortex-a53-sweep-diagnostic/results/boot2-write-candidate-o-20260718.txt).
- [2026-07-14 live vendor-to-mainline gap audit](2026-07-14-live-vendor-mainline-gap-audit/README.md)
  — read-only comparison of the live Gemian vendor contracts with the current
  Linux 7.1.3 handoff and first-boot boundaries.
- [2026-07-14 upstream MT6797 coverage audit](2026-07-14-upstream-mt6797-coverage-audit/README.md)
  — source-level reuse/new-driver census, MT6797 I2C fallback validation, and
  the SPI controller boundary through the existing `mt6765_compat` profile;
  patches 0072–0073 and their validated disabled-node package are recorded in
  the SPI patch-validation result.
- [2026-07-13 camera recovery](2026-07-13-camera-recovery/README.md)
  — runtime SP5509 camera identity, bounded vendor-ELF chip-ID/I2C recovery,
  MT6797 SENINF/ISP resource boundary, and the new-sensor-driver versus
  existing-mainline-driver decision.
- [2026-07-13 external-display recovery](2026-07-13-external-display-recovery/README.md)
  — unbound SII9022/EDID candidates, SII9024A-named vendor wiring, and the
  Linux 7.1.3 `sii902x` bridge reuse boundary.
- [2026-07-13 memory carve-out recovery](2026-07-13-memory-carveout-recovery/README.md)
  — discontiguous DRAM, fixed firmware reservations, dynamic CONSYS/SCP-share/
  SPM ownership, and the Linux 7.1.3 DT boundary.
- [2026-07-13 modem/CCCI recovery](2026-07-13-modem-ccci-recovery/README.md)
  — live MD1 and MD3/C2K CCCI/CLDMA topology, shared-memory/EMI ownership,
  and the new MT6797 transport versus reusable WWAN/TTY boundary.
- [2026-07-13 UART/console recovery](2026-07-13-uart-console-recovery/README.md)
  — live `ttyMT0`–`ttyMT3`, vendor AP-DMA/console behavior, Linux 8250 reuse,
  and the LK command-line naming boundary.
- [2026-07-13 kernel integration](2026-07-13-kernel-integration/README.md)
  — reproducible Linux 7.1.3 preparation, configuration, 57-patch compilation,
  artifact packaging, and checksum/provenance verification.

## Layout

Create a directory named with the start date and a short subject:

```text
experiments/2026-07-11-uart-identification/
  README.md
  scripts/       collection, decoding, and analysis helpers
  src/           purpose-built probe or test source
  fixtures/      small redistributable inputs needed for tests
  results/       small sanitized logs, tables, or summaries
```

Copy `experiments/TEMPLATE.md` to the new directory as `README.md`. Omit unused
subdirectories. Code must state its dependencies and default to read-only or
dry-run behavior. A command that can modify hardware must require an explicit
target and opt-in flag.

## Evidence policy

- Keep raw private captures outside Git. Commit only the smallest sanitized
  evidence needed to support the result.
- Redact serial numbers, IMEI values, identifying MAC addresses, keys,
  credentials, calibration blobs, and user data.
- Do not commit firmware, partition images, NVRAM, proprietary source or
  documents, or artifacts without verified redistribution rights.
- Hash externally retained evidence when its identity matters, but do not
  publish a hash if it could identify a person or device.
- Record failures, negative results, and ambiguity. They prevent repeated unsafe
  work and are valid outcomes.

When an experiment establishes a durable fact, summarize it in
`docs/hardware/` and link back to the experiment. When it changes runtime support,
update `docs/HARDWARE_SUPPORT.md` with the exact evidence. When it produces a
kernel change, export the logical commit into `patches/` and link all three.
