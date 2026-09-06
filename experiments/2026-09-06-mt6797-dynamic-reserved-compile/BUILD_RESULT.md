# Build result

The first Buildbox compile of repository commit
`d72947ccac50465189d997bb5453b6e0958e5ba6` reached the intended real arm64
object and failed in `drivers/net/wireless/mediatek/mt6797/image-binding.c`.
Linux defines `current` as `get_current()`, so using `current` as one function
parameter and one local declaration name produced strict-prototype, invalid
initializer and incompatible-pointer diagnostics. This proves that the
correct object was selected, but it is not a successful compile.

The repair only renamed those two identifiers to `observed`; it changes no
control flow, data, interface or hardware effect. The regenerated patch is
byte-identical to its canonical proposal copy at SHA-256
`684db9c82d60d42cfbb197ce9f52dd3899f76e1f7c29925554162a73d11aafd0`.
Patch replay, 52 predecessor checks, 32 concurrent claim rounds, 72 reserved
checks and ASan/UBSan pass.

The exact follow-up at repository commit
`dca5365cf278f05e4d82cffc0a283d65870e5942` passed. Buildbox job
`dca5365cf278f05e4d82cffc0a283d65870e5942-mt6797-hif-parser-compile-m0`
produced release `7.3.0-rc1-mt6797-hif-parser-compile`; its validated package
inventory is SHA-256
`e8c99f8a80dad553f6d6fc204f5cd5fba86587831dea63994f2cdfc4037919b5`.
The package records the pinned upstream commit, clean repository revision,
10-patch provider series, patchset SHA-256
`10d141bfcd610773a4bdc892fd68d9ad88839dd60fe2e97146ded087bf1c139a`
and resolved config SHA-256
`b7c37fa4b68056470ef392a9d6eef55cd3b56f5310ed9e20fbf91b31231c3282`.

The real `drivers/net/wireless/mediatek/mt6797/image-binding.o` is an ELF64
AArch64 relocatable object at SHA-256
`5e62422dc32fe44e9376994082d4e216ab52d60640e058b3446aedc95cc63c61`.
The bounded [object evidence](object-evidence.txt) retains the read-only
Buildbox receipt, exact symbol sets and whitespace-normalized 103-token compile
command; that receipt hashes to
`7cb1230fe1036eb09ed3e1bafc86d881adfc74e7e8be9a343cc5b36c8df3f631`.
Its recorded compile command uses `aarch64-linux-gnu-gcc` against the exact
source SHA-256
`1bc3041d9a6688a3601913d5bda819eb52098aa33523d148d9341de9ea91d60b`;
the command record hashes to
`9db7da2f1b1ec573291339b7d645be26196845d510396f5625aca64dd22594c0`.
The object defines the public owner/binding APIs, including
`mt6797_image_owner_bind_reserved`, and has real unresolved references to
`of_find_property`, `of_reserved_mem_lookup`,
`of_reserved_mem_region_to_resource`, address/size-cell helpers and OF node
reference helpers. It also retains `of_address_to_resource` for the preserved
static path. No initcall, platform registration, mapping, DMA, power operation
or callback invocation was introduced.

No device was accessed and no boot candidate was created.
