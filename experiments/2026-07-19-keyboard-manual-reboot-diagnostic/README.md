# Candidate X: clean tty1 and explicit manual reboot

| Field | Value |
| --- | --- |
| Experiment ID | `2026-07-19-keyboard-manual-reboot-diagnostic` |
| Candidate | X |
| Status | Build, validation, and guarded installation passed; attempt 1 booted and worked by owner report, but typed `reboot` appeared to hang |
| Device scope | Named Gemini PDA used for Candidate W |
| Baseline | Exact exported Candidate W artifact |
| Kernel/DT delta | Forced command line removes only `console=tty2`; final DTB must remain byte-exact W |
| Initramfs delta | No watchdog worker/access; independent keyboard probe, respawned tty1 shell, explicit typed `reboot` wrapper |
| Validation state | 220 non-timestamp package files matched, both final artifacts matched recursively, all 32 LK gates passed, and all 47 mutations were rejected |
| Hardware state | Exact X was fully read back and selected once; no automatic return followed typed `reboot`, recovery was by power key, and unbooted Candidate Z now occupies `boot2` |

## Why X exists

The owner-attended Candidate W run established the intended keyboard path on
this unit: the AW9523 provider and matrix driver bound, a matrix-owned event
node appeared, and physical press/release records survived for H, E, L, P, and
Enter. The owner independently reported a visible shell, a working keyboard,
and that the `TER16x32` font is the desired size. Those positive results select
W's kernel patchset, final hardware DTB, keyboard resources, polling policy,
font, rotation, CPU, storage, and networking policy as X's immutable
foundation. This is one run with limited key evidence, not repeatability, full
key coverage, or retained proof that a shell command executed. See W's
[attempt-1 runtime record](../2026-07-19-keyboard-wrrd-diagnostic/results/runtime-candidate-w-attempt-1-20260719.txt).

W's two serviceability observations did not pass. Kernel log lines remained
visibly mixed with the tty1 shell even though W requested `console=tty2`, and
W's userspace watchdog ownership/ping caused the expected 31-second reset
before the owner could do useful interactive work. There was no retained
`pass` marker, so W does not establish shell-command execution or full key
coverage.

Linux's VT console printer follows the foreground VT. Selecting a different VT
for `console=` therefore does not guarantee that framebuffer printk remains
off the foreground shell. X removes the virtual-console target entirely while
retaining `console=ttyS0,921600n8`, `/dev/kmsg`, `console-ramoops`, fbcon,
rotation, and the built-in `TER16x32` font.

## Exact retained baseline

The builder must accept only the exported directory
`candidate-W-keyboard-wrrd-final-34c41fad`. The dedicated validator pins its
complete regular-file inventory and these component identities:

- artifact `SHA256SUMS` SHA-256:
  `257b17585c171e29ae3510fdab7602aa59e4da570aa906abb8b9e5b7e8da5851`;
- raw W boot image SHA-256:
  `34c41fad1e86de05b6a1f64f7e5d9229bd26ea88d982b0a57f2b9573aeb782d4`;
- final W DTB SHA-256:
  `bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f`;
- W initramfs SHA-256:
  `3793bec7a63074b237d041bcd42e6edfccc80f0a3d7b19869abf99ee7874dac6`;
- static event helper SHA-256:
  `b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602`.

X must copy W's final DTB byte for byte. It must not use a newly packaged DTB
or alter simplefb, ramoops, watchdog hardware description, I2C5, AW9523,
matrix polling/keymap, CPU, storage, USB, or network hardware policy.

## Configuration delta

The profile
`observability-fbcon-rotation-keyboard-wrrd-manual-reboot` applies the exact W
fragment stack, followed by
[`configs/gemini-keyboard-manual-reboot.fragment`](../../configs/gemini-keyboard-manual-reboot.fragment).
Its resolved forced command line must equal W's command line after deleting
only the single `console=tty2` token. The resulting console list is exactly:

```text
console=ttyS0,921600n8
```

The package validator rejects every `console=ttyN` token and requires the
inherited `fbcon=rotate:3`, `fbcon=font:TER16x32`, `maxcpus=1`, storage
exclusions, direct MT6797 I2C match, and exact W watchdog-core policy:
`CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y` with
`CONFIG_WATCHDOG_OPEN_TIMEOUT=0`. Retaining those kernel options lets the
kernel keep a firmware-started timer serviced; X userspace does not take
watchdog ownership. As a whole-file delta gate, the validator replaces X's
single resolved `CONFIG_CMDLINE` line with W's exact tty2 line and requires
the reconstructed configuration to match W's SHA-256
`e143daa84127e2c04895c2576943dfb77ee10903c35f4d8cc9fe1dc90bf1bebb`.
This rejects any unrelated resolved-configuration change even when package
provenance is coherently refreshed.

