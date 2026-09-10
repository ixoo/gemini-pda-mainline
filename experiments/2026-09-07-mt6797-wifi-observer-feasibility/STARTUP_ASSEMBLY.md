# Startup filesystem assembly

The second private filesystem includes the [PID1 startup](BOOT_STARTUP.md),
the controller and responder, the five retained inputs, and an exact session
manifest. It was assembled and inspected in the RE VM. It is not selected for
boot and has no Android boot container or deployment receipt.

The existing [builder](build-startup-filesystem.py) accepts an optional fourth
argument after the output package:

```sh
python3 build-startup-filesystem.py PRIVATE_INPUTS RUNTIME_TAR NEW_PACKAGE SESSION_JSON
```

Without that argument it still produces an input-only filesystem. With it,
at this assembly revision the builder validated the session schema,
required the exact five startup source hashes and required the generated input
manifest to match the session. It installed `/init` with mode 0500, the four
Python files and session with mode 0400, and the four virtual-filesystem mount
directories. The pinned runtime already contains three controller files; their
copies are replaced by the explicitly hashed current sources. No startup code
is invoked during assembly.

The current [export startup](CAPTURE_DEVICE.md) advances the builder to schema 2
and seven pinned startup sources (six Python files plus `/init`). The second
package recorded here remains the original schema-1 artifact; it is not silently
updated or selected by the new code.

The assembly session binds the verified [44-patch kernel](FULL_KERNEL.md), its
configuration and input manifest, the tested runtime, private inputs and startup
sources. Kernel release and version were extracted from the linked binary.
Its CPU expectation is `0-9`, an unvalidated assembly expectation rather than a
runtime observation. The builder checks session/source/input consistency; the
caller separately verifies the kernel package and its provenance. These fields
do not attest a running kernel. Selecting a device session still requires review
of CPU state and other kernel actors, capture preparation, recovery and boot
arguments. Changing the session changes the candidate identity used by capture.

The [sanitized receipt](results/startup-assembly.json) records 1,629 archive
members and a compressed size of 23,571,711 bytes. An independent newc parser
checked unique relative paths, root ownership, zero timestamps, allowed file
types, absence of paths beneath symlinks, exact startup and input contents,
file modes and mount directories. Comparison against the earlier input-only
archive found only the intended startup files, session, mount directories and
controller file-mode changes. Every other runtime member remained identical.

The packaged startup and controller modules imported successfully using the
packaged ARM64 Python in an isolated RE-VM chroot. Their entry points were not
called. Altered startup and private-input manifest hashes were refused without
publishing a package; temporary assembly directories were removed. All five
package files passed checksum checks in the VM and after private export.

This is filesystem and import evidence, not a PDA boot or a radio test. No
device access occurred. Read-only mount behavior on the native kernel, complete
kernel actor isolation, capture zero-state preparation, container validation
and the owner-approved radio/recovery session remain required. Private firmware,
calibration, manifests and the combined archive remain unpublished.

## Export filesystem

The [third assembly receipt](results/startup-export-assembly.json) records the
schema-2 export action against the verified 46-patch kernel. The builder installs
seven pinned startup sources and binds the exact kernel package, runtime and
private input manifest. Its `0-7` CPU expectation follows the source's CPU8/9
refusal; it is not an observed candidate boot. Earlier packages remain unchanged.

The archive has 1,631 members and is 23,576,689 compressed bytes. Independent
newc inspection verifies exact source/input bytes, modes, root ownership, zero
timestamps, unique relative paths and absence of paths below symlinks. Exactly
five members differ from the second archive: `/init`, startup, the two export
modules and session metadata. All other runtime and retained input bytes match.
All five package files pass VM and fetched checksums; local directories and
files have modes 0700 and 0600 respectively.

The actual packaged ARM64 Python passed 13 startup tests, ten stream tests and
four bridge test groups in an isolated RE-VM chroot with its own devpts mount.
USB controls and device identity were injected; the duplex terminal transfer
used synthetic bytes. No PDA, radio, capture initializer or clearing operation
ran. Temporary extracted roots and mount namespaces were removed. The boot
container, native mounts, actual USB export and recovery remain unvalidated.

## Compact export filesystem

The third archive cannot fit the retained loader's 16 MiB Android image limit.
The [fourth assembly](results/runtime-compact.json) uses the separately verified
[compact runtime](RUNTIME.md#compact-boot-runtime) with the same 46-patch kernel.
The builder and startup preflight now pin that runtime. The earlier archives
remain unchanged and are not candidate inputs.

The new archive is 7,844,041 bytes with 723 members. Independent newc inspection
verified every selected runtime file, all seven current startup source hashes,
all five unchanged private inputs, modes, ownership, timestamps and paths.
Compared with the third assembly, 908 runtime members are absent; only startup's
runtime pin, the private input manifest and session metadata change among the
retained members. Package checksums and startup hashes also pass after export.
All 46 fixture tests passed using the actual packaged ARM64 Python.

With the 8,447,406-byte kernel payload, one 2,048-byte header and page-aligned
payloads project to 16,295,936 bytes, leaving 481,280 bytes below the limit.
This calculation resolves the size obstacle, not the complete LK container,
header/DT handoff, native mounts, physical USB export or recovery requirements.
The subsequent [native container](EXPORT_CONTAINER.md) passes offline assembly
and layout validation; physical handoff and recovery remain outstanding.
