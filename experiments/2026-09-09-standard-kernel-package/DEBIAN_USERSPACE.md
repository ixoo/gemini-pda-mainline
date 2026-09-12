# Debian ARM64 userspace evaluation

Status: an off-device userspace archive is built and checked. It is not a PDA
boot candidate. Debian 13 ARM64 is the evaluation default while the owner's
distribution preference is pending; no persistent storage medium or allocation
has been selected.

## Result and exact inputs

A native ARM64 Ubuntu 24.04.4 analysis VM (kernel 6.8.0-139-generic, APT 2.8.3)
ran `mmdebstrap` 1.4.3-6 with `minbase`, adding
systemd, udev, D-Bus, NSS/PAM integration, initramfs-tools, iproute2, kmod and CA
certificates. It installed **119 packages** from the Debian and Debian-security
snapshots requested at **20260912T000000Z**. The signed base release identifies
Debian **13.6**; updates and security metadata are dated 2026-09-11.

The [receipt](results/debian-userspace.json) records archive and signed-release
identities, checks and configuration findings. The
[package inventory](results/debian-packages.tsv) pins every installed version,
architecture, archive path and package SHA-256. Notable inputs are systemd/udev
**257.13-1~deb13u1**, glibc **2.41-12+deb13u3** and initramfs-tools **0.148.4**.
The latter matches the source version in the [persistent-root audit](PERSISTENT_ROOT.md).

The preserved archive is `debian-trixie-arm64-audit.tar.gz`, **101,262,854 bytes**,
SHA-256 `e72e859a5f5f9b404bbb89e4c2593a6f4e5b7c2f17570f31902a15047ab9a488`.
Its prepared directory occupies **315,793,408 allocated bytes** on the VM's
filesystem; that is not a minimum PDA partition size. Downloaded package caches
and indexes were removed after their identities were recorded. The host-derived
hostname and resolver settings were generalized, and machine-id remains empty.

The private archive, full logs, signed metadata and prepared directory remain
under the ignored userspace-audit artifact directories. No distribution binaries
or image are committed here. No kernel was built or copied into this archive.

## Validation and limits

- `dpkg --audit` produced no findings; `apt-get check` found no dependency errors.
- The ARM64 systemd binary executes natively in a chroot and reports the pinned
  version. Its ELF header identifies AArch64.
- Debian's own `systemd-analyze --man=no verify` passed for `basic.target`,
  `multi-user.target`, `shutdown.target`, `systemd-udevd.service`,
  `systemd-logind.service` and `dbus.service`.
- A fresh extraction of the preserved archive passed the package audit, systemd
  execution and same unit checks. All 119 installed package records matched;
  merged `/usr`, empty machine-id and generalized host settings were checked.
- All three retained InRelease files independently passed `gpgv` with the
  authenticated updated keyring. APT signature and expiry checks stayed enabled.

These initial checks cover packages, binary execution and static services on
the VM's kernel. The later [container lifecycle](DEBIAN_RUNTIME.md) separately
tests PID 1 and selected services. The archive supplies neither PDA
networking/login configuration nor a kernel, initramfs, root selector,
filesystem layout or recovery/update adapter.
It has not been installed or booted on the PDA. Package integrity does not prove
storage reliability or writable-root shutdown.

## Tested A53 kernel comparison

