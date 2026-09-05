# Private HIF/parser Buildbox result

Buildbox completed and validated `mt6797-hif-parser-compile` at
`b1cf6c1b9f38f7e334f4c6514ed21376dad92ddb`. The validated package was fetched
through the normal helper; no source tree or object files were transferred.

| Identity | SHA-256 |
| --- | --- |
| Package inventory | `910a00382d6ecdaa8ff77a6a49752063818f6d1e53b0b002260749b6817fee85` |
| Source | `45590c057805bc9cf7281ce04d5dbde5316b7c8b017998cafac301f67e92682d` |
| Five-patch set | `8899bed441b001ab224efb95bf2aa02dc1f1f6c81816cecb01dac5bd6a40b80e` |
| Resolved configuration | `b7c37fa4b68056470ef392a9d6eef55cd3b56f5310ed9e20fbf91b31231c3282` |
| Image.gz | `64f1359201d25c04883375a61b244c235d8d0c7daa58f5aaac88edb6078fd5c6` |

The release is `7.3.0-rc1-mt6797-hif-parser-compile`. The package validator
accepted its provenance, complete inventory and 118 DTBs. Required networking
menus, COMPILE_TEST, MT6797_HIF_CORE and CRC32 all resolved enabled. The job's
`warning:`/`error:` scan returned no matches.

Read-only backend inspection confirmed all three private objects are ELF64
little-endian AArch64. Their command records define `__KERNEL__` and contain no
host-test substitution. Source hashes match the pinned packaged inputs. Nonzero
global functions include HIF alloc/free/read32/download_section, mtke_parse,
mtke_get and mtke_crc32; both HIF scalar callbacks are nonzero local functions.
All seven global functions plus crc32_le have matching definitions and addresses
in vmlinux and System.map. The private archive contains all three objects.

| Object | SHA-256 |
| --- | --- |
| hif.o | `9a730ee9ea3aadfa7dd88581b52f2bc531f76b4d6855c91e7048484f8ab3bc5a` |
| mtke.o | `85b9edb8d80b226a86eb6d8ddaa78c04f874ffed251795ae470b8e356b2f4666` |
| crc-kernel.o | `77803e5c638a2ff1e63cec3f9ac59cc3f1fcc9e4d107c3f517eca9bfe40ae034` |

The parser refers to mtke_crc32, whose adapter has a CALL26 relocation to
crc32_le, an initial all-ones value and final `mvn` complement. The HIF write
callback emits `dmb oshst` before its 32-bit store; the read callback emits its
32-bit load before `dmb oshld`. No private object contains initcall or export
sections; reviewed sources have no registration or runtime caller.

The proposal incorrectly expected a standalone `lib/crc/crc32.o`. The first
acceptance check refused on that missing path. The pinned `scripts/Makefile.build`
lines 93–95 flatten built-in composite objects into their parts; the actual CRC
archive contains `crc32-main.o` and `arm64/crc32-core.o`. The former defines
crc32_le, which also matches the linked symbol. This verified Kbuild composition
corrects the path expectation without changing the kernel or relaxing linkage
acceptance. The original proposal remains an immutable record of that mistake.

Result: compilation and linkage accepted. No boot candidate, runtime owner,
firmware loading, radio action or hardware support claim is created. Existing
Checkpatch metadata and host-only typedef findings remain disclosed.
