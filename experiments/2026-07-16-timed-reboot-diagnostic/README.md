# Experiment: fixed-delay reboot marker

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-16-timed-reboot-diagnostic` |
| Status | One runtime attempt transitioned after an estimated 5–10 seconds; this strongly supports `/init` execution, but automatic restart was not achieved |
| Subsystem | Retained LK handoff, early userspace, generic kernel restart path |
| Device variant | Current Gemini PDA unit; exact retail sub-variant not independently established |
| Date(s) | 2026-07-16 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Did the dark, steady, non-enumerating USB candidate execute `/init` despite
providing no observable UART, display, or USB channel?

The follow-up changes one regular file in the initramfs through a tracked
patch: `/init` arms `/bin/busybox reboot -f` in a child process before any
mount or device-node dependency, with a fixed 10-second delay. A reset
attributable to that exact candidate would prove Linux scheduled the initramfs
far enough to execute the timer and generic reboot syscall. Absence of a reset
would remain ambiguous between pre-init failure and a nonfunctional platform
restart hook.

## Provenance and environment

The baseline is the exact first USB diagnostic candidate:

```text
candidate sha256: 41b97a83c53e76cc0fc117660dd4f7189b397f63ea5f6545fc00ef89af0263ca
initramfs sha256: 6468beafdec6343aa9ee61fc3e72fedf777162a13db8981eb9429babbd194e00
DTB sha256:       5717a8c2f3f4f02533fae4dad8c9f9137f0f78cb0986fd6908a74309722e7db4
```

That image was written and fully read back from `boot2`. The device remained
dark and steady, while two bounded macOS checks observed no USB child device.
See the [USB runtime result](../2026-07-16-usb-gadget-diagnostic/results/runtime-usb-enumeration-attempt-20260716.txt).

## Safety assessment

The build scripts only create and parse files and have no device, partition,
adb, fastboot, MediaTek, or flashing interface. The candidate retains the
storage-disabled USB diagnostic kernel and read-only procfs/sysfs policy.

Unlike the baseline, booting this candidate intentionally requests a system
reset 10 seconds after `/init` starts. The short fixed delay keeps the attended
test bounded; it is not a claim about the unknown handed-off watchdog state or
the restart mechanism that will ultimately handle the request. If LK preserves
the `boot2` selection across reset, the device could enter a short reboot loop.
A future test must therefore be attended with the known-good primary/recovery
path ready, must stop after the first attributable reset, and must not be left
running unattended. Candidate generation does not authorize a device write or
boot. Primary `boot`, preloader, NVRAM, and GPT remain protected.

This unit currently has neither working UART nor a proven display/USB channel
for this kernel. Consequently, the proposed boot does not satisfy the normal
UART prerequisite in [`docs/SAFETY.md`](../../docs/SAFETY.md). On 2026-07-16,
after that conflict and the reboot-loop risk were stated explicitly, the owner
directed: `Copy to boot2`. This approves a one-time alternative-recovery
exception and this specific non-primary `boot2` write; it does not authorize a
primary-slot write or an unattended boot.

The exception relies on the independently working primary Gemian boot, the
proven MediaTek read/restore path, the existing private partition backups, and
a new full `boot2` backup before the write. Any boot must be attended. Stop
after the first attributable reset and do not deliberately reselect `boot2`.
If selection persists and a loop begins, unplug USB/power, hold the power key
to force the unit off, and restore `boot2` from the new backup through Gemian
or the proven MediaTek path before any repeat. Unexpected heat, charging
behavior, or changed recovery behavior remains an immediate stop condition.

## Associated code

- `initramfs/timed-reboot.patch`: the exact addition to the tested USB `/init`
  that arms an early 10-second forced-reboot child.
- `scripts/build-initramfs.sh`: rebuilds the same archive tree using the same
  static BusyBox and USB shell.
- `scripts/validate-initramfs-delta.sh`: requires identical archive paths,
  types, modes, links, and regular-file bytes except `/init`.
- `scripts/validate-boot-delta.py`: requires identical Android header fields,
  kernel, appended DTB, and padding except the ramdisk size/canonical ID.
- `scripts/build-timed-reboot-candidate.sh`: rebuilds and hash-pins the tested
  USB baseline before producing the non-flashing variant.
- `results/runtime-timed-reboot-attempt-20260716.txt`: sanitized owner
  observation, post-recovery reason flags, and conservative interpretation.
- `results/restart-path-source-audit-20260716.txt`: exact BusyBox, PSCI,
  TOPRGU, and Gemian reset-policy comparison.

## Procedure

1. In the development VM, invoke the builder with the exact validated USB
   kernel package and a new explicit output directory.
2. Verify `SHA256SUMS`, LK parsing, the initramfs single-file delta, and the
   Android ramdisk-only container delta.
3. Rebuild into a second new directory and require a recursive byte match.
4. After separate authorization, resolve and back up `boot2`, write the exact
   full-partition image, synchronize and flush it, then require a complete
   read-back hash match. This was completed on 2026-07-16.

Under this explicit exception, the owner selected `boot2` for one attended
hardware test.
The delay begins only when `/init` runs, so wall time from the button press will
be longer than 10 seconds. Stop after one reset. A return to the normal stock
splash within a repeatable window is positive evidence for `/init`; a dark
steady state beyond two minutes is negative only for the combined
init-plus-restart-marker path. Any repeated loop is a stop condition.

## Observations

The build produced `gemini-lk-rebootdiag.boot.img` (6,520,832 bytes):

```text
candidate sha256:      61fb961a8de48a7e0a9acf83447b90cc7012b741a10b0707cb7e73d33e8081c8
initramfs sha256:      8a63939caf76473ad8d688e923155d2b9800bf25cd2017c36acafb08a11bb71b
kernel payload sha256: 96488981298c72554243c13db57640196099c307c2524483d16ce4dbc8650aa3
DTB sha256:            5717a8c2f3f4f02533fae4dad8c9f9137f0f78cb0986fd6908a74309722e7db4
```

The LK parser passed. The archive-delta validator proved that `/init` is the
only differing initramfs file and that its bytes equal the hash-pinned tested
USB `/init` plus `initramfs/timed-reboot.patch`, applied with no offset or
fuzz. The Android-v0 delta validator proved that the kernel plus appended DTB
is byte-identical to the USB candidate; only the ramdisk and the consequent
ramdisk-size/canonical-ID header fields differ. It independently recomputed
both canonical Android-v0 IDs.

Two independent output directories matched recursively. `SHA256SUMS` passed
in the VM and again after export to the Git-ignored host directory:

```text
artifacts/vm-export/boot-candidates/
  gemini-rebootdiag-20260716-D-3d92a7e9-fdf1d345/
