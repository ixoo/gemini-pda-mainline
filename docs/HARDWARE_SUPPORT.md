# Hardware support matrix

This is the concise current support view for the Gemini PDA mainline effort.
Detailed investigation narratives, candidate identities, hashes, raw samples,
and rejected branches belong in [`experiments/`](../experiments/README.md).
Durable hardware facts belong in [`docs/hardware/`](hardware/README.md).

Last reviewed: **2026-08-25**.

Unless a row says otherwise, runtime evidence applies to the named development
Gemini PDA unit and the local Linux 7.1.3 integration series. A successful
diagnostic profile is not automatically support in the manifest's default
`full` profile or in released upstream Linux.

## State definitions

Runtime state:

| State | Meaning |
| --- | --- |
| `unknown` | No reproducible current-mainline result is recorded. |
| `enumerates` | A driver probes or the device is visible, but function is not established. |
| `partial` | Some intended behavior works, with documented gaps. |
| `working` | The named acceptance test passes on identified hardware and kernel inputs. |
| `stable` | Released upstream code passes a documented regression protocol. |
| `regressed` | A previously passing protocol now fails. |
| `not-applicable` | The hardware is absent on this variant. |

Upstream state:

| State | Meaning |
| --- | --- |
| `missing` | Required support is not known upstream. |
| `local` | A temporary local implementation or board description exists. |
| `RFC` | A public request-for-comments series exists. |
| `submitted` | A patch series is under formal upstream review. |
| `accepted` | A maintainer tree contains the change. |
| `released` | A tagged upstream kernel contains the change. |

Firmware boundary:

| State | Meaning |
| --- | --- |
| `none` | No separately loaded firmware is known for this function. |
| `required-free` | Redistributable firmware is required. |
| `required-nonfree` | Non-redistributable device firmware is required. |
| `unknown` | The firmware or licensing boundary is not established. |

## Current matrix

