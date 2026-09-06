# Build result

Buildbox compiled and validated repository commit
`6e52fb732b1bcf3ffc936b8f9fdbd8d38089d9a2` with the
`mt6797-hif-parser-compile` profile. Job
`6e52fb732b1bcf3ffc936b8f9fdbd8d38089d9a2-mt6797-hif-parser-compile-m0`
produced release `7.3.0-rc1-mt6797-hif-parser-compile` and validated package
inventory SHA-256
`402f7d23d1b3ae76ecb9ac4d83749092ef863142807351d465711f6c997f6fb9`.
The package was fetched only through `scripts/buildbox fetch-package` beneath
the ignored buildbox artifact tree.

| Identity | SHA-256 |
| --- | --- |
| Upstream source | `45590c057805bc9cf7281ce04d5dbde5316b7c8b017998cafac301f67e92682d` |
| Eleven-patch set | `c0cd312a209936a139db73c794d6b1f21133431c4d5f8aeb8f5b252e4e2af074` |
| Resolved configuration | `b7c37fa4b68056470ef392a9d6eef55cd3b56f5310ed9e20fbf91b31231c3282` |
| Image.gz | `059babe5ab8937f6f91c9c6faee8b24bd98f24ff7b9fd228e7ec738a75256dc6` |
| `emi-abi.o` | `c0fe41eb1248c7cce8b68497697e256c2bcd5a6daac17181909652fad7d68d2d` |
| Object command record | `8de4ed4f27ffb9e49fd33e1db36a50e473c314109fc2e3e3dc07f3f31b91384a` |

The real object is ELF64 little-endian AArch64 and is present in the private
MT6797 built-in archive. Its command record uses `aarch64-linux-gnu-gcc`,
defines `__KERNEL__`, contains 103 normalized shell tokens, and hashes those
NUL-joined tokens to
`adefe26f3d126de27f01b7edb50b34315de8e781e3397cd34e26e2d8f3ddfa00`.
The object defines both `mt6797_emi_prepare` and
`mt6797_emi_decode_result` and has no undefined symbols. Its source and header
hashes exactly match the experiment sources. A complete source-tree search
finds only their declarations and definitions, so the object is linked but
unreferenced.

The package validator accepted its complete inventory, 118 DTBs, exact source,
profile, configuration and proposal series. `CONFIG_MT6797_HIF_CORE=y` remains
compile-test-only. This result proves the helper's Linux type, compilation and
linkage compatibility. It does not prove an EMI owner, selector state, region
policy, secure service, reserved-memory mapping, firmware execution or Wi-Fi
support. No device was accessed and no boot candidate or hardware write was
created.
