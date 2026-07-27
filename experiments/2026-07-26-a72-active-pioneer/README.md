# Experiment: Candidate Pioneer — active MT6797 CPU8

## Record

| Field | Value |
| --- | --- |
| ID | \`2026-07-26-a72-active-pioneer\` |
| Status | \`installed to inactive boot2; awaiting manual boot\` |
| Subsystem | MT6797 Cortex-A72 power sequencing and PSCI CPU_ON |
| Device variant | Named Gemini PDA unit |

## Hypothesis

The vendor-observed CPU8 bring-up transaction can be used as a one-way,
fail-closed Linux provider while firmware remains owner of DVFS, HPS, idle,
thermal policy, and CPU9. If the sequence is correct, CPU8 will reach
\`online\` under a \`maxcpus=9\` boot contract that requests CPU8 after CPU0--7,
while CPU9 remains unrequested, and the exact known-good USB Ethernet shell will
remain usable.

The unique evidence behind this candidate is the prior Gemian CPU8 load trace,
the live DA9214 capture, and the source/audit reconstruction of the SPM, TOPRGU, DA9214, SRAM-LDO,
PSCI, and MP2-DCM ordering. This is a new active-power experiment, not a
repeat of the observer or read-only candidates.

## Safety and provenance

The candidate uses the exact AO initramfs, keymap, console helpers, and AO DT
baseline that previously provided the working console, keyboard, USB Ethernet
shell, and manual reboot. The only functional kernel delta is enabling the
CPU8 provider and its PSCI hooks; CPU9 remains fail-closed and there is no
inverse/off/DVFS policy.

Assembly is storage-inert. The builder requires a validated Pioneer VM package,
rebuilds the DT twice, assembles the LK Android-v0 container twice, validates
all LK gates, and emits a zero-padded 16 MiB \`boot2-padded.img\`. Installation
is a separately guarded operation that resolves logical GPT \`boot2\`, verifies
it is inactive and unmounted, preserves a full backup, writes one bounded
16 MiB image, flushes it, and verifies a full readback checksum.

## Procedure

1. Build and validate the Pioneer kernel package with \`./scripts/dev-vm
   build-kernel\`.
2. Run \`scripts/build-candidate-pioneer.sh\` with the exact AO artifact and
   publish the resulting candidate outside Git.
3. Install only the candidate's \`boot2-padded.img\` to inactive logical
   \`boot2\`; do not reboot automatically.
4. Boot \`boot2\` manually and capture the USB shell banner, kernel release,
   \`/proc/cpuinfo\`, CPU online mask, A72 provider logs/sysfs, and watchdog
   state. A second boot is required if the first result is inconclusive.

## Observations

The preceding Galileo image was caught in pre-boot review with
\`maxcpus=8\`, which could request only CPU0--7; it was never booted. The
corrected image changes only that boundary to \`maxcpus=9\`. Compile/configuration
and container validation passed for the corrected image. Pioneer adds an active A72
DT provider node, exact CPU8/CPU9/watchdog/BUCKB phandle references, and a
kernel-native late hotplug retry through \`add_cpu(8)\` after platform-driver
initialization. The new DA9214 patch preserves the legacy driver’s second
PAGE_CON selector byte (0x82) while retaining the console-preserving
write-only transport. The image was installed to inactive logical \`boot2\` with
an exact full-partition readback; see
\`results/install-pioneer-boot2-20260726.txt\`. Runtime evidence will be
recorded in \`results/\` after boot.

## Conclusion

Not yet determined. A successful build is not hardware support.
