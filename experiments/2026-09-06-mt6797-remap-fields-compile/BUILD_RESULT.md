# Build result

Buildbox compiled and validated repository commit
`8af75b14cba55dcd1078ac74eb96b11e1656b79a` with the isolated
`mt6797-hif-parser-compile` profile. Job
`8af75b14cba55dcd1078ac74eb96b11e1656b79a-mt6797-hif-parser-compile-m0`
produced release `7.3.0-rc1-mt6797-hif-parser-compile` and validated package
inventory SHA-256
`a686a5fb6807ea78df3adfefb830a451d59939d94d3336282d42bdc4b131e11e`.
The package was fetched only through `scripts/buildbox fetch-package` beneath
the ignored Buildbox artifact tree.

| Identity | SHA-256 |
| --- | --- |
| Upstream source | `45590c057805bc9cf7281ce04d5dbde5316b7c8b017998cafac301f67e92682d` |
| Twelve-patch set | `328274e36f3aa70956025ae35045f7f670bb3aff14616402cfd788aa8919a197` |
| Resolved configuration | `b7c37fa4b68056470ef392a9d6eef55cd3b56f5310ed9e20fbf91b31231c3282` |
| `Image.gz` | `f93eec235d8c1159ff265e8f503eb34fbc7638f483d80fbf00908d4972f1081f` |
| `remap-fields.o` | `2c6f617a4f4b2c299f2867c834347e47fee61ee925895efc3884d8e2903db9f4` |
| Object command record | `bd18af23e08ea02563945a8c66646fa1436e9b9e627b6efa851f5de024398706` |

The real object is ELF64 little-endian AArch64 and is a member of the private
MT6797 thin built-in archive. Its command record uses
`aarch64-linux-gnu-gcc`, defines `__KERNEL__` exactly once, contains 103
normalized shell tokens, and hashes those NUL-joined tokens to
`aeb725de5bc7a551711c3c4fba3fa94c07aa40da8dcd771f97c87513bc98f83f`.
The object defines all four remap helper functions and has no undefined
symbols. Its source and header hashes exactly match the experiment sources.
A complete prepared-source search finds one declaration and one definition of
each public helper and no caller.

The package validator accepted its complete inventory, 118 DTBs, exact source,
profile, configuration and proposal series. `CONFIG_MT6797_HIF_CORE=y` remains
compile-test-only. This result proves the helper's Linux type, compilation and
linkage compatibility. It does not prove a shared register owner, current
register state, owner provenance, serialization, readback, external-writer
exclusion, mapping, firmware execution or Wi-Fi support. No device was
accessed, and no boot candidate or hardware write was created.
