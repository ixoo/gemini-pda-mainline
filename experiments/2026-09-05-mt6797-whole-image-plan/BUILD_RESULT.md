# Whole-image planner Buildbox acceptance

The explicit Buildbox build of `mt6797-hif-parser-compile` completed at
`2acb1bd2377d45402532999145f1c6b836037d65`. Its validated package was fetched
through the normal helper. Only that package was transferred; source and object
inspection remained on the backend.

| Identity | SHA-256 |
| --- | --- |
| Package inventory | `0cb2ebc8f91077357a0dc4990f4b572c4b0e8816848e3ceec019e45f4b471283` |
| Source | `45590c057805bc9cf7281ce04d5dbde5316b7c8b017998cafac301f67e92682d` |
| Six-patch set | `7d94d13406587dd16c50782c081b5995e26dbe70660260298b1661e0982eea20` |
| Resolved configuration | `b7c37fa4b68056470ef392a9d6eef55cd3b56f5310ed9e20fbf91b31231c3282` |
| Image.gz | `7856c9452b536d7fa15a52c932cf21397af1a0383df52eaab476a132858cf825` |
| image-plan.o | `55b8176a6fafd69ab06004a39e322b22e06bc5888be9a9ab7bfd4f7c88c74d0a` |

The package validator accepted provenance, all checksums and 118 DTBs, with
release `7.3.0-rc1-mt6797-hif-parser-compile`. COMPILE_TEST, MT6797_HIF_CORE
and CRC32 resolved enabled. The configuration identity is unchanged from the
[preceding HIF/parser build](../2026-09-05-mt6797-hif-parser-compile/BUILD_RESULT.md).

Backend inspection verified an AArch64 object and kernel compilation command
without a host-test substitution. The compiled source hashes match the reviewed
repository files: `image-plan.c` is
`219d7efa892679fb5bfb8d215f8e306bc16da3a6a879d0c7ee57ff7c3934455e`
and `image-plan.h` is
`425b137eb0d829218600b0e35a2c7268ff2aa4643923bdd148b8061bae33772e`.
All five prepare/describe/admit/get_ordinary/invalidate functions are nonzero
global FUNC definitions. The object refers to the real mtke_parse/mtke_get;
all five definitions match vmlinux and System.map.

The private archive contains image-plan.o, hif.o, mtke.o and crc-kernel.o.
The three preceding objects are byte-identical to the accepted preceding build;
their AArch64/kernel-command checks passed again. All four HIF functions and
parser/CRC symbols remain linked with matching System.map definitions. The
CRC adapter still calls crc32_le with its final complement. No private object
contains initcall or export sections.

Result: compilation and linkage accepted. The mixed-image ownership refusal
remains in force. This creates no runtime caller, firmware load, boot candidate
or hardware support claim. The previously disclosed Checkpatch DCO and
MAINTAINERS findings remain unresolved for upstream submission.
