# Persistent-root migration audit

Status: offline input audit; no persistent-system candidate or write protocol.
The later [Debian userspace evaluation](DEBIAN_USERSPACE.md) builds and checks a
standalone ARM64 archive and identifies service/configuration gaps. It selects
no storage target and does not implement a persistent-root installation.

The tested serviceability kernel has useful built-in storage and filesystem
support, but replacing its diagnostic archive with a distribution initramfs
does not by itself select a persistent root or preserve its recovery contract.

## Exact inputs

The retained `kernel.config` from build commit
`ded915b81d56902d8800ff9fefc477480e4bcaa1`, profile
`mt6797-pwrap-reset-serviceability`, was read in place. Its SHA-256 is
`194834d90eb2443f4b14ba8f2078ba16fe0c63f69088fcc8c063fe25af01c410`, matching
the [foundation audit](../2026-09-05-owner-away-experiment-preparation/baseline/BASELINE_AUDIT.md).
This comparison checks the configuration file, not the entire package again.

For a concrete distribution-side comparison, the following Debian
`initramfs-tools` **0.148.4** sources were retrieved on 2026-09-09. This is an
explicit source version, not a selection of the future distribution and not
the installed Gemian version 0.130 inspected in the parent record.

| Source | SHA-256 |
| --- | --- |
| [init](https://sources.debian.org/data/main/i/initramfs-tools/0.148.4/init) | `0a9bb34973c78987922b57f010e99c36ddf102e8a5a2fd198385566539f5d6d5` |
| [scripts/local](https://sources.debian.org/data/main/i/initramfs-tools/0.148.4/scripts/local) | `e4af112fd0d528fcb9b6094a9a2dd529b8936310d6939f7272299951b9a27448` |
| [scripts/functions](https://sources.debian.org/data/main/i/initramfs-tools/0.148.4/scripts/functions) | `b328b49756e00ec7c692dcdd28526831def5e9e0d7a0d0963087b450c2db4743` |

## Findings and implementation consequences

1. **Root selection needs an explicit input.** The kernel has
   `CONFIG_CMDLINE_FORCE=y`, `rdinit=/init`, and no `root=` token. Editing the
   Android header cannot supply that missing token. Debian's inspected `init`
   initializes `ROOT`, reads archive configuration, then parses `/proc/cmdline`;
   its local-root path refuses an empty `ROOT`. A selected root therefore needs
   either reviewed initramfs configuration or a new kernel command-line policy.
   Do not bake a guessed partition number into the generic board fragment.
2. **A read-only root request is not a no-write protocol.** The local-root
   script calls `checkfs` before mounting, independently of its read-only flag.
   With a known filesystem, an available checker and checks not skipped,
   `_checkfs_once` defaults to automatic repair (`-a`); explicit repair policy
   can choose other flags. Its handling accepts a corrected-filesystem result.
   The inspected scripts are therefore outside the existing raw read-only eMMC
   experiment. A persistent-root protocol must cover checking/repair and the
   selected filesystem's mount behavior, then userspace remount and shutdown.
3. **The basic image readers are present.** `BLK_DEV_INITRD`, all seven `RD_*`
   decompression options, `MMC`, `MMC_BLOCK`, `MMC_MTK`, `EXT4_FS`, `DEVTMPFS`,
   `BINFMT_ELF` and `BINFMT_SCRIPT` are built in. This rules out an absent ext4
   or initramfs decompressor in this configuration; it does not prove a generated
   archive fits LK, mounts storage reliably or boots the selected userspace.
4. **Distribution compatibility is still a separate audit.** Modules and
   network namespaces are disabled; cgroups, PID/user namespaces, seccomp,
   inotify, epoll, signalfd and timerfd are enabled. This is no certification of
   a distribution's service requirements. In particular, package availability
   cannot supply loadable drivers to a kernel built without module support.
5. **Recovery must follow filesystem lifetime.** The historical diagnostic
   recovery wrapper uses a forced reboot without a storage synchronization
   contract. Its [recorded scope](../2026-09-05-owner-away-experiment-preparation/baseline/BASELINE_AUDIT.md)
   cannot be extended to a writable persistent root. The new protocol needs
   orderly service/filesystem shutdown and an independently bootable Gemian
   recovery path before a persistent-root boot is admitted.

## Next input and validation boundary

Confirm the distribution, exact root medium and owner-approved storage allocation
before implementing the persistent-root adapter or installation. Retain the
existing recovery filesystem; no existing
partition is designated expendable by this audit. Resolve root selection,
filesystem effects, complete userspace requirements and image size against
those concrete inputs, then validate package/update/predecessor retention
off-device. The [read-only eMMC packet](../2026-09-05-owner-away-experiment-preparation/emmc/README.md)
remains a separately scoped hardware prerequisite, not a filesystem-write test.

Only source and configuration inspection ran. No downloaded script was
executed, no kernel or root filesystem was built, and no device was accessed.
No configuration/profile, candidate, deployment or runtime claim changed.
