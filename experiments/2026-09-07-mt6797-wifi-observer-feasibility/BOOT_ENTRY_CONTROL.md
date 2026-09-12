# Export-kernel boot-entry control

Status: passed on device. The exact PID1 marker survived the normal return to
authenticated Gemian. The one-selection budget is consumed. This
is one distinct control after the inconclusive [second export
attempt](EXPORT_ATTEMPT_2.md) and the successful [normal Gemian restart
retention test](RETENTION_RESET_COMPARISON.md). It does not repeat either boot.

## Hypothesis and decision

The same 46-patch kernel may reach a minimal BusyBox PID1 even though the full
export startup produced no observable USB or retained marker. One marker
followed by the normal kernel restart path tests that possibility and whether
this particular kernel can return with console evidence. Gemian's successful
retention control motivates this path; it does not prove candidate retention.

After one physical boot2 selection:

* A complete matching marker in the next Gemian console proves this control
  reached its final userspace stage, and that its marker survived the return.
  Continue diagnosis of the full export startup using that evidence.
* A candidate-attributable kernel log without the marker may locate an earlier
  failure. Interpret only the stages actually present.
* A return without attributable evidence does not prove which kernel ran or
  where the marker was lost. No return also remains inconclusive: the control
  cannot recover a pre-PID1 hang, a failed identity/log check or a blocked normal
  restart. Do not repeat this image or infer an init failure from silence.

The changed kernel boot UUID in a marker must differ from both the preceding
and returned Gemian UUIDs. Match the exact control UUID and marker stage; mere
presence of a pstore file is insufficient.

## Selected bytes and effect budget

The [receipt](results/boot-entry-control-20260912.json) identifies the prepared
container. Its kernel field is exactly the previously built `b69963d0…a0bbb`
field from project commit `c9a8d30423da33a7fae8c95f2c0d9b5f96b90ee7`.
The kernel, DT, firmware/calibration files and compact runtime are unchanged.
The archive still contains 723 members. Only `/init`, the session manifest and
the shared Python validator differ; Python is not executed by this control.
The boot arguments retain the same settings with a new fixed control identity.
The raw container remains 16,295,936 bytes, padded to the exact 16,777,216-byte
boot2 size. The inherited filename `export.boot.img` denotes its kernel family;
the manifest explicitly says `startup_action: boot-entry`.

[`boot-entry-init.sh`](boot-entry-init.sh) permits only PID1. It mounts devtmpfs
and proc, checks AArch64/Linux `3.18.41+`, validates the boot UUID and exact
ordered diagnostic arguments, and rejects duplicates or a SysRq override.
It verifies the non-symlink `1:11` kernel-log node and opens it once. It makes
one `printf` invocation with this 138-byte record, including prefix/newline:

```text
<11>wifi-boot-entry-v1 control=7f21b732-da47-4245-ad83-e985044054a6 boot=BOOT_UUID stage=before-normal-restart
```