| Subsystem | Runtime | Upstream | Firmware | Current boundary and remaining gaps |
| --- | --- | --- | --- | --- |
| Non-primary development boot | `working` | `local` | `required-nonfree` | An exact current Linux 7.1.3 Image reached `/init`, USB/netcat, CPU0--7, the I2C5/AW9523 polling-keyboard baseline, watchdog takeover, the read-only DA921x provider, and native reboot from owner-selected logical `boot2`. The current DT retains ten exact Stage-27 CPU `clock-frequency` properties required to prevent the installed LK CPU iterator from repeating its first node; CPU8/9 remained offline and known-good Gemian returned. Standard bootloader ownership and repeated cold boots remain open. See the [read-only provider baseline](../experiments/2026-08-17-mainline-da921x-readonly-provider-baseline/README.md). |
| Loader-retained console | `partial` | `local` | `required-nonfree` | A readable, rotated fbcon shell works and the selected font is usable. Appearance may be delayed; kernel logs can share the interactive console. Stable log separation and native DRM/panel/backlight ownership remain open. |
| Built-in keyboard | `partial` | `local` | `none` | AW9523 plus generic matrix polling provides working keyboard input and the current physical map. F1–F10, Page Up/Page Down, modifiers, rollover, wake, and complete event coverage still need explicit tests. See the [keyboard facts](hardware/keyboard.md). |
| USB gadget Ethernet and development shell | `working` | `local` | `none` | Peripheral-mode Ethernet, addressing, ping, and a bounded no-authentication development shell work on the USB-only link. Host mode, role switching, charging, both physical ports, and hotplug regression remain open. See the [USB gadget experiment](../experiments/2026-07-21-usb-gadget-ethernet/README.md). |
| Kernel restart | `working` | `local` | `none` | The normal Linux restart path reaches MT6797 TOPRGU and has returned the unit to Gemian in attributable tests. Power-off, every reset source, and long-run repeatability remain separate gates. See the [restart experiment](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/README.md). |
| Watchdog reset | `partial` | `local` | `none` | The no-bark-IRQ TOPRGU watchdog path can register, expire, and reset the unit. Pretimeout/bark IRQ behavior and a general watchdog regression protocol are not established. See the [watchdog diagnostic](../experiments/2026-07-18-watchdog-registration-diagnostic/README.md). |
| eMMC development access | `partial` | `local` | `none` | The block layer can expose the live GPT and supports guarded reads plus development writes to explicitly resolved non-active `boot2`. Primary `boot` remains protected in the working environment, and broad storage reliability, suspend, and filesystem testing remain open. See the [eMMC experiment](../experiments/2026-07-25-emmc-development/README.md). |
| Cortex-A53 CPU0–7 | `partial` | `local` | `none` | All eight A53 CPUs can be online together and remain present on the latest serviceability baseline. Coherency stress, boot repetition, cpufreq/OPP, idle, thermal, and suspend are not established. See the [A53 sweep](../experiments/2026-07-18-cortex-a53-sweep-diagnostic/README.md). |
| Cortex-A72 CPU8–9 | `partial` | `local` | `unknown` | Exact mainline CPU8 admission now completes P27, provider acquisition, isolation, masked stable SRAM validation, and P28, then issues one zero-returning CPU_ON callback. Generic arm64 secondary completion still times out with `-EIO`; CPU8 remains offline and CPU9 stays vetoed. Separately, an experiment-only Gemian-derived kernel repeatably retains both A72 CPUs and validates bounded scheduler work plus target-local MPIDR/MIDR records. This is not stable/default support. Early CPU8 entry localization, architecture completion, safe CPU_OFF, sustained load, cpufreq/OPP, thermal, suspend, and default integration remain unproved. See the [mainline stage-7 result](../experiments/2026-08-31-mainline-a72-sram-selector-mask-contract-repair/results/runtime-attempt-2-online-wait-timeout-20260831.txt), [target-register complete pass](../experiments/2026-08-28-a72-pmsg-witness/results/runtime-attempt-1-complete-pass-20260829.txt), and [DA921x/A72 boundary](hardware/da921x-i2c6-a72.md). |
| DVFSP handoff and AP-DMA ownership | `partial` | `local` | `none` | The local handoff passed late validation, released I2C6 for the read-only DA921x provider, and preserved the shared AP-DMA owner used by I2C5. The current exact Stage-27 serviceability runtime cumulatively binds the platform-state source plus the read-free clock and BigiDVFS backends with no protected read, clock enable, or secure call. Separately, one exact handoff-owned ABI-2/generation-1 protected-clock snapshot returned with sole CSPM and MCUMIXED owners while I2C6, DA921x, keyboard, USB, and CPU0--7 remained serviceable; exact before/after records survived the native return. BigiDVFS readback, retry, resume, error recovery, writable ownership, and CPU8/CPU9 admission remain unproved. See the [three-backend bind result](../experiments/2026-08-24-mainline-a72-bigidvfs-backend-stage27-control/results/runtime-attempt-1-serviceable-20260824.txt), [resource map](hardware/mt6797-live-resource-map.md), and [one-read result](../experiments/2026-08-23-mainline-protected-clock-first-dmesg-call/results/runtime-attempt-1-pass-20260823.txt). |
| MT6797 I2C6 native short transfer | `partial` | `local` | `none` | The native packed/FIFO pointer/read path and one exact one-message two-byte write are runtime-proven. The bounded write completed once as `[0xda, 0x46]` with exact controller attribution, no retry, immediate/delayed `0x46` readback, and unchanged full-byte poststate. Arbitrary writes, failures, reset recovery, suspend, and stress are unproved. See the [same-value result](../experiments/2026-08-20-mainline-da921x-same-value-dt-contract-repair/results/runtime-attempt-2-success-20260820.txt) and [DA921x/I2C6 boundary](hardware/da921x-i2c6-a72.md). |
| Legacy DA921x board-control contract | `partial` | `local` | `none` | Natural bind and one unbind/rebind lifecycle completed the fixed `0x68`/`0x69` DA9213/DA9214/DA9215-compatible tuple at exact `14 -> 14 -> 28` read counts, with DMA and every write/other counter zero. This closes the read-only identification lifecycle, not unique silicon identity, page semantics, writes, or rail state. See the [lifecycle result](../experiments/2026-08-01-da921x-post-event-lifecycle/results/runtime.txt). |
| Legacy DA921x identification/provider | `partial` | `local` | `none` | The dedicated legacy driver binds two read-only providers. An exact provider-ready boot deferred the composed observer until DA921x bound, then completed two stable samples and ten read-only transfers with tuple `7b/c1/00/46/46`, zero writes/actions, and the serviceability baseline intact. A separate exact default-off same-value runtime retained Buck B `0x46` across one attributed `0xda <- 0x46` write plus readback. This closes the composed read-only boundary and Roadmap Gate 6 for the reviewed no-op only; active rail ownership, changed-value rollback, resume, and production A72 integration remain unproved. See the [composed read-only result](../experiments/2026-08-25-mainline-a72-platform-provider-deferred-bind-repair/results/runtime-attempt-1-provider-ready-pass-20260825.txt), [same-value result](../experiments/2026-08-20-mainline-da921x-same-value-dt-contract-repair/results/runtime-attempt-2-success-20260820.txt), and [ordered roadmap](ROADMAP.md#ordered-gates). |
| MT6351 PMIC wrapper and selected regulators | `partial` | `local` | `none` | The eMMC profile bound PWRAP and its MT6351 child and exposed the required VEMC/VIO18 rails without MMC probe defer. This does not validate the complete regulator tree or general sequencing. See the [eMMC result](../experiments/2026-07-25-emmc-development/README.md) and [PMIC recovery record](../experiments/2026-07-11-mt6351-pmic-recovery/README.md). |
| RTC, power keys, and power-off | `unknown` | `local` | `unknown` | Resources and vendor behavior are documented, but EINT, RTC timekeeping, power-key events, and a safe kernel power-off path have no current acceptance result. |
| microSD | `unknown` | `local` | `none` | Controller and slot resources are documented, but insertion, I/O, removal, and suspend have no current acceptance result. See the [MSDC recovery record](../experiments/2026-07-12-mt6797-msdc-recovery/README.md). |
| Native display and backlight | `unknown` | `local` | `none` | Loader-retained simplefb output must not be confused with native DRM support. Panel identity, DSI pipeline, power/reset, backlight ownership, and repeated modesets remain open. See the [panel recovery record](../experiments/2026-07-11-gemini-panel-recovery/README.md). |
| Touchscreen | `unknown` | `local` | `unknown` | Vendor identity and wiring evidence exist, but no current-mainline multitouch acceptance test is recorded. See the [input recovery record](../experiments/2026-07-12-input-backlight-recovery/README.md). |
| Charger, fuel gauge, and battery telemetry | `unknown` | `local` | `unknown` | BQ25890/FAN49101 evidence and alternatives are documented. Safe charging, telemetry, thermal protection, suspend behavior, and standard power-supply integration remain unproved. See the [charger recovery record](../experiments/2026-07-12-charger-power-recovery/README.md). |
| Thermal management | `unknown` | `local` | `none` | Sensor banks, calibration inputs, and vendor resources are recovered, but no safe current-mainline trip-point or throttling protocol is established. See the [thermal recovery record](../experiments/2026-07-13-mt6797-thermal-recovery/README.md). |
| Suspend and wake | `unknown` | `missing` | `unknown` | PMIC, clocks, SPM, IRQ, regulator, storage, USB, and wake-source ownership are not complete enough for a safe system-suspend claim. |
| Audio | `unknown` | `local` | `unknown` | AFE, codec, and route evidence exists; speaker, microphone, headphone, and jack behavior have no current-mainline acceptance result. See the [audio recovery record](../experiments/2026-07-12-audio-afe-recovery/README.md). |
| Mali GPU | `unknown` | `local` | `none` | The Mali-T88x and platform resources are known, but Panfrost integration, clocks, power domains, IOMMU, DVFS, and thermal behavior are untested. See the [GPU recovery record](../experiments/2026-07-12-mt6797-gpu-panfrost-recovery/README.md). |
| Wi-Fi, Bluetooth, GNSS, and FM | `unknown` | `missing` | `required-nonfree` | The CONSYS/WMT firmware boundary is documented, but maintainable upstream transports and runtime acceptance tests are missing. See the [connectivity recovery record](../experiments/2026-07-12-connectivity-wmt-recovery/README.md). |
| Sensors | `unknown` | `local` | `unknown` | Bus addresses and vendor logical devices are documented, but exact electrical identity and standard IIO/input runtime coverage remain incomplete. See the [sensor recovery record](../experiments/2026-07-12-sensor-iio-recovery/README.md). |
| Cellular modem | `unknown` | `missing` | `required-nonfree` | CCCI/CLDMA and shared-memory ownership are research inputs only. A safe upstream transport, crash isolation, regulatory boundary, and standard userspace integration are missing. |
| Cameras | `unknown` | `missing` | `required-nonfree` | Sensor and pipeline resources are incomplete; no current-mainline capture path is established. See the [camera recovery record](../experiments/2026-07-13-camera-recovery/README.md). |

## Updating the matrix

Keep each row to the current conclusion and remaining gaps. Do not add
candidate-by-candidate chronology here.

Every runtime promotion must link to an experiment record containing:

- exact device variant;
- kernel commit and selected patch/profile revision;
- resolved configuration and toolchain;
- test protocol and repetition count;
- sanitized evidence;
- known negative space;
- upstream series or commit when upstream state changes.

Use `working` only for a named acceptance test. Use `stable` only when released
upstream code passes the project's documented regression protocol.
