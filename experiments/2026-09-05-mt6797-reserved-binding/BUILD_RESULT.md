# Reserved-memory descriptor Buildbox acceptance

The explicit `mt6797-hif-parser-compile` build at
`1d12bc918ad87d25e4df5bd212179c8e7e678e86` passed compilation, linkage and
package validation. The normal helper fetched only the validated package;
source and object inspection stayed on Buildbox.

| Identity | SHA-256 |
| --- | --- |
| Package inventory | `2728bb312f01258265e696460f77b5dcc7b6deb5eda75a4c69881718171567a5` |
| Nine-patch set | `331130d2ea0292be5b24e3c4ad3978cfc837bc5bb049b9b20e6f02aa0c4c4c01` |
| Resolved configuration | `b7c37fa4b68056470ef392a9d6eef55cd3b56f5310ed9e20fbf91b31231c3282` |
| Image.gz | `1567fd464fe739321f0629b0908848f2daafa91562b3c5c2b106cd537bef9c20` |
| image-binding.o | `3e9c4c62e53c0af39c185004d4e0b18191af12935aca18580a74a0bf8cd21eb4` |

All package checksums and provenance passed, including 118 DTBs. Release is
`7.3.0-rc1-mt6797-hif-parser-compile`. Source archive and configuration are
unchanged from the [preceding build](../2026-09-05-mt6797-hif-start-core/BUILD_RESULT.md).
The managed provider source path was refreshed under the backend lock for the
changed patch set. No extra experiment-specific Linux tree was retained.

The backend C/header hashes exactly match [proposal.json](proposal.json).
The object is AArch64 and its saved command uses the real kernel compiler
without `MT6797_BINDING_HOST_TEST`. It is a member of the private archive.
The three new APIs have nonzero definitions in the object and vmlinux, with
matching System.map entries: bind_reserved is 400 bytes, reserved_info is
240 bytes, and unbind_reserved is 204 bytes.

Undefined references use actual Linux device, phandle, OF property/address and
reserved-memory lookup/resource APIs. OF, OF_ADDRESS and OF_RESERVED_MEM are
enabled. The static OF configuration may inline node reference operations;
this does not test dynamic OF lifetime behavior. Kernel allocation, mutex and
image-plan references remain. The HIF, image-plan, parser and CRC objects are
byte-identical to the preceding accepted build.

The object has no initcall/export sections, generation test hook, mapping,
DMA setup, SMC or driver-registration reference. Disassembly of binding begin
returns validation errors or -95 (EOPNOTSUPP); it does not return active success.
Source review and host fixtures retain the separate caller-stabilization and
exclusive-ownership limits described in [README.md](README.md).

Result: isolated compilation and linkage accepted. No device access, firmware
load, runtime resource claim or boot candidate is admitted. This remains a
synthetic non-certifying experiment archive, not an upstream submission or a
Wi-Fi hardware-support result.
