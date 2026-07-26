# Experiment: Candidate Galileo — active MT6797 CPU8

## Record

| Field | Value |
| --- | --- |
| ID | \`2026-07-26-a72-active-galileo\` |
| Status | \`running; candidate assembled, hardware not yet tested\` |
| Subsystem | MT6797 Cortex-A72 power sequencing and PSCI CPU_ON |
| Device variant | Named Gemini PDA unit |

## Hypothesis

The vendor-observed CPU8 bring-up transaction can be used as a one-way,
fail-closed Linux provider while firmware remains owner of DVFS, HPS, idle,
thermal policy, and CPU9. If the sequence is correct, CPU8 will reach
\`online\` under the existing \`maxcpus=8\` boot contract and the exact known-good
USB Ethernet shell will remain usable.

The unique evidence behind this candidate is the prior Gemian CPU8 load trace
and the source/audit reconstruction of the SPM, TOPRGU, DA9214, SRAM-LDO,
PSCI, and MP2-DCM ordering. This is a new active-power experiment, not a
repeat of the observer or read-only candidates.

## Safety and provenance

The candidate uses the exact AO initramfs, keymap, console helpers, and AO DT
baseline that previously provided the working console, keyboard, USB Ethernet
shell, and manual reboot. The only functional kernel delta is enabling the
CPU8 provider and its PSCI hooks; CPU9 remains fail-closed and there is no
inverse/off/DVFS policy.

Assembly is storage-inert. The builder requires a validated Galileo VM package,
rebuilds the DT twice, assembles the LK Android-v0 container twice, validates
all LK gates, and emits a zero-padded 16 MiB \`boot2-padded.img\`. Installation
is a separately guarded operation that resolves logical GPT \`boot2\`, verifies
it is inactive and unmounted, preserves a full backup, writes one bounded
16 MiB image, flushes it, and verifies a full readback checksum.

## Procedure

1. Build and validate the Galileo kernel package with \`./scripts/dev-vm
   build-kernel\`.
2. Run \`scripts/build-candidate-galileo.sh\` with the exact AO artifact and
   publish the resulting candidate outside Git.
3. Install only the candidate's \`boot2-padded.img\` to inactive logical
   \`boot2\`; do not reboot automatically.
4. Boot \`boot2\` manually and capture the USB shell banner, kernel release,
   \`/proc/cpuinfo\`, CPU online mask, A72 provider logs/sysfs, and watchdog
   state. A second boot is required if the first result is inconclusive.

## Observations

Initial result: not tested on hardware. Compile/configuration and container
validation passed. Runtime evidence will be recorded in \`results/\` after the
manual boot.

## Conclusion

Not yet determined. A successful build is not hardware support.
