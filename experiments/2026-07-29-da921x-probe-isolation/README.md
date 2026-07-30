# DA921x automatic-probe boot isolation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-29-da921x-probe-isolation` |
| Status | `attempt 1 serviceable; automatic child path implicated` |
| Subsystem | regulator, I2C, arm64 Device Tree |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-07-29 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 serviceability regression |

## Question or hypothesis

Did Gate 3 attempt 1 fail because the new DA921x child automatically probed
during boot, or because of another part of the rebuilt kernel, read-only I2C6
oracle, or Android boot container?

This diagnostic preserves the exact Gate 3 `Image.gz`, configuration,
serviceability initramfs, I2C6 controller description, read-only oracle, LK
name, command line, and container layout. Its sole semantic DT change adds
`status = "disabled"` to `/i2c@1100e000/regulator@68`, preventing creation and
automatic probing of that one child.

## Safety assessment

The candidate adds no hardware operation or writable control. Disabling the
child removes the fourteen automatic identification reads attempted by the
Gate 3 design; it does not enable a provider, consumer, register write, A72
request, retry, reset, or transfer trigger.

Installation may target only live-GPT-resolved logical `boot2` in Gemian after
the full current checksum matches exact failed Gate 3. The standing policy
records that predecessor checksum without creating a fresh partition backup,
requires stable power and a complete post-write readback checksum, and then
shuts the device down cleanly for owner selection. It never writes another
partition or reboots automatically.

## Associated code

- `scripts/build-isolation-dtb.sh`: exact-hash-pinned, single-property DT
  derivation
- `scripts/build-candidate.sh`: duplicate deterministic Android-v0 assembly and
  LK validation from exact Gate 3 components
- `scripts/install-boot2.sh`: exact-candidate guarded installation with no
  fresh predecessor backup, a complete independent readback, and clean
  post-success shutdown
- `results/pre-boot-hypothesis.txt`: predeclared decision table

## Decision

- A serviceable boot implicates the enabled child’s automatic creation/probe
  path and keeps Gate 3 in the driver/I2C integration layer. It does not alone
  distinguish client creation, probe timing, or the fourteen-read driver logic.
- Another pre-serviceability watchdog-class return moves suspicion away from
  the child probe to the preserved rebuilt-kernel/oracle/container boundary.
- Either result forbids an unchanged repeat and does not permit provider or A72
  work.

## Observations

Two independent derivations produced byte- and mode-identical artifact trees.
The raw Android-v0 image is
`1d69be035044b4daea53fb3754294ee85862bb7259feb764e2d48e667b2cb65e`;
the exact 16 MiB image is
`b726b1d86ed5fa68b221a7f3ea25ed068a455f143a97098b15c26552e6713baa`.
All 32 LK gates passed.

Decompiling the Gate 3 and isolation DTs produced exactly one semantic diff:
`status = "disabled"` on `/i2c@1100e000/regulator@68`. The exact Gate 3
`Image.gz`, configuration, initramfs, and all other DT semantics are preserved.
See `results/offline-validation.txt`.

The guarded installer resolved logical `boot2` from the live GPT as
`/dev/mmcblk0p30` while the active Gemian root remained `/dev/mmcblk0p29`.
Battery was present at 100 percent with `Good` health. The full predecessor
checksum matched exact failed Gate 3. Under the standing policy, no fresh
partition backup was created. The write was synced and flushed, and a complete
independent readback matched the exact padded isolation candidate. The
temporary readback was removed. The device then shut down cleanly and became
unreachable without rebooting. See `results/install-boot2-20260729.txt`.

On attempt 1, the owner selected `boot2` and reported that boot appeared
healthy, USB was available, and the console was delayed. The direct USB
netcat endpoint then provided an unauthenticated, link-local root shell as
designed. Exact runtime identity was `7.1.3-gemini-da921x-life`, CPUs 0--7
were online, and CPUs 8--9 remained offline.

The live DT contained the exact legacy child with `status = "disabled"`.
No `0x68` I2C client or bound driver link existed and no DA921x identity log
was emitted. I2C6 handoff was ready, while its transfer, DMA, nonzero-start,
IRQ, and every lifecycle-oracle counter remained zero. USB was configured and
up, one `keyboard-matrix` input existed, `/dev/tty1` was present, and the
established fatal-log and I2C-timeout signatures were both zero. Runtime
collection performed no device-partition read or write and triggered no
driver bind or transfer. See
`results/runtime-candidate-probe-disabled-attempt-1-20260729.txt`.

## Conclusion

Attempt 1 passes the serviceability discriminator. Because the exact failed
Gate 3 kernel, oracle, initramfs, controller description, and container
contract become serviceable when only the child is disabled, the enabled
DA921x child’s automatic creation/probe path is implicated. This result does
not distinguish client creation, early probe timing, or the fourteen-read
probe logic. It supplies no bind/unbind lifecycle result and Gate 3 remains
open.

## Follow-up

Do not repeat this exact candidate. Design a post-serviceability discriminator
that keeps the child inactive during boot and makes the identification driver
available as an explicitly invoked module only after console and USB gates
pass. That later experiment must predeclare the exact load, probe, lifecycle,
and zero-write evidence before another boot.
