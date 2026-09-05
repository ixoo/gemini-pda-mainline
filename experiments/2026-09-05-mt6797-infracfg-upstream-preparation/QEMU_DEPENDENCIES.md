# Packaged QEMU preparation for the upstream KUnit profile

## Selected tool and evidence

Use Debian bookworm's `qemu-system-arm` package, version
`1:7.2+dfsg-7+deb12u18+b3`, with its matching common package and data package.
It provides `qemu-system-aarch64`; rebuilding QEMU is unnecessary for this
preparation. The [package inventory](qemu-debian-packages.json) records all
39 absent packages in the declared dependency-name closure, exact download
URLs, archive sizes, SHA-256 values and the observed installed dependencies.
Their compressed total is **21,419,684 bytes**. No recommends or suggests are
included. [Debian package description](https://packages.debian.org/bookworm/qemu-system-arm).

Read-only Buildbox inspection found Debian 12 on x86_64, UID 10001, no sudo,
and no system emulator on PATH or in a bounded search of known tool roots.
The installed `qemu-user-static` package has the same Debian QEMU version;
its `/usr/bin/qemu-aarch64-static` runs userspace programs and cannot boot
this KUnit kernel. Existing libc, compiler and shared-library packages are
recorded as a host baseline, not replacement inputs.

The initial research prepared metadata without acquiring binary packages.
Hashes came from official Debian HTTPS download pages, linked per package
in the inventory. A Debian Release/InRelease signature was not verified.
The dependency-name graph came from Debian's package pages; the subsequent
setup checked complete versioned relations in the verified `.deb` control
records. The [completed setup receipt](results/qemu-debian-setup.json) records
that later result separately from the input inventory.

## Completed setup and corrections

The admitted setup completed on Buildbox with QEMU **7.2.22**, Debian version
`1:7.2+dfsg-7+deb12u18+b3`, at
`/workspace/gemini-pda/tools/qemu-bookworm-7.2-deb12u18-b3`.
All 39 package identities and actual versioned dependency relations passed.
The complete inventory contained 2,257 members; after publication, all 1,323
regular files and all 50 resolved libraries were independently rehashed.
The receipt includes the 90 module/data records and the full remote receipt
identity. Eager symbol binding, the `virt` machine and `max` CPU checks passed.
No guest or device was started. Downloads and staging were removed.

The first attempt refused a package-control identity before extraction. The
metadata had omitted Debian epochs that do not appear in filenames: four
versions needed correction (`libcacard0`, `libjpeg62-turbo`, `liborc-0.4-0`,
and `libusb-1.0-0`). All package URLs, sizes and payload hashes stayed the
same. The full 39-package epoch audit and corrected inventory were used for
the successful attempt; no fallback or relaxed identity check was used.

[`setup-qemu-debian.py`](scripts/setup-qemu-debian.py) pins the exact inventory
and destination, defaults to preflight and requires `--execute` to prepare
the prefix. Existing destinations are preserved and refused. Its independent
review corrected transfer cancellation before HTTP headers and lazy symbol
resolution before execution. The four
[`test-qemu-setup.py`](scripts/test-qemu-setup.py) fixtures pass, including a
real slow-body deadline and SIGTERM while headers are still arriving. These
fixtures use only synthetic localhost traffic. They also cover unsafe link
traversal, unsupported dependencies and foreign-architecture rejection.

The setup receipt pins the exact executed helper and inventory. The full
member receipt remains at `setup-receipt.json` inside the prefix. System
packages, compiler paths and shell startup files were not changed.

## One bounded setup

The setup uses the single versioned prefix
`/workspace/gemini-pda/tools/qemu-bookworm-7.2-deb12u18-b3`. Keep acquisition
and staging under that same managed tools root. Reserve at least 512 MiB
free space before beginning. Do not write to `/usr`, `/lib`, the system
package database, compiler paths or shell startup files.

1. Recheck the recorded installed dependency versions. Download only the
   inventory's exact HTTPS URLs into exclusive partial files, with finite
   transfer time/size limits. Require every exact byte count and SHA-256
   before treating a download as an input. Refuse mismatches rather than
   substituting another version.
2. Read each verified package's control fields. Require the recorded
   package name, version and architecture, and resolve its actual `Depends`
   and `Pre-Depends` against the selected package set plus the recorded
   installed baseline. An omitted or incompatible dependency is a setup
   failure; it does not authorize a system upgrade.
3. Inspect package member paths and links before extraction into a fresh
   staging prefix. Extract package data with `dpkg-deb --extract`; do not
   run maintainer scripts, `dpkg --install`, `apt install`, or `ldconfig`.
   Keep library links inside the prefix and preserve package attribution.
   Reject unexpected cross-package file replacement or links through an
   existing directory outside the managed prefix.
4. Check the emulator's actual shared-library resolution, version and
   machine/CPU enumeration using the invocation below. Keep the exact
   binary and resolved-library identities in a setup receipt. Only after
   these checks pass, publish the versioned prefix without replacing an
   existing installation.
5. Record the inventory and receipt identities, then remove regenerable
   package downloads and staging state. Install cleanup handling as soon
   as temporary state exists; after interruption, classify that exact
   managed state before removing partials or retrying.

The installed-library baseline is intentionally reused. The prefix does
not supply another glibc or compiler, and its environment applies only to
the emulator process. Actual loader resolution remains the deciding check.

## Invocation and acceptance checks

For a published prefix, use invocation-local paths:

```sh
qemu_prefix=/workspace/gemini-pda/tools/qemu-bookworm-7.2-deb12u18-b3
env LD_BIND_NOW=1 \
    LD_LIBRARY_PATH="$qemu_prefix/usr/lib/x86_64-linux-gnu:$qemu_prefix/lib/x86_64-linux-gnu" \
    QEMU_MODULE_DIR="$qemu_prefix/usr/lib/x86_64-linux-gnu/qemu" \
    "$qemu_prefix/usr/bin/qemu-system-aarch64" \
    -L "$qemu_prefix/usr/share/qemu" --version
```

Use the same environment for the loader's `--list` inspection and the
emulator's `-machine help` and `-machine virt,accel=tcg -cpu help` checks.
Require no unresolved library or symbol, the expected Debian QEMU version,
and the `virt` machine and `max` CPU selected by the
[profile proposal](PROFILE_PROPOSAL.md). Inspect the ELF interpreter first
instead of assuming a loader pathname. None of these checks is a kernel
test result.

Debian's [common-package inventory](https://packages.debian.org/bookworm/amd64/qemu-system-common/filelist)
places modules under `usr/lib/x86_64-linux-gnu/qemu`.
QEMU 7.2's [module loader](https://github.com/qemu/qemu/blob/v7.2.0/util/module.c#L235)
consults `QEMU_MODULE_DIR`; its
[`-L` option](https://github.com/qemu/qemu/blob/v7.2.0/qemu-options.hx#L4302)
sets the data search directory. Explicit paths keep the retained system
userspace emulator and shared build environment unchanged.

The eventual KUnit runner must select its exact validated kernel package
and the reviewed pure-test arguments separately. Setup success establishes
an available emulator, not either KUnit suite's result or MT6797 hardware
support. Record the emulator executable, package inventory and runtime
library identities with each attributed run.
