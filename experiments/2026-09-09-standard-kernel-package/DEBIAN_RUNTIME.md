# Debian userspace boot and shutdown in the ARM64 VM

Status: one container lifecycle passed on 2026-09-12. This advances the
[archive evaluation](DEBIAN_USERSPACE.md) from static checks to actual PID 1,
service startup, D-Bus activation and orderly userspace shutdown. It is not a
Gemini kernel boot or a persistent-storage/recovery test.

## Inputs and scope

The [runtime receipt](results/debian-runtime.json) pins the unchanged archive,
package inventory, VM kernel, container runtime, observation and logs.
The archive SHA-256 remains
`e72e859a5f5f9b404bbb89e4c2593a6f4e5b7c2f17570f31902a15047ab9a488`.
A fresh extraction ran in the native ARM64 Ubuntu 24.04.4 analysis VM, using
its **6.8.0-139-generic** kernel and `systemd-container`
**255.4-1ubuntu8.17**. The guest's systemd is **257.13-1~deb13u1**.

The only preparation inside the extraction was an empty `var/log/journal`
directory for persistent logs. No service was masked or reconfigured to pass.
Nspawn supplied its normal container environment and a private network with
no host network interface. No kernel was built, emulated or substituted in the
PDA. Runtime machine-id, logs and other generated state belong to this separate
extraction; the original archive and its empty machine-id are unchanged.

## Observed result

At observation, `/proc/1/comm` was `systemd`, the guest reported system state
`running`, and its failed-unit listing was empty. `basic.target` and
`multi-user.target` were active; D-Bus, journald and logind were running.
Udev was **inactive with a failed condition**, so this observation supplies no
device enumeration or udev execution evidence.

D-Bus activated hostname and locale services and returned the configured
hostname and `LANG=C.UTF-8`. Both services remained active for the observation.
Their network namespace identities differed from PID 1's and from each other,
corroborating actual `PrivateNetwork=yes` setup on this VM kernel. This gives a
concrete service case for the missing `NET_NS` facility in the tested A53
configuration. The observed `IPAddressDeny` properties establish configuration,
not BPF filter attachment or traffic enforcement; those were not exercised.

The first transient observation unit failed before running its body: a script
placed in the backing root's `run` directory was hidden by the container's live
`/run` tmpfs. Passing the same body directly through `systemd-run`, with its
argument environment expansion disabled, succeeded in the **same running
container**. The initial exit status 2 and journal warning are retained. The
later empty failed-unit list does not erase that earlier observer failure.

A normal `machinectl poweroff` request returned zero. The guest journal records
service stops, unmounts of its temporary mounts, and reaching `shutdown`,
`umount`, `final` and `poweroff` targets. The host journal records successful
container service deactivation. The machine registration was gone, the host
service was inactive, and no mounts remained below the test root. Shutdown
completed before the 180-second runtime bound; no timeout recovery was needed.
The original archive checksum still matched afterward.

These observations do not test an eMMC filesystem check, repair, root mount,
block-device flush, TOPRGU restart, hardware power-off or return to Gemian.
A container lifecycle must not replace the separately required PDA storage and
recovery protocol.

## Reproduction and retained evidence

Use a fresh extraction of the exact archive into a managed directory in the
ARM64 VM; preserve the original. Create `var/log/journal` before starting it.
The launch uses standard tools:

```sh
sudo systemd-run --unit="$machine" --service-type=notify \
  --property=Delegate=yes --property=KillMode=mixed \
  --property=RuntimeMaxSec=180 --property=TimeoutStartSec=45 \
  --property=TimeoutStopSec=30 \
  /usr/bin/systemd-nspawn --boot --directory="$root" --machine="$machine" \
  --keep-unit --register=yes --settings=no --private-network \
  --link-journal=no --resolv-conf=off --timezone=off --console=pipe \
  --notify-ready=yes
```

Use `systemd-run --machine="$machine" --wait --pipe --collect
--expand-environment=no /bin/sh -c "$observation"` to run an observation body
in the running container. Query system state and units, use D-Bus Properties
`Get` on hostname1 `Hostname` and locale1 `Locale`, and compare each service's
`MainPID` network namespace with `/proc/1/ns/net`. These calls request metadata,
not hostname/locale changes. The receipt pins the measured values and body hash.

Request `machinectl poweroff "$machine"` after collection. Preserve the host
unit journal and guest journal before any cleanup. Require the guest shutdown
targets, successful host deactivation, absent machine registration and no
remaining root mounts; a missing machine alone is not a successful shutdown.
The private artifacts retain both observation attempts, launch/closure logs,
three host-journal lines and 150 guest-journal lines. No new runner or permanent
service was added to the project or the prepared archive.

Next confirm the distribution and exact storage allocation, resolve the tested
kernel's missing service facilities, and prepare the persistent-root and
recovery plan. The container does not supply those missing inputs or consume
the separately selected Wi-Fi device session.
