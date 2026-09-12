# Debian services on the A53 kernel in QEMU

Status: the exact service-facilities kernel passed one Debian boot, service
isolation and IPv4 filtering observation, orderly poweroff and an offline ext4
check in QEMU. This is off-device runtime evidence; no PDA candidate or storage
allocation is selected.

## Inputs and scope

The [receipt](results/a53-debian-qemu.json) pins the unmodified `Image` from
[Buildbox commit](A53_SERVICE_FACILITIES.md)
`ac6cf1774966ff282449881c5337d9888eab1d5a`, release
`7.1.3-gemini-a53-service-facilities`, SHA-256
`539d187e76d2948128060b6e6a82625824fb6be70b490fe043820ef0a4e491b6`.
The kernel was not rebuilt in the VM. Userspace is a fresh extraction of the
verified [119-package Debian archive](DEBIAN_USERSPACE.md), whose original
checksum remains unchanged after the test.

QEMU 8.2.2 ran under software emulation in the ARM64 RE VM, with machine
`virt-8.2,gic-version=3`, two Cortex-A53 CPUs and 2 GiB RAM. The generic
[QEMU virt platform](https://www.qemu.org/docs/master/system/arm/virt.html)
supplies PL011, GIC and virtio hardware; it does not emulate the Gemini board.
No network adapter or physical device was passed through.

A temporary BusyBox initramfs mounts the sole virtual ext4 disk read-only and
switches to Debian's systemd as PID1. The kernel's forced command line remains
unchanged. The fixture explicitly opens `/dev/ttyAMA0` for its console and
selects `/dev/vda`; neither choice is a proposed PDA root or console adapter.
Debian subsequently remounts its virtual root writable through ordinary
systemd startup. A 1 GiB sparse regular file holds that filesystem; this size
is a test allocation, not a minimum persistent-system size.

Only an fstab entry, an observation script/service/timer and a persistent
journal directory were added to the fresh extraction. No existing service was
masked and no Debian package was added. The timer starts the observer after
20 seconds; its service has a 60-second timeout, and the QEMU process has a
150-second outer limit. A preceding minimal initramfs smoke boot of the same
kernel exited normally within its 90-second limit.

## Observations

Debian boot `8e67bad2-70fa-4f7c-be6d-ac9841018843` reported the exact kernel
release, ARM64 and systemd PID1. The system was `running`, with no failed units
before the filter probe. D-Bus, journald, logind and udev were active and running;
basic and multi-user targets were active. The only pending job was the observer
itself. This includes actual udev execution, which the earlier
[container lifecycle](DEBIAN_RUNTIME.md) skipped through its container condition.

D-Bus hostname and locale property queries succeeded. Their service processes
ran in distinct network namespaces, different from PID1 and each other, with
`PrivateNetwork=yes` and `IPAddressDeny=any`. Three transient services then
attempted the same one-byte IPv4 UDP write to loopback port 9:

| Service policy | Observed result |
| --- | --- |
| No IP filter | Exit 0 |
| `IPAddressDeny=any` | Exit 1, `Operation not permitted` on write |
| Deny any plus `IPAddressAllow=localhost` | Exit 0 |

This demonstrates a causal effect of the configured cgroup IP policy on the
tested kernel. It does not cover IPv6, ingress, external connectivity, arbitrary
BPF programs or general networking. The observed defaults were
`unprivileged_bpf_disabled=2` and `bpf_jit_enable=1`; no JIT disassembly claim is
made from those values alone.

The observer exited zero and requested ordinary systemd poweroff. Logs show
filesystem synchronization, all filesystems unmounted and devices detached,
a final sync, then poweroff. QEMU exited zero after 33.941 seconds. Read-only
inspection of the stopped disk found a clean filesystem, and `e2fsck -fn`
returned zero. These results cover the virtual filesystem lifecycle only;
Gemini eMMC writes, hardware shutdown and independent recovery remain untested.

The journal retains warnings for unavailable QEMU cache hierarchy/IPMI,
the inherited unused-clock policy, the initial console before the fixture
opens PL011, and the deliberately denied transient service. No warning-free
boot claim follows. Raw serial output, extracted journal, observations and the
unique virtual disk are retained privately, with hashes in the receipt.

## Reproduction and next boundary

Use the exact kernel and archive above, a fresh temporary ext4 image, and the
minimal mount/switch-root fixture described above. The QEMU invocation uses
`-accel tcg -machine virt-8.2,gic-version=3 -cpu cortex-a53 -smp 2 -m 2048
-nodefaults -display none -monitor none -nic none -no-reboot`, a file-backed
serial console, the kernel/initramfs, and a sole `virtio-blk-device` backed by
the regular raw image. Never substitute a host block device.

Run the three probes with `systemd-run --wait --pipe --collect`, adding the
policies shown in the table, and executing
`/bin/bash -c 'printf x >/dev/udp/127.0.0.1/9'`. Preserve both the expected
denial and the successful controls. After terminal QEMU exit, use read-only
`debugfs` to extract the observation and journal, then inspect/check the image
without repair. The receipt pins the one-off fixture scripts and exact inputs;
there is no new project runner or installed project service.

Confirm the distribution and owner-selected storage allocation before building
a [persistent-root candidate](PERSISTENT_ROOT.md). Device packaging, updates,
rollback, filesystem effects and independent recovery still need their own
reviewed protocol. The successful emulated boot advances service compatibility
and consumes no device session or hardware regression budget.
