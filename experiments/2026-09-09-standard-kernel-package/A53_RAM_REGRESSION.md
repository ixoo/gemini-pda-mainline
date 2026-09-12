# A53 service-kernel RAM regression candidate

Status: composition recipe and exact-shell tests prepared. Complete image
composition and its receipt remain pending. No deployment or physical session
is selected; the unresolved Wi-Fi boot retains device custody.

## Purpose and bounded change

The [service-facilities kernel](A53_SERVICE_FACILITIES.md) passes the
[Debian QEMU runtime](A53_DEBIAN_QEMU.md), but has not run on the PDA. Its
first board regression can reuse the accepted authenticated RAM environment,
independently of future persistent-root storage selection. This is a step
toward the A53 integration baseline, not a distribution installation or the
ten-cold-boot release gate.

The [composition recipe](build-a53-ram-candidate.py) requires the exact
Buildbox package from `ac6cf1774966ff282449881c5337d9888eab1d5a` and the
[accepted console candidate](../2026-09-08-keyboard-console-ownership/validation.json).
It checks the complete kernel package inventory and all six accepted parent
file hashes. The parent image is identified by its full digest, never its
timestamp or a mutable profile name.

Only `/init` changes within the 47-member RAM archive: its one exact kernel
release check becomes `7.1.3-gemini-a53-service-facilities`. All other member
bytes and metadata remain identical, including private authentication keys,
console ownership, CPU0–7 gates, bounded logging and recovery helpers. The
accepted device tree remains byte-identical; it has no embedded build-identity
property requiring replacement. No storage mount, peripheral activation,
hotplug request or automatic recovery is added to startup.

The recipe uses the existing archive parser/serializer and Android-v0
serializer/analyzer. It checks archive round-trip equality, actual kernel
decompression, logger-sealing syscall linkage, exact LK addresses/format and
16 MiB partition fit. Output is private, contains a secret host key and is
never published. Composition itself has no device access.

From a clean source checkout in the RE VM, provide the accepted parent and
validated kernel package as explicit paths:

```sh
python3 experiments/2026-09-09-standard-kernel-package/build-a53-ram-candidate.py \
  --kernel-package "$A53_KERNEL_PACKAGE" \
  --parent "$A53_ACCEPTED_RAM_CANDIDATE" \
  --output "$A53_NEW_RAM_CANDIDATE"
```

The output parent must exist. An occupied output is refused. The locked managed
stage contains regenerable composition data only; a later invocation removes
an abandoned stage without deleting an existing final candidate.

## Focused validation

The [init test receipt](results/a53-service-ram-init.json) records five cases
using the exact accepted ARM64 BusyBox under QEMU. The existing shell fixture's
effect proxy supplies the chosen kernel release; mount, network, console,
logger and PID1 effects remain injected. The new release launches exactly the
two expected services and init, all with null standard descriptors and
`CONSOLE=/dev/null`. The old release, an unrelated release, a wrong CPU mask and
a failed devtmpfs mount each hold before any service launch. Shell syntax and
the complete archive member/metadata round-trip pass.

The prior authentication and logging results remain evidence for the unchanged
userspace bytes. These five tests do not rerun Dropbear authentication, exercise
real device nodes, test the new kernel's PID1 path or establish board support.

## Before a device session

After composition, bind the collection and recovery tools to this new kernel
and candidate. Historical baseline tools pin the old release; they must not be
used unchanged or have their closed validation receipts reclassified. Freeze
a distinct finite session, including its hypothesis, observation branches,
authenticated identity, bounded log preservation and reviewed normal recovery.
Do not reactivate consumed keyboard or eMMC observation budgets.

The proposed board question is whether the service configuration preserves
CPU0–7 startup, authenticated USB, console availability and complete logging
on the existing device description. Namespace/BPF behavior on the PDA needs
its own declared measurement; the RAM shell alone cannot demonstrate Debian
service behavior. Missing identity or logs must remain inconclusive.

Resolve the currently selected Wi-Fi session before installation. Any later
boot2 write still uses the reviewed live-GPT guard, full readback and clean
shutdown, followed by owner-operated physical selection. No installation,
collector or physical-selection budget is supplied by this preparation record.
