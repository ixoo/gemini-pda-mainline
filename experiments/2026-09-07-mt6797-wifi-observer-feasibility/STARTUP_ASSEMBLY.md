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
requires the exact five startup source hashes, and requires the generated input
manifest to match the session. It installs `/init` with mode 0500, the four
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
