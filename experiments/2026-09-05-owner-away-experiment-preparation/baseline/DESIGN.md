# Authenticated A53 userspace design

Preparation is **preparing**, with no deployment or runtime admission. The
[foundation audit](BASELINE_AUDIT.md) owns the exact successful input identity.
The [userspace contract](userspace.json) pins the intended additions. The
kernel, resolved configuration and composed DT stay byte-identical; this is an
independent authenticated observation path, not a marker-only repeated boot.

## Administration and credentials

Use the existing `usb0` direct link, `10.15.19.82/24`, without DHCP, routing,
DNS, a default route, or another network interface. Bind SSH to both that
address and `usb0`. Host configuration requires an unused address on this
subnet, a provisioned administration key, `IdentitiesOnly=yes`,
`IdentityAgent=none`, strict pinned `known_hosts`, and no ambient SSH config.
The host separates stdout and stderr and treats disconnect, timeout, missing
terminal evidence, changed identity, or a nonzero exit as incomplete evidence.

The official [Dropbear source](https://matt.ucc.asn.au/dropbear/releases/dropbear-2026.94.tar.bz2)
is pinned by its published SHA-256; the detached signature has **not** been
authenticated. Source review of `src/svr-runopts.c` establishes `-D` key
directory, address/interface binding, finite session duration and idle limit.
`localoptions.h` disables password/PAM, TCP/Unix-socket/agent/X11 forwarding,
SFTP and automatic host-key generation. The public-key protocol is upstream
Dropbear; no custom authentication mechanism is introduced.

The local provisioner generates separate fresh Ed25519 host and administrator
keys with `ssh-keygen`. Private material stays mode 0600 under the ignored,
mode 0700 `artifacts/credentials/a53-auth/`. It never overwrites an existing
credential set. Only the public administrator key enters `authorized_keys`;
the host private key enters the private candidate image, making that whole
image secret-bearing and ineligible for Git/public upload. Offline `known_hosts`
binds the generated host public key. No first-use network trust is required.
The small OpenSSH-to-Dropbear container conversion is checked independently
against the pinned upstream `dropbearconvert` using disposable fixture keys.
No real credential leaves the local host for Buildbox.

The private image can be reproduced byte-for-byte only with the same protected
credential bundle. Public reproduction uses fresh credentials and necessarily
produces a different image identity. Credential rotation invalidates candidate,
deployment and observation identities; it never overwrites an old receipt.

Dropbear's `LICENSE`, LibTomCrypt and LibTomMath notices accompany the private
userspace package. The static C runtime's licensing and complete corresponding
BusyBox source/build provenance must be reviewed before redistributing a
binary bundle; local private testing does not grant public distribution rights.
No proprietary firmware or calibration is included in this candidate. A later
Wi-Fi experiment may supply owner-provided hash-pinned private blobs through
the standard firmware-loader path in its own isolated candidate; those blobs
and their rights record remain separate from this USB interface.

## Console and logging

The exact inherited forced kernel command line selects `ttyS0`, not a VT.
Retain serial console, earlycon, the kernel ring and existing ramoops contract.
No `console=tty0`/`tty1`, loglevel change, retained-RAM writer or kernel change
is needed. The inherited local shell and background `x-probe` are removed;
their old markers and automatic 15-second evdev read must not consume the new
keyboard packet's budget. `tty1` shows an explicit status screen with no shell.
It retains the exact map, Unicode and complete map-readback helpers. Keyboard
observation receives exclusive foreground VT use only during its own packet.

One reader drains `/dev/kmsg` from the earliest available sequence into a
maximum 2 MiB RAM file for at most 600 seconds. It records gaps, overflow,
truncation and its terminal reason; missing early sequence/terminal status
cannot establish complete logs. It never clears or writes the kernel ring.
The 8 MiB `/run` mount bounds all temporary state. SSH diagnostics use a
finite inherited file-size ceiling; reaching it causes failure, not silent
log recycling. Raw logs remain private pending field-by-field sanitization.

## Relevant resource boundary

Preserve PWRAP compact reset input 1, MT6351 VEMC/VIO18, the exact MSDC
25 MHz/8-bit DT contract, and the peripheral-only MTU3/PHY contract. CPU0–7
must be online and CPU8/9 present but offline. Thermal/AUXADC, cpufreq, idle,
suspend, CPU triggers, load, extra input reads and storage writes are absent.
Disabled drivers do not imply absent DT nodes: the historical I2C6/DA9214
description remains exactly as audited. AP-DMA/CONSYS resources and reservations
must stay unchanged; Wi-Fi owns any later proposed ownership transition.

## Packaging, deployment and recovery gates

Reconstruct from the checked exact historical package and initramfs, using
an allowlisted member delta. Drop the unauthenticated `usb-net`, `usb-shell`,
the dormant `emmc-flash-boot2`, automatic input worker and local command shell.
Preserve the proven native `/bin/reboot`, map, console helpers and BusyBox.
Independently compare two assemblies and validate every member, kernel/DT,
Android-v0 addresses/header, exact padding and secret-bearing output modes.

The new installer must adopt the current `boot2-device-guard.sh` twice and
bind a receipt to the full padded image digest. The historical installer is
evidence, not reusable deployment authority. Candidate selection, live GPT,
inactive root/mount/holder/swap checks, stable power, full readback and clean
shutdown remain mandatory. No generic runner or alternative writer is added.

The first session permits one physical boot, a single bounded baseline
observation, rejected-key/host checks, one authenticated recovery request and
changed-ID known-good confirmation. The exact native reboot wrapper remains
the recovery primitive; that request is separately admitted only after the
new artifact, boot ID and wrapper hash match. Failure before SSH service may
require the owner to return to the known-good physical path. Missing USB gives
no kernel conclusion. Console/auth regressions reject the baseline; a complete
serviceability pass plus confirmed recovery permits matching dependent packets.
Ten-cold-boot acceptance is cumulative and is not a prerequisite for those
packets. Exact numeric combined-session budgets and complete receipt/recovery
tools must be frozen before any preparation state advances to conditional.
