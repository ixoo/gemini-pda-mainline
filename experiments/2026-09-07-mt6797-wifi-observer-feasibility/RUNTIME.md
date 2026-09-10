# Controller runtime packaging

The [controller](CONTROLLER_CYCLE.md) needs Python 3.7 or later. The retained
Gemian userspace is not its packaging baseline. The [runtime builder](build-runtime.py)
extracts the [pinned Debian 12 ARM64 packages](runtime-inputs.json) without
installing them on either host or device or running their maintainer scripts.
The package set is Python 3.11 minimal, its standard library, static BusyBox
and the recursively selected first alternatives of their declared dependencies.
It is a runtime preparation archive, not a configured Debian installation.

Debian's signed Bookworm `InRelease` authenticates the pinned ARM64 package
index; every package identity, size and checksum must match that index.
Downloads are cached by filename and checked on reuse. If the pinned release
or packages leave the mirror, the builder refuses different bytes; update or
restore authenticated inputs explicitly. Package contents, including copyright
notices, remain in the ignored artifact, outside this repository.

Run from a clean project checkout on Linux x86_64, with `gpgv`, the Debian archive
keyring, `dpkg-deb`, GNU tar/gzip, QEMU's static ARM64 user emulator, and working
unprivileged user namespaces. Serialize access to the cache/output pair; on
Buildbox hold its existing shared build lock. Temporary extraction/download
state is removed on normal failure and on the next invocation after interruption:

```sh
PATH=/usr/sbin:/usr/bin:/bin python3 build-runtime.py CACHE NEW_PACKAGE
```

The builder checks ARM64/64-bit little-endian execution, SHA-256 and monotonic
nanosecond timing, runs the existing controller process and responder fixtures,
and checks BusyBox shell execution in a user-namespace chroot. Only the package's
Python and ARM64 libraries are available inside that root. QEMU translates
syscalls to the host kernel; this is not Linux 3.18 or device compatibility
validation. The emulator and fixture files are removed before packaging.

`runtime.tar.gz` contains the runtime and three importable controller sources,
with normalized tar ownership/order/timestamps and gzip metadata. There is no
`/init`, firmware, boot container or trigger. Construction of the actual minimal
startup, fixed firmware lookup layout, capture preparation, remaining kernel
actor/reset isolation and exact session admission still precede a device test.
The [runtime receipt](results/runtime-package.json) records successful packaging
at `05288f07f4da6ae3550dd72707307e1caed008ba`: seven controller tests, twelve
responder tests and the ABI/hash/time/BusyBox checks passed. All five fetched
package files and 1,608 archive members were checked, including exact controller
source hashes and absence of init, firmware, emulator and fixture scripts.
The compressed archive is 23,266,365 bytes; the unpacked regular files total
73,481,387 bytes. Two launcher attempts failed before Python execution because
`chroot` was outside the command search path; the successful invocation resolves
it before clearing the test environment and includes `/usr/sbin` in the host
path. No interpreter or device failure was inferred from those launcher errors.

A second extraction and test at `05df41212f663bdf84f292e97a662a50e745c07a`
passed the same checks and produced a byte-identical `runtime.tar.gz`. It used
the same authenticated cached packages, QEMU and host kernel. The receipt pins
both complete package manifests; this establishes repeatable runtime packaging,
with boot integration still untested. The subsequent
[native Gemian check](RUNTIME_NATIVE.md) passes the scoped ABI, clock, hashing
and mocked controller/responder tests on Linux 3.18.41+ without an emulator.
Actual connectivity and recovery remain outside that result.

The subsequent [private input filesystem](STARTUP_FILESYSTEM.md) places the
verified retained inputs at the selected lookup paths. It still has no init
or trigger and remains incomplete boot integration.

The [minimal startup implementation](BOOT_STARTUP.md) now supplies the read-only
mount and PID1 preflight/controller sequence. Its focused checks pass, but it
has not been booted on the PDA.

## Compact boot runtime

The full preparation runtime cannot fit the retained loader's 16 MiB image
limit: its filesystem alone is larger than that limit. The
[compact builder](build-compact-runtime.py) selects unchanged bytes from the
pinned preparation archive. It keeps Python, the complete pure-Python standard
library, twelve named extension modules, their selected libraries, static
BusyBox and copyright/license files. It excludes package-management utilities,
locales, manuals, unused extensions and their libraries. This is a controller
runtime, not a complete Python distribution. Hashing uses Python's built-in
`_sha256` implementation rather than the omitted OpenSSL extension.

```sh
python3 build-compact-runtime.py VERIFIED_PARENT_TAR NEW_RUNTIME_TAR
```

The [compact receipt](results/runtime-compact.json) pins the 7,510,652-byte
archive. Host and ARM64 VM construction produced identical bytes. The selected
23 ELF files have no missing named library dependencies. All 46 startup,
stream, bridge, controller and responder fixture tests passed in the assembled
ARM64 filesystem. USB controls are injected and transfer payloads synthetic.

The [native compact result](results/runtime-compact-native.json) separately
records the unchanged [bounded Gemian protocol](RUNTIME_NATIVE.md) with this
archive: the ABI/hash/clock/isolation checks and 19 controller/responder tests
passed on Linux 3.18.41+ in six integer-clock seconds. Boot identity remained
unchanged; the exact log was retrieved and verified before temporary RAM files
were removed. No radio, watchdog, partition or restart operation occurred.
The new [filesystem assembly](STARTUP_ASSEMBLY.md#compact-export-filesystem)
fits the projected image budget; boot and recovery validation remain open.
