# Minimal observation startup

The [init script](startup-init.sh) and [PID1 controller entry](startup.py) implement
the selected minimal userspace. The [compact private filesystem](STARTUP_ASSEMBLY.md#compact-export-filesystem)
included their preceding revision with an export session manifest for the
[first physical attempt](EXPORT_ATTEMPT_1.md). The current
[bootstrap diagnostics](BOOTSTRAP_DIAGNOSTICS.md) are packaged for the
[second session](EXPORT_SESSION_2.md), with device validation outstanding.
They must not run in the current Gemian environment.

When packaged as `/init`, the shell requires PID1, mounts devtmpfs first and
opens the checked kernel log node on descriptor 3. It then mounts proc, sysfs,
pstore and an 8 MiB temporary `/run`, opens the console and disables SysRq through its
software setting. It bind-mounts the common firmware, WLAN firmware, calibration,
session metadata, controller sources and `/init` read-only, with nosuid/nodev/
noexec. Python reads the scripts rather than executing files from those mounts.
It then replaces the shell with the pinned Python 3.11 runtime in a cleared
environment. It starts no service manager, network manager, shell service,
Android userspace or supplicant.

The Python entry requires root PID1, read-only input mounts, exact startup-file
hashes, exact private-manifest bytes and all five input hashes and sizes. It
rejects alternate firmware files, directory symlinks, earlier WLAN lookup paths
and a firmware-class path override. It verifies kernel release/version/config,
the selected cycle boot argument, `rdinit=/init`, `panic=0`, `cpuidle.off=1`,
empty hotplug-helper setting, disabled SysRq and expected online CPUs. Duplicate
required boot arguments and any `sysrq_always_enabled` argument are refusals.
Process inspection uses the pinned kernel's `PF_KTHREAD` flag, not an empty
command line, to reject every other userspace process, including zombies.
Existing network interfaces must be administratively down.

The schema-2 manifest explicitly selects `cycle` or `export`. In cycle mode,
only then does it import the checked controller, open and identify its detector
through the existing controller checks, recheck kernel/process/interface state,
and invoke the existing single-cycle implementation. There is one invocation,
with no retry. Success still requires recovered capture classification. On
failure or completion PID1 waits; it neither disarms nor reloads the watchdog
and issues no software restart. A refusal before takeover leaves recovery to
the owner; the planned session must account for that case.
In [export mode](CAPTURE_DEVICE.md), PID1 instead reads the preserved raw PMSG
file, sets up one ACM serial function and serves one requested snapshot. It
then parks with the serial descriptor open. It never opens the detector or
continues into the cycle. The init script mounts pstore read-only for this path.

## Identity and packaging contract

`/etc/wifi-cycle/session.json` is a private, externally pinned build manifest.
Its schema is validated by `validate_session()`: schema version 2, an explicit
startup action, a nonzero
cycle UUID, expected kernel release/version/online CPUs, kernel image/input/
configuration hashes, the pinned runtime archive hash, private input-manifest
hash, and hashes for `/init` plus the six Python startup/controller/export sources.
The image/input hashes are build-time provenance fields; PID1 cannot attest
the running kernel image from those supplied fields.

The capture's candidate SHA-256 is defined here as the exact session-manifest
file hash. This avoids embedding a boot image's own checksum inside itself.
The final package/deployment receipt must independently bind this manifest to
the exact kernel, filesystem and complete padded boot image, with full boot2
readback. The decoder must expect that manifest hash, the selected cycle ID,
the observed boot UUID and the private input-manifest hash. A release string or
manifest supplied by the caller is not cryptographic kernel attestation.
The assembly follow-up installs these files and the mount-point directories;
its manifest remains unselected for a device session. The earlier input-only
package remains unchanged.

## Observed responder identity and checks

A fresh [bounded cached-identity query](results/startup-cached-identity.json) on
known-good Gemian returned chip `0x0279` and firmware version `0x8a00`. PID1 uses
these exact expected values; the responder refuses a mismatch. The descriptor
was opened read-only, identified through sysfs, queried twice and closed. The
boot ID remained unchanged. Source review of the named ioctl branches and
`wmt_lib_get_icinfo` identifies cache-field returns, not hardware transactions;
open/close affect the software reference count and may log. No command read,
reply write, initialization, radio or reset request occurred. This is not proof
of firmware acceptance or calibration applicability.

The [validation receipt](results/startup-validation.json) records 12 synthetic
preflight tests on the host and in the pinned ARM64 runtime in the RE VM.
They cover identity composition, writable mounts, altered inputs/controller,
duplicate boot settings, SysRq/firmware overrides, alternate lookup symlinks,
another userspace process, an up interface and configuration mismatch.
Shell syntax and ShellCheck pass. The exact bind/remount loop was also executed
with the pinned BusyBox in a separate VM mount/PID namespace: all six root write
attempts failed with a read-only-filesystem error, original bytes remained
unchanged and a writable control succeeded. An earlier fixture's missing stderr
destination invalidated its write-attempt claim; the corrected run checks the
actual error. Temporary namespaces and fixtures were removed.

These checks do not execute a PDA boot, validate Linux 3.18 mount behavior, or
prove continuous kernel actor isolation. Remaining system restart/notifier and
shared-resource control, capture zero-state preparation, complete packaging and
the owner-approved radio/recovery session still precede device execution.
The [live preparation inspection](CAPTURE_PREPARATION.md) found nonempty PMSG
memory. The new export action implements a preservation path; actual device
export and the clear operation remain unvalidated and unimplemented respectively.
