# Initial backlog

The GitHub issues are the live record. This seed list captures intended scope and milestone placement so project structure remains reviewable in Git.

| Milestone | Issue | Acceptance summary |
| --- | --- | --- |
| M0 | [Project plan and upstream acceptance gates](https://github.com/ixoo/gemini-pda-mainline/issues/1) | All work maps to a milestone, evidence gate, upstream destination, and deletion condition |
| M0 | [Document safe recovery, partition boundaries, and UART access](https://github.com/ixoo/gemini-pda-mainline/issues/4) | Tested recovery path, protected partitions, redaction rules, and debug access |
| M0 | [Inventory Gemini variants and hardware with provenance](https://github.com/ixoo/gemini-pda-mainline/issues/2) | Variant-aware component map with source, confidence, and validation method |
| M0 | [Audit historical Gemini and MT6797 patchsets against current upstream](https://github.com/ixoo/gemini-pda-mainline/issues/3) | Each patch classified as merged, obsolete, unsafe, or still required |
| M0 | [Coordinate scope with active Gemini mainline efforts](https://github.com/ixoo/gemini-pda-mainline/issues/5) | Overlap and collaboration boundaries documented before parallel driver work |
| M0 | [Add reproducible kernel, initramfs, and boot-image build](https://github.com/ixoo/gemini-pda-mainline/issues/6) | Pinned inputs and hashes; no vendor kernel code or destructive default target |
| M0 | [Add CI for documentation, scripts, patch hygiene, and DT schemas](https://github.com/ixoo/gemini-pda-mainline/issues/8) | Automated lint, shell/static checks, checkpatch, and schema validation as content appears |
| M1 | [Reproduce current-mainline UART initramfs boot](https://github.com/ixoo/gemini-pda-mainline/issues/7) | Ten cold boots with exact commit, config, artifacts, and logs |
| M1 | [Characterize LK Device Tree and command-line mutations](https://github.com/ixoo/gemini-pda-mainline/issues/9) | Pre/post comparison and minimal boot contract documented |
| M1 | [Propose Planet Computers Devicetree vendor prefix and minimal Gemini board DTS](https://github.com/ixoo/gemini-pda-mainline/issues/10) | Binding/prefix/board series submitted and tracked publicly |
| M1 | [Validate CPUs, RAM, clocks, PSCI, timers, interrupts, and watchdog](https://github.com/ixoo/gemini-pda-mainline/issues/11) | Ten CPUs and safe memory behavior under repeatable stress |
| M2 | [Bring up PMIC wrapper, regulators, RTC, reboot, and poweroff](https://github.com/ixoo/gemini-pda-mainline/issues/12) | Correct power model and orderly lifecycle operations |
| M2 | [Bring up eMMC with a persistent root filesystem](https://github.com/ixoo/gemini-pda-mainline/issues/15) | Bounded I/O, repeated boots, clean filesystem, and recovery preserved |
| M2 | [Bring up USB gadget serial and networking for SSH recovery](https://github.com/ixoo/gemini-pda-mainline/issues/14) | Standard gadget interfaces and repeatable host connectivity |
| M2 | [Identify charger and fuel-gauge hardware and expose safe telemetry](https://github.com/ixoo/gemini-pda-mainline/issues/13) | Verified components, readouts, limits, and failure behavior |
| M3 | [Bring up microSD with hotplug and suspend tests](https://github.com/ixoo/gemini-pda-mainline/issues/16) | Detection, I/O, remove/reinsert, and suspend behavior pass |
| M3 | [Mainline the keyboard using generic AW9523/GPIO infrastructure](https://github.com/ixoo/gemini-pda-mainline/issues/17) | Matrix, modifiers, rollover, wake, and LEDs use a generic upstream design |
| M3 | [Bring up both USB-C ports and role switching](https://github.com/ixoo/gemini-pda-mainline/issues/19) | Port capabilities and repeated device/host/hotplug tests documented |
| M4 | [Map and mainline the MT6797 DRM display pipeline](https://github.com/ixoo/gemini-pda-mainline/issues/18) | MMSYS/SMI/IOMMU/CMDQ/DSI dependencies result in KMS scanout |
| M4 | [Identify and drive the native panel, backlight, and power sequence](https://github.com/ixoo/gemini-pda-mainline/issues/20) | Verified compatible, schema, native mode, and repeatable power cycles |
| M4 | [Identify and mainline the touchscreen](https://github.com/ixoo/gemini-pda-mainline/issues/21) | Proven component identity, multitouch, calibration, and suspend behavior |
| M5 | [Add CPU OPP/cpufreq and thermal cooling](https://github.com/ixoo/gemini-pda-mainline/issues/22) | Validated tables and safe thermal stress behavior |
| M5 | [Implement suspend-to-RAM and wake-source regression tests](https://github.com/ixoo/gemini-pda-mainline/issues/23) | Repeated cycles, correct wake, charging safety, and no corruption |
| M6 | [Integrate Mali-T880 with Panfrost](https://github.com/ixoo/gemini-pda-mainline/issues/24) | Correct clocks, power, resets, IOMMU, and stable rendering |
| M6 | [Bring up MT6351 audio routing](https://github.com/ixoo/gemini-pda-mainline/issues/26) | Speakers, microphones, headset, and jack detection work through ASoC |
| M6 | [Identify and bring up Wi-Fi, Bluetooth, and GNSS](https://github.com/ixoo/gemini-pda-mainline/issues/25) | Firmware boundary and upstream driver/transport are documented and functional |
| M6 | [Inventory and bring up sensors across variants](https://github.com/ixoo/gemini-pda-mainline/issues/27) | Variant-aware map and standard IIO/input support |
| M7 | [Chain-load U-Boot or maintained open LK and boot standard artifacts](https://github.com/ixoo/gemini-pda-mainline/issues/28) | Standard Image/DTB/initramfs with independently bootable recovery |
| M7 | [Land released-kernel support in a distribution and regression lab](https://github.com/ixoo/gemini-pda-mainline/issues/29) | No permanent fork; released-kernel boot is repeatably tested |
| Stretch | [Document the CCCI/baseband boundary and cellular transport feasibility](https://github.com/ixoo/gemini-pda-mainline/issues/30) | Architecture report and upstream feasibility without unsafe radio work |
