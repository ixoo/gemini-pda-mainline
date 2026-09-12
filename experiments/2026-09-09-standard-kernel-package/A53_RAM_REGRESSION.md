# A53 service-kernel RAM regression candidate

Status: complete private image composed and validated; exact-shell and hosted
Linux checks pass. No deployment or physical session is selected; the unresolved
Wi-Fi boot retains device custody. Collection/recovery binding and a distinct
finite session remain required before device use.

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

## Complete composition result

The [composition receipt](results/a53-service-ram-candidate.json) records the
image built from clean recipe commit
`4ce5197b3c79139baaae6dc2026c6566336dde5d` in the RE VM. The existing
Buildbox kernel was reused; no kernel compilation or device action occurred.
The complete boot image is 9,129,984 bytes, leaving 7,647,232 bytes in boot2.
Its SHA-256 is
`97c23e3f34686d8831e56f9903e109f6b9ba89cb121c88996f25411e86d5bec0`;
the exact 16 MiB padded image has SHA-256
`f185a0f2f993f8c68227f2a6e225e951ee22487d418610b9156ee1e517f56cb0`.

The LK analyzer accepted the image, paired payloads, header and load addresses.
A separate readback checked all output hashes, the complete file inventory,
private permissions and exact zero padding. Inverting the one release-string
change reproduces the original init member including metadata. All 46 other
members and the device tree compare equal to the accepted parent. The packaged
init hash matches the five-case fixture. Managed staging was removed; the final
private candidate remains in the RE VM, with no host image fetch or installation.

Local repository checks and the exact source commit's
[hosted Linux checks](https://github.com/ixoo/gemini-pda-mainline/actions/runs/34725518175)
passed. No new kernel/DT source or binding changed, so no additional kernel
build or DT schema run was needed. This is packaging and injected userspace
evidence only; it establishes no new physical support claim.

## Before a device session

Bind the collection and recovery tools to this new kernel
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