`BOOT_UUID` is the current 36-character kernel UUID. This ordinary console
record uses the existing pstore console path and shares its
[registration limitation](BOOTSTRAP_DIAGNOSTICS.md#registration-dependency-and-layout-audit).
There is no raw PMSG read, clear, capture claim, controller takeover, firmware
load, WMT request, USB setup or background userspace process. The native
kernel's existing initialization still runs.

After the marker succeeds, traps are disabled and BusyBox `reboot -f` is called
once as a child of PID1. Here `-f` selects the restart syscall instead of an
init-service request; the kernel still executes its normal reboot notifiers,
device shutdown and architecture restart. This is not an emergency-restart
request or a direct register writer. The existing [restart gate](RESTART_GATE.md)
allows the normal path before capture claims ownership. No capture claim is
made by this control. A returned call parks without retry. Any earlier caught
failure also parks; this is not a general watchdog or guaranteed recovery.

## Offline validation and device procedure

The exact compact-runtime BusyBox is 1,846,504 bytes, SHA-256
`61781806ad3650b0b9d2b3fc6971e2bffdca967af1a95375abd0578bafff14fb`.
A non-root RE-VM trace injected the sync result and an `EPERM` restart result.
It showed one sync and one `LINUX_REBOOT_CMD_RESTART`, no signal to PID1, and
exit status 1. No actual VM restart occurred. Its attempted wtmp open is a
userspace accounting operation; this control mounts no storage filesystem.

The [ARM64 shell test](test-boot-entry-init.py) ran eight paths in private
mount/PID namespaces with the real pinned BusyBox: success with a returned
restart, wrong session, duplicate panic argument, SysRq override, wrong kernel,
invalid log node, failed marker and failed proc mount. The log sink, restart,
kernel release and command-line source were injected. Each refusal made no restart request; the
success made one marker and one request, then parked. This does not execute the
candidate kernel or establish reset reliability. The shared startup tests also
reject an incorrect control UUID and refuse entry into the Python cycle path.

Archive comparison verified every unchanged member and source digest. Container
reassembly was identical; native addresses, header, payloads, padding and DT
reservations passed the existing validator, which rejected 17 container and
six input mutations. Shell syntax and ShellCheck passed. No new kernel build
was needed because its exact bytes are reused.

The private installer reuses the reviewed live-GPT boot2 guard and changes only
fixed candidate, package, evidence and preceding-boot identities. It requires
stable known-good Gemian and power, verifies the inactive/non-root partition,
records its predecessor, skips a matching image or writes and fully reads it
back, then shuts down cleanly. It makes no fresh partition backup. The owner
selects boot2 physically; the agent remains the sole device custodian.

Arm the existing 180-second changed-boot Gemian collector before that selection.
On an authenticated return it preserves `console-ramoops` once, at most 65,536
bytes, with before/after boot checks; absence consumes zero payload reads.
Analyze the private capture in the RE VM. Preserve all unique evidence before
any subsequent recovery. This control admits its single normal restart; a
timeout does not authorize a second selection or an unreviewed fallback.

Standing [project device authorization](../../docs/SAFETY.md#standing-project-device-authorization)
covers this reviewed installation/control. Hardware support, successful export
and a WLAN cycle remain unproven.

## Deployment

The final inputs are published at `aca7237337b260238a60de84aa80b2e6998dc48f`;
[hosted repository checks](https://github.com/ixoo/gemini-pda-mainline/actions/runs/34661559667)
passed. The installer confirmed the preceding Gemian boot and resolved boot2
as `179:30`, distinct from root `179:29`. Both power samples at each gate
reported a present, healthy, fully charged battery and external power. The
predecessor matched the second export image. The write, flush, full on-device
checksum and independent complete readback all matched this control's
`7d19a05e…b60a3` padded image. No fresh predecessor backup was made.

After preserving the deployment evidence, the installer requested clean
poweroff. The remote closed the SSH connection (status 255), and a subsequent
reachability check failed. This is the observed shutdown handoff; physical
selection remained an owner action. The reviewed collector was armed before
requesting that single selection. Installation alone did not establish a new
boot or marker. The receipt records these deployment observations;
private installers, raw images and transport logs remain excluded from Git.

## Runtime result

The owner confirmed the single physical selection. At `00:29:57 UTC` on
2026-09-12, the collector authenticated Gemian boot
`57a8683b-b9dc-4643-99c1-aca916d3ae54`, with Linux `3.18.41+`/AArch64, MT6797X,
Debian 9 and running systemd. Before/after boot UUIDs matched. Its sole console
read preserved 65,524 bytes, SHA-256
`6a93806be655d02e3905b89288c47e731cda31fe3bd895687a401c761aa2def9`.

Private RE-VM analysis found the complete expected control marker exactly once
at byte 56,595. It carries candidate boot
`2408a654-f543-47b4-8254-a84e13874c05`, distinct from both Gemian boots. The
kernel timestamp is `1.924290` seconds; the following normal restart message
is at `2.418511` seconds. No panic, BUG, WARNING, unhandled-kernel-fault or call
trace token appears in the retained tail after the marker. This bounded token
check is not a complete kernel-health assessment. The earlier kernel banner
is not present in this ring snapshot.

This establishes entry into the control's BusyBox PID1, successful devtmpfs and
proc setup, passage through its argument/log checks, and retention through the
return. It also supplies an observed warm-return path for the same kernel used
by the unsuccessful export attempts. It does not prove that either older
attempt reached PID1, identify their failure, or validate the full Python/USB
startup. The next change can add this observed return path to full export
startup so a caught refusal leaves recoverable stage evidence. Do not repeat
the boot-entry control. Gemian is left running; no further recovery or device
write was requested after preserving this log.
