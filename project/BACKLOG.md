# Initial backlog

The GitHub issues are the live record. This seed list captures intended scope and milestone placement so project structure remains reviewable in Git.

| Milestone | Issue | Acceptance summary |
| --- | --- | --- |
| M0 | Project plan and upstream acceptance gates | All work maps to a milestone, evidence gate, upstream destination, and deletion condition |
| M0 | Document safe recovery, partition boundaries, and UART access | Tested recovery path, protected partitions, redaction rules, and debug access |
| M0 | Inventory Gemini variants and hardware with provenance | Variant-aware component map with source, confidence, and validation method |
| M0 | Audit historical Gemini and MT6797 patchsets against current upstream | Each patch classified as merged, obsolete, unsafe, or still required |
| M0 | Coordinate scope with active Gemini mainline efforts | Overlap and collaboration boundaries documented before parallel driver work |
| M0 | Add reproducible kernel, initramfs, and boot-image build | Pinned inputs and hashes; no vendor kernel code or destructive default target |
| M0 | Add CI for documentation, scripts, patch hygiene, and DT schemas | Automated lint, shell/static checks, checkpatch, and schema validation as content appears |
| M1 | Reproduce current-mainline UART initramfs boot | Ten cold boots with exact commit, config, artifacts, and logs |
| M1 | Characterize LK Device Tree and command-line mutations | Pre/post comparison and minimal boot contract documented |
| M1 | Propose Planet Computers Devicetree vendor prefix and minimal Gemini board DTS | Binding/prefix/board series submitted and tracked publicly |
| M1 | Validate CPUs, RAM, clocks, PSCI, timers, interrupts, and watchdog | Ten CPUs and safe memory behavior under repeatable stress |
| M2 | Bring up PMIC wrapper, regulators, RTC, reboot, and poweroff | Correct power model and orderly lifecycle operations |
| M2 | Bring up eMMC with a persistent root filesystem | Bounded I/O, repeated boots, clean filesystem, and recovery preserved |
| M2 | Bring up USB gadget serial and networking for SSH recovery | Standard gadget interfaces and repeatable host connectivity |
| M2 | Identify charger and fuel-gauge hardware and expose safe telemetry | Verified components, readouts, limits, and failure behavior |
| M3 | Bring up microSD with hotplug and suspend tests | Detection, I/O, remove/reinsert, and suspend behavior pass |
| M3 | Mainline the keyboard using generic AW9523/GPIO infrastructure | Matrix, modifiers, rollover, wake, and LEDs use a generic upstream design |
| M3 | Bring up both USB-C ports and role switching | Port capabilities and repeated device/host/hotplug tests documented |
| M4 | Map and mainline the MT6797 DRM display pipeline | MMSYS/SMI/IOMMU/CMDQ/DSI dependencies result in KMS scanout |
| M4 | Identify and drive the native panel, backlight, and power sequence | Verified compatible, schema, native mode, and repeatable power cycles |
| M4 | Identify and mainline the touchscreen | Proven component identity, multitouch, calibration, and suspend behavior |
| M5 | Add CPU OPP/cpufreq and thermal cooling | Validated tables and safe thermal stress behavior |
| M5 | Implement suspend-to-RAM and wake-source regression tests | Repeated cycles, correct wake, charging safety, and no corruption |
| M6 | Integrate Mali-T880 with Panfrost | Correct clocks, power, resets, IOMMU, and stable rendering |
| M6 | Bring up MT6351 audio routing | Speakers, microphones, headset, and jack detection work through ASoC |
| M6 | Identify and bring up Wi-Fi, Bluetooth, and GNSS | Firmware boundary and upstream driver/transport are documented and functional |
| M6 | Inventory and bring up sensors across variants | Variant-aware map and standard IIO/input support |
| M7 | Chain-load U-Boot or maintained open LK and boot standard artifacts | Standard Image/DTB/initramfs with independently bootable recovery |
| M7 | Land released-kernel support in a distribution and regression lab | No permanent fork; released-kernel boot is repeatably tested |
| Stretch | Document the CCCI/baseband boundary and cellular transport feasibility | Architecture report and upstream feasibility without unsafe radio work |
