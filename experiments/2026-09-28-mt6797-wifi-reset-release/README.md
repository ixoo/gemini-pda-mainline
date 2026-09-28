# Gated CONMCU reset-release diagnostic

The [powered EMI boot](../2026-09-28-mt6797-wifi-powered-emi/results/runtime-1.json)
found empty region-18/19/23 ranges with a nonzero secure-read control after
CONN reached ON and chip ID settled to `0x0279`. It did not release CONMCU
reset. The selected Gemian `CONFIG_OF` path sets MCU ACR bit 18 before its
TOPRGU release and waits 20 ms afterward. This experiment tests that next
common-owner transition once, without an EMI write or firmware transfer.

The named `mt6797-a53-wifi-reset-release` profile extends the previous
candidate with [patch 0040](../../patches/proposals/0040-soc-mediatek-probe-gated-MT6797-CONMCU-reset-release.patch).
It requires confirmed CONN ON, held CONMCU reset, chip ID `0x0279`, and a
same-boot powered EMI snapshot: region-1 control exactly `0x44604460`, both
region-23 range reads zero, and region-18/19 range and policy reads zero.
Only then does it read and set ACR bit 18 through its four-byte claimed
resource, require readback, release its exclusive TOPRGU reset once, and
check reset, domain and chip ID after 20 ms. The owner retains all power and
reset effects on success or failure until reviewed recovery. The patch has
synthetic non-certifying authorship and is not an upstream submission.

The hypothesis is that the release returns success, TOPRGU status becomes
deasserted, CONN remains confirmed ON and chip ID remains `0x0279`. A failed
power, reset, ID or EMI gate stops before the ACR write. Failed ACR readback
keeps reset held. A reset operation or post-release check failure retains
state, preserves logs and proceeds only through reviewed recovery, with no
second release, speculative reassertion, firmware transfer, EMI policy write,
radio action or DMA use. A successful result admits subsequent HIF/downloader
work; it does not prove firmware readiness or usable Wi-Fi.

Before device use, require a clean pushed Buildbox build, validated package
and boot candidate, live-GPT guarded boot2 installation with matching full
readback, clean shutdown, an armed finite USB collector, and physical boot2
selection by the owner. Preserve the complete log and A53 regression, then
confirm a changed-boot Gemian Wi-Fi return through the reviewed path.

## Prepared candidate

The clean pushed commit `26951f2e23a7e920ef48238d5b624ea51db14d71`
built on Buildbox with `KERNEL_PROFILE=mt6797-a53-wifi-reset-release` and
validated package digest
`94ada6cf3a2dd56e20f0e83a2e6e821e05a71c351ee8b488ffdb268e9b8fb813`.
The private RAM root retained the same 52 members and firmware bytes; only
the release check in `init` changed. The candidate keeps the boot-tested
board DTB and adds only the source-matching ACR resource and one-shot flag
to its CONSYS node. The boot-container validator passed. Its full 16-MiB
boot2 SHA-256 is
`4483a35bc23dc5d0bfca856848a70ca512e071caa89741098e0f461b65a9e141`.
The [checksum-only receipt](results/candidate.json) pins all inputs. No
device action has been taken for this candidate. The guarded installer was
generated offline against the matching previous image and passed `bash -n`
and ShellCheck. A pinned-key read of the current Gemian boot found kernel
`3.18.41+`, boot ID `fcb8a468-5333-454a-8fca-c50fea118ccf` and WLAN
carrier 1 before installation.

## Installation and shutdown limit

The guarded installer resolved logical `boot2` from the live GPT in that
Gemian boot, verified the expected predecessor and stable power, wrote the
new image, flushed it and matched an independent full-partition readback.
It then requested `systemctl poweroff`, but Gemian remained reachable through
the bounded shutdown check; the installer exited 2 rather than claiming a
clean shutdown. A bounded read-only follow-up found the same Gemian boot ID,
PID 1 in uninterruptible `tty_ldisc_ref_wait`, and a timed-out `systemctl`
job query. Those observations do not prove the cause of the failed shutdown.
The [sanitized receipt](results/install-attempt-1.json) pins the exact image
and the private deployment-summary checksum. At that checkpoint, no
reset-release boot had run.

The owner then reported the PDA off and selected boot2 before the collector was
armed. The mainline USB route appeared and pinned-key SSH authenticated a new
boot of the intended release. An authenticated A53 observation passed; the
reviewed RAM logger seal preserved a complete sequence-zero log; the power
controller provider was bound. The [sanitized runtime record](results/runtime-1.json)
shows the one-shot same-boot gate passed, MCU ACR bit 18 changed from clear to
set, CONMCU reset released, and chip ID remained `0x0279` with CONN ON. After
evidence preservation, the reviewed native recovery request returned the PDA
to a changed-boot Gemian desktop with `wlan0` carrier 1.

This was a post-selection salvage, not a prearmed finite collector run. The
prior clean-shutdown failure remains; do not relabel this as a complete A53
session regression. Firmware execution, HIF/DMA use and mainline Wi-Fi remain
untested. The next implementation step can build on the confirmed reset-release
state, but needs its own admission for firmware and HIF effects.
