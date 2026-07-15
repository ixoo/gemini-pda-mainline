# Experiment: Gemian hardware inventory

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-11-gemian-hardware-inventory` |
| Status | `completed` |
| Subsystem | Whole-device discovery baseline |
| Device variant | Gemini PDA; retail variant not independently established |
| Date | 2026-07-11 |
| Investigator | Repository maintainer with Codex assistance |
| Tracking issue | None |

## Question

What hardware, buses, bindings, memory reservations, and firmware boundaries
are directly visible from the installed Gemian vendor kernel, without changing
the device or collecting unique identifiers?

## Provenance and environment

- OS: Debian GNU/Linux 9 (stretch), Gemian userspace.
- Kernel: `3.18.41+`, build `#7 SMP PREEMPT Fri Mar 29 10:39:03 GMT 2019`.
- Architecture: AArch64.
- Device-tree root: model `MT6797X`, compatible `mediatek,MT6797`.
- Access: SSH as the regular `gemini` user at the owner's supplied private-LAN
  address, authenticated by the owner's SSH agent.
- Boot path, target slot, vendor-tree commit, kernel config hash, and toolchain:
  not established by this read-only inventory.

## Safety assessment

The procedure was read-only. It read sysfs, procfs, device tree, kernel config,
boot log, and already-mounted debugfs data. It did not write device nodes,
change sysfs controls, bind/unbind drivers, suspend, reboot, scan unbound I2C
addresses, or read block-device contents.

Unique identifiers and private data were excluded: serials, IMEI/MEID, MAC
addresses, eMMC CID, filesystem UUIDs, keys, calibration data, firmware,
partition contents, and user files. Boot arguments and logs are sanitized by
the collector as defense in depth.

Passwordless sudo was expected, but both `sudo -n true` and `sudo -n -l`
reported that a password was required. Collection initially continued without
elevation because most relevant information was readable. The owner later
supplied the sudo password, which was entered only into an interactive prompt
and was not placed in a command, file, or repository output. This enabled a
read-only `/proc/iomem` capture. The vendor kernel has no
`/sys/kernel/debug/regulator/regulator_summary`; equivalent named-rail snapshot
data was collected from `/sys/class/regulator`. The sudo credential timestamp
was invalidated with `sudo -k` before disconnecting.

## Associated code

[`scripts/collect.sh`](scripts/collect.sh) is a Bash-only inventory collector.
Run one section from the host:

```sh
ssh gemini@DEVICE 'bash -s -- identity' < scripts/collect.sh
```

Valid sections are `identity`, `device-tree`, `buses`, `peripherals`, `debugfs`,
`kernel`, and `all`. If noninteractive sudo is actually configured, substituting
`sudo -n bash -s` may expose protected read-only resources. Review output before
saving it; the script minimizes identifiers but cannot anticipate every vendor
kernel extension.

[`scripts/decode-dt-capture.py`](scripts/decode-dt-capture.py) parses a saved
`device-tree` section, builds a phandle map, and resolves standard clock, reset,
power-domain, IOMMU, PHY, DMA, GPIO, supply, interrupt, and pinctrl references.
For example:

```sh
python3 scripts/decode-dt-capture.py device-tree.txt \
  --match 'msdc|pwrap|audio|m4u|mali|disp|dsi|usb'
```

The decoder does not translate vendor-specific property layouts or infer
missing cell counts. Unresolved values remain raw big-endian cells.

[`scripts/decode-eint-capture.py`](scripts/decode-eint-capture.py) decodes the
vendor MT6797 GPIO-to-EINT table, hardware-debounce encodings, built-in EINT
muxes, and direct-routing candidates. It can also verify an authored Linux pin
header independently against the captured table:

```sh
python3 scripts/decode-eint-capture.py device-tree.txt \
  --kernel-header /path/to/pinctrl-mtk-mt6797.h --gpio 262 --eint 176
```

The source/live boundary and the reason the vendor pinctrl map cannot be reused
directly are recorded in the [MT6797 EINT recovery experiment](../2026-07-12-mt6797-eint-recovery/README.md).

## Procedure

1. Confirm SSH access with `BatchMode=yes` and run identity collection.
2. Test noninteractive sudo only with `sudo -n`; do not prompt for a password.
3. Collect DT node topology and selected driver-facing property values,
   including register ranges, interrupts, clocks, resets, power domains,
   IOMMUs, PHYs, DMA channels, pinctrl references, GPIOs, supplies, regulator
   constraints, and storage capabilities. Phandles are included so references
   can be resolved offline.
4. Enumerate platform, I2C, SPI, MMC, USB, input, network, and block topology.
5. Read power, thermal, framebuffer, ALSA, interrupt, pinmux, clock, and kernel
   configuration data that is already exposed.
6. Cross-check bound drivers against DT labels. Treat unbound labels as
   descriptions, not verified physical components.
7. Store only the interpreted, sanitized baseline, not a bulk raw capture.

## Observations and analysis

The observation set is summarized in the durable
[Gemian hardware baseline](../../docs/hardware/gemini-gemian-baseline.md). A
fresh owner-authorized, read-only rerun on 2026-07-13 is summarized in the
[live inventory result](results/live-inventory-rerun-20260713.txt); its raw
captures remain private and Git-ignored. It confirms the vendor bindings,
USB/Type-C class absence, UART ports, thermal snapshots, regulator state, and
downstream configuration without changing the device. It
identifies the platform topology and many live vendor bindings while preserving
uncertainty around the exact retail variant, panel, cameras, alternate/unbound
sensor nodes, NFC, fingerprint, HDMI/MHL, and PMIC silicon identity.

A bounded SSH reconnect probe on 2026-07-14 is recorded in the
[reconnect result](results/live-ssh-reconnect-20260714.txt). It confirms that
the pinned mode-0600 local key and explicit identity options still reach the
same vendor runtime; its identity capture is Git-ignored and sanitized.

The vendor kernel's successful binding is useful evidence for board wiring and
component candidates. It is not evidence that those paths work on current
mainline, and it does not establish that every DT node represents populated
hardware. Runtime values such as battery percentage, temperature, active
clocks, and online CPUs are snapshots rather than stable specifications.

## Conclusion

`confirmed` that a sanitized, read-only Gemian baseline can expose enough
topology to guide focused mainline experiments. Individual component claims are
scoped by the confidence labels in the hardware document. Mainline runtime
support remains untested, so no support-matrix state was promoted.

## Follow-up

- Resolve the sudo-policy discrepancy only if future unattended protected reads
  become necessary; do not weaken access controls for routine collection.
- Repeat focused experiments for variant identity, PMIC/regulator topology,
  USB-C port mapping, panel identity, and GPIO/EINT correlations.
- For the EINT/pinctrl implementation boundary, run the [MT6797 EINT
  analyzer](../2026-07-12-mt6797-eint-recovery/scripts/analyze-mt6797-eint-contract.sh)
  and keep the [mainline design result](../2026-07-12-mt6797-eint-recovery/results/mt6797-eint-mainline-design.md)
  aligned with any new controlled interrupt test.
- Link future test records and patches from the hardware baseline.
