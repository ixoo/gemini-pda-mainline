# One bounded post-START Wi-Fi capability query

The [WMT-prepared runtime](../2026-09-29-mt6797-wmt-before-start/results/runtime-3.json)
completed the two EMI copies, two ordinary HIF transfers and one firmware START.
WCIR reported firmware ready without the earlier workqueue panic. The session
still had no normal command/reply exchange, network interface or traffic.

This candidate adds one source-pinned gen3 capability query immediately after
that ready observation. The exact [normal-command contract](../2026-09-05-mt6797-wifi-contract/NORMAL_COMMAND.md)
uses a 124-byte zero-filled CID `0x80` request, a one-page normal TC4 debit,
port-1 WRPLR length 124, a 128-byte PIO receive span, and a matching sequence,
event ID and packet type. The driver has no `Tc4Page` override or other normal
command user, so its new software ledger uses the selected vendor default of
26 pages, independently of INIT's 104-page pools. There is no refill or retry.
The capability fields are observations, not proof of firmware provenance or
calibration. MAC, date and reserved reply bytes are never logged.

The patch requires the held function-1 mapping, driver ownership, START-ready
state and an empty WRPLR before submission. It shares INIT's sequence history,
uses sequence 4 after the selected two section commands and START sequence 3,
and makes one attempt under a one-second absolute deadline. Unexpected port-0
data, malformed port-1 length or reply, bus error or deadline poisons the HIF
session. The firmware-ready record remains separate from the query result.
No NVRAM command, radio command, packet DMA, network interface or calibration
write is enabled.

## Build and boot decision

Profile `mt6797-a53-wifi-capability-probe` adds only patch 0053 and a distinct
local version to the last firmware-ready profile. Its hypothesis is that the
running firmware accepts this bounded normal command and returns a matching
capability event. A full Buildbox kernel build, exact candidate assembly and
validated boot2 installation are required before a physical boot. The
candidate should retain the previously booted board DT and private RAM root,
with only the release identity updated. The owner selects boot2 physically
after clean shutdown; the direct USB session must verify the new boot ID and
release before the one-shot WMT/START trigger.

If WRPLR is nonempty before transmission, do not send and preserve the log to
identify the event owner. A TX or reply error is a terminal result for this
boot, not grounds to repeat the trigger. If the reply passes, retain only the
seven non-private capability fields and inspect calibration applicability and
the packet path separately. In every branch preserve the complete private log,
run the A53 regression if the boot survives, then use the reviewed changed-boot
Gemian return. A panic instead requires retained evidence and recovery before
another candidate. Success here would demonstrate one command/reply exchange,
not working Wi-Fi.

## Offline validation

The new kernel patch applies to the exact prepared Buildbox source. A focused
host test at [`tests/test-capability.c`](tests/test-capability.c) compiles the
actual patched HIF core with the existing test compatibility header and checks
the literal PIO sequence, all 69 injected scalar access failures, an occupied
receive queue, malformed lengths and sequence, a missing-reply timeout and
one-attempt behavior. The existing HIF core host suite also passes with the
patched source. These tests simulate ordered MMIO and cannot prove hardware
response or calibration. Kernel build and device result are pending.

The [Buildbox package and offline candidate](results/build.json) passed for
commit `870cf3653783537ae15a4383cf5bd89e0b430e05`. The private RAM root
changed only `/init`'s expected release; its 52-member round trip preserved
the firmware hash. The resulting [sanitized candidate receipt](results/candidate.json)
pins full boot2 SHA-256
`fb7f09828cbc32da40f4110c5f84fca3ba85d1fc71be57f877e43d658c485bb5`
and the same booted board DT SHA-256
`cef9373ea3aa0e1a8a45a13b953ae95e48939b211e41a73052543be784ee3214`.
The guarded installer is bound to the last verified boot2 predecessor
`42c3c298b88e31757a7d1c8e785afe3494a10937e70bb87d2e6bb31704f2073e`
and live known-good Gemian boot `2a58b4d3-9bb7-4844-9bea-1effc72122a1`.
Its offline validation, Bash syntax and ShellCheck pass. Installation, physical
selection and runtime observation remain pending.