## Initramfs contract

The deterministic archive uses exact W BusyBox and the exact W static input
helper. Its unique marker is
`GEMINI_KEYBOARD_MANUAL_REBOOT_20260719_X`; the tty1 prompt is `GEMINI-X#`.

- BusyBox `init` respawns `/bin/local-shell` on tty1.
- `/init` launches `/bin/x-probe` independently before starting BusyBox init.
- Background records go only to `/run/x-status`, `/dev/kmsg`, and ttyS0. No
  background path references tty0, tty1, tty2, or `/dev/console`.
- The archive has no watchdog program. No payload path names, opens, or pings
  `/dev/watchdog*` or the watchdog sysfs device.
- Typing `reboot` invokes the tracked `/bin/reboot` wrapper. It records the
  exact `manual_reboot=requested` marker, performs no sync or storage command,
  and calls the exact pinned BusyBox applet as `reboot -n -f`. A reboot can
  therefore happen only after the user types the command (or through an
  independent failure outside this userspace contract).

The initramfs validator parses the newc archive before extraction, rejects
unsafe or unexpected members, checks source/archive equality and output sinks,
and independently reconstructs the complete gzip stream byte for byte. It uses
a fixed private directory below `/tmp`; caller-controlled `TMPDIR` cannot place
scratch files in the selected package or W artifact.

The top-level builder records every patch, fragment, tool, validator, payload,
and builder source in a start/end repository-input snapshot. After the selected
package and W artifact pass their validators, all bytes used by assembly are
copied into a private immutable staging tree and rechecked against their pins.
Before creating the flat regular-file output manifest, the builder constructs
a second initramfs and Android-v0 container and requires byte identity. The
separate mutation harness then rebuilds the full artifact and exercises
selected-source symlinks, output races and nesting, coherent package/config
substitutions, unsafe archives, watchdog or visible-VT payload access,
automatic or syncing reboot paths, component substitutions, and final-artifact
inventory/mode changes.

## Validated artifact and guarded installation

Two clean kernel builds reproduced all 220 non-timestamp regular files exactly;
their only package difference is timestamp-derived provenance. Two complete
Candidate X assemblies are recursively identical. The selected 6,864,896-byte
Android-v0 image has SHA-256
`bf4003871daaba1faa293f2b128021d3a67d41ebf3ddff1c42463409803b9296`;
its deterministic initramfs has SHA-256
`b54ce3cd75e7947ed867165e31abbf6ee6cbac7d41d171435f99bba7825bc769`.
The exact-W final DTB remains byte-identical. The container passed all 32 LK
gates, and the mutation harness rejected all 47 intended corruptions. See the
[final build reproduction](results/final-build-reproduction-20260719.txt) and
[mutation result](results/validator-mutations-20260719.txt).

The guarded installer resolved logical `boot2` from the live GPT as
`/dev/mmcblk0p30`, while the active root was `/dev/mmcblk0p29`. It preserved a
mode-0600, Git-ignored full backup of W whose SHA-256 is
`0ff3220096aa53f792116b3899e356bc2516816c9c330309c3d81e9fe1446608`,
then wrote, synchronized, flushed, and fully read back the exact 16 MiB padded
X image. The padded image and full readback both have SHA-256
`e89d71f15465b544db163b5f0b90b456e913c38ba4d2ed49aa7bde345148c855`.
The device stayed in its known-good OS with an unchanged boot ID; no reboot or
shutdown was performed. See the [guarded write/readback
record](results/boot2-write-candidate-x-20260719.txt).

These build/install records alone establish reproducibility, static content,
and the stored bytes that were on logical `boot2`; they do not establish
runtime behavior. Attempt 1 supplies the separate runtime boundary below.

## Attempt 1 runtime

The owner manually selected X from logical `boot2` and reported that it booted
and worked before typing `reboot`. The command appeared to hang and no automatic
return was observed. The current Gemian boot reason after recovery was
`power_key`/`keypad`, supporting power-key recovery rather than an unassisted X
return. Authenticated post-recovery pstore contained zero regular files.

No exact X marker, prompt, keyboard event, shell marker, uptime marker,
`manual_reboot=requested`, or failure marker survived. The owner report passes
only X boot and pre-reboot interaction at owner-report level. It does not prove
a clean console, exact X kernel/initramfs entry, uptime beyond W's boundary, any
individual keyboard subgate, wrapper entry, reboot syscall entry, restart
handler entry, or reset assertion. The typed manual-reboot gate failed
operationally with an unknown internal boundary. See the [attempt-1 runtime
record](results/runtime-candidate-x-attempt-1-20260719.txt).