The comparison uses the exact retained serviceability configuration identified
in [PERSISTENT_ROOT.md](PERSISTENT_ROOT.md), SHA-256
`194834d90eb2443f4b14ba8f2078ba16fe0c63f69088fcc8c063fe25af01c410`.
All eleven base facilities checked against the pinned
[systemd requirements](https://sources.debian.org/src/systemd/257.13-1~deb13u1/README/)
are enabled, including cgroups, devtmpfs, file handles and event/Unix-socket APIs.
That does not cover the installed services' requested isolation or resource
controls:

| Observed configuration | Consequence for a future distribution profile |
| --- | --- |
| `NET_NS=n` | Cannot provide `PrivateNetwork=yes`, requested by the installed hostname, locale and trim services. |
| `BPF_SYSCALL=n`, `BPF_JIT=n`; no `CGROUP_BPF` | Cannot provide the cgroup-BPF filtering behind `IPAddressDeny=any`, requested by several installed services including udev and journald. |
| `FW_LOADER_USER_HELPER=y`, fallback disabled | The upstream systemd requirements reject this legacy firmware-loading interface; review disabling it in the future profile. This is not evidence of an observed firmware-load failure. |
| `CFS_BANDWIDTH=n`, `PSI=n` | CPU quotas and systemd-oomd's pressure observation are unavailable if those features are selected. No quota directive was found in the inspected installed service files; oomd was not installed. |
| IPv6 and network scheduling disabled | Distribution networking policy still needs an explicit choice and check. |
| Modules disabled; forced command line has no root selector | Preserve built-in driver availability and resolve initramfs/root selection through the existing persistent-root contract. |

The receipt pins the inspected installed service files and their directives.
No service failure or sandbox fallback was inferred from a successful static
unit check. The later [A53 service-facilities profile](A53_SERVICE_FACILITIES.md)
freezes the tested foundation and compiles the missing namespace/BPF facilities,
with legacy firmware fallback disabled. Its complete configuration delta and
build limitations are recorded separately. It selects no persistent root or
replacement Wi-Fi candidate, and its PDA runtime validation remains outstanding.

## Reproduction

Use a native ARM64 Linux environment with sufficient free disk space, root
chroot/mount capability, APT, `mmdebstrap`, and an authenticated Debian keyring
containing the trixie keys. The successful run used the keyring extracted from
`debian-archive-keyring` **2023.3+deb12u2**. Its package SHA-256 is
`f699e2f88dca05212f2a452b58475f2993cb6993dfbafb1d0205a3291eb8b4b8`.
The receipt preserves its trust chain through signed bookworm metadata.

The initial build refused the VM's older 2023.4ubuntu1 keyring because the
selected signing keys were unavailable. The replacement was authenticated
through bookworm's automatic and stable-release signatures, then its package
index and package hashes. Signature checking was not bypassed. The earlier
simulation did not establish that real archive authentication would pass.

In a new managed output directory, with `keyring` naming the authenticated GPG
keyring file, the successful bootstrap command was equivalent to:

```sh
sudo mmdebstrap --mode=root --variant=minbase --format=directory \
  --architectures=arm64 --keyring="$keyring" \
  --skip=cleanup/apt/lists,cleanup/apt/cache \
  --include=systemd-sysv,udev,dbus,libnss-systemd,libpam-systemd,initramfs-tools,iproute2,kmod,ca-certificates \
  trixie "$work/rootfs" \
  'deb https://snapshot.debian.org/archive/debian/20260912T000000Z/ trixie main' \
  'deb https://snapshot.debian.org/archive/debian/20260912T000000Z/ trixie-updates main' \
  'deb https://snapshot.debian.org/archive/debian-security/20260912T000000Z/ trixie-security main'
```

Record `dpkg-query -W` versions and matching APT SHA-256 records before removing
indexes/caches. Verify the retained signed releases and run the checks above in
the chroot. Generalize hostname/resolver/machine-id state, preserve Unix
ownership and special files when archiving, and validate a fresh extraction.
The package selection is pinned; byte-identical archive reproduction is not
claimed because installation generates filesystem metadata and logs.

The security/update metadata expires on 2026-09-18. Later historical reproduction
must handle only that frozen snapshot's expiry explicitly, following the
[Debian snapshot instructions](https://snapshot.debian.org/#usage), while still
verifying signatures and matching the recorded release/package hashes. A live
system must move to a reviewed normal update policy, not remain on this audit
snapshot.

## Next decision

Confirm the distribution and exact expendable storage allocation, then design
root selection, filesystem effects, orderly shutdown, independent recovery and
package/update/predecessor retention against that target. The existing recovery
filesystem is retained. Do not turn this directory archive into an installation
by assuming a partition number or reusing the diagnostic forced-restart path.