```

The complete static record is
[results/timed-reboot-candidate-20260716.txt](results/timed-reboot-candidate-20260716.txt).
The candidate was zero-extended to the exact 16 MiB `boot2` size, written to
`/dev/mmcblk0p30`, synchronized, flushed, and read back in full. The resulting
partition SHA-256 is
`7ba69e5ed6ae81fcc9d74fa78fdd8bc53431af83011dcb3f58bed5d4cef98089`.
The prior `boot2` bytes were first saved privately under the Git-ignored
device-partition artifacts directory with mode `0600`. Primary `boot` and the
running Gemian root were not touched.

The explicit exception, target preflight, backup, write, synchronization, and
full read-back evidence are tracked separately in
[results/boot2-write-20260716.txt](results/boot2-write-20260716.txt).

The owner then selected `boot2`. The screen was dark while its backlight stayed
on for a while; the backlight later turned off and the device entered an
off-like state. No automatic reboot or boot loop followed. The owner had to
press the power button to start the device again. The owner later estimated
5–10 seconds from backlight-on to backlight-off. This was recollection rather
than a stopwatch measurement, but it is compatible with the nominal 10-second
`/init` sleep.

The following manually started Gemian boot reported `androidboot.bootreason`
as `power_key` and `/sys/bootinfo/powerup_reason` as `keypad`. Its PMIC
battery-removal, PMIC watchdog-reboot, AED watchdog,
FIQ-step, and exception-type indicators were all zero. `/sys/fs/pstore` was
empty, and the vendor `last_kmsg` ram-console header reported only zero status.
The private raw capture contains device identifiers and remains mode `0600`
under the Git-ignored artifacts tree. The sanitized runtime record is
[results/runtime-timed-reboot-attempt-20260716.txt](results/runtime-timed-reboot-attempt-20260716.txt).

## Analysis

The static evidence isolates the intended runtime variable: the exact USB
candidate kernel and DTB are retained, while the replacement `/init` starts a
10-second child timer that calls `/bin/busybox reboot -f`. The baseline stayed
dark and steady; the one-file initramfs variant instead reached a later
backlight-off, off-like state after an estimated 5–10 seconds. The estimate is
compatible with the 10-second sleep. Together with the one-file delta, this is
strong positive evidence for kernel scheduling, initramfs `/init`, the timer,
and entry into the restart path, but it is not direct confirmation: the timing
was not measured by stopwatch, no candidate log survived, and the test has not
been repeated.

The exact static BusyBox `reboot -f` requests `RB_AUTOBOOT`, not poweroff. In
Linux 7.1.3 the arm64 restart chain invokes PSCI `SYSTEM_RESET` first and the
MediaTek TOPRGU watchdog restart handler if PSCI returns. The candidate has no
poweroff node or enabled PMIC poweroff driver.

The source comparison exposes a more specific MT6797 discrepancy. Mainline's
TOPRGU handler writes software reset but preserves mode bit 4. Gemian names the
same bit `AUTO_RESTART`, documents `1` as bypassing the power key, and sets it
for a normal reboot before software reset. Therefore three off-like outcomes
remain: PSCI itself produced an off or key-gated reset; PSCI returned and
TOPRGU reset succeeded with bit 4 clear, leaving the unit waiting for the power
key; or TOPRGU reset did not assert and its handler looped with the system
already quiesced. The second is a concrete, source-backed match for the
observation and is now the leading discrepancy, but the test does not prove
which handler ran. See the
[restart-path source audit](results/restart-path-source-audit-20260716.txt).

The following power-key boot's zero watchdog/exception indicators establish
only that Gemian did not report a watchdog/crash boot. They are compatible with
a successful software reset into a key-gated state. An empty pstore is also
non-diagnostic because the diagnostic DTB reserves the vendor pstore range
without a `ramoops` backend and the candidate has `CONFIG_PSTORE_RAM=y` but not
`CONFIG_PSTORE_CONSOLE`.

## Conclusion

The fixed-delay reboot candidate is reproducible, durably present on `boot2`,
and fully verified by read-back. Its first runtime attempt is the strongest
evidence so far that this mainline kernel reached external initramfs `/init`.
The 5–10-second estimate materially strengthens that conclusion, but it remains
indirect and unrepeated rather than confirmed. Automatic restart was not
achieved. Physical poweroff, a successful key-gated reset, and a
quiesced failed restart handler remain unresolved; the inherited TOPRGU bit-4
policy is the strongest concrete discrepancy. This does not promote any
support-matrix entry to working.

## Follow-up

On any separately authorized repeat, measure backlight-on to backlight-off with
a stopwatch. First isolate PSCI `SYSTEM_RESET` from the TOPRGU watchdog fallback
and test the bit-4 bypass-key policy before using reboot as an attributable
marker again. Any repeat requires a fresh explicit instruction and the attended
stop procedure above. Keep USB as a later initialized subsystem; do not change
its driver based on this restart result.
