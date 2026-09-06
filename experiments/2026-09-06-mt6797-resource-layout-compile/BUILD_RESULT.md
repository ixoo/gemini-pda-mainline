# Build result

Buildbox compiled and validated repository commit
`80992c3a76c9db08298935f8068241a389f222e1` with the isolated
`mt6797-hif-parser-compile` profile. Job
`80992c3a76c9db08298935f8068241a389f222e1-mt6797-hif-parser-compile-m0`
produced release `7.3.0-rc1-mt6797-hif-parser-compile` and validated package
inventory SHA-256
`d6b7a5a6b6432cb5d77e9c7089ecc40d549e31c8ff91226d1f0e0e999834edee`.
The package was fetched only through `scripts/buildbox fetch-package` beneath
the ignored Buildbox artifact tree.

| Identity | SHA-256 |
| --- | --- |
| Upstream source | `45590c057805bc9cf7281ce04d5dbde5316b7c8b017998cafac301f67e92682d` |
| Thirteen-patch set | `f7b5310d1c874da9efa82baaa3f181bac1657eea5d3c6fe8a4f033ea9f0b73a8` |
| Resolved configuration | `b7c37fa4b68056470ef392a9d6eef55cd3b56f5310ed9e20fbf91b31231c3282` |
| `Image.gz` | `95e10a7c84bbd17619631f456823d3eb084c76cbac20bbd522605af79b427248` |
| `resource-layout.o` | `dd67589e7315f0ffc48a91f060a8dec73aba38fd3c9ba3b4abd8636cdc48325c` |
| Object command record | `c5532551813cd84a7157795280801d9f45a6e62d10da9be3c5d9ae7d1c4acc24` |

The real object is ELF64 little-endian AArch64 and is a member of the private
MT6797 thin built-in archive. Its command record uses
`ccache aarch64-linux-gnu-gcc` and defines `__KERNEL__` exactly once. The
object defines `mt6797_resource_layout_build`; its expected undefined
`mt6797_remap_encode_common` reference resolves to the predecessor definition
in both the same built-in archive and final `vmlinux`. Compiler-generated
`memset` also resolves in the final link. Its source and header hashes exactly
match the experiment sources. A complete prepared-source search finds one
declaration and one definition of the constructor and no caller. The existing
active binding refusal remains present.

The package validator accepted its complete inventory, 118 DTBs, exact source,
profile, configuration and proposal series. `CONFIG_MT6797_HIF_CORE=y` remains
compile-test-only. This result proves Linux type, compilation, linkage and
predecessor-symbol compatibility for the pure layout constructor. It does not
prove resource freshness or ownership, selector provenance, MPU permissions or
priority, common serialization, external-writer exclusion, mapping, firmware
execution or Wi-Fi support. No device was accessed, and no boot candidate or
hardware write was created.
