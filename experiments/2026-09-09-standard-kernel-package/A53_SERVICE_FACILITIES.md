# A53 distribution service facilities

Status: build-input checkpoint; compilation pending. This profile enables
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

After compilation, compare the complete resolved configuration with the exact
retained foundation configuration, account for dependency changes and check
the service implementation objects/symbols. Verify the immutable package and
compressed/decompressed image size. No DT source or binding is changed here.

Network policy beyond the evaluated directives, modules, root selection,
filesystem checks/writes, orderly hardware shutdown and independent recovery
remain governed by the [persistent-root contract](PERSISTENT_ROOT.md).
The historical candidate's separately composed DT and diagnostic initramfs are
not supplied by this compile profile. A new device candidate needs its own
reviewed composition and session; neither the build nor the VM container
replaces that requirement.
