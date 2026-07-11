# Roadmap

Milestones are evidence gates, not release dates. Work may proceed in parallel when it does not compromise a safe boot loop, but a milestone is complete only when all exit criteria are demonstrated on real hardware and documented.

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

**Outcome:** a current upstream-derived arm64 kernel boots from a non-primary Gemini boot slot and reaches an initramfs shell over UART without vendor kernel code.

Exit criteria:

- early console and normal UART logs captured;
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
- keyboard wake, rollover, LEDs/backlight, and lid/power buttons have documented status;
- microSD detection, I/O, remove/reinsert, and suspend behavior are tested;
- both USB-C paths are inventoried and supported to the extent hardware allows;
- device/host role switching and repeated hotplug pass a regression protocol.

## M4 — Native display and touch

**Outcome:** the Gemini is locally interactive with an upstream DRM/KMS display pipeline.

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