## Hypothesis and decision-changing evidence

> With no virtual kernel console and no userspace watchdog ownership, tty1
> will remain a clean, unbounded local shell while serial and ramoops preserve
> diagnostic logging. Typing `reboot` will leave the exact manual-request
> marker and issue one BusyBox no-sync forced reboot.

| Result | Interpretation | Next action |
| --- | --- | --- |
| No exact X marker after a confirmed selection/recovery attempt | X entry is unattributable | Do not repeat an identical artifact; add an independent observation only if it can change the next decision |
| Exact X entry and `GEMINI-X#` remain visible without interleaved printk | Serial-only kernel-console isolation passes | Preserve the command line and test useful shell commands separately |
| Printk still appears on tty1 | The output is not explained by a registered VT console target | Identify the writer from exact text before changing log level or tty policy |
| X entry survives but AW9523, matrix, or the exact event node regresses | A retained W keyboard gate changed unexpectedly | Reject X and compare the exact kernel, DTB, and initramfs inputs before any new keyboard change |
| X remains at the prompt for at least 45 seconds | The session has passed W's approximately 31-second automatic-reset boundary once | Continue with the typed keyboard command; do not infer longer-term stability |
| `echo KEYBOARD-X-OK` is accepted and prints exact `KEYBOARD-X-OK` | The attended command/keyboard gate passes once | Preserve the exact command result separately from optional broader key observations |
| Device resets before a typed `reboot`, with no manual-request marker | The reset is outside X's userspace watchdog path | Recover ramoops/boot reason and audit inherited timer or another reset source |
| Exact `manual_reboot=requested` survives | The typed wrapper was reached once | Record this independently; it does not prove that the restart completed |
| Gemian returns after the typed request | The restart/return gate passes once | Correlate it with the separate request marker; do not infer clean filesystem shutdown because `-n` deliberately skips sync |
| `reboot` returns to the shell with a failure marker | BusyBox forced-restart syscall failed | Retain the shell and investigate only restart syscall/platform behavior |

This experiment does not test key coverage, rollover, suspend/wake, native
display, storage, network serviceability, or clean shutdown.

## Successor boundary

Do not repeat unchanged X merely to localize the generic restart hang. The
[restart-path audit](../2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/results/restart-path-audit-20260720.txt)
shows that BusyBox `reboot -n -f` correctly enters the no-sync reboot syscall,
after which arm64 quiesces and runs PSCI before the MediaTek watchdog restart
handler. Empty pstore cannot distinguish those branches, and SysRq reaches the
same `machine_restart` chain.

[Candidate Y](../2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/README.md)
therefore retains X's exact kernel, DTB, and configuration while changing only
four initramfs members. Its typed wrapper performs an exact `mtk-wdt` preflight,
sends one handoff ping, holds the descriptor, and waits visibly for the W-proven
31-second hardware expiry without `reboot(2)`, sync, or fallback. An exact
BusyBox audit subsequently established that bare `reboot` bypasses that wrapper
and that watchdog-open failure cannot reach its promised refusal. Y was
rejected before boot and never selected. See the decisive [command-dispatch
audit](../2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/results/preboot-command-dispatch-audit-20260720.txt).

[Candidate Z](../2026-07-19-keyboard-reboot-dispatch-diagnostic/README.md) is
the latest validated and installed successor. It retains exact Y's
kernel/DT/config and makes command dispatch plus watchdog-open failure
attributable through a five-member initramfs delta. Two complete builds match
recursively, the exact-BusyBox Linux-arm64 dispatch gate, 32/32 LK gates, and
75/75 mutations passed, and its full logical-`boot2` readback matches padded
SHA-256
`ba21e6424f94c82f14fd51b5681eea68d6cf09e9177e4f9ca2061c9f129abb40`.
Z has not been booted. X therefore remains the last owner-tested artifact. See
the [Z build](../2026-07-19-keyboard-reboot-dispatch-diagnostic/results/build-validation-20260720.txt),
[dispatch validation](../2026-07-19-keyboard-reboot-dispatch-diagnostic/results/ash-dispatch-validation-20260720.txt),
[mutations](../2026-07-19-keyboard-reboot-dispatch-diagnostic/results/validator-mutations-20260720.txt),
and [write/readback](../2026-07-19-keyboard-reboot-dispatch-diagnostic/results/boot2-write-candidate-z-20260720.txt).
