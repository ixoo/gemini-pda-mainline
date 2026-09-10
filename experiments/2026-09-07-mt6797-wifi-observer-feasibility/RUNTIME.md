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

From a clean project checkout on Linux x86_64, with `gpgv`, the Debian archive
keyring, `dpkg-deb`, GNU tar/gzip, QEMU's static ARM64 user emulator, and working
unprivileged user namespaces:

```sh
python3 build-runtime.py CACHE NEW_PACKAGE
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
Runtime preparation has not yet been executed for these inputs.
