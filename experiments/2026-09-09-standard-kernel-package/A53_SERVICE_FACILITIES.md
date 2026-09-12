# A53 distribution service facilities

Status: Buildbox compilation and package validation passed. This profile enables
facilities requested by the evaluated Debian services. It selects no device
candidate, storage allocation or persistent-root installation.

## Concrete need and selected inputs

The [Debian package audit](DEBIAN_USERSPACE.md) identified installed services
requesting `PrivateNetwork=yes` and `IPAddressDeny=any`, while the tested A53
kernel lacks network namespaces and cgroup BPF. The
[native container lifecycle](DEBIAN_RUNTIME.md) established actual private
network namespace creation for hostname and locale services on the VM kernel.
It did not test BPF filtering or the Gemini kernel.

The new `mt6797-a53-service-facilities` profile adds `NET_NS`, `BPF_SYSCALL`,
`BPF_JIT` and `CGROUP_BPF`. These provide the kernel facilities for private
network namespaces and systemd's cgroup IP filtering. A build alone cannot
establish that systemd creates a namespace, attaches a filter or enforces a
traffic policy on the PDA.

The profile also disables the legacy firmware sysfs fallback. The evaluated
systemd requirements exclude it, and contemporary udev does not supply that
loader. Direct firmware loading from normal filesystem paths remains enabled.
This changes no retained firmware bytes or radio activation policy.

The [explicit series](../../patches/series-a53-service-foundation) preserves
the exact bytes of the historical 505-entry series from build commit
`ded915b81d56902d8800ff9fefc477480e4bcaa1`. Every selected patch is unchanged
and remains in canonical order. The eleven ordered configuration fragments
also match the [foundation audit](../2026-09-05-owner-away-experiment-preparation/baseline/BASELINE_AUDIT.md).
The profile adds only the [service fragment](../../configs/gemini-a53-service-facilities.fragment)
after those inputs, with a distinct release suffix. Linux remains pinned to
the manifest's 7.1.3 archive.

The historical profile name now selects 529 patches, so it is not used to
reconstruct the tested foundation. The new series pathname changes the build
tool's patchset identity even though all 505 ordered patch bytes match. Record
both identities explicitly; do not claim binary equivalence to the old package.
No existing profile or selected Wi-Fi input is changed.

## Validation and remaining boundary

```sh
KERNEL_PROFILE=mt6797-a53-service-facilities ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-a53-service-facilities ./scripts/buildbox fetch-package
```

The [build receipt](results/a53-service-facilities.json) binds the successful
compile at `ac6cf1774966ff282449881c5337d9888eab1d5a`. All 207 prior profiles
and their effective inputs are unchanged. Four inspected core Kconfig files
in the prepared source match the pinned 7.1.3 archive. The namespace, BPF syscall,
cgroup filter and ARM64 JIT implementation objects compiled, and their relevant
symbols are linked. Direct `request_firmware()` remains linked.

The complete configuration comparison finds 23 effective changes: the six
explicit fragment values and 17 dependency/default selections. Five additional
disabled options change visibility without changing their effective values. CPU topology,
forced command line, thermal/frequency/idle/suspend policy, modules, wireless,
storage, filesystem and USB controls remain unchanged. The receipt enumerates
every change, including these less obvious consequences:

- BPF selects task-RCU support, binary formatting, socket-message/network
  ingress/egress support and page pools; the JIT selects executable memory.
- ARM64's JIT default becomes effective, as does the upstream default disabling
  unprivileged BPF. This is a compiled default, not an observed PDA sysctl.
- `NET_DEVMEM` and `IO_URING_ZCRX` are automatic `def_bool` selections once page
  pools and the already enabled DMA-buffer, io_uring, IPv4 and busy-poll
  dependencies are present. They have no independent user-configurable switch.
  Retaining those existing interfaces therefore also compiles these facilities.
- Page-pool statistics become effective from the initial arm64 defconfig
  selections. They are included in the configuration delta and possible
  allocation/recycling overhead; no new driver configuration is enabled.

The compressed image is 6,045,287 bytes, increasing by 408,385 bytes. Its
decompressed length is 14,624,776 bytes, increasing by 935,936 bytes, and the
ARM64 header reports a 15,204,352-byte effective memory size. Both memory sizes
fit the existing 52,428,800-byte LK kernel limit. No complete distribution
initramfs/container has been composed, so this is not a boot2 package-fit claim.

The build has no compiler errors. Its one unused-function compiler warning and
fourteen DT `ranges_format` warnings match the historical build after source
directory normalization. Applying the unchanged historical patch `0261` also
reports one trailing-whitespace line. These inherited findings are retained;
this work changes no patch, DT source or binding and runs no new DT schema test.
Remote package validation, local full inventory/checksum validation and hosted
Linux repository checks passed.

No userspace was run on this compiled kernel. Network namespace creation,
cgroup BPF attachment and actual filtering on the PDA remain runtime gates.

Network policy beyond the evaluated directives, modules, root selection,
filesystem checks/writes, orderly hardware shutdown and independent recovery
remain governed by the [persistent-root contract](PERSISTENT_ROOT.md).
The historical candidate's separately composed DT and diagnostic initramfs are
not supplied by this compile profile. A new device candidate needs its own
reviewed composition and session; neither the build nor the VM container
replaces that requirement.
