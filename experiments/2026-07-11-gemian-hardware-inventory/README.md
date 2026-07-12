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

## Procedure

1. Confirm SSH access with `BatchMode=yes` and run identity collection.
2. Test noninteractive sudo only with `sudo -n`; do not prompt for a password.
3. Collect DT node topology and selected properties.
4. Enumerate platform, I2C, SPI, MMC, USB, input, network, and block topology.
5. Read power, thermal, framebuffer, ALSA, interrupt, pinmux, clock, and kernel
   configuration data that is already exposed.
6. Cross-check bound drivers against DT labels. Treat unbound labels as
   descriptions, not verified physical components.
7. Store only the interpreted, sanitized baseline, not a bulk raw capture.

## Observations and analysis

The observation set is summarized in the durable
[Gemian hardware baseline](../../docs/hardware/gemini-gemian-baseline.md). It
identifies the platform topology and many live vendor bindings while preserving
uncertainty around the exact retail variant, panel, cameras, alternate/unbound
sensor nodes, NFC, fingerprint, HDMI/MHL, and PMIC silicon identity.

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
- Link future test records and patches from the hardware baseline.
