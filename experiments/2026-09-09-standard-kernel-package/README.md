# Standard kernel packages and the retained boot path

Status: source/live hook audit complete; update design only. No package built or installed.
The standard Debian kernel packaging path can provide versioned kernel,
configuration, symbols, DTBs and modules. It does not itself construct or
select the Android-v0 container required by the retained Gemini LK path.
Keep that adapter separate from the generic kernel package.

## Inspected inputs

The [receipt](inspection.json) pins three packaging/build files from the
prepared Linux 7.1.3 tree on Buildbox and their identical counterparts at
upstream `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`. This is file-level source
inspection, not a package build or a claim that either complete tree matches
a tested device candidate. The kernel manifest remains the source authority.

Two bounded read-only SSH requests inspected known-good Gemian on boot
`21748845-bc80-4536-b67c-84f7bb16c74f`, release `3.18.41+`, architecture
`aarch64`. Each checked identity before its reads and confirmed the same boot
at the end. The root task was sole custodian. The first request listed the
four standard kernel-hook directories under `/etc/kernel` and
`/usr/share/kernel`, their regular hook names/executable status, and queried three
package names. The second read the named initramfs post-install/removal
hooks and `update-initramfs`, with 32 KiB per-file limits, and inventoried the
post-update and initramfs hook directories. It used a ten-second remote and
fifteen-second host deadline; captured output was 10,943 bytes.

No hook, package installation/removal, initramfs generation, service, mount,
register, radio, reboot or partition operation was executed. The second
capture is private and mode 0600; the receipt contains only sanitized facts
and digests. The first request's observation is retained in the task output;
it is not represented as a separately saved raw capture.

## Actual package-to-hook interface

| Stage | Inspected behavior | Consequence for Gemini |
| --- | --- | --- |
| Upstream arm64 image selection | `image_name` reports `KBUILD_IMAGE`: normally `arch/arm64/boot/Image.gz`, or `vmlinuz.efi` for EFI zboot. | The filename `vmlinuz` does not identify the payload format. The retained LK adapter must validate actual input format and reject an EFI-zboot payload. |
| Kernel file installation | `builddeb` copies that selected image to `/boot/vmlinuz-$KERNELRELEASE`, plus versioned config and System.map. | Use exact versioned paths and package identity, not the newest file or a mutable default symlink. |
| DT and modules | When selected and built, DTBs install under `/usr/lib/linux-image-$KERNELRELEASE`; modules install under `/lib/modules/$KERNELRELEASE`. | Pair the board DTB and any modules with the same kernel inputs. DTBs remain separate until the retained-container adapter consumes the selected board file. |
| Maintainer scripts | Four scripts dispatch matching hooks from `/etc/kernel` and `/usr/share/kernel`, pass the release and image pathname, and export `INITRD` according to the kernel configuration. | Package install/remove can execute hooks. A staging or extraction check must not be represented as an on-device installation test. |
| Installed Gemian hooks | Post-install has executable `apt-auto-removal` and `initramfs-tools`; post-removal has executable `initramfs-tools`. | Kernel retention and initramfs handling exist, but the apt hook's internals were not inspected. Do not infer a safe rollback-retention policy from its name. |
| Installed initramfs hook | With `INITRD` not `No`, post-install invokes `update-initramfs -c -t` for the passed release; post-removal invokes `-d -t`. | These are file creation/removal effects, not a verified LK container or deployment. |
| Installed bootloader dispatch | `update-initramfs` dispatches `/etc/initramfs/post-update.d` if it is a directory. That directory test was false in this session. | The inspected chain supplies no LK container or slot-selection hook. Other uninspected scripts are outside this claim. |

`initramfs-tools` was version `0.130` and `linux-base` `4.5`. `dpkg-query`
found no `flash-kernel` record; this is not a whole-filesystem executable
inventory. These observations describe the current Gemian recovery environment,
not a selected future distribution or its installed hooks.

## Consumption and rollback contract

Use standard distribution packages for their normal versioned files. Reuse
upstream packaging instead of maintaining a second kernel-file layout. The
retained-loader adapter must consume an explicitly selected package/release,
its matching Gemini DTB and an explicitly selected initramfs. Keep the original
package files intact. Construct and validate the development Android-v0 image
with the existing [kernel/container workflow](../../docs/KERNEL_WORKFLOW.md),
including LK size/format constraints and exact provenance. A generated distro
initramfs is a new input; it does not inherit the tested diagnostic initramfs's
size, drivers, authentication, startup behavior or recovery result.

Package installation and boot selection are distinct decisions. A future
adapter may prepare a candidate after the standard initramfs hook, but must
not turn a normal package hook into an unguarded block-device writer. Under
the present recovery contract, deployment still resolves logical boot2 from
live GPT, verifies the inactive target, checks full padded readback, and hands
off physical selection to the owner. Primary boot remains independent.

Retain the preceding exact kernel package, matching DTB/initramfs and validated
container until the successor passes its named runtime regression and a
reviewed rollback test. Removing a package can remove its initramfs through
the inspected post-removal hook; therefore generic package autoremove cannot
be accepted as the tested-candidate retention policy without review. Retaining
files alone does not prove rollback or make the predecessor boot automatically.

The next implementation input is a selected persistent-root/distribution and
an admitted filesystem update/rollback protocol. The present diagnostic
baseline is not that persistent installation. The
[persistent-root migration audit](PERSISTENT_ROOT.md) identifies forced
command-line root selection, pre-mount filesystem checking and orderly
shutdown as concrete gaps in reusing that baseline. Once selected, test package
staging, exact image/DTB/initramfs pairing, hook ordering and predecessor
retention off-device before the separately admitted runtime update. Do not
install a probe package into known-good Gemian merely to test these scripts.
No new package builder, hook framework or boot writer is added by this record.

## Validation scope

Source and installed-script digests were collected, control flow inspected,
and live boot identity checked across both acquisitions. No kernel compilation,
Debian package build, hook execution, distribution boot or rollback test ran.
Repository publication checks validate these documents, not the proposed
future update path. Ordinary distribution updates remain an open roadmap gate.
